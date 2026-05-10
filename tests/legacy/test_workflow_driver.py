"""Tests for WorkflowDriver — pure step machine.

Validates:
1. start_workflow returns StepResult with step event + obs event.
2. start_workflow with no plan returns terminal failed StepResult.
3. advance_step emits next step event for non-terminal advancement.
4. advance_step returns terminal completed when all steps done.
5. fail_workflow returns terminal failed with reason.
6. cancel_workflow returns terminal cancelled with metadata.
7. Step events carry _orch_intent_id, _orch_step_index, _orch_plan_id.
8. Driver NEVER emits orch_intent_completed/failed/cancelled.
"""

from __future__ import annotations

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.substrate.intent_models import (
    Intent,
    IntentStatus,
    IntentType,
    PlanStep,
    compute_intent_id,
)
from umh.substrate.plan_registry import PlanRegistry
from umh.substrate.workflow_driver import StepResult, WorkflowDriver


def _make_intent(
    intent_type: IntentType = IntentType.LIFECYCLE_FINALIZE,
    goal: dict | None = None,
    session_name: str = "test_session",
    status: IntentStatus = IntentStatus.PENDING,
    current_step: int = 0,
    total_steps: int = 0,
) -> Intent:
    goal = goal or {"session_name": session_name}
    return Intent(
        intent_id=compute_intent_id(intent_type, goal),
        intent_type=intent_type,
        goal=goal,
        session_name=session_name,
        status=status,
        created_at="2026-04-17T00:00:00+00:00",
        current_step=current_step,
        total_steps=total_steps,
    )


def _two_step_generator(intent: Intent, state: dict) -> tuple[PlanStep, ...]:
    return (
        PlanStep(step_index=0, event_type="step_a", payload={"idx": 0}),
        PlanStep(step_index=1, event_type="step_b", payload={"idx": 1}),
    )


def _one_step_generator(intent: Intent, state: dict) -> tuple[PlanStep, ...]:
    return (PlanStep(step_index=0, event_type="only_step", payload={}),)


def _empty_generator(intent: Intent, state: dict) -> tuple[PlanStep, ...]:
    return ()


def _make_registry(*pairs: tuple[IntentType, ...]) -> PlanRegistry:
    reg = PlanRegistry()
    return reg


def _make_two_step_registry() -> PlanRegistry:
    reg = PlanRegistry()
    reg.register(IntentType.LIFECYCLE_FINALIZE, _two_step_generator)
    return reg


def _make_one_step_registry() -> PlanRegistry:
    reg = PlanRegistry()
    reg.register(IntentType.LIFECYCLE_FINALIZE, _one_step_generator)
    return reg


_LIFECYCLE_EVENTS = {
    "orch_intent_completed",
    "orch_intent_failed",
    "orch_intent_cancelled",
}


class TestWorkflowDriverStartWorkflow(unittest.TestCase):
    def test_start_emits_step_event_and_obs(self):
        driver = WorkflowDriver(_make_two_step_registry())
        intent = _make_intent()
        result = driver.start_workflow(intent, {})

        self.assertFalse(result.terminal)
        self.assertIsNone(result.terminal_status)
        self.assertEqual(len(result.events), 2)

        step_event = result.events[0]
        obs_event = result.events[1]
        self.assertEqual(step_event.event_type, "step_a")
        self.assertEqual(obs_event.event_type, "orch_intent_step_dispatched")

    def test_start_step_event_carries_orch_metadata(self):
        driver = WorkflowDriver(_make_two_step_registry())
        intent = _make_intent()
        result = driver.start_workflow(intent, {})

        step_event = result.events[0]
        self.assertEqual(step_event.metadata["_orch_intent_id"], intent.intent_id)
        self.assertEqual(step_event.metadata["_orch_step_index"], 0)
        self.assertIn("_orch_plan_id", step_event.metadata)

    def test_start_mutations_update_intent(self):
        driver = WorkflowDriver(_make_two_step_registry())
        intent = _make_intent()
        result = driver.start_workflow(intent, {})

        self.assertTrue(len(result.mutations) >= 1)
        set_mut = result.mutations[0]
        self.assertEqual(set_mut["op"], "SET")
        self.assertEqual(set_mut["value"]["status"], IntentStatus.ACTIVE.value)
        self.assertEqual(set_mut["value"]["total_steps"], 2)

    def test_start_no_plan_returns_terminal_failed(self):
        reg = PlanRegistry()  # empty — no generators
        driver = WorkflowDriver(reg)
        intent = _make_intent()
        result = driver.start_workflow(intent, {})

        self.assertTrue(result.terminal)
        self.assertEqual(result.terminal_status, "failed")
        self.assertEqual(result.terminal_reason, "no_plan_available")
        self.assertEqual(len(result.events), 0)

    def test_start_empty_plan_returns_terminal_failed(self):
        reg = PlanRegistry()
        reg.register(IntentType.LIFECYCLE_FINALIZE, _empty_generator)
        driver = WorkflowDriver(reg)
        intent = _make_intent()
        result = driver.start_workflow(intent, {})

        self.assertTrue(result.terminal)
        self.assertEqual(result.terminal_status, "failed")

    def test_start_never_emits_lifecycle_events(self):
        driver = WorkflowDriver(_make_two_step_registry())
        intent = _make_intent()
        result = driver.start_workflow(intent, {})

        for ev in result.events:
            self.assertNotIn(ev.event_type, _LIFECYCLE_EVENTS)


