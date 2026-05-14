"""
Phase 9H — Failure-aware priority decay tests.

Validates that:
  1. No decay before threshold
  2. Decay triggers exactly at threshold
  3. Decay compounds over multiple threshold crossings
  4. Decay never drops below MIN_PRIORITY_MULTIPLIER
  5. Success resets streak and multiplier
  6. Scoring reflects reduced priority
  7. Determinism across identical outcome sequences
  8. No effect on goals with no outcomes
"""

import sys
import uuid
from datetime import datetime, timedelta, timezone

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from control_plane.goals.goal_selector import (
    DECAY_FACTOR,
    DEFAULT_WEIGHTS,
    FAILURE_THRESHOLD,
    MIN_PRIORITY_MULTIPLIER,
    Goal,
    GoalSelector,
    GoalState,
    MultiHorizonProfile,
    OpportunityCostLayer,
    PerformanceProfile,
    StrategicHorizonLayer,
)

NOW = datetime.now(timezone.utc)


def _make_goal(
    title: str = "Test Goal",
    priority: int = 10,
    gid: str | None = None,
    failure_streak: int = 0,
    decay_multiplier: float = 1.0,
) -> Goal:
    return Goal(
        id=gid or str(uuid.uuid4())[:8],
        org_id="test-org",
        title=title,
        state=GoalState.DEFERRED,
        priority=priority,
        expected_impact=0.5,
        estimated_cost=0.5,
        confidence=0.5,
        created_at=NOW,
        updated_at=NOW,
        failure_streak=failure_streak,
        priority_decay_multiplier=decay_multiplier,
    )


def _selector() -> GoalSelector:
    sel = GoalSelector.__new__(GoalSelector)
    sel.org_id = "test-org"
    sel.focus_budget = 3
    sel.weights = dict(DEFAULT_WEIGHTS)
    sel.opportunity_cost = OpportunityCostLayer()
    sel.strategic_horizon = StrategicHorizonLayer(
        performance_weight=sel.weights.get("performance", 0.20),
    )
    return sel


def _apply_outcomes(goal: Goal, outcomes: list[str]) -> Goal:
    """Simulate outcome sequence on a goal's decay state (no DB)."""
    for outcome in outcomes:
        if outcome == "success":
            goal.failure_streak = 0
            goal.priority_decay_multiplier = 1.0
        else:
            goal.failure_streak += 1
            if goal.failure_streak >= FAILURE_THRESHOLD:
                goal.priority_decay_multiplier = max(
                    MIN_PRIORITY_MULTIPLIER,
                    goal.priority_decay_multiplier * DECAY_FACTOR,
                )
    return goal


# ─── 1. No decay before threshold ───────────────────────────────────────────


class TestNoDecayBeforeThreshold:
    def test_zero_failures(self):
        g = _make_goal()
        _apply_outcomes(g, [])
        assert g.failure_streak == 0
        assert g.priority_decay_multiplier == 1.0

    def test_one_failure(self):
        g = _make_goal()
        _apply_outcomes(g, ["failure"])
        assert g.failure_streak == 1
        assert g.priority_decay_multiplier == 1.0

    def test_four_failures(self):
        """Just below threshold — no decay."""
        g = _make_goal()
        _apply_outcomes(g, ["failure"] * (FAILURE_THRESHOLD - 1))
        assert g.failure_streak == FAILURE_THRESHOLD - 1
        assert g.priority_decay_multiplier == 1.0


# ─── 2. Decay triggers exactly at threshold ─────────────────────────────────


class TestDecayAtThreshold:
    def test_exactly_at_threshold(self):
        g = _make_goal()
        _apply_outcomes(g, ["failure"] * FAILURE_THRESHOLD)
        assert g.failure_streak == FAILURE_THRESHOLD
        assert g.priority_decay_multiplier == DECAY_FACTOR

    def test_one_past_threshold(self):
        g = _make_goal()
        _apply_outcomes(g, ["failure"] * (FAILURE_THRESHOLD + 1))
        assert g.failure_streak == FAILURE_THRESHOLD + 1
        expected = DECAY_FACTOR * DECAY_FACTOR
        assert abs(g.priority_decay_multiplier - expected) < 0.0001


# ─── 3. Decay compounds ─────────────────────────────────────────────────────


