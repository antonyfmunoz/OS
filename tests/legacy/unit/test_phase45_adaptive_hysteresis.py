"""Phase 45 — Adaptive Hysteresis Threshold Layer v1 tests.

Covers: AdaptiveThresholdConfig, ThresholdResult, ThresholdSnapshot,
compute_adaptive_threshold, compute_all_thresholds, adaptive behavior,
pipeline integration with RegimeFilter + RegimeMemory, hard invariants
161-165, edge cases, serialization, dependency boundary,
exports/compilation, Phase 44 regression.

Target: 150-190 tests.
"""

from __future__ import annotations

import ast
import math
import sys

import pytest

sys.path.insert(0, "/opt/OS")

from umh.runtime.regime import RegimeType, classify_all_regimes
from umh.runtime.regime_memory import RegimeMemory
from umh.runtime.regime_filter import RegimeFilter, filter_regime, FilterState
from umh.runtime.hysteresis_adaptive import (
    DEFAULT_ADAPTIVE_CONFIG,
    AdaptiveThresholdConfig,
    ThresholdResult,
    ThresholdSnapshot,
    _DEFAULT_BASE_THRESHOLD,
    _DEFAULT_MAX_THRESHOLD,
    _DEFAULT_MIN_THRESHOLD,
    _DEFAULT_STABILITY_WEIGHT,
    _DEFAULT_VOLATILITY_WEIGHT,
    compute_adaptive_threshold,
    compute_all_thresholds,
)

RT = RegimeType


# ── helpers ─────────────────────────────────────────────────────────


def _compute(delta: float, duration: int, config: AdaptiveThresholdConfig | None = None) -> int:
    return compute_adaptive_threshold("test", delta, duration, config).adaptive_threshold


