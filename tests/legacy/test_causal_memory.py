"""Tests for runtime.causal_memory — causal transition memory.

Covers:
1. Determinism
2. No data → no effect
3. Correct aggregation
4. Bounded outputs
5. Confidence scaling
6. No regression baseline
7. Persistence roundtrip
8. Context-specific learning
9. Multi-context separation
10. Pipeline integration
11. Benchmark integration
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.causal_memory import (
    MAX_BIAS,
    MIN_OBSERVATIONS,
    NO_CAUSAL_SIGNAL,
    CausalMemoryEngine,
    CausalSignal,
    TransitionStats,
    apply_causal_bias,
)


# ─── 1. Determinism ────────────────────────────────────────────────


class TestDeterminism:
    def test_identical_sequences_identical_signals(self):
        def run():
            engine = CausalMemoryEngine()
            for i in range(30):
                engine.record_transition("stable", "action_0", 0.8, 0.5)
            return engine.compute_signal("stable")

        s1 = run()
        s2 = run()
        assert s1.confidence == s2.confidence
        assert s1.action_bias == s2.action_bias

    def test_identical_sequences_identical_snapshots(self):
        def build():
            engine = CausalMemoryEngine()
            for i in range(20):
                engine.record_transition("stable", "action_0", 0.8, 0.5)
                engine.record_transition("regime_change", "action_1", 0.3, 0.2)
            return engine.snapshot()

        s1 = build()
        s2 = build()
        assert s1 == s2


# ─── 2. No data → no effect ────────────────────────────────────────


class TestNoDataNoEffect:
    def test_empty_engine_returns_no_signal(self):
        engine = CausalMemoryEngine()
        signal = engine.compute_signal("stable")
        assert signal is NO_CAUSAL_SIGNAL

    def test_below_min_observations_returns_no_signal(self):
        engine = CausalMemoryEngine()
        for i in range(MIN_OBSERVATIONS - 1):
            engine.record_transition("stable", "action_0", 0.8, 0.5)
        signal = engine.compute_signal("stable")
        assert not signal.action_bias

    def test_wrong_context_returns_no_signal(self):
        engine = CausalMemoryEngine()
        for i in range(30):
            engine.record_transition("stable", "action_0", 0.8, 0.5)
        signal = engine.compute_signal("adversarial")
        assert not signal.action_bias

    def test_no_signal_sentinel(self):
        assert NO_CAUSAL_SIGNAL.action_bias == {}
        assert NO_CAUSAL_SIGNAL.confidence == 0.0
        assert NO_CAUSAL_SIGNAL.reason == "no_data"

    def test_apply_no_signal_passthrough(self):
        scores = {"a": 0.5, "b": 0.3}
        adjusted = apply_causal_bias(scores, NO_CAUSAL_SIGNAL)
        assert adjusted == scores


# ─── 3. Correct aggregation ────────────────────────────────────────


class TestCorrectAggregation:
    def test_stats_track_count(self):
        ts = TransitionStats(context_type="stable", action="action_0")
        for _ in range(10):
            ts.update(0.1, 0.05)
        assert ts.count == 10

    def test_stats_track_positive_count(self):
        ts = TransitionStats(context_type="stable", action="action_0")
        ts.update(0.1, 0.05)
        ts.update(-0.1, -0.05)
        ts.update(0.2, 0.1)
        assert ts.positive_count == 2
        assert ts.success_rate > 0.6

    def test_stats_ema_smoothing(self):
        ts = TransitionStats(context_type="stable", action="action_0")
        for _ in range(20):
            ts.update(1.0, 0.5)
        for _ in range(20):
            ts.update(-1.0, -0.5)
        assert ts.avg_reward_delta < 1.0
        assert ts.avg_reward_delta > -1.0

    def test_engine_aggregates_per_context_action(self):
        engine = CausalMemoryEngine()
        for i in range(30):
            engine.record_transition("stable", "action_0", 0.9, 0.5)
        for i in range(30):
            engine.record_transition("stable", "action_1", 0.3, 0.2)
        assert engine.context_action_pairs >= 1


# ─── 4. Bounded outputs ────────────────────────────────────────────


class TestBoundedOutputs:
    def test_bias_within_bounds(self):
        engine = CausalMemoryEngine()
        for i in range(40):
            engine.record_transition("stable", "action_0", 1.0, 0.8)
        for i in range(40):
            engine.record_transition("stable", "action_1", 0.0, 0.0)
        signal = engine.compute_signal("stable")
        for bias in signal.action_bias.values():
            assert abs(bias) <= MAX_BIAS + 1e-9

    def test_confidence_bounded_zero_to_one(self):
        engine = CausalMemoryEngine()
        for i in range(100):
            engine.record_transition("stable", "action_0", 1.0, 1.0)
        signal = engine.compute_signal("stable")
        assert 0.0 <= signal.confidence <= 1.0

    def test_stability_score_bounded(self):
        ts = TransitionStats(context_type="stable", action="action_0")
        for _ in range(20):
            ts.update(1.0, 0.5)
        assert 0.0 <= ts.stability_score <= 1.0

    def test_apply_preserves_leader_with_large_gap(self):
        scores = {"action_0": 1.0, "action_1": 0.3, "action_2": 0.2}
        signal = CausalSignal(
            action_bias={"action_0": -0.05, "action_1": 0.05},
            confidence=1.0,
            matched_context="stable",
            reason="test",
        )
        adjusted = apply_causal_bias(scores, signal)
        assert max(adjusted, key=adjusted.get) == "action_0"


# ─── 5. Confidence scaling ─────────────────────────────────────────


class TestConfidenceScaling:
    def test_low_observations_low_confidence(self):
        engine = CausalMemoryEngine()
        for i in range(MIN_OBSERVATIONS + 2):
            engine.record_transition("stable", "action_0", 0.8, 0.5)
            engine.record_transition("stable", "action_1", 0.3, 0.2)
        signal = engine.compute_signal("stable")
        assert signal.confidence <= 1.0

    def test_high_observations_higher_confidence(self):
        engine = CausalMemoryEngine()
        for i in range(60):
            engine.record_transition("stable", "action_0", 0.8, 0.5)
            engine.record_transition("stable", "action_1", 0.3, 0.2)
        signal = engine.compute_signal("stable")
        assert signal.confidence > 0.3

    def test_high_variance_reduces_confidence(self):
        engine_stable = CausalMemoryEngine()
        engine_noisy = CausalMemoryEngine()

        for i in range(40):
            engine_stable.record_transition("stable", "action_0", 0.8, 0.5)
            engine_stable.record_transition("stable", "action_1", 0.3, 0.2)

        for i in range(40):
            val = 1.0 if i % 2 == 0 else 0.0
            engine_noisy.record_transition("stable", "action_0", val, val * 0.5)
            engine_noisy.record_transition(
                "stable", "action_1", 1.0 - val, (1.0 - val) * 0.5
            )

        sig_stable = engine_stable.compute_signal("stable")
        sig_noisy = engine_noisy.compute_signal("stable")
        assert sig_stable.confidence >= sig_noisy.confidence


# ─── 6. No regression baseline ─────────────────────────────────────


class TestNoRegressionBaseline:
    def test_periodic_no_regression(self):
        from umh.runtime_engine.benchmark_env import EOSDecisionSystem, EOSWithCorrectionSystem
        from umh.runtime_engine.long_horizon_benchmark import (
            PeriodicShiftScenario,
            run_long_horizon,
        )

        s1 = PeriodicShiftScenario(seed=42, period=200)
        corrected = EOSWithCorrectionSystem()
        r_corr = run_long_horizon(corrected, s1, horizon=1000, seed=42)

        s2 = PeriodicShiftScenario(seed=42, period=200)
        substrate = EOSDecisionSystem()
        r_sub = run_long_horizon(substrate, s2, horizon=1000, seed=42)

        assert (
            r_corr.reward_metrics.avg_reward >= r_sub.reward_metrics.avg_reward * 0.99
        )

    def test_adversarial_no_regression(self):
        from umh.runtime_engine.benchmark_env import EOSWithCorrectionSystem
        from umh.runtime_engine.long_horizon_benchmark import (
            AdversarialFlipScenario,
            run_long_horizon,
        )

        scenario = AdversarialFlipScenario(seed=42, flip_start=300, flip_end=500)
        system = EOSWithCorrectionSystem()
        result = run_long_horizon(system, scenario, horizon=1000, seed=42)
        assert result.reward_metrics.avg_reward > 0.72

    def test_static_no_regression(self):
        from umh.runtime_engine.benchmark_env import EOSDecisionSystem, EOSWithCorrectionSystem
        from umh.runtime_engine.long_horizon_benchmark import (
            StaticStableScenario,
            run_long_horizon,
        )

        s1 = StaticStableScenario(seed=42)
        corrected = EOSWithCorrectionSystem()
        r_corr = run_long_horizon(corrected, s1, horizon=1000, seed=42)

        s2 = StaticStableScenario(seed=42)
        substrate = EOSDecisionSystem()
        r_sub = run_long_horizon(substrate, s2, horizon=1000, seed=42)

        assert (
            r_corr.reward_metrics.avg_reward >= r_sub.reward_metrics.avg_reward * 0.99
        )


# ─── 7. Persistence roundtrip ──────────────────────────────────────


class TestPersistenceRoundtrip:
    def test_snapshot_restore_roundtrip(self):
        engine1 = CausalMemoryEngine()
        for i in range(30):
            engine1.record_transition("stable", "action_0", 0.8, 0.5)
            engine1.record_transition("regime_change", "action_1", 0.3, 0.2)
        snap = engine1.snapshot()

        engine2 = CausalMemoryEngine()
        engine2.restore(snap)

        assert engine2.observation_count == engine1.observation_count
        assert engine2.context_action_pairs == engine1.context_action_pairs
        assert engine2.snapshot() == snap

    def test_restore_none_safe(self):
        engine = CausalMemoryEngine()
        engine.restore(None)
        assert engine.observation_count == 0

    def test_restore_empty_dict_safe(self):
        engine = CausalMemoryEngine()
        engine.restore({})
        assert engine.observation_count == 0

    def test_snapshot_has_version(self):
        engine = CausalMemoryEngine()
        snap = engine.snapshot()
        assert "version" in snap
        assert snap["version"] == 1

    def test_restored_engine_produces_same_signal(self):
        engine1 = CausalMemoryEngine()
        for i in range(30):
            engine1.record_transition("stable", "action_0", 0.9, 0.6)
            engine1.record_transition("stable", "action_1", 0.3, 0.1)
        snap = engine1.snapshot()

        engine2 = CausalMemoryEngine()
        engine2.restore(snap)

        s1 = engine1.compute_signal("stable")
        s2 = engine2.compute_signal("stable")
        assert s1.confidence == s2.confidence
        assert s1.action_bias == s2.action_bias


# ─── 8. Context-specific learning ──────────────────────────────────


class TestContextSpecificLearning:
    def test_learns_different_patterns_per_context(self):
        engine = CausalMemoryEngine()
        for i in range(30):
            engine.record_transition("stable", "action_0", 0.9, 0.6)
        for i in range(30):
            engine.record_transition("adversarial", "action_0", 0.1, -0.2)

        sig_stable = engine.compute_signal("stable")
        sig_adv = engine.compute_signal("adversarial")

        assert sig_stable.matched_context == "stable"
        assert sig_adv.matched_context == "adversarial"

    def test_context_match_only_uses_relevant_data(self):
        engine = CausalMemoryEngine()
        for i in range(30):
            engine.record_transition("stable", "action_0", 0.9, 0.6)
        for i in range(30):
            engine.record_transition("noise", "action_0", 0.3, 0.1)

        sig_stable = engine.compute_signal("stable")
        sig_noise = engine.compute_signal("noise")

        assert sig_stable.matched_context == "stable"
        assert sig_noise.matched_context == "noise"


# ─── 9. Multi-context separation ───────────────────────────────────


class TestMultiContextSeparation:
    def test_separate_contexts_produce_independent_signals(self):
        engine = CausalMemoryEngine()
        for i in range(30):
            engine.record_transition("stable", "action_0", 0.9, 0.6)
        for i in range(30):
            engine.record_transition("drift", "action_1", 0.8, 0.5)

        sig_stable = engine.compute_signal("stable")
        sig_drift = engine.compute_signal("drift")

        assert sig_stable.matched_context != sig_drift.matched_context

    def test_unknown_context_returns_no_signal(self):
        engine = CausalMemoryEngine()
        for i in range(30):
            engine.record_transition("stable", "action_0", 0.9, 0.6)
        signal = engine.compute_signal("never_seen_before")
        assert not signal.action_bias


# ─── 10. Pipeline integration ──────────────────────────────────────


class TestPipelineIntegration:
    def test_apply_causal_bias_additive(self):
        scores = {"action_0": 0.5, "action_1": 0.3}
        signal = CausalSignal(
            action_bias={"action_0": 0.02, "action_1": -0.02},
            confidence=0.8,
            matched_context="stable",
            reason="test",
        )
        adjusted = apply_causal_bias(scores, signal)
        assert abs(adjusted["action_0"] - 0.52) < 1e-9
        assert abs(adjusted["action_1"] - 0.28) < 1e-9

    def test_apply_empty_bias_passthrough(self):
        scores = {"action_0": 0.5, "action_1": 0.3}
        signal = CausalSignal(
            action_bias={},
            confidence=0.0,
            matched_context="stable",
            reason="test",
        )
        adjusted = apply_causal_bias(scores, signal)
        assert adjusted == scores

    def test_apply_empty_scores_passthrough(self):
        signal = CausalSignal(
            action_bias={"action_0": 0.02},
            confidence=0.8,
            matched_context="stable",
            reason="test",
        )
        adjusted = apply_causal_bias({}, signal)
        assert adjusted == {}

    def test_to_dict(self):
        signal = CausalSignal(
            action_bias={"action_0": 0.03},
            confidence=0.75,
            matched_context="stable",
            reason="causal_bias_applied",
        )
        d = signal.to_dict()
        assert "action_bias" in d
        assert "confidence" in d
        assert "matched_context" in d

    def test_stats_to_dict(self):
        ts = TransitionStats(context_type="stable", action="action_0")
        ts.update(0.1, 0.05)
        d = ts.to_dict()
        assert d["context_type"] == "stable"
        assert d["count"] == 1

    def test_reset_clears_state(self):
        engine = CausalMemoryEngine()
        for i in range(20):
            engine.record_transition("stable", "action_0", 0.8, 0.5)
        engine.reset()
        assert engine.observation_count == 0
        assert engine.context_action_pairs == 0


# ─── 11. Benchmark integration ─────────────────────────────────────


class TestBenchmarkIntegration:
    def test_mixed_regime_no_regression(self):
        from umh.runtime_engine.benchmark_env import EOSDecisionSystem, EOSWithCorrectionSystem
        from umh.runtime_engine.long_horizon_benchmark import (
            MixedRegimeScenario,
            run_long_horizon,
        )

        s1 = MixedRegimeScenario(seed=42)
        corrected = EOSWithCorrectionSystem()
        r_corr = run_long_horizon(corrected, s1, horizon=1000, seed=42)

        s2 = MixedRegimeScenario(seed=42)
        substrate = EOSDecisionSystem()
        r_sub = run_long_horizon(substrate, s2, horizon=1000, seed=42)

        assert (
            r_corr.reward_metrics.avg_reward >= r_sub.reward_metrics.avg_reward * 0.99
        )

    def test_restart_continuity(self):
        from umh.runtime_engine.benchmark_env import EOSWithCorrectionSystem
        from umh.runtime_engine.long_horizon_benchmark import (
            StaticStableScenario,
            simulate_restart_continuity,
        )

        scenario = StaticStableScenario(seed=42)
        rc = simulate_restart_continuity(
            EOSWithCorrectionSystem, scenario, horizon=1000, seed=42
        )
        assert rc.divergence < 0.001
        assert rc.within_tolerance

    def test_slow_drift_no_regression(self):
        from umh.runtime_engine.benchmark_env import EOSDecisionSystem, EOSWithCorrectionSystem
        from umh.runtime_engine.long_horizon_benchmark import (
            SlowDriftScenario,
            run_long_horizon,
        )

        s1 = SlowDriftScenario(seed=42)
        corrected = EOSWithCorrectionSystem()
        r_corr = run_long_horizon(corrected, s1, horizon=1000, seed=42)

        s2 = SlowDriftScenario(seed=42)
        substrate = EOSDecisionSystem()
        r_sub = run_long_horizon(substrate, s2, horizon=1000, seed=42)

        assert (
            r_corr.reward_metrics.avg_reward >= r_sub.reward_metrics.avg_reward * 0.99
        )
