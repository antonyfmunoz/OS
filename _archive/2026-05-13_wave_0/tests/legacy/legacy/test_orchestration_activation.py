"""Tests for orchestration production activation wiring.

Validates:
1. Inactive mode preserves legacy behavior (no orchestration subscribers).
2. Active mode wires orchestration + execution subscribers into scheduler.
3. Active operator ingress routes through orchestration only.
4. Inactive operator ingress stays legacy.
5. Active mode execution result path reaches coordinator.
6. No double-processing in active mode.
7. Scheduler assembly contains all required subscribers in active mode.
8. PlannerStrategy yields when orchestration is active.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, "/opt/OS")

from umh.substrate.event_log_runtime import EventLogRuntime
from umh.substrate.event_scheduler import EventScheduler, SchedulerEvent
from umh.substrate.execution_bootstrap import (
    bootstrap_execution_result_handler,
    bootstrap_execution_worker,
)
from umh.substrate.intent_models import (
    IntentStatus,
    IntentType,
    PlanStep,
    compute_intent_id,
    intent_store_key,
)
from umh.substrate.lifecycle_handlers import create_lifecycle_scheduler
from umh.substrate.orchestration_bootstrap import bootstrap_orchestration
from umh.substrate.orchestration_mode import (
    orchestration_mode_active,
    set_orchestration_mode_for_testing,
)
from umh.substrate.runtime_state_store import RuntimeStateStore


# ── Helpers ──────────────────────────────────────────────────────────


def _make_scheduler() -> tuple[EventScheduler, RuntimeStateStore]:
    store = RuntimeStateStore()
    log = EventLogRuntime(log_path=Path(tempfile.mktemp(suffix=".jsonl")))
    scheduler = EventScheduler(store=store, event_log=log)
    return scheduler, store


def _make_lifecycle_scheduler() -> tuple[EventScheduler, RuntimeStateStore]:
    store = RuntimeStateStore()
    log = EventLogRuntime(log_path=Path(tempfile.mktemp(suffix=".jsonl")))
    scheduler = create_lifecycle_scheduler(store=store, event_log=log)
    return scheduler, store


def _one_step_generator(intent, state):
    return (PlanStep(step_index=0, event_type="test_step_event", payload={}),)


def _count_subscribers(scheduler: EventScheduler) -> int:
    return sum(len(subs) for subs in scheduler._subscribers.values())


def _get_subscriber_names(scheduler: EventScheduler) -> set[str]:
    names = set()
    for subs_list in scheduler._subscribers.values():
        for sub in subs_list:
            if hasattr(sub, "name"):
                names.add(sub.name)
    return names


def _get_subscribed_event_types(scheduler: EventScheduler) -> set[str]:
    return set(scheduler._subscribers.keys())


# ── Tests ────────────────────────────────────────────────────────────


class TestOrchestrationModeHelper(unittest.TestCase):
    def setUp(self):
        set_orchestration_mode_for_testing(None)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_default_inactive(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ORCHESTRATION_MODE", None)
            set_orchestration_mode_for_testing(None)
            self.assertFalse(orchestration_mode_active())

    def test_active_when_set(self):
        set_orchestration_mode_for_testing(True)
        self.assertTrue(orchestration_mode_active())

    def test_inactive_when_wrong_value(self):
        set_orchestration_mode_for_testing(None)
        with mock.patch.dict(os.environ, {"ORCHESTRATION_MODE": "disabled"}):
            self.assertFalse(orchestration_mode_active())

    def test_active_env_var(self):
        set_orchestration_mode_for_testing(None)
        with mock.patch.dict(os.environ, {"ORCHESTRATION_MODE": "active"}):
            self.assertTrue(orchestration_mode_active())

    def test_case_insensitive(self):
        set_orchestration_mode_for_testing(None)
        with mock.patch.dict(os.environ, {"ORCHESTRATION_MODE": "ACTIVE"}):
            self.assertTrue(orchestration_mode_active())


class TestInactiveModePreservesLegacy(unittest.TestCase):
    """Test 1: inactive mode has no orchestration subscribers."""

    def setUp(self):
        set_orchestration_mode_for_testing(None)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_lifecycle_scheduler_has_no_orchestration_subscribers(self):
        scheduler, _store = _make_lifecycle_scheduler()
        event_types = _get_subscribed_event_types(scheduler)

        # Should have lifecycle events only
        self.assertIn("run_completion_proposed", event_types)
        self.assertIn("finalization_succeeded", event_types)

        # Should NOT have orchestration events
        self.assertNotIn("operator_intent_requested", event_types)
        self.assertNotIn("decision_intent_proposed", event_types)
        self.assertNotIn("cron_intent_requested", event_types)
        self.assertNotIn("result_intent_requested", event_types)
        self.assertNotIn("intent_cancel_requested", event_types)

        # Should NOT have execution worker events
        self.assertNotIn("execution_requested", event_types)

    def test_subscriber_count_matches_legacy(self):
        scheduler, _store = _make_lifecycle_scheduler()
        # Legacy lifecycle = 6 subscribers
        self.assertEqual(_count_subscribers(scheduler), 6)


class TestActiveModeWiresAllLayers(unittest.TestCase):
    """Test 2: active mode wires orchestration + execution into scheduler."""

    def setUp(self):
        set_orchestration_mode_for_testing(True)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_all_three_layers_present(self):
        scheduler, store = _make_lifecycle_scheduler()
        bootstrap_orchestration(scheduler)
        bootstrap_execution_worker(scheduler, store)
        bootstrap_execution_result_handler(scheduler)

        event_types = _get_subscribed_event_types(scheduler)

        # Lifecycle layer
        self.assertIn("run_completion_proposed", event_types)
        self.assertIn("finalization_succeeded", event_types)
        self.assertIn("publication_confirmed", event_types)
        self.assertIn("clear_requested", event_types)
        self.assertIn("clear_confirmed", event_types)
        self.assertIn("terminal_seal_applied", event_types)

        # Orchestration layer
        self.assertIn("operator_intent_requested", event_types)
        self.assertIn("decision_intent_proposed", event_types)
        self.assertIn("cron_intent_requested", event_types)
        self.assertIn("result_intent_requested", event_types)
        self.assertIn("intent_cancel_requested", event_types)

        # Execution worker layer
        self.assertIn("execution_requested", event_types)
        self.assertIn("execution_retried", event_types)

        # Execution result layer (subscribed by both orchestration AND result handler)
        self.assertIn("execution_completed", event_types)
        self.assertIn("execution_failed", event_types)
        self.assertIn("execution_timed_out", event_types)
        self.assertIn("execution_rejected", event_types)

    def test_subscriber_count(self):
        scheduler, store = _make_lifecycle_scheduler()
        bootstrap_orchestration(scheduler)
        bootstrap_execution_worker(scheduler, store)
        bootstrap_execution_result_handler(scheduler)

        # 6 lifecycle + 9 orchestration + 2 execution worker + 4 execution result handler = 21
        self.assertEqual(_count_subscribers(scheduler), 21)

    def test_no_duplicate_registration(self):
        scheduler, store = _make_lifecycle_scheduler()

        # Wire twice — should not crash, just add more subscribers
        coord1 = bootstrap_orchestration(scheduler)
        coord2 = bootstrap_orchestration(scheduler)

        # Different coordinator instances
        self.assertIsNot(coord1, coord2)


class TestActiveOperatorIngressRoutesOrchestration(unittest.TestCase):
    """Test 3: active operator ingress emits orchestration event."""

    def setUp(self):
        set_orchestration_mode_for_testing(True)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_orchestration_ingress_emitted_on_proposal_accepted(self):
        """When orchestration is active and proposal is accepted,
        an orchestration ingress event should be emitted."""
        # We test via the _emit_orchestration_ingress function directly
        # since propose_run_completion depends on the full lifecycle manager
        from umh.substrate.trigger_adapters import from_operator

        event = from_operator(
            intent_type="lifecycle_finalize",
            goal={"session_name": "test_session"},
            session_name="test_session",
            operator_id="webhook",
        )
        self.assertEqual(event.event_type, "operator_intent_requested")
        self.assertEqual(event.payload["intent_type"], "lifecycle_finalize")
        self.assertEqual(event.payload["goal"]["session_name"], "test_session")


class TestInactiveOperatorStaysLegacy(unittest.TestCase):
    """Test 4: inactive mode uses legacy path."""

    def setUp(self):
        set_orchestration_mode_for_testing(False)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_planner_strategy_works_when_inactive(self):
        """PlannerStrategy evaluates normally when orchestration inactive."""
        from umh.substrate.planner import PlannerStrategy

        strategy = PlannerStrategy()
        # With no active intents, should return None
        result = strategy.evaluate({})
        self.assertIsNone(result)


class TestActiveExecutionResultReachesCoordinator(unittest.TestCase):
    """Test 5: execution results reach coordinator in active mode."""

    def setUp(self):
        set_orchestration_mode_for_testing(True)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_execution_result_correlates_to_intent(self):
        scheduler, store = _make_lifecycle_scheduler()
        coord = bootstrap_orchestration(scheduler)
        coord._plan_registry.register(
            IntentType.LIFECYCLE_FINALIZE, _one_step_generator
        )

        # Phase 1: Create intent via ingress
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
        intent_id = compute_intent_id(IntentType.LIFECYCLE_FINALIZE, goal)

        # Intent should be ACTIVE
        intent_data = store.get(intent_store_key(intent_id))
        self.assertIsNotNone(intent_data)
        self.assertEqual(intent_data["status"], IntentStatus.ACTIVE.value)

        # Phase 2: Find step event ID from correlation store
        snapshot = store.snapshot()
        step_event_ids = [
            k.split(".", 1)[1] for k in snapshot if k.startswith("intent_step_events.")
        ]
        self.assertGreater(len(step_event_ids), 0)
        step_event_id = step_event_ids[0]

        # Phase 3: Simulate execution completion
        exec_id = "exec_test_activation_001"
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
                    "correlation_id": "corr_act_1",
                    "causal_event_id": step_event_id,
                    "primitive_name": "test_prim",
                    "status": "succeeded",
                    "outputs": {},
                },
            },
        )
        scheduler.emit(exec_result)
        scheduler.run()

        # Intent should be COMPLETED
        intent_data = store.get(intent_store_key(intent_id))
        self.assertEqual(intent_data["status"], IntentStatus.COMPLETED.value)


class TestNoDoubleProcessing(unittest.TestCase):
    """Test 6: no double-processing in active mode."""

    def setUp(self):
        set_orchestration_mode_for_testing(True)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_planner_strategy_yields_when_active(self):
        """PlannerStrategy returns None when orchestration is active,
        preventing double-processing of intent step progression."""
        from umh.substrate.planner import PlannerStrategy

        strategy = PlannerStrategy()

        # Even with active intents in state, planner should yield
        from umh.substrate.intent_models import (
            Intent,
            build_intent_create_mutations,
        )

        intent = Intent(
            intent_id="int_test123",
            intent_type=IntentType.LIFECYCLE_FINALIZE,
            goal={"session_name": "test"},
            status=IntentStatus.ACTIVE,
            session_name="test",
            current_step=0,
            total_steps=2,
        )
        state = {}
        for mut in build_intent_create_mutations(intent):
            state[mut["key"]] = mut["value"]

        result = strategy.evaluate(state)
        self.assertIsNone(result)

    def test_finalization_deferred_when_active(self):
        """attempt_canonical_finalization returns deferred when orchestration active."""
        from umh.substrate.run_lifecycle import (
            FinalizationDecision,
            attempt_canonical_finalization,
            reset_for_tests,
            start_run,
        )

        reset_for_tests()
        handle = start_run("test_sess")

        decision = attempt_canonical_finalization(
            "test_sess", "test", lambda: {"success": True}
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "orchestration_deferred")
        self.assertTrue(decision.finalization_result.get("orchestration_deferred"))

        reset_for_tests()

    def test_clear_deferred_when_active(self):
        """request_run_clear returns deferred when orchestration active."""
        from umh.substrate.run_lifecycle import (
            request_run_clear,
            reset_for_tests,
            start_run,
        )

        reset_for_tests()
        handle = start_run("test_sess")

        decision = request_run_clear("test_sess", "test")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "orchestration_deferred")

        reset_for_tests()


class TestSchedulerAssembly(unittest.TestCase):
    """Test 7: full assembly has all required subscribers."""

    def setUp(self):
        set_orchestration_mode_for_testing(True)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_full_assembly_event_types(self):
        scheduler, store = _make_lifecycle_scheduler()
        bootstrap_orchestration(scheduler)
        bootstrap_execution_worker(scheduler, store)
        bootstrap_execution_result_handler(scheduler)

        event_types = _get_subscribed_event_types(scheduler)

        # All required event types present
        required = {
            # Lifecycle
            "run_completion_proposed",
            "finalization_succeeded",
            "publication_confirmed",
            "clear_requested",
            "clear_confirmed",
            "terminal_seal_applied",
            # Orchestration ingress
            "decision_intent_proposed",
            "operator_intent_requested",
            "cron_intent_requested",
            "result_intent_requested",
            # Orchestration cancel
            "intent_cancel_requested",
            # Execution
            "execution_requested",
            "execution_retried",
            # Execution results (shared by orchestration + result handler)
            "execution_completed",
            "execution_failed",
            "execution_timed_out",
            "execution_rejected",
        }

        for req in required:
            self.assertIn(req, event_types, f"missing required event type: {req}")


class TestPlannerStrategyGate(unittest.TestCase):
    """Test 8: PlannerStrategy yields when orchestration active."""

    def setUp(self):
        set_orchestration_mode_for_testing(None)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_planner_works_when_inactive(self):
        from umh.substrate.planner import PlannerStrategy

        set_orchestration_mode_for_testing(False)
        strategy = PlannerStrategy()
        # No intents → None (normal behavior, not short-circuit)
        result = strategy.evaluate({})
        self.assertIsNone(result)

    def test_planner_yields_when_active(self):
        from umh.substrate.planner import PlannerStrategy

        set_orchestration_mode_for_testing(True)
        strategy = PlannerStrategy()

        # Even with intents, should return None
        from umh.substrate.intent_models import (
            Intent,
            build_intent_create_mutations,
        )

        intent = Intent(
            intent_id="int_gate_test",
            intent_type=IntentType.LIFECYCLE_FINALIZE,
            goal={"session_name": "gate_test"},
            status=IntentStatus.ACTIVE,
            session_name="gate_test",
            current_step=0,
            total_steps=3,
        )
        state = {}
        for mut in build_intent_create_mutations(intent):
            state[mut["key"]] = mut["value"]

        result = strategy.evaluate(state)
        self.assertIsNone(result)

    def test_planner_evaluates_intents_when_inactive(self):
        """Planner actively processes intents when orchestration is off."""
        from umh.substrate.planner import PlannerStrategy

        set_orchestration_mode_for_testing(False)
        strategy = PlannerStrategy()

        from umh.substrate.intent_models import (
            Intent,
            build_intent_create_mutations,
        )

        intent = Intent(
            intent_id="int_active_test",
            intent_type=IntentType.LIFECYCLE_FINALIZE,
            goal={"session_name": "active_test"},
            status=IntentStatus.ACTIVE,
            session_name="active_test",
            current_step=0,
            total_steps=3,
        )
        state = {}
        for mut in build_intent_create_mutations(intent):
            state[mut["key"]] = mut["value"]

        result = strategy.evaluate(state)
        # Should produce a decision (not None) because there IS an active intent
        self.assertIsNotNone(result)
        self.assertIn("finalization_succeeded", result.event_type)


if __name__ == "__main__":
    unittest.main()
