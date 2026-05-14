"""Phase 38 — Context-Aware Tradeoff Weighting Layer v1.

Tests for:
  - ExecutionContext (creation, frozen, clamping, defaults, is_neutral, to_dict)
  - NEUTRAL_CONTEXT constant
  - WeightAdjustment (creation, frozen, to_dict)
  - WeightAdaptationResult (creation, frozen, to_dict, adjusted_weights)
  - WeightAdapter (creation, keyword properties, custom keywords)
  - Weight adaptation rules (urgency, risk, pressure, stability)
  - Keyword matching logic
  - Multiplier bounds ([0.5, 2.0])
  - Stability dampening
  - apply_context_weights convenience function
  - TradeoffEngine.resolve with context integration
  - TradeoffScorer.compute_factor with context
  - Context summary building
  - Combined signal interactions
  - Determinism and stability
  - Hard invariants 126-130
  - Explainability
  - Boundary / exports / compile
"""

from __future__ import annotations

import ast
import sys
from dataclasses import FrozenInstanceError

import pytest

sys.path.insert(0, "/opt/OS")


# ---------------------------------------------------------------------------
# Section 1: ExecutionContext creation
# ---------------------------------------------------------------------------


class TestExecutionContextCreation:
    def test_defaults(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext()
        assert ctx.urgency == 0.5
        assert ctx.risk_level == 0.5
        assert ctx.resource_pressure == 0.5
        assert ctx.stability_mode == 0.0

    def test_custom_values(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext(
            urgency=0.9, risk_level=0.2, resource_pressure=0.7, stability_mode=0.5
        )
        assert ctx.urgency == 0.9
        assert ctx.risk_level == 0.2
        assert ctx.resource_pressure == 0.7
        assert ctx.stability_mode == 0.5

    def test_frozen(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext()
        with pytest.raises(FrozenInstanceError):
            ctx.urgency = 0.8  # type: ignore[misc]

    def test_clamp_high(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext(
            urgency=1.5, risk_level=2.0, resource_pressure=99.0, stability_mode=5.0
        )
        assert ctx.urgency == 1.0
        assert ctx.risk_level == 1.0
        assert ctx.resource_pressure == 1.0
        assert ctx.stability_mode == 1.0

    def test_clamp_low(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext(
            urgency=-0.5, risk_level=-1.0, resource_pressure=-99.0, stability_mode=-1.0
        )
        assert ctx.urgency == 0.0
        assert ctx.risk_level == 0.0
        assert ctx.resource_pressure == 0.0
        assert ctx.stability_mode == 0.0

    def test_boundary_values(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext(
            urgency=0.0, risk_level=1.0, resource_pressure=0.0, stability_mode=1.0
        )
        assert ctx.urgency == 0.0
        assert ctx.risk_level == 1.0
        assert ctx.resource_pressure == 0.0
        assert ctx.stability_mode == 1.0


# ---------------------------------------------------------------------------
# Section 2: ExecutionContext properties and serialization
# ---------------------------------------------------------------------------


class TestExecutionContextProperties:
    def test_is_neutral_default(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext()
        assert ctx.is_neutral is True

    def test_is_neutral_non_default_urgency(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext(urgency=0.8)
        assert ctx.is_neutral is False

    def test_is_neutral_non_default_risk(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext(risk_level=0.1)
        assert ctx.is_neutral is False

    def test_is_neutral_non_default_pressure(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext(resource_pressure=0.9)
        assert ctx.is_neutral is False

    def test_is_neutral_non_default_stability(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext(stability_mode=0.1)
        assert ctx.is_neutral is False

    def test_to_dict(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext(urgency=0.7, risk_level=0.3)
        d = ctx.to_dict()
        assert d["urgency"] == 0.7
        assert d["risk_level"] == 0.3
        assert d["resource_pressure"] == 0.5
        assert d["stability_mode"] == 0.0
        assert d["is_neutral"] is False

    def test_to_dict_neutral(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext()
        d = ctx.to_dict()
        assert d["is_neutral"] is True


# ---------------------------------------------------------------------------
# Section 3: NEUTRAL_CONTEXT constant
# ---------------------------------------------------------------------------


class TestNeutralContext:
    def test_exists_and_neutral(self) -> None:
        from umh.runtime.context import NEUTRAL_CONTEXT

        assert NEUTRAL_CONTEXT.is_neutral is True

    def test_default_values(self) -> None:
        from umh.runtime.context import NEUTRAL_CONTEXT

        assert NEUTRAL_CONTEXT.urgency == 0.5
        assert NEUTRAL_CONTEXT.risk_level == 0.5
        assert NEUTRAL_CONTEXT.resource_pressure == 0.5
        assert NEUTRAL_CONTEXT.stability_mode == 0.0

    def test_frozen(self) -> None:
        from umh.runtime.context import NEUTRAL_CONTEXT

        with pytest.raises(FrozenInstanceError):
            NEUTRAL_CONTEXT.urgency = 1.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Section 4: WeightAdjustment
# ---------------------------------------------------------------------------


class TestWeightAdjustment:
    def test_creation(self) -> None:
        from umh.runtime.weighting import WeightAdjustment

        wa = WeightAdjustment(
            dimension_name="latency",
            base_weight=1.0,
            multiplier=1.3,
            adjusted_weight=1.3,
            reasons=("urgency boosted (0.90)",),
        )
        assert wa.dimension_name == "latency"
        assert wa.base_weight == 1.0
        assert wa.multiplier == 1.3
        assert wa.adjusted_weight == 1.3
        assert len(wa.reasons) == 1

    def test_frozen(self) -> None:
        from umh.runtime.weighting import WeightAdjustment

        wa = WeightAdjustment(
            dimension_name="x", base_weight=1.0, multiplier=1.0, adjusted_weight=1.0, reasons=()
        )
        with pytest.raises(FrozenInstanceError):
            wa.dimension_name = "y"  # type: ignore[misc]

    def test_to_dict(self) -> None:
        from umh.runtime.weighting import WeightAdjustment

        wa = WeightAdjustment(
            dimension_name="speed",
            base_weight=2.0,
            multiplier=1.24,
            adjusted_weight=2.48,
            reasons=("urgency boosted (0.90)",),
        )
        d = wa.to_dict()
        assert d["dimension_name"] == "speed"
        assert d["base_weight"] == 2.0
        assert d["multiplier"] == 1.24
        assert d["adjusted_weight"] == 2.48
        assert d["reasons"] == ["urgency boosted (0.90)"]

    def test_multiple_reasons(self) -> None:
        from umh.runtime.weighting import WeightAdjustment

        wa = WeightAdjustment(
            dimension_name="x",
            base_weight=1.0,
            multiplier=1.5,
            adjusted_weight=1.5,
            reasons=("urgency boosted (0.90)", "stability dampened (0.50)"),
        )
        assert len(wa.reasons) == 2


# ---------------------------------------------------------------------------
# Section 5: WeightAdaptationResult
# ---------------------------------------------------------------------------


class TestWeightAdaptationResult:
    def test_creation(self) -> None:
        from umh.runtime.weighting import WeightAdaptationResult, WeightAdjustment

        adj = WeightAdjustment(
            dimension_name="x",
            base_weight=1.0,
            multiplier=1.0,
            adjusted_weight=1.0,
            reasons=("no adjustment",),
        )
        result = WeightAdaptationResult(
            adjustments=(adj,),
            context_summary="neutral context; no weight adjustments",
            any_changed=False,
        )
        assert len(result.adjustments) == 1
        assert result.any_changed is False

    def test_frozen(self) -> None:
        from umh.runtime.weighting import WeightAdaptationResult

        result = WeightAdaptationResult(adjustments=(), context_summary="test", any_changed=False)
        with pytest.raises(FrozenInstanceError):
            result.any_changed = True  # type: ignore[misc]

    def test_to_dict(self) -> None:
        from umh.runtime.weighting import WeightAdaptationResult, WeightAdjustment

        adj = WeightAdjustment(
            dimension_name="cost",
            base_weight=1.0,
            multiplier=1.2,
            adjusted_weight=1.2,
            reasons=("pressure boosted",),
        )
        result = WeightAdaptationResult(
            adjustments=(adj,), context_summary="high pressure", any_changed=True
        )
        d = result.to_dict()
        assert d["any_changed"] is True
        assert len(d["adjustments"]) == 1
        assert d["context_summary"] == "high pressure"

    def test_adjusted_weights_property(self) -> None:
        from umh.runtime.weighting import WeightAdaptationResult, WeightAdjustment

        adj1 = WeightAdjustment(
            dimension_name="speed", base_weight=1.0, multiplier=1.3, adjusted_weight=1.3, reasons=()
        )
        adj2 = WeightAdjustment(
            dimension_name="cost", base_weight=2.0, multiplier=0.8, adjusted_weight=1.6, reasons=()
        )
        result = WeightAdaptationResult(
            adjustments=(adj1, adj2), context_summary="test", any_changed=True
        )
        weights = result.adjusted_weights
        assert weights["speed"] == 1.3
        assert weights["cost"] == 1.6


# ---------------------------------------------------------------------------
# Section 6: WeightAdapter creation
# ---------------------------------------------------------------------------


class TestWeightAdapterCreation:
    def test_default_keywords(self) -> None:
        from umh.runtime.weighting import WeightAdapter

        wa = WeightAdapter()
        assert "latency" in wa.urgency_keywords
        assert "speed" in wa.urgency_keywords
        assert "success" in wa.risk_keywords
        assert "stability" in wa.risk_keywords
        assert "efficiency" in wa.pressure_keywords
        assert "cost" in wa.pressure_keywords

    def test_custom_keywords(self) -> None:
        from umh.runtime.weighting import WeightAdapter

        wa = WeightAdapter(
            urgency_keywords=frozenset({"velocity"}),
            risk_keywords=frozenset({"danger"}),
            pressure_keywords=frozenset({"money"}),
        )
        assert wa.urgency_keywords == frozenset({"velocity"})
        assert wa.risk_keywords == frozenset({"danger"})
        assert wa.pressure_keywords == frozenset({"money"})


# ---------------------------------------------------------------------------
# Section 7: Urgency adaptation
# ---------------------------------------------------------------------------


class TestUrgencyAdaptation:
    def _make_profile(self) -> "TradeoffProfile":
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile

        return TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="latency", weight=1.0),
                TradeoffDimension(name="quality", weight=1.0),
            ),
            name="test",
        )

    def test_high_urgency_boosts_latency(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(self._make_profile(), ctx)

        latency_adj = next(a for a in result.adjustments if a.dimension_name == "latency")
        assert latency_adj.multiplier > 1.0
        assert any("urgency boosted" in r for r in latency_adj.reasons)

    def test_low_urgency_reduces_latency(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        ctx = ExecutionContext(urgency=0.1)
        result = adapter.adjust(self._make_profile(), ctx)

        latency_adj = next(a for a in result.adjustments if a.dimension_name == "latency")
        assert latency_adj.multiplier < 1.0
        assert any("urgency reduced" in r for r in latency_adj.reasons)

    def test_neutral_urgency_no_change(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        ctx = ExecutionContext(urgency=0.5)
        result = adapter.adjust(self._make_profile(), ctx)

        latency_adj = next(a for a in result.adjustments if a.dimension_name == "latency")
        assert abs(latency_adj.multiplier - 1.0) < 1e-6

    def test_urgency_does_not_affect_non_matching(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(self._make_profile(), ctx)

        quality_adj = next(a for a in result.adjustments if a.dimension_name == "quality")
        assert not any("urgency" in r for r in quality_adj.reasons)

    def test_urgency_strength_factor(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        ctx = ExecutionContext(urgency=1.0)
        result = adapter.adjust(self._make_profile(), ctx)

        latency_adj = next(a for a in result.adjustments if a.dimension_name == "latency")
        expected = 1.0 + (1.0 - 0.5) * 0.6
        assert abs(latency_adj.multiplier - expected) < 1e-6


# ---------------------------------------------------------------------------
# Section 8: Risk adaptation
# ---------------------------------------------------------------------------


class TestRiskAdaptation:
    def _make_profile(self) -> "TradeoffProfile":
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile

        return TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="safety", weight=1.0),
                TradeoffDimension(name="performance", weight=1.0),
            ),
            name="test",
        )

    def test_high_risk_boosts_safety(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        ctx = ExecutionContext(risk_level=0.9)
        result = adapter.adjust(self._make_profile(), ctx)

        safety_adj = next(a for a in result.adjustments if a.dimension_name == "safety")
        assert safety_adj.multiplier > 1.0
        assert any("risk boosted" in r for r in safety_adj.reasons)

    def test_low_risk_reduces_safety(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        ctx = ExecutionContext(risk_level=0.1)
        result = adapter.adjust(self._make_profile(), ctx)

        safety_adj = next(a for a in result.adjustments if a.dimension_name == "safety")
        assert safety_adj.multiplier < 1.0

    def test_risk_does_not_affect_non_matching(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        ctx = ExecutionContext(risk_level=0.9)
        result = adapter.adjust(self._make_profile(), ctx)

        perf_adj = next(a for a in result.adjustments if a.dimension_name == "performance")
        assert not any("risk" in r for r in perf_adj.reasons)


# ---------------------------------------------------------------------------
# Section 9: Pressure adaptation
# ---------------------------------------------------------------------------


class TestPressureAdaptation:
    def _make_profile(self) -> "TradeoffProfile":
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile

        return TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="cost_efficiency", weight=1.0),
                TradeoffDimension(name="accuracy", weight=1.0),
            ),
            name="test",
        )

    def test_high_pressure_boosts_efficiency(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        ctx = ExecutionContext(resource_pressure=0.9)
        result = adapter.adjust(self._make_profile(), ctx)

        cost_adj = next(a for a in result.adjustments if a.dimension_name == "cost_efficiency")
        assert cost_adj.multiplier > 1.0
        assert any("pressure boosted" in r for r in cost_adj.reasons)

    def test_low_pressure_reduces_efficiency(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        ctx = ExecutionContext(resource_pressure=0.1)
        result = adapter.adjust(self._make_profile(), ctx)

        cost_adj = next(a for a in result.adjustments if a.dimension_name == "cost_efficiency")
        assert cost_adj.multiplier < 1.0

    def test_pressure_strength_lower_than_urgency(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        ctx_pressure = ExecutionContext(resource_pressure=1.0)
        ctx_urgency = ExecutionContext(urgency=1.0)

        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile

        eff_profile = TradeoffProfile(
            dimensions=(TradeoffDimension(name="efficiency", weight=1.0),)
        )
        lat_profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))

        eff_result = adapter.adjust(eff_profile, ctx_pressure)
        lat_result = adapter.adjust(lat_profile, ctx_urgency)

        eff_mult = eff_result.adjustments[0].multiplier
        lat_mult = lat_result.adjustments[0].multiplier
        assert lat_mult > eff_mult


# ---------------------------------------------------------------------------
# Section 10: Stability dampening
# ---------------------------------------------------------------------------


class TestStabilityDampening:
    def test_stability_dampens_urgency_boost(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="speed", weight=1.0),))

        ctx_no_stab = ExecutionContext(urgency=1.0, stability_mode=0.0)
        ctx_with_stab = ExecutionContext(urgency=1.0, stability_mode=1.0)

        result_no = adapter.adjust(profile, ctx_no_stab)
        result_yes = adapter.adjust(profile, ctx_with_stab)

        mult_no = result_no.adjustments[0].multiplier
        mult_yes = result_yes.adjustments[0].multiplier

        assert mult_no > mult_yes
        assert mult_yes > 1.0

    def test_full_stability_halves_deviation(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))

        ctx = ExecutionContext(urgency=1.0, stability_mode=1.0)
        result = adapter.adjust(profile, ctx)

        raw_deviation = (1.0 - 0.5) * 0.6  # 0.3
        dampened_deviation = raw_deviation * (1.0 - 1.0 * 0.5)  # 0.15
        expected_multiplier = 1.0 + dampened_deviation  # 1.15

        assert abs(result.adjustments[0].multiplier - expected_multiplier) < 1e-6

    def test_stability_adds_reason(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="speed", weight=1.0),))
        ctx = ExecutionContext(urgency=0.9, stability_mode=0.5)
        result = adapter.adjust(profile, ctx)

        adj = result.adjustments[0]
        assert any("stability dampened" in r for r in adj.reasons)

    def test_zero_stability_no_dampening(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        ctx = ExecutionContext(urgency=0.9, stability_mode=0.0)
        result = adapter.adjust(profile, ctx)

        adj = result.adjustments[0]
        assert not any("stability" in r for r in adj.reasons)

    def test_stability_dampens_reduction_too(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))

        ctx_no_stab = ExecutionContext(urgency=0.1, stability_mode=0.0)
        ctx_with_stab = ExecutionContext(urgency=0.1, stability_mode=1.0)

        mult_no = adapter.adjust(profile, ctx_no_stab).adjustments[0].multiplier
        mult_yes = adapter.adjust(profile, ctx_with_stab).adjustments[0].multiplier

        assert mult_no < mult_yes  # dampening pushes reduction toward 1.0


# ---------------------------------------------------------------------------
# Section 11: Multiplier bounds
# ---------------------------------------------------------------------------


class TestMultiplierBounds:
    def test_multiplier_lower_bound(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        ctx = ExecutionContext(urgency=0.0)
        result = adapter.adjust(profile, ctx)
        assert result.adjustments[0].multiplier >= 0.5

    def test_multiplier_upper_bound(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        ctx = ExecutionContext(urgency=1.0)
        result = adapter.adjust(profile, ctx)
        assert result.adjustments[0].multiplier <= 2.0

    def test_combined_signals_still_bounded(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter(
            urgency_keywords=frozenset({"combo"}),
            risk_keywords=frozenset({"combo"}),
            pressure_keywords=frozenset({"combo"}),
        )
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="combo_test", weight=1.0),))
        ctx = ExecutionContext(urgency=1.0, risk_level=1.0, resource_pressure=1.0)
        result = adapter.adjust(profile, ctx)
        assert 0.5 <= result.adjustments[0].multiplier <= 2.0

    def test_all_low_signals_still_bounded(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter(
            urgency_keywords=frozenset({"combo"}),
            risk_keywords=frozenset({"combo"}),
            pressure_keywords=frozenset({"combo"}),
        )
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="combo_test", weight=1.0),))
        ctx = ExecutionContext(urgency=0.0, risk_level=0.0, resource_pressure=0.0)
        result = adapter.adjust(profile, ctx)
        assert 0.5 <= result.adjustments[0].multiplier <= 2.0


# ---------------------------------------------------------------------------
# Section 12: Keyword matching
# ---------------------------------------------------------------------------


class TestKeywordMatching:
    def test_substring_match(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(
            dimensions=(TradeoffDimension(name="response_latency_p99", weight=1.0),)
        )
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        assert result.adjustments[0].multiplier > 1.0

    def test_case_sensitive_name_with_lowercase_keyword(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="LATENCY", weight=1.0),))
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        assert result.adjustments[0].multiplier > 1.0

    def test_no_match_no_adjustment(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="throughput", weight=1.0),))
        ctx = ExecutionContext(urgency=0.9, risk_level=0.9, resource_pressure=0.9)
        result = adapter.adjust(profile, ctx)
        assert abs(result.adjustments[0].multiplier - 1.0) < 1e-6

    def test_multiple_keyword_hits_single_dimension(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(
            dimensions=(TradeoffDimension(name="fast_speed_latency", weight=1.0),)
        )
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        adj = result.adjustments[0]
        assert adj.multiplier > 1.0
        urgency_reasons = [r for r in adj.reasons if "urgency" in r]
        assert len(urgency_reasons) == 1


# ---------------------------------------------------------------------------
# Section 13: apply_context_weights convenience function
# ---------------------------------------------------------------------------


class TestApplyContextWeights:
    def test_neutral_context_returns_same_profile(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import apply_context_weights

        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        ctx = ExecutionContext()
        adjusted, result = apply_context_weights(profile, ctx)
        assert adjusted is profile
        assert result.any_changed is False

    def test_non_neutral_returns_new_profile(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import apply_context_weights

        profile = TradeoffProfile(
            dimensions=(TradeoffDimension(name="latency", weight=1.0),),
            name="original",
        )
        ctx = ExecutionContext(urgency=0.9)
        adjusted, result = apply_context_weights(profile, ctx)
        assert adjusted is not profile
        assert adjusted.name == "original_adapted"
        assert result.any_changed is True

    def test_adjusted_profile_preserves_dimension_structure(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import apply_context_weights

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="latency", direction="minimize", weight=2.0, tolerance=0.3),
                TradeoffDimension(name="quality", direction="maximize", weight=1.5, tolerance=0.1),
            ),
        )
        ctx = ExecutionContext(urgency=0.9)
        adjusted, _ = apply_context_weights(profile, ctx)

        lat_dim = next(d for d in adjusted.dimensions if d.name == "latency")
        assert lat_dim.direction == "minimize"
        assert lat_dim.tolerance == 0.3
        assert lat_dim.weight != 2.0

        qual_dim = next(d for d in adjusted.dimensions if d.name == "quality")
        assert qual_dim.direction == "maximize"
        assert qual_dim.tolerance == 0.1

    def test_custom_adapter_used(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter, apply_context_weights

        custom = WeightAdapter(urgency_keywords=frozenset({"custom_dim"}))
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="custom_dim", weight=1.0),))
        ctx = ExecutionContext(urgency=0.9)
        adjusted, result = apply_context_weights(profile, ctx, custom)
        assert result.any_changed is True

    def test_unnamed_profile_gets_adapted_name(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import apply_context_weights

        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="speed", weight=1.0),))
        ctx = ExecutionContext(urgency=0.9)
        adjusted, _ = apply_context_weights(profile, ctx)
        assert adjusted.name == "adapted"


