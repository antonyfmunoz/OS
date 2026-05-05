"""Tests for the decision engine — determinism, replay, and integration.

Validates:
1. Deterministic output: same state → same DecisionOutput every time.
2. Replay consistency: evaluate_snapshot with a captured snapshot
   produces the same result as evaluate with a live store.
3. Rule priority ordering works correctly.
4. Engine disabled → returns None.
5. DECISION_MADE event has correct shape.
6. evaluate_and_emit wires into scheduler correctly.
7. No-match state returns None.
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
from umh.substrate.event_scheduler import EventScheduler, SchedulerEvent
from umh.substrate.runtime_state_store import RuntimeStateStore


# ---------------------------------------------------------------------------
# Test rules
# ---------------------------------------------------------------------------


def _needs_finalization(state: dict) -> bool:
    """True when status is completion_proposed but not yet finalized."""
    return (
        state.get("status") == "completion_proposed"
        and state.get("finalization_status") != "succeeded"
    )


def _build_finalization_payload(state: dict) -> dict:
    return {
        "session_name": state.get("session_name", "test"),
        "finalization_result": {"success": True},
    }


def _needs_publication(state: dict) -> bool:
    return (
        state.get("finalization_status") == "succeeded"
        and state.get("publication_confirmed") is not True
    )


def _build_publication_payload(state: dict) -> dict:
    return {"session_name": state.get("session_name", "test")}


FINALIZATION_RULE = Rule(
    rule_id="finalize_ready",
    description="Trigger finalization when completion is proposed",
    condition=_needs_finalization,
    event_type="finalization_succeeded",
    build_payload=_build_finalization_payload,
    priority=10,
)

PUBLICATION_RULE = Rule(
    rule_id="publish_ready",
    description="Trigger publication when finalization succeeded",
    condition=_needs_publication,
    event_type="publication_confirmed",
    build_payload=_build_publication_payload,
    priority=20,
)


def _make_engine(enabled: bool = True) -> DecisionEngine:
    strategy = RuleBasedStrategy(rules=[FINALIZATION_RULE, PUBLICATION_RULE])
    return DecisionEngine(strategy=strategy, enabled=enabled)


def _make_store(state: dict) -> RuntimeStateStore:
    store = RuntimeStateStore()
    for k, v in state.items():
        store.set(k, v)
    return store


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_deterministic_same_state_same_output():
    """Same state snapshot must produce identical DecisionOutput."""
    state = {"status": "completion_proposed", "session_name": "s1"}
    engine = _make_engine()

    store = _make_store(state)
    out1 = engine.evaluate(store)
    out2 = engine.evaluate(store)

    assert out1 is not None
    assert out2 is not None
    assert out1.decision_id == out2.decision_id
    assert out1.event_type == out2.event_type
    assert out1.payload == out2.payload
    assert out1.reasoning == out2.reasoning
    assert out1.state_hash == out2.state_hash


def test_replay_consistency():
    """evaluate_snapshot with a captured snapshot must match evaluate with store."""
    state = {"status": "completion_proposed", "session_name": "s1"}
    engine = _make_engine()

    store = _make_store(state)
    live_out = engine.evaluate(store)

    snapshot = store.snapshot()
    replay_out = engine.evaluate_snapshot(snapshot)

    assert live_out is not None
    assert replay_out is not None
    assert live_out.decision_id == replay_out.decision_id
    assert live_out.event_type == replay_out.event_type
    assert live_out.payload == replay_out.payload
    assert live_out.state_hash == replay_out.state_hash


def test_priority_ordering():
    """Lower priority number fires first."""
    state = {
        "status": "completion_proposed",
        "finalization_status": None,
        "session_name": "s1",
    }
    engine = _make_engine()
    store = _make_store(state)

    out = engine.evaluate(store)
    assert out is not None
    assert out.event_type == "finalization_succeeded"  # priority 10 beats 20


def test_second_rule_fires_when_first_does_not_match():
    """When higher-priority rule doesn't match, next rule is evaluated."""
    state = {
        "status": "finalized",
        "finalization_status": "succeeded",
        "publication_confirmed": False,
        "session_name": "s1",
    }
    engine = _make_engine()
    store = _make_store(state)

    out = engine.evaluate(store)
    assert out is not None
    assert out.event_type == "publication_confirmed"


def test_no_match_returns_none():
    """When no rule matches, engine returns None."""
    state = {
        "status": "finalized",
        "finalization_status": "succeeded",
        "publication_confirmed": True,
        "session_name": "s1",
    }
    engine = _make_engine()
    store = _make_store(state)

    out = engine.evaluate(store)
    assert out is None


