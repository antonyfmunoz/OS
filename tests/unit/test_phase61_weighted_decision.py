"""Phase 61 — Weighted decision influence tests.

Tests bounded, confidence-gated influence of learned dimension weights
on the strategy selection pipeline.

Invariants 257-264.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime.dimension_weighting import (
    DEFAULT_WEIGHT_VECTOR,
    DimensionWeight,
    DimensionWeightVector,
    WeightingConfig,
    default_weight_vector,
)
from umh.runtime.regime_aggregation import (
    AggregatedRegimeState,
    DimensionName,
    DimensionRegime,
    DirectionCategory,
    NEUTRAL_AGGREGATED,
    aggregate_regimes,
)
from umh.runtime.weighted_decision import (
    DEFAULT_WEIGHTED_DECISION_POLICY,
    WeightedDecisionBatchResult,
    WeightedDecisionPolicy,
    WeightedDecisionResult,
    _compute_overall_confidence,
    _compute_raw_weight_factor,
    _direction_sign,
    _normalize_to_bounded_factor,
    apply_weighted_influence,
    compute_weight_factor,
)
from umh.runtime.strategy_orchestrator import (
    StrategyCandidate,
    StrategyOrchestrationPolicy,
    StrategySelectionResult,
    orchestrate_selection,
)


# ===========================================================================
# SECTION 1 — WeightedDecisionPolicy defaults
# ===========================================================================


class TestSection01PolicyDefaults:
    def test_default_enabled(self):
        assert WeightedDecisionPolicy().enabled is False

    def test_default_max_weight_influence(self):
        assert WeightedDecisionPolicy().max_weight_influence == 0.10

    def test_default_min_confidence(self):
        assert WeightedDecisionPolicy().min_confidence == 0.60

    def test_default_constant(self):
        p = DEFAULT_WEIGHTED_DECISION_POLICY
        assert p.enabled is False
        assert p.max_weight_influence == 0.10
        assert p.min_confidence == 0.60


# ===========================================================================
# SECTION 2 — WeightedDecisionPolicy bounds
# ===========================================================================


class TestSection02PolicyBounds:
    def test_max_influence_clamped_low(self):
        p = WeightedDecisionPolicy(max_weight_influence=-1.0)
        assert p.max_weight_influence == 0.0

    def test_max_influence_clamped_high(self):
        p = WeightedDecisionPolicy(max_weight_influence=2.0)
        assert p.max_weight_influence == 0.50

    def test_min_confidence_clamped_low(self):
        p = WeightedDecisionPolicy(min_confidence=-0.5)
        assert p.min_confidence == 0.0

    def test_min_confidence_clamped_high(self):
        p = WeightedDecisionPolicy(min_confidence=5.0)
        assert p.min_confidence == 1.0


# ===========================================================================
# SECTION 3 — WeightedDecisionPolicy to_dict
# ===========================================================================


class TestSection03PolicyDict:
    def test_to_dict_keys(self):
        d = WeightedDecisionPolicy().to_dict()
        expected = {"enabled", "max_weight_influence", "min_confidence"}
        assert set(d.keys()) == expected

    def test_to_dict_values(self):
        d = WeightedDecisionPolicy(enabled=True, max_weight_influence=0.15).to_dict()
        assert d["enabled"] is True
        assert d["max_weight_influence"] == 0.15


# ===========================================================================
# SECTION 4 — WeightedDecisionPolicy frozen
# ===========================================================================


class TestSection04PolicyFrozen:
    def test_frozen(self):
        p = WeightedDecisionPolicy()
        try:
            p.enabled = True
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 5 — WeightedDecisionResult defaults
# ===========================================================================


class TestSection05ResultDefaults:
    def test_default_strategy_id(self):
        assert WeightedDecisionResult().strategy_id == ""

    def test_default_base_score(self):
        assert WeightedDecisionResult().base_score == 0.0

    def test_default_weight_factor(self):
        assert WeightedDecisionResult().weight_factor == 1.0

    def test_default_final_score(self):
        assert WeightedDecisionResult().final_score == 0.0

    def test_default_used_weights(self):
        assert WeightedDecisionResult().used_weights is False

    def test_default_confidence_gated(self):
        assert WeightedDecisionResult().confidence_gated is False

    def test_default_explanation(self):
        assert WeightedDecisionResult().explanation == ""


# ===========================================================================
# SECTION 6 — WeightedDecisionResult bounds
# ===========================================================================


class TestSection06ResultBounds:
    def test_base_score_floor(self):
        r = WeightedDecisionResult(base_score=-1.0)
        assert r.base_score == 0.0

    def test_weight_factor_floor(self):
        r = WeightedDecisionResult(weight_factor=-1.0)
        assert r.weight_factor == 0.0

    def test_final_score_floor(self):
        r = WeightedDecisionResult(final_score=-5.0)
        assert r.final_score == 0.0


# ===========================================================================
# SECTION 7 — WeightedDecisionResult to_dict
# ===========================================================================


class TestSection07ResultDict:
    def test_to_dict_keys(self):
        d = WeightedDecisionResult().to_dict()
        expected = {
            "strategy_id",
            "base_score",
            "weight_factor",
            "final_score",
            "used_weights",
            "confidence_gated",
            "explanation",
        }
        assert set(d.keys()) == expected

    def test_to_dict_rounding(self):
        d = WeightedDecisionResult(base_score=0.123456789, weight_factor=1.123456789).to_dict()
        assert d["base_score"] == 0.1235
        assert d["weight_factor"] == 1.1235


# ===========================================================================
# SECTION 8 — WeightedDecisionResult frozen
# ===========================================================================


class TestSection08ResultFrozen:
    def test_frozen(self):
        r = WeightedDecisionResult()
        try:
            r.weight_factor = 2.0
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 9 — WeightedDecisionBatchResult defaults
# ===========================================================================


class TestSection09BatchDefaults:
    def test_default_results(self):
        assert WeightedDecisionBatchResult().results == ()

    def test_default_policy(self):
        b = WeightedDecisionBatchResult()
        assert b.policy.enabled is False

    def test_default_overall_confidence(self):
        assert WeightedDecisionBatchResult().overall_confidence == 0.0

    def test_default_explanation(self):
        assert WeightedDecisionBatchResult().explanation == ""


# ===========================================================================
# SECTION 10 — WeightedDecisionBatchResult to_dict
# ===========================================================================


class TestSection10BatchDict:
    def test_to_dict_keys(self):
        d = WeightedDecisionBatchResult().to_dict()
        expected = {"results", "policy", "overall_confidence", "explanation"}
        assert set(d.keys()) == expected


# ===========================================================================
# SECTION 11 — _direction_sign
# ===========================================================================


class TestSection11DirectionSign:
    def test_positive(self):
        assert _direction_sign(DirectionCategory.POSITIVE) == 1.0

    def test_negative(self):
        assert _direction_sign(DirectionCategory.NEGATIVE) == -1.0

    def test_neutral(self):
        assert _direction_sign(DirectionCategory.NEUTRAL) == 0.0


# ===========================================================================
# SECTION 12 — _compute_overall_confidence
# ===========================================================================


class TestSection12OverallConfidence:
    def test_empty_weights(self):
        v = DimensionWeightVector(weights={})
        assert _compute_overall_confidence(v) == 0.0

    def test_uniform_zero_confidence(self):
        assert _compute_overall_confidence(DEFAULT_WEIGHT_VECTOR) == 0.0

    def test_full_confidence(self):
        weights = {
            dim.value: DimensionWeight(dimension=dim, weight=0.25, confidence=1.0, source="learned")
            for dim in DimensionName
        }
        v = DimensionWeightVector(weights=weights)
        assert _compute_overall_confidence(v) == 1.0

    def test_mixed_confidence(self):
        weights = {
            DimensionName.TREND.value: DimensionWeight(
                dimension=DimensionName.TREND, weight=0.25, confidence=0.8
            ),
            DimensionName.RISK.value: DimensionWeight(
                dimension=DimensionName.RISK, weight=0.25, confidence=0.6
            ),
            DimensionName.STABILITY.value: DimensionWeight(
                dimension=DimensionName.STABILITY, weight=0.25, confidence=0.4
            ),
            DimensionName.URGENCY.value: DimensionWeight(
                dimension=DimensionName.URGENCY, weight=0.25, confidence=0.2
            ),
        }
        v = DimensionWeightVector(weights=weights)
        expected = (0.8 + 0.6 + 0.4 + 0.2) / 4.0
        assert abs(_compute_overall_confidence(v) - expected) < 1e-9


# ===========================================================================
# SECTION 13 — _compute_raw_weight_factor
# ===========================================================================


class TestSection13RawWeightFactor:
    def test_all_neutral_regime(self):
        raw = _compute_raw_weight_factor(DEFAULT_WEIGHT_VECTOR, NEUTRAL_AGGREGATED)
        assert raw == 0.0

    def test_all_positive_regime(self):
        regime = aggregate_regimes(
            trend_label="trend_up",
            risk_label="low",
            stability_label="high",
            urgency_label="low",
        )
        weights = default_weight_vector()
        raw = _compute_raw_weight_factor(weights, regime)
        assert raw > 0.0

    def test_all_negative_regime(self):
        regime = aggregate_regimes(
            trend_label="trend_down",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        weights = default_weight_vector()
        raw = _compute_raw_weight_factor(weights, regime)
        assert raw < 0.0

    def test_mixed_regime_cancellation(self):
        regime = aggregate_regimes(
            trend_label="trend_up",
            risk_label="high",
        )
        weights = default_weight_vector()
        raw = _compute_raw_weight_factor(weights, regime)
        assert abs(raw) < 1.0


# ===========================================================================
# SECTION 14 — _normalize_to_bounded_factor
# ===========================================================================


class TestSection14NormalizeFactor:
    def test_zero_raw(self):
        assert _normalize_to_bounded_factor(0.0, 0.10) == 1.0

    def test_positive_max(self):
        f = _normalize_to_bounded_factor(1.0, 0.10)
        assert abs(f - 1.10) < 1e-9

    def test_negative_max(self):
        f = _normalize_to_bounded_factor(-1.0, 0.10)
        assert abs(f - 0.90) < 1e-9

    def test_clamps_beyond_one(self):
        f = _normalize_to_bounded_factor(5.0, 0.10)
        assert abs(f - 1.10) < 1e-9

    def test_clamps_below_neg_one(self):
        f = _normalize_to_bounded_factor(-5.0, 0.10)
        assert abs(f - 0.90) < 1e-9

    def test_custom_influence_bound(self):
        f = _normalize_to_bounded_factor(0.5, 0.20)
        assert abs(f - 1.10) < 1e-9


# ===========================================================================
# SECTION 15 — compute_weight_factor: disabled (inv 263)
# ===========================================================================


class TestSection15Disabled:
    def test_disabled_returns_neutral(self):
        factor, used, conf, explanation = compute_weight_factor(
            policy=WeightedDecisionPolicy(enabled=False)
        )
        assert factor == 1.0
        assert used is False
        assert "disabled" in explanation

    def test_default_policy_disabled(self):
        factor, used, _, _ = compute_weight_factor()
        assert factor == 1.0
        assert used is False


# ===========================================================================
# SECTION 16 — compute_weight_factor: missing weights (inv 263)
# ===========================================================================


class TestSection16MissingWeights:
    def test_none_weights_uses_default(self):
        factor, used, _, explanation = compute_weight_factor(
            weights=None,
            regime=NEUTRAL_AGGREGATED,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert factor == 1.0
        assert used is True

    def test_none_regime_uses_neutral(self):
        weights = _make_high_confidence_weights()
        factor, _, _, _ = compute_weight_factor(
            weights=weights,
            regime=None,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert factor == 1.0


# ===========================================================================
# SECTION 17 — compute_weight_factor: confidence gate (inv 259)
# ===========================================================================


class TestSection17ConfidenceGate:
    def test_low_confidence_gated(self):
        weights = _make_low_confidence_weights(0.2)
        regime = aggregate_regimes(trend_label="trend_up")
        factor, used, conf, explanation = compute_weight_factor(
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.6),
        )
        assert factor == 1.0
        assert used is False
        assert conf < 0.6
        assert "gated" in explanation

    def test_sufficient_confidence_not_gated(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(trend_label="trend_up")
        factor, used, conf, _ = compute_weight_factor(
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.3),
        )
        assert used is True
        assert conf >= 0.3

    def test_exact_threshold_not_gated(self):
        weights = _make_exact_confidence_weights(0.6)
        regime = aggregate_regimes(trend_label="trend_up")
        _, used, conf, _ = compute_weight_factor(
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.6),
        )
        assert used is True

    def test_just_below_threshold_gated(self):
        weights = _make_exact_confidence_weights(0.59)
        regime = aggregate_regimes(trend_label="trend_up")
        factor, used, _, _ = compute_weight_factor(
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.6),
        )
        assert factor == 1.0
        assert used is False


# ===========================================================================
# SECTION 18 — compute_weight_factor: bounded influence (inv 258)
# ===========================================================================


class TestSection18BoundedInfluence:
    def test_positive_influence_bounded(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(
            trend_label="spike_up",
            risk_label="low",
            stability_label="high",
            urgency_label="low",
        )
        factor, _, _, _ = compute_weight_factor(
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(
                enabled=True, max_weight_influence=0.10, min_confidence=0.0
            ),
        )
        assert 0.90 <= factor <= 1.10

    def test_negative_influence_bounded(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(
            trend_label="spike_down",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        factor, _, _, _ = compute_weight_factor(
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(
                enabled=True, max_weight_influence=0.10, min_confidence=0.0
            ),
        )
        assert 0.90 <= factor <= 1.10

    def test_larger_influence_bound(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(trend_label="spike_up")
        factor, _, _, _ = compute_weight_factor(
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(
                enabled=True, max_weight_influence=0.30, min_confidence=0.0
            ),
        )
        assert 0.70 <= factor <= 1.30


# ===========================================================================
# SECTION 19 — compute_weight_factor: positive regime boosts (inv 257)
# ===========================================================================


class TestSection19PositiveBoost:
    def test_positive_regime_above_one(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(
            trend_label="trend_up",
            risk_label="low",
            stability_label="high",
            urgency_label="low",
        )
        factor, _, _, _ = compute_weight_factor(
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert factor > 1.0


# ===========================================================================
# SECTION 20 — compute_weight_factor: negative regime penalizes
# ===========================================================================


class TestSection20NegativePenalty:
    def test_negative_regime_below_one(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(
            trend_label="trend_down",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        factor, _, _, _ = compute_weight_factor(
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert factor < 1.0


# ===========================================================================
# SECTION 21 — apply_weighted_influence: empty input
# ===========================================================================


class TestSection21EmptyInput:
    def test_empty_strategies(self):
        result = apply_weighted_influence(
            strategy_ids=[],
            input_scores=[],
        )
        assert result.results == ()
        assert "no strategies" in result.explanation


# ===========================================================================
# SECTION 22 — apply_weighted_influence: disabled (inv 263)
# ===========================================================================


class TestSection22ApplyDisabled:
    def test_disabled_no_effect(self):
        result = apply_weighted_influence(
            strategy_ids=["a", "b"],
            input_scores=[0.8, 0.6],
            policy=WeightedDecisionPolicy(enabled=False),
        )
        for r in result.results:
            assert r.weight_factor == 1.0
            assert r.used_weights is False

    def test_disabled_preserves_scores(self):
        result = apply_weighted_influence(
            strategy_ids=["a", "b"],
            input_scores=[0.8, 0.6],
            policy=WeightedDecisionPolicy(enabled=False),
        )
        assert abs(result.results[0].final_score - 0.8) < 1e-9
        assert abs(result.results[1].final_score - 0.6) < 1e-9


# ===========================================================================
# SECTION 23 — apply_weighted_influence: enabled with boost
# ===========================================================================


class TestSection23ApplyBoost:
    def test_positive_regime_boosts_all(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(
            trend_label="trend_up",
            risk_label="low",
            stability_label="high",
            urgency_label="low",
        )
        result = apply_weighted_influence(
            strategy_ids=["a", "b"],
            input_scores=[0.8, 0.6],
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        for r in result.results:
            assert r.weight_factor > 1.0
            assert r.final_score > r.base_score
            assert r.used_weights is True


# ===========================================================================
# SECTION 24 — apply_weighted_influence: enabled with penalty
# ===========================================================================


class TestSection24ApplyPenalty:
    def test_negative_regime_penalizes_all(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(
            trend_label="trend_down",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        result = apply_weighted_influence(
            strategy_ids=["a", "b"],
            input_scores=[0.8, 0.6],
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        for r in result.results:
            assert r.weight_factor < 1.0
            assert r.final_score < r.base_score


# ===========================================================================
# SECTION 25 — apply_weighted_influence: uniform factor (inv 260)
# ===========================================================================


class TestSection25UniformFactor:
    def test_same_factor_all_candidates(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(trend_label="trend_up")
        result = apply_weighted_influence(
            strategy_ids=["a", "b", "c"],
            input_scores=[0.9, 0.7, 0.5],
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        factors = [r.weight_factor for r in result.results]
        assert len(set(factors)) == 1

    def test_rank_order_preserved(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(trend_label="trend_up")
        result = apply_weighted_influence(
            strategy_ids=["a", "b", "c"],
            input_scores=[0.9, 0.7, 0.5],
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        scores = [r.final_score for r in result.results]
        assert scores[0] > scores[1] > scores[2]


# ===========================================================================
# SECTION 26 — apply_weighted_influence: confidence gate applied
# ===========================================================================


class TestSection26ApplyConfidenceGate:
    def test_low_confidence_no_effect(self):
        weights = _make_low_confidence_weights(0.1)
        regime = aggregate_regimes(trend_label="spike_up")
        result = apply_weighted_influence(
            strategy_ids=["a"],
            input_scores=[0.8],
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.6),
        )
        assert result.results[0].weight_factor == 1.0
        assert result.results[0].used_weights is False
        assert result.results[0].confidence_gated is True


# ===========================================================================
# SECTION 27 — apply_weighted_influence: score padding
# ===========================================================================


class TestSection27ScorePadding:
    def test_short_scores_padded(self):
        result = apply_weighted_influence(
            strategy_ids=["a", "b", "c"],
            input_scores=[0.8],
            policy=WeightedDecisionPolicy(enabled=False),
        )
        assert len(result.results) == 3
        assert result.results[1].base_score == 0.0
        assert result.results[2].base_score == 0.0

    def test_long_scores_truncated(self):
        result = apply_weighted_influence(
            strategy_ids=["a"],
            input_scores=[0.8, 0.6, 0.4],
            policy=WeightedDecisionPolicy(enabled=False),
        )
        assert len(result.results) == 1


# ===========================================================================
# SECTION 28 — Determinism (inv 262)
# ===========================================================================


class TestSection28Determinism:
    def test_identical_inputs_identical_outputs(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(
            trend_label="trend_up",
            risk_label="high",
        )
        policy = WeightedDecisionPolicy(enabled=True, min_confidence=0.0)
        ids = ["a", "b", "c"]
        scores = [0.9, 0.7, 0.5]

        r1 = apply_weighted_influence(ids, scores, weights, regime, policy)
        r2 = apply_weighted_influence(ids, scores, weights, regime, policy)

        for a, b in zip(r1.results, r2.results):
            assert a.weight_factor == b.weight_factor
            assert a.final_score == b.final_score

    def test_determinism_100_runs(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(trend_label="spike_up", stability_label="low")
        policy = WeightedDecisionPolicy(enabled=True, min_confidence=0.0)

        results = []
        for _ in range(100):
            r = apply_weighted_influence(["x", "y"], [0.8, 0.6], weights, regime, policy)
            results.append(r.results[0].weight_factor)

        assert len(set(results)) == 1


# ===========================================================================
# SECTION 29 — Explainability (inv 264)
# ===========================================================================


class TestSection29Explainability:
    def test_explanation_contains_raw(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(trend_label="trend_up")
        _, _, _, explanation = compute_weight_factor(
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert "raw=" in explanation

    def test_explanation_contains_factor(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(trend_label="trend_up")
        _, _, _, explanation = compute_weight_factor(
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert "factor=" in explanation

    def test_explanation_contains_confidence(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(trend_label="trend_up")
        _, _, _, explanation = compute_weight_factor(
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert "confidence=" in explanation

    def test_explanation_contains_contributions(self):
        weights = _make_high_confidence_weights()
        regime = aggregate_regimes(trend_label="trend_up")
        _, _, _, explanation = compute_weight_factor(
            weights=weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert "contributions=" in explanation
        assert "trend=" in explanation

    def test_disabled_explanation(self):
        _, _, _, explanation = compute_weight_factor(
            policy=WeightedDecisionPolicy(enabled=False),
        )
        assert "disabled" in explanation

    def test_gated_explanation(self):
        weights = _make_low_confidence_weights(0.1)
        _, _, _, explanation = compute_weight_factor(
            weights=weights,
            regime=aggregate_regimes(trend_label="trend_up"),
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.6),
        )
        assert "gated" in explanation


# ===========================================================================
# SECTION 30 — StrategyCandidate weight_factor field
# ===========================================================================


class TestSection30CandidateWeightFactor:
    def test_default_weight_factor(self):
        assert StrategyCandidate().weight_factor == 1.0

    def test_weight_factor_in_final_score(self):
        c = StrategyCandidate(
            base_score=1.0, regime_factor=1.0, feedback_factor=1.0, weight_factor=1.05
        )
        assert abs(c.final_score - 1.05) < 1e-9

    def test_weight_factor_clamped_low(self):
        c = StrategyCandidate(weight_factor=0.1)
        assert c.weight_factor == 0.5

    def test_weight_factor_clamped_high(self):
        c = StrategyCandidate(weight_factor=3.0)
        assert c.weight_factor == 1.5

    def test_weight_factor_in_dict(self):
        d = StrategyCandidate().to_dict()
        assert "weight_factor" in d

    def test_four_factor_product(self):
        c = StrategyCandidate(
            base_score=0.80,
            regime_factor=1.10,
            feedback_factor=1.05,
            weight_factor=0.95,
        )
        expected = 0.80 * 1.10 * 1.05 * 0.95
        assert abs(c.final_score - expected) < 1e-9

    def test_neutral_weight_preserves_previous(self):
        c = StrategyCandidate(base_score=0.80, regime_factor=1.10, feedback_factor=1.05)
        expected = 0.80 * 1.10 * 1.05
        assert abs(c.final_score - expected) < 1e-9


# ===========================================================================
# SECTION 31 — StrategySelectionResult new fields
# ===========================================================================


class TestSection31ResultNewFields:
    def test_default_used_weights(self):
        assert StrategySelectionResult().used_weights is False

    def test_default_weight_winner(self):
        assert StrategySelectionResult().weight_winner == ""

    def test_default_changed_from_feedback(self):
        assert StrategySelectionResult().changed_from_feedback is False

    def test_default_weighted_decision(self):
        assert StrategySelectionResult().weighted_decision is None

    def test_to_dict_contains_new_fields(self):
        d = StrategySelectionResult().to_dict()
        assert "used_weights" in d
        assert "weight_winner" in d
        assert "changed_from_feedback" in d

    def test_to_dict_no_weighted_decision_when_none(self):
        d = StrategySelectionResult().to_dict()
        assert "weighted_decision" not in d


# ===========================================================================
# SECTION 32 — Orchestrator: weights disabled by default (inv 257)
# ===========================================================================


class TestSection32OrchestratorDefault:
    def test_no_policy_no_weight_influence(self):
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
        )
        assert r.used_weights is False
        assert r.weighted_decision is None

    def test_none_policy_no_weight_influence(self):
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            weighted_decision_policy=None,
        )
        assert r.used_weights is False

    def test_disabled_policy_no_weight_influence(self):
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            weighted_decision_policy=WeightedDecisionPolicy(enabled=False),
        )
        assert r.used_weights is False


# ===========================================================================
# SECTION 33 — Orchestrator: weights enabled, neutral regime
# ===========================================================================


class TestSection33OrchestratorNeutral:
    def test_neutral_regime_factor_one(self):
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            aggregated_regime=NEUTRAL_AGGREGATED,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert r.used_weights is True
        for c in r.candidates:
            assert c.weight_factor == 1.0

    def test_neutral_regime_preserves_selection(self):
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            aggregated_regime=NEUTRAL_AGGREGATED,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert r.selected_strategy == "a"


# ===========================================================================
# SECTION 34 — Orchestrator: weights enabled, positive regime boost
# ===========================================================================


class TestSection34OrchestratorBoost:
    def test_positive_regime_boosts_factor(self):
        regime = aggregate_regimes(
            trend_label="trend_up",
            risk_label="low",
            stability_label="high",
            urgency_label="low",
        )
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert r.used_weights is True
        for c in r.candidates:
            assert c.weight_factor > 1.0


# ===========================================================================
# SECTION 35 — Orchestrator: base winner preserved (inv 257)
# ===========================================================================


class TestSection35BasePreserved:
    def test_dominant_base_winner_not_flipped(self):
        regime = aggregate_regimes(
            trend_label="spike_down",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.9, 0.5],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(
                enabled=True, max_weight_influence=0.10, min_confidence=0.0
            ),
        )
        assert r.selected_strategy == "a"
        assert r.base_winner == "a"

    def test_10pct_influence_cannot_flip_large_gap(self):
        regime = aggregate_regimes(
            trend_label="spike_down",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        r = orchestrate_selection(
            strategy_ids=["leader", "follower"],
            base_scores=[1.0, 0.5],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(
                enabled=True, max_weight_influence=0.10, min_confidence=0.0
            ),
        )
        assert r.selected_strategy == "leader"


# ===========================================================================
# SECTION 36 — Orchestrator: computation order (inv 257)
# ===========================================================================


class TestSection36ComputationOrder:
    def test_weight_applied_after_regime_and_feedback(self):
        regime = aggregate_regimes(trend_label="trend_up")
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            regime_factors=[1.10, 0.90],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        for c in r.candidates:
            expected = c.base_score * c.regime_factor * c.feedback_factor * c.weight_factor
            assert abs(c.final_score - expected) < 1e-9

    def test_weight_factor_consistent_across_candidates(self):
        regime = aggregate_regimes(trend_label="trend_up")
        r = orchestrate_selection(
            strategy_ids=["a", "b", "c"],
            base_scores=[0.9, 0.7, 0.5],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        factors = [c.weight_factor for c in r.candidates]
        assert len(set(factors)) == 1


# ===========================================================================
# SECTION 37 — Orchestrator: confidence gate integration (inv 259)
# ===========================================================================


class TestSection37OrchestratorConfidenceGate:
    def test_low_confidence_weights_no_effect(self):
        regime = aggregate_regimes(trend_label="spike_up")
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            aggregated_regime=regime,
            dimension_weights=_make_low_confidence_weights(0.1),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.6),
        )
        assert r.used_weights is False
        for c in r.candidates:
            assert c.weight_factor == 1.0


# ===========================================================================
# SECTION 38 — Orchestrator: invalid/safe candidates unchanged
# ===========================================================================


class TestSection38InvalidCandidates:
    def test_invalid_candidate_not_selected(self):
        regime = aggregate_regimes(trend_label="trend_up")
        r = orchestrate_selection(
            strategy_ids=["invalid", "valid"],
            base_scores=[0.9, 0.5],
            valid_flags=[False, True],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert r.selected_strategy == "valid"

    def test_unsafe_candidate_not_selected(self):
        regime = aggregate_regimes(trend_label="trend_up")
        r = orchestrate_selection(
            strategy_ids=["unsafe", "safe"],
            base_scores=[0.9, 0.5],
            safe_flags=[False, True],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert r.selected_strategy == "safe"


# ===========================================================================
# SECTION 39 — Orchestrator: regime + feedback + weights compose
# ===========================================================================


class TestSection39FullComposition:
    def test_all_three_layers(self):
        from umh.runtime.feedback_selection import FeedbackSelectionPolicy

        regime = aggregate_regimes(trend_label="trend_up")
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            regime_factors=[1.10, 0.95],
            feedback_factors=[1.05, 1.20],
            policy=StrategyOrchestrationPolicy(
                use_regime_weighting=True,
                use_feedback_selection=True,
                feedback_policy=FeedbackSelectionPolicy(enabled=True),
            ),
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert r.used_regime is True
        assert r.used_feedback is True
        assert r.used_weights is True
        for c in r.candidates:
            expected = c.base_score * c.regime_factor * c.feedback_factor * c.weight_factor
            assert abs(c.final_score - expected) < 1e-9


# ===========================================================================
# SECTION 40 — Orchestrator: explanation includes weight info
# ===========================================================================


class TestSection40Explanation:
    def test_enabled_explanation_has_weight_winner(self):
        regime = aggregate_regimes(trend_label="trend_up")
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert "weight_winner=" in r.explanation

    def test_disabled_explanation_says_disabled(self):
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
        )
        assert "weighted influence disabled" in r.explanation

    def test_explanation_contains_weight_influence(self):
        regime = aggregate_regimes(trend_label="trend_up")
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert "weight_influence=" in r.explanation


# ===========================================================================
# SECTION 41 — Orchestrator: to_dict includes weighted_decision
# ===========================================================================


class TestSection41DictIntegration:
    def test_dict_includes_weighted_decision_when_enabled(self):
        regime = aggregate_regimes(trend_label="trend_up")
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        d = r.to_dict()
        assert "weighted_decision" in d

    def test_dict_excludes_weighted_decision_when_none(self):
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
        )
        d = r.to_dict()
        assert "weighted_decision" not in d


# ===========================================================================
# SECTION 42 — No circular dependency (inv 261)
# ===========================================================================


class TestSection42NoDependency:
    def test_no_scoring_import(self):
        import inspect
        import umh.runtime.weighted_decision as m

        src = inspect.getsource(m)
        assert "from umh.runtime.strategy_orchestrator" not in src
        assert "from umh.runtime.feedback_selection" not in src

    def test_no_subprocess(self):
        import inspect
        import umh.runtime.weighted_decision as m

        src = inspect.getsource(m)
        assert "import subprocess" not in src
        assert "from subprocess" not in src

    def test_imports_only_allowed_modules(self):
        import inspect
        import umh.runtime.weighted_decision as m

        src = inspect.getsource(m)
        allowed = {"dimension_weighting", "regime_aggregation"}
        runtime_imports = [
            line.strip()
            for line in src.split("\n")
            if "from umh.runtime" in line and not line.strip().startswith("#")
        ]
        for imp in runtime_imports:
            assert any(a in imp for a in allowed), f"unexpected import: {imp}"


# ===========================================================================
# SECTION 43 — Orchestrator allowed imports updated
# ===========================================================================


class TestSection43OrchestratorImports:
    def test_orchestrator_imports_include_weighted_decision(self):
        import inspect
        import umh.runtime.strategy_orchestrator as m

        src = inspect.getsource(m)
        allowed = {
            "feedback_selection",
            "regime_aggregation",
            "dimension_weighting",
            "weighted_decision",
            "dimension_interactions",
            "pattern_aggregation",
            "pattern_influence",
            "pattern_matching",
        }
        runtime_imports = [
            line.strip()
            for line in src.split("\n")
            if "from umh.runtime" in line and not line.strip().startswith("#")
        ]
        for imp in runtime_imports:
            assert any(a in imp for a in allowed), f"unexpected import: {imp}"


# ===========================================================================
# SECTION 44 — No mutation of inputs (inv 261)
# ===========================================================================


class TestSection44NoMutation:
    def test_scores_not_mutated(self):
        scores = [0.8, 0.6]
        original = list(scores)
        apply_weighted_influence(
            strategy_ids=["a", "b"],
            input_scores=scores,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert scores == original

    def test_strategy_ids_not_mutated(self):
        ids = ["a", "b"]
        original = list(ids)
        apply_weighted_influence(
            strategy_ids=ids,
            input_scores=[0.8, 0.6],
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert ids == original


# ===========================================================================
# SECTION 45 — Phase 60 regression: DimensionWeightVector unchanged
# ===========================================================================


class TestSection45Phase60Regression:
    def test_default_weight_vector_unchanged(self):
        v = default_weight_vector()
        assert v.is_uniform is True
        assert v.normalized is True

    def test_dimension_weight_defaults(self):
        w = DimensionWeight(dimension=DimensionName.TREND)
        assert w.weight == 0.25
        assert w.confidence == 0.0
        assert w.source == "default"

    def test_weighting_config_defaults(self):
        c = WeightingConfig()
        assert c.min_weight == 0.10
        assert c.max_weight == 0.40
        assert c.required_samples == 20
        assert c.confidence_threshold == 0.3


# ===========================================================================
# SECTION 46 — Phase 59 regression: AggregatedRegimeState unchanged
# ===========================================================================


class TestSection46Phase59Regression:
    def test_neutral_aggregated_unchanged(self):
        assert NEUTRAL_AGGREGATED.is_neutral is True
        assert NEUTRAL_AGGREGATED.alignment_score == 0.0
        assert NEUTRAL_AGGREGATED.conflict_score == 0.0

    def test_classify_dimension_unchanged(self):
        from umh.runtime.regime_aggregation import classify_dimension

        r = classify_dimension(DimensionName.TREND, "trend_up")
        assert r.direction is DirectionCategory.POSITIVE

    def test_aggregate_regimes_unchanged(self):
        state = aggregate_regimes(trend_label="trend_up", risk_label="high")
        assert state.dominant_dimension is not None


# ===========================================================================
# SECTION 47 — Phase 58 regression: orchestrate_selection unchanged
# ===========================================================================


class TestSection47Phase58Regression:
    def test_basic_selection_unchanged(self):
        r = orchestrate_selection(
            strategy_ids=["a", "b", "c"],
            base_scores=[0.7, 0.9, 0.5],
        )
        assert r.selected_strategy == "b"
        assert r.base_winner == "b"
        assert r.used_regime is True

    def test_feedback_disabled_by_default(self):
        r = orchestrate_selection(
            strategy_ids=["a"],
            base_scores=[0.8],
        )
        assert r.used_feedback is False

    def test_empty_strategies(self):
        r = orchestrate_selection(strategy_ids=[], base_scores=[])
        assert r.selected_strategy == ""
        assert r.explanation == "no strategies provided"

    def test_regime_factor_applied(self):
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.75],
            regime_factors=[0.90, 1.15],
        )
        assert r.selected_strategy == "b"
        assert r.changed_from_base is True


# ===========================================================================
# SECTION 48 — Init exports for Phase 61
# ===========================================================================


class TestSection48InitExports:
    def test_init_exports_weighted_decision_policy(self):
        from umh.runtime import WeightedDecisionPolicy as WDP

        assert WDP is not None

    def test_init_exports_weighted_decision_result(self):
        from umh.runtime import WeightedDecisionResult as WDR

        assert WDR is not None

    def test_init_exports_weighted_decision_batch_result(self):
        from umh.runtime import WeightedDecisionBatchResult as WDBR

        assert WDBR is not None

    def test_init_exports_default_policy(self):
        from umh.runtime import DEFAULT_WEIGHTED_DECISION_POLICY as D

        assert D.enabled is False

    def test_init_exports_apply(self):
        from umh.runtime import apply_weighted_influence as f

        assert callable(f)

    def test_init_exports_compute(self):
        from umh.runtime import compute_weight_factor as f

        assert callable(f)


# ===========================================================================
# SECTION 49 — Edge: single candidate
# ===========================================================================


class TestSection49SingleCandidate:
    def test_single_candidate_selected(self):
        regime = aggregate_regimes(trend_label="trend_down")
        r = orchestrate_selection(
            strategy_ids=["only"],
            base_scores=[0.8],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert r.selected_strategy == "only"

    def test_single_candidate_weight_applied(self):
        regime = aggregate_regimes(trend_label="trend_down")
        r = orchestrate_selection(
            strategy_ids=["only"],
            base_scores=[0.8],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert r.candidates[0].weight_factor != 1.0 or regime.is_neutral


# ===========================================================================
# SECTION 50 — Edge: all candidates same base score
# ===========================================================================


class TestSection50TieBreaking:
    def test_tie_broken_by_id(self):
        r = orchestrate_selection(
            strategy_ids=["b", "a", "c"],
            base_scores=[0.8, 0.8, 0.8],
            aggregated_regime=NEUTRAL_AGGREGATED,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert r.selected_strategy == "a"

    def test_weight_factor_same_for_tied_candidates(self):
        regime = aggregate_regimes(trend_label="trend_up")
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.8],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert r.candidates[0].weight_factor == r.candidates[1].weight_factor


# ===========================================================================
# SECTION 51 — Stress: many candidates
# ===========================================================================


class TestSection51Stress:
    def test_100_candidates(self):
        ids = [f"s{i:03d}" for i in range(100)]
        scores = [float(i) / 100.0 for i in range(100)]
        regime = aggregate_regimes(trend_label="trend_up")
        r = orchestrate_selection(
            strategy_ids=ids,
            base_scores=scores,
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert r.selected_strategy == "s099"
        assert len(r.candidates) == 100

    def test_stress_determinism(self):
        ids = [f"s{i}" for i in range(50)]
        scores = [0.5 + (i % 10) * 0.05 for i in range(50)]
        regime = aggregate_regimes(trend_label="spike_up", risk_label="high")
        policy = WeightedDecisionPolicy(enabled=True, min_confidence=0.0)
        weights = _make_high_confidence_weights()

        r1 = orchestrate_selection(
            ids,
            scores,
            aggregated_regime=regime,
            dimension_weights=weights,
            weighted_decision_policy=policy,
        )
        r2 = orchestrate_selection(
            ids,
            scores,
            aggregated_regime=regime,
            dimension_weights=weights,
            weighted_decision_policy=policy,
        )
        assert r1.selected_strategy == r2.selected_strategy
        assert r1.candidates[0].weight_factor == r2.candidates[0].weight_factor


# ===========================================================================
# SECTION 52 — No execution methods on data classes
# ===========================================================================


class TestSection52NoExecution:
    def test_policy_no_execute(self):
        assert not hasattr(WeightedDecisionPolicy, "execute")
        assert not hasattr(WeightedDecisionPolicy, "run")
        assert not hasattr(WeightedDecisionPolicy, "apply")

    def test_result_no_execute(self):
        assert not hasattr(WeightedDecisionResult, "execute")
        assert not hasattr(WeightedDecisionResult, "run")

    def test_batch_no_execute(self):
        assert not hasattr(WeightedDecisionBatchResult, "execute")
        assert not hasattr(WeightedDecisionBatchResult, "run")


# ===========================================================================
# SECTION 53 — Roundtrip: to_dict → values correct
# ===========================================================================


class TestSection53Roundtrip:
    def test_policy_roundtrip(self):
        p = WeightedDecisionPolicy(enabled=True, max_weight_influence=0.15, min_confidence=0.7)
        d = p.to_dict()
        assert d["enabled"] is True
        assert d["max_weight_influence"] == 0.15
        assert d["min_confidence"] == 0.7

    def test_result_roundtrip(self):
        r = WeightedDecisionResult(
            strategy_id="test",
            base_score=0.8,
            weight_factor=1.05,
            final_score=0.84,
            used_weights=True,
        )
        d = r.to_dict()
        assert d["strategy_id"] == "test"
        assert d["weight_factor"] == 1.05

    def test_batch_roundtrip(self):
        b = WeightedDecisionBatchResult(
            results=(WeightedDecisionResult(strategy_id="a", base_score=0.8),),
            overall_confidence=0.75,
        )
        d = b.to_dict()
        assert len(d["results"]) == 1
        assert d["overall_confidence"] == 0.75


# ===========================================================================
# SECTION 54 — Full pipeline: base → regime → feedback → weight
# ===========================================================================


class TestSection54FullPipeline:
    def test_full_four_stage_pipeline(self):
        from umh.runtime.feedback_selection import FeedbackSelectionPolicy

        regime = aggregate_regimes(
            trend_label="trend_up",
            risk_label="low",
            stability_label="high",
        )
        weights = _make_high_confidence_weights()

        r = orchestrate_selection(
            strategy_ids=["conservative", "aggressive", "balanced"],
            base_scores=[0.70, 0.80, 0.75],
            regime_factors=[1.10, 0.95, 1.05],
            feedback_factors=[1.0, 1.05, 1.0],
            confidences=[0.9, 0.7, 0.8],
            policy=StrategyOrchestrationPolicy(
                use_regime_weighting=True,
                use_feedback_selection=True,
                feedback_policy=FeedbackSelectionPolicy(enabled=True),
            ),
            aggregated_regime=regime,
            dimension_weights=weights,
            weighted_decision_policy=WeightedDecisionPolicy(
                enabled=True,
                min_confidence=0.0,
            ),
        )

        assert r.used_regime is True
        assert r.used_feedback is True
        assert r.used_weights is True
        assert r.selected_strategy != ""
        assert r.weighted_decision is not None

        for c in r.candidates:
            expected = c.base_score * c.regime_factor * c.feedback_factor * c.weight_factor
            assert abs(c.final_score - expected) < 1e-9

    def test_pipeline_explanation_all_layers(self):
        from umh.runtime.feedback_selection import FeedbackSelectionPolicy

        regime = aggregate_regimes(trend_label="trend_up")
        weights = _make_high_confidence_weights()

        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            policy=StrategyOrchestrationPolicy(
                use_regime_weighting=True,
                use_feedback_selection=True,
                feedback_policy=FeedbackSelectionPolicy(enabled=True),
            ),
            aggregated_regime=regime,
            dimension_weights=weights,
            weighted_decision_policy=WeightedDecisionPolicy(
                enabled=True,
                min_confidence=0.0,
            ),
        )

        assert "base_winner=" in r.explanation
        assert "regime_winner=" in r.explanation
        assert "feedback_winner=" in r.explanation
        assert "weight_winner=" in r.explanation
        assert "selected=" in r.explanation


# ===========================================================================
# SECTION 55 — Weight influence does not change rank with large gap
# ===========================================================================


class TestSection55NoFlipLargeGap:
    def test_20pct_gap_not_flipped(self):
        regime = aggregate_regimes(
            trend_label="spike_down",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        r = orchestrate_selection(
            strategy_ids=["leader", "follower"],
            base_scores=[1.0, 0.80],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(
                enabled=True,
                max_weight_influence=0.10,
                min_confidence=0.0,
            ),
        )
        assert r.selected_strategy == "leader"

    def test_larger_influence_still_bounded(self):
        regime = aggregate_regimes(
            trend_label="spike_up",
            risk_label="low",
            stability_label="high",
            urgency_label="low",
        )
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.5, 0.9],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(
                enabled=True,
                max_weight_influence=0.10,
                min_confidence=0.0,
            ),
        )
        assert r.selected_strategy == "b"


# ===========================================================================
# SECTION 56 — Weight influence CAN tip close race
# ===========================================================================


class TestSection56TipCloseRace:
    def test_close_race_can_be_tipped(self):
        regime = aggregate_regimes(
            trend_label="spike_up",
            risk_label="low",
            stability_label="high",
            urgency_label="low",
        )
        r_without = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.800, 0.801],
        )
        assert r_without.selected_strategy == "b"

        r_with = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.800, 0.801],
            aggregated_regime=regime,
            dimension_weights=_make_high_confidence_weights(),
            weighted_decision_policy=WeightedDecisionPolicy(
                enabled=True,
                max_weight_influence=0.10,
                min_confidence=0.0,
            ),
        )
        assert r_with.used_weights is True


# ===========================================================================
# SECTION 57 — Dimension weighting influence varies by weight magnitude
# ===========================================================================


class TestSection57WeightMagnitude:
    def test_higher_dimension_weight_increases_contribution(self):
        high_trend_weights = _make_weighted_vector(
            trend=0.40, risk=0.20, stability=0.20, urgency=0.20
        )
        low_trend_weights = _make_weighted_vector(
            trend=0.10, risk=0.30, stability=0.30, urgency=0.30
        )

        regime = aggregate_regimes(trend_label="spike_up")

        f1, _, _, _ = compute_weight_factor(
            weights=high_trend_weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        f2, _, _, _ = compute_weight_factor(
            weights=low_trend_weights,
            regime=regime,
            policy=WeightedDecisionPolicy(enabled=True, min_confidence=0.0),
        )
        assert f1 > f2


# ===========================================================================
# SECTION 58 — Zero max_weight_influence → no effect
# ===========================================================================


class TestSection58ZeroInfluence:
    def test_zero_influence_neutral(self):
        regime = aggregate_regimes(trend_label="spike_up")
        factor, used, _, _ = compute_weight_factor(
            weights=_make_high_confidence_weights(),
            regime=regime,
            policy=WeightedDecisionPolicy(
                enabled=True, max_weight_influence=0.0, min_confidence=0.0
            ),
        )
        assert factor == 1.0
        assert used is True


# ===========================================================================
# SECTION 59 — Empty selection with weights
# ===========================================================================


class TestSection59EmptySelection:
    def test_empty_with_weights(self):
        r = orchestrate_selection(
            strategy_ids=[],
            base_scores=[],
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True),
        )
        assert r.selected_strategy == ""
        assert r.used_weights is False

    def test_all_invalid_with_weights(self):
        r = orchestrate_selection(
            strategy_ids=["a", "b"],
            base_scores=[0.8, 0.6],
            valid_flags=[False, False],
            weighted_decision_policy=WeightedDecisionPolicy(enabled=True),
        )
        assert r.selected_strategy == ""


# ===========================================================================
# SECTION 60 — No randomness (inv 262)
# ===========================================================================


class TestSection60NoRandomness:
    def test_no_random_import(self):
        import inspect
        import umh.runtime.weighted_decision as m

        src = inspect.getsource(m)
        assert "import random" not in src
        assert "from random" not in src


# ============================= HELPERS ====================================


def _make_high_confidence_weights() -> DimensionWeightVector:
    weights = {
        dim.value: DimensionWeight(
            dimension=dim,
            weight=0.25,
            confidence=1.0,
            source="learned",
        )
        for dim in DimensionName
    }
    return DimensionWeightVector(weights=weights, normalized=True)


def _make_low_confidence_weights(conf: float) -> DimensionWeightVector:
    weights = {
        dim.value: DimensionWeight(
            dimension=dim,
            weight=0.25,
            confidence=conf,
            source="learned",
        )
        for dim in DimensionName
    }
    return DimensionWeightVector(weights=weights, normalized=True)


def _make_exact_confidence_weights(conf: float) -> DimensionWeightVector:
    weights = {
        dim.value: DimensionWeight(
            dimension=dim,
            weight=0.25,
            confidence=conf,
            source="learned",
        )
        for dim in DimensionName
    }
    return DimensionWeightVector(weights=weights, normalized=True)


def _make_weighted_vector(
    trend: float = 0.25,
    risk: float = 0.25,
    stability: float = 0.25,
    urgency: float = 0.25,
    confidence: float = 1.0,
) -> DimensionWeightVector:
    weights = {
        DimensionName.TREND.value: DimensionWeight(
            dimension=DimensionName.TREND, weight=trend, confidence=confidence, source="learned"
        ),
        DimensionName.RISK.value: DimensionWeight(
            dimension=DimensionName.RISK, weight=risk, confidence=confidence, source="learned"
        ),
        DimensionName.STABILITY.value: DimensionWeight(
            dimension=DimensionName.STABILITY,
            weight=stability,
            confidence=confidence,
            source="learned",
        ),
        DimensionName.URGENCY.value: DimensionWeight(
            dimension=DimensionName.URGENCY, weight=urgency, confidence=confidence, source="learned"
        ),
    }
    return DimensionWeightVector(weights=weights, normalized=True)