# ---------------------------------------------------------------------------
# Section 14: Context summary building
# ---------------------------------------------------------------------------


class TestContextSummary:
    def test_neutral_summary(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="x", weight=1.0),))
        ctx = ExecutionContext()
        result = adapter.adjust(profile, ctx)
        assert "neutral" in result.context_summary

    def test_high_urgency_summary(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        assert "high urgency" in result.context_summary

    def test_high_risk_summary(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="safety", weight=1.0),))
        ctx = ExecutionContext(risk_level=0.9)
        result = adapter.adjust(profile, ctx)
        assert "high risk" in result.context_summary

    def test_high_pressure_summary(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="cost", weight=1.0),))
        ctx = ExecutionContext(resource_pressure=0.9)
        result = adapter.adjust(profile, ctx)
        assert "high resource pressure" in result.context_summary

    def test_stability_mode_summary(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="speed", weight=1.0),))
        ctx = ExecutionContext(urgency=0.9, stability_mode=0.8)
        result = adapter.adjust(profile, ctx)
        assert "stability mode active" in result.context_summary

    def test_no_matching_dims_summary(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="unrelated", weight=1.0),))
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        assert "no matching dimensions" in result.context_summary

    def test_low_signals_in_summary(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="x", weight=1.0),))
        ctx = ExecutionContext(urgency=0.1, risk_level=0.1, resource_pressure=0.1)
        result = adapter.adjust(profile, ctx)
        assert "low urgency" in result.context_summary
        assert "low risk" in result.context_summary
        assert "low resource pressure" in result.context_summary


