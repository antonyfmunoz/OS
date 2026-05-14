"""Phase 49 — Composite State Dynamics Layer v1.

160+ tests covering:
- Direction computation per ordered dimension
- Trend semantic direction
- First update produces neutral dynamics
- Identical state increments persistence
- Changed state increments transition count
- Persistence resets on change
- Dimension deltas
- CompositeStateDynamics properties
- CompositeStateMemory lifecycle
- Snapshot immutability
- Dimensions independence
- Explainability
- Pipeline integration with Phase 42-48
- Serialization
- Edge cases
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.runtime.regime import RegimeType
from umh.runtime.regime_state import (
    CompositeRegimeState,
    ConfidenceLevel,
    NEUTRAL_COMPOSITE,
    RiskLevel,
    StabilityLevel,
    UrgencyLevel,
    build_composite_state,
)
from umh.runtime.regime_dynamics import (
    CompositeDimensionDelta,
    CompositeStateDynamics,
    CompositeStateMemory,
    DimensionDirection,
    compute_confidence_direction,
    compute_dimension_deltas,
    compute_risk_direction,
    compute_stability_direction,
    compute_trend_direction,
    compute_urgency_direction,
)


def _make_state(
    trend=RegimeType.STABLE,
    risk=RiskLevel.LOW,
    urgency=UrgencyLevel.LOW,
    stability=StabilityLevel.HIGH,
    confidence=ConfidenceLevel.HIGH,
    name="s",
) -> CompositeRegimeState:
    return CompositeRegimeState(
        signal_name=name,
        trend=trend,
        risk=risk,
        urgency=urgency,
        stability=stability,
        confidence=confidence,
    )


# ── Section 1: Risk direction ───────────────────────────────────────


class TestRiskDirection:
    def test_low_to_high_increasing(self):
        assert (
            compute_risk_direction(RiskLevel.LOW, RiskLevel.HIGH) == DimensionDirection.INCREASING
        )

    def test_high_to_low_decreasing(self):
        assert (
            compute_risk_direction(RiskLevel.HIGH, RiskLevel.LOW) == DimensionDirection.DECREASING
        )

    def test_low_to_medium_increasing(self):
        assert (
            compute_risk_direction(RiskLevel.LOW, RiskLevel.MEDIUM) == DimensionDirection.INCREASING
        )

    def test_medium_to_low_decreasing(self):
        assert (
            compute_risk_direction(RiskLevel.MEDIUM, RiskLevel.LOW) == DimensionDirection.DECREASING
        )

    def test_medium_to_high_increasing(self):
        assert (
            compute_risk_direction(RiskLevel.MEDIUM, RiskLevel.HIGH)
            == DimensionDirection.INCREASING
        )

    def test_high_to_medium_decreasing(self):
        assert (
            compute_risk_direction(RiskLevel.HIGH, RiskLevel.MEDIUM)
            == DimensionDirection.DECREASING
        )

    def test_same_low_flat(self):
        assert compute_risk_direction(RiskLevel.LOW, RiskLevel.LOW) == DimensionDirection.FLAT

    def test_same_medium_flat(self):
        assert compute_risk_direction(RiskLevel.MEDIUM, RiskLevel.MEDIUM) == DimensionDirection.FLAT

    def test_same_high_flat(self):
        assert compute_risk_direction(RiskLevel.HIGH, RiskLevel.HIGH) == DimensionDirection.FLAT


# ── Section 2: Urgency direction ────────────────────────────────────


class TestUrgencyDirection:
    def test_low_to_high_increasing(self):
        assert (
            compute_urgency_direction(UrgencyLevel.LOW, UrgencyLevel.HIGH)
            == DimensionDirection.INCREASING
        )

    def test_high_to_low_decreasing(self):
        assert (
            compute_urgency_direction(UrgencyLevel.HIGH, UrgencyLevel.LOW)
            == DimensionDirection.DECREASING
        )

    def test_medium_to_medium_flat(self):
        assert (
            compute_urgency_direction(UrgencyLevel.MEDIUM, UrgencyLevel.MEDIUM)
            == DimensionDirection.FLAT
        )

    def test_low_to_medium_increasing(self):
        assert (
            compute_urgency_direction(UrgencyLevel.LOW, UrgencyLevel.MEDIUM)
            == DimensionDirection.INCREASING
        )

    def test_high_to_medium_decreasing(self):
        assert (
            compute_urgency_direction(UrgencyLevel.HIGH, UrgencyLevel.MEDIUM)
            == DimensionDirection.DECREASING
        )


# ── Section 3: Stability direction ──────────────────────────────────


class TestStabilityDirection:
    def test_low_to_high_increasing(self):
        assert (
            compute_stability_direction(StabilityLevel.LOW, StabilityLevel.HIGH)
            == DimensionDirection.INCREASING
        )

    def test_high_to_low_decreasing(self):
        assert (
            compute_stability_direction(StabilityLevel.HIGH, StabilityLevel.LOW)
            == DimensionDirection.DECREASING
        )

    def test_medium_to_medium_flat(self):
        assert (
            compute_stability_direction(StabilityLevel.MEDIUM, StabilityLevel.MEDIUM)
            == DimensionDirection.FLAT
        )

    def test_low_to_medium_increasing(self):
        assert (
            compute_stability_direction(StabilityLevel.LOW, StabilityLevel.MEDIUM)
            == DimensionDirection.INCREASING
        )


# ── Section 4: Confidence direction ─────────────────────────────────


class TestConfidenceDirection:
    def test_low_to_high_increasing(self):
        assert (
            compute_confidence_direction(ConfidenceLevel.LOW, ConfidenceLevel.HIGH)
            == DimensionDirection.INCREASING
        )

    def test_high_to_low_decreasing(self):
        assert (
            compute_confidence_direction(ConfidenceLevel.HIGH, ConfidenceLevel.LOW)
            == DimensionDirection.DECREASING
        )

    def test_medium_to_medium_flat(self):
        assert (
            compute_confidence_direction(ConfidenceLevel.MEDIUM, ConfidenceLevel.MEDIUM)
            == DimensionDirection.FLAT
        )

    def test_low_to_medium_increasing(self):
        assert (
            compute_confidence_direction(ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM)
            == DimensionDirection.INCREASING
        )


# ── Section 5: Trend semantic direction ─────────────────────────────


class TestTrendDirection:
    def test_stable_to_trend_up_increasing(self):
        assert (
            compute_trend_direction(RegimeType.STABLE, RegimeType.TREND_UP)
            == DimensionDirection.INCREASING
        )

    def test_stable_to_spike_up_increasing(self):
        assert (
            compute_trend_direction(RegimeType.STABLE, RegimeType.SPIKE_UP)
            == DimensionDirection.INCREASING
        )

    def test_stable_to_trend_down_decreasing(self):
        assert (
            compute_trend_direction(RegimeType.STABLE, RegimeType.TREND_DOWN)
            == DimensionDirection.DECREASING
        )

    def test_stable_to_spike_down_decreasing(self):
        assert (
            compute_trend_direction(RegimeType.STABLE, RegimeType.SPIKE_DOWN)
            == DimensionDirection.DECREASING
        )

    def test_trend_up_to_spike_up_increasing(self):
        assert (
            compute_trend_direction(RegimeType.TREND_UP, RegimeType.SPIKE_UP)
            == DimensionDirection.INCREASING
        )

    def test_spike_up_to_trend_up_decreasing(self):
        assert (
            compute_trend_direction(RegimeType.SPIKE_UP, RegimeType.TREND_UP)
            == DimensionDirection.DECREASING
        )

    def test_trend_down_to_spike_down_decreasing(self):
        assert (
            compute_trend_direction(RegimeType.TREND_DOWN, RegimeType.SPIKE_DOWN)
            == DimensionDirection.DECREASING
        )

    def test_spike_down_to_trend_down_increasing(self):
        assert (
            compute_trend_direction(RegimeType.SPIKE_DOWN, RegimeType.TREND_DOWN)
            == DimensionDirection.INCREASING
        )

    def test_same_stable_flat(self):
        assert (
            compute_trend_direction(RegimeType.STABLE, RegimeType.STABLE) == DimensionDirection.FLAT
        )

    def test_same_spike_up_flat(self):
        assert (
            compute_trend_direction(RegimeType.SPIKE_UP, RegimeType.SPIKE_UP)
            == DimensionDirection.FLAT
        )

    def test_spike_up_to_spike_down_decreasing(self):
        assert (
            compute_trend_direction(RegimeType.SPIKE_UP, RegimeType.SPIKE_DOWN)
            == DimensionDirection.DECREASING
        )

    def test_spike_down_to_spike_up_increasing(self):
        assert (
            compute_trend_direction(RegimeType.SPIKE_DOWN, RegimeType.SPIKE_UP)
            == DimensionDirection.INCREASING
        )

    def test_trend_up_to_trend_down_decreasing(self):
        assert (
            compute_trend_direction(RegimeType.TREND_UP, RegimeType.TREND_DOWN)
            == DimensionDirection.DECREASING
        )

    def test_trend_down_to_trend_up_increasing(self):
        assert (
            compute_trend_direction(RegimeType.TREND_DOWN, RegimeType.TREND_UP)
            == DimensionDirection.INCREASING
        )


# ── Section 6: DimensionDirection enum values ───────────────────────


class TestDimensionDirectionEnum:
    def test_increasing(self):
        assert DimensionDirection.INCREASING.value == "increasing"

    def test_decreasing(self):
        assert DimensionDirection.DECREASING.value == "decreasing"

    def test_flat(self):
        assert DimensionDirection.FLAT.value == "flat"

    def test_changed(self):
        assert DimensionDirection.CHANGED.value == "changed"

    def test_unknown(self):
        assert DimensionDirection.UNKNOWN.value == "unknown"


# ── Section 7: compute_dimension_deltas ─────────────────────────────


class TestDimensionDeltas:
    def test_same_state_all_flat(self):
        state = _make_state()
        deltas = compute_dimension_deltas(state, state)
        assert len(deltas) == 5
        assert all(d.direction == DimensionDirection.FLAT for d in deltas)

    def test_five_dimensions_returned(self):
        state = _make_state()
        deltas = compute_dimension_deltas(state, state)
        names = [d.dimension_name for d in deltas]
        assert names == ["trend", "risk", "urgency", "stability", "confidence"]

    def test_risk_change_detected(self):
        prev = _make_state(risk=RiskLevel.LOW)
        curr = _make_state(risk=RiskLevel.HIGH)
        deltas = compute_dimension_deltas(prev, curr)
        risk_d = [d for d in deltas if d.dimension_name == "risk"][0]
        assert risk_d.changed is True
        assert risk_d.direction == DimensionDirection.INCREASING

    def test_trend_change_detected(self):
        prev = _make_state(trend=RegimeType.STABLE)
        curr = _make_state(trend=RegimeType.SPIKE_UP)
        deltas = compute_dimension_deltas(prev, curr)
        trend_d = [d for d in deltas if d.dimension_name == "trend"][0]
        assert trend_d.changed is True
        assert trend_d.direction == DimensionDirection.INCREASING

    def test_unchanged_dimension_not_changed(self):
        prev = _make_state(risk=RiskLevel.LOW)
        curr = _make_state(risk=RiskLevel.HIGH)
        deltas = compute_dimension_deltas(prev, curr)
        urgency_d = [d for d in deltas if d.dimension_name == "urgency"][0]
        assert urgency_d.changed is False

    def test_all_dimensions_changed(self):
        prev = _make_state(
            trend=RegimeType.STABLE,
            risk=RiskLevel.LOW,
            urgency=UrgencyLevel.LOW,
            stability=StabilityLevel.HIGH,
            confidence=ConfidenceLevel.HIGH,
        )
        curr = _make_state(
            trend=RegimeType.SPIKE_UP,
            risk=RiskLevel.HIGH,
            urgency=UrgencyLevel.HIGH,
            stability=StabilityLevel.LOW,
            confidence=ConfidenceLevel.LOW,
        )
        deltas = compute_dimension_deltas(prev, curr)
        assert all(d.changed for d in deltas)


# ── Section 8: CompositeDimensionDelta ──────────────────────────────


class TestDimensionDelta:
    def test_to_dict(self):
        prev = _make_state(risk=RiskLevel.LOW)
        curr = _make_state(risk=RiskLevel.HIGH)
        deltas = compute_dimension_deltas(prev, curr)
        risk_d = [d for d in deltas if d.dimension_name == "risk"][0]
        d = risk_d.to_dict()
        assert set(d.keys()) == {
            "dimension_name",
            "previous_value",
            "current_value",
            "direction",
            "changed",
            "explanation",
        }
        assert d["previous_value"] == "low"
        assert d["current_value"] == "high"
        assert d["direction"] == "increasing"
        assert d["changed"] is True

    def test_explanation_changed(self):
        prev = _make_state(risk=RiskLevel.LOW)
        curr = _make_state(risk=RiskLevel.HIGH)
        deltas = compute_dimension_deltas(prev, curr)
        risk_d = [d for d in deltas if d.dimension_name == "risk"][0]
        assert "low→high" in risk_d.explanation
        assert "increasing" in risk_d.explanation

    def test_explanation_flat(self):
        state = _make_state()
        deltas = compute_dimension_deltas(state, state)
        risk_d = [d for d in deltas if d.dimension_name == "risk"][0]
        assert "flat" in risk_d.explanation

    def test_frozen(self):
        state = _make_state()
        deltas = compute_dimension_deltas(state, state)
        with pytest.raises(AttributeError):
            deltas[0].changed = True


# ── Section 9: First update — neutral dynamics ─────────────────────


class TestFirstUpdate:
    def test_first_update_is_first(self):
        mem = CompositeStateMemory()
        state = _make_state()
        dyn = mem.update(state)
        assert dyn.is_first_update is True

    def test_first_update_persistence_one(self):
        mem = CompositeStateMemory()
        state = _make_state()
        dyn = mem.update(state)
        assert dyn.persistence_duration == 1

    def test_first_update_transitions_zero(self):
        mem = CompositeStateMemory()
        state = _make_state()
        dyn = mem.update(state)
        assert dyn.transition_count == 0

    def test_first_update_all_flat(self):
        mem = CompositeStateMemory()
        state = _make_state()
        dyn = mem.update(state)
        assert dyn.all_flat is True

    def test_first_update_no_changed(self):
        mem = CompositeStateMemory()
        state = _make_state()
        dyn = mem.update(state)
        assert dyn.changed_dimensions == []

    def test_first_update_previous_equals_current(self):
        mem = CompositeStateMemory()
        state = _make_state()
        dyn = mem.update(state)
        assert dyn.previous_state == dyn.current_state


# ── Section 10: Identical state increments persistence ─────────────


class TestPersistence:
    def test_persistence_increments(self):
        mem = CompositeStateMemory()
        state = _make_state()
        mem.update(state)
        dyn = mem.update(state)
        assert dyn.persistence_duration == 2

    def test_persistence_10_ticks(self):
        mem = CompositeStateMemory()
        state = _make_state()
        for _ in range(10):
            dyn = mem.update(state)
        assert dyn.persistence_duration == 10

    def test_persistence_no_transitions(self):
        mem = CompositeStateMemory()
        state = _make_state()
        for _ in range(5):
            dyn = mem.update(state)
        assert dyn.transition_count == 0

    def test_persistence_all_flat(self):
        mem = CompositeStateMemory()
        state = _make_state()
        mem.update(state)
        dyn = mem.update(state)
        assert dyn.all_flat is True


# ── Section 11: Changed state increments transition ────────────────


class TestTransitionCount:
    def test_first_change_increments(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH)
        mem.update(s1)
        dyn = mem.update(s2)
        assert dyn.transition_count == 1

    def test_multiple_changes(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH)
        s3 = _make_state(risk=RiskLevel.MEDIUM)
        mem.update(s1)
        mem.update(s2)
        dyn = mem.update(s3)
        assert dyn.transition_count == 2

    def test_change_resets_persistence(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH)
        mem.update(s1)
        mem.update(s1)
        mem.update(s1)
        dyn = mem.update(s2)
        assert dyn.persistence_duration == 1

    def test_back_and_forth_counts_each(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH)
        mem.update(s1)
        mem.update(s2)
        mem.update(s1)
        dyn = mem.update(s2)
        assert dyn.transition_count == 3

    def test_change_any_dimension_counts(self):
        mem = CompositeStateMemory()
        s1 = _make_state()
        s2 = _make_state(confidence=ConfidenceLevel.LOW)
        mem.update(s1)
        dyn = mem.update(s2)
        assert dyn.transition_count == 1


# ── Section 12: CompositeStateDynamics properties ──────────────────


class TestDynamicsProperties:
    def test_changed_dimensions_list(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW, urgency=UrgencyLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH, urgency=UrgencyLevel.HIGH)
        mem.update(s1)
        dyn = mem.update(s2)
        assert "risk" in dyn.changed_dimensions
        assert "urgency" in dyn.changed_dimensions
        assert "trend" not in dyn.changed_dimensions

    def test_any_changed_true(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH)
        mem.update(s1)
        dyn = mem.update(s2)
        assert dyn.any_changed is True

    def test_any_changed_false(self):
        mem = CompositeStateMemory()
        state = _make_state()
        mem.update(state)
        dyn = mem.update(state)
        assert dyn.any_changed is False

    def test_get_delta_by_name(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH)
        mem.update(s1)
        dyn = mem.update(s2)
        d = dyn.get_delta("risk")
        assert d is not None
        assert d.direction == DimensionDirection.INCREASING

    def test_get_delta_missing(self):
        mem = CompositeStateMemory()
        state = _make_state()
        dyn = mem.update(state)
        assert dyn.get_delta("nonexistent") is None


# ── Section 13: Explainability ─────────────────────────────────────


class TestExplainability:
    def test_unchanged_explanation(self):
        mem = CompositeStateMemory()
        state = _make_state()
        mem.update(state)
        dyn = mem.update(state)
        assert "unchanged" in dyn.explanation
        assert "persistence=2" in dyn.explanation

    def test_changed_explanation(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH)
        mem.update(s1)
        dyn = mem.update(s2)
        assert "changed" in dyn.explanation.lower()
        assert "risk" in dyn.explanation

    def test_multiple_changed_in_explanation(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW, urgency=UrgencyLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH, urgency=UrgencyLevel.HIGH)
        mem.update(s1)
        dyn = mem.update(s2)
        assert "risk" in dyn.explanation
        assert "urgency" in dyn.explanation

    def test_explanation_contains_direction(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH)
        mem.update(s1)
        dyn = mem.update(s2)
        assert "increasing" in dyn.explanation


# ── Section 14: Snapshot immutability (invariant 182) ──────────────


class TestSnapshotImmutability:
    def test_dynamics_frozen(self):
        mem = CompositeStateMemory()
        state = _make_state()
        dyn = mem.update(state)
        with pytest.raises(AttributeError):
            dyn.transition_count = 99

    def test_input_state_not_mutated(self):
        state = _make_state(risk=RiskLevel.LOW)
        before = state.to_dict()
        mem = CompositeStateMemory()
        mem.update(state)
        mem.update(_make_state(risk=RiskLevel.HIGH))
        after = state.to_dict()
        assert before == after

    def test_dimension_delta_frozen(self):
        state = _make_state()
        deltas = compute_dimension_deltas(state, state)
        with pytest.raises(AttributeError):
            deltas[0].direction = DimensionDirection.INCREASING


# ── Section 15: Dimensions independent (invariant 184) ─────────────


class TestDimensionIndependence:
    def test_risk_change_only_affects_risk(self):
        prev = _make_state(risk=RiskLevel.LOW)
        curr = _make_state(risk=RiskLevel.HIGH)
        deltas = compute_dimension_deltas(prev, curr)
        non_risk = [d for d in deltas if d.dimension_name != "risk"]
        assert all(d.changed is False for d in non_risk)
        assert all(d.direction == DimensionDirection.FLAT for d in non_risk)

    def test_urgency_change_only_affects_urgency(self):
        prev = _make_state(urgency=UrgencyLevel.LOW)
        curr = _make_state(urgency=UrgencyLevel.HIGH)
        deltas = compute_dimension_deltas(prev, curr)
        non_urgency = [d for d in deltas if d.dimension_name != "urgency"]
        assert all(d.changed is False for d in non_urgency)

    def test_trend_change_only_affects_trend(self):
        prev = _make_state(trend=RegimeType.STABLE)
        curr = _make_state(trend=RegimeType.SPIKE_UP)
        deltas = compute_dimension_deltas(prev, curr)
        non_trend = [d for d in deltas if d.dimension_name != "trend"]
        assert all(d.changed is False for d in non_trend)


# ── Section 16: CompositeStateMemory lifecycle ─────────────────────


class TestMemoryLifecycle:
    def test_initial_state_none(self):
        mem = CompositeStateMemory()
        assert mem.current_state is None
        assert mem.previous_state is None

    def test_after_first_update(self):
        mem = CompositeStateMemory()
        state = _make_state()
        mem.update(state)
        assert mem.current_state is not None
        assert mem.previous_state is not None

    def test_tick_increments(self):
        mem = CompositeStateMemory()
        assert mem.tick == 0
        mem.update(_make_state())
        assert mem.tick == 1
        mem.update(_make_state())
        assert mem.tick == 2

    def test_reset(self):
        mem = CompositeStateMemory()
        mem.update(_make_state())
        mem.update(_make_state())
        mem.reset()
        assert mem.tick == 0
        assert mem.transition_count == 0
        assert mem.persistence_duration == 0
        assert mem.current_state is None

    def test_to_dict_empty(self):
        mem = CompositeStateMemory()
        d = mem.to_dict()
        assert d["tick"] == 0
        assert d["current_state"] is None

    def test_to_dict_populated(self):
        mem = CompositeStateMemory()
        mem.update(_make_state())
        d = mem.to_dict()
        assert d["tick"] == 1
        assert d["current_state"] is not None

    def test_previous_state_tracks(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH)
        mem.update(s1)
        mem.update(s2)
        assert mem.previous_state.risk == RiskLevel.LOW
        assert mem.current_state.risk == RiskLevel.HIGH


# ── Section 17: Determinism (invariant 181) ────────────────────────


class TestDeterminism:
    def test_same_sequence_same_result(self):
        def run_sequence():
            mem = CompositeStateMemory()
            s1 = _make_state(risk=RiskLevel.LOW)
            s2 = _make_state(risk=RiskLevel.HIGH)
            mem.update(s1)
            return mem.update(s2)

        d1 = run_sequence()
        d2 = run_sequence()
        assert d1.transition_count == d2.transition_count
        assert d1.persistence_duration == d2.persistence_duration
        assert d1.any_changed == d2.any_changed
        assert d1.changed_dimensions == d2.changed_dimensions

    def test_direction_deterministic(self):
        for _ in range(50):
            assert (
                compute_risk_direction(RiskLevel.LOW, RiskLevel.HIGH)
                == DimensionDirection.INCREASING
            )

    def test_deltas_deterministic(self):
        prev = _make_state(risk=RiskLevel.LOW)
        curr = _make_state(risk=RiskLevel.HIGH)
        d1 = compute_dimension_deltas(prev, curr)
        d2 = compute_dimension_deltas(prev, curr)
        for a, b in zip(d1, d2):
            assert a.direction == b.direction
            assert a.changed == b.changed


# ── Section 18: Missing previous state (invariant 183) ─────────────


class TestMissingPreviousState:
    def test_first_update_safe(self):
        mem = CompositeStateMemory()
        state = _make_state()
        dyn = mem.update(state)
        assert dyn.is_first_update is True
        assert dyn.persistence_duration == 1
        assert dyn.transition_count == 0

    def test_no_crash_on_first_update(self):
        mem = CompositeStateMemory()
        for rt in RegimeType:
            for rl in RiskLevel:
                s = _make_state(trend=rt, risk=rl)
                mem2 = CompositeStateMemory()
                dyn = mem2.update(s)
                assert dyn.is_first_update is True


# ── Section 19: Dynamics does not mutate planning (invariant 185) ──


class TestNoExecutionMutation:
    def test_dynamics_is_observational(self):
        mem = CompositeStateMemory()
        s1 = _make_state()
        s2 = _make_state(risk=RiskLevel.HIGH)
        dyn1 = mem.update(s1)
        dyn2 = mem.update(s2)
        assert isinstance(dyn1, CompositeStateDynamics)
        assert isinstance(dyn2, CompositeStateDynamics)


# ── Section 20: Serialization ──────────────────────────────────────


class TestSerialization:
    def test_dynamics_to_dict(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH)
        mem.update(s1)
        dyn = mem.update(s2)
        d = dyn.to_dict()
        assert "previous_state" in d
        assert "current_state" in d
        assert "dimension_deltas" in d
        assert "transition_count" in d
        assert "persistence_duration" in d
        assert "changed_dimensions" in d
        assert "is_first_update" in d
        assert "explanation" in d

    def test_dimension_delta_to_dict(self):
        state = _make_state()
        deltas = compute_dimension_deltas(state, state)
        d = deltas[0].to_dict()
        assert set(d.keys()) == {
            "dimension_name",
            "previous_value",
            "current_value",
            "direction",
            "changed",
            "explanation",
        }


# ── Section 21: Pipeline integration with Phase 42-48 ─────────────


class TestPipelineIntegration:
    def test_build_composite_then_dynamics(self):
        s1 = build_composite_state("urgency", RegimeType.STABLE, 0.01, 0.01, 20)
        s2 = build_composite_state("urgency", RegimeType.SPIKE_UP, 0.30, 0.20, 1)
        mem = CompositeStateMemory()
        mem.update(s1)
        dyn = mem.update(s2)
        assert dyn.any_changed is True
        assert "trend" in dyn.changed_dimensions
        assert "risk" in dyn.changed_dimensions

    def test_classify_then_composite_then_dynamics(self):
        from umh.runtime.regime import classify_regime, RegimeThresholds

        r1 = classify_regime("urgency", 0.05, RegimeThresholds())
        r2 = classify_regime("urgency", 0.30, RegimeThresholds())

        s1 = build_composite_state("urgency", r1.regime, r1.magnitude, 0.01, 10)
        s2 = build_composite_state("urgency", r2.regime, r2.magnitude, 0.20, 1)

        mem = CompositeStateMemory()
        mem.update(s1)
        dyn = mem.update(s2)
        assert dyn.get_delta("trend").direction == DimensionDirection.INCREASING

    def test_filter_then_dynamics(self):
        from umh.runtime.regime_filter import FilterState, filter_regime

        fs = FilterState(signal_name="urgency", confirmed_regime=RegimeType.STABLE)
        fr = filter_regime(fs, RegimeType.SPIKE_UP, 1)

        s1 = build_composite_state("urgency", RegimeType.STABLE, 0.01, 0.01, 20)
        s2 = build_composite_state("urgency", fr.filtered_regime, 0.30, 0.20, 0)

        mem = CompositeStateMemory()
        mem.update(s1)
        dyn = mem.update(s2)
        assert dyn.any_changed is True

    def test_composite_match_uses_dynamics_current(self):
        from umh.runtime.regime_state import COMPOSITE_AGGRESSIVE, compute_composite_match

        s1 = build_composite_state("urgency", RegimeType.STABLE, 0.01, 0.01, 20)
        s2 = build_composite_state("urgency", RegimeType.SPIKE_UP, 0.30, 0.20, 1)

        mem = CompositeStateMemory()
        mem.update(s1)
        dyn = mem.update(s2)

        r = compute_composite_match(COMPOSITE_AGGRESSIVE, dyn.current_state)
        assert r.factor > 1.0


# ── Section 22: Complex transition sequences ──────────────────────


class TestComplexSequences:
    def test_oscillation_counts_transitions(self):
        mem = CompositeStateMemory()
        low = _make_state(risk=RiskLevel.LOW)
        high = _make_state(risk=RiskLevel.HIGH)
        mem.update(low)
        for i in range(5):
            mem.update(high if i % 2 == 0 else low)
        assert mem.transition_count == 5

    def test_gradual_increase(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW, urgency=UrgencyLevel.LOW)
        s2 = _make_state(risk=RiskLevel.MEDIUM, urgency=UrgencyLevel.LOW)
        s3 = _make_state(risk=RiskLevel.HIGH, urgency=UrgencyLevel.MEDIUM)
        mem.update(s1)
        d2 = mem.update(s2)
        d3 = mem.update(s3)
        assert d2.get_delta("risk").direction == DimensionDirection.INCREASING
        assert d3.get_delta("risk").direction == DimensionDirection.INCREASING
        assert d3.get_delta("urgency").direction == DimensionDirection.INCREASING

    def test_persistence_after_change(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH)
        mem.update(s1)
        mem.update(s1)
        mem.update(s1)
        mem.update(s2)
        mem.update(s2)
        dyn = mem.update(s2)
        assert dyn.persistence_duration == 3
        assert dyn.transition_count == 1

    def test_single_dimension_change_is_transition(self):
        mem = CompositeStateMemory()
        s1 = _make_state(confidence=ConfidenceLevel.HIGH)
        s2 = _make_state(confidence=ConfidenceLevel.LOW)
        mem.update(s1)
        dyn = mem.update(s2)
        assert dyn.transition_count == 1
        assert "confidence" in dyn.changed_dimensions


# ── Section 23: NEUTRAL_COMPOSITE handling ───────────────────────────


class TestNeutralComposite:
    def test_neutral_first_update(self):
        mem = CompositeStateMemory()
        dyn = mem.update(NEUTRAL_COMPOSITE)
        assert dyn.is_first_update is True
        assert dyn.all_flat is True

    def test_neutral_to_neutral_persistence(self):
        mem = CompositeStateMemory()
        mem.update(NEUTRAL_COMPOSITE)
        dyn = mem.update(NEUTRAL_COMPOSITE)
        assert dyn.persistence_duration == 2
        assert dyn.transition_count == 0

    def test_neutral_to_aggressive(self):
        mem = CompositeStateMemory()
        mem.update(NEUTRAL_COMPOSITE)
        aggressive = _make_state(
            trend=RegimeType.SPIKE_UP,
            risk=RiskLevel.HIGH,
            urgency=UrgencyLevel.HIGH,
            stability=StabilityLevel.LOW,
            confidence=ConfidenceLevel.LOW,
        )
        dyn = mem.update(aggressive)
        assert dyn.transition_count == 1
        assert dyn.any_changed is True
        assert len(dyn.changed_dimensions) >= 3

    def test_aggressive_to_neutral(self):
        mem = CompositeStateMemory()
        aggressive = _make_state(
            trend=RegimeType.SPIKE_UP,
            risk=RiskLevel.HIGH,
            urgency=UrgencyLevel.HIGH,
            stability=StabilityLevel.LOW,
            confidence=ConfidenceLevel.LOW,
        )
        mem.update(aggressive)
        dyn = mem.update(NEUTRAL_COMPOSITE)
        assert dyn.transition_count == 1
        assert dyn.get_delta("trend").direction == DimensionDirection.DECREASING


# ── Section 24: Reset and re-use ─────────────────────────────────────


class TestResetReuse:
    def test_reset_then_reuse(self):
        mem = CompositeStateMemory()
        mem.update(_make_state(risk=RiskLevel.LOW))
        mem.update(_make_state(risk=RiskLevel.HIGH))
        mem.reset()
        dyn = mem.update(_make_state(risk=RiskLevel.MEDIUM))
        assert dyn.is_first_update is True
        assert dyn.transition_count == 0
        assert dyn.persistence_duration == 1

    def test_reset_clears_everything(self):
        mem = CompositeStateMemory()
        for _ in range(10):
            mem.update(_make_state())
        mem.reset()
        assert mem.tick == 0
        assert mem.transition_count == 0
        assert mem.persistence_duration == 0
        assert mem.current_state is None
        assert mem.previous_state is None

    def test_reset_mid_sequence(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH)
        mem.update(s1)
        mem.update(s2)
        mem.update(s2)
        mem.reset()
        dyn = mem.update(s1)
        assert dyn.is_first_update is True
        assert mem.tick == 1


# ── Section 25: All trend pair transitions ───────────────────────────


class TestAllTrendPairs:
    def test_spike_down_to_stable(self):
        assert (
            compute_trend_direction(RegimeType.SPIKE_DOWN, RegimeType.STABLE)
            == DimensionDirection.INCREASING
        )

    def test_stable_to_stable(self):
        assert (
            compute_trend_direction(RegimeType.STABLE, RegimeType.STABLE) == DimensionDirection.FLAT
        )

    def test_trend_down_to_stable(self):
        assert (
            compute_trend_direction(RegimeType.TREND_DOWN, RegimeType.STABLE)
            == DimensionDirection.INCREASING
        )

    def test_stable_to_trend_down(self):
        assert (
            compute_trend_direction(RegimeType.STABLE, RegimeType.TREND_DOWN)
            == DimensionDirection.DECREASING
        )

    def test_spike_down_to_trend_up(self):
        assert (
            compute_trend_direction(RegimeType.SPIKE_DOWN, RegimeType.TREND_UP)
            == DimensionDirection.INCREASING
        )

    def test_trend_up_to_stable(self):
        assert (
            compute_trend_direction(RegimeType.TREND_UP, RegimeType.STABLE)
            == DimensionDirection.DECREASING
        )

    def test_spike_down_to_spike_down(self):
        assert (
            compute_trend_direction(RegimeType.SPIKE_DOWN, RegimeType.SPIKE_DOWN)
            == DimensionDirection.FLAT
        )

    def test_trend_down_to_trend_down(self):
        assert (
            compute_trend_direction(RegimeType.TREND_DOWN, RegimeType.TREND_DOWN)
            == DimensionDirection.FLAT
        )

    def test_trend_up_to_trend_up(self):
        assert (
            compute_trend_direction(RegimeType.TREND_UP, RegimeType.TREND_UP)
            == DimensionDirection.FLAT
        )


# ── Section 26: Stability and confidence full matrix ─────────────────


class TestStabilityFullMatrix:
    def test_medium_to_high(self):
        assert (
            compute_stability_direction(StabilityLevel.MEDIUM, StabilityLevel.HIGH)
            == DimensionDirection.INCREASING
        )

    def test_high_to_medium(self):
        assert (
            compute_stability_direction(StabilityLevel.HIGH, StabilityLevel.MEDIUM)
            == DimensionDirection.DECREASING
        )

    def test_low_to_low(self):
        assert (
            compute_stability_direction(StabilityLevel.LOW, StabilityLevel.LOW)
            == DimensionDirection.FLAT
        )

    def test_high_to_high(self):
        assert (
            compute_stability_direction(StabilityLevel.HIGH, StabilityLevel.HIGH)
            == DimensionDirection.FLAT
        )


class TestConfidenceFullMatrix:
    def test_medium_to_high(self):
        assert (
            compute_confidence_direction(ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH)
            == DimensionDirection.INCREASING
        )

    def test_high_to_medium(self):
        assert (
            compute_confidence_direction(ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
            == DimensionDirection.DECREASING
        )

    def test_medium_to_low(self):
        assert (
            compute_confidence_direction(ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW)
            == DimensionDirection.DECREASING
        )

    def test_low_to_low(self):
        assert (
            compute_confidence_direction(ConfidenceLevel.LOW, ConfidenceLevel.LOW)
            == DimensionDirection.FLAT
        )

    def test_high_to_high(self):
        assert (
            compute_confidence_direction(ConfidenceLevel.HIGH, ConfidenceLevel.HIGH)
            == DimensionDirection.FLAT
        )


# ── Section 27: Multi-dimension deltas ───────────────────────────────


class TestMultiDimensionDeltas:
    def test_three_dimensions_change(self):
        prev = _make_state(
            risk=RiskLevel.LOW,
            urgency=UrgencyLevel.LOW,
            stability=StabilityLevel.HIGH,
        )
        curr = _make_state(
            risk=RiskLevel.HIGH,
            urgency=UrgencyLevel.HIGH,
            stability=StabilityLevel.LOW,
        )
        deltas = compute_dimension_deltas(prev, curr)
        changed = [d for d in deltas if d.changed]
        assert len(changed) == 3
        risk_d = [d for d in deltas if d.dimension_name == "risk"][0]
        assert risk_d.direction == DimensionDirection.INCREASING
        stability_d = [d for d in deltas if d.dimension_name == "stability"][0]
        assert stability_d.direction == DimensionDirection.DECREASING

    def test_opposing_directions(self):
        prev = _make_state(risk=RiskLevel.HIGH, urgency=UrgencyLevel.LOW)
        curr = _make_state(risk=RiskLevel.LOW, urgency=UrgencyLevel.HIGH)
        deltas = compute_dimension_deltas(prev, curr)
        risk_d = [d for d in deltas if d.dimension_name == "risk"][0]
        urg_d = [d for d in deltas if d.dimension_name == "urgency"][0]
        assert risk_d.direction == DimensionDirection.DECREASING
        assert urg_d.direction == DimensionDirection.INCREASING

    def test_all_five_change(self):
        prev = _make_state(
            trend=RegimeType.SPIKE_DOWN,
            risk=RiskLevel.HIGH,
            urgency=UrgencyLevel.HIGH,
            stability=StabilityLevel.LOW,
            confidence=ConfidenceLevel.LOW,
        )
        curr = _make_state(
            trend=RegimeType.SPIKE_UP,
            risk=RiskLevel.LOW,
            urgency=UrgencyLevel.LOW,
            stability=StabilityLevel.HIGH,
            confidence=ConfidenceLevel.HIGH,
        )
        deltas = compute_dimension_deltas(prev, curr)
        assert all(d.changed for d in deltas)
        trend_d = [d for d in deltas if d.dimension_name == "trend"][0]
        assert trend_d.direction == DimensionDirection.INCREASING
        risk_d = [d for d in deltas if d.dimension_name == "risk"][0]
        assert risk_d.direction == DimensionDirection.DECREASING

    def test_only_confidence_changes(self):
        prev = _make_state(confidence=ConfidenceLevel.HIGH)
        curr = _make_state(confidence=ConfidenceLevel.LOW)
        deltas = compute_dimension_deltas(prev, curr)
        conf_d = [d for d in deltas if d.dimension_name == "confidence"][0]
        assert conf_d.changed is True
        assert conf_d.direction == DimensionDirection.DECREASING
        others = [d for d in deltas if d.dimension_name != "confidence"]
        assert all(not d.changed for d in others)


# ── Section 28: Long sequences ───────────────────────────────────────


class TestLongSequences:
    def test_50_tick_persistence(self):
        mem = CompositeStateMemory()
        state = _make_state()
        for _ in range(50):
            dyn = mem.update(state)
        assert dyn.persistence_duration == 50
        assert dyn.transition_count == 0
        assert mem.tick == 50

    def test_alternating_50_transitions(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH)
        mem.update(s1)
        for i in range(50):
            mem.update(s2 if i % 2 == 0 else s1)
        assert mem.transition_count == 50

    def test_gradual_five_step_escalation(self):
        mem = CompositeStateMemory()
        states = [
            _make_state(trend=RegimeType.SPIKE_DOWN, risk=RiskLevel.LOW),
            _make_state(trend=RegimeType.TREND_DOWN, risk=RiskLevel.LOW),
            _make_state(trend=RegimeType.STABLE, risk=RiskLevel.MEDIUM),
            _make_state(trend=RegimeType.TREND_UP, risk=RiskLevel.MEDIUM),
            _make_state(trend=RegimeType.SPIKE_UP, risk=RiskLevel.HIGH),
        ]
        dyns = []
        for s in states:
            dyns.append(mem.update(s))
        for d in dyns[1:]:
            assert d.get_delta("trend").direction == DimensionDirection.INCREASING
        assert mem.transition_count == 4

    def test_stable_then_spike_then_stable(self):
        mem = CompositeStateMemory()
        stable = _make_state()
        spike = _make_state(trend=RegimeType.SPIKE_UP, risk=RiskLevel.HIGH)
        for _ in range(5):
            mem.update(stable)
        dyn_spike = mem.update(spike)
        assert dyn_spike.transition_count == 1
        assert dyn_spike.persistence_duration == 1
        for _ in range(5):
            dyn = mem.update(stable)
        assert dyn.persistence_duration == 5
        assert mem.transition_count == 2


# ── Section 29: Dynamics to_dict completeness ────────────────────────


class TestDynamicsDictCompleteness:
    def test_first_update_dict(self):
        mem = CompositeStateMemory()
        dyn = mem.update(_make_state())
        d = dyn.to_dict()
        assert d["is_first_update"] is True
        assert d["transition_count"] == 0
        assert d["persistence_duration"] == 1
        assert d["changed_dimensions"] == []
        assert len(d["dimension_deltas"]) == 5

    def test_changed_dict_values(self):
        mem = CompositeStateMemory()
        mem.update(_make_state(risk=RiskLevel.LOW))
        dyn = mem.update(_make_state(risk=RiskLevel.HIGH))
        d = dyn.to_dict()
        assert d["is_first_update"] is False
        assert d["transition_count"] == 1
        assert "risk" in d["changed_dimensions"]
        risk_delta = [dd for dd in d["dimension_deltas"] if dd["dimension_name"] == "risk"][0]
        assert risk_delta["direction"] == "increasing"
        assert risk_delta["changed"] is True

    def test_memory_dict_after_transitions(self):
        mem = CompositeStateMemory()
        s1 = _make_state(risk=RiskLevel.LOW)
        s2 = _make_state(risk=RiskLevel.HIGH)
        mem.update(s1)
        mem.update(s2)
        mem.update(s2)
        d = mem.to_dict()
        assert d["tick"] == 3
        assert d["transition_count"] == 1
        assert d["persistence_duration"] == 2


# ── Section 30: Edge cases — same signal_name different dimensions ───


class TestSignalNameEdgeCases:
    def test_different_signal_names_still_track(self):
        mem = CompositeStateMemory()
        s1 = _make_state(name="alpha", risk=RiskLevel.LOW)
        s2 = _make_state(name="beta", risk=RiskLevel.HIGH)
        mem.update(s1)
        dyn = mem.update(s2)
        assert dyn.any_changed is True

    def test_same_values_different_names_is_change(self):
        mem = CompositeStateMemory()
        s1 = _make_state(name="a")
        s2 = _make_state(name="b")
        mem.update(s1)
        dyn = mem.update(s2)
        # signal_name is not compared in _states_equal — only dimensions
        assert dyn.all_flat is True
        assert dyn.transition_count == 0


# ── Section 31: Dimension delta explanations ─────────────────────────


class TestDeltaExplanations:
    def test_changed_has_arrow(self):
        prev = _make_state(risk=RiskLevel.LOW)
        curr = _make_state(risk=RiskLevel.HIGH)
        deltas = compute_dimension_deltas(prev, curr)
        risk_d = [d for d in deltas if d.dimension_name == "risk"][0]
        assert "→" in risk_d.explanation

    def test_flat_no_arrow(self):
        state = _make_state()
        deltas = compute_dimension_deltas(state, state)
        for d in deltas:
            assert "→" not in d.explanation

    def test_trend_changed_explanation(self):
        prev = _make_state(trend=RegimeType.STABLE)
        curr = _make_state(trend=RegimeType.SPIKE_UP)
        deltas = compute_dimension_deltas(prev, curr)
        trend_d = [d for d in deltas if d.dimension_name == "trend"][0]
        assert "stable→spike_up" in trend_d.explanation
        assert "increasing" in trend_d.explanation

    def test_urgency_medium_to_high(self):
        prev = _make_state(urgency=UrgencyLevel.MEDIUM)
        curr = _make_state(urgency=UrgencyLevel.HIGH)
        deltas = compute_dimension_deltas(prev, curr)
        urg_d = [d for d in deltas if d.dimension_name == "urgency"][0]
        assert "medium→high" in urg_d.explanation

    def test_stability_decreasing_explanation(self):
        prev = _make_state(stability=StabilityLevel.HIGH)
        curr = _make_state(stability=StabilityLevel.LOW)
        deltas = compute_dimension_deltas(prev, curr)
        stab_d = [d for d in deltas if d.dimension_name == "stability"][0]
        assert "decreasing" in stab_d.explanation
        assert "high→low" in stab_d.explanation


# ── Section 32: Dynamics explanation strings ─────────────────────────


class TestDynamicsExplanations:
    def test_no_change_mentions_persistence(self):
        mem = CompositeStateMemory()
        state = _make_state()
        mem.update(state)
        mem.update(state)
        mem.update(state)
        dyn = mem.update(state)
        assert "persistence=4" in dyn.explanation

    def test_change_lists_all_changed(self):
        mem = CompositeStateMemory()
        s1 = _make_state(
            risk=RiskLevel.LOW, urgency=UrgencyLevel.LOW, stability=StabilityLevel.HIGH
        )
        s2 = _make_state(
            risk=RiskLevel.HIGH, urgency=UrgencyLevel.HIGH, stability=StabilityLevel.LOW
        )
        mem.update(s1)
        dyn = mem.update(s2)
        assert "risk" in dyn.explanation
        assert "urgency" in dyn.explanation
        assert "stability" in dyn.explanation

    def test_single_change_explanation(self):
        mem = CompositeStateMemory()
        s1 = _make_state(confidence=ConfidenceLevel.HIGH)
        s2 = _make_state(confidence=ConfidenceLevel.LOW)
        mem.update(s1)
        dyn = mem.update(s2)
        assert "confidence" in dyn.explanation
        assert "trend" not in dyn.explanation


# ── Section 33: Import surface ───────────────────────────────────────


class TestImportSurface:
    def test_all_public_types_importable(self):
        from umh.runtime import (
            CompositeDimensionDelta,
            CompositeStateDynamics,
            CompositeStateMemory,
            DimensionDirection,
            compute_confidence_direction,
            compute_dimension_deltas,
            compute_risk_direction,
            compute_stability_direction,
            compute_trend_direction,
            compute_urgency_direction,
        )

        assert CompositeDimensionDelta is not None
        assert CompositeStateDynamics is not None
        assert CompositeStateMemory is not None
        assert DimensionDirection is not None
        assert compute_confidence_direction is not None
        assert compute_dimension_deltas is not None
        assert compute_risk_direction is not None
        assert compute_stability_direction is not None
        assert compute_trend_direction is not None
        assert compute_urgency_direction is not None


# ── Section 34: Urgency full matrix ──────────────────────────────────


class TestUrgencyFullMatrix:
    def test_medium_to_high(self):
        assert (
            compute_urgency_direction(UrgencyLevel.MEDIUM, UrgencyLevel.HIGH)
            == DimensionDirection.INCREASING
        )

    def test_medium_to_low(self):
        assert (
            compute_urgency_direction(UrgencyLevel.MEDIUM, UrgencyLevel.LOW)
            == DimensionDirection.DECREASING
        )

    def test_low_to_low(self):
        assert (
            compute_urgency_direction(UrgencyLevel.LOW, UrgencyLevel.LOW) == DimensionDirection.FLAT
        )

    def test_high_to_high(self):
        assert (
            compute_urgency_direction(UrgencyLevel.HIGH, UrgencyLevel.HIGH)
            == DimensionDirection.FLAT
        )


# ── Section 35: Risk full matrix ─────────────────────────────────────


class TestRiskFullMatrix:
    def test_medium_to_high(self):
        assert (
            compute_risk_direction(RiskLevel.MEDIUM, RiskLevel.HIGH)
            == DimensionDirection.INCREASING
        )

    def test_medium_to_low(self):
        assert (
            compute_risk_direction(RiskLevel.MEDIUM, RiskLevel.LOW) == DimensionDirection.DECREASING
        )

    def test_low_to_low(self):
        assert compute_risk_direction(RiskLevel.LOW, RiskLevel.LOW) == DimensionDirection.FLAT

    def test_high_to_high(self):
        assert compute_risk_direction(RiskLevel.HIGH, RiskLevel.HIGH) == DimensionDirection.FLAT


# ── Section 36: Memory properties after first update ─────────────────


class TestMemoryPropertiesAfterFirst:
    def test_persistence_property(self):
        mem = CompositeStateMemory()
        mem.update(_make_state())
        assert mem.persistence_duration == 1

    def test_transition_property(self):
        mem = CompositeStateMemory()
        mem.update(_make_state())
        assert mem.transition_count == 0
