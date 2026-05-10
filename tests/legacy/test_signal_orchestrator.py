"""Tests for eos_ai.signal_orchestrator — signal coordination layer."""

from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from typing import Any

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.signal_orchestrator import (
    MAX_COMBINED_BIAS,
    NO_ORCHESTRATED_SIGNAL,
    OrchestratedSignal,
    SignalBundle,
    SignalOrchestrator,
    _bias_variance,
    _cosine_similarity,
    _sign_agreement_ratio,
    apply_orchestrated_signal,
)


# ─── Fake signal types for testing ──────────────────────────────────


@dataclass(frozen=True)
class FakeCausalSignal:
    action_bias: dict[str, float]
    confidence: float = 0.6
    matched_context: str = "stable"


@dataclass(frozen=True)
class FakeCreditSignal:
    action_credit: dict[str, float]
    confidence: float = 0.5
    horizon: int = 10
    reason: str = "test"


@dataclass(frozen=True)
class FakeForesightSignal:
    action_bias: dict[str, float]
    confidence: float = 0.5
    horizon: int = 3
    reason: str = "test"


@dataclass(frozen=True)
class FakeMetaSignal:
    matched: bool = True
    priors: dict[str, float] | None = None
    similarity: float = 0.8
    prototype_id: int | None = 0
    signature: Any = None
    prototype_usage_count: int = 5
    prototype_avg_reward: float = 0.8


@dataclass(frozen=True)
class FakeExplorationSignal:
    exploration_active: bool = True
    exploration_adjustments: dict[str, float] | None = None
    exploration_reason: str = "test"
    candidates_boosted: tuple[str, ...] = ()
    activation_strength: float = 0.5


@dataclass(frozen=True)
class FakeTrapSignal:
    active: bool = True
    dominant_action: str | None = "action_0"
    trap_adjustment: float = 0.03
    reward_mismatch: float = 0.7
    stagnation_length: int = 5
    reason: str = "test"


@dataclass(frozen=True)
class FakeStabilitySignal:
    active: bool = True
    switch_rate: float = 0.8
    reward_improvement: float = 0.0
    exploration_adjustment: float = -0.02
    confidence_adjustment: float = 0.02
    reason: str = "test"


@dataclass(frozen=True)
class FakeContextSignal:
    regime_change_likelihood: float = 0.0
    adversarial_likelihood: float = 0.0
    noise_level: float = 0.1
    drift_strength: float = 0.0
    dominant_type: str = "stable"


# ─── Tests ──────────────────────────────────────────────────────────


class TestDeterminism(unittest.TestCase):
    def test_same_input_same_output(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.02, "b": -0.01}),
            credit_signal=FakeCreditSignal(action_credit={"a": 0.01, "b": -0.02}),
        )
        r1 = orch.orchestrate(bundle)
        r2 = orch.orchestrate(bundle)
        self.assertEqual(r1.combined_action_bias, r2.combined_action_bias)
        self.assertEqual(r1.consensus_score, r2.consensus_score)
        self.assertEqual(r1.active_signals, r2.active_signals)

    def test_repeated_calls_no_state_drift(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.03}),
            foresight_signal=FakeForesightSignal(action_bias={"a": 0.02}),
        )
        results = [orch.orchestrate(bundle) for _ in range(10)]
        for r in results[1:]:
            self.assertEqual(r.combined_action_bias, results[0].combined_action_bias)


