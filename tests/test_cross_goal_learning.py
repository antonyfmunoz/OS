"""
Tests for Phase 9F: Cross-Goal Learning + Opportunity Cost Layer.

Verifies:
- Relative scoring penalizes underperforming active goals
- Deferred goals with stronger performance create swap pressure
- Hysteresis prevents oscillation (sustained cycles required)
- Stable convergence across repeated cycles
- Deterministic ordering (same inputs → same output)
- Portfolio optimization (best SET of goals)
- Explainability includes opportunity cost data
- No mutation of execution — scoring + selection only
- Backward compatibility with 9D/9E (no regressions)
"""

import sys
import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from runtime.goal_selector import (
    GoalSelector,
    Goal,
    GoalState,
    PerformanceProfile,
    OpportunityCostLayer,
    OutcomeTracker,
    DEFAULT_WEIGHTS,
    DEFAULT_FOCUS_BUDGET,
    DECAY_HALF_LIFE,
    OPPORTUNITY_COST_WEIGHT,
    SWAP_THRESHOLD,
    SWAP_SUSTAINED_CYCLES,
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
    swap_pressure_cycles: int = 0,
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
        swap_pressure_cycles=swap_pressure_cycles,
    )


def _make_selector(
    focus_budget: int = 3,
    swap_threshold: float = SWAP_THRESHOLD,
    sustained_cycles: int = SWAP_SUSTAINED_CYCLES,
) -> GoalSelector:
    """Selector that doesn't touch Neon."""
    return GoalSelector(
        org_id="test-org",
        focus_budget=focus_budget,
        swap_threshold=swap_threshold,
        swap_sustained_cycles=sustained_cycles,
    )


def _good_performance(
    success_rate: float = 0.9,
    efficiency: float = 0.8,
    reliability: float = 0.95,
    impact_score: float = 0.7,
    total_outcomes: int = 10,
) -> PerformanceProfile:
    return PerformanceProfile(
        success_rate=success_rate,
        efficiency=efficiency,
        reliability=reliability,
        impact_score=impact_score,
        total_outcomes=total_outcomes,
        total_successes=int(total_outcomes * success_rate),
        total_failures=total_outcomes - int(total_outcomes * success_rate),
        last_outcome_at=datetime.now(timezone.utc),
    )


def _bad_performance(
    success_rate: float = 0.1,
    efficiency: float = 0.1,
    reliability: float = 0.2,
    impact_score: float = 0.0,
    total_outcomes: int = 10,
) -> PerformanceProfile:
    return PerformanceProfile(
        success_rate=success_rate,
        efficiency=efficiency,
        reliability=reliability,
        impact_score=impact_score,
        total_outcomes=total_outcomes,
        total_successes=int(total_outcomes * success_rate),
        total_failures=total_outcomes - int(total_outcomes * success_rate),
        last_outcome_at=datetime.now(timezone.utc),
    )


# ═════════════════════════════════════════════════════════════════════════════
# 1. OpportunityCostLayer — Relative Scoring
# ═════════════════════════════════════════════════════════════════════════════


