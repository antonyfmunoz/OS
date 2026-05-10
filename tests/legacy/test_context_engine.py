"""Tests for eos_ai.context_engine — context disambiguation layer."""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.context_engine import (
    NO_CONTEXT_SIGNAL,
    ContextClassifier,
    ContextSignal,
    gate_exploration_inputs,
    gate_stability_effect,
    gate_trap_adjustment,
)


class TestContextClassifier:
    def test_returns_no_signal_below_min_observations(self):
        c = ContextClassifier()
        signal = c.classify(["a"] * 5, [1.0] * 5)
        assert signal is NO_CONTEXT_SIGNAL

    def test_stable_environment_produces_low_signals(self):
        c = ContextClassifier()
        actions = ["action_0"] * 50
        rewards = [1.0] * 50
        signal = c.classify(actions, rewards)
        assert signal.regime_change_likelihood < 0.05
        assert signal.adversarial_likelihood < 0.05
        assert signal.dominant_type == "stable"

    def test_sharp_drop_raises_adversarial_or_regime(self):
        c = ContextClassifier()
        actions = ["action_0"] * 30
        rewards = [1.0] * 20 + [0.2] * 10
        signal = c.classify(actions, rewards)
        combined = signal.adversarial_likelihood + signal.regime_change_likelihood
        assert combined > 0.1

    def test_periodic_rewards_raise_regime(self):
        c = ContextClassifier()
        for _ in range(5):
            actions = ["action_0"] * 120
            rewards = [1.0] * 20 + [0.3] * 10 + [1.0] * 20 + [0.3] * 10
            rewards = rewards * 3
            signal = c.classify(actions, rewards[:120])
        assert signal.regime_change_likelihood > 0.05 or signal.noise_level > 0.05

    def test_high_variance_raises_noise(self):
        c = ContextClassifier()
        actions = ["action_0"] * 30
        rewards = [1.0, 0.2] * 15
        signal = c.classify(actions, rewards)
        assert signal.noise_level > 0.05

    def test_ema_smoothing(self):
        c = ContextClassifier()
        actions = ["action_0"] * 30
        rewards = [1.0] * 20 + [0.2] * 10
        s1 = c.classify(actions, rewards)
        s2 = c.classify(actions, rewards)
        assert s1.regime_change_likelihood != s2.regime_change_likelihood

    def test_classify_deterministic(self):
        c1 = ContextClassifier()
        c2 = ContextClassifier()
        actions = ["action_0"] * 30
        rewards = [1.0] * 20 + [0.2] * 10
        s1 = c1.classify(actions, rewards)
        s2 = c2.classify(actions, rewards)
        assert s1 == s2


class TestSnapshotRestore:
    def test_roundtrip(self):
        c1 = ContextClassifier()
        actions = ["action_0"] * 30
        rewards = [1.0] * 20 + [0.3] * 10
        c1.classify(actions, rewards)
        snap = c1.snapshot()

        c2 = ContextClassifier()
        c2.restore(snap)

        assert c2.snapshot() == snap

    def test_restore_none_is_safe(self):
        c = ContextClassifier()
        c.restore(None)
        c.restore({})

    def test_reset(self):
        c = ContextClassifier()
        c.classify(["a"] * 30, [1.0] * 30)
        c.reset()
        assert c._observations == 0


class TestContextSignal:
    def test_to_dict(self):
        s = ContextSignal(
            regime_change_likelihood=0.5,
            adversarial_likelihood=0.3,
            noise_level=0.1,
            drift_strength=0.05,
            dominant_type="regime_change",
        )
        d = s.to_dict()
        assert d["dominant_type"] == "regime_change"
        assert d["regime_change_likelihood"] == 0.5

    def test_frozen(self):
        s = NO_CONTEXT_SIGNAL
        try:
            s.noise_level = 0.5  # type: ignore
            assert False, "Should be frozen"
        except AttributeError:
            pass


class TestGateTrapAdjustment:
    def test_passthrough_when_no_non_adversarial(self):
        ctx = ContextSignal(0.0, 0.5, 0.0, 0.0, "adversarial")
        assert gate_trap_adjustment(0.1, ctx) == 0.1

    def test_reduced_when_regime_present(self):
        ctx = ContextSignal(0.5, 0.3, 0.0, 0.0, "regime_change")
        gated = gate_trap_adjustment(0.1, ctx)
        assert gated < 0.1

    def test_zero_when_adversarial_zero(self):
        ctx = ContextSignal(0.5, 0.0, 0.0, 0.0, "regime_change")
        gated = gate_trap_adjustment(0.1, ctx)
        assert gated == 0.0


class TestGateStabilityEffect:
    def test_passthrough_below_threshold(self):
        ctx = ContextSignal(0.0, 0.0, 0.05, 0.0, "stable")
        ea, ca = gate_stability_effect(0.5, 0.3, ctx)
        assert ea == 0.5
        assert ca == 0.3

    def test_dampened_above_threshold(self):
        ctx = ContextSignal(0.0, 0.0, 0.5, 0.0, "noise")
        ea, ca = gate_stability_effect(0.5, 0.3, ctx)
        assert ea < 0.5
        assert ca < 0.3


class TestGateExplorationInputs:
    def test_passthrough_when_stable(self):
        ctx = ContextSignal(0.0, 0.0, 0.0, 0.0, "stable")
        streak, trend = gate_exploration_inputs(5, "degrading", [], ctx)
        assert streak == 5
        assert trend == "degrading"

    def test_suppressed_when_regime_detected(self):
        ctx = ContextSignal(0.3, 0.0, 0.0, 0.0, "regime_change")
        streak, trend = gate_exploration_inputs(5, "degrading", [], ctx)
        assert streak == 0
        assert trend == "flat"

    def test_suppressed_on_sharp_reward_drop(self):
        ctx = ContextSignal(0.0, 0.0, 0.0, 0.0, "stable")
        rewards = [1.0] * 20 + [0.4, 0.4, 0.4]
        streak, trend = gate_exploration_inputs(3, "degrading", rewards, ctx)
        assert streak == 0
        assert trend == "flat"

    def test_no_suppression_without_sharp_drop(self):
        ctx = ContextSignal(0.0, 0.0, 0.0, 0.0, "stable")
        rewards = [1.0] * 20 + [0.9, 0.9, 0.9]
        streak, trend = gate_exploration_inputs(3, "degrading", rewards, ctx)
        assert streak == 3
        assert trend == "degrading"

    def test_no_suppression_with_short_history(self):
        ctx = ContextSignal(0.0, 0.0, 0.0, 0.0, "stable")
        streak, trend = gate_exploration_inputs(3, "degrading", [0.4] * 3, ctx)
        assert streak == 3