# ---------------------------------------------------------------------------
# Section 15: TradeoffEngine.resolve with context
# ---------------------------------------------------------------------------


class TestTradeoffEngineContext:
    def test_resolve_without_context_unchanged(self) -> None:
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="latency", direction="minimize", weight=1.0),
                TradeoffDimension(name="quality", direction="maximize", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        candidates = {"a": {"latency": 0.3, "quality": 0.8}, "b": {"latency": 0.7, "quality": 0.4}}
        result = engine.resolve(candidates)
        assert result is not None

    def test_resolve_with_neutral_context_same_as_without(self) -> None:
        from umh.runtime.context import NEUTRAL_CONTEXT
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="latency", direction="minimize", weight=1.0),
                TradeoffDimension(name="quality", direction="maximize", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        candidates = {"a": {"latency": 0.3, "quality": 0.8}, "b": {"latency": 0.7, "quality": 0.4}}

        result_no_ctx = engine.resolve(candidates)
        result_with_ctx = engine.resolve(candidates, context=NEUTRAL_CONTEXT)

        assert result_no_ctx is not None
        assert result_with_ctx is not None
        assert result_no_ctx.best.candidate_id == result_with_ctx.best.candidate_id
        assert abs(result_no_ctx.best.weighted_score - result_with_ctx.best.weighted_score) < 1e-9

    def test_urgency_context_shifts_winner(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="latency", direction="minimize", weight=1.0),
                TradeoffDimension(name="quality", direction="maximize", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        candidates = {
            "fast": {"latency": 0.1, "quality": 0.4},
            "good": {"latency": 0.8, "quality": 0.9},
        }

        ctx_urgent = ExecutionContext(urgency=1.0)
        result = engine.resolve(candidates, context=ctx_urgent)
        assert result is not None
        assert result.best.candidate_id == "fast"

    def test_risk_context_shifts_winner(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="safety_score", direction="maximize", weight=1.0),
                TradeoffDimension(name="throughput", direction="maximize", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        candidates = {
            "safe": {"safety_score": 0.9, "throughput": 0.3},
            "fast": {"safety_score": 0.3, "throughput": 0.9},
        }

        ctx_risky = ExecutionContext(risk_level=1.0)
        result = engine.resolve(candidates, context=ctx_risky)
        assert result is not None
        assert result.best.candidate_id == "safe"

    def test_resolve_with_custom_adapter(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        custom = WeightAdapter(urgency_keywords=frozenset({"throughput"}))
        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="throughput", weight=1.0),
                TradeoffDimension(name="accuracy", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        candidates = {
            "a": {"throughput": 0.9, "accuracy": 0.4},
            "b": {"throughput": 0.4, "accuracy": 0.9},
        }

        ctx = ExecutionContext(urgency=1.0)
        result = engine.resolve(candidates, context=ctx, adapter=custom)
        assert result is not None
        assert result.best.candidate_id == "a"


# ---------------------------------------------------------------------------
# Section 16: TradeoffScorer.compute_factor with context
# ---------------------------------------------------------------------------


class TestTradeoffScorerContext:
    def test_scorer_passes_context_to_engine(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        ctx = ExecutionContext(urgency=0.9)
        influence = scorer.compute_factor(
            meta_goal_scores={"latency_score": 0.8, "quality_score": 0.5},
            candidate_id="test",
            context=ctx,
        )
        assert influence.factor != 0.0
        assert 0.85 <= influence.factor <= 1.15

    def test_scorer_without_context_same_as_before(self) -> None:
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=True)
        influence = scorer.compute_factor(
            meta_goal_scores={"score_a": 0.7},
            candidate_id="test",
        )
        assert influence.factor == 1.0

    def test_scorer_disabled_ignores_context(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffScorer

        scorer = TradeoffScorer(enabled=False)
        ctx = ExecutionContext(urgency=1.0)
        influence = scorer.compute_factor(
            meta_goal_scores={"latency": 0.9},
            candidate_id="test",
            context=ctx,
        )
        assert influence.factor == 1.0
        assert "disabled" in influence.reason


# ---------------------------------------------------------------------------
# Section 17: Combined signal interactions
# ---------------------------------------------------------------------------


class TestCombinedSignals:
    def test_urgency_plus_risk_multiple_dims(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="speed", weight=1.0),
                TradeoffDimension(name="safety", weight=1.0),
                TradeoffDimension(name="other", weight=1.0),
            )
        )
        ctx = ExecutionContext(urgency=0.9, risk_level=0.9)
        result = adapter.adjust(profile, ctx)

        speed_adj = next(a for a in result.adjustments if a.dimension_name == "speed")
        safety_adj = next(a for a in result.adjustments if a.dimension_name == "safety")
        other_adj = next(a for a in result.adjustments if a.dimension_name == "other")

        assert speed_adj.multiplier > 1.0
        assert safety_adj.multiplier > 1.0
        assert abs(other_adj.multiplier - 1.0) < 1e-6

    def test_opposing_signals_cancel(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter(
            urgency_keywords=frozenset({"dual"}),
            risk_keywords=frozenset({"dual"}),
        )
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="dual_metric", weight=1.0),))
        ctx_high_both = ExecutionContext(urgency=0.9, risk_level=0.9)
        result = adapter.adjust(profile, ctx_high_both)
        adj = result.adjustments[0]
        assert adj.multiplier > 1.0

        ctx_mixed = ExecutionContext(urgency=0.9, risk_level=0.1)
        result_mixed = adapter.adjust(profile, ctx_mixed)
        adj_mixed = result_mixed.adjustments[0]
        assert abs(adj_mixed.multiplier) < abs(adj.multiplier)

    def test_all_signals_high_with_stability(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter(
            urgency_keywords=frozenset({"all"}),
            risk_keywords=frozenset({"all"}),
            pressure_keywords=frozenset({"all"}),
        )
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="all_signals", weight=1.0),))
        ctx = ExecutionContext(
            urgency=1.0, risk_level=1.0, resource_pressure=1.0, stability_mode=1.0
        )
        result = adapter.adjust(profile, ctx)
        adj = result.adjustments[0]
        assert 0.5 <= adj.multiplier <= 2.0
        assert any("stability" in r for r in adj.reasons)


