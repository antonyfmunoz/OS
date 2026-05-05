"""Context-aware weight adaptation — dynamic tradeoff weight adjustment.

Adjusts tradeoff dimension weights based on ExecutionContext signals
using deterministic, bounded rules. No state mutation, no randomness.

Adaptation rules:
    high urgency → boost latency/speed dimensions
    high risk → boost success/stability dimensions
    high resource_pressure → boost efficiency dimensions
    stability_mode → compress all weights toward 1.0

Weight multiplier bounds: [_MIN_MULTIPLIER, _MAX_MULTIPLIER]

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from umh.runtime.context import ExecutionContext
    from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile


_MIN_MULTIPLIER = 0.5
_MAX_MULTIPLIER = 2.0
_URGENCY_STRENGTH = 0.6
_RISK_STRENGTH = 0.6
_PRESSURE_STRENGTH = 0.4
_STABILITY_DAMPENING = 0.5

_URGENCY_KEYWORDS = frozenset({"latency", "speed", "time", "fast", "quick", "urgent"})
_RISK_KEYWORDS = frozenset({"success", "stability", "safety", "reliable", "quality", "risk"})
_PRESSURE_KEYWORDS = frozenset({"efficiency", "cost", "resource", "effort", "budget", "cheap"})


@dataclass(frozen=True)
class WeightAdjustment:
    """Result of adapting a single dimension's weight."""

    dimension_name: str
    base_weight: float
    multiplier: float
    adjusted_weight: float
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_name": self.dimension_name,
            "base_weight": round(self.base_weight, 4),
            "multiplier": round(self.multiplier, 4),
            "adjusted_weight": round(self.adjusted_weight, 4),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class WeightAdaptationResult:
    """Complete weight adaptation output for a profile."""

    adjustments: tuple[WeightAdjustment, ...]
    context_summary: str
    any_changed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "adjustments": [a.to_dict() for a in self.adjustments],
            "context_summary": self.context_summary,
            "any_changed": self.any_changed,
        }

    @property
    def adjusted_weights(self) -> dict[str, float]:
        return {a.dimension_name: a.adjusted_weight for a in self.adjustments}