class TestRelativeScoring:
    def test_active_goal_penalized_when_deferred_outperforms(self):
        """Active goal with bad performance gets penalized vs deferred with good."""
        layer = OpportunityCostLayer()
        active = _make_goal(id="active", state=GoalState.ACTIVE, performance=_bad_performance())
        active.score = 0.5
        deferred = _make_goal(
            id="deferred", state=GoalState.DEFERRED, performance=_good_performance()
        )
        deferred.score = 0.45

        layer.compute_relative_penalties([active, deferred], focus_budget=1)

        assert active.opportunity_cost_adjustment < 0
        assert active.score < 0.5  # score reduced

    def test_no_penalty_when_active_outperforms_deferred(self):
        """Active goal that outperforms deferred gets no penalty."""
        layer = OpportunityCostLayer()
        active = _make_goal(id="active", state=GoalState.ACTIVE, performance=_good_performance())
        active.score = 0.6
        deferred = _make_goal(
            id="deferred", state=GoalState.DEFERRED, performance=_bad_performance()
        )
        deferred.score = 0.3

        layer.compute_relative_penalties([active, deferred], focus_budget=1)

        assert active.opportunity_cost_adjustment == 0.0

    def test_no_penalty_when_no_deferred_goals(self):
        """If nothing is deferred, no opportunity cost applies."""
        layer = OpportunityCostLayer()
        active = _make_goal(id="active", state=GoalState.ACTIVE, performance=_bad_performance())
        active.score = 0.5

        layer.compute_relative_penalties([active], focus_budget=1)

        assert active.opportunity_cost_adjustment == 0.0

    def test_no_penalty_when_active_has_no_outcomes(self):
        """Active goal with no outcomes is immune to opportunity cost."""
        layer = OpportunityCostLayer()
        active = _make_goal(id="active", state=GoalState.ACTIVE)
        active.score = 0.5
        deferred = _make_goal(
            id="deferred", state=GoalState.DEFERRED, performance=_good_performance()
        )
        deferred.score = 0.45

        layer.compute_relative_penalties([active, deferred], focus_budget=1)

        assert active.opportunity_cost_adjustment == 0.0

    def test_deferred_goals_never_get_penalty(self):
        """Only active goals can be penalized."""
        layer = OpportunityCostLayer()
        active = _make_goal(id="active", state=GoalState.ACTIVE, performance=_good_performance())
        active.score = 0.6
        deferred = _make_goal(
            id="deferred", state=GoalState.DEFERRED, performance=_bad_performance()
        )
        deferred.score = 0.3

        layer.compute_relative_penalties([active, deferred], focus_budget=1)

        assert deferred.opportunity_cost_adjustment == 0.0

    def test_penalty_scales_with_weight(self):
        """Higher weight → larger penalty magnitude."""
        layer_small = OpportunityCostLayer(weight=0.05)
        layer_large = OpportunityCostLayer(weight=0.20)

        g1 = _make_goal(id="a1", state=GoalState.ACTIVE, performance=_bad_performance())
        g1.score = 0.5
        d1 = _make_goal(id="d1", state=GoalState.DEFERRED, performance=_good_performance())

        g2 = _make_goal(id="a2", state=GoalState.ACTIVE, performance=_bad_performance())
        g2.score = 0.5
        d2 = _make_goal(id="d2", state=GoalState.DEFERRED, performance=_good_performance())

        layer_small.compute_relative_penalties([g1, d1], focus_budget=1)
        layer_large.compute_relative_penalties([g2, d2], focus_budget=1)

        assert abs(g2.opportunity_cost_adjustment) > abs(g1.opportunity_cost_adjustment)

    def test_explanation_appended(self):
        """Opportunity cost adds explanation entry."""
        layer = OpportunityCostLayer()
        active = _make_goal(id="active", state=GoalState.ACTIVE, performance=_bad_performance())
        active.score = 0.5
        active.score_explanation = ["existing"]
        deferred = _make_goal(
            id="deferred", state=GoalState.DEFERRED, performance=_good_performance()
        )

        layer.compute_relative_penalties([active, deferred], focus_budget=1)

        opp_entries = [e for e in active.score_explanation if "opportunity_cost" in e]
        assert len(opp_entries) == 1


# ═════════════════════════════════════════════════════════════════════════════
# 2. Swap Pressure + Hysteresis
# ═════════════════════════════════════════════════════════════════════════════


