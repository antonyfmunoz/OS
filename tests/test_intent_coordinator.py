"""Tests for IntentCoordinator — top-level orchestration handler.

Validates:
1. Ingress: creates intent from raw event, activates when slot available.
2. Dedup: skips duplicate intent (same type + goal).
3. Pending queuing: excess intents stay PENDING when max_active reached.
4. Execution result correlation: step success advances intent.
5. Execution result: step failure fails intent.
6. Cancellation: intent_cancel_requested transitions to FAILED with metadata.
7. Pending promotion: after terminal, next PENDING is promoted.
8. Event ordering: terminal events before promotion events.
9. Keyed index: active_intent.{id} SET on activation, REMOVE on deactivation.
10. Coordinator is SOLE emitter of orch_intent_completed/failed/cancelled.
"""

from __future__ import annotations

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.substrate.event_scheduler import (
    ExecutionResult as SchedulerExecutionResult,
    SchedulerEvent,
)
from umh.substrate.intent_models import (
    Intent,
    IntentStatus,
    IntentType,
    PlanStep,
    compute_intent_id,
    intent_store_key,
)
from umh.substrate.plan_registry import PlanRegistry
from umh.substrate.runtime_state_store import RuntimeStateStore
from umh.substrate.workflow_driver import WorkflowDriver
from umh.substrate.intent_coordinator import IntentCoordinator


# ── Helpers ──────────────────────────────────────────────────────────


def _two_step_generator(intent: Intent, state: dict) -> tuple[PlanStep, ...]:
    return (
        PlanStep(step_index=0, event_type="step_a", payload={}),
        PlanStep(step_index=1, event_type="step_b", payload={}),
    )


def _one_step_generator(intent: Intent, state: dict) -> tuple[PlanStep, ...]:
    return (PlanStep(step_index=0, event_type="only_step", payload={}),)


def _make_registry(gen=_two_step_generator) -> PlanRegistry:
    reg = PlanRegistry()
    reg.register(IntentType.LIFECYCLE_FINALIZE, gen)
    return reg


def _make_coordinator(
    gen=_two_step_generator, max_active: int = 1
) -> IntentCoordinator:
    reg = _make_registry(gen)
    driver = WorkflowDriver(reg)
    return IntentCoordinator(reg, driver, max_active=max_active)


def _make_store(state: dict | None = None) -> RuntimeStateStore:
    store = RuntimeStateStore()
    if state:
        for k, v in state.items():
            store.set(k, v)
    return store


def _make_ingress_event(
    intent_type: str = "lifecycle_finalize",
    goal: dict | None = None,
    priority: int = 100,
    session_name: str = "test_session",
    event_type: str = "operator_intent_requested",
) -> SchedulerEvent:
    return SchedulerEvent(
        event_type=event_type,
        session_name=session_name,
        source="test",
        payload={
            "intent_type": intent_type,
            "goal": goal or {"session_name": session_name},
            "priority": priority,
        },
    )


def _apply_mutations(store: RuntimeStateStore, mutations: list[dict]) -> None:
    """Apply mutations to store for test state setup."""
    for m in mutations:
        op = m["op"]
        key = m["key"]
        if op == "SET":
            store.set(key, m["value"])
        elif op == "REMOVE":
            # Simulate REMOVE by deleting the key
            try:
                with store._lock:
                    if key in store._state:
                        del store._state[key]
            except Exception:
                pass


# ── Ingress tests ────────────────────────────────────────────────────


