"""
Score distribution analysis — distribution-aware metrics for strategy scoring.

Computes statistical properties of strategy score distributions to inform
exploration intensity. The key insight: the raw gap between top and second
strategy is meaningless without knowing the dispersion of all scores.

normalized_gap = (max - second_best) / (std_dev + ε)

A normalized_gap > 2.0 means the leader is 2+ standard deviations ahead —
exploration should be gentle (the system has strong conviction).
A normalized_gap < 1.0 means the gap is within noise — exploration should
be aggressive (the system is uncertain).

Design constraints:
- Deterministic: same scores → same output, always.
- Pure: no side effects, no state, no I/O.
- Bounded: all outputs are finite and well-defined for any input.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

EPSILON = 1e-9


@dataclass(frozen=True)
class ScoreDistribution:
    """Statistical summary of a strategy score distribution."""

    n_strategies: int
    mean_score: float
    std_dev: float
    max_score: float
    second_best: float
    min_score: float
    raw_gap: float
    normalized_gap: float
    dispersion: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_strategies": self.n_strategies,
            "mean_score": round(self.mean_score, 6),
            "std_dev": round(self.std_dev, 6),
            "max_score": round(self.max_score, 6),
            "second_best": round(self.second_best, 6),
            "min_score": round(self.min_score, 6),
            "raw_gap": round(self.raw_gap, 6),
            "normalized_gap": round(self.normalized_gap, 6),
            "dispersion": round(self.dispersion, 6),
        }


@dataclass(frozen=True)
class RelativeUncertainty:
    """How uncertain the system should be about its top choice.

    level ∈ [0, 1]:
        0.0 = absolute confidence (huge normalized gap, low dispersion)
        1.0 = maximum uncertainty (tiny normalized gap, high dispersion)

    This drives exploration intensity:
        high uncertainty → explore aggressively
        low uncertainty → explore gently or not at all
    """

    level: float
    reason: str
    distribution: ScoreDistribution

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": round(self.level, 6),
            "reason": self.reason,
            "distribution": self.distribution.to_dict(),
        }


def compute_distribution(scores: dict[str, float]) -> ScoreDistribution:
    """Compute statistical summary of strategy scores.

    Deterministic. Pure. Handles all edge cases:
    - Empty/single strategy → zeroed distribution.
    - All-equal scores → std_dev = 0, normalized_gap = 0.
    - Negative scores → handled correctly.
    """
    n = len(scores)
    if n == 0:
        return ScoreDistribution(
            n_strategies=0,
            mean_score=0.0,
            std_dev=0.0,
            max_score=0.0,
            second_best=0.0,
            min_score=0.0,
            raw_gap=0.0,
            normalized_gap=0.0,
            dispersion=0.0,
        )

    values = sorted(scores.values(), reverse=True)
    max_score = values[0]
    second_best = values[1] if n >= 2 else max_score
    min_score = values[-1]

    mean = sum(values) / n

    if n < 2:
        std = 0.0
    else:
        variance = sum((v - mean) ** 2 for v in values) / (n - 1)
        std = math.sqrt(variance)

    raw_gap = max_score - second_best
    normalized_gap = raw_gap / (std + EPSILON)

    dispersion = (
        std / (abs(mean) + EPSILON)
        if abs(mean) > EPSILON
        else (std / EPSILON if std > 0 else 0.0)
    )

    return ScoreDistribution(
        n_strategies=n,
        mean_score=mean,
        std_dev=std,
        max_score=max_score,
        second_best=second_best,
        min_score=min_score,
        raw_gap=raw_gap,
        normalized_gap=normalized_gap,
        dispersion=dispersion,
    )


def compute_relative_uncertainty(
    scores: dict[str, float],
) -> RelativeUncertainty:
    """Compute how uncertain the system should be about its top strategy choice.

    Uses normalized_gap and dispersion to produce a single uncertainty level [0, 1].

    Logic:
        - normalized_gap > 2.0 → low uncertainty (leader is clearly ahead)
        - normalized_gap < 0.5 → high uncertainty (gap is within noise)
        - dispersion modulates: high dispersion amplifies uncertainty
        - all-zero or single strategy → zero uncertainty (uninformed, not uncertain)
    """
    dist = compute_distribution(scores)

    if dist.n_strategies < 2:
        return RelativeUncertainty(
            level=0.0, reason="insufficient_strategies", distribution=dist
        )

    if dist.max_score <= 0 and dist.second_best <= 0:
        return RelativeUncertainty(level=0.0, reason="no_data", distribution=dist)

    if dist.raw_gap == 0.0:
        level = 1.0
        return RelativeUncertainty(level=level, reason="near_tie", distribution=dist)

    gap_factor = 1.0 - _clamp(dist.normalized_gap / 3.0, 0.0, 1.0)

    dispersion_boost = _clamp(dist.dispersion / 2.0, 0.0, 0.3)

    level = _clamp(gap_factor + dispersion_boost, 0.0, 1.0)

    if dist.normalized_gap > 2.0:
        reason = "high_confidence"
    elif dist.normalized_gap > 1.0:
        reason = "moderate_confidence"
    elif dist.normalized_gap > 0.5:
        reason = "low_confidence"
    else:
        reason = "near_tie"

    return RelativeUncertainty(level=level, reason=reason, distribution=dist)


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v
