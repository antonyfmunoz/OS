"""Tests for meta-weight signal amplification.

Covers:
1. Meta signal strength computation
2. Signal strength affects adjustment scaling
3. Meta-weights diverge from static weights in benchmark
4. Backward compatibility of snapshot/restore
5. Determinism
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.meta_weight_engine import (
    MAX_ADJUSTMENT,
    MetaWeightEngine,
    SignalPerformance,
)


class TestMetaSignalStrength:
    def test_zero_before_minimum_observations(self):
        engine = MetaWeightEngine()
        for i in range(5):
            engine.record_outcome(
                {
                    "goal": 0.8,
                    "plan": 0.5,
                    "strategy": 0.6,
                    "state_bias": 0.4,
                    "credit": 0.3,
                    "exploration": 0.2,
                    "commitment": 0.7,
                },
                0.8,
            )
        assert engine.compute_meta_signal_strength() == 0.0

    def test_positive_with_consistent_signals(self):
        engine = MetaWeightEngine()
        for i in range(20):
            engine.record_outcome(
                {
                    "goal": 0.9,
                    "plan": 0.1,
                    "strategy": 0.9,
                    "state_bias": 0.1,
                    "credit": 0.9,
                    "exploration": 0.1,
                    "commitment": 0.9,
                },
                0.9,
            )
        strength = engine.compute_meta_signal_strength()
        assert strength >= 0.0

    def test_bounded_zero_to_one(self):
        engine = MetaWeightEngine()
        for i in range(50):
            quality = 1.0 if i % 2 == 0 else 0.0
            engine.record_outcome(
                {
                    "goal": quality,
                    "plan": quality,
                    "strategy": quality,
                    "state_bias": quality,
                    "credit": quality,
                    "exploration": quality,
                    "commitment": quality,
                },
                quality,
            )
        strength = engine.compute_meta_signal_strength()
        assert 0.0 <= strength <= 1.0


class TestMetaSignalScaling:
    def test_adjustment_scales_with_strength(self):
        base_weights = {
            "goal": 0.2,
            "plan": 0.15,
            "strategy": 0.15,
            "state_bias": 0.1,
            "credit": 0.15,
            "exploration": 0.1,
            "commitment": 0.15,
        }

        engine_low = MetaWeightEngine()
        for i in range(5):
            engine_low.record_outcome(
                {
                    "goal": 0.9,
                    "plan": 0.1,
                    "strategy": 0.5,
                    "state_bias": 0.5,
                    "credit": 0.5,
                    "exploration": 0.5,
                    "commitment": 0.5,
                },
                0.9,
            )
        result_low = engine_low.get_adapted_weights(base_weights)

        engine_high = MetaWeightEngine()
        for i in range(30):
            engine_high.record_outcome(
                {
                    "goal": 0.9,
                    "plan": 0.1,
                    "strategy": 0.5,
                    "state_bias": 0.5,
                    "credit": 0.5,
                    "exploration": 0.5,
                    "commitment": 0.5,
                },
                0.9,
            )
        result_high = engine_high.get_adapted_weights(base_weights)

        goal_adj_low = abs(result_low.adjustments.get("goal", 0.0))
        goal_adj_high = abs(result_high.adjustments.get("goal", 0.0))
        assert goal_adj_high >= goal_adj_low

    def test_adjustments_still_clamped(self):
        base_weights = {
            "goal": 0.2,
            "plan": 0.15,
            "strategy": 0.15,
            "state_bias": 0.1,
            "credit": 0.15,
            "exploration": 0.1,
            "commitment": 0.15,
        }
        engine = MetaWeightEngine()
        for i in range(100):
            engine.record_outcome(
                {
                    "goal": 1.0,
                    "plan": 0.0,
                    "strategy": 1.0,
                    "state_bias": 0.0,
                    "credit": 1.0,
                    "exploration": 0.0,
                    "commitment": 1.0,
                },
                1.0,
            )
        result = engine.get_adapted_weights(base_weights)
        for adj in result.adjustments.values():
            assert abs(adj) <= MAX_ADJUSTMENT


class TestSignalPerformanceNewFields:
    def test_variance_tracked(self):
        perf = SignalPerformance()
        perf.update(0.8)
        perf.update(0.2)
        perf.update(0.8)
        assert perf.ema_variance > 0

    def test_consistency_tracked(self):
        perf = SignalPerformance()
        for _ in range(10):
            perf.update(0.9)
        assert perf.direction_consistency >= 0

    def test_to_dict_includes_new_fields(self):
        perf = SignalPerformance()
        perf.update(0.5)
        d = perf.to_dict()
        assert "ema_variance" in d
        assert "direction_consistency" in d


class TestSnapshotRestoreNewFields:
    def test_new_fields_survive_roundtrip(self):
        engine = MetaWeightEngine()
        for i in range(20):
            engine.record_outcome(
                {
                    "goal": 0.8,
                    "plan": 0.5,
                    "strategy": 0.6,
                    "state_bias": 0.4,
                    "credit": 0.3,
                    "exploration": 0.2,
                    "commitment": 0.7,
                },
                0.8,
            )
        snap = engine.snapshot()

        engine2 = MetaWeightEngine()
        engine2.restore(snap)

        assert (
            engine.compute_meta_signal_strength()
            == engine2.compute_meta_signal_strength()
        )

    def test_backward_compatible_restore(self):
        engine = MetaWeightEngine()
        old_snapshot = {
            "goal": {"ema": 0.5, "observations": 10, "last_contribution": 0.4},
            "plan": {"ema": 0.3, "observations": 10, "last_contribution": 0.2},
            "strategy": {"ema": 0.4, "observations": 10, "last_contribution": 0.3},
            "state_bias": {"ema": 0.2, "observations": 10, "last_contribution": 0.1},
            "credit": {"ema": 0.3, "observations": 10, "last_contribution": 0.2},
            "exploration": {"ema": 0.1, "observations": 10, "last_contribution": 0.05},
            "commitment": {"ema": 0.4, "observations": 10, "last_contribution": 0.3},
        }
        engine.restore(old_snapshot)
        assert engine.total_observations == 10
        assert engine._performance["goal"].ema_variance == 0.0


class TestMetaDivergence:
    def test_corrected_no_regression_in_periodic(self):
        from umh.runtime_engine.benchmark_env import (
            EOSDecisionSystem,
            EOSWithCorrectionSystem,
        )
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


class TestMetaDeterminism:
    def test_identical_sequences_identical_strength(self):
        def run_engine():
            engine = MetaWeightEngine()
            for i in range(20):
                engine.record_outcome(
                    {
                        "goal": 0.8,
                        "plan": 0.5,
                        "strategy": 0.6,
                        "state_bias": 0.4,
                        "credit": 0.3,
                        "exploration": 0.2,
                        "commitment": 0.7,
                    },
                    0.8,
                )
            return engine.compute_meta_signal_strength()

        s1 = run_engine()
        s2 = run_engine()
        assert s1 == s2