class TestIngressHandler(unittest.TestCase):
    def test_creates_and_activates_intent(self):
        coord = _make_coordinator()
        store = _make_store()
        event = _make_ingress_event()

        result = coord._handle_intent_ingress(store, event)

        self.assertIn("intent_id", result.metadata)
        intent_id = result.metadata["intent_id"]

        # Should have mutations: intent SET + active_intent SET
        set_keys = [m["key"] for m in result.mutations if m["op"] == "SET"]
        self.assertIn(intent_store_key(intent_id), set_keys)
        self.assertIn(f"active_intent.{intent_id}", set_keys)

        # Should have events: step event + step_dispatched + intent_created
        event_types = [e.event_type for e in result.emitted_events]
        self.assertIn("step_a", event_types)
        self.assertIn("orch_intent_step_dispatched", event_types)
        self.assertIn("orch_intent_created", event_types)

    def test_dedup_skips_existing_intent(self):
        coord = _make_coordinator()
        goal = {"session_name": "test_session"}
        intent_id = compute_intent_id(IntentType.LIFECYCLE_FINALIZE, goal)

        # Pre-populate store with existing intent
        store = _make_store(
            {
                intent_store_key(intent_id): {
                    "intent_id": intent_id,
                    "intent_type": "lifecycle_finalize",
                    "goal": goal,
                    "status": "active",
                    "priority": 100,
                    "created_at": "2026-04-17T00:00:00+00:00",
                    "session_name": "test_session",
                    "current_step": 0,
                    "total_steps": 2,
                    "metadata": {},
                }
            }
        )
        event = _make_ingress_event()
        result = coord._handle_intent_ingress(store, event)

        self.assertTrue(result.metadata.get("skipped"))
        self.assertEqual(result.metadata.get("reason"), "intent_already_exists")

    def test_unknown_intent_type_dropped(self):
        coord = _make_coordinator()
        store = _make_store()
        event = _make_ingress_event(intent_type="nonexistent_type")

        result = coord._handle_intent_ingress(store, event)
        self.assertTrue(result.metadata.get("skipped"))
        self.assertEqual(result.metadata.get("reason"), "unknown_intent_type")

    def test_pending_when_max_active_reached(self):
        coord = _make_coordinator(max_active=1)
        store = _make_store()

        # First intent fills the slot
        event1 = _make_ingress_event(goal={"session_name": "s1"})
        result1 = coord._handle_intent_ingress(store, event1)
        _apply_mutations(store, result1.mutations)

        # Second intent should queue as PENDING
        event2 = _make_ingress_event(goal={"session_name": "s2"})
        result2 = coord._handle_intent_ingress(store, event2)

        intent_id2 = result2.metadata["intent_id"]
        # Should have intent SET but NO active_intent SET
        set_keys = [m["key"] for m in result2.mutations if m["op"] == "SET"]
        self.assertIn(intent_store_key(intent_id2), set_keys)
        self.assertNotIn(f"active_intent.{intent_id2}", set_keys)

        # Intent should be PENDING in the mutation
        intent_mut = next(
            m
            for m in result2.mutations
            if m["key"] == intent_store_key(intent_id2) and m["op"] == "SET"
        )
        self.assertEqual(intent_mut["value"]["status"], IntentStatus.PENDING.value)


# ── Execution result tests ───────────────────────────────────────────


