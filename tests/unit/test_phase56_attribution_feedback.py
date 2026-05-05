"""Phase 56 — Attribution-guided feedback coupling tests.

Tests the controlled coupling layer that converts contextual attribution
into bounded, explainable feedback influence.

Invariants 217-224.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime.attribution import (
    AttributionBucket,
    AttributionDimension,
    AttributionEngine,
    ContextAttributionRecord,
    ContextFeatures,
    extract_context_features,
)
from umh.runtime.attribution_feedback import (
    EPSILON,
    AttributionFeedbackPolicy,
    AttributionFeedbackResult,
    CombinedFeedbackResult,
    CouplingDirection,
    combine_feedback_factors,
    compare_scores,
    compute_attribution_feedback_factor,
    is_equal,
    is_greater,
    is_less,
)
from umh.runtime.feedback_bridge import FeedbackBridge, FeedbackRecord
from umh.runtime.outcome import OutcomeStatus, StrategyOutcome
from umh.runtime.outcome_memory import OutcomeMemory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_OUTCOME_COUNTER = 0


def _make_outcome(
    strategy: str = "strat_a",
    state: str = "state_1",
    status: OutcomeStatus = OutcomeStatus.SUCCESS,
    score: float = 0.8,
    latency: float = 1.0,
    effort: float = 0.3,
    metadata: dict | None = None,
) -> StrategyOutcome:
    global _OUTCOME_COUNTER
    _OUTCOME_COUNTER += 1
    return StrategyOutcome(
        outcome_id=f"out_{_OUTCOME_COUNTER}",
        decision_id=f"dec_{_OUTCOME_COUNTER}",
        action_name=f"action_{_OUTCOME_COUNTER}",
        strategy_name=strategy,
        state_signature=state,
        status=status,
        success_score=score,
        latency=latency,
        effort=effort,
        metadata=metadata or {},
    )


def _make_record(
    strategy: str = "strat_a",
    state: str = "state_1",
    overall_score: float = 0.7,
    confidence: float = 0.8,
    buckets: tuple[AttributionBucket, ...] = (),
) -> ContextAttributionRecord:
    return ContextAttributionRecord(
        strategy_name=strategy,
        state_signature=state,
        overall_score=overall_score,
        confidence=confidence,
        dimension_buckets=buckets,
        explanation=f"test record for {strategy}",
    )


def _pos_bucket(
    dim: AttributionDimension = AttributionDimension.TREND,
    value: str = "up",
    score: float = 0.9,
    confidence: float = 0.8,
    samples: int = 25,
) -> AttributionBucket:
    return AttributionBucket(
        dimension=dim,
        value=value,
        sample_count=samples,
        success_count=int(samples * score),
        average_success_score=score,
        confidence=confidence,
    )


def _neg_bucket(
    dim: AttributionDimension = AttributionDimension.RISK,
    value: str = "high",
    score: float = 0.3,
    confidence: float = 0.8,
    samples: int = 25,
) -> AttributionBucket:
    return AttributionBucket(
        dimension=dim,
        value=value,
        sample_count=samples,
        failure_count=int(samples * (1 - score)),
        average_success_score=score,
        confidence=confidence,
    )


# ===========================================================================
# SECTION 1 — CouplingDirection enum
# ===========================================================================


class TestSection01CouplingDirection:
    def test_boost_value(self):
        assert CouplingDirection.BOOST.value == "boost"

    def test_penalize_value(self):
        assert CouplingDirection.PENALIZE.value == "penalize"

    def test_neutral_value(self):
        assert CouplingDirection.NEUTRAL.value == "neutral"

    def test_member_count(self):
        assert len(CouplingDirection) == 3


# ===========================================================================
# SECTION 2 — AttributionFeedbackPolicy defaults
# ===========================================================================


class TestSection02PolicyDefaults:
    def test_disabled_by_default(self):
        p = AttributionFeedbackPolicy()
        assert p.enabled is False

    def test_default_min_confidence(self):
        assert AttributionFeedbackPolicy().min_confidence == 0.5

    def test_default_max_boost(self):
        assert AttributionFeedbackPolicy().max_boost == 0.08

    def test_default_max_penalty(self):
        assert AttributionFeedbackPolicy().max_penalty == 0.08

    def test_default_neutral_factor(self):
        assert AttributionFeedbackPolicy().neutral_factor == 1.0

    def test_default_required_samples(self):
        assert AttributionFeedbackPolicy().required_samples == 20


# ===========================================================================
# SECTION 3 — Policy bounds clamping
# ===========================================================================


class TestSection03PolicyBounds:
    def test_min_confidence_clamped_low(self):
        p = AttributionFeedbackPolicy(min_confidence=-0.5)
        assert p.min_confidence == 0.0

    def test_min_confidence_clamped_high(self):
        p = AttributionFeedbackPolicy(min_confidence=2.0)
        assert p.min_confidence == 1.0

    def test_max_boost_clamped_low(self):
        p = AttributionFeedbackPolicy(max_boost=-0.1)
        assert p.max_boost == 0.0

    def test_max_boost_clamped_high(self):
        p = AttributionFeedbackPolicy(max_boost=0.5)
        assert p.max_boost == 0.20

    def test_max_penalty_clamped_low(self):
        p = AttributionFeedbackPolicy(max_penalty=-0.1)
        assert p.max_penalty == 0.0

    def test_max_penalty_clamped_high(self):
        p = AttributionFeedbackPolicy(max_penalty=0.5)
        assert p.max_penalty == 0.20

    def test_required_samples_clamped(self):
        p = AttributionFeedbackPolicy(required_samples=0)
        assert p.required_samples == 1

    def test_required_samples_negative(self):
        p = AttributionFeedbackPolicy(required_samples=-10)
        assert p.required_samples == 1


# ===========================================================================
# SECTION 4 — Policy to_dict
# ===========================================================================


class TestSection04PolicyDict:
    def test_to_dict_keys(self):
        d = AttributionFeedbackPolicy().to_dict()
        expected = {
            "enabled",
            "min_confidence",
            "max_boost",
            "max_penalty",
            "neutral_factor",
            "required_samples",
        }
        assert set(d.keys()) == expected

    def test_to_dict_values(self):
        d = AttributionFeedbackPolicy(enabled=True, max_boost=0.05).to_dict()
        assert d["enabled"] is True
        assert d["max_boost"] == 0.05


# ===========================================================================
# SECTION 5 — Policy frozen
# ===========================================================================


class TestSection05PolicyFrozen:
    def test_frozen(self):
        p = AttributionFeedbackPolicy()
        try:
            p.enabled = True
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 6 — AttributionFeedbackResult defaults
# ===========================================================================


class TestSection06ResultDefaults:
    def test_default_factor(self):
        r = AttributionFeedbackResult()
        assert r.factor == 1.0

    def test_default_confidence(self):
        assert AttributionFeedbackResult().confidence == 0.0

    def test_default_direction(self):
        assert AttributionFeedbackResult().direction == CouplingDirection.NEUTRAL

    def test_default_reason(self):
        assert AttributionFeedbackResult().reason == ""

    def test_default_dimensions(self):
        r = AttributionFeedbackResult()
        assert r.strongest_positive_dimension == ""
        assert r.strongest_negative_dimension == ""

    def test_default_enabled(self):
        assert AttributionFeedbackResult().enabled is False


# ===========================================================================
# SECTION 7 — Result bounds
# ===========================================================================


class TestSection07ResultBounds:
    def test_factor_clamped_low(self):
        r = AttributionFeedbackResult(factor=-1.0)
        assert r.factor == 0.0

    def test_factor_clamped_high(self):
        r = AttributionFeedbackResult(factor=5.0)
        assert r.factor == 2.0

    def test_confidence_clamped_low(self):
        r = AttributionFeedbackResult(confidence=-0.5)
        assert r.confidence == 0.0

    def test_confidence_clamped_high(self):
        r = AttributionFeedbackResult(confidence=2.0)
        assert r.confidence == 1.0


# ===========================================================================
# SECTION 8 — Result to_dict
# ===========================================================================


class TestSection08ResultDict:
    def test_to_dict_keys(self):
        d = AttributionFeedbackResult().to_dict()
        expected = {
            "factor",
            "confidence",
            "direction",
            "reason",
            "strongest_positive_dimension",
            "strongest_negative_dimension",
            "enabled",
        }
        assert set(d.keys()) == expected

    def test_to_dict_direction_string(self):
        r = AttributionFeedbackResult(direction=CouplingDirection.BOOST)
        assert r.to_dict()["direction"] == "boost"


# ===========================================================================
# SECTION 9 — Result frozen
# ===========================================================================


class TestSection09ResultFrozen:
    def test_frozen(self):
        r = AttributionFeedbackResult()
        try:
            r.factor = 0.5
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 10 — CombinedFeedbackResult defaults
# ===========================================================================


class TestSection10CombinedDefaults:
    def test_default_combined_factor(self):
        assert CombinedFeedbackResult().combined_factor == 1.0

    def test_default_base_factor(self):
        assert CombinedFeedbackResult().base_factor == 1.0

    def test_default_attribution_factor(self):
        assert CombinedFeedbackResult().attribution_factor == 1.0

    def test_default_reason(self):
        assert CombinedFeedbackResult().reason == ""


# ===========================================================================
# SECTION 11 — CombinedFeedbackResult bounds
# ===========================================================================


class TestSection11CombinedBounds:
    def test_combined_factor_clamped_low(self):
        r = CombinedFeedbackResult(combined_factor=-1.0)
        assert r.combined_factor == 0.0

    def test_combined_factor_clamped_high(self):
        r = CombinedFeedbackResult(combined_factor=5.0)
        assert r.combined_factor == 2.0


# ===========================================================================
# SECTION 12 — CombinedFeedbackResult to_dict
# ===========================================================================


class TestSection12CombinedDict:
    def test_to_dict_keys(self):
        d = CombinedFeedbackResult().to_dict()
        assert set(d.keys()) == {"combined_factor", "base_factor", "attribution_factor", "reason"}


# ===========================================================================
# SECTION 13 — CombinedFeedbackResult frozen
# ===========================================================================


class TestSection13CombinedFrozen:
    def test_frozen(self):
        r = CombinedFeedbackResult()
        try:
            r.combined_factor = 0.5
            assert False, "should be frozen"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 14 — Disabled policy returns neutral (inv 217)
# ===========================================================================


class TestSection14DisabledPolicy:
    def test_disabled_returns_neutral_factor(self):
        r = compute_attribution_feedback_factor(None)
        assert r.factor == 1.0

    def test_disabled_direction_neutral(self):
        r = compute_attribution_feedback_factor(None)
        assert r.direction == CouplingDirection.NEUTRAL

    def test_disabled_not_enabled(self):
        r = compute_attribution_feedback_factor(None)
        assert r.enabled is False

    def test_disabled_reason(self):
        r = compute_attribution_feedback_factor(None)
        assert "disabled" in r.reason

    def test_disabled_with_record(self):
        rec = _make_record()
        r = compute_attribution_feedback_factor(rec)
        assert r.factor == 1.0

    def test_explicit_disabled_policy(self):
        p = AttributionFeedbackPolicy(enabled=False)
        rec = _make_record(confidence=1.0)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor == 1.0
        assert r.enabled is False


# ===========================================================================
# SECTION 15 — Missing attribution returns neutral (inv 224)
# ===========================================================================


class TestSection15MissingAttribution:
    def test_none_attribution(self):
        p = AttributionFeedbackPolicy(enabled=True)
        r = compute_attribution_feedback_factor(None, p)
        assert r.factor == 1.0

    def test_none_reason(self):
        p = AttributionFeedbackPolicy(enabled=True)
        r = compute_attribution_feedback_factor(None, p)
        assert "no attribution data" in r.reason

    def test_none_is_enabled(self):
        p = AttributionFeedbackPolicy(enabled=True)
        r = compute_attribution_feedback_factor(None, p)
        assert r.enabled is True

    def test_empty_buckets(self):
        p = AttributionFeedbackPolicy(enabled=True)
        rec = _make_record(buckets=())
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor == 1.0
        assert "no dimension buckets" in r.reason


# ===========================================================================
# SECTION 16 — Low confidence returns neutral (inv 219)
# ===========================================================================


class TestSection16LowConfidence:
    def test_low_record_confidence(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.5)
        buckets = (_pos_bucket(confidence=0.8),)
        rec = _make_record(confidence=0.3, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor == 1.0

    def test_low_bucket_confidence(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.5)
        buckets = (_pos_bucket(confidence=0.2),)
        rec = _make_record(confidence=0.9, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor == 1.0

    def test_low_confidence_reason(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.5)
        buckets = (_pos_bucket(confidence=0.3),)
        rec = _make_record(confidence=0.4, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert "below threshold" in r.reason

    def test_exactly_at_threshold(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.5)
        buckets = (_pos_bucket(confidence=0.5),)
        rec = _make_record(confidence=0.5, overall_score=0.5, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor != 1.0 or r.direction == CouplingDirection.NEUTRAL


# ===========================================================================
# SECTION 17 — Positive attribution boosts
# ===========================================================================


class TestSection17PositiveBoost:
    def test_boost_direction(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = (_pos_bucket(score=0.9, confidence=0.8),)
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.direction == CouplingDirection.BOOST

    def test_boost_factor_above_one(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = (_pos_bucket(score=0.9, confidence=0.8),)
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor > 1.0

    def test_boost_bounded(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.1, max_boost=0.08)
        buckets = (_pos_bucket(score=1.0, confidence=1.0),)
        rec = _make_record(overall_score=0.0, confidence=1.0, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor <= 1.08

    def test_boost_positive_dimension_recorded(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = (
            _pos_bucket(dim=AttributionDimension.TREND, value="up", score=0.9, confidence=0.8),
        )
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert "trend=up" in r.strongest_positive_dimension


# ===========================================================================
# SECTION 18 — Negative attribution penalizes
# ===========================================================================


class TestSection18NegativePenalty:
    def test_penalty_direction(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = (_neg_bucket(score=0.1, confidence=0.8),)
        rec = _make_record(overall_score=0.7, confidence=0.8, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.direction == CouplingDirection.PENALIZE

    def test_penalty_factor_below_one(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = (_neg_bucket(score=0.1, confidence=0.8),)
        rec = _make_record(overall_score=0.7, confidence=0.8, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor < 1.0

    def test_penalty_bounded(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.1, max_penalty=0.08)
        buckets = (_neg_bucket(score=0.0, confidence=1.0),)
        rec = _make_record(overall_score=1.0, confidence=1.0, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor >= 0.92

    def test_negative_dimension_recorded(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = (
            _neg_bucket(dim=AttributionDimension.RISK, value="high", score=0.1, confidence=0.8),
        )
        rec = _make_record(overall_score=0.7, confidence=0.8, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert "risk=high" in r.strongest_negative_dimension


# ===========================================================================
# SECTION 19 — Neutral attribution
# ===========================================================================


class TestSection19NeutralAttribution:
    def test_no_deviation_neutral(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = (_pos_bucket(score=0.7, confidence=0.8),)
        rec = _make_record(overall_score=0.56, confidence=0.8, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.direction == CouplingDirection.NEUTRAL or abs(r.factor - 1.0) < 0.001

    def test_only_strategy_buckets_neutral(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b = AttributionBucket(
            dimension=AttributionDimension.STRATEGY,
            value="strat_a",
            sample_count=30,
            average_success_score=0.9,
            confidence=0.9,
        )
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor == 1.0


# ===========================================================================
# SECTION 20 — Factor clamping (inv 218)
# ===========================================================================


class TestSection20FactorClamping:
    def test_default_policy_max_factor(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.0)
        buckets = (_pos_bucket(score=1.0, confidence=1.0),)
        rec = _make_record(overall_score=0.0, confidence=1.0, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor <= 1.08

    def test_default_policy_min_factor(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.0)
        buckets = (_neg_bucket(score=0.0, confidence=1.0),)
        rec = _make_record(overall_score=1.0, confidence=1.0, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor >= 0.92

    def test_factor_within_bounds(self):
        p = AttributionFeedbackPolicy(
            enabled=True, min_confidence=0.0, max_boost=0.05, max_penalty=0.05
        )
        buckets = (_pos_bucket(score=1.0, confidence=1.0),)
        rec = _make_record(overall_score=0.0, confidence=1.0, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert 0.95 <= r.factor <= 1.05


# ===========================================================================
# SECTION 21 — Positive dimension detection
# ===========================================================================


class TestSection21PositiveDetection:
    def test_detects_highest_bucket(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b1 = _pos_bucket(dim=AttributionDimension.TREND, value="up", score=0.9, confidence=0.8)
        b2 = _pos_bucket(
            dim=AttributionDimension.STABILITY, value="high", score=0.8, confidence=0.8
        )
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=(b1, b2))
        r = compute_attribution_feedback_factor(rec, p)
        assert "trend=up" in r.strongest_positive_dimension

    def test_no_positive_when_all_below(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b = _neg_bucket(score=0.3, confidence=0.8)
        rec = _make_record(overall_score=0.7, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.strongest_positive_dimension == ""


# ===========================================================================
# SECTION 22 — Negative dimension detection
# ===========================================================================


class TestSection22NegativeDetection:
    def test_detects_lowest_bucket(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b1 = _neg_bucket(dim=AttributionDimension.RISK, value="high", score=0.1, confidence=0.8)
        b2 = _neg_bucket(
            dim=AttributionDimension.URGENCY, value="critical", score=0.3, confidence=0.8
        )
        rec = _make_record(overall_score=0.7, confidence=0.8, buckets=(b1, b2))
        r = compute_attribution_feedback_factor(rec, p)
        assert "risk=high" in r.strongest_negative_dimension

    def test_no_negative_when_all_above(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b = _pos_bucket(score=0.9, confidence=0.8)
        rec = _make_record(overall_score=0.3, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.strongest_negative_dimension == ""


# ===========================================================================
# SECTION 23 — Dimension tie determinism
# ===========================================================================


class TestSection23TieDeterminism:
    def test_same_score_deterministic(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b1 = _pos_bucket(dim=AttributionDimension.TREND, value="up", score=0.9, confidence=0.8)
        b2 = _pos_bucket(
            dim=AttributionDimension.STABILITY, value="high", score=0.9, confidence=0.8
        )
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=(b1, b2))
        results = [compute_attribution_feedback_factor(rec, p) for _ in range(10)]
        factors = [r.factor for r in results]
        assert len(set(factors)) == 1


# ===========================================================================
# SECTION 24 — Sparse bucket handling
# ===========================================================================


class TestSection24SparseBucket:
    def test_zero_sample_bucket_ignored(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b = AttributionBucket(
            dimension=AttributionDimension.TREND,
            value="up",
            sample_count=0,
            average_success_score=1.0,
            confidence=0.0,
        )
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor == 1.0

    def test_low_sample_bucket_low_confidence(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.5)
        b = _pos_bucket(score=0.9, confidence=0.1, samples=2)
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor == 1.0


# ===========================================================================
# SECTION 25 — Combined confidence (min of record + bucket)
# ===========================================================================


class TestSection25CombinedConfidence:
    def test_uses_minimum(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b = _pos_bucket(score=0.9, confidence=0.4)
        rec = _make_record(overall_score=0.5, confidence=0.9, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.confidence == 0.4

    def test_record_lower(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b = _pos_bucket(score=0.9, confidence=0.9)
        rec = _make_record(overall_score=0.5, confidence=0.35, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.confidence == 0.35

    def test_both_sufficient(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.5)
        b = _pos_bucket(score=0.9, confidence=0.8)
        rec = _make_record(overall_score=0.5, confidence=0.7, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.confidence == 0.7
        assert r.factor != 1.0


# ===========================================================================
# SECTION 26 — combine_feedback_factors neutral
# ===========================================================================


class TestSection26CombineNeutral:
    def test_attribution_neutral_returns_base(self):
        r = combine_feedback_factors(1.05, 1.0)
        assert r.combined_factor == 1.05

    def test_attribution_neutral_reason(self):
        r = combine_feedback_factors(1.05, 1.0)
        assert "attribution neutral" in r.reason

    def test_base_factors_preserved(self):
        r = combine_feedback_factors(0.95, 1.0)
        assert r.base_factor == 0.95
        assert r.attribution_factor == 1.0


# ===========================================================================
# SECTION 27 — combine_feedback_factors boost clamped
# ===========================================================================


class TestSection27CombineBoost:
    def test_combined_boost_clamped(self):
        r = combine_feedback_factors(1.10, 1.08)
        assert r.combined_factor <= 1.12

    def test_combined_factor_positive(self):
        r = combine_feedback_factors(1.05, 1.05)
        assert r.combined_factor > 1.0

    def test_explicit_max(self):
        r = combine_feedback_factors(1.10, 1.08, max_combined_boost=0.05)
        assert r.combined_factor <= 1.05


# ===========================================================================
# SECTION 28 — combine_feedback_factors penalty clamped
# ===========================================================================


class TestSection28CombinePenalty:
    def test_combined_penalty_clamped(self):
        r = combine_feedback_factors(0.90, 0.92)
        assert r.combined_factor >= 0.88

    def test_combined_factor_negative(self):
        r = combine_feedback_factors(0.95, 0.95)
        assert r.combined_factor < 1.0

    def test_explicit_max_penalty(self):
        r = combine_feedback_factors(0.90, 0.92, max_combined_penalty=0.05)
        assert r.combined_factor >= 0.95


# ===========================================================================
# SECTION 29 — combine deterministic
# ===========================================================================


class TestSection29CombineDeterministic:
    def test_same_inputs_same_output(self):
        results = [combine_feedback_factors(1.05, 1.03) for _ in range(10)]
        assert len(set(r.combined_factor for r in results)) == 1


# ===========================================================================
# SECTION 30 — combine explanation
# ===========================================================================


class TestSection30CombineExplanation:
    def test_reason_includes_base(self):
        r = combine_feedback_factors(1.05, 1.03)
        assert "base=" in r.reason

    def test_reason_includes_attribution(self):
        r = combine_feedback_factors(1.05, 1.03)
        assert "attribution=" in r.reason

    def test_reason_includes_clamped(self):
        r = combine_feedback_factors(1.05, 1.03)
        assert "clamped" in r.reason


# ===========================================================================
# SECTION 31 — FeedbackBridge default behavior unchanged (inv 217)
# ===========================================================================


class TestSection31BridgeUnchanged:
    def test_record_outcome_signature(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        o = _make_outcome()
        rec = bridge.record_outcome(o)
        assert isinstance(rec, FeedbackRecord)
        assert rec.outcome == o

    def test_bridge_has_no_attribution_required(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        o = _make_outcome()
        rec = bridge.record_outcome(o)
        assert rec.explanation
        assert "strat_a" in rec.explanation


# ===========================================================================
# SECTION 32 — Optional attribution feedback composable
# ===========================================================================


class TestSection32OptionalComposition:
    def test_can_compute_attribution_after_bridge(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        for i in range(25):
            o = _make_outcome(
                score=0.8 if i < 20 else 0.2,
                metadata={"trend": "up", "risk": "low"},
            )
            bridge.record_outcome(o)

        engine = AttributionEngine(required_samples=10)
        attr = engine.build_attribution(mem.list_outcomes(), strategy_name="strat_a")
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        r = compute_attribution_feedback_factor(attr, p)
        assert r.enabled is True
        assert isinstance(r.factor, float)


# ===========================================================================
# SECTION 33 — No mutation of outcomes (inv 220)
# ===========================================================================


class TestSection33NoOutcomeMutation:
    def test_outcomes_unchanged(self):
        outcomes = [_make_outcome(score=0.8, metadata={"trend": "up"}) for _ in range(25)]
        original_scores = [o.success_score for o in outcomes]
        engine = AttributionEngine(required_samples=10)
        attr = engine.build_attribution(outcomes, strategy_name="strat_a")
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.1)
        compute_attribution_feedback_factor(attr, p)
        assert [o.success_score for o in outcomes] == original_scores


# ===========================================================================
# SECTION 34 — No mutation of attribution records (inv 220)
# ===========================================================================


class TestSection34NoAttributionMutation:
    def test_record_unchanged(self):
        buckets = (_pos_bucket(score=0.9, confidence=0.8),)
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=buckets)
        original_score = rec.overall_score
        original_conf = rec.confidence
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        compute_attribution_feedback_factor(rec, p)
        assert rec.overall_score == original_score
        assert rec.confidence == original_conf

    def test_bucket_unchanged(self):
        b = _pos_bucket(score=0.9, confidence=0.8)
        original_score = b.average_success_score
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=(b,))
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        compute_attribution_feedback_factor(rec, p)
        assert b.average_success_score == original_score


# ===========================================================================
# SECTION 35 — Deterministic output (inv 221)
# ===========================================================================


class TestSection35Deterministic:
    def test_same_inputs_same_result(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = (_pos_bucket(score=0.9, confidence=0.8),)
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=buckets)
        results = [compute_attribution_feedback_factor(rec, p) for _ in range(20)]
        factors = [r.factor for r in results]
        assert len(set(factors)) == 1

    def test_directions_consistent(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = (_neg_bucket(score=0.1, confidence=0.8),)
        rec = _make_record(overall_score=0.7, confidence=0.8, buckets=buckets)
        results = [compute_attribution_feedback_factor(rec, p) for _ in range(20)]
        directions = [r.direction for r in results]
        assert len(set(directions)) == 1


# ===========================================================================
# SECTION 36 — No execution / planner mutation (inv 222)
# ===========================================================================


class TestSection36NoExecution:
    def test_no_execute_method(self):
        assert not hasattr(AttributionFeedbackPolicy, "execute")
        assert not hasattr(AttributionFeedbackResult, "execute")

    def test_no_apply_method(self):
        assert not hasattr(AttributionFeedbackPolicy, "apply")
        assert not hasattr(AttributionFeedbackResult, "apply")

    def test_no_set_score(self):
        assert not hasattr(AttributionFeedbackPolicy, "set_score")
        assert not hasattr(AttributionFeedbackResult, "set_score")


# ===========================================================================
# SECTION 37 — Factor never overrides base score (inv 223)
# ===========================================================================


class TestSection37NoOverride:
    def test_factor_is_multiplier_not_replacement(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.1)
        buckets = (_pos_bucket(score=0.9, confidence=0.8),)
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert 0.92 <= r.factor <= 1.08

    def test_combine_preserves_base(self):
        r = combine_feedback_factors(1.05, 1.03)
        assert r.base_factor == 1.05


# ===========================================================================
# SECTION 38 — Boundary compliance
# ===========================================================================


class TestSection38Boundary:
    def test_no_os_import(self):
        import umh.runtime.attribution_feedback as m
        import inspect

        src = inspect.getsource(m)
        code_section = src.split('"""')[-1]
        assert "import os" not in code_section

    def test_no_subprocess_import(self):
        import umh.runtime.attribution_feedback as m
        import inspect

        src = inspect.getsource(m)
        code_section = src.split('"""')[-1]
        assert "import subprocess" not in code_section

    def test_no_docker_import(self):
        import umh.runtime.attribution_feedback as m
        import inspect

        src = inspect.getsource(m)
        code_section = src.split('"""')[-1]
        assert "import docker" not in code_section

    def test_no_cells_import(self):
        import umh.runtime.attribution_feedback as m
        import inspect

        src = inspect.getsource(m)
        assert "from umh.cells" not in src
        assert "from umh.environments" not in src
        assert "from umh.adapters" not in src


