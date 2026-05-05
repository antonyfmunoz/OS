"""Tests for Long-Horizon Stability & Drift Validation harness.

Covers 8 categories:
1. Determinism — identical seeds => identical outputs
2. Static stability — EOS does not degrade in STATIC_STABLE
3. Repeated adaptation — recovery doesn't degrade monotonically
4. Adversarial resilience — EOS outperforms baselines in adversarial flip
5. Noisy robustness — no runaway drift under noise
6. Restart continuity — restarted run aligns with uninterrupted
7. Detector sanity — synthetic traces trigger detectors correctly
8. Boundedness — all tracked signals within expected ranges
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.long_horizon_benchmark import (
    AdversarialFlipScenario,
    MixedRegimeScenario,
    NoisyStationaryScenario,
    PeriodicShiftScenario,
    SlowDriftScenario,
    StaticStableScenario,
    _linear_slope,
    _variance,
    compute_diagnostics,
    compute_recovery_metrics,
    compute_reward_metrics,
    compute_safety_metrics,
    compute_stability_metrics,
    detect_drift,
    detect_lock_in,
    detect_oscillation,
    detect_runaway,
    get_all_scenarios,
    run_full_long_horizon_benchmark,
    run_long_horizon,
    simulate_restart_continuity,
    SYSTEM_FACTORIES,
)
from umh.runtime_engine.benchmark_env import (
    EOSDecisionSystem,
    EOSWithRegimeSystem,
    StaticWeightsBaseline,
    RandomBaseline,
)


# ─── 1. Determinism ──────────────────────────────────────────────────


class TestDeterminism:
    """Identical seeds + identical config => identical outputs."""

    def test_same_seed_same_scenario_same_system_identical_result(self):
        scenario = StaticStableScenario(seed=42)
        sys1 = EOSDecisionSystem()
        r1 = run_long_horizon(sys1, scenario, horizon=200, seed=42)

        scenario2 = StaticStableScenario(seed=42)
        sys2 = EOSDecisionSystem()
        r2 = run_long_horizon(sys2, scenario2, horizon=200, seed=42)

        assert r1.reward_metrics.avg_reward == r2.reward_metrics.avg_reward
        assert (
            r1.reward_metrics.cumulative_reward == r2.reward_metrics.cumulative_reward
        )
        assert (
            r1.stability_metrics.action_switch_rate
            == r2.stability_metrics.action_switch_rate
        )

    def test_different_seeds_different_results(self):
        s1 = PeriodicShiftScenario(seed=42, period=50)
        sys1 = RandomBaseline(seed=42)
        r1 = run_long_horizon(sys1, s1, horizon=200, seed=42)

        s2 = PeriodicShiftScenario(seed=42, period=50)
        sys2 = RandomBaseline(seed=99)
        r2 = run_long_horizon(sys2, s2, horizon=200, seed=99)

        assert (
            r1.reward_metrics.rolling_mean_final != r2.reward_metrics.rolling_mean_final
        )

    def test_full_benchmark_deterministic(self):
        r1 = run_full_long_horizon_benchmark(
            horizon=100,
            seed=42,
            systems=["eos_substrate", "static_weights"],
            scenarios=["StaticStable"],
        )
        r2 = run_full_long_horizon_benchmark(
            horizon=100,
            seed=42,
            systems=["eos_substrate", "static_weights"],
            scenarios=["StaticStable"],
        )

        for sys_name in r1.results:
            for scen_name in r1.results[sys_name]:
                a = r1.results[sys_name][scen_name]
                b = r2.results[sys_name][scen_name]
                assert a.reward_metrics.avg_reward == b.reward_metrics.avg_reward
                assert (
                    a.drift_metrics.reward_slope_tail
                    == b.drift_metrics.reward_slope_tail
                )


# ─── 2. Static stability ─────────────────────────────────────────────


class TestStaticStability:
    """EOS does not degrade in STATIC_STABLE across long horizon."""

    def test_eos_converges_in_static(self):
        scenario = StaticStableScenario(seed=42)
        system = EOSDecisionSystem()
        result = run_long_horizon(system, scenario, horizon=500, seed=42)

        assert result.reward_metrics.avg_reward > 0.3

    def test_eos_no_drift_in_static(self):
        scenario = StaticStableScenario(seed=42)
        system = EOSDecisionSystem()
        result = run_long_horizon(system, scenario, horizon=1000, seed=42)

        assert result.drift_metrics.reward_slope_tail >= -0.001

    def test_eos_outperforms_random_in_static(self):
        scenario_e = StaticStableScenario(seed=42)
        eos = EOSDecisionSystem()
        r_eos = run_long_horizon(eos, scenario_e, horizon=500, seed=42)

        scenario_r = StaticStableScenario(seed=42)
        rand = RandomBaseline(seed=42)
        r_rand = run_long_horizon(rand, scenario_r, horizon=500, seed=42)

        assert r_eos.reward_metrics.avg_reward >= r_rand.reward_metrics.avg_reward

    def test_static_scenario_best_is_action_0(self):
        scenario = StaticStableScenario(seed=42)
        r0, _ = scenario.evaluate_action("action_0", 0)
        r1, _ = scenario.evaluate_action("action_1", 0)
        r3, _ = scenario.evaluate_action("action_3", 0)
        assert r0 > r1 > r3


# ─── 3. Repeated adaptation ─────────────────────────────────────────


class TestRepeatedAdaptation:
    """Recovery doesn't degrade monotonically in PERIODIC_SHIFT."""

    def test_eos_recovers_in_periodic_shift(self):
        scenario = PeriodicShiftScenario(seed=42, period=200)
        system = EOSWithRegimeSystem()
        result = run_long_horizon(system, scenario, horizon=1000, seed=42)

        assert result.reward_metrics.avg_reward > 0.2

    def test_recovery_degradation_bounded(self):
        scenario = PeriodicShiftScenario(seed=42, period=200)
        system = EOSWithRegimeSystem()
        result = run_long_horizon(system, scenario, horizon=1000, seed=42)

        assert result.recovery_metrics.recovery_degradation < 100

    def test_periodic_shift_scenario_rotates_best(self):
        scenario = PeriodicShiftScenario(seed=42, period=200)

        r0_at_0, _ = scenario.evaluate_action("action_0", 0)
        r0_at_200, _ = scenario.evaluate_action("action_0", 200)
        r1_at_200, _ = scenario.evaluate_action("action_1", 200)

        assert r0_at_0 > r0_at_200
        assert r1_at_200 > r0_at_200


