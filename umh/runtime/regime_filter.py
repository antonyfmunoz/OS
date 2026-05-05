"""Regime hysteresis — duration-based confirmation before regime transitions.

Prevents noise-driven oscillation by requiring a new regime to persist
for confirm_threshold consecutive ticks before the transition is accepted.

Filter rules:
    IF raw_regime == confirmed_regime:
        clear pending, return confirmed_regime

    ELIF raw_regime != pending_regime:
        pending_regime = raw_regime
        pending_duration = 1
        return confirmed_regime

    ELSE (raw_regime == pending_regime):
        pending_duration += 1
        IF pending_duration >= confirm_threshold:
            ACCEPT: confirmed_regime = raw_regime, clear pending
            return raw_regime
        ELSE:
            return confirmed_regime

Stateful — holds per-signal FilterState.
No I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.runtime.regime import RegimeType

_DEFAULT_CONFIRM_THRESHOLD = 3
_SIGNAL_NAMES = ("urgency", "risk_level", "resource_pressure", "stability_mode")


@dataclass
class FilterState:
    """Per-signal hysteresis state. Mutable — updated each tick."""

    signal_name: str
    confirmed_regime: RegimeType = RegimeType.STABLE
    pending_regime: RegimeType | None = None
    pending_duration: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "confirmed_regime": self.confirmed_regime.value,
            "pending_regime": self.pending_regime.value
            if self.pending_regime is not None
            else None,
            "pending_duration": self.pending_duration,
        }


@dataclass(frozen=True)
class FilterResult:
    """Output of a single filter application."""

    signal_name: str
    raw_regime: RegimeType
    filtered_regime: RegimeType
    was_confirmed: bool
    pending_regime: RegimeType | None
    pending_duration: int

    @property
    def was_suppressed(self) -> bool:
        return self.raw_regime != self.filtered_regime

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "raw_regime": self.raw_regime.value,
            "filtered_regime": self.filtered_regime.value,
            "was_confirmed": self.was_confirmed,
            "was_suppressed": self.was_suppressed,
            "pending_regime": self.pending_regime.value
            if self.pending_regime is not None
            else None,
            "pending_duration": self.pending_duration,
        }


@dataclass(frozen=True)
class FilterSnapshot:
    """Frozen snapshot of all filter results at one tick."""

    results: dict[str, FilterResult]
    tick: int

    def get(self, signal_name: str) -> FilterResult | None:
        return self.results.get(signal_name)

    def get_filtered_regime(self, signal_name: str) -> RegimeType:
        r = self.results.get(signal_name)
        return r.filtered_regime if r is not None else RegimeType.STABLE

    def any_confirmed(self) -> bool:
        return any(r.was_confirmed for r in self.results.values())

    def any_suppressed(self) -> bool:
        return any(r.was_suppressed for r in self.results.values())

    def all_stable(self) -> bool:
        return all(r.filtered_regime is RegimeType.STABLE for r in self.results.values())

    def confirmed_signals(self) -> list[str]:
        return sorted(name for name, r in self.results.items() if r.was_confirmed)

    def suppressed_signals(self) -> list[str]:
        return sorted(name for name, r in self.results.items() if r.was_suppressed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": {k: v.to_dict() for k, v in sorted(self.results.items())},
            "tick": self.tick,
            "any_confirmed": self.any_confirmed(),
            "any_suppressed": self.any_suppressed(),
            "all_stable": self.all_stable(),
        }


def filter_regime(
    state: FilterState,
    raw_regime: RegimeType,
    confirm_threshold: int,
) -> FilterResult:
    """Apply hysteresis filter to a single signal.

    Returns the filtered regime (may differ from raw_regime if not yet confirmed).
    Mutates state in place.
    """
    if raw_regime == state.confirmed_regime:
        state.pending_regime = None
        state.pending_duration = 0
        return FilterResult(
            signal_name=state.signal_name,
            raw_regime=raw_regime,
            filtered_regime=state.confirmed_regime,
            was_confirmed=False,
            pending_regime=None,
            pending_duration=0,
        )

    if state.pending_regime != raw_regime:
        state.pending_regime = raw_regime
        state.pending_duration = 1
    else:
        state.pending_duration += 1

    if state.pending_duration >= confirm_threshold:
        state.confirmed_regime = raw_regime
        state.pending_regime = None
        state.pending_duration = 0
        return FilterResult(
            signal_name=state.signal_name,
            raw_regime=raw_regime,
            filtered_regime=raw_regime,
            was_confirmed=True,
            pending_regime=None,
            pending_duration=0,
        )

    return FilterResult(
        signal_name=state.signal_name,
        raw_regime=raw_regime,
        filtered_regime=state.confirmed_regime,
        was_confirmed=False,
        pending_regime=raw_regime,
        pending_duration=state.pending_duration,
    )


class RegimeFilter:
    """Hysteresis filter for regime transitions.

    Requires a new regime to persist for confirm_threshold consecutive
    ticks before accepting the transition. Prevents noise-driven
    oscillation in the regime pipeline.

    Thread safety: not thread-safe. Designed for single-threaded tick loops.
    """

    def __init__(
        self,
        *,
        confirm_threshold: int = _DEFAULT_CONFIRM_THRESHOLD,
        signals: tuple[str, ...] | None = None,
    ) -> None:
        self._confirm_threshold = max(1, confirm_threshold)
        active_signals = signals or _SIGNAL_NAMES
        self._states: dict[str, FilterState] = {
            name: FilterState(signal_name=name) for name in active_signals
        }
        self._tick: int = 0

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def confirm_threshold(self) -> int:
        return self._confirm_threshold

    @property
    def states(self) -> dict[str, FilterState]:
        return dict(self._states)

    def filter(
        self,
        raw_regimes: dict[str, RegimeType],
    ) -> FilterSnapshot:
        """Filter all signals through hysteresis.

        Accepts a dict of signal_name → raw RegimeType (typically from
        RegimeMemory or classify output). Returns a FilterSnapshot with
        the filtered (confirmed) regimes.
        """
        self._tick += 1
        results: dict[str, FilterResult] = {}

        for name, raw_regime in raw_regimes.items():
            if name not in self._states:
                self._states[name] = FilterState(signal_name=name)
            results[name] = filter_regime(self._states[name], raw_regime, self._confirm_threshold)

        return FilterSnapshot(results=results, tick=self._tick)

    def filter_single(
        self,
        signal_name: str,
        raw_regime: RegimeType,
    ) -> FilterResult:
        """Filter a single signal through hysteresis."""
        if signal_name not in self._states:
            self._states[signal_name] = FilterState(signal_name=signal_name)
        return filter_regime(self._states[signal_name], raw_regime, self._confirm_threshold)

    def get_confirmed_regime(self, signal_name: str) -> RegimeType:
        s = self._states.get(signal_name)
        return s.confirmed_regime if s is not None else RegimeType.STABLE

    def get_pending(self, signal_name: str) -> tuple[RegimeType | None, int]:
        s = self._states.get(signal_name)
        if s is None:
            return None, 0
        return s.pending_regime, s.pending_duration

    def reset(self) -> None:
        """Reset all filter states to STABLE with no pending."""
        for state in self._states.values():
            state.confirmed_regime = RegimeType.STABLE
            state.pending_regime = None
            state.pending_duration = 0
        self._tick = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self._tick,
            "confirm_threshold": self._confirm_threshold,
            "states": {k: v.to_dict() for k, v in sorted(self._states.items())},
        }
