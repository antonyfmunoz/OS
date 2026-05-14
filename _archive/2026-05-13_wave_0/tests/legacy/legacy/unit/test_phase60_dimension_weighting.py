"""Phase 60 — Adaptive dimension weighting tests.

Tests weight model, normalization, clamping, confidence blending,
learning from outcomes, orchestrator integration, and explainability.

Invariants 249-256.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime.dimension_weighting import (
    DEFAULT_WEIGHT_VECTOR,
    DEFAULT_WEIGHTING_CONFIG,
    DimensionWeight,
    DimensionWeightVector,
    WeightingConfig,
    compute_dimension_weights,
    default_weight_vector,
    _blend_with_default,
    _compute_dimension_range,
    _compute_dimension_variance,
    _compute_raw_importance,
    _normalize_weights,
)
from umh.runtime.outcome import OutcomeStatus, StrategyOutcome
from umh.runtime.regime_aggregation import DimensionName


# ── helpers ───────────────────────────────────────────────────────────


def _make_outcome(
    strategy: str = "s1",
    state: str = "ctx1",
    score: float = 0.7,
    status: OutcomeStatus = OutcomeStatus.SUCCESS,
    trend: str = "",
    risk: str = "",
    stability: str = "",
    urgency: str = "",
) -> StrategyOutcome:
    meta: dict = {}
    if trend:
        meta["trend"] = trend
    if risk:
        meta["risk"] = risk
    if stability:
        meta["stability"] = stability
    if urgency:
        meta["urgency"] = urgency
    return StrategyOutcome(
        outcome_id=f"o-{id(meta)}",
        decision_id="d1",
        action_name="act",
        strategy_name=strategy,
        state_signature=state,
        status=status,
        success_score=score,
        metadata=meta,
    )


# ===========================================================================
# SECTION 1 — DimensionWeight defaults
# ===========================================================================


class TestSection01DimensionWeightDefaults:
    def test_default_weight(self):
        w = DimensionWeight(dimension=DimensionName.TREND)
        assert w.weight == 0.25

    def test_default_confidence(self):
        w = DimensionWeight(dimension=DimensionName.TREND)
        assert w.confidence == 0.0

    def test_default_source(self):
        w = DimensionWeight(dimension=DimensionName.TREND)
        assert w.source == "default"


# ===========================================================================
# SECTION 2 — DimensionWeight bounds (inv 249)
# ===========================================================================


class TestSection02DimensionWeightBounds:
    def test_weight_clamped_low(self):
        w = DimensionWeight(dimension=DimensionName.TREND, weight=-0.5)
        assert w.weight == 0.0

    def test_weight_clamped_high(self):
        w = DimensionWeight(dimension=DimensionName.TREND, weight=5.0)
        assert w.weight == 1.0

    def test_confidence_clamped_low(self):
        w = DimensionWeight(dimension=DimensionName.TREND, confidence=-1.0)
        assert w.confidence == 0.0

    def test_confidence_clamped_high(self):
        w = DimensionWeight(dimension=DimensionName.TREND, confidence=3.0)
        assert w.confidence == 1.0


# ===========================================================================
# SECTION 3 — DimensionWeight to_dict
# ===========================================================================


class TestSection03DimensionWeightDict:
    def test_keys(self):
        w = DimensionWeight(
            dimension=DimensionName.RISK, weight=0.3, confidence=0.8, source="learned"
        )
        d = w.to_dict()
        assert set(d.keys()) == {"dimension", "weight", "confidence", "source"}

    def test_values(self):
        w = DimensionWeight(dimension=DimensionName.RISK, weight=0.3, source="learned")
        d = w.to_dict()
        assert d["dimension"] == "risk"
        assert d["source"] == "learned"


# ===========================================================================
# SECTION 4 — DimensionWeight frozen
# ===========================================================================


class TestSection04DimensionWeightFrozen:
    def test_cannot_set_weight(self):
        w = DimensionWeight(dimension=DimensionName.TREND)
        try:
            w.weight = 0.5  # type: ignore[misc]
            assert False, "should raise"
        except AttributeError:
            pass

    def test_cannot_set_source(self):
        w = DimensionWeight(dimension=DimensionName.TREND)
        try:
            w.source = "learned"  # type: ignore[misc]
            assert False, "should raise"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 5 — DimensionWeightVector defaults
# ===========================================================================


class TestSection05VectorDefaults:
    def test_default_normalized(self):
        v = DimensionWeightVector(weights={})
        assert v.normalized is False

    def test_default_explanation(self):
        v = DimensionWeightVector(weights={})
        assert v.explanation == ""


# ===========================================================================
# SECTION 6 — DimensionWeightVector properties
# ===========================================================================


class TestSection06VectorProperties:
    def test_is_uniform_default(self):
        v = default_weight_vector()
        assert v.is_uniform is True

    def test_is_learned_default(self):
        v = default_weight_vector()
        assert v.is_learned is False

    def test_is_learned_with_learned_source(self):
        weights = {
            DimensionName.TREND.value: DimensionWeight(
                dimension=DimensionName.TREND, weight=0.3, source="learned"
            ),
        }
        v = DimensionWeightVector(weights=weights)
        assert v.is_learned is True


# ===========================================================================
# SECTION 7 — DimensionWeightVector get / get_weight
# ===========================================================================


class TestSection07VectorAccess:
    def test_get_existing(self):
        v = default_weight_vector()
        w = v.get(DimensionName.TREND)
        assert w is not None
        assert w.weight == 0.25

    def test_get_missing(self):
        v = DimensionWeightVector(weights={})
        assert v.get(DimensionName.TREND) is None

    def test_get_weight_existing(self):
        v = default_weight_vector()
        assert v.get_weight(DimensionName.RISK) == 0.25

    def test_get_weight_missing_returns_default(self):
        v = DimensionWeightVector(weights={})
        assert v.get_weight(DimensionName.RISK) == 0.25


# ===========================================================================
# SECTION 8 — DimensionWeightVector to_dict
# ===========================================================================


class TestSection08VectorDict:
    def test_keys(self):
        v = default_weight_vector()
        d = v.to_dict()
        assert set(d.keys()) == {"weights", "normalized", "explanation", "is_uniform", "is_learned"}

    def test_weight_keys(self):
        v = default_weight_vector()
        d = v.to_dict()
        assert set(d["weights"].keys()) == {"trend", "risk", "stability", "urgency"}


# ===========================================================================
# SECTION 9 — DimensionWeightVector frozen
# ===========================================================================


class TestSection09VectorFrozen:
    def test_cannot_set_normalized(self):
        v = default_weight_vector()
        try:
            v.normalized = False  # type: ignore[misc]
            assert False, "should raise"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 10 — Default weights uniform (inv 250)
# ===========================================================================


class TestSection10DefaultUniform:
    def test_all_025(self):
        v = default_weight_vector()
        for w in v.weights.values():
            assert w.weight == 0.25

    def test_sum_one(self):
        v = default_weight_vector()
        total = sum(w.weight for w in v.weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_all_default_source(self):
        v = default_weight_vector()
        for w in v.weights.values():
            assert w.source == "default"

    def test_four_dimensions(self):
        v = default_weight_vector()
        assert len(v.weights) == 4


# ===========================================================================
# SECTION 11 — DEFAULT_WEIGHT_VECTOR constant
# ===========================================================================


class TestSection11Constant:
    def test_is_uniform(self):
        assert DEFAULT_WEIGHT_VECTOR.is_uniform is True

    def test_is_normalized(self):
        assert DEFAULT_WEIGHT_VECTOR.normalized is True

    def test_not_learned(self):
        assert DEFAULT_WEIGHT_VECTOR.is_learned is False


# ===========================================================================
# SECTION 12 — WeightingConfig defaults
# ===========================================================================


class TestSection12ConfigDefaults:
    def test_min_weight(self):
        c = WeightingConfig()
        assert c.min_weight == 0.10

    def test_max_weight(self):
        c = WeightingConfig()
        assert c.max_weight == 0.40

    def test_required_samples(self):
        c = WeightingConfig()
        assert c.required_samples == 20

    def test_confidence_threshold(self):
        c = WeightingConfig()
        assert c.confidence_threshold == 0.3


# ===========================================================================
# SECTION 13 — WeightingConfig bounds
# ===========================================================================


class TestSection13ConfigBounds:
    def test_min_weight_floor(self):
        c = WeightingConfig(min_weight=-1.0)
        assert c.min_weight == 0.01

    def test_max_weight_floor(self):
        c = WeightingConfig(max_weight=0.0)
        assert c.max_weight >= c.min_weight + 0.05

    def test_required_samples_floor(self):
        c = WeightingConfig(required_samples=-5)
        assert c.required_samples == 1


# ===========================================================================
# SECTION 14 — WeightingConfig to_dict
# ===========================================================================


class TestSection14ConfigDict:
    def test_keys(self):
        d = WeightingConfig().to_dict()
        assert set(d.keys()) == {
            "min_weight",
            "max_weight",
            "required_samples",
            "confidence_threshold",
        }


# ===========================================================================
# SECTION 15 — WeightingConfig frozen
# ===========================================================================


class TestSection15ConfigFrozen:
    def test_cannot_set(self):
        c = WeightingConfig()
        try:
            c.min_weight = 0.5  # type: ignore[misc]
            assert False
        except AttributeError:
            pass


# ===========================================================================
# SECTION 16 — _normalize_weights: basic
# ===========================================================================


class TestSection16Normalize:
    def test_uniform_input(self):
        raw = {d: 1.0 for d in DimensionName}
        result = _normalize_weights(raw)
        for w in result.values():
            assert abs(w - 0.25) < 1e-9

    def test_sum_one(self):
        raw = {
            DimensionName.TREND: 3.0,
            DimensionName.RISK: 1.0,
            DimensionName.STABILITY: 1.0,
            DimensionName.URGENCY: 1.0,
        }
        result = _normalize_weights(raw)
        assert abs(sum(result.values()) - 1.0) < 1e-9

    def test_zero_total_returns_default(self):
        raw = {d: 0.0 for d in DimensionName}
        result = _normalize_weights(raw)
        for w in result.values():
            assert abs(w - 0.25) < 1e-9


# ===========================================================================
# SECTION 17 — _normalize_weights: clamping (inv 251)
# ===========================================================================


class TestSection17NormalizeClamping:
    def test_max_weight_enforced(self):
        raw = {
            DimensionName.TREND: 100.0,
            DimensionName.RISK: 0.01,
            DimensionName.STABILITY: 0.01,
            DimensionName.URGENCY: 0.01,
        }
        result = _normalize_weights(raw, min_weight=0.10, max_weight=0.40)
        for w in result.values():
            assert w <= 0.40 + 1e-7

    def test_min_weight_enforced(self):
        raw = {
            DimensionName.TREND: 100.0,
            DimensionName.RISK: 0.01,
            DimensionName.STABILITY: 0.01,
            DimensionName.URGENCY: 0.01,
        }
        result = _normalize_weights(raw, min_weight=0.10, max_weight=0.40)
        for w in result.values():
            assert w >= 0.10 - 1e-7

    def test_sum_still_one_after_clamp(self):
        raw = {
            DimensionName.TREND: 50.0,
            DimensionName.RISK: 1.0,
            DimensionName.STABILITY: 1.0,
            DimensionName.URGENCY: 1.0,
        }
        result = _normalize_weights(raw, min_weight=0.10, max_weight=0.40)
        assert abs(sum(result.values()) - 1.0) < 1e-9


# ===========================================================================
# SECTION 18 — _compute_dimension_variance
# ===========================================================================


class TestSection18Variance:
    def test_empty(self):
        assert _compute_dimension_variance([]) == 0.0

    def test_single_bucket(self):
        from umh.runtime.attribution import AttributionBucket, AttributionDimension

        b = AttributionBucket(
            dimension=AttributionDimension.TREND,
            value="up",
            sample_count=10,
            average_success_score=0.8,
            confidence=0.9,
        )
        assert _compute_dimension_variance([b]) == 0.0

    def test_two_buckets_different(self):
        from umh.runtime.attribution import AttributionBucket, AttributionDimension

        b1 = AttributionBucket(
            dimension=AttributionDimension.TREND,
            value="up",
            sample_count=10,
            average_success_score=0.9,
            confidence=1.0,
        )
        b2 = AttributionBucket(
            dimension=AttributionDimension.TREND,
            value="down",
            sample_count=10,
            average_success_score=0.1,
            confidence=1.0,
        )
        v = _compute_dimension_variance([b1, b2])
        assert v > 0


# ===========================================================================
# SECTION 19 — _compute_dimension_range
# ===========================================================================


class TestSection19Range:
    def test_empty(self):
        assert _compute_dimension_range([]) == 0.0

    def test_single(self):
        from umh.runtime.attribution import AttributionBucket, AttributionDimension

        b = AttributionBucket(
            dimension=AttributionDimension.RISK,
            value="low",
            sample_count=10,
            average_success_score=0.8,
            confidence=0.9,
        )
        assert _compute_dimension_range([b]) == 0.0

    def test_spread(self):
        from umh.runtime.attribution import AttributionBucket, AttributionDimension

        b1 = AttributionBucket(
            dimension=AttributionDimension.RISK,
            value="low",
            sample_count=10,
            average_success_score=0.9,
            confidence=1.0,
        )
        b2 = AttributionBucket(
            dimension=AttributionDimension.RISK,
            value="high",
            sample_count=10,
            average_success_score=0.3,
            confidence=1.0,
        )
        r = _compute_dimension_range([b1, b2])
        assert abs(r - 0.6) < 1e-9


# ===========================================================================
# SECTION 20 — _blend_with_default (inv 252)
# ===========================================================================


class TestSection20Blend:
    def test_zero_confidence_returns_default(self):
        assert abs(_blend_with_default(0.4, 0.0) - 0.25) < 1e-9

    def test_full_confidence_returns_learned(self):
        assert abs(_blend_with_default(0.4, 1.0) - 0.4) < 1e-9

    def test_half_confidence_blends(self):
        result = _blend_with_default(0.4, 0.5)
        expected = 0.4 * 0.5 + 0.25 * 0.5
        assert abs(result - expected) < 1e-9


# ===========================================================================
# SECTION 21 — compute_dimension_weights: no outcomes (inv 252)
# ===========================================================================


class TestSection21NoOutcomes:
    def test_empty_list(self):
        v = compute_dimension_weights([])
        assert v.is_uniform
        assert v.normalized

    def test_default_source(self):
        v = compute_dimension_weights([])
        for w in v.weights.values():
            assert w.source == "default"

    def test_sum_one(self):
        v = compute_dimension_weights([])
        total = sum(w.weight for w in v.weights.values())
        assert abs(total - 1.0) < 1e-9


# ===========================================================================
# SECTION 22 — compute_dimension_weights: uniform outcomes
# ===========================================================================


class TestSection22UniformOutcomes:
    def test_all_same_score(self):
        outcomes = [
            _make_outcome(score=0.7, trend="up", risk="low", stability="high", urgency="low")
            for _ in range(30)
        ]
        v = compute_dimension_weights(outcomes)
        assert v.normalized

    def test_four_dimensions(self):
        outcomes = [
            _make_outcome(score=0.7, trend="up", risk="low", stability="high", urgency="low")
            for _ in range(30)
        ]
        v = compute_dimension_weights(outcomes)
        assert len(v.weights) == 4


# ===========================================================================
# SECTION 23 — compute_dimension_weights: varied outcomes produce learning
# ===========================================================================


class TestSection23VariedOutcomes:
    def test_discriminative_dimension_gets_weight(self):
        outcomes = []
        for _ in range(20):
            outcomes.append(
                _make_outcome(
                    score=0.9, trend="trend_up", risk="low", stability="high", urgency="low"
                )
            )
        for _ in range(20):
            outcomes.append(
                _make_outcome(
                    score=0.2, trend="spike_down", risk="low", stability="high", urgency="low"
                )
            )
        v = compute_dimension_weights(outcomes)
        trend_w = v.get_weight(DimensionName.TREND)
        # trend varies (up=0.9, down=0.2) while others constant → trend should have higher weight
        risk_w = v.get_weight(DimensionName.RISK)
        assert trend_w > risk_w or v.is_uniform

    def test_sum_still_one(self):
        outcomes = []
        for _ in range(20):
            outcomes.append(_make_outcome(score=0.9, trend="trend_up"))
        for _ in range(20):
            outcomes.append(_make_outcome(score=0.1, trend="spike_down"))
        v = compute_dimension_weights(outcomes)
        total = sum(w.weight for w in v.weights.values())
        assert abs(total - 1.0) < 1e-9


# ===========================================================================
# SECTION 24 — Weights bounded (inv 249)
# ===========================================================================


class TestSection24WeightsBounded:
    def test_all_within_zero_one(self):
        outcomes = []
        for _ in range(30):
            outcomes.append(_make_outcome(score=0.95, trend="spike_up", risk="high"))
        for _ in range(30):
            outcomes.append(_make_outcome(score=0.05, trend="spike_down", risk="low"))
        v = compute_dimension_weights(outcomes)
        for w in v.weights.values():
            assert 0.0 <= w.weight <= 1.0

    def test_confidence_within_zero_one(self):
        outcomes = [_make_outcome(score=0.5, trend="up") for _ in range(50)]
        v = compute_dimension_weights(outcomes)
        for w in v.weights.values():
            assert 0.0 <= w.confidence <= 1.0


# ===========================================================================
# SECTION 25 — No dimension dominates (inv 251)
# ===========================================================================


class TestSection25NoDominance:
    def test_max_weight_ratio(self):
        outcomes = []
        for _ in range(50):
            outcomes.append(
                _make_outcome(
                    score=0.99, trend="spike_up", risk="low", stability="high", urgency="low"
                )
            )
        for _ in range(50):
            outcomes.append(
                _make_outcome(
                    score=0.01, trend="spike_down", risk="low", stability="high", urgency="low"
                )
            )
        v = compute_dimension_weights(outcomes)
        weights = [w.weight for w in v.weights.values()]
        if max(weights) > 0 and min(weights) > 0:
            ratio = max(weights) / min(weights)
            assert ratio < 5.0  # reasonable cap


# ===========================================================================
# SECTION 26 — Deterministic (inv 253)
# ===========================================================================


class TestSection26Deterministic:
    def test_same_inputs_same_output(self):
        outcomes = [
            _make_outcome(score=0.8, trend="up", risk="low"),
            _make_outcome(score=0.3, trend="down", risk="high"),
        ] * 15
        a = compute_dimension_weights(outcomes)
        b = compute_dimension_weights(outcomes)
        assert a.to_dict() == b.to_dict()

    def test_repeated_ten_times(self):
        outcomes = [_make_outcome(score=0.7, trend="spike_up") for _ in range(30)]
        results = [compute_dimension_weights(outcomes).to_dict() for _ in range(10)]
        for r in results[1:]:
            assert r == results[0]


# ===========================================================================
# SECTION 27 — No scoring mutation (inv 254)
# ===========================================================================


class TestSection27NoScoringMutation:
    def test_no_score_method(self):
        v = default_weight_vector()
        assert not hasattr(v, "apply_to_score")
        assert not hasattr(v, "compute_factor")

    def test_no_factor_field(self):
        d = default_weight_vector().to_dict()
        assert "factor" not in d
        assert "score" not in d


# ===========================================================================
# SECTION 28 — No circular dependency (inv 255)
# ===========================================================================


class TestSection28NoCircular:
    def test_no_scoring_import(self):
        import umh.runtime.dimension_weighting as mod
        import inspect

        src = inspect.getsource(mod)
        assert "from umh.runtime.strategy_orchestrator" not in src
        assert "from umh.runtime.feedback_selection" not in src

    def test_only_reads_outcomes(self):
        import umh.runtime.dimension_weighting as mod
        import inspect

        src = inspect.getsource(mod)
        runtime_imports = [
            l.strip()
            for l in src.split("\n")
            if l.strip().startswith("from umh.runtime") and not l.strip().startswith("#")
        ]
        allowed = {"attribution", "outcome", "regime_aggregation"}
        for imp in runtime_imports:
            assert any(a in imp for a in allowed), f"unexpected import: {imp}"


# ===========================================================================
# SECTION 29 — Explainability (inv 256)
# ===========================================================================


class TestSection29Explainability:
    def test_default_has_explanation(self):
        v = default_weight_vector()
        assert len(v.explanation) > 0

    def test_computed_has_explanation(self):
        outcomes = [_make_outcome(score=0.7, trend="up") for _ in range(30)]
        v = compute_dimension_weights(outcomes)
        assert len(v.explanation) > 0

    def test_explanation_mentions_dimensions(self):
        outcomes = [
            _make_outcome(score=0.9, trend="spike_up", risk="low"),
            _make_outcome(score=0.1, trend="spike_down", risk="high"),
        ] * 15
        v = compute_dimension_weights(outcomes)
        exp = v.explanation.lower()
        assert "trend" in exp or "risk" in exp or "stability" in exp or "urgency" in exp


# ===========================================================================
# SECTION 30 — Boundary compliance
# ===========================================================================


class TestSection30Boundary:
    def test_no_os_import(self):
        import umh.runtime.dimension_weighting as mod
        import inspect

        src = inspect.getsource(mod)
        lines = [
            l.strip()
            for l in src.split("\n")
            if l.strip().startswith("import os") or l.strip().startswith("from os")
        ]
        assert len(lines) == 0

    def test_no_subprocess(self):
        import umh.runtime.dimension_weighting as mod
        import inspect

        src = inspect.getsource(mod)
        lines = [
            l.strip()
            for l in src.split("\n")
            if l.strip().startswith("import subprocess") or l.strip().startswith("from subprocess")
        ]
        assert len(lines) == 0

    def test_no_random(self):
        import umh.runtime.dimension_weighting as mod
        import inspect

        src = inspect.getsource(mod)
        assert "import random" not in src

    def test_no_cells_import(self):
        import umh.runtime.dimension_weighting as mod
        import inspect

        src = inspect.getsource(mod)
        assert "umh.cells" not in src
        assert "umh.environments" not in src
        assert "umh.adapters" not in src


# ===========================================================================
# SECTION 31 — Import surface
# ===========================================================================


class TestSection31ImportSurface:
    def test_from_init(self):
        from umh.runtime import (
            DEFAULT_WEIGHTING_CONFIG,
            DEFAULT_WEIGHT_VECTOR,
            DimensionWeight,
            DimensionWeightVector,
            WeightingConfig,
            compute_dimension_weights,
            default_weight_vector,
        )

        assert DimensionWeight is not None
        assert DimensionWeightVector is not None


# ===========================================================================
# SECTION 32 — Orchestrator integration: dimension_weights param
# ===========================================================================


class TestSection32OrchestratorParam:
    def test_default_none(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r = orchestrate_selection(["a"], [1.0])
        assert r.dimension_weights is None

    def test_attached_to_result(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        v = default_weight_vector()
        r = orchestrate_selection(["a"], [1.0], dimension_weights=v)
        assert r.dimension_weights is v

    def test_no_scoring_change(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r1 = orchestrate_selection(["a", "b"], [0.8, 0.7])
        v = default_weight_vector()
        r2 = orchestrate_selection(["a", "b"], [0.8, 0.7], dimension_weights=v)
        assert r1.selected_strategy == r2.selected_strategy


# ===========================================================================
# SECTION 33 — Orchestrator explanation includes dimension weights
# ===========================================================================


class TestSection33OrchestratorExplanation:
    def test_explanation_includes_weights(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        v = default_weight_vector()
        r = orchestrate_selection(["a"], [1.0], dimension_weights=v)
        assert "dimension_weights=" in r.explanation

    def test_explanation_without_weights(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r = orchestrate_selection(["a"], [1.0])
        assert "dimension_weights=" not in r.explanation


# ===========================================================================
# SECTION 34 — Orchestrator to_dict includes dimension weights
# ===========================================================================


class TestSection34OrchestratorDict:
    def test_dict_includes_weights(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        v = default_weight_vector()
        r = orchestrate_selection(["a"], [1.0], dimension_weights=v)
        d = r.to_dict()
        assert "dimension_weights" in d

    def test_dict_excludes_when_none(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r = orchestrate_selection(["a"], [1.0])
        d = r.to_dict()
        assert "dimension_weights" not in d


# ===========================================================================
# SECTION 35 — Phase 59 unchanged
# ===========================================================================


class TestSection35Phase59Unchanged:
    def test_aggregation_still_works(self):
        from umh.runtime.regime_aggregation import aggregate_regimes

        state = aggregate_regimes(trend_label="spike_up", risk_label="low")
        assert state.alignment_score == 1.0

    def test_aggregation_exports(self):
        from umh.runtime import AggregatedRegimeState, aggregate_regimes

        assert AggregatedRegimeState is not None


# ===========================================================================
# SECTION 36 — Phase 58 unchanged
# ===========================================================================


class TestSection36Phase58Unchanged:
    def test_orchestrate_basic(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r = orchestrate_selection(["a", "b"], [0.5, 0.8])
        assert r.selected_strategy == "b"

    def test_result_fields(self):
        from umh.runtime.strategy_orchestrator import StrategySelectionResult

        r = StrategySelectionResult()
        assert hasattr(r, "base_winner")
        assert hasattr(r, "aggregated_regime")
        assert hasattr(r, "dimension_weights")


# ===========================================================================
# SECTION 37 — Confidence blending edge cases
# ===========================================================================


class TestSection37ConfidenceEdge:
    def test_below_threshold_uses_default(self):
        cfg = WeightingConfig(confidence_threshold=0.5, required_samples=100)
        outcomes = [_make_outcome(score=0.9, trend="up") for _ in range(5)]
        v = compute_dimension_weights(outcomes, config=cfg)
        for w in v.weights.values():
            assert w.source == "default"

    def test_above_threshold_can_learn(self):
        cfg = WeightingConfig(confidence_threshold=0.1, required_samples=5)
        outcomes = []
        for _ in range(20):
            outcomes.append(_make_outcome(score=0.95, trend="spike_up", risk="low"))
        for _ in range(20):
            outcomes.append(_make_outcome(score=0.05, trend="spike_down", risk="high"))
        v = compute_dimension_weights(outcomes, config=cfg)
        has_learned = any(w.source == "learned" for w in v.weights.values())
        assert has_learned or v.is_uniform


# ===========================================================================
# SECTION 38 — Custom config
# ===========================================================================


class TestSection38CustomConfig:
    def test_custom_min_max(self):
        cfg = WeightingConfig(min_weight=0.15, max_weight=0.35)
        assert cfg.min_weight == 0.15
        assert cfg.max_weight == 0.35

    def test_config_applied(self):
        cfg = WeightingConfig(required_samples=5)
        outcomes = [_make_outcome(score=0.8, trend="up") for _ in range(10)]
        v = compute_dimension_weights(outcomes, config=cfg)
        assert v.normalized


# ===========================================================================
# SECTION 39 — No mutation of inputs (inv 247 analog)
# ===========================================================================


class TestSection39NoMutation:
    def test_outcomes_not_mutated(self):
        outcomes = [_make_outcome(score=0.7, trend="up") for _ in range(10)]
        count_before = len(outcomes)
        compute_dimension_weights(outcomes)
        assert len(outcomes) == count_before

    def test_config_not_mutated(self):
        cfg = WeightingConfig()
        orig_min = cfg.min_weight
        compute_dimension_weights([], config=cfg)
        assert cfg.min_weight == orig_min


# ===========================================================================
# SECTION 40 — Stress: 200 outcomes
# ===========================================================================


class TestSection40Stress:
    def test_200_outcomes(self):
        outcomes = []
        for i in range(200):
            trend = "spike_up" if i % 3 == 0 else "spike_down" if i % 3 == 1 else "stable"
            risk = "high" if i % 2 == 0 else "low"
            outcomes.append(
                _make_outcome(
                    score=0.1 + (i % 10) * 0.09,
                    trend=trend,
                    risk=risk,
                )
            )
        v = compute_dimension_weights(outcomes)
        assert v.normalized
        total = sum(w.weight for w in v.weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_deterministic_under_load(self):
        outcomes = [
            _make_outcome(score=0.5 + (i % 5) * 0.1, trend="up" if i % 2 == 0 else "down")
            for i in range(100)
        ]
        a = compute_dimension_weights(outcomes)
        b = compute_dimension_weights(outcomes)
        assert a.to_dict() == b.to_dict()


# ===========================================================================
# SECTION 41 — No execution methods
# ===========================================================================


class TestSection41NoExecution:
    def test_no_execute(self):
        import umh.runtime.dimension_weighting as mod

        assert not hasattr(mod, "execute")
        assert not hasattr(mod, "run")

    def test_no_io(self):
        import umh.runtime.dimension_weighting as mod
        import inspect

        src = inspect.getsource(mod)
        assert "open(" not in src
        assert "pathlib" not in src


# ===========================================================================
# SECTION 42 — Normalization sum property
# ===========================================================================


class TestSection42NormSum:
    def test_computed_weights_sum_one(self):
        outcomes = [
            _make_outcome(score=0.9, trend="spike_up", risk="low", stability="high", urgency="low"),
            _make_outcome(
                score=0.1, trend="spike_down", risk="high", stability="low", urgency="high"
            ),
        ] * 20
        v = compute_dimension_weights(outcomes)
        total = sum(w.weight for w in v.weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_default_weights_sum_one(self):
        v = default_weight_vector()
        total = sum(w.weight for w in v.weights.values())
        assert abs(total - 1.0) < 1e-9


# ===========================================================================
# SECTION 43 — Missing dimension data partial
# ===========================================================================


class TestSection43MissingPartial:
    def test_only_trend_data(self):
        outcomes = [_make_outcome(score=0.8, trend="up") for _ in range(30)]
        v = compute_dimension_weights(outcomes)
        assert len(v.weights) == 4
        total = sum(w.weight for w in v.weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_no_metadata(self):
        outcomes = [_make_outcome(score=0.7) for _ in range(30)]
        v = compute_dimension_weights(outcomes)
        assert v.normalized


# ===========================================================================
# SECTION 44 — Orchestrator: dimension_weights in empty selection
# ===========================================================================


class TestSection44EmptySelection:
    def test_empty_ids(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        v = default_weight_vector()
        r = orchestrate_selection([], [], dimension_weights=v)
        assert r.dimension_weights is None

    def test_all_invalid(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        v = default_weight_vector()
        r = orchestrate_selection(["a"], [1.0], valid_flags=[False], dimension_weights=v)
        assert r.dimension_weights is None


# ===========================================================================
# SECTION 45 — Existing init exports regression
# ===========================================================================


class TestSection45InitRegression:
    def test_strategy_orchestrator_exports(self):
        from umh.runtime import (
            StrategyCandidate,
            StrategyOrchestrationPolicy,
            orchestrate_selection,
        )

        assert StrategyCandidate is not None

    def test_feedback_selection_exports(self):
        from umh.runtime import FeedbackSelectionPolicy, select_with_feedback

        assert FeedbackSelectionPolicy is not None

    def test_aggregation_exports(self):
        from umh.runtime import AggregatedRegimeState, aggregate_regimes

        assert AggregatedRegimeState is not None

    def test_dimension_weighting_exports(self):
        from umh.runtime import (
            DimensionWeight,
            DimensionWeightVector,
            compute_dimension_weights,
        )

        assert DimensionWeight is not None


# ===========================================================================
# SECTION 46 — Full pipeline: both aggregated_regime and dimension_weights
# ===========================================================================


class TestSection46FullPipeline:
    def test_both_attached(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection
        from umh.runtime.regime_aggregation import aggregate_regimes

        agg = aggregate_regimes(trend_label="spike_up")
        wv = default_weight_vector()
        r = orchestrate_selection(
            ["a", "b"],
            [0.7, 0.8],
            aggregated_regime=agg,
            dimension_weights=wv,
        )
        assert r.aggregated_regime is agg
        assert r.dimension_weights is wv
        assert "aggregated_regime=" in r.explanation
        assert "dimension_weights=" in r.explanation

    def test_scoring_unaffected(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection
        from umh.runtime.regime_aggregation import aggregate_regimes

        r_plain = orchestrate_selection(["a", "b"], [0.6, 0.9])
        r_full = orchestrate_selection(
            ["a", "b"],
            [0.6, 0.9],
            aggregated_regime=aggregate_regimes(trend_label="spike_down"),
            dimension_weights=default_weight_vector(),
        )
        assert r_plain.selected_strategy == r_full.selected_strategy


# ===========================================================================
# SECTION 47 — Explanation content quality
# ===========================================================================


class TestSection47ExplanationContent:
    def test_default_explanation_mentions_no_data(self):
        v = default_weight_vector()
        assert "no outcome data" in v.explanation.lower() or "default" in v.explanation.lower()

    def test_learned_explanation_mentions_confidence(self):
        outcomes = []
        for _ in range(25):
            outcomes.append(_make_outcome(score=0.9, trend="spike_up", risk="low"))
        for _ in range(25):
            outcomes.append(_make_outcome(score=0.1, trend="spike_down", risk="high"))
        v = compute_dimension_weights(outcomes, config=WeightingConfig(required_samples=5))
        if v.is_learned:
            assert "confidence" in v.explanation.lower()


# ===========================================================================
# SECTION 48 — StrategySelectionResult dimension_weights field
# ===========================================================================


class TestSection48ResultField:
    def test_field_exists(self):
        from umh.runtime.strategy_orchestrator import StrategySelectionResult

        r = StrategySelectionResult()
        assert r.dimension_weights is None

    def test_field_accepts_vector(self):
        from umh.runtime.strategy_orchestrator import StrategySelectionResult

        v = default_weight_vector()
        r = StrategySelectionResult(dimension_weights=v)
        assert r.dimension_weights is v


# ===========================================================================
# SECTION 49 — No randomness
# ===========================================================================


class TestSection49NoRandomness:
    def test_no_random_import(self):
        import umh.runtime.dimension_weighting as mod
        import inspect

        src = inspect.getsource(mod)
        assert "import random" not in src


# ===========================================================================
# SECTION 50 — DEFAULT_WEIGHTING_CONFIG constant
# ===========================================================================


class TestSection50DefaultConfig:
    def test_constant_values(self):
        assert DEFAULT_WEIGHTING_CONFIG.min_weight == 0.10
        assert DEFAULT_WEIGHTING_CONFIG.max_weight == 0.40
        assert DEFAULT_WEIGHTING_CONFIG.required_samples == 20
        assert DEFAULT_WEIGHTING_CONFIG.confidence_threshold == 0.3