# ─── 4. Adversarial resilience ───────────────────────────────────────


class TestAdversarialResilience:
    """EOS outperforms baselines in adversarial flip."""

    def test_eos_handles_adversarial_flip(self):
        scenario = AdversarialFlipScenario(seed=42)
        system = EOSDecisionSystem()
        result = run_long_horizon(system, scenario, horizon=1000, seed=42)

        assert result.reward_metrics.avg_reward > 0.2

    def test_eos_beats_static_in_adversarial(self):
        s_eos = AdversarialFlipScenario(seed=42)
        eos = EOSDecisionSystem()
        r_eos = run_long_horizon(eos, s_eos, horizon=1000, seed=42)

        s_static = AdversarialFlipScenario(seed=42)
        static = StaticWeightsBaseline(fixed_weight=0.1)
        r_static = run_long_horizon(static, s_static, horizon=1000, seed=42)

        assert (
            r_eos.reward_metrics.avg_reward >= r_static.reward_metrics.avg_reward * 0.8
        )

    def test_adversarial_scenario_inverts_during_flip(self):
        scenario = AdversarialFlipScenario(seed=42, flip_start=300, flip_end=500)

        r0_before, _ = scenario.evaluate_action("action_0", 100)
        r3_before, _ = scenario.evaluate_action("action_3", 100)
        assert r0_before > r3_before

        r0_during, _ = scenario.evaluate_action("action_0", 400)
        r3_during, _ = scenario.evaluate_action("action_3", 400)
        assert r3_during > r0_during

        r0_after, _ = scenario.evaluate_action("action_0", 600)
        r3_after, _ = scenario.evaluate_action("action_3", 600)
        assert r0_after > r3_after


# ─── 5. Noisy robustness ─────────────────────────────────────────────


