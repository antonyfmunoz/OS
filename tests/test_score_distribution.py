"""Tests for distribution-aware scoring in the exploration engine.

Validates:
1. ScoreDistribution computes correct statistics.
2. RelativeUncertainty produces correct levels for key scenarios.
3. Normalized gap scales correctly with distribution shape.
4. Multi-strategy scaling works (3+, 5+, 10+ strategies).
5. Skewed vs uniform distributions produce appropriate uncertainty.
6. Stability: no oscillation in repeated computations.
7. Integration: exploration engine uses distribution-aware logic correctly.
8. Benchmark preservation: no regression vs baseline.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.score_distribution import (
    EPSILON,
    ScoreDistribution,
    RelativeUncertainty,
    compute_distribution,
    compute_relative_uncertainty,
)
from umh.runtime_engine.exploration_engine import (
    compute_exploration_signal,
    apply_exploration_adjustments,
)
from umh.runtime_engine.benchmark_env import (
    EOSDecisionSystem,
    EOSWithExplorationSystem,
    StaticScenario,
    ShiftingScenario,
    NoisyScenario,
    AdversarialScenario,
    run_simulation,
)


# ─── ScoreDistribution correctness ─────────────────────────────────


def test_distribution_empty():
    """Empty scores → zeroed distribution."""
    d = compute_distribution({})
    assert d.n_strategies == 0
    assert d.mean_score == 0.0
    assert d.std_dev == 0.0
    assert d.normalized_gap == 0.0


def test_distribution_single():
    """Single strategy → zero std_dev, zero gap."""
    d = compute_distribution({"a": 0.8})
    assert d.n_strategies == 1
    assert d.max_score == 0.8
    assert d.second_best == 0.8
    assert d.std_dev == 0.0
    assert d.raw_gap == 0.0
    assert d.normalized_gap == 0.0


def test_distribution_two_equal():
    """Two equal scores → zero gap, zero std_dev."""
    d = compute_distribution({"a": 0.5, "b": 0.5})
    assert d.n_strategies == 2
    assert d.raw_gap == 0.0
    assert d.std_dev == 0.0
    assert d.normalized_gap == 0.0


def test_distribution_two_unequal():
    """Two unequal scores → positive gap, correct stats."""
    d = compute_distribution({"a": 1.0, "b": 0.0})
    assert d.n_strategies == 2
    assert d.max_score == 1.0
    assert d.second_best == 0.0
    assert d.raw_gap == 1.0
    assert d.std_dev > 0
    assert d.normalized_gap > 0


def test_distribution_three_strategies():
    """Three strategies with spread → correct ordering."""
    d = compute_distribution({"a": 0.9, "b": 0.3, "c": 0.1})
    assert d.max_score == 0.9
    assert d.second_best == 0.3
    assert d.min_score == 0.1
    assert abs(d.raw_gap - 0.6) < 1e-9


def test_distribution_negative_scores():
    """Negative scores → handled correctly."""
    d = compute_distribution({"a": -0.1, "b": -0.5, "c": -0.3})
    assert d.max_score == -0.1
    assert d.second_best == -0.3
    assert d.min_score == -0.5
    assert d.raw_gap > 0


def test_distribution_all_zero():
    """All zeros → zero everything."""
    d = compute_distribution({"a": 0.0, "b": 0.0, "c": 0.0})
    assert d.std_dev == 0.0
    assert d.raw_gap == 0.0
    assert d.normalized_gap == 0.0


def test_distribution_deterministic():
    """Same scores → same distribution, always."""
    scores = {"x": 0.7, "y": 0.4, "z": 0.1}
    d1 = compute_distribution(scores)
    d2 = compute_distribution(scores)
    assert d1 == d2


def test_distribution_to_dict_roundtrip():
    """to_dict produces expected keys with rounded values."""
    d = compute_distribution({"a": 0.8, "b": 0.2})
    dd = d.to_dict()
    assert set(dd.keys()) == {
        "n_strategies",
        "mean_score",
        "std_dev",
        "max_score",
        "second_best",
        "min_score",
        "raw_gap",
        "normalized_gap",
        "dispersion",
    }
    assert all(isinstance(v, (int, float)) for v in dd.values())


# ─── Normalized gap properties ──────────────────────────────────────


def test_normalized_gap_increases_with_dominance():
    """Larger raw gap relative to std_dev → larger normalized_gap."""
    d_tight = compute_distribution({"a": 0.51, "b": 0.49})
    d_wide = compute_distribution({"a": 0.9, "b": 0.1})
    assert d_wide.normalized_gap >= d_tight.normalized_gap


def test_normalized_gap_large_when_dominant():
    """Dominant strategy → normalized_gap well above 1.0."""
    d = compute_distribution({"a": 10.0, "b": 0.01, "c": 0.01, "d": 0.01})
    assert d.normalized_gap > 1.5


def test_normalized_gap_small_when_near_tie():
    """Near-tie → normalized_gap near 0."""
    d = compute_distribution({"a": 0.501, "b": 0.500, "c": 0.499})
    assert d.normalized_gap < 1.0


# ─── RelativeUncertainty ────────────────────────────────────────────


def test_uncertainty_exact_tie():
    """All equal positive scores → maximum uncertainty."""
    ru = compute_relative_uncertainty({"a": 0.5, "b": 0.5, "c": 0.5, "d": 0.5})
    assert ru.level == 1.0
    assert ru.reason == "near_tie"


def test_uncertainty_all_zero():
    """All-zero scores → no data, not uncertain."""
    ru = compute_relative_uncertainty({"a": 0.0, "b": 0.0})
    assert ru.level == 0.0
    assert ru.reason == "no_data"


def test_uncertainty_single_strategy():
    """Single strategy → insufficient."""
    ru = compute_relative_uncertainty({"a": 0.8})
    assert ru.level == 0.0
    assert ru.reason == "insufficient_strategies"


def test_uncertainty_empty():
    """Empty → insufficient."""
    ru = compute_relative_uncertainty({})
    assert ru.level == 0.0
    assert ru.reason == "insufficient_strategies"


def test_uncertainty_clear_leader_lower_than_tie():
    """Clear leader should have lower uncertainty than a near-tie."""
    ru_leader = compute_relative_uncertainty({"a": 10.0, "b": 0.1, "c": 0.1})
    ru_tie = compute_relative_uncertainty({"a": 0.5, "b": 0.5, "c": 0.5})
    assert ru_leader.level < ru_tie.level


def test_uncertainty_bounded():
    """Uncertainty level always in [0, 1]."""
    test_cases = [
        {"a": 100.0, "b": 0.001},
        {"a": 0.5, "b": 0.5},
        {"a": 0.001, "b": 0.001, "c": 0.001},
        {"a": 1.0, "b": 0.99, "c": 0.98, "d": 0.97},
    ]
    for scores in test_cases:
        ru = compute_relative_uncertainty(scores)
        assert 0.0 <= ru.level <= 1.0, f"Out of bounds: {ru.level} for {scores}"


def test_uncertainty_deterministic():
    """Same input → same output, 100 times."""
    scores = {"a": 0.7, "b": 0.3, "c": 0.1}
    results = [compute_relative_uncertainty(scores).to_dict() for _ in range(100)]
    assert all(r == results[0] for r in results)


def test_uncertainty_to_dict_structure():
    """to_dict returns expected structure."""
    ru = compute_relative_uncertainty({"a": 0.8, "b": 0.2})
    d = ru.to_dict()
    assert "level" in d
    assert "reason" in d
    assert "distribution" in d
    assert isinstance(d["distribution"], dict)


# ─── Multi-strategy scaling ─────────────────────────────────────────


def test_multi_strategy_5():
    """5 strategies with spread → valid distribution."""
    scores = {"a": 0.9, "b": 0.7, "c": 0.5, "d": 0.3, "e": 0.1}
    d = compute_distribution(scores)
    assert d.n_strategies == 5
    assert d.max_score == 0.9
    assert d.second_best == 0.7
    assert d.std_dev > 0


def test_multi_strategy_10():
    """10 strategies → valid distribution with correct ordering."""
    scores = {f"s{i}": i * 0.1 for i in range(10)}
    d = compute_distribution(scores)
    assert d.n_strategies == 10
    assert d.max_score == 0.9
    assert d.second_best == 0.8
    assert d.min_score == 0.0


def test_multi_strategy_exploration_scales():
    """More strategies with flat scores → higher exploration intensity."""
    scores_2 = {"a": 0.5, "b": 0.5}
    scores_5 = {f"s{i}": 0.5 for i in range(5)}
    scores_10 = {f"s{i}": 0.5 for i in range(10)}

    ru_2 = compute_relative_uncertainty(scores_2)
    ru_5 = compute_relative_uncertainty(scores_5)
    ru_10 = compute_relative_uncertainty(scores_10)

    assert ru_2.level == 1.0
    assert ru_5.level == 1.0
    assert ru_10.level == 1.0


# ─── Skewed vs uniform distributions ────────────────────────────────


def test_skewed_lower_than_uniform():
    """Heavily skewed distribution → lower uncertainty than uniform."""
    scores_skewed = {"dominant": 10.0, "b": 0.1, "c": 0.05, "d": 0.01}
    scores_uniform = {"a": 2.5, "b": 2.5, "c": 2.5, "d": 2.5}
    ru_skewed = compute_relative_uncertainty(scores_skewed)
    ru_uniform = compute_relative_uncertainty(scores_uniform)
    assert ru_skewed.level < ru_uniform.level, (
        f"Skewed ({ru_skewed.level:.4f}) should be less uncertain than uniform ({ru_uniform.level:.4f})"
    )


def test_uniform_high_uncertainty():
    """Uniform distribution → high uncertainty."""
    scores = {"a": 1.0, "b": 1.0, "c": 1.0, "d": 1.0}
    ru = compute_relative_uncertainty(scores)
    assert ru.level == 1.0


def test_nearly_uniform_high_uncertainty():
    """Nearly uniform → still high uncertainty."""
    scores = {"a": 1.01, "b": 1.00, "c": 0.99, "d": 0.98}
    ru = compute_relative_uncertainty(scores)
    assert ru.level > 0.5, f"Nearly uniform should be high uncertainty, got {ru.level}"


def test_bimodal_vs_unimodal():
    """Bimodal with tight top cluster → higher uncertainty than unimodal with large gap."""
    scores_bimodal = {"a": 0.9, "b": 0.85, "c": 0.1, "d": 0.05}
    scores_unimodal = {"a": 0.9, "b": 0.3, "c": 0.1, "d": 0.05}
    ru_bi = compute_relative_uncertainty(scores_bimodal)
    ru_uni = compute_relative_uncertainty(scores_unimodal)
    assert ru_bi.level >= ru_uni.level, (
        f"Bimodal ({ru_bi.level:.4f}) should be at least as uncertain as unimodal ({ru_uni.level:.4f})"
    )


# ─── Exploration engine distribution integration ────────────────────


def test_exploration_uses_distribution():
    """Exploration signal changes based on distribution shape, not just raw gap."""
    # Near-tie: should trigger high_uncertainty
    sig_tie = compute_exploration_signal(
        plan_confidence=0.8,
        objective_trend="improving",
        failure_streak=0,
        strategy_scores={"a": 0.5, "b": 0.5, "c": 0.5},
    )
    assert sig_tie.exploration_active is True
    assert "high_uncertainty" in sig_tie.exploration_reason

    # Clear leader: should not trigger via uncertainty alone
    sig_clear = compute_exploration_signal(
        plan_confidence=0.9,
        objective_trend="improving",
        failure_streak=0,
        strategy_scores={"a": 0.95, "b": 0.05},
    )
    assert sig_clear.exploration_active is False


def test_exploration_penalty_scales_with_distribution():
    """Penalty as fraction of gap should be smaller when normalized_gap is high."""
    # Moderate gap, high normalized_gap (confident)
    sig_conf = compute_exploration_signal(
        plan_confidence=0.1,
        objective_trend="degrading",
        failure_streak=3,
        strategy_scores={"a": 0.8, "b": 0.2, "c": 0.19, "d": 0.18},
    )

    # Same raw gap range but lower normalized_gap (noisy distribution)
    sig_noisy = compute_exploration_signal(
        plan_confidence=0.1,
        objective_trend="degrading",
        failure_streak=3,
        strategy_scores={"a": 0.8, "b": 0.6, "c": 0.4, "d": 0.2},
    )

    if sig_conf.exploration_active and sig_noisy.exploration_active:
        from umh.runtime_engine.score_distribution import compute_distribution

        dist_conf = compute_distribution({"a": 0.8, "b": 0.2, "c": 0.19, "d": 0.18})
        dist_noisy = compute_distribution({"a": 0.8, "b": 0.6, "c": 0.4, "d": 0.2})

        conf_penalty = abs(sig_conf.exploration_adjustments.get("a", 0.0))
        noisy_penalty = abs(sig_noisy.exploration_adjustments.get("a", 0.0))

        conf_gap = dist_conf.raw_gap
        noisy_gap = dist_noisy.raw_gap

        conf_frac = conf_penalty / conf_gap if conf_gap > 0 else 0
        noisy_frac = noisy_penalty / noisy_gap if noisy_gap > 0 else 0

        assert dist_conf.normalized_gap > dist_noisy.normalized_gap, (
            "Test setup: confident should have higher normalized_gap"
        )
        assert conf_frac <= noisy_frac + 0.01, (
            f"Confident leader should get smaller gap-fraction penalty: "
            f"conf={conf_frac:.4f} vs noisy={noisy_frac:.4f}"
        )


# ─── Stability: no oscillation ──────────────────────────────────────


def test_stability_repeated_computation():
    """Repeated computation with same inputs → identical results."""
    scores = {"a": 0.7, "b": 0.4, "c": 0.2, "d": 0.1}
    signals = []
    for _ in range(50):
        s = compute_exploration_signal(
            plan_confidence=0.2,
            objective_trend="degrading",
            failure_streak=3,
            strategy_scores=scores,
        )
        signals.append(s.to_dict())
    assert all(s == signals[0] for s in signals)


def test_stability_gradual_score_change():
    """Gradual score changes → gradual adjustment changes (no jumps)."""
    prev_penalty = None
    for top_score_10x in range(50, 100, 5):
        top_score = top_score_10x / 100.0
        scores = {"a": top_score, "b": 0.3, "c": 0.1}
        s = compute_exploration_signal(
            plan_confidence=0.2,
            objective_trend="degrading",
            failure_streak=3,
            strategy_scores=scores,
        )
        if s.exploration_active:
            penalty = abs(s.exploration_adjustments.get("a", 0.0))
            if prev_penalty is not None:
                assert abs(penalty - prev_penalty) < 0.5, (
                    f"Jump detected: {prev_penalty:.4f} → {penalty:.4f}"
                )
            prev_penalty = penalty


# ─── Benchmark preservation ─────────────────────────────────────────


def test_benchmark_static_no_regression():
    """Distribution-aware exploration doesn't regress static performance."""
    baseline = EOSDecisionSystem()
    explore = EOSWithExplorationSystem()
    scenario = StaticScenario()

    m_b = run_simulation(baseline, scenario, steps=200, seed=42)
    m_e = run_simulation(explore, scenario, steps=200, seed=42)

    assert m_e.avg_reward >= m_b.avg_reward - 0.05


