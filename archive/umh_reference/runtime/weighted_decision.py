"""Weighted decision influence — bounded bias from learned dimension weights.

Applies dimension weights (Phase 60) and aggregated regime state (Phase 59)
as a gentle, bounded influence on strategy scoring.  Base score remains
primary authority (inv 257).  Influence is bounded (inv 258), confidence-
gated (inv 259), and no single dimension may dominate (inv 260).

Computation:
    For each dimension:
        signal_strength = regime.strength * regime.confidence
        weighted_contribution = signal_strength * dimension_weight
    raw_weight_factor = sum(weighted_contributions)
    Normalize into [1 - max_influence, 1 + max_influence].
    Confidence gate: overall confidence < threshold → factor = 1.0.

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
No circular dependency: reads weights and regime, never writes to scoring.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.runtime.dimension_weighting import (
    DEFAULT_WEIGHT_VECTOR,
    DimensionWeightVector,
)
from umh.runtime.regime_aggregation import (
    AggregatedRegimeState,
    DimensionName,
    DirectionCategory,
    NEUTRAL_AGGREGATED,
)

_DEFAULT_MAX_INFLUENCE: float = 0.10
_DEFAULT_MIN_CONFIDENCE: float = 0.60


@dataclass(frozen=True)
class WeightedDecisionPolicy:
    """Policy controlling weighted decision influence."""

    enabled: bool = False
    max_weight_influence: float = _DEFAULT_MAX_INFLUENCE
    min_confidence: float = _DEFAULT_MIN_CONFIDENCE

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_weight_influence",
            max(0.0, min(0.50, self.max_weight_influence)),
        )
        object.__setattr__(
            self,
            "min_confidence",
            max(0.0, min(1.0, self.min_confidence)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "max_weight_influence": round(self.max_weight_influence, 4),
            "min_confidence": round(self.min_confidence, 4),
        }


DEFAULT_WEIGHTED_DECISION_POLICY = WeightedDecisionPolicy()


@dataclass(frozen=True)
class WeightedDecisionResult:
    """Result of applying weighted decision influence to a single candidate."""

    strategy_id: str = ""
    base_score: float = 0.0
    weight_factor: float = 1.0
    final_score: float = 0.0
    used_weights: bool = False
    confidence_gated: bool = False
    explanation: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_score", max(0.0, self.base_score))
        object.__setattr__(self, "weight_factor", max(0.0, self.weight_factor))
        object.__setattr__(self, "final_score", max(0.0, self.final_score))

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "base_score": round(self.base_score, 4),
            "weight_factor": round(self.weight_factor, 4),
            "final_score": round(self.final_score, 4),
            "used_weights": self.used_weights,
            "confidence_gated": self.confidence_gated,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class WeightedDecisionBatchResult:
    """Result of applying weighted influence across all candidates."""

    results: tuple[WeightedDecisionResult, ...] = ()
    policy: WeightedDecisionPolicy = DEFAULT_WEIGHTED_DECISION_POLICY
    overall_confidence: float = 0.0
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": [r.to_dict() for r in self.results],
            "policy": self.policy.to_dict(),
            "overall_confidence": round(self.overall_confidence, 4),
            "explanation": self.explanation,
        }


# ── Core computation ─────────────────────────────────────────────────


def _direction_sign(direction: DirectionCategory) -> float:
    """Map direction to a sign: POSITIVE → +1, NEGATIVE → -1, NEUTRAL → 0."""
    if direction is DirectionCategory.POSITIVE:
        return 1.0
    if direction is DirectionCategory.NEGATIVE:
        return -1.0
    return 0.0


def _compute_overall_confidence(weights: DimensionWeightVector) -> float:
    """Mean confidence across all dimension weights."""
    if not weights.weights:
        return 0.0
    total = sum(w.confidence for w in weights.weights.values())
    return total / len(weights.weights)


def _compute_raw_weight_factor(
    weights: DimensionWeightVector,
    regime: AggregatedRegimeState,
) -> float:
    """Compute the raw signed weight factor from dimension weights and regime.

    For each dimension:
        signal_strength = regime.strength * regime.confidence
        weighted_contribution = signal_strength * dimension_weight * direction_sign
    Return sum of weighted_contributions.
    """
    total = 0.0
    for dim in DimensionName:
        dim_weight = weights.get_weight(dim)
        dim_regime = regime.get_or_neutral(dim)
        signal_strength = dim_regime.strength * dim_regime.confidence
        sign = _direction_sign(dim_regime.direction)
        total += signal_strength * dim_weight * sign
    return total


def _normalize_to_bounded_factor(
    raw: float,
    max_influence: float,
) -> float:
    """Normalize raw weight factor into [1 - max_influence, 1 + max_influence].

    raw is unbounded. Clamp to [-1, 1] then scale.
    """
    clamped = max(-1.0, min(1.0, raw))
    return 1.0 + clamped * max_influence


def compute_weight_factor(
    weights: DimensionWeightVector | None = None,
    regime: AggregatedRegimeState | None = None,
    policy: WeightedDecisionPolicy | None = None,
) -> tuple[float, bool, float, str]:
    """Compute the weight factor for decision influence.

    Returns (weight_factor, used_weights, overall_confidence, explanation).
    Deterministic (inv 262). Missing weights → neutral (inv 263).
    """
    pol = policy or DEFAULT_WEIGHTED_DECISION_POLICY

    if not pol.enabled:
        return 1.0, False, 0.0, "weighted influence disabled"

    w = weights or DEFAULT_WEIGHT_VECTOR
    r = regime or NEUTRAL_AGGREGATED

    overall_conf = _compute_overall_confidence(w)

    if overall_conf < pol.min_confidence:
        return (
            1.0,
            False,
            overall_conf,
            f"confidence {overall_conf:.2f} < threshold {pol.min_confidence:.2f}: gated to neutral",
        )

    raw = _compute_raw_weight_factor(w, r)
    factor = _normalize_to_bounded_factor(raw, pol.max_weight_influence)

    parts = []
    for dim in sorted(DimensionName, key=lambda d: d.value):
        dw = w.get_weight(dim)
        dr = r.get_or_neutral(dim)
        sign = _direction_sign(dr.direction)
        contrib = dr.strength * dr.confidence * dw * sign
        parts.append(f"{dim.value}={contrib:+.4f}")

    explanation = (
        f"raw={raw:.4f}, factor={factor:.4f}, "
        f"confidence={overall_conf:.2f}, "
        f"contributions=[{', '.join(parts)}]"
    )

    return factor, True, overall_conf, explanation


def apply_weighted_influence(
    strategy_ids: list[str],
    input_scores: list[float],
    weights: DimensionWeightVector | None = None,
    regime: AggregatedRegimeState | None = None,
    policy: WeightedDecisionPolicy | None = None,
) -> WeightedDecisionBatchResult:
    """Apply weighted decision influence to a list of candidates.

    The same weight_factor applies to all candidates — it biases based on
    the current regime context, not per-candidate features.
    This ensures no candidate crosses valid/safe boundaries (inv 260).

    Deterministic (inv 262). Missing → neutral (inv 263).
    Explainable (inv 264).
    """
    pol = policy or DEFAULT_WEIGHTED_DECISION_POLICY

    if not strategy_ids:
        return WeightedDecisionBatchResult(
            explanation="no strategies provided",
        )

    n = len(strategy_ids)
    scores = list(input_scores)
    if len(scores) < n:
        scores.extend([0.0] * (n - len(scores)))
    elif len(scores) > n:
        scores = scores[:n]

    factor, used, overall_conf, factor_explanation = compute_weight_factor(
        weights=weights,
        regime=regime,
        policy=pol,
    )

    results: list[WeightedDecisionResult] = []
    for i in range(n):
        final = scores[i] * factor
        results.append(
            WeightedDecisionResult(
                strategy_id=strategy_ids[i],
                base_score=scores[i],
                weight_factor=factor,
                final_score=final,
                used_weights=used,
                confidence_gated=not used and pol.enabled,
                explanation=factor_explanation,
            )
        )

    return WeightedDecisionBatchResult(
        results=tuple(results),
        policy=pol,
        overall_confidence=overall_conf,
        explanation=factor_explanation,
    )
