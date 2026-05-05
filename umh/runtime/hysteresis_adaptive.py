"""Adaptive hysteresis — per-signal threshold computation.

Makes confirm_threshold adaptive based on signal volatility and regime
stability. Signals with large deltas confirm faster; signals with long
regime durations resist switching.

Adaptation formula:
    factor = 1.0 + volatility_weight * abs(delta) - stability_weight * log(duration + 1)
    adaptive_threshold = round(base_threshold * factor)
    adaptive_threshold = clamp(adaptive_threshold, min_threshold, max_threshold)

Default weights:
    volatility_weight = -2.0  (negative: large delta → lower factor → faster confirm)
    stability_weight  =  0.5  (positive: long duration → lower factor → more resistance)

Wait — re-reading the spec:
    + volatility_weight * abs(delta)   → large delta increases factor
    - stability_weight * log(duration) → long duration decreases factor

But large delta should REDUCE threshold (confirm faster).
So volatility_weight should be NEGATIVE in the formula,
OR we invert the interpretation.

Chosen design:
    factor = 1.0 - volatility_adjust + stability_adjust
    where:
        volatility_adjust = volatility_weight * abs(delta)   → reduces threshold
        stability_adjust  = stability_weight * log(duration + 1) → increases threshold

This gives:
    large delta → factor decreases → threshold decreases → faster confirmation
    long duration → factor increases → threshold increases → more resistance

Bounds: adaptive_threshold ∈ [min_threshold, max_threshold] (default [1, 6])

Stateless computation. No I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

_DEFAULT_BASE_THRESHOLD = 3
_DEFAULT_MIN_THRESHOLD = 1
_DEFAULT_MAX_THRESHOLD = 6
_DEFAULT_VOLATILITY_WEIGHT = 2.0
_DEFAULT_STABILITY_WEIGHT = 0.5


@dataclass(frozen=True)
class AdaptiveThresholdConfig:
    """Configuration for adaptive threshold computation."""

    base_threshold: int = _DEFAULT_BASE_THRESHOLD
    min_threshold: int = _DEFAULT_MIN_THRESHOLD
    max_threshold: int = _DEFAULT_MAX_THRESHOLD
    volatility_weight: float = _DEFAULT_VOLATILITY_WEIGHT
    stability_weight: float = _DEFAULT_STABILITY_WEIGHT

    def __post_init__(self) -> None:
        b = max(1, self.base_threshold)
        mn = max(1, self.min_threshold)
        mx = max(mn, self.max_threshold)
        vw = max(0.0, self.volatility_weight)
        sw = max(0.0, self.stability_weight)
        object.__setattr__(self, "base_threshold", b)
        object.__setattr__(self, "min_threshold", mn)
        object.__setattr__(self, "max_threshold", mx)
        object.__setattr__(self, "volatility_weight", vw)
        object.__setattr__(self, "stability_weight", sw)

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_threshold": self.base_threshold,
            "min_threshold": self.min_threshold,
            "max_threshold": self.max_threshold,
            "volatility_weight": round(self.volatility_weight, 4),
            "stability_weight": round(self.stability_weight, 4),
        }


DEFAULT_ADAPTIVE_CONFIG = AdaptiveThresholdConfig()


@dataclass(frozen=True)
class ThresholdResult:
    """Output of adaptive threshold computation for a single signal."""

    signal_name: str
    adaptive_threshold: int
    base_threshold: int
    factor: float
    delta_magnitude: float
    duration: int
    volatility_adjust: float
    stability_adjust: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "adaptive_threshold": self.adaptive_threshold,
            "base_threshold": self.base_threshold,
            "factor": round(self.factor, 4),
            "delta_magnitude": round(self.delta_magnitude, 4),
            "duration": self.duration,
            "volatility_adjust": round(self.volatility_adjust, 4),
            "stability_adjust": round(self.stability_adjust, 4),
        }


@dataclass(frozen=True)
class ThresholdSnapshot:
    """Frozen snapshot of adaptive thresholds for all signals."""

    thresholds: dict[str, ThresholdResult]

    def get(self, signal_name: str) -> ThresholdResult | None:
        return self.thresholds.get(signal_name)

    def get_threshold(self, signal_name: str, default: int = _DEFAULT_BASE_THRESHOLD) -> int:
        r = self.thresholds.get(signal_name)
        return r.adaptive_threshold if r is not None else default

    def min_threshold(self) -> int:
        if not self.thresholds:
            return _DEFAULT_BASE_THRESHOLD
        return min(r.adaptive_threshold for r in self.thresholds.values())

    def max_threshold(self) -> int:
        if not self.thresholds:
            return _DEFAULT_BASE_THRESHOLD
        return max(r.adaptive_threshold for r in self.thresholds.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "thresholds": {k: v.to_dict() for k, v in sorted(self.thresholds.items())},
        }


def compute_adaptive_threshold(
    signal_name: str,
    delta_magnitude: float,
    duration: int,
    config: AdaptiveThresholdConfig | None = None,
) -> ThresholdResult:
    """Compute adaptive confirm threshold for a single signal.

    Deterministic, stateless. Same inputs always produce the same threshold.

    Args:
        signal_name: Name of the signal.
        delta_magnitude: Absolute value of the signal's delta (from EMA).
        duration: How many ticks the signal has been in its current regime.
        config: Optional configuration. Uses defaults if None.

    Returns:
        ThresholdResult with the computed adaptive threshold.
    """
    c = config or DEFAULT_ADAPTIVE_CONFIG

    volatility_adjust = c.volatility_weight * delta_magnitude
    stability_adjust = c.stability_weight * math.log(max(duration, 0) + 1)

    factor = 1.0 - volatility_adjust + stability_adjust

    raw_threshold = c.base_threshold * factor
    adaptive = max(c.min_threshold, min(c.max_threshold, round(raw_threshold)))

    return ThresholdResult(
        signal_name=signal_name,
        adaptive_threshold=adaptive,
        base_threshold=c.base_threshold,
        factor=factor,
        delta_magnitude=delta_magnitude,
        duration=duration,
        volatility_adjust=volatility_adjust,
        stability_adjust=stability_adjust,
    )


def compute_all_thresholds(
    deltas: dict[str, float],
    durations: dict[str, int],
    config: AdaptiveThresholdConfig | None = None,
) -> ThresholdSnapshot:
    """Compute adaptive thresholds for all signals.

    Args:
        deltas: signal_name → absolute delta magnitude.
        durations: signal_name → current regime duration in ticks.
        config: Optional configuration.

    Returns:
        ThresholdSnapshot with per-signal adaptive thresholds.
    """
    results: dict[str, ThresholdResult] = {}
    for name in sorted(deltas):
        dur = durations.get(name, 0)
        results[name] = compute_adaptive_threshold(name, abs(deltas[name]), dur, config)
    return ThresholdSnapshot(thresholds=results)
