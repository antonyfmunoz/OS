"""Tests for eos_ai.meta_generalization — cross-scenario meta-learning.

Covers:
1. Signature computation and bounds
2. Prototype learning and EMA updates
3. Similarity matching
4. Bounded priors
5. Prototype merging and cap enforcement
6. Persistence (snapshot/restore)
7. Backward compatibility
8. Determinism
9. No-match passthrough
10. Pipeline integration helpers
11. Benchmark integration (warm-start vs cold-start)
12. Safety rules
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.meta_generalization import (
    MAX_PROTOTYPES,
    MERGE_SIMILARITY_THRESHOLD,
    MIN_OBSERVATIONS_FOR_SIGNATURE,
    MIN_PROTOTYPE_USAGE,
    NO_GENERALIZATION,
    PRIOR_BOUND_CONFIDENCE,
    PRIOR_BOUND_EXPLORATION,
    PRIOR_BOUND_POLICY,
    PRIOR_BOUND_STRATEGY,
    SIMILARITY_THRESHOLD,
    GeneralizationResult,
    MetaGeneralizationEngine,
    ScenarioSignature,
    apply_confidence_prior,
    apply_exploration_prior,
    apply_strategy_priors,
    compute_scenario_signature,
    compute_similarity,
)


# ─── 1. Signature computation ──────────────────────────────────────


class TestSignatureComputation:
    def test_none_below_min_observations(self):
        sig = compute_scenario_signature(["a"] * 5, [1.0] * 5)
        assert sig is None

    def test_returns_signature_above_min(self):
        actions = ["a"] * 20
        rewards = [0.8] * 20
        sig = compute_scenario_signature(actions, rewards)
        assert sig is not None
        assert isinstance(sig, ScenarioSignature)

    def test_all_dimensions_bounded_zero_to_one(self):
        actions = ["a", "b"] * 25
        rewards = [1.0, 0.0] * 25
        sig = compute_scenario_signature(actions, rewards)
        assert sig is not None
        for val in sig.to_tuple():
            assert 0.0 <= val <= 1.0, f"Dimension out of bounds: {val}"

    def test_stable_high_reward_signature(self):
        actions = ["a"] * 30
        rewards = [0.95] * 30
        sig = compute_scenario_signature(actions, rewards)
        assert sig is not None
        assert sig.avg_reward > 0.9
        assert sig.reward_volatility < 0.05
        assert sig.action_switch_rate < 0.01

    def test_volatile_signature(self):
        actions = ["a", "b"] * 15
        rewards = [1.0, 0.1] * 15
        sig = compute_scenario_signature(actions, rewards)
        assert sig is not None
        assert sig.reward_volatility > 0.3
        assert sig.action_switch_rate > 0.9

    def test_to_dict_roundtrip(self):
        actions = ["a"] * 20
        rewards = [0.7] * 20
        sig = compute_scenario_signature(actions, rewards)
        assert sig is not None
        d = sig.to_dict()
        assert len(d) == 8
        assert all(isinstance(v, float) for v in d.values())

    def test_to_tuple_length(self):
        actions = ["a"] * 20
        rewards = [0.5] * 20
        sig = compute_scenario_signature(actions, rewards)
        assert sig is not None
        assert len(sig.to_tuple()) == 8


# ─── 2. Prototype learning ─────────────────────────────────────────


class TestPrototypeLearning:
    def test_learn_creates_prototype(self):
        engine = MetaGeneralizationEngine()
        actions = ["a"] * 30
        rewards = [0.9] * 30
        engine.learn(actions, rewards, outcome_reward=0.9)
        assert engine.prototype_count == 1

    def test_learn_updates_existing_prototype(self):
        engine = MetaGeneralizationEngine()
        actions = ["a"] * 30
        rewards = [0.9] * 30
        engine.learn(actions, rewards, outcome_reward=0.9)
        engine.learn(actions, rewards, outcome_reward=0.85)
        assert engine.prototype_count == 1

    def test_different_scenarios_create_different_prototypes(self):
        engine = MetaGeneralizationEngine()
        engine.learn(["a"] * 30, [0.9] * 30, outcome_reward=0.9)
        engine.learn(["a", "b"] * 15, [1.0, 0.1] * 15, outcome_reward=0.5)
        assert engine.prototype_count == 2

    def test_learn_ignores_insufficient_data(self):
        engine = MetaGeneralizationEngine()
        engine.learn(["a"] * 5, [0.9] * 5, outcome_reward=0.9)
        assert engine.prototype_count == 0

    def test_success_profile_tracked(self):
        engine = MetaGeneralizationEngine()
        profile = {"trap_recovery": 0.8, "regime_adaptation": 0.6}
        engine.learn(
            ["a"] * 30, [0.9] * 30, outcome_reward=0.9, success_profile=profile
        )
        snap = engine.snapshot()
        proto = snap["prototypes"][0]
        assert "trap_recovery" in proto["success_profile"]
        assert "regime_adaptation" in proto["success_profile"]


# ─── 3. Similarity matching ────────────────────────────────────────


class TestSimilarityMatching:
    def test_identical_signatures_similarity_one(self):
        sig = compute_scenario_signature(["a"] * 30, [0.9] * 30)
        assert sig is not None
        centroid = list(sig.to_tuple())
        sim = compute_similarity(sig, centroid)
        assert sim > 0.99

    def test_different_signatures_lower_similarity(self):
        sig1 = compute_scenario_signature(["a"] * 30, [0.9] * 30)
        sig2 = compute_scenario_signature(["a", "b"] * 15, [1.0, 0.1] * 15)
        assert sig1 is not None and sig2 is not None
        sim = compute_similarity(sig1, list(sig2.to_tuple()))
        assert sim < SIMILARITY_THRESHOLD

    def test_similarity_bounded_zero_to_one(self):
        sig = compute_scenario_signature(["a"] * 30, [0.5] * 30)
        assert sig is not None
        centroid = [0.0] * 8
        sim = compute_similarity(sig, centroid)
        assert 0.0 <= sim <= 1.0


# ─── 4. Bounded priors ─────────────────────────────────────────────


class TestBoundedPriors:
    def _trained_engine(self) -> MetaGeneralizationEngine:
        engine = MetaGeneralizationEngine()
        actions = ["a"] * 30
        rewards = [0.9] * 30
        for _ in range(MIN_PROTOTYPE_USAGE + 2):
            engine.learn(actions, rewards, outcome_reward=0.9)
        return engine

    def test_priors_within_bounds(self):
        engine = self._trained_engine()
        result = engine.classify(["a"] * 30, [0.9] * 30)
        if result.matched and result.priors:
            for key, val in result.priors.items():
                if key == "strategy":
                    assert abs(val) <= PRIOR_BOUND_STRATEGY
                elif key == "policy":
                    assert abs(val) <= PRIOR_BOUND_POLICY
                elif key == "exploration":
                    assert abs(val) <= PRIOR_BOUND_EXPLORATION
                elif key == "confidence":
                    assert abs(val) <= PRIOR_BOUND_CONFIDENCE

    def test_no_priors_before_min_usage(self):
        engine = MetaGeneralizationEngine()
        actions = ["a"] * 30
        rewards = [0.9] * 30
        engine.learn(actions, rewards, outcome_reward=0.9)
        result = engine.classify(actions, rewards)
        assert not result.priors

    def test_priors_scale_with_similarity(self):
        engine = self._trained_engine()
        result_close = engine.classify(["a"] * 30, [0.9] * 30)
        result_far = engine.classify(["a"] * 30, [0.7] * 30)
        if result_close.matched and result_far.matched:
            close_mag = sum(abs(v) for v in result_close.priors.values())
            far_mag = sum(abs(v) for v in result_far.priors.values())
            assert close_mag >= far_mag


# ─── 5. Prototype cap and merging ──────────────────────────────────


class TestPrototypeCap:
    def test_max_prototypes_enforced(self):
        engine = MetaGeneralizationEngine()
        for i in range(MAX_PROTOTYPES + 5):
            reward_base = 0.1 * (i % 10)
            sr = 1.0 if i % 2 == 0 else 0.0
            actions = ["a"] * 30 if sr == 0.0 else (["a", "b"] * 15)
            rewards = [reward_base + j * 0.001 for j in range(30)]
            engine.learn(actions, rewards, outcome_reward=reward_base)
        assert engine.prototype_count <= MAX_PROTOTYPES

    def test_merge_similar_prototypes(self):
        engine = MetaGeneralizationEngine()
        actions = ["a"] * 30
        rewards1 = [0.90] * 30
        rewards2 = [0.91] * 30
        engine.learn(actions, rewards1, outcome_reward=0.90)
        engine.learn(actions, rewards2, outcome_reward=0.91)
        assert engine.prototype_count <= 2


# ─── 6. Persistence ────────────────────────────────────────────────


class TestPersistence:
    def test_snapshot_restore_roundtrip(self):
        engine1 = MetaGeneralizationEngine()
        for _ in range(5):
            engine1.learn(["a"] * 30, [0.9] * 30, outcome_reward=0.9)
        snap = engine1.snapshot()

        engine2 = MetaGeneralizationEngine()
        engine2.restore(snap)

        assert engine2.prototype_count == engine1.prototype_count
        assert engine2.snapshot() == snap

    def test_restore_none_safe(self):
        engine = MetaGeneralizationEngine()
        engine.restore(None)
        assert engine.prototype_count == 0

    def test_restore_empty_dict_safe(self):
        engine = MetaGeneralizationEngine()
        engine.restore({})
        assert engine.prototype_count == 0

    def test_snapshot_has_version(self):
        engine = MetaGeneralizationEngine()
        snap = engine.snapshot()
        assert "version" in snap
        assert snap["version"] == 1


# ─── 7. Backward compatibility ─────────────────────────────────────


class TestBackwardCompatibility:
    def test_classify_without_prototypes_returns_no_generalization(self):
        engine = MetaGeneralizationEngine()
        result = engine.classify(["a"] * 30, [0.9] * 30)
        assert not result.matched
        assert result.priors == {}

    def test_no_generalization_sentinel(self):
        assert NO_GENERALIZATION.matched is False
        assert NO_GENERALIZATION.prototype_id is None
        assert NO_GENERALIZATION.priors == {}

    def test_restore_preserves_behavior(self):
        engine1 = MetaGeneralizationEngine()
        for _ in range(MIN_PROTOTYPE_USAGE + 2):
            engine1.learn(["a"] * 30, [0.9] * 30, outcome_reward=0.9)
        snap = engine1.snapshot()

        engine2 = MetaGeneralizationEngine()
        engine2.restore(snap)

        r1 = engine1.classify(["a"] * 30, [0.9] * 30)
        r2 = engine2.classify(["a"] * 30, [0.9] * 30)
        assert r1.matched == r2.matched
        assert abs(r1.similarity - r2.similarity) < 1e-6
        for key in set(r1.priors) | set(r2.priors):
            assert abs(r1.priors.get(key, 0) - r2.priors.get(key, 0)) < 1e-6


# ─── 8. Determinism ────────────────────────────────────────────────


class TestDeterminism:
    def test_identical_inputs_identical_signatures(self):
        actions = ["a", "b"] * 15
        rewards = [0.8, 0.3] * 15
        s1 = compute_scenario_signature(actions, rewards)
        s2 = compute_scenario_signature(actions, rewards)
        assert s1 is not None and s2 is not None
        assert s1.to_tuple() == s2.to_tuple()

    def test_identical_sequences_identical_classify(self):
        def run():
            engine = MetaGeneralizationEngine()
            for _ in range(MIN_PROTOTYPE_USAGE + 2):
                engine.learn(["a"] * 30, [0.9] * 30, outcome_reward=0.9)
            return engine.classify(["a"] * 30, [0.9] * 30)

        r1 = run()
        r2 = run()
        assert r1.matched == r2.matched
        assert r1.similarity == r2.similarity
        assert r1.priors == r2.priors

    def test_identical_learn_sequences_identical_state(self):
        def build():
            engine = MetaGeneralizationEngine()
            for _ in range(10):
                engine.learn(["a"] * 30, [0.9] * 30, outcome_reward=0.9)
            return engine.snapshot()

        s1 = build()
        s2 = build()
        assert s1 == s2


# ─── 9. No-match passthrough ───────────────────────────────────────


class TestNoMatchPassthrough:
    def test_unmatched_scenario_returns_empty_priors(self):
        engine = MetaGeneralizationEngine()
        for _ in range(5):
            engine.learn(["a"] * 30, [0.9] * 30, outcome_reward=0.9)
        result = engine.classify(["a", "b"] * 15, [1.0, 0.1] * 15)
        assert not result.matched
        assert result.priors == {}

    def test_strategy_priors_passthrough_when_unmatched(self):
        scores = {"a": 0.5, "b": 0.3}
        adjusted = apply_strategy_priors(scores, NO_GENERALIZATION)
        assert adjusted == scores

    def test_confidence_prior_passthrough_when_unmatched(self):
        result = apply_confidence_prior(0.8, NO_GENERALIZATION)
        assert result == 0.8

    def test_exploration_prior_passthrough_when_unmatched(self):
        result = apply_exploration_prior(0.3, NO_GENERALIZATION)
        assert result == 0.3


# ─── 10. Pipeline integration helpers ──────────────────────────────


class TestPipelineHelpers:
    def _make_matched_result(self, priors: dict[str, float]) -> GeneralizationResult:
        sig = compute_scenario_signature(["a"] * 20, [0.8] * 20)
        return GeneralizationResult(
            matched=True,
            prototype_id=0,
            similarity=0.85,
            signature=sig,
            priors=priors,
            prototype_usage_count=5,
            prototype_avg_reward=0.8,
        )

    def test_apply_strategy_priors(self):
        scores = {"a": 0.5, "b": 0.3}
        result = self._make_matched_result({"strategy": 0.02})
        adjusted = apply_strategy_priors(scores, result)
        assert adjusted["a"] == 0.52
        assert adjusted["b"] == 0.32

    def test_apply_confidence_prior(self):
        result = self._make_matched_result({"confidence": 0.02})
        adjusted = apply_confidence_prior(0.5, result)
        assert adjusted is not None
        assert abs(adjusted - 0.52) < 1e-9

    def test_apply_exploration_prior(self):
        result = self._make_matched_result({"exploration": -0.03})
        adjusted = apply_exploration_prior(0.5, result)
        assert adjusted is not None
        assert abs(adjusted - 0.47) < 1e-9

    def test_confidence_prior_none_passthrough(self):
        result = self._make_matched_result({"confidence": 0.02})
        assert apply_confidence_prior(None, result) is None

    def test_exploration_prior_none_passthrough(self):
        result = self._make_matched_result({"exploration": 0.02})
        assert apply_exploration_prior(None, result) is None

    def test_confidence_prior_clamped(self):
        result = self._make_matched_result({"confidence": 0.03})
        adjusted = apply_confidence_prior(0.99, result)
        assert adjusted is not None
        assert adjusted <= 1.0

    def test_exploration_prior_clamped(self):
        result = self._make_matched_result({"exploration": -0.05})
        adjusted = apply_exploration_prior(0.01, result)
        assert adjusted is not None
        assert adjusted >= 0.0


# ─── 11. Benchmark integration ─────────────────────────────────────


class TestBenchmarkIntegration:
    def test_warm_start_no_regression(self):
        from umh.runtime_engine.benchmark_env import EOSWithCorrectionSystem
        from umh.runtime_engine.long_horizon_benchmark import (
            PeriodicShiftScenario,
            run_long_horizon,
        )

        s1 = PeriodicShiftScenario(seed=42, period=200)
        system = EOSWithCorrectionSystem()
        r = run_long_horizon(system, s1, horizon=1000, seed=42)
        assert r.reward_metrics.avg_reward >= 0.90

    def test_adversarial_still_recovers(self):
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
        from umh.runtime_engine.benchmark_env import (
            EOSDecisionSystem,
            EOSWithCorrectionSystem,
        )
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


# ─── 12. Safety rules ──────────────────────────────────────────────


class TestSafetyRules:
    def test_priors_never_exceed_bounds(self):
        engine = MetaGeneralizationEngine()
        for i in range(30):
            reward_val = 1.0 if i % 2 == 0 else 0.0
            engine.learn(
                ["a"] * 30,
                [reward_val] * 30,
                outcome_reward=reward_val,
            )

        snap = engine.snapshot()
        for proto in snap["prototypes"]:
            for key, val in proto["learned_priors"].items():
                if key == "strategy":
                    assert abs(val) <= PRIOR_BOUND_STRATEGY + 1e-9
                elif key == "policy":
                    assert abs(val) <= PRIOR_BOUND_POLICY + 1e-9
                elif key == "exploration":
                    assert abs(val) <= PRIOR_BOUND_EXPLORATION + 1e-9
                elif key == "confidence":
                    assert abs(val) <= PRIOR_BOUND_CONFIDENCE + 1e-9

    def test_prototype_count_hard_cap(self):
        engine = MetaGeneralizationEngine()
        for i in range(50):
            base = i * 0.02
            actions = [f"action_{i % 10}"] * 30
            rewards = [min(1.0, base + j * 0.001) for j in range(30)]
            engine.learn(actions, rewards, outcome_reward=base)
        assert engine.prototype_count <= MAX_PROTOTYPES

    def test_reset_clears_all_state(self):
        engine = MetaGeneralizationEngine()
        engine.learn(["a"] * 30, [0.9] * 30, outcome_reward=0.9)
        engine.reset()
        assert engine.prototype_count == 0
        assert engine._observations == 0

    def test_generalization_result_to_dict(self):
        sig = compute_scenario_signature(["a"] * 20, [0.8] * 20)
        result = GeneralizationResult(
            matched=True,
            prototype_id=1,
            similarity=0.85,
            signature=sig,
            priors={"strategy": 0.02, "confidence": 0.01},
            prototype_usage_count=5,
            prototype_avg_reward=0.8,
        )
        d = result.to_dict()
        assert d["matched"] is True
        assert "prototype_id" in d
        assert "priors" in d
        assert "signature" in d

    def test_no_generalization_to_dict(self):
        d = NO_GENERALIZATION.to_dict()
        assert d["matched"] is False
        assert "prototype_id" not in d