def test_disabled_returns_none():
    """Disabled engine always returns None."""
    state = {"status": "completion_proposed", "session_name": "s1"}
    engine = _make_engine(enabled=False)
    store = _make_store(state)

    out = engine.evaluate(store)
    assert out is None


def test_decision_made_event_shape():
    """The observability event has the required fields."""
    state = {"status": "completion_proposed", "session_name": "s1"}
    engine = _make_engine()
    store = _make_store(state)

    out = engine.evaluate(store)
    assert out is not None

    obs = out.observability_event
    assert obs.event_type == "decision_made"
    assert obs.payload["decision_id"] == out.decision_id
    assert obs.payload["state_hash"] == out.state_hash
    assert obs.payload["chosen_event_type"] == "finalization_succeeded"
    assert obs.payload["reasoning"] != ""
    assert obs.metadata["strategy"] == "rule_based"


def test_action_event_shape():
    """The action event has correct event_type and decision_id in metadata."""
    state = {"status": "completion_proposed", "session_name": "s1"}
    engine = _make_engine()
    store = _make_store(state)

    out = engine.evaluate(store)
    assert out is not None

    action = out.action_event
    assert action.event_type == "finalization_succeeded"
    assert action.metadata["decision_id"] == out.decision_id
    assert action.source.startswith("decision_engine:")


def test_evaluate_and_emit():
    """evaluate_and_emit emits both events into the scheduler."""
    state = {"status": "completion_proposed", "session_name": "s1"}
    store = _make_store(state)
    engine = _make_engine()

    scheduler = EventScheduler(store=store)

    out = evaluate_and_emit(engine, store, scheduler)
    assert out is not None
    assert scheduler.pending_count() == 2  # observability + action


def test_evaluate_and_emit_no_decision():
    """evaluate_and_emit with no matching rules emits nothing."""
    state = {
        "status": "terminal",
        "finalization_status": "succeeded",
        "publication_confirmed": True,
        "session_name": "s1",
    }
    store = _make_store(state)
    engine = _make_engine()

    scheduler = EventScheduler(store=store)

    out = evaluate_and_emit(engine, store, scheduler)
    assert out is None
    assert scheduler.pending_count() == 0


def test_state_hash_matches_store():
    """Engine state_hash matches RuntimeStateStore.compute_state_hash()."""
    state = {"status": "completion_proposed", "session_name": "s1"}
    store = _make_store(state)
    engine = _make_engine()

    out = engine.evaluate(store)
    assert out is not None
    assert out.state_hash == store.compute_state_hash()


def test_different_state_different_decision_id():
    """Different state snapshots produce different decision_ids."""
    engine = _make_engine()

    store1 = _make_store({"status": "completion_proposed", "session_name": "s1"})
    store2 = _make_store({"status": "completion_proposed", "session_name": "s2"})

    out1 = engine.evaluate(store1)
    out2 = engine.evaluate(store2)

    assert out1 is not None
    assert out2 is not None
    assert out1.decision_id != out2.decision_id


def test_evaluation_count_tracks():
    """Engine tracks how many evaluations have been performed."""
    engine = _make_engine()
    store = _make_store({"status": "completion_proposed", "session_name": "s1"})

    assert engine.evaluation_count == 0
    engine.evaluate(store)
    assert engine.evaluation_count == 1
    engine.evaluate(store)
    assert engine.evaluation_count == 2


def test_rule_condition_error_skips_rule():
    """A rule whose condition raises is skipped, not fatal."""

    def bad_condition(state):
        raise ValueError("broken")

    bad_rule = Rule(
        rule_id="broken",
        description="Always errors",
        condition=bad_condition,
        event_type="never_fires",
        build_payload=lambda s: {},
        priority=1,
    )

    strategy = RuleBasedStrategy(rules=[bad_rule, FINALIZATION_RULE])
    engine = DecisionEngine(strategy=strategy)
    store = _make_store({"status": "completion_proposed", "session_name": "s1"})

    out = engine.evaluate(store)
    assert out is not None
    assert out.event_type == "finalization_succeeded"


def test_add_rule_maintains_priority():
    """Adding a rule re-sorts by priority."""
    strategy = RuleBasedStrategy(rules=[PUBLICATION_RULE])
    assert strategy.rules[0].rule_id == "publish_ready"

    strategy.add_rule(FINALIZATION_RULE)
    assert strategy.rules[0].rule_id == "finalize_ready"  # priority 10 < 20


def test_enable_disable_toggle():
    """Engine can be toggled on and off."""
    engine = _make_engine(enabled=True)
    store = _make_store({"status": "completion_proposed", "session_name": "s1"})

    assert engine.evaluate(store) is not None

    engine.enabled = False
    assert engine.evaluate(store) is None

    engine.enabled = True
    assert engine.evaluate(store) is not None


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
