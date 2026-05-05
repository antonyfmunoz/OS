"""Phase 42 — Temporal Regime Classification Layer v1.

Tests for:
  - RegimeType enum (values, members)
  - RegimeThresholds (defaults, clamping, to_dict)
  - RegimeResult (creation, frozen, properties, to_dict)
  - RegimeSnapshot (creation, frozen, accessors, aggregation)
  - classify_regime (STABLE, TREND_UP, TREND_DOWN, SPIKE_UP, SPIKE_DOWN)
  - classify_all_regimes (multi-signal, custom thresholds)
  - classify_from_horizon (HorizonSnapshot integration)
  - Threshold boundary behavior
  - No oscillation under small noise
  - Sign direction correctness
  - Determinism
  - Hard invariants 146-150
  - Custom thresholds
  - Edge cases
  - Serialization
  - Dependency boundary
  - Exports and compilation
  - Phase 41 regression
"""

from __future__ import annotations

import ast
import sys
from dataclasses import FrozenInstanceError

import pytest

sys.path.insert(0, "/opt/OS")


# ---------------------------------------------------------------------------
# Section 1: RegimeType enum
# ---------------------------------------------------------------------------


class TestRegimeType:
    def test_stable_value(self) -> None:
        from umh.runtime.regime import RegimeType

        assert RegimeType.STABLE.value == "stable"

    def test_trend_up_value(self) -> None:
        from umh.runtime.regime import RegimeType

        assert RegimeType.TREND_UP.value == "trend_up"

    def test_trend_down_value(self) -> None:
        from umh.runtime.regime import RegimeType

        assert RegimeType.TREND_DOWN.value == "trend_down"

    def test_spike_up_value(self) -> None:
        from umh.runtime.regime import RegimeType

        assert RegimeType.SPIKE_UP.value == "spike_up"

    def test_spike_down_value(self) -> None:
        from umh.runtime.regime import RegimeType

        assert RegimeType.SPIKE_DOWN.value == "spike_down"

    def test_five_members(self) -> None:
        from umh.runtime.regime import RegimeType

        assert len(RegimeType) == 5

    def test_from_value(self) -> None:
        from umh.runtime.regime import RegimeType

        assert RegimeType("stable") is RegimeType.STABLE
        assert RegimeType("spike_up") is RegimeType.SPIKE_UP


# ---------------------------------------------------------------------------
# Section 2: RegimeThresholds
# ---------------------------------------------------------------------------


class TestRegimeThresholds:
    def test_defaults(self) -> None:
        from umh.runtime.regime import RegimeThresholds

        t = RegimeThresholds()
        assert t.spike_threshold == pytest.approx(0.25)
        assert t.trend_threshold == pytest.approx(0.08)

    def test_custom(self) -> None:
        from umh.runtime.regime import RegimeThresholds

        t = RegimeThresholds(spike_threshold=0.3, trend_threshold=0.1)
        assert t.spike_threshold == pytest.approx(0.3)
        assert t.trend_threshold == pytest.approx(0.1)

    def test_frozen(self) -> None:
        from umh.runtime.regime import RegimeThresholds

        t = RegimeThresholds()
        with pytest.raises(FrozenInstanceError):
            t.spike_threshold = 0.5  # type: ignore[misc]

    def test_spike_clamped_low(self) -> None:
        from umh.runtime.regime import RegimeThresholds

        t = RegimeThresholds(spike_threshold=0.001)
        assert t.spike_threshold >= 0.01

    def test_spike_clamped_high(self) -> None:
        from umh.runtime.regime import RegimeThresholds

        t = RegimeThresholds(spike_threshold=5.0)
        assert t.spike_threshold <= 1.0

    def test_trend_cannot_exceed_spike(self) -> None:
        from umh.runtime.regime import RegimeThresholds

        t = RegimeThresholds(spike_threshold=0.2, trend_threshold=0.3)
        assert t.trend_threshold < t.spike_threshold

    def test_to_dict(self) -> None:
        from umh.runtime.regime import RegimeThresholds

        t = RegimeThresholds()
        d = t.to_dict()
        assert d["spike_threshold"] == 0.25
        assert d["trend_threshold"] == 0.08

    def test_default_thresholds_constant(self) -> None:
        from umh.runtime.regime import DEFAULT_THRESHOLDS

        assert DEFAULT_THRESHOLDS.spike_threshold == pytest.approx(0.25)
        assert DEFAULT_THRESHOLDS.trend_threshold == pytest.approx(0.08)


