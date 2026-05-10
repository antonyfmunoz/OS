"""Signal profiles for adaptive temporal smoothing.

Defines per-signal smoothing characteristics based on volatility class.
Each signal gets a base alpha and adaptation parameters that control
how the smoothing factor responds to recent variance.

Volatility classes:
    low    — slow-changing signals (risk, stability) → base_alpha=0.3
    medium — moderate signals (resource_pressure)    → base_alpha=0.5
    high   — fast-changing signals (urgency)         → base_alpha=0.7

Alpha adaptation formula:
    delta = |current - previous|
    adjustment = (delta - 0.5) * adaptation_strength
    adapted_alpha = clamp(base_alpha + adjustment, _MIN_ALPHA, _MAX_ALPHA)

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MIN_ALPHA = 0.2
_MAX_ALPHA = 0.8

_VOLATILITY_BASE_ALPHA = {
    "low": 0.3,
    "medium": 0.5,
    "high": 0.7,
}

_DEFAULT_ADAPTATION_STRENGTH = 0.3
_DEFAULT_DELTA_MIDPOINT = 0.25


def _clamp_alpha(v: float) -> float:
    return max(_MIN_ALPHA, min(_MAX_ALPHA, v))


@dataclass(frozen=True)
class SignalProfile:
    """Per-signal smoothing configuration."""

    name: str
    volatility_class: str = "medium"
    base_alpha: float | None = None
    adaptation_strength: float = _DEFAULT_ADAPTATION_STRENGTH

    def __post_init__(self) -> None:
        if self.volatility_class not in _VOLATILITY_BASE_ALPHA:
            object.__setattr__(self, "volatility_class", "medium")

        if self.base_alpha is None:
            resolved = _VOLATILITY_BASE_ALPHA[self.volatility_class]
            object.__setattr__(self, "base_alpha", resolved)
        else:
            object.__setattr__(self, "base_alpha", _clamp_alpha(self.base_alpha))

        s = max(0.0, min(1.0, self.adaptation_strength))
        object.__setattr__(self, "adaptation_strength", s)

    @property
    def effective_base_alpha(self) -> float:
        return self.base_alpha if self.base_alpha is not None else 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "volatility_class": self.volatility_class,
            "base_alpha": round(self.effective_base_alpha, 4),
            "adaptation_strength": round(self.adaptation_strength, 4),
        }


DEFAULT_SIGNAL_PROFILES: dict[str, SignalProfile] = {
    "urgency": SignalProfile(name="urgency", volatility_class="high"),
    "risk_level": SignalProfile(name="risk_level", volatility_class="low"),
    "resource_pressure": SignalProfile(name="resource_pressure", volatility_class="medium"),
    "stability_mode": SignalProfile(name="stability_mode", volatility_class="low"),
}


@dataclass(frozen=True)
class AdaptedAlpha:
    """Result of adapting alpha for a single signal."""

    signal_name: str
    base_alpha: float
    delta: float
    adjustment: float
    adapted_alpha: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "base_alpha": round(self.base_alpha, 4),
            "delta": round(self.delta, 4),
            "adjustment": round(self.adjustment, 4),
            "adapted_alpha": round(self.adapted_alpha, 4),
        }


@dataclass(frozen=True)
class AdaptationSnapshot:
    """Complete per-signal alpha adaptation for one tick."""

    alphas: dict[str, AdaptedAlpha]
    tick: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "alphas": {k: v.to_dict() for k, v in sorted(self.alphas.items())},
            "tick": self.tick,
        }

    def get_alpha(self, signal_name: str) -> float:
        if signal_name in self.alphas:
            return self.alphas[signal_name].adapted_alpha
        return 0.5


def compute_adapted_alpha(
    profile: SignalProfile,
    current_value: float,
    previous_value: float,
) -> AdaptedAlpha:
    """Compute adapted alpha for a single signal based on recent delta.

    Large delta → increase alpha (be more responsive).
    Small delta → decrease alpha (be more stable).
    """
    delta = abs(current_value - previous_value)

    adjustment = (delta - _DEFAULT_DELTA_MIDPOINT) * profile.adaptation_strength
    base = profile.effective_base_alpha
    raw_alpha = base + adjustment
    adapted = _clamp_alpha(raw_alpha)

    return AdaptedAlpha(
        signal_name=profile.name,
        base_alpha=base,
        delta=delta,
        adjustment=adjustment,
        adapted_alpha=adapted,
    )


def compute_all_adapted_alphas(
    profiles: dict[str, SignalProfile],
    current_values: dict[str, float],
    previous_values: dict[str, float],
    tick: int = 0,
) -> AdaptationSnapshot:
    """Compute adapted alphas for all signals."""
    alphas: dict[str, AdaptedAlpha] = {}
    for name, profile in sorted(profiles.items()):
        curr = current_values.get(name, 0.5)
        prev = previous_values.get(name, 0.5)
        alphas[name] = compute_adapted_alpha(profile, curr, prev)

    return AdaptationSnapshot(alphas=alphas, tick=tick)
