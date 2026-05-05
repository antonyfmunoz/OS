"""Regime-specific half-life — per-regime memory speed adjustment.

Modifies the adaptive half-life multiplicatively based on the current
regime classification. Stable regimes get longer memory (patterns persist),
spike/chaos regimes get shorter memory (old patterns fade faster).

Design principles:
    - Off by default (enabled must be explicitly True)
    - Multiplicative composition: regime_hl = volatility_hl × multiplier
    - Multiplier ordering: STABLE >= TREND >= SPIKE >= CHAOS (inv 364)
    - Clamped to [min_half_life, max_half_life] (inv 372)
    - Missing regime → multiplier = 1.0 (inv 369)
    - Deterministic: no randomness (inv 366)
    - No mutation of past records (inv 367)
    - No feedback coupling (inv 368)
    - Fully explainable per step (inv 370)

Invariants 363-372.

Pure computation — no I/O, no child processes.
No imports from cell, environment, or adapter layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.runtime.adaptive_half_life import AdaptiveHalfLifeResult
from umh.runtime.regime import RegimeType


class RegimeCategory(Enum):
    """Coarse regime categories for half-life adjustment."""

    STABLE = "stable"
    TREND = "trend"
    SPIKE = "spike"
    CHAOS = "chaos"


_DEFAULT_MULTIPLIERS: dict[RegimeCategory, float] = {
    RegimeCategory.STABLE: 1.5,
    RegimeCategory.TREND: 1.0,
    RegimeCategory.SPIKE: 0.6,
    RegimeCategory.CHAOS: 0.4,
}

_REGIME_TYPE_TO_CATEGORY: dict[RegimeType, RegimeCategory] = {
    RegimeType.STABLE: RegimeCategory.STABLE,
    RegimeType.TREND_UP: RegimeCategory.TREND,
    RegimeType.TREND_DOWN: RegimeCategory.TREND,
    RegimeType.SPIKE_UP: RegimeCategory.SPIKE,
    RegimeType.SPIKE_DOWN: RegimeCategory.SPIKE,
}


@dataclass(frozen=True)
class RegimeHalfLifeConfig:
    """Configuration for regime-specific half-life adjustment."""

    enabled: bool = False
    base_half_life: int = 50
    regime_multipliers: dict[RegimeCategory, float] = field(
        default_factory=lambda: dict(_DEFAULT_MULTIPLIERS)
    )
    min_half_life: int = 10
    max_half_life: int = 200

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_half_life", max(1, self.base_half_life))
        object.__setattr__(self, "min_half_life", max(1, self.min_half_life))
        object.__setattr__(self, "max_half_life", max(self.min_half_life, self.max_half_life))
        clamped = {}
        for cat, mult in self.regime_multipliers.items():
            clamped[cat] = max(0.01, min(10.0, mult))
        object.__setattr__(self, "regime_multipliers", clamped)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "base_half_life": self.base_half_life,
            "regime_multipliers": {
                cat.value: round(mult, 4) for cat, mult in self.regime_multipliers.items()
            },
            "min_half_life": self.min_half_life,
            "max_half_life": self.max_half_life,
        }


@dataclass(frozen=True)
class RegimeHalfLifeResult:
    """Result of regime-specific half-life computation (inv 370)."""

    final_half_life: int = 50
    base_half_life: int = 50
    volatility_half_life: int = 50
    regime_multiplier: float = 1.0
    regime: str = ""
    regime_category: str = ""
    volatility: float = 0.0
    applied: bool = False
    reason_if_not_applied: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_half_life": self.final_half_life,
            "base_half_life": self.base_half_life,
            "volatility_half_life": self.volatility_half_life,
            "regime_multiplier": round(self.regime_multiplier, 4),
            "regime": self.regime,
            "regime_category": self.regime_category,
            "volatility": round(self.volatility, 6),
            "applied": self.applied,
            "reason_if_not_applied": self.reason_if_not_applied,
        }


def classify_regime_category(
    regime_type: RegimeType | None = None,
    regime_label: str | None = None,
) -> RegimeCategory:
    """Map a RegimeType or string label to a coarse RegimeCategory.

    Falls back to TREND (neutral multiplier) if unrecognized (inv 369).
    """
    if regime_type is not None:
        return _REGIME_TYPE_TO_CATEGORY.get(regime_type, RegimeCategory.TREND)

    if regime_label is not None:
        label = regime_label.lower().strip()
        for cat in RegimeCategory:
            if cat.value == label:
                return cat
        if "spike" in label:
            return RegimeCategory.SPIKE
        if "trend" in label:
            return RegimeCategory.TREND
        if "stable" in label:
            return RegimeCategory.STABLE
        if "chaos" in label:
            return RegimeCategory.CHAOS

    return RegimeCategory.TREND


def compute_regime_half_life(
    adaptive_result: AdaptiveHalfLifeResult | None = None,
    regime_type: RegimeType | None = None,
    regime_label: str | None = None,
    config: RegimeHalfLifeConfig | None = None,
) -> RegimeHalfLifeResult:
    """Compute regime-adjusted half-life from adaptive result and regime.

    Composition: final = volatility_adjusted_half_life × regime_multiplier
    Clamped to [min_half_life, max_half_life].
    """
    cfg = config or RegimeHalfLifeConfig()

    if not cfg.enabled:
        vol_hl = (
            adaptive_result.computed_half_life
            if adaptive_result is not None and adaptive_result.applied
            else cfg.base_half_life
        )
        return RegimeHalfLifeResult(
            final_half_life=vol_hl,
            base_half_life=cfg.base_half_life,
            volatility_half_life=vol_hl,
            applied=False,
            reason_if_not_applied="regime half-life disabled",
        )

    if adaptive_result is not None and adaptive_result.applied:
        vol_hl = adaptive_result.computed_half_life
        volatility = adaptive_result.volatility
    else:
        vol_hl = cfg.base_half_life
        volatility = 0.0

    category = classify_regime_category(regime_type, regime_label)
    multiplier = cfg.regime_multipliers.get(category, 1.0)

    raw = vol_hl * multiplier
    clamped = max(cfg.min_half_life, min(cfg.max_half_life, int(round(raw))))

    regime_str = ""
    if regime_type is not None:
        regime_str = regime_type.value
    elif regime_label is not None:
        regime_str = regime_label

    return RegimeHalfLifeResult(
        final_half_life=clamped,
        base_half_life=cfg.base_half_life,
        volatility_half_life=vol_hl,
        regime_multiplier=multiplier,
        regime=regime_str,
        regime_category=category.value,
        volatility=volatility,
        applied=True,
    )
