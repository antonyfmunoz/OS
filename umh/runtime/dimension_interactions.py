"""Cross-dimension interaction factors — bounded pairwise modulation.

Captures non-linear interactions between regime dimensions that linear
aggregation misses. For example, high trend + high risk is worse than
either alone; high urgency + low stability compounds danger.

Design constraints:
    - Sparse: max 3 active interaction pairs (no combinatorial explosion)
    - Bounded: interaction_factor ∈ [0.9, 1.1] (cannot dominate)
    - Deterministic: same inputs → same output
    - Explainable: every active pair documented in result

Interaction rules map (dimension_a, dimension_b) → condition → factor.
Conditions are evaluated against DimensionRegime direction/strength.
Only non-neutral factors count as active. Top N by |factor - 1.0|
are selected; their product is clamped to [0.9, 1.1].

Pure computation — no I/O, no child processes.
No imports from cell, environment, or adapter layers.
No circular dependency: reads regime_aggregation types only.
Never mutates input data (inv 311).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.runtime.regime_aggregation import (
    DimensionName,
    DimensionRegime,
    DirectionCategory,
)

_INTERACTION_FACTOR_MIN: float = 0.9
_INTERACTION_FACTOR_MAX: float = 1.1
_DEFAULT_MAX_ACTIVE_PAIRS: int = 3
_NEUTRAL_FACTOR: float = 1.0


class InteractionDirection(Enum):
    """Simplified direction for interaction rule matching."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    ANY = "any"


@dataclass(frozen=True)
class InteractionRule:
    """A single interaction rule: when dim_a and dim_b match directions, apply factor."""

    dim_a: DimensionName
    dim_b: DimensionName
    dir_a: InteractionDirection
    dir_b: InteractionDirection
    factor: float = 1.0
    label: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "factor",
            max(_INTERACTION_FACTOR_MIN, min(_INTERACTION_FACTOR_MAX, self.factor)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dim_a": self.dim_a.value,
            "dim_b": self.dim_b.value,
            "dir_a": self.dir_a.value,
            "dir_b": self.dir_b.value,
            "factor": round(self.factor, 4),
            "label": self.label,
        }


_DEFAULT_INTERACTION_RULES: list[InteractionRule] = [
    InteractionRule(
        dim_a=DimensionName.TREND,
        dim_b=DimensionName.RISK,
        dir_a=InteractionDirection.POSITIVE,
        dir_b=InteractionDirection.NEGATIVE,
        factor=0.95,
        label="trend_up+high_risk→caution",
    ),
    InteractionRule(
        dim_a=DimensionName.TREND,
        dim_b=DimensionName.RISK,
        dir_a=InteractionDirection.POSITIVE,
        dir_b=InteractionDirection.POSITIVE,
        factor=1.05,
        label="trend_up+low_risk→boost",
    ),
    InteractionRule(
        dim_a=DimensionName.STABILITY,
        dim_b=DimensionName.URGENCY,
        dir_a=InteractionDirection.NEGATIVE,
        dir_b=InteractionDirection.NEGATIVE,
        factor=0.9,
        label="low_stability+high_urgency→danger",
    ),
    InteractionRule(
        dim_a=DimensionName.STABILITY,
        dim_b=DimensionName.URGENCY,
        dir_a=InteractionDirection.POSITIVE,
        dir_b=InteractionDirection.NEGATIVE,
        factor=1.05,
        label="high_stability+high_urgency→confident",
    ),
]


@dataclass(frozen=True)
class InteractionConfig:
    """Configuration for cross-dimension interactions."""

    enabled: bool = False
    max_active_pairs: int = _DEFAULT_MAX_ACTIVE_PAIRS
    rules: tuple[InteractionRule, ...] = ()
    strength_threshold: float = 0.3

    def __post_init__(self) -> None:
        object.__setattr__(self, "max_active_pairs", max(1, min(6, self.max_active_pairs)))
        object.__setattr__(self, "strength_threshold", max(0.0, min(1.0, self.strength_threshold)))
        if not self.rules:
            object.__setattr__(self, "rules", tuple(_DEFAULT_INTERACTION_RULES))

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "max_active_pairs": self.max_active_pairs,
            "rules": [r.to_dict() for r in self.rules],
            "strength_threshold": round(self.strength_threshold, 4),
        }


DEFAULT_INTERACTION_CONFIG = InteractionConfig()


@dataclass(frozen=True)
class ActiveInteraction:
    """A single activated interaction pair with its computed factor."""

    rule: InteractionRule
    dim_a_regime: DimensionRegime
    dim_b_regime: DimensionRegime
    raw_factor: float = 1.0
    strength_weight: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "raw_factor",
            max(_INTERACTION_FACTOR_MIN, min(_INTERACTION_FACTOR_MAX, self.raw_factor)),
        )
        object.__setattr__(self, "strength_weight", max(0.0, min(1.0, self.strength_weight)))

    @property
    def deviation(self) -> float:
        return abs(self.raw_factor - _NEUTRAL_FACTOR)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule.to_dict(),
            "dim_a_strength": round(self.dim_a_regime.strength, 4),
            "dim_b_strength": round(self.dim_b_regime.strength, 4),
            "raw_factor": round(self.raw_factor, 4),
            "strength_weight": round(self.strength_weight, 4),
            "deviation": round(self.deviation, 4),
        }


