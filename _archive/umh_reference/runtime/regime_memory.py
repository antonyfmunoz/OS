"""Regime memory — temporal persistence and transition tracking for regimes.

Tracks per-signal regime state across ticks: current regime, previous regime,
duration in current regime, total transition count, and last transition tick.

Update rules:
    IF new_regime == current_regime:
        duration += 1
    ELSE:
        previous_regime = current_regime
        current_regime = new_regime
        duration = 1
        transition_count += 1
        last_transition_tick = tick

RegimeMemory is stateful — it holds per-signal RegimeState.
RegimeTransition records are frozen snapshots of individual transitions.

No I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.runtime.regime import RegimeSnapshot, RegimeType

_SIGNAL_NAMES = ("urgency", "risk_level", "resource_pressure", "stability_mode")


@dataclass
class RegimeState:
    """Per-signal regime tracking state. Mutable — updated each tick."""

    signal_name: str
    current_regime: RegimeType = RegimeType.STABLE
    previous_regime: RegimeType = RegimeType.STABLE
    duration: int = 0
    transition_count: int = 0
    last_transition_tick: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "current_regime": self.current_regime.value,
            "previous_regime": self.previous_regime.value,
            "duration": self.duration,
            "transition_count": self.transition_count,
            "last_transition_tick": self.last_transition_tick,
        }


@dataclass(frozen=True)
class RegimeTransition:
    """Frozen record of a single regime transition."""

    signal_name: str
    from_regime: RegimeType
    to_regime: RegimeType
    tick: int
    previous_duration: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "from_regime": self.from_regime.value,
            "to_regime": self.to_regime.value,
            "tick": self.tick,
            "previous_duration": self.previous_duration,
        }


@dataclass(frozen=True)
class RegimeMemorySnapshot:
    """Frozen snapshot of all regime states at a point in time."""

    states: dict[str, RegimeState]
    transitions: list[RegimeTransition]
    tick: int

    def get_state(self, signal_name: str) -> RegimeState | None:
        return self.states.get(signal_name)

    def get_duration(self, signal_name: str) -> int:
        s = self.states.get(signal_name)
        return s.duration if s is not None else 0

    def get_regime(self, signal_name: str) -> RegimeType:
        s = self.states.get(signal_name)
        return s.current_regime if s is not None else RegimeType.STABLE

    def had_transition(self, signal_name: str) -> bool:
        return any(t.signal_name == signal_name for t in self.transitions)

    def transition_count(self) -> int:
        return len(self.transitions)

    def all_stable(self) -> bool:
        return all(s.current_regime is RegimeType.STABLE for s in self.states.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "states": {k: v.to_dict() for k, v in sorted(self.states.items())},
            "transitions": [t.to_dict() for t in self.transitions],
            "tick": self.tick,
        }


def update_regime_state(
    state: RegimeState,
    new_regime: RegimeType,
    tick: int,
) -> RegimeTransition | None:
    """Update a single signal's regime state. Returns transition if one occurred."""
    if state.current_regime == new_regime:
        state.duration += 1
        return None

    previous_duration = state.duration
    transition = RegimeTransition(
        signal_name=state.signal_name,
        from_regime=state.current_regime,
        to_regime=new_regime,
        tick=tick,
        previous_duration=previous_duration,
    )

    state.previous_regime = state.current_regime
    state.current_regime = new_regime
    state.duration = 1
    state.transition_count += 1
    state.last_transition_tick = tick

    return transition


class RegimeMemory:
    """Temporal memory for regime states across ticks.

    Tracks per-signal regime persistence, duration, and transitions.
    The only stateful component in the regime pipeline.

    Thread safety: not thread-safe. Designed for single-threaded tick loops.
    """

    def __init__(self, *, signals: tuple[str, ...] | None = None) -> None:
        active_signals = signals or _SIGNAL_NAMES
        self._states: dict[str, RegimeState] = {
            name: RegimeState(signal_name=name) for name in active_signals
        }
        self._tick: int = 0
        self._history: list[RegimeTransition] = []

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def states(self) -> dict[str, RegimeState]:
        return dict(self._states)

    @property
    def history(self) -> list[RegimeTransition]:
        return list(self._history)

    def update(self, snapshot: RegimeSnapshot) -> RegimeMemorySnapshot:
        """Update all regime states from a RegimeSnapshot.

        Returns a frozen snapshot of the current state plus any
        transitions that occurred on this tick.
        """
        self._tick += 1
        transitions: list[RegimeTransition] = []

        for name, result in snapshot.regimes.items():
            if name not in self._states:
                self._states[name] = RegimeState(signal_name=name)

            t = update_regime_state(self._states[name], result.regime, self._tick)
            if t is not None:
                transitions.append(t)
                self._history.append(t)

        for name, state in self._states.items():
            if name not in snapshot.regimes:
                state.duration += 1

        return RegimeMemorySnapshot(
            states=dict(self._states),
            transitions=transitions,
            tick=self._tick,
        )

    def update_single(
        self,
        signal_name: str,
        regime: RegimeType,
        tick: int | None = None,
    ) -> RegimeTransition | None:
        """Update a single signal's regime state.

        Returns the transition if one occurred, None otherwise.
        """
        effective_tick = tick if tick is not None else self._tick + 1
        if tick is None:
            self._tick += 1

        if signal_name not in self._states:
            self._states[signal_name] = RegimeState(signal_name=signal_name)

        t = update_regime_state(self._states[signal_name], regime, effective_tick)
        if t is not None:
            self._history.append(t)
        return t

    def get_state(self, signal_name: str) -> RegimeState | None:
        return self._states.get(signal_name)

    def get_duration(self, signal_name: str) -> int:
        s = self._states.get(signal_name)
        return s.duration if s is not None else 0

    def get_regime(self, signal_name: str) -> RegimeType:
        s = self._states.get(signal_name)
        return s.current_regime if s is not None else RegimeType.STABLE

    def get_transition_count(self, signal_name: str) -> int:
        s = self._states.get(signal_name)
        return s.transition_count if s is not None else 0

    def total_transitions(self) -> int:
        return len(self._history)

    def recent_transitions(self, n: int = 5) -> list[RegimeTransition]:
        return self._history[-n:]

    def reset(self) -> None:
        """Reset all regime states to STABLE with zero duration."""
        for state in self._states.values():
            state.current_regime = RegimeType.STABLE
            state.previous_regime = RegimeType.STABLE
            state.duration = 0
            state.transition_count = 0
            state.last_transition_tick = 0
        self._tick = 0
        self._history.clear()

    def snapshot(self) -> RegimeMemorySnapshot:
        """Return a frozen snapshot of current state without updating."""
        return RegimeMemorySnapshot(
            states=dict(self._states),
            transitions=[],
            tick=self._tick,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self._tick,
            "states": {k: v.to_dict() for k, v in sorted(self._states.items())},
            "total_transitions": len(self._history),
            "recent_transitions": [t.to_dict() for t in self._history[-5:]],
        }