# ---------------------------------------------------------------------------
# Section 3: RegimeResult creation
# ---------------------------------------------------------------------------


class TestRegimeResultCreation:
    def test_stable(self) -> None:
        from umh.runtime.regime import RegimeResult, RegimeType

        r = RegimeResult(
            signal_name="urgency",
            regime=RegimeType.STABLE,
            delta=0.02,
            magnitude=0.02,
            is_spike=False,
            is_trend=False,
        )
        assert r.signal_name == "urgency"
        assert r.regime is RegimeType.STABLE
        assert r.is_stable is True

    def test_spike_up(self) -> None:
        from umh.runtime.regime import RegimeResult, RegimeType

        r = RegimeResult(
            signal_name="urgency",
            regime=RegimeType.SPIKE_UP,
            delta=0.4,
            magnitude=0.4,
            is_spike=True,
            is_trend=False,
        )
        assert r.is_spike is True
        assert r.is_up is True
        assert r.is_down is False

    def test_spike_down(self) -> None:
        from umh.runtime.regime import RegimeResult, RegimeType

        r = RegimeResult(
            signal_name="urgency",
            regime=RegimeType.SPIKE_DOWN,
            delta=-0.4,
            magnitude=0.4,
            is_spike=True,
            is_trend=False,
        )
        assert r.is_spike is True
        assert r.is_down is True
        assert r.is_up is False

    def test_trend_up(self) -> None:
        from umh.runtime.regime import RegimeResult, RegimeType

        r = RegimeResult(
            signal_name="urgency",
            regime=RegimeType.TREND_UP,
            delta=0.15,
            magnitude=0.15,
            is_spike=False,
            is_trend=True,
        )
        assert r.is_trend is True
        assert r.is_up is True

    def test_trend_down(self) -> None:
        from umh.runtime.regime import RegimeResult, RegimeType

        r = RegimeResult(
            signal_name="urgency",
            regime=RegimeType.TREND_DOWN,
            delta=-0.15,
            magnitude=0.15,
            is_spike=False,
            is_trend=True,
        )
        assert r.is_trend is True
        assert r.is_down is True

    def test_frozen(self) -> None:
        from umh.runtime.regime import RegimeResult, RegimeType

        r = RegimeResult(
            signal_name="x",
            regime=RegimeType.STABLE,
            delta=0.0,
            magnitude=0.0,
            is_spike=False,
            is_trend=False,
        )
        with pytest.raises(FrozenInstanceError):
            r.delta = 0.5  # type: ignore[misc]

    def test_to_dict(self) -> None:
        from umh.runtime.regime import RegimeResult, RegimeType

        r = RegimeResult(
            signal_name="urgency",
            regime=RegimeType.SPIKE_UP,
            delta=0.35,
            magnitude=0.35,
            is_spike=True,
            is_trend=False,
        )
        d = r.to_dict()
        assert d["signal_name"] == "urgency"
        assert d["regime"] == "spike_up"
        assert d["delta"] == 0.35
        assert d["magnitude"] == 0.35
        assert d["is_spike"] is True
        assert d["is_trend"] is False


# ---------------------------------------------------------------------------
# Section 4: RegimeResult properties
# ---------------------------------------------------------------------------


class TestRegimeResultProperties:
    def test_is_stable_true(self) -> None:
        from umh.runtime.regime import classify_regime

        r = classify_regime("x", 0.0)
        assert r.is_stable is True

    def test_is_stable_false_for_spike(self) -> None:
        from umh.runtime.regime import classify_regime

        r = classify_regime("x", 0.3)
        assert r.is_stable is False

    def test_is_up_for_positive_trend(self) -> None:
        from umh.runtime.regime import classify_regime

        r = classify_regime("x", 0.15)
        assert r.is_up is True
        assert r.is_down is False

    def test_is_down_for_negative_trend(self) -> None:
        from umh.runtime.regime import classify_regime

        r = classify_regime("x", -0.15)
        assert r.is_down is True
        assert r.is_up is False

    def test_is_up_for_positive_spike(self) -> None:
        from umh.runtime.regime import classify_regime

        r = classify_regime("x", 0.4)
        assert r.is_up is True

    def test_is_down_for_negative_spike(self) -> None:
        from umh.runtime.regime import classify_regime

        r = classify_regime("x", -0.4)
        assert r.is_down is True

    def test_stable_not_up_not_down(self) -> None:
        from umh.runtime.regime import classify_regime

        r = classify_regime("x", 0.01)
        assert r.is_up is False
        assert r.is_down is False