@dataclass(frozen=True)
class InteractionResult:
    """Result of cross-dimension interaction computation."""

    interaction_factor: float = 1.0
    raw_product: float = 1.0
    active_interactions: tuple[ActiveInteraction, ...] = ()
    total_rules_evaluated: int = 0
    total_rules_matched: int = 0
    clamped: bool = False
    explanation: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "interaction_factor",
            max(_INTERACTION_FACTOR_MIN, min(_INTERACTION_FACTOR_MAX, self.interaction_factor)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "interaction_factor": round(self.interaction_factor, 4),
            "raw_product": round(self.raw_product, 6),
            "active_interactions": [a.to_dict() for a in self.active_interactions],
            "total_rules_evaluated": self.total_rules_evaluated,
            "total_rules_matched": self.total_rules_matched,
            "clamped": self.clamped,
            "explanation": self.explanation,
        }


def _direction_matches(
    regime_direction: DirectionCategory,
    rule_direction: InteractionDirection,
) -> bool:
    """Check if a regime's direction matches a rule's required direction."""
    if rule_direction is InteractionDirection.ANY:
        return True
    if rule_direction is InteractionDirection.POSITIVE:
        return regime_direction is DirectionCategory.POSITIVE
    if rule_direction is InteractionDirection.NEGATIVE:
        return regime_direction is DirectionCategory.NEGATIVE
    return False


def _evaluate_rule(
    rule: InteractionRule,
    regimes: dict[DimensionName, DimensionRegime],
    strength_threshold: float,
) -> ActiveInteraction | None:
    """Evaluate a single interaction rule against current dimension regimes.

    Returns ActiveInteraction if both dimensions match, None otherwise.
    """
    regime_a = regimes.get(rule.dim_a)
    regime_b = regimes.get(rule.dim_b)

    if regime_a is None or regime_b is None:
        return None

    if not _direction_matches(regime_a.direction, rule.dir_a):
        return None
    if not _direction_matches(regime_b.direction, rule.dir_b):
        return None

    combined_strength = min(regime_a.strength, regime_b.strength)
    if combined_strength < strength_threshold:
        return None

    strength_weight = combined_strength
    weighted_factor = _NEUTRAL_FACTOR + (rule.factor - _NEUTRAL_FACTOR) * strength_weight

    return ActiveInteraction(
        rule=rule,
        dim_a_regime=regime_a,
        dim_b_regime=regime_b,
        raw_factor=weighted_factor,
        strength_weight=strength_weight,
    )


def compute_interaction_factor(
    dimension_regimes: dict[DimensionName, DimensionRegime] | None = None,
    config: InteractionConfig | None = None,
) -> InteractionResult:
    """Compute cross-dimension interaction factor.

    Evaluates all rules, selects top N by deviation from 1.0,
    computes product, clamps to [0.9, 1.1].

    Deterministic (inv 306). No mutation (inv 311). Bounded (inv 303).
    Missing inputs → 1.0 (inv 308). Sparse (inv 305). Explainable (inv 309).
    """
    cfg = config or DEFAULT_INTERACTION_CONFIG

    if not cfg.enabled:
        return InteractionResult(
            interaction_factor=_NEUTRAL_FACTOR,
            raw_product=_NEUTRAL_FACTOR,
            total_rules_evaluated=0,
            explanation="interactions disabled",
        )

    regimes = dimension_regimes or {}

    if not regimes:
        return InteractionResult(
            interaction_factor=_NEUTRAL_FACTOR,
            raw_product=_NEUTRAL_FACTOR,
            total_rules_evaluated=len(cfg.rules),
            explanation="no dimension regimes provided: neutral",
        )

    matched: list[ActiveInteraction] = []

    for rule in cfg.rules:
        result = _evaluate_rule(rule, regimes, cfg.strength_threshold)
        if result is not None and result.deviation > 0.0001:
            matched.append(result)

    total_matched = len(matched)

    if not matched:
        return InteractionResult(
            interaction_factor=_NEUTRAL_FACTOR,
            raw_product=_NEUTRAL_FACTOR,
            total_rules_evaluated=len(cfg.rules),
            total_rules_matched=0,
            explanation="no rules matched: neutral",
        )

    matched.sort(key=lambda a: a.deviation, reverse=True)
    selected = matched[: cfg.max_active_pairs]

    raw_product = _NEUTRAL_FACTOR
    for active in selected:
        raw_product *= active.raw_factor

    clamped = raw_product < _INTERACTION_FACTOR_MIN or raw_product > _INTERACTION_FACTOR_MAX
    final_factor = max(_INTERACTION_FACTOR_MIN, min(_INTERACTION_FACTOR_MAX, raw_product))

    parts = []
    for active in selected:
        parts.append(f"{active.rule.label}={active.raw_factor:.4f}")
    parts.append(f"product={raw_product:.6f}")
    if clamped:
        parts.append(f"clamped={final_factor:.4f}")
    parts.append(f"matched={total_matched}/{len(cfg.rules)}")
    parts.append(f"active={len(selected)}/{cfg.max_active_pairs}")

    return InteractionResult(
        interaction_factor=final_factor,
        raw_product=raw_product,
        active_interactions=tuple(selected),
        total_rules_evaluated=len(cfg.rules),
        total_rules_matched=total_matched,
        clamped=clamped,
        explanation="; ".join(parts),
    )