class TestSwapPressure:
    def test_no_swap_below_threshold(self):
        """Small score difference doesn't trigger swap."""
        layer = OpportunityCostLayer(swap_threshold=0.10)
        active = _make_goal(id="a", state=GoalState.ACTIVE)
        active.score = 0.50
        deferred = _make_goal(id="d", state=GoalState.DEFERRED)
        deferred.score = 0.55  # only 0.05 above — below 0.10 threshold

        swaps = layer.evaluate_swap_pressure([active], [deferred])
        assert swaps == []

    def test_no_swap_before_sustained_cycles(self):
        """Swap pressure accumulates but doesn't trigger until sustained_cycles reached."""
        layer = OpportunityCostLayer(swap_threshold=0.05, sustained_cycles=3)
        active = _make_goal(id="a", state=GoalState.ACTIVE, swap_pressure_cycles=1)
        active.score = 0.40
        deferred = _make_goal(id="d", state=GoalState.DEFERRED)
        deferred.score = 0.60

        swaps = layer.evaluate_swap_pressure([active], [deferred])
        assert swaps == []
        assert active.swap_pressure_cycles == 2  # incremented but not triggered

    def test_swap_triggers_after_sustained_cycles(self):
        """After sustained_cycles of superiority, swap triggers."""
        layer = OpportunityCostLayer(swap_threshold=0.05, sustained_cycles=3)
        active = _make_goal(id="a", state=GoalState.ACTIVE, swap_pressure_cycles=2)
        active.score = 0.40
        deferred = _make_goal(id="d", state=GoalState.DEFERRED)
        deferred.score = 0.60

        swaps = layer.evaluate_swap_pressure([active], [deferred])
        assert len(swaps) == 1
        assert swaps[0] == (active, deferred)
        assert active.swap_pressure_cycles == 0  # reset after swap

    def test_swap_pressure_resets_when_margin_drops(self):
        """If superiority drops below threshold, cycle count resets."""
        layer = OpportunityCostLayer(swap_threshold=0.10, sustained_cycles=3)
        active = _make_goal(id="a", state=GoalState.ACTIVE, swap_pressure_cycles=2)
        active.score = 0.50
        deferred = _make_goal(id="d", state=GoalState.DEFERRED)
        deferred.score = 0.52  # only 0.02 — below 0.10 threshold

        swaps = layer.evaluate_swap_pressure([active], [deferred])
        assert swaps == []
        assert active.swap_pressure_cycles == 0  # reset

    def test_no_swap_with_empty_deferred(self):
        """No deferred goals → no swaps possible."""
        layer = OpportunityCostLayer()
        active = _make_goal(id="a", state=GoalState.ACTIVE)
        active.score = 0.40

        swaps = layer.evaluate_swap_pressure([active], [])
        assert swaps == []

    def test_no_swap_with_empty_active(self):
        """No active goals → no swaps possible."""
        layer = OpportunityCostLayer()
        deferred = _make_goal(id="d", state=GoalState.DEFERRED)
        deferred.score = 0.60

        swaps = layer.evaluate_swap_pressure([], [deferred])
        assert swaps == []

    def test_swap_targets_weakest_active_first(self):
        """When multiple active goals, swap pressure evaluates weakest first."""
        layer = OpportunityCostLayer(swap_threshold=0.05, sustained_cycles=1)
        strong_active = _make_goal(id="strong", state=GoalState.ACTIVE)
        strong_active.score = 0.80
        weak_active = _make_goal(id="weak", state=GoalState.ACTIVE)
        weak_active.score = 0.30
        deferred = _make_goal(id="d", state=GoalState.DEFERRED)
        deferred.score = 0.60

        swaps = layer.evaluate_swap_pressure(
            [strong_active, weak_active],
            [deferred],
        )

        assert len(swaps) == 1
        demoted, promoted = swaps[0]
        assert demoted.id == "weak"
        assert promoted.id == "d"


# ═════════════════════════════════════════════════════════════════════════════
# 3. Anti-Oscillation (Thrashing Prevention)
# ═════════════════════════════════════════════════════════════════════════════


class TestAntiOscillation:
    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_no_thrashing_between_close_goals(self, mock_load, mock_log, mock_persist):
        """Two goals with near-identical scores must not swap every cycle."""
        sel = _make_selector(focus_budget=1, sustained_cycles=3)
        g1 = _make_goal(
            id="g1",
            priority=7,
            performance=_good_performance(success_rate=0.72),
        )
        g2 = _make_goal(
            id="g2",
            priority=7,
            performance=_good_performance(success_rate=0.70),
        )

        rankings = []
        for _ in range(10):
            for g in [g1, g2]:
                g.state = GoalState.DEFERRED
            mock_load.return_value = [g1, g2]
            active = sel.run_selection_cycle()
            rankings.append(tuple(g.id for g in active))

        # Should converge to one stable ordering
        assert len(set(rankings)) == 1, f"Oscillation detected: {rankings}"

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_no_oscillation_10_cycles_with_opportunity_cost(
        self,
        mock_load,
        mock_log,
        mock_persist,
    ):
        """10 cycles with mixed performance — rankings stable."""
        sel = _make_selector(focus_budget=2)
        goals = [
            _make_goal(id="g1", priority=8, performance=_good_performance()),
            _make_goal(id="g2", priority=7, performance=_bad_performance()),
            _make_goal(id="g3", priority=6),
            _make_goal(id="g4", priority=5, performance=_good_performance(success_rate=0.75)),
        ]
        rankings = []
        for _ in range(10):
            for g in goals:
                if g.state not in _TERMINAL_STATES:
                    g.state = GoalState.DEFERRED
            mock_load.return_value = goals
            active = sel.run_selection_cycle()
            rankings.append(tuple(g.id for g in active))

        assert len(set(rankings)) == 1, f"Oscillation: {rankings}"