class WeightAdapter:
    """Adapts tradeoff dimension weights based on execution context.

    Deterministic, bounded, pure. No state mutation.
    Each context signal applies a multiplier to matching dimensions.
    Stability mode dampens all deviations toward 1.0.
    """

    def __init__(
        self,
        *,
        urgency_keywords: frozenset[str] | None = None,
        risk_keywords: frozenset[str] | None = None,
        pressure_keywords: frozenset[str] | None = None,
    ) -> None:
        self._urgency_kw = urgency_keywords or _URGENCY_KEYWORDS
        self._risk_kw = risk_keywords or _RISK_KEYWORDS
        self._pressure_kw = pressure_keywords or _PRESSURE_KEYWORDS

    @property
    def urgency_keywords(self) -> frozenset[str]:
        return self._urgency_kw

    @property
    def risk_keywords(self) -> frozenset[str]:
        return self._risk_kw

    @property
    def pressure_keywords(self) -> frozenset[str]:
        return self._pressure_kw

    def adjust(
        self,
        profile: TradeoffProfile,
        context: ExecutionContext,
    ) -> WeightAdaptationResult:
        """Adjust dimension weights based on context. Pure, no side effects."""
        adjustments: list[WeightAdjustment] = []
        any_changed = False

        for dim in profile.dimensions:
            multiplier, reasons = self._compute_multiplier(dim, context)

            if context.stability_mode > 0.0:
                deviation = multiplier - 1.0
                dampened = deviation * (1.0 - context.stability_mode * _STABILITY_DAMPENING)
                multiplier = 1.0 + dampened
                if abs(deviation) > 1e-9:
                    reasons = (*reasons, f"stability dampened ({context.stability_mode:.2f})")

            multiplier = max(_MIN_MULTIPLIER, min(_MAX_MULTIPLIER, multiplier))
            adjusted = dim.weight * multiplier

            if abs(multiplier - 1.0) > 1e-6:
                any_changed = True

            adjustments.append(
                WeightAdjustment(
                    dimension_name=dim.name,
                    base_weight=dim.weight,
                    multiplier=multiplier,
                    adjusted_weight=adjusted,
                    reasons=reasons if reasons else ("no adjustment",),
                )
            )

        summary = self._build_summary(context, any_changed)

        return WeightAdaptationResult(
            adjustments=tuple(adjustments),
            context_summary=summary,
            any_changed=any_changed,
        )

    def _compute_multiplier(
        self,
        dim: TradeoffDimension,
        context: ExecutionContext,
    ) -> tuple[float, tuple[str, ...]]:
        """Compute the raw multiplier for a single dimension."""
        name_lower = dim.name.lower()
        multiplier = 1.0
        reasons: list[str] = []

        urgency_delta = context.urgency - 0.5
        if abs(urgency_delta) > 0.05 and self._matches_keywords(name_lower, self._urgency_kw):
            boost = urgency_delta * _URGENCY_STRENGTH
            multiplier += boost
            direction = "boosted" if boost > 0 else "reduced"
            reasons.append(f"urgency {direction} ({context.urgency:.2f})")

        risk_delta = context.risk_level - 0.5
        if abs(risk_delta) > 0.05 and self._matches_keywords(name_lower, self._risk_kw):
            boost = risk_delta * _RISK_STRENGTH
            multiplier += boost
            direction = "boosted" if boost > 0 else "reduced"
            reasons.append(f"risk {direction} ({context.risk_level:.2f})")

        pressure_delta = context.resource_pressure - 0.5
        if abs(pressure_delta) > 0.05 and self._matches_keywords(name_lower, self._pressure_kw):
            boost = pressure_delta * _PRESSURE_STRENGTH
            multiplier += boost
            direction = "boosted" if boost > 0 else "reduced"
            reasons.append(f"pressure {direction} ({context.resource_pressure:.2f})")

        return multiplier, tuple(reasons)

    def _matches_keywords(self, name: str, keywords: frozenset[str]) -> bool:
        """Check if a dimension name contains any keyword."""
        for kw in keywords:
            if kw in name:
                return True
        return False

    def _build_summary(self, context: ExecutionContext, any_changed: bool) -> str:
        parts: list[str] = []

        if context.is_neutral:
            return "neutral context; no weight adjustments"

        if context.urgency > 0.7:
            parts.append("high urgency")
        elif context.urgency < 0.3:
            parts.append("low urgency")

        if context.risk_level > 0.7:
            parts.append("high risk")
        elif context.risk_level < 0.3:
            parts.append("low risk")

        if context.resource_pressure > 0.7:
            parts.append("high resource pressure")
        elif context.resource_pressure < 0.3:
            parts.append("low resource pressure")

        if context.stability_mode > 0.5:
            parts.append("stability mode active")

        if not any_changed:
            parts.append("no matching dimensions")

        return "; ".join(parts) if parts else "moderate context; minor adjustments"


def apply_context_weights(
    profile: TradeoffProfile,
    context: ExecutionContext,
    adapter: WeightAdapter | None = None,
) -> tuple[TradeoffProfile, WeightAdaptationResult]:
    """Apply context-aware weight adaptation to a profile.

    Returns (adjusted_profile, adaptation_result).
    The adjusted profile has the same dimensions but with modified weights.
    """
    from umh.runtime.context import ExecutionContext as _EC
    from umh.runtime.tradeoff import TradeoffDimension, TradeoffProfile

    if adapter is None:
        adapter = WeightAdapter()

    result = adapter.adjust(profile, context)

    if not result.any_changed:
        return profile, result

    new_dims: list[TradeoffDimension] = []
    for adj in result.adjustments:
        original = None
        for d in profile.dimensions:
            if d.name == adj.dimension_name:
                original = d
                break

        if original is not None:
            new_dims.append(
                TradeoffDimension(
                    name=original.name,
                    direction=original.direction,
                    weight=adj.adjusted_weight,
                    tolerance=original.tolerance,
                )
            )

    adjusted_profile = TradeoffProfile(
        dimensions=tuple(new_dims),
        name=f"{profile.name}_adapted" if profile.name else "adapted",
    )

    return adjusted_profile, result