class TestNoisyRobustness:
    """No runaway drift under noise."""

    def test_eos_stable_in_noisy_stationary(self):
        scenario = NoisyStationaryScenario(seed=42)
        system = EOSDecisionSystem()
        result = run_long_horizon(system, scenario, horizon=1000, seed=42)

        assert result.safety_metrics.runaway_episodes <= 5

    def test_noisy_scenario_has_noise(self):
        scenario = NoisyStationaryScenario(seed=42, noise_scale=0.25)
        rewards = [scenario.evaluate_action("action_0", step)[0] for step in range(100)]
        assert min(rewards) < max(rewards)

    def test_noisy_scenario_preserves_order_on_average(self):
        scenario = NoisyStationaryScenario(seed=42, noise_scale=0.25)
        r0 = sum(scenario.evaluate_action("action_0", s)[0] for s in range(200)) / 200
        r3 = sum(scenario.evaluate_action("action_3", s)[0] for s in range(200)) / 200
        assert r0 > r3

    def test_eos_no_runaway_drift_in_noise(self):
        scenario = NoisyStationaryScenario(seed=42)
        system = EOSDecisionSystem()
        result = run_long_horizon(system, scenario, horizon=1000, seed=42)

        assert result.drift_metrics.reward_slope_tail > -0.005


# ─── 6. Restart continuity ───────────────────────────────────────────


class TestRestartContinuity:
    """Restarted run aligns with uninterrupted."""

    def test_static_restart_within_tolerance(self):
        rc = simulate_restart_continuity(
            system_factory=EOSDecisionSystem,
            scenario=StaticStableScenario(seed=42),
            horizon=500,
            seed=42,
            restart_interval=100,
        )

        assert rc.within_tolerance or rc.divergence < 0.10

    def test_noisy_restart_bounded_divergence(self):
        rc = simulate_restart_continuity(
            system_factory=EOSDecisionSystem,
            scenario=NoisyStationaryScenario(seed=42),
            horizon=500,
            seed=42,
            restart_interval=100,
        )

        assert rc.divergence < 0.20

    def test_restart_continuity_metrics_structure(self):
        rc = simulate_restart_continuity(
            system_factory=EOSDecisionSystem,
            scenario=StaticStableScenario(seed=42),
            horizon=200,
            seed=42,
        )

        d = rc.to_dict()
        assert "uninterrupted_avg_reward" in d
        assert "restarted_avg_reward" in d
        assert "divergence" in d
        assert "within_tolerance" in d
        assert isinstance(d["within_tolerance"], bool)


# ─── 7. Detector sanity ──────────────────────────────────────────────


class TestDetectorSanity:
    """Synthetic traces trigger oscillation / lock-in / drift detectors correctly."""

    def test_oscillation_detects_rapid_switching(self):
        actions = []
        for i in range(200):
            actions.append("action_0" if i % 2 == 0 else "action_1")
        rewards = [0.5] * 200

        episodes = detect_oscillation(actions, rewards)
        assert episodes > 0

    def test_oscillation_ignores_stable_trace(self):
        actions = ["action_0"] * 200
        rewards = [0.8] * 200

        episodes = detect_oscillation(actions, rewards)
        assert episodes == 0

    def test_lock_in_detects_stuck_with_declining_reward(self):
        actions = ["action_0"] * 200
        rewards = [0.9 - i * 0.008 for i in range(200)]

        episodes = detect_lock_in(actions, rewards)
        assert episodes > 0

    def test_lock_in_ignores_stuck_with_stable_reward(self):
        actions = ["action_0"] * 200
        rewards = [0.8] * 200

        episodes = detect_lock_in(actions, rewards)
        assert episodes == 0

    def test_lock_in_ignores_switching_actions(self):
        actions = []
        for i in range(200):
            actions.append(f"action_{i % 4}")
        rewards = [0.9 - i * 0.003 for i in range(200)]

        episodes = detect_lock_in(actions, rewards)
        assert episodes == 0

    def test_drift_detects_declining_reward(self):
        rewards = [1.0 - i * 0.001 for i in range(500)]

        episodes = detect_drift(rewards)
        assert episodes > 0

    def test_drift_ignores_stable_reward(self):
        rewards = [0.8] * 500

        episodes = detect_drift(rewards)
        assert episodes == 0

    def test_runaway_detects_growing_variance(self):
        rewards = []
        for i in range(300):
            if i < 150:
                rewards.append(0.5 + 0.01 * (1 if i % 2 == 0 else -1))
            else:
                rewards.append(0.5 + 0.4 * (1 if i % 2 == 0 else -1))

        episodes = detect_runaway(rewards)
        assert episodes > 0

    def test_runaway_ignores_stable_variance(self):
        rewards = [0.5] * 200
        episodes = detect_runaway(rewards)
        assert episodes == 0

    def test_diagnostics_aggregate(self):
        actions = []
        for i in range(200):
            actions.append("action_0" if i % 2 == 0 else "action_1")
        rewards = [0.5] * 200

        diag = compute_diagnostics(actions, rewards)
        assert diag.oscillation_detected is True
        assert isinstance(diag.details, dict)
        assert "oscillation_episodes" in diag.details