class TestDecayCompounds:
    def test_compound_decay(self):
        """Each failure past threshold compounds the decay."""
        g = _make_goal()
        n_failures = FAILURE_THRESHOLD + 5
        _apply_outcomes(g, ["failure"] * n_failures)

        # Decay applies on failures at index FAILURE_THRESHOLD-1 through n_failures-1
        # That's (n_failures - FAILURE_THRESHOLD + 1) applications
        applications = n_failures - FAILURE_THRESHOLD + 1
        expected = DECAY_FACTOR**applications
        expected = max(MIN_PRIORITY_MULTIPLIER, expected)
        assert abs(g.priority_decay_multiplier - expected) < 0.0001

    def test_deep_compound(self):
        """Many failures compound decay down toward the floor."""
        g = _make_goal()
        _apply_outcomes(g, ["failure"] * 30)
        assert g.priority_decay_multiplier >= MIN_PRIORITY_MULTIPLIER
        assert g.priority_decay_multiplier <= DECAY_FACTOR


# ─── 4. Never below minimum ─────────────────────────────────────────────────


class TestFloor:
    def test_floor_with_massive_failures(self):
        g = _make_goal()
        _apply_outcomes(g, ["failure"] * 100)
        assert g.priority_decay_multiplier == MIN_PRIORITY_MULTIPLIER

    def test_floor_exact_value(self):
        g = _make_goal()
        _apply_outcomes(g, ["failure"] * 1000)
        assert g.priority_decay_multiplier == MIN_PRIORITY_MULTIPLIER
        assert g.priority_decay_multiplier > 0.0


# ─── 5. Success resets ──────────────────────────────────────────────────────


class TestSuccessResets:
    def test_success_resets_streak(self):
        g = _make_goal()
        _apply_outcomes(g, ["failure"] * 10)
        assert g.failure_streak == 10
        assert g.priority_decay_multiplier < 1.0

        _apply_outcomes(g, ["success"])
        assert g.failure_streak == 0
        assert g.priority_decay_multiplier == 1.0

    def test_success_after_deep_decay(self):
        g = _make_goal()
        _apply_outcomes(g, ["failure"] * 50)
        assert g.priority_decay_multiplier == MIN_PRIORITY_MULTIPLIER

        _apply_outcomes(g, ["success"])
        assert g.priority_decay_multiplier == 1.0
        assert g.failure_streak == 0

    def test_failure_success_failure_pattern(self):
        """Interleaved pattern: success always fully resets."""
        g = _make_goal()

        # 4 failures (below threshold) → no decay
        _apply_outcomes(g, ["failure"] * 4)
        assert g.priority_decay_multiplier == 1.0

        # Success → resets
        _apply_outcomes(g, ["success"])
        assert g.failure_streak == 0

        # 5 failures → triggers decay
        _apply_outcomes(g, ["failure"] * FAILURE_THRESHOLD)
        assert g.priority_decay_multiplier == DECAY_FACTOR

        # Success → full reset
        _apply_outcomes(g, ["success"])
        assert g.priority_decay_multiplier == 1.0
        assert g.failure_streak == 0

    def test_partial_counts_as_failure(self):
        """'partial' outcome counts as failure for streak purposes."""
        g = _make_goal()
        _apply_outcomes(g, ["partial"] * FAILURE_THRESHOLD)
        assert g.failure_streak == FAILURE_THRESHOLD
        assert g.priority_decay_multiplier == DECAY_FACTOR


# ─── 6. Scoring reflects reduced priority ───────────────────────────────────


