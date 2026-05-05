"""Adaptive dimension weighting — learns importance per dimension from outcome history.

Produces a bounded weighting vector over regime dimensions (trend, risk,
stability, urgency) based on how much each dimension discriminates
between successful and unsuccessful outcomes.

Learning mechanism:
    For each dimension, compute variance in bucket_scores across its values.
    Higher variance → dimension is more informative → higher weight.
    Normalize to sum=1.0, then clamp to [min_weight, max_weight].

Confidence blending:
    final_weight = learned_weight * confidence + default_weight * (1 - confidence)
    confidence = min(1.0, sample_count / required_samples)

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
No circular dependency: reads outcomes, never writes to scoring.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.runtime.attribution import (
    AttributionBucket,
    AttributionDimension,
    AttributionEngine,
)
from umh.runtime.outcome import StrategyOutcome
from umh.runtime.regime_aggregation import DimensionName

_DEFAULT_WEIGHT = 0.25
_MIN_WEIGHT = 0.10
_MAX_WEIGHT = 0.40
_DEFAULT_REQUIRED_SAMPLES = 20
_DEFAULT_CONFIDENCE_THRESHOLD = 0.3

_DIMENSION_TO_ATTRIBUTION: dict[DimensionName, AttributionDimension] = {
    DimensionName.TREND: AttributionDimension.TREND,
    DimensionName.RISK: AttributionDimension.RISK,
    DimensionName.STABILITY: AttributionDimension.STABILITY,
    DimensionName.URGENCY: AttributionDimension.URGENCY,
}


@dataclass(frozen=True)
class DimensionWeight:
    """Weight for a single dimension."""

    dimension: DimensionName
    weight: float = _DEFAULT_WEIGHT
    confidence: float = 0.0
    source: str = "default"

    def __post_init__(self) -> None:
        object.__setattr__(self, "weight", max(0.0, min(1.0, self.weight)))
        object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "weight": round(self.weight, 4),
            "confidence": round(self.confidence, 4),
            "source": self.source,
        }


@dataclass(frozen=True)
class DimensionWeightVector:
    """Complete weighting across all dimensions."""

    weights: dict[str, DimensionWeight]
    normalized: bool = False
    explanation: str = ""

    @property
    def is_uniform(self) -> bool:
        vals = [w.weight for w in self.weights.values()]
        if not vals:
            return True
        return max(vals) - min(vals) < 1e-9

    @property
    def is_learned(self) -> bool:
        return any(w.source == "learned" for w in self.weights.values())

    def get(self, dimension: DimensionName) -> DimensionWeight | None:
        return self.weights.get(dimension.value)

    def get_weight(self, dimension: DimensionName) -> float:
        w = self.weights.get(dimension.value)
        return w.weight if w is not None else _DEFAULT_WEIGHT

    def to_dict(self) -> dict[str, Any]:
        return {
            "weights": {k: v.to_dict() for k, v in sorted(self.weights.items())},
            "normalized": self.normalized,
            "explanation": self.explanation,
            "is_uniform": self.is_uniform,
            "is_learned": self.is_learned,
        }


def default_weight_vector() -> DimensionWeightVector:
    """Return uniform default weights (inv 250)."""
    weights = {
        dim.value: DimensionWeight(
            dimension=dim,
            weight=_DEFAULT_WEIGHT,
            confidence=0.0,
            source="default",
        )
        for dim in DimensionName
    }
    return DimensionWeightVector(
        weights=weights,
        normalized=True,
        explanation="uniform defaults: no outcome data",
    )


DEFAULT_WEIGHT_VECTOR = default_weight_vector()


# ── Learning from outcomes ────────────────────────────────────────────


def _compute_dimension_variance(buckets: list[AttributionBucket]) -> float:
    """Compute variance of bucket_scores for a dimension's buckets.

    Higher variance means the dimension discriminates more between contexts.
    """
    if len(buckets) < 2:
        return 0.0
    scores = [b.bucket_score for b in buckets]
    mean = sum(scores) / len(scores)
    return sum((s - mean) ** 2 for s in scores) / len(scores)


def _compute_dimension_range(buckets: list[AttributionBucket]) -> float:
    """Compute range of bucket_scores (max - min).

    Complementary to variance: captures spread without assuming distribution.
    """
    if len(buckets) < 2:
        return 0.0
    scores = [b.bucket_score for b in buckets]
    return max(scores) - min(scores)


def _compute_raw_importance(buckets: list[AttributionBucket]) -> float:
    """Combined importance score: mean of variance and range.

    Using both metrics makes the signal more robust than either alone.
    """
    variance = _compute_dimension_variance(buckets)
    score_range = _compute_dimension_range(buckets)
    return (variance + score_range) / 2.0


def _normalize_weights(
    raw: dict[DimensionName, float],
    min_weight: float = _MIN_WEIGHT,
    max_weight: float = _MAX_WEIGHT,
) -> dict[DimensionName, float]:
    """Normalize raw importance scores into bounded weights summing to 1.0.

    Iterative: normalize → clamp → renormalize until stable (max 10 rounds).
    """
    total = sum(raw.values())
    if total <= 0:
        return {dim: _DEFAULT_WEIGHT for dim in DimensionName}

    weights = {dim: raw[dim] / total for dim in raw}

    for _ in range(20):
        clamped = {dim: max(min_weight, min(max_weight, w)) for dim, w in weights.items()}
        clamp_total = sum(clamped.values())
        if clamp_total <= 0:
            return {dim: _DEFAULT_WEIGHT for dim in DimensionName}
        weights = {dim: clamped[dim] / clamp_total for dim in clamped}
        if all(min_weight - 1e-12 <= w <= max_weight + 1e-12 for w in weights.values()):
            break

    return weights


def _compute_confidence(
    buckets: list[AttributionBucket],
    required_samples: int,
) -> float:
    """Confidence based on sample coverage and consistency.

    sample_confidence: how many samples we have vs required
    consistency: 1 - coefficient_of_variation (lower variation in counts = more consistent)
    """
    if not buckets:
        return 0.0

    total_samples = sum(b.sample_count for b in buckets)
    sample_confidence = min(1.0, total_samples / max(1, required_samples))

    counts = [b.sample_count for b in buckets]
    mean_count = sum(counts) / len(counts) if counts else 0
    if mean_count > 0:
        std_dev = (sum((c - mean_count) ** 2 for c in counts) / len(counts)) ** 0.5
        cv = std_dev / mean_count
        consistency = max(0.0, min(1.0, 1.0 - cv))
    else:
        consistency = 0.0

    return sample_confidence * 0.7 + consistency * 0.3


def _blend_with_default(
    learned_weight: float,
    confidence: float,
    default_weight: float = _DEFAULT_WEIGHT,
) -> float:
    """Confidence-gated blending toward uniform default (inv 252)."""
    return learned_weight * confidence + default_weight * (1.0 - confidence)


@dataclass(frozen=True)
class WeightingConfig:
    """Configuration for the dimension weighting computation."""

    min_weight: float = _MIN_WEIGHT
    max_weight: float = _MAX_WEIGHT
    required_samples: int = _DEFAULT_REQUIRED_SAMPLES
    confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD

    def __post_init__(self) -> None:
        object.__setattr__(self, "min_weight", max(0.01, min(0.25, self.min_weight)))
        object.__setattr__(
            self, "max_weight", max(self.min_weight + 0.05, min(0.90, self.max_weight))
        )
        object.__setattr__(self, "required_samples", max(1, self.required_samples))
        object.__setattr__(
            self, "confidence_threshold", max(0.0, min(1.0, self.confidence_threshold))
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_weight": round(self.min_weight, 4),
            "max_weight": round(self.max_weight, 4),
            "required_samples": self.required_samples,
            "confidence_threshold": round(self.confidence_threshold, 4),
        }


DEFAULT_WEIGHTING_CONFIG = WeightingConfig()


def compute_dimension_weights(
    outcomes: list[StrategyOutcome],
    config: WeightingConfig | None = None,
) -> DimensionWeightVector:
    """Compute adaptive dimension weights from outcome history.

    Deterministic (inv 253). Missing data → uniform (inv 252).
    Weights bounded (inv 249). No dimension dominates (inv 251).
    """
    cfg = config or DEFAULT_WEIGHTING_CONFIG

    if not outcomes:
        return default_weight_vector()

    engine = AttributionEngine(required_samples=cfg.required_samples)
    record = engine.build_attribution(outcomes)

    dim_buckets: dict[DimensionName, list[AttributionBucket]] = {dim: [] for dim in DimensionName}
    for bucket in record.dimension_buckets:
        for dim_name, attr_dim in _DIMENSION_TO_ATTRIBUTION.items():
            if bucket.dimension is attr_dim:
                dim_buckets[dim_name].append(bucket)

    raw_importance: dict[DimensionName, float] = {}
    confidences: dict[DimensionName, float] = {}

    for dim in DimensionName:
        buckets = dim_buckets[dim]
        raw_importance[dim] = _compute_raw_importance(buckets)
        confidences[dim] = _compute_confidence(buckets, cfg.required_samples)

    all_zero = all(v == 0.0 for v in raw_importance.values())
    if all_zero:
        return DimensionWeightVector(
            weights={
                dim.value: DimensionWeight(
                    dimension=dim,
                    weight=_DEFAULT_WEIGHT,
                    confidence=confidences[dim],
                    source="default",
                )
                for dim in DimensionName
            },
            normalized=True,
            explanation="all dimensions equally informative: using defaults",
        )

    normalized = _normalize_weights(raw_importance, cfg.min_weight, cfg.max_weight)

    final_weights: dict[str, DimensionWeight] = {}
    explanation_parts: list[str] = []

    for dim in sorted(DimensionName, key=lambda d: d.value):
        conf = confidences[dim]
        learned_w = normalized[dim]

        if conf < cfg.confidence_threshold:
            final_w = _DEFAULT_WEIGHT
            source = "default"
            explanation_parts.append(
                f"{dim.value}={final_w:.3f}(default, confidence={conf:.2f}<{cfg.confidence_threshold:.2f})"
            )
        else:
            final_w = _blend_with_default(learned_w, conf)
            source = "learned"
            explanation_parts.append(f"{dim.value}={final_w:.3f}(learned, confidence={conf:.2f})")

        final_weights[dim.value] = DimensionWeight(
            dimension=dim,
            weight=final_w,
            confidence=conf,
            source=source,
        )

    renorm_total = sum(w.weight for w in final_weights.values())
    if renorm_total > 0:
        renormalized: dict[str, DimensionWeight] = {}
        for key, dw in final_weights.items():
            new_w = dw.weight / renorm_total
            renormalized[key] = DimensionWeight(
                dimension=dw.dimension,
                weight=new_w,
                confidence=dw.confidence,
                source=dw.source,
            )
        final_weights = renormalized

    explanation = "; ".join(explanation_parts)

    return DimensionWeightVector(
        weights=final_weights,
        normalized=True,
        explanation=explanation,
    )
