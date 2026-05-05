"""Composite state dynamics — temporal evolution of multi-dimensional regime state.

Tracks how composite regime states change over time:
    - per-dimension direction (INCREASING / DECREASING / FLAT / CHANGED / UNKNOWN)
    - transition count (how many times the composite state changed)
    - persistence duration (how many ticks the current state has held)
    - explainable state dynamics

Observational only — does not influence strategy selection or execution.

Stateful memory model (CompositeStateMemory tracks previous/current).
No I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from umh.runtime.regime import RegimeType
from umh.runtime.regime_state import (
    CompositeRegimeState,
    ConfidenceLevel,
    RiskLevel,
    StabilityLevel,
    UrgencyLevel,
)


class DimensionDirection(Enum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    FLAT = "flat"
    CHANGED = "changed"
    UNKNOWN = "unknown"


_ORDERED_RISK = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}
_ORDERED_URGENCY = {UrgencyLevel.LOW: 0, UrgencyLevel.MEDIUM: 1, UrgencyLevel.HIGH: 2}
_ORDERED_STABILITY = {StabilityLevel.LOW: 0, StabilityLevel.MEDIUM: 1, StabilityLevel.HIGH: 2}
_ORDERED_CONFIDENCE = {ConfidenceLevel.LOW: 0, ConfidenceLevel.MEDIUM: 1, ConfidenceLevel.HIGH: 2}

_TREND_SEMANTIC = {
    RegimeType.SPIKE_DOWN: -2,
    RegimeType.TREND_DOWN: -1,
    RegimeType.STABLE: 0,
    RegimeType.TREND_UP: 1,
    RegimeType.SPIKE_UP: 2,
}


def _ordered_direction(prev_ord: int, curr_ord: int) -> DimensionDirection:
    if curr_ord > prev_ord:
        return DimensionDirection.INCREASING
    if curr_ord < prev_ord:
        return DimensionDirection.DECREASING
    return DimensionDirection.FLAT


def compute_trend_direction(prev: RegimeType, curr: RegimeType) -> DimensionDirection:
    if prev == curr:
        return DimensionDirection.FLAT
    prev_s = _TREND_SEMANTIC.get(prev)
    curr_s = _TREND_SEMANTIC.get(curr)
    if prev_s is None or curr_s is None:
        return DimensionDirection.CHANGED
    if curr_s > prev_s:
        return DimensionDirection.INCREASING
    if curr_s < prev_s:
        return DimensionDirection.DECREASING
    return DimensionDirection.CHANGED


def compute_risk_direction(prev: RiskLevel, curr: RiskLevel) -> DimensionDirection:
    return _ordered_direction(_ORDERED_RISK[prev], _ORDERED_RISK[curr])


def compute_urgency_direction(prev: UrgencyLevel, curr: UrgencyLevel) -> DimensionDirection:
    return _ordered_direction(_ORDERED_URGENCY[prev], _ORDERED_URGENCY[curr])


def compute_stability_direction(prev: StabilityLevel, curr: StabilityLevel) -> DimensionDirection:
    return _ordered_direction(_ORDERED_STABILITY[prev], _ORDERED_STABILITY[curr])


def compute_confidence_direction(
    prev: ConfidenceLevel, curr: ConfidenceLevel
) -> DimensionDirection:
    return _ordered_direction(_ORDERED_CONFIDENCE[prev], _ORDERED_CONFIDENCE[curr])


@dataclass(frozen=True)
class CompositeDimensionDelta:
    """Direction result for a single dimension between two states."""

    dimension_name: str
    previous_value: str
    current_value: str
    direction: DimensionDirection
    changed: bool
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_name": self.dimension_name,
            "previous_value": self.previous_value,
            "current_value": self.current_value,
            "direction": self.direction.value,
            "changed": self.changed,
            "explanation": self.explanation,
        }


def _make_delta(
    name: str, prev_val: str, curr_val: str, direction: DimensionDirection
) -> CompositeDimensionDelta:
    changed = prev_val != curr_val
    if changed:
        explanation = f"{name} {prev_val}→{curr_val} {direction.value}"
    else:
        explanation = f"{name} {curr_val} {direction.value}"
    return CompositeDimensionDelta(
        dimension_name=name,
        previous_value=prev_val,
        current_value=curr_val,
        direction=direction,
        changed=changed,
        explanation=explanation,
    )


def compute_dimension_deltas(
    previous: CompositeRegimeState,
    current: CompositeRegimeState,
) -> tuple[CompositeDimensionDelta, ...]:
    """Compute per-dimension deltas between two composite states."""
    return (
        _make_delta(
            "trend",
            previous.trend.value,
            current.trend.value,
            compute_trend_direction(previous.trend, current.trend),
        ),
        _make_delta(
            "risk",
            previous.risk.value,
            current.risk.value,
            compute_risk_direction(previous.risk, current.risk),
        ),
        _make_delta(
            "urgency",
            previous.urgency.value,
            current.urgency.value,
            compute_urgency_direction(previous.urgency, current.urgency),
        ),
        _make_delta(
            "stability",
            previous.stability.value,
            current.stability.value,
            compute_stability_direction(previous.stability, current.stability),
        ),
        _make_delta(
            "confidence",
            previous.confidence.value,
            current.confidence.value,
            compute_confidence_direction(previous.confidence, current.confidence),
        ),
    )


@dataclass(frozen=True)
class CompositeStateDynamics:
    """Temporal dynamics between two composite regime states."""

    previous_state: CompositeRegimeState
    current_state: CompositeRegimeState
    dimension_deltas: tuple[CompositeDimensionDelta, ...]
    transition_count: int
    persistence_duration: int
    is_first_update: bool

    @property
    def changed_dimensions(self) -> list[str]:
        return [d.dimension_name for d in self.dimension_deltas if d.changed]

    @property
    def any_changed(self) -> bool:
        return any(d.changed for d in self.dimension_deltas)

    @property
    def all_flat(self) -> bool:
        return all(d.direction == DimensionDirection.FLAT for d in self.dimension_deltas)

    @property
    def explanation(self) -> str:
        changed = [d for d in self.dimension_deltas if d.changed]
        if not changed:
            return f"Composite state unchanged (persistence={self.persistence_duration})"
        parts = [d.explanation for d in changed]
        return "Composite state changed: " + ", ".join(parts)

    def get_delta(self, dimension_name: str) -> CompositeDimensionDelta | None:
        for d in self.dimension_deltas:
            if d.dimension_name == dimension_name:
                return d
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "previous_state": self.previous_state.to_dict(),
            "current_state": self.current_state.to_dict(),
            "dimension_deltas": [d.to_dict() for d in self.dimension_deltas],
            "transition_count": self.transition_count,
            "persistence_duration": self.persistence_duration,
            "changed_dimensions": self.changed_dimensions,
            "is_first_update": self.is_first_update,
            "explanation": self.explanation,
        }


def _states_equal(a: CompositeRegimeState, b: CompositeRegimeState) -> bool:
    return (
        a.trend == b.trend
        and a.risk == b.risk
        and a.urgency == b.urgency
        and a.stability == b.stability
        and a.confidence == b.confidence
    )


class CompositeStateMemory:
    """Tracks temporal evolution of composite regime states.

    Maintains previous/current state, transition count, and persistence
    duration. Each call to update() produces a CompositeStateDynamics
    snapshot describing the change.
    """

    def __init__(self) -> None:
        self._previous: CompositeRegimeState | None = None
        self._current: CompositeRegimeState | None = None
        self._transition_count: int = 0
        self._persistence_duration: int = 0
        self._tick: int = 0

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def transition_count(self) -> int:
        return self._transition_count

    @property
    def persistence_duration(self) -> int:
        return self._persistence_duration

    @property
    def current_state(self) -> CompositeRegimeState | None:
        return self._current

    @property
    def previous_state(self) -> CompositeRegimeState | None:
        return self._previous

    def update(self, state: CompositeRegimeState) -> CompositeStateDynamics:
        """Update memory with a new composite state and return dynamics.

        First update: previous = current = state, persistence = 1, transitions = 0.
        Same state: persistence += 1.
        Changed state: transition_count += 1, persistence = 1.
        """
        self._tick += 1

        if self._current is None:
            self._previous = state
            self._current = state
            self._persistence_duration = 1

            deltas = compute_dimension_deltas(state, state)
            return CompositeStateDynamics(
                previous_state=state,
                current_state=state,
                dimension_deltas=deltas,
                transition_count=0,
                persistence_duration=1,
                is_first_update=True,
            )

        self._previous = self._current
        self._current = state

        if _states_equal(self._previous, state):
            self._persistence_duration += 1
        else:
            self._transition_count += 1
            self._persistence_duration = 1

        deltas = compute_dimension_deltas(self._previous, state)

        return CompositeStateDynamics(
            previous_state=self._previous,
            current_state=state,
            dimension_deltas=deltas,
            transition_count=self._transition_count,
            persistence_duration=self._persistence_duration,
            is_first_update=False,
        )

    def reset(self) -> None:
        """Reset memory to initial state."""
        self._previous = None
        self._current = None
        self._transition_count = 0
        self._persistence_duration = 0
        self._tick = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self._tick,
            "transition_count": self._transition_count,
            "persistence_duration": self._persistence_duration,
            "current_state": self._current.to_dict() if self._current else None,
            "previous_state": self._previous.to_dict() if self._previous else None,
        }