class TestNoDataNoEffect(unittest.TestCase):
    def test_empty_bundle(self):
        orch = SignalOrchestrator()
        result = orch.orchestrate(SignalBundle())
        self.assertEqual(result.combined_action_bias, {})
        self.assertEqual(result.reason, "no_signals")

    def test_all_none_signals(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            meta_signal=None,
            context_signal=None,
            causal_signal=None,
            credit_signal=None,
            foresight_signal=None,
            exploration_signal=None,
            trap_signal=None,
            stability_signal=None,
        )
        result = orch.orchestrate(bundle)
        self.assertEqual(result, NO_ORCHESTRATED_SIGNAL)

    def test_inactive_signals_produce_no_effect(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            trap_signal=FakeTrapSignal(active=False),
            stability_signal=FakeStabilitySignal(active=False),
            exploration_signal=FakeExplorationSignal(exploration_active=False),
        )
        result = orch.orchestrate(bundle)
        self.assertEqual(result.combined_action_bias, {})

    def test_empty_bias_signals(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={}),
            credit_signal=FakeCreditSignal(action_credit={}),
        )
        result = orch.orchestrate(bundle)
        self.assertEqual(result.combined_action_bias, {})

    def test_context_engine_never_produces_bias(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            context_signal=FakeContextSignal(),
        )
        result = orch.orchestrate(bundle)
        self.assertEqual(result.combined_action_bias, {})


class TestAgreementBoosting(unittest.TestCase):
    def test_aligned_signals_amplified(self):
        orch = SignalOrchestrator()
        bundle_aligned = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.03, "b": -0.02}),
            credit_signal=FakeCreditSignal(action_credit={"a": 0.02, "b": -0.01}),
            foresight_signal=FakeForesightSignal(action_bias={"a": 0.03, "b": -0.02}),
        )
        result = orch.orchestrate(bundle_aligned)
        self.assertIn("a", result.combined_action_bias)
        self.assertGreater(result.combined_action_bias.get("a", 0), 0)
        self.assertGreater(result.consensus_score, 0.5)

    def test_consensus_score_high_when_aligned(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"x": 0.04}),
            credit_signal=FakeCreditSignal(action_credit={"x": 0.03}),
        )
        result = orch.orchestrate(bundle)
        self.assertGreater(result.consensus_score, 0.5)

    def test_aligned_beats_single_signal(self):
        orch = SignalOrchestrator()
        single = orch.orchestrate(
            SignalBundle(
                causal_signal=FakeCausalSignal(
                    action_bias={"a": 0.02, "b": -0.01}, confidence=0.6
                ),
            )
        )
        multi = orch.orchestrate(
            SignalBundle(
                causal_signal=FakeCausalSignal(
                    action_bias={"a": 0.02, "b": -0.01}, confidence=0.6
                ),
                credit_signal=FakeCreditSignal(
                    action_credit={"a": 0.02, "b": -0.01}, confidence=0.6
                ),
            )
        )
        self.assertGreaterEqual(multi.total_confidence, single.total_confidence)


class TestConflictSuppression(unittest.TestCase):
    def test_conflicting_signals_dampened(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.04, "b": -0.03}),
            credit_signal=FakeCreditSignal(action_credit={"a": -0.04, "b": 0.03}),
        )
        result = orch.orchestrate(bundle)
        self.assertLess(result.consensus_score, 0.5)
        for val in result.combined_action_bias.values():
            self.assertLessEqual(abs(val), MAX_COMBINED_BIAS)

    def test_all_signals_disagree(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.04, "b": -0.03}),
            credit_signal=FakeCreditSignal(action_credit={"a": -0.04, "b": 0.03}),
            foresight_signal=FakeForesightSignal(action_bias={"a": 0.01, "b": 0.04}),
        )
        result = orch.orchestrate(bundle)
        self.assertLessEqual(result.consensus_score, 0.6)
        for val in result.combined_action_bias.values():
            self.assertLessEqual(abs(val), MAX_COMBINED_BIAS)

    def test_suppression_reported(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(
                action_bias={"a": 0.04, "b": -0.03}, confidence=0.8
            ),
            credit_signal=FakeCreditSignal(
                action_credit={"a": -0.04, "b": 0.03}, confidence=0.1
            ),
            foresight_signal=FakeForesightSignal(
                action_bias={"a": -0.03, "b": 0.04}, confidence=0.1
            ),
        )
        result = orch.orchestrate(bundle)
        total = len(result.active_signals) + len(result.suppressed_signals)
        self.assertGreater(total, 0)