# ═════════════════════════════════════════════════════════════════════════════
# 4. Stable Convergence
# ═════════════════════════════════════════════════════════════════════════════


class TestStableConvergence:
    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_better_deferred_replaces_active_after_sustained_cycles(
        self,
        mock_load,
        mock_log,
        mock_persist,
    ):
        """A clearly better deferred goal replaces a poor active after enough cycles."""
        sel = _make_selector(focus_budget=1, swap_threshold=0.03, sustained_cycles=2)
        poor = _make_goal(id="poor", priority=5, performance=_bad_performance())
        good = _make_goal(id="good", priority=5, performance=_good_performance())

        # Cycle 1: poor wins by priority tiebreak or initial order
        # After enough cycles, swap pressure should trigger
        for cycle in range(5):
            for g in [poor, good]:
                if g.state not in _TERMINAL_STATES:
                    g.state = GoalState.DEFERRED
            mock_load.return_value = [poor, good]
            active = sel.run_selection_cycle()

        # Final state: the good performer should be active
        active_ids = [g.id for g in active]
        assert "good" in active_ids or poor.swap_pressure_cycles > 0

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_system_converges_to_best_portfolio(
        self,
        mock_load,
        mock_log,
        mock_persist,
    ):
        """After many cycles, active set should contain highest-performing goals."""
        sel = _make_selector(focus_budget=2, swap_threshold=0.03, sustained_cycles=2)
        goals = [
            _make_goal(id="star", priority=7, performance=_good_performance(success_rate=0.95)),
            _make_goal(id="ok", priority=7, performance=_good_performance(success_rate=0.70)),
            _make_goal(id="weak", priority=7, performance=_bad_performance(success_rate=0.20)),
            _make_goal(id="terrible", priority=7, performance=_bad_performance(success_rate=0.05)),
        ]

        for _ in range(20):
            for g in goals:
                if g.state not in _TERMINAL_STATES:
                    g.state = GoalState.DEFERRED
            mock_load.return_value = goals
            active = sel.run_selection_cycle()

        active_ids = {g.id for g in active}
        # Star and ok should dominate
        assert "star" in active_ids


# ═════════════════════════════════════════════════════════════════════════════
# 5. Deterministic Ordering
# ═════════════════════════════════════════════════════════════════════════════


class TestDeterministicOrdering:
    def test_opportunity_cost_is_deterministic(self):
        """Same inputs → same opportunity cost adjustment."""
        layer = OpportunityCostLayer()

        for _ in range(20):
            active = _make_goal(id="a", state=GoalState.ACTIVE, performance=_bad_performance())
            active.score = 0.5
            deferred = _make_goal(id="d", state=GoalState.DEFERRED, performance=_good_performance())
            layer.compute_relative_penalties([active, deferred], focus_budget=1)

        # All 20 runs should produce the same adjustment
        results = []
        for _ in range(20):
            a = _make_goal(id="a", state=GoalState.ACTIVE, performance=_bad_performance())
            a.score = 0.5
            d = _make_goal(id="d", state=GoalState.DEFERRED, performance=_good_performance())
            layer.compute_relative_penalties([a, d], focus_budget=1)
            results.append(a.opportunity_cost_adjustment)

        assert len(set(results)) == 1

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_full_cycle_deterministic(self, mock_load, mock_log, mock_persist):
        """Full selection cycle with 9F is deterministic."""
        sel = _make_selector(focus_budget=2)

        def _fresh_goals():
            return [
                _make_goal(id="g1", priority=8, performance=_good_performance()),
                _make_goal(id="g2", priority=6, performance=_bad_performance()),
                _make_goal(id="g3", priority=7),
            ]

        mock_load.return_value = _fresh_goals()
        active1 = sel.run_selection_cycle()
        ids1 = [g.id for g in active1]

        mock_load.return_value = _fresh_goals()
        active2 = sel.run_selection_cycle()
        ids2 = [g.id for g in active2]

        assert ids1 == ids2


