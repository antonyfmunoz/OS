"""Tests for decision engine → orchestration ingress unification.

Validates that when ORCHESTRATION_MODE=active, DecisionEngine output is
translated from raw lifecycle events into decision_intent_proposed events,
routing through orchestration instead of directly triggering lifecycle
handlers.

Test categories:
1. Translation: lifecycle event types → decision_intent_proposed
2. Passthrough: non-lifecycle event types pass through unchanged
3. Full flow: decision → intent → orchestration → execution → completion
4. No double-processing: lifecycle handlers don't independently chain
5. Correlation chain: decision provenance preserved end-to-end
6. Inactive mode: legacy path unchanged
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, "/opt/OS")

from umh.substrate.decision_engine import (
    DecisionEngine,
    DecisionOutput,
    Rule,
    RuleBasedStrategy,
    _LIFECYCLE_EVENT_TO_INTENT,
    evaluate_and_emit,
)
from umh.substrate.event_log_runtime import EventLogRuntime
from umh.substrate.event_scheduler import EventScheduler, SchedulerEvent
from umh.substrate.execution_bootstrap import (
    bootstrap_execution_result_handler,
    bootstrap_execution_worker,
)
from umh.substrate.intent_models import (
    IntentStatus,
    IntentType,
    compute_intent_id,
    intent_store_key,
)
from umh.substrate.lifecycle_handlers import create_lifecycle_scheduler
from umh.substrate.orchestration_bootstrap import bootstrap_orchestration
from umh.substrate.orchestration_mode import set_orchestration_mode_for_testing
from umh.substrate.runtime_state_store import RuntimeStateStore


# ── Helpers ──────────────────────────────────────────────────────────

# Status → canonical event type (matches execution fabric vocabulary)
_STATUS_TO_EVENT_TYPE = {
    "succeeded": "execution_completed",
    "failed": "execution_failed",
    "timed_out": "execution_timed_out",
    "rejected": "execution_rejected",
}


def _make_finalization_rule(session: str = "test_session") -> Rule:
    """Rule that fires finalization_succeeded when state has session_name."""
    return Rule(
        rule_id="test_finalize",
        description="test finalization rule",
        condition=lambda s: s.get("session_name") == session,
        event_type="finalization_succeeded",
        build_payload=lambda s: {"session_name": s["session_name"]},
        priority=10,
    )


def _make_publication_rule(session: str = "test_session") -> Rule:
    """Rule that fires publication_confirmed."""
    return Rule(
        rule_id="test_publish",
        description="test publication rule",
        condition=lambda s: s.get("needs_publication") is True,
        event_type="publication_confirmed",
        build_payload=lambda s: {"session_name": s.get("session_name", "")},
        priority=10,
    )


def _make_clear_rule(session: str = "test_session") -> Rule:
    """Rule that fires clear_requested."""
    return Rule(
        rule_id="test_clear",
        description="test clear rule",
        condition=lambda s: s.get("needs_clear") is True,
        event_type="clear_requested",
        build_payload=lambda s: {"session_name": s.get("session_name", "")},
        priority=10,
    )


def _make_custom_rule() -> Rule:
    """Rule that fires a non-lifecycle event (should pass through unchanged)."""
    return Rule(
        rule_id="test_custom",
        description="test custom event rule",
        condition=lambda s: s.get("custom_trigger") is True,
        event_type="custom_action_fired",
        build_payload=lambda s: {"data": "test"},
        priority=10,
    )


def _build_engine(rules: list[Rule]) -> DecisionEngine:
    """Build a DecisionEngine with given rules."""
    strategy = RuleBasedStrategy(rules)
    return DecisionEngine(strategy=strategy)


def _build_fully_wired_scheduler() -> (
    tuple[EventScheduler, RuntimeStateStore, object]
):
    """Build scheduler with all 3 layers (lifecycle + orchestration + execution)."""
    store = RuntimeStateStore()
    log = EventLogRuntime(log_path=Path(tempfile.mktemp(suffix=".jsonl")))
    scheduler = create_lifecycle_scheduler(store=store, event_log=log)
    coordinator = bootstrap_orchestration(scheduler)
    bootstrap_execution_worker(scheduler, store)
    bootstrap_execution_result_handler(scheduler)
    return scheduler, store, coordinator


def _simulate_execution_result(
    store: RuntimeStateStore,
    scheduler: EventScheduler,
    step_event_id: str,
    exec_id: str,
    status: str = "succeeded",
) -> None:
    """Simulate execution worker completing a step."""
    store.set(
        f"in_flight_executions.{exec_id}",
        {
            "original_request": {
                "causal_event_id": step_event_id,
                "execution_id": exec_id,
            },
        },
    )
    event_type = _STATUS_TO_EVENT_TYPE.get(status, f"execution_{status}")
    result_event = SchedulerEvent(
        event_type=event_type,
        session_name="test_session",
        source="execution_worker",
        payload={
            "result": {
                "execution_id": exec_id,
                "correlation_id": f"corr_{exec_id}",
                "causal_event_id": step_event_id,
                "primitive_name": "test_primitive",
                "status": status,
                "outputs": {},
            },
        },
    )
    scheduler.emit(result_event)


def _get_step_event_id_for_intent(
    store: RuntimeStateStore, intent_id: str, step_index: int
) -> str | None:
    """Find the step event_id for a given intent and step index."""
    snapshot = store.snapshot()
    for key, value in snapshot.items():
        if key.startswith("intent_step_events."):
            if (
                value.get("intent_id") == intent_id
                and value.get("step_index") == step_index
            ):
                return key.split(".", 1)[1]
    return None


# ── Tests ────────────────────────────────────────────────────────────


class TestTranslationMapping(unittest.TestCase):
    """Verify the lifecycle event → intent type mapping is complete."""

    def test_mapping_covers_all_lifecycle_entry_events(self):
        """Every lifecycle entry event type maps to an intent type."""
        expected = {
            "finalization_succeeded": "lifecycle_finalize",
            "publication_confirmed": "lifecycle_publish",
            "clear_requested": "lifecycle_clear",
            "clear_confirmed": "lifecycle_clear",
            "run_completion_proposed": "lifecycle_finalize",
        }
        self.assertEqual(_LIFECYCLE_EVENT_TO_INTENT, expected)

    def test_all_mapped_intent_types_are_valid(self):
        """Every intent type in the mapping is a valid IntentType enum value."""
        valid_types = {t.value for t in IntentType}
        for intent_type in _LIFECYCLE_EVENT_TO_INTENT.values():
            self.assertIn(
                intent_type, valid_types, f"{intent_type} is not a valid IntentType"
            )


class TestActiveTranslation(unittest.TestCase):
    """When active, evaluate_and_emit translates lifecycle events."""

    def setUp(self):
        set_orchestration_mode_for_testing(True)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_finalization_becomes_decision_intent_proposed(self):
        """finalization_succeeded → decision_intent_proposed."""
        engine = _build_engine([_make_finalization_rule()])
        store = RuntimeStateStore()
        store.set("session_name", "test_session")
        scheduler = EventScheduler(store=store)

        output = evaluate_and_emit(engine, store, scheduler)

        self.assertIsNotNone(output)
        self.assertEqual(output.event_type, "finalization_succeeded")

        # Check what's in the scheduler queue
        events = list(scheduler._queue)
        event_types = [e.event_type for e in events]

        # Should have: decision_made (observability) + decision_intent_proposed
        self.assertIn("decision_made", event_types)
        self.assertIn("decision_intent_proposed", event_types)
        # Should NOT have the raw lifecycle event
        self.assertNotIn("finalization_succeeded", event_types)

    def test_publication_becomes_decision_intent_proposed(self):
        """publication_confirmed → decision_intent_proposed."""
        engine = _build_engine([_make_publication_rule()])
        store = RuntimeStateStore()
        store.set("needs_publication", True)
        store.set("session_name", "test_session")
        scheduler = EventScheduler(store=store)

        output = evaluate_and_emit(engine, store, scheduler)
        events = list(scheduler._queue)
        event_types = [e.event_type for e in events]

        self.assertIn("decision_intent_proposed", event_types)
        self.assertNotIn("publication_confirmed", event_types)

    def test_clear_becomes_decision_intent_proposed(self):
        """clear_requested → decision_intent_proposed."""
        engine = _build_engine([_make_clear_rule()])
        store = RuntimeStateStore()
        store.set("needs_clear", True)
        store.set("session_name", "test_session")
        scheduler = EventScheduler(store=store)

        output = evaluate_and_emit(engine, store, scheduler)
        events = list(scheduler._queue)
        event_types = [e.event_type for e in events]

        self.assertIn("decision_intent_proposed", event_types)
        self.assertNotIn("clear_requested", event_types)

    def test_ingress_payload_carries_intent_type(self):
        """Translated event carries correct intent_type in payload."""
        engine = _build_engine([_make_finalization_rule()])
        store = RuntimeStateStore()
        store.set("session_name", "test_session")
        scheduler = EventScheduler(store=store)

        evaluate_and_emit(engine, store, scheduler)

        ingress = [e for e in scheduler._queue if e.event_type == "decision_intent_proposed"][0]
        self.assertEqual(ingress.payload["intent_type"], "lifecycle_finalize")

    def test_ingress_preserves_decision_provenance(self):
        """source_context carries original decision_id, event_type, strategy."""
        engine = _build_engine([_make_finalization_rule()])
        store = RuntimeStateStore()
        store.set("session_name", "test_session")
        scheduler = EventScheduler(store=store)

        output = evaluate_and_emit(engine, store, scheduler)

        ingress = [e for e in scheduler._queue if e.event_type == "decision_intent_proposed"][0]
        ctx = ingress.payload["source_context"]
        self.assertEqual(ctx["decision_id"], output.decision_id)
        self.assertEqual(ctx["original_event_type"], "finalization_succeeded")
        self.assertEqual(ctx["strategy_name"], "rule_based")
        self.assertIn("state_hash", ctx)
        self.assertIn("reasoning", ctx)


class TestActivePassthrough(unittest.TestCase):
    """Non-lifecycle events pass through unchanged in active mode."""

    def setUp(self):
        set_orchestration_mode_for_testing(True)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_custom_event_not_translated(self):
        """Non-lifecycle event types emit as raw action events."""
        engine = _build_engine([_make_custom_rule()])
        store = RuntimeStateStore()
        store.set("custom_trigger", True)
        scheduler = EventScheduler(store=store)

        output = evaluate_and_emit(engine, store, scheduler)

        events = list(scheduler._queue)
        event_types = [e.event_type for e in events]

        # Should have the raw custom event, NOT decision_intent_proposed
        self.assertIn("custom_action_fired", event_types)
        self.assertNotIn("decision_intent_proposed", event_types)
        # Observability still fires
        self.assertIn("decision_made", event_types)


class TestInactivePreservesLegacy(unittest.TestCase):
    """When inactive, evaluate_and_emit works exactly as before."""

    def setUp(self):
        set_orchestration_mode_for_testing(False)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_finalization_emits_raw_event(self):
        """In inactive mode, finalization_succeeded emits directly."""
        engine = _build_engine([_make_finalization_rule()])
        store = RuntimeStateStore()
        store.set("session_name", "test_session")
        scheduler = EventScheduler(store=store)

        evaluate_and_emit(engine, store, scheduler)

        events = list(scheduler._queue)
        event_types = [e.event_type for e in events]

        self.assertIn("finalization_succeeded", event_types)
        self.assertNotIn("decision_intent_proposed", event_types)
        self.assertIn("decision_made", event_types)

    def test_no_decision_returns_none(self):
        """No matching rule → no events emitted."""
        engine = _build_engine([_make_finalization_rule()])
        store = RuntimeStateStore()
        store.set("session_name", "wrong_session")
        scheduler = EventScheduler(store=store)

        result = evaluate_and_emit(engine, store, scheduler)

        self.assertIsNone(result)
        events = list(scheduler._queue)
        self.assertEqual(len(events), 0)


class TestDecisionToOrchestrationFullFlow(unittest.TestCase):
    """Decision → intent → orchestration → execution → completion.

    Proves the full ingress unification path works end-to-end:
    1. DecisionEngine produces finalization_succeeded
    2. evaluate_and_emit translates to decision_intent_proposed
    3. IntentCoordinator creates intent, activates, dispatches step 0
    4. Steps execute through execution results
    5. Intent reaches COMPLETED
    """

    def setUp(self):
        set_orchestration_mode_for_testing(True)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_decision_driven_lifecycle_finalize(self):
        """Full flow: decision → orchestration → 3-step lifecycle."""
        scheduler, store, coord = _build_fully_wired_scheduler()

        # Seed state so the rule fires
        store.set("session_name", "test_session")

        # Build engine with finalization rule
        engine = _build_engine([_make_finalization_rule()])

        # ── Phase 1: Decision evaluates and emits ingress ──
        output = evaluate_and_emit(engine, store, scheduler)
        self.assertIsNotNone(output)
        self.assertEqual(output.event_type, "finalization_succeeded")

        # Drain the scheduler — this processes decision_intent_proposed
        run1 = scheduler.run()

        # Intent should be created and active
        goal = {"session_name": "test_session"}
        intent_id = compute_intent_id(IntentType.LIFECYCLE_FINALIZE, goal)
        intent_data = store.get(intent_store_key(intent_id))
        self.assertIsNotNone(intent_data, "intent not created from decision ingress")
        self.assertEqual(intent_data["status"], IntentStatus.ACTIVE.value)
        self.assertEqual(intent_data["total_steps"], 3)
        self.assertEqual(intent_data["current_step"], 0)

        # Step 0 correlation should exist
        step0_id = _get_step_event_id_for_intent(store, intent_id, 0)
        self.assertIsNotNone(step0_id, "step 0 correlation not written")

        # ── Phase 2: Execute step 0 → step 1 ──
        _simulate_execution_result(store, scheduler, step0_id, "exec_d_step0")
        scheduler.run()

        intent_data = store.get(intent_store_key(intent_id))
        self.assertEqual(intent_data["current_step"], 1)

        step1_id = _get_step_event_id_for_intent(store, intent_id, 1)
        self.assertIsNotNone(step1_id)

        # ── Phase 3: Execute step 1 → step 2 ──
        _simulate_execution_result(store, scheduler, step1_id, "exec_d_step1")
        scheduler.run()

        intent_data = store.get(intent_store_key(intent_id))
        self.assertEqual(intent_data["current_step"], 2)

        step2_id = _get_step_event_id_for_intent(store, intent_id, 2)
        self.assertIsNotNone(step2_id)

        # ── Phase 4: Execute step 2 → COMPLETED ──
        _simulate_execution_result(store, scheduler, step2_id, "exec_d_step2")
        scheduler.run()

        intent_data = store.get(intent_store_key(intent_id))
        self.assertEqual(intent_data["status"], IntentStatus.COMPLETED.value)

        # Active index removed
        active = store.get(f"active_intent.{intent_id}")
        self.assertIsNone(active)

    def test_correlation_chain_preserves_decision_provenance(self):
        """Decision provenance flows through the entire chain."""
        scheduler, store, coord = _build_fully_wired_scheduler()
        store.set("session_name", "test_session")

        engine = _build_engine([_make_finalization_rule()])
        output = evaluate_and_emit(engine, store, scheduler)

        # Before draining, verify the ingress event has provenance
        ingress_events = [
            e for e in scheduler._queue
            if e.event_type == "decision_intent_proposed"
        ]
        self.assertEqual(len(ingress_events), 1)
        ctx = ingress_events[0].payload["source_context"]
        self.assertEqual(ctx["decision_id"], output.decision_id)
        self.assertEqual(ctx["original_event_type"], "finalization_succeeded")


class TestNoDoubleProcessing(unittest.TestCase):
    """Lifecycle handlers don't independently chain when decision enters
    through orchestration ingress."""

    def setUp(self):
        set_orchestration_mode_for_testing(True)

    def tearDown(self):
        set_orchestration_mode_for_testing(None)

    def test_lifecycle_handlers_dont_chain_from_decision(self):
        """After decision → ingress → step 0, intent stays at step 0
        without execution result (lifecycle handlers can't advance it)."""
        scheduler, store, coord = _build_fully_wired_scheduler()
        store.set("session_name", "test_session")

        engine = _build_engine([_make_finalization_rule()])
        evaluate_and_emit(engine, store, scheduler)
        scheduler.run()

        # Intent exists at step 0
        goal = {"session_name": "test_session"}
        intent_id = compute_intent_id(IntentType.LIFECYCLE_FINALIZE, goal)
        intent_data = store.get(intent_store_key(intent_id))
        self.assertEqual(intent_data["current_step"], 0)
        self.assertEqual(intent_data["status"], IntentStatus.ACTIVE.value)

        # Run scheduler again — should be idle, no advancement
        run2 = scheduler.run()
        self.assertEqual(run2.events_processed, 0)

        # Intent still at step 0
        intent_data = store.get(intent_store_key(intent_id))
        self.assertEqual(intent_data["current_step"], 0)

    def test_planner_strategy_yields_with_decision_intent(self):
        """PlannerStrategy yields when active, even with decision-created intents."""
        scheduler, store, coord = _build_fully_wired_scheduler()
        store.set("session_name", "test_session")

        engine = _build_engine([_make_finalization_rule()])
        evaluate_and_emit(engine, store, scheduler)
        scheduler.run()

        from umh.substrate.planner import PlannerStrategy

        strategy = PlannerStrategy()
        result = strategy.evaluate(store.snapshot())
        self.assertIsNone(result)

    def test_no_raw_lifecycle_event_in_active_decision(self):
        """The raw lifecycle event never enters the scheduler in active mode."""
        store = RuntimeStateStore()
        store.set("session_name", "test_session")
        scheduler = EventScheduler(store=store)

        engine = _build_engine([_make_finalization_rule()])
        evaluate_and_emit(engine, store, scheduler)

        # Walk the entire queue — no finalization_succeeded
        for event in scheduler._queue:
            self.assertNotEqual(
                event.event_type,
                "finalization_succeeded",
                "raw lifecycle event leaked into scheduler in active mode",
            )


if __name__ == "__main__":
    unittest.main()