class TestWorkflowDriverAdvanceStep(unittest.TestCase):
    def test_advance_to_next_step(self):
        driver = WorkflowDriver(_make_two_step_registry())
        intent = _make_intent(status=IntentStatus.ACTIVE, current_step=0, total_steps=2)
        result = driver.advance_step(intent, 0, {})

        self.assertFalse(result.terminal)
        self.assertEqual(len(result.events), 2)
        self.assertEqual(result.events[0].event_type, "step_b")
        self.assertEqual(result.events[0].metadata["_orch_step_index"], 1)

    def test_advance_past_last_step_terminal_completed(self):
        driver = WorkflowDriver(_make_two_step_registry())
        intent = _make_intent(status=IntentStatus.ACTIVE, current_step=1, total_steps=2)
        result = driver.advance_step(intent, 1, {})

        self.assertTrue(result.terminal)
        self.assertEqual(result.terminal_status, "completed")
        self.assertEqual(result.steps_executed, 2)
        self.assertEqual(len(result.events), 0)

    def test_advance_single_step_plan_completes_immediately(self):
        driver = WorkflowDriver(_make_one_step_registry())
        intent = _make_intent(status=IntentStatus.ACTIVE, current_step=0, total_steps=1)
        result = driver.advance_step(intent, 0, {})

        self.assertTrue(result.terminal)
        self.assertEqual(result.terminal_status, "completed")

    def test_advance_plan_disappeared_returns_failed(self):
        reg = PlanRegistry()  # no generators
        driver = WorkflowDriver(reg)
        intent = _make_intent(status=IntentStatus.ACTIVE, current_step=0, total_steps=2)
        result = driver.advance_step(intent, 0, {})

        self.assertTrue(result.terminal)
        self.assertEqual(result.terminal_status, "failed")
        self.assertIn("plan_disappeared", result.terminal_reason)

    def test_advance_never_emits_lifecycle_events(self):
        driver = WorkflowDriver(_make_two_step_registry())
        intent = _make_intent(status=IntentStatus.ACTIVE, current_step=0, total_steps=2)
        # Terminal advance
        result = driver.advance_step(intent, 1, {})
        for ev in result.events:
            self.assertNotIn(ev.event_type, _LIFECYCLE_EVENTS)


class TestWorkflowDriverFailCancel(unittest.TestCase):
    def test_fail_workflow(self):
        driver = WorkflowDriver(_make_two_step_registry())
        intent = _make_intent(status=IntentStatus.ACTIVE)
        result = driver.fail_workflow(intent, "test_failure")

        self.assertTrue(result.terminal)
        self.assertEqual(result.terminal_status, "failed")
        self.assertEqual(result.terminal_reason, "test_failure")
        self.assertEqual(len(result.events), 0)

        # Mutation sets FAILED status
        self.assertTrue(
            any(
                m["op"] == "SET" and m["value"]["status"] == IntentStatus.FAILED.value
                for m in result.mutations
            )
        )

    def test_cancel_workflow(self):
        driver = WorkflowDriver(_make_two_step_registry())
        intent = _make_intent(status=IntentStatus.ACTIVE)
        result = driver.cancel_workflow(intent, "operator_requested")

        self.assertTrue(result.terminal)
        self.assertEqual(result.terminal_status, "cancelled")
        self.assertEqual(result.terminal_reason, "operator_requested")
        self.assertEqual(len(result.events), 0)

        # Mutation includes cancelled metadata
        set_mut = next(m for m in result.mutations if m["op"] == "SET")
        self.assertTrue(set_mut["value"]["metadata"]["cancelled"])
        self.assertEqual(
            set_mut["value"]["metadata"]["cancel_reason"], "operator_requested"
        )


if __name__ == "__main__":
    unittest.main()