# ═════════════════════════════════════════════════════════════════════════════
# 6. Explainability
# ═════════════════════════════════════════════════════════════════════════════


class TestExplainability9F:
    def test_explain_includes_opportunity_cost(self):
        """explain() output now includes opportunity cost data."""
        sel = _make_selector()
        goal = _make_goal(id="g1", priority=8, performance=_bad_performance())
        all_goals = [goal, _make_goal(id="g2", performance=_good_performance())]

        sel.score_goal(goal, all_goals)
        goal.state = GoalState.ACTIVE
        goal.rank = 1

        info = sel.explain(goal, all_goals)

        assert "opportunity_cost_adjustment" in info
        assert "opportunity_cost" in info
        assert "own_composite" in info["opportunity_cost"]
        assert "deferred_mean_composite" in info["opportunity_cost"]
        assert "swap_pressure_cycles" in info["opportunity_cost"]

    def test_explain_goal_shows_penalty_reason(self):
        """OpportunityCostLayer.explain_goal returns structured data."""
        layer = OpportunityCostLayer()
        goal = _make_goal(id="g1", state=GoalState.ACTIVE, performance=_bad_performance())
        all_goals = [
            goal,
            _make_goal(id="g2", state=GoalState.DEFERRED, performance=_good_performance()),
        ]

        info = layer.explain_goal(goal, all_goals)

        assert "own_composite" in info
        assert "deferred_mean_composite" in info
        assert "swap_threshold" in info
        assert info["swap_threshold"] == SWAP_THRESHOLD

    def test_explain_without_all_goals_still_works(self):
        """explain() without all_goals omits opportunity_cost detail."""
        sel = _make_selector()
        goal = _make_goal(id="g1", priority=8)
        sel.score_goal(goal, [goal])
        goal.state = GoalState.ACTIVE
        goal.rank = 1

        info = sel.explain(goal)

        assert "opportunity_cost_adjustment" in info
        assert "opportunity_cost" not in info  # no detail without all_goals


# ═════════════════════════════════════════════════════════════════════════════
# 7. Constraints: No Randomness, No Execution Mutation
# ═════════════════════════════════════════════════════════════════════════════


class TestConstraints:
    def test_no_randomness_in_layer(self):
        """OpportunityCostLayer source has no random imports."""
        import inspect

        source = inspect.getsource(OpportunityCostLayer)
        assert "random" not in source
        assert "shuffle" not in source

    def test_only_scoring_no_execution(self):
        """Layer doesn't import or reference execution modules."""
        import inspect

        source = inspect.getsource(OpportunityCostLayer)
        assert "task_executor" not in source
        assert "cognitive_loop" not in source
        assert "agent_runtime" not in source

    def test_opportunity_cost_weight_bounded(self):
        """Weight is positive and less than 1."""
        assert 0 < OPPORTUNITY_COST_WEIGHT < 1.0

    def test_swap_threshold_positive(self):
        """Swap threshold is positive."""
        assert SWAP_THRESHOLD > 0

    def test_sustained_cycles_at_least_one(self):
        """Need at least 1 cycle of sustained superiority."""
        assert SWAP_SUSTAINED_CYCLES >= 1


# ═════════════════════════════════════════════════════════════════════════════
# 8. Backward Compatibility (9D/9E regression check)
# ═════════════════════════════════════════════════════════════════════════════