# ---------------------------------------------------------------------------
# Section 5: RegimeSnapshot
# ---------------------------------------------------------------------------


class TestRegimeSnapshot:
    def test_creation(self) -> None:
        from umh.runtime.regime import RegimeSnapshot, RegimeType, classify_regime

        regimes = {"urgency": classify_regime("urgency", 0.3)}
        snap = RegimeSnapshot(regimes=regimes, tick=1)
        assert snap.tick == 1
        assert "urgency" in snap.regimes

    def test_frozen(self) -> None:
        from umh.runtime.regime import RegimeSnapshot

        snap = RegimeSnapshot(regimes={}, tick=0)
        with pytest.raises(FrozenInstanceError):
            snap.tick = 5  # type: ignore[misc]

    def test_get_existing(self) -> None:
        from umh.runtime.regime import RegimeSnapshot, classify_regime

        r = classify_regime("urgency", 0.3)
        snap = RegimeSnapshot(regimes={"urgency": r}, tick=1)
        assert snap.get("urgency") is r

    def test_get_missing(self) -> None:
        from umh.runtime.regime import RegimeSnapshot

        snap = RegimeSnapshot(regimes={}, tick=1)
        assert snap.get("missing") is None

    def test_get_regime_existing(self) -> None:
        from umh.runtime.regime import RegimeSnapshot, RegimeType, classify_regime

        snap = RegimeSnapshot(regimes={"urgency": classify_regime("urgency", 0.3)}, tick=1)
        assert snap.get_regime("urgency") is RegimeType.SPIKE_UP

    def test_get_regime_missing_returns_stable(self) -> None:
        from umh.runtime.regime import RegimeSnapshot, RegimeType

        snap = RegimeSnapshot(regimes={}, tick=1)
        assert snap.get_regime("missing") is RegimeType.STABLE

    def test_has_any_spike(self) -> None:
        from umh.runtime.regime import classify_all_regimes

        snap = classify_all_regimes({"urgency": 0.3, "risk": 0.01})
        assert snap.has_any_spike() is True

    def test_has_any_spike_false(self) -> None:
        from umh.runtime.regime import classify_all_regimes

        snap = classify_all_regimes({"urgency": 0.01, "risk": 0.01})
        assert snap.has_any_spike() is False

    def test_has_any_trend(self) -> None:
        from umh.runtime.regime import classify_all_regimes

        snap = classify_all_regimes({"urgency": 0.15, "risk": 0.01})
        assert snap.has_any_trend() is True

    def test_has_any_trend_false(self) -> None:
        from umh.runtime.regime import classify_all_regimes

        snap = classify_all_regimes({"urgency": 0.01, "risk": 0.01})
        assert snap.has_any_trend() is False

    def test_all_stable(self) -> None:
        from umh.runtime.regime import classify_all_regimes

        snap = classify_all_regimes({"urgency": 0.01, "risk": 0.02})
        assert snap.all_stable() is True

    def test_all_stable_false(self) -> None:
        from umh.runtime.regime import classify_all_regimes

        snap = classify_all_regimes({"urgency": 0.3, "risk": 0.01})
        assert snap.all_stable() is False

    def test_spike_signals(self) -> None:
        from umh.runtime.regime import classify_all_regimes

        snap = classify_all_regimes({"urgency": 0.3, "risk": 0.01, "pressure": 0.4})
        assert snap.spike_signals() == ["pressure", "urgency"]

    def test_trend_signals(self) -> None:
        from umh.runtime.regime import classify_all_regimes

        snap = classify_all_regimes({"urgency": 0.15, "risk": 0.01, "pressure": -0.1})
        assert snap.trend_signals() == ["pressure", "urgency"]

    def test_to_dict(self) -> None:
        from umh.runtime.regime import classify_all_regimes

        snap = classify_all_regimes({"urgency": 0.3, "risk": 0.01}, tick=5)
        d = snap.to_dict()
        assert d["tick"] == 5
        assert "urgency" in d["regimes"]
        assert "risk" in d["regimes"]
        assert "has_any_spike" in d
        assert "has_any_trend" in d
        assert "all_stable" in d


# ---------------------------------------------------------------------------
# Section 6: classify_regime — STABLE
# ---------------------------------------------------------------------------


