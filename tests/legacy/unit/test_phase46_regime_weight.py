"""Phase 46 — Regime-Aware Weight Adaptation Layer v1.

150+ tests covering:
- Core factor computation per regime type
- Duration scaling for trends
- Clamping / bounds enforcement
- Config validation
- Snapshot operations
- Batch computation
- apply_regime_weight
- Determinism
- Monotonicity
- Pipeline integration with prior phases
- Serialization
- Edge cases
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.runtime.regime import RegimeType
from umh.runtime.regime_weight import (
    DEFAULT_WEIGHT_CONFIG,
    RegimeWeightConfig,
    RegimeWeightResult,
    RegimeWeightSnapshot,
    apply_regime_weight,
    compute_all_regime_factors,
    compute_regime_factor,
    _STABLE_FACTOR,
    _SPIKE_FACTOR_UP,
    _SPIKE_FACTOR_DOWN,
    _TREND_BASE_UP,
    _TREND_BASE_DOWN,
    _TREND_DURATION_RATE,
    _TREND_DURATION_CAP,
    _DEFAULT_MIN_FACTOR,
    _DEFAULT_MAX_FACTOR,
)


# ── Section 1: STABLE regime ────────────────────────────────────────


class TestStableRegime:
    def test_stable_factor_is_one(self):
        r = compute_regime_factor("urgency", RegimeType.STABLE, 0)
        assert r.factor == 1.0

    def test_stable_factor_duration_zero(self):
        r = compute_regime_factor("urgency", RegimeType.STABLE, 0)
        assert r.factor == 1.0

    def test_stable_factor_duration_100(self):
        r = compute_regime_factor("urgency", RegimeType.STABLE, 100)
        assert r.factor == 1.0

    def test_stable_factor_duration_1000(self):
        r = compute_regime_factor("urgency", RegimeType.STABLE, 1000)
        assert r.factor == 1.0

    def test_stable_reason(self):
        r = compute_regime_factor("urgency", RegimeType.STABLE, 0)
        assert "stable" in r.reason.lower()

    def test_stable_regime_stored(self):
        r = compute_regime_factor("urgency", RegimeType.STABLE, 5)
        assert r.regime == RegimeType.STABLE

    def test_stable_signal_name(self):
        r = compute_regime_factor("risk_level", RegimeType.STABLE, 0)
        assert r.signal_name == "risk_level"

    def test_stable_raw_equals_factor(self):
        r = compute_regime_factor("urgency", RegimeType.STABLE, 0)
        assert r.raw_factor == r.factor


# ── Section 2: TREND_UP regime ──────────────────────────────────────


class TestTrendUpRegime:
    def test_trend_up_base(self):
        r = compute_regime_factor("urgency", RegimeType.TREND_UP, 0)
        assert r.factor == _TREND_BASE_UP

    def test_trend_up_increases_factor(self):
        r = compute_regime_factor("urgency", RegimeType.TREND_UP, 0)
        assert r.factor > 1.0

    def test_trend_up_duration_1(self):
        r = compute_regime_factor("urgency", RegimeType.TREND_UP, 1)
        expected = _TREND_BASE_UP + min(_TREND_DURATION_CAP, 1 * _TREND_DURATION_RATE)
        assert r.factor == pytest.approx(expected)

    def test_trend_up_duration_5(self):
        r = compute_regime_factor("urgency", RegimeType.TREND_UP, 5)
        expected = _TREND_BASE_UP + min(_TREND_DURATION_CAP, 5 * _TREND_DURATION_RATE)
        assert r.factor == pytest.approx(expected)

    def test_trend_up_duration_10(self):
        r = compute_regime_factor("urgency", RegimeType.TREND_UP, 10)
        expected = _TREND_BASE_UP + _TREND_DURATION_CAP
        assert r.factor == pytest.approx(expected)

    def test_trend_up_duration_100_capped(self):
        r = compute_regime_factor("urgency", RegimeType.TREND_UP, 100)
        expected = _TREND_BASE_UP + _TREND_DURATION_CAP
        assert r.factor == pytest.approx(expected)

    def test_trend_up_monotonic_with_duration(self):
        factors = [
            compute_regime_factor("urgency", RegimeType.TREND_UP, d).factor
            for d in range(20)
        ]
        for i in range(1, len(factors)):
            assert factors[i] >= factors[i - 1]

    def test_trend_up_reason_contains_bonus(self):
        r = compute_regime_factor("urgency", RegimeType.TREND_UP, 5)
        assert "bonus" in r.reason.lower()

    def test_trend_up_greater_than_stable(self):
        stable = compute_regime_factor("urgency", RegimeType.STABLE, 0).factor
        trend = compute_regime_factor("urgency", RegimeType.TREND_UP, 0).factor
        assert trend > stable


# ── Section 3: TREND_DOWN regime ────────────────────────────────────


class TestTrendDownRegime:
    def test_trend_down_base(self):
        r = compute_regime_factor("urgency", RegimeType.TREND_DOWN, 0)
        assert r.factor == _TREND_BASE_DOWN

    def test_trend_down_decreases_factor(self):
        r = compute_regime_factor("urgency", RegimeType.TREND_DOWN, 0)
        assert r.factor < 1.0

    def test_trend_down_duration_1(self):
        r = compute_regime_factor("urgency", RegimeType.TREND_DOWN, 1)
        expected = _TREND_BASE_DOWN - min(_TREND_DURATION_CAP, 1 * _TREND_DURATION_RATE)
        assert r.factor == pytest.approx(expected)

    def test_trend_down_duration_5(self):
        r = compute_regime_factor("urgency", RegimeType.TREND_DOWN, 5)
        expected = _TREND_BASE_DOWN - min(_TREND_DURATION_CAP, 5 * _TREND_DURATION_RATE)
        assert r.factor == pytest.approx(expected)

    def test_trend_down_duration_10_capped(self):
        r = compute_regime_factor("urgency", RegimeType.TREND_DOWN, 10)
        expected = _TREND_BASE_DOWN - _TREND_DURATION_CAP
        assert r.factor == pytest.approx(expected)

    def test_trend_down_duration_100_capped(self):
        r = compute_regime_factor("urgency", RegimeType.TREND_DOWN, 100)
        expected = _TREND_BASE_DOWN - _TREND_DURATION_CAP
        assert r.factor == pytest.approx(expected)

    def test_trend_down_monotonic_decreasing(self):
        factors = [
            compute_regime_factor("urgency", RegimeType.TREND_DOWN, d).factor
            for d in range(20)
        ]
        for i in range(1, len(factors)):
            assert factors[i] <= factors[i - 1]

    def test_trend_down_reason_contains_penalty(self):
        r = compute_regime_factor("urgency", RegimeType.TREND_DOWN, 5)
        assert "penalty" in r.reason.lower()

    def test_trend_down_less_than_stable(self):
        stable = compute_regime_factor("urgency", RegimeType.STABLE, 0).factor
        trend = compute_regime_factor("urgency", RegimeType.TREND_DOWN, 0).factor
        assert trend < stable


# ── Section 4: SPIKE_UP regime ──────────────────────────────────────


class TestSpikeUpRegime:
    def test_spike_up_factor(self):
        r = compute_regime_factor("urgency", RegimeType.SPIKE_UP, 0)
        assert r.factor == _SPIKE_FACTOR_UP

    def test_spike_up_no_duration_scaling(self):
        r0 = compute_regime_factor("urgency", RegimeType.SPIKE_UP, 0)
        r100 = compute_regime_factor("urgency", RegimeType.SPIKE_UP, 100)
        assert r0.factor == r100.factor

    def test_spike_up_greater_than_trend_up(self):
        spike = compute_regime_factor("urgency", RegimeType.SPIKE_UP, 0).factor
        trend = compute_regime_factor("urgency", RegimeType.TREND_UP, 0).factor
        assert spike > trend

    def test_spike_up_reason(self):
        r = compute_regime_factor("urgency", RegimeType.SPIKE_UP, 0)
        assert "spike" in r.reason.lower()

    def test_spike_up_raw_equals_factor(self):
        r = compute_regime_factor("urgency", RegimeType.SPIKE_UP, 0)
        assert r.raw_factor == r.factor


# ── Section 5: SPIKE_DOWN regime ────────────────────────────────────


class TestSpikeDownRegime:
    def test_spike_down_factor(self):
        r = compute_regime_factor("urgency", RegimeType.SPIKE_DOWN, 0)
        assert r.factor == _SPIKE_FACTOR_DOWN

    def test_spike_down_no_duration_scaling(self):
        r0 = compute_regime_factor("urgency", RegimeType.SPIKE_DOWN, 0)
        r100 = compute_regime_factor("urgency", RegimeType.SPIKE_DOWN, 100)
        assert r0.factor == r100.factor

    def test_spike_down_less_than_trend_down(self):
        spike = compute_regime_factor("urgency", RegimeType.SPIKE_DOWN, 0).factor
        trend = compute_regime_factor("urgency", RegimeType.TREND_DOWN, 0).factor
        assert spike < trend

    def test_spike_down_reason(self):
        r = compute_regime_factor("urgency", RegimeType.SPIKE_DOWN, 0)
        assert "spike" in r.reason.lower()


# ── Section 6: Ordering invariants ──────────────────────────────────


class TestFactorOrdering:
    def test_spike_down_lt_trend_down_lt_stable_lt_trend_up_lt_spike_up(self):
        sd = compute_regime_factor("s", RegimeType.SPIKE_DOWN, 0).factor
        td = compute_regime_factor("s", RegimeType.TREND_DOWN, 0).factor
        st = compute_regime_factor("s", RegimeType.STABLE, 0).factor
        tu = compute_regime_factor("s", RegimeType.TREND_UP, 0).factor
        su = compute_regime_factor("s", RegimeType.SPIKE_UP, 0).factor
        assert sd < td < st < tu < su

    def test_all_regimes_produce_different_factors(self):
        factors = set()
        for rt in RegimeType:
            f = compute_regime_factor("s", rt, 0).factor
            factors.add(f)
        assert len(factors) == 5

    def test_symmetric_distance_spike(self):
        up = compute_regime_factor("s", RegimeType.SPIKE_UP, 0).factor
        down = compute_regime_factor("s", RegimeType.SPIKE_DOWN, 0).factor
        assert abs(up - 1.0) == pytest.approx(abs(down - 1.0))

    def test_symmetric_distance_trend(self):
        up = compute_regime_factor("s", RegimeType.TREND_UP, 0).factor
        down = compute_regime_factor("s", RegimeType.TREND_DOWN, 0).factor
        assert abs(up - 1.0) == pytest.approx(abs(down - 1.0))


# ── Section 7: Clamping / bounds ────────────────────────────────────


class TestBoundsEnforcement:
    def test_default_min_factor(self):
        assert DEFAULT_WEIGHT_CONFIG.min_factor == 0.85

    def test_default_max_factor(self):
        assert DEFAULT_WEIGHT_CONFIG.max_factor == 1.15

    def test_factor_never_below_min(self):
        for rt in RegimeType:
            for d in [0, 1, 5, 10, 50, 100, 1000]:
                r = compute_regime_factor("s", rt, d)
                assert r.factor >= _DEFAULT_MIN_FACTOR

    def test_factor_never_above_max(self):
        for rt in RegimeType:
            for d in [0, 1, 5, 10, 50, 100, 1000]:
                r = compute_regime_factor("s", rt, d)
                assert r.factor <= _DEFAULT_MAX_FACTOR

    def test_clamp_with_extreme_config_up(self):
        cfg = RegimeWeightConfig(spike_factor_up=2.0, max_factor=1.15)
        r = compute_regime_factor("s", RegimeType.SPIKE_UP, 0, cfg)
        assert r.factor == cfg.max_factor
        assert r.raw_factor == 2.0

    def test_clamp_with_extreme_config_down(self):
        cfg = RegimeWeightConfig(spike_factor_down=0.1, min_factor=0.85)
        r = compute_regime_factor("s", RegimeType.SPIKE_DOWN, 0, cfg)
        assert r.factor == 0.85
        assert r.raw_factor == pytest.approx(0.1)

    def test_clamp_trend_up_extreme_duration_rate(self):
        cfg = RegimeWeightConfig(trend_duration_rate=1.0, trend_duration_cap=10.0)
        r = compute_regime_factor("s", RegimeType.TREND_UP, 100, cfg)
        assert r.factor <= cfg.max_factor

    def test_clamp_trend_down_extreme_duration_rate(self):
        cfg = RegimeWeightConfig(trend_duration_rate=1.0, trend_duration_cap=10.0)
        r = compute_regime_factor("s", RegimeType.TREND_DOWN, 100, cfg)
        assert r.factor >= cfg.min_factor

    def test_regime_factor_bounded_invariant_166(self):
        for rt in RegimeType:
            for d in range(50):
                r = compute_regime_factor("s", rt, d)
                assert _DEFAULT_MIN_FACTOR <= r.factor <= _DEFAULT_MAX_FACTOR


# ── Section 8: Config validation ────────────────────────────────────


class TestConfigValidation:
    def test_default_config_values(self):
        c = DEFAULT_WEIGHT_CONFIG
        assert c.min_factor == 0.85
        assert c.max_factor == 1.15
        assert c.trend_base_up == 1.05
        assert c.trend_base_down == 0.95
        assert c.trend_duration_rate == 0.005
        assert c.trend_duration_cap == 0.05
        assert c.spike_factor_up == 1.10
        assert c.spike_factor_down == 0.90
        assert c.stable_factor == 1.0

    def test_min_factor_clamped_to_0_5(self):
        c = RegimeWeightConfig(min_factor=0.1)
        assert c.min_factor == 0.5

    def test_max_factor_at_least_min(self):
        c = RegimeWeightConfig(min_factor=0.9, max_factor=0.8)
        assert c.max_factor >= c.min_factor

    def test_negative_duration_rate_clamped(self):
        c = RegimeWeightConfig(trend_duration_rate=-1.0)
        assert c.trend_duration_rate == 0.0

    def test_negative_duration_cap_clamped(self):
        c = RegimeWeightConfig(trend_duration_cap=-1.0)
        assert c.trend_duration_cap == 0.0

    def test_spike_up_clamped_to_1(self):
        c = RegimeWeightConfig(spike_factor_up=0.5)
        assert c.spike_factor_up == 1.0

    def test_spike_down_clamped_to_0_1(self):
        c = RegimeWeightConfig(spike_factor_down=-0.5)
        assert c.spike_factor_down == 0.0

    def test_trend_base_up_clamped_to_1(self):
        c = RegimeWeightConfig(trend_base_up=0.5)
        assert c.trend_base_up == 1.0

    def test_trend_base_down_clamped_to_0_1(self):
        c = RegimeWeightConfig(trend_base_down=-0.5)
        assert c.trend_base_down == 0.0

    def test_config_frozen(self):
        c = RegimeWeightConfig()
        with pytest.raises(AttributeError):
            c.min_factor = 0.5

    def test_config_to_dict(self):
        d = DEFAULT_WEIGHT_CONFIG.to_dict()
        assert "min_factor" in d
        assert "max_factor" in d
        assert "spike_factor_up" in d
        assert len(d) == 9

    def test_config_to_dict_rounded(self):
        c = RegimeWeightConfig(trend_duration_rate=0.123456789)
        d = c.to_dict()
        assert d["trend_duration_rate"] == 0.1235


# ── Section 9: Determinism (invariant 167) ──────────────────────────


class TestDeterminism:
    def test_same_inputs_same_output(self):
        r1 = compute_regime_factor("urgency", RegimeType.TREND_UP, 5)
        r2 = compute_regime_factor("urgency", RegimeType.TREND_UP, 5)
        assert r1.factor == r2.factor

    def test_deterministic_across_100_calls(self):
        results = [
            compute_regime_factor("urgency", RegimeType.SPIKE_UP, 3).factor
            for _ in range(100)
        ]
        assert len(set(results)) == 1

    def test_same_regime_same_factor_invariant_168(self):
        for rt in RegimeType:
            f1 = compute_regime_factor("a", rt, 7).factor
            f2 = compute_regime_factor("b", rt, 7).factor
            assert f1 == f2

    def test_deterministic_mapping_invariant_167(self):
        for rt in RegimeType:
            for d in [0, 1, 5, 10, 50]:
                f1 = compute_regime_factor("s", rt, d).factor
                f2 = compute_regime_factor("s", rt, d).factor
                assert f1 == f2


# ── Section 10: No state mutation (invariant 169) ───────────────────


class TestNoStateMutation:
    def test_config_unchanged_after_compute(self):
        cfg = RegimeWeightConfig()
        before = cfg.to_dict()
        compute_regime_factor("s", RegimeType.TREND_UP, 10, cfg)
        after = cfg.to_dict()
        assert before == after

    def test_result_frozen(self):
        r = compute_regime_factor("s", RegimeType.STABLE, 0)
        with pytest.raises(AttributeError):
            r.factor = 2.0

    def test_snapshot_weights_are_frozen(self):
        snap = compute_all_regime_factors(
            {"a": RegimeType.STABLE}, {"a": 0}
        )
        r = snap.get("a")
        with pytest.raises(AttributeError):
            r.factor = 2.0

    def test_no_side_effects_on_repeated_calls(self):
        results = []
        for _ in range(10):
            r = compute_regime_factor("s", RegimeType.TREND_UP, 5)
            results.append(r.factor)
        assert all(f == results[0] for f in results)


# ── Section 11: Regime cannot dominate score (invariant 170) ────────


class TestRegimeCannotDominate:
    def test_max_influence_is_15_percent(self):
        for rt in RegimeType:
            for d in range(50):
                r = compute_regime_factor("s", rt, d)
                deviation = abs(r.factor - 1.0)
                assert deviation <= 0.15 + 1e-9

    def test_factor_1_0_preserves_score(self):
        assert apply_regime_weight(100.0, 1.0) == 100.0

    def test_max_factor_increases_by_15_percent(self):
        result = apply_regime_weight(100.0, 1.15)
        assert result == pytest.approx(115.0)

    def test_min_factor_decreases_by_15_percent(self):
        result = apply_regime_weight(100.0, 0.85)
        assert result == pytest.approx(85.0)

    def test_regime_weaker_than_base_score(self):
        base = 50.0
        for rt in RegimeType:
            for d in [0, 5, 10, 50]:
                f = compute_regime_factor("s", rt, d).factor
                adjusted = apply_regime_weight(base, f)
                assert adjusted >= base * 0.85
                assert adjusted <= base * 1.15


# ── Section 12: apply_regime_weight ─────────────────────────────────


class TestApplyRegimeWeight:
    def test_neutral_factor(self):
        assert apply_regime_weight(10.0, 1.0) == 10.0

    def test_boost_factor(self):
        assert apply_regime_weight(10.0, 1.10) == pytest.approx(11.0)

    def test_reduction_factor(self):
        assert apply_regime_weight(10.0, 0.90) == pytest.approx(9.0)

    def test_zero_score(self):
        assert apply_regime_weight(0.0, 1.15) == 0.0

    def test_negative_score(self):
        assert apply_regime_weight(-10.0, 1.10) == pytest.approx(-11.0)

    def test_large_score(self):
        assert apply_regime_weight(1000.0, 1.05) == pytest.approx(1050.0)


# ── Section 13: RegimeWeightResult ──────────────────────────────────


class TestRegimeWeightResult:
    def test_to_dict_keys(self):
        r = compute_regime_factor("urgency", RegimeType.SPIKE_UP, 3)
        d = r.to_dict()
        assert set(d.keys()) == {
            "signal_name", "factor", "raw_factor", "regime", "duration", "reason"
        }

    def test_to_dict_regime_is_string(self):
        r = compute_regime_factor("urgency", RegimeType.SPIKE_UP, 3)
        d = r.to_dict()
        assert d["regime"] == "spike_up"

    def test_to_dict_factor_rounded(self):
        r = compute_regime_factor("urgency", RegimeType.TREND_UP, 3)
        d = r.to_dict()
        assert isinstance(d["factor"], float)

    def test_duration_stored(self):
        r = compute_regime_factor("urgency", RegimeType.STABLE, 42)
        assert r.duration == 42


# ── Section 14: RegimeWeightSnapshot ────────────────────────────────


class TestRegimeWeightSnapshot:
    def test_get_existing(self):
        snap = compute_all_regime_factors(
            {"urgency": RegimeType.STABLE}, {"urgency": 0}
        )
        assert snap.get("urgency") is not None

    def test_get_missing(self):
        snap = compute_all_regime_factors(
            {"urgency": RegimeType.STABLE}, {"urgency": 0}
        )
        assert snap.get("nonexistent") is None

    def test_get_factor_existing(self):
        snap = compute_all_regime_factors(
            {"urgency": RegimeType.SPIKE_UP}, {"urgency": 0}
        )
        assert snap.get_factor("urgency") == _SPIKE_FACTOR_UP

    def test_get_factor_missing_default(self):
        snap = compute_all_regime_factors(
            {"urgency": RegimeType.STABLE}, {"urgency": 0}
        )
        assert snap.get_factor("missing") == 1.0

    def test_get_factor_missing_custom_default(self):
        snap = compute_all_regime_factors(
            {"urgency": RegimeType.STABLE}, {"urgency": 0}
        )
        assert snap.get_factor("missing", default=0.5) == 0.5

    def test_min_factor(self):
        snap = compute_all_regime_factors(
            {"a": RegimeType.SPIKE_DOWN, "b": RegimeType.STABLE},
            {"a": 0, "b": 0},
        )
        assert snap.min_factor() == _SPIKE_FACTOR_DOWN

    def test_max_factor(self):
        snap = compute_all_regime_factors(
            {"a": RegimeType.SPIKE_UP, "b": RegimeType.STABLE},
            {"a": 0, "b": 0},
        )
        assert snap.max_factor() == _SPIKE_FACTOR_UP

    def test_min_factor_empty(self):
        snap = RegimeWeightSnapshot(weights={})
        assert snap.min_factor() == 1.0

    def test_max_factor_empty(self):
        snap = RegimeWeightSnapshot(weights={})
        assert snap.max_factor() == 1.0

    def test_all_neutral_true(self):
        snap = compute_all_regime_factors(
            {"a": RegimeType.STABLE, "b": RegimeType.STABLE},
            {"a": 0, "b": 0},
        )
        assert snap.all_neutral() is True

    def test_all_neutral_false(self):
        snap = compute_all_regime_factors(
            {"a": RegimeType.STABLE, "b": RegimeType.SPIKE_UP},
            {"a": 0, "b": 0},
        )
        assert snap.all_neutral() is False

    def test_biased_signals_empty_when_all_stable(self):
        snap = compute_all_regime_factors(
            {"a": RegimeType.STABLE, "b": RegimeType.STABLE},
            {"a": 0, "b": 0},
        )
        assert snap.biased_signals() == []

    def test_biased_signals_returns_non_stable(self):
        snap = compute_all_regime_factors(
            {"a": RegimeType.STABLE, "b": RegimeType.SPIKE_UP, "c": RegimeType.TREND_DOWN},
            {"a": 0, "b": 0, "c": 0},
        )
        assert snap.biased_signals() == ["b", "c"]

    def test_to_dict(self):
        snap = compute_all_regime_factors(
            {"urgency": RegimeType.STABLE}, {"urgency": 0}
        )
        d = snap.to_dict()
        assert "weights" in d
        assert "urgency" in d["weights"]


# ── Section 15: compute_all_regime_factors ──────────────────────────


class TestComputeAllRegimeFactors:
    def test_single_signal(self):
        snap = compute_all_regime_factors(
            {"urgency": RegimeType.STABLE}, {"urgency": 0}
        )
        assert len(snap.weights) == 1

    def test_four_signals(self):
        regimes = {
            "urgency": RegimeType.SPIKE_UP,
            "risk_level": RegimeType.TREND_DOWN,
            "resource_pressure": RegimeType.STABLE,
            "stability_mode": RegimeType.TREND_UP,
        }
        durations = {"urgency": 0, "risk_level": 5, "resource_pressure": 10, "stability_mode": 3}
        snap = compute_all_regime_factors(regimes, durations)
        assert len(snap.weights) == 4

    def test_missing_duration_defaults_to_zero(self):
        snap = compute_all_regime_factors(
            {"urgency": RegimeType.TREND_UP}, {}
        )
        r = snap.get("urgency")
        assert r.duration == 0

    def test_extra_durations_ignored(self):
        snap = compute_all_regime_factors(
            {"urgency": RegimeType.STABLE},
            {"urgency": 0, "extra": 99},
        )
        assert len(snap.weights) == 1

    def test_sorted_by_name(self):
        regimes = {"c": RegimeType.STABLE, "a": RegimeType.STABLE, "b": RegimeType.STABLE}
        snap = compute_all_regime_factors(regimes, {})
        keys = list(snap.weights.keys())
        assert keys == ["a", "b", "c"]

    def test_empty_regimes(self):
        snap = compute_all_regime_factors({}, {})
        assert len(snap.weights) == 0

    def test_custom_config_propagated(self):
        cfg = RegimeWeightConfig(spike_factor_up=1.12)
        snap = compute_all_regime_factors(
            {"s": RegimeType.SPIKE_UP}, {"s": 0}, cfg
        )
        assert snap.get("s").factor == 1.12


# ── Section 16: Negative duration ───────────────────────────────────


class TestNegativeDuration:
    def test_negative_duration_clamped_to_zero(self):
        r = compute_regime_factor("s", RegimeType.TREND_UP, -5)
        r0 = compute_regime_factor("s", RegimeType.TREND_UP, 0)
        assert r.factor == r0.factor

    def test_negative_duration_stored_as_zero(self):
        r = compute_regime_factor("s", RegimeType.TREND_UP, -10)
        assert r.duration == 0


# ── Section 17: Duration cap boundary ──────────────────────────────


class TestDurationCapBoundary:
    def test_exactly_at_cap_trend_up(self):
        cap_duration = int(_TREND_DURATION_CAP / _TREND_DURATION_RATE)
        r = compute_regime_factor("s", RegimeType.TREND_UP, cap_duration)
        expected = _TREND_BASE_UP + _TREND_DURATION_CAP
        assert r.factor == pytest.approx(expected)

    def test_one_below_cap_trend_up(self):
        cap_duration = int(_TREND_DURATION_CAP / _TREND_DURATION_RATE)
        r = compute_regime_factor("s", RegimeType.TREND_UP, cap_duration - 1)
        expected = _TREND_BASE_UP + (cap_duration - 1) * _TREND_DURATION_RATE
        assert r.factor == pytest.approx(expected)

    def test_one_above_cap_trend_up(self):
        cap_duration = int(_TREND_DURATION_CAP / _TREND_DURATION_RATE)
        r = compute_regime_factor("s", RegimeType.TREND_UP, cap_duration + 1)
        expected = _TREND_BASE_UP + _TREND_DURATION_CAP
        assert r.factor == pytest.approx(expected)

    def test_exactly_at_cap_trend_down(self):
        cap_duration = int(_TREND_DURATION_CAP / _TREND_DURATION_RATE)
        r = compute_regime_factor("s", RegimeType.TREND_DOWN, cap_duration)
        expected = _TREND_BASE_DOWN - _TREND_DURATION_CAP
        assert r.factor == pytest.approx(expected)

    def test_trend_up_max_factor_at_cap(self):
        r = compute_regime_factor("s", RegimeType.TREND_UP, 1000)
        assert r.factor == pytest.approx(_TREND_BASE_UP + _TREND_DURATION_CAP)

    def test_trend_down_min_factor_at_cap(self):
        r = compute_regime_factor("s", RegimeType.TREND_DOWN, 1000)
        assert r.factor == pytest.approx(_TREND_BASE_DOWN - _TREND_DURATION_CAP)


# ── Section 18: Multiple signals independence ──────────────────────


class TestSignalIndependence:
    def test_different_regimes_different_factors(self):
        snap = compute_all_regime_factors(
            {"a": RegimeType.SPIKE_UP, "b": RegimeType.SPIKE_DOWN},
            {"a": 0, "b": 0},
        )
        assert snap.get_factor("a") != snap.get_factor("b")

    def test_signal_name_does_not_affect_factor(self):
        r1 = compute_regime_factor("alpha", RegimeType.TREND_UP, 5)
        r2 = compute_regime_factor("beta", RegimeType.TREND_UP, 5)
        assert r1.factor == r2.factor

    def test_no_cross_signal_contamination(self):
        snap1 = compute_all_regime_factors(
            {"a": RegimeType.SPIKE_UP}, {"a": 0}
        )
        snap2 = compute_all_regime_factors(
            {"a": RegimeType.SPIKE_UP, "b": RegimeType.SPIKE_DOWN},
            {"a": 0, "b": 0},
        )
        assert snap1.get_factor("a") == snap2.get_factor("a")


# ── Section 19: Scoring chain integration ──────────────────────────


class TestScoringChainIntegration:
    def test_full_scoring_chain(self):
        base_score = 80.0
        identity_factor = 1.05
        goal_bias = 1.02
        regime_factor = compute_regime_factor("urgency", RegimeType.TREND_UP, 5).factor

        score = base_score * identity_factor * goal_bias * regime_factor
        assert score > base_score

    def test_scoring_chain_stable_regime_preserves_prior_factors(self):
        base_score = 80.0
        identity_factor = 1.05
        goal_bias = 1.02
        regime_factor = compute_regime_factor("urgency", RegimeType.STABLE, 0).factor

        score = base_score * identity_factor * goal_bias * regime_factor
        expected = base_score * identity_factor * goal_bias
        assert score == pytest.approx(expected)

    def test_scoring_chain_spike_down_reduces(self):
        base_score = 100.0
        identity_factor = 1.0
        goal_bias = 1.0
        regime_factor = compute_regime_factor("urgency", RegimeType.SPIKE_DOWN, 0).factor

        score = base_score * identity_factor * goal_bias * regime_factor
        assert score < base_score

    def test_regime_factor_in_chain_bounded(self):
        base_score = 100.0
        for rt in RegimeType:
            f = compute_regime_factor("s", rt, 50).factor
            adjusted = base_score * f
            assert 85.0 <= adjusted <= 115.0


# ── Section 20: Pipeline integration with Phase 42-45 ──────────────


class TestPipelineIntegration:
    def test_regime_to_weight_pipeline(self):
        from umh.runtime.regime import classify_regime, RegimeThresholds

        thresholds = RegimeThresholds()
        result = classify_regime("urgency", 0.30, thresholds)
        r = compute_regime_factor("urgency", result.regime, 0)
        assert r.regime == RegimeType.SPIKE_UP
        assert r.factor == _SPIKE_FACTOR_UP

    def test_stable_classify_to_weight(self):
        from umh.runtime.regime import classify_regime, RegimeThresholds

        thresholds = RegimeThresholds()
        result = classify_regime("urgency", 0.01, thresholds)
        r = compute_regime_factor("urgency", result.regime, 10)
        assert r.regime == RegimeType.STABLE
        assert r.factor == 1.0

    def test_trend_classify_to_weight(self):
        from umh.runtime.regime import classify_regime, RegimeThresholds

        thresholds = RegimeThresholds()
        result = classify_regime("urgency", 0.15, thresholds)
        r = compute_regime_factor("urgency", result.regime, 3)
        assert r.regime == RegimeType.TREND_UP
        expected = _TREND_BASE_UP + min(_TREND_DURATION_CAP, 3 * _TREND_DURATION_RATE)
        assert r.factor == pytest.approx(expected)

    def test_filter_then_weight(self):
        from umh.runtime.regime_filter import FilterState, filter_regime

        state = FilterState(signal_name="urgency", confirmed_regime=RegimeType.STABLE)
        fr = filter_regime(state, RegimeType.SPIKE_UP, 1)
        r = compute_regime_factor("urgency", fr.filtered_regime, 0)
        assert r.regime == RegimeType.SPIKE_UP
        assert r.factor == _SPIKE_FACTOR_UP

    def test_filter_suppressed_uses_confirmed(self):
        from umh.runtime.regime_filter import FilterState, filter_regime

        state = FilterState(signal_name="urgency", confirmed_regime=RegimeType.STABLE)
        fr = filter_regime(state, RegimeType.SPIKE_UP, 3)
        r = compute_regime_factor("urgency", fr.filtered_regime, 10)
        assert r.regime == RegimeType.STABLE
        assert r.factor == 1.0

    def test_full_pipeline_classify_memory_filter_weight(self):
        from umh.runtime.regime import classify_regime, RegimeThresholds
        from umh.runtime.regime_memory import RegimeMemory, RegimeState
        from umh.runtime.regime_filter import RegimeFilter

        thresholds = RegimeThresholds()

        classified = classify_regime("urgency", 0.30, thresholds)
        assert classified.regime == RegimeType.SPIKE_UP

        mem = RegimeMemory()
        mem._states["urgency"] = RegimeState(
            signal_name="urgency",
            current_regime=RegimeType.SPIKE_UP,
            duration=3,
        )

        rf = RegimeFilter(confirm_threshold=1)
        raw_regimes = {"urgency": classified.regime}
        fs = rf.filter(raw_regimes)

        regime = fs.get_filtered_regime("urgency")
        duration = mem.get_duration("urgency")

        wr = compute_regime_factor("urgency", regime, duration)
        assert wr.factor == _SPIKE_FACTOR_UP

    def test_adaptive_threshold_to_weight(self):
        from umh.runtime.hysteresis_adaptive import compute_adaptive_threshold

        tr = compute_adaptive_threshold("urgency", 0.3, 0)
        assert tr.adaptive_threshold == 1

        wr = compute_regime_factor("urgency", RegimeType.SPIKE_UP, 0)
        assert wr.factor == _SPIKE_FACTOR_UP


# ── Section 21: Custom config edge cases ───────────────────────────


class TestCustomConfig:
    def test_zero_duration_rate(self):
        cfg = RegimeWeightConfig(trend_duration_rate=0.0)
        r = compute_regime_factor("s", RegimeType.TREND_UP, 100, cfg)
        assert r.factor == cfg.trend_base_up

    def test_zero_duration_cap(self):
        cfg = RegimeWeightConfig(trend_duration_cap=0.0)
        r = compute_regime_factor("s", RegimeType.TREND_UP, 100, cfg)
        assert r.factor == cfg.trend_base_up

    def test_narrow_bounds(self):
        cfg = RegimeWeightConfig(min_factor=0.99, max_factor=1.01)
        for rt in RegimeType:
            r = compute_regime_factor("s", rt, 10, cfg)
            assert 0.99 <= r.factor <= 1.01

    def test_wide_bounds(self):
        cfg = RegimeWeightConfig(min_factor=0.5, max_factor=2.0)
        r = compute_regime_factor("s", RegimeType.SPIKE_UP, 0, cfg)
        assert r.factor == _SPIKE_FACTOR_UP

    def test_equal_bounds(self):
        cfg = RegimeWeightConfig(min_factor=1.0, max_factor=1.0)
        for rt in RegimeType:
            r = compute_regime_factor("s", rt, 5, cfg)
            assert r.factor == 1.0

    def test_stable_factor_custom(self):
        cfg = RegimeWeightConfig(stable_factor=0.98)
        r = compute_regime_factor("s", RegimeType.STABLE, 0, cfg)
        assert r.factor == 0.98

    def test_none_config_uses_default(self):
        r = compute_regime_factor("s", RegimeType.STABLE, 0, None)
        assert r.factor == 1.0


# ── Section 22: Exact numerical verification ───────────────────────


class TestExactNumerical:
    def test_trend_up_duration_0_exact(self):
        r = compute_regime_factor("s", RegimeType.TREND_UP, 0)
        assert r.factor == 1.05

    def test_trend_up_duration_1_exact(self):
        r = compute_regime_factor("s", RegimeType.TREND_UP, 1)
        assert r.factor == pytest.approx(1.055)

    def test_trend_up_duration_2_exact(self):
        r = compute_regime_factor("s", RegimeType.TREND_UP, 2)
        assert r.factor == pytest.approx(1.06)

    def test_trend_up_duration_10_exact(self):
        r = compute_regime_factor("s", RegimeType.TREND_UP, 10)
        assert r.factor == pytest.approx(1.10)

    def test_trend_down_duration_0_exact(self):
        r = compute_regime_factor("s", RegimeType.TREND_DOWN, 0)
        assert r.factor == 0.95

    def test_trend_down_duration_1_exact(self):
        r = compute_regime_factor("s", RegimeType.TREND_DOWN, 1)
        assert r.factor == pytest.approx(0.945)

    def test_trend_down_duration_2_exact(self):
        r = compute_regime_factor("s", RegimeType.TREND_DOWN, 2)
        assert r.factor == pytest.approx(0.94)

    def test_trend_down_duration_10_exact(self):
        r = compute_regime_factor("s", RegimeType.TREND_DOWN, 10)
        assert r.factor == pytest.approx(0.90)

    def test_spike_up_exact(self):
        r = compute_regime_factor("s", RegimeType.SPIKE_UP, 0)
        assert r.factor == 1.10

    def test_spike_down_exact(self):
        r = compute_regime_factor("s", RegimeType.SPIKE_DOWN, 0)
        assert r.factor == 0.90

    def test_stable_exact(self):
        r = compute_regime_factor("s", RegimeType.STABLE, 0)
        assert r.factor == 1.0

    def test_trend_up_at_cap_exact(self):
        r = compute_regime_factor("s", RegimeType.TREND_UP, 10)
        assert r.factor == pytest.approx(1.10)

    def test_trend_down_at_cap_exact(self):
        r = compute_regime_factor("s", RegimeType.TREND_DOWN, 10)
        assert r.factor == pytest.approx(0.90)

    def test_trend_up_past_cap_same_as_cap(self):
        r10 = compute_regime_factor("s", RegimeType.TREND_UP, 10)
        r100 = compute_regime_factor("s", RegimeType.TREND_UP, 100)
        assert r10.factor == r100.factor


# ── Section 23: All regime types covered ───────────────────────────


class TestAllRegimesCovered:
    def test_every_regime_produces_result(self):
        for rt in RegimeType:
            r = compute_regime_factor("s", rt, 0)
            assert isinstance(r, RegimeWeightResult)

    def test_every_regime_has_reason(self):
        for rt in RegimeType:
            r = compute_regime_factor("s", rt, 0)
            assert len(r.reason) > 0

    def test_every_regime_factor_is_float(self):
        for rt in RegimeType:
            r = compute_regime_factor("s", rt, 0)
            assert isinstance(r.factor, float)

    def test_all_regime_sweep_bounded(self):
        for rt in RegimeType:
            for d in range(100):
                r = compute_regime_factor("s", rt, d)
                assert 0.85 <= r.factor <= 1.15


# ── Section 24: Raw factor vs clamped factor ───────────────────────


class TestRawVsClamped:
    def test_default_config_no_clamping_needed(self):
        for rt in RegimeType:
            r = compute_regime_factor("s", rt, 0)
            assert r.raw_factor == r.factor

    def test_trend_at_cap_no_clamping(self):
        r = compute_regime_factor("s", RegimeType.TREND_UP, 10)
        assert r.raw_factor == r.factor

    def test_extreme_config_shows_clamping(self):
        cfg = RegimeWeightConfig(spike_factor_up=2.0, max_factor=1.15)
        r = compute_regime_factor("s", RegimeType.SPIKE_UP, 0, cfg)
        assert r.raw_factor == 2.0
        assert r.factor == 1.15
        assert r.raw_factor != r.factor

    def test_raw_factor_preserved_in_dict(self):
        cfg = RegimeWeightConfig(spike_factor_up=2.0, max_factor=1.15)
        r = compute_regime_factor("s", RegimeType.SPIKE_UP, 0, cfg)
        d = r.to_dict()
        assert d["raw_factor"] == 2.0
        assert d["factor"] == 1.15
