"""Tests for runtime.signal_sensitivity — adaptive signal sensitivity layer."""

from __future__ import annotations

import math
import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.signal_sensitivity import (
    DEFAULT_SENSITIVITY,
    MAX_BIAS,
    MAX_SENSITIVITY,
    MIN_SENSITIVITY,
    NO_SENSITIVITY,
    SensitivityResult,
    apply_sensitivity,
    compute_sensitivity,
)


class TestDeterminism(unittest.TestCase):
    def test_same_input_same_output(self):
        r1 = compute_sensitivity(
            combined_action_bias={"a": 0.02, "b": -0.01},
            consensus_score=0.7,
            signal_confidences={"causal": 0.3, "credit": 0.2},
            context_type="stable",
            active_signal_count=2,
        )
        r2 = compute_sensitivity(
            combined_action_bias={"a": 0.02, "b": -0.01},
            consensus_score=0.7,
            signal_confidences={"causal": 0.3, "credit": 0.2},
            context_type="stable",
            active_signal_count=2,
        )
        self.assertEqual(r1.sensitivity_factor, r2.sensitivity_factor)
        self.assertEqual(r1.reason, r2.reason)

    def test_repeated_calls_identical(self):
        results = [
            compute_sensitivity(
                combined_action_bias={"a": 0.03},
                consensus_score=0.8,
                signal_confidences={"x": 0.4},
                context_type="stable",
                active_signal_count=1,
            )
            for _ in range(10)
        ]
        for r in results[1:]:
            self.assertEqual(r.sensitivity_factor, results[0].sensitivity_factor)


class TestEarlyActivation(unittest.TestCase):
    def test_low_confidence_consistent_gets_boost(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.02, "b": 0.01},
            consensus_score=0.7,
            signal_confidences={"causal": 0.2, "credit": 0.15},
            context_type="stable",
            active_signal_count=2,
        )
        self.assertGreater(result.sensitivity_factor, 1.0)
        self.assertTrue(result.applied)
        self.assertIn("low_data_boost", result.reason)

    def test_low_confidence_but_inconsistent_no_boost(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.02, "b": -0.02, "c": 0.01, "d": -0.01},
            consensus_score=0.7,
            signal_confidences={"causal": 0.2},
            context_type="stable",
            active_signal_count=1,
        )
        self.assertLessEqual(result.low_data_boost, 1.01)

    def test_high_confidence_no_boost(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.03},
            consensus_score=0.8,
            signal_confidences={"causal": 0.8, "credit": 0.9},
            context_type="stable",
            active_signal_count=2,
        )
        self.assertAlmostEqual(result.low_data_boost, 1.0, places=2)

    def test_zero_confidence_no_boost(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.02},
            consensus_score=0.7,
            signal_confidences={"causal": 0.0},
            context_type="stable",
            active_signal_count=1,
        )
        self.assertAlmostEqual(result.low_data_boost, 1.0, places=2)


class TestNoiseSuppression(unittest.TestCase):
    def test_high_variance_low_consensus_suppresses(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.04, "b": -0.04},
            consensus_score=0.2,
            signal_confidences={"causal": 0.5},
            context_type="stable",
            active_signal_count=1,
        )
        self.assertLess(result.noise_suppression, 1.0)

    def test_low_variance_no_suppression(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.02, "b": 0.02},
            consensus_score=0.2,
            signal_confidences={"causal": 0.5},
            context_type="stable",
            active_signal_count=1,
        )
        self.assertAlmostEqual(result.noise_suppression, 1.0, places=2)

    def test_high_consensus_no_suppression(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.04, "b": -0.04},
            consensus_score=0.8,
            signal_confidences={"causal": 0.5},
            context_type="stable",
            active_signal_count=1,
        )
        self.assertAlmostEqual(result.noise_suppression, 1.0, places=2)


class TestContextGating(unittest.TestCase):
    def test_unstable_context_no_amplification(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.03},
            consensus_score=0.8,
            signal_confidences={"causal": 0.2},
            context_type="adversarial",
            active_signal_count=3,
        )
        self.assertEqual(result.sensitivity_factor, DEFAULT_SENSITIVITY)
        self.assertFalse(result.applied)

    def test_regime_context_no_amplification(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.03},
            consensus_score=0.8,
            signal_confidences={"causal": 0.2},
            context_type="regime_change",
            active_signal_count=3,
        )
        self.assertFalse(result.applied)

    def test_stable_context_allows_amplification(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.02, "b": 0.01},
            consensus_score=0.7,
            signal_confidences={"causal": 0.2, "credit": 0.15},
            context_type="stable",
            active_signal_count=2,
        )
        self.assertTrue(result.applied)