class TestClassifyStable:
    def test_zero_delta(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.0)
        assert r.regime is RegimeType.STABLE

    def test_small_positive(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.05)
        assert r.regime is RegimeType.STABLE

    def test_small_negative(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", -0.05)
        assert r.regime is RegimeType.STABLE

    def test_just_below_trend_threshold(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.079)
        assert r.regime is RegimeType.STABLE

    def test_magnitude_correct(self) -> None:
        from umh.runtime.regime import classify_regime

        r = classify_regime("x", -0.05)
        assert r.magnitude == pytest.approx(0.05)

    def test_not_spike_not_trend(self) -> None:
        from umh.runtime.regime import classify_regime

        r = classify_regime("x", 0.02)
        assert r.is_spike is False
        assert r.is_trend is False


# ---------------------------------------------------------------------------
# Section 7: classify_regime — TREND
# ---------------------------------------------------------------------------


class TestClassifyTrend:
    def test_trend_up(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.15)
        assert r.regime is RegimeType.TREND_UP

    def test_trend_down(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", -0.15)
        assert r.regime is RegimeType.TREND_DOWN

    def test_at_trend_threshold(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.08)
        assert r.regime is RegimeType.TREND_UP

    def test_just_below_spike_threshold(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.249)
        assert r.regime is RegimeType.TREND_UP

    def test_is_trend_flag(self) -> None:
        from umh.runtime.regime import classify_regime

        r = classify_regime("x", 0.15)
        assert r.is_trend is True
        assert r.is_spike is False

    def test_negative_at_threshold(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", -0.08)
        assert r.regime is RegimeType.TREND_DOWN


# ---------------------------------------------------------------------------
# Section 8: classify_regime — SPIKE
# ---------------------------------------------------------------------------


class TestClassifySpike:
    def test_spike_up(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.3)
        assert r.regime is RegimeType.SPIKE_UP

    def test_spike_down(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", -0.3)
        assert r.regime is RegimeType.SPIKE_DOWN

    def test_at_spike_threshold(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.25)
        assert r.regime is RegimeType.SPIKE_UP

    def test_large_spike(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.9)
        assert r.regime is RegimeType.SPIKE_UP

    def test_large_negative_spike(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", -0.9)
        assert r.regime is RegimeType.SPIKE_DOWN

    def test_is_spike_flag(self) -> None:
        from umh.runtime.regime import classify_regime

        r = classify_regime("x", 0.3)
        assert r.is_spike is True
        assert r.is_trend is False

    def test_magnitude_at_spike(self) -> None:
        from umh.runtime.regime import classify_regime

        r = classify_regime("x", -0.4)
        assert r.magnitude == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# Section 9: Sign direction
# ---------------------------------------------------------------------------


class TestSignDirection:
    def test_positive_delta_up(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        for delta in [0.1, 0.2, 0.3, 0.5, 0.8]:
            r = classify_regime("x", delta)
            if r.regime is not RegimeType.STABLE:
                assert r.is_up is True
                assert r.is_down is False

    def test_negative_delta_down(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        for delta in [-0.1, -0.2, -0.3, -0.5, -0.8]:
            r = classify_regime("x", delta)
            if r.regime is not RegimeType.STABLE:
                assert r.is_down is True
                assert r.is_up is False

    def test_zero_is_stable(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.0)
        assert r.regime is RegimeType.STABLE
        assert r.is_up is False
        assert r.is_down is False

    def test_tiny_positive_stable(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.001)
        assert r.regime is RegimeType.STABLE

    def test_tiny_negative_stable(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", -0.001)
        assert r.regime is RegimeType.STABLE


# ---------------------------------------------------------------------------
# Section 10: classify_all_regimes
# ---------------------------------------------------------------------------


class TestClassifyAllRegimes:
    def test_multi_signal(self) -> None:
        from umh.runtime.regime import classify_all_regimes

        snap = classify_all_regimes(
            {
                "urgency": 0.3,
                "risk_level": 0.01,
                "resource_pressure": -0.15,
                "stability_mode": 0.0,
            }
        )
        assert len(snap.regimes) == 4

    def test_tick_recorded(self) -> None:
        from umh.runtime.regime import classify_all_regimes

        snap = classify_all_regimes({"urgency": 0.0}, tick=42)
        assert snap.tick == 42

    def test_correct_per_signal(self) -> None:
        from umh.runtime.regime import RegimeType, classify_all_regimes

        snap = classify_all_regimes(
            {
                "urgency": 0.3,
                "risk": 0.01,
                "pressure": -0.15,
            }
        )
        assert snap.get_regime("urgency") is RegimeType.SPIKE_UP
        assert snap.get_regime("risk") is RegimeType.STABLE
        assert snap.get_regime("pressure") is RegimeType.TREND_DOWN

    def test_custom_thresholds(self) -> None:
        from umh.runtime.regime import RegimeThresholds, RegimeType, classify_all_regimes

        t = RegimeThresholds(spike_threshold=0.5, trend_threshold=0.2)
        snap = classify_all_regimes({"urgency": 0.3}, thresholds=t)
        assert snap.get_regime("urgency") is RegimeType.TREND_UP

    def test_empty_deltas(self) -> None:
        from umh.runtime.regime import classify_all_regimes

        snap = classify_all_regimes({})
        assert len(snap.regimes) == 0
        assert snap.all_stable() is True


# ---------------------------------------------------------------------------
# Section 11: classify_from_horizon integration
# ---------------------------------------------------------------------------


class TestClassifyFromHorizon:
    def test_basic_integration(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory
        from umh.runtime.regime import RegimeType, classify_from_horizon

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.3))
        r = hm.smooth(ExecutionContext(urgency=0.9))
        snap = classify_from_horizon(r.snapshot)
        assert "urgency" in snap.regimes
        assert snap.tick == r.snapshot.tick

    def test_stable_after_convergence(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory
        from umh.runtime.regime import classify_from_horizon

        hm = HorizonMemory()
        for _ in range(30):
            r = hm.smooth(ExecutionContext(urgency=0.5))
        snap = classify_from_horizon(r.snapshot)
        assert snap.all_stable() is True

    def test_spike_detected(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory
        from umh.runtime.regime import RegimeType, classify_from_horizon

        hm = HorizonMemory()
        for _ in range(10):
            hm.smooth(ExecutionContext(urgency=0.3))
        r = hm.smooth(ExecutionContext(urgency=0.9))
        snap = classify_from_horizon(r.snapshot)
        urgency_regime = snap.get_regime("urgency")
        assert urgency_regime in (RegimeType.SPIKE_UP, RegimeType.TREND_UP)

    def test_custom_thresholds(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory
        from umh.runtime.regime import RegimeThresholds, classify_from_horizon

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.3))
        r = hm.smooth(ExecutionContext(urgency=0.9))
        t = RegimeThresholds(spike_threshold=0.9, trend_threshold=0.01)
        snap = classify_from_horizon(r.snapshot, thresholds=t)
        assert snap.has_any_spike() is False

    def test_rejects_non_horizon_snapshot(self) -> None:
        from umh.runtime.regime import classify_from_horizon

        with pytest.raises(TypeError, match="Expected HorizonSnapshot"):
            classify_from_horizon({"not": "a snapshot"})

    def test_all_signals_classified(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory
        from umh.runtime.regime import classify_from_horizon

        hm = HorizonMemory()
        hm.smooth(ExecutionContext())
        r = hm.smooth(ExecutionContext(urgency=0.9))
        snap = classify_from_horizon(r.snapshot)
        for name in ("urgency", "risk_level", "resource_pressure", "stability_mode"):
            assert name in snap.regimes


# ---------------------------------------------------------------------------
# Section 12: Threshold boundary behavior
# ---------------------------------------------------------------------------


class TestThresholdBoundaries:
    def test_exactly_at_trend_threshold(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.08)
        assert r.regime is RegimeType.TREND_UP

    def test_just_below_trend_threshold(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.0799)
        assert r.regime is RegimeType.STABLE

    def test_exactly_at_spike_threshold(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.25)
        assert r.regime is RegimeType.SPIKE_UP

    def test_just_below_spike_threshold(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.2499)
        assert r.regime is RegimeType.TREND_UP

    def test_negative_at_trend_threshold(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", -0.08)
        assert r.regime is RegimeType.TREND_DOWN

    def test_negative_at_spike_threshold(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", -0.25)
        assert r.regime is RegimeType.SPIKE_DOWN

    def test_negative_just_below_trend(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", -0.0799)
        assert r.regime is RegimeType.STABLE


# ---------------------------------------------------------------------------
# Section 13: No oscillation under small noise
# ---------------------------------------------------------------------------


class TestNoOscillation:
    def test_stable_band_consistent(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        for delta in [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07]:
            r = classify_regime("x", delta)
            assert r.regime is RegimeType.STABLE

    def test_trend_band_consistent(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        for delta_100x in range(9, 25):
            delta = delta_100x / 100.0
            r = classify_regime("x", delta)
            assert r.regime is RegimeType.TREND_UP

    def test_spike_band_consistent(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        for delta_10x in range(25, 100):
            delta = delta_10x / 100.0
            r = classify_regime("x", delta)
            assert r.regime is RegimeType.SPIKE_UP

    def test_noise_around_zero_stays_stable(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        for i in range(100):
            delta = (i - 50) / 1000.0
            r = classify_regime("x", delta)
            assert r.regime is RegimeType.STABLE

    def test_repeated_same_delta_same_result(self) -> None:
        from umh.runtime.regime import classify_regime

        results = [classify_regime("x", 0.15).regime for _ in range(100)]
        assert len(set(results)) == 1


# ---------------------------------------------------------------------------
# Section 14: Custom thresholds
# ---------------------------------------------------------------------------


class TestCustomThresholds:
    def test_wider_stable_band(self) -> None:
        from umh.runtime.regime import RegimeThresholds, RegimeType, classify_regime

        t = RegimeThresholds(spike_threshold=0.5, trend_threshold=0.2)
        r = classify_regime("x", 0.15, thresholds=t)
        assert r.regime is RegimeType.STABLE

    def test_narrower_stable_band(self) -> None:
        from umh.runtime.regime import RegimeThresholds, RegimeType, classify_regime

        t = RegimeThresholds(spike_threshold=0.2, trend_threshold=0.03)
        r = classify_regime("x", 0.05, thresholds=t)
        assert r.regime is RegimeType.TREND_UP

    def test_lower_spike_threshold(self) -> None:
        from umh.runtime.regime import RegimeThresholds, RegimeType, classify_regime

        t = RegimeThresholds(spike_threshold=0.1, trend_threshold=0.03)
        r = classify_regime("x", 0.12, thresholds=t)
        assert r.regime is RegimeType.SPIKE_UP

    def test_thresholds_passed_through(self) -> None:
        from umh.runtime.regime import RegimeThresholds, RegimeType, classify_all_regimes

        t = RegimeThresholds(spike_threshold=0.5, trend_threshold=0.3)
        snap = classify_all_regimes({"urgency": 0.35}, thresholds=t)
        assert snap.get_regime("urgency") is RegimeType.TREND_UP


# ---------------------------------------------------------------------------
# Section 15: Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_delta_same_regime(self) -> None:
        from umh.runtime.regime import classify_regime

        results = []
        for _ in range(10):
            r = classify_regime("urgency", 0.15)
            results.append(r.regime)
        assert len(set(results)) == 1

    def test_same_delta_same_magnitude(self) -> None:
        from umh.runtime.regime import classify_regime

        results = []
        for _ in range(10):
            r = classify_regime("urgency", -0.3)
            results.append(r.magnitude)
        assert len(set(results)) == 1

    def test_deterministic_across_signals(self) -> None:
        from umh.runtime.regime import classify_regime

        r1 = classify_regime("urgency", 0.15)
        r2 = classify_regime("risk_level", 0.15)
        assert r1.regime == r2.regime
        assert r1.magnitude == r2.magnitude

    def test_all_regimes_deterministic(self) -> None:
        from umh.runtime.regime import classify_all_regimes

        deltas = {"urgency": 0.3, "risk": 0.01, "pressure": -0.15}
        s1 = classify_all_regimes(deltas, tick=1)
        s2 = classify_all_regimes(deltas, tick=1)
        for name in deltas:
            assert s1.get_regime(name) == s2.get_regime(name)


# ---------------------------------------------------------------------------
# Section 16: Hard invariants 146-150
# ---------------------------------------------------------------------------


class TestHardInvariants:
    def test_inv146_deterministic_classification(self) -> None:
        from umh.runtime.regime import classify_regime

        runs = [classify_regime("urgency", 0.2).regime for _ in range(20)]
        assert all(r == runs[0] for r in runs)

    def test_inv147_no_state_mutation(self) -> None:
        from umh.runtime.regime import classify_regime

        r1 = classify_regime("urgency", 0.3)
        r2 = classify_regime("urgency", 0.1)
        r3 = classify_regime("urgency", 0.3)
        assert r1.regime == r3.regime
        assert r1.magnitude == r3.magnitude

    def test_inv148_same_delta_same_regime(self) -> None:
        from umh.runtime.regime import classify_regime

        deltas = [0.0, 0.05, 0.08, 0.15, 0.25, 0.5, -0.05, -0.15, -0.3]
        for d in deltas:
            r1 = classify_regime("a", d)
            r2 = classify_regime("b", d)
            assert r1.regime == r2.regime

    def test_inv149_neutral_delta_stable(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 0.0)
        assert r.regime is RegimeType.STABLE

    def test_inv149_near_zero_stable(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        for d in [0.001, -0.001, 0.01, -0.01, 0.05, -0.05]:
            r = classify_regime("x", d)
            assert r.regime is RegimeType.STABLE

    def test_inv150_no_oscillation_small_noise(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        base = 0.04
        noise_range = 0.03
        results = []
        for i in range(100):
            delta = base + (i % 10 - 5) * noise_range / 10
            r = classify_regime("x", delta)
            results.append(r.regime)
        assert all(r is RegimeType.STABLE for r in results)


# ---------------------------------------------------------------------------
# Section 17: Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_delta_exactly_one(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 1.0)
        assert r.regime is RegimeType.SPIKE_UP

    def test_delta_exactly_negative_one(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", -1.0)
        assert r.regime is RegimeType.SPIKE_DOWN

    def test_delta_very_small_positive(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", 1e-10)
        assert r.regime is RegimeType.STABLE

    def test_delta_very_small_negative(self) -> None:
        from umh.runtime.regime import RegimeType, classify_regime

        r = classify_regime("x", -1e-10)
        assert r.regime is RegimeType.STABLE

    def test_signal_name_preserved(self) -> None:
        from umh.runtime.regime import classify_regime

        r = classify_regime("my_custom_signal", 0.15)
        assert r.signal_name == "my_custom_signal"

    def test_empty_snapshot_all_stable(self) -> None:
        from umh.runtime.regime import RegimeSnapshot

        snap = RegimeSnapshot(regimes={}, tick=0)
        assert snap.all_stable() is True
        assert snap.has_any_spike() is False
        assert snap.has_any_trend() is False
        assert snap.spike_signals() == []
        assert snap.trend_signals() == []


# ---------------------------------------------------------------------------
# Section 18: Full pipeline integration
# ---------------------------------------------------------------------------


class TestFullPipelineIntegration:
    def test_horizon_to_regime_pipeline(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.regime import classify_from_horizon

        cm = ContextMemory()
        for _ in range(10):
            cm.smooth_horizon(ExecutionContext(urgency=0.3))
        _, snap = cm.smooth_horizon(ExecutionContext(urgency=0.9))
        regime_snap = classify_from_horizon(snap)
        assert "urgency" in regime_snap.regimes
        r = regime_snap.get("urgency")
        assert r is not None
        assert r.is_up is True

    def test_stable_pipeline(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.regime import classify_from_horizon

        cm = ContextMemory()
        for _ in range(20):
            _, snap = cm.smooth_horizon(ExecutionContext(urgency=0.5))
        regime_snap = classify_from_horizon(snap)
        assert regime_snap.all_stable() is True

    def test_drop_pipeline(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory
        from umh.runtime.regime import classify_from_horizon

        cm = ContextMemory()
        for _ in range(10):
            cm.smooth_horizon(ExecutionContext(urgency=0.8))
        _, snap = cm.smooth_horizon(ExecutionContext(urgency=0.1))
        regime_snap = classify_from_horizon(snap)
        r = regime_snap.get("urgency")
        assert r is not None
        assert r.is_down is True


# ---------------------------------------------------------------------------
# Section 19: Serialization roundtrip
# ---------------------------------------------------------------------------


class TestSerializationRoundtrip:
    def test_regime_result_to_dict(self) -> None:
        from umh.runtime.regime import classify_regime

        r = classify_regime("urgency", 0.3)
        d = r.to_dict()
        assert d["regime"] == "spike_up"
        assert d["signal_name"] == "urgency"
        assert d["is_spike"] is True

    def test_regime_snapshot_to_dict(self) -> None:
        from umh.runtime.regime import classify_all_regimes

        snap = classify_all_regimes({"urgency": 0.3, "risk": 0.01}, tick=7)
        d = snap.to_dict()
        assert d["tick"] == 7
        assert d["has_any_spike"] is True
        assert d["all_stable"] is False

    def test_thresholds_to_dict(self) -> None:
        from umh.runtime.regime import RegimeThresholds

        t = RegimeThresholds(spike_threshold=0.3, trend_threshold=0.1)
        d = t.to_dict()
        assert d["spike_threshold"] == 0.3
        assert d["trend_threshold"] == 0.1


# ---------------------------------------------------------------------------
# Section 20: Dependency boundary
# ---------------------------------------------------------------------------


class TestDependencyBoundary:
    def test_regime_no_forbidden_imports(self) -> None:
        with open("/opt/OS/umh/runtime/regime.py") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = ""
                if isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name
                assert "subprocess" not in module

    def test_regime_no_cells_envs_adapters(self) -> None:
        with open("/opt/OS/umh/runtime/regime.py") as f:
            source = f.read()
        for forbidden in ("from umh.cells", "from umh.environments", "from umh.adapters"):
            assert forbidden not in source


# ---------------------------------------------------------------------------
# Section 21: Exports and compilation
# ---------------------------------------------------------------------------


class TestExportsAndCompilation:
    def test_runtime_exports_regime_types(self) -> None:
        from umh.runtime import (
            DEFAULT_THRESHOLDS,
            RegimeResult,
            RegimeSnapshot,
            RegimeThresholds,
            RegimeType,
            classify_all_regimes,
            classify_from_horizon,
            classify_regime,
        )

        assert RegimeType is not None
        assert RegimeResult is not None
        assert RegimeSnapshot is not None
        assert RegimeThresholds is not None
        assert DEFAULT_THRESHOLDS is not None
        assert classify_regime is not None
        assert classify_all_regimes is not None
        assert classify_from_horizon is not None

    def test_regime_compiles(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/regime.py", doraise=True)

    def test_init_compiles(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/__init__.py", doraise=True)

    def test_all_new_exports_in_all_list(self) -> None:
        import umh.runtime as rt

        expected = [
            "DEFAULT_THRESHOLDS",
            "RegimeResult",
            "RegimeSnapshot",
            "RegimeThresholds",
            "RegimeType",
            "classify_all_regimes",
            "classify_from_horizon",
            "classify_regime",
        ]
        for name in expected:
            assert name in rt.__all__, f"{name} not in __all__"


# ---------------------------------------------------------------------------
# Section 22: Phase 41 regression
# ---------------------------------------------------------------------------


class TestPhase41Regression:
    def test_horizon_memory_unchanged(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.horizon import HorizonMemory

        hm = HorizonMemory()
        hm.smooth(ExecutionContext(urgency=0.0))
        r = hm.smooth(ExecutionContext(urgency=1.0))
        assert r.fast_context.urgency > r.slow_context.urgency

    def test_horizon_value_unchanged(self) -> None:
        from umh.runtime.horizon import compute_horizon_value

        hv = compute_horizon_value("urgency", 1.0, 0.0, 0.0, 0.7, 0.3)
        assert hv.fast == pytest.approx(0.7)
        assert hv.slow == pytest.approx(0.3)

    def test_context_memory_smooth_horizon_unchanged(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        r, snap = cm.smooth_horizon(ExecutionContext(urgency=0.8))
        assert r.smoothed.urgency == pytest.approx(0.8)

    def test_adaptive_smooth_unchanged(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth_adaptive(ExecutionContext(urgency=0.0))
        r, snap = cm.smooth_adaptive(ExecutionContext(urgency=1.0))
        assert r.smoothed.urgency > 0.0

    def test_fixed_alpha_smooth_unchanged(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory(alpha=0.5)
        cm.smooth(ExecutionContext(urgency=0.0))
        r = cm.smooth(ExecutionContext(urgency=1.0))
        assert r.smoothed.urgency == pytest.approx(0.5)

    def test_neutral_context_unchanged(self) -> None:
        from umh.runtime.context import NEUTRAL_CONTEXT

        assert NEUTRAL_CONTEXT.is_neutral is True

    def test_reset_still_works(self) -> None:
        from umh.runtime.context import ExecutionContext
        from umh.runtime.context_memory import ContextMemory

        cm = ContextMemory()
        cm.smooth(ExecutionContext(urgency=0.9))
        r = cm.reset()
        assert r.smoothed.is_neutral is True
        assert r.was_reset is True

    def test_make_context_unchanged(self) -> None:
        from umh.runtime.context import make_context

        ctx = make_context(urgency=0.8)
        assert ctx.urgency == 0.8