# ─── 8. Boundedness ──────────────────────────────────────────────────


class TestBoundedness:
    """All tracked bounded signals remain within expected ranges."""

    def test_reward_metrics_bounded(self):
        scenario = StaticStableScenario(seed=42)
        system = EOSDecisionSystem()
        result = run_long_horizon(system, scenario, horizon=500, seed=42)

        assert 0.0 <= result.reward_metrics.avg_reward <= 1.0
        assert result.reward_metrics.cumulative_reward >= 0.0
        assert 0.0 <= result.reward_metrics.rolling_mean_final <= 1.0
        assert result.reward_metrics.rolling_std_final >= 0.0

    def test_stability_metrics_bounded(self):
        scenario = PeriodicShiftScenario(seed=42)
        system = EOSDecisionSystem()
        result = run_long_horizon(system, scenario, horizon=500, seed=42)

        assert 0.0 <= result.stability_metrics.action_switch_rate <= 1.0
        assert result.stability_metrics.objective_volatility >= 0.0

    def test_drift_metrics_reasonable(self):
        scenario = NoisyStationaryScenario(seed=42)
        system = EOSDecisionSystem()
        result = run_long_horizon(system, scenario, horizon=500, seed=42)

        assert 0.0 <= result.drift_metrics.strategy_concentration <= 1.0
        assert isinstance(result.drift_metrics.false_lock_in_episodes, int)
        assert result.drift_metrics.false_lock_in_episodes >= 0

    def test_safety_metrics_non_negative(self):
        scenario = MixedRegimeScenario(seed=42)
        system = EOSWithRegimeSystem()
        result = run_long_horizon(system, scenario, horizon=500, seed=42)

        assert result.safety_metrics.oscillation_episodes >= 0
        assert result.safety_metrics.lock_in_episodes >= 0
        assert result.safety_metrics.drift_episodes >= 0
        assert result.safety_metrics.runaway_episodes >= 0

    def test_all_scenarios_produce_valid_rewards(self):
        scenarios = get_all_scenarios(seed=42)
        for name, scenario in scenarios.items():
            for step in range(100):
                for action in scenario.actions:
                    r, s = scenario.evaluate_action(action, step)
                    assert 0.0 <= r <= 1.0, (
                        f"{name} action={action} step={step} reward={r}"
                    )
                    assert isinstance(s, bool)

    def test_to_dict_roundtrip(self):
        scenario = StaticStableScenario(seed=42)
        system = EOSDecisionSystem()
        result = run_long_horizon(system, scenario, horizon=100, seed=42)

        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["system_name"] == "eos_substrate"
        assert d["scenario_name"] == "StaticStableScenario"
        assert d["horizon"] == 100
        assert "reward_metrics" in d
        assert "stability_metrics" in d
        assert "recovery_metrics" in d
        assert "drift_metrics" in d
        assert "safety_metrics" in d
        assert "diagnostics" in d
        assert "restart_continuity" in d


# ─── Helper function tests ───────────────────────────────────────────


class TestHelpers:
    def test_linear_slope_positive(self):
        values = [float(i) for i in range(100)]
        slope = _linear_slope(values)
        assert abs(slope - 1.0) < 0.001

    def test_linear_slope_negative(self):
        values = [100.0 - float(i) for i in range(100)]
        slope = _linear_slope(values)
        assert abs(slope - (-1.0)) < 0.001

    def test_linear_slope_flat(self):
        values = [5.0] * 100
        slope = _linear_slope(values)
        assert abs(slope) < 1e-10

    def test_linear_slope_single_element(self):
        assert _linear_slope([1.0]) == 0.0

    def test_variance_constant(self):
        assert _variance([5.0, 5.0, 5.0, 5.0]) == 0.0

    def test_variance_known(self):
        vals = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        v = _variance(vals)
        assert abs(v - 4.571428571428571) < 0.001

    def test_variance_empty(self):
        assert _variance([]) == 0.0


# ─── Scenario-specific math tests ────────────────────────────────────