class TestDensityBoost(unittest.TestCase):
    def test_many_signals_high_consensus_boost(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.03},
            consensus_score=0.8,
            signal_confidences={"c1": 0.6, "c2": 0.5, "c3": 0.7, "c4": 0.6},
            context_type="stable",
            active_signal_count=4,
        )
        self.assertGreater(result.density_boost, 1.0)

    def test_few_signals_no_density_boost(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.03},
            consensus_score=0.8,
            signal_confidences={"c1": 0.6},
            context_type="stable",
            active_signal_count=1,
        )
        self.assertAlmostEqual(result.density_boost, 1.0, places=2)

    def test_many_signals_low_consensus_no_density_boost(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.03},
            consensus_score=0.3,
            signal_confidences={"c1": 0.6, "c2": 0.5, "c3": 0.7, "c4": 0.6},
            context_type="stable",
            active_signal_count=4,
        )
        self.assertAlmostEqual(result.density_boost, 1.0, places=2)


class TestBoundedScaling(unittest.TestCase):
    def test_factor_within_bounds(self):
        for conf in [0.0, 0.1, 0.3, 0.5, 0.8, 1.0]:
            for consensus in [0.0, 0.3, 0.5, 0.8, 1.0]:
                for count in [0, 1, 3, 6]:
                    result = compute_sensitivity(
                        combined_action_bias={"a": 0.03, "b": -0.02},
                        consensus_score=consensus,
                        signal_confidences={"x": conf},
                        context_type="stable",
                        active_signal_count=count,
                    )
                    self.assertGreaterEqual(result.sensitivity_factor, MIN_SENSITIVITY)
                    self.assertLessEqual(result.sensitivity_factor, MAX_SENSITIVITY)

    def test_applied_bias_bounded(self):
        biases = {"a": 0.05, "b": -0.05}
        sensitivity = SensitivityResult(
            sensitivity_factor=1.5,
            reason="test",
            applied=True,
            low_data_boost=1.5,
            noise_suppression=1.0,
            density_boost=1.0,
        )
        result = apply_sensitivity(biases, sensitivity)
        for val in result.values():
            self.assertLessEqual(abs(val), MAX_BIAS + 1e-9)

    def test_no_nans_or_infs(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.0},
            consensus_score=0.0,
            signal_confidences={},
            context_type="stable",
            active_signal_count=0,
        )
        self.assertFalse(math.isnan(result.sensitivity_factor))
        self.assertFalse(math.isinf(result.sensitivity_factor))


class TestApplySensitivity(unittest.TestCase):
    def test_not_applied_passthrough(self):
        biases = {"a": 0.03, "b": -0.02}
        result = apply_sensitivity(biases, NO_SENSITIVITY)
        self.assertEqual(result, biases)

    def test_factor_scales_biases(self):
        biases = {"a": 0.02}
        sensitivity = SensitivityResult(
            sensitivity_factor=1.3,
            reason="test",
            applied=True,
            low_data_boost=1.3,
            noise_suppression=1.0,
            density_boost=1.0,
        )
        result = apply_sensitivity(biases, sensitivity)
        self.assertAlmostEqual(result["a"], 0.026, places=4)

    def test_suppression_reduces_biases(self):
        biases = {"a": 0.04, "b": -0.03}
        sensitivity = SensitivityResult(
            sensitivity_factor=0.6,
            reason="noise",
            applied=True,
            low_data_boost=1.0,
            noise_suppression=0.6,
            density_boost=1.0,
        )
        result = apply_sensitivity(biases, sensitivity)
        self.assertAlmostEqual(result["a"], 0.024, places=4)

    def test_empty_biases_passthrough(self):
        result = apply_sensitivity(
            {},
            SensitivityResult(
                sensitivity_factor=1.3,
                reason="test",
                applied=True,
                low_data_boost=1.3,
                noise_suppression=1.0,
                density_boost=1.0,
            ),
        )
        self.assertEqual(result, {})

    def test_leader_protection(self):
        scores = {"a": 0.9, "b": 0.7}
        biases = {"a": -0.04, "b": 0.03}
        sensitivity = SensitivityResult(
            sensitivity_factor=1.3,
            reason="test",
            applied=True,
            low_data_boost=1.3,
            noise_suppression=1.0,
            density_boost=1.0,
        )
        result = apply_sensitivity(biases, sensitivity, strategy_scores=scores)
        if "a" in result:
            self.assertGreaterEqual(result["a"], 0.0)


class TestSafetyRules(unittest.TestCase):
    def test_low_consensus_no_amplification(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.03},
            consensus_score=0.1,
            signal_confidences={"causal": 0.3},
            context_type="stable",
            active_signal_count=1,
        )
        self.assertLessEqual(result.sensitivity_factor, DEFAULT_SENSITIVITY)

    def test_conflicting_signals_not_amplified(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.04, "b": -0.04},
            consensus_score=0.15,
            signal_confidences={"causal": 0.4, "credit": 0.4},
            context_type="stable",
            active_signal_count=2,
        )
        self.assertLessEqual(result.sensitivity_factor, DEFAULT_SENSITIVITY)