# ---------------------------------------------------------------------------
# Section 18: Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_inputs_same_output(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="latency", weight=1.0),
                TradeoffDimension(name="safety", weight=2.0),
            )
        )
        ctx = ExecutionContext(urgency=0.8, risk_level=0.7, stability_mode=0.3)

        results = [adapter.adjust(profile, ctx) for _ in range(10)]
        for r in results[1:]:
            for a1, a2 in zip(results[0].adjustments, r.adjustments):
                assert a1.multiplier == a2.multiplier
                assert a1.adjusted_weight == a2.adjusted_weight

    def test_resolve_deterministic_with_context(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="latency", weight=1.0),
                TradeoffDimension(name="quality", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        candidates = {"a": {"latency": 0.3, "quality": 0.8}, "b": {"latency": 0.7, "quality": 0.4}}
        ctx = ExecutionContext(urgency=0.9)

        results = [engine.resolve(candidates, context=ctx) for _ in range(10)]
        for r in results[1:]:
            assert r is not None and results[0] is not None
            assert r.best.candidate_id == results[0].best.candidate_id
            assert abs(r.best.weighted_score - results[0].best.weighted_score) < 1e-9


# ---------------------------------------------------------------------------
# Section 19: Hard invariants 126-130
# ---------------------------------------------------------------------------


class TestHardInvariants:
    def test_inv126_no_state_mutation(self) -> None:
        """Invariant 126: Weight adaptation must be pure (no state mutation)."""
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="speed", weight=1.0),
                TradeoffDimension(name="cost", weight=2.0),
            )
        )
        ctx = ExecutionContext(urgency=0.9)

        original_dims = profile.dimensions
        adapter.adjust(profile, ctx)
        assert profile.dimensions is original_dims
        assert profile.dimensions[0].weight == 1.0
        assert profile.dimensions[1].weight == 2.0

    def test_inv127_deterministic(self) -> None:
        """Invariant 127: No stochastic weight adaptation."""
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        ctx = ExecutionContext(urgency=0.85, risk_level=0.3, stability_mode=0.4)

        multipliers = set()
        for _ in range(50):
            r = adapter.adjust(profile, ctx)
            multipliers.add(round(r.adjustments[0].multiplier, 10))
        assert len(multipliers) == 1

    def test_inv128_bounded_multipliers(self) -> None:
        """Invariant 128: Weight multipliers bounded to [0.5, 2.0]."""
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter(
            urgency_keywords=frozenset({"x"}),
            risk_keywords=frozenset({"x"}),
            pressure_keywords=frozenset({"x"}),
        )
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="x", weight=1.0),))

        for u in [0.0, 0.5, 1.0]:
            for r in [0.0, 0.5, 1.0]:
                for p in [0.0, 0.5, 1.0]:
                    for s in [0.0, 0.5, 1.0]:
                        ctx = ExecutionContext(
                            urgency=u, risk_level=r, resource_pressure=p, stability_mode=s
                        )
                        result = adapter.adjust(profile, ctx)
                        m = result.adjustments[0].multiplier
                        assert 0.5 <= m <= 2.0, f"Out of bounds: {m} for u={u},r={r},p={p},s={s}"

    def test_inv129_explainable_reasons(self) -> None:
        """Invariant 129: Every weight adjustment must be explainable."""
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="speed", weight=1.0),
                TradeoffDimension(name="safety", weight=1.0),
                TradeoffDimension(name="cost", weight=1.0),
            )
        )
        ctx = ExecutionContext(
            urgency=0.9, risk_level=0.8, resource_pressure=0.7, stability_mode=0.3
        )
        result = adapter.adjust(profile, ctx)

        for adj in result.adjustments:
            assert len(adj.reasons) > 0
            for reason in adj.reasons:
                assert isinstance(reason, str)
                assert len(reason) > 0

    def test_inv130_no_io_no_subprocess(self) -> None:
        """Invariant 130: No I/O or subprocess in weighting or context modules."""
        source_files = [
            "/opt/OS/umh/runtime/context.py",
            "/opt/OS/umh/runtime/weighting.py",
        ]
        forbidden_modules = {"subprocess", "socket", "requests", "urllib", "http"}

        for path in source_files:
            with open(path) as f:
                source = f.read()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert alias.name not in forbidden_modules, f"{path} imports {alias.name}"
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        top = node.module.split(".")[0]
                        assert top not in forbidden_modules, f"{path} imports from {node.module}"


