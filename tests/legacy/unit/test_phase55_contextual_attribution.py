"""Phase 55 — Contextual Outcome Attribution.

Tests covering:
- Attribution data model (bucket, record, features)
- Context feature extraction
- Attribution engine (grouping, scoring, confidence)
- Global vs local attribution
- Explanation generation
- Safety invariants (211-216)
- Integration with outcome memory and feedback bridge
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.runtime.outcome import OutcomeStatus, StrategyOutcome, StrategyStats
from umh.runtime.outcome_memory import OutcomeMemory
from umh.runtime.feedback_bridge import FeedbackBridge
from umh.runtime.attribution import (
    AttributionBucket,
    AttributionDimension,
    AttributionEngine,
    ContextAttributionRecord,
    ContextFeatures,
    extract_context_features,
)


def _make_outcome(
    outcome_id: str = "o1",
    strategy_name: str = "aggressive",
    state_signature: str = "state_a",
    status: OutcomeStatus = OutcomeStatus.SUCCESS,
    success_score: float = 0.8,
    latency: float = 1.0,
    effort: float = 0.5,
    metadata: dict | None = None,
) -> StrategyOutcome:
    return StrategyOutcome(
        outcome_id=outcome_id,
        decision_id="d1",
        action_name="act",
        strategy_name=strategy_name,
        state_signature=state_signature,
        status=status,
        success_score=success_score,
        latency=latency,
        effort=effort,
        metadata=metadata or {},
    )


def _rich_outcome(
    outcome_id: str = "r1",
    strategy_name: str = "aggressive",
    state_signature: str = "state_a",
    status: OutcomeStatus = OutcomeStatus.SUCCESS,
    success_score: float = 0.8,
    trend: str = "rising",
    risk: str = "high",
    urgency: str = "medium",
    stability: str = "low",
    confidence: str = "moderate",
    objective: str = "growth",
    goal_type: str = "revenue",
) -> StrategyOutcome:
    return StrategyOutcome(
        outcome_id=outcome_id,
        decision_id="d1",
        action_name="act",
        strategy_name=strategy_name,
        state_signature=state_signature,
        status=status,
        success_score=success_score,
        latency=1.0,
        effort=0.5,
        metadata={
            "trend": trend,
            "risk": risk,
            "urgency": urgency,
            "stability": stability,
            "confidence": confidence,
            "objective": objective,
            "goal_type": goal_type,
        },
    )


# ═══════════════════════════════════════════════════════════════════════
# ATTRIBUTION DIMENSION ENUM
# ═══════════════════════════════════════════════════════════════════════


# ── Section 1: AttributionDimension enum ────────────────────────────


class TestAttributionDimensionEnum:
    def test_strategy(self):
        assert AttributionDimension.STRATEGY.value == "strategy"

    def test_state_signature(self):
        assert AttributionDimension.STATE_SIGNATURE.value == "state_signature"

    def test_trend(self):
        assert AttributionDimension.TREND.value == "trend"

    def test_risk(self):
        assert AttributionDimension.RISK.value == "risk"

    def test_urgency(self):
        assert AttributionDimension.URGENCY.value == "urgency"

    def test_stability(self):
        assert AttributionDimension.STABILITY.value == "stability"

    def test_confidence(self):
        assert AttributionDimension.CONFIDENCE.value == "confidence"

    def test_objective(self):
        assert AttributionDimension.OBJECTIVE.value == "objective"

    def test_goal_type(self):
        assert AttributionDimension.GOAL_TYPE.value == "goal_type"

    def test_nine_members(self):
        assert len(AttributionDimension) == 9


# ═══════════════════════════════════════════════════════════════════════
# ATTRIBUTION BUCKET
# ═══════════════════════════════════════════════════════════════════════


# ── Section 2: Bucket defaults ──────────────────────────────────────


class TestBucketDefaults:
    def test_default_counts_zero(self):
        b = AttributionBucket(dimension=AttributionDimension.STRATEGY, value="agg")
        assert b.sample_count == 0
        assert b.success_count == 0
        assert b.failure_count == 0
        assert b.partial_count == 0

    def test_default_averages_zero(self):
        b = AttributionBucket(dimension=AttributionDimension.STRATEGY, value="agg")
        assert b.average_success_score == 0.0
        assert b.average_latency == 0.0
        assert b.average_effort == 0.0

    def test_default_confidence_zero(self):
        b = AttributionBucket(dimension=AttributionDimension.STRATEGY, value="agg")
        assert b.confidence == 0.0

    def test_bucket_score_zero_when_empty(self):
        b = AttributionBucket(dimension=AttributionDimension.STRATEGY, value="agg")
        assert b.bucket_score == 0.0


# ── Section 3: Bucket clamping ──────────────────────────────────────


class TestBucketClamping:
    def test_negative_sample_count(self):
        b = AttributionBucket(dimension=AttributionDimension.RISK, value="high", sample_count=-5)
        assert b.sample_count == 0

    def test_score_clamped_above(self):
        b = AttributionBucket(
            dimension=AttributionDimension.RISK,
            value="high",
            average_success_score=1.5,
        )
        assert b.average_success_score == 1.0

    def test_score_clamped_below(self):
        b = AttributionBucket(
            dimension=AttributionDimension.RISK,
            value="high",
            average_success_score=-0.3,
        )
        assert b.average_success_score == 0.0

    def test_effort_clamped(self):
        b = AttributionBucket(dimension=AttributionDimension.RISK, value="high", average_effort=2.0)
        assert b.average_effort == 1.0

    def test_latency_clamped_below(self):
        b = AttributionBucket(
            dimension=AttributionDimension.RISK, value="high", average_latency=-1.0
        )
        assert b.average_latency == 0.0

    def test_confidence_clamped(self):
        b = AttributionBucket(dimension=AttributionDimension.RISK, value="high", confidence=1.5)
        assert b.confidence == 1.0


# ── Section 4: Bucket score computation ─────────────────────────────


class TestBucketScore:
    def test_score_is_product(self):
        b = AttributionBucket(
            dimension=AttributionDimension.STRATEGY,
            value="agg",
            average_success_score=0.8,
            confidence=0.5,
        )
        assert abs(b.bucket_score - 0.4) < 1e-9

    def test_full_confidence(self):
        b = AttributionBucket(
            dimension=AttributionDimension.STRATEGY,
            value="agg",
            average_success_score=0.9,
            confidence=1.0,
        )
        assert abs(b.bucket_score - 0.9) < 1e-9

    def test_zero_confidence(self):
        b = AttributionBucket(
            dimension=AttributionDimension.STRATEGY,
            value="agg",
            average_success_score=0.9,
            confidence=0.0,
        )
        assert b.bucket_score == 0.0


# ── Section 5: Bucket to_dict ───────────────────────────────────────


class TestBucketToDict:
    def test_all_keys(self):
        b = AttributionBucket(
            dimension=AttributionDimension.RISK,
            value="high",
            sample_count=10,
            success_count=7,
            failure_count=3,
            average_success_score=0.7,
            confidence=0.5,
        )
        d = b.to_dict()
        assert set(d.keys()) == {
            "dimension",
            "value",
            "sample_count",
            "success_count",
            "failure_count",
            "partial_count",
            "average_success_score",
            "average_latency",
            "average_effort",
            "confidence",
            "bucket_score",
        }

    def test_dimension_is_string(self):
        b = AttributionBucket(dimension=AttributionDimension.RISK, value="high")
        assert b.to_dict()["dimension"] == "risk"

    def test_values_rounded(self):
        b = AttributionBucket(
            dimension=AttributionDimension.RISK,
            value="high",
            average_success_score=0.123456,
            confidence=0.654321,
        )
        d = b.to_dict()
        assert d["average_success_score"] == 0.1235
        assert d["confidence"] == 0.6543


# ── Section 6: Bucket frozen ────────────────────────────────────────


class TestBucketFrozen:
    def test_immutable(self):
        b = AttributionBucket(dimension=AttributionDimension.RISK, value="high")
        with pytest.raises(AttributeError):
            b.sample_count = 5

    def test_immutable_score(self):
        b = AttributionBucket(dimension=AttributionDimension.RISK, value="high")
        with pytest.raises(AttributeError):
            b.confidence = 0.5


# ═══════════════════════════════════════════════════════════════════════
# CONTEXT ATTRIBUTION RECORD
# ═══════════════════════════════════════════════════════════════════════


# ── Section 7: Record defaults ──────────────────────────────────────


class TestRecordDefaults:
    def test_empty_buckets(self):
        r = ContextAttributionRecord(strategy_name="agg", state_signature="s1")
        assert r.dimension_buckets == ()
        assert r.overall_score == 0.0
        assert r.confidence == 0.0

    def test_explanation_default(self):
        r = ContextAttributionRecord(strategy_name="agg", state_signature="s1")
        assert r.explanation == ""


# ── Section 8: Record clamping ──────────────────────────────────────


class TestRecordClamping:
    def test_overall_score_clamped(self):
        r = ContextAttributionRecord(strategy_name="agg", state_signature="s1", overall_score=1.5)
        assert r.overall_score == 1.0

    def test_confidence_clamped(self):
        r = ContextAttributionRecord(strategy_name="agg", state_signature="s1", confidence=-0.2)
        assert r.confidence == 0.0


# ── Section 9: Record to_dict ───────────────────────────────────────


class TestRecordToDict:
    def test_all_keys(self):
        r = ContextAttributionRecord(strategy_name="agg", state_signature="s1")
        d = r.to_dict()
        assert set(d.keys()) == {
            "strategy_name",
            "state_signature",
            "dimension_buckets",
            "overall_score",
            "confidence",
            "explanation",
        }

    def test_buckets_serialized(self):
        b = AttributionBucket(dimension=AttributionDimension.RISK, value="high")
        r = ContextAttributionRecord(
            strategy_name="agg",
            state_signature="s1",
            dimension_buckets=(b,),
        )
        d = r.to_dict()
        assert len(d["dimension_buckets"]) == 1
        assert d["dimension_buckets"][0]["dimension"] == "risk"


# ── Section 10: Record frozen ───────────────────────────────────────


class TestRecordFrozen:
    def test_immutable(self):
        r = ContextAttributionRecord(strategy_name="agg", state_signature="s1")
        with pytest.raises(AttributeError):
            r.overall_score = 0.5


# ═══════════════════════════════════════════════════════════════════════
# CONTEXT FEATURES
# ═══════════════════════════════════════════════════════════════════════


# ── Section 11: ContextFeatures defaults ────────────────────────────


class TestContextFeaturesDefaults:
    def test_all_empty(self):
        f = ContextFeatures()
        assert f.strategy_name == ""
        assert f.trend == ""
        assert f.risk == ""

    def test_to_dict(self):
        f = ContextFeatures(strategy_name="agg", risk="high")
        d = f.to_dict()
        assert d["strategy_name"] == "agg"
        assert d["risk"] == "high"
        assert d["trend"] == ""


# ── Section 12: Feature extraction ──────────────────────────────────


class TestFeatureExtraction:
    def test_extracts_strategy_name(self):
        o = _make_outcome(strategy_name="conservative")
        f = extract_context_features(o)
        assert f.strategy_name == "conservative"

    def test_extracts_state_signature(self):
        o = _make_outcome(state_signature="state_x")
        f = extract_context_features(o)
        assert f.state_signature == "state_x"

    def test_extracts_trend_from_metadata(self):
        o = _make_outcome(metadata={"trend": "rising"})
        f = extract_context_features(o)
        assert f.trend == "rising"

    def test_extracts_risk_from_metadata(self):
        o = _make_outcome(metadata={"risk": "high"})
        f = extract_context_features(o)
        assert f.risk == "high"

    def test_extracts_urgency_from_metadata(self):
        o = _make_outcome(metadata={"urgency": "critical"})
        f = extract_context_features(o)
        assert f.urgency == "critical"

    def test_extracts_stability_from_metadata(self):
        o = _make_outcome(metadata={"stability": "low"})
        f = extract_context_features(o)
        assert f.stability == "low"

    def test_extracts_confidence_from_metadata(self):
        o = _make_outcome(metadata={"confidence": "moderate"})
        f = extract_context_features(o)
        assert f.confidence_level == "moderate"

    def test_extracts_objective_from_metadata(self):
        o = _make_outcome(metadata={"objective": "growth"})
        f = extract_context_features(o)
        assert f.objective == "growth"

    def test_extracts_goal_type_from_metadata(self):
        o = _make_outcome(metadata={"goal_type": "revenue"})
        f = extract_context_features(o)
        assert f.goal_type == "revenue"


# ── Section 13: Missing metadata handled ────────────────────────────


class TestMissingMetadata:
    def test_empty_metadata(self):
        o = _make_outcome(metadata={})
        f = extract_context_features(o)
        assert f.trend == ""
        assert f.risk == ""
        assert f.objective == ""

    def test_none_metadata_field(self):
        o = _make_outcome(metadata={"trend": None})
        f = extract_context_features(o)
        assert f.trend == "None"

    def test_partial_metadata(self):
        o = _make_outcome(metadata={"risk": "high"})
        f = extract_context_features(o)
        assert f.risk == "high"
        assert f.trend == ""
        assert f.stability == ""


# ── Section 14: Coarse state-only attribution ───────────────────────


class TestCoarseAttribution:
    def test_state_only_no_metadata(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", state_signature="s1") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes)
        state_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.STATE_SIGNATURE
        ]
        assert len(state_buckets) == 1
        assert state_buckets[0].value == "s1"
        assert state_buckets[0].sample_count == 5


# ═══════════════════════════════════════════════════════════════════════
# ATTRIBUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════


# ── Section 15: Engine defaults ─────────────────────────────────────


class TestEngineDefaults:
    def test_default_required_samples(self):
        e = AttributionEngine()
        assert e.required_samples == 20

    def test_custom_required_samples(self):
        e = AttributionEngine(required_samples=10)
        assert e.required_samples == 10

    def test_required_samples_floor(self):
        e = AttributionEngine(required_samples=0)
        assert e.required_samples == 1


# ── Section 16: Engine groups by strategy ───────────────────────────


class TestEngineGroupsByStrategy:
    def test_single_strategy(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes)
        strat_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.STRATEGY
        ]
        assert len(strat_buckets) == 1
        assert strat_buckets[0].value == "aggressive"

    def test_multiple_strategies(self):
        outcomes = [
            _make_outcome(outcome_id="o1", strategy_name="agg"),
            _make_outcome(outcome_id="o2", strategy_name="con"),
            _make_outcome(outcome_id="o3", strategy_name="bal"),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes)
        strat_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.STRATEGY
        ]
        assert len(strat_buckets) == 3


# ── Section 17: Engine groups by state ──────────────────────────────


class TestEngineGroupsByState:
    def test_single_state(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", state_signature="s1") for i in range(3)]
        engine = AttributionEngine(required_samples=3)
        r = engine.build_attribution(outcomes)
        state_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.STATE_SIGNATURE
        ]
        assert len(state_buckets) == 1
        assert state_buckets[0].value == "s1"

    def test_multiple_states(self):
        outcomes = [
            _make_outcome(outcome_id="o1", state_signature="s1"),
            _make_outcome(outcome_id="o2", state_signature="s2"),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes)
        state_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.STATE_SIGNATURE
        ]
        assert len(state_buckets) == 2


# ── Section 18: Engine groups by context dimensions ─────────────────


class TestEngineGroupsByContext:
    def test_groups_by_trend(self):
        outcomes = [
            _rich_outcome(outcome_id="o1", trend="rising"),
            _rich_outcome(outcome_id="o2", trend="falling"),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes)
        trend_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.TREND
        ]
        assert len(trend_buckets) == 2
        values = {b.value for b in trend_buckets}
        assert values == {"rising", "falling"}

    def test_groups_by_risk(self):
        outcomes = [
            _rich_outcome(outcome_id="o1", risk="high"),
            _rich_outcome(outcome_id="o2", risk="low"),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes)
        risk_buckets = [b for b in r.dimension_buckets if b.dimension == AttributionDimension.RISK]
        assert len(risk_buckets) == 2

    def test_groups_by_urgency(self):
        outcomes = [
            _rich_outcome(outcome_id="o1", urgency="critical"),
            _rich_outcome(outcome_id="o2", urgency="low"),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes)
        urg_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.URGENCY
        ]
        assert len(urg_buckets) == 2

    def test_groups_by_stability(self):
        outcomes = [
            _rich_outcome(outcome_id="o1", stability="stable"),
            _rich_outcome(outcome_id="o2", stability="unstable"),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes)
        stab_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.STABILITY
        ]
        assert len(stab_buckets) == 2

    def test_groups_by_confidence(self):
        outcomes = [
            _rich_outcome(outcome_id="o1", confidence="high"),
            _rich_outcome(outcome_id="o2", confidence="low"),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes)
        conf_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.CONFIDENCE
        ]
        assert len(conf_buckets) == 2

    def test_groups_by_objective(self):
        outcomes = [
            _rich_outcome(outcome_id="o1", objective="growth"),
            _rich_outcome(outcome_id="o2", objective="stability"),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes)
        obj_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.OBJECTIVE
        ]
        assert len(obj_buckets) == 2

    def test_groups_by_goal_type(self):
        outcomes = [
            _rich_outcome(outcome_id="o1", goal_type="revenue"),
            _rich_outcome(outcome_id="o2", goal_type="retention"),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes)
        gt_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.GOAL_TYPE
        ]
        assert len(gt_buckets) == 2


# ── Section 19: Bucket stats computation ────────────────────────────


class TestBucketStatsComputation:
    def test_counts_correct(self):
        outcomes = [
            _rich_outcome(outcome_id="o1", status=OutcomeStatus.SUCCESS, risk="high"),
            _rich_outcome(outcome_id="o2", status=OutcomeStatus.FAILURE, risk="high"),
            _rich_outcome(outcome_id="o3", status=OutcomeStatus.PARTIAL, risk="high"),
        ]
        engine = AttributionEngine(required_samples=3)
        r = engine.build_attribution(outcomes)
        risk_buckets = [b for b in r.dimension_buckets if b.dimension == AttributionDimension.RISK]
        assert len(risk_buckets) == 1
        b = risk_buckets[0]
        assert b.success_count == 1
        assert b.failure_count == 1
        assert b.partial_count == 1
        assert b.sample_count == 3

    def test_averages_correct(self):
        outcomes = [
            _rich_outcome(outcome_id="o1", success_score=0.6, risk="high"),
            _rich_outcome(outcome_id="o2", success_score=0.8, risk="high"),
        ]
        engine = AttributionEngine(required_samples=2)
        r = engine.build_attribution(outcomes)
        risk_buckets = [b for b in r.dimension_buckets if b.dimension == AttributionDimension.RISK]
        assert abs(risk_buckets[0].average_success_score - 0.7) < 1e-9


# ── Section 20: Confidence computation ──────────────────────────────


class TestConfidenceComputation:
    def test_full_confidence(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}") for i in range(20)]
        engine = AttributionEngine(required_samples=20)
        r = engine.build_attribution(outcomes)
        assert r.confidence == 1.0

    def test_partial_confidence(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}") for i in range(10)]
        engine = AttributionEngine(required_samples=20)
        r = engine.build_attribution(outcomes)
        assert abs(r.confidence - 0.5) < 1e-9

    def test_bucket_confidence(self):
        outcomes = [_rich_outcome(outcome_id=f"o{i}", risk="high") for i in range(10)]
        engine = AttributionEngine(required_samples=20)
        r = engine.build_attribution(outcomes)
        risk_buckets = [b for b in r.dimension_buckets if b.dimension == AttributionDimension.RISK]
        assert abs(risk_buckets[0].confidence - 0.5) < 1e-9


# ── Section 21: Empty outcomes ──────────────────────────────────────


class TestEmptyOutcomes:
    def test_no_outcomes(self):
        engine = AttributionEngine()
        r = engine.build_attribution([])
        assert r.overall_score == 0.0
        assert r.confidence == 0.0
        assert len(r.dimension_buckets) == 0

    def test_no_outcomes_explanation(self):
        engine = AttributionEngine()
        r = engine.build_attribution([])
        assert "no outcomes" in r.explanation

    def test_no_outcomes_strategy_filter(self):
        engine = AttributionEngine()
        outcomes = [_make_outcome(strategy_name="agg")]
        r = engine.build_attribution(outcomes, strategy_name="nonexistent")
        assert r.overall_score == 0.0


# ── Section 22: Sparse data degradation (inv 214) ──────────────────


class TestSparseDataDegradation:
    def test_single_outcome_low_confidence(self):
        outcomes = [_make_outcome()]
        engine = AttributionEngine(required_samples=20)
        r = engine.build_attribution(outcomes)
        assert r.confidence < 0.1

    def test_sparse_explanation(self):
        outcomes = [_make_outcome()]
        engine = AttributionEngine(required_samples=20)
        r = engine.build_attribution(outcomes)
        assert "insufficient" in r.explanation or r.confidence < 0.5

    def test_few_outcomes_conservative(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", success_score=1.0) for i in range(3)]
        engine = AttributionEngine(required_samples=20)
        r = engine.build_attribution(outcomes)
        strat_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.STRATEGY
        ]
        assert strat_buckets[0].bucket_score < 0.2


# ═══════════════════════════════════════════════════════════════════════
# GLOBAL VS LOCAL ATTRIBUTION
# ═══════════════════════════════════════════════════════════════════════


# ── Section 23: Global strategy attribution ─────────────────────────


class TestGlobalAttribution:
    def test_global_includes_all(self):
        outcomes = [
            _make_outcome(outcome_id="o1", state_signature="s1"),
            _make_outcome(outcome_id="o2", state_signature="s2"),
        ]
        engine = AttributionEngine(required_samples=2)
        r = engine.compute_global_strategy_attribution(outcomes, "aggressive")
        assert r.confidence == 1.0

    def test_global_filters_strategy(self):
        outcomes = [
            _make_outcome(outcome_id="o1", strategy_name="agg"),
            _make_outcome(outcome_id="o2", strategy_name="con"),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.compute_global_strategy_attribution(outcomes, "agg")
        strat_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.STRATEGY
        ]
        assert len(strat_buckets) == 1
        assert strat_buckets[0].value == "agg"


# ── Section 24: Context strategy attribution ────────────────────────


class TestContextAttribution:
    def test_context_filters_state(self):
        outcomes = [
            _make_outcome(outcome_id="o1", state_signature="s1", success_score=0.9),
            _make_outcome(outcome_id="o2", state_signature="s2", success_score=0.3),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.compute_context_strategy_attribution(outcomes, "aggressive", "s1")
        assert abs(r.overall_score - 0.9) < 0.01

    def test_context_different_from_global(self):
        outcomes = [
            _make_outcome(outcome_id="o1", state_signature="s1", success_score=0.9),
            _make_outcome(outcome_id="o2", state_signature="s2", success_score=0.1),
        ]
        engine = AttributionEngine(required_samples=1)
        g = engine.compute_global_strategy_attribution(outcomes, "aggressive")
        c = engine.compute_context_strategy_attribution(outcomes, "aggressive", "s1")
        assert c.overall_score > g.overall_score


# ── Section 25: Compare global vs context ───────────────────────────


class TestCompareGlobalVsContext:
    def test_comparison_returns_both(self):
        outcomes = [
            _make_outcome(outcome_id="o1", state_signature="s1", success_score=0.9),
            _make_outcome(outcome_id="o2", state_signature="s2", success_score=0.3),
        ]
        engine = AttributionEngine(required_samples=1)
        cmp = engine.compare_global_vs_context(outcomes, "aggressive", "s1")
        assert "global" in cmp
        assert "context" in cmp
        assert "score_difference" in cmp
        assert "summary" in cmp

    def test_context_outperforms(self):
        outcomes = [
            _make_outcome(outcome_id="o1", state_signature="s1", success_score=1.0),
            _make_outcome(outcome_id="o2", state_signature="s2", success_score=0.0),
        ]
        engine = AttributionEngine(required_samples=1)
        cmp = engine.compare_global_vs_context(outcomes, "aggressive", "s1")
        assert cmp["score_difference"] > 0
        assert "outperforms" in cmp["summary"]

    def test_context_underperforms(self):
        outcomes = [
            _make_outcome(outcome_id="o1", state_signature="s1", success_score=0.0),
            _make_outcome(outcome_id="o2", state_signature="s2", success_score=1.0),
        ]
        engine = AttributionEngine(required_samples=1)
        cmp = engine.compare_global_vs_context(outcomes, "aggressive", "s1")
        assert cmp["score_difference"] < 0
        assert "underperforms" in cmp["summary"]

    def test_context_matches(self):
        outcomes = [
            _make_outcome(outcome_id="o1", state_signature="s1", success_score=0.5),
            _make_outcome(outcome_id="o2", state_signature="s2", success_score=0.5),
        ]
        engine = AttributionEngine(required_samples=1)
        cmp = engine.compare_global_vs_context(outcomes, "aggressive", "s1")
        assert "matches" in cmp["summary"]


# ═══════════════════════════════════════════════════════════════════════
# EXPLANATION GENERATION
# ═══════════════════════════════════════════════════════════════════════


# ── Section 26: Explanation content ─────────────────────────────────


class TestExplanationContent:
    def test_includes_strategy_name(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes)
        assert "aggressive" in r.explanation

    def test_includes_outcome_count(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}") for i in range(7)]
        engine = AttributionEngine(required_samples=7)
        r = engine.build_attribution(outcomes)
        assert "7 outcomes" in r.explanation

    def test_includes_confidence(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes)
        assert "confidence" in r.explanation

    def test_includes_overall_score(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes)
        assert "overall_score" in r.explanation


# ── Section 27: Explanation strongest/weakest ───────────────────────


class TestExplanationStrengthWeakness:
    def test_strongest_identified(self):
        outcomes = [
            _rich_outcome(outcome_id="o1", risk="high", success_score=0.9),
            _rich_outcome(outcome_id="o2", risk="low", success_score=0.2),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes)
        assert "strongest" in r.explanation

    def test_weakest_identified(self):
        outcomes = [
            _rich_outcome(outcome_id="o1", risk="high", success_score=0.9),
            _rich_outcome(outcome_id="o2", risk="low", success_score=0.2),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes)
        assert "weakest" in r.explanation


# ── Section 28: Explanation sparse data ─────────────────────────────


class TestExplanationSparseData:
    def test_insufficient_data_noted(self):
        outcomes = [_make_outcome()]
        engine = AttributionEngine(required_samples=100)
        r = engine.build_attribution(outcomes)
        assert "insufficient" in r.explanation

    def test_no_outcomes_noted(self):
        engine = AttributionEngine()
        r = engine.build_attribution([])
        assert "no outcomes" in r.explanation


# ═══════════════════════════════════════════════════════════════════════
# SAFETY INVARIANTS
# ═══════════════════════════════════════════════════════════════════════


# ── Section 29: Attribution derived from outcomes only (inv 211) ────


class TestDerivedFromOutcomesOnly:
    def test_no_external_data(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", success_score=0.7) for i in range(10)]
        engine = AttributionEngine(required_samples=10)
        r = engine.build_attribution(outcomes)
        assert r.overall_score > 0
        assert r.confidence > 0

    def test_same_outcomes_same_result(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", success_score=0.7) for i in range(10)]
        engine = AttributionEngine(required_samples=10)
        r1 = engine.build_attribution(outcomes)
        r2 = engine.build_attribution(outcomes)
        assert r1.overall_score == r2.overall_score
        assert r1.confidence == r2.confidence


# ── Section 30: No mutation of outcomes (inv 212) ───────────────────


class TestNoOutcomeMutation:
    def test_outcomes_unchanged_after_attribution(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", success_score=0.7) for i in range(5)]
        scores_before = [o.success_score for o in outcomes]
        engine = AttributionEngine()
        engine.build_attribution(outcomes)
        scores_after = [o.success_score for o in outcomes]
        assert scores_before == scores_after

    def test_list_unchanged(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}") for i in range(5)]
        count_before = len(outcomes)
        engine = AttributionEngine()
        engine.build_attribution(outcomes)
        assert len(outcomes) == count_before


# ── Section 31: Deterministic (inv 213) ─────────────────────────────


class TestDeterministic:
    def test_same_input_same_output(self):
        outcomes = [
            _rich_outcome(outcome_id=f"o{i}", risk="high", success_score=0.7) for i in range(10)
        ]
        engine = AttributionEngine(required_samples=10)
        r1 = engine.build_attribution(outcomes)
        r2 = engine.build_attribution(outcomes)
        assert r1.to_dict() == r2.to_dict()

    def test_deterministic_buckets(self):
        outcomes = [
            _rich_outcome(outcome_id="o1", risk="high", success_score=0.9),
            _rich_outcome(outcome_id="o2", risk="low", success_score=0.3),
        ]
        engine = AttributionEngine(required_samples=1)
        r1 = engine.build_attribution(outcomes)
        r2 = engine.build_attribution(outcomes)
        for b1, b2 in zip(r1.dimension_buckets, r2.dimension_buckets):
            assert b1.to_dict() == b2.to_dict()


# ── Section 32: Graceful degradation (inv 214) ─────────────────────


class TestGracefulDegradation:
    def test_empty_list(self):
        engine = AttributionEngine()
        r = engine.build_attribution([])
        assert r is not None
        assert r.overall_score == 0.0

    def test_no_metadata(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes)
        trend_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.TREND
        ]
        assert len(trend_buckets) == 0

    def test_mixed_metadata(self):
        outcomes = [
            _make_outcome(outcome_id="o1", metadata={"risk": "high"}),
            _make_outcome(outcome_id="o2"),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes)
        risk_buckets = [b for b in r.dimension_buckets if b.dimension == AttributionDimension.RISK]
        assert len(risk_buckets) == 1
        assert risk_buckets[0].sample_count == 1


# ── Section 33: No execution (inv 215) ──────────────────────────────


class TestNoExecution:
    def test_no_subprocess_import(self):
        import umh.runtime.attribution as mod

        source = open(mod.__file__).read()
        assert "import subprocess" not in source

    def test_no_os_import(self):
        import umh.runtime.attribution as mod

        source = open(mod.__file__).read()
        assert "import os" not in source

    def test_no_cells_import(self):
        import umh.runtime.attribution as mod

        source = open(mod.__file__).read()
        assert "umh.cells" not in source

    def test_no_docker_import(self):
        import umh.runtime.attribution as mod

        source = open(mod.__file__).read()
        assert "docker" not in source


# ── Section 34: Observational by default (inv 216) ──────────────────


class TestObservationalByDefault:
    def test_engine_has_no_mutate_method(self):
        engine = AttributionEngine()
        assert not hasattr(engine, "apply")
        assert not hasattr(engine, "execute")
        assert not hasattr(engine, "modify")
        assert not hasattr(engine, "set_score")

    def test_record_is_frozen(self):
        r = ContextAttributionRecord(strategy_name="agg", state_signature="s1")
        with pytest.raises(AttributeError):
            r.overall_score = 0.5

    def test_bucket_is_frozen(self):
        b = AttributionBucket(dimension=AttributionDimension.RISK, value="high")
        with pytest.raises(AttributeError):
            b.sample_count = 5


# ═══════════════════════════════════════════════════════════════════════
# FILTERING
# ═══════════════════════════════════════════════════════════════════════


# ── Section 35: Strategy filter ─────────────────────────────────────


class TestStrategyFilter:
    def test_filters_by_strategy(self):
        outcomes = [
            _make_outcome(outcome_id="o1", strategy_name="agg", success_score=0.9),
            _make_outcome(outcome_id="o2", strategy_name="con", success_score=0.3),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes, strategy_name="agg")
        assert abs(r.overall_score - 0.9) < 0.01

    def test_filter_removes_others(self):
        outcomes = [
            _make_outcome(outcome_id="o1", strategy_name="agg"),
            _make_outcome(outcome_id="o2", strategy_name="con"),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes, strategy_name="agg")
        strat_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.STRATEGY
        ]
        assert all(b.value == "agg" for b in strat_buckets)


# ── Section 36: State filter ───────────────────────────────────────


class TestStateFilter:
    def test_filters_by_state(self):
        outcomes = [
            _make_outcome(outcome_id="o1", state_signature="s1", success_score=0.9),
            _make_outcome(outcome_id="o2", state_signature="s2", success_score=0.1),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes, state_signature="s1")
        assert abs(r.overall_score - 0.9) < 0.01


# ── Section 37: Combined filter ────────────────────────────────────


class TestCombinedFilter:
    def test_strategy_and_state(self):
        outcomes = [
            _make_outcome(
                outcome_id="o1", strategy_name="agg", state_signature="s1", success_score=1.0
            ),
            _make_outcome(
                outcome_id="o2", strategy_name="agg", state_signature="s2", success_score=0.0
            ),
            _make_outcome(
                outcome_id="o3", strategy_name="con", state_signature="s1", success_score=0.5
            ),
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes, strategy_name="agg", state_signature="s1")
        assert abs(r.overall_score - 1.0) < 0.01


# ═══════════════════════════════════════════════════════════════════════
# IMPORT SURFACE
# ═══════════════════════════════════════════════════════════════════════


# ── Section 38: All importable from umh.runtime ─────────────────────


class TestImportSurface:
    def test_all_importable(self):
        from umh.runtime import (
            AttributionBucket,
            AttributionDimension,
            AttributionEngine,
            ContextAttributionRecord,
            ContextFeatures,
            extract_context_features,
        )

        assert AttributionBucket is not None
        assert AttributionDimension is not None
        assert AttributionEngine is not None
        assert ContextAttributionRecord is not None
        assert ContextFeatures is not None
        assert extract_context_features is not None


# ═══════════════════════════════════════════════════════════════════════
# INTEGRATION
# ═══════════════════════════════════════════════════════════════════════


# ── Section 39: With outcome memory ─────────────────────────────────


class TestWithOutcomeMemory:
    def test_attribution_from_memory(self):
        mem = OutcomeMemory()
        for i in range(10):
            mem.append(
                _rich_outcome(
                    outcome_id=f"o{i}",
                    risk="high" if i < 5 else "low",
                    success_score=0.9 if i < 5 else 0.3,
                )
            )
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(mem.list_outcomes())
        risk_buckets = [b for b in r.dimension_buckets if b.dimension == AttributionDimension.RISK]
        high_risk = [b for b in risk_buckets if b.value == "high"][0]
        low_risk = [b for b in risk_buckets if b.value == "low"][0]
        assert high_risk.average_success_score > low_risk.average_success_score


# ── Section 40: With feedback bridge ────────────────────────────────


class TestWithFeedbackBridge:
    def test_bridge_default_unchanged(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        o = _make_outcome()
        record = bridge.record_outcome(o, objective_id="obj1")
        assert record.link is not None
        assert record.strategy_stats is not None

    def test_attribution_after_bridge(self):
        mem = OutcomeMemory()
        bridge = FeedbackBridge(mem)
        for i in range(5):
            bridge.record_outcome(
                _rich_outcome(outcome_id=f"o{i}", risk="high", success_score=0.8),
                objective_id="obj1",
            )
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(mem.list_outcomes())
        assert r.confidence == 1.0


# ═══════════════════════════════════════════════════════════════════════
# EDGE CASES
# ═══════════════════════════════════════════════════════════════════════


# ── Section 41: All same dimension values ───────────────────────────


class TestAllSameDimensionValues:
    def test_single_risk_value(self):
        outcomes = [_rich_outcome(outcome_id=f"o{i}", risk="high") for i in range(10)]
        engine = AttributionEngine(required_samples=10)
        r = engine.build_attribution(outcomes)
        risk_buckets = [b for b in r.dimension_buckets if b.dimension == AttributionDimension.RISK]
        assert len(risk_buckets) == 1
        assert risk_buckets[0].confidence == 1.0


# ── Section 42: Many dimension values ──────────────────────────────


class TestManyDimensionValues:
    def test_many_unique_states(self):
        outcomes = [
            _make_outcome(outcome_id=f"o{i}", state_signature=f"state_{i}") for i in range(20)
        ]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes)
        state_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.STATE_SIGNATURE
        ]
        assert len(state_buckets) == 20


# ── Section 43: Mixed statuses ──────────────────────────────────────


class TestMixedStatuses:
    def test_all_status_types(self):
        outcomes = [
            _make_outcome(outcome_id="o1", status=OutcomeStatus.SUCCESS),
            _make_outcome(outcome_id="o2", status=OutcomeStatus.FAILURE),
            _make_outcome(outcome_id="o3", status=OutcomeStatus.PARTIAL),
            _make_outcome(outcome_id="o4", status=OutcomeStatus.UNKNOWN),
        ]
        engine = AttributionEngine(required_samples=4)
        r = engine.build_attribution(outcomes)
        strat_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.STRATEGY
        ]
        assert strat_buckets[0].success_count == 1
        assert strat_buckets[0].failure_count == 1
        assert strat_buckets[0].partial_count == 1


# ── Section 44: Overall score accuracy ──────────────────────────────


class TestOverallScoreAccuracy:
    def test_overall_is_mean(self):
        outcomes = [
            _make_outcome(outcome_id="o1", success_score=0.6),
            _make_outcome(outcome_id="o2", success_score=0.8),
            _make_outcome(outcome_id="o3", success_score=1.0),
        ]
        engine = AttributionEngine(required_samples=3)
        r = engine.build_attribution(outcomes)
        assert abs(r.overall_score - 0.8) < 1e-9

    def test_single_outcome(self):
        outcomes = [_make_outcome(success_score=0.65)]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes)
        assert abs(r.overall_score - 0.65) < 1e-9


# ── Section 45: No metadata dimensions are empty ───────────────────


class TestNoMetadataEmpty:
    def test_no_trend_bucket(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes)
        trend_buckets = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.TREND
        ]
        assert len(trend_buckets) == 0

    def test_no_risk_bucket(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes)
        risk_buckets = [b for b in r.dimension_buckets if b.dimension == AttributionDimension.RISK]
        assert len(risk_buckets) == 0

    def test_strategy_and_state_always_present(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes)
        strat = [b for b in r.dimension_buckets if b.dimension == AttributionDimension.STRATEGY]
        state = [
            b for b in r.dimension_buckets if b.dimension == AttributionDimension.STATE_SIGNATURE
        ]
        assert len(strat) >= 1
        assert len(state) >= 1


# ── Section 46: ContextFeatures frozen ──────────────────────────────


class TestContextFeaturesFrozen:
    def test_immutable(self):
        f = ContextFeatures(strategy_name="agg")
        with pytest.raises(AttributeError):
            f.strategy_name = "con"


# ── Section 47: Record with buckets serialization ───────────────────


class TestRecordBucketsSerialization:
    def test_multiple_buckets(self):
        buckets = tuple(
            AttributionBucket(
                dimension=AttributionDimension.RISK,
                value=f"level_{i}",
                sample_count=i + 1,
            )
            for i in range(5)
        )
        r = ContextAttributionRecord(
            strategy_name="agg",
            state_signature="s1",
            dimension_buckets=buckets,
            overall_score=0.7,
            confidence=0.8,
        )
        d = r.to_dict()
        assert len(d["dimension_buckets"]) == 5
        assert d["dimension_buckets"][0]["sample_count"] == 1
        assert d["dimension_buckets"][4]["sample_count"] == 5


# ── Section 48: Large outcome set ───────────────────────────────────


class TestLargeOutcomeSet:
    def test_hundred_outcomes(self):
        outcomes = [
            _rich_outcome(
                outcome_id=f"o{i}",
                risk="high" if i % 3 == 0 else "low",
                trend="rising" if i % 2 == 0 else "falling",
                success_score=(i % 10) / 10.0,
            )
            for i in range(100)
        ]
        engine = AttributionEngine(required_samples=20)
        r = engine.build_attribution(outcomes)
        assert r.confidence == 1.0
        assert len(r.dimension_buckets) > 10

    def test_large_set_deterministic(self):
        outcomes = [
            _rich_outcome(
                outcome_id=f"o{i}",
                risk="high" if i % 2 == 0 else "low",
                success_score=0.5 + (i % 5) * 0.1,
            )
            for i in range(50)
        ]
        engine = AttributionEngine(required_samples=20)
        r1 = engine.build_attribution(outcomes)
        r2 = engine.build_attribution(outcomes)
        assert r1.overall_score == r2.overall_score
        assert len(r1.dimension_buckets) == len(r2.dimension_buckets)


# ── Section 49: Strategy name in record ─────────────────────────────


class TestStrategyNameInRecord:
    def test_from_filter(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", strategy_name="agg") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes, strategy_name="agg")
        assert r.strategy_name == "agg"

    def test_from_first_outcome(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", strategy_name="agg") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes)
        assert r.strategy_name == "agg"

    def test_empty_when_no_outcomes(self):
        engine = AttributionEngine()
        r = engine.build_attribution([], strategy_name="nonexistent")
        assert r.strategy_name == "nonexistent"


# ── Section 50: State signature in record ───────────────────────────


class TestStateSignatureInRecord:
    def test_from_filter(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", state_signature="s1") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes, state_signature="s1")
        assert r.state_signature == "s1"

    def test_from_first_outcome(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", state_signature="s1") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes)
        assert r.state_signature == "s1"


# ═══════════════════════════════════════════════════════════════════════
# CROSS-DIMENSION ANALYSIS
# ═══════════════════════════════════════════════════════════════════════


# ── Section 51: Multi-dimension rich outcomes ───────────────────────


class TestMultiDimensionRich:
    def test_all_dimensions_populated(self):
        outcomes = [_rich_outcome(outcome_id=f"o{i}") for i in range(10)]
        engine = AttributionEngine(required_samples=10)
        r = engine.build_attribution(outcomes)
        dims_present = {b.dimension for b in r.dimension_buckets}
        assert AttributionDimension.STRATEGY in dims_present
        assert AttributionDimension.STATE_SIGNATURE in dims_present
        assert AttributionDimension.TREND in dims_present
        assert AttributionDimension.RISK in dims_present
        assert AttributionDimension.URGENCY in dims_present
        assert AttributionDimension.STABILITY in dims_present
        assert AttributionDimension.CONFIDENCE in dims_present
        assert AttributionDimension.OBJECTIVE in dims_present
        assert AttributionDimension.GOAL_TYPE in dims_present

    def test_different_strategies_different_risk(self):
        outcomes = [
            _rich_outcome(outcome_id="o1", strategy_name="agg", risk="high", success_score=0.9),
            _rich_outcome(outcome_id="o2", strategy_name="agg", risk="high", success_score=0.8),
            _rich_outcome(outcome_id="o3", strategy_name="con", risk="low", success_score=0.3),
            _rich_outcome(outcome_id="o4", strategy_name="con", risk="low", success_score=0.2),
        ]
        engine = AttributionEngine(required_samples=2)
        r_agg = engine.build_attribution(outcomes, strategy_name="agg")
        r_con = engine.build_attribution(outcomes, strategy_name="con")
        assert r_agg.overall_score > r_con.overall_score


# ── Section 52: Explanation with context filter ─────────────────────


class TestExplanationWithContext:
    def test_context_in_explanation(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", state_signature="state_x") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes, state_signature="state_x")
        assert "state_x" in r.explanation

    def test_no_context_omits_state(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes)
        assert "context=" not in r.explanation


# ── Section 53: Bucket score sweep ──────────────────────────────────


class TestBucketScoreSweep:
    def test_score_increases_with_confidence(self):
        scores = []
        for n in [1, 5, 10, 20]:
            outcomes = [
                _rich_outcome(outcome_id=f"o{i}", risk="high", success_score=0.8) for i in range(n)
            ]
            engine = AttributionEngine(required_samples=20)
            r = engine.build_attribution(outcomes)
            risk_buckets = [
                b for b in r.dimension_buckets if b.dimension == AttributionDimension.RISK
            ]
            if risk_buckets:
                scores.append(risk_buckets[0].bucket_score)
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i - 1]


# ── Section 54: Compare with identical data ─────────────────────────


class TestCompareIdentical:
    def test_identical_global_local(self):
        outcomes = [
            _make_outcome(outcome_id=f"o{i}", state_signature="s1", success_score=0.7)
            for i in range(10)
        ]
        engine = AttributionEngine(required_samples=10)
        cmp = engine.compare_global_vs_context(outcomes, "aggressive", "s1")
        assert abs(cmp["score_difference"]) < 0.01
        assert "matches" in cmp["summary"]


# ── Section 55: Bucket to_dict roundtrip ────────────────────────────


class TestBucketDictRoundtrip:
    def test_populated_bucket(self):
        b = AttributionBucket(
            dimension=AttributionDimension.URGENCY,
            value="critical",
            sample_count=15,
            success_count=10,
            failure_count=3,
            partial_count=2,
            average_success_score=0.75,
            average_latency=2.5,
            average_effort=0.4,
            confidence=0.75,
        )
        d = b.to_dict()
        assert d["value"] == "critical"
        assert d["sample_count"] == 15
        assert d["success_count"] == 10
        assert d["failure_count"] == 3
        assert d["partial_count"] == 2

    def test_bucket_score_in_dict(self):
        b = AttributionBucket(
            dimension=AttributionDimension.RISK,
            value="low",
            average_success_score=0.6,
            confidence=0.8,
        )
        d = b.to_dict()
        assert abs(d["bucket_score"] - 0.48) < 0.001


# ── Section 56: Feature extraction edge cases ───────────────────────


class TestFeatureExtractionEdge:
    def test_numeric_metadata_coerced(self):
        o = _make_outcome(metadata={"risk": 42})
        f = extract_context_features(o)
        assert f.risk == "42"

    def test_bool_metadata_coerced(self):
        o = _make_outcome(metadata={"stability": True})
        f = extract_context_features(o)
        assert f.stability == "True"

    def test_list_metadata_coerced(self):
        o = _make_outcome(metadata={"trend": [1, 2, 3]})
        f = extract_context_features(o)
        assert f.trend == "[1, 2, 3]"


# ── Section 57: Engine with zero-score outcomes ─────────────────────


class TestZeroScoreOutcomes:
    def test_all_zero_scores(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", success_score=0.0) for i in range(10)]
        engine = AttributionEngine(required_samples=10)
        r = engine.build_attribution(outcomes)
        assert r.overall_score == 0.0
        assert r.confidence == 1.0

    def test_zero_score_bucket(self):
        outcomes = [
            _rich_outcome(outcome_id=f"o{i}", risk="high", success_score=0.0) for i in range(10)
        ]
        engine = AttributionEngine(required_samples=10)
        r = engine.build_attribution(outcomes)
        risk_b = [b for b in r.dimension_buckets if b.dimension == AttributionDimension.RISK]
        assert risk_b[0].bucket_score == 0.0


# ── Section 58: Engine with perfect scores ──────────────────────────


class TestPerfectScoreOutcomes:
    def test_all_perfect(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", success_score=1.0) for i in range(20)]
        engine = AttributionEngine(required_samples=20)
        r = engine.build_attribution(outcomes)
        assert r.overall_score == 1.0
        assert r.confidence == 1.0

    def test_perfect_bucket_score(self):
        outcomes = [
            _rich_outcome(outcome_id=f"o{i}", risk="low", success_score=1.0) for i in range(20)
        ]
        engine = AttributionEngine(required_samples=20)
        r = engine.build_attribution(outcomes)
        risk_b = [b for b in r.dimension_buckets if b.dimension == AttributionDimension.RISK]
        assert abs(risk_b[0].bucket_score - 1.0) < 1e-9


# ── Section 59: Compare global vs context empty ─────────────────────


class TestCompareGlobalVsContextEmpty:
    def test_nonexistent_strategy(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        cmp = engine.compare_global_vs_context(outcomes, "nonexistent", "s1")
        assert cmp["global"]["overall_score"] == 0.0
        assert cmp["context"]["overall_score"] == 0.0

    def test_nonexistent_state(self):
        outcomes = [_make_outcome(outcome_id=f"o{i}", state_signature="s1") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        cmp = engine.compare_global_vs_context(outcomes, "aggressive", "nonexistent")
        assert cmp["context"]["overall_score"] == 0.0
        assert cmp["global"]["overall_score"] > 0


# ── Section 60: Attribution explanation formatting ──────────────────


class TestExplanationFormatting:
    def test_no_crash_on_single_bucket(self):
        outcomes = [_rich_outcome(outcome_id="o1")]
        engine = AttributionEngine(required_samples=1)
        r = engine.build_attribution(outcomes)
        assert isinstance(r.explanation, str)
        assert len(r.explanation) > 0

    def test_explanation_does_not_repeat_strongest_weakest(self):
        outcomes = [_rich_outcome(outcome_id=f"o{i}") for i in range(5)]
        engine = AttributionEngine(required_samples=5)
        r = engine.build_attribution(outcomes)
        if r.explanation.count("strongest") > 0:
            assert r.explanation.count("strongest") == 1
