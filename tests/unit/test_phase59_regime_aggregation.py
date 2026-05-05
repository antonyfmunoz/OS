"""Phase 59 — Multi-signal regime aggregation tests.

Tests per-dimension regime classification, aggregation into
composite state, alignment/conflict scoring, dominant dimension
selection, and orchestrator integration.

Invariants 242-248.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime.regime_aggregation import (
    NEUTRAL_AGGREGATED,
    NEUTRAL_RISK,
    NEUTRAL_STABILITY,
    NEUTRAL_TREND,
    NEUTRAL_URGENCY,
    AggregatedRegimeState,
    DimensionName,
    DimensionRegime,
    DirectionCategory,
    aggregate_from_dict,
    aggregate_regimes,
    classify_dimension,
)


# ===========================================================================
# SECTION 1 — DimensionName enum
# ===========================================================================


class TestSection01DimensionName:
    def test_trend_value(self):
        assert DimensionName.TREND.value == "trend"

    def test_risk_value(self):
        assert DimensionName.RISK.value == "risk"

    def test_stability_value(self):
        assert DimensionName.STABILITY.value == "stability"

    def test_urgency_value(self):
        assert DimensionName.URGENCY.value == "urgency"

    def test_all_four(self):
        assert len(DimensionName) == 4


# ===========================================================================
# SECTION 2 — DirectionCategory enum
# ===========================================================================


class TestSection02DirectionCategory:
    def test_positive(self):
        assert DirectionCategory.POSITIVE.value == "positive"

    def test_negative(self):
        assert DirectionCategory.NEGATIVE.value == "negative"

    def test_neutral(self):
        assert DirectionCategory.NEUTRAL.value == "neutral"

    def test_all_three(self):
        assert len(DirectionCategory) == 3


# ===========================================================================
# SECTION 3 — DimensionRegime defaults and bounds
# ===========================================================================


class TestSection03DimensionRegimeDefaults:
    def test_default_strength(self):
        r = DimensionRegime(
            dimension=DimensionName.TREND,
            regime_label="stable",
            direction=DirectionCategory.NEUTRAL,
        )
        assert r.strength == 0.0

    def test_default_confidence(self):
        r = DimensionRegime(
            dimension=DimensionName.TREND,
            regime_label="stable",
            direction=DirectionCategory.NEUTRAL,
        )
        assert r.confidence == 0.0

    def test_strength_clamped_low(self):
        r = DimensionRegime(
            dimension=DimensionName.TREND,
            regime_label="x",
            direction=DirectionCategory.NEUTRAL,
            strength=-0.5,
        )
        assert r.strength == 0.0

    def test_strength_clamped_high(self):
        r = DimensionRegime(
            dimension=DimensionName.TREND,
            regime_label="x",
            direction=DirectionCategory.NEUTRAL,
            strength=2.0,
        )
        assert r.strength == 1.0

    def test_confidence_clamped_low(self):
        r = DimensionRegime(
            dimension=DimensionName.TREND,
            regime_label="x",
            direction=DirectionCategory.NEUTRAL,
            confidence=-1.0,
        )
        assert r.confidence == 0.0

    def test_confidence_clamped_high(self):
        r = DimensionRegime(
            dimension=DimensionName.TREND,
            regime_label="x",
            direction=DirectionCategory.NEUTRAL,
            confidence=5.0,
        )
        assert r.confidence == 1.0


# ===========================================================================
# SECTION 4 — DimensionRegime effective_strength
# ===========================================================================


class TestSection04EffectiveStrength:
    def test_product(self):
        r = DimensionRegime(
            dimension=DimensionName.TREND,
            regime_label="trend_up",
            direction=DirectionCategory.POSITIVE,
            strength=0.8,
            confidence=0.5,
        )
        assert abs(r.effective_strength - 0.4) < 1e-9

    def test_zero_confidence(self):
        r = DimensionRegime(
            dimension=DimensionName.TREND,
            regime_label="trend_up",
            direction=DirectionCategory.POSITIVE,
            strength=1.0,
            confidence=0.0,
        )
        assert r.effective_strength == 0.0

    def test_full(self):
        r = DimensionRegime(
            dimension=DimensionName.TREND,
            regime_label="spike_up",
            direction=DirectionCategory.POSITIVE,
            strength=1.0,
            confidence=1.0,
        )
        assert r.effective_strength == 1.0


# ===========================================================================
# SECTION 5 — DimensionRegime to_dict
# ===========================================================================


class TestSection05DimensionRegimeDict:
    def test_keys(self):
        r = DimensionRegime(
            dimension=DimensionName.RISK,
            regime_label="high",
            direction=DirectionCategory.NEGATIVE,
            strength=0.9,
            confidence=0.7,
        )
        d = r.to_dict()
        expected = {
            "dimension",
            "regime_label",
            "direction",
            "strength",
            "confidence",
            "effective_strength",
        }
        assert set(d.keys()) == expected

    def test_values(self):
        r = DimensionRegime(
            dimension=DimensionName.RISK,
            regime_label="high",
            direction=DirectionCategory.NEGATIVE,
            strength=1.0,
            confidence=1.0,
        )
        d = r.to_dict()
        assert d["dimension"] == "risk"
        assert d["direction"] == "negative"


# ===========================================================================
# SECTION 6 — DimensionRegime frozen
# ===========================================================================


class TestSection06DimensionRegimeFrozen:
    def test_cannot_set_strength(self):
        r = DimensionRegime(
            dimension=DimensionName.TREND,
            regime_label="stable",
            direction=DirectionCategory.NEUTRAL,
        )
        try:
            r.strength = 0.5  # type: ignore[misc]
            assert False, "should raise"
        except AttributeError:
            pass

    def test_cannot_set_dimension(self):
        r = DimensionRegime(
            dimension=DimensionName.TREND,
            regime_label="stable",
            direction=DirectionCategory.NEUTRAL,
        )
        try:
            r.dimension = DimensionName.RISK  # type: ignore[misc]
            assert False, "should raise"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 7 — Neutral constants
# ===========================================================================


class TestSection07NeutralConstants:
    def test_neutral_trend(self):
        assert NEUTRAL_TREND.dimension is DimensionName.TREND
        assert NEUTRAL_TREND.direction is DirectionCategory.NEUTRAL
        assert NEUTRAL_TREND.strength == 0.0

    def test_neutral_risk(self):
        assert NEUTRAL_RISK.dimension is DimensionName.RISK
        assert NEUTRAL_RISK.direction is DirectionCategory.NEUTRAL

    def test_neutral_stability(self):
        assert NEUTRAL_STABILITY.dimension is DimensionName.STABILITY
        assert NEUTRAL_STABILITY.direction is DirectionCategory.NEUTRAL

    def test_neutral_urgency(self):
        assert NEUTRAL_URGENCY.dimension is DimensionName.URGENCY
        assert NEUTRAL_URGENCY.direction is DirectionCategory.NEUTRAL


# ===========================================================================
# SECTION 8 — classify_dimension: trend (inv 242)
# ===========================================================================


class TestSection08ClassifyTrend:
    def test_stable(self):
        r = classify_dimension(DimensionName.TREND, "stable")
        assert r.direction is DirectionCategory.NEUTRAL
        assert r.strength == 0.0

    def test_trend_up(self):
        r = classify_dimension(DimensionName.TREND, "trend_up")
        assert r.direction is DirectionCategory.POSITIVE
        assert r.strength == 0.5

    def test_trend_down(self):
        r = classify_dimension(DimensionName.TREND, "trend_down")
        assert r.direction is DirectionCategory.NEGATIVE
        assert r.strength == 0.5

    def test_spike_up(self):
        r = classify_dimension(DimensionName.TREND, "spike_up")
        assert r.direction is DirectionCategory.POSITIVE
        assert r.strength == 1.0

    def test_spike_down(self):
        r = classify_dimension(DimensionName.TREND, "spike_down")
        assert r.direction is DirectionCategory.NEGATIVE
        assert r.strength == 1.0

    def test_unknown_label(self):
        r = classify_dimension(DimensionName.TREND, "garbage")
        assert r.direction is DirectionCategory.NEUTRAL
        assert r.regime_label == "neutral"


# ===========================================================================
# SECTION 9 — classify_dimension: risk (inv 242)
# ===========================================================================


class TestSection09ClassifyRisk:
    def test_low(self):
        r = classify_dimension(DimensionName.RISK, "low")
        assert r.direction is DirectionCategory.POSITIVE
        assert r.strength == 0.2

    def test_medium(self):
        r = classify_dimension(DimensionName.RISK, "medium")
        assert r.direction is DirectionCategory.NEUTRAL
        assert r.strength == 0.5

    def test_high(self):
        r = classify_dimension(DimensionName.RISK, "high")
        assert r.direction is DirectionCategory.NEGATIVE
        assert r.strength == 1.0


# ===========================================================================
# SECTION 10 — classify_dimension: stability (inv 242)
# ===========================================================================


class TestSection10ClassifyStability:
    def test_high(self):
        r = classify_dimension(DimensionName.STABILITY, "high")
        assert r.direction is DirectionCategory.POSITIVE
        assert r.strength == 0.2

    def test_medium(self):
        r = classify_dimension(DimensionName.STABILITY, "medium")
        assert r.direction is DirectionCategory.NEUTRAL

    def test_low(self):
        r = classify_dimension(DimensionName.STABILITY, "low")
        assert r.direction is DirectionCategory.NEGATIVE
        assert r.strength == 1.0


# ===========================================================================
# SECTION 11 — classify_dimension: urgency (inv 242)
# ===========================================================================


class TestSection11ClassifyUrgency:
    def test_low(self):
        r = classify_dimension(DimensionName.URGENCY, "low")
        assert r.direction is DirectionCategory.POSITIVE

    def test_medium(self):
        r = classify_dimension(DimensionName.URGENCY, "medium")
        assert r.direction is DirectionCategory.NEUTRAL

    def test_high(self):
        r = classify_dimension(DimensionName.URGENCY, "high")
        assert r.direction is DirectionCategory.NEGATIVE
        assert r.strength == 1.0


# ===========================================================================
# SECTION 12 — classify_dimension: confidence passed through
# ===========================================================================


class TestSection12Confidence:
    def test_custom_confidence(self):
        r = classify_dimension(DimensionName.TREND, "spike_up", confidence=0.3)
        assert r.confidence == 0.3

    def test_default_confidence(self):
        r = classify_dimension(DimensionName.TREND, "spike_up")
        assert r.confidence == 1.0

    def test_confidence_clamped(self):
        r = classify_dimension(DimensionName.TREND, "spike_up", confidence=5.0)
        assert r.confidence == 1.0


# ===========================================================================
# SECTION 13 — classify_dimension: case insensitive
# ===========================================================================


class TestSection13CaseInsensitive:
    def test_upper_case(self):
        r = classify_dimension(DimensionName.TREND, "SPIKE_UP")
        assert r.direction is DirectionCategory.POSITIVE

    def test_mixed_case(self):
        r = classify_dimension(DimensionName.RISK, "High")
        assert r.direction is DirectionCategory.NEGATIVE


# ===========================================================================
# SECTION 14 — AggregatedRegimeState defaults
# ===========================================================================


class TestSection14AggregatedDefaults:
    def test_default_alignment(self):
        state = AggregatedRegimeState(regimes={})
        assert state.alignment_score == 0.0

    def test_default_conflict(self):
        state = AggregatedRegimeState(regimes={})
        assert state.conflict_score == 0.0

    def test_default_dominant(self):
        state = AggregatedRegimeState(regimes={})
        assert state.dominant_dimension is None

    def test_default_explanation(self):
        state = AggregatedRegimeState(regimes={})
        assert state.explanation == ""


# ===========================================================================
# SECTION 15 — AggregatedRegimeState bounds
# ===========================================================================


class TestSection15AggregatedBounds:
    def test_alignment_clamped_high(self):
        state = AggregatedRegimeState(regimes={}, alignment_score=2.0)
        assert state.alignment_score == 1.0

    def test_alignment_clamped_low(self):
        state = AggregatedRegimeState(regimes={}, alignment_score=-1.0)
        assert state.alignment_score == 0.0

    def test_conflict_clamped_high(self):
        state = AggregatedRegimeState(regimes={}, conflict_score=5.0)
        assert state.conflict_score == 1.0

    def test_conflict_clamped_low(self):
        state = AggregatedRegimeState(regimes={}, conflict_score=-3.0)
        assert state.conflict_score == 0.0


# ===========================================================================
# SECTION 16 — AggregatedRegimeState properties
# ===========================================================================


class TestSection16AggregatedProperties:
    def test_is_aligned(self):
        state = AggregatedRegimeState(regimes={}, alignment_score=0.8, conflict_score=0.2)
        assert state.is_aligned is True
        assert state.is_conflicted is False

    def test_is_conflicted(self):
        state = AggregatedRegimeState(regimes={}, alignment_score=0.2, conflict_score=0.8)
        assert state.is_conflicted is True
        assert state.is_aligned is False

    def test_is_neutral(self):
        state = AggregatedRegimeState(regimes={}, alignment_score=0.0, conflict_score=0.0)
        assert state.is_neutral is True


# ===========================================================================
# SECTION 17 — AggregatedRegimeState get / get_or_neutral
# ===========================================================================


class TestSection17AggregatedAccess:
    def test_get_existing(self):
        state = aggregate_regimes(trend_label="spike_up")
        r = state.get(DimensionName.TREND)
        assert r is not None
        assert r.regime_label == "spike_up"

    def test_get_missing_returns_none(self):
        state = AggregatedRegimeState(regimes={})
        assert state.get(DimensionName.TREND) is None

    def test_get_or_neutral(self):
        state = AggregatedRegimeState(regimes={})
        r = state.get_or_neutral(DimensionName.RISK)
        assert r.dimension is DimensionName.RISK
        assert r.direction is DirectionCategory.NEUTRAL


# ===========================================================================
# SECTION 18 — AggregatedRegimeState to_dict
# ===========================================================================


class TestSection18AggregatedDict:
    def test_keys(self):
        state = aggregate_regimes(trend_label="stable")
        d = state.to_dict()
        expected = {
            "regimes",
            "dominant_dimension",
            "alignment_score",
            "conflict_score",
            "explanation",
            "is_aligned",
            "is_conflicted",
            "is_neutral",
        }
        assert set(d.keys()) == expected

    def test_regimes_nested(self):
        state = aggregate_regimes(trend_label="spike_up")
        d = state.to_dict()
        assert "trend" in d["regimes"]


# ===========================================================================
# SECTION 19 — AggregatedRegimeState frozen
# ===========================================================================


class TestSection19AggregatedFrozen:
    def test_cannot_set_alignment(self):
        state = aggregate_regimes()
        try:
            state.alignment_score = 0.5  # type: ignore[misc]
            assert False, "should raise"
        except AttributeError:
            pass

    def test_cannot_set_dominant(self):
        state = aggregate_regimes()
        try:
            state.dominant_dimension = DimensionName.TREND  # type: ignore[misc]
            assert False, "should raise"
        except AttributeError:
            pass


# ===========================================================================
# SECTION 20 — NEUTRAL_AGGREGATED constant
# ===========================================================================


class TestSection20NeutralAggregated:
    def test_all_four_dimensions(self):
        assert len(NEUTRAL_AGGREGATED.regimes) == 4

    def test_all_neutral(self):
        for r in NEUTRAL_AGGREGATED.regimes.values():
            assert r.direction is DirectionCategory.NEUTRAL

    def test_no_dominant(self):
        assert NEUTRAL_AGGREGATED.dominant_dimension is None

    def test_is_neutral(self):
        assert NEUTRAL_AGGREGATED.is_neutral is True


# ===========================================================================
# SECTION 21 — aggregate_regimes: all missing = neutral (inv 245)
# ===========================================================================


class TestSection21AllMissingNeutral:
    def test_no_args(self):
        state = aggregate_regimes()
        assert len(state.regimes) == 4
        for r in state.regimes.values():
            assert r.direction is DirectionCategory.NEUTRAL

    def test_alignment_zero(self):
        state = aggregate_regimes()
        assert state.alignment_score == 0.0

    def test_conflict_zero(self):
        state = aggregate_regimes()
        assert state.conflict_score == 0.0

    def test_no_dominant(self):
        state = aggregate_regimes()
        assert state.dominant_dimension is None


# ===========================================================================
# SECTION 22 — aggregate_regimes: partial missing (inv 245)
# ===========================================================================


class TestSection22PartialMissing:
    def test_only_trend(self):
        state = aggregate_regimes(trend_label="spike_up")
        assert state.regimes["trend"].regime_label == "spike_up"
        assert state.regimes["risk"].direction is DirectionCategory.NEUTRAL

    def test_only_risk(self):
        state = aggregate_regimes(risk_label="high")
        assert state.regimes["risk"].direction is DirectionCategory.NEGATIVE
        assert state.regimes["trend"].direction is DirectionCategory.NEUTRAL


# ===========================================================================
# SECTION 23 — Alignment: all agree positive (inv 243)
# ===========================================================================


class TestSection23AllPositive:
    def test_alignment_one(self):
        state = aggregate_regimes(
            trend_label="trend_up",
            risk_label="low",
            stability_label="high",
            urgency_label="low",
        )
        assert state.alignment_score == 1.0

    def test_conflict_zero(self):
        state = aggregate_regimes(
            trend_label="trend_up",
            risk_label="low",
            stability_label="high",
            urgency_label="low",
        )
        assert state.conflict_score == 0.0

    def test_is_aligned(self):
        state = aggregate_regimes(
            trend_label="trend_up",
            risk_label="low",
            stability_label="high",
            urgency_label="low",
        )
        assert state.is_aligned is True


# ===========================================================================
# SECTION 24 — Alignment: all agree negative
# ===========================================================================


class TestSection24AllNegative:
    def test_alignment_one(self):
        state = aggregate_regimes(
            trend_label="spike_down",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        assert state.alignment_score == 1.0

    def test_conflict_zero(self):
        state = aggregate_regimes(
            trend_label="spike_down",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        assert state.conflict_score == 0.0


# ===========================================================================
# SECTION 25 — Conflict: opposing dimensions (inv 243, 244)
# ===========================================================================


class TestSection25Conflict:
    def test_two_pos_two_neg(self):
        state = aggregate_regimes(
            trend_label="trend_up",
            risk_label="low",
            stability_label="low",
            urgency_label="high",
        )
        assert state.alignment_score == 0.5
        assert state.conflict_score == 0.5

    def test_three_pos_one_neg(self):
        state = aggregate_regimes(
            trend_label="trend_up",
            risk_label="low",
            stability_label="high",
            urgency_label="high",
        )
        assert abs(state.alignment_score - 0.75) < 1e-9
        assert abs(state.conflict_score - 0.25) < 1e-9

    def test_one_pos_three_neg(self):
        state = aggregate_regimes(
            trend_label="trend_up",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        assert abs(state.alignment_score - 0.75) < 1e-9
        assert abs(state.conflict_score - 0.25) < 1e-9


# ===========================================================================
# SECTION 26 — Neutral dimensions excluded from alignment/conflict
# ===========================================================================


class TestSection26NeutralExcluded:
    def test_one_non_neutral(self):
        state = aggregate_regimes(
            trend_label="spike_up",
            risk_label="medium",
            stability_label="medium",
            urgency_label="medium",
        )
        assert state.alignment_score == 1.0
        assert state.conflict_score == 0.0

    def test_all_neutral(self):
        state = aggregate_regimes(
            trend_label="stable",
            risk_label="medium",
            stability_label="medium",
            urgency_label="medium",
        )
        assert state.alignment_score == 0.0
        assert state.conflict_score == 0.0


# ===========================================================================
# SECTION 27 — Dominant dimension: highest effective_strength (inv 243)
# ===========================================================================


class TestSection27DominantDimension:
    def test_spike_dominates(self):
        state = aggregate_regimes(
            trend_label="spike_up",
            risk_label="low",
        )
        assert state.dominant_dimension is DimensionName.TREND

    def test_high_risk_dominates(self):
        state = aggregate_regimes(
            trend_label="trend_up",
            risk_label="high",
        )
        assert state.dominant_dimension is DimensionName.RISK

    def test_no_dominant_when_all_neutral(self):
        state = aggregate_regimes()
        assert state.dominant_dimension is None


# ===========================================================================
# SECTION 28 — Dominant dimension: tie-break by name (inv 243)
# ===========================================================================


class TestSection28DominantTieBreak:
    def test_tie_broken_lexicographically(self):
        state = aggregate_regimes(
            risk_label="high",
            urgency_label="high",
        )
        # both strength=1.0, confidence=1.0 → effective=1.0
        # "risk" < "urgency" lexicographically
        assert state.dominant_dimension is DimensionName.RISK

    def test_confidence_affects_dominant(self):
        state = aggregate_regimes(
            risk_label="high",
            urgency_label="high",
            risk_confidence=0.3,
            urgency_confidence=0.9,
        )
        assert state.dominant_dimension is DimensionName.URGENCY


# ===========================================================================
# SECTION 29 — Determinism (inv 243)
# ===========================================================================


class TestSection29Determinism:
    def test_same_inputs_same_output(self):
        a = aggregate_regimes(
            trend_label="spike_up",
            risk_label="high",
            stability_label="low",
            urgency_label="medium",
        )
        b = aggregate_regimes(
            trend_label="spike_up",
            risk_label="high",
            stability_label="low",
            urgency_label="medium",
        )
        assert a.alignment_score == b.alignment_score
        assert a.conflict_score == b.conflict_score
        assert a.dominant_dimension == b.dominant_dimension
        assert a.explanation == b.explanation

    def test_dict_output_matches(self):
        a = aggregate_regimes(trend_label="trend_up", risk_label="low")
        b = aggregate_regimes(trend_label="trend_up", risk_label="low")
        assert a.to_dict() == b.to_dict()


# ===========================================================================
# SECTION 30 — No combinatorial explosion (inv 244)
# ===========================================================================


class TestSection30NoCombinatorial:
    def test_output_is_single_state(self):
        state = aggregate_regimes(
            trend_label="spike_up",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        assert isinstance(state, AggregatedRegimeState)
        assert len(state.regimes) == 4

    def test_bounded_scores(self):
        state = aggregate_regimes(
            trend_label="spike_up",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        assert 0.0 <= state.alignment_score <= 1.0
        assert 0.0 <= state.conflict_score <= 1.0


# ===========================================================================
# SECTION 31 — Explainability (inv 246)
# ===========================================================================


class TestSection31Explainability:
    def test_explanation_contains_dimensions(self):
        state = aggregate_regimes(
            trend_label="spike_up",
            risk_label="high",
        )
        assert "trend=" in state.explanation
        assert "risk=" in state.explanation

    def test_explanation_contains_dominant(self):
        state = aggregate_regimes(trend_label="spike_up")
        assert "dominant=" in state.explanation

    def test_explanation_contains_alignment(self):
        state = aggregate_regimes(
            trend_label="spike_up",
            risk_label="low",
        )
        assert "alignment=" in state.explanation

    def test_explanation_contains_conflict(self):
        state = aggregate_regimes(
            trend_label="spike_up",
            risk_label="high",
        )
        assert "conflict=" in state.explanation


# ===========================================================================
# SECTION 32 — No mutation (inv 247)
# ===========================================================================


class TestSection32NoMutation:
    def test_dict_input_not_mutated(self):
        labels = {"trend": "spike_up", "risk": "high"}
        confs = {"trend": 0.8, "risk": 0.9}
        labels_copy = dict(labels)
        confs_copy = dict(confs)
        aggregate_from_dict(labels, confs)
        assert labels == labels_copy
        assert confs == confs_copy

    def test_result_frozen(self):
        state = aggregate_regimes(trend_label="stable")
        try:
            state.alignment_score = 0.5  # type: ignore[misc]
            assert False
        except AttributeError:
            pass


# ===========================================================================
# SECTION 33 — aggregate_from_dict
# ===========================================================================


class TestSection33AggregateFromDict:
    def test_basic(self):
        state = aggregate_from_dict({"trend": "spike_up", "risk": "low"})
        assert state.regimes["trend"].direction is DirectionCategory.POSITIVE
        assert state.regimes["risk"].direction is DirectionCategory.POSITIVE

    def test_with_confidences(self):
        state = aggregate_from_dict(
            {"trend": "spike_up"},
            {"trend": 0.5},
        )
        assert state.regimes["trend"].confidence == 0.5

    def test_unknown_keys_ignored(self):
        state = aggregate_from_dict({"trend": "spike_up", "foo": "bar"})
        assert "foo" not in state.regimes
        assert len(state.regimes) == 4

    def test_empty_dict(self):
        state = aggregate_from_dict({})
        assert state.is_neutral


# ===========================================================================
# SECTION 34 — No scoring impact (inv 248)
# ===========================================================================


class TestSection34NoScoringImpact:
    def test_no_score_method(self):
        state = aggregate_regimes(trend_label="spike_up")
        assert not hasattr(state, "apply_to_score")
        assert not hasattr(state, "compute_factor")

    def test_no_factor_field(self):
        d = aggregate_regimes(trend_label="spike_up").to_dict()
        assert "factor" not in d
        assert "score" not in d


# ===========================================================================
# SECTION 35 — Boundary compliance
# ===========================================================================


class TestSection35Boundary:
    def test_no_os_import(self):
        import umh.runtime.regime_aggregation as mod
        import inspect

        src = inspect.getsource(mod)
        lines = [
            l.strip()
            for l in src.split("\n")
            if l.strip().startswith("import os") or l.strip().startswith("from os")
        ]
        assert len(lines) == 0

    def test_no_subprocess(self):
        import umh.runtime.regime_aggregation as mod
        import inspect

        src = inspect.getsource(mod)
        lines = [
            l.strip()
            for l in src.split("\n")
            if l.strip().startswith("import subprocess") or l.strip().startswith("from subprocess")
        ]
        assert len(lines) == 0

    def test_no_random(self):
        import umh.runtime.regime_aggregation as mod
        import inspect

        src = inspect.getsource(mod)
        assert "import random" not in src

    def test_no_cells_import(self):
        import umh.runtime.regime_aggregation as mod
        import inspect

        src = inspect.getsource(mod)
        assert "umh.cells" not in src
        assert "umh.environments" not in src
        assert "umh.adapters" not in src


# ===========================================================================
# SECTION 36 — Import surface
# ===========================================================================


class TestSection36ImportSurface:
    def test_from_init(self):
        from umh.runtime import (
            AggregatedRegimeState,
            DimensionName,
            DimensionRegime,
            DirectionCategory,
            NEUTRAL_AGGREGATED,
            aggregate_from_dict,
            aggregate_regimes,
            classify_dimension,
        )

        assert AggregatedRegimeState is not None
        assert DimensionName is not None
        assert DimensionRegime is not None
        assert DirectionCategory is not None
        assert NEUTRAL_AGGREGATED is not None


# ===========================================================================
# SECTION 37 — Orchestrator integration: aggregated_regime param
# ===========================================================================


class TestSection37OrchestratorParam:
    def test_default_none(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r = orchestrate_selection(["a"], [1.0])
        assert r.aggregated_regime is None

    def test_attached_to_result(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        agg = aggregate_regimes(trend_label="spike_up")
        r = orchestrate_selection(["a"], [1.0], aggregated_regime=agg)
        assert r.aggregated_regime is agg

    def test_no_scoring_change(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r_without = orchestrate_selection(["a", "b"], [0.8, 0.7])
        agg = aggregate_regimes(
            trend_label="spike_down",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        r_with = orchestrate_selection(["a", "b"], [0.8, 0.7], aggregated_regime=agg)
        assert r_without.selected_strategy == r_with.selected_strategy
        assert r_without.base_winner == r_with.base_winner


# ===========================================================================
# SECTION 38 — Orchestrator explanation includes aggregated regime
# ===========================================================================


class TestSection38OrchestratorExplanation:
    def test_explanation_includes_aggregated(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        agg = aggregate_regimes(trend_label="spike_up")
        r = orchestrate_selection(["a"], [1.0], aggregated_regime=agg)
        assert "aggregated_regime=" in r.explanation

    def test_explanation_without_aggregated(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r = orchestrate_selection(["a"], [1.0])
        assert "aggregated_regime=" not in r.explanation


# ===========================================================================
# SECTION 39 — Orchestrator to_dict includes aggregated regime
# ===========================================================================


class TestSection39OrchestratorDict:
    def test_dict_includes_aggregated(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        agg = aggregate_regimes(trend_label="spike_up")
        r = orchestrate_selection(["a"], [1.0], aggregated_regime=agg)
        d = r.to_dict()
        assert "aggregated_regime" in d
        assert d["aggregated_regime"]["regimes"]["trend"]["regime_label"] == "spike_up"

    def test_dict_excludes_when_none(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r = orchestrate_selection(["a"], [1.0])
        d = r.to_dict()
        assert "aggregated_regime" not in d


# ===========================================================================
# SECTION 40 — Phase 58 behavior unchanged
# ===========================================================================


class TestSection40Phase58Unchanged:
    def test_default_selection_unchanged(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r = orchestrate_selection(
            ["a", "b", "c"],
            [0.5, 0.8, 0.6],
        )
        assert r.selected_strategy == "b"
        assert r.used_regime is True
        assert r.used_feedback is False

    def test_regime_weighting_unchanged(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r = orchestrate_selection(
            ["a", "b"],
            [0.7, 0.8],
            regime_factors=[1.15, 0.85],
        )
        # a: 0.7*1.15=0.805, b: 0.8*0.85=0.68
        assert r.selected_strategy == "a"

    def test_result_fields_present(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r = orchestrate_selection(["a"], [1.0])
        assert hasattr(r, "base_winner")
        assert hasattr(r, "regime_winner")
        assert hasattr(r, "feedback_winner")
        assert hasattr(r, "changed_from_base")
        assert hasattr(r, "changed_from_regime")


# ===========================================================================
# SECTION 41 — Mixed alignment with neutrals
# ===========================================================================


class TestSection41MixedWithNeutrals:
    def test_two_positive_two_neutral(self):
        state = aggregate_regimes(
            trend_label="trend_up",
            risk_label="low",
            stability_label="medium",
            urgency_label="medium",
        )
        assert state.alignment_score == 1.0
        assert state.conflict_score == 0.0

    def test_one_pos_one_neg_two_neutral(self):
        state = aggregate_regimes(
            trend_label="trend_up",
            risk_label="high",
            stability_label="medium",
            urgency_label="medium",
        )
        assert state.alignment_score == 0.5
        assert state.conflict_score == 0.5


# ===========================================================================
# SECTION 42 — Alignment/conflict symmetry
# ===========================================================================


class TestSection42Symmetry:
    def test_alignment_plus_conflict_lte_one(self):
        state = aggregate_regimes(
            trend_label="spike_up",
            risk_label="high",
            stability_label="low",
            urgency_label="low",
        )
        assert state.alignment_score + state.conflict_score <= 1.0 + 1e-9

    def test_symmetric_for_even_split(self):
        state = aggregate_regimes(
            trend_label="trend_up",
            risk_label="low",
            stability_label="low",
            urgency_label="high",
        )
        assert abs(state.alignment_score - state.conflict_score) < 1e-9


# ===========================================================================
# SECTION 43 — Confidence affects dominant but not direction
# ===========================================================================


class TestSection43ConfidenceEffect:
    def test_low_confidence_still_directional(self):
        state = aggregate_regimes(
            trend_label="spike_up",
            trend_confidence=0.1,
        )
        assert state.regimes["trend"].direction is DirectionCategory.POSITIVE

    def test_low_confidence_reduces_dominant(self):
        state = aggregate_regimes(
            trend_label="spike_up",
            risk_label="high",
            trend_confidence=0.1,
            risk_confidence=0.9,
        )
        assert state.dominant_dimension is DimensionName.RISK


# ===========================================================================
# SECTION 44 — Stress: many combinations
# ===========================================================================


class TestSection44Stress:
    def test_all_trend_types(self):
        for label in ["stable", "trend_up", "trend_down", "spike_up", "spike_down"]:
            state = aggregate_regimes(trend_label=label)
            assert state.regimes["trend"].regime_label == label

    def test_all_risk_levels(self):
        for label in ["low", "medium", "high"]:
            state = aggregate_regimes(risk_label=label)
            assert state.regimes["risk"].regime_label == label


# ===========================================================================
# SECTION 45 — Explanation: no dominant when all neutral
# ===========================================================================


class TestSection45NoDominant:
    def test_explanation_says_no_dominant(self):
        state = aggregate_regimes()
        assert "no dominant dimension" in state.explanation

    def test_explanation_with_dominant(self):
        state = aggregate_regimes(trend_label="spike_up")
        assert "dominant=trend" in state.explanation


# ===========================================================================
# SECTION 46 — Independence: each dimension classified separately (inv 242)
# ===========================================================================


class TestSection46Independence:
    def test_trend_independent_of_risk(self):
        a = aggregate_regimes(trend_label="spike_up", risk_label="low")
        b = aggregate_regimes(trend_label="spike_up", risk_label="high")
        assert a.regimes["trend"].direction == b.regimes["trend"].direction
        assert a.regimes["trend"].strength == b.regimes["trend"].strength

    def test_risk_independent_of_stability(self):
        a = aggregate_regimes(risk_label="high", stability_label="high")
        b = aggregate_regimes(risk_label="high", stability_label="low")
        assert a.regimes["risk"].direction == b.regimes["risk"].direction


# ===========================================================================
# SECTION 47 — Edge: all dimensions same direction but different strength
# ===========================================================================


class TestSection47SameDirectionDiffStrength:
    def test_dominant_is_strongest(self):
        state = aggregate_regimes(
            trend_label="trend_up",  # strength=0.5
            risk_label="low",  # strength=0.2
            stability_label="high",  # strength=0.2
            urgency_label="low",  # strength=0.2
        )
        assert state.dominant_dimension is DimensionName.TREND

    def test_all_positive_full_alignment(self):
        state = aggregate_regimes(
            trend_label="trend_up",
            risk_label="low",
            stability_label="high",
            urgency_label="low",
        )
        assert state.alignment_score == 1.0


# ===========================================================================
# SECTION 48 — Edge: single non-neutral dimension
# ===========================================================================


class TestSection48SingleNonNeutral:
    def test_single_positive(self):
        state = aggregate_regimes(trend_label="spike_up")
        assert state.alignment_score == 1.0
        assert state.conflict_score == 0.0

    def test_single_negative(self):
        state = aggregate_regimes(risk_label="high")
        assert state.alignment_score == 1.0
        assert state.conflict_score == 0.0


# ===========================================================================
# SECTION 49 — Roundtrip: to_dict consistency
# ===========================================================================


class TestSection49Roundtrip:
    def test_regime_dicts_have_all_keys(self):
        state = aggregate_regimes(
            trend_label="spike_up",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        d = state.to_dict()
        for dim_key in ["trend", "risk", "stability", "urgency"]:
            rd = d["regimes"][dim_key]
            assert "dimension" in rd
            assert "direction" in rd
            assert "strength" in rd
            assert "confidence" in rd

    def test_dominant_in_dict(self):
        state = aggregate_regimes(trend_label="spike_up")
        d = state.to_dict()
        assert d["dominant_dimension"] == "trend"

    def test_none_dominant_in_dict(self):
        state = aggregate_regimes()
        d = state.to_dict()
        assert d["dominant_dimension"] is None


# ===========================================================================
# SECTION 50 — No randomness (inv 243)
# ===========================================================================


class TestSection50NoRandomness:
    def test_no_random_import(self):
        import umh.runtime.regime_aggregation as mod
        import inspect

        src = inspect.getsource(mod)
        assert "import random" not in src

    def test_repeated_calls_identical(self):
        results = [
            aggregate_regimes(
                trend_label="spike_up",
                risk_label="high",
                stability_label="low",
                urgency_label="medium",
            ).to_dict()
            for _ in range(10)
        ]
        for r in results[1:]:
            assert r == results[0]


# ===========================================================================
# SECTION 51 — Orchestrator: aggregated_regime does not affect scoring (inv 248)
# ===========================================================================


class TestSection51NoScoringImpact:
    def test_same_winner_with_and_without(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        ids = ["alpha", "beta", "gamma"]
        scores = [0.6, 0.9, 0.7]
        r1 = orchestrate_selection(ids, scores)
        agg = aggregate_regimes(
            trend_label="spike_down",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        r2 = orchestrate_selection(ids, scores, aggregated_regime=agg)
        assert r1.selected_strategy == r2.selected_strategy == "beta"

    def test_same_candidates_scores(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        ids = ["a", "b"]
        scores = [0.5, 0.8]
        r1 = orchestrate_selection(ids, scores)
        agg = aggregate_regimes(trend_label="spike_up")
        r2 = orchestrate_selection(ids, scores, aggregated_regime=agg)
        for c1, c2 in zip(r1.candidates, r2.candidates):
            assert c1.base_score == c2.base_score
            assert c1.regime_factor == c2.regime_factor


# ===========================================================================
# SECTION 52 — StrategySelectionResult: aggregated_regime field
# ===========================================================================


class TestSection52ResultField:
    def test_field_exists(self):
        from umh.runtime.strategy_orchestrator import StrategySelectionResult

        r = StrategySelectionResult()
        assert r.aggregated_regime is None

    def test_field_accepts_aggregated(self):
        from umh.runtime.strategy_orchestrator import StrategySelectionResult

        agg = aggregate_regimes(trend_label="spike_up")
        r = StrategySelectionResult(aggregated_regime=agg)
        assert r.aggregated_regime is agg


# ===========================================================================
# SECTION 53 — Alignment score formula verification
# ===========================================================================


class TestSection53AlignmentFormula:
    def test_three_of_four_positive(self):
        # 3 positive (trend_up, low risk, high stability), 1 negative (high urgency)
        # 3 non-neutral → majority=3, minority=1 → alignment=3/4=0.75, conflict=1/4=0.25
        state = aggregate_regimes(
            trend_label="trend_up",
            risk_label="low",
            stability_label="high",
            urgency_label="high",
        )
        assert abs(state.alignment_score - 0.75) < 1e-9
        assert abs(state.conflict_score - 0.25) < 1e-9

    def test_one_of_four_positive(self):
        # 1 positive (trend_up), 3 negative (high risk, low stability, high urgency)
        state = aggregate_regimes(
            trend_label="trend_up",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        assert abs(state.alignment_score - 0.75) < 1e-9
        assert abs(state.conflict_score - 0.25) < 1e-9


# ===========================================================================
# SECTION 54 — Dimension ordering in explanation
# ===========================================================================


class TestSection54ExplanationOrdering:
    def test_dimensions_in_alphabetical_order(self):
        state = aggregate_regimes(
            trend_label="spike_up",
            risk_label="high",
            stability_label="low",
            urgency_label="high",
        )
        exp = state.explanation
        risk_pos = exp.index("risk=")
        stability_pos = exp.index("stability=")
        trend_pos = exp.index("trend=")
        urgency_pos = exp.index("urgency=")
        assert risk_pos < stability_pos < trend_pos < urgency_pos


# ===========================================================================
# SECTION 55 — Full pipeline: orchestrator + aggregation integration
# ===========================================================================


class TestSection55FullPipeline:
    def test_full_pipeline(self):
        from umh.runtime.strategy_orchestrator import (
            StrategyOrchestrationPolicy,
            orchestrate_selection,
        )

        agg = aggregate_regimes(
            trend_label="spike_up",
            risk_label="low",
            stability_label="high",
            urgency_label="low",
        )
        r = orchestrate_selection(
            ["conservative", "aggressive"],
            [0.7, 0.8],
            regime_factors=[0.9, 1.1],
            aggregated_regime=agg,
        )
        assert r.selected_strategy in ("conservative", "aggressive")
        assert r.aggregated_regime is agg
        assert agg.is_aligned

    def test_full_pipeline_with_feedback(self):
        from umh.runtime.feedback_selection import FeedbackSelectionPolicy
        from umh.runtime.strategy_orchestrator import (
            StrategyOrchestrationPolicy,
            orchestrate_selection,
        )

        agg = aggregate_regimes(trend_label="trend_down", risk_label="high")
        policy = StrategyOrchestrationPolicy(
            use_feedback_selection=True,
            feedback_policy=FeedbackSelectionPolicy(enabled=True),
        )
        r = orchestrate_selection(
            ["a", "b"],
            [0.7, 0.75],
            regime_factors=[1.0, 1.0],
            feedback_factors=[1.1, 0.9],
            confidences=[0.8, 0.8],
            policy=policy,
            aggregated_regime=agg,
        )
        assert r.aggregated_regime is agg
        assert "aggregated_regime=" in r.explanation


# ===========================================================================
# SECTION 56 — Phase 57 feedback_selection unchanged
# ===========================================================================


class TestSection56Phase57Unchanged:
    def test_feedback_selection_import(self):
        from umh.runtime.feedback_selection import (
            FeedbackSelectionPolicy,
            select_with_feedback,
        )

        r = select_with_feedback(["a", "b"], [0.8, 0.6])
        assert r.selected_candidate == "a"

    def test_feedback_selection_policy_defaults(self):
        from umh.runtime.feedback_selection import FeedbackSelectionPolicy

        p = FeedbackSelectionPolicy()
        assert p.enabled is False
        assert p.min_confidence == 0.6


# ===========================================================================
# SECTION 57 — Phase 58 orchestrator unchanged (signature backward compat)
# ===========================================================================


class TestSection57Phase58Compat:
    def test_orchestrate_without_aggregated(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        r = orchestrate_selection(["a", "b"], [0.5, 0.8])
        assert r.selected_strategy == "b"
        assert r.aggregated_regime is None

    def test_existing_params_still_work(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection
        import inspect

        sig = inspect.signature(orchestrate_selection)
        for p in [
            "strategy_ids",
            "base_scores",
            "regime_factors",
            "feedback_factors",
            "confidences",
            "valid_flags",
            "safe_flags",
            "policy",
        ]:
            assert p in sig.parameters


# ===========================================================================
# SECTION 58 — Edge: unknown dimension labels
# ===========================================================================


class TestSection58UnknownLabels:
    def test_unknown_trend(self):
        r = classify_dimension(DimensionName.TREND, "xyz")
        assert r.direction is DirectionCategory.NEUTRAL
        assert r.regime_label == "neutral"

    def test_unknown_risk(self):
        r = classify_dimension(DimensionName.RISK, "xyz")
        assert r.direction is DirectionCategory.NEUTRAL
        assert r.regime_label == "neutral"

    def test_aggregate_with_unknowns(self):
        state = aggregate_regimes(
            trend_label="unknown",
            risk_label="garbage",
        )
        assert state.regimes["trend"].direction is DirectionCategory.NEUTRAL
        assert state.regimes["risk"].direction is DirectionCategory.NEUTRAL


# ===========================================================================
# SECTION 59 — Edge: empty aggregation (all None)
# ===========================================================================


class TestSection59EmptyAggregation:
    def test_all_none(self):
        state = aggregate_regimes()
        assert state.alignment_score == 0.0
        assert state.conflict_score == 0.0
        assert state.dominant_dimension is None

    def test_empty_dict(self):
        state = aggregate_from_dict({})
        assert state.is_neutral


# ===========================================================================
# SECTION 60 — DimensionRegime: regime_label stored correctly
# ===========================================================================


class TestSection60RegimeLabel:
    def test_known_label_preserved(self):
        r = classify_dimension(DimensionName.TREND, "spike_up")
        assert r.regime_label == "spike_up"

    def test_unknown_label_becomes_neutral(self):
        r = classify_dimension(DimensionName.TREND, "bogus")
        assert r.regime_label == "neutral"


# ===========================================================================
# SECTION 61 — Stress: 100 aggregations deterministic
# ===========================================================================


class TestSection61Stress:
    def test_hundred_aggregations(self):
        results = []
        for _ in range(100):
            state = aggregate_regimes(
                trend_label="spike_up",
                risk_label="high",
                stability_label="low",
                urgency_label="high",
            )
            results.append(state.to_dict())
        for r in results[1:]:
            assert r == results[0]


# ===========================================================================
# SECTION 62 — No execution methods (inv 248)
# ===========================================================================


class TestSection62NoExecution:
    def test_no_execute(self):
        import umh.runtime.regime_aggregation as mod

        assert not hasattr(mod, "execute")
        assert not hasattr(mod, "run")

    def test_no_io(self):
        import umh.runtime.regime_aggregation as mod
        import inspect

        src = inspect.getsource(mod)
        assert "open(" not in src
        assert "pathlib" not in src


# ===========================================================================
# SECTION 63 — Confidence interplay with alignment
# ===========================================================================


class TestSection63ConfidenceAlignment:
    def test_confidence_does_not_affect_alignment(self):
        a = aggregate_regimes(
            trend_label="spike_up",
            risk_label="low",
            trend_confidence=0.1,
            risk_confidence=0.1,
        )
        b = aggregate_regimes(
            trend_label="spike_up",
            risk_label="low",
            trend_confidence=1.0,
            risk_confidence=1.0,
        )
        assert a.alignment_score == b.alignment_score
        assert a.conflict_score == b.conflict_score

    def test_confidence_affects_dominant_only(self):
        a = aggregate_regimes(
            trend_label="spike_up",
            risk_label="high",
            trend_confidence=0.9,
            risk_confidence=0.1,
        )
        assert a.dominant_dimension is DimensionName.TREND

        b = aggregate_regimes(
            trend_label="spike_up",
            risk_label="high",
            trend_confidence=0.1,
            risk_confidence=0.9,
        )
        assert b.dominant_dimension is DimensionName.RISK


# ===========================================================================
# SECTION 64 — Orchestrator: aggregated_regime in empty selection
# ===========================================================================


class TestSection64EmptySelection:
    def test_empty_ids_no_aggregated(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        agg = aggregate_regimes(trend_label="spike_up")
        r = orchestrate_selection([], [], aggregated_regime=agg)
        assert r.selected_strategy == ""
        assert r.aggregated_regime is None

    def test_all_invalid_no_aggregated(self):
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        agg = aggregate_regimes(trend_label="spike_up")
        r = orchestrate_selection(
            ["a"],
            [1.0],
            valid_flags=[False],
            aggregated_regime=agg,
        )
        assert r.selected_strategy == ""
        assert r.aggregated_regime is None


# ===========================================================================
# SECTION 65 — Regression: existing __init__ exports still work
# ===========================================================================


class TestSection65InitExports:
    def test_strategy_orchestrator_exports(self):
        from umh.runtime import (
            StrategyCandidate,
            StrategyOrchestrationPolicy,
            StrategySelectionResult,
            orchestrate_selection,
        )

        assert StrategyCandidate is not None

    def test_feedback_selection_exports(self):
        from umh.runtime import (
            FeedbackSelectionPolicy,
            select_with_feedback,
        )

        assert FeedbackSelectionPolicy is not None

    def test_regime_aggregation_exports(self):
        from umh.runtime import (
            AggregatedRegimeState,
            DimensionName,
            DimensionRegime,
            DirectionCategory,
            NEUTRAL_AGGREGATED,
            aggregate_from_dict,
            aggregate_regimes,
            classify_dimension,
        )

        assert AggregatedRegimeState is not None