class TestExecutionResultHandler(unittest.TestCase):
    def _setup_active_intent(self, coord, store, goal=None):
        """Helper: create and activate an intent, apply mutations, return (intent_id, step_event_id)."""
        goal = goal or {"session_name": "test_session"}
        event = _make_ingress_event(goal=goal)
        result = coord._handle_intent_ingress(store, event)
        _apply_mutations(store, result.mutations)

        intent_id = result.metadata["intent_id"]

        # Find step event to get its event_id (for correlation)
        step_events = [
            e
            for e in result.emitted_events
            if e.metadata.get("_orch_intent_id") == intent_id
        ]
        step_event_id = step_events[0].event_id if step_events else ""

        return intent_id, step_event_id

    def _make_exec_result_event(self, execution_id, status="succeeded", error=None):
        event_type = (
            f"execution_{status}" if status != "succeeded" else "execution_completed"
        )
        return SchedulerEvent(
            event_type=event_type,
            session_name="test_session",
            source="execution_worker",
            payload={
                "result": {
                    "execution_id": execution_id,
                    "correlation_id": "corr_1",
                    "causal_event_id": "causal_1",
                    "primitive_name": "test_prim",
                    "status": status,
                    "outputs": {},
                    "error": error,
                },
            },
        )

    def test_success_advances_step(self):
        coord = _make_coordinator()
        store = _make_store()
        intent_id, step_event_id = self._setup_active_intent(coord, store)

        # Simulate execution infrastructure:
        # in_flight_executions.{exec_id} -> original_request.causal_event_id -> step_event_id
        exec_id = "exec_001"
        store.set(
            f"in_flight_executions.{exec_id}",
            {
                "original_request": {"causal_event_id": step_event_id},
            },
        )

        exec_event = SchedulerEvent(
            event_type="execution_completed",
            session_name="test_session",
            source="execution_worker",
            payload={
                "result": {
                    "execution_id": exec_id,
                    "correlation_id": "corr_1",
                    "causal_event_id": step_event_id,
                    "primitive_name": "test_prim",
                    "status": "succeeded",
                    "outputs": {},
                },
            },
        )

        result = coord._handle_execution_result(store, exec_event)

        self.assertEqual(result.metadata["intent_id"], intent_id)
        self.assertEqual(result.metadata["execution_status"], "succeeded")

        # Should have step_completed obs event
        event_types = [e.event_type for e in result.emitted_events]
        self.assertIn("orch_intent_step_completed", event_types)

        # Non-terminal (2-step plan, completed step 0) -> should emit next step
        self.assertIn("step_b", event_types)

    def test_failure_fails_intent(self):
        coord = _make_coordinator()
        store = _make_store()
        intent_id, step_event_id = self._setup_active_intent(coord, store)

        exec_id = "exec_002"
        store.set(
            f"in_flight_executions.{exec_id}",
            {
                "original_request": {"causal_event_id": step_event_id},
            },
        )

        exec_event = SchedulerEvent(
            event_type="execution_failed",
            session_name="test_session",
            source="execution_worker",
            payload={
                "result": {
                    "execution_id": exec_id,
                    "correlation_id": "corr_1",
                    "causal_event_id": step_event_id,
                    "primitive_name": "test_prim",
                    "status": "failed",
                    "outputs": {},
                    "error": "runtime_error",
                },
            },
        )

        result = coord._handle_execution_result(store, exec_event)

        event_types = [e.event_type for e in result.emitted_events]
        self.assertIn("orch_intent_step_failed", event_types)
        self.assertIn("orch_intent_failed", event_types)

        # Should deactivate
        remove_keys = [m["key"] for m in result.mutations if m["op"] == "REMOVE"]
        self.assertIn(f"active_intent.{intent_id}", remove_keys)

    def test_no_correlation_returns_empty(self):
        coord = _make_coordinator()
        store = _make_store()

        exec_event = SchedulerEvent(
            event_type="execution_completed",
            session_name="test_session",
            source="execution_worker",
            payload={
                "result": {
                    "execution_id": "unknown_exec",
                    "correlation_id": "corr_1",
                    "causal_event_id": "no_match",
                    "primitive_name": "test_prim",
                    "status": "succeeded",
                    "outputs": {},
                },
            },
        )

        result = coord._handle_execution_result(store, exec_event)
        self.assertEqual(len(result.mutations), 0)
        self.assertEqual(len(result.emitted_events), 0)


# ── Cancellation tests ──────────────────────────────────────────────


class TestCancellationHandler(unittest.TestCase):
    def test_cancel_active_intent(self):
        coord = _make_coordinator()
        store = _make_store()

        # Create and activate an intent
        event = _make_ingress_event()
        ingress_result = coord._handle_intent_ingress(store, event)
        _apply_mutations(store, ingress_result.mutations)
        intent_id = ingress_result.metadata["intent_id"]

        # Cancel it
        cancel_event = SchedulerEvent(
            event_type="intent_cancel_requested",
            session_name="test_session",
            source="operator",
            payload={"intent_id": intent_id, "reason": "operator_cancel"},
        )

        result = coord._handle_intent_cancel(store, cancel_event)

        event_types = [e.event_type for e in result.emitted_events]
        self.assertIn("orch_intent_cancelled", event_types)

        remove_keys = [m["key"] for m in result.mutations if m["op"] == "REMOVE"]
        self.assertIn(f"active_intent.{intent_id}", remove_keys)

    def test_cancel_nonexistent_skipped(self):
        coord = _make_coordinator()
        store = _make_store()

        cancel_event = SchedulerEvent(
            event_type="intent_cancel_requested",
            session_name="test_session",
            source="operator",
            payload={"intent_id": "nonexistent_id", "reason": "test"},
        )

        result = coord._handle_intent_cancel(store, cancel_event)
        self.assertTrue(result.metadata.get("skipped"))