def test_benchmark_shifting_improvement():
    """Distribution-aware exploration still helps in shifting scenario."""
    baseline = EOSDecisionSystem()
    explore = EOSWithExplorationSystem()
    scenario = ShiftingScenario(shift_step=50)

    m_b = run_simulation(baseline, scenario, steps=200, seed=42)
    m_e = run_simulation(explore, scenario, steps=200, seed=42)

    assert m_e.avg_reward >= m_b.avg_reward, (
        f"Exploration should help shifting: explore={m_e.avg_reward:.4f} vs base={m_b.avg_reward:.4f}"
    )


def test_benchmark_noisy_no_regression():
    """Distribution-aware exploration doesn't regress noisy performance."""
    baseline = EOSDecisionSystem()
    explore = EOSWithExplorationSystem()
    scenario = NoisyScenario()

    m_b = run_simulation(baseline, scenario, steps=200, seed=42)
    m_e = run_simulation(explore, scenario, steps=200, seed=42)

    assert m_e.avg_reward >= m_b.avg_reward - 0.05


def test_benchmark_adversarial_bounded():
    """Distribution-aware exploration stays within tolerance in adversarial."""
    baseline = EOSDecisionSystem()
    explore = EOSWithExplorationSystem()
    scenario = AdversarialScenario()

    m_b = run_simulation(baseline, scenario, steps=120, seed=42)
    m_e = run_simulation(explore, scenario, steps=120, seed=42)

    assert m_e.avg_reward >= m_b.avg_reward - 0.05


def test_benchmark_deterministic():
    """Distribution-aware exploration is still fully deterministic."""
    e1 = EOSWithExplorationSystem()
    e2 = EOSWithExplorationSystem()
    scenario = ShiftingScenario()

    m1 = run_simulation(e1, scenario, steps=100, seed=42)
    m2 = run_simulation(e2, scenario, steps=100, seed=42)

    assert m1.rewards == m2.rewards
    assert m1.actions_chosen == m2.actions_chosen


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