def _factor(delta: float, duration: int, config: AdaptiveThresholdConfig | None = None) -> float:
    return compute_adaptive_threshold("test", delta, duration, config).factor


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 1: AdaptiveThresholdConfig creation and defaults
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConfigCreation:
    def test_default_values(self):
        c = AdaptiveThresholdConfig()
        assert c.base_threshold == 3
        assert c.min_threshold == 1
        assert c.max_threshold == 6
        assert c.volatility_weight == 2.0
        assert c.stability_weight == 0.5

    def test_custom_values(self):
        c = AdaptiveThresholdConfig(
            base_threshold=5,
            min_threshold=2,
            max_threshold=10,
            volatility_weight=3.0,
            stability_weight=1.0,
        )
        assert c.base_threshold == 5
        assert c.min_threshold == 2
        assert c.max_threshold == 10
        assert c.volatility_weight == 3.0
        assert c.stability_weight == 1.0

    def test_frozen(self):
        c = AdaptiveThresholdConfig()
        with pytest.raises(AttributeError):
            c.base_threshold = 10

    def test_base_threshold_minimum_one(self):
        c = AdaptiveThresholdConfig(base_threshold=0)
        assert c.base_threshold == 1

    def test_min_threshold_minimum_one(self):
        c = AdaptiveThresholdConfig(min_threshold=0)
        assert c.min_threshold == 1

    def test_max_at_least_min(self):
        c = AdaptiveThresholdConfig(min_threshold=5, max_threshold=3)
        assert c.max_threshold >= c.min_threshold

    def test_negative_weights_clamped_to_zero(self):
        c = AdaptiveThresholdConfig(volatility_weight=-1.0, stability_weight=-2.0)
        assert c.volatility_weight == 0.0
        assert c.stability_weight == 0.0

    def test_to_dict(self):
        c = AdaptiveThresholdConfig()
        d = c.to_dict()
        assert d["base_threshold"] == 3
        assert d["min_threshold"] == 1
        assert d["max_threshold"] == 6
        assert d["volatility_weight"] == 2.0
        assert d["stability_weight"] == 0.5

    def test_default_config_singleton(self):
        assert DEFAULT_ADAPTIVE_CONFIG.base_threshold == _DEFAULT_BASE_THRESHOLD
        assert DEFAULT_ADAPTIVE_CONFIG.volatility_weight == _DEFAULT_VOLATILITY_WEIGHT
        assert DEFAULT_ADAPTIVE_CONFIG.stability_weight == _DEFAULT_STABILITY_WEIGHT


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 2: ThresholdResult creation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestThresholdResult:
    def test_creation(self):
        r = ThresholdResult(
            signal_name="urgency",
            adaptive_threshold=2,
            base_threshold=3,
            factor=0.6,
            delta_magnitude=0.3,
            duration=0,
            volatility_adjust=0.6,
            stability_adjust=0.0,
        )
        assert r.signal_name == "urgency"
        assert r.adaptive_threshold == 2
        assert r.factor == 0.6

    def test_frozen(self):
        r = ThresholdResult("urgency", 2, 3, 0.6, 0.3, 0, 0.6, 0.0)
        with pytest.raises(AttributeError):
            r.adaptive_threshold = 5

    def test_to_dict(self):
        r = ThresholdResult("urgency", 2, 3, 0.6, 0.3, 0, 0.6, 0.0)
        d = r.to_dict()
        assert d["signal_name"] == "urgency"
        assert d["adaptive_threshold"] == 2
        assert d["base_threshold"] == 3
        assert d["factor"] == 0.6
        assert d["delta_magnitude"] == 0.3
        assert d["duration"] == 0
        assert d["volatility_adjust"] == 0.6
        assert d["stability_adjust"] == 0.0

    def test_to_dict_rounding(self):
        r = ThresholdResult("test", 3, 3, 1.00001, 0.00001, 0, 0.00002, 0.00003)
        d = r.to_dict()
        assert d["factor"] == 1.0
        assert d["delta_magnitude"] == 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 3: ThresholdSnapshot
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestThresholdSnapshot:
    def test_creation(self):
        r = ThresholdResult("urgency", 2, 3, 0.6, 0.3, 0, 0.6, 0.0)
        snap = ThresholdSnapshot(thresholds={"urgency": r})
        assert len(snap.thresholds) == 1

    def test_frozen(self):
        snap = ThresholdSnapshot(thresholds={})
        with pytest.raises(AttributeError):
            snap.thresholds = {}

    def test_get(self):
        r = ThresholdResult("urgency", 2, 3, 0.6, 0.3, 0, 0.6, 0.0)
        snap = ThresholdSnapshot(thresholds={"urgency": r})
        assert snap.get("urgency") is r
        assert snap.get("missing") is None

    def test_get_threshold(self):
        r = ThresholdResult("urgency", 2, 3, 0.6, 0.3, 0, 0.6, 0.0)
        snap = ThresholdSnapshot(thresholds={"urgency": r})
        assert snap.get_threshold("urgency") == 2

    def test_get_threshold_missing_returns_default(self):
        snap = ThresholdSnapshot(thresholds={})
        assert snap.get_threshold("missing") == _DEFAULT_BASE_THRESHOLD

    def test_get_threshold_custom_default(self):
        snap = ThresholdSnapshot(thresholds={})
        assert snap.get_threshold("missing", default=5) == 5

    def test_min_threshold(self):
        r1 = ThresholdResult("a", 1, 3, 0.3, 0.5, 0, 1.0, 0.0)
        r2 = ThresholdResult("b", 5, 3, 1.7, 0.0, 50, 0.0, 2.0)
        snap = ThresholdSnapshot(thresholds={"a": r1, "b": r2})
        assert snap.min_threshold() == 1

    def test_max_threshold(self):
        r1 = ThresholdResult("a", 1, 3, 0.3, 0.5, 0, 1.0, 0.0)
        r2 = ThresholdResult("b", 5, 3, 1.7, 0.0, 50, 0.0, 2.0)
        snap = ThresholdSnapshot(thresholds={"a": r1, "b": r2})
        assert snap.max_threshold() == 5

    def test_min_max_empty(self):
        snap = ThresholdSnapshot(thresholds={})
        assert snap.min_threshold() == _DEFAULT_BASE_THRESHOLD
        assert snap.max_threshold() == _DEFAULT_BASE_THRESHOLD

    def test_to_dict(self):
        r = ThresholdResult("urgency", 2, 3, 0.6, 0.3, 0, 0.6, 0.0)
        snap = ThresholdSnapshot(thresholds={"urgency": r})
        d = snap.to_dict()
        assert "urgency" in d["thresholds"]

    def test_to_dict_sorted_keys(self):
        r1 = ThresholdResult("z", 3, 3, 1.0, 0.0, 0, 0.0, 0.0)
        r2 = ThresholdResult("a", 3, 3, 1.0, 0.0, 0, 0.0, 0.0)
        snap = ThresholdSnapshot(thresholds={"z": r1, "a": r2})
        d = snap.to_dict()
        keys = list(d["thresholds"].keys())
        assert keys == sorted(keys)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 4: compute_adaptive_threshold — baseline behavior
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestBaselineBehavior:
    def test_zero_delta_zero_duration_returns_base(self):
        assert _compute(0.0, 0) == 3

    def test_returns_threshold_result(self):
        r = compute_adaptive_threshold("urgency", 0.0, 0)
        assert isinstance(r, ThresholdResult)
        assert r.signal_name == "urgency"

    def test_factor_at_baseline_is_one(self):
        assert _factor(0.0, 0) == 1.0

    def test_none_config_uses_default(self):
        r1 = compute_adaptive_threshold("test", 0.1, 5, None)
        r2 = compute_adaptive_threshold("test", 0.1, 5, DEFAULT_ADAPTIVE_CONFIG)
        assert r1.adaptive_threshold == r2.adaptive_threshold
        assert r1.factor == r2.factor


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 5: Large delta reduces threshold (faster confirmation)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLargeDeltaReducesThreshold:
    def test_large_delta_reduces_to_minimum(self):
        assert _compute(0.3, 0) == 1

    def test_very_large_delta_clamps_to_min(self):
        assert _compute(1.0, 0) == 1

    def test_moderate_delta_reduces_somewhat(self):
        t = _compute(0.05, 0)
        assert t <= 3

    def test_larger_delta_lower_threshold(self):
        t_small = _compute(0.05, 0)
        t_large = _compute(0.3, 0)
        assert t_large <= t_small

    def test_monotonic_decrease_with_delta(self):
        deltas = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]
        thresholds = [_compute(d, 0) for d in deltas]
        for i in range(len(thresholds) - 1):
            assert thresholds[i + 1] <= thresholds[i]

    def test_factor_decreases_with_delta(self):
        f_small = _factor(0.05, 0)
        f_large = _factor(0.3, 0)
        assert f_large < f_small

    def test_volatility_adjust_proportional(self):
        r = compute_adaptive_threshold("test", 0.3, 0)
        assert r.volatility_adjust == pytest.approx(0.6, abs=0.001)

    def test_spike_delta_confirms_fast(self):
        assert _compute(0.5, 0) == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 6: Long duration increases threshold (resists switching)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLongDurationIncreasesThreshold:
    def test_long_duration_increases_threshold(self):
        t_short = _compute(0.0, 0)
        t_long = _compute(0.0, 10)
        assert t_long > t_short

    def test_very_long_duration_clamps_to_max(self):
        assert _compute(0.0, 100) == 6

    def test_monotonic_increase_with_duration(self):
        durations = [0, 1, 5, 10, 50, 100]
        thresholds = [_compute(0.0, d) for d in durations]
        for i in range(len(thresholds) - 1):
            assert thresholds[i + 1] >= thresholds[i]

    def test_factor_increases_with_duration(self):
        f_short = _factor(0.0, 0)
        f_long = _factor(0.0, 50)
        assert f_long > f_short

    def test_stability_adjust_logarithmic(self):
        r = compute_adaptive_threshold("test", 0.0, 10)
        expected = 0.5 * math.log(11)
        assert r.stability_adjust == pytest.approx(expected, abs=0.001)

    def test_duration_10_raises_threshold(self):
        assert _compute(0.0, 10) == 6

    def test_duration_5_moderate_increase(self):
        t = _compute(0.0, 5)
        assert t >= 3
        assert t <= 6


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 7: Combined effects
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCombinedEffects:
    def test_large_delta_long_duration_partial_cancel(self):
        t = _compute(0.3, 10)
        assert t >= 1
        assert t <= 6

    def test_large_delta_overrides_moderate_duration(self):
        t = _compute(0.3, 5)
        assert t < _compute(0.0, 5)

    def test_very_long_duration_overrides_moderate_delta(self):
        t = _compute(0.1, 100)
        assert t > _compute(0.1, 0)

    def test_competing_forces_reference_value(self):
        assert _compute(0.3, 10) == 5

    def test_balanced_case(self):
        t = _compute(0.1, 5)
        assert t == 5


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 8: Bounds enforcement
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestBoundsEnforcement:
    def test_never_below_min(self):
        for delta in [0.0, 0.1, 0.3, 0.5, 1.0, 2.0]:
            for dur in [0, 1, 5, 10]:
                t = _compute(delta, dur)
                assert t >= 1

    def test_never_above_max(self):
        for delta in [0.0, 0.1, 0.3, 0.5]:
            for dur in [0, 1, 5, 10, 50, 100, 1000]:
                t = _compute(delta, dur)
                assert t <= 6

    def test_custom_bounds(self):
        c = AdaptiveThresholdConfig(min_threshold=2, max_threshold=4)
        t_low = compute_adaptive_threshold("test", 1.0, 0, c).adaptive_threshold
        t_high = compute_adaptive_threshold("test", 0.0, 1000, c).adaptive_threshold
        assert t_low == 2
        assert t_high == 4

    def test_negative_factor_clamps_to_min(self):
        r = compute_adaptive_threshold("test", 1.0, 0)
        assert r.factor < 0
        assert r.adaptive_threshold == 1

    def test_huge_factor_clamps_to_max(self):
        r = compute_adaptive_threshold("test", 0.0, 10000)
        assert r.factor > 2
        assert r.adaptive_threshold == 6

    def test_integer_output(self):
        for delta in [0.0, 0.05, 0.1, 0.2, 0.3]:
            for dur in [0, 1, 5, 10, 50]:
                t = _compute(delta, dur)
                assert isinstance(t, int)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 9: compute_all_thresholds
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestComputeAllThresholds:
    def test_basic_usage(self):
        deltas = {"urgency": 0.3, "risk_level": 0.0}
        durations = {"urgency": 0, "risk_level": 10}
        snap = compute_all_thresholds(deltas, durations)
        assert snap.get_threshold("urgency") == 1
        assert snap.get_threshold("risk_level") == 6

    def test_missing_duration_defaults_to_zero(self):
        deltas = {"urgency": 0.0}
        durations = {}
        snap = compute_all_thresholds(deltas, durations)
        assert snap.get_threshold("urgency") == 3

    def test_sorted_output(self):
        deltas = {"z": 0.0, "a": 0.0, "m": 0.0}
        snap = compute_all_thresholds(deltas, {})
        keys = list(snap.thresholds.keys())
        assert keys == sorted(keys)

    def test_multiple_signals(self):
        deltas = {
            "urgency": 0.3,
            "risk_level": 0.0,
            "resource_pressure": 0.1,
            "stability_mode": 0.0,
        }
        durations = {
            "urgency": 0,
            "risk_level": 50,
            "resource_pressure": 5,
            "stability_mode": 0,
        }
        snap = compute_all_thresholds(deltas, durations)
        assert snap.get_threshold("urgency") < snap.get_threshold("risk_level")

    def test_negative_delta_uses_abs(self):
        deltas = {"test": -0.3}
        snap = compute_all_thresholds(deltas, {})
        assert snap.get_threshold("test") == 1

    def test_custom_config(self):
        c = AdaptiveThresholdConfig(base_threshold=5, volatility_weight=0.0)
        deltas = {"test": 0.0}
        snap = compute_all_thresholds(deltas, {}, c)
        assert snap.get_threshold("test") == 5


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 10: Custom config behavior
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCustomConfig:
    def test_zero_volatility_weight_ignores_delta(self):
        c = AdaptiveThresholdConfig(volatility_weight=0.0)
        t1 = compute_adaptive_threshold("test", 0.0, 0, c).adaptive_threshold
        t2 = compute_adaptive_threshold("test", 1.0, 0, c).adaptive_threshold
        assert t1 == t2

    def test_zero_stability_weight_ignores_duration(self):
        c = AdaptiveThresholdConfig(stability_weight=0.0)
        t1 = compute_adaptive_threshold("test", 0.0, 0, c).adaptive_threshold
        t2 = compute_adaptive_threshold("test", 0.0, 1000, c).adaptive_threshold
        assert t1 == t2

    def test_high_volatility_weight_aggressive(self):
        c = AdaptiveThresholdConfig(volatility_weight=10.0)
        t = compute_adaptive_threshold("test", 0.1, 0, c).adaptive_threshold
        assert t == 1

    def test_high_stability_weight_conservative(self):
        c = AdaptiveThresholdConfig(stability_weight=5.0)
        t = compute_adaptive_threshold("test", 0.0, 5, c).adaptive_threshold
        assert t == 6

    def test_wide_bounds(self):
        c = AdaptiveThresholdConfig(min_threshold=1, max_threshold=20)
        t = compute_adaptive_threshold("test", 0.0, 1000, c).adaptive_threshold
        assert t <= 20
        assert t > 6

    def test_narrow_bounds(self):
        c = AdaptiveThresholdConfig(min_threshold=3, max_threshold=3)
        t = compute_adaptive_threshold("test", 1.0, 0, c).adaptive_threshold
        assert t == 3
        t2 = compute_adaptive_threshold("test", 0.0, 1000, c).adaptive_threshold
        assert t2 == 3


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 11: Integration with RegimeFilter
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRegimeFilterIntegration:
    def test_adaptive_threshold_used_in_filter(self):
        state = FilterState(signal_name="urgency")
        threshold = _compute(0.3, 0)
        assert threshold == 1
        r = filter_regime(state, RT.SPIKE_UP, threshold)
        assert r.was_confirmed is True
        assert r.filtered_regime is RT.SPIKE_UP

    def test_high_threshold_suppresses(self):
        state = FilterState(signal_name="urgency")
        threshold = _compute(0.0, 50)
        assert threshold == 6
        r = filter_regime(state, RT.SPIKE_UP, threshold)
        assert r.was_confirmed is False
        assert r.filtered_regime is RT.STABLE

    def test_adaptive_filter_pipeline(self):
        mem = RegimeMemory(signals=("urgency",))
        deltas = {"urgency": 0.3}
        regime_snap = classify_all_regimes(deltas, tick=1)
        mem_snap = mem.update(regime_snap)

        duration = mem.get_duration("urgency")
        delta_mag = abs(deltas["urgency"])
        threshold = _compute(delta_mag, duration)
        assert threshold == 2

        state = FilterState(signal_name="urgency")
        filter_regime(state, mem_snap.get_regime("urgency"), threshold)
        r = filter_regime(state, mem_snap.get_regime("urgency"), threshold)
        assert r.filtered_regime is RT.SPIKE_UP

    def test_stable_regime_high_duration_resists(self):
        mem = RegimeMemory(signals=("urgency",))
        snap = classify_all_regimes({"urgency": 0.0}, tick=0)
        for _ in range(50):
            mem.update(snap)

        duration = mem.get_duration("urgency")
        threshold = _compute(0.0, duration)
        assert threshold == 6

    def test_fast_signal_low_threshold(self):
        threshold = _compute(0.5, 0)
        assert threshold == 1

    def test_slow_signal_high_threshold(self):
        threshold = _compute(0.0, 100)
        assert threshold == 6


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 12: Full pipeline integration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFullPipeline:
    def test_classify_memory_adaptive_filter(self):
        mem = RegimeMemory(signals=("urgency", "risk_level"))
        deltas = {"urgency": 0.3, "risk_level": 0.0}

        regime_snap = classify_all_regimes(deltas, tick=1)
        mem_snap = mem.update(regime_snap)

        thresholds = compute_all_thresholds(
            {n: abs(deltas.get(n, 0.0)) for n in mem_snap.states},
            {n: s.duration for n, s in mem_snap.states.items()},
        )

        t_urgency = thresholds.get_threshold("urgency")
        assert t_urgency == 2
        t_risk = thresholds.get_threshold("risk_level")
        assert t_risk >= 3

        fs = FilterState(signal_name="urgency")
        for _ in range(t_urgency):
            r = filter_regime(fs, mem_snap.get_regime("urgency"), t_urgency)
        assert r.filtered_regime is RT.SPIKE_UP

        fs2 = FilterState(signal_name="risk_level")
        r2 = filter_regime(fs2, mem_snap.get_regime("risk_level"), t_risk)
        assert r2.filtered_regime is RT.STABLE

    def test_four_signal_pipeline(self):
        mem = RegimeMemory()
        deltas = {
            "urgency": 0.3,
            "risk_level": 0.0,
            "resource_pressure": 0.1,
            "stability_mode": -0.15,
        }
        regime_snap = classify_all_regimes(deltas, tick=1)
        mem_snap = mem.update(regime_snap)

        snap = compute_all_thresholds(
            {n: abs(deltas.get(n, 0.0)) for n in mem_snap.states},
            {n: s.duration for n, s in mem_snap.states.items()},
        )

        assert snap.get_threshold("urgency") == 2
        assert snap.get_threshold("risk_level") == 4
        assert snap.get_threshold("resource_pressure") == 3
        assert snap.get_threshold("stability_mode") == 3

    def test_sustained_stable_increases_threshold_over_time(self):
        mem = RegimeMemory(signals=("urgency",))
        thresholds_over_time = []
        for i in range(20):
            snap = classify_all_regimes({"urgency": 0.0}, tick=i + 1)
            mem_snap = mem.update(snap)
            t = _compute(0.0, mem.get_duration("urgency"))
            thresholds_over_time.append(t)
        assert thresholds_over_time[-1] >= thresholds_over_time[0]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 13: Determinism
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDeterminism:
    def test_same_inputs_same_output(self):
        r1 = compute_adaptive_threshold("urgency", 0.15, 7)
        r2 = compute_adaptive_threshold("urgency", 0.15, 7)
        assert r1.adaptive_threshold == r2.adaptive_threshold
        assert r1.factor == r2.factor

    def test_independent_of_call_order(self):
        t1 = _compute(0.3, 5)
        _compute(0.0, 100)
        _compute(1.0, 0)
        t2 = _compute(0.3, 5)
        assert t1 == t2

    def test_compute_all_deterministic(self):
        deltas = {"a": 0.3, "b": 0.0}
        durations = {"a": 0, "b": 50}
        s1 = compute_all_thresholds(deltas, durations)
        s2 = compute_all_thresholds(deltas, durations)
        for name in deltas:
            assert s1.get_threshold(name) == s2.get_threshold(name)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 14: Hard invariants 161-165
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestHardInvariants:
    def test_inv161_adaptive_threshold_bounded(self):
        """Invariant 161: Adaptive threshold always within [min, max]."""
        for delta in [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0]:
            for dur in [0, 1, 5, 10, 50, 100, 500, 1000]:
                t = _compute(delta, dur)
                assert 1 <= t <= 6, f"delta={delta}, dur={dur}, t={t}"

    def test_inv161_custom_bounds(self):
        c = AdaptiveThresholdConfig(min_threshold=2, max_threshold=8)
        for delta in [0.0, 0.5, 1.0]:
            for dur in [0, 10, 100]:
                t = compute_adaptive_threshold("test", delta, dur, c).adaptive_threshold
                assert 2 <= t <= 8

    def test_inv162_deterministic_adaptation(self):
        """Invariant 162: Same inputs always produce same threshold."""
        for delta in [0.0, 0.1, 0.3]:
            for dur in [0, 5, 50]:
                t1 = _compute(delta, dur)
                t2 = _compute(delta, dur)
                assert t1 == t2

    def test_inv163_stable_regimes_resist_switching(self):
        """Invariant 163: Longer duration in a regime increases threshold."""
        t_fresh = _compute(0.0, 0)
        t_established = _compute(0.0, 50)
        assert t_established > t_fresh

    def test_inv163_across_many_durations(self):
        prev = _compute(0.0, 0)
        for dur in [1, 5, 10, 20, 50, 100]:
            t = _compute(0.0, dur)
            assert t >= prev
            prev = t

    def test_inv164_large_shifts_confirm_faster(self):
        """Invariant 164: Larger delta magnitude reduces threshold."""
        t_small = _compute(0.05, 0)
        t_large = _compute(0.3, 0)
        assert t_large < t_small

    def test_inv164_across_many_deltas(self):
        prev = _compute(0.0, 0)
        for delta in [0.05, 0.1, 0.15, 0.2, 0.25, 0.3]:
            t = _compute(delta, 0)
            assert t <= prev
            prev = t

    def test_inv165_no_oscillation_introduced(self):
        """Invariant 165: Monotonic behavior — no oscillation in threshold values."""
        for fixed_dur in [0, 5, 10]:
            deltas = [i * 0.02 for i in range(30)]
            thresholds = [_compute(d, fixed_dur) for d in deltas]
            for i in range(len(thresholds) - 1):
                assert thresholds[i + 1] <= thresholds[i]

    def test_inv165_monotonic_with_duration(self):
        for fixed_delta in [0.0, 0.1, 0.3]:
            durations = list(range(0, 100, 5))
            thresholds = [_compute(fixed_delta, d) for d in durations]
            for i in range(len(thresholds) - 1):
                assert thresholds[i + 1] >= thresholds[i]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 15: Edge cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEdgeCases:
    def test_negative_duration_treated_as_zero(self):
        t = _compute(0.0, -5)
        assert t == _compute(0.0, 0)

    def test_zero_delta_exact(self):
        t = _compute(0.0, 0)
        assert t == 3

    def test_negative_delta_magnitude_uses_abs_in_compute_all(self):
        snap = compute_all_thresholds({"test": -0.5}, {})
        assert snap.get_threshold("test") == 1

    def test_very_small_delta(self):
        t = _compute(0.001, 0)
        assert t == 3

    def test_single_signal(self):
        snap = compute_all_thresholds({"only": 0.0}, {"only": 0})
        assert len(snap.thresholds) == 1
        assert snap.get_threshold("only") == 3

    def test_many_signals(self):
        deltas = {f"sig_{i}": 0.0 for i in range(20)}
        snap = compute_all_thresholds(deltas, {})
        assert len(snap.thresholds) == 20

    def test_duration_1(self):
        t = _compute(0.0, 1)
        assert t >= 3

    def test_extreme_delta(self):
        t = _compute(10.0, 0)
        assert t == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 16: Serialization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSerialization:
    def test_all_dicts_json_serializable(self):
        import json

        r = compute_adaptive_threshold("urgency", 0.3, 5)
        json.dumps(r.to_dict())

        snap = compute_all_thresholds({"urgency": 0.3, "risk": 0.0}, {"urgency": 0, "risk": 50})
        json.dumps(snap.to_dict())

        c = DEFAULT_ADAPTIVE_CONFIG
        json.dumps(c.to_dict())

    def test_config_to_dict_roundtrip_shape(self):
        c = AdaptiveThresholdConfig()
        d = c.to_dict()
        assert set(d.keys()) == {
            "base_threshold",
            "min_threshold",
            "max_threshold",
            "volatility_weight",
            "stability_weight",
        }

    def test_threshold_result_to_dict_shape(self):
        r = compute_adaptive_threshold("test", 0.1, 5)
        d = r.to_dict()
        expected_keys = {
            "signal_name",
            "adaptive_threshold",
            "base_threshold",
            "factor",
            "delta_magnitude",
            "duration",
            "volatility_adjust",
            "stability_adjust",
        }
        assert set(d.keys()) == expected_keys


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 17: Dependency boundary
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDependencyBoundary:
    def test_no_io_imports(self):
        source = open("/opt/OS/umh/runtime/hysteresis_adaptive.py").read()
        tree = ast.parse(source)
        forbidden = {"os", "subprocess", "socket", "http", "requests", "urllib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert node.module.split(".")[0] not in forbidden

    def test_no_cell_imports(self):
        source = open("/opt/OS/umh/runtime/hysteresis_adaptive.py").read()
        assert "umh.cells" not in source
        assert "umh.environments" not in source
        assert "umh.adapters" not in source

    def test_no_umh_imports(self):
        source = open("/opt/OS/umh/runtime/hysteresis_adaptive.py").read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("umh."):
                pytest.fail(f"Unexpected umh import: {node.module}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 18: Exports and compilation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExportsAndCompilation:
    def test_hysteresis_adaptive_compiles(self):
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/hysteresis_adaptive.py", doraise=True)

    def test_init_compiles(self):
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/__init__.py", doraise=True)

    def test_exports_from_init(self):
        from umh.runtime import (
            DEFAULT_ADAPTIVE_CONFIG,
            AdaptiveThresholdConfig,
            ThresholdResult,
            ThresholdSnapshot,
            compute_adaptive_threshold,
            compute_all_thresholds,
        )

        assert AdaptiveThresholdConfig is not None
        assert ThresholdResult is not None
        assert ThresholdSnapshot is not None
        assert compute_adaptive_threshold is not None
        assert compute_all_thresholds is not None
        assert DEFAULT_ADAPTIVE_CONFIG is not None

    def test_in_all_list(self):
        from umh.runtime import __all__

        expected = [
            "DEFAULT_ADAPTIVE_CONFIG",
            "AdaptiveThresholdConfig",
            "ThresholdResult",
            "ThresholdSnapshot",
            "compute_adaptive_threshold",
            "compute_all_thresholds",
        ]
        for name in expected:
            assert name in __all__, f"{name} missing from __all__"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 19: Phase 44 regression
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPhase44Regression:
    def test_filter_regime_still_works(self):
        state = FilterState(signal_name="urgency")
        r = filter_regime(state, RT.SPIKE_UP, 3)
        assert r.filtered_regime is RT.STABLE
        assert r.was_suppressed is True

    def test_regime_filter_still_works(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for _ in range(3):
            snap = filt.filter({"urgency": RT.SPIKE_UP})
        assert snap.get_filtered_regime("urgency") is RT.SPIKE_UP

    def test_filter_noise_resistance(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for i in range(20):
            rt = RT.SPIKE_UP if i % 2 == 0 else RT.STABLE
            filt.filter({"urgency": rt})
        assert filt.get_confirmed_regime("urgency") is RT.STABLE

    def test_regime_memory_still_works(self):
        mem = RegimeMemory(signals=("urgency",))
        snap = classify_all_regimes({"urgency": 0.3}, tick=1)
        result = mem.update(snap)
        assert result.get_regime("urgency") is RT.SPIKE_UP

    def test_regime_memory_duration(self):
        mem = RegimeMemory(signals=("urgency",))
        for _ in range(5):
            mem.update(classify_all_regimes({"urgency": 0.0}, tick=0))
        assert mem.get_duration("urgency") == 5


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 20: Behavioral scenarios
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestBehavioralScenarios:
    def test_fast_signal_switches_quickly(self):
        state = FilterState(signal_name="urgency")
        t = _compute(0.5, 0)
        assert t == 1
        r = filter_regime(state, RT.SPIKE_UP, t)
        assert r.was_confirmed is True

    def test_stable_regime_resists_change(self):
        state = FilterState(signal_name="urgency")
        t = _compute(0.0, 100)
        assert t == 6
        for _ in range(5):
            r = filter_regime(state, RT.SPIKE_UP, t)
        assert r.filtered_regime is RT.STABLE

    def test_stable_regime_eventually_confirms(self):
        state = FilterState(signal_name="urgency")
        t = _compute(0.0, 100)
        assert t == 6
        for _ in range(6):
            r = filter_regime(state, RT.SPIKE_UP, t)
        assert r.filtered_regime is RT.SPIKE_UP

    def test_adaptive_vs_fixed_threshold(self):
        fixed_threshold = 3
        adaptive_fast = _compute(0.5, 0)
        adaptive_slow = _compute(0.0, 50)
        assert adaptive_fast < fixed_threshold
        assert adaptive_slow > fixed_threshold

    def test_threshold_progression_over_stable_ticks(self):
        thresholds = []
        for dur in range(0, 20):
            thresholds.append(_compute(0.0, dur))
        assert thresholds[0] <= thresholds[-1]
        assert all(thresholds[i] <= thresholds[i + 1] for i in range(len(thresholds) - 1))

    def test_spike_with_history_balances(self):
        t_fresh_spike = _compute(0.3, 0)
        t_established_spike = _compute(0.3, 50)
        assert t_fresh_spike < t_established_spike


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 21: Reference value verification
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestReferenceValues:
    def test_zero_zero(self):
        assert _compute(0.0, 0) == 3

    def test_delta_030_dur_0(self):
        assert _compute(0.3, 0) == 1

    def test_delta_050_dur_0(self):
        assert _compute(0.5, 0) == 1

    def test_delta_100_dur_0(self):
        assert _compute(1.0, 0) == 1

    def test_delta_000_dur_10(self):
        assert _compute(0.0, 10) == 6

    def test_delta_000_dur_100(self):
        assert _compute(0.0, 100) == 6

    def test_delta_030_dur_10(self):
        assert _compute(0.3, 10) == 5

    def test_delta_010_dur_5(self):
        assert _compute(0.1, 5) == 5

    def test_delta_000_dur_50(self):
        assert _compute(0.0, 50) == 6

    def test_delta_005_dur_0(self):
        assert _compute(0.05, 0) == 3

    def test_delta_015_dur_0(self):
        r = compute_adaptive_threshold("test", 0.15, 0)
        assert r.volatility_adjust == pytest.approx(0.3, abs=0.001)
        assert r.adaptive_threshold == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 22: Factor decomposition
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFactorDecomposition:
    def test_volatility_adjust_is_weight_times_delta(self):
        r = compute_adaptive_threshold("test", 0.2, 0)
        assert r.volatility_adjust == pytest.approx(0.4, abs=0.001)

    def test_stability_adjust_is_weight_times_log(self):
        r = compute_adaptive_threshold("test", 0.0, 10)
        expected = 0.5 * math.log(11)
        assert r.stability_adjust == pytest.approx(expected, abs=0.001)

    def test_factor_is_one_minus_vol_plus_stab(self):
        r = compute_adaptive_threshold("test", 0.2, 10)
        expected_factor = 1.0 - r.volatility_adjust + r.stability_adjust
        assert r.factor == pytest.approx(expected_factor, abs=0.0001)

    def test_threshold_is_rounded_base_times_factor(self):
        r = compute_adaptive_threshold("test", 0.1, 5)
        raw = r.base_threshold * r.factor
        assert r.adaptive_threshold == max(1, min(6, round(raw)))

    def test_base_threshold_in_result(self):
        r = compute_adaptive_threshold("test", 0.0, 0)
        assert r.base_threshold == 3

    def test_signal_name_in_result(self):
        r = compute_adaptive_threshold("my_signal", 0.0, 0)
        assert r.signal_name == "my_signal"

    def test_delta_magnitude_in_result(self):
        r = compute_adaptive_threshold("test", 0.25, 0)
        assert r.delta_magnitude == 0.25

    def test_duration_in_result(self):
        r = compute_adaptive_threshold("test", 0.0, 42)
        assert r.duration == 42


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 23: Per-signal differentiation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPerSignalDifferentiation:
    def test_different_deltas_different_thresholds(self):
        snap = compute_all_thresholds(
            {"fast": 0.5, "slow": 0.0},
            {"fast": 0, "slow": 0},
        )
        assert snap.get_threshold("fast") < snap.get_threshold("slow")

    def test_different_durations_different_thresholds(self):
        snap = compute_all_thresholds(
            {"fresh": 0.0, "established": 0.0},
            {"fresh": 0, "established": 100},
        )
        assert snap.get_threshold("fresh") < snap.get_threshold("established")

    def test_signals_computed_independently(self):
        snap = compute_all_thresholds(
            {"a": 0.3, "b": 0.0},
            {"a": 0, "b": 50},
        )
        a_solo = _compute(0.3, 0)
        b_solo = _compute(0.0, 50)
        assert snap.get_threshold("a") == a_solo
        assert snap.get_threshold("b") == b_solo

    def test_min_max_reflect_spread(self):
        snap = compute_all_thresholds(
            {"fast": 0.5, "slow": 0.0},
            {"fast": 0, "slow": 100},
        )
        assert snap.min_threshold() == 1
        assert snap.max_threshold() == 6

    def test_all_same_delta_same_duration(self):
        snap = compute_all_thresholds(
            {"a": 0.1, "b": 0.1, "c": 0.1},
            {"a": 5, "b": 5, "c": 5},
        )
        ts = [snap.get_threshold(n) for n in ["a", "b", "c"]]
        assert ts[0] == ts[1] == ts[2]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 24: Stability analysis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestStabilityAnalysis:
    def test_threshold_plateau_at_max(self):
        t_500 = _compute(0.0, 500)
        t_1000 = _compute(0.0, 1000)
        assert t_500 == t_1000 == 6

    def test_threshold_plateau_at_min(self):
        t_1 = _compute(1.0, 0)
        t_5 = _compute(5.0, 0)
        assert t_1 == t_5 == 1

    def test_log_curve_diminishing_returns(self):
        diff_0_to_10 = _factor(0.0, 10) - _factor(0.0, 0)
        diff_100_to_110 = _factor(0.0, 110) - _factor(0.0, 100)
        assert diff_0_to_10 > diff_100_to_110

    def test_volatility_linear_scaling(self):
        r1 = compute_adaptive_threshold("test", 0.1, 0)
        r2 = compute_adaptive_threshold("test", 0.2, 0)
        assert r2.volatility_adjust == pytest.approx(2 * r1.volatility_adjust, abs=0.001)

    def test_stability_does_not_depend_on_delta(self):
        r1 = compute_adaptive_threshold("test", 0.0, 10)
        r2 = compute_adaptive_threshold("test", 0.5, 10)
        assert r1.stability_adjust == r2.stability_adjust

    def test_volatility_does_not_depend_on_duration(self):
        r1 = compute_adaptive_threshold("test", 0.2, 0)
        r2 = compute_adaptive_threshold("test", 0.2, 100)
        assert r1.volatility_adjust == r2.volatility_adjust

    def test_threshold_sweep_delta_at_dur_0(self):
        results = [(d, _compute(d, 0)) for d in [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]]
        for i in range(len(results) - 1):
            assert results[i][1] >= results[i + 1][1]

    def test_threshold_sweep_duration_at_delta_0(self):
        results = [(d, _compute(0.0, d)) for d in [0, 1, 2, 5, 10, 20, 50]]
        for i in range(len(results) - 1):
            assert results[i][1] <= results[i + 1][1]

    def test_config_with_base_5(self):
        c = AdaptiveThresholdConfig(base_threshold=5, max_threshold=10)
        assert compute_adaptive_threshold("test", 0.0, 0, c).adaptive_threshold == 5

    def test_equal_opposing_forces(self):
        r = compute_adaptive_threshold("test", 0.1, 5)
        assert r.volatility_adjust > 0
        assert r.stability_adjust > 0
