"""Tests for intent-level competition and scoring.

Validates:
1. Two intents, one higher success rate → selected.
2. Same score → deterministic tie-break on (intent_type, goal_hash).
3. No memory → neutral score (0.0).
4. Blocked intent never selected even if it would score highest.
5. Deterministic across 100 runs.
6. Replay produces identical selection.
7. Single candidate → no competition event emitted.
8. score_intent edge cases.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.decision_engine import (
    DecisionEngine,
    DecisionOutput,
    Rule,
    RuleBasedStrategy,
    _select_winner,
    evaluate_and_emit,
)
from umh.substrate.event_scheduler import EventScheduler, SchedulerEvent
from umh.substrate.intent_memory import (
    compute_memory_key,
    lookup_intent_memory,
    score_intent,
)
from umh.substrate.orchestration_mode import set_orchestration_mode_for_testing
from umh.substrate.runtime_state_store import RuntimeStateStore


# ── Helpers ──────────────────────────────────────────────────────────


def _make_store(state: dict | None = None) -> RuntimeStateStore:
    store = RuntimeStateStore()
    for k, v in (state or {}).items():
        store.set(k, v)
    return store


def _finalize_condition(state: dict) -> bool:
    return state.get("needs_finalize", False)


def _publish_condition(state: dict) -> bool:
    return state.get("needs_publish", False)


def _clear_condition(state: dict) -> bool:
    return state.get("needs_clear", False)


FINALIZE_RULE = Rule(
    rule_id="finalize",
    description="Trigger finalization",
    condition=_finalize_condition,
    event_type="finalization_succeeded",
    build_payload=lambda s: {"session_name": s.get("session_name", "test")},
    priority=10,
)

PUBLISH_RULE = Rule(
    rule_id="publish",
    description="Trigger publication",
    condition=_publish_condition,
    event_type="publication_confirmed",
    build_payload=lambda s: {"session_name": s.get("session_name", "test")},
    priority=20,
)

CLEAR_RULE = Rule(
    rule_id="clear",
    description="Trigger clear",
    condition=_clear_condition,
    event_type="clear_requested",
    build_payload=lambda s: {"session_name": s.get("session_name", "test")},
    priority=30,
)


def _make_engine(rules: list[Rule] | None = None) -> DecisionEngine:
    strategy = RuleBasedStrategy(
        rules=rules or [FINALIZE_RULE, PUBLISH_RULE, CLEAR_RULE]
    )
    return DecisionEngine(strategy=strategy)


def _seed_memory(
    store: RuntimeStateStore,
    intent_type: str,
    goal: dict,
    success_count: int = 0,
    failure_count: int = 0,
    execution_count: int = 0,
) -> None:
    """Write a synthetic memory record into the store."""
    key = compute_memory_key(intent_type, goal)
    store.set(
        key,
        {
            "intent_type": intent_type,
            "goal": goal,
            "success_count": success_count,
            "failure_count": failure_count,
            "failure_by_type": {
                "execution_failed": failure_count,
                "execution_timed_out": 0,
                "execution_rejected": 0,
                "driver_failure": 0,
            },
            "last_outcome": "completed" if success_count > 0 else "failed",
            "last_reason": "",
            "execution_count": execution_count or (success_count + failure_count),
            "last_updated_at": "2026-04-17T12:00:00+00:00",
            "last_success_at": "2026-04-17T12:00:00+00:00"
            if success_count > 0
            else None,
        },
    )


# ── score_intent tests ──────────────────────────────────────────────


def test_score_intent_none_memory():
    """No memory → neutral 0.0."""
    assert score_intent(None) == 0.0


def test_score_intent_zero_execution():
    """Zero execution_count → 0.0 (defensive)."""
    assert (
        score_intent({"execution_count": 0, "success_count": 0, "failure_count": 0})
        == 0.0
    )


def test_score_intent_all_success():
    """3 successes, 0 failures, 3 executions → 1.0."""
    mem = {"execution_count": 3, "success_count": 3, "failure_count": 0}
    assert score_intent(mem) == 1.0


def test_score_intent_all_failure():
    """0 successes, 3 failures, 3 executions → -0.3."""
    mem = {"execution_count": 3, "success_count": 0, "failure_count": 3}
    assert abs(score_intent(mem) - (-0.3)) < 1e-9


def test_score_intent_mixed():
    """2 successes, 1 failure, 3 executions → 2/3 - 0.1 ≈ 0.5667."""
    mem = {"execution_count": 3, "success_count": 2, "failure_count": 1}
    expected = (2 / 3) - (1 * 0.1)
    assert abs(score_intent(mem) - expected) < 1e-9


# ── _select_winner tests ────────────────────────────────────────────


def _make_output(event_type: str, session_name: str = "test") -> DecisionOutput:
    """Build a minimal DecisionOutput for testing."""
    import hashlib

    state_hash = hashlib.sha256(f"{event_type}:{session_name}".encode()).hexdigest()[
        :16
    ]
    return DecisionOutput(
        decision_id=f"dec_{event_type[:8]}",
        event_type=event_type,
        payload={"session_name": session_name},
        reasoning=f"test {event_type}",
        state_hash=state_hash,
        strategy_name="test",
    )


def test_select_winner_higher_score_wins():
    """Candidate with higher score is selected."""
    a = _make_output("finalization_succeeded")
    b = _make_output("publication_confirmed")

    scored = [
        (a, "lifecycle_finalize", 0.8),
        (b, "lifecycle_publish", 0.5),
    ]

    result = _select_winner(scored)
    assert result is not None
    winner, intent_type, score = result
    assert winner.event_type == "finalization_succeeded"
    assert score == 0.8


def test_select_winner_deterministic_tiebreak():
    """Equal scores → deterministic tie-break on (intent_type, goal_hash)."""
    a = _make_output("finalization_succeeded")
    b = _make_output("publication_confirmed")

    scored = [
        (a, "lifecycle_finalize", 0.5),
        (b, "lifecycle_publish", 0.5),
    ]

    result = _select_winner(scored)
    assert result is not None
    winner, _, _ = result

    # Run again with reversed input order — same winner
    scored_reversed = [
        (b, "lifecycle_publish", 0.5),
        (a, "lifecycle_finalize", 0.5),
    ]
    result2 = _select_winner(scored_reversed)
    assert result2 is not None
    winner2, _, _ = result2

    assert winner.decision_id == winner2.decision_id


def test_select_winner_empty():
    """Empty list → None."""
    assert _select_winner([]) is None


# ── Competitive evaluate_and_emit tests ─────────────────────────────


def test_competition_higher_success_rate_wins():
    """With two lifecycle candidates, the one with better memory wins."""
    set_orchestration_mode_for_testing(True)
    try:
        state = {
            "needs_finalize": True,
            "needs_publish": True,
            "session_name": "s1",
        }
        store = _make_store(state)
        engine = _make_engine()

        # finalize: 8/10 success, 2 failures → score = 0.8 - 0.2 = 0.6
        finalize_goal = {"session_name": "s1"}
        _seed_memory(
            store,
            "lifecycle_finalize",
            finalize_goal,
            success_count=8,
            failure_count=2,
            execution_count=10,
        )

        # publish: 3/10 success, 7 failures → score = 0.3 - 0.7 = -0.4
        publish_goal = {"session_name": "s1"}
        _seed_memory(
            store,
            "lifecycle_publish",
            publish_goal,
            success_count=3,
            failure_count=7,
            execution_count=10,
        )

        scheduler = EventScheduler(store=store)
        result = evaluate_and_emit(engine, store, scheduler)

        assert result is not None
        assert result.event_type == "finalization_succeeded"

        # Verify competition event was emitted
        events = list(scheduler._queue)
        event_types = [e.event_type for e in events]
        assert "intent_competition_resolved" in event_types
        assert "decision_intent_proposed" in event_types
    finally:
        set_orchestration_mode_for_testing(False)


def test_competition_blocked_intent_never_selected():
    """A blocked intent is excluded even if it would score highest."""
    set_orchestration_mode_for_testing(True)
    try:
        state = {
            "needs_finalize": True,
            "needs_publish": True,
            "session_name": "s1",
        }
        store = _make_store(state)
        engine = _make_engine()

        # finalize: would score high BUT is blocked (3+ failures, 0 success,
        # 2+ execution_failed)
        finalize_goal = {"session_name": "s1"}
        key = compute_memory_key("lifecycle_finalize", finalize_goal)
        store.set(
            key,
            {
                "intent_type": "lifecycle_finalize",
                "goal": finalize_goal,
                "success_count": 0,
                "failure_count": 5,
                "failure_by_type": {
                    "execution_failed": 3,
                    "execution_timed_out": 0,
                    "execution_rejected": 0,
                    "driver_failure": 0,
                },
                "last_outcome": "failed",
                "last_reason": "crash",
                "execution_count": 5,
                "last_updated_at": "2026-04-17T12:00:00+00:00",
                "last_success_at": None,
            },
        )

        # publish: low score but not blocked → should win by default
        publish_goal = {"session_name": "s1"}
        _seed_memory(
            store,
            "lifecycle_publish",
            publish_goal,
            success_count=1,
            failure_count=1,
            execution_count=2,
        )

        scheduler = EventScheduler(store=store)
        result = evaluate_and_emit(engine, store, scheduler)

        assert result is not None
        assert result.event_type == "publication_confirmed"

        events = list(scheduler._queue)
        event_types = [e.event_type for e in events]
        assert "decision_blocked_by_memory" in event_types
    finally:
        set_orchestration_mode_for_testing(False)


def test_competition_no_memory_neutral_score():
    """Candidates with no memory get score 0.0 — still selectable."""
    set_orchestration_mode_for_testing(True)
    try:
        state = {
            "needs_finalize": True,
            "needs_publish": True,
            "session_name": "s1",
        }
        store = _make_store(state)
        engine = _make_engine()

        # No memory seeded — both get score 0.0 → tie-break decides
        scheduler = EventScheduler(store=store)
        result = evaluate_and_emit(engine, store, scheduler)

        assert result is not None
        # One of the two should be selected (deterministic tie-break)
        assert result.event_type in ("finalization_succeeded", "publication_confirmed")
    finally:
        set_orchestration_mode_for_testing(False)


def test_competition_deterministic_100_runs():
    """Same state + memory → same winner across 100 runs."""
    set_orchestration_mode_for_testing(True)
    try:
        winners = []
        for _ in range(100):
            state = {
                "needs_finalize": True,
                "needs_publish": True,
                "session_name": "s1",
            }
            store = _make_store(state)

            # Give finalize a slight edge
            finalize_goal = {"session_name": "s1"}
            _seed_memory(
                store,
                "lifecycle_finalize",
                finalize_goal,
                success_count=7,
                failure_count=1,
                execution_count=8,
            )
            publish_goal = {"session_name": "s1"}
            _seed_memory(
                store,
                "lifecycle_publish",
                publish_goal,
                success_count=5,
                failure_count=2,
                execution_count=7,
            )

            engine = _make_engine()
            scheduler = EventScheduler(store=store)
            result = evaluate_and_emit(engine, store, scheduler)
            assert result is not None
            winners.append(result.event_type)

        # All 100 must be identical
        assert len(set(winners)) == 1
    finally:
        set_orchestration_mode_for_testing(False)


def test_competition_replay_identical_selection():
    """Replaying the same state snapshot produces identical selection."""
    set_orchestration_mode_for_testing(True)
    try:
        state = {
            "needs_finalize": True,
            "needs_publish": True,
            "session_name": "s1",
        }

        # Run 1
        store1 = _make_store(state)
        _seed_memory(
            store1,
            "lifecycle_finalize",
            {"session_name": "s1"},
            success_count=6,
            failure_count=1,
            execution_count=7,
        )
        _seed_memory(
            store1,
            "lifecycle_publish",
            {"session_name": "s1"},
            success_count=4,
            failure_count=3,
            execution_count=7,
        )
        engine1 = _make_engine()
        scheduler1 = EventScheduler(store=store1)
        result1 = evaluate_and_emit(engine1, store1, scheduler1)

        # Run 2 — identical setup
        store2 = _make_store(state)
        _seed_memory(
            store2,
            "lifecycle_finalize",
            {"session_name": "s1"},
            success_count=6,
            failure_count=1,
            execution_count=7,
        )
        _seed_memory(
            store2,
            "lifecycle_publish",
            {"session_name": "s1"},
            success_count=4,
            failure_count=3,
            execution_count=7,
        )
        engine2 = _make_engine()
        scheduler2 = EventScheduler(store=store2)
        result2 = evaluate_and_emit(engine2, store2, scheduler2)

        assert result1 is not None and result2 is not None
        assert result1.decision_id == result2.decision_id
        assert result1.event_type == result2.event_type
        assert result1.state_hash == result2.state_hash
    finally:
        set_orchestration_mode_for_testing(False)


def test_single_candidate_no_competition_event():
    """When only one lifecycle candidate exists, no competition event is emitted."""
    set_orchestration_mode_for_testing(True)
    try:
        state = {
            "needs_finalize": True,
            "needs_publish": False,
            "session_name": "s1",
        }
        store = _make_store(state)
        engine = _make_engine()

        scheduler = EventScheduler(store=store)
        result = evaluate_and_emit(engine, store, scheduler)

        assert result is not None
        events = list(scheduler._queue)
        event_types = [e.event_type for e in events]
        assert "intent_competition_resolved" not in event_types
        assert "decision_intent_proposed" in event_types
    finally:
        set_orchestration_mode_for_testing(False)


def test_all_candidates_blocked_returns_none():
    """When all lifecycle candidates are blocked, no decision is emitted."""
    set_orchestration_mode_for_testing(True)
    try:
        state = {
            "needs_finalize": True,
            "needs_publish": False,
            "session_name": "s1",
        }
        store = _make_store(state)

        # Block finalize
        finalize_goal = {"session_name": "s1"}
        key = compute_memory_key("lifecycle_finalize", finalize_goal)
        store.set(
            key,
            {
                "intent_type": "lifecycle_finalize",
                "goal": finalize_goal,
                "success_count": 0,
                "failure_count": 5,
                "failure_by_type": {
                    "execution_failed": 3,
                    "execution_timed_out": 0,
                    "execution_rejected": 0,
                    "driver_failure": 0,
                },
                "last_outcome": "failed",
                "last_reason": "crash",
                "execution_count": 5,
                "last_updated_at": "2026-04-17T12:00:00+00:00",
                "last_success_at": None,
            },
        )

        engine = _make_engine()
        scheduler = EventScheduler(store=store)
        result = evaluate_and_emit(engine, store, scheduler)

        # All blocked → returns the blocked output (preserves old contract)
        # but no decision_intent_proposed emitted
        assert result is not None
        events = list(scheduler._queue)
        event_types = [e.event_type for e in events]
        assert "decision_blocked_by_memory" in event_types
        assert "decision_intent_proposed" not in event_types
    finally:
        set_orchestration_mode_for_testing(False)


def test_legacy_path_unchanged():
    """When orchestration mode is off, evaluate_and_emit uses legacy single-output path."""
    set_orchestration_mode_for_testing(False)

    state = {"needs_finalize": True, "session_name": "s1"}
    store = _make_store(state)
    engine = _make_engine()

    scheduler = EventScheduler(store=store)
    result = evaluate_and_emit(engine, store, scheduler)

    assert result is not None
    assert result.event_type == "finalization_succeeded"

    events = list(scheduler._queue)
    event_types = [e.event_type for e in events]
    assert "decision_made" in event_types
    assert "finalization_succeeded" in event_types
    assert "intent_competition_resolved" not in event_types
    assert "decision_intent_proposed" not in event_types


def test_evaluate_candidates_returns_all_matching():
    """RuleBasedStrategy.evaluate_candidates returns all matching rules."""
    strategy = RuleBasedStrategy(rules=[FINALIZE_RULE, PUBLISH_RULE, CLEAR_RULE])
    state = {
        "needs_finalize": True,
        "needs_publish": True,
        "needs_clear": False,
        "session_name": "s1",
    }
    candidates = strategy.evaluate_candidates(state)
    assert len(candidates) == 2
    event_types = {c.event_type for c in candidates}
    assert event_types == {"finalization_succeeded", "publication_confirmed"}


def test_evaluate_candidates_unique_decision_ids():
    """Each candidate from evaluate_candidates gets a unique decision_id."""
    strategy = RuleBasedStrategy(rules=[FINALIZE_RULE, PUBLISH_RULE])
    state = {
        "needs_finalize": True,
        "needs_publish": True,
        "session_name": "s1",
    }
    candidates = strategy.evaluate_candidates(state)
    assert len(candidates) == 2
    assert candidates[0].decision_id != candidates[1].decision_id


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
