"""Phase 43 — Regime Memory + Transition Tracking Layer v1 tests.

Covers: RegimeState, RegimeTransition, RegimeMemorySnapshot,
update_regime_state, RegimeMemory lifecycle, pipeline integration,
hard invariants 151-155, edge cases, serialization, dependency boundary,
exports/compilation, Phase 42 regression.

Target: 130-180 tests.
"""

from __future__ import annotations

import ast
import copy
import sys

import pytest

sys.path.insert(0, "/opt/OS")

from umh.runtime.regime import (
    RegimeResult,
    RegimeSnapshot,
    RegimeType,
    classify_all_regimes,
)
from umh.runtime.regime_memory import (
    RegimeMemory,
    RegimeMemorySnapshot,
    RegimeState,
    RegimeTransition,
    _SIGNAL_NAMES,
    update_regime_state,
)


# ── helpers ─────────────────────────────────────────────────────────


def _make_regime_result(name: str, regime: RegimeType, delta: float = 0.0) -> RegimeResult:
    return RegimeResult(
        signal_name=name,
        regime=regime,
        delta=delta,
        magnitude=abs(delta),
        is_spike=regime in (RegimeType.SPIKE_UP, RegimeType.SPIKE_DOWN),
        is_trend=regime in (RegimeType.TREND_UP, RegimeType.TREND_DOWN),
    )