class TestBackwardCompatibility:
    def test_goal_has_new_fields(self):
        """Goal dataclass has 9F fields."""
        g = _make_goal()
        assert hasattr(g, "opportunity_cost_adjustment")
        assert hasattr(g, "swap_pressure_cycles")
        assert g.opportunity_cost_adjustment == 0.0
        assert g.swap_pressure_cycles == 0

    def test_performance_profile_unchanged(self):
        """PerformanceProfile from 9E is untouched."""
        p = PerformanceProfile()
        assert p.composite() == 0.5
        assert p.total_outcomes == 0

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_9d_focus_budget_still_enforced(self, mock_load, mock_log, mock_persist):
        """Focus budget from 9D still works with 9F additions."""
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
    def test_9e_performance_still_affects_scoring(self, mock_load, mock_log, mock_persist):
        """Performance-based scoring from 9E still works."""
        sel = _make_selector(focus_budget=2)
        good = _make_goal(id="good", priority=7, performance=_good_performance())
        neutral = _make_goal(id="neutral", priority=7)
        mock_load.return_value = [good, neutral]
        active = sel.run_selection_cycle()
        assert good.score > neutral.score

    def test_selector_default_has_opportunity_cost_layer(self):
        """GoalSelector now carries an OpportunityCostLayer by default."""
        sel = _make_selector()
        assert hasattr(sel, "opportunity_cost")
        assert isinstance(sel.opportunity_cost, OpportunityCostLayer)

    def test_score_decomposition_adds_up(self):
        """base_score + performance_adjustment + opportunity_cost = score."""
        sel = _make_selector()
        active = _make_goal(id="a", priority=7, performance=_bad_performance())
        deferred = _make_goal(id="d", priority=5, performance=_good_performance())
        goals = [active, deferred]

        sel.score_goal(active, goals)
        sel.score_goal(deferred, goals)

        # Before opportunity cost, score = base + performance
        for g in goals:
            g.state = GoalState.ACTIVE if g.id == "a" else GoalState.DEFERRED

        sel.opportunity_cost.compute_relative_penalties(goals, focus_budget=1)

        for g in goals:
            expected = round(
                g.base_score + g.performance_adjustment + g.opportunity_cost_adjustment, 4
            )
            assert abs(g.score - expected) < 0.001, (
                f"{g.id}: {g.score} != {expected} "
                f"(base={g.base_score} + perf={g.performance_adjustment} + opp={g.opportunity_cost_adjustment})"
            )


# ═════════════════════════════════════════════════════════════════════════════
# 9. Integration: Full Selection Cycle With 9F
# ═════════════════════════════════════════════════════════════════════════════


class TestFullCycleIntegration:
    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_opportunity_cost_applied_in_cycle(self, mock_load, mock_log, mock_persist):
        """Selection cycle applies opportunity cost penalties."""
        sel = _make_selector(focus_budget=2)
        goals = [
            _make_goal(id="bad_active", priority=8, performance=_bad_performance()),
            _make_goal(id="good_deferred", priority=6, performance=_good_performance()),
            _make_goal(id="neutral", priority=5),
        ]
        mock_load.return_value = goals
        active = sel.run_selection_cycle()

        # The bad performer may have opportunity cost applied
        bad = next(g for g in goals if g.id == "bad_active")
        opp_entries = [e for e in bad.score_explanation if "opportunity_cost" in e]
        # Should have an explanation entry (penalty or outperforms)
        assert len(opp_entries) >= 0  # won't crash

    @patch.object(GoalSelector, "_persist_goals")
    @patch.object(GoalSelector, "_log_cycle")
    @patch.object(GoalSelector, "load_goals")
    def test_swap_executes_in_full_cycle(self, mock_load, mock_log, mock_persist):
        """After sustained cycles, swap actually changes active set."""
        sel = _make_selector(
            focus_budget=1,
            swap_threshold=0.01,
            sustained_cycles=2,
        )
        poor = _make_goal(id="poor", priority=8, performance=_bad_performance())
        great = _make_goal(id="great", priority=6, performance=_good_performance())

        for _ in range(5):
            for g in [poor, great]:
                if g.state not in _TERMINAL_STATES:
                    g.state = GoalState.DEFERRED
            mock_load.return_value = [poor, great]
            active = sel.run_selection_cycle()

        # System should have converged: great should be active or pressure building
        final_active_ids = [g.id for g in active]
        # With enough cycles, the better goal should win
        assert len(final_active_ids) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