class TestBoundedOutputs(unittest.TestCase):
    def test_combined_bias_bounded(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.05, "b": -0.05}),
            credit_signal=FakeCreditSignal(action_credit={"a": 0.05, "b": -0.05}),
            foresight_signal=FakeForesightSignal(action_bias={"a": 0.05, "b": -0.05}),
        )
        result = orch.orchestrate(bundle)
        for val in result.combined_action_bias.values():
            self.assertLessEqual(abs(val), MAX_COMBINED_BIAS + 1e-9)

    def test_consensus_score_in_range(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.02}),
            credit_signal=FakeCreditSignal(action_credit={"a": 0.01}),
        )
        result = orch.orchestrate(bundle)
        self.assertGreaterEqual(result.consensus_score, 0.0)
        self.assertLessEqual(result.consensus_score, 1.0)

    def test_confidence_in_range(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.02}),
            credit_signal=FakeCreditSignal(action_credit={"a": 0.01}),
        )
        result = orch.orchestrate(bundle)
        self.assertGreaterEqual(result.total_confidence, 0.0)
        self.assertLessEqual(result.total_confidence, 1.0)

    def test_scale_factors_in_range(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.02}),
            credit_signal=FakeCreditSignal(action_credit={"a": -0.01}),
            foresight_signal=FakeForesightSignal(action_bias={"a": 0.03}),
        )
        result = orch.orchestrate(bundle)
        for sf in result.scale_factors.values():
            self.assertGreaterEqual(sf, 0.0)
            self.assertLessEqual(sf, 1.0)

    def test_leader_protection(self):
        orch = SignalOrchestrator()
        scores = {"a": 0.9, "b": 0.7}
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": -0.05, "b": 0.05}),
            credit_signal=FakeCreditSignal(action_credit={"a": -0.04, "b": 0.04}),
        )
        result = orch.orchestrate(bundle, strategy_scores=scores)
        if "a" in result.combined_action_bias:
            self.assertGreaterEqual(result.combined_action_bias["a"], 0.0)


class TestPartialAvailability(unittest.TestCase):
    def test_single_signal_passthrough(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.03}),
        )
        result = orch.orchestrate(bundle)
        self.assertEqual(result.reason, "single_signal")
        self.assertIn("a", result.combined_action_bias)
        self.assertEqual(result.consensus_score, 1.0)

    def test_two_of_eight_signals(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.02}),
            foresight_signal=FakeForesightSignal(action_bias={"a": 0.03}),
        )
        result = orch.orchestrate(bundle)
        self.assertIn("a", result.combined_action_bias)
        self.assertEqual(len(result.active_signals), 2)

    def test_mixed_signal_types(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.02}),
            trap_signal=FakeTrapSignal(
                active=True, dominant_action="b", trap_adjustment=0.03
            ),
        )
        result = orch.orchestrate(bundle)
        self.assertGreater(len(result.active_signals), 0)

    def test_meta_signal_requires_matched(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            meta_signal=FakeMetaSignal(matched=False, priors={"a": 0.02}),
        )
        result = orch.orchestrate(bundle)
        self.assertEqual(result.combined_action_bias, {})


class TestPriorityResolution(unittest.TestCase):
    def test_stability_outranks_exploration(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(
                action_bias={"a": 0.04, "b": -0.03}, confidence=0.8
            ),
            credit_signal=FakeCreditSignal(
                action_credit={"a": -0.04, "b": 0.03}, confidence=0.1
            ),
            foresight_signal=FakeForesightSignal(
                action_bias={"a": -0.03, "b": 0.04}, confidence=0.1
            ),
        )
        result = orch.orchestrate(bundle)
        if result.suppressed_signals:
            for suppressed in result.suppressed_signals:
                self.assertNotEqual(suppressed, "stability_guard")

    def test_dominant_signal_identified(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(
                action_bias={"a": 0.04, "b": -0.03}, confidence=0.9
            ),
            credit_signal=FakeCreditSignal(action_credit={"a": 0.01}, confidence=0.2),
        )
        result = orch.orchestrate(bundle)
        self.assertTrue(len(result.dominant_signal_source) > 0)


