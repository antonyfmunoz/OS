"""Tests for stability guard — prevents thrashing without killing adaptation.

Covers:
1. Guard activates on high switch rate + low improvement
2. Guard inactive on low switch rate
3. Guard inactive when switching improves reward
4. Adjustments are bounded
5. Determinism
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.stability_guard import (
    NO_STABILITY_SIGNAL,
    compute_stability_signal,
)


class TestStabilityGuardActivation:
    def test_activates_on_high_switching_no_improvement(self):
        actions = ["action_0" if i % 2 == 0 else "action_1" for i in range(30)]
        rewards = [0.5] * 30

        signal = compute_stability_signal(actions, rewards)
        assert signal.active
        assert signal.switch_rate >= 0.6

    def test_inactive_on_low_switch_rate(self):
        actions = ["action_0"] * 30
        rewards = [0.5] * 30

        signal = compute_stability_signal(actions, rewards)
        assert not signal.active

    def test_inactive_when_switching_improves_reward(self):
        actions = ["action_0" if i % 2 == 0 else "action_1" for i in range(30)]
        rewards = [0.3 + i * 0.02 for i in range(30)]

        signal = compute_stability_signal(actions, rewards)
        assert not signal.active

    def test_inactive_below_window_size(self):
        actions = ["action_0", "action_1"] * 5
        rewards = [0.5] * 10

        signal = compute_stability_signal(actions, rewards)
        assert not signal.active


class TestStabilityGuardBounds:
    def test_exploration_adjustment_negative(self):
        actions = ["action_0" if i % 2 == 0 else "action_1" for i in range(30)]
        rewards = [0.5] * 30

        signal = compute_stability_signal(actions, rewards)
        if signal.active:
            assert signal.exploration_adjustment <= 0.0

    def test_confidence_adjustment_positive(self):
        actions = ["action_0" if i % 2 == 0 else "action_1" for i in range(30)]
        rewards = [0.5] * 30

        signal = compute_stability_signal(actions, rewards)
        if signal.active:
            assert signal.confidence_adjustment >= 0.0


class TestStabilityGuardDeterminism:
    def test_identical_inputs_identical_outputs(self):
        actions = ["action_0" if i % 2 == 0 else "action_1" for i in range(30)]
        rewards = [0.5] * 30

        s1 = compute_stability_signal(actions, rewards)
        s2 = compute_stability_signal(actions, rewards)

        assert s1.active == s2.active
        assert s1.switch_rate == s2.switch_rate
        assert s1.exploration_adjustment == s2.exploration_adjustment


class TestStabilityReducesOscillation:
    def test_slow_drift_oscillation_reduced(self):
        from umh.runtime_engine.benchmark_env import EOSWithCorrectionSystem
        from umh.runtime_engine.long_horizon_benchmark import SlowDriftScenario, run_long_horizon

        s1 = SlowDriftScenario(seed=42)
        system = EOSWithCorrectionSystem()
        result = run_long_horizon(system, s1, horizon=2500, seed=42)

        assert result.safety_metrics.oscillation_episodes <= 25


class TestStabilityToDict:
    def test_active_signal_to_dict(self):
        actions = ["action_0" if i % 2 == 0 else "action_1" for i in range(30)]
        rewards = [0.5] * 30
        signal = compute_stability_signal(actions, rewards)
        d = signal.to_dict()
        assert "active" in d

    def test_inactive_signal_to_dict(self):
        d = NO_STABILITY_SIGNAL.to_dict()
        assert d["active"] is False