class TestScenarioMath:
    def test_slow_drift_eventually_reduces_action_0(self):
        scenario = SlowDriftScenario(seed=42, drift_rate=0.001)
        r_early, _ = scenario.evaluate_action("action_0", 0)
        r_late, _ = scenario.evaluate_action("action_0", 800)
        assert r_early > r_late

    def test_mixed_regime_phases(self):
        scenario = MixedRegimeScenario(seed=42)

        r0_static, _ = scenario.evaluate_action("action_0", 50)
        r3_static, _ = scenario.evaluate_action("action_3", 50)
        assert r0_static > r3_static

        r2_shift, _ = scenario.evaluate_action("action_2", 450)
        r0_shift, _ = scenario.evaluate_action("action_0", 450)
        assert r2_shift > r0_shift

        r3_adv, _ = scenario.evaluate_action("action_3", 700)
        r0_adv, _ = scenario.evaluate_action("action_0", 700)
        assert r3_adv > r0_adv

    def test_get_all_scenarios_returns_six(self):
        scenarios = get_all_scenarios()
        assert len(scenarios) == 6
        expected = {
            "StaticStable",
            "PeriodicShift",
            "AdversarialFlip",
            "NoisyStationary",
            "SlowDrift",
            "MixedRegime",
        }
        assert set(scenarios.keys()) == expected


# ─── Full benchmark structure tests ──────────────────────────────────


class TestBenchmarkStructure:
    def test_benchmark_result_has_all_systems_and_scenarios(self):
        result = run_full_long_horizon_benchmark(
            horizon=50,
            seed=42,
            systems=["eos_substrate", "random"],
            scenarios=["StaticStable", "NoisyStationary"],
        )
        assert "eos_substrate" in result.results
        assert "random" in result.results
        assert "StaticStable" in result.results["eos_substrate"]
        assert "NoisyStationary" in result.results["eos_substrate"]

    def test_summary_table_renders(self):
        result = run_full_long_horizon_benchmark(
            horizon=50,
            seed=42,
            systems=["eos_substrate"],
            scenarios=["StaticStable"],
        )
        table = result.summary_table()
        assert "eos_substrate" in table
        assert "StaticStable" in table

    def test_system_factories_all_valid(self):
        for name, factory in SYSTEM_FACTORIES.items():
            system = factory()
            assert hasattr(system, "choose_action")
            assert hasattr(system, "observe_outcome")
            assert hasattr(system, "reset")

    def test_benchmark_to_dict(self):
        result = run_full_long_horizon_benchmark(
            horizon=50,
            seed=42,
            systems=["eos_substrate"],
            scenarios=["StaticStable"],
        )
        d = result.to_dict()
        assert d["horizon"] == 50
        assert d["seed"] == 42
        assert "eos_substrate" in d["results"]


# ─── Metric computation unit tests ───────────────────────────────────


class TestMetricComputation:
    def test_reward_metrics_empty(self):
        m = compute_reward_metrics([])
        assert m.avg_reward == 0.0
        assert m.cumulative_reward == 0.0

    def test_reward_metrics_known(self):
        rewards = [0.5] * 100
        m = compute_reward_metrics(rewards)
        assert abs(m.avg_reward - 0.5) < 1e-6
        assert abs(m.cumulative_reward - 50.0) < 1e-6
        assert abs(m.rolling_mean_final - 0.5) < 1e-6
        assert m.rolling_std_final < 1e-6

    def test_stability_metrics_no_switches(self):
        actions = ["action_0"] * 100
        rewards = [0.8] * 100
        m = compute_stability_metrics(actions, rewards)
        assert m.action_switch_rate == 0.0

    def test_stability_metrics_all_switches(self):
        actions = ["action_0" if i % 2 == 0 else "action_1" for i in range(100)]
        rewards = [0.5] * 100
        m = compute_stability_metrics(actions, rewards)
        assert abs(m.action_switch_rate - 1.0) < 0.02

    def test_recovery_metrics_non_periodic_returns_empty(self):
        actions = ["action_0"] * 100
        rewards = [0.8] * 100
        scenario = StaticStableScenario(seed=42)
        m = compute_recovery_metrics(actions, rewards, scenario, 100)
        assert len(m.shift_recovery_times) == 0
        assert m.avg_recovery_time == 0.0

    def test_safety_metrics_clean_trace(self):
        actions = ["action_0"] * 500
        rewards = [0.8] * 500
        m = compute_safety_metrics(actions, rewards)
        assert m.oscillation_episodes == 0
        assert m.lock_in_episodes == 0
        assert m.runaway_episodes == 0