def _make_snapshot(regimes: dict[str, RegimeType], tick: int = 0) -> RegimeSnapshot:
    results = {}
    for name, regime in regimes.items():
        results[name] = _make_regime_result(name, regime)
    return RegimeSnapshot(regimes=results, tick=tick)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 1: RegimeState creation and defaults
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRegimeStateCreation:
    def test_default_values(self):
        s = RegimeState(signal_name="urgency")
        assert s.signal_name == "urgency"
        assert s.current_regime is RegimeType.STABLE
        assert s.previous_regime is RegimeType.STABLE
        assert s.duration == 0
        assert s.transition_count == 0
        assert s.last_transition_tick == 0

    def test_custom_values(self):
        s = RegimeState(
            signal_name="risk",
            current_regime=RegimeType.SPIKE_UP,
            previous_regime=RegimeType.TREND_UP,
            duration=5,
            transition_count=3,
            last_transition_tick=10,
        )
        assert s.current_regime is RegimeType.SPIKE_UP
        assert s.previous_regime is RegimeType.TREND_UP
        assert s.duration == 5
        assert s.transition_count == 3
        assert s.last_transition_tick == 10

    def test_mutable(self):
        s = RegimeState(signal_name="urgency")
        s.duration = 10
        s.current_regime = RegimeType.TREND_UP
        assert s.duration == 10
        assert s.current_regime is RegimeType.TREND_UP

    def test_to_dict(self):
        s = RegimeState(signal_name="urgency")
        d = s.to_dict()
        assert d["signal_name"] == "urgency"
        assert d["current_regime"] == "stable"
        assert d["previous_regime"] == "stable"
        assert d["duration"] == 0
        assert d["transition_count"] == 0
        assert d["last_transition_tick"] == 0

    def test_to_dict_non_default(self):
        s = RegimeState(
            signal_name="risk",
            current_regime=RegimeType.SPIKE_DOWN,
            previous_regime=RegimeType.TREND_DOWN,
            duration=7,
            transition_count=2,
            last_transition_tick=5,
        )
        d = s.to_dict()
        assert d["current_regime"] == "spike_down"
        assert d["previous_regime"] == "trend_down"
        assert d["duration"] == 7

    def test_all_regime_types_in_to_dict(self):
        for rt in RegimeType:
            s = RegimeState(signal_name="test", current_regime=rt)
            d = s.to_dict()
            assert d["current_regime"] == rt.value


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 2: RegimeTransition frozen record
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRegimeTransition:
    def test_creation(self):
        t = RegimeTransition(
            signal_name="urgency",
            from_regime=RegimeType.STABLE,
            to_regime=RegimeType.SPIKE_UP,
            tick=3,
            previous_duration=5,
        )
        assert t.signal_name == "urgency"
        assert t.from_regime is RegimeType.STABLE
        assert t.to_regime is RegimeType.SPIKE_UP
        assert t.tick == 3
        assert t.previous_duration == 5

    def test_frozen(self):
        t = RegimeTransition(
            signal_name="urgency",
            from_regime=RegimeType.STABLE,
            to_regime=RegimeType.SPIKE_UP,
            tick=3,
            previous_duration=5,
        )
        with pytest.raises(AttributeError):
            t.tick = 10

    def test_to_dict(self):
        t = RegimeTransition(
            signal_name="risk",
            from_regime=RegimeType.TREND_UP,
            to_regime=RegimeType.SPIKE_UP,
            tick=7,
            previous_duration=3,
        )
        d = t.to_dict()
        assert d["signal_name"] == "risk"
        assert d["from_regime"] == "trend_up"
        assert d["to_regime"] == "spike_up"
        assert d["tick"] == 7
        assert d["previous_duration"] == 3

    def test_equality(self):
        t1 = RegimeTransition("a", RegimeType.STABLE, RegimeType.SPIKE_UP, 1, 0)
        t2 = RegimeTransition("a", RegimeType.STABLE, RegimeType.SPIKE_UP, 1, 0)
        assert t1 == t2

    def test_inequality(self):
        t1 = RegimeTransition("a", RegimeType.STABLE, RegimeType.SPIKE_UP, 1, 0)
        t2 = RegimeTransition("b", RegimeType.STABLE, RegimeType.SPIKE_UP, 1, 0)
        assert t1 != t2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 3: RegimeMemorySnapshot
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRegimeMemorySnapshot:
    def test_creation(self):
        states = {"urgency": RegimeState(signal_name="urgency")}
        snap = RegimeMemorySnapshot(states=states, transitions=[], tick=0)
        assert snap.tick == 0
        assert len(snap.states) == 1

    def test_frozen(self):
        snap = RegimeMemorySnapshot(states={}, transitions=[], tick=0)
        with pytest.raises(AttributeError):
            snap.tick = 5

    def test_get_state(self):
        states = {"urgency": RegimeState(signal_name="urgency", duration=3)}
        snap = RegimeMemorySnapshot(states=states, transitions=[], tick=1)
        s = snap.get_state("urgency")
        assert s is not None
        assert s.duration == 3

    def test_get_state_missing(self):
        snap = RegimeMemorySnapshot(states={}, transitions=[], tick=0)
        assert snap.get_state("urgency") is None

    def test_get_duration(self):
        states = {"urgency": RegimeState(signal_name="urgency", duration=7)}
        snap = RegimeMemorySnapshot(states=states, transitions=[], tick=1)
        assert snap.get_duration("urgency") == 7

    def test_get_duration_missing(self):
        snap = RegimeMemorySnapshot(states={}, transitions=[], tick=0)
        assert snap.get_duration("urgency") == 0

    def test_get_regime(self):
        states = {"urgency": RegimeState(signal_name="urgency", current_regime=RegimeType.SPIKE_UP)}
        snap = RegimeMemorySnapshot(states=states, transitions=[], tick=1)
        assert snap.get_regime("urgency") is RegimeType.SPIKE_UP

    def test_get_regime_missing_returns_stable(self):
        snap = RegimeMemorySnapshot(states={}, transitions=[], tick=0)
        assert snap.get_regime("urgency") is RegimeType.STABLE

    def test_had_transition_true(self):
        t = RegimeTransition("urgency", RegimeType.STABLE, RegimeType.SPIKE_UP, 1, 0)
        snap = RegimeMemorySnapshot(states={}, transitions=[t], tick=1)
        assert snap.had_transition("urgency") is True

    def test_had_transition_false(self):
        t = RegimeTransition("risk", RegimeType.STABLE, RegimeType.SPIKE_UP, 1, 0)
        snap = RegimeMemorySnapshot(states={}, transitions=[t], tick=1)
        assert snap.had_transition("urgency") is False

    def test_transition_count(self):
        t1 = RegimeTransition("a", RegimeType.STABLE, RegimeType.SPIKE_UP, 1, 0)
        t2 = RegimeTransition("b", RegimeType.STABLE, RegimeType.TREND_UP, 1, 0)
        snap = RegimeMemorySnapshot(states={}, transitions=[t1, t2], tick=1)
        assert snap.transition_count() == 2

    def test_all_stable_true(self):
        states = {
            "a": RegimeState(signal_name="a"),
            "b": RegimeState(signal_name="b"),
        }
        snap = RegimeMemorySnapshot(states=states, transitions=[], tick=0)
        assert snap.all_stable() is True

    def test_all_stable_false(self):
        states = {
            "a": RegimeState(signal_name="a"),
            "b": RegimeState(signal_name="b", current_regime=RegimeType.SPIKE_UP),
        }
        snap = RegimeMemorySnapshot(states=states, transitions=[], tick=0)
        assert snap.all_stable() is False

    def test_all_stable_empty(self):
        snap = RegimeMemorySnapshot(states={}, transitions=[], tick=0)
        assert snap.all_stable() is True

    def test_to_dict(self):
        states = {"urgency": RegimeState(signal_name="urgency")}
        snap = RegimeMemorySnapshot(states=states, transitions=[], tick=5)
        d = snap.to_dict()
        assert d["tick"] == 5
        assert "urgency" in d["states"]
        assert d["transitions"] == []

    def test_to_dict_with_transitions(self):
        t = RegimeTransition("urgency", RegimeType.STABLE, RegimeType.SPIKE_UP, 1, 0)
        snap = RegimeMemorySnapshot(states={}, transitions=[t], tick=1)
        d = snap.to_dict()
        assert len(d["transitions"]) == 1
        assert d["transitions"][0]["signal_name"] == "urgency"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 4: update_regime_state function
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestUpdateRegimeState:
    def test_same_regime_increments_duration(self):
        s = RegimeState(signal_name="urgency", current_regime=RegimeType.STABLE, duration=3)
        result = update_regime_state(s, RegimeType.STABLE, tick=4)
        assert result is None
        assert s.duration == 4

    def test_different_regime_creates_transition(self):
        s = RegimeState(signal_name="urgency", current_regime=RegimeType.STABLE, duration=5)
        result = update_regime_state(s, RegimeType.SPIKE_UP, tick=6)
        assert result is not None
        assert result.from_regime is RegimeType.STABLE
        assert result.to_regime is RegimeType.SPIKE_UP
        assert result.previous_duration == 5
        assert result.tick == 6

    def test_transition_updates_state(self):
        s = RegimeState(signal_name="urgency", current_regime=RegimeType.STABLE, duration=5)
        update_regime_state(s, RegimeType.SPIKE_UP, tick=6)
        assert s.current_regime is RegimeType.SPIKE_UP
        assert s.previous_regime is RegimeType.STABLE
        assert s.duration == 1
        assert s.transition_count == 1
        assert s.last_transition_tick == 6

    def test_multiple_same_regime_accumulates(self):
        s = RegimeState(signal_name="urgency", duration=0)
        for i in range(10):
            update_regime_state(s, RegimeType.STABLE, tick=i + 1)
        assert s.duration == 10
        assert s.transition_count == 0

    def test_transition_resets_duration_to_one(self):
        s = RegimeState(signal_name="urgency", current_regime=RegimeType.STABLE, duration=100)
        update_regime_state(s, RegimeType.TREND_UP, tick=101)
        assert s.duration == 1

    def test_transition_preserves_previous_duration(self):
        s = RegimeState(signal_name="urgency", current_regime=RegimeType.STABLE, duration=42)
        t = update_regime_state(s, RegimeType.TREND_DOWN, tick=43)
        assert t.previous_duration == 42

    def test_consecutive_transitions(self):
        s = RegimeState(signal_name="urgency")
        update_regime_state(s, RegimeType.STABLE, tick=1)
        assert s.duration == 1

        t = update_regime_state(s, RegimeType.SPIKE_UP, tick=2)
        assert t is not None
        assert s.transition_count == 1

        t = update_regime_state(s, RegimeType.TREND_DOWN, tick=3)
        assert t is not None
        assert s.transition_count == 2
        assert s.previous_regime is RegimeType.SPIKE_UP

    def test_zero_duration_transition(self):
        s = RegimeState(signal_name="urgency", current_regime=RegimeType.STABLE, duration=0)
        t = update_regime_state(s, RegimeType.SPIKE_UP, tick=1)
        assert t is not None
        assert t.previous_duration == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 5: RegimeMemory construction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRegimeMemoryConstruction:
    def test_default_signals(self):
        mem = RegimeMemory()
        assert set(mem.states.keys()) == set(_SIGNAL_NAMES)

    def test_custom_signals(self):
        mem = RegimeMemory(signals=("alpha", "beta"))
        assert set(mem.states.keys()) == {"alpha", "beta"}

    def test_initial_tick_zero(self):
        mem = RegimeMemory()
        assert mem.tick == 0

    def test_initial_history_empty(self):
        mem = RegimeMemory()
        assert mem.history == []

    def test_initial_all_stable(self):
        mem = RegimeMemory()
        for state in mem.states.values():
            assert state.current_regime is RegimeType.STABLE
            assert state.duration == 0

    def test_states_returns_copy(self):
        mem = RegimeMemory()
        s1 = mem.states
        s2 = mem.states
        assert s1 is not s2

    def test_history_returns_copy(self):
        mem = RegimeMemory()
        h1 = mem.history
        h2 = mem.history
        assert h1 is not h2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 6: RegimeMemory.update() — same regime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRegimeMemoryUpdateSameRegime:
    def test_stable_increments_duration(self):
        mem = RegimeMemory(signals=("urgency",))
        snap = _make_snapshot({"urgency": RegimeType.STABLE})
        result = mem.update(snap)
        assert result.get_duration("urgency") == 1
        assert result.transition_count() == 0

    def test_repeated_stable_accumulates(self):
        mem = RegimeMemory(signals=("urgency",))
        snap = _make_snapshot({"urgency": RegimeType.STABLE})
        for _ in range(5):
            result = mem.update(snap)
        assert result.get_duration("urgency") == 5
        assert result.transition_count() == 0

    def test_tick_increments(self):
        mem = RegimeMemory(signals=("urgency",))
        snap = _make_snapshot({"urgency": RegimeType.STABLE})
        for i in range(3):
            result = mem.update(snap)
        assert result.tick == 3
        assert mem.tick == 3


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 7: RegimeMemory.update() — regime change
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRegimeMemoryUpdateRegimeChange:
    def test_transition_detected(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        result = mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        assert result.had_transition("urgency")
        assert result.transition_count() == 1

    def test_transition_resets_duration(self):
        mem = RegimeMemory(signals=("urgency",))
        for _ in range(5):
            mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        result = mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        assert result.get_duration("urgency") == 1

    def test_transition_records_previous(self):
        mem = RegimeMemory(signals=("urgency",))
        for _ in range(5):
            mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        result = mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        t = result.transitions[0]
        assert t.from_regime is RegimeType.STABLE
        assert t.to_regime is RegimeType.SPIKE_UP
        assert t.previous_duration == 5

    def test_history_accumulates(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        mem.update(_make_snapshot({"urgency": RegimeType.TREND_DOWN}))
        assert mem.total_transitions() == 2
        assert len(mem.history) == 2

    def test_regime_after_transition(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        assert mem.get_regime("urgency") is RegimeType.SPIKE_UP

    def test_transition_count_per_signal(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        assert mem.get_transition_count("urgency") == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 8: Cross-signal independence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCrossSignalIndependence:
    def test_signals_track_independently(self):
        mem = RegimeMemory(signals=("a", "b"))
        mem.update(_make_snapshot({"a": RegimeType.STABLE, "b": RegimeType.SPIKE_UP}))
        assert mem.get_regime("a") is RegimeType.STABLE
        assert mem.get_regime("b") is RegimeType.SPIKE_UP

    def test_transition_in_one_not_other(self):
        mem = RegimeMemory(signals=("a", "b"))
        mem.update(_make_snapshot({"a": RegimeType.STABLE, "b": RegimeType.STABLE}))
        result = mem.update(_make_snapshot({"a": RegimeType.STABLE, "b": RegimeType.SPIKE_UP}))
        assert not result.had_transition("a")
        assert result.had_transition("b")

    def test_durations_independent(self):
        mem = RegimeMemory(signals=("a", "b"))
        for _ in range(3):
            mem.update(_make_snapshot({"a": RegimeType.STABLE, "b": RegimeType.STABLE}))
        mem.update(_make_snapshot({"a": RegimeType.STABLE, "b": RegimeType.SPIKE_UP}))
        assert mem.get_duration("a") == 4
        assert mem.get_duration("b") == 1

    def test_transition_counts_independent(self):
        mem = RegimeMemory(signals=("a", "b"))
        mem.update(_make_snapshot({"a": RegimeType.STABLE, "b": RegimeType.STABLE}))
        mem.update(_make_snapshot({"a": RegimeType.SPIKE_UP, "b": RegimeType.STABLE}))
        mem.update(_make_snapshot({"a": RegimeType.STABLE, "b": RegimeType.SPIKE_UP}))
        assert mem.get_transition_count("a") == 2
        assert mem.get_transition_count("b") == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 9: Dynamic signal registration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDynamicSignalRegistration:
    def test_new_signal_in_snapshot(self):
        mem = RegimeMemory(signals=("a",))
        snap = _make_snapshot({"a": RegimeType.STABLE, "new_signal": RegimeType.SPIKE_UP})
        result = mem.update(snap)
        assert "new_signal" in result.states

    def test_new_signal_starts_at_duration_one(self):
        mem = RegimeMemory(signals=("a",))
        snap = _make_snapshot({"a": RegimeType.STABLE, "new_signal": RegimeType.SPIKE_UP})
        result = mem.update(snap)
        assert result.get_duration("new_signal") == 1

    def test_absent_signal_increments_duration(self):
        mem = RegimeMemory(signals=("a", "b"))
        mem.update(_make_snapshot({"a": RegimeType.STABLE, "b": RegimeType.STABLE}))
        result = mem.update(_make_snapshot({"a": RegimeType.STABLE}))
        assert result.get_duration("b") == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 10: update_single
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestUpdateSingle:
    def test_same_regime_no_transition(self):
        mem = RegimeMemory(signals=("urgency",))
        t = mem.update_single("urgency", RegimeType.STABLE)
        assert t is None

    def test_different_regime_returns_transition(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update_single("urgency", RegimeType.STABLE)
        t = mem.update_single("urgency", RegimeType.SPIKE_UP)
        assert t is not None
        assert t.to_regime is RegimeType.SPIKE_UP

    def test_auto_increments_tick(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update_single("urgency", RegimeType.STABLE)
        assert mem.tick == 1
        mem.update_single("urgency", RegimeType.STABLE)
        assert mem.tick == 2

    def test_explicit_tick(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update_single("urgency", RegimeType.STABLE, tick=10)
        assert mem.tick == 0

    def test_unknown_signal_auto_registers(self):
        mem = RegimeMemory(signals=("a",))
        mem.update_single("new_signal", RegimeType.SPIKE_UP)
        assert "new_signal" in mem.states

    def test_transition_added_to_history(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update_single("urgency", RegimeType.STABLE)
        mem.update_single("urgency", RegimeType.SPIKE_UP)
        assert mem.total_transitions() == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 11: Rapid flip behavior
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRapidFlip:
    def test_rapid_oscillation(self):
        mem = RegimeMemory(signals=("urgency",))
        for i in range(10):
            regime = RegimeType.SPIKE_UP if i % 2 == 0 else RegimeType.STABLE
            mem.update(_make_snapshot({"urgency": regime}))
        assert mem.get_duration("urgency") == 1
        assert mem.get_transition_count("urgency") == 10

    def test_every_flip_recorded(self):
        mem = RegimeMemory(signals=("urgency",))
        for i in range(6):
            regime = RegimeType.SPIKE_UP if i % 2 == 0 else RegimeType.STABLE
            mem.update(_make_snapshot({"urgency": regime}))
        assert mem.total_transitions() == 6
        assert len(mem.history) == 6

    def test_all_five_regimes_cycled(self):
        mem = RegimeMemory(signals=("urgency",))
        regimes = list(RegimeType)
        for rt in regimes:
            mem.update(_make_snapshot({"urgency": rt}))
        assert mem.get_transition_count("urgency") == len(regimes) - 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 12: Reset
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestReset:
    def test_reset_clears_duration(self):
        mem = RegimeMemory(signals=("urgency",))
        for _ in range(5):
            mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        mem.reset()
        assert mem.get_duration("urgency") == 0

    def test_reset_clears_regimes(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        mem.reset()
        assert mem.get_regime("urgency") is RegimeType.STABLE

    def test_reset_clears_history(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        mem.reset()
        assert mem.total_transitions() == 0
        assert mem.history == []

    def test_reset_clears_tick(self):
        mem = RegimeMemory(signals=("urgency",))
        for _ in range(5):
            mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        mem.reset()
        assert mem.tick == 0

    def test_reset_preserves_signal_set(self):
        mem = RegimeMemory(signals=("a", "b", "c"))
        mem.reset()
        assert set(mem.states.keys()) == {"a", "b", "c"}

    def test_usable_after_reset(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        mem.reset()
        result = mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        assert result.get_duration("urgency") == 1
        assert result.transition_count() == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 13: Snapshot (no-update)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSnapshotNoUpdate:
    def test_snapshot_does_not_increment_tick(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        snap = mem.snapshot()
        assert snap.tick == 1
        assert mem.tick == 1

    def test_snapshot_has_empty_transitions(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        snap = mem.snapshot()
        assert snap.transitions == []

    def test_snapshot_reflects_current_state(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        snap = mem.snapshot()
        assert snap.get_regime("urgency") is RegimeType.SPIKE_UP


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 14: recent_transitions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRecentTransitions:
    def test_returns_last_n(self):
        mem = RegimeMemory(signals=("urgency",))
        regimes = [
            RegimeType.STABLE,
            RegimeType.SPIKE_UP,
            RegimeType.STABLE,
            RegimeType.TREND_DOWN,
            RegimeType.STABLE,
            RegimeType.SPIKE_DOWN,
        ]
        for rt in regimes:
            mem.update(_make_snapshot({"urgency": rt}))
        recent = mem.recent_transitions(3)
        assert len(recent) == 3
        assert recent[-1].to_regime is RegimeType.SPIKE_DOWN

    def test_returns_all_if_fewer(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        recent = mem.recent_transitions(10)
        assert len(recent) == 1

    def test_default_n_is_5(self):
        mem = RegimeMemory(signals=("urgency",))
        for i, rt in enumerate(
            [
                RegimeType.STABLE,
                RegimeType.SPIKE_UP,
                RegimeType.STABLE,
                RegimeType.TREND_DOWN,
                RegimeType.STABLE,
                RegimeType.SPIKE_DOWN,
                RegimeType.STABLE,
                RegimeType.TREND_UP,
            ]
        ):
            mem.update(_make_snapshot({"urgency": rt}))
        recent = mem.recent_transitions()
        assert len(recent) == 5


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 15: Accessors for missing signals
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestMissingSignalAccessors:
    def test_get_state_missing(self):
        mem = RegimeMemory(signals=("a",))
        assert mem.get_state("nonexistent") is None

    def test_get_duration_missing(self):
        mem = RegimeMemory(signals=("a",))
        assert mem.get_duration("nonexistent") == 0

    def test_get_regime_missing(self):
        mem = RegimeMemory(signals=("a",))
        assert mem.get_regime("nonexistent") is RegimeType.STABLE

    def test_get_transition_count_missing(self):
        mem = RegimeMemory(signals=("a",))
        assert mem.get_transition_count("nonexistent") == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 16: Serialization (to_dict)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSerialization:
    def test_regime_memory_to_dict(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        d = mem.to_dict()
        assert d["tick"] == 1
        assert "urgency" in d["states"]
        assert d["total_transitions"] == 0
        assert d["recent_transitions"] == []

    def test_to_dict_with_transitions(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        d = mem.to_dict()
        assert d["total_transitions"] == 1
        assert len(d["recent_transitions"]) == 1

    def test_to_dict_recent_capped_at_five(self):
        mem = RegimeMemory(signals=("urgency",))
        for i, rt in enumerate(
            [
                RegimeType.STABLE,
                RegimeType.SPIKE_UP,
                RegimeType.STABLE,
                RegimeType.TREND_DOWN,
                RegimeType.STABLE,
                RegimeType.SPIKE_DOWN,
                RegimeType.STABLE,
                RegimeType.TREND_UP,
            ]
        ):
            mem.update(_make_snapshot({"urgency": rt}))
        d = mem.to_dict()
        assert d["total_transitions"] == 7
        assert len(d["recent_transitions"]) == 5

    def test_to_dict_sorted_states(self):
        mem = RegimeMemory(signals=("z_signal", "a_signal"))
        d = mem.to_dict()
        keys = list(d["states"].keys())
        assert keys == sorted(keys)

    def test_all_dicts_are_plain_types(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        d = mem.to_dict()
        import json

        json.dumps(d)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 17: Long-duration stability tracking
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLongDurationStability:
    def test_100_ticks_stable(self):
        mem = RegimeMemory(signals=("urgency",))
        snap = _make_snapshot({"urgency": RegimeType.STABLE})
        for _ in range(100):
            mem.update(snap)
        assert mem.get_duration("urgency") == 100
        assert mem.total_transitions() == 0
        assert mem.tick == 100

    def test_duration_resets_after_spike_then_accumulates(self):
        mem = RegimeMemory(signals=("urgency",))
        for _ in range(50):
            mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        for _ in range(30):
            mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        assert mem.get_duration("urgency") == 31
        assert mem.total_transitions() == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 18: Pipeline integration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPipelineIntegration:
    def test_classify_then_memory(self):
        deltas = {"urgency": 0.0, "risk_level": 0.3}
        regime_snap = classify_all_regimes(deltas, tick=1)
        mem = RegimeMemory(signals=("urgency", "risk_level"))
        result = mem.update(regime_snap)
        assert result.get_regime("urgency") is RegimeType.STABLE
        assert result.get_regime("risk_level") is RegimeType.SPIKE_UP

    def test_classify_transition_detected(self):
        mem = RegimeMemory(signals=("urgency",))
        snap1 = classify_all_regimes({"urgency": 0.0}, tick=1)
        mem.update(snap1)
        snap2 = classify_all_regimes({"urgency": 0.3}, tick=2)
        result = mem.update(snap2)
        assert result.had_transition("urgency")
        assert result.get_regime("urgency") is RegimeType.SPIKE_UP

    def test_pipeline_deterministic(self):
        mem1 = RegimeMemory(signals=("urgency",))
        mem2 = RegimeMemory(signals=("urgency",))
        deltas_seq = [0.0, 0.0, 0.3, 0.3, 0.1, 0.0]
        for i, d in enumerate(deltas_seq):
            snap = classify_all_regimes({"urgency": d}, tick=i + 1)
            r1 = mem1.update(snap)
            r2 = mem2.update(snap)
            assert r1.get_regime("urgency") == r2.get_regime("urgency")
            assert r1.get_duration("urgency") == r2.get_duration("urgency")

    def test_full_four_signal_pipeline(self):
        mem = RegimeMemory()
        deltas = {
            "urgency": 0.0,
            "risk_level": 0.1,
            "resource_pressure": 0.3,
            "stability_mode": -0.15,
        }
        snap = classify_all_regimes(deltas, tick=1)
        result = mem.update(snap)
        assert result.get_regime("urgency") is RegimeType.STABLE
        assert result.get_regime("risk_level") is RegimeType.TREND_UP
        assert result.get_regime("resource_pressure") is RegimeType.SPIKE_UP
        assert result.get_regime("stability_mode") is RegimeType.TREND_DOWN


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 19: Determinism
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDeterminism:
    def test_same_sequence_same_result(self):
        def run_sequence():
            mem = RegimeMemory(signals=("urgency",))
            regimes = [
                RegimeType.STABLE,
                RegimeType.STABLE,
                RegimeType.SPIKE_UP,
                RegimeType.SPIKE_UP,
                RegimeType.TREND_DOWN,
                RegimeType.STABLE,
            ]
            results = []
            for rt in regimes:
                r = mem.update(_make_snapshot({"urgency": rt}))
                results.append((r.get_regime("urgency"), r.get_duration("urgency")))
            return results, mem.total_transitions()

        r1, t1 = run_sequence()
        r2, t2 = run_sequence()
        assert r1 == r2
        assert t1 == t2

    def test_independent_instances(self):
        mem1 = RegimeMemory(signals=("urgency",))
        mem2 = RegimeMemory(signals=("urgency",))
        mem1.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        assert mem1.get_regime("urgency") is RegimeType.SPIKE_UP
        assert mem2.get_regime("urgency") is RegimeType.STABLE


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 20: Hard invariants 151-155
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestHardInvariants:
    def test_inv151_same_regime_increments_duration(self):
        """Invariant 151: Same regime on consecutive ticks increments duration."""
        mem = RegimeMemory(signals=("urgency",))
        for i in range(10):
            result = mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
            assert result.get_duration("urgency") == i + 1

    def test_inv152_regime_change_resets_duration_to_one(self):
        """Invariant 152: Regime change resets duration to 1."""
        mem = RegimeMemory(signals=("urgency",))
        for _ in range(5):
            mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        result = mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        assert result.get_duration("urgency") == 1

    def test_inv153_transition_records_previous_regime(self):
        """Invariant 153: Transition records correct from/to regime."""
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        result = mem.update(_make_snapshot({"urgency": RegimeType.TREND_UP}))
        t = result.transitions[0]
        assert t.from_regime is RegimeType.STABLE
        assert t.to_regime is RegimeType.TREND_UP

    def test_inv154_transition_count_monotonic(self):
        """Invariant 154: Per-signal transition count is monotonically non-decreasing."""
        mem = RegimeMemory(signals=("urgency",))
        prev_count = 0
        regimes = [
            RegimeType.STABLE,
            RegimeType.SPIKE_UP,
            RegimeType.SPIKE_UP,
            RegimeType.STABLE,
            RegimeType.TREND_DOWN,
            RegimeType.STABLE,
        ]
        for rt in regimes:
            mem.update(_make_snapshot({"urgency": rt}))
            count = mem.get_transition_count("urgency")
            assert count >= prev_count
            prev_count = count

    def test_inv155_signals_mutually_independent(self):
        """Invariant 155: Signals are mutually independent — changes to one don't affect another."""
        mem = RegimeMemory(signals=("a", "b"))
        mem.update(_make_snapshot({"a": RegimeType.STABLE, "b": RegimeType.STABLE}))
        a_duration_before = mem.get_duration("a")
        mem.update(_make_snapshot({"a": RegimeType.STABLE, "b": RegimeType.SPIKE_UP}))
        assert mem.get_duration("a") == a_duration_before + 1
        assert mem.get_regime("a") is RegimeType.STABLE

    def test_inv151_across_all_regime_types(self):
        for rt in RegimeType:
            mem = RegimeMemory(signals=("sig",))
            mem.update(_make_snapshot({"sig": rt}))
            for i in range(5):
                result = mem.update(_make_snapshot({"sig": rt}))
            assert mem.get_duration("sig") == 6

    def test_inv152_for_all_transitions(self):
        pairs = [
            (RegimeType.STABLE, RegimeType.SPIKE_UP),
            (RegimeType.SPIKE_UP, RegimeType.STABLE),
            (RegimeType.TREND_UP, RegimeType.TREND_DOWN),
            (RegimeType.SPIKE_DOWN, RegimeType.SPIKE_UP),
        ]
        for from_rt, to_rt in pairs:
            mem = RegimeMemory(signals=("sig",))
            mem.update(_make_snapshot({"sig": from_rt}))
            mem.update(_make_snapshot({"sig": from_rt}))
            mem.update(_make_snapshot({"sig": from_rt}))
            result = mem.update(_make_snapshot({"sig": to_rt}))
            assert result.get_duration("sig") == 1

    def test_inv154_over_many_transitions(self):
        mem = RegimeMemory(signals=("sig",))
        prev = 0
        for i in range(50):
            rt = list(RegimeType)[i % len(RegimeType)]
            mem.update(_make_snapshot({"sig": rt}))
            count = mem.get_transition_count("sig")
            assert count >= prev
            prev = count


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 21: Edge cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEdgeCases:
    def test_single_signal_memory(self):
        mem = RegimeMemory(signals=("only",))
        result = mem.update(_make_snapshot({"only": RegimeType.STABLE}))
        assert result.get_duration("only") == 1

    def test_empty_snapshot(self):
        mem = RegimeMemory(signals=("a",))
        mem.update(_make_snapshot({"a": RegimeType.STABLE}))
        result = mem.update(_make_snapshot({}))
        assert result.get_duration("a") == 2

    def test_snapshot_with_extra_signals(self):
        mem = RegimeMemory(signals=("a",))
        result = mem.update(
            _make_snapshot(
                {"a": RegimeType.STABLE, "b": RegimeType.SPIKE_UP, "c": RegimeType.TREND_DOWN}
            )
        )
        assert "b" in result.states
        assert "c" in result.states

    def test_transition_on_first_tick(self):
        mem = RegimeMemory(signals=("urgency",))
        result = mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        assert result.had_transition("urgency")
        assert result.get_duration("urgency") == 1

    def test_no_transition_on_first_tick_if_stable(self):
        mem = RegimeMemory(signals=("urgency",))
        result = mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        assert not result.had_transition("urgency")
        assert result.get_duration("urgency") == 1

    def test_many_signals(self):
        signals = tuple(f"signal_{i}" for i in range(20))
        mem = RegimeMemory(signals=signals)
        snap = _make_snapshot({s: RegimeType.STABLE for s in signals})
        result = mem.update(snap)
        assert len(result.states) == 20


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 22: Dependency boundary
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDependencyBoundary:
    def test_no_io_imports(self):
        source = open("/opt/OS/umh/runtime/regime_memory.py").read()
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
        source = open("/opt/OS/umh/runtime/regime_memory.py").read()
        assert "umh.cells" not in source
        assert "umh.environments" not in source
        assert "umh.adapters" not in source

    def test_imports_only_regime(self):
        source = open("/opt/OS/umh/runtime/regime_memory.py").read()
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
    def test_regime_memory_compiles(self):
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/regime_memory.py", doraise=True)

    def test_init_compiles(self):
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/__init__.py", doraise=True)

    def test_exports_from_init(self):
        from umh.runtime import (
            RegimeMemory,
            RegimeMemorySnapshot,
            RegimeState,
            RegimeTransition,
            update_regime_state,
        )

        assert RegimeMemory is not None
        assert RegimeMemorySnapshot is not None
        assert RegimeState is not None
        assert RegimeTransition is not None
        assert update_regime_state is not None

    def test_in_all_list(self):
        from umh.runtime import __all__

        expected = [
            "RegimeMemory",
            "RegimeMemorySnapshot",
            "RegimeState",
            "RegimeTransition",
            "update_regime_state",
        ]
        for name in expected:
            assert name in __all__, f"{name} missing from __all__"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 24: Phase 42 regression
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPhase42Regression:
    def test_regime_type_enum(self):
        assert RegimeType.STABLE.value == "stable"
        assert RegimeType.SPIKE_UP.value == "spike_up"
        assert RegimeType.SPIKE_DOWN.value == "spike_down"
        assert RegimeType.TREND_UP.value == "trend_up"
        assert RegimeType.TREND_DOWN.value == "trend_down"

    def test_classify_all_regimes_stable(self):
        deltas = {"urgency": 0.0, "risk_level": 0.01}
        snap = classify_all_regimes(deltas, tick=1)
        assert snap.all_stable()

    def test_classify_all_regimes_spike(self):
        deltas = {"urgency": 0.3}
        snap = classify_all_regimes(deltas, tick=1)
        assert snap.has_any_spike()
        assert snap.get_regime("urgency") is RegimeType.SPIKE_UP

    def test_classify_all_regimes_trend(self):
        deltas = {"urgency": 0.1}
        snap = classify_all_regimes(deltas, tick=1)
        assert snap.has_any_trend()
        assert snap.get_regime("urgency") is RegimeType.TREND_UP

    def test_regime_result_frozen(self):
        r = _make_regime_result("urgency", RegimeType.STABLE)
        with pytest.raises(AttributeError):
            r.regime = RegimeType.SPIKE_UP

    def test_regime_snapshot_frozen(self):
        snap = RegimeSnapshot(regimes={}, tick=0)
        with pytest.raises(AttributeError):
            snap.tick = 5


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 25: Multi-tick lifecycle scenarios
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestMultiTickLifecycle:
    def test_spike_settle_pattern(self):
        mem = RegimeMemory(signals=("urgency",))
        for _ in range(3):
            mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        for _ in range(5):
            mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        assert mem.get_regime("urgency") is RegimeType.STABLE
        assert mem.get_duration("urgency") == 5
        assert mem.total_transitions() == 2

    def test_gradual_escalation(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        mem.update(_make_snapshot({"urgency": RegimeType.TREND_UP}))
        mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        assert mem.get_regime("urgency") is RegimeType.SPIKE_UP
        assert mem.total_transitions() == 2
        history = mem.history
        assert history[0].from_regime is RegimeType.STABLE
        assert history[0].to_regime is RegimeType.TREND_UP
        assert history[1].from_regime is RegimeType.TREND_UP
        assert history[1].to_regime is RegimeType.SPIKE_UP

    def test_all_stable_after_many_ticks(self):
        mem = RegimeMemory()
        snap = _make_snapshot(
            {
                "urgency": RegimeType.STABLE,
                "risk_level": RegimeType.STABLE,
                "resource_pressure": RegimeType.STABLE,
                "stability_mode": RegimeType.STABLE,
            }
        )
        for _ in range(20):
            result = mem.update(snap)
        assert result.all_stable()
        assert mem.total_transitions() == 0

    def test_mixed_signals_lifecycle(self):
        mem = RegimeMemory(signals=("a", "b"))
        mem.update(_make_snapshot({"a": RegimeType.STABLE, "b": RegimeType.STABLE}))
        mem.update(_make_snapshot({"a": RegimeType.SPIKE_UP, "b": RegimeType.STABLE}))
        mem.update(_make_snapshot({"a": RegimeType.SPIKE_UP, "b": RegimeType.TREND_DOWN}))
        mem.update(_make_snapshot({"a": RegimeType.STABLE, "b": RegimeType.TREND_DOWN}))
        assert mem.get_transition_count("a") == 2
        assert mem.get_transition_count("b") == 1
        assert mem.get_duration("a") == 1
        assert mem.get_duration("b") == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Section 26: Additional coverage
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestAdditionalCoverage:
    def test_update_single_with_explicit_tick_no_auto_increment(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update_single("urgency", RegimeType.STABLE, tick=100)
        mem.update_single("urgency", RegimeType.STABLE, tick=200)
        assert mem.tick == 0

    def test_snapshot_serialization_roundtrip_shape(self):
        mem = RegimeMemory(signals=("urgency",))
        mem.update(_make_snapshot({"urgency": RegimeType.STABLE}))
        mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        snap = mem.snapshot()
        d = snap.to_dict()
        assert set(d.keys()) == {"states", "transitions", "tick"}

    def test_transition_previous_duration_zero_on_first_tick(self):
        mem = RegimeMemory(signals=("urgency",))
        result = mem.update(_make_snapshot({"urgency": RegimeType.SPIKE_UP}))
        t = result.transitions[0]
        assert t.previous_duration == 0

    def test_regime_memory_snapshot_to_dict_sorted(self):
        states = {
            "z": RegimeState(signal_name="z"),
            "a": RegimeState(signal_name="a"),
            "m": RegimeState(signal_name="m"),
        }
        snap = RegimeMemorySnapshot(states=states, transitions=[], tick=0)
        d = snap.to_dict()
        keys = list(d["states"].keys())
        assert keys == sorted(keys)