class TestSignalExtraction(unittest.TestCase):
    def test_trap_signal_converted(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            trap_signal=FakeTrapSignal(
                active=True, dominant_action="x", trap_adjustment=0.04
            ),
        )
        result = orch.orchestrate(bundle)
        self.assertIn("x", result.combined_action_bias)
        self.assertLess(result.combined_action_bias["x"], 0)

    def test_exploration_signal_converted(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            exploration_signal=FakeExplorationSignal(
                exploration_active=True,
                exploration_adjustments={"a": -0.03, "b": 0.02},
            ),
        )
        result = orch.orchestrate(bundle)
        self.assertIn("a", result.combined_action_bias)

    def test_stability_guard_uses_internal_key(self):
        """Stability guard has no per-action bias, uses __stability_dampen__."""
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            stability_signal=FakeStabilitySignal(
                active=True, exploration_adjustment=-0.02
            ),
        )
        result = orch.orchestrate(bundle)
        self.assertNotIn("__stability_dampen__", result.combined_action_bias)


class TestCosineHelpers(unittest.TestCase):
    def test_identical_vectors(self):
        a = {"x": 1.0, "y": -0.5}
        self.assertAlmostEqual(_cosine_similarity(a, a), 1.0, places=6)

    def test_opposite_vectors(self):
        a = {"x": 1.0, "y": -0.5}
        b = {"x": -1.0, "y": 0.5}
        self.assertAlmostEqual(_cosine_similarity(a, b), -1.0, places=6)

    def test_orthogonal_vectors(self):
        a = {"x": 1.0}
        b = {"y": 1.0}
        self.assertAlmostEqual(_cosine_similarity(a, b), 0.0, places=6)

    def test_empty_vectors(self):
        self.assertEqual(_cosine_similarity({}, {}), 0.0)

    def test_sign_agreement_all_agree(self):
        v1 = {"a": 0.1, "b": -0.2}
        v2 = {"a": 0.3, "b": -0.1}
        self.assertAlmostEqual(_sign_agreement_ratio([v1, v2]), 1.0)

    def test_sign_agreement_none_agree(self):
        v1 = {"a": 0.1, "b": -0.2}
        v2 = {"a": -0.3, "b": 0.1}
        self.assertAlmostEqual(_sign_agreement_ratio([v1, v2]), 0.0)

    def test_bias_variance_identical(self):
        v = [{"a": 0.1}, {"a": 0.1}]
        self.assertAlmostEqual(_bias_variance(v), 0.0)

    def test_bias_variance_different(self):
        v = [{"a": 0.1}, {"a": -0.1}]
        self.assertGreater(_bias_variance(v), 0.0)


class TestToDict(unittest.TestCase):
    def test_orchestrated_signal_to_dict(self):
        sig = OrchestratedSignal(
            combined_action_bias={"a": 0.02345},
            total_confidence=0.7123,
            consensus_score=0.8456,
            active_signals=("causal_memory", "credit_assignment"),
            suppressed_signals=("exploration_engine",),
            dominant_signal_source="causal_memory",
            scale_factors={"causal_memory": 0.9, "credit_assignment": 0.7},
            reason="orchestrated",
        )
        d = sig.to_dict()
        self.assertIn("combined_action_bias", d)
        self.assertIn("active_signals", d)
        self.assertEqual(d["reason"], "orchestrated")


