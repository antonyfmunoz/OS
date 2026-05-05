"""Tests for the deterministic exploration engine.

Validates:
1. Deterministic behavior — same inputs → same signal.
2. Correct triggering — degrading/low-confidence/failure-streak activate exploration.
3. Faster adaptation vs baseline — exploration system adapts faster in shifting scenarios.
4. No regression in static env — exploration doesn't hurt converged systems.
5. Bounded adjustments — penalties and boosts within specified limits.
6. No randomness — re-runs produce identical results.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.exploration_engine import (
    CONFIDENCE_THRESHOLD,
    FAILURE_STREAK_THRESHOLD,
    NO_EXPLORATION,
    ExplorationSignal,
    apply_exploration_adjustments,
    compute_exploration_signal,
)
from umh.runtime_engine.benchmark_env import (
    AdversarialScenario,
    EOSDecisionSystem,
    EOSWithExplorationSystem,
    ShiftingScenario,
    StaticScenario,
    NoisyScenario,
    run_simulation,
)


# ─── Deterministic behavior ──────────────────────────────────────


def test_deterministic_same_inputs():
    """Same inputs → same signal."""
    scores = {"a": 0.8, "b": 0.3, "c": 0.1}
    s1 = compute_exploration_signal(
        plan_confidence=0.2,
        objective_trend="degrading",
        failure_streak=3,
        strategy_scores=scores,
    )
    s2 = compute_exploration_signal(
        plan_confidence=0.2,
        objective_trend="degrading",
        failure_streak=3,
        strategy_scores=scores,
    )
    assert s1.exploration_active == s2.exploration_active
    assert s1.exploration_adjustments == s2.exploration_adjustments
    assert s1.exploration_reason == s2.exploration_reason
    assert s1.activation_strength == s2.activation_strength


def test_no_randomness_across_runs():
    """Re-running exploration engine 100 times produces identical results."""
    scores = {"x": 0.5, "y": 0.5, "z": 0.5}
    results = []
    for _ in range(100):
        s = compute_exploration_signal(
            plan_confidence=0.1,
            objective_trend="degrading",
            failure_streak=4,
            strategy_scores=scores,
        )
        results.append(s.to_dict())
    assert all(r == results[0] for r in results)


# ─── Correct triggering ──────────────────────────────────────────


def test_degrading_trend_triggers():
    """Degrading objective trend should activate exploration."""
    s = compute_exploration_signal(
        plan_confidence=0.8,
        objective_trend="degrading",
        failure_streak=0,
        strategy_scores={"a": 0.9, "b": 0.3},
    )
    assert s.exploration_active is True
    assert "degrading_trend" in s.exploration_reason


def test_low_confidence_triggers():
    """Low plan confidence should activate exploration."""
    s = compute_exploration_signal(
        plan_confidence=0.1,
        objective_trend="improving",
        failure_streak=0,
        strategy_scores={"a": 0.9, "b": 0.3},
    )
    assert s.exploration_active is True
    assert "low_confidence" in s.exploration_reason


def test_failure_streak_triggers():
    """Consecutive failures above threshold should activate exploration."""
    s = compute_exploration_signal(
        plan_confidence=0.8,
        objective_trend="improving",
        failure_streak=FAILURE_STREAK_THRESHOLD + 1,
        strategy_scores={"a": 0.9, "b": 0.3},
    )
    assert s.exploration_active is True
    assert "failure_streak" in s.exploration_reason


def test_high_uncertainty_triggers():
    """Equal strategy scores (high uncertainty) should activate exploration."""
    s = compute_exploration_signal(
        plan_confidence=0.8,
        objective_trend="improving",
        failure_streak=0,
        strategy_scores={"a": 0.5, "b": 0.5, "c": 0.5, "d": 0.5},
    )
    assert s.exploration_active is True
    assert "high_uncertainty" in s.exploration_reason


def test_no_trigger_when_stable():
    """Good conditions should not trigger exploration."""
    s = compute_exploration_signal(
        plan_confidence=0.9,
        objective_trend="improving",
        failure_streak=0,
        strategy_scores={"a": 0.95, "b": 0.05},
    )
    assert s.exploration_active is False


def test_no_trigger_single_strategy():
    """Single strategy cannot explore — nothing to boost."""
    s = compute_exploration_signal(
        plan_confidence=0.1,
        objective_trend="degrading",
        failure_streak=5,
        strategy_scores={"only_one": 0.5},
    )
    assert s.exploration_active is False


def test_no_trigger_empty_scores():
    """Empty strategy scores → no exploration."""
    s = compute_exploration_signal(
        plan_confidence=0.1,
        objective_trend="degrading",
        failure_streak=5,
        strategy_scores={},
    )
    assert s.exploration_active is False


def test_no_trigger_none_scores():
    """None strategy scores → no exploration."""
    s = compute_exploration_signal(
        plan_confidence=0.1,
        objective_trend="degrading",
        failure_streak=5,
        strategy_scores=None,
    )
    assert s.exploration_active is False


# ─── Bounded adjustments ─────────────────────────────────────────


def test_penalty_bounded():
    """Top strategy penalty must not exceed 50% of its score (hard bound)."""
    s = compute_exploration_signal(
        plan_confidence=0.0,
        objective_trend="degrading",
        failure_streak=10,
        strategy_scores={"a": 1.0, "b": 0.0, "c": 0.0},
    )
    if s.exploration_active:
        penalty = abs(s.exploration_adjustments.get("a", 0.0))
        assert penalty <= 1.0 * 0.5 + 1e-9, (
            f"Penalty {penalty} exceeds 50% of top score"
        )


def test_boost_budget_equals_penalty():
    """Total boost to alternatives equals the penalty taken from top."""
    s = compute_exploration_signal(
        plan_confidence=0.0,
        objective_trend="degrading",
        failure_streak=10,
        strategy_scores={"a": 1.0, "b": 0.0},
    )
    if s.exploration_active:
        penalty = abs(s.exploration_adjustments.get("a", 0.0))
        total_boost = sum(v for v in s.exploration_adjustments.values() if v > 0)
        assert abs(total_boost - penalty) < 1e-9, "Budget not conserved"


def test_total_redistribution_conservative():
    """Total redistribution should not exceed the penalty applied."""
    s = compute_exploration_signal(
        plan_confidence=0.0,
        objective_trend="degrading",
        failure_streak=10,
        strategy_scores={"a": 1.0, "b": 0.0, "c": 0.0, "d": 0.0},
    )
    if s.exploration_active:
        penalty = abs(s.exploration_adjustments.get("a", 0.0))
        total_boost = sum(v for v in s.exploration_adjustments.values() if v > 0)
        assert total_boost <= penalty + 1e-9


def test_scores_remain_nonnegative():
    """After applying adjustments, no score goes below 0."""
    scores = {"a": 0.01, "b": 0.005, "c": 0.001}
    s = compute_exploration_signal(
        plan_confidence=0.0,
        objective_trend="degrading",
        failure_streak=5,
        strategy_scores=scores,
    )
    adjusted = apply_exploration_adjustments(scores, s)
    for v in adjusted.values():
        assert v >= 0.0


# ─── apply_exploration_adjustments ────────────────────────────────


def test_apply_no_exploration_returns_copy():
    """When not active, returns exact copy of scores."""
    scores = {"a": 0.5, "b": 0.3}
    adjusted = apply_exploration_adjustments(scores, NO_EXPLORATION)
    assert adjusted == scores
    scores["a"] = 999.0
    assert adjusted["a"] == 0.5


def test_apply_adjustments_additive():
    """Adjustments are additive to original scores."""
    scores = {"a": 0.8, "b": 0.2}
    signal = ExplorationSignal(
        exploration_active=True,
        exploration_adjustments={"a": -0.02, "b": 0.02},
        exploration_reason="test",
        candidates_boosted=("b",),
        activation_strength=0.5,
    )
    adjusted = apply_exploration_adjustments(scores, signal)
    assert abs(adjusted["a"] - 0.78) < 1e-9
    assert abs(adjusted["b"] - 0.22) < 1e-9


# ─── Benchmark integration: no regression in static ──────────────


def test_no_regression_static():
    """Exploration engine must not degrade static scenario performance."""
    baseline = EOSDecisionSystem()
    explore = EOSWithExplorationSystem()
    scenario = StaticScenario()

    m_base = run_simulation(baseline, scenario, steps=100, seed=42)
    m_explore = run_simulation(explore, scenario, steps=100, seed=42)

    assert m_explore.avg_reward >= m_base.avg_reward - 0.05, (
        f"Regression: explore={m_explore.avg_reward:.4f} vs base={m_base.avg_reward:.4f}"
    )


def test_no_regression_noisy():
    """Exploration engine must not degrade noisy scenario performance."""
    baseline = EOSDecisionSystem()
    explore = EOSWithExplorationSystem()
    scenario = NoisyScenario()

    m_base = run_simulation(baseline, scenario, steps=100, seed=42)
    m_explore = run_simulation(explore, scenario, steps=100, seed=42)

    assert m_explore.avg_reward >= m_base.avg_reward - 0.05, (
        f"Regression: explore={m_explore.avg_reward:.4f} vs base={m_base.avg_reward:.4f}"
    )


# ─── Benchmark integration: faster adaptation ────────────────────


def test_faster_adaptation_shifting():
    """Exploration system should adapt faster in shifting scenario."""
    baseline = EOSDecisionSystem()
    explore = EOSWithExplorationSystem()
    scenario = ShiftingScenario(shift_step=50)

    m_base = run_simulation(baseline, scenario, steps=100, seed=42)
    m_explore = run_simulation(explore, scenario, steps=100, seed=42)

    base_late = m_base.late_avg_reward
    explore_late = m_explore.late_avg_reward

    assert explore_late >= base_late - 0.05, (
        f"Exploration did not help: explore_late={explore_late:.4f} vs base_late={base_late:.4f}"
    )


def test_faster_adaptation_adversarial():
    """Exploration system should handle adversarial scenario at least as well."""
    baseline = EOSDecisionSystem()
    explore = EOSWithExplorationSystem()
    scenario = AdversarialScenario()

    m_base = run_simulation(baseline, scenario, steps=120, seed=42)
    m_explore = run_simulation(explore, scenario, steps=120, seed=42)

    assert m_explore.avg_reward >= m_base.avg_reward - 0.05, (
        f"Exploration regressed: explore={m_explore.avg_reward:.4f} vs base={m_base.avg_reward:.4f}"
    )


# ─── Exploration system determinism in benchmark ─────────────────


def test_exploration_benchmark_deterministic():
    """Exploration system produces identical results across runs."""
    explore1 = EOSWithExplorationSystem()
    explore2 = EOSWithExplorationSystem()
    scenario = ShiftingScenario()

    m1 = run_simulation(explore1, scenario, steps=50, seed=42)
    m2 = run_simulation(explore2, scenario, steps=50, seed=42)

    assert m1.rewards == m2.rewards
    assert m1.actions_chosen == m2.actions_chosen


# ─── ExplorationSignal.to_dict ────────────────────────────────────


def test_signal_to_dict():
    """to_dict produces expected structure."""
    s = compute_exploration_signal(
        plan_confidence=0.1,
        objective_trend="degrading",
        failure_streak=3,
        strategy_scores={"a": 0.8, "b": 0.2},
    )
    d = s.to_dict()
    assert "exploration_active" in d
    assert "exploration_adjustments" in d
    assert "exploration_reason" in d
    assert "candidates_boosted" in d
    assert "activation_strength" in d
    assert isinstance(d["candidates_boosted"], list)


# ─── DecisionTrace integration ────────────────────────────────────


def test_decision_trace_fields():
    """DecisionTrace accepts the new exploration fields."""
    from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

    trace = build_trace(
        turn_id=1,
        det_exploration_active=True,
        det_exploration_adjustments={"a": -0.02, "b": 0.02},
    )
    assert trace.det_exploration_active is True
    assert trace.det_exploration_adjustments == {"a": -0.02, "b": 0.02}

    d = trace.to_dict()
    assert d["det_exploration_active"] is True
    assert d["det_exploration_adjustments"] == {"a": -0.02, "b": 0.02}


def test_decision_trace_none_fields():
    """DecisionTrace with None exploration fields doesn't include them in dict."""
    from umh.runtime_engine.decision_trace import build_trace

    trace = build_trace(turn_id=1)
    d = trace.to_dict()
    assert "det_exploration_active" not in d
    assert "det_exploration_adjustments" not in d


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
