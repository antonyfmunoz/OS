"""Tests for trap recovery engine — adversarial recovery validation.

Covers:
1. Trap detection activates on sustained mismatch
2. Trap signal is correctly bounded
3. Adjustments penalize dominant and boost alternatives
4. Signal deactivates when reward improves
5. Adversarial flip recovery in full simulation
6. Determinism
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.trap_recovery_engine import (
    MAX_TRAP_BIAS,
    NO_TRAP_SIGNAL,
    TrapDetector,
    TrapSignal,
    apply_trap_adjustments,
)


class TestTrapDetection:
    def test_no_signal_before_minimum_window(self):
        det = TrapDetector()
        for i in range(5):
            det.observe("action_0", 0.5)
        signal = det.compute_signal({"action_0": 1.0, "action_1": 0.5})
        assert not signal.active

    def test_activates_on_sustained_mismatch(self):
        det = TrapDetector()
        for i in range(20):
            det.observe("action_0", 1.0)
        for i in range(20):
            det.observe("action_0", 0.4)
        signal = det.compute_signal({"action_0": 1.0, "action_1": 0.5})
        assert signal.active
        assert signal.dominant_action == "action_0"

    def test_does_not_activate_on_high_reward(self):
        det = TrapDetector()
        for i in range(40):
            det.observe("action_0", 0.9)
        signal = det.compute_signal({"action_0": 1.0, "action_1": 0.5})
        assert not signal.active

    def test_does_not_activate_on_diverse_actions(self):
        det = TrapDetector()
        actions = ["action_0", "action_1", "action_2", "action_3"]
        for i in range(40):
            det.observe(actions[i % 4], 0.4)
        signal = det.compute_signal({"action_0": 1.0, "action_1": 0.5})
        assert not signal.active

    def test_deactivates_when_reward_improves(self):
        det = TrapDetector()
        for i in range(20):
            det.observe("action_0", 1.0)
        for i in range(15):
            det.observe("action_0", 0.4)
        signal = det.compute_signal({"action_0": 1.0, "action_1": 0.5})
        assert signal.active

        for i in range(20):
            det.observe("action_0", 1.0)
        signal2 = det.compute_signal({"action_0": 1.0, "action_1": 0.5})
        assert not signal2.active


class TestTrapSignalBounds:
    def test_adjustment_bounded(self):
        det = TrapDetector()
        for i in range(20):
            det.observe("action_0", 1.0)
        for i in range(30):
            det.observe("action_0", 0.1)
        signal = det.compute_signal({"action_0": 1.0, "action_1": 0.5})
        assert signal.trap_adjustment <= MAX_TRAP_BIAS
        assert signal.trap_adjustment >= 0.0

    def test_no_signal_has_zero_adjustment(self):
        assert NO_TRAP_SIGNAL.trap_adjustment == 0.0
        assert not NO_TRAP_SIGNAL.active


class TestTrapAdjustments:
    def test_apply_penalizes_dominant(self):
        scores = {"action_0": 1.0, "action_1": 0.5, "action_2": 0.3}
        signal = TrapSignal(
            active=True,
            dominant_action="action_0",
            trap_adjustment=0.04,
            reward_mismatch=0.4,
            stagnation_length=10,
            reason="test",
        )
        adjusted = apply_trap_adjustments(scores, signal)
        assert adjusted["action_0"] < scores["action_0"]
        assert adjusted["action_1"] > scores["action_1"]
        assert adjusted["action_2"] > scores["action_2"]

    def test_apply_no_signal_passthrough(self):
        scores = {"action_0": 1.0, "action_1": 0.5}
        adjusted = apply_trap_adjustments(scores, NO_TRAP_SIGNAL)
        assert adjusted == scores

    def test_adjusted_scores_penalize_dominant(self):
        scores = {"action_0": 0.02, "action_1": 0.5}
        signal = TrapSignal(
            active=True,
            dominant_action="action_0",
            trap_adjustment=0.05,
            reward_mismatch=0.5,
            stagnation_length=10,
            reason="test",
        )
        adjusted = apply_trap_adjustments(scores, signal)
        assert adjusted["action_0"] < scores["action_0"]
        assert adjusted["action_1"] > scores["action_1"]


class TestTrapSnapshotRestore:
    def test_snapshot_restore_preserves_state(self):
        det1 = TrapDetector()
        for i in range(30):
            det1.observe("action_0", 0.8 - i * 0.01)

        snap = det1.snapshot()
        det2 = TrapDetector()
        det2.restore(snap)

        signal1 = det1.compute_signal({"action_0": 1.0, "action_1": 0.5})
        signal2 = det2.compute_signal({"action_0": 1.0, "action_1": 0.5})

        assert signal1.active == signal2.active
        assert signal1.trap_adjustment == signal2.trap_adjustment

    def test_restore_empty_dict_safe(self):
        det = TrapDetector()
        det.restore({})
        signal = det.compute_signal({"action_0": 1.0})
        assert not signal.active

    def test_restore_none_safe(self):
        det = TrapDetector()
        det.restore(None)
        signal = det.compute_signal({"action_0": 1.0})
        assert not signal.active


class TestTrapDeterminism:
    def test_identical_sequences_identical_signals(self):
        def run_detector():
            det = TrapDetector()
            for i in range(20):
                det.observe("action_0", 1.0)
            for i in range(20):
                det.observe("action_0", 0.4)
            return det.compute_signal({"action_0": 1.0, "action_1": 0.5})

        s1 = run_detector()
        s2 = run_detector()
        assert s1.active == s2.active
        assert s1.trap_adjustment == s2.trap_adjustment
        assert s1.dominant_action == s2.dominant_action


class TestAdversarialRecovery:
    def test_corrected_system_recovers_from_flip(self):
        from umh.runtime_engine.benchmark_env import EOSWithCorrectionSystem
        from umh.runtime_engine.long_horizon_benchmark import (
            AdversarialFlipScenario,
            run_long_horizon,
        )

        scenario = AdversarialFlipScenario(seed=42, flip_start=300, flip_end=500)
        system = EOSWithCorrectionSystem()
        result = run_long_horizon(system, scenario, horizon=1000, seed=42)

        assert result.reward_metrics.avg_reward > 0.72

    def test_corrected_beats_uncorrected_in_adversarial(self):
        from umh.runtime_engine.benchmark_env import EOSDecisionSystem, EOSWithCorrectionSystem
        from umh.runtime_engine.long_horizon_benchmark import (
            AdversarialFlipScenario,
            run_long_horizon,
        )

        s1 = AdversarialFlipScenario(seed=42)
        corrected = EOSWithCorrectionSystem()
        r_corr = run_long_horizon(corrected, s1, horizon=1000, seed=42)

        s2 = AdversarialFlipScenario(seed=42)
        uncorr = EOSDecisionSystem()
        r_uncorr = run_long_horizon(uncorr, s2, horizon=1000, seed=42)

        assert r_corr.reward_metrics.avg_reward >= r_uncorr.reward_metrics.avg_reward


class TestTrapToDict:
    def test_active_signal_to_dict(self):
        signal = TrapSignal(
            active=True,
            dominant_action="action_0",
            trap_adjustment=0.03,
            reward_mismatch=0.4,
            stagnation_length=10,
            reason="test",
        )
        d = signal.to_dict()
        assert d["active"] is True
        assert "dominant_action" in d
        assert "reason" in d

    def test_inactive_signal_to_dict(self):
        d = NO_TRAP_SIGNAL.to_dict()
        assert d["active"] is False
        assert "dominant_action" not in d
