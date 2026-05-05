"""Tests for the intent + planning system.

Validates:
1. Plan determinism: same intent + state → same plan, always.
2. Replay consistency: snapshot-based evaluation matches live store.
3. Multi-step execution: intent progresses through plan steps correctly.
4. IntentAwareStrategy: planner takes priority, falls back to rules.
5. Observability events have correct shape.
6. Intent lifecycle: pending → active → completed.
7. Edge cases: no intents, no generator, exhausted steps.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.decision_engine import (
    DecisionEngine,
    DecisionOutput,
    Rule,
    RuleBasedStrategy,
    _compute_state_hash,
    evaluate_and_emit,
)
from umh.substrate.event_scheduler import EventScheduler
from umh.substrate.intent_models import (
    Intent,
    IntentStatus,
    IntentType,
    Plan,
    PlanStep,
    build_intent_create_mutations,
    build_intent_update_mutations,
    compute_intent_id,
    compute_plan_id,
    get_active_intents_from_state,
    get_intent_from_state,
    intent_store_key,
)
from umh.substrate.planner import (
    IntentAwareStrategy,
    PlannerStrategy,
    build_intent_complete_mutations,
    build_step_advance_mutations,
    derive_plan,
)
from umh.substrate.planner_events import (
    build_intent_completed_event,
    build_intent_created_event,
    build_plan_created_event,
    build_plan_step_emitted_event,
)
from umh.substrate.runtime_state_store import RuntimeStateStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store(state: dict | None = None) -> RuntimeStateStore:
    store = RuntimeStateStore()
    if state:
        for k, v in state.items():
            store.set(k, v)
    return store


def _make_intent(
    intent_type: IntentType = IntentType.LIFECYCLE_FINALIZE,
    goal: dict | None = None,
    priority: int = 100,
    session_name: str = "test_session",
    status: IntentStatus = IntentStatus.ACTIVE,
    current_step: int = 0,
    total_steps: int = 0,
    created_at: str = "2026-04-17T00:00:00+00:00",
) -> Intent:
    """Create a test intent with deterministic fields."""
    goal = goal or {"finalization_result": {"success": True}}
    iid = compute_intent_id(intent_type, goal)
    return Intent(
        intent_id=iid,
        intent_type=intent_type,
        goal=goal,
        priority=priority,
        status=status,
        created_at=created_at,
        session_name=session_name,
        current_step=current_step,
        total_steps=total_steps,
    )


def _store_with_intent(intent: Intent) -> RuntimeStateStore:
    """Create a store with a single active intent."""
    store = RuntimeStateStore()
    mutations = build_intent_create_mutations(intent)
    store.apply_mutations(mutations)
    return store


def _make_rule_fallback() -> RuleBasedStrategy:
    """Simple rule-based fallback for testing composite strategy."""
    return RuleBasedStrategy(
        rules=[
            Rule(
                rule_id="fallback_rule",
                description="Always fires when status=idle",
                condition=lambda s: s.get("status") == "idle",
                event_type="idle_action",
                build_payload=lambda s: {"session_name": s.get("session_name", "")},
                priority=50,
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Intent model tests
# ---------------------------------------------------------------------------


class TestIntentModel:
    def test_intent_id_deterministic(self):
        """Same type + goal → same intent_id."""
        goal = {"key": "value"}
        id1 = compute_intent_id(IntentType.LIFECYCLE_FINALIZE, goal)
        id2 = compute_intent_id(IntentType.LIFECYCLE_FINALIZE, goal)
        assert id1 == id2

    def test_intent_id_varies_with_type(self):
        """Different type → different intent_id."""
        goal = {"key": "value"}
        id1 = compute_intent_id(IntentType.LIFECYCLE_FINALIZE, goal)
        id2 = compute_intent_id(IntentType.LIFECYCLE_PUBLISH, goal)
        assert id1 != id2

    def test_intent_id_varies_with_goal(self):
        """Different goal → different intent_id."""
        id1 = compute_intent_id(IntentType.CUSTOM, {"a": 1})
        id2 = compute_intent_id(IntentType.CUSTOM, {"a": 2})
        assert id1 != id2

    def test_serialisation_roundtrip(self):
        """to_dict / from_dict roundtrip preserves all fields."""
        intent = _make_intent()
        d = intent.to_dict()
        restored = Intent.from_dict(d)
        assert restored.intent_id == intent.intent_id
        assert restored.intent_type == intent.intent_type
        assert restored.goal == intent.goal
        assert restored.priority == intent.priority
        assert restored.status == intent.status
        assert restored.current_step == intent.current_step

    def test_with_status(self):
        """with_status returns new intent with updated status."""
        intent = _make_intent(status=IntentStatus.PENDING)
        active = intent.with_status(IntentStatus.ACTIVE)
        assert active.status == IntentStatus.ACTIVE
        assert intent.status == IntentStatus.PENDING  # original unchanged

    def test_with_step_advanced(self):
        """with_step_advanced increments current_step."""
        intent = _make_intent(current_step=1)
        advanced = intent.with_step_advanced()
        assert advanced.current_step == 2
        assert intent.current_step == 1  # original unchanged

    def test_is_terminal(self):
        """Completed and failed intents are terminal."""
        assert _make_intent(status=IntentStatus.COMPLETED).is_terminal
        assert _make_intent(status=IntentStatus.FAILED).is_terminal
        assert not _make_intent(status=IntentStatus.ACTIVE).is_terminal
        assert not _make_intent(status=IntentStatus.PENDING).is_terminal

    def test_steps_remaining(self):
        intent = _make_intent(current_step=1, total_steps=3)
        assert intent.steps_remaining == 2


class TestIntentStateMutations:
    def test_create_mutations(self):
        """build_intent_create_mutations produces SET (intent) + SET (keyed index)."""
        intent = _make_intent()
        mutations = build_intent_create_mutations(intent)
        assert len(mutations) == 2
        assert mutations[0]["op"] == "SET"
        assert mutations[0]["key"] == intent_store_key(intent.intent_id)
        assert mutations[1]["op"] == "SET"
        assert mutations[1]["key"] == f"active_intent.{intent.intent_id}"
        assert mutations[1]["value"]["priority"] == intent.priority

    def test_store_persistence_roundtrip(self):
        """Intent survives store → snapshot → extract cycle."""
        intent = _make_intent()
        store = _store_with_intent(intent)

        snapshot = store.snapshot()
        extracted = get_intent_from_state(snapshot, intent.intent_id)
        assert extracted is not None
        assert extracted.intent_id == intent.intent_id
        assert extracted.goal == intent.goal

    def test_active_intents_sorted_by_priority(self):
        """get_active_intents_from_state returns intents sorted by priority."""
        low = _make_intent(
            intent_type=IntentType.LIFECYCLE_FINALIZE,
            goal={"finalization_result": {"success": True}},
            priority=10,
        )
        high = _make_intent(
            intent_type=IntentType.LIFECYCLE_PUBLISH,
            goal={"finalization_result": {"success": True}},
            priority=50,
        )
        store = RuntimeStateStore()
        store.apply_mutations(build_intent_create_mutations(high))
        store.apply_mutations(build_intent_create_mutations(low))

        intents = get_active_intents_from_state(store.snapshot())
        assert len(intents) == 2
        assert intents[0].priority < intents[1].priority

    def test_terminal_intents_excluded_from_active(self):
        """Completed intents are not returned by get_active_intents_from_state."""
        intent = _make_intent(status=IntentStatus.COMPLETED)
        store = _store_with_intent(intent)

        intents = get_active_intents_from_state(store.snapshot())
        assert len(intents) == 0


# ---------------------------------------------------------------------------
# Plan derivation tests
# ---------------------------------------------------------------------------


class TestPlanDerivation:
    def test_lifecycle_finalize_plan(self):
        """LIFECYCLE_FINALIZE produces 3-step plan."""
        intent = _make_intent(intent_type=IntentType.LIFECYCLE_FINALIZE)
        plan = derive_plan(intent, {})
        assert plan is not None
        assert plan.step_count == 3
        assert plan.steps[0].event_type == "finalization_succeeded"
        assert plan.steps[1].event_type == "publication_confirmed"
        assert plan.steps[2].event_type == "clear_requested"

    def test_lifecycle_publish_plan(self):
        """LIFECYCLE_PUBLISH produces 1-step plan."""
        intent = _make_intent(intent_type=IntentType.LIFECYCLE_PUBLISH)
        plan = derive_plan(intent, {})
        assert plan is not None
        assert plan.step_count == 1
        assert plan.steps[0].event_type == "publication_confirmed"

    def test_lifecycle_clear_plan(self):
        """LIFECYCLE_CLEAR produces 2-step plan."""
        intent = _make_intent(intent_type=IntentType.LIFECYCLE_CLEAR)
        plan = derive_plan(intent, {})
        assert plan is not None
        assert plan.step_count == 2
        assert plan.steps[0].event_type == "clear_requested"
        assert plan.steps[1].event_type == "clear_confirmed"

    def test_execution_request_plan(self):
        """EXECUTION_REQUEST produces 1-step plan."""
        intent = _make_intent(
            intent_type=IntentType.EXECUTION_REQUEST,
            goal={"request": {"primitive": "test"}},
        )
        plan = derive_plan(intent, {})
        assert plan is not None
        assert plan.step_count == 1
        assert plan.steps[0].event_type == "execution_requested"

    def test_custom_plan(self):
        """CUSTOM intent uses steps from goal."""
        intent = _make_intent(
            intent_type=IntentType.CUSTOM,
            goal={
                "steps": [
                    {"event_type": "step_a", "payload": {"x": 1}},
                    {"event_type": "step_b", "payload": {"y": 2}},
                ]
            },
        )
        plan = derive_plan(intent, {})
        assert plan is not None
        assert plan.step_count == 2
        assert plan.steps[0].event_type == "step_a"
        assert plan.steps[1].event_type == "step_b"

    def test_unregistered_type_returns_none(self):
        """WORKFLOW_RUN has no default generator."""
        intent = _make_intent(intent_type=IntentType.WORKFLOW_RUN)
        plan = derive_plan(intent, {})
        assert plan is None

    def test_plan_id_deterministic(self):
        """Same intent + same steps → same plan_id."""
        intent = _make_intent()
        plan1 = derive_plan(intent, {})
        plan2 = derive_plan(intent, {})
        assert plan1 is not None
        assert plan2 is not None
        assert plan1.plan_id == plan2.plan_id

    def test_plan_step_at_bounds(self):
        """step_at returns None for out-of-bounds index."""
        intent = _make_intent()
        plan = derive_plan(intent, {})
        assert plan is not None
        assert plan.step_at(-1) is None
        assert plan.step_at(plan.step_count) is None
        assert plan.step_at(0) is not None


# ---------------------------------------------------------------------------
# Planner strategy determinism tests
# ---------------------------------------------------------------------------


class TestPlannerDeterminism:
    def test_same_state_same_output(self):
        """Same state snapshot → identical DecisionOutput."""
        intent = _make_intent()
        store = _store_with_intent(intent)
        planner = PlannerStrategy()

        snapshot = store.snapshot()
        out1 = planner.evaluate(snapshot)
        out2 = planner.evaluate(snapshot)

        assert out1 is not None
        assert out2 is not None
        assert out1.decision_id == out2.decision_id
        assert out1.event_type == out2.event_type
        assert out1.payload == out2.payload
        assert out1.state_hash == out2.state_hash

    def test_replay_from_snapshot(self):
        """Snapshot-based eval matches live store eval."""
        intent = _make_intent()
        store = _store_with_intent(intent)
        planner = PlannerStrategy()

        snapshot = store.snapshot()
        live_out = planner.evaluate(snapshot)

        # Simulate replay: create new store from snapshot
        replay_store = _make_store(snapshot)
        replay_snapshot = replay_store.snapshot()
        replay_out = planner.evaluate(replay_snapshot)

        assert live_out is not None
        assert replay_out is not None
        assert live_out.decision_id == replay_out.decision_id
        assert live_out.event_type == replay_out.event_type

    def test_different_state_different_decision_id(self):
        """Different state → different decision_id."""
        intent1 = _make_intent(session_name="s1")
        intent2 = _make_intent(session_name="s2")

        store1 = _store_with_intent(intent1)
        store2 = _store_with_intent(intent2)

        planner = PlannerStrategy()
        out1 = planner.evaluate(store1.snapshot())
        out2 = planner.evaluate(store2.snapshot())

        assert out1 is not None
        assert out2 is not None
        assert out1.decision_id != out2.decision_id


# ---------------------------------------------------------------------------
# Multi-step execution tests
# ---------------------------------------------------------------------------


class TestMultiStepExecution:
    def test_step_progression(self):
        """Intent advances through plan steps correctly."""
        intent = _make_intent(
            intent_type=IntentType.LIFECYCLE_FINALIZE,
            current_step=0,
        )
        plan = derive_plan(intent, {})
        assert plan is not None

        store = _store_with_intent(intent)
        planner = PlannerStrategy()

        # Step 0: finalization_succeeded
        out0 = planner.evaluate(store.snapshot())
        assert out0 is not None
        assert out0.event_type == "finalization_succeeded"
        assert out0.payload["_step_index"] == 0

        # Advance to step 1
        advanced = intent.with_step_advanced()
        store.apply_mutations(build_step_advance_mutations(intent))

        out1 = planner.evaluate(store.snapshot())
        assert out1 is not None
        assert out1.event_type == "publication_confirmed"
        assert out1.payload["_step_index"] == 1

        # Advance to step 2
        store.apply_mutations(build_step_advance_mutations(advanced))

        out2 = planner.evaluate(store.snapshot())
        assert out2 is not None
        assert out2.event_type == "clear_requested"
        assert out2.payload["_step_index"] == 2

    def test_exhausted_steps_triggers_completion(self):
        """When all steps done, planner emits intent_completion_requested."""
        intent = _make_intent(
            intent_type=IntentType.LIFECYCLE_FINALIZE,
            current_step=3,  # 3-step plan, index 3 = past end
            total_steps=3,
        )
        store = _store_with_intent(intent)
        planner = PlannerStrategy()

        out = planner.evaluate(store.snapshot())
        assert out is not None
        assert out.event_type == "intent_completion_requested"
        assert out.payload["steps_executed"] == 3

    def test_intent_completion_mutations(self):
        """build_intent_complete_mutations marks intent as completed."""
        intent = _make_intent(status=IntentStatus.ACTIVE)
        mutations = build_intent_complete_mutations(intent)

        store = _store_with_intent(intent)
        store.apply_mutations(mutations)

        snapshot = store.snapshot()
        updated = get_intent_from_state(snapshot, intent.intent_id)
        assert updated is not None
        assert updated.status == IntentStatus.COMPLETED

    def test_full_lifecycle_three_steps(self):
        """Full 3-step intent lifecycle: step 0 → step 1 → step 2 → complete."""
        intent = _make_intent(intent_type=IntentType.LIFECYCLE_FINALIZE)
        store = _store_with_intent(intent)
        planner = PlannerStrategy()

        expected_events = [
            "finalization_succeeded",
            "publication_confirmed",
            "clear_requested",
            "intent_completion_requested",
        ]

        current = intent
        for i, expected in enumerate(expected_events):
            out = planner.evaluate(store.snapshot())
            assert out is not None, f"Step {i}: expected output but got None"
            assert out.event_type == expected, (
                f"Step {i}: expected {expected}, got {out.event_type}"
            )

            if expected == "intent_completion_requested":
                store.apply_mutations(build_intent_complete_mutations(current))
            else:
                store.apply_mutations(build_step_advance_mutations(current))
                current = current.with_step_advanced()

        # After completion, no more decisions
        final = planner.evaluate(store.snapshot())
        assert final is None


# ---------------------------------------------------------------------------
# IntentAwareStrategy tests
# ---------------------------------------------------------------------------


class TestIntentAwareStrategy:
    def test_planner_takes_priority(self):
        """When intents exist, planner fires instead of rules."""
        intent = _make_intent()
        store = _store_with_intent(intent)
        store.set("status", "idle")  # Would trigger rule fallback

        strategy = IntentAwareStrategy(fallback=_make_rule_fallback())
        out = strategy.evaluate(store.snapshot())

        assert out is not None
        assert out.strategy_name == "planner"

    def test_fallback_when_no_intents(self):
        """Without intents, rule-based fallback fires."""
        store = _make_store({"status": "idle", "session_name": "test"})

        strategy = IntentAwareStrategy(fallback=_make_rule_fallback())
        out = strategy.evaluate(store.snapshot())

        assert out is not None
        assert out.strategy_name == "rule_based"

    def test_no_fallback_no_intents_returns_none(self):
        """Without intents and no fallback, returns None."""
        store = _make_store({"status": "idle"})

        strategy = IntentAwareStrategy(fallback=None)
        out = strategy.evaluate(store.snapshot())

        assert out is None

    def test_integrates_with_decision_engine(self):
        """IntentAwareStrategy works as DecisionEngine strategy."""
        intent = _make_intent()
        store = _store_with_intent(intent)

        strategy = IntentAwareStrategy(fallback=_make_rule_fallback())
        engine = DecisionEngine(strategy=strategy)

        out = engine.evaluate(store)
        assert out is not None
        assert out.event_type == "finalization_succeeded"

    def test_integrates_with_evaluate_and_emit(self):
        """Full integration: engine + scheduler via evaluate_and_emit."""
        intent = _make_intent()
        store = _store_with_intent(intent)

        strategy = IntentAwareStrategy(fallback=_make_rule_fallback())
        engine = DecisionEngine(strategy=strategy)
        scheduler = EventScheduler(store=store)

        out = evaluate_and_emit(engine, store, scheduler)
        assert out is not None
        assert scheduler.pending_count() == 2  # observability + action


# ---------------------------------------------------------------------------
# Observability event shape tests
# ---------------------------------------------------------------------------


class TestObservabilityEvents:
    def test_intent_created_event(self):
        ev = build_intent_created_event(
            intent_id="int_abc",
            intent_type="lifecycle_finalize",
            goal={"key": "val"},
            priority=10,
            session_name="s1",
        )
        assert ev.event_type == "intent_created"
        assert ev.payload["intent_id"] == "int_abc"
        assert ev.payload["intent_type"] == "lifecycle_finalize"
        assert ev.metadata["intent_id"] == "int_abc"

    def test_plan_created_event(self):
        ev = build_plan_created_event(
            plan_id="pln_abc",
            intent_id="int_abc",
            step_count=3,
            session_name="s1",
        )
        assert ev.event_type == "plan_created"
        assert ev.payload["step_count"] == 3

    def test_plan_step_emitted_event(self):
        ev = build_plan_step_emitted_event(
            plan_id="pln_abc",
            intent_id="int_abc",
            step_index=1,
            event_type="finalization_succeeded",
            session_name="s1",
        )
        assert ev.event_type == "plan_step_emitted"
        assert ev.payload["step_index"] == 1
        assert ev.payload["emitted_event_type"] == "finalization_succeeded"

    def test_intent_completed_event(self):
        ev = build_intent_completed_event(
            intent_id="int_abc",
            intent_type="lifecycle_finalize",
            session_name="s1",
            steps_executed=3,
        )
        assert ev.event_type == "intent_completed"
        assert ev.payload["steps_executed"] == 3


# ---------------------------------------------------------------------------
# Priority selection tests
# ---------------------------------------------------------------------------


class TestPrioritySelection:
    def test_highest_priority_intent_selected(self):
        """Planner selects the highest-priority (lowest number) active intent."""
        low_priority = _make_intent(
            intent_type=IntentType.LIFECYCLE_PUBLISH,
            goal={"publish": True},
            priority=50,
        )
        high_priority = _make_intent(
            intent_type=IntentType.LIFECYCLE_FINALIZE,
            goal={"finalization_result": {"success": True}},
            priority=10,
        )

        store = RuntimeStateStore()
        store.apply_mutations(build_intent_create_mutations(low_priority))
        store.apply_mutations(build_intent_create_mutations(high_priority))

        planner = PlannerStrategy()
        out = planner.evaluate(store.snapshot())

        assert out is not None
        assert out.payload["_intent_id"] == high_priority.intent_id

    def test_skip_to_next_if_no_generator(self):
        """If highest-priority has no generator, fall through to next."""
        # WORKFLOW_RUN has no generator
        no_gen = _make_intent(
            intent_type=IntentType.WORKFLOW_RUN,
            goal={"workflow": "test"},
            priority=1,
        )
        has_gen = _make_intent(
            intent_type=IntentType.LIFECYCLE_FINALIZE,
            goal={"finalization_result": {"success": True}},
            priority=50,
        )

        store = RuntimeStateStore()
        store.apply_mutations(build_intent_create_mutations(no_gen))
        store.apply_mutations(build_intent_create_mutations(has_gen))

        planner = PlannerStrategy()
        out = planner.evaluate(store.snapshot())

        assert out is not None
        assert out.payload["_intent_id"] == has_gen.intent_id


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
