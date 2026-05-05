"""Adaptive half-life — environment-responsive decay rate for temporal weighting.

Adjusts the half-life parameter dynamically based on recent outcome volatility:
stable environments get longer memory (higher half-life), volatile environments
get shorter memory (lower half-life).

Design principles:
    - Off by default (enabled must be explicitly True)
    - Volatility = variance of recent outcome_scores, normalized
    - half_life = base × (1 + (1 - volatility) × sensitivity)
    - Clamped to [min_half_life, max_half_life]
    - Deterministic: no randomness, no wall-clock (inv 356)
    - No mutation of historical records (inv 357)
    - No feedback from scoring (inv 358)
    - Smooth: bounded rate of change (inv 359)
    - Explainable: returns volatility, window, computed half-life (inv 360)
    - Missing data → fallback to base_half_life (inv 361)

Invariants 353-362.

Pure computation — no I/O, no child processes.
No imports from cell, environment, or adapter layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MAX_VARIANCE: float = 0.25


@dataclass(frozen=True)
class AdaptiveHalfLifeConfig:
    """Configuration for adaptive half-life adjustment."""

    enabled: bool = False
    base_half_life: int = 50
    min_half_life: int = 10
    max_half_life: int = 200
    volatility_window: int = 20
    volatility_sensitivity: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_half_life", max(1, self.base_half_life))
        object.__setattr__(self, "min_half_life", max(1, self.min_half_life))
        object.__setattr__(self, "max_half_life", max(self.min_half_life, self.max_half_life))
        object.__setattr__(self, "volatility_window", max(2, self.volatility_window))
        object.__setattr__(
            self,
            "volatility_sensitivity",
            max(0.0, min(10.0, self.volatility_sensitivity)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "base_half_life": self.base_half_life,
            "min_half_life": self.min_half_life,
            "max_half_life": self.max_half_life,
            "volatility_window": self.volatility_window,
            "volatility_sensitivity": round(self.volatility_sensitivity, 4),
        }


@dataclass(frozen=True)
class AdaptiveHalfLifeResult:
    """Result of adaptive half-life computation (inv 360)."""

    computed_half_life: int = 50
    base_half_life: int = 50
    volatility: float = 0.0
    window_size: int = 0
    applied: bool = False
    reason_if_not_applied: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "computed_half_life": self.computed_half_life,
            "base_half_life": self.base_half_life,
            "volatility": round(self.volatility, 6),
            "window_size": self.window_size,
            "applied": self.applied,
            "reason_if_not_applied": self.reason_if_not_applied,
        }


def _compute_variance(scores: list[float]) -> float:
    """Compute population variance of a list of scores."""
    if len(scores) < 2:
        return 0.0
    mean = sum(scores) / len(scores)
    return sum((s - mean) ** 2 for s in scores) / len(scores)


def compute_volatility(
    recent_scores: list[float],
    max_variance: float = _MAX_VARIANCE,
) -> float:
    """Compute normalized volatility from recent outcome scores.

    Returns value in [0, 1] where 0 = perfectly stable, 1 = maximally volatile.
    """
    if len(recent_scores) < 2:
        return 0.0
    variance = _compute_variance(recent_scores)
    if max_variance <= 0:
        return 0.0
    normalized = variance / max_variance
    return max(0.0, min(1.0, normalized))


def compute_adaptive_half_life(
    recent_scores: list[float] | None = None,
    config: AdaptiveHalfLifeConfig | None = None,
) -> AdaptiveHalfLifeResult:
    """Compute environment-adaptive half-life from recent outcome volatility.

    Formula:
        volatility = clamp(variance(recent_scores) / max_variance, 0, 1)
        half_life = base × (1 + (1 - volatility) × sensitivity)
        half_life = clamp(half_life, min_half_life, max_half_life)

    Interpretation:
        - Low volatility (stable) → (1 - vol) is large → longer half-life → more memory
        - High volatility (unstable) → (1 - vol) is small → shorter half-life → less memory
    """
    cfg = config or AdaptiveHalfLifeConfig()

    if not cfg.enabled:
        return AdaptiveHalfLifeResult(
            computed_half_life=cfg.base_half_life,
            base_half_life=cfg.base_half_life,
            applied=False,
            reason_if_not_applied="adaptive half-life disabled",
        )

    scores = recent_scores or []

    if len(scores) < 2:
        return AdaptiveHalfLifeResult(
            computed_half_life=cfg.base_half_life,
            base_half_life=cfg.base_half_life,
            window_size=len(scores),
            applied=False,
            reason_if_not_applied="insufficient data for volatility computation",
        )

    windowed = scores[-cfg.volatility_window :]
    volatility = compute_volatility(windowed)

    raw_half_life = cfg.base_half_life * (1.0 + (1.0 - volatility) * cfg.volatility_sensitivity)
    clamped = max(cfg.min_half_life, min(cfg.max_half_life, int(round(raw_half_life))))

    return AdaptiveHalfLifeResult(
        computed_half_life=clamped,
        base_half_life=cfg.base_half_life,
        volatility=volatility,
        window_size=len(windowed),
        applied=True,
    )