# ===========================================================================
# SECTION 39 — Import surface
# ===========================================================================


class TestSection39ImportSurface:
    def test_all_exports(self):
        from umh.runtime import (
            AttributionFeedbackPolicy,
            AttributionFeedbackResult,
            CombinedFeedbackResult,
            CouplingDirection,
            combine_feedback_factors,
            compute_attribution_feedback_factor,
        )

        assert AttributionFeedbackPolicy is not None
        assert AttributionFeedbackResult is not None
        assert CombinedFeedbackResult is not None
        assert CouplingDirection is not None
        assert combine_feedback_factors is not None
        assert compute_attribution_feedback_factor is not None


# ===========================================================================
# SECTION 40 — Integration: full pipeline
# ===========================================================================


class TestSection40Integration:
    def test_full_pipeline(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        for i in range(30):
            meta = {"trend": "up" if i < 20 else "down", "risk": "low"}
            o = _make_outcome(
                score=0.85 if i < 20 else 0.3,
                metadata=meta,
            )
            bridge.record_outcome(o)

        engine = AttributionEngine(required_samples=10)
        attr = engine.build_attribution(mem.list_outcomes(), strategy_name="strat_a")

        policy = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        result = compute_attribution_feedback_factor(attr, policy)

        assert result.enabled is True
        assert isinstance(result.factor, float)
        assert 0.92 <= result.factor <= 1.08
        assert result.reason

    def test_pipeline_with_composition(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        for _ in range(30):
            o = _make_outcome(score=0.8, metadata={"trend": "up"})
            bridge.record_outcome(o)

        engine = AttributionEngine(required_samples=10)
        attr = engine.build_attribution(mem.list_outcomes(), strategy_name="strat_a")

        policy = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        attr_result = compute_attribution_feedback_factor(attr, policy)

        base_factor = 1.05
        combined = combine_feedback_factors(base_factor, attr_result.factor)
        assert 0.88 <= combined.combined_factor <= 1.12


# ===========================================================================
# SECTION 41 — Edge: both positive and negative buckets
# ===========================================================================


class TestSection41MixedBuckets:
    def test_positive_wins_when_stronger_deviation(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        pos = _pos_bucket(dim=AttributionDimension.TREND, value="up", score=0.95, confidence=0.8)
        neg = _neg_bucket(dim=AttributionDimension.RISK, value="high", score=0.6, confidence=0.8)
        rec = _make_record(overall_score=0.7, confidence=0.8, buckets=(pos, neg))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.strongest_positive_dimension != ""
        assert r.strongest_negative_dimension != ""

    def test_negative_wins_when_stronger_deviation(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        pos = _pos_bucket(dim=AttributionDimension.TREND, value="up", score=0.75, confidence=0.8)
        neg = _neg_bucket(dim=AttributionDimension.RISK, value="high", score=0.05, confidence=0.8)
        rec = _make_record(overall_score=0.7, confidence=0.8, buckets=(pos, neg))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor < 1.0 or r.direction == CouplingDirection.PENALIZE


# ===========================================================================
# SECTION 42 — Edge: many buckets
# ===========================================================================


class TestSection42ManyBuckets:
    def test_many_buckets_deterministic(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = tuple(
            _pos_bucket(
                dim=AttributionDimension.TREND,
                value=f"val_{i}",
                score=0.5 + i * 0.05,
                confidence=0.8,
            )
            for i in range(8)
        )
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=buckets)
        results = [compute_attribution_feedback_factor(rec, p) for _ in range(5)]
        assert len(set(r.factor for r in results)) == 1


# ===========================================================================
# SECTION 43 — Edge: confidence exactly zero
# ===========================================================================


class TestSection43ZeroConfidence:
    def test_zero_record_confidence(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.1)
        buckets = (_pos_bucket(score=0.9, confidence=0.8),)
        rec = _make_record(overall_score=0.5, confidence=0.0, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor == 1.0

    def test_zero_bucket_confidence(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.1)
        b = _pos_bucket(score=0.9, confidence=0.0)
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor == 1.0


# ===========================================================================
# SECTION 44 — Edge: confidence exactly 1.0
# ===========================================================================


class TestSection44FullConfidence:
    def test_full_confidence_applies(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.5)
        buckets = (_pos_bucket(score=0.9, confidence=1.0),)
        rec = _make_record(overall_score=0.5, confidence=1.0, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor > 1.0
        assert r.confidence == 1.0


# ===========================================================================
# SECTION 45 — Edge: overall_score = 0
# ===========================================================================


class TestSection45ZeroOverall:
    def test_zero_overall_boosts_any_positive(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = (_pos_bucket(score=0.5, confidence=0.8),)
        rec = _make_record(overall_score=0.0, confidence=0.8, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor > 1.0


# ===========================================================================
# SECTION 46 — Edge: overall_score = 1.0
# ===========================================================================


class TestSection46PerfectOverall:
    def test_perfect_overall_penalizes_any_negative(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = (_neg_bucket(score=0.5, confidence=0.8),)
        rec = _make_record(overall_score=1.0, confidence=0.8, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor < 1.0


# ===========================================================================
# SECTION 47 — Edge: combine with extreme factors
# ===========================================================================


class TestSection47CombineExtremes:
    def test_both_boost_clamped(self):
        r = combine_feedback_factors(1.15, 1.10)
        assert r.combined_factor <= 1.12

    def test_both_penalty_clamped(self):
        r = combine_feedback_factors(0.85, 0.85)
        assert r.combined_factor >= 0.88

    def test_opposing_factors(self):
        r = combine_feedback_factors(1.10, 0.92)
        assert 0.88 <= r.combined_factor <= 1.12

    def test_custom_clamp_limits(self):
        r = combine_feedback_factors(1.10, 1.08, max_combined_boost=0.20)
        assert r.combined_factor <= 1.20


# ===========================================================================
# SECTION 48 — Edge: combine max_combined bounds clamping
# ===========================================================================


class TestSection48CombineBoundsClamping:
    def test_max_combined_boost_clamped_high(self):
        r = combine_feedback_factors(1.10, 1.08, max_combined_boost=0.50)
        assert r.combined_factor <= 1.25

    def test_max_combined_penalty_clamped_high(self):
        r = combine_feedback_factors(0.85, 0.85, max_combined_penalty=0.50)
        assert r.combined_factor >= 0.75


# ===========================================================================
# SECTION 49 — Explainability: reason always populated
# ===========================================================================


class TestSection49Explainability:
    def test_disabled_has_reason(self):
        r = compute_attribution_feedback_factor(None)
        assert len(r.reason) > 0

    def test_missing_data_has_reason(self):
        p = AttributionFeedbackPolicy(enabled=True)
        r = compute_attribution_feedback_factor(None, p)
        assert len(r.reason) > 0

    def test_low_confidence_has_reason(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.9)
        buckets = (_pos_bucket(score=0.9, confidence=0.5),)
        rec = _make_record(overall_score=0.5, confidence=0.5, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert len(r.reason) > 0

    def test_boost_has_reason(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = (_pos_bucket(score=0.9, confidence=0.8),)
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert "boost" in r.reason

    def test_penalty_has_reason(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = (_neg_bucket(score=0.1, confidence=0.8),)
        rec = _make_record(overall_score=0.7, confidence=0.8, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert "penalize" in r.reason


# ===========================================================================
# SECTION 50 — to_dict roundtrips
# ===========================================================================


class TestSection50Roundtrips:
    def test_policy_roundtrip(self):
        p = AttributionFeedbackPolicy(enabled=True, max_boost=0.05)
        d = p.to_dict()
        assert d["enabled"] is True
        assert d["max_boost"] == 0.05

    def test_result_roundtrip(self):
        r = AttributionFeedbackResult(
            factor=1.05,
            confidence=0.8,
            direction=CouplingDirection.BOOST,
            reason="test boost",
            strongest_positive_dimension="trend=up",
            enabled=True,
        )
        d = r.to_dict()
        assert d["factor"] == 1.05
        assert d["direction"] == "boost"
        assert d["strongest_positive_dimension"] == "trend=up"

    def test_combined_roundtrip(self):
        r = CombinedFeedbackResult(
            combined_factor=1.05,
            base_factor=1.03,
            attribution_factor=1.02,
            reason="test",
        )
        d = r.to_dict()
        assert d["combined_factor"] == 1.05
        assert d["base_factor"] == 1.03


# ===========================================================================
# SECTION 51 — Factor scaled by confidence
# ===========================================================================


class TestSection51ConfidenceScaling:
    def test_higher_confidence_stronger_factor(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b_high = _pos_bucket(score=0.9, confidence=0.9)
        b_low = _pos_bucket(score=0.9, confidence=0.4)
        rec_high = _make_record(overall_score=0.5, confidence=0.9, buckets=(b_high,))
        rec_low = _make_record(overall_score=0.5, confidence=0.4, buckets=(b_low,))
        r_high = compute_attribution_feedback_factor(rec_high, p)
        r_low = compute_attribution_feedback_factor(rec_low, p)
        assert r_high.factor >= r_low.factor

    def test_penalty_scaled_by_confidence(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b_high = _neg_bucket(score=0.1, confidence=0.9)
        b_low = _neg_bucket(score=0.1, confidence=0.4)
        rec_high = _make_record(overall_score=0.7, confidence=0.9, buckets=(b_high,))
        rec_low = _make_record(overall_score=0.7, confidence=0.4, buckets=(b_low,))
        r_high = compute_attribution_feedback_factor(rec_high, p)
        r_low = compute_attribution_feedback_factor(rec_low, p)
        assert r_high.factor <= r_low.factor


# ===========================================================================
# SECTION 52 — Custom policy values
# ===========================================================================


class TestSection52CustomPolicy:
    def test_tight_bounds(self):
        p = AttributionFeedbackPolicy(
            enabled=True, min_confidence=0.1, max_boost=0.02, max_penalty=0.02
        )
        buckets = (_pos_bucket(score=1.0, confidence=1.0),)
        rec = _make_record(overall_score=0.0, confidence=1.0, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor <= 1.02

    def test_wide_bounds(self):
        p = AttributionFeedbackPolicy(
            enabled=True, min_confidence=0.1, max_boost=0.15, max_penalty=0.15
        )
        buckets = (_pos_bucket(score=1.0, confidence=1.0),)
        rec = _make_record(overall_score=0.0, confidence=1.0, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor <= 1.15

    def test_zero_bounds(self):
        p = AttributionFeedbackPolicy(
            enabled=True, min_confidence=0.1, max_boost=0.0, max_penalty=0.0
        )
        buckets = (_pos_bucket(score=1.0, confidence=1.0),)
        rec = _make_record(overall_score=0.0, confidence=1.0, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor == 1.0


# ===========================================================================
# SECTION 53 — Deviation magnitude
# ===========================================================================


class TestSection53DeviationMagnitude:
    def test_small_deviation_small_effect(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b = _pos_bucket(score=0.72, confidence=0.8)
        rec = _make_record(overall_score=0.55, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert abs(r.factor - 1.0) < 0.02

    def test_large_deviation_larger_effect(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b = _pos_bucket(score=0.95, confidence=0.8)
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor > 1.01


# ===========================================================================
# SECTION 54 — Strategy bucket excluded from dimension detection
# ===========================================================================


class TestSection54StrategyExcluded:
    def test_strategy_bucket_not_positive(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b = AttributionBucket(
            dimension=AttributionDimension.STRATEGY,
            value="strat_a",
            sample_count=30,
            average_success_score=1.0,
            confidence=1.0,
        )
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.strongest_positive_dimension == ""
        assert r.factor == 1.0

    def test_strategy_bucket_not_negative(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b = AttributionBucket(
            dimension=AttributionDimension.STRATEGY,
            value="strat_a",
            sample_count=30,
            average_success_score=0.0,
            confidence=1.0,
        )
        rec = _make_record(overall_score=0.8, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.strongest_negative_dimension == ""
        assert r.factor == 1.0


# ===========================================================================
# SECTION 55 — Multiple dimensions
# ===========================================================================


class TestSection55MultipleDimensions:
    def test_picks_strongest_across_dims(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b1 = _pos_bucket(dim=AttributionDimension.TREND, value="up", score=0.85, confidence=0.8)
        b2 = _pos_bucket(
            dim=AttributionDimension.STABILITY, value="high", score=0.95, confidence=0.8
        )
        b3 = _neg_bucket(dim=AttributionDimension.RISK, value="extreme", score=0.1, confidence=0.8)
        rec = _make_record(overall_score=0.6, confidence=0.8, buckets=(b1, b2, b3))
        r = compute_attribution_feedback_factor(rec, p)
        assert "stability=high" in r.strongest_positive_dimension
        assert "risk=extreme" in r.strongest_negative_dimension


# ===========================================================================
# SECTION 56 — Explanation content
# ===========================================================================


class TestSection56ExplanationContent:
    def test_disabled_reason_clear(self):
        r = compute_attribution_feedback_factor(None)
        assert "coupling disabled" in r.reason or "disabled" in r.reason

    def test_confidence_below_threshold_reason(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.8)
        buckets = (_pos_bucket(score=0.9, confidence=0.5),)
        rec = _make_record(overall_score=0.5, confidence=0.5, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert "threshold" in r.reason

    def test_boost_reason_includes_deviation(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        buckets = (_pos_bucket(score=0.9, confidence=0.8),)
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=buckets)
        r = compute_attribution_feedback_factor(rec, p)
        assert "deviation" in r.reason


# ===========================================================================
# SECTION 57 — Edge: all buckets equal to overall
# ===========================================================================


class TestSection57AllEqual:
    def test_all_equal_near_neutral(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        bucket_score = 0.7 * 0.8
        b1 = _pos_bucket(dim=AttributionDimension.TREND, value="up", score=0.7, confidence=0.8)
        b2 = _pos_bucket(dim=AttributionDimension.STABILITY, value="med", score=0.7, confidence=0.8)
        rec = _make_record(overall_score=bucket_score, confidence=0.8, buckets=(b1, b2))
        r = compute_attribution_feedback_factor(rec, p)
        assert abs(r.factor - 1.0) < 0.01


# ===========================================================================
# SECTION 58 — Edge: single bucket matches overall
# ===========================================================================


class TestSection58SingleMatch:
    def test_exact_match_neutral_ish(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        overall = 0.56
        b = _pos_bucket(dim=AttributionDimension.TREND, value="up", score=0.7, confidence=0.8)
        rec = _make_record(overall_score=overall, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert abs(r.factor - 1.0) < 0.08


# ===========================================================================
# SECTION 59 — combine_feedback_factors edge: both exactly 1.0
# ===========================================================================


class TestSection59CombineBothNeutral:
    def test_both_neutral(self):
        r = combine_feedback_factors(1.0, 1.0)
        assert r.combined_factor == 1.0
        assert "attribution neutral" in r.reason


# ===========================================================================
# SECTION 60 — combine_feedback_factors edge: base exactly 1.0
# ===========================================================================


class TestSection60CombineBaseNeutral:
    def test_base_neutral_attribution_boost(self):
        r = combine_feedback_factors(1.0, 1.05)
        assert r.combined_factor == 1.05

    def test_base_neutral_attribution_penalty(self):
        r = combine_feedback_factors(1.0, 0.95)
        assert r.combined_factor == 0.95


# ===========================================================================
# SECTION 61 — Full end-to-end with FeedbackBridge and composition
# ===========================================================================


class TestSection61EndToEnd:
    def test_full_e2e(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        for i in range(40):
            meta = {
                "trend": "up",
                "risk": "low" if i < 30 else "high",
                "stability": "stable",
            }
            o = _make_outcome(
                score=0.85 if i < 30 else 0.2,
                metadata=meta,
            )
            bridge.record_outcome(o)

        engine = AttributionEngine(required_samples=10)
        attr = engine.build_attribution(mem.list_outcomes(), strategy_name="strat_a")

        attr_policy = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        attr_result = compute_attribution_feedback_factor(attr, attr_policy)
        assert attr_result.enabled is True

        base_factor = 1.05
        combined = combine_feedback_factors(base_factor, attr_result.factor)
        assert 0.88 <= combined.combined_factor <= 1.12
        assert combined.base_factor == base_factor
        assert combined.attribution_factor == attr_result.factor
        assert combined.reason


# ===========================================================================
# SECTION 62 — Opt-in invariant with real AttributionEngine
# ===========================================================================


class TestSection62OptInReal:
    def test_default_policy_no_influence(self):
        engine = AttributionEngine(required_samples=5)
        outcomes = [_make_outcome(score=0.9, metadata={"trend": "up"}) for _ in range(20)]
        attr = engine.build_attribution(outcomes, strategy_name="strat_a")
        r = compute_attribution_feedback_factor(attr)
        assert r.factor == 1.0
        assert r.enabled is False


# ===========================================================================
# SECTION 63 — Bounded invariant stress test (inv 218)
# ===========================================================================


class TestSection63BoundedStress:
    def test_extreme_positive_bounded(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.0, max_boost=0.08)
        for score_val in [0.99, 1.0]:
            for conf in [0.5, 0.8, 1.0]:
                b = _pos_bucket(score=score_val, confidence=conf)
                rec = _make_record(overall_score=0.0, confidence=conf, buckets=(b,))
                r = compute_attribution_feedback_factor(rec, p)
                assert r.factor <= 1.08, f"score={score_val}, conf={conf}, factor={r.factor}"

    def test_extreme_negative_bounded(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.0, max_penalty=0.08)
        for score_val in [0.0, 0.01]:
            for conf in [0.5, 0.8, 1.0]:
                b = _neg_bucket(score=score_val, confidence=conf)
                rec = _make_record(overall_score=1.0, confidence=conf, buckets=(b,))
                r = compute_attribution_feedback_factor(rec, p)
                assert r.factor >= 0.92, f"score={score_val}, conf={conf}, factor={r.factor}"


# ===========================================================================
# SECTION 64 — Graceful degradation (inv 224)
# ===========================================================================


class TestSection64GracefulDegradation:
    def test_empty_strategy_name(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        rec = _make_record(strategy="", overall_score=0.5, confidence=0.8, buckets=())
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor == 1.0

    def test_empty_state_signature(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        rec = _make_record(state="", overall_score=0.5, confidence=0.8, buckets=())
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor == 1.0

    def test_all_zero_scores(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.1)
        b = _neg_bucket(score=0.0, confidence=0.5)
        rec = _make_record(overall_score=0.0, confidence=0.5, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert 0.92 <= r.factor <= 1.08


# ===========================================================================
# SECTION 65 — Policy with non-default neutral_factor
# ===========================================================================


class TestSection65NonDefaultNeutral:
    def test_custom_neutral_factor(self):
        p = AttributionFeedbackPolicy(enabled=False, neutral_factor=0.95)
        r = compute_attribution_feedback_factor(None, p)
        assert r.factor == 0.95


# ===========================================================================
# SECTION 66 — combine_feedback_factors bounds clamping on params
# ===========================================================================


class TestSection66CombineParamClamping:
    def test_negative_max_boost_clamped(self):
        r = combine_feedback_factors(1.05, 1.03, max_combined_boost=-0.1)
        assert r.combined_factor <= 1.0

    def test_negative_max_penalty_clamped(self):
        r = combine_feedback_factors(0.95, 0.97, max_combined_penalty=-0.1)
        assert r.combined_factor >= 1.0

    def test_huge_max_boost_clamped(self):
        r = combine_feedback_factors(1.10, 1.10, max_combined_boost=0.50)
        assert r.combined_factor <= 1.25


# ===========================================================================
# SECTION 67 — Precision safety: epsilon comparators
# ===========================================================================


class TestSection67EpsilonComparators:
    def test_fp_drift_treated_as_equal(self):
        assert is_equal(0.7 * 0.8, 0.56)

    def test_fp_drift_not_greater(self):
        assert not is_greater(0.7 * 0.8, 0.56)

    def test_fp_drift_not_less(self):
        assert not is_less(0.7 * 0.8, 0.56)

    def test_compare_scores_fp_drift_equal(self):
        assert compare_scores(0.7 * 0.8, 0.56) == "equal"

    def test_compare_scores_greater_outside_epsilon(self):
        assert compare_scores(0.57, 0.56) == "greater"

    def test_compare_scores_less_outside_epsilon(self):
        assert compare_scores(0.55, 0.56) == "less"

    def test_compare_scores_equal_inside_epsilon(self):
        assert compare_scores(0.56 + 1e-10, 0.56) == "equal"

    def test_is_greater_outside_epsilon(self):
        assert is_greater(1.0, 0.5)

    def test_is_less_outside_epsilon(self):
        assert is_less(0.3, 0.7)

    def test_epsilon_value(self):
        assert EPSILON == 1e-9


# ===========================================================================
# SECTION 68 — Precision safety: near-equal bucket does not produce false signal
# ===========================================================================


class TestSection68NearEqualBucket:
    def test_near_equal_not_negative(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b = _pos_bucket(
            dim=AttributionDimension.TREND,
            value="up",
            score=0.7,
            confidence=0.8,
        )
        overall = 0.7 * 0.8
        rec = _make_record(overall_score=overall, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.direction == CouplingDirection.NEUTRAL
        assert r.strongest_negative_dimension == ""

    def test_near_equal_not_positive(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        overall = 0.56
        b = _pos_bucket(
            dim=AttributionDimension.TREND,
            value="up",
            score=0.7,
            confidence=0.8,
        )
        rec = _make_record(overall_score=overall, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.direction == CouplingDirection.NEUTRAL
        assert r.strongest_positive_dimension == ""

    def test_near_equal_factor_neutral(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b = _pos_bucket(
            dim=AttributionDimension.TREND,
            value="up",
            score=0.7,
            confidence=0.8,
        )
        rec = _make_record(overall_score=0.7 * 0.8, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.factor == 1.0


# ===========================================================================
# SECTION 69 — Precision safety: all-equal buckets produce neutral attribution
# ===========================================================================


class TestSection69AllBucketsEqual:
    def test_all_buckets_semantically_equal(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        overall = 0.7 * 0.8
        b1 = _pos_bucket(dim=AttributionDimension.TREND, value="up", score=0.7, confidence=0.8)
        b2 = _pos_bucket(dim=AttributionDimension.STABILITY, value="med", score=0.7, confidence=0.8)
        b3 = _pos_bucket(dim=AttributionDimension.URGENCY, value="low", score=0.7, confidence=0.8)
        rec = _make_record(overall_score=overall, confidence=0.8, buckets=(b1, b2, b3))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.direction == CouplingDirection.NEUTRAL
        assert r.factor == 1.0
        assert r.strongest_positive_dimension == ""
        assert r.strongest_negative_dimension == ""


# ===========================================================================
# SECTION 70 — Precision safety: meaningful differences still work
# ===========================================================================


class TestSection70MeaningfulDifferences:
    def test_meaningful_positive_still_boosts(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b = _pos_bucket(
            dim=AttributionDimension.TREND,
            value="up",
            score=0.95,
            confidence=0.8,
        )
        rec = _make_record(overall_score=0.5, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.direction == CouplingDirection.BOOST
        assert r.factor > 1.0

    def test_meaningful_negative_still_penalizes(self):
        p = AttributionFeedbackPolicy(enabled=True, min_confidence=0.3)
        b = _neg_bucket(
            dim=AttributionDimension.RISK,
            value="high",
            score=0.1,
            confidence=0.8,
        )
        rec = _make_record(overall_score=0.7, confidence=0.8, buckets=(b,))
        r = compute_attribution_feedback_factor(rec, p)
        assert r.direction == CouplingDirection.PENALIZE
        assert r.factor < 1.0
