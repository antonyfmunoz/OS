"""Phase 50 — Outcome Memory + Execution Feedback Bridge v1.

160+ tests covering:
- Outcome model defaults and clamping
- OutcomeStatus enum
- DecisionOutcomeLink
- StrategyStats computation
- StrategyPerformanceSignal
- OutcomeMemory append-only
- OutcomeMemory query by strategy/state
- OutcomeMemory stats computation
- OutcomeMemory feedback factor
- FeedbackBridge record and link
- FeedbackBridge explanation
- FeedbackBridge summary
- Append-only invariant
- Immutability invariant
- No execution invariant
- Graceful degradation with missing data
- Pipeline integration
- Serialization
- Edge cases
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.runtime.outcome import (
    DecisionOutcomeLink,
    OutcomeStatus,
    StrategyOutcome,
    StrategyPerformanceSignal,
    StrategyStats,
)
from umh.runtime.outcome_memory import OutcomeMemory
from umh.runtime.feedback_bridge import FeedbackBridge, FeedbackRecord


def _make_outcome(
    outcome_id: str = "o1",
    decision_id: str = "d1",
    action_name: str = "act",
    strategy_name: str = "aggressive",
    state_signature: str = "state_a",
    status: OutcomeStatus = OutcomeStatus.SUCCESS,
    success_score: float = 0.8,
    latency: float = 1.0,
    effort: float = 0.5,
    error_count: int = 0,
) -> StrategyOutcome:
    return StrategyOutcome(
        outcome_id=outcome_id,
        decision_id=decision_id,
        action_name=action_name,
        strategy_name=strategy_name,
        state_signature=state_signature,
        status=status,
        success_score=success_score,
        latency=latency,
        effort=effort,
        error_count=error_count,
    )


# ── Section 1: OutcomeStatus enum ────────────────────────────────────


class TestOutcomeStatus:
    def test_success(self):
        assert OutcomeStatus.SUCCESS.value == "success"

    def test_failure(self):
        assert OutcomeStatus.FAILURE.value == "failure"

    def test_partial(self):
        assert OutcomeStatus.PARTIAL.value == "partial"

    def test_unknown(self):
        assert OutcomeStatus.UNKNOWN.value == "unknown"

    def test_four_members(self):
        assert len(OutcomeStatus) == 4


# ── Section 2: StrategyOutcome defaults ──────────────────────────────


class TestOutcomeDefaults:
    def test_default_status_unknown(self):
        o = StrategyOutcome(
            outcome_id="x",
            decision_id="d",
            action_name="a",
            strategy_name="s",
            state_signature="st",
        )
        assert o.status == OutcomeStatus.UNKNOWN

    def test_default_success_score_zero(self):
        o = StrategyOutcome(
            outcome_id="x",
            decision_id="d",
            action_name="a",
            strategy_name="s",
            state_signature="st",
        )
        assert o.success_score == 0.0

    def test_default_latency_zero(self):
        o = StrategyOutcome(
            outcome_id="x",
            decision_id="d",
            action_name="a",
            strategy_name="s",
            state_signature="st",
        )
        assert o.latency == 0.0

    def test_default_effort_zero(self):
        o = StrategyOutcome(
            outcome_id="x",
            decision_id="d",
            action_name="a",
            strategy_name="s",
            state_signature="st",
        )
        assert o.effort == 0.0

    def test_default_error_count_zero(self):
        o = StrategyOutcome(
            outcome_id="x",
            decision_id="d",
            action_name="a",
            strategy_name="s",
            state_signature="st",
        )
        assert o.error_count == 0

    def test_timestamp_auto_set(self):
        o = _make_outcome()
        assert o.timestamp != ""


# ── Section 3: StrategyOutcome clamping ──────────────────────────────


class TestOutcomeClamping:
    def test_success_score_clamp_high(self):
        o = _make_outcome(success_score=2.0)
        assert o.success_score == 1.0

    def test_success_score_clamp_low(self):
        o = _make_outcome(success_score=-0.5)
        assert o.success_score == 0.0

    def test_latency_clamp_negative(self):
        o = _make_outcome(latency=-10.0)
        assert o.latency == 0.0

    def test_effort_clamp_high(self):
        o = _make_outcome(effort=5.0)
        assert o.effort == 1.0

    def test_effort_clamp_low(self):
        o = _make_outcome(effort=-1.0)
        assert o.effort == 0.0

    def test_error_count_clamp_negative(self):
        o = _make_outcome(error_count=-5)
        assert o.error_count == 0

    def test_valid_values_unchanged(self):
        o = _make_outcome(success_score=0.5, latency=2.0, effort=0.3, error_count=2)
        assert o.success_score == 0.5
        assert o.latency == 2.0
        assert o.effort == 0.3
        assert o.error_count == 2


# ── Section 4: StrategyOutcome frozen ────────────────────────────────


class TestOutcomeFrozen:
    def test_cannot_set_status(self):
        o = _make_outcome()
        with pytest.raises(AttributeError):
            o.status = OutcomeStatus.FAILURE

    def test_cannot_set_score(self):
        o = _make_outcome()
        with pytest.raises(AttributeError):
            o.success_score = 0.9

    def test_cannot_set_outcome_id(self):
        o = _make_outcome()
        with pytest.raises(AttributeError):
            o.outcome_id = "new"


# ── Section 5: StrategyOutcome to_dict ───────────────────────────────


class TestOutcomeToDict:
    def test_keys(self):
        o = _make_outcome()
        d = o.to_dict()
        expected = {
            "outcome_id",
            "decision_id",
            "action_name",
            "strategy_name",
            "state_signature",
            "status",
            "success_score",
            "latency",
            "effort",
            "error_count",
            "timestamp",
            "metadata",
        }
        assert set(d.keys()) == expected

    def test_status_is_string(self):
        o = _make_outcome(status=OutcomeStatus.SUCCESS)
        d = o.to_dict()
        assert d["status"] == "success"

    def test_values_match(self):
        o = _make_outcome(success_score=0.75, error_count=3)
        d = o.to_dict()
        assert d["success_score"] == 0.75
        assert d["error_count"] == 3


# ── Section 6: DecisionOutcomeLink ───────────────────────────────────


class TestDecisionOutcomeLink:
    def test_creation(self):
        link = DecisionOutcomeLink(
            state_signature="st",
            decision_id="d1",
            strategy_name="aggressive",
            objective_id="obj1",
            outcome_id="o1",
        )
        assert link.state_signature == "st"
        assert link.decision_id == "d1"
        assert link.strategy_name == "aggressive"
        assert link.objective_id == "obj1"
        assert link.outcome_id == "o1"

    def test_frozen(self):
        link = DecisionOutcomeLink(
            state_signature="st",
            decision_id="d1",
            strategy_name="aggressive",
            objective_id="obj1",
            outcome_id="o1",
        )
        with pytest.raises(AttributeError):
            link.state_signature = "new"

    def test_to_dict(self):
        link = DecisionOutcomeLink(
            state_signature="st",
            decision_id="d1",
            strategy_name="aggressive",
            objective_id="obj1",
            outcome_id="o1",
        )
        d = link.to_dict()
        assert d["state_signature"] == "st"
        assert d["outcome_id"] == "o1"

    def test_to_dict_keys(self):
        link = DecisionOutcomeLink(
            state_signature="st",
            decision_id="d1",
            strategy_name="aggressive",
            objective_id="obj1",
            outcome_id="o1",
        )
        d = link.to_dict()
        assert set(d.keys()) == {
            "state_signature",
            "decision_id",
            "strategy_name",
            "objective_id",
            "outcome_id",
        }


# ── Section 7: StrategyStats ────────────────────────────────────────


class TestStrategyStats:
    def test_success_rate_with_data(self):
        stats = StrategyStats(
            strategy_name="aggressive",
            total_count=10,
            success_count=7,
            failure_count=2,
            partial_count=1,
            unknown_count=0,
            average_success_score=0.7,
            average_latency=1.0,
            average_effort=0.5,
        )
        assert stats.success_rate == 0.7

    def test_success_rate_empty(self):
        stats = StrategyStats(
            strategy_name="aggressive",
            total_count=0,
            success_count=0,
            failure_count=0,
            partial_count=0,
            unknown_count=0,
            average_success_score=0.0,
            average_latency=0.0,
            average_effort=0.0,
        )
        assert stats.success_rate == 0.0

    def test_to_dict_has_success_rate(self):
        stats = StrategyStats(
            strategy_name="x",
            total_count=4,
            success_count=3,
            failure_count=1,
            partial_count=0,
            unknown_count=0,
            average_success_score=0.75,
            average_latency=0.5,
            average_effort=0.3,
        )
        d = stats.to_dict()
        assert d["success_rate"] == 0.75

    def test_frozen(self):
        stats = StrategyStats(
            strategy_name="x",
            total_count=1,
            success_count=1,
            failure_count=0,
            partial_count=0,
            unknown_count=0,
            average_success_score=1.0,
            average_latency=0.1,
            average_effort=0.1,
        )
        with pytest.raises(AttributeError):
            stats.total_count = 99


# ── Section 8: StrategyPerformanceSignal ─────────────────────────────


class TestPerformanceSignal:
    def test_creation(self):
        sig = StrategyPerformanceSignal(
            strategy_name="aggressive",
            sample_size=5,
            success_rate=0.8,
            average_score=0.75,
            confidence=0.5,
        )
        assert sig.strategy_name == "aggressive"
        assert sig.confidence == 0.5

    def test_frozen(self):
        sig = StrategyPerformanceSignal(
            strategy_name="x",
            sample_size=10,
            success_rate=1.0,
            average_score=1.0,
            confidence=1.0,
        )
        with pytest.raises(AttributeError):
            sig.confidence = 0.0

    def test_to_dict(self):
        sig = StrategyPerformanceSignal(
            strategy_name="x",
            sample_size=5,
            success_rate=0.6,
            average_score=0.55,
            confidence=0.5,
        )
        d = sig.to_dict()
        assert d["sample_size"] == 5
        assert d["confidence"] == 0.5


# ── Section 9: OutcomeMemory append ──────────────────────────────────


class TestMemoryAppend:
    def test_empty_count(self):
        mem = OutcomeMemory()
        assert mem.count == 0

    def test_append_increments_count(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome())
        assert mem.count == 1

    def test_append_multiple(self):
        mem = OutcomeMemory()
        for i in range(5):
            mem.append(_make_outcome(outcome_id=f"o{i}"))
        assert mem.count == 5

    def test_list_outcomes_returns_all(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(outcome_id="a"))
        mem.append(_make_outcome(outcome_id="b"))
        outcomes = mem.list_outcomes()
        assert len(outcomes) == 2
        assert outcomes[0].outcome_id == "a"
        assert outcomes[1].outcome_id == "b"

    def test_list_outcomes_returns_copy(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome())
        lst = mem.list_outcomes()
        lst.clear()
        assert mem.count == 1


# ── Section 10: OutcomeMemory append-only (invariant 186) ────────────


class TestAppendOnly:
    def test_no_remove_method(self):
        mem = OutcomeMemory()
        assert not hasattr(mem, "remove")

    def test_no_delete_method(self):
        mem = OutcomeMemory()
        assert not hasattr(mem, "delete")

    def test_no_clear_method(self):
        mem = OutcomeMemory()
        assert not hasattr(mem, "clear")

    def test_no_pop_method(self):
        mem = OutcomeMemory()
        assert not hasattr(mem, "pop")

    def test_internal_list_not_exposed(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome())
        outcomes = mem.list_outcomes()
        assert outcomes is not mem._outcomes


# ── Section 11: OutcomeMemory query by strategy ──────────────────────


class TestQueryByStrategy:
    def test_query_empty(self):
        mem = OutcomeMemory()
        assert mem.query_by_strategy("aggressive") == []

    def test_query_filters(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(strategy_name="aggressive"))
        mem.append(_make_outcome(strategy_name="conservative"))
        mem.append(_make_outcome(strategy_name="aggressive", outcome_id="o2"))
        results = mem.query_by_strategy("aggressive")
        assert len(results) == 2

    def test_query_no_match(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(strategy_name="aggressive"))
        assert mem.query_by_strategy("balanced") == []


# ── Section 12: OutcomeMemory query by state ─────────────────────────


class TestQueryByState:
    def test_query_empty(self):
        mem = OutcomeMemory()
        assert mem.query_by_state("state_a") == []

    def test_query_filters(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(state_signature="state_a"))
        mem.append(_make_outcome(state_signature="state_b"))
        mem.append(_make_outcome(state_signature="state_a", outcome_id="o2"))
        results = mem.query_by_state("state_a")
        assert len(results) == 2

    def test_query_by_state_and_strategy(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(state_signature="sa", strategy_name="agg"))
        mem.append(_make_outcome(state_signature="sa", strategy_name="con", outcome_id="o2"))
        mem.append(_make_outcome(state_signature="sb", strategy_name="agg", outcome_id="o3"))
        results = mem.query_by_state_and_strategy("sa", "agg")
        assert len(results) == 1


# ── Section 13: OutcomeMemory stats computation ─────────────────────


class TestStatsComputation:
    def test_empty_stats(self):
        mem = OutcomeMemory()
        stats = mem.compute_strategy_stats("aggressive")
        assert stats.total_count == 0
        assert stats.success_count == 0
        assert stats.average_success_score == 0.0

    def test_success_count(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(status=OutcomeStatus.SUCCESS, outcome_id="o1"))
        mem.append(_make_outcome(status=OutcomeStatus.SUCCESS, outcome_id="o2"))
        mem.append(_make_outcome(status=OutcomeStatus.FAILURE, outcome_id="o3"))
        stats = mem.compute_strategy_stats("aggressive")
        assert stats.success_count == 2
        assert stats.failure_count == 1

    def test_partial_count(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(status=OutcomeStatus.PARTIAL))
        stats = mem.compute_strategy_stats("aggressive")
        assert stats.partial_count == 1

    def test_unknown_count(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(status=OutcomeStatus.UNKNOWN))
        stats = mem.compute_strategy_stats("aggressive")
        assert stats.unknown_count == 1

    def test_average_success_score(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(success_score=0.6, outcome_id="o1"))
        mem.append(_make_outcome(success_score=0.8, outcome_id="o2"))
        stats = mem.compute_strategy_stats("aggressive")
        assert abs(stats.average_success_score - 0.7) < 1e-9

    def test_average_latency(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(latency=1.0, outcome_id="o1"))
        mem.append(_make_outcome(latency=3.0, outcome_id="o2"))
        stats = mem.compute_strategy_stats("aggressive")
        assert abs(stats.average_latency - 2.0) < 1e-9

    def test_average_effort(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(effort=0.2, outcome_id="o1"))
        mem.append(_make_outcome(effort=0.8, outcome_id="o2"))
        stats = mem.compute_strategy_stats("aggressive")
        assert abs(stats.average_effort - 0.5) < 1e-9

    def test_state_strategy_stats(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(state_signature="sa", strategy_name="agg", outcome_id="o1"))
        mem.append(
            _make_outcome(
                state_signature="sa",
                strategy_name="agg",
                outcome_id="o2",
                status=OutcomeStatus.FAILURE,
            )
        )
        mem.append(_make_outcome(state_signature="sb", strategy_name="agg", outcome_id="o3"))
        stats = mem.compute_state_strategy_stats("sa", "agg")
        assert stats.total_count == 2
        assert stats.success_count == 1
        assert stats.failure_count == 1

    def test_success_rate_computed(self):
        mem = OutcomeMemory()
        for i in range(7):
            mem.append(_make_outcome(status=OutcomeStatus.SUCCESS, outcome_id=f"s{i}"))
        for i in range(3):
            mem.append(_make_outcome(status=OutcomeStatus.FAILURE, outcome_id=f"f{i}"))
        stats = mem.compute_strategy_stats("aggressive")
        assert abs(stats.success_rate - 0.7) < 1e-9


# ── Section 14: OutcomeMemory performance signal ─────────────────────


class TestPerformanceSignalComputation:
    def test_empty_signal(self):
        mem = OutcomeMemory()
        sig = mem.get_performance_signal("aggressive")
        assert sig.sample_size == 0
        assert sig.confidence == 0.0

    def test_partial_confidence(self):
        mem = OutcomeMemory()
        for i in range(5):
            mem.append(_make_outcome(outcome_id=f"o{i}"))
        sig = mem.get_performance_signal("aggressive")
        assert sig.confidence == 0.5

    def test_full_confidence(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(_make_outcome(outcome_id=f"o{i}"))
        sig = mem.get_performance_signal("aggressive")
        assert sig.confidence == 1.0

    def test_over_required_confidence_capped(self):
        mem = OutcomeMemory()
        for i in range(20):
            mem.append(_make_outcome(outcome_id=f"o{i}"))
        sig = mem.get_performance_signal("aggressive")
        assert sig.confidence == 1.0

    def test_custom_required_samples(self):
        mem = OutcomeMemory(required_samples=5)
        for i in range(5):
            mem.append(_make_outcome(outcome_id=f"o{i}"))
        sig = mem.get_performance_signal("aggressive")
        assert sig.confidence == 1.0


# ── Section 15: Feedback factor ──────────────────────────────────────


class TestFeedbackFactor:
    def test_insufficient_data_neutral(self):
        mem = OutcomeMemory()
        for i in range(5):
            mem.append(_make_outcome(outcome_id=f"o{i}"))
        factor = mem.get_strategy_feedback_factor("aggressive")
        assert factor == 1.0

    def test_strong_positive_boosts(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(_make_outcome(outcome_id=f"o{i}", success_score=0.9))
        factor = mem.get_strategy_feedback_factor("aggressive")
        assert factor > 1.0
        assert factor <= 1.10

    def test_poor_history_suppresses(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(_make_outcome(outcome_id=f"o{i}", success_score=0.1))
        factor = mem.get_strategy_feedback_factor("aggressive")
        assert factor < 1.0
        assert factor >= 0.90

    def test_clamp_upper(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(_make_outcome(outcome_id=f"o{i}", success_score=1.0))
        factor = mem.get_strategy_feedback_factor("aggressive")
        assert factor <= 1.10

    def test_clamp_lower(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(_make_outcome(outcome_id=f"o{i}", success_score=0.0))
        factor = mem.get_strategy_feedback_factor("aggressive")
        assert factor >= 0.90

    def test_neutral_score_neutral_factor(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(_make_outcome(outcome_id=f"o{i}", success_score=0.5))
        factor = mem.get_strategy_feedback_factor("aggressive")
        assert factor == 1.0

    def test_state_specific_factor(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(
                _make_outcome(
                    outcome_id=f"o{i}",
                    success_score=0.9,
                    state_signature="sa",
                )
            )
        for i in range(10):
            mem.append(
                _make_outcome(
                    outcome_id=f"p{i}",
                    success_score=0.1,
                    state_signature="sb",
                )
            )
        factor_a = mem.get_strategy_feedback_factor("aggressive", "sa")
        factor_b = mem.get_strategy_feedback_factor("aggressive", "sb")
        assert factor_a > 1.0
        assert factor_b < 1.0

    def test_empty_memory_neutral(self):
        mem = OutcomeMemory()
        factor = mem.get_strategy_feedback_factor("aggressive")
        assert factor == 1.0


# ── Section 16: FeedbackBridge record ────────────────────────────────


class TestFeedbackBridgeRecord:
    def test_record_returns_feedback(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        outcome = _make_outcome()
        fb = bridge.record_outcome(outcome, objective_id="obj1")
        assert isinstance(fb, FeedbackRecord)

    def test_record_creates_link(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        outcome = _make_outcome()
        fb = bridge.record_outcome(outcome, objective_id="obj1")
        assert fb.link.outcome_id == "o1"
        assert fb.link.decision_id == "d1"
        assert fb.link.objective_id == "obj1"

    def test_record_appends_to_memory(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        bridge.record_outcome(_make_outcome())
        assert mem.count == 1

    def test_record_increments_link_count(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        bridge.record_outcome(_make_outcome())
        bridge.record_outcome(_make_outcome(outcome_id="o2"))
        assert bridge.link_count == 2

    def test_record_returns_stats(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        outcome = _make_outcome()
        fb = bridge.record_outcome(outcome)
        assert fb.strategy_stats.total_count == 1
        assert fb.state_strategy_stats.total_count == 1


# ── Section 17: FeedbackBridge link queries ──────────────────────────


class TestFeedbackBridgeLinks:
    def test_get_links(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        bridge.record_outcome(_make_outcome())
        bridge.record_outcome(_make_outcome(outcome_id="o2"))
        links = bridge.get_links()
        assert len(links) == 2

    def test_get_links_returns_copy(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        bridge.record_outcome(_make_outcome())
        links = bridge.get_links()
        links.clear()
        assert bridge.link_count == 1

    def test_get_links_for_strategy(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        bridge.record_outcome(_make_outcome(strategy_name="agg"))
        bridge.record_outcome(_make_outcome(strategy_name="con", outcome_id="o2"))
        assert len(bridge.get_links_for_strategy("agg")) == 1

    def test_get_links_for_state(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        bridge.record_outcome(_make_outcome(state_signature="sa"))
        bridge.record_outcome(_make_outcome(state_signature="sb", outcome_id="o2"))
        assert len(bridge.get_links_for_state("sa")) == 1


# ── Section 18: FeedbackBridge explanation ───────────────────────────


class TestFeedbackExplanation:
    def test_explanation_contains_strategy(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        fb = bridge.record_outcome(_make_outcome(strategy_name="aggressive"))
        assert "aggressive" in fb.explanation

    def test_explanation_contains_status(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        fb = bridge.record_outcome(_make_outcome(status=OutcomeStatus.SUCCESS))
        assert "success" in fb.explanation

    def test_explanation_contains_score(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        fb = bridge.record_outcome(_make_outcome(success_score=0.80))
        assert "0.80" in fb.explanation

    def test_explanation_contains_state(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        fb = bridge.record_outcome(_make_outcome(state_signature="state_a"))
        assert "state_a" in fb.explanation

    def test_explanation_first_has_count(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        fb = bridge.record_outcome(_make_outcome())
        assert "1 execution" in fb.explanation

    def test_explanation_mentions_confidence(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        fb = bridge.record_outcome(_make_outcome())
        assert "Confidence" in fb.explanation

    def test_explanation_low_confidence_when_few(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        fb = bridge.record_outcome(_make_outcome())
        assert "LOW" in fb.explanation

    def test_explanation_sufficient_when_many(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        for i in range(10):
            bridge.record_outcome(_make_outcome(outcome_id=f"o{i}"))
        fb = bridge.record_outcome(_make_outcome(outcome_id="o10"))
        assert "sufficient" in fb.explanation


# ── Section 19: FeedbackBridge summary ───────────────────────────────


class TestFeedbackSummary:
    def test_summary_structure(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        bridge.record_outcome(_make_outcome())
        s = bridge.get_feedback_summary("aggressive")
        assert "strategy_name" in s
        assert "stats" in s
        assert "performance_signal" in s
        assert "feedback_factor" in s

    def test_summary_strategy_name(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        bridge.record_outcome(_make_outcome())
        s = bridge.get_feedback_summary("aggressive")
        assert s["strategy_name"] == "aggressive"

    def test_summary_empty(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        s = bridge.get_feedback_summary("unknown")
        assert s["stats"]["total_count"] == 0
        assert s["feedback_factor"] == 1.0


# ── Section 20: FeedbackBridge to_dict ───────────────────────────────


class TestFeedbackBridgeDict:
    def test_to_dict_empty(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        d = bridge.to_dict()
        assert d["link_count"] == 0
        assert d["outcome_count"] == 0
        assert d["strategies"] == []

    def test_to_dict_populated(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        bridge.record_outcome(_make_outcome(strategy_name="agg"))
        bridge.record_outcome(_make_outcome(strategy_name="con", outcome_id="o2"))
        d = bridge.to_dict()
        assert d["link_count"] == 2
        assert d["outcome_count"] == 2
        assert "agg" in d["strategies"]
        assert "con" in d["strategies"]


# ── Section 21: FeedbackRecord frozen ────────────────────────────────


class TestFeedbackRecordFrozen:
    def test_cannot_set_link(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        fb = bridge.record_outcome(_make_outcome())
        with pytest.raises(AttributeError):
            fb.link = None

    def test_cannot_set_explanation(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        fb = bridge.record_outcome(_make_outcome())
        with pytest.raises(AttributeError):
            fb.explanation = "new"


# ── Section 22: FeedbackRecord to_dict ───────────────────────────────


class TestFeedbackRecordDict:
    def test_keys(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        fb = bridge.record_outcome(_make_outcome())
        d = fb.to_dict()
        assert set(d.keys()) == {
            "link",
            "outcome",
            "strategy_stats",
            "state_strategy_stats",
            "explanation",
        }


# ── Section 23: Historical immutability (invariant 187) ──────────────


class TestHistoricalImmutability:
    def test_outcome_in_memory_not_mutable(self):
        mem = OutcomeMemory()
        outcome = _make_outcome()
        mem.append(outcome)
        retrieved = mem.list_outcomes()[0]
        with pytest.raises(AttributeError):
            retrieved.success_score = 0.99

    def test_original_not_affected_by_append(self):
        outcome = _make_outcome(success_score=0.5)
        before = outcome.to_dict()
        mem = OutcomeMemory()
        mem.append(outcome)
        mem.append(_make_outcome(outcome_id="o2", success_score=0.9))
        after = outcome.to_dict()
        assert before == after

    def test_stats_frozen(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome())
        stats = mem.compute_strategy_stats("aggressive")
        with pytest.raises(AttributeError):
            stats.total_count = 99


# ── Section 24: No execution (invariant 188) ────────────────────────


class TestNoExecution:
    def test_bridge_has_no_execute(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        assert not hasattr(bridge, "execute")

    def test_bridge_has_no_run(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        assert not hasattr(bridge, "run")

    def test_bridge_has_no_dispatch(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        assert not hasattr(bridge, "dispatch")

    def test_no_subprocess_in_bridge(self):
        import umh.runtime.feedback_bridge as fb_mod

        source = open(fb_mod.__file__).read()
        assert "import subprocess" not in source

    def test_no_subprocess_in_outcome(self):
        import umh.runtime.outcome as o_mod

        source = open(o_mod.__file__).read()
        assert "import subprocess" not in source

    def test_no_subprocess_in_memory(self):
        import umh.runtime.outcome_memory as om_mod

        source = open(om_mod.__file__).read()
        assert "import subprocess" not in source


# ── Section 25: State → decision → result linkage (invariant 189) ────


class TestLinkageInvariant:
    def test_link_captures_state(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        fb = bridge.record_outcome(
            _make_outcome(state_signature="my_state"),
            objective_id="obj1",
        )
        assert fb.link.state_signature == "my_state"

    def test_link_captures_decision(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        fb = bridge.record_outcome(_make_outcome(decision_id="dec_42"))
        assert fb.link.decision_id == "dec_42"

    def test_link_captures_outcome(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        fb = bridge.record_outcome(_make_outcome(outcome_id="out_99"))
        assert fb.link.outcome_id == "out_99"

    def test_link_captures_strategy(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        fb = bridge.record_outcome(_make_outcome(strategy_name="recovery"))
        assert fb.link.strategy_name == "recovery"


# ── Section 26: Graceful degradation (invariant 190) ────────────────


class TestGracefulDegradation:
    def test_empty_memory_stats(self):
        mem = OutcomeMemory()
        stats = mem.compute_strategy_stats("nonexistent")
        assert stats.total_count == 0
        assert stats.average_success_score == 0.0

    def test_empty_memory_factor(self):
        mem = OutcomeMemory()
        factor = mem.get_strategy_feedback_factor("nonexistent")
        assert factor == 1.0

    def test_empty_memory_signal(self):
        mem = OutcomeMemory()
        sig = mem.get_performance_signal("nonexistent")
        assert sig.sample_size == 0
        assert sig.confidence == 0.0

    def test_empty_bridge_summary(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        s = bridge.get_feedback_summary("nonexistent")
        assert s["stats"]["total_count"] == 0

    def test_query_missing_strategy(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(strategy_name="agg"))
        assert mem.query_by_strategy("nonexistent") == []

    def test_query_missing_state(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(state_signature="sa"))
        assert mem.query_by_state("nonexistent") == []


# ── Section 27: Determinism (invariant 186 extended) ────────────────


class TestDeterminism:
    def test_same_sequence_same_stats(self):
        def run():
            mem = OutcomeMemory()
            for i in range(10):
                mem.append(
                    _make_outcome(
                        outcome_id=f"o{i}",
                        success_score=i * 0.1,
                        status=OutcomeStatus.SUCCESS if i % 2 == 0 else OutcomeStatus.FAILURE,
                    )
                )
            return mem.compute_strategy_stats("aggressive")

        s1 = run()
        s2 = run()
        assert s1.total_count == s2.total_count
        assert s1.success_count == s2.success_count
        assert abs(s1.average_success_score - s2.average_success_score) < 1e-9

    def test_same_sequence_same_factor(self):
        def run():
            mem = OutcomeMemory()
            for i in range(10):
                mem.append(_make_outcome(outcome_id=f"o{i}", success_score=0.8))
            return mem.get_strategy_feedback_factor("aggressive")

        assert run() == run()


# ── Section 28: OutcomeMemory list_strategies ────────────────────────


class TestListStrategies:
    def test_empty(self):
        mem = OutcomeMemory()
        assert mem.list_strategies() == []

    def test_unique_strategies(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(strategy_name="agg", outcome_id="o1"))
        mem.append(_make_outcome(strategy_name="con", outcome_id="o2"))
        mem.append(_make_outcome(strategy_name="agg", outcome_id="o3"))
        strategies = mem.list_strategies()
        assert strategies == ["agg", "con"]

    def test_preserves_order(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(strategy_name="z", outcome_id="o1"))
        mem.append(_make_outcome(strategy_name="a", outcome_id="o2"))
        mem.append(_make_outcome(strategy_name="m", outcome_id="o3"))
        assert mem.list_strategies() == ["z", "a", "m"]


# ── Section 29: OutcomeMemory to_dict ────────────────────────────────


class TestMemoryToDict:
    def test_empty_dict(self):
        mem = OutcomeMemory()
        d = mem.to_dict()
        assert d["count"] == 0
        assert d["required_samples"] == 10
        assert d["strategies"] == []

    def test_populated_dict(self):
        mem = OutcomeMemory(required_samples=5)
        mem.append(_make_outcome(strategy_name="agg"))
        d = mem.to_dict()
        assert d["count"] == 1
        assert d["required_samples"] == 5
        assert d["strategies"] == ["agg"]


# ── Section 30: Import surface ───────────────────────────────────────


class TestImportSurface:
    def test_all_public_importable(self):
        from umh.runtime import (
            DecisionOutcomeLink,
            FeedbackBridge,
            FeedbackRecord,
            OutcomeMemory,
            OutcomeStatus,
            StrategyOutcome,
            StrategyPerformanceSignal,
            StrategyStats,
        )

        assert DecisionOutcomeLink is not None
        assert FeedbackBridge is not None
        assert FeedbackRecord is not None
        assert OutcomeMemory is not None
        assert OutcomeStatus is not None
        assert StrategyOutcome is not None
        assert StrategyPerformanceSignal is not None
        assert StrategyStats is not None


# ── Section 31: Edge cases ───────────────────────────────────────────


class TestEdgeCases:
    def test_metadata_dict(self):
        o = _make_outcome()
        assert isinstance(o.metadata, dict)

    def test_metadata_in_to_dict(self):
        o = StrategyOutcome(
            outcome_id="x",
            decision_id="d",
            action_name="a",
            strategy_name="s",
            state_signature="st",
            metadata={"key": "val"},
        )
        d = o.to_dict()
        assert d["metadata"] == {"key": "val"}

    def test_required_samples_minimum_one(self):
        mem = OutcomeMemory(required_samples=0)
        assert mem.required_samples == 1

    def test_required_samples_negative(self):
        mem = OutcomeMemory(required_samples=-5)
        assert mem.required_samples == 1

    def test_very_high_latency(self):
        o = _make_outcome(latency=99999.0)
        assert o.latency == 99999.0

    def test_zero_score_zero_effort(self):
        o = _make_outcome(success_score=0.0, effort=0.0)
        assert o.success_score == 0.0
        assert o.effort == 0.0


# ── Section 32: Multi-strategy interaction ───────────────────────────


class TestMultiStrategy:
    def test_independent_stats(self):
        mem = OutcomeMemory()
        for i in range(5):
            mem.append(
                _make_outcome(
                    outcome_id=f"a{i}",
                    strategy_name="agg",
                    status=OutcomeStatus.SUCCESS,
                    success_score=0.9,
                )
            )
        for i in range(5):
            mem.append(
                _make_outcome(
                    outcome_id=f"c{i}",
                    strategy_name="con",
                    status=OutcomeStatus.FAILURE,
                    success_score=0.2,
                )
            )
        agg_stats = mem.compute_strategy_stats("agg")
        con_stats = mem.compute_strategy_stats("con")
        assert agg_stats.success_count == 5
        assert con_stats.failure_count == 5
        assert agg_stats.average_success_score > con_stats.average_success_score

    def test_independent_factors(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(
                _make_outcome(
                    outcome_id=f"a{i}",
                    strategy_name="agg",
                    success_score=0.9,
                )
            )
        for i in range(10):
            mem.append(
                _make_outcome(
                    outcome_id=f"c{i}",
                    strategy_name="con",
                    success_score=0.1,
                )
            )
        assert mem.get_strategy_feedback_factor("agg") > 1.0
        assert mem.get_strategy_feedback_factor("con") < 1.0

    def test_independent_signals(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(
                _make_outcome(
                    outcome_id=f"a{i}",
                    strategy_name="agg",
                    success_score=0.9,
                )
            )
        sig_agg = mem.get_performance_signal("agg")
        sig_con = mem.get_performance_signal("con")
        assert sig_agg.confidence == 1.0
        assert sig_con.confidence == 0.0


# ── Section 33: No import boundary violations ───────────────────────


class TestBoundaryViolations:
    def test_no_cells_import_outcome(self):
        import umh.runtime.outcome as mod

        source = open(mod.__file__).read()
        assert "umh.cells" not in source

    def test_no_environments_import_memory(self):
        import umh.runtime.outcome_memory as mod

        source = open(mod.__file__).read()
        assert "umh.environments" not in source

    def test_no_adapters_import_bridge(self):
        import umh.runtime.feedback_bridge as mod

        source = open(mod.__file__).read()
        assert "umh.adapters" not in source


# ── Section 34: Long sequences ───────────────────────────────────────


class TestLongSequences:
    def test_100_outcomes(self):
        mem = OutcomeMemory()
        for i in range(100):
            mem.append(
                _make_outcome(
                    outcome_id=f"o{i}",
                    success_score=(i % 10) / 10,
                    status=OutcomeStatus.SUCCESS if i % 3 != 0 else OutcomeStatus.FAILURE,
                )
            )
        stats = mem.compute_strategy_stats("aggressive")
        assert stats.total_count == 100
        assert stats.success_count + stats.failure_count == 100

    def test_100_bridge_records(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        for i in range(100):
            bridge.record_outcome(_make_outcome(outcome_id=f"o{i}"))
        assert bridge.link_count == 100
        assert mem.count == 100


# ── Section 35: Feedback factor boundary values ──────────────────────


class TestFactorBoundaries:
    def test_exact_threshold_triggers(self):
        mem = OutcomeMemory(required_samples=10)
        for i in range(10):
            mem.append(_make_outcome(outcome_id=f"o{i}", success_score=0.8))
        factor = mem.get_strategy_feedback_factor("aggressive")
        assert factor != 1.0

    def test_one_below_threshold_neutral(self):
        mem = OutcomeMemory(required_samples=10)
        for i in range(9):
            mem.append(_make_outcome(outcome_id=f"o{i}", success_score=0.8))
        factor = mem.get_strategy_feedback_factor("aggressive")
        assert factor == 1.0

    def test_mixed_scores_moderate_factor(self):
        mem = OutcomeMemory()
        for i in range(5):
            mem.append(_make_outcome(outcome_id=f"h{i}", success_score=0.9))
        for i in range(5):
            mem.append(_make_outcome(outcome_id=f"l{i}", success_score=0.1))
        factor = mem.get_strategy_feedback_factor("aggressive")
        assert factor == 1.0


# ── Section 36: Multi-state interaction ──────────────────────────────


class TestMultiState:
    def test_different_states_same_strategy(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(
                _make_outcome(
                    outcome_id=f"a{i}",
                    state_signature="sa",
                    success_score=0.9,
                )
            )
        for i in range(10):
            mem.append(
                _make_outcome(
                    outcome_id=f"b{i}",
                    state_signature="sb",
                    success_score=0.2,
                )
            )
        stats_a = mem.compute_state_strategy_stats("sa", "aggressive")
        stats_b = mem.compute_state_strategy_stats("sb", "aggressive")
        assert stats_a.average_success_score > stats_b.average_success_score

    def test_state_does_not_leak(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(state_signature="sa", outcome_id="o1"))
        mem.append(_make_outcome(state_signature="sb", outcome_id="o2"))
        assert len(mem.query_by_state("sa")) == 1
        assert len(mem.query_by_state("sb")) == 1

    def test_global_stats_include_all_states(self):
        mem = OutcomeMemory()
        mem.append(_make_outcome(state_signature="sa", outcome_id="o1"))
        mem.append(_make_outcome(state_signature="sb", outcome_id="o2"))
        stats = mem.compute_strategy_stats("aggressive")
        assert stats.total_count == 2


# ── Section 37: Feedback bridge with multiple strategies ─────────────


class TestBridgeMultiStrategy:
    def test_summary_per_strategy(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        for i in range(5):
            bridge.record_outcome(
                _make_outcome(
                    outcome_id=f"a{i}",
                    strategy_name="agg",
                )
            )
        for i in range(3):
            bridge.record_outcome(
                _make_outcome(
                    outcome_id=f"c{i}",
                    strategy_name="con",
                )
            )
        s_agg = bridge.get_feedback_summary("agg")
        s_con = bridge.get_feedback_summary("con")
        assert s_agg["stats"]["total_count"] == 5
        assert s_con["stats"]["total_count"] == 3

    def test_links_per_strategy(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        bridge.record_outcome(_make_outcome(strategy_name="agg", outcome_id="o1"))
        bridge.record_outcome(_make_outcome(strategy_name="con", outcome_id="o2"))
        bridge.record_outcome(_make_outcome(strategy_name="agg", outcome_id="o3"))
        assert len(bridge.get_links_for_strategy("agg")) == 2
        assert len(bridge.get_links_for_strategy("con")) == 1


# ── Section 38: Explanation with history ─────────────────────────────


class TestExplanationWithHistory:
    def test_accumulated_global_stats(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        for i in range(5):
            bridge.record_outcome(_make_outcome(outcome_id=f"o{i}"))
        fb = bridge.record_outcome(_make_outcome(outcome_id="o5"))
        assert "6 executions" in fb.explanation

    def test_state_specific_count(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        bridge.record_outcome(_make_outcome(state_signature="sa", outcome_id="o1"))
        bridge.record_outcome(_make_outcome(state_signature="sb", outcome_id="o2"))
        fb = bridge.record_outcome(_make_outcome(state_signature="sa", outcome_id="o3"))
        assert "2 executions" in fb.explanation


# ── Section 39: Performance signal accuracy ──────────────────────────


class TestSignalAccuracy:
    def test_success_rate_in_signal(self):
        mem = OutcomeMemory()
        for i in range(8):
            mem.append(
                _make_outcome(
                    outcome_id=f"s{i}",
                    status=OutcomeStatus.SUCCESS,
                )
            )
        for i in range(2):
            mem.append(
                _make_outcome(
                    outcome_id=f"f{i}",
                    status=OutcomeStatus.FAILURE,
                )
            )
        sig = mem.get_performance_signal("aggressive")
        assert abs(sig.success_rate - 0.8) < 1e-9

    def test_average_score_in_signal(self):
        mem = OutcomeMemory()
        for i in range(4):
            mem.append(_make_outcome(outcome_id=f"o{i}", success_score=0.5))
        sig = mem.get_performance_signal("aggressive")
        assert abs(sig.average_score - 0.5) < 1e-9

    def test_signal_to_dict_roundtrip(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(_make_outcome(outcome_id=f"o{i}", success_score=0.7))
        sig = mem.get_performance_signal("aggressive")
        d = sig.to_dict()
        assert d["strategy_name"] == "aggressive"
        assert d["sample_size"] == 10
        assert d["confidence"] == 1.0


# ── Section 40: Stats to_dict roundtrip ──────────────────────────────


class TestStatsDictRoundtrip:
    def test_all_fields_present(self):
        mem = OutcomeMemory()
        for i in range(3):
            mem.append(
                _make_outcome(
                    outcome_id=f"o{i}",
                    status=[OutcomeStatus.SUCCESS, OutcomeStatus.FAILURE, OutcomeStatus.PARTIAL][i],
                    success_score=0.5,
                    latency=1.5,
                    effort=0.3,
                )
            )
        stats = mem.compute_strategy_stats("aggressive")
        d = stats.to_dict()
        assert d["total_count"] == 3
        assert d["success_count"] == 1
        assert d["failure_count"] == 1
        assert d["partial_count"] == 1
        assert d["unknown_count"] == 0
        assert d["average_success_score"] == 0.5
        assert d["average_latency"] == 1.5
        assert d["average_effort"] == 0.3


# ── Section 41: Outcome memory property access ──────────────────────


class TestMemoryProperties:
    def test_bridge_exposes_memory(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        assert bridge.outcome_memory is mem

    def test_memory_required_samples_default(self):
        mem = OutcomeMemory()
        assert mem.required_samples == 10

    def test_memory_required_samples_custom(self):
        mem = OutcomeMemory(required_samples=20)
        assert mem.required_samples == 20


# ── Section 42: Feedback factor formula verification ─────────────────


class TestFactorFormula:
    def test_score_0_75_factor(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(_make_outcome(outcome_id=f"o{i}", success_score=0.75))
        factor = mem.get_strategy_feedback_factor("aggressive")
        expected = 1.0 + (0.75 - 0.5) * 0.2
        assert abs(factor - expected) < 1e-9

    def test_score_0_25_factor(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(_make_outcome(outcome_id=f"o{i}", success_score=0.25))
        factor = mem.get_strategy_feedback_factor("aggressive")
        expected = 1.0 + (0.25 - 0.5) * 0.2
        assert abs(factor - expected) < 1e-9

    def test_score_1_0_clamped(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(_make_outcome(outcome_id=f"o{i}", success_score=1.0))
        factor = mem.get_strategy_feedback_factor("aggressive")
        assert factor == 1.10

    def test_score_0_0_clamped(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(_make_outcome(outcome_id=f"o{i}", success_score=0.0))
        factor = mem.get_strategy_feedback_factor("aggressive")
        assert factor == 0.90

    def test_factor_monotonic_with_score(self):
        factors = []
        for score in [0.0, 0.25, 0.5, 0.75, 1.0]:
            mem = OutcomeMemory()
            for i in range(10):
                mem.append(_make_outcome(outcome_id=f"o{i}", success_score=score))
            factors.append(mem.get_strategy_feedback_factor("aggressive"))
        for j in range(len(factors) - 1):
            assert factors[j] <= factors[j + 1]
