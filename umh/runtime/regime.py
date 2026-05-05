"""Temporal regime classification — discrete labels from continuous delta.

Converts the raw delta (fast EMA - slow EMA) from the horizon layer
into discrete regime classifications: STABLE, TREND_UP, TREND_DOWN,
SPIKE_UP, SPIKE_DOWN.

Classification rules (deterministic, threshold-based):
    abs_delta < trend_threshold  → STABLE
    abs_delta >= spike_threshold → SPIKE_UP / SPIKE_DOWN
    otherwise                    → TREND_UP / TREND_DOWN

    delta > 0 → UP direction
    delta < 0 → DOWN direction

Default thresholds:
    spike_threshold = 0.25
    trend_threshold = 0.08

Stateless — no mutation, no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

_DEFAULT_SPIKE_THRESHOLD = 0.25
_DEFAULT_TREND_THRESHOLD = 0.08


class RegimeType(Enum):
    """Discrete temporal regime classification."""

    STABLE = "stable"
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    SPIKE_UP = "spike_up"
    SPIKE_DOWN = "spike_down"


@dataclass(frozen=True)
class RegimeThresholds:
    """Configurable thresholds for regime classification."""

    spike_threshold: float = _DEFAULT_SPIKE_THRESHOLD
    trend_threshold: float = _DEFAULT_TREND_THRESHOLD

    def __post_init__(self) -> None:
        s = max(0.01, min(1.0, self.spike_threshold))
        t = max(0.001, min(s - 0.001, self.trend_threshold))
        object.__setattr__(self, "spike_threshold", s)
        object.__setattr__(self, "trend_threshold", t)

    def to_dict(self) -> dict[str, Any]:
        return {
            "spike_threshold": round(self.spike_threshold, 4),
            "trend_threshold": round(self.trend_threshold, 4),
        }


DEFAULT_THRESHOLDS = RegimeThresholds()


@dataclass(frozen=True)
class RegimeResult:
    """Output of regime classification for a single signal."""

    signal_name: str
    regime: RegimeType
    delta: float
    magnitude: float
    is_spike: bool
    is_trend: bool

    @property
    def is_stable(self) -> bool:
        return self.regime is RegimeType.STABLE

    @property
    def is_up(self) -> bool:
        return self.regime in (RegimeType.SPIKE_UP, RegimeType.TREND_UP)

    @property
    def is_down(self) -> bool:
        return self.regime in (RegimeType.SPIKE_DOWN, RegimeType.TREND_DOWN)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "regime": self.regime.value,
            "delta": round(self.delta, 4),
            "magnitude": round(self.magnitude, 4),
            "is_spike": self.is_spike,
            "is_trend": self.is_trend,
        }


@dataclass(frozen=True)
class RegimeSnapshot:
    """Complete regime classification for all signals at one tick."""

    regimes: dict[str, RegimeResult]
    tick: int

    def get(self, signal_name: str) -> RegimeResult | None:
        return self.regimes.get(signal_name)

    def get_regime(self, signal_name: str) -> RegimeType:
        r = self.regimes.get(signal_name)
        return r.regime if r is not None else RegimeType.STABLE

    def has_any_spike(self) -> bool:
        return any(r.is_spike for r in self.regimes.values())

    def has_any_trend(self) -> bool:
        return any(r.is_trend for r in self.regimes.values())

    def all_stable(self) -> bool:
        return all(r.is_stable for r in self.regimes.values())

    def spike_signals(self) -> list[str]:
        return sorted(name for name, r in self.regimes.items() if r.is_spike)

    def trend_signals(self) -> list[str]:
        return sorted(name for name, r in self.regimes.items() if r.is_trend)

    def to_dict(self) -> dict[str, Any]:
        return {
            "regimes": {k: v.to_dict() for k, v in sorted(self.regimes.items())},
            "tick": self.tick,
            "has_any_spike": self.has_any_spike(),
            "has_any_trend": self.has_any_trend(),
            "all_stable": self.all_stable(),
        }


def classify_regime(
    signal_name: str,
    delta: float,
    thresholds: RegimeThresholds | None = None,
) -> RegimeResult:
    """Classify a single signal's delta into a discrete regime.

    Deterministic, stateless, bounded. Same delta always produces
    the same regime.
    """
    t = thresholds or DEFAULT_THRESHOLDS
    magnitude = abs(delta)

    if magnitude < t.trend_threshold:
        regime = RegimeType.STABLE
        is_spike = False
        is_trend = False
    elif magnitude >= t.spike_threshold:
        regime = RegimeType.SPIKE_UP if delta > 0 else RegimeType.SPIKE_DOWN
        is_spike = True
        is_trend = False
    else:
        regime = RegimeType.TREND_UP if delta > 0 else RegimeType.TREND_DOWN
        is_spike = False
        is_trend = True

    return RegimeResult(
        signal_name=signal_name,
        regime=regime,
        delta=delta,
        magnitude=magnitude,
        is_spike=is_spike,
        is_trend=is_trend,
    )


def classify_all_regimes(
    deltas: dict[str, float],
    thresholds: RegimeThresholds | None = None,
    tick: int = 0,
) -> RegimeSnapshot:
    """Classify regimes for all signals from their deltas."""
    regimes: dict[str, RegimeResult] = {}
    for name in sorted(deltas):
        regimes[name] = classify_regime(name, deltas[name], thresholds)
    return RegimeSnapshot(regimes=regimes, tick=tick)


def classify_from_horizon(
    snapshot: object,
    thresholds: RegimeThresholds | None = None,
) -> RegimeSnapshot:
    """Classify regimes directly from a HorizonSnapshot.

    Extracts deltas from the horizon snapshot and classifies each.
    Accepts Any to avoid circular import — validated at runtime.
    """
    from umh.runtime.horizon import HorizonSnapshot

    if not isinstance(snapshot, HorizonSnapshot):
        msg = f"Expected HorizonSnapshot, got {type(snapshot).__name__}"
        raise TypeError(msg)

    deltas = {name: hv.delta for name, hv in snapshot.values.items()}
    return classify_all_regimes(deltas, thresholds, snapshot.tick)
