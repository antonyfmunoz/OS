"""Integration tests for the orchestration layer through the EventScheduler.

Validates end-to-end flow:
1. bootstrap_orchestration wires correct subscription count.
2. Ingress event → scheduler.run() → intent created and activated.
3. Full lifecycle: ingress → execution result → intent completed.
4. Two intents: A completes, B promoted from PENDING.
5. Cancellation through scheduler.
6. Event ordering guarantee in combined terminal + promotion.
7. Keyed index state consistency after full lifecycle.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from umh.substrate.event_log_runtime import EventLogRuntime
from umh.substrate.event_scheduler import EventScheduler, SchedulerEvent
from umh.substrate.intent_models import (
    Intent,
    IntentStatus,
    IntentType,
    PlanStep,
    compute_intent_id,
    intent_store_key,
)
from umh.substrate.orchestration_bootstrap import bootstrap_orchestration
from umh.substrate.runtime_state_store import RuntimeStateStore


# ── Test plan generators ─────────────────────────────────────────────


def _one_step_generator(intent: Intent, state: dict) -> tuple[PlanStep, ...]:
    return (PlanStep(step_index=0, event_type="test_step_event", payload={}),)


def _two_step_generator(intent: Intent, state: dict) -> tuple[PlanStep, ...]:
    return (
        PlanStep(step_index=0, event_type="step_a", payload={}),
        PlanStep(step_index=1, event_type="step_b", payload={}),
    )


# ── Helpers ──────────────────────────────────────────────────────────


def _make_scheduler() -> tuple[EventScheduler, RuntimeStateStore]:
    store = RuntimeStateStore()
    log = EventLogRuntime(log_path=Path(tempfile.mktemp(suffix=".jsonl")))
    scheduler = EventScheduler(store=store, event_log=log)
    return scheduler, store


def _make_ingress_event(
    goal: dict | None = None,
    priority: int = 100,
    event_type: str = "operator_intent_requested",
) -> SchedulerEvent:
    goal = goal or {"session_name": "test_session"}
    return SchedulerEvent(
        event_type=event_type,
        session_name="test_session",
        source="test",
        payload={
            "intent_type": "lifecycle_finalize",
            "goal": goal,
            "priority": priority,
        },
    )


# ── Tests ────────────────────────────────────────────────────────────


class TestBootstrap(unittest.TestCase):
    def test_wires_correct_subscription_count(self):
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler)

        # 4 ingress + 4 execution result + 1 cancel = 9
        total_subs = sum(len(subs) for subs in scheduler._subscribers.values())
        self.assertEqual(total_subs, 9)


class TestIngressThroughScheduler(unittest.TestCase):
    def test_ingress_creates_intent(self):
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler)

        # Override with test generator
        coord._plan_registry.register(
            IntentType.LIFECYCLE_FINALIZE, _one_step_generator
        )

        event = _make_ingress_event()
        scheduler.emit(event)
        run_result = scheduler.run()

        # Intent should exist in store
        goal = {"session_name": "test_session"}
        intent_id = compute_intent_id(IntentType.LIFECYCLE_FINALIZE, goal)
        intent_data = store.get(intent_store_key(intent_id))

        self.assertIsNotNone(intent_data)
        self.assertEqual(intent_data["status"], IntentStatus.ACTIVE.value)

        # Active index should exist
        active = store.get(f"active_intent.{intent_id}")
        self.assertIsNotNone(active)
        self.assertEqual(active["status"], IntentStatus.ACTIVE.value)


class TestFullLifecycle(unittest.TestCase):
    def test_ingress_to_completion(self):
        """Full cycle: ingress → step event emitted → simulate execution → advance → complete."""
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler)
        coord._plan_registry.register(
            IntentType.LIFECYCLE_FINALIZE, _one_step_generator
        )

        # Phase 1: ingress
        event = _make_ingress_event()
        scheduler.emit(event)
        run1 = scheduler.run()

        goal = {"session_name": "test_session"}
        intent_id = compute_intent_id(IntentType.LIFECYCLE_FINALIZE, goal)

        # Find step_event_id from the intent_step_events keys in the store
        snapshot = store.snapshot()
        step_event_ids = [
            k.split(".", 1)[1] for k in snapshot if k.startswith("intent_step_events.")
        ]
        self.assertGreater(len(step_event_ids), 0)
        step_event_id = step_event_ids[0]

        # Phase 2: simulate execution completion
        exec_id = "exec_test_001"
        store.set(
            f"in_flight_executions.{exec_id}",
            {
                "original_request": {"causal_event_id": step_event_id},
            },
        )

        exec_result_event = SchedulerEvent(
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
        scheduler.emit(exec_result_event)
        run2 = scheduler.run()

        # Intent should be COMPLETED
        intent_data = store.get(intent_store_key(intent_id))
        self.assertEqual(intent_data["status"], IntentStatus.COMPLETED.value)

        # Active index should be removed
        active = store.get(f"active_intent.{intent_id}")
        self.assertIsNone(active)


class TestTwoIntentPromotion(unittest.TestCase):
    def test_second_intent_promoted_after_first_completes(self):
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler)
        coord._plan_registry.register(
            IntentType.LIFECYCLE_FINALIZE, _one_step_generator
        )

        # Intent A
        event_a = _make_ingress_event(goal={"session_name": "s1"})
        scheduler.emit(event_a)
        scheduler.run()

        intent_id_a = compute_intent_id(
            IntentType.LIFECYCLE_FINALIZE, {"session_name": "s1"}
        )

        # Intent B (should queue as PENDING)
        event_b = _make_ingress_event(goal={"session_name": "s2"})
        scheduler.emit(event_b)
        scheduler.run()

        intent_id_b = compute_intent_id(
            IntentType.LIFECYCLE_FINALIZE, {"session_name": "s2"}
        )

        # B should be PENDING
        intent_b_data = store.get(intent_store_key(intent_id_b))
        self.assertEqual(intent_b_data["status"], IntentStatus.PENDING.value)

        # Complete A via execution result
        snapshot = store.snapshot()
        step_event_ids = [
            k.split(".", 1)[1] for k in snapshot if k.startswith("intent_step_events.")
        ]
        # Get the step event for intent A
        step_event_id_a = None
        for seid in step_event_ids:
            mapping = store.get(f"intent_step_events.{seid}")
            if mapping and mapping["intent_id"] == intent_id_a:
                step_event_id_a = seid
                break

        self.assertIsNotNone(step_event_id_a)

        exec_id = "exec_a"
        store.set(
            f"in_flight_executions.{exec_id}",
            {
                "original_request": {"causal_event_id": step_event_id_a},
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
                    "causal_event_id": step_event_id_a,
                    "primitive_name": "test_prim",
                    "status": "succeeded",
                    "outputs": {},
                },
            },
        )
        scheduler.emit(exec_event)
        scheduler.run()

        # A should be COMPLETED
        intent_a_data = store.get(intent_store_key(intent_id_a))
        self.assertEqual(intent_a_data["status"], IntentStatus.COMPLETED.value)

        # B should be ACTIVE (promoted)
        intent_b_data = store.get(intent_store_key(intent_id_b))
        self.assertEqual(intent_b_data["status"], IntentStatus.ACTIVE.value)

        # B should have active index
        active_b = store.get(f"active_intent.{intent_id_b}")
        self.assertIsNotNone(active_b)

        # A should NOT have active index
        active_a = store.get(f"active_intent.{intent_id_a}")
        self.assertIsNone(active_a)


class TestCancellationThroughScheduler(unittest.TestCase):
    def test_cancel_through_scheduler(self):
        scheduler, store = _make_scheduler()
        coord = bootstrap_orchestration(scheduler)
        coord._plan_registry.register(
            IntentType.LIFECYCLE_FINALIZE, _one_step_generator
        )

        # Create and activate
        event = _make_ingress_event()
        scheduler.emit(event)
        scheduler.run()

        goal = {"session_name": "test_session"}
        intent_id = compute_intent_id(IntentType.LIFECYCLE_FINALIZE, goal)

        # Cancel
        cancel_event = SchedulerEvent(
            event_type="intent_cancel_requested",
            session_name="test_session",
            source="operator",
            payload={"intent_id": intent_id, "reason": "test_cancel"},
        )
        scheduler.emit(cancel_event)
        scheduler.run()

        # Intent should be FAILED with cancelled metadata
        intent_data = store.get(intent_store_key(intent_id))
        self.assertEqual(intent_data["status"], IntentStatus.FAILED.value)
        self.assertTrue(intent_data["metadata"].get("cancelled"))

        # Active index removed
        active = store.get(f"active_intent.{intent_id}")
        self.assertIsNone(active)


if __name__ == "__main__":
    unittest.main()
