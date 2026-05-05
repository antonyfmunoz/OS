"""Phase 40 — Adaptive Temporal Smoothing Layer v1.

Tests for:
  - SignalProfile (creation, frozen, defaults, clamping, to_dict)
  - DEFAULT_SIGNAL_PROFILES constant
  - AdaptedAlpha (creation, frozen, to_dict)
  - AdaptationSnapshot (creation, frozen, to_dict, get_alpha)
  - compute_adapted_alpha (formula, bounds, delta sensitivity)
  - compute_all_adapted_alphas (all signals, custom profiles)
  - adaptive_smooth_context (per-signal alpha, output bounds)
  - ContextMemory.smooth_adaptive (first tick, multi tick, profiles)
  - Per-signal alpha differentiation
  - Volatility class behavior (low, medium, high)
  - Variance-driven adaptation
  - Cross-signal independence
  - Integration with WeightAdapter
  - Integration with TradeoffEngine
  - Determinism
  - Hard invariants 136-140
  - Dependency boundary
  - Exports and compilation
  - Phase 39 regression
"""

from __future__ import annotations

import ast
import sys
from dataclasses import FrozenInstanceError

import pytest

sys.path.insert(0, "/opt/OS")


# ---------------------------------------------------------------------------
# Section 1: SignalProfile creation
# ---------------------------------------------------------------------------


