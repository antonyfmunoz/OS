"""
Tests for GoalSelector — Phase 9D + 9E.

Verifies:
- Deterministic ranking (same inputs → same order)
- Stable ordering (no oscillation between cycles)
- Focus budget enforcement
- State transitions
- Blocker resolution
- Scoring math
- Integration with event system
- Performance adjustment (9E): scoring adapts after outcomes
- Time decay (9E): recent outcomes matter more
- Stability (9E): no oscillation from feedback
"""

import sys
import os
import math
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from eos_ai.goal_selector import (
    GoalSelector,
    Goal,
    GoalState,
    PerformanceProfile,
    OutcomeTracker,
    DEFAULT_WEIGHTS,
    DEFAULT_FOCUS_BUDGET,
    DECAY_HALF_LIFE,
    _TERMINAL_STATES,
    _SCORABLE_STATES,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _make_goal(
    id: str = "g1",
    title: str = "Test goal",
    priority: int = 5,
    expected_impact: float = 0.5,
    estimated_cost: float = 0.5,
    confidence: float = 0.5,
    state: GoalState = GoalState.DEFERRED,
    blocked_by: list[str] | None = None,
    age_days: float = 0.0,
    performance: PerformanceProfile | None = None,
) -> Goal:
    created = datetime.now(timezone.utc) - timedelta(days=age_days)
    return Goal(
        id=id,
        org_id="test-org",
        title=title,
        priority=priority,
        expected_impact=expected_impact,
        estimated_cost=estimated_cost,
        confidence=confidence,
        state=state,
        blocked_by=blocked_by or [],
        created_at=created,
        updated_at=created,
        performance=performance or PerformanceProfile(),
    )


def _make_selector(focus_budget: int = 3) -> GoalSelector:
    """Selector that doesn't touch Neon."""
    sel = GoalSelector(org_id="test-org", focus_budget=focus_budget)
    return sel


# ─── Scoring tests ──────────────────────────────────────────────────────────


class TestScoring:
    def test_higher_priority_scores_higher(self):
        sel = _make_selector()
        high = _make_goal(id="high", priority=10)
        low = _make_goal(id="low", priority=1)
        goals = [high, low]
        sel.score_goal(high, goals)
        sel.score_goal(low, goals)
        assert high.score > low.score

    def test_higher_impact_scores_higher(self):
        sel = _make_selector()
        high = _make_goal(id="high", expected_impact=0.9)
        low = _make_goal(id="low", expected_impact=0.1)
        goals = [high, low]
        sel.score_goal(high, goals)
        sel.score_goal(low, goals)
        assert high.score > low.score

    def test_lower_cost_scores_higher(self):
        sel = _make_selector()
        cheap = _make_goal(id="cheap", estimated_cost=0.1)
        expensive = _make_goal(id="expensive", estimated_cost=0.9)
        goals = [cheap, expensive]
        sel.score_goal(cheap, goals)
        sel.score_goal(expensive, goals)
        assert cheap.score > expensive.score

    def test_newer_goals_score_higher_than_old(self):
        sel = _make_selector()
        new = _make_goal(id="new", age_days=0)
        old = _make_goal(id="old", age_days=60)
        goals = [new, old]
        sel.score_goal(new, goals)
        sel.score_goal(old, goals)
        assert new.score > old.score

    def test_dependency_unlock_boosts_score(self):
        sel = _make_selector()
        keystone = _make_goal(id="keystone")
        dependent1 = _make_goal(id="d1", blocked_by=["keystone"])
        dependent2 = _make_goal(id="d2", blocked_by=["keystone"])
        goals = [keystone, dependent1, dependent2]
        sel.score_goal(keystone, goals)
        plain = _make_goal(id="plain")
        sel.score_goal(plain, [plain])
        assert keystone.score > plain.score

    def test_score_is_deterministic(self):
        sel = _make_selector()
        goal = _make_goal()
        goals = [goal]
        sel.score_goal(goal, goals)
        score1 = goal.score

        goal.score = 0.0
        sel.score_goal(goal, goals)
        score2 = goal.score

        assert score1 == score2

    def test_score_in_valid_range(self):
        sel = _make_selector()
        goal = _make_goal(priority=10, expected_impact=1.0, estimated_cost=0.0, confidence=1.0)
        sel.score_goal(goal, [goal])
        assert 0.0 <= goal.score <= 1.0

    def test_explanation_populated(self):
        sel = _make_selector()
        goal = _make_goal()
        sel.score_goal(goal, [goal])
        assert len(goal.score_explanation) == 7  # 6 base + 1 performance
        # Performance line may say "neutral" instead of "→"
        base_entries = [e for e in goal.score_explanation if "→" in e]
        assert len(base_entries) == 6


# ─── Selection cycle tests ──────────────────────────────────────────────────


class TestSelectionCycle:
    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_focus_budget_enforced(self, mock_load, mock_log, mock_persist):
        sel = _make_selector(focus_budget=2)
        goals = [
            _make_goal(id="g1", priority=10),
            _make_goal(id="g2", priority=7),
            _make_goal(id="g3", priority=3),
        ]
        mock_load.return_value = goals
        active = sel.run_selection_cycle()
        assert len(active) == 2
        assert all(g.state == GoalState.ACTIVE for g in active)

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_deferred_goals_not_active(self, mock_load, mock_log, mock_persist):
        sel = _make_selector(focus_budget=1)
        goals = [
            _make_goal(id="g1", priority=10),
            _make_goal(id="g2", priority=5),
        ]
        mock_load.return_value = goals
        active = sel.run_selection_cycle()
        assert len(active) == 1
        deferred = [g for g in goals if g.state == GoalState.DEFERRED]
        assert len(deferred) == 1

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_terminal_goals_untouched(self, mock_load, mock_log, mock_persist):
        sel = _make_selector(focus_budget=3)
        completed = _make_goal(id="done", state=GoalState.COMPLETED)
        dropped = _make_goal(id="nope", state=GoalState.DROPPED)
        active_goal = _make_goal(id="g1", priority=8)
        mock_load.return_value = [completed, dropped, active_goal]
        active = sel.run_selection_cycle()
        assert completed.state == GoalState.COMPLETED
        assert dropped.state == GoalState.DROPPED
        assert len(active) == 1

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_stable_ordering_across_cycles(self, mock_load, mock_log, mock_persist):
        """Same inputs → same ranking order across multiple cycles."""
        sel = _make_selector(focus_budget=2)
        goals = [
            _make_goal(id="g1", priority=10, expected_impact=0.9),
            _make_goal(id="g2", priority=5, expected_impact=0.5),
            _make_goal(id="g3", priority=3, expected_impact=0.3),
        ]
        mock_load.return_value = goals
        active1 = sel.run_selection_cycle()
        ids1 = [g.id for g in active1]

        # Reset states for second cycle
        for g in goals:
            g.state = GoalState.DEFERRED
        mock_load.return_value = goals
        active2 = sel.run_selection_cycle()
        ids2 = [g.id for g in active2]

        assert ids1 == ids2

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_no_oscillation(self, mock_load, mock_log, mock_persist):
        """Run 10 cycles — ranking should not flip-flop."""
        sel = _make_selector(focus_budget=2)
        goals = [
            _make_goal(id="g1", priority=8, expected_impact=0.7),
            _make_goal(id="g2", priority=7, expected_impact=0.8),
            _make_goal(id="g3", priority=3, expected_impact=0.4),
        ]
        rankings = []
        for _ in range(10):
            for g in goals:
                if g.state in _SCORABLE_STATES or g.state == GoalState.DEFERRED:
                    g.state = GoalState.DEFERRED
            mock_load.return_value = goals
            active = sel.run_selection_cycle()
            rankings.append(tuple(g.id for g in active))

        # All 10 cycles should produce identical active sets
        assert len(set(rankings)) == 1


# ─── Blocker resolution tests ───────────────────────────────────────────────


class TestBlockerResolution:
    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_blocked_goal_stays_blocked(self, mock_load, mock_log, mock_persist):
        sel = _make_selector(focus_budget=3)
        blocker = _make_goal(id="blocker", priority=10, state=GoalState.ACTIVE)
        blocked = _make_goal(
            id="blocked", priority=8, state=GoalState.BLOCKED, blocked_by=["blocker"]
        )
        mock_load.return_value = [blocker, blocked]
        active = sel.run_selection_cycle()
        assert blocked.state == GoalState.BLOCKED

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_blocked_goal_unblocks_when_blocker_completed(self, mock_load, mock_log, mock_persist):
        sel = _make_selector(focus_budget=3)
        blocker = _make_goal(id="blocker", state=GoalState.COMPLETED)
        blocked = _make_goal(
            id="blocked", priority=8, state=GoalState.BLOCKED, blocked_by=["blocker"]
        )
        mock_load.return_value = [blocker, blocked]
        active = sel.run_selection_cycle()
        assert blocked.state in (GoalState.ACTIVE, GoalState.DEFERRED)


# ─── State transition tests ─────────────────────────────────────────────────


class TestStateTransitions:
    @patch.object(GoalSelector, "_persist_goal")
    @patch.object(GoalSelector, "_emit_event")
    @patch.object(GoalSelector, "load_goals")
    def test_activate(self, mock_load, mock_emit, mock_persist):
        sel = _make_selector()
        goal = _make_goal(id="g1", state=GoalState.DEFERRED)
        mock_load.return_value = [goal]
        result = sel.activate("g1")
        assert result.state == GoalState.ACTIVE
        mock_emit.assert_called_once()

    @patch.object(GoalSelector, "_persist_goal")
    @patch.object(GoalSelector, "_emit_event")
    @patch.object(GoalSelector, "load_goals")
    def test_defer(self, mock_load, mock_emit, mock_persist):
        sel = _make_selector()
        goal = _make_goal(id="g1", state=GoalState.ACTIVE)
        mock_load.return_value = [goal]
        result = sel.defer("g1")
        assert result.state == GoalState.DEFERRED

    @patch.object(GoalSelector, "_persist_goal")
    @patch.object(GoalSelector, "_emit_event")
    @patch.object(GoalSelector, "load_goals")
    def test_cannot_activate_completed(self, mock_load, mock_emit, mock_persist):
        sel = _make_selector()
        goal = _make_goal(id="g1", state=GoalState.COMPLETED)
        mock_load.return_value = [goal]
        with pytest.raises(ValueError, match="Cannot activate completed"):
            sel.activate("g1")

    @patch.object(GoalSelector, "_persist_goal")
    @patch.object(GoalSelector, "_emit_event")
    @patch.object(GoalSelector, "load_goals")
    def test_activate_at_budget_demotes_lowest(self, mock_load, mock_emit, mock_persist):
        sel = _make_selector(focus_budget=2)
        g1 = _make_goal(id="g1", priority=10, state=GoalState.ACTIVE)
        g1.score = 0.9
        g2 = _make_goal(id="g2", priority=5, state=GoalState.ACTIVE)
        g2.score = 0.5
        g3 = _make_goal(id="g3", priority=7, state=GoalState.DEFERRED)
        mock_load.return_value = [g1, g2, g3]
        result = sel.activate("g3")
        assert result.state == GoalState.ACTIVE
        assert g2.state == GoalState.DEFERRED


# ─── is_active gate test ─────────────────────────────────────────────────────


class TestGate:
    @patch.object(GoalSelector, "load_goals")
    def test_active_goal_passes_gate(self, mock_load):
        sel = _make_selector()
        goal = _make_goal(id="g1", state=GoalState.ACTIVE)
        mock_load.return_value = [goal]
        assert sel.is_active("g1") is True

    @patch.object(GoalSelector, "load_goals")
    def test_deferred_goal_blocked_by_gate(self, mock_load):
        sel = _make_selector()
        goal = _make_goal(id="g1", state=GoalState.DEFERRED)
        mock_load.return_value = [goal]
        assert sel.is_active("g1") is False

    @patch.object(GoalSelector, "load_goals")
    def test_nonexistent_goal_blocked(self, mock_load):
        sel = _make_selector()
        mock_load.return_value = []
        assert sel.is_active("nope") is False


# ─── Explainability test ────────────────────────────────────────────────────


class TestExplainability:
    def test_explain_returns_required_fields(self):
        sel = _make_selector()
        goal = _make_goal(id="g1", priority=8)
        sel.score_goal(goal, [goal])
        goal.state = GoalState.ACTIVE
        goal.rank = 1
        info = sel.explain(goal)
        assert "score" in info
        assert "base_score" in info
        assert "performance_adjustment" in info
        assert "rank" in info
        assert "state" in info
        assert "why" in info
        assert "performance" in info
        assert info["state"] == "active"
        assert isinstance(info["why"], list)


# ═════════════════════════════════════════════════════════════════════════════
# Phase 9E: Outcome-Driven Reweighting Tests
# ═════════════════════════════════════════════════════════════════════════════


# ─── PerformanceProfile tests ───────────────────────────────────────────────


class TestPerformanceProfile:
    def test_neutral_when_no_outcomes(self):
        p = PerformanceProfile()
        assert p.composite() == 0.5

    def test_perfect_performance_above_neutral(self):
        p = PerformanceProfile(
            success_rate=1.0,
            efficiency=1.0,
            reliability=1.0,
            impact_score=1.0,
            total_outcomes=10,
        )
        assert p.composite() == 1.0

    def test_zero_performance_below_neutral(self):
        p = PerformanceProfile(
            success_rate=0.0,
            efficiency=0.0,
            reliability=0.0,
            impact_score=0.0,
            total_outcomes=10,
        )
        assert p.composite() == 0.0

    def test_serialization_roundtrip(self):
        now = datetime.now(timezone.utc)
        p = PerformanceProfile(
            success_rate=0.85,
            efficiency=0.7,
            reliability=0.9,
            impact_score=0.6,
            total_outcomes=20,
            total_successes=17,
            total_failures=3,
            avg_execution_time=15.5,
            last_outcome_at=now,
        )
        d = p.to_dict()
        p2 = PerformanceProfile.from_dict(d)
        assert p2.success_rate == 0.85
        assert p2.total_outcomes == 20
        assert p2.last_outcome_at is not None


# ─── Performance adjustment scoring tests ────────────────────────────────────


class TestPerformanceScoring:
    def test_good_performance_boosts_score(self):
        sel = _make_selector()
        good_perf = PerformanceProfile(
            success_rate=0.9,
            efficiency=0.8,
            reliability=0.95,
            impact_score=0.7,
            total_outcomes=10,
            last_outcome_at=datetime.now(timezone.utc),
        )
        goal_with = _make_goal(id="perf", performance=good_perf)
        goal_without = _make_goal(id="noperf")
        sel.score_goal(goal_with, [goal_with])
        sel.score_goal(goal_without, [goal_without])
        assert goal_with.score > goal_without.score
        assert goal_with.performance_adjustment > 0

    def test_bad_performance_penalizes_score(self):
        sel = _make_selector()
        bad_perf = PerformanceProfile(
            success_rate=0.1,
            efficiency=0.1,
            reliability=0.2,
            impact_score=0.0,
            total_outcomes=10,
            last_outcome_at=datetime.now(timezone.utc),
        )
        goal_bad = _make_goal(id="bad", performance=bad_perf)
        goal_neutral = _make_goal(id="neutral")
        sel.score_goal(goal_bad, [goal_bad])
        sel.score_goal(goal_neutral, [goal_neutral])
        assert goal_bad.score < goal_neutral.score
        assert goal_bad.performance_adjustment < 0

    def test_no_outcomes_is_neutral(self):
        sel = _make_selector()
        goal = _make_goal()
        sel.score_goal(goal, [goal])
        assert goal.performance_adjustment == 0.0
        assert goal.base_score == goal.score

    def test_base_plus_adjustment_equals_score(self):
        sel = _make_selector()
        perf = PerformanceProfile(
            success_rate=0.8,
            efficiency=0.7,
            reliability=0.9,
            impact_score=0.5,
            total_outcomes=5,
            last_outcome_at=datetime.now(timezone.utc),
        )
        goal = _make_goal(performance=perf)
        sel.score_goal(goal, [goal])
        assert abs(goal.score - (goal.base_score + goal.performance_adjustment)) < 0.001

    def test_explanation_includes_performance(self):
        sel = _make_selector()
        perf = PerformanceProfile(
            success_rate=0.8,
            efficiency=0.7,
            reliability=0.9,
            impact_score=0.5,
            total_outcomes=5,
            last_outcome_at=datetime.now(timezone.utc),
        )
        goal = _make_goal(performance=perf)
        sel.score_goal(goal, [goal])
        # 9G: explanation uses perf_short/perf_medium/perf_long instead of single "performance"
        perf_entries = [e for e in goal.score_explanation if "perf_" in e]
        assert len(perf_entries) == 3  # short, medium, long
        assert all("neutral" not in e for e in perf_entries)

    def test_no_outcomes_explanation_says_neutral(self):
        sel = _make_selector()
        goal = _make_goal()
        sel.score_goal(goal, [goal])
        perf_entries = [e for e in goal.score_explanation if "performance" in e]
        assert len(perf_entries) == 1
        assert "neutral" in perf_entries[0]


# ─── Time decay tests ───────────────────────────────────────────────────────


class TestTimeDecay:
    def test_recent_outcome_full_weight(self):
        sel = _make_selector()
        perf = PerformanceProfile(
            success_rate=0.9,
            efficiency=0.8,
            reliability=0.9,
            impact_score=0.7,
            total_outcomes=5,
            last_outcome_at=datetime.now(timezone.utc),
        )
        decay = sel._performance_decay(perf)
        assert decay > 0.99

    def test_old_outcome_decayed(self):
        sel = _make_selector()
        perf = PerformanceProfile(
            success_rate=0.9,
            efficiency=0.8,
            reliability=0.9,
            impact_score=0.7,
            total_outcomes=5,
            last_outcome_at=datetime.now(timezone.utc) - timedelta(days=3),
        )
        decay = sel._performance_decay(perf)
        assert decay < 0.2

    def test_one_halflife_is_roughly_half(self):
        sel = _make_selector()
        perf = PerformanceProfile(
            success_rate=0.9,
            efficiency=0.8,
            reliability=0.9,
            impact_score=0.7,
            total_outcomes=5,
            last_outcome_at=datetime.now(timezone.utc) - timedelta(seconds=DECAY_HALF_LIFE),
        )
        decay = sel._performance_decay(perf)
        assert 0.45 < decay < 0.55

    def test_no_outcome_full_weight(self):
        sel = _make_selector()
        perf = PerformanceProfile()
        decay = sel._performance_decay(perf)
        assert decay == 1.0

    def test_stale_performance_has_less_impact(self):
        """Stale data differentiated via multi-horizon profiles (9G).

        In 9G, staleness is captured at profile computation time (OutcomeTracker),
        not at scoring time. A goal with worse short-term profile than long-term
        reflects recency. This test uses explicit horizon profiles to verify.
        """
        from eos_ai.goal_selector import MultiHorizonProfile

        sel = _make_selector()
        recent_perf = PerformanceProfile(
            success_rate=0.9,
            efficiency=0.8,
            reliability=0.9,
            impact_score=0.7,
            total_outcomes=5,
            last_outcome_at=datetime.now(timezone.utc),
        )
        stale_perf = PerformanceProfile(
            success_rate=0.5,
            efficiency=0.4,
            reliability=0.5,
            impact_score=0.3,
            total_outcomes=5,
            last_outcome_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        # Recent goal: strong across all horizons
        recent_goal = _make_goal(id="recent", performance=recent_perf)
        recent_goal.horizons = MultiHorizonProfile(
            short_term=recent_perf,
            medium_term=recent_perf,
            long_term=recent_perf,
        )
        # Stale goal: strong long-term but weak short-term (data decayed)
        stale_goal = _make_goal(id="stale", performance=stale_perf)
        stale_goal.horizons = MultiHorizonProfile(
            short_term=stale_perf,
            medium_term=stale_perf,
            long_term=recent_perf,
        )
        sel.score_goal(recent_goal, [recent_goal])
        sel.score_goal(stale_goal, [stale_goal])
        assert recent_goal.performance_adjustment > stale_goal.performance_adjustment


# ─── Adaptive ranking stability tests ────────────────────────────────────────


class TestAdaptiveStability:
    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_performer_rises_in_ranking(self, mock_load, mock_log, mock_persist):
        """Goal with good performance should outrank equal-priority goal without."""
        sel = _make_selector(focus_budget=2)
        good_perf = PerformanceProfile(
            success_rate=0.9,
            efficiency=0.8,
            reliability=0.95,
            impact_score=0.7,
            total_outcomes=10,
            last_outcome_at=datetime.now(timezone.utc),
        )
        g1 = _make_goal(id="g1", priority=7, performance=good_perf)
        g2 = _make_goal(id="g2", priority=7)
        g3 = _make_goal(id="g3", priority=7)
        mock_load.return_value = [g1, g2, g3]
        active = sel.run_selection_cycle()
        active_ids = [g.id for g in active]
        assert "g1" in active_ids
        assert g1.rank == 1

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_failing_goal_drops_in_ranking(self, mock_load, mock_log, mock_persist):
        """Goal with bad performance should rank below equal-priority goal without."""
        sel = _make_selector(focus_budget=2)
        bad_perf = PerformanceProfile(
            success_rate=0.1,
            efficiency=0.1,
            reliability=0.2,
            impact_score=0.0,
            total_outcomes=10,
            last_outcome_at=datetime.now(timezone.utc),
        )
        g_bad = _make_goal(id="bad", priority=7, performance=bad_perf)
        g_ok = _make_goal(id="ok", priority=7)
        mock_load.return_value = [g_bad, g_ok]
        sel.run_selection_cycle()
        assert g_bad.rank > g_ok.rank

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_deterministic_with_performance(self, mock_load, mock_log, mock_persist):
        """Same performance data → same ranking across cycles."""
        sel = _make_selector(focus_budget=2)
        perf = PerformanceProfile(
            success_rate=0.8,
            efficiency=0.7,
            reliability=0.9,
            impact_score=0.5,
            total_outcomes=5,
            last_outcome_at=datetime.now(timezone.utc),
        )
        goals = [
            _make_goal(id="g1", priority=8, performance=perf),
            _make_goal(id="g2", priority=6),
            _make_goal(id="g3", priority=4),
        ]
        mock_load.return_value = goals
        active1 = sel.run_selection_cycle()
        ids1 = [g.id for g in active1]

        for g in goals:
            g.state = GoalState.DEFERRED
        mock_load.return_value = goals
        active2 = sel.run_selection_cycle()
        ids2 = [g.id for g in active2]

        assert ids1 == ids2

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_no_oscillation_with_performance(self, mock_load, mock_log, mock_persist):
        """10 cycles with mixed performance — no flip-flopping."""
        sel = _make_selector(focus_budget=2)
        good = PerformanceProfile(
            success_rate=0.85,
            efficiency=0.7,
            reliability=0.9,
            impact_score=0.6,
            total_outcomes=8,
            last_outcome_at=datetime.now(timezone.utc),
        )
        bad = PerformanceProfile(
            success_rate=0.2,
            efficiency=0.3,
            reliability=0.4,
            impact_score=0.1,
            total_outcomes=8,
            last_outcome_at=datetime.now(timezone.utc),
        )
        goals = [
            _make_goal(id="g1", priority=7, performance=good),
            _make_goal(id="g2", priority=7, performance=bad),
            _make_goal(id="g3", priority=7),
        ]
        rankings = []
        for _ in range(10):
            for g in goals:
                if g.state not in _TERMINAL_STATES:
                    g.state = GoalState.DEFERRED
            mock_load.return_value = goals
            active = sel.run_selection_cycle()
            rankings.append(tuple(g.id for g in active))

        assert len(set(rankings)) == 1


# ─── OutcomeTracker unit tests ───────────────────────────────────────────────


class TestOutcomeTracker:
    def test_empty_profile_is_neutral(self):
        """No outcomes → neutral profile."""
        p = PerformanceProfile()
        assert p.composite() == 0.5
        assert p.total_outcomes == 0

    def test_performance_profile_composite_range(self):
        """Composite always in [0, 1]."""
        for sr in [0.0, 0.5, 1.0]:
            for eff in [0.0, 0.5, 1.0]:
                for rel in [0.0, 0.5, 1.0]:
                    for imp in [0.0, 0.5, 1.0]:
                        p = PerformanceProfile(
                            success_rate=sr,
                            efficiency=eff,
                            reliability=rel,
                            impact_score=imp,
                            total_outcomes=10,
                        )
                        assert 0.0 <= p.composite() <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