# ---------------------------------------------------------------------------
# Section 20: Explainability
# ---------------------------------------------------------------------------


class TestExplainability:
    def test_adjustment_has_dimension_name(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="speed", weight=1.0),
                TradeoffDimension(name="safety", weight=1.5),
            )
        )
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        names = [a.dimension_name for a in result.adjustments]
        assert "speed" in names
        assert "safety" in names

    def test_to_dict_round_trip(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        d = result.to_dict()

        assert "adjustments" in d
        assert "context_summary" in d
        assert "any_changed" in d
        assert len(d["adjustments"]) == 1
        adj_d = d["adjustments"][0]
        assert "dimension_name" in adj_d
        assert "reasons" in adj_d

    def test_context_to_dict_complete(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext(
            urgency=0.7, risk_level=0.3, resource_pressure=0.8, stability_mode=0.2
        )
        d = ctx.to_dict()
        assert set(d.keys()) == {
            "urgency",
            "risk_level",
            "resource_pressure",
            "stability_mode",
            "is_neutral",
        }


# ---------------------------------------------------------------------------
# Section 21: Boundary / edge cases
# ---------------------------------------------------------------------------


class TestBoundaryEdgeCases:
    def test_empty_profile(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=())
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        assert len(result.adjustments) == 0
        assert result.any_changed is False

    def test_single_dimension(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        assert len(result.adjustments) == 1
        assert result.any_changed is True

    def test_many_dimensions(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        dims = tuple(TradeoffDimension(name=f"dim_{i}", weight=1.0) for i in range(20))
        profile = TradeoffProfile(dimensions=dims)
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        assert len(result.adjustments) == 20

    def test_zero_weight_dimension(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=0.0),))
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        adj = result.adjustments[0]
        assert adj.adjusted_weight == 0.0

    def test_max_weight_dimension(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=10.0),))
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        adj = result.adjustments[0]
        assert adj.adjusted_weight > 10.0

    def test_deadzone_near_05(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        ctx = ExecutionContext(urgency=0.53)
        result = adapter.adjust(profile, ctx)
        adj = result.adjustments[0]
        assert abs(adj.multiplier - 1.0) < 1e-6

    def test_just_outside_deadzone(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        ctx = ExecutionContext(urgency=0.56)
        result = adapter.adjust(profile, ctx)
        adj = result.adjustments[0]
        assert adj.multiplier > 1.0


# ---------------------------------------------------------------------------
# Section 22: End-to-end pipeline
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_e2e_context_changes_engine_result(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="latency", direction="minimize", weight=1.0),
                TradeoffDimension(name="stability", direction="maximize", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)

        candidates = {
            "fast_risky": {"latency": 0.1, "stability": 0.3},
            "slow_stable": {"latency": 0.8, "stability": 0.9},
        }

        no_ctx = engine.resolve(candidates)
        assert no_ctx is not None

        urgent_ctx = ExecutionContext(urgency=1.0)
        urgent_result = engine.resolve(candidates, context=urgent_ctx)
        assert urgent_result is not None
        assert urgent_result.best.candidate_id == "fast_risky"

        risky_ctx = ExecutionContext(risk_level=1.0)
        risky_result = engine.resolve(candidates, context=risky_ctx)
        assert risky_result is not None
        assert risky_result.best.candidate_id == "slow_stable"

    def test_e2e_apply_and_resolve(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile
        from umh.runtime.weighting import apply_context_weights

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="speed", direction="maximize", weight=1.0),
                TradeoffDimension(name="safety", direction="maximize", weight=1.0),
            )
        )
        ctx = ExecutionContext(urgency=0.9)
        adapted_profile, adaptation_result = apply_context_weights(profile, ctx)

        assert adaptation_result.any_changed is True

        engine = TradeoffEngine(profile=adapted_profile)
        candidates = {"fast": {"speed": 0.9, "safety": 0.4}, "safe": {"speed": 0.4, "safety": 0.9}}
        result = engine.resolve(candidates)

        assert result is not None
        assert result.best.candidate_id == "fast"

    def test_e2e_stability_prevents_extreme_shifts(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="speed", weight=1.0),
                TradeoffDimension(name="reliability", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        candidates = {
            "fast": {"speed": 0.8, "reliability": 0.5},
            "reliable": {"speed": 0.5, "reliability": 0.8},
        }

        ctx_no_stab = ExecutionContext(urgency=1.0, stability_mode=0.0)
        ctx_full_stab = ExecutionContext(urgency=1.0, stability_mode=1.0)

        result_no = engine.resolve(candidates, context=ctx_no_stab)
        result_stab = engine.resolve(candidates, context=ctx_full_stab)

        assert result_no is not None and result_stab is not None
        score_gap_no = abs(result_no.ranked[0].weighted_score - result_no.ranked[1].weighted_score)
        score_gap_stab = abs(
            result_stab.ranked[0].weighted_score - result_stab.ranked[1].weighted_score
        )
        assert score_gap_stab < score_gap_no


# ---------------------------------------------------------------------------
# Section 23: Dependency boundary
# ---------------------------------------------------------------------------


class TestDependencyBoundary:
    def test_context_no_forbidden_imports(self) -> None:
        with open("/opt/OS/umh/runtime/context.py") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name
                elif isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module
                if module:
                    assert not module.startswith("umh.cells"), f"Forbidden import: {module}"
                    assert not module.startswith("umh.environments"), f"Forbidden import: {module}"
                    assert not module.startswith("umh.adapters"), f"Forbidden import: {module}"

    def test_weighting_no_forbidden_imports(self) -> None:
        with open("/opt/OS/umh/runtime/weighting.py") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name
                elif isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module
                if module:
                    assert not module.startswith("umh.cells"), f"Forbidden import: {module}"
                    assert not module.startswith("umh.environments"), f"Forbidden import: {module}"
                    assert not module.startswith("umh.adapters"), f"Forbidden import: {module}"


# ---------------------------------------------------------------------------
# Section 24: Exports and compilation
# ---------------------------------------------------------------------------


class TestExportsAndCompilation:
    def test_runtime_exports_context_types(self) -> None:
        from umh.runtime import ExecutionContext, NEUTRAL_CONTEXT

        assert ExecutionContext is not None
        assert NEUTRAL_CONTEXT is not None

    def test_runtime_exports_weighting_types(self) -> None:
        from umh.runtime import (
            WeightAdapter,
            WeightAdaptationResult,
            WeightAdjustment,
            apply_context_weights,
        )

        assert WeightAdapter is not None
        assert WeightAdaptationResult is not None
        assert WeightAdjustment is not None
        assert apply_context_weights is not None

    def test_context_py_compiles(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/context.py", doraise=True)

    def test_weighting_py_compiles(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/weighting.py", doraise=True)

    def test_tradeoff_py_compiles(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/tradeoff.py", doraise=True)

    def test_init_py_compiles(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/__init__.py", doraise=True)

    def test_all_exports_in_all_list(self) -> None:
        import umh.runtime as rt

        expected = [
            "ExecutionContext",
            "NEUTRAL_CONTEXT",
            "WeightAdapter",
            "WeightAdaptationResult",
            "WeightAdjustment",
            "apply_context_weights",
        ]
        for name in expected:
            assert name in rt.__all__, f"{name} not in __all__"


# ---------------------------------------------------------------------------
# Section 25: Additional coverage — context edge cases
# ---------------------------------------------------------------------------


class TestContextEdgeCases:
    def test_exact_default_values_are_neutral(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext(
            urgency=0.5, risk_level=0.5, resource_pressure=0.5, stability_mode=0.0
        )
        assert ctx.is_neutral is True

    def test_near_default_not_neutral(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext(urgency=0.5000001)
        assert ctx.is_neutral is False

    def test_all_max_values(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext(
            urgency=1.0, risk_level=1.0, resource_pressure=1.0, stability_mode=1.0
        )
        assert ctx.is_neutral is False
        assert ctx.urgency == 1.0

    def test_all_min_values(self) -> None:
        from umh.runtime.context import ExecutionContext

        ctx = ExecutionContext(
            urgency=0.0, risk_level=0.0, resource_pressure=0.0, stability_mode=0.0
        )
        assert ctx.is_neutral is False
        assert ctx.urgency == 0.0


# ---------------------------------------------------------------------------
# Section 26: Additional coverage — adapter behavior
# ---------------------------------------------------------------------------


class TestAdapterBehavior:
    def test_adjust_returns_correct_types(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdaptationResult, WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        assert isinstance(result, WeightAdaptationResult)
        assert isinstance(result.adjustments, tuple)

    def test_adjusted_weight_equals_base_times_multiplier(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=3.0),))
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        adj = result.adjustments[0]
        assert abs(adj.adjusted_weight - adj.base_weight * adj.multiplier) < 1e-9

    def test_no_adjustment_reason_when_neutral(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        ctx = ExecutionContext()
        result = adapter.adjust(profile, ctx)
        adj = result.adjustments[0]
        assert "no adjustment" in adj.reasons

    def test_multiple_dimensions_independent(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="latency", weight=1.0),
                TradeoffDimension(name="safety", weight=1.0),
                TradeoffDimension(name="efficiency", weight=1.0),
            )
        )
        ctx = ExecutionContext(urgency=0.9, risk_level=0.9, resource_pressure=0.9)
        result = adapter.adjust(profile, ctx)

        latency_adj = next(a for a in result.adjustments if a.dimension_name == "latency")
        safety_adj = next(a for a in result.adjustments if a.dimension_name == "safety")
        eff_adj = next(a for a in result.adjustments if a.dimension_name == "efficiency")

        assert any("urgency" in r for r in latency_adj.reasons)
        assert any("risk" in r for r in safety_adj.reasons)
        assert any("pressure" in r for r in eff_adj.reasons)

    def test_order_of_dimensions_preserved(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="z_dim", weight=1.0),
                TradeoffDimension(name="a_dim", weight=1.0),
                TradeoffDimension(name="m_dim", weight=1.0),
            )
        )
        ctx = ExecutionContext(urgency=0.9)
        result = adapter.adjust(profile, ctx)
        names = [a.dimension_name for a in result.adjustments]
        assert names == ["z_dim", "a_dim", "m_dim"]


# ---------------------------------------------------------------------------
# Section 27: Additional coverage — engine integration edge cases
# ---------------------------------------------------------------------------


class TestEngineIntegrationEdge:
    def test_single_candidate_with_context_still_resolves(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        engine = TradeoffEngine(profile=profile)
        candidates = {"only": {"latency": 0.7}}
        ctx = ExecutionContext(urgency=1.0)
        result = engine.resolve(candidates, context=ctx)
        assert result is not None
        assert result.best.candidate_id == "only"

    def test_context_with_no_dimensions_still_resolves(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffEngine, TradeoffProfile

        engine = TradeoffEngine(profile=TradeoffProfile(dimensions=()))
        candidates = {"a": {"x": 0.8}, "b": {"x": 0.4}}
        ctx = ExecutionContext(urgency=1.0)
        result = engine.resolve(candidates, context=ctx)
        assert result is not None

    def test_context_does_not_mutate_engine_profile(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        engine = TradeoffEngine(profile=profile)
        original_weight = engine.profile.dimensions[0].weight

        ctx = ExecutionContext(urgency=1.0)
        engine.resolve({"a": {"latency": 0.5}}, context=ctx)

        assert engine.profile.dimensions[0].weight == original_weight

    def test_profile_override_with_context(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        engine = TradeoffEngine()
        override_profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="speed", weight=1.0),
                TradeoffDimension(name="cost", weight=1.0),
            )
        )
        candidates = {"a": {"speed": 0.9, "cost": 0.3}, "b": {"speed": 0.3, "cost": 0.9}}
        ctx = ExecutionContext(urgency=1.0)
        result = engine.resolve(candidates, profile=override_profile, context=ctx)
        assert result is not None

    def test_pareto_filtering_still_works_with_context(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="latency", direction="minimize", weight=1.0),
                TradeoffDimension(name="quality", direction="maximize", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile, enable_pareto=True)
        candidates = {
            "a": {"latency": 0.1, "quality": 0.9},
            "dominated": {"latency": 0.9, "quality": 0.1},
        }
        ctx = ExecutionContext(urgency=0.7)
        result = engine.resolve(candidates, context=ctx)
        assert result is not None
        assert "dominated" in result.dominated

    def test_tolerance_filtering_with_context(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="speed", weight=1.0, tolerance=0.3),
                TradeoffDimension(name="safety", weight=1.0, tolerance=0.3),
            )
        )
        engine = TradeoffEngine(profile=profile)
        candidates = {"a": {"speed": 0.9, "safety": 0.9}, "b": {"speed": 0.1, "safety": 0.1}}
        ctx = ExecutionContext(urgency=0.8)
        result = engine.resolve(candidates, context=ctx)
        assert result is not None


# ---------------------------------------------------------------------------
# Section 28: Additional coverage — apply_context_weights edge cases
# ---------------------------------------------------------------------------


class TestApplyContextWeightsEdge:
    def test_non_matching_dimensions_unchanged(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import apply_context_weights

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="throughput", weight=2.0),
                TradeoffDimension(name="accuracy", weight=3.0),
            )
        )
        ctx = ExecutionContext(urgency=0.9, risk_level=0.9, resource_pressure=0.9)
        adjusted, result = apply_context_weights(profile, ctx)
        assert adjusted is profile

    def test_mixed_matching_and_non_matching(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import apply_context_weights

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="latency", weight=1.0),
                TradeoffDimension(name="throughput", weight=1.0),
            )
        )
        ctx = ExecutionContext(urgency=0.9)
        adjusted, result = apply_context_weights(profile, ctx)
        assert result.any_changed is True

        lat_dim = next(d for d in adjusted.dimensions if d.name == "latency")
        thr_dim = next(d for d in adjusted.dimensions if d.name == "throughput")
        assert lat_dim.weight > 1.0
        assert thr_dim.weight == 1.0

    def test_apply_preserves_dimension_count(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import apply_context_weights

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="speed", weight=1.0),
                TradeoffDimension(name="safety", weight=1.0),
                TradeoffDimension(name="cost", weight=1.0),
            )
        )
        ctx = ExecutionContext(urgency=0.9, risk_level=0.9, resource_pressure=0.9)
        adjusted, _ = apply_context_weights(profile, ctx)
        assert adjusted.dimension_count == 3


# ---------------------------------------------------------------------------
# Section 29: Additional stability and combined tests
# ---------------------------------------------------------------------------


class TestAdditionalStability:
    def test_partial_stability_dampening_computation(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))

        ctx = ExecutionContext(urgency=1.0, stability_mode=0.5)
        result = adapter.adjust(profile, ctx)

        raw_deviation = (1.0 - 0.5) * 0.6  # 0.3
        dampened = raw_deviation * (1.0 - 0.5 * 0.5)  # 0.3 * 0.75 = 0.225
        expected = 1.0 + dampened  # 1.225

        assert abs(result.adjustments[0].multiplier - expected) < 1e-6

    def test_stability_with_no_matching_dims_is_neutral(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="throughput", weight=1.0),))
        ctx = ExecutionContext(urgency=0.9, stability_mode=1.0)
        result = adapter.adjust(profile, ctx)
        assert abs(result.adjustments[0].multiplier - 1.0) < 1e-6

    def test_moderate_context_summary(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        ctx = ExecutionContext(urgency=0.6, risk_level=0.6, resource_pressure=0.6)
        result = adapter.adjust(profile, ctx)
        assert "moderate" in result.context_summary or "minor" in result.context_summary