class TestApplyOrchestratedSignal(unittest.TestCase):
    def test_applies_bias_additively(self):
        scores = {"a": 0.5, "b": 0.3}
        sig = OrchestratedSignal(
            combined_action_bias={"a": 0.02, "b": -0.01},
            total_confidence=0.7,
            consensus_score=0.8,
            active_signals=("causal_memory",),
            suppressed_signals=(),
            dominant_signal_source="causal_memory",
            scale_factors={},
            reason="orchestrated",
        )
        adjusted = apply_orchestrated_signal(scores, sig)
        self.assertAlmostEqual(adjusted["a"], 0.52, places=4)
        self.assertAlmostEqual(adjusted["b"], 0.29, places=4)

    def test_no_bias_passthrough(self):
        scores = {"a": 0.5}
        result = apply_orchestrated_signal(scores, NO_ORCHESTRATED_SIGNAL)
        self.assertEqual(result, scores)

    def test_empty_scores_passthrough(self):
        sig = OrchestratedSignal(
            combined_action_bias={"a": 0.02},
            total_confidence=0.7,
            consensus_score=0.8,
            active_signals=("causal_memory",),
            suppressed_signals=(),
            dominant_signal_source="causal_memory",
            scale_factors={},
            reason="orchestrated",
        )
        result = apply_orchestrated_signal({}, sig)
        self.assertEqual(result, {})


class TestNoRegressionBaseline(unittest.TestCase):
    def test_single_causal_produces_output(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.03, "b": -0.02}),
        )
        result = orch.orchestrate(bundle)
        self.assertIn("a", result.combined_action_bias)
        self.assertGreater(result.combined_action_bias["a"], 0)

    def test_three_aligned_stronger_than_one(self):
        orch = SignalOrchestrator()
        one = orch.orchestrate(
            SignalBundle(
                causal_signal=FakeCausalSignal(
                    action_bias={"a": 0.02, "b": -0.01}, confidence=0.5
                ),
            )
        )
        three = orch.orchestrate(
            SignalBundle(
                causal_signal=FakeCausalSignal(
                    action_bias={"a": 0.02, "b": -0.01}, confidence=0.5
                ),
                credit_signal=FakeCreditSignal(
                    action_credit={"a": 0.02, "b": -0.01}, confidence=0.5
                ),
                foresight_signal=FakeForesightSignal(
                    action_bias={"a": 0.02, "b": -0.01}, confidence=0.5
                ),
            )
        )
        self.assertGreaterEqual(three.total_confidence, one.total_confidence)

    def test_consensus_is_monotonic_in_agreement(self):
        orch = SignalOrchestrator()
        aligned = orch.orchestrate(
            SignalBundle(
                causal_signal=FakeCausalSignal(action_bias={"a": 0.03, "b": -0.02}),
                credit_signal=FakeCreditSignal(action_credit={"a": 0.03, "b": -0.02}),
            )
        )
        conflicting = orch.orchestrate(
            SignalBundle(
                causal_signal=FakeCausalSignal(action_bias={"a": 0.03, "b": -0.02}),
                credit_signal=FakeCreditSignal(action_credit={"a": -0.03, "b": 0.02}),
            )
        )
        self.assertGreater(aligned.consensus_score, conflicting.consensus_score)