class TestSignalProfileCreation:
    def test_defaults(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        sp = SignalProfile(name="test")
        assert sp.name == "test"
        assert sp.volatility_class == "medium"
        assert sp.effective_base_alpha == 0.5
        assert sp.adaptation_strength == 0.3

    def test_high_volatility(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        sp = SignalProfile(name="urgency", volatility_class="high")
        assert sp.effective_base_alpha == 0.7

    def test_low_volatility(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        sp = SignalProfile(name="risk", volatility_class="low")
        assert sp.effective_base_alpha == 0.3

    def test_medium_volatility(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        sp = SignalProfile(name="pressure", volatility_class="medium")
        assert sp.effective_base_alpha == 0.5

    def test_custom_base_alpha(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        sp = SignalProfile(name="x", base_alpha=0.6)
        assert sp.effective_base_alpha == 0.6

    def test_custom_base_alpha_clamped_low(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        sp = SignalProfile(name="x", base_alpha=0.05)
        assert sp.effective_base_alpha == 0.2

    def test_custom_base_alpha_clamped_high(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        sp = SignalProfile(name="x", base_alpha=0.99)
        assert sp.effective_base_alpha == 0.8

    def test_invalid_volatility_corrected(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        sp = SignalProfile(name="x", volatility_class="extreme")
        assert sp.volatility_class == "medium"

    def test_frozen(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        sp = SignalProfile(name="x")
        with pytest.raises(FrozenInstanceError):
            sp.name = "y"  # type: ignore[misc]

    def test_custom_adaptation_strength(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        sp = SignalProfile(name="x", adaptation_strength=0.5)
        assert sp.adaptation_strength == 0.5

    def test_adaptation_strength_clamped(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        sp = SignalProfile(name="x", adaptation_strength=2.0)
        assert sp.adaptation_strength == 1.0

        sp2 = SignalProfile(name="x", adaptation_strength=-1.0)
        assert sp2.adaptation_strength == 0.0

    def test_to_dict(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        sp = SignalProfile(name="urgency", volatility_class="high")
        d = sp.to_dict()
        assert d["name"] == "urgency"
        assert d["volatility_class"] == "high"
        assert d["base_alpha"] == 0.7
        assert "adaptation_strength" in d


# ---------------------------------------------------------------------------
# Section 2: DEFAULT_SIGNAL_PROFILES
# ---------------------------------------------------------------------------


class TestDefaultSignalProfiles:
    def test_has_all_four_signals(self) -> None:
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES

        assert "urgency" in DEFAULT_SIGNAL_PROFILES
        assert "risk_level" in DEFAULT_SIGNAL_PROFILES
        assert "resource_pressure" in DEFAULT_SIGNAL_PROFILES
        assert "stability_mode" in DEFAULT_SIGNAL_PROFILES

    def test_urgency_is_high_volatility(self) -> None:
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES

        assert DEFAULT_SIGNAL_PROFILES["urgency"].volatility_class == "high"
        assert DEFAULT_SIGNAL_PROFILES["urgency"].effective_base_alpha == 0.7

    def test_risk_is_low_volatility(self) -> None:
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES

        assert DEFAULT_SIGNAL_PROFILES["risk_level"].volatility_class == "low"
        assert DEFAULT_SIGNAL_PROFILES["risk_level"].effective_base_alpha == 0.3

    def test_pressure_is_medium_volatility(self) -> None:
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES

        assert DEFAULT_SIGNAL_PROFILES["resource_pressure"].volatility_class == "medium"
        assert DEFAULT_SIGNAL_PROFILES["resource_pressure"].effective_base_alpha == 0.5

    def test_stability_is_low_volatility(self) -> None:
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES

        assert DEFAULT_SIGNAL_PROFILES["stability_mode"].volatility_class == "low"
        assert DEFAULT_SIGNAL_PROFILES["stability_mode"].effective_base_alpha == 0.3


# ---------------------------------------------------------------------------
# Section 3: AdaptedAlpha
# ---------------------------------------------------------------------------


class TestAdaptedAlpha:
    def test_creation(self) -> None:
        from umh.runtime.context_profile import AdaptedAlpha

        aa = AdaptedAlpha(
            signal_name="urgency", base_alpha=0.7, delta=0.5, adjustment=0.075, adapted_alpha=0.775
        )
        assert aa.signal_name == "urgency"
        assert aa.base_alpha == 0.7
        assert aa.delta == 0.5

    def test_frozen(self) -> None:
        from umh.runtime.context_profile import AdaptedAlpha

        aa = AdaptedAlpha(
            signal_name="x", base_alpha=0.5, delta=0.0, adjustment=0.0, adapted_alpha=0.5
        )
        with pytest.raises(FrozenInstanceError):
            aa.signal_name = "y"  # type: ignore[misc]

    def test_to_dict(self) -> None:
        from umh.runtime.context_profile import AdaptedAlpha

        aa = AdaptedAlpha(
            signal_name="risk", base_alpha=0.3, delta=0.1, adjustment=-0.045, adapted_alpha=0.255
        )
        d = aa.to_dict()
        assert d["signal_name"] == "risk"
        assert d["base_alpha"] == 0.3
        assert "delta" in d
        assert "adjustment" in d
        assert "adapted_alpha" in d


# ---------------------------------------------------------------------------
# Section 4: AdaptationSnapshot
# ---------------------------------------------------------------------------


class TestAdaptationSnapshot:
    def test_creation(self) -> None:
        from umh.runtime.context_profile import AdaptationSnapshot, AdaptedAlpha

        aa = AdaptedAlpha(
            signal_name="urgency", base_alpha=0.7, delta=0.0, adjustment=0.0, adapted_alpha=0.7
        )
        snap = AdaptationSnapshot(alphas={"urgency": aa}, tick=1)
        assert snap.tick == 1
        assert "urgency" in snap.alphas

    def test_frozen(self) -> None:
        from umh.runtime.context_profile import AdaptationSnapshot

        snap = AdaptationSnapshot(alphas={}, tick=0)
        with pytest.raises(FrozenInstanceError):
            snap.tick = 1  # type: ignore[misc]

    def test_get_alpha_exists(self) -> None:
        from umh.runtime.context_profile import AdaptationSnapshot, AdaptedAlpha

        aa = AdaptedAlpha(
            signal_name="urgency", base_alpha=0.7, delta=0.3, adjustment=0.015, adapted_alpha=0.715
        )
        snap = AdaptationSnapshot(alphas={"urgency": aa}, tick=1)
        assert snap.get_alpha("urgency") == 0.715

    def test_get_alpha_missing_returns_default(self) -> None:
        from umh.runtime.context_profile import AdaptationSnapshot

        snap = AdaptationSnapshot(alphas={}, tick=0)
        assert snap.get_alpha("nonexistent") == 0.5

    def test_to_dict(self) -> None:
        from umh.runtime.context_profile import AdaptationSnapshot, AdaptedAlpha

        aa = AdaptedAlpha(
            signal_name="risk", base_alpha=0.3, delta=0.0, adjustment=0.0, adapted_alpha=0.3
        )
        snap = AdaptationSnapshot(alphas={"risk": aa}, tick=5)
        d = snap.to_dict()
        assert d["tick"] == 5
        assert "risk" in d["alphas"]


# ---------------------------------------------------------------------------
# Section 5: compute_adapted_alpha
# ---------------------------------------------------------------------------


class TestComputeAdaptedAlpha:
    def test_zero_delta(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        sp = SignalProfile(name="x", volatility_class="medium")
        result = compute_adapted_alpha(sp, 0.5, 0.5)
        assert result.delta == 0.0
        assert result.adapted_alpha < sp.effective_base_alpha

    def test_large_delta_increases_alpha(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        sp = SignalProfile(name="x", volatility_class="medium")
        result = compute_adapted_alpha(sp, 1.0, 0.0)
        assert result.adapted_alpha > sp.effective_base_alpha

    def test_small_delta_decreases_alpha(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        sp = SignalProfile(name="x", volatility_class="medium")
        result = compute_adapted_alpha(sp, 0.5, 0.49)
        assert result.adapted_alpha < sp.effective_base_alpha

    def test_midpoint_delta_no_adjustment(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        sp = SignalProfile(name="x", volatility_class="medium", adaptation_strength=0.3)
        result = compute_adapted_alpha(sp, 0.75, 0.5)
        assert result.delta == pytest.approx(0.25)
        assert result.adjustment == pytest.approx(0.0)
        assert result.adapted_alpha == pytest.approx(sp.effective_base_alpha)

    def test_alpha_clamped_upper(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        sp = SignalProfile(name="x", volatility_class="high")
        result = compute_adapted_alpha(sp, 1.0, 0.0)
        assert result.adapted_alpha <= 0.8

    def test_alpha_clamped_lower(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        sp = SignalProfile(name="x", volatility_class="low")
        result = compute_adapted_alpha(sp, 0.5, 0.5)
        assert result.adapted_alpha >= 0.2

    def test_formula_exact(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        sp = SignalProfile(name="x", volatility_class="medium", adaptation_strength=0.3)
        result = compute_adapted_alpha(sp, 0.9, 0.3)
        delta = 0.6
        adjustment = (delta - 0.25) * 0.3
        expected = max(0.2, min(0.8, 0.5 + adjustment))
        assert result.adapted_alpha == pytest.approx(expected)

    def test_symmetric_delta(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        sp = SignalProfile(name="x", volatility_class="medium")
        r1 = compute_adapted_alpha(sp, 0.8, 0.2)
        r2 = compute_adapted_alpha(sp, 0.2, 0.8)
        assert r1.adapted_alpha == r2.adapted_alpha


# ---------------------------------------------------------------------------
# Section 6: compute_all_adapted_alphas
# ---------------------------------------------------------------------------


class TestComputeAllAdaptedAlphas:
    def test_computes_all_signals(self) -> None:
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES, compute_all_adapted_alphas

        current = {
            "urgency": 0.9,
            "risk_level": 0.5,
            "resource_pressure": 0.7,
            "stability_mode": 0.3,
        }
        previous = {
            "urgency": 0.5,
            "risk_level": 0.5,
            "resource_pressure": 0.5,
            "stability_mode": 0.3,
        }
        snap = compute_all_adapted_alphas(DEFAULT_SIGNAL_PROFILES, current, previous)

        assert "urgency" in snap.alphas
        assert "risk_level" in snap.alphas
        assert "resource_pressure" in snap.alphas
        assert "stability_mode" in snap.alphas

    def test_urgency_gets_higher_alpha(self) -> None:
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES, compute_all_adapted_alphas

        current = {
            "urgency": 0.9,
            "risk_level": 0.9,
            "resource_pressure": 0.9,
            "stability_mode": 0.9,
        }
        previous = {
            "urgency": 0.5,
            "risk_level": 0.5,
            "resource_pressure": 0.5,
            "stability_mode": 0.5,
        }
        snap = compute_all_adapted_alphas(DEFAULT_SIGNAL_PROFILES, current, previous)

        assert snap.get_alpha("urgency") > snap.get_alpha("risk_level")

    def test_custom_profiles(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_all_adapted_alphas

        custom = {"urgency": SignalProfile(name="urgency", volatility_class="low")}
        current = {"urgency": 0.9}
        previous = {"urgency": 0.5}
        snap = compute_all_adapted_alphas(custom, current, previous)

        assert snap.get_alpha("urgency") < 0.5

    def test_tick_recorded(self) -> None:
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES, compute_all_adapted_alphas

        current = {"urgency": 0.5}
        previous = {"urgency": 0.5}
        snap = compute_all_adapted_alphas(DEFAULT_SIGNAL_PROFILES, current, previous, tick=42)
        assert snap.tick == 42

    def test_missing_signal_uses_default(self) -> None:
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES, compute_all_adapted_alphas

        current = {}
        previous = {}
        snap = compute_all_adapted_alphas(DEFAULT_SIGNAL_PROFILES, current, previous)
        assert len(snap.alphas) == 4


# ---------------------------------------------------------------------------
# Section 7: adaptive_smooth_context
# ---------------------------------------------------------------------------


class TestAdaptiveSmoothContext:
    def test_per_signal_different_alphas(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import adaptive_smooth_context

        current = ExecutionContext(
            urgency=1.0, risk_level=1.0, resource_pressure=1.0, stability_mode=1.0
        )
        previous = ExecutionContext(
            urgency=0.0, risk_level=0.0, resource_pressure=0.0, stability_mode=0.0
        )
        smoothed, snapshot = adaptive_smooth_context(current, previous)

        assert smoothed.urgency > smoothed.risk_level
        assert smoothed.urgency > smoothed.stability_mode

    def test_returns_frozen_context(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import adaptive_smooth_context

        current = ExecutionContext(urgency=0.8)
        previous = ExecutionContext(urgency=0.2)
        smoothed, _ = adaptive_smooth_context(current, previous)

        with pytest.raises(FrozenInstanceError):
            smoothed.urgency = 0.0  # type: ignore[misc]

    def test_output_bounded(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import adaptive_smooth_context

        current = ExecutionContext(
            urgency=1.0, risk_level=0.0, resource_pressure=1.0, stability_mode=0.0
        )
        previous = ExecutionContext(
            urgency=0.0, risk_level=1.0, resource_pressure=0.0, stability_mode=1.0
        )
        smoothed, _ = adaptive_smooth_context(current, previous)

        assert 0.0 <= smoothed.urgency <= 1.0
        assert 0.0 <= smoothed.risk_level <= 1.0
        assert 0.0 <= smoothed.resource_pressure <= 1.0
        assert 0.0 <= smoothed.stability_mode <= 1.0

    def test_identical_inputs_preserved(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import adaptive_smooth_context

        ctx = ExecutionContext(
            urgency=0.6, risk_level=0.4, resource_pressure=0.7, stability_mode=0.2
        )
        smoothed, _ = adaptive_smooth_context(ctx, ctx)
        assert smoothed.urgency == pytest.approx(0.6)
        assert smoothed.risk_level == pytest.approx(0.4)

    def test_returns_snapshot(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import adaptive_smooth_context

        current = ExecutionContext(urgency=0.9)
        previous = ExecutionContext(urgency=0.1)
        _, snapshot = adaptive_smooth_context(current, previous, tick=7)
        assert snapshot.tick == 7
        assert "urgency" in snapshot.alphas

    def test_custom_profiles_used(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import adaptive_smooth_context
        from umh.runtime.context_profile import SignalProfile

        custom = {"urgency": SignalProfile(name="urgency", volatility_class="low")}
        current = ExecutionContext(urgency=1.0)
        previous = ExecutionContext(urgency=0.0)

        smoothed_custom, _ = adaptive_smooth_context(current, previous, profiles=custom)
        smoothed_default, _ = adaptive_smooth_context(current, previous)

        assert smoothed_custom.urgency < smoothed_default.urgency


# ---------------------------------------------------------------------------
# Section 8: ContextMemory.smooth_adaptive — first tick
# ---------------------------------------------------------------------------


class TestSmoothAdaptiveFirstTick:
    def test_first_tick_passthrough(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        raw = ExecutionContext(urgency=0.9, risk_level=0.2)
        result, snapshot = cm.smooth_adaptive(raw)

        assert result.smoothed.urgency == 0.9
        assert result.smoothed.risk_level == 0.2
        assert result.tick == 1

    def test_first_tick_sets_initialized(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.8))
        assert cm.initialized is True

    def test_first_tick_snapshot_has_base_alphas(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        _, snapshot = cm.smooth_adaptive(ExecutionContext(urgency=0.9))
        assert snapshot.get_alpha("urgency") == pytest.approx(0.7)
        assert snapshot.get_alpha("risk_level") == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Section 9: ContextMemory.smooth_adaptive — multi tick
# ---------------------------------------------------------------------------


class TestSmoothAdaptiveMultiTick:
    def test_second_tick_blends(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.0))
        result, _ = cm.smooth_adaptive(ExecutionContext(urgency=1.0))

        assert 0.0 < result.smoothed.urgency < 1.0

    def test_urgency_responds_faster_than_risk(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.0, risk_level=0.0))
        result, _ = cm.smooth_adaptive(ExecutionContext(urgency=1.0, risk_level=1.0))

        assert result.smoothed.urgency > result.smoothed.risk_level

    def test_convergence_to_sustained_signal(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.0))

        for _ in range(20):
            result, _ = cm.smooth_adaptive(ExecutionContext(urgency=1.0))

        assert result.smoothed.urgency > 0.99

    def test_tick_advances(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext())
        cm.smooth_adaptive(ExecutionContext())
        cm.smooth_adaptive(ExecutionContext())
        assert cm.tick == 3

    def test_previous_context_updated(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.3))
        result, _ = cm.smooth_adaptive(ExecutionContext(urgency=0.7))
        assert cm.previous_context.urgency == result.smoothed.urgency


# ---------------------------------------------------------------------------
# Section 10: Per-signal alpha differentiation
# ---------------------------------------------------------------------------


class TestPerSignalDifferentiation:
    def test_high_vol_signal_tracks_spike_fast(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.5, risk_level=0.5))
        result, _ = cm.smooth_adaptive(ExecutionContext(urgency=1.0, risk_level=1.0))

        urgency_delta = abs(result.smoothed.urgency - 0.5)
        risk_delta = abs(result.smoothed.risk_level - 0.5)
        assert urgency_delta > risk_delta

    def test_low_vol_signal_resists_noise(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(risk_level=0.5))

        cm.smooth_adaptive(ExecutionContext(risk_level=0.9))
        cm.smooth_adaptive(ExecutionContext(risk_level=0.1))
        result, _ = cm.smooth_adaptive(ExecutionContext(risk_level=0.5))

        assert abs(result.smoothed.risk_level - 0.5) < 0.25

    def test_medium_vol_between_high_and_low(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.0, risk_level=0.0, resource_pressure=0.0))
        result, _ = cm.smooth_adaptive(
            ExecutionContext(urgency=1.0, risk_level=1.0, resource_pressure=1.0)
        )

        assert result.smoothed.urgency > result.smoothed.resource_pressure
        assert result.smoothed.resource_pressure > result.smoothed.risk_level


# ---------------------------------------------------------------------------
# Section 11: Variance-driven adaptation
# ---------------------------------------------------------------------------


class TestVarianceDrivenAdaptation:
    def test_high_variance_increases_alpha(self) -> None:
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES, compute_all_adapted_alphas

        current = {"urgency": 1.0}
        previous = {"urgency": 0.0}
        snap = compute_all_adapted_alphas(DEFAULT_SIGNAL_PROFILES, current, previous)
        assert snap.get_alpha("urgency") > DEFAULT_SIGNAL_PROFILES["urgency"].effective_base_alpha

    def test_low_variance_decreases_alpha(self) -> None:
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES, compute_all_adapted_alphas

        current = {"urgency": 0.5}
        previous = {"urgency": 0.5}
        snap = compute_all_adapted_alphas(DEFAULT_SIGNAL_PROFILES, current, previous)
        assert snap.get_alpha("urgency") < DEFAULT_SIGNAL_PROFILES["urgency"].effective_base_alpha

    def test_moderate_variance_near_base(self) -> None:
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES, compute_all_adapted_alphas

        current = {"urgency": 0.75}
        previous = {"urgency": 0.5}
        snap = compute_all_adapted_alphas(DEFAULT_SIGNAL_PROFILES, current, previous)
        diff = abs(
            snap.get_alpha("urgency") - DEFAULT_SIGNAL_PROFILES["urgency"].effective_base_alpha
        )
        assert diff < 0.05


# ---------------------------------------------------------------------------
# Section 12: Cross-signal independence
# ---------------------------------------------------------------------------


class TestCrossSignalIndependence:
    def test_urgency_change_doesnt_affect_risk_alpha(self) -> None:
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES, compute_all_adapted_alphas

        base_current = {"urgency": 0.5, "risk_level": 0.5}
        base_previous = {"urgency": 0.5, "risk_level": 0.5}
        snap_base = compute_all_adapted_alphas(DEFAULT_SIGNAL_PROFILES, base_current, base_previous)

        changed_current = {"urgency": 1.0, "risk_level": 0.5}
        snap_changed = compute_all_adapted_alphas(
            DEFAULT_SIGNAL_PROFILES, changed_current, base_previous
        )

        assert snap_base.get_alpha("risk_level") == snap_changed.get_alpha("risk_level")

    def test_risk_change_doesnt_affect_urgency_alpha(self) -> None:
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES, compute_all_adapted_alphas

        base_current = {"urgency": 0.5, "risk_level": 0.5}
        base_previous = {"urgency": 0.5, "risk_level": 0.5}
        snap_base = compute_all_adapted_alphas(DEFAULT_SIGNAL_PROFILES, base_current, base_previous)

        changed_current = {"urgency": 0.5, "risk_level": 1.0}
        snap_changed = compute_all_adapted_alphas(
            DEFAULT_SIGNAL_PROFILES, changed_current, base_previous
        )

        assert snap_base.get_alpha("urgency") == snap_changed.get_alpha("urgency")


# ---------------------------------------------------------------------------
# Section 13: Integration with WeightAdapter
# ---------------------------------------------------------------------------


class TestWeightAdapterIntegration:
    def test_adaptive_smoothed_feeds_adapter(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.5))
        result, _ = cm.smooth_adaptive(ExecutionContext(urgency=0.9))

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="latency", weight=1.0),))
        adapt_result = adapter.adjust(profile, result.smoothed)
        assert adapt_result.adjustments[0].multiplier > 1.0

    def test_adaptive_vs_fixed_produces_different_weights(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile
        from umh.runtime.weighting import WeightAdapter

        cm_adaptive = ContextMemory()
        cm_fixed = ContextMemory(alpha=0.5)

        cm_adaptive.smooth_adaptive(ExecutionContext(urgency=0.5))
        cm_fixed.smooth(ExecutionContext(urgency=0.5))

        r_adaptive, _ = cm_adaptive.smooth_adaptive(ExecutionContext(urgency=0.9))
        r_fixed = cm_fixed.smooth(ExecutionContext(urgency=0.9))

        adapter = WeightAdapter()
        profile = TradeoffProfile(dimensions=(TradeoffDimension(name="speed", weight=1.0),))

        w_adaptive = adapter.adjust(profile, r_adaptive.smoothed).adjustments[0].multiplier
        w_fixed = adapter.adjust(profile, r_fixed.smoothed).adjustments[0].multiplier

        assert w_adaptive != w_fixed


# ---------------------------------------------------------------------------
# Section 14: Integration with TradeoffEngine
# ---------------------------------------------------------------------------


class TestTradeoffEngineIntegration:
    def test_adaptive_context_in_engine(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.5))
        smoothed = cm.smooth_adaptive(ExecutionContext(urgency=1.0))[0].smoothed

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="speed", weight=1.0),
                TradeoffDimension(name="safety", weight=1.0),
            )
        )
        engine = TradeoffEngine(profile=profile)
        candidates = {"fast": {"speed": 0.9, "safety": 0.3}, "safe": {"speed": 0.3, "safety": 0.9}}
        result = engine.resolve(candidates, context=smoothed)
        assert result is not None

    def test_full_pipeline_adaptive(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.tradeoff import TradeoffDimension, TradeoffEngine, TradeoffProfile
        from umh.runtime.weighting import apply_context_weights

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.5))
        smoothed = cm.smooth_adaptive(ExecutionContext(urgency=0.9))[0].smoothed

        profile = TradeoffProfile(
            dimensions=(
                TradeoffDimension(name="latency", direction="minimize", weight=1.0),
                TradeoffDimension(name="quality", direction="maximize", weight=1.0),
            )
        )
        adapted, _ = apply_context_weights(profile, smoothed)
        engine = TradeoffEngine(profile=adapted)
        candidates = {
            "fast": {"latency": 0.1, "quality": 0.4},
            "good": {"latency": 0.8, "quality": 0.9},
        }
        result = engine.resolve(candidates)
        assert result is not None


# ---------------------------------------------------------------------------
# Section 15: Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_inputs_same_output(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import adaptive_smooth_context

        c = ExecutionContext(urgency=0.9, risk_level=0.2)
        p = ExecutionContext(urgency=0.1, risk_level=0.8)
        results = [adaptive_smooth_context(c, p) for _ in range(10)]

        for s, snap in results[1:]:
            assert s.urgency == results[0][0].urgency
            assert s.risk_level == results[0][0].risk_level

    def test_memory_sequence_deterministic(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        def run_sequence() -> list[float]:
            cm = ContextMemory()
            vals = []
            for u in [0.1, 0.9, 0.3, 0.7, 0.5, 0.8, 0.2]:
                r, _ = cm.smooth_adaptive(ExecutionContext(urgency=u))
                vals.append(r.smoothed.urgency)
            return vals

        r1 = run_sequence()
        r2 = run_sequence()
        for v1, v2 in zip(r1, r2):
            assert v1 == v2

    def test_compute_adapted_alpha_deterministic(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        sp = SignalProfile(name="x", volatility_class="high")
        results = set()
        for _ in range(50):
            r = compute_adapted_alpha(sp, 0.8, 0.2)
            results.add(round(r.adapted_alpha, 15))
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Section 16: Hard invariants 136-140
# ---------------------------------------------------------------------------


class TestHardInvariants:
    def test_inv136_alpha_bounded_per_signal(self) -> None:
        """Invariant 136: Alpha must remain bounded per signal."""
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES, compute_all_adapted_alphas

        for u in [0.0, 0.25, 0.5, 0.75, 1.0]:
            for r in [0.0, 0.5, 1.0]:
                for p in [0.0, 0.5, 1.0]:
                    current = {
                        "urgency": u,
                        "risk_level": r,
                        "resource_pressure": p,
                        "stability_mode": 0.5,
                    }
                    previous = {
                        "urgency": 0.5,
                        "risk_level": 0.5,
                        "resource_pressure": 0.5,
                        "stability_mode": 0.5,
                    }
                    snap = compute_all_adapted_alphas(DEFAULT_SIGNAL_PROFILES, current, previous)
                    for name in snap.alphas:
                        alpha = snap.get_alpha(name)
                        assert 0.2 <= alpha <= 0.8, f"Alpha {alpha} out of bounds for {name}"

    def test_inv137_no_stochastic_alpha(self) -> None:
        """Invariant 137: No stochastic alpha changes."""
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES, compute_all_adapted_alphas

        current = {"urgency": 0.8, "risk_level": 0.3}
        previous = {"urgency": 0.2, "risk_level": 0.7}

        alphas = set()
        for _ in range(50):
            snap = compute_all_adapted_alphas(DEFAULT_SIGNAL_PROFILES, current, previous)
            alphas.add(round(snap.get_alpha("urgency"), 15))
        assert len(alphas) == 1

    def test_inv138_adaptation_deterministic(self) -> None:
        """Invariant 138: Adaptation must be deterministic."""
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        def run() -> list[tuple[float, float]]:
            cm = ContextMemory()
            results = []
            for u in [0.1, 0.9, 0.2, 0.8, 0.5]:
                r, snap = cm.smooth_adaptive(ExecutionContext(urgency=u, risk_level=0.5))
                results.append((r.smoothed.urgency, snap.get_alpha("urgency")))
            return results

        r1 = run()
        r2 = run()
        for (v1, a1), (v2, a2) in zip(r1, r2):
            assert v1 == v2
            assert a1 == a2

    def test_inv139_no_cross_signal_interference(self) -> None:
        """Invariant 139: No cross-signal interference."""
        from umh.runtime.context_profile import DEFAULT_SIGNAL_PROFILES, compute_all_adapted_alphas

        base = {"urgency": 0.5, "risk_level": 0.5, "resource_pressure": 0.5, "stability_mode": 0.5}
        prev = dict(base)

        snap1 = compute_all_adapted_alphas(DEFAULT_SIGNAL_PROFILES, base, prev)

        modified = dict(base)
        modified["urgency"] = 1.0
        snap2 = compute_all_adapted_alphas(DEFAULT_SIGNAL_PROFILES, modified, prev)

        assert snap1.get_alpha("risk_level") == snap2.get_alpha("risk_level")
        assert snap1.get_alpha("resource_pressure") == snap2.get_alpha("resource_pressure")
        assert snap1.get_alpha("stability_mode") == snap2.get_alpha("stability_mode")

    def test_inv140_neutral_stays_neutral(self) -> None:
        """Invariant 140: Neutral context must remain neutral."""
        from umh.runtime.context import NEUTRAL_CONTEXT
        from umh.runtime.context_memory import adaptive_smooth_context

        smoothed, _ = adaptive_smooth_context(NEUTRAL_CONTEXT, NEUTRAL_CONTEXT)
        assert smoothed.is_neutral is True

    def test_inv140_neutral_through_memory(self) -> None:
        """Invariant 140: Neutral through memory stays neutral."""
        from umh.runtime.context import NEUTRAL_CONTEXT
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        for _ in range(10):
            r, _ = cm.smooth_adaptive(NEUTRAL_CONTEXT)

        assert r.smoothed.is_neutral is True


# ---------------------------------------------------------------------------
# Section 17: Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_custom_profiles_falls_back_to_defaults(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import adaptive_smooth_context

        current = ExecutionContext(urgency=1.0)
        previous = ExecutionContext(urgency=0.0)
        smoothed, snapshot = adaptive_smooth_context(current, previous, profiles={})
        assert len(snapshot.alphas) == 4
        assert "urgency" in snapshot.alphas
        assert smoothed.urgency > 0.5

    def test_single_signal_profile(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import adaptive_smooth_context
        from umh.runtime.context_profile import SignalProfile

        profiles = {"urgency": SignalProfile(name="urgency", volatility_class="high")}
        current = ExecutionContext(urgency=1.0)
        previous = ExecutionContext(urgency=0.0)
        smoothed, snapshot = adaptive_smooth_context(current, previous, profiles=profiles)
        assert "urgency" in snapshot.alphas
        assert smoothed.urgency > 0.5

    def test_zero_adaptation_strength(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        sp = SignalProfile(name="x", volatility_class="medium", adaptation_strength=0.0)
        r = compute_adapted_alpha(sp, 1.0, 0.0)
        assert r.adapted_alpha == sp.effective_base_alpha

    def test_max_adaptation_strength(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        sp = SignalProfile(name="x", volatility_class="medium", adaptation_strength=1.0)
        r = compute_adapted_alpha(sp, 1.0, 0.0)
        assert 0.2 <= r.adapted_alpha <= 0.8

    def test_smooth_adaptive_after_reset(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.9))
        cm.reset()
        result, _ = cm.smooth_adaptive(ExecutionContext(urgency=0.7))
        assert result.smoothed.urgency == 0.7

    def test_smooth_adaptive_after_override(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.override(ExecutionContext(urgency=0.0))
        result, _ = cm.smooth_adaptive(ExecutionContext(urgency=1.0))
        assert 0.0 < result.smoothed.urgency < 1.0

    def test_mixed_smooth_and_smooth_adaptive(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.3))
        result, _ = cm.smooth_adaptive(ExecutionContext(urgency=0.9))
        assert 0.3 < result.smoothed.urgency < 0.9

    def test_smooth_result_alpha_is_zero_for_adaptive(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.5))
        result, _ = cm.smooth_adaptive(ExecutionContext(urgency=0.9))
        assert result.alpha == 0.0


# ---------------------------------------------------------------------------
# Section 18: Dependency boundary
# ---------------------------------------------------------------------------


class TestDependencyBoundary:
    def test_context_profile_no_forbidden_imports(self) -> None:
        with open("/opt/OS/umh/runtime/context_profile.py") as f:
            source = f.read()
        tree = ast.parse(source)
        forbidden = {"subprocess", "socket", "requests", "urllib", "http"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in forbidden
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden

    def test_context_profile_no_cells_envs_adapters(self) -> None:
        with open("/opt/OS/umh/runtime/context_profile.py") as f:
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
                    assert not module.startswith("umh.cells")
                    assert not module.startswith("umh.environments")
                    assert not module.startswith("umh.adapters")


# ---------------------------------------------------------------------------
# Section 19: Exports and compilation
# ---------------------------------------------------------------------------


class TestExportsAndCompilation:
    def test_runtime_exports_profile_types(self) -> None:
        from umh.runtime import (
            AdaptationSnapshot,
            AdaptedAlpha,
            DEFAULT_SIGNAL_PROFILES,
            SignalProfile,
            compute_adapted_alpha,
            compute_all_adapted_alphas,
        )

        assert SignalProfile is not None
        assert AdaptedAlpha is not None
        assert AdaptationSnapshot is not None
        assert DEFAULT_SIGNAL_PROFILES is not None
        assert compute_adapted_alpha is not None
        assert compute_all_adapted_alphas is not None

    def test_runtime_exports_adaptive_smooth(self) -> None:
        from umh.runtime import adaptive_smooth_context

        assert adaptive_smooth_context is not None

    def test_context_profile_compiles(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/context_profile.py", doraise=True)

    def test_context_memory_compiles(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/context_memory.py", doraise=True)

    def test_init_compiles(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/__init__.py", doraise=True)

    def test_all_new_exports_in_all_list(self) -> None:
        import umh.runtime as rt

        expected = [
            "AdaptationSnapshot",
            "AdaptedAlpha",
            "DEFAULT_SIGNAL_PROFILES",
            "SignalProfile",
            "adaptive_smooth_context",
            "compute_adapted_alpha",
            "compute_all_adapted_alphas",
        ]
        for name in expected:
            assert name in rt.__all__, f"{name} not in __all__"


# ---------------------------------------------------------------------------
# Section 20: Phase 39 regression
# ---------------------------------------------------------------------------


class TestPhase39Regression:
    def test_fixed_alpha_smooth_unchanged(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.0))
        r = cm.smooth(ExecutionContext(urgency=1.0))
        assert r.smoothed.urgency == pytest.approx(0.5)

    def test_smooth_context_function_unchanged(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import smooth_context

        c = ExecutionContext(urgency=1.0)
        p = ExecutionContext(urgency=0.0)
        result = smooth_context(c, p, 0.5)
        assert result.urgency == pytest.approx(0.5)

    def test_smooth_value_function_unchanged(self) -> None:
        from umh.runtime.context_memory import smooth_value

        assert smooth_value(1.0, 0.0, 0.5) == pytest.approx(0.5)

    def test_neutral_context_unchanged(self) -> None:
        from umh.runtime.context import NEUTRAL_CONTEXT

        assert NEUTRAL_CONTEXT.is_neutral is True

    def test_make_context_unchanged(self) -> None:
        from umh.runtime.context import make_context

        ctx = make_context(urgency=0.8)
        assert ctx.urgency == 0.8

    def test_reset_still_works(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext(urgency=0.9))
        r = cm.reset()
        assert r.smoothed.is_neutral is True
        assert r.was_reset is True

    def test_override_still_works(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        r = cm.override(ExecutionContext(urgency=0.7))
        assert r.smoothed.urgency == 0.7


# ---------------------------------------------------------------------------
# Section 21: Volatility class alpha spread
# ---------------------------------------------------------------------------


class TestVolatilityClassAlphaSpread:
    def test_high_volatility_base_alpha(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        p = SignalProfile(name="s", volatility_class="high")
        assert p.effective_base_alpha == pytest.approx(0.7)

    def test_medium_volatility_base_alpha(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        p = SignalProfile(name="s", volatility_class="medium")
        assert p.effective_base_alpha == pytest.approx(0.5)

    def test_low_volatility_base_alpha(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        p = SignalProfile(name="s", volatility_class="low")
        assert p.effective_base_alpha == pytest.approx(0.3)

    def test_high_more_responsive_than_medium(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        high = SignalProfile(name="h", volatility_class="high")
        med = SignalProfile(name="m", volatility_class="medium")
        ah = compute_adapted_alpha(high, 0.8, 0.2)
        am = compute_adapted_alpha(med, 0.8, 0.2)
        assert ah.adapted_alpha > am.adapted_alpha

    def test_medium_more_responsive_than_low(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        med = SignalProfile(name="m", volatility_class="medium")
        low = SignalProfile(name="l", volatility_class="low")
        am = compute_adapted_alpha(med, 0.8, 0.2)
        al = compute_adapted_alpha(low, 0.8, 0.2)
        assert am.adapted_alpha > al.adapted_alpha

    def test_spread_ordering_with_same_delta(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        for delta in [0.0, 0.25, 0.5, 0.75, 1.0]:
            high = compute_adapted_alpha(
                SignalProfile(name="h", volatility_class="high"), 0.5 + delta / 2, 0.5 - delta / 2
            )
            med = compute_adapted_alpha(
                SignalProfile(name="m", volatility_class="medium"), 0.5 + delta / 2, 0.5 - delta / 2
            )
            low = compute_adapted_alpha(
                SignalProfile(name="l", volatility_class="low"), 0.5 + delta / 2, 0.5 - delta / 2
            )
            assert high.adapted_alpha >= med.adapted_alpha
            assert med.adapted_alpha >= low.adapted_alpha


# ---------------------------------------------------------------------------
# Section 22: Multi-tick adaptive convergence
# ---------------------------------------------------------------------------


class TestMultiTickAdaptiveConvergence:
    def test_converges_to_constant_input(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        target = ExecutionContext(
            urgency=0.8, risk_level=0.3, resource_pressure=0.6, stability_mode=0.1
        )
        for _ in range(20):
            result, _ = cm.smooth_adaptive(target)
        assert result.smoothed.urgency == pytest.approx(0.8, abs=0.01)
        assert result.smoothed.risk_level == pytest.approx(0.3, abs=0.01)

    def test_fast_signal_converges_faster(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.0, risk_level=0.0))
        target = ExecutionContext(urgency=0.8, risk_level=0.8)
        r, _ = cm.smooth_adaptive(target)
        urgency_err = abs(r.smoothed.urgency - 0.8)
        risk_err = abs(r.smoothed.risk_level - 0.8)
        assert urgency_err < risk_err

    def test_oscillating_input_dampened(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.5))
        values = []
        for i in range(10):
            raw = ExecutionContext(urgency=0.0 if i % 2 == 0 else 1.0)
            r, _ = cm.smooth_adaptive(raw)
            values.append(r.smoothed.urgency)
        variance_smoothed = sum((v - 0.5) ** 2 for v in values) / len(values)
        assert variance_smoothed < 0.25

    def test_step_response_tracks_direction(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.0))
        prev = 0.0
        for _ in range(5):
            r, _ = cm.smooth_adaptive(ExecutionContext(urgency=1.0))
            assert r.smoothed.urgency >= prev
            prev = r.smoothed.urgency

    def test_adaptive_alpha_changes_across_ticks(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.0))
        _, snap1 = cm.smooth_adaptive(ExecutionContext(urgency=1.0))
        _, snap2 = cm.smooth_adaptive(ExecutionContext(urgency=1.0))
        alpha1 = snap1.get_alpha("urgency")
        alpha2 = snap2.get_alpha("urgency")
        assert alpha1 != alpha2


# ---------------------------------------------------------------------------
# Section 23: Adaptation strength effect
# ---------------------------------------------------------------------------


class TestAdaptationStrengthEffect:
    def test_zero_strength_gives_base_alpha(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        p = SignalProfile(name="s", volatility_class="medium", adaptation_strength=0.0)
        result = compute_adapted_alpha(p, 1.0, 0.0)
        assert result.adapted_alpha == pytest.approx(p.effective_base_alpha)

    def test_max_strength_gives_largest_adjustment(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        weak = SignalProfile(name="w", adaptation_strength=0.1)
        strong = SignalProfile(name="s", adaptation_strength=1.0)
        rw = compute_adapted_alpha(weak, 1.0, 0.0)
        rs = compute_adapted_alpha(strong, 1.0, 0.0)
        assert abs(rs.adjustment) > abs(rw.adjustment)

    def test_strength_scales_linearly_with_delta(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        p = SignalProfile(name="s", volatility_class="medium", adaptation_strength=0.5)
        r1 = compute_adapted_alpha(p, 0.5, 0.0)
        r2 = compute_adapted_alpha(p, 1.0, 0.0)
        adj_ratio = r2.adjustment / r1.adjustment if r1.adjustment != 0 else float("inf")
        delta_ratio = (1.0 - 0.25) / (0.5 - 0.25)
        assert adj_ratio == pytest.approx(delta_ratio)

    def test_negative_strength_clamped_to_zero(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        p = SignalProfile(name="s", adaptation_strength=-0.5)
        assert p.adaptation_strength == 0.0

    def test_strength_above_one_clamped(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        p = SignalProfile(name="s", adaptation_strength=2.0)
        assert p.adaptation_strength == 1.0


# ---------------------------------------------------------------------------
# Section 24: Snapshot tick tracking
# ---------------------------------------------------------------------------


class TestSnapshotTickTracking:
    def test_tick_increments_per_adaptive_call(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        _, s1 = cm.smooth_adaptive(ExecutionContext())
        _, s2 = cm.smooth_adaptive(ExecutionContext())
        _, s3 = cm.smooth_adaptive(ExecutionContext())
        assert s1.tick == 1
        assert s2.tick == 2
        assert s3.tick == 3

    def test_tick_tracks_between_smooth_and_adaptive(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext())
        cm.smooth(ExecutionContext())
        _, snap = cm.smooth_adaptive(ExecutionContext())
        assert snap.tick == 3

    def test_tick_tracks_after_reset(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext())
        cm.reset()
        _, snap = cm.smooth_adaptive(ExecutionContext())
        assert snap.tick == 3

    def test_snapshot_tick_matches_result_tick(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        r, s = cm.smooth_adaptive(ExecutionContext())
        assert r.tick == s.tick


# ---------------------------------------------------------------------------
# Section 25: SmoothingResult to_dict with adaptive
# ---------------------------------------------------------------------------


class TestSmoothingResultToDict:
    def test_adaptive_result_serializes(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        r, _ = cm.smooth_adaptive(ExecutionContext(urgency=0.7))
        d = r.to_dict()
        assert "smoothed" in d
        assert "raw" in d
        assert "tick" in d
        assert isinstance(d["alpha"], float)

    def test_snapshot_serializes(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext())
        _, snap = cm.smooth_adaptive(ExecutionContext(urgency=0.9))
        d = snap.to_dict()
        assert "alphas" in d
        assert "tick" in d
        assert all(
            k in d["alphas"]
            for k in ["urgency", "risk_level", "resource_pressure", "stability_mode"]
        )

    def test_adapted_alpha_to_dict_round_trip(self) -> None:
        from umh.runtime.context_profile import AdaptedAlpha

        a = AdaptedAlpha(
            signal_name="urgency", base_alpha=0.7, delta=0.5, adjustment=0.075, adapted_alpha=0.775
        )
        d = a.to_dict()
        assert d["signal_name"] == "urgency"
        assert d["adapted_alpha"] == 0.775

    def test_context_memory_to_dict_after_adaptive(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.6))
        d = cm.to_dict()
        assert d["initialized"] is True
        assert d["tick"] == 1


# ---------------------------------------------------------------------------
# Section 26: Custom profiles through ContextMemory
# ---------------------------------------------------------------------------


class TestCustomProfilesThroughMemory:
    def test_custom_profiles_used_in_smooth_adaptive(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.context_profile import SignalProfile

        profiles = {
            "urgency": SignalProfile(name="urgency", volatility_class="low"),
            "risk_level": SignalProfile(name="risk_level", volatility_class="high"),
            "resource_pressure": SignalProfile(name="resource_pressure", volatility_class="medium"),
            "stability_mode": SignalProfile(name="stability_mode", volatility_class="medium"),
        }
        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext())
        _, snap = cm.smooth_adaptive(
            ExecutionContext(urgency=0.9, risk_level=0.9), profiles=profiles
        )
        assert snap.get_alpha("urgency") < snap.get_alpha("risk_level")

    def test_profiles_dont_persist_between_calls(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.context_profile import SignalProfile

        custom = {
            "urgency": SignalProfile(name="urgency", volatility_class="low"),
            "risk_level": SignalProfile(name="risk_level", volatility_class="low"),
            "resource_pressure": SignalProfile(name="resource_pressure", volatility_class="low"),
            "stability_mode": SignalProfile(name="stability_mode", volatility_class="low"),
        }
        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext())
        _, snap1 = cm.smooth_adaptive(ExecutionContext(urgency=0.9), profiles=custom)
        _, snap2 = cm.smooth_adaptive(ExecutionContext(urgency=0.9))
        a1 = snap1.get_alpha("urgency")
        a2 = snap2.get_alpha("urgency")
        assert a1 != a2

    def test_none_profiles_uses_defaults(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext())
        _, snap = cm.smooth_adaptive(ExecutionContext(urgency=0.9), profiles=None)
        assert snap.get_alpha("urgency") > snap.get_alpha("risk_level")


# ---------------------------------------------------------------------------
# Section 27: Delta midpoint behavior
# ---------------------------------------------------------------------------


class TestDeltaMidpointBehavior:
    def test_below_midpoint_decreases_alpha(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        p = SignalProfile(name="s", volatility_class="medium")
        r = compute_adapted_alpha(p, 0.5, 0.4)
        assert r.adjustment < 0

    def test_above_midpoint_increases_alpha(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        p = SignalProfile(name="s", volatility_class="medium")
        r = compute_adapted_alpha(p, 0.5, 0.0)
        assert r.adjustment > 0

    def test_at_midpoint_zero_adjustment(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        p = SignalProfile(name="s", volatility_class="medium")
        r = compute_adapted_alpha(p, 0.75, 0.5)
        assert r.adjustment == pytest.approx(0.0)

    def test_adjustment_magnitude_proportional_to_delta_distance(self) -> None:
        from umh.runtime.context_profile import SignalProfile, compute_adapted_alpha

        p = SignalProfile(name="s", volatility_class="medium", adaptation_strength=0.5)
        r1 = compute_adapted_alpha(p, 0.6, 0.0)
        r2 = compute_adapted_alpha(p, 0.8, 0.0)
        assert abs(r2.adjustment) > abs(r1.adjustment)


# ---------------------------------------------------------------------------
# Section 28: Effective base alpha property
# ---------------------------------------------------------------------------


class TestEffectiveBaseAlpha:
    def test_effective_base_alpha_from_volatility(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        p = SignalProfile(name="s", volatility_class="high")
        assert p.effective_base_alpha == pytest.approx(0.7)

    def test_effective_base_alpha_from_custom(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        p = SignalProfile(name="s", base_alpha=0.6)
        assert p.effective_base_alpha == pytest.approx(0.6)

    def test_effective_base_alpha_clamped_custom(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        p = SignalProfile(name="s", base_alpha=0.1)
        assert p.effective_base_alpha == pytest.approx(0.2)

    def test_signal_profile_to_dict_roundtrip(self) -> None:
        from umh.runtime.context_profile import SignalProfile

        p = SignalProfile(name="urgency", volatility_class="high", adaptation_strength=0.4)
        d = p.to_dict()
        assert d["name"] == "urgency"
        assert d["volatility_class"] == "high"
        assert d["base_alpha"] == pytest.approx(0.7)
        assert d["adaptation_strength"] == pytest.approx(0.4)