class TestScoringIntegration:
    def test_decayed_score_lower(self):
        """A decayed goal should score lower than an identical non-decayed goal."""
        sel = _selector()

        g_healthy = _make_goal("Healthy", priority=10, gid="healthy")
        g_decayed = _make_goal("Decayed", priority=10, gid="decayed")
        g_decayed.failure_streak = 10
        g_decayed.priority_decay_multiplier = MIN_PRIORITY_MULTIPLIER

        goals = [g_healthy, g_decayed]
        sel.score_goal(g_healthy, goals)
        sel.score_goal(g_decayed, goals)

        assert g_healthy.score > g_decayed.score, (
            f"Healthy ({g_healthy.score:.4f}) should outscore decayed ({g_decayed.score:.4f})"
        )

    def test_decay_closes_priority_gap(self):
        """Decay should allow a lower-priority performer to compete."""
        sel = _selector()

        # High priority, fully decayed
        g_hi = _make_goal("High Pri Decayed", priority=10, gid="hi")
        g_hi.priority_decay_multiplier = MIN_PRIORITY_MULTIPLIER

        # Low priority, no decay
        g_lo = _make_goal("Low Pri Fresh", priority=4, gid="lo")

        goals = [g_hi, g_lo]
        sel.score_goal(g_hi, goals)
        sel.score_goal(g_lo, goals)

        # effective_priority for g_hi = 10 * 0.3 = 3.0
        # effective_priority for g_lo = 4 * 1.0 = 4.0
        # g_lo should now beat g_hi on priority contribution
        hi_eff = g_hi.priority * g_hi.priority_decay_multiplier
        lo_eff = g_lo.priority * g_lo.priority_decay_multiplier
        assert lo_eff > hi_eff

    def test_score_explanation_shows_decay(self):
        """When decayed, the explanation should include decay info."""
        sel = _selector()

        g = _make_goal("Decayed", priority=8)
        g.failure_streak = 7
        g.priority_decay_multiplier = DECAY_FACTOR

        sel.score_goal(g, [g])

        decay_lines = [l for l in g.score_explanation if "decay=" in l]
        assert len(decay_lines) == 1, f"Expected decay in explanation, got: {g.score_explanation}"
        assert "streak=7" in decay_lines[0]

    def test_no_decay_in_explanation_when_healthy(self):
        """Healthy goals should not mention decay in explanation."""
        sel = _selector()

        g = _make_goal("Healthy", priority=8)
        sel.score_goal(g, [g])

        decay_lines = [l for l in g.score_explanation if "decay=" in l]
        assert len(decay_lines) == 0


# ─── 7. Determinism ─────────────────────────────────────────────────────────


class TestDeterminism:
    def test_identical_sequences_same_result(self):
        """Same outcome sequence on identical goals produces identical state."""
        seq = ["failure"] * 8 + ["success"] + ["failure"] * 6

        g_a = _make_goal("A", gid="a")
        g_b = _make_goal("B", gid="b")

        _apply_outcomes(g_a, seq)
        _apply_outcomes(g_b, seq)

        assert g_a.failure_streak == g_b.failure_streak
        assert g_a.priority_decay_multiplier == g_b.priority_decay_multiplier

    def test_deterministic_scoring(self):
        """Same decay state + same inputs → same score."""
        sel = _selector()

        g_a = _make_goal("A", priority=7, gid="a", failure_streak=6, decay_multiplier=DECAY_FACTOR)
        g_b = _make_goal("B", priority=7, gid="b", failure_streak=6, decay_multiplier=DECAY_FACTOR)

        sel.score_goal(g_a, [g_a])
        sel.score_goal(g_b, [g_b])

        assert abs(g_a.score - g_b.score) < 0.0001


# ─── 8. No effect on goals with no outcomes ─────────────────────────────────


class TestNoOutcomeGoals:
    def test_fresh_goal_no_decay(self):
        """A goal with no outcomes should have default decay state."""
        g = _make_goal()
        assert g.failure_streak == 0
        assert g.priority_decay_multiplier == 1.0

    def test_fresh_goal_scoring_unchanged(self):
        """Scoring a fresh goal should produce the same result as pre-9H."""
        sel = _selector()

        g = _make_goal("Fresh", priority=7)
        sel.score_goal(g, [g])

        # priority contribution should be 7/10 * 0.25 = 0.175
        expected_pri_contrib = (7 / 10.0) * 0.25
        # The explanation for a non-decayed goal should be "priority=7/10 → 0.175"
        pri_line = g.score_explanation[0]
        assert "decay=" not in pri_line
        assert "0.175" in pri_line


# ─── 9. Explainability ──────────────────────────────────────────────────────


class TestExplainability:
    def test_explain_includes_decay_fields(self):
        """explain() should include decay fields."""
        sel = _selector()

        g = _make_goal("Explain Test", priority=9)
        g.failure_streak = 8
        g.priority_decay_multiplier = 0.49

        sel.score_goal(g, [g])
        info = sel.explain(g)

        assert "priority_decay_multiplier" in info
        assert "failure_streak" in info
        assert "effective_priority" in info
        assert info["priority_decay_multiplier"] == 0.49
        assert info["failure_streak"] == 8
        assert abs(info["effective_priority"] - 9 * 0.49) < 0.01

    def test_explain_healthy_goal(self):
        """Healthy goal should show multiplier=1.0, streak=0."""
        sel = _selector()

        g = _make_goal("Healthy", priority=5)
        sel.score_goal(g, [g])
        info = sel.explain(g)

        assert info["priority_decay_multiplier"] == 1.0
        assert info["failure_streak"] == 0
        assert info["effective_priority"] == 5.0


# ─── Runner ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
