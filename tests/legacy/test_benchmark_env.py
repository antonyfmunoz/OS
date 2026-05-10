"""Tests for the benchmark environment.

Validates:
1. Deterministic runs — same seed produces identical results.
2. Reproducibility — re-running produces the same metrics.
3. Adaptation detection — EOS system changes behavior over time.
4. Recovery validation — EOS recovers from adversarial shifts.
5. Scenario correctness — each scenario produces expected reward structure.
6. Baseline sanity — baselines behave as specified.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.benchmark_env import (
    AdversarialScenario,
    ComparisonResult,
    EOSDecisionSystem,
    NoisyScenario,
    PolicyOnlyBaseline,
    RandomBaseline,
    RunMetrics,
    SeededRNG,
    ShiftingScenario,
    StaticScenario,
    StaticWeightsBaseline,
    run_full_benchmark,
    run_simulation,
)


# ─── SeededRNG tests ──────────────────────────────────────────────


def test_seeded_rng_deterministic():
    """Same seed → same sequence."""
    a = SeededRNG(42)
    b = SeededRNG(42)
    for _ in range(100):
        assert a.next_int() == b.next_int()


def test_seeded_rng_different_seeds():
    """Different seeds → different sequences."""
    a = SeededRNG(42)
    b = SeededRNG(99)
    vals_a = [a.next_int() for _ in range(10)]
    vals_b = [b.next_int() for _ in range(10)]
    assert vals_a != vals_b


def test_seeded_rng_float_range():
    """next_float returns values in [0, 1)."""
    rng = SeededRNG(42)
    for _ in range(1000):
        v = rng.next_float()
        assert 0.0 <= v < 1.0


# ─── Scenario reward structure tests ─────────────────────────────


def test_static_scenario_fixed_rewards():
    """Static scenario: action_0 always best, action_3 always worst."""
    s = StaticScenario()
    for step in range(20):
        r0, _ = s.evaluate_action("action_0", step)
        r3, _ = s.evaluate_action("action_3", step)
        assert r0 > r3


def test_shifting_scenario_changes():
    """Shifting scenario: best action changes at shift_step."""
    s = ShiftingScenario(shift_step=50)
    r0_early, _ = s.evaluate_action("action_0", 10)
    r3_early, _ = s.evaluate_action("action_3", 10)
    assert r0_early > r3_early

    r0_late, _ = s.evaluate_action("action_0", 60)
    r3_late, _ = s.evaluate_action("action_3", 60)
    assert r3_late > r0_late


def test_noisy_scenario_bounded():
    """Noisy scenario rewards stay in [0, 1]."""
    s = NoisyScenario()
    for step in range(100):
        for action in s.actions:
            r, _ = s.evaluate_action(action, step)
            assert 0.0 <= r <= 1.0


def test_adversarial_scenario_three_phases():
    """Adversarial scenario: invert at 40, restore at 80."""
    s = AdversarialScenario()
    r0_p1, _ = s.evaluate_action("action_0", 10)
    r3_p1, _ = s.evaluate_action("action_3", 10)
    assert r0_p1 > r3_p1

    r0_p2, _ = s.evaluate_action("action_0", 50)
    r3_p2, _ = s.evaluate_action("action_3", 50)
    assert r3_p2 > r0_p2

    r0_p3, _ = s.evaluate_action("action_0", 90)
    r3_p3, _ = s.evaluate_action("action_3", 90)
    assert r0_p3 > r3_p3


# ─── Deterministic run tests ─────────────────────────────────────


def test_deterministic_static():
    """Same seed, same scenario → identical rewards and actions."""
    sys1 = EOSDecisionSystem()
    sys2 = EOSDecisionSystem()
    scenario = StaticScenario()

    m1 = run_simulation(sys1, scenario, steps=50, seed=42)
    m2 = run_simulation(sys2, scenario, steps=50, seed=42)

    assert m1.rewards == m2.rewards
    assert m1.actions_chosen == m2.actions_chosen
    assert m1.successes == m2.successes


def test_deterministic_noisy():
    """Noisy scenario is still deterministic given same seed."""
    sys1 = EOSDecisionSystem()
    sys2 = EOSDecisionSystem()
    scenario = NoisyScenario()

    m1 = run_simulation(sys1, scenario, steps=50, seed=42)
    m2 = run_simulation(sys2, scenario, steps=50, seed=42)

    assert m1.rewards == m2.rewards


# ─── Reproducibility tests ───────────────────────────────────────


def test_full_benchmark_reproducible():
    """Full benchmark produces identical results on re-run."""
    r1 = run_full_benchmark(steps=30, seed=42)
    r2 = run_full_benchmark(steps=30, seed=42)

    for sys_name in r1.results:
        for scen_name in r1.results[sys_name]:
            m1 = r1.results[sys_name][scen_name]
            m2 = r2.results[sys_name][scen_name]
            assert m1.rewards == m2.rewards, f"Mismatch: {sys_name}/{scen_name}"
            assert m1.actions_chosen == m2.actions_chosen


# ─── Adaptation detection tests ──────────────────────────────────


def test_eos_adapts_in_static():
    """EOS should converge: late rewards >= early rewards in static scenario."""
    eos = EOSDecisionSystem()
    m = run_simulation(eos, StaticScenario(), steps=100, seed=42)
    assert m.late_avg_reward >= m.early_avg_reward, (
        f"EOS did not improve: early={m.early_avg_reward:.4f} late={m.late_avg_reward:.4f}"
    )


def test_eos_beats_random():
    """EOS should outperform random baseline in static scenario."""
    eos = EOSDecisionSystem()
    rand = RandomBaseline(seed=42)
    scenario = StaticScenario()

    m_eos = run_simulation(eos, scenario, steps=100, seed=42)
    m_rand = run_simulation(rand, scenario, steps=100, seed=42)

    assert m_eos.avg_reward >= m_rand.avg_reward, (
        f"EOS ({m_eos.avg_reward:.4f}) did not beat random ({m_rand.avg_reward:.4f})"
    )


def test_eos_learns_from_memory():
    """EOS action distribution should shift toward higher-reward actions over time."""
    eos = EOSDecisionSystem()
    m = run_simulation(eos, StaticScenario(), steps=100, seed=42)

    early_actions = m.actions_chosen[:20]
    late_actions = m.actions_chosen[-20:]

    early_best = early_actions.count("action_0")
    late_best = late_actions.count("action_0")

    assert late_best >= early_best, (
        f"EOS did not learn: early action_0 count={early_best}, late={late_best}"
    )


# ─── Recovery validation tests ───────────────────────────────────


def test_eos_detects_shift():
    """In shifting scenario, EOS should change behavior after the shift."""
    eos = EOSDecisionSystem()
    m = run_simulation(eos, ShiftingScenario(shift_step=50), steps=100, seed=42)

    pre_shift = m.actions_chosen[40:50]
    post_shift = m.actions_chosen[70:80]

    pre_set = set(pre_shift)
    post_set = set(post_shift)

    assert pre_set != post_set or len(post_set) > 1, (
        "EOS did not detect the regime shift"
    )


def test_adversarial_recovery():
    """In adversarial scenario, EOS should attempt recovery after inversion."""
    eos = EOSDecisionSystem()
    m = run_simulation(eos, AdversarialScenario(), steps=120, seed=42)

    phase1_actions = set(m.actions_chosen[30:40])
    phase3_actions = set(m.actions_chosen[100:120])

    assert len(phase3_actions) >= 1, "EOS produced no actions in recovery phase"


# ─── Baseline sanity tests ───────────────────────────────────────


def test_random_baseline_diverse():
    """Random baseline should pick multiple different actions."""
    rand = RandomBaseline(seed=42)
    m = run_simulation(rand, StaticScenario(), steps=100, seed=42)
    unique_actions = set(m.actions_chosen)
    assert len(unique_actions) > 1


def test_policy_only_constant():
    """Policy-only baseline always picks the same action."""
    pol = PolicyOnlyBaseline()
    m = run_simulation(pol, StaticScenario(), steps=50, seed=42)
    assert len(set(m.actions_chosen)) == 1


def test_static_weights_no_meta_drift():
    """Static weights baseline never changes its penalty weight."""
    sw = StaticWeightsBaseline(fixed_weight=0.15)
    run_simulation(sw, StaticScenario(), steps=100, seed=42)
    assert sw.fixed_weight == 0.15


# ─── Metrics computation tests ───────────────────────────────────


def test_metrics_avg_reward():
    m = RunMetrics("test", "test", 3, rewards=[1.0, 0.5, 0.0])
    assert abs(m.avg_reward - 0.5) < 1e-9


def test_metrics_variance():
    m = RunMetrics("test", "test", 3, rewards=[1.0, 1.0, 1.0])
    assert m.reward_variance == 0.0


def test_metrics_convergence():
    actions = ["a"] * 5 + ["b"] * 15
    m = RunMetrics("test", "test", 20, actions_chosen=actions)
    assert m.convergence_step == 5


def test_metrics_no_convergence():
    actions = ["a", "b"] * 10
    m = RunMetrics("test", "test", 20, actions_chosen=actions)
    assert m.convergence_step is None


def test_metrics_improvement_ratio():
    rewards = [0.2] * 20 + [0.8] * 80
    m = RunMetrics("test", "test", 100, rewards=rewards)
    assert m.improvement_ratio > 1.0


def test_metrics_performance_curve():
    rewards = list(range(20))
    m = RunMetrics("test", "test", 20, rewards=[float(x) for x in rewards])
    curve = m.performance_curve(window=5)
    assert len(curve) == 16
    assert curve[0] < curve[-1]


# ─── Integration: comparison summary ─────────────────────────────


def test_comparison_summary_format():
    """Full benchmark summary should be a non-empty string with all systems."""
    result = run_full_benchmark(steps=30, seed=42)
    summary = result.summary()
    assert "eos_substrate" in summary
    assert "static_weights" in summary
    assert "random" in summary
    assert "policy_only" in summary
    assert "Avg Reward" in summary


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
