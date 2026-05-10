"""Tests for cron and result-driven ingress activation.

Validates:
A. Cron activation — active mode emits cron_intent_requested, inactive unchanged.
B. Result-driven ingress — follow-on from completed intent emits result_intent_requested.
C. No double-processing — single-owner sequencing, no duplicate intent creation.
D. Regression safety — existing orchestration tests still pass.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, "/opt/OS")

from umh.substrate.event_log_runtime import EventLogRuntime
from umh.substrate.event_scheduler import EventScheduler, SchedulerEvent
from umh.substrate.intent_models import (
    IntentStatus,
    IntentType,
    PlanStep,
    compute_intent_id,
    intent_store_key,
)
from umh.substrate.orchestration_bootstrap import bootstrap_orchestration
from umh.substrate.orchestration_mode import set_orchestration_mode_for_testing
from umh.substrate.runtime_state_store import RuntimeStateStore
from umh.substrate.trigger_adapters import from_cron, from_result


# ── Helpers ──────────────────────────────────────────────────────────


def _make_scheduler() -> tuple[EventScheduler, RuntimeStateStore]:
    store = RuntimeStateStore()
    log = EventLogRuntime(log_path=Path(tempfile.mktemp(suffix=".jsonl")))
    scheduler = EventScheduler(store=store, event_log=log)
    return scheduler, store


def _one_step_generator(intent, state):
    return (PlanStep(step_index=0, event_type="test_step_event", payload={}),)


def _two_step_generator(intent, state):
    return (
        PlanStep(step_index=0, event_type="test_step_1", payload={}),
        PlanStep(step_index=1, event_type="test_step_2", payload={}),
    )


def _workflow_run_generator(intent, state):
    """Plan generator for WORKFLOW_RUN intents — single step."""
    return (
        PlanStep(
            step_index=0,
            event_type="workflow_step",
            payload={"workflow": intent.goal.get("workflow", "unknown")},
        ),
    )


# ── A. Cron Activation Tests ─────────────────────────────────────────


class TestCronIngressActiveMode(unittest.TestCase):
    """A.1: active mode cron source emits cron_intent_requested and reaches coordinator."""

    def setUp(self):
        set_orchestration_mode_for_testing(True)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_from_cron_builds_correct_event(self):
        """from_cron adapter produces cron_intent_requested with correct metadata."""
        event = from_cron(
            intent_type="workflow_run",
            goal={"workflow": "open_day", "workspace": "builder"},
            session_name="day_workflow",
            cron_source="open_day",
        )
        self.assertEqual(event.event_type, "cron_intent_requested")
        self.assertEqual(event.payload["intent_type"], "workflow_run")
        self.assertEqual(event.payload["goal"]["workflow"], "open_day")
        self.assertIn("cron:open_day", event.source)

    def test_cron_event_reaches_coordinator_and_creates_intent(self):
        """Emitting cron_intent_requested into wired scheduler creates an intent."""
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler)
        coord._plan_registry.register(IntentType.WORKFLOW_RUN, _workflow_run_generator)

        cron_event = from_cron(
            intent_type="workflow_run",
            goal={"workflow": "open_day"},
            session_name="day_workflow",
            cron_source="open_day",
        )
        scheduler.emit(cron_event)
        result = scheduler.run()

        # At least the ingress event was processed
        self.assertGreater(result.events_processed, 0)

        # Intent should exist in store
        goal = {"workflow": "open_day"}
        intent_id = compute_intent_id(IntentType.WORKFLOW_RUN, goal)
        intent_data = store.get(intent_store_key(intent_id))
        self.assertIsNotNone(intent_data, "cron intent was not created in store")
        self.assertEqual(intent_data["intent_type"], "workflow_run")
        self.assertIn(intent_data["status"], ["active", "pending"])

    def test_cron_dedup_prevents_duplicate_intent(self):
        """Same cron_intent_requested emitted twice creates only one intent."""
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler)
        coord._plan_registry.register(IntentType.WORKFLOW_RUN, _workflow_run_generator)

        event1 = from_cron(
            intent_type="workflow_run",
            goal={"workflow": "open_day"},
            session_name="day_workflow",
            cron_source="open_day",
        )
        event2 = from_cron(
            intent_type="workflow_run",
            goal={"workflow": "open_day"},
            session_name="day_workflow",
            cron_source="open_day",
        )

        scheduler.emit(event1)
        scheduler.run()
        scheduler.emit(event2)
        scheduler.run()

        # Count intents in store
        snapshot = store.snapshot()
        intent_keys = [k for k in snapshot if k.startswith("intent:")]
        self.assertEqual(len(intent_keys), 1, "duplicate cron intent was created")


class TestCronIngressInactiveMode(unittest.TestCase):
    """A.2: inactive mode cron path unchanged."""

    def setUp(self):
        set_orchestration_mode_for_testing(False)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_day_workflows_open_day_returns_normal_when_inactive(self):
        """open_day returns normal response (not orchestration_deferred) when inactive."""
        from umh.substrate.day_workflows import _try_emit_cron_intent

        result = _try_emit_cron_intent(
            intent_type="workflow_run",
            goal={"workflow": "open_day"},
            session_name="day_workflow",
            cron_source="open_day",
        )
        self.assertIsNone(result, "should return None when orchestration inactive")

    def test_day_workflows_close_day_returns_normal_when_inactive(self):
        """close_day returns normal response (not orchestration_deferred) when inactive."""
        from umh.substrate.day_workflows import _try_emit_cron_intent

        result = _try_emit_cron_intent(
            intent_type="workflow_run",
            goal={"workflow": "close_day"},
            session_name="day_workflow",
            cron_source="close_day",
        )
        self.assertIsNone(result, "should return None when orchestration inactive")


class TestCronActiveModeDeferral(unittest.TestCase):
    """A.3: active mode day_workflows helper returns deferred response."""

    def setUp(self):
        set_orchestration_mode_for_testing(True)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_try_emit_cron_intent_returns_deferred_when_active(self):
        """_try_emit_cron_intent returns orchestration_deferred dict when active."""
        from umh.substrate.day_workflows import _try_emit_cron_intent

        result = _try_emit_cron_intent(
            intent_type="workflow_run",
            goal={"workflow": "open_day"},
            session_name="day_workflow",
            cron_source="open_day",
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "orchestration_deferred")
        self.assertEqual(result["intent_type"], "workflow_run")
        self.assertEqual(result["cron_source"], "open_day")
        self.assertIn("event_id", result)


# ── B. Result-Driven Ingress Tests ───────────────────────────────────


class TestResultDrivenIngress(unittest.TestCase):
    """B.1: completed intent with follow_on emits result_intent_requested."""

    def setUp(self):
        set_orchestration_mode_for_testing(True)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_follow_on_emitted_on_intent_completion(self):
        """When an intent with follow_on completes, result_intent_requested is emitted."""
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler)
        coord._plan_registry.register(
            IntentType.LIFECYCLE_FINALIZE, _one_step_generator
        )
        coord._plan_registry.register(IntentType.LIFECYCLE_CLEAR, _one_step_generator)

        # Create intent with follow_on
        ingress = SchedulerEvent(
            event_type="operator_intent_requested",
            session_name="test_session",
            source="test",
            payload={
                "intent_type": "lifecycle_finalize",
                "goal": {
                    "session_name": "test_session",
                    "follow_on": {
                        "intent_type": "lifecycle_clear",
                        "goal": {"session_name": "test_session"},
                        "priority": 50,
                    },
                },
                "priority": 100,
            },
        )
        scheduler.emit(ingress)
        scheduler.run()

        # Get intent_id for the finalize intent
        finalize_goal = {
            "session_name": "test_session",
            "follow_on": {
                "intent_type": "lifecycle_clear",
                "goal": {"session_name": "test_session"},
                "priority": 50,
            },
        }
        finalize_id = compute_intent_id(IntentType.LIFECYCLE_FINALIZE, finalize_goal)

        # Find the step event to simulate execution completion
        snapshot = store.snapshot()
        step_event_ids = [
            k.split(".", 1)[1] for k in snapshot if k.startswith("intent_step_events.")
        ]
        self.assertGreater(len(step_event_ids), 0, "no step events recorded")
        step_event_id = step_event_ids[0]

        # Simulate execution completion
        exec_id = "exec_followon_001"
        store.set(
            f"in_flight_executions.{exec_id}",
            {"original_request": {"causal_event_id": step_event_id}},
        )

        exec_result = SchedulerEvent(
            event_type="execution_completed",
            session_name="test_session",
            source="execution_worker",
            payload={
                "result": {
                    "execution_id": exec_id,
                    "correlation_id": "corr_followon_1",
                    "causal_event_id": step_event_id,
                    "primitive_name": "test_prim",
                    "status": "succeeded",
                    "outputs": {},
                },
            },
        )
        scheduler.emit(exec_result)
        scheduler.run()

        # The finalize intent should be COMPLETED
        finalize_data = store.get(intent_store_key(finalize_id))
        self.assertIsNotNone(finalize_data)
        self.assertEqual(finalize_data["status"], IntentStatus.COMPLETED.value)

        # The follow-on clear intent should now exist
        clear_goal = {"session_name": "test_session"}
        clear_id = compute_intent_id(IntentType.LIFECYCLE_CLEAR, clear_goal)
        clear_data = store.get(intent_store_key(clear_id))
        self.assertIsNotNone(clear_data, "follow-on intent was not created")
        self.assertEqual(clear_data["intent_type"], "lifecycle_clear")

    def test_no_follow_on_when_goal_lacks_field(self):
        """Intent without follow_on does not emit result_intent_requested."""
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler)
        coord._plan_registry.register(
            IntentType.LIFECYCLE_FINALIZE, _one_step_generator
        )

        # Intent WITHOUT follow_on
        ingress = SchedulerEvent(
            event_type="operator_intent_requested",
            session_name="test_session",
            source="test",
            payload={
                "intent_type": "lifecycle_finalize",
                "goal": {"session_name": "test_session"},
                "priority": 100,
            },
        )
        scheduler.emit(ingress)
        scheduler.run()

        goal = {"session_name": "test_session"}
        finalize_id = compute_intent_id(IntentType.LIFECYCLE_FINALIZE, goal)

        snapshot = store.snapshot()
        step_event_ids = [
            k.split(".", 1)[1] for k in snapshot if k.startswith("intent_step_events.")
        ]
        step_event_id = step_event_ids[0]

        exec_id = "exec_no_followon_001"
        store.set(
            f"in_flight_executions.{exec_id}",
            {"original_request": {"causal_event_id": step_event_id}},
        )

        exec_result = SchedulerEvent(
            event_type="execution_completed",
            session_name="test_session",
            source="execution_worker",
            payload={
                "result": {
                    "execution_id": exec_id,
                    "correlation_id": "corr_no_followon",
                    "causal_event_id": step_event_id,
                    "primitive_name": "test_prim",
                    "status": "succeeded",
                    "outputs": {},
                },
            },
        )
        scheduler.emit(exec_result)
        scheduler.run()

        # Only one intent should exist (the finalize)
        snapshot = store.snapshot()
        intent_keys = [k for k in snapshot if k.startswith("intent:")]
        self.assertEqual(len(intent_keys), 1, "unexpected follow-on intent created")

    def test_from_result_builds_correct_event(self):
        """from_result adapter produces result_intent_requested with correct metadata."""
        event = from_result(
            intent_type="lifecycle_clear",
            goal={"session_name": "test"},
            session_name="test",
            triggering_intent_id="int_abc123",
        )
        self.assertEqual(event.event_type, "result_intent_requested")
        self.assertEqual(event.payload["intent_type"], "lifecycle_clear")
        self.assertEqual(event.source, "intent_coordinator")
        self.assertEqual(event.metadata.get("triggering_intent_id"), "int_abc123")

    def test_result_ingress_reaches_coordinator(self):
        """result_intent_requested routed through scheduler reaches coordinator."""
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler)
        coord._plan_registry.register(IntentType.LIFECYCLE_CLEAR, _one_step_generator)

        result_event = from_result(
            intent_type="lifecycle_clear",
            goal={"session_name": "result_test"},
            session_name="result_test",
            triggering_intent_id="int_trigger_001",
        )
        scheduler.emit(result_event)
        result = scheduler.run()

        self.assertGreater(result.events_processed, 0)

        goal = {"session_name": "result_test"}
        intent_id = compute_intent_id(IntentType.LIFECYCLE_CLEAR, goal)
        intent_data = store.get(intent_store_key(intent_id))
        self.assertIsNotNone(intent_data, "result ingress intent was not created")
        self.assertEqual(intent_data["intent_type"], "lifecycle_clear")


# ── C. No Double-Processing Tests ────────────────────────────────────


class TestNoDoubleProcessing(unittest.TestCase):
    """C: active mode has single-owner sequencing, no duplicate progression."""

    def setUp(self):
        set_orchestration_mode_for_testing(True)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_duplicate_cron_ingress_rejected(self):
        """Same cron event emitted after intent exists is rejected (dedup)."""
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler)
        coord._plan_registry.register(IntentType.WORKFLOW_RUN, _workflow_run_generator)

        goal = {"workflow": "open_day"}
        event = from_cron(
            intent_type="workflow_run",
            goal=goal,
            session_name="day_workflow",
            cron_source="open_day",
        )

        # First emission
        scheduler.emit(event)
        scheduler.run()

        # Second emission with same goal
        event2 = from_cron(
            intent_type="workflow_run",
            goal=goal,
            session_name="day_workflow",
            cron_source="open_day",
        )
        scheduler.emit(event2)
        scheduler.run()

        # Only one intent
        snapshot = store.snapshot()
        intent_keys = [k for k in snapshot if k.startswith("intent:")]
        self.assertEqual(len(intent_keys), 1)

    def test_duplicate_result_ingress_rejected(self):
        """Same result_intent_requested emitted twice creates only one intent."""
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler)
        coord._plan_registry.register(IntentType.LIFECYCLE_CLEAR, _one_step_generator)

        goal = {"session_name": "dedup_test"}
        event1 = from_result(
            intent_type="lifecycle_clear",
            goal=goal,
            session_name="dedup_test",
            triggering_intent_id="int_trig_1",
        )
        event2 = from_result(
            intent_type="lifecycle_clear",
            goal=goal,
            session_name="dedup_test",
            triggering_intent_id="int_trig_2",
        )

        scheduler.emit(event1)
        scheduler.run()
        scheduler.emit(event2)
        scheduler.run()

        snapshot = store.snapshot()
        intent_keys = [k for k in snapshot if k.startswith("intent:")]
        self.assertEqual(len(intent_keys), 1, "duplicate result intent was created")

    def test_planner_strategy_still_yields_in_active_mode(self):
        """PlannerStrategy yields when active — no double lifecycle driving."""
        from umh.substrate.planner import PlannerStrategy

        strategy = PlannerStrategy()
        result = strategy.evaluate({})
        self.assertIsNone(result)

    def test_max_active_one_intent_at_a_time(self):
        """Only one intent is ACTIVE at a time (max_active=1)."""
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler, max_active=1)
        coord._plan_registry.register(
            IntentType.LIFECYCLE_FINALIZE, _one_step_generator
        )
        coord._plan_registry.register(IntentType.LIFECYCLE_CLEAR, _one_step_generator)

        # Emit two different intents
        e1 = from_cron(
            intent_type="lifecycle_finalize",
            goal={"session_name": "s1"},
            session_name="s1",
            cron_source="cron1",
        )
        e2 = from_cron(
            intent_type="lifecycle_clear",
            goal={"session_name": "s2"},
            session_name="s2",
            cron_source="cron2",
        )
        scheduler.emit(e1)
        scheduler.emit(e2)
        scheduler.run()

        # Count active intents
        snapshot = store.snapshot()
        active_keys = [k for k in snapshot if k.startswith("active_intent.")]
        self.assertEqual(len(active_keys), 1, "more than one active intent")


# ── D. Regression Safety Tests ───────────────────────────────────────


class TestRegressionSafety(unittest.TestCase):
    """D: existing orchestration behavior preserved."""

    def setUp(self):
        set_orchestration_mode_for_testing(None)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_operator_ingress_still_works_active(self):
        """Operator ingress remains functional in active mode."""
        set_orchestration_mode_for_testing(True)
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler)
        coord._plan_registry.register(
            IntentType.LIFECYCLE_FINALIZE, _one_step_generator
        )

        from umh.substrate.trigger_adapters import from_operator

        event = from_operator(
            intent_type="lifecycle_finalize",
            goal={"session_name": "regression_test"},
            session_name="regression_test",
            operator_id="antony",
        )
        scheduler.emit(event)
        scheduler.run()

        goal = {"session_name": "regression_test"}
        intent_id = compute_intent_id(IntentType.LIFECYCLE_FINALIZE, goal)
        intent_data = store.get(intent_store_key(intent_id))
        self.assertIsNotNone(intent_data)

    def test_decision_ingress_still_works_active(self):
        """Decision ingress remains functional in active mode."""
        set_orchestration_mode_for_testing(True)
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler)
        coord._plan_registry.register(
            IntentType.LIFECYCLE_FINALIZE, _one_step_generator
        )

        from umh.substrate.trigger_adapters import from_decision

        event = from_decision(
            intent_type="lifecycle_finalize",
            goal={"session_name": "decision_test"},
            session_name="decision_test",
        )
        scheduler.emit(event)
        scheduler.run()

        goal = {"session_name": "decision_test"}
        intent_id = compute_intent_id(IntentType.LIFECYCLE_FINALIZE, goal)
        intent_data = store.get(intent_store_key(intent_id))
        self.assertIsNotNone(intent_data)

    def test_inactive_mode_no_orchestration_behavior(self):
        """When inactive, no orchestration intents created even with events emitted."""
        set_orchestration_mode_for_testing(False)
        scheduler, store = _make_scheduler()
        # No bootstrap_orchestration — mimic inactive mode

        event = from_cron(
            intent_type="workflow_run",
            goal={"workflow": "open_day"},
            session_name="day_workflow",
            cron_source="open_day",
        )
        scheduler.emit(event)
        scheduler.run()

        # No subscribers, so no intents created
        snapshot = store.snapshot()
        intent_keys = [k for k in snapshot if k.startswith("intent:")]
        self.assertEqual(len(intent_keys), 0)

    def test_existing_execution_correlation_unbroken(self):
        """Full execution result correlation path still works end-to-end."""
        set_orchestration_mode_for_testing(True)
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler)
        coord._plan_registry.register(
            IntentType.LIFECYCLE_FINALIZE, _one_step_generator
        )

        ingress = SchedulerEvent(
            event_type="operator_intent_requested",
            session_name="corr_test",
            source="test",
            payload={
                "intent_type": "lifecycle_finalize",
                "goal": {"session_name": "corr_test"},
                "priority": 100,
            },
        )
        scheduler.emit(ingress)
        scheduler.run()

        goal = {"session_name": "corr_test"}
        intent_id = compute_intent_id(IntentType.LIFECYCLE_FINALIZE, goal)

        snapshot = store.snapshot()
        step_event_ids = [
            k.split(".", 1)[1] for k in snapshot if k.startswith("intent_step_events.")
        ]
        self.assertGreater(len(step_event_ids), 0)
        step_event_id = step_event_ids[0]

        exec_id = "exec_regression_001"
        store.set(
            f"in_flight_executions.{exec_id}",
            {"original_request": {"causal_event_id": step_event_id}},
        )

        exec_result = SchedulerEvent(
            event_type="execution_completed",
            session_name="corr_test",
            source="execution_worker",
            payload={
                "result": {
                    "execution_id": exec_id,
                    "correlation_id": "corr_regression",
                    "causal_event_id": step_event_id,
                    "primitive_name": "test_prim",
                    "status": "succeeded",
                    "outputs": {},
                },
            },
        )
        scheduler.emit(exec_result)
        scheduler.run()

        intent_data = store.get(intent_store_key(intent_id))
        self.assertEqual(intent_data["status"], IntentStatus.COMPLETED.value)


if __name__ == "__main__":
    unittest.main()