class TestBenchmarkIntegration(unittest.TestCase):
    def test_orchestrator_with_real_signal_types(self):
        """Use actual signal types from EOS engines."""
        from umh.runtime_engine.causal_memory import CausalSignal
        from umh.runtime_engine.credit_assignment import CreditSignal
        from umh.runtime_engine.foresight_engine import ForesightSignal

        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=CausalSignal(
                action_bias={"a": 0.02, "b": -0.01},
                confidence=0.6,
                matched_context="stable",
                reason="data_available",
            ),
            credit_signal=CreditSignal(
                action_credit={"a": 0.01, "b": -0.02},
                horizon=10,
                confidence=0.5,
                reason="data_available",
            ),
            foresight_signal=ForesightSignal(
                action_bias={"a": 0.02, "b": -0.01},
                confidence=0.4,
                horizon=3,
                reason="foresight_applied",
            ),
        )
        result = orch.orchestrate(bundle)
        self.assertIn("a", result.combined_action_bias)
        self.assertGreater(result.consensus_score, 0.5)
        for val in result.combined_action_bias.values():
            self.assertLessEqual(abs(val), MAX_COMBINED_BIAS + 1e-9)

    def test_orchestrator_with_trap_and_causal(self):
        """Trap and causal signals together."""
        from umh.runtime_engine.causal_memory import CausalSignal
        from umh.runtime_engine.trap_recovery_engine import TrapSignal

        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=CausalSignal(
                action_bias={"action_0": 0.03, "action_1": -0.01},
                confidence=0.7,
                matched_context="stable",
                reason="data_available",
            ),
            trap_signal=TrapSignal(
                active=True,
                dominant_action="action_0",
                trap_adjustment=0.04,
                reward_mismatch=0.8,
                stagnation_length=6,
                reason="stagnation",
            ),
        )
        result = orch.orchestrate(bundle)
        self.assertGreater(len(result.active_signals), 0)

    def test_full_benchmark_smoke(self):
        """Run a mini benchmark with orchestrator."""
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


class TestSafetyRules(unittest.TestCase):
    def test_no_bias_exceeds_max(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(
                action_bias={"a": 0.05, "b": 0.05, "c": 0.05}
            ),
            credit_signal=FakeCreditSignal(
                action_credit={"a": 0.05, "b": 0.05, "c": 0.05}
            ),
            foresight_signal=FakeForesightSignal(
                action_bias={"a": 0.05, "b": 0.05, "c": 0.05}
            ),
        )
        result = orch.orchestrate(bundle)
        for val in result.combined_action_bias.values():
            self.assertLessEqual(abs(val), MAX_COMBINED_BIAS + 1e-9)

    def test_no_nans_or_infs(self):
        import math as m

        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.0}),
            credit_signal=FakeCreditSignal(action_credit={"b": 0.0}),
        )
        result = orch.orchestrate(bundle)
        for val in result.combined_action_bias.values():
            self.assertFalse(m.isnan(val))
            self.assertFalse(m.isinf(val))
        self.assertFalse(m.isnan(result.consensus_score))
        self.assertFalse(m.isnan(result.total_confidence))

    def test_identity_on_zero_signals(self):
        scores = {"a": 0.5, "b": 0.3}
        adjusted = apply_orchestrated_signal(scores, NO_ORCHESTRATED_SIGNAL)
        self.assertEqual(adjusted, scores)


class TestEdgeCases(unittest.TestCase):
    def test_single_action(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"only": 0.03}),
            credit_signal=FakeCreditSignal(action_credit={"only": 0.02}),
        )
        result = orch.orchestrate(bundle)
        self.assertLessEqual(
            abs(result.combined_action_bias.get("only", 0.0)),
            MAX_COMBINED_BIAS + 1e-9,
        )

    def test_many_actions(self):
        orch = SignalOrchestrator()
        actions = {f"act_{i}": 0.01 * ((-1) ** i) for i in range(20)}
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias=actions),
        )
        result = orch.orchestrate(bundle)
        for val in result.combined_action_bias.values():
            self.assertLessEqual(abs(val), MAX_COMBINED_BIAS + 1e-9)

    def test_disjoint_action_sets(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 0.03}),
            credit_signal=FakeCreditSignal(action_credit={"b": 0.02}),
        )
        result = orch.orchestrate(bundle)
        self.assertGreater(len(result.combined_action_bias), 0)

    def test_very_small_biases_filtered(self):
        orch = SignalOrchestrator()
        bundle = SignalBundle(
            causal_signal=FakeCausalSignal(action_bias={"a": 1e-12}),
        )
        result = orch.orchestrate(bundle)
        self.assertEqual(result.combined_action_bias, {})


if __name__ == "__main__":
    unittest.main()