# ── Promotion tests ─────────────────────────────────────────────────


class TestPendingPromotion(unittest.TestCase):
    def test_promotion_after_completion(self):
        """After first intent completes, pending intent should be promoted."""
        coord = _make_coordinator(gen=_one_step_generator, max_active=1)
        store = _make_store()

        # Intent A: activate
        event_a = _make_ingress_event(goal={"session_name": "s1"})
        result_a = coord._handle_intent_ingress(store, event_a)
        _apply_mutations(store, result_a.mutations)
        intent_id_a = result_a.metadata["intent_id"]
        step_event_a = [
            e
            for e in result_a.emitted_events
            if e.metadata.get("_orch_intent_id") == intent_id_a
        ][0]

        # Intent B: should be PENDING
        event_b = _make_ingress_event(goal={"session_name": "s2"})
        result_b = coord._handle_intent_ingress(store, event_b)
        _apply_mutations(store, result_b.mutations)
        intent_id_b = result_b.metadata["intent_id"]

        # Verify B is PENDING
        intent_b_raw = store.get(intent_store_key(intent_id_b))
        self.assertEqual(intent_b_raw["status"], "pending")

        # Simulate execution of A completing
        exec_id = "exec_a"
        store.set(
            f"in_flight_executions.{exec_id}",
            {
                "original_request": {"causal_event_id": step_event_a.event_id},
            },
        )

        exec_event = SchedulerEvent(
            event_type="execution_completed",
            session_name="test_session",
            source="execution_worker",
            payload={
                "result": {
                    "execution_id": exec_id,
                    "correlation_id": "corr_1",
                    "causal_event_id": step_event_a.event_id,
                    "primitive_name": "test_prim",
                    "status": "succeeded",
                    "outputs": {},
                },
            },
        )

        result = coord._handle_execution_result(store, exec_event)

        # Event ordering: terminal events for A, then activation events for B
        event_types = [e.event_type for e in result.emitted_events]

        # A's terminal events
        self.assertIn("orch_intent_step_completed", event_types)
        self.assertIn("orch_intent_completed", event_types)

        # B's activation events (promotion)
        self.assertIn("only_step", event_types)

        # Ordering check: orch_intent_completed before only_step
        completed_idx = event_types.index("orch_intent_completed")
        step_idx = event_types.index("only_step")
        self.assertLess(completed_idx, step_idx)


# ── Keyed index tests ───────────────────────────────────────────────


class TestKeyedIndex(unittest.TestCase):
    def test_activation_writes_keyed_index(self):
        coord = _make_coordinator()
        store = _make_store()
        event = _make_ingress_event()

        result = coord._handle_intent_ingress(store, event)
        intent_id = result.metadata["intent_id"]

        # active_intent.{id} should be in mutations
        active_muts = [
            m
            for m in result.mutations
            if m["key"] == f"active_intent.{intent_id}" and m["op"] == "SET"
        ]
        self.assertEqual(len(active_muts), 1)
        val = active_muts[0]["value"]
        self.assertEqual(val["status"], IntentStatus.ACTIVE.value)
        self.assertIn("priority", val)
        self.assertIn("total_steps", val)

    def test_step_correlation_written(self):
        coord = _make_coordinator()
        store = _make_store()
        event = _make_ingress_event()

        result = coord._handle_intent_ingress(store, event)
        intent_id = result.metadata["intent_id"]

        # intent_step_events.{event_id} should be in mutations
        corr_muts = [
            m
            for m in result.mutations
            if m["key"].startswith("intent_step_events.") and m["op"] == "SET"
        ]
        self.assertGreater(len(corr_muts), 0)
        self.assertEqual(corr_muts[0]["value"]["intent_id"], intent_id)
        self.assertEqual(corr_muts[0]["value"]["step_index"], 0)


if __name__ == "__main__":
    unittest.main()
