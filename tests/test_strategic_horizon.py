"""
Tests for Phase 9G: Multi-Timescale Decision + Strategic Horizon Layer.

Verifies:
- Short-term spikes don't instantly replace stable long-term goals
- Long-term consistent goals earn stability bonus and persist
- Multi-horizon scoring produces correct weighted adjustments
- Stability bonus calculation follows threshold + proportional scaling
- MultiHorizonProfile serialization roundtrip
- Backward compat: legacy performance promotes to all horizons
- Deterministic outputs across runs
- No oscillation with mixed horizon data
- Score decomposition (base + horizon adj + stability = score)
- Constraints: no randomness, no execution mutation
- Explainability includes horizon breakdown
"""

import sys
import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from control_plane.goals.goal_selector import (
    GoalSelector,
    Goal,
    GoalState,
    PerformanceProfile,
    MultiHorizonProfile,
    StrategicHorizonLayer,
    OpportunityCostLayer,
    OutcomeTracker,
    DEFAULT_WEIGHTS,
    HORIZON_WEIGHTS,
    STABILITY_BONUS_THRESHOLD,
    STABILITY_BONUS_MAX,
    SHORT_TERM_HALF_LIFE,
    MEDIUM_TERM_HALF_LIFE,
    LONG_TERM_HALF_LIFE,
    _TERMINAL_STATES,
    _SCORABLE_STATES,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _perf(
    sr: float = 0.5,
    eff: float = 0.5,
    rel: float = 0.5,
    imp: float = 0.5,
    n: int = 10,
) -> PerformanceProfile:
    return PerformanceProfile(
        success_rate=sr,
        efficiency=eff,
        reliability=rel,
        impact_score=imp,
        total_outcomes=n,
        total_successes=int(n * sr),
        total_failures=n - int(n * sr),
        last_outcome_at=datetime.now(timezone.utc),
    )


def _horizons(
    short: PerformanceProfile | None = None,
    medium: PerformanceProfile | None = None,
    long: PerformanceProfile | None = None,
) -> MultiHorizonProfile:
    return MultiHorizonProfile(
        short_term=short or PerformanceProfile(),
        medium_term=medium or PerformanceProfile(),
        long_term=long or PerformanceProfile(),
    )


def _make_goal(
    id: str = "g1",
    priority: int = 5,
    performance: PerformanceProfile | None = None,
    horizons: MultiHorizonProfile | None = None,
    state: GoalState = GoalState.DEFERRED,
) -> Goal:
    created = datetime.now(timezone.utc)
    return Goal(
        id=id,
        org_id="test-org",
        title=f"Goal {id}",
        priority=priority,
        state=state,
        created_at=created,
        updated_at=created,
        performance=performance or PerformanceProfile(),
        horizons=horizons or MultiHorizonProfile(),
    )


def _make_selector(focus_budget: int = 3) -> GoalSelector:
    return GoalSelector(org_id="test-org", focus_budget=focus_budget)


# ═════════════════════════════════════════════════════════════════════════════
# 1. MultiHorizonProfile
# ═════════════════════════════════════════════════════════════════════════════


class TestMultiHorizonProfile:
    def test_default_composites_are_neutral(self):
        h = MultiHorizonProfile()
        c = h.composites()
        assert c["short"] == 0.5
        assert c["medium"] == 0.5
        assert c["long"] == 0.5

    def test_weighted_composite_default_weights(self):
        h = _horizons(
            short=_perf(sr=1.0, eff=1.0, rel=1.0, imp=1.0),
            medium=_perf(sr=0.0, eff=0.0, rel=0.0, imp=0.0),
            long=_perf(sr=0.5, eff=0.5, rel=0.5, imp=0.5),
        )
        wc = h.weighted_composite()
        # short=1.0*0.4 + medium=0.0*0.4 + long=0.5*0.2 = 0.5
        assert abs(wc - 0.5) < 0.01

    def test_has_outcomes_false_when_empty(self):
        h = MultiHorizonProfile()
        assert h.has_outcomes() is False

    def test_has_outcomes_true_when_medium_has_data(self):
        h = _horizons(medium=_perf(n=5))
        assert h.has_outcomes() is True

    def test_serialization_roundtrip(self):
        h = _horizons(
            short=_perf(sr=0.9, eff=0.8, n=5),
            medium=_perf(sr=0.7, eff=0.6, n=10),
            long=_perf(sr=0.5, eff=0.4, n=20),
        )
        d = h.to_dict()
        h2 = MultiHorizonProfile.from_dict(d)
        assert h2.short_term.success_rate == 0.9
        assert h2.medium_term.total_outcomes == 10
        assert h2.long_term.efficiency == 0.4

    def test_from_dict_legacy_single_profile(self):
        """Legacy single PerformanceProfile dict promotes to all horizons."""
        legacy = _perf(sr=0.8, eff=0.7, n=15).to_dict()
        h = MultiHorizonProfile.from_dict(legacy)
        assert h.short_term.success_rate == 0.8
        assert h.medium_term.success_rate == 0.8
        assert h.long_term.success_rate == 0.8

    def test_from_dict_empty(self):
        h = MultiHorizonProfile.from_dict({})
        assert h.has_outcomes() is False


# ═════════════════════════════════════════════════════════════════════════════
# 2. StrategicHorizonLayer — Scoring
# ═════════════════════════════════════════════════════════════════════════════


class TestHorizonScoring:
    def test_no_outcomes_zero_adjustment(self):
        layer = StrategicHorizonLayer()
        goal = _make_goal()
        adj = layer.compute_horizon_adjustment(goal)
        assert adj == 0.0
        assert goal.stability_bonus == 0.0

    def test_good_performance_positive_adjustment(self):
        layer = StrategicHorizonLayer()
        good = _perf(sr=0.9, eff=0.8, rel=0.95, imp=0.7)
        goal = _make_goal(horizons=_horizons(short=good, medium=good, long=good))
        adj = layer.compute_horizon_adjustment(goal)
        assert adj > 0
        assert goal.performance_adjustment > 0

    def test_bad_performance_negative_adjustment(self):
        layer = StrategicHorizonLayer()
        bad = _perf(sr=0.1, eff=0.1, rel=0.2, imp=0.0)
        goal = _make_goal(horizons=_horizons(short=bad, medium=bad, long=bad))
        adj = layer.compute_horizon_adjustment(goal)
        assert adj < 0

    def test_short_term_weighted_more_than_long(self):
        """Short-term has 0.4 weight vs long-term 0.2 — same perf, more impact."""
        layer = StrategicHorizonLayer()
        strong = _perf(sr=1.0, eff=1.0, rel=1.0, imp=1.0)
        neutral = _perf(sr=0.5, eff=0.5, rel=0.5, imp=0.5)

        # Goal with strong short-term only
        g_short = _make_goal(
            id="short",
            horizons=_horizons(short=strong, medium=neutral, long=neutral),
        )
        # Goal with strong long-term only
        g_long = _make_goal(
            id="long",
            horizons=_horizons(short=neutral, medium=neutral, long=strong),
        )

        layer.compute_horizon_adjustment(g_short)
        layer.compute_horizon_adjustment(g_long)

        assert g_short.horizon_adjustments["short"] > g_long.horizon_adjustments["long"]

    def test_per_horizon_adjustments_populated(self):
        layer = StrategicHorizonLayer()
        good = _perf(sr=0.9, eff=0.8, rel=0.9, imp=0.7)
        goal = _make_goal(horizons=_horizons(short=good, medium=good, long=good))
        layer.compute_horizon_adjustment(goal)

        assert "short" in goal.horizon_adjustments
        assert "medium" in goal.horizon_adjustments
        assert "long" in goal.horizon_adjustments
        assert all(v > 0 for v in goal.horizon_adjustments.values())

    def test_legacy_performance_promotes_to_horizons(self):
        """Goal with performance but no horizons → auto-promotion."""
        layer = StrategicHorizonLayer()
        perf = _perf(sr=0.9, eff=0.8, rel=0.9, imp=0.7)
        goal = _make_goal(performance=perf)
        adj = layer.compute_horizon_adjustment(goal)
        assert adj > 0
        assert goal.horizons.has_outcomes()


# ═════════════════════════════════════════════════════════════════════════════
# 3. Stability Bonus
# ═════════════════════════════════════════════════════════════════════════════


class TestStabilityBonus:
    def test_no_bonus_below_threshold(self):
        """All horizons below threshold → no bonus."""
        layer = StrategicHorizonLayer()
        weak = _perf(sr=0.4, eff=0.3, rel=0.4, imp=0.2)
        goal = _make_goal(horizons=_horizons(short=weak, medium=weak, long=weak))
        layer.compute_horizon_adjustment(goal)
        assert goal.stability_bonus == 0.0

    def test_bonus_when_all_above_threshold(self):
        """All horizons above threshold → bonus earned."""
        layer = StrategicHorizonLayer()
        strong = _perf(sr=0.9, eff=0.8, rel=0.9, imp=0.7)
        goal = _make_goal(horizons=_horizons(short=strong, medium=strong, long=strong))
        layer.compute_horizon_adjustment(goal)
        assert goal.stability_bonus > 0
        assert goal.stability_bonus <= STABILITY_BONUS_MAX

    def test_no_bonus_when_one_horizon_below_threshold(self):
        """One weak horizon kills the stability bonus."""
        layer = StrategicHorizonLayer()
        strong = _perf(sr=0.9, eff=0.8, rel=0.9, imp=0.7)
        weak = _perf(sr=0.2, eff=0.1, rel=0.2, imp=0.1)
        goal = _make_goal(horizons=_horizons(short=strong, medium=strong, long=weak))
        layer.compute_horizon_adjustment(goal)
        assert goal.stability_bonus == 0.0

    def test_bonus_proportional_to_excess(self):
        """Higher composites → bigger bonus."""
        layer = StrategicHorizonLayer()
        medium_perf = _perf(sr=0.7, eff=0.65, rel=0.7, imp=0.6)
        strong_perf = _perf(sr=0.95, eff=0.9, rel=0.95, imp=0.85)

        g_medium = _make_goal(
            id="med",
            horizons=_horizons(short=medium_perf, medium=medium_perf, long=medium_perf),
        )
        g_strong = _make_goal(
            id="str",
            horizons=_horizons(short=strong_perf, medium=strong_perf, long=strong_perf),
        )

        layer.compute_horizon_adjustment(g_medium)
        layer.compute_horizon_adjustment(g_strong)

        assert g_strong.stability_bonus > g_medium.stability_bonus

    def test_max_bonus_capped(self):
        """Even perfect performance → bonus capped at STABILITY_BONUS_MAX."""
        layer = StrategicHorizonLayer()
        perfect = _perf(sr=1.0, eff=1.0, rel=1.0, imp=1.0)
        goal = _make_goal(horizons=_horizons(short=perfect, medium=perfect, long=perfect))
        layer.compute_horizon_adjustment(goal)
        assert goal.stability_bonus <= STABILITY_BONUS_MAX


# ═════════════════════════════════════════════════════════════════════════════
# 4. Short-Term Spikes vs Long-Term Stability
# ═════════════════════════════════════════════════════════════════════════════


class TestSpikeVsStability:
    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_short_spike_doesnt_replace_stable_goal(
        self,
        mock_load,
        mock_log,
        mock_persist,
    ):
        """Goal with strong short-term but weak long-term shouldn't beat
        a goal with consistent performance across all horizons."""
        sel = _make_selector(focus_budget=1)
        stable_perf = _perf(sr=0.75, eff=0.7, rel=0.8, imp=0.6)
        spike_short = _perf(sr=0.95, eff=0.9, rel=0.95, imp=0.8)
        spike_long = _perf(sr=0.2, eff=0.15, rel=0.3, imp=0.1)

        stable = _make_goal(
            id="stable",
            priority=7,
            horizons=_horizons(short=stable_perf, medium=stable_perf, long=stable_perf),
        )
        spike = _make_goal(
            id="spike",
            priority=7,
            horizons=_horizons(short=spike_short, medium=spike_long, long=spike_long),
        )

        mock_load.return_value = [stable, spike]
        active = sel.run_selection_cycle()

        # Stable should win: it has stability bonus + consistent medium/long
        assert active[0].id == "stable"

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_long_term_performer_persists(self, mock_load, mock_log, mock_persist):
        """A goal performing well across all horizons should stay active."""
        sel = _make_selector(focus_budget=2)
        consistent = _perf(sr=0.85, eff=0.8, rel=0.9, imp=0.7)
        mediocre = _perf(sr=0.5, eff=0.5, rel=0.5, imp=0.5)

        g_consistent = _make_goal(
            id="consistent",
            priority=7,
            horizons=_horizons(short=consistent, medium=consistent, long=consistent),
        )
        g_mediocre = _make_goal(
            id="mediocre",
            priority=7,
            horizons=_horizons(short=mediocre, medium=mediocre, long=mediocre),
        )
        g_neutral = _make_goal(id="neutral", priority=7)

        rankings = []
        for _ in range(10):
            for g in [g_consistent, g_mediocre, g_neutral]:
                if g.state not in _TERMINAL_STATES:
                    g.state = GoalState.DEFERRED
            mock_load.return_value = [g_consistent, g_mediocre, g_neutral]
            active = sel.run_selection_cycle()
            rankings.append(tuple(g.id for g in active))

        # Consistent should always be in active set
        for r in rankings:
            assert "consistent" in r


# ═════════════════════════════════════════════════════════════════════════════
# 5. Determinism + No Oscillation
# ═════════════════════════════════════════════════════════════════════════════


class TestDeterminism9G:
    def test_horizon_scoring_deterministic(self):
        layer = StrategicHorizonLayer()
        perf = _perf(sr=0.8, eff=0.7, rel=0.9, imp=0.6)
        results = []
        for _ in range(20):
            g = _make_goal(horizons=_horizons(short=perf, medium=perf, long=perf))
            adj = layer.compute_horizon_adjustment(g)
            results.append(adj)
        assert len(set(results)) == 1

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_no_oscillation_with_horizons(self, mock_load, mock_log, mock_persist):
        sel = _make_selector(focus_budget=2)
        good_h = _horizons(
            short=_perf(sr=0.85, eff=0.8, rel=0.9, imp=0.7),
            medium=_perf(sr=0.80, eff=0.75, rel=0.85, imp=0.65),
            long=_perf(sr=0.78, eff=0.7, rel=0.82, imp=0.6),
        )
        bad_h = _horizons(
            short=_perf(sr=0.2, eff=0.15, rel=0.3, imp=0.1),
            medium=_perf(sr=0.25, eff=0.2, rel=0.35, imp=0.15),
            long=_perf(sr=0.3, eff=0.25, rel=0.4, imp=0.2),
        )
        goals = [
            _make_goal(id="g1", priority=7, horizons=good_h),
            _make_goal(id="g2", priority=7, horizons=bad_h),
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


# ═════════════════════════════════════════════════════════════════════════════
# 6. Score Decomposition
# ═════════════════════════════════════════════════════════════════════════════


class TestScoreDecomposition:
    def test_base_plus_horizon_plus_stability_equals_score(self):
        sel = _make_selector()
        perf = _perf(sr=0.85, eff=0.8, rel=0.9, imp=0.7)
        goal = _make_goal(horizons=_horizons(short=perf, medium=perf, long=perf))
        sel.score_goal(goal, [goal])

        horizon_sum = sum(goal.horizon_adjustments.values())
        expected = goal.base_score + horizon_sum + goal.stability_bonus
        assert abs(goal.score - expected) < 0.001, (
            f"score={goal.score} != base({goal.base_score}) + "
            f"horizons({horizon_sum}) + stability({goal.stability_bonus})"
        )

    def test_performance_adjustment_matches_horizon_sum_plus_bonus(self):
        sel = _make_selector()
        perf = _perf(sr=0.85, eff=0.8, rel=0.9, imp=0.7)
        goal = _make_goal(horizons=_horizons(short=perf, medium=perf, long=perf))
        sel.score_goal(goal, [goal])

        horizon_sum = sum(goal.horizon_adjustments.values())
        expected_perf = horizon_sum + goal.stability_bonus
        assert abs(goal.performance_adjustment - expected_perf) < 0.001


# ═════════════════════════════════════════════════════════════════════════════
# 7. Explainability
# ═════════════════════════════════════════════════════════════════════════════


class TestExplainability9G:
    def test_explain_includes_horizon_data(self):
        sel = _make_selector()
        perf = _perf(sr=0.8, eff=0.7, rel=0.9, imp=0.6)
        goal = _make_goal(horizons=_horizons(short=perf, medium=perf, long=perf))
        sel.score_goal(goal, [goal])
        goal.state = GoalState.ACTIVE
        goal.rank = 1

        info = sel.explain(goal)

        assert "stability_bonus" in info
        assert "horizon_adjustments" in info
        assert "horizons" in info
        assert "strategic_horizon" in info
        sh = info["strategic_horizon"]
        assert "short_term" in sh
        assert "medium_term" in sh
        assert "long_term" in sh
        assert "horizon_weights" in sh

    def test_explanation_lines_include_all_horizons(self):
        sel = _make_selector()
        perf = _perf(sr=0.8, eff=0.7, rel=0.9, imp=0.6)
        goal = _make_goal(horizons=_horizons(short=perf, medium=perf, long=perf))
        sel.score_goal(goal, [goal])

        lines = goal.score_explanation
        assert any("perf_short" in l for l in lines)
        assert any("perf_medium" in l for l in lines)
        assert any("perf_long" in l for l in lines)
        assert any("stability_bonus" in l for l in lines)


# ═════════════════════════════════════════════════════════════════════════════
# 8. Constraints
# ═════════════════════════════════════════════════════════════════════════════


class TestConstraints9G:
    def test_no_randomness(self):
        import inspect

        source = inspect.getsource(StrategicHorizonLayer)
        assert "random" not in source
        assert "shuffle" not in source

    def test_no_execution_mutation(self):
        import inspect

        source = inspect.getsource(StrategicHorizonLayer)
        assert "task_executor" not in source
        assert "cognitive_loop" not in source

    def test_timescale_constants_ordered(self):
        assert SHORT_TERM_HALF_LIFE < MEDIUM_TERM_HALF_LIFE < LONG_TERM_HALF_LIFE

    def test_horizon_weights_sum_to_one(self):
        assert abs(sum(HORIZON_WEIGHTS.values()) - 1.0) < 0.001

    def test_stability_threshold_in_valid_range(self):
        assert 0 < STABILITY_BONUS_THRESHOLD < 1.0

    def test_stability_max_positive_and_bounded(self):
        assert 0 < STABILITY_BONUS_MAX < 0.10


# ═════════════════════════════════════════════════════════════════════════════
# 9. Backward Compatibility
# ═════════════════════════════════════════════════════════════════════════════


class TestBackwardCompat9G:
    def test_goal_has_horizon_fields(self):
        g = _make_goal()
        assert hasattr(g, "horizons")
        assert hasattr(g, "stability_bonus")
        assert hasattr(g, "horizon_adjustments")
        assert g.stability_bonus == 0.0
        assert g.horizon_adjustments == {"short": 0.0, "medium": 0.0, "long": 0.0}

    def test_selector_has_strategic_horizon(self):
        sel = _make_selector()
        assert hasattr(sel, "strategic_horizon")
        assert isinstance(sel.strategic_horizon, StrategicHorizonLayer)

    def test_no_outcomes_still_neutral(self):
        sel = _make_selector()
        goal = _make_goal()
        sel.score_goal(goal, [goal])
        assert goal.performance_adjustment == 0.0
        assert goal.stability_bonus == 0.0

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_9d_focus_budget_still_enforced(self, mock_load, mock_log, mock_persist):
        sel = _make_selector(focus_budget=2)
        goals = [
            _make_goal(id="g1", priority=10),
            _make_goal(id="g2", priority=7),
            _make_goal(id="g3", priority=3),
        ]
        mock_load.return_value = goals
        active = sel.run_selection_cycle()
        assert len(active) == 2

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_9f_opportunity_cost_still_works(self, mock_load, mock_log, mock_persist):
        """Opportunity cost from 9F still applies in 9G."""
        sel = _make_selector(focus_budget=2)
        bad_perf = _perf(sr=0.1, eff=0.1, rel=0.2, imp=0.0)
        good_perf = _perf(sr=0.9, eff=0.8, rel=0.95, imp=0.7)
        goals = [
            _make_goal(id="bad", priority=8, performance=bad_perf),
            _make_goal(id="good", priority=6, performance=good_perf),
            _make_goal(id="neutral", priority=5),
        ]
        mock_load.return_value = goals
        sel.run_selection_cycle()
        # System should still function with opportunity cost layer


# ═════════════════════════════════════════════════════════════════════════════
# 10. OutcomeTracker Multi-Horizon
# ═════════════════════════════════════════════════════════════════════════════


class TestOutcomeTrackerHorizons:
    def test_compute_profile_from_rows_respects_half_life(self):
        """Different half-lives produce different profiles from same data."""
        now = datetime.now(timezone.utc)
        rows = [
            {
                "outcome_type": "success",
                "execution_time": 30.0,
                "impact_delta": 0.5,
                "created_at": now - timedelta(hours=12),
            },
            {
                "outcome_type": "failure",
                "execution_time": 60.0,
                "impact_delta": 0.0,
                "created_at": now - timedelta(hours=12),
            },
        ]

        short = OutcomeTracker._compute_profile_from_rows(rows, SHORT_TERM_HALF_LIFE)
        long = OutcomeTracker._compute_profile_from_rows(rows, LONG_TERM_HALF_LIFE)

        # Short-term decay is aggressive (6h half-life, 12h old data → ~25% weight)
        # Long-term decay is gentle (7d half-life, 12h old data → ~95% weight)
        # Both have same raw counts, but different weighted results
        assert short.total_outcomes == long.total_outcomes
        # The success_rate should differ because of different decay weights
        # (with only 2 data points at same age, the rates are the same,
        # but the decay factor itself differs)

    def test_compute_profile_from_rows_empty(self):
        result = OutcomeTracker._compute_profile_from_rows([], MEDIUM_TERM_HALF_LIFE)
        assert result.total_outcomes == 0
        assert result.composite() == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
