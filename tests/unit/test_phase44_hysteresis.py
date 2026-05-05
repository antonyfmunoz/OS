"""Phase 44 — Regime Hysteresis + Confirmation Layer v1 tests.

Covers: FilterState, FilterResult, FilterSnapshot, filter_regime,
RegimeFilter lifecycle, noise resistance, confirmation gating,
pipeline integration, hard invariants 156-160, edge cases,
serialization, dependency boundary, exports/compilation,
Phase 43 regression.

Target: 140-180 tests.
"""

from __future__ import annotations

import ast
import sys

import pytest

sys.path.insert(0, "/opt/OS")

from umh.runtime.regime import (
    RegimeType,
    classify_all_regimes,
)
from umh.runtime.regime_memory import (
    RegimeMemory,
)
from umh.runtime.regime_filter import (
    FilterResult,
    FilterSnapshot,
    FilterState,
    RegimeFilter,
    _DEFAULT_CONFIRM_THRESHOLD,
    _SIGNAL_NAMES,
    filter_regime,
)


# ── helpers ─────────────────────────────────────────────────────────

RT = RegimeType


def _filter_sequence(
    filt: RegimeFilter,
    signal: str,
    regimes: list[RegimeType],
) -> list[FilterResult]:
    """Feed a sequence of raw regimes through the filter, return results."""
    results = []
    for rt in regimes:
        snap = filt.filter({signal: rt})
        results.append(snap.get(signal))
    return results


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 1: FilterState creation and defaults
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFilterStateCreation:
    def test_default_values(self):
        s = FilterState(signal_name="urgency")
        assert s.signal_name == "urgency"
        assert s.confirmed_regime is RT.STABLE
        assert s.pending_regime is None
        assert s.pending_duration == 0

    def test_custom_values(self):
        s = FilterState(
            signal_name="risk",
            confirmed_regime=RT.SPIKE_UP,
            pending_regime=RT.TREND_DOWN,
            pending_duration=2,
        )
        assert s.confirmed_regime is RT.SPIKE_UP
        assert s.pending_regime is RT.TREND_DOWN
        assert s.pending_duration == 2

    def test_mutable(self):
        s = FilterState(signal_name="urgency")
        s.confirmed_regime = RT.SPIKE_UP
        s.pending_regime = RT.TREND_DOWN
        s.pending_duration = 5
        assert s.confirmed_regime is RT.SPIKE_UP
        assert s.pending_regime is RT.TREND_DOWN
        assert s.pending_duration == 5

    def test_to_dict(self):
        s = FilterState(signal_name="urgency")
        d = s.to_dict()
        assert d["signal_name"] == "urgency"
        assert d["confirmed_regime"] == "stable"
        assert d["pending_regime"] is None
        assert d["pending_duration"] == 0

    def test_to_dict_with_pending(self):
        s = FilterState(
            signal_name="risk",
            confirmed_regime=RT.STABLE,
            pending_regime=RT.SPIKE_UP,
            pending_duration=2,
        )
        d = s.to_dict()
        assert d["pending_regime"] == "spike_up"
        assert d["pending_duration"] == 2

    def test_to_dict_all_regime_types(self):
        for rt in RT:
            s = FilterState(signal_name="test", confirmed_regime=rt)
            d = s.to_dict()
            assert d["confirmed_regime"] == rt.value


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 2: FilterResult frozen record
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFilterResult:
    def test_creation(self):
        r = FilterResult(
            signal_name="urgency",
            raw_regime=RT.SPIKE_UP,
            filtered_regime=RT.STABLE,
            was_confirmed=False,
            pending_regime=RT.SPIKE_UP,
            pending_duration=1,
        )
        assert r.signal_name == "urgency"
        assert r.raw_regime is RT.SPIKE_UP
        assert r.filtered_regime is RT.STABLE
        assert r.was_confirmed is False

    def test_frozen(self):
        r = FilterResult("urgency", RT.SPIKE_UP, RT.STABLE, False, RT.SPIKE_UP, 1)
        with pytest.raises(AttributeError):
            r.filtered_regime = RT.SPIKE_UP

    def test_was_suppressed_true(self):
        r = FilterResult("urgency", RT.SPIKE_UP, RT.STABLE, False, RT.SPIKE_UP, 1)
        assert r.was_suppressed is True

    def test_was_suppressed_false(self):
        r = FilterResult("urgency", RT.STABLE, RT.STABLE, False, None, 0)
        assert r.was_suppressed is False

    def test_confirmed_not_suppressed(self):
        r = FilterResult("urgency", RT.SPIKE_UP, RT.SPIKE_UP, True, None, 0)
        assert r.was_confirmed is True
        assert r.was_suppressed is False

    def test_to_dict(self):
        r = FilterResult("urgency", RT.SPIKE_UP, RT.STABLE, False, RT.SPIKE_UP, 2)
        d = r.to_dict()
        assert d["signal_name"] == "urgency"
        assert d["raw_regime"] == "spike_up"
        assert d["filtered_regime"] == "stable"
        assert d["was_confirmed"] is False
        assert d["was_suppressed"] is True
        assert d["pending_regime"] == "spike_up"
        assert d["pending_duration"] == 2

    def test_to_dict_no_pending(self):
        r = FilterResult("urgency", RT.STABLE, RT.STABLE, False, None, 0)
        d = r.to_dict()
        assert d["pending_regime"] is None
        assert d["pending_duration"] == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 3: FilterSnapshot
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFilterSnapshot:
    def test_creation(self):
        r = FilterResult("urgency", RT.STABLE, RT.STABLE, False, None, 0)
        snap = FilterSnapshot(results={"urgency": r}, tick=1)
        assert snap.tick == 1
        assert len(snap.results) == 1

    def test_frozen(self):
        snap = FilterSnapshot(results={}, tick=0)
        with pytest.raises(AttributeError):
            snap.tick = 5

    def test_get(self):
        r = FilterResult("urgency", RT.STABLE, RT.STABLE, False, None, 0)
        snap = FilterSnapshot(results={"urgency": r}, tick=1)
        assert snap.get("urgency") is r
        assert snap.get("missing") is None

    def test_get_filtered_regime(self):
        r = FilterResult("urgency", RT.SPIKE_UP, RT.STABLE, False, RT.SPIKE_UP, 1)
        snap = FilterSnapshot(results={"urgency": r}, tick=1)
        assert snap.get_filtered_regime("urgency") is RT.STABLE

    def test_get_filtered_regime_missing(self):
        snap = FilterSnapshot(results={}, tick=0)
        assert snap.get_filtered_regime("missing") is RT.STABLE

    def test_any_confirmed_true(self):
        r = FilterResult("urgency", RT.SPIKE_UP, RT.SPIKE_UP, True, None, 0)
        snap = FilterSnapshot(results={"urgency": r}, tick=1)
        assert snap.any_confirmed() is True

    def test_any_confirmed_false(self):
        r = FilterResult("urgency", RT.STABLE, RT.STABLE, False, None, 0)
        snap = FilterSnapshot(results={"urgency": r}, tick=1)
        assert snap.any_confirmed() is False

    def test_any_suppressed_true(self):
        r = FilterResult("urgency", RT.SPIKE_UP, RT.STABLE, False, RT.SPIKE_UP, 1)
        snap = FilterSnapshot(results={"urgency": r}, tick=1)
        assert snap.any_suppressed() is True

    def test_any_suppressed_false(self):
        r = FilterResult("urgency", RT.STABLE, RT.STABLE, False, None, 0)
        snap = FilterSnapshot(results={"urgency": r}, tick=1)
        assert snap.any_suppressed() is False

    def test_all_stable_true(self):
        r1 = FilterResult("a", RT.STABLE, RT.STABLE, False, None, 0)
        r2 = FilterResult("b", RT.STABLE, RT.STABLE, False, None, 0)
        snap = FilterSnapshot(results={"a": r1, "b": r2}, tick=1)
        assert snap.all_stable() is True

    def test_all_stable_false(self):
        r1 = FilterResult("a", RT.STABLE, RT.STABLE, False, None, 0)
        r2 = FilterResult("b", RT.SPIKE_UP, RT.SPIKE_UP, True, None, 0)
        snap = FilterSnapshot(results={"a": r1, "b": r2}, tick=1)
        assert snap.all_stable() is False

    def test_all_stable_empty(self):
        snap = FilterSnapshot(results={}, tick=0)
        assert snap.all_stable() is True

    def test_confirmed_signals(self):
        r1 = FilterResult("a", RT.SPIKE_UP, RT.SPIKE_UP, True, None, 0)
        r2 = FilterResult("b", RT.STABLE, RT.STABLE, False, None, 0)
        snap = FilterSnapshot(results={"a": r1, "b": r2}, tick=1)
        assert snap.confirmed_signals() == ["a"]

    def test_suppressed_signals(self):
        r1 = FilterResult("a", RT.SPIKE_UP, RT.STABLE, False, RT.SPIKE_UP, 1)
        r2 = FilterResult("b", RT.STABLE, RT.STABLE, False, None, 0)
        snap = FilterSnapshot(results={"a": r1, "b": r2}, tick=1)
        assert snap.suppressed_signals() == ["a"]

    def test_to_dict(self):
        r = FilterResult("urgency", RT.STABLE, RT.STABLE, False, None, 0)
        snap = FilterSnapshot(results={"urgency": r}, tick=1)
        d = snap.to_dict()
        assert d["tick"] == 1
        assert "urgency" in d["results"]
        assert d["any_confirmed"] is False
        assert d["any_suppressed"] is False
        assert d["all_stable"] is True

    def test_to_dict_sorted_keys(self):
        r1 = FilterResult("z", RT.STABLE, RT.STABLE, False, None, 0)
        r2 = FilterResult("a", RT.STABLE, RT.STABLE, False, None, 0)
        snap = FilterSnapshot(results={"z": r1, "a": r2}, tick=1)
        d = snap.to_dict()
        keys = list(d["results"].keys())
        assert keys == sorted(keys)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 4: filter_regime function — same regime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFilterRegimeSame:
    def test_same_regime_returns_confirmed(self):
        s = FilterState(signal_name="urgency")
        r = filter_regime(s, RT.STABLE, confirm_threshold=3)
        assert r.filtered_regime is RT.STABLE
        assert r.was_confirmed is False
        assert r.was_suppressed is False

    def test_same_regime_clears_pending(self):
        s = FilterState(signal_name="urgency", pending_regime=RT.SPIKE_UP, pending_duration=2)
        filter_regime(s, RT.STABLE, confirm_threshold=3)
        assert s.pending_regime is None
        assert s.pending_duration == 0

    def test_repeated_same_regime(self):
        s = FilterState(signal_name="urgency")
        for _ in range(10):
            r = filter_regime(s, RT.STABLE, confirm_threshold=3)
        assert r.filtered_regime is RT.STABLE
        assert s.pending_regime is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 5: filter_regime function — new pending
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFilterRegimeNewPending:
    def test_new_regime_starts_pending(self):
        s = FilterState(signal_name="urgency")
        r = filter_regime(s, RT.SPIKE_UP, confirm_threshold=3)
        assert r.filtered_regime is RT.STABLE
        assert r.was_suppressed is True
        assert s.pending_regime is RT.SPIKE_UP
        assert s.pending_duration == 1

    def test_different_pending_resets(self):
        s = FilterState(
            signal_name="urgency",
            pending_regime=RT.SPIKE_UP,
            pending_duration=2,
        )
        r = filter_regime(s, RT.TREND_DOWN, confirm_threshold=3)
        assert s.pending_regime is RT.TREND_DOWN
        assert s.pending_duration == 1
        assert r.filtered_regime is RT.STABLE

    def test_pending_result_carries_info(self):
        s = FilterState(signal_name="urgency")
        r = filter_regime(s, RT.SPIKE_UP, confirm_threshold=3)
        assert r.pending_regime is RT.SPIKE_UP
        assert r.pending_duration == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 6: filter_regime function — confirmation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFilterRegimeConfirmation:
    def test_confirmed_after_threshold(self):
        s = FilterState(signal_name="urgency")
        for _ in range(2):
            r = filter_regime(s, RT.SPIKE_UP, confirm_threshold=3)
            assert r.filtered_regime is RT.STABLE
        r = filter_regime(s, RT.SPIKE_UP, confirm_threshold=3)
        assert r.filtered_regime is RT.SPIKE_UP
        assert r.was_confirmed is True

    def test_confirmed_clears_pending(self):
        s = FilterState(signal_name="urgency")
        for _ in range(3):
            filter_regime(s, RT.SPIKE_UP, confirm_threshold=3)
        assert s.pending_regime is None
        assert s.pending_duration == 0

    def test_confirmed_updates_state(self):
        s = FilterState(signal_name="urgency")
        for _ in range(3):
            filter_regime(s, RT.SPIKE_UP, confirm_threshold=3)
        assert s.confirmed_regime is RT.SPIKE_UP

    def test_threshold_1_confirms_immediately(self):
        s = FilterState(signal_name="urgency")
        r = filter_regime(s, RT.SPIKE_UP, confirm_threshold=1)
        assert r.filtered_regime is RT.SPIKE_UP
        assert r.was_confirmed is True

    def test_threshold_boundary_not_confirmed(self):
        s = FilterState(signal_name="urgency")
        filter_regime(s, RT.SPIKE_UP, confirm_threshold=3)
        r = filter_regime(s, RT.SPIKE_UP, confirm_threshold=3)
        assert r.filtered_regime is RT.STABLE
        assert r.was_confirmed is False
        assert s.pending_duration == 2

    def test_threshold_boundary_confirmed(self):
        s = FilterState(signal_name="urgency")
        filter_regime(s, RT.SPIKE_UP, confirm_threshold=3)
        filter_regime(s, RT.SPIKE_UP, confirm_threshold=3)
        r = filter_regime(s, RT.SPIKE_UP, confirm_threshold=3)
        assert r.filtered_regime is RT.SPIKE_UP
        assert r.was_confirmed is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 7: RegimeFilter construction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRegimeFilterConstruction:
    def test_default_signals(self):
        filt = RegimeFilter()
        assert set(filt.states.keys()) == set(_SIGNAL_NAMES)

    def test_custom_signals(self):
        filt = RegimeFilter(signals=("alpha", "beta"))
        assert set(filt.states.keys()) == {"alpha", "beta"}

    def test_default_threshold(self):
        filt = RegimeFilter()
        assert filt.confirm_threshold == _DEFAULT_CONFIRM_THRESHOLD

    def test_custom_threshold(self):
        filt = RegimeFilter(confirm_threshold=5)
        assert filt.confirm_threshold == 5

    def test_threshold_minimum_one(self):
        filt = RegimeFilter(confirm_threshold=0)
        assert filt.confirm_threshold == 1
        filt2 = RegimeFilter(confirm_threshold=-5)
        assert filt2.confirm_threshold == 1

    def test_initial_tick_zero(self):
        filt = RegimeFilter()
        assert filt.tick == 0

    def test_states_returns_copy(self):
        filt = RegimeFilter()
        s1 = filt.states
        s2 = filt.states
        assert s1 is not s2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 8: RegimeFilter.filter() — single spike suppression
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSingleSpikeSuppression:
    def test_single_spike_suppressed(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        snap = filt.filter({"urgency": RT.SPIKE_UP})
        assert snap.get_filtered_regime("urgency") is RT.STABLE
        assert snap.any_suppressed() is True

    def test_single_spike_then_return_stable(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        filt.filter({"urgency": RT.SPIKE_UP})
        snap = filt.filter({"urgency": RT.STABLE})
        assert snap.get_filtered_regime("urgency") is RT.STABLE
        assert snap.any_suppressed() is False

    def test_two_spikes_not_enough(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        filt.filter({"urgency": RT.SPIKE_UP})
        snap = filt.filter({"urgency": RT.SPIKE_UP})
        assert snap.get_filtered_regime("urgency") is RT.STABLE


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 9: RegimeFilter.filter() — sustained signal confirmation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSustainedSignalConfirmation:
    def test_three_ticks_confirms(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for _ in range(2):
            filt.filter({"urgency": RT.SPIKE_UP})
        snap = filt.filter({"urgency": RT.SPIKE_UP})
        assert snap.get_filtered_regime("urgency") is RT.SPIKE_UP
        assert snap.any_confirmed() is True

    def test_confirmed_then_persists(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for _ in range(3):
            filt.filter({"urgency": RT.SPIKE_UP})
        snap = filt.filter({"urgency": RT.SPIKE_UP})
        assert snap.get_filtered_regime("urgency") is RT.SPIKE_UP
        assert snap.any_confirmed() is False

    def test_confirmed_regime_accessible(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for _ in range(3):
            filt.filter({"urgency": RT.SPIKE_UP})
        assert filt.get_confirmed_regime("urgency") is RT.SPIKE_UP

    def test_tick_increments_on_filter(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for i in range(5):
            filt.filter({"urgency": RT.STABLE})
        assert filt.tick == 5


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 10: Noise resistance — flip-flop patterns
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestNoiseResistance:
    def test_alternating_spikes_never_confirm(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for i in range(20):
            rt = RT.SPIKE_UP if i % 2 == 0 else RT.STABLE
            snap = filt.filter({"urgency": rt})
        assert filt.get_confirmed_regime("urgency") is RT.STABLE

    def test_alternating_different_regimes_never_confirm(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        regimes = [RT.SPIKE_UP, RT.TREND_DOWN, RT.SPIKE_DOWN, RT.TREND_UP]
        for i in range(20):
            snap = filt.filter({"urgency": regimes[i % len(regimes)]})
        assert filt.get_confirmed_regime("urgency") is RT.STABLE

    def test_noise_then_sustained_confirms(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        filt.filter({"urgency": RT.SPIKE_UP})
        filt.filter({"urgency": RT.STABLE})
        filt.filter({"urgency": RT.SPIKE_UP})
        filt.filter({"urgency": RT.STABLE})
        for _ in range(3):
            filt.filter({"urgency": RT.SPIKE_UP})
        assert filt.get_confirmed_regime("urgency") is RT.SPIKE_UP

    def test_interrupted_pending_resets(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        filt.filter({"urgency": RT.SPIKE_UP})
        filt.filter({"urgency": RT.SPIKE_UP})
        filt.filter({"urgency": RT.STABLE})
        pending, dur = filt.get_pending("urgency")
        assert pending is None
        assert dur == 0

    def test_pending_switch_resets_count(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        filt.filter({"urgency": RT.SPIKE_UP})
        filt.filter({"urgency": RT.SPIKE_UP})
        filt.filter({"urgency": RT.TREND_DOWN})
        pending, dur = filt.get_pending("urgency")
        assert pending is RT.TREND_DOWN
        assert dur == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 11: Threshold boundary behavior
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestThresholdBoundary:
    def test_one_below_threshold_not_confirmed(self):
        for threshold in [2, 3, 5, 10]:
            filt = RegimeFilter(signals=("urgency",), confirm_threshold=threshold)
            for _ in range(threshold - 1):
                filt.filter({"urgency": RT.SPIKE_UP})
            assert filt.get_confirmed_regime("urgency") is RT.STABLE

    def test_exactly_at_threshold_confirmed(self):
        for threshold in [1, 2, 3, 5, 10]:
            filt = RegimeFilter(signals=("urgency",), confirm_threshold=threshold)
            for _ in range(threshold):
                filt.filter({"urgency": RT.SPIKE_UP})
            assert filt.get_confirmed_regime("urgency") is RT.SPIKE_UP

    def test_above_threshold_stays_confirmed(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for _ in range(10):
            filt.filter({"urgency": RT.SPIKE_UP})
        assert filt.get_confirmed_regime("urgency") is RT.SPIKE_UP


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 12: Cross-signal independence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCrossSignalIndependence:
    def test_signals_filtered_independently(self):
        filt = RegimeFilter(signals=("a", "b"), confirm_threshold=3)
        for _ in range(3):
            filt.filter({"a": RT.SPIKE_UP, "b": RT.STABLE})
        assert filt.get_confirmed_regime("a") is RT.SPIKE_UP
        assert filt.get_confirmed_regime("b") is RT.STABLE

    def test_one_signal_pending_other_not(self):
        filt = RegimeFilter(signals=("a", "b"), confirm_threshold=3)
        filt.filter({"a": RT.SPIKE_UP, "b": RT.STABLE})
        pa, da = filt.get_pending("a")
        pb, db = filt.get_pending("b")
        assert pa is RT.SPIKE_UP
        assert da == 1
        assert pb is None
        assert db == 0

    def test_different_confirmation_timing(self):
        filt = RegimeFilter(signals=("a", "b"), confirm_threshold=3)
        filt.filter({"a": RT.SPIKE_UP, "b": RT.STABLE})
        filt.filter({"a": RT.SPIKE_UP, "b": RT.TREND_DOWN})
        snap = filt.filter({"a": RT.SPIKE_UP, "b": RT.TREND_DOWN})
        assert snap.get("a").was_confirmed is True
        assert snap.get("b").was_confirmed is False

    def test_many_signals_independent(self):
        signals = tuple(f"sig_{i}" for i in range(10))
        filt = RegimeFilter(signals=signals, confirm_threshold=3)
        for _ in range(3):
            regimes = {s: RT.SPIKE_UP if i % 2 == 0 else RT.STABLE for i, s in enumerate(signals)}
            filt.filter(regimes)
        for i, s in enumerate(signals):
            if i % 2 == 0:
                assert filt.get_confirmed_regime(s) is RT.SPIKE_UP
            else:
                assert filt.get_confirmed_regime(s) is RT.STABLE


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 13: Dynamic signal registration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDynamicSignalRegistration:
    def test_new_signal_auto_registered(self):
        filt = RegimeFilter(signals=("a",))
        snap = filt.filter({"a": RT.STABLE, "new_signal": RT.SPIKE_UP})
        assert "new_signal" in snap.results

    def test_new_signal_starts_stable(self):
        filt = RegimeFilter(signals=("a",), confirm_threshold=3)
        snap = filt.filter({"new_signal": RT.SPIKE_UP})
        assert snap.get_filtered_regime("new_signal") is RT.STABLE

    def test_filter_single_auto_registers(self):
        filt = RegimeFilter(signals=("a",))
        r = filt.filter_single("new_signal", RT.STABLE)
        assert r.filtered_regime is RT.STABLE
        assert "new_signal" in filt.states


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 14: filter_single
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFilterSingle:
    def test_filter_single_same_regime(self):
        filt = RegimeFilter(signals=("urgency",))
        r = filt.filter_single("urgency", RT.STABLE)
        assert r.filtered_regime is RT.STABLE
        assert r.was_suppressed is False

    def test_filter_single_suppressed(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        r = filt.filter_single("urgency", RT.SPIKE_UP)
        assert r.filtered_regime is RT.STABLE
        assert r.was_suppressed is True

    def test_filter_single_does_not_increment_tick(self):
        filt = RegimeFilter(signals=("urgency",))
        filt.filter_single("urgency", RT.STABLE)
        assert filt.tick == 0

    def test_filter_single_confirmed_after_threshold(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for _ in range(2):
            filt.filter_single("urgency", RT.SPIKE_UP)
        r = filt.filter_single("urgency", RT.SPIKE_UP)
        assert r.was_confirmed is True
        assert r.filtered_regime is RT.SPIKE_UP


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 15: Reset
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestReset:
    def test_reset_clears_confirmed(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for _ in range(3):
            filt.filter({"urgency": RT.SPIKE_UP})
        filt.reset()
        assert filt.get_confirmed_regime("urgency") is RT.STABLE

    def test_reset_clears_pending(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        filt.filter({"urgency": RT.SPIKE_UP})
        filt.reset()
        pending, dur = filt.get_pending("urgency")
        assert pending is None
        assert dur == 0

    def test_reset_clears_tick(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for _ in range(5):
            filt.filter({"urgency": RT.STABLE})
        filt.reset()
        assert filt.tick == 0

    def test_reset_preserves_signal_set(self):
        filt = RegimeFilter(signals=("a", "b", "c"))
        filt.reset()
        assert set(filt.states.keys()) == {"a", "b", "c"}

    def test_usable_after_reset(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for _ in range(3):
            filt.filter({"urgency": RT.SPIKE_UP})
        filt.reset()
        for _ in range(3):
            filt.filter({"urgency": RT.TREND_DOWN})
        assert filt.get_confirmed_regime("urgency") is RT.TREND_DOWN


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 16: get_pending
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestGetPending:
    def test_no_pending(self):
        filt = RegimeFilter(signals=("urgency",))
        pending, dur = filt.get_pending("urgency")
        assert pending is None
        assert dur == 0

    def test_with_pending(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        filt.filter({"urgency": RT.SPIKE_UP})
        pending, dur = filt.get_pending("urgency")
        assert pending is RT.SPIKE_UP
        assert dur == 1

    def test_missing_signal(self):
        filt = RegimeFilter(signals=("a",))
        pending, dur = filt.get_pending("missing")
        assert pending is None
        assert dur == 0

    def test_get_confirmed_missing(self):
        filt = RegimeFilter(signals=("a",))
        assert filt.get_confirmed_regime("missing") is RT.STABLE


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 17: Serialization (to_dict)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSerialization:
    def test_regime_filter_to_dict(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        filt.filter({"urgency": RT.STABLE})
        d = filt.to_dict()
        assert d["tick"] == 1
        assert d["confirm_threshold"] == 3
        assert "urgency" in d["states"]

    def test_to_dict_sorted_states(self):
        filt = RegimeFilter(signals=("z_signal", "a_signal"))
        d = filt.to_dict()
        keys = list(d["states"].keys())
        assert keys == sorted(keys)

    def test_all_dicts_are_json_serializable(self):
        import json

        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        filt.filter({"urgency": RT.SPIKE_UP})
        filt.filter({"urgency": RT.SPIKE_UP})
        snap = filt.filter({"urgency": RT.SPIKE_UP})
        json.dumps(filt.to_dict())
        json.dumps(snap.to_dict())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 18: Pipeline integration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPipelineIntegration:
    def test_classify_to_memory_to_filter(self):
        deltas = {"urgency": 0.3, "risk_level": 0.0}
        regime_snap = classify_all_regimes(deltas, tick=1)

        mem = RegimeMemory(signals=("urgency", "risk_level"))
        mem_snap = mem.update(regime_snap)

        raw_regimes = {name: state.current_regime for name, state in mem_snap.states.items()}
        filt = RegimeFilter(signals=("urgency", "risk_level"), confirm_threshold=3)
        fsnap = filt.filter(raw_regimes)

        assert fsnap.get_filtered_regime("urgency") is RT.STABLE
        assert fsnap.get_filtered_regime("risk_level") is RT.STABLE

    def test_sustained_pipeline_confirms(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        mem = RegimeMemory(signals=("urgency",))

        for _ in range(3):
            regime_snap = classify_all_regimes({"urgency": 0.3}, tick=0)
            mem_snap = mem.update(regime_snap)
            raw = {n: s.current_regime for n, s in mem_snap.states.items()}
            fsnap = filt.filter(raw)

        assert fsnap.get_filtered_regime("urgency") is RT.SPIKE_UP

    def test_transient_spike_filtered_in_pipeline(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        mem = RegimeMemory(signals=("urgency",))

        regime_snap = classify_all_regimes({"urgency": 0.3}, tick=0)
        mem_snap = mem.update(regime_snap)
        raw = {n: s.current_regime for n, s in mem_snap.states.items()}
        filt.filter(raw)

        regime_snap = classify_all_regimes({"urgency": 0.0}, tick=0)
        mem_snap = mem.update(regime_snap)
        raw = {n: s.current_regime for n, s in mem_snap.states.items()}
        fsnap = filt.filter(raw)

        assert fsnap.get_filtered_regime("urgency") is RT.STABLE

    def test_four_signal_pipeline(self):
        filt = RegimeFilter(confirm_threshold=3)
        mem = RegimeMemory()

        deltas = {
            "urgency": 0.0,
            "risk_level": 0.1,
            "resource_pressure": 0.3,
            "stability_mode": -0.15,
        }
        for _ in range(3):
            regime_snap = classify_all_regimes(deltas, tick=0)
            mem_snap = mem.update(regime_snap)
            raw = {n: s.current_regime for n, s in mem_snap.states.items()}
            fsnap = filt.filter(raw)

        assert fsnap.get_filtered_regime("urgency") is RT.STABLE
        assert fsnap.get_filtered_regime("risk_level") is RT.TREND_UP
        assert fsnap.get_filtered_regime("resource_pressure") is RT.SPIKE_UP
        assert fsnap.get_filtered_regime("stability_mode") is RT.TREND_DOWN


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 19: Determinism
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDeterminism:
    def test_same_sequence_same_result(self):
        def run_sequence():
            filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
            regimes = [RT.STABLE, RT.SPIKE_UP, RT.SPIKE_UP, RT.SPIKE_UP, RT.STABLE, RT.STABLE]
            results = []
            for rt in regimes:
                snap = filt.filter({"urgency": rt})
                results.append(snap.get_filtered_regime("urgency"))
            return results

        r1 = run_sequence()
        r2 = run_sequence()
        assert r1 == r2

    def test_independent_instances(self):
        filt1 = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        filt2 = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for _ in range(3):
            filt1.filter({"urgency": RT.SPIKE_UP})
        assert filt1.get_confirmed_regime("urgency") is RT.SPIKE_UP
        assert filt2.get_confirmed_regime("urgency") is RT.STABLE

    def test_deterministic_across_all_regime_types(self):
        for rt in RT:
            filt = RegimeFilter(signals=("sig",), confirm_threshold=3)
            for _ in range(3):
                filt.filter({"sig": rt})
            if rt is RT.STABLE:
                assert filt.get_confirmed_regime("sig") is RT.STABLE
            else:
                assert filt.get_confirmed_regime("sig") is rt


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 20: Hard invariants 156-160
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestHardInvariants:
    def test_inv156_no_instant_regime_switching(self):
        """Invariant 156: A single tick of a new regime does not change confirmed."""
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        snap = filt.filter({"urgency": RT.SPIKE_UP})
        assert snap.get_filtered_regime("urgency") is RT.STABLE

    def test_inv156_for_all_regime_types(self):
        for rt in RT:
            if rt is RT.STABLE:
                continue
            filt = RegimeFilter(signals=("sig",), confirm_threshold=3)
            snap = filt.filter({"sig": rt})
            assert snap.get_filtered_regime("sig") is RT.STABLE

    def test_inv157_confirmed_transitions_only(self):
        """Invariant 157: Only confirmed (threshold-met) transitions change output."""
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=5)
        for i in range(4):
            snap = filt.filter({"urgency": RT.SPIKE_UP})
            assert snap.get_filtered_regime("urgency") is RT.STABLE
        snap = filt.filter({"urgency": RT.SPIKE_UP})
        assert snap.get_filtered_regime("urgency") is RT.SPIKE_UP

    def test_inv158_noise_does_not_trigger_flips(self):
        """Invariant 158: Alternating noise never produces a transition."""
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for i in range(100):
            rt = RT.SPIKE_UP if i % 2 == 0 else RT.STABLE
            snap = filt.filter({"urgency": rt})
            assert snap.get_filtered_regime("urgency") is RT.STABLE

    def test_inv159_deterministic_filtering(self):
        """Invariant 159: Same input sequence always produces same output."""

        def run():
            filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
            seq = [
                RT.STABLE,
                RT.SPIKE_UP,
                RT.STABLE,
                RT.SPIKE_UP,
                RT.SPIKE_UP,
                RT.SPIKE_UP,
                RT.STABLE,
            ]
            return [filt.filter({"urgency": r}).get_filtered_regime("urgency") for r in seq]

        assert run() == run()

    def test_inv160_no_cross_signal_contamination(self):
        """Invariant 160: Changes to one signal never affect another."""
        filt = RegimeFilter(signals=("a", "b"), confirm_threshold=3)
        for _ in range(3):
            filt.filter({"a": RT.SPIKE_UP, "b": RT.STABLE})
        assert filt.get_confirmed_regime("a") is RT.SPIKE_UP
        assert filt.get_confirmed_regime("b") is RT.STABLE
        pending_b, dur_b = filt.get_pending("b")
        assert pending_b is None

    def test_inv156_with_threshold_2(self):
        filt = RegimeFilter(signals=("sig",), confirm_threshold=2)
        snap = filt.filter({"sig": RT.SPIKE_UP})
        assert snap.get_filtered_regime("sig") is RT.STABLE

    def test_inv158_rapid_three_regime_noise(self):
        filt = RegimeFilter(signals=("sig",), confirm_threshold=3)
        cycle = [RT.SPIKE_UP, RT.TREND_DOWN, RT.SPIKE_DOWN]
        for i in range(30):
            snap = filt.filter({"sig": cycle[i % 3]})
            assert snap.get_filtered_regime("sig") is RT.STABLE

    def test_inv160_five_signals_independent(self):
        signals = ("a", "b", "c", "d", "e")
        filt = RegimeFilter(signals=signals, confirm_threshold=3)
        for _ in range(3):
            filt.filter(
                {
                    "a": RT.SPIKE_UP,
                    "b": RT.STABLE,
                    "c": RT.TREND_DOWN,
                    "d": RT.STABLE,
                    "e": RT.SPIKE_DOWN,
                }
            )
        assert filt.get_confirmed_regime("a") is RT.SPIKE_UP
        assert filt.get_confirmed_regime("b") is RT.STABLE
        assert filt.get_confirmed_regime("c") is RT.TREND_DOWN
        assert filt.get_confirmed_regime("d") is RT.STABLE
        assert filt.get_confirmed_regime("e") is RT.SPIKE_DOWN


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 21: Edge cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEdgeCases:
    def test_single_signal_filter(self):
        filt = RegimeFilter(signals=("only",), confirm_threshold=3)
        snap = filt.filter({"only": RT.STABLE})
        assert snap.get_filtered_regime("only") is RT.STABLE

    def test_high_threshold(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=100)
        for _ in range(99):
            snap = filt.filter({"urgency": RT.SPIKE_UP})
            assert snap.get_filtered_regime("urgency") is RT.STABLE
        snap = filt.filter({"urgency": RT.SPIKE_UP})
        assert snap.get_filtered_regime("urgency") is RT.SPIKE_UP

    def test_double_transition(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for _ in range(3):
            filt.filter({"urgency": RT.SPIKE_UP})
        assert filt.get_confirmed_regime("urgency") is RT.SPIKE_UP
        for _ in range(3):
            filt.filter({"urgency": RT.STABLE})
        assert filt.get_confirmed_regime("urgency") is RT.STABLE

    def test_transition_to_all_regime_types(self):
        for target_rt in RT:
            if target_rt is RT.STABLE:
                continue
            filt = RegimeFilter(signals=("sig",), confirm_threshold=2)
            for _ in range(2):
                filt.filter({"sig": target_rt})
            assert filt.get_confirmed_regime("sig") is target_rt

    def test_back_to_stable_needs_confirmation_too(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for _ in range(3):
            filt.filter({"urgency": RT.SPIKE_UP})
        assert filt.get_confirmed_regime("urgency") is RT.SPIKE_UP
        filt.filter({"urgency": RT.STABLE})
        assert filt.get_confirmed_regime("urgency") is RT.SPIKE_UP
        filt.filter({"urgency": RT.STABLE})
        assert filt.get_confirmed_regime("urgency") is RT.SPIKE_UP
        filt.filter({"urgency": RT.STABLE})
        assert filt.get_confirmed_regime("urgency") is RT.STABLE

    def test_empty_filter_call(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        snap = filt.filter({})
        assert snap.tick == 1
        assert len(snap.results) == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 22: Dependency boundary
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDependencyBoundary:
    def test_no_io_imports(self):
        source = open("/opt/OS/umh/runtime/regime_filter.py").read()
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
        source = open("/opt/OS/umh/runtime/regime_filter.py").read()
        assert "umh.cells" not in source
        assert "umh.environments" not in source
        assert "umh.adapters" not in source

    def test_imports_only_regime(self):
        source = open("/opt/OS/umh/runtime/regime_filter.py").read()
        tree = ast.parse(source)
        umh_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("umh."):
                umh_imports.append(node.module)
        assert all(m == "umh.runtime.regime" for m in umh_imports)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 23: Exports and compilation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExportsAndCompilation:
    def test_regime_filter_compiles(self):
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/regime_filter.py", doraise=True)

    def test_init_compiles(self):
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/__init__.py", doraise=True)

    def test_exports_from_init(self):
        from umh.runtime import (
            FilterResult,
            FilterSnapshot,
            FilterState,
            RegimeFilter,
            filter_regime,
        )

        assert FilterResult is not None
        assert FilterSnapshot is not None
        assert FilterState is not None
        assert RegimeFilter is not None
        assert filter_regime is not None

    def test_in_all_list(self):
        from umh.runtime import __all__

        expected = [
            "FilterResult",
            "FilterSnapshot",
            "FilterState",
            "RegimeFilter",
            "filter_regime",
        ]
        for name in expected:
            assert name in __all__, f"{name} missing from __all__"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 24: Phase 43 regression
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPhase43Regression:
    def test_regime_type_enum(self):
        assert RT.STABLE.value == "stable"
        assert RT.SPIKE_UP.value == "spike_up"
        assert RT.SPIKE_DOWN.value == "spike_down"
        assert RT.TREND_UP.value == "trend_up"
        assert RT.TREND_DOWN.value == "trend_down"

    def test_regime_memory_still_works(self):
        mem = RegimeMemory(signals=("urgency",))
        regime_snap = classify_all_regimes({"urgency": 0.3}, tick=1)
        result = mem.update(regime_snap)
        assert result.get_regime("urgency") is RT.SPIKE_UP

    def test_classify_all_regimes_stable(self):
        snap = classify_all_regimes({"urgency": 0.0}, tick=1)
        assert snap.all_stable()

    def test_regime_memory_transition(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(classify_all_regimes({"urgency": 0.0}, tick=1))
        result = mem.update(classify_all_regimes({"urgency": 0.3}, tick=2))
        assert result.had_transition("urgency")

    def test_regime_memory_duration(self):
        mem = RegimeMemory(signals=("urgency",))
        for _ in range(5):
            mem.update(classify_all_regimes({"urgency": 0.0}, tick=0))
        assert mem.get_duration("urgency") == 5


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 25: Multi-transition lifecycle
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestMultiTransitionLifecycle:
    def test_spike_confirm_settle_confirm(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for _ in range(3):
            filt.filter({"urgency": RT.SPIKE_UP})
        assert filt.get_confirmed_regime("urgency") is RT.SPIKE_UP
        for _ in range(3):
            filt.filter({"urgency": RT.STABLE})
        assert filt.get_confirmed_regime("urgency") is RT.STABLE

    def test_gradual_escalation_filtered(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        filt.filter({"urgency": RT.TREND_UP})
        filt.filter({"urgency": RT.SPIKE_UP})
        assert filt.get_confirmed_regime("urgency") is RT.STABLE

    def test_stable_to_trend_to_spike_requires_full_confirmation(self):
        filt = RegimeFilter(signals=("urgency",), confirm_threshold=3)
        for _ in range(3):
            filt.filter({"urgency": RT.TREND_UP})
        assert filt.get_confirmed_regime("urgency") is RT.TREND_UP
        for _ in range(3):
            filt.filter({"urgency": RT.SPIKE_UP})
        assert filt.get_confirmed_regime("urgency") is RT.SPIKE_UP

    def test_all_stable_after_many_filtered_ticks(self):
        filt = RegimeFilter(confirm_threshold=3)
        for _ in range(20):
            snap = filt.filter(
                {
                    "urgency": RT.STABLE,
                    "risk_level": RT.STABLE,
                    "resource_pressure": RT.STABLE,
                    "stability_mode": RT.STABLE,
                }
            )
        assert snap.all_stable()

    def test_mixed_signal_lifecycle(self):
        filt = RegimeFilter(signals=("a", "b"), confirm_threshold=2)
        filt.filter({"a": RT.SPIKE_UP, "b": RT.STABLE})
        filt.filter({"a": RT.SPIKE_UP, "b": RT.TREND_DOWN})
        assert filt.get_confirmed_regime("a") is RT.SPIKE_UP
        assert filt.get_confirmed_regime("b") is RT.STABLE
        filt.filter({"a": RT.SPIKE_UP, "b": RT.TREND_DOWN})
        assert filt.get_confirmed_regime("b") is RT.TREND_DOWN


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 26: Additional coverage — threshold variations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestThresholdVariations:
    def test_threshold_1_confirms_on_first_new_regime(self):
        filt = RegimeFilter(signals=("sig",), confirm_threshold=1)
        snap = filt.filter({"sig": RT.SPIKE_UP})
        assert snap.get_filtered_regime("sig") is RT.SPIKE_UP
        assert snap.any_confirmed() is True

    def test_threshold_2_needs_two_ticks(self):
        filt = RegimeFilter(signals=("sig",), confirm_threshold=2)
        snap = filt.filter({"sig": RT.SPIKE_UP})
        assert snap.get_filtered_regime("sig") is RT.STABLE
        snap = filt.filter({"sig": RT.SPIKE_UP})
        assert snap.get_filtered_regime("sig") is RT.SPIKE_UP

    def test_threshold_10_is_very_conservative(self):
        filt = RegimeFilter(signals=("sig",), confirm_threshold=10)
        for i in range(9):
            snap = filt.filter({"sig": RT.SPIKE_UP})
            assert snap.get_filtered_regime("sig") is RT.STABLE
        snap = filt.filter({"sig": RT.SPIKE_UP})
        assert snap.get_filtered_regime("sig") is RT.SPIKE_UP

    def test_threshold_affects_both_directions(self):
        filt = RegimeFilter(signals=("sig",), confirm_threshold=2)
        filt.filter({"sig": RT.SPIKE_UP})
        filt.filter({"sig": RT.SPIKE_UP})
        assert filt.get_confirmed_regime("sig") is RT.SPIKE_UP
        filt.filter({"sig": RT.STABLE})
        assert filt.get_confirmed_regime("sig") is RT.SPIKE_UP
        filt.filter({"sig": RT.STABLE})
        assert filt.get_confirmed_regime("sig") is RT.STABLE


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 27: Additional noise patterns
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestAdditionalNoisePatterns:
    def test_almost_confirmed_then_interrupted(self):
        filt = RegimeFilter(signals=("sig",), confirm_threshold=5)
        for _ in range(4):
            filt.filter({"sig": RT.SPIKE_UP})
        assert filt.get_confirmed_regime("sig") is RT.STABLE
        filt.filter({"sig": RT.STABLE})
        assert filt.get_confirmed_regime("sig") is RT.STABLE
        pending, dur = filt.get_pending("sig")
        assert pending is None

    def test_repeated_interruptions(self):
        filt = RegimeFilter(signals=("sig",), confirm_threshold=3)
        for _ in range(5):
            filt.filter({"sig": RT.SPIKE_UP})
            filt.filter({"sig": RT.SPIKE_UP})
            filt.filter({"sig": RT.STABLE})
        assert filt.get_confirmed_regime("sig") is RT.STABLE

    def test_three_way_noise_never_confirms(self):
        filt = RegimeFilter(signals=("sig",), confirm_threshold=2)
        cycle = [RT.SPIKE_UP, RT.TREND_DOWN, RT.SPIKE_DOWN]
        for i in range(30):
            filt.filter({"sig": cycle[i % 3]})
        assert filt.get_confirmed_regime("sig") is RT.STABLE

    def test_confirm_after_noise_clears(self):
        filt = RegimeFilter(signals=("sig",), confirm_threshold=3)
        filt.filter({"sig": RT.SPIKE_UP})
        filt.filter({"sig": RT.TREND_DOWN})
        filt.filter({"sig": RT.SPIKE_DOWN})
        for _ in range(3):
            filt.filter({"sig": RT.TREND_UP})
        assert filt.get_confirmed_regime("sig") is RT.TREND_UP

    def test_suppressed_count_in_noise(self):
        filt = RegimeFilter(signals=("sig",), confirm_threshold=3)
        results = _filter_sequence(filt, "sig", [RT.SPIKE_UP, RT.STABLE, RT.SPIKE_UP])
        suppressed = [r for r in results if r.was_suppressed]
        assert len(suppressed) == 2

    def test_long_stable_then_noise_stays_stable(self):
        filt = RegimeFilter(signals=("sig",), confirm_threshold=3)
        for _ in range(50):
            filt.filter({"sig": RT.STABLE})
        filt.filter({"sig": RT.SPIKE_UP})
        filt.filter({"sig": RT.STABLE})
        assert filt.get_confirmed_regime("sig") is RT.STABLE

    def test_confirmed_spike_then_noise_stays_spike(self):
        filt = RegimeFilter(signals=("sig",), confirm_threshold=3)
        for _ in range(3):
            filt.filter({"sig": RT.SPIKE_UP})
        assert filt.get_confirmed_regime("sig") is RT.SPIKE_UP
        filt.filter({"sig": RT.STABLE})
        filt.filter({"sig": RT.SPIKE_UP})
        assert filt.get_confirmed_regime("sig") is RT.SPIKE_UP

    def test_pending_info_after_interruption(self):
        filt = RegimeFilter(signals=("sig",), confirm_threshold=3)
        filt.filter({"sig": RT.SPIKE_UP})
        filt.filter({"sig": RT.SPIKE_UP})
        snap = filt.filter({"sig": RT.TREND_DOWN})
        r = snap.get("sig")
        assert r.pending_regime is RT.TREND_DOWN
        assert r.pending_duration == 1

    def test_sequence_helper_works(self):
        filt = RegimeFilter(signals=("sig",), confirm_threshold=3)
        results = _filter_sequence(filt, "sig", [RT.STABLE, RT.SPIKE_UP, RT.SPIKE_UP, RT.SPIKE_UP])
        assert results[0].filtered_regime is RT.STABLE
        assert results[-1].filtered_regime is RT.SPIKE_UP
        assert results[-1].was_confirmed is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 28: Confirmation latency
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConfirmationLatency:
    def test_latency_equals_threshold(self):
        for threshold in [1, 2, 3, 5]:
            filt = RegimeFilter(signals=("sig",), confirm_threshold=threshold)
            for i in range(threshold):
                snap = filt.filter({"sig": RT.SPIKE_UP})
            assert snap.get_filtered_regime("sig") is RT.SPIKE_UP

    def test_no_confirmation_at_threshold_minus_one(self):
        for threshold in [2, 3, 5, 10]:
            filt = RegimeFilter(signals=("sig",), confirm_threshold=threshold)
            for i in range(threshold - 1):
                snap = filt.filter({"sig": RT.SPIKE_UP})
            assert snap.get_filtered_regime("sig") is RT.STABLE