class TestNoRegressionBaseline(unittest.TestCase):
    def test_identity_with_default_confidence(self):
        result = compute_sensitivity(
            combined_action_bias={"a": 0.02},
            consensus_score=0.7,
            signal_confidences={"causal": 0.7},
            context_type="stable",
            active_signal_count=1,
        )
        self.assertAlmostEqual(result.sensitivity_factor, DEFAULT_SENSITIVITY, places=1)

    def test_no_signal_no_effect(self):
        result = compute_sensitivity(
            combined_action_bias={},
            consensus_score=0.8,
            signal_confidences={"causal": 0.5},
            context_type="stable",
            active_signal_count=1,
        )
        self.assertEqual(result, NO_SENSITIVITY)

    def test_stable_system_not_destabilized(self):
        biases = {"a": 0.03, "b": -0.01}
        for _ in range(50):
            sens = compute_sensitivity(
                combined_action_bias=biases,
                consensus_score=0.7,
                signal_confidences={"causal": 0.6},
                context_type="stable",
                active_signal_count=2,
            )
            applied = apply_sensitivity(biases, sens)
            for val in applied.values():
                self.assertLessEqual(abs(val), MAX_BIAS + 1e-9)


class TestToDict(unittest.TestCase):
    def test_serialization(self):
        result = SensitivityResult(
            sensitivity_factor=1.25,
            reason="low_data_boost",
            applied=True,
            low_data_boost=1.25,
            noise_suppression=1.0,
            density_boost=1.0,
        )
        d = result.to_dict()
        self.assertEqual(d["sensitivity_factor"], 1.25)
        self.assertEqual(d["reason"], "low_data_boost")
        self.assertTrue(d["applied"])


class TestOrchestratorInteraction(unittest.TestCase):
    def test_sensitivity_applied_to_orchestrated_output(self):
        from umh.runtime_engine.signal_orchestrator import (
            SignalBundle,
            SignalOrchestrator,
        )

        from dataclasses import dataclass

        @dataclass(frozen=True)
        class FakeCausalSignal:
            action_bias: dict[str, float]
            confidence: float = 0.3
            matched_context: str = "stable"

        @dataclass(frozen=True)
        class FakeCreditSignal:
            action_credit: dict[str, float]
            confidence: float = 0.2
            horizon: int = 5
            reason: str = "test"

        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.03, "b": 0.01}),
            credit_signal=FakeCreditSignal(action_credit={"a": 0.02, "b": 0.01}),
        )
        orch_result = orch.orchestrate(bundle)

        confidences = {name: 0.25 for name in orch_result.active_signals}

        sens = compute_sensitivity(
            combined_action_bias=orch_result.combined_action_bias,
            consensus_score=orch_result.consensus_score,
            signal_confidences=confidences,
            context_type="stable",
            active_signal_count=len(orch_result.active_signals),
        )

        scaled = apply_sensitivity(orch_result.combined_action_bias, sens)

        for val in scaled.values():
            self.assertLessEqual(abs(val), MAX_BIAS + 1e-9)

    def test_full_pipeline_with_real_signals(self):
        from umh.runtime_engine.causal_memory import CausalSignal
        from umh.runtime_engine.credit_assignment import CreditSignal
        from umh.runtime_engine.signal_orchestrator import (
            SignalBundle,
            SignalOrchestrator,
        )

        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=CausalSignal(
                action_bias={"a": 0.02, "b": -0.01},
                confidence=0.3,
                matched_context="stable",
                reason="data_available",
            ),
            credit_signal=CreditSignal(
                action_credit={"a": 0.01, "b": -0.02},
                horizon=8,
                confidence=0.2,
                reason="data_available",
            ),
        )
        orch_result = orch.orchestrate(bundle)

        sens = compute_sensitivity(
            combined_action_bias=orch_result.combined_action_bias,
            consensus_score=orch_result.consensus_score,
            signal_confidences={"causal": 0.3, "credit": 0.2},
            context_type="stable",
            active_signal_count=len(orch_result.active_signals),
        )

        self.assertGreaterEqual(sens.sensitivity_factor, MIN_SENSITIVITY)
        self.assertLessEqual(sens.sensitivity_factor, MAX_SENSITIVITY)


class TestBenchmarkIntegration(unittest.TestCase):
    def test_benchmark_smoke(self):
        from umh.runtime_engine.long_horizon_benchmark import (
            SYSTEM_FACTORIES,
            get_all_scenarios,
            run_long_horizon,
        )

        seed = 42
        scenarios = get_all_scenarios(seed=seed)
        scenario = scenarios["StaticStable"]
        sys_obj = SYSTEM_FACTORIES["eos_corrected"]()
        result = run_long_horizon(sys_obj, scenario, horizon=50, seed=seed)
        self.assertGreaterEqual(result.reward_metrics.avg_reward, 0.0)


if __name__ == "__main__":
    unittest.main()
