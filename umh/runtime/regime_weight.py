"""Regime-aware weight adaptation — factor computation from regime state.

Adjusts decision weights based on current regime without overriding
base scoring logic. Regime influence is bounded and deterministic.

Factor rules:
    STABLE:     1.0
    TREND_UP:   1.05 + min(0.05, duration * 0.005)
    TREND_DOWN: 0.95 - min(0.05, duration * 0.005)
    SPIKE_UP:   1.10
    SPIKE_DOWN: 0.90

Bounds: factor ∈ [0.85, 1.15]

Stateless computation. No I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.runtime.regime import RegimeType

_DEFAULT_MIN_FACTOR = 0.85
_DEFAULT_MAX_FACTOR = 1.15

_TREND_BASE_UP = 1.05
_TREND_BASE_DOWN = 0.95
_TREND_DURATION_RATE = 0.005
_TREND_DURATION_CAP = 0.05

_SPIKE_FACTOR_UP = 1.10
_SPIKE_FACTOR_DOWN = 0.90
_STABLE_FACTOR = 1.0


@dataclass(frozen=True)
class RegimeWeightConfig:
    """Configuration for regime weight adaptation."""

    min_factor: float = _DEFAULT_MIN_FACTOR
    max_factor: float = _DEFAULT_MAX_FACTOR
    trend_base_up: float = _TREND_BASE_UP
    trend_base_down: float = _TREND_BASE_DOWN
    trend_duration_rate: float = _TREND_DURATION_RATE
    trend_duration_cap: float = _TREND_DURATION_CAP
    spike_factor_up: float = _SPIKE_FACTOR_UP
    spike_factor_down: float = _SPIKE_FACTOR_DOWN
    stable_factor: float = _STABLE_FACTOR

    def __post_init__(self) -> None:
        mn = max(0.5, min(1.0, self.min_factor))
        mx = max(mn, min(2.0, self.max_factor))
        object.__setattr__(self, "min_factor", mn)
        object.__setattr__(self, "max_factor", mx)
        object.__setattr__(self, "trend_base_up", max(1.0, self.trend_base_up))
        object.__setattr__(self, "trend_base_down", max(0.0, min(1.0, self.trend_base_down)))
        object.__setattr__(self, "trend_duration_rate", max(0.0, self.trend_duration_rate))
        object.__setattr__(self, "trend_duration_cap", max(0.0, self.trend_duration_cap))
        object.__setattr__(self, "spike_factor_up", max(1.0, self.spike_factor_up))
        object.__setattr__(self, "spike_factor_down", max(0.0, min(1.0, self.spike_factor_down)))
        object.__setattr__(self, "stable_factor", max(0.0, self.stable_factor))

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_factor": round(self.min_factor, 4),
            "max_factor": round(self.max_factor, 4),
            "trend_base_up": round(self.trend_base_up, 4),
            "trend_base_down": round(self.trend_base_down, 4),
            "trend_duration_rate": round(self.trend_duration_rate, 4),
            "trend_duration_cap": round(self.trend_duration_cap, 4),
            "spike_factor_up": round(self.spike_factor_up, 4),
            "spike_factor_down": round(self.spike_factor_down, 4),
            "stable_factor": round(self.stable_factor, 4),
        }


DEFAULT_WEIGHT_CONFIG = RegimeWeightConfig()


@dataclass(frozen=True)
class RegimeWeightResult:
    """Output of regime weight computation for a single signal."""

    signal_name: str
    factor: float
    raw_factor: float
    regime: RegimeType
    duration: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "factor": round(self.factor, 6),
            "raw_factor": round(self.raw_factor, 6),
            "regime": self.regime.value,
            "duration": self.duration,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class RegimeWeightSnapshot:
    """Frozen snapshot of regime weight factors for all signals."""

    weights: dict[str, RegimeWeightResult]

    def get(self, signal_name: str) -> RegimeWeightResult | None:
        return self.weights.get(signal_name)

    def get_factor(self, signal_name: str, default: float = _STABLE_FACTOR) -> float:
        r = self.weights.get(signal_name)
        return r.factor if r is not None else default

    def min_factor(self) -> float:
        if not self.weights:
            return _STABLE_FACTOR
        return min(r.factor for r in self.weights.values())

    def max_factor(self) -> float:
        if not self.weights:
            return _STABLE_FACTOR
        return max(r.factor for r in self.weights.values())

    def all_neutral(self) -> bool:
        return all(r.factor == _STABLE_FACTOR for r in self.weights.values())

    def biased_signals(self) -> list[str]:
        return sorted(n for n, r in self.weights.items() if r.factor != _STABLE_FACTOR)

    def to_dict(self) -> dict[str, Any]:
        return {
            "weights": {k: v.to_dict() for k, v in sorted(self.weights.items())},
        }


def compute_regime_factor(
    signal_name: str,
    regime: RegimeType,
    duration: int,
    config: RegimeWeightConfig | None = None,
) -> RegimeWeightResult:
    """Compute weight adjustment factor for a single signal's regime state.

    Deterministic, stateless. Same inputs always produce the same factor.

    Args:
        signal_name: Name of the signal.
        regime: Current confirmed regime for this signal.
        duration: How many ticks the signal has been in this regime.
        config: Optional configuration. Uses defaults if None.

    Returns:
        RegimeWeightResult with the computed factor.
    """
    c = config or DEFAULT_WEIGHT_CONFIG
    dur = max(0, duration)

    if regime == RegimeType.STABLE:
        raw = c.stable_factor
        reason = "stable regime, neutral factor"

    elif regime == RegimeType.TREND_UP:
        duration_bonus = min(c.trend_duration_cap, dur * c.trend_duration_rate)
        raw = c.trend_base_up + duration_bonus
        reason = f"trend up, duration bonus {duration_bonus:.4f}"

    elif regime == RegimeType.TREND_DOWN:
        duration_penalty = min(c.trend_duration_cap, dur * c.trend_duration_rate)
        raw = c.trend_base_down - duration_penalty
        reason = f"trend down, duration penalty {duration_penalty:.4f}"

    elif regime == RegimeType.SPIKE_UP:
        raw = c.spike_factor_up
        reason = "spike up, immediate boost"

    elif regime == RegimeType.SPIKE_DOWN:
        raw = c.spike_factor_down
        reason = "spike down, immediate reduction"

    else:
        raw = c.stable_factor
        reason = "unknown regime, default to stable"

    factor = max(c.min_factor, min(c.max_factor, raw))

    return RegimeWeightResult(
        signal_name=signal_name,
        factor=factor,
        raw_factor=raw,
        regime=regime,
        duration=dur,
        reason=reason,
    )


def compute_all_regime_factors(
    regimes: dict[str, RegimeType],
    durations: dict[str, int],
    config: RegimeWeightConfig | None = None,
) -> RegimeWeightSnapshot:
    """Compute weight factors for all signals.

    Args:
        regimes: signal_name → current confirmed RegimeType.
        durations: signal_name → current regime duration in ticks.
        config: Optional configuration.

    Returns:
        RegimeWeightSnapshot with per-signal weight factors.
    """
    results: dict[str, RegimeWeightResult] = {}
    for name in sorted(regimes):
        dur = durations.get(name, 0)
        results[name] = compute_regime_factor(name, regimes[name], dur, config)
    return RegimeWeightSnapshot(weights=results)


def apply_regime_weight(
    base_score: float,
    factor: float,
) -> float:
    """Apply regime weight factor to a base score.

    Simple multiplication — the regime factor biases but cannot dominate.
    With default bounds [0.85, 1.15], the maximum influence is ±15%.

    Args:
        base_score: The pre-regime score.
        factor: The regime weight factor (already clamped).

    Returns:
        Adjusted score.
    """
    return base_score * factor
