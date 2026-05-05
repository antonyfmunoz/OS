"""Attribution-guided feedback coupling — bounded, explainable influence.

Converts contextual attribution into confidence-gated feedback factors.
Opt-in only — disabled by default. Returns neutral (1.0) unless explicitly
enabled with sufficient confidence.

Correlation-based, not causal. Observational attribution only.

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal

from umh.runtime.attribution import (
    AttributionBucket,
    AttributionDimension,
    ContextAttributionRecord,
)


EPSILON: float = 1e-9


def is_greater(a: float, b: float, epsilon: float = EPSILON) -> bool:
    return a > b + epsilon


def is_less(a: float, b: float, epsilon: float = EPSILON) -> bool:
    return a < b - epsilon


def is_equal(a: float, b: float, epsilon: float = EPSILON) -> bool:
    return abs(a - b) <= epsilon


def compare_scores(
    a: float, b: float, epsilon: float = EPSILON
) -> Literal["greater", "less", "equal"]:
    if a > b + epsilon:
        return "greater"
    if a < b - epsilon:
        return "less"
    return "equal"


class CouplingDirection(Enum):
    BOOST = "boost"
    PENALIZE = "penalize"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class AttributionFeedbackPolicy:
    """Policy controlling attribution-to-feedback coupling."""

    enabled: bool = False
    min_confidence: float = 0.5
    max_boost: float = 0.08
    max_penalty: float = 0.08
    neutral_factor: float = 1.0
    required_samples: int = 20

    def __post_init__(self) -> None:
        object.__setattr__(self, "min_confidence", max(0.0, min(1.0, self.min_confidence)))
        object.__setattr__(self, "max_boost", max(0.0, min(0.20, self.max_boost)))
        object.__setattr__(self, "max_penalty", max(0.0, min(0.20, self.max_penalty)))
        object.__setattr__(self, "required_samples", max(1, self.required_samples))

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "min_confidence": round(self.min_confidence, 4),
            "max_boost": round(self.max_boost, 4),
            "max_penalty": round(self.max_penalty, 4),
            "neutral_factor": round(self.neutral_factor, 4),
            "required_samples": self.required_samples,
        }


@dataclass(frozen=True)
class AttributionFeedbackResult:
    """Result of computing attribution-guided feedback."""

    factor: float = 1.0
    confidence: float = 0.0
    direction: CouplingDirection = CouplingDirection.NEUTRAL
    reason: str = ""
    strongest_positive_dimension: str = ""
    strongest_negative_dimension: str = ""
    enabled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "factor", max(0.0, min(2.0, self.factor)))
        object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor": round(self.factor, 4),
            "confidence": round(self.confidence, 4),
            "direction": self.direction.value,
            "reason": self.reason,
            "strongest_positive_dimension": self.strongest_positive_dimension,
            "strongest_negative_dimension": self.strongest_negative_dimension,
            "enabled": self.enabled,
        }


@dataclass(frozen=True)
class CombinedFeedbackResult:
    """Result of combining base feedback with attribution feedback."""

    combined_factor: float = 1.0
    base_factor: float = 1.0
    attribution_factor: float = 1.0
    reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "combined_factor", max(0.0, min(2.0, self.combined_factor)))
        object.__setattr__(self, "base_factor", max(0.0, min(2.0, self.base_factor)))
        object.__setattr__(self, "attribution_factor", max(0.0, min(2.0, self.attribution_factor)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "combined_factor": round(self.combined_factor, 4),
            "base_factor": round(self.base_factor, 4),
            "attribution_factor": round(self.attribution_factor, 4),
            "reason": self.reason,
        }


def _find_strongest_positive(
    buckets: tuple[AttributionBucket, ...],
    overall_score: float,
) -> AttributionBucket | None:
    candidates = [
        b
        for b in buckets
        if b.sample_count > 0
        and b.dimension != AttributionDimension.STRATEGY
        and is_greater(b.bucket_score, overall_score)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda b: b.bucket_score)


def _find_strongest_negative(
    buckets: tuple[AttributionBucket, ...],
    overall_score: float,
) -> AttributionBucket | None:
    candidates = [
        b
        for b in buckets
        if b.sample_count > 0
        and b.dimension != AttributionDimension.STRATEGY
        and is_less(b.bucket_score, overall_score)
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda b: b.bucket_score)


def _compute_combined_confidence(
    record: ContextAttributionRecord,
    bucket: AttributionBucket | None,
) -> float:
    if bucket is None:
        return record.confidence
    return min(record.confidence, bucket.confidence)


def compute_attribution_feedback_factor(
    attribution_record: ContextAttributionRecord | None,
    policy: AttributionFeedbackPolicy | None = None,
) -> AttributionFeedbackResult:
    p = policy or AttributionFeedbackPolicy()

    if not p.enabled:
        return AttributionFeedbackResult(
            factor=p.neutral_factor,
            confidence=0.0,
            direction=CouplingDirection.NEUTRAL,
            reason="attribution coupling disabled",
            enabled=False,
        )

    if attribution_record is None:
        return AttributionFeedbackResult(
            factor=p.neutral_factor,
            confidence=0.0,
            direction=CouplingDirection.NEUTRAL,
            reason="no attribution data available",
            enabled=True,
        )

    if not attribution_record.dimension_buckets:
        return AttributionFeedbackResult(
            factor=p.neutral_factor,
            confidence=0.0,
            direction=CouplingDirection.NEUTRAL,
            reason="attribution record has no dimension buckets",
            enabled=True,
        )

    positive = _find_strongest_positive(
        attribution_record.dimension_buckets,
        attribution_record.overall_score,
    )
    negative = _find_strongest_negative(
        attribution_record.dimension_buckets,
        attribution_record.overall_score,
    )

    driving_bucket = positive if positive is not None else negative
    if driving_bucket is None:
        return AttributionFeedbackResult(
            factor=p.neutral_factor,
            confidence=attribution_record.confidence,
            direction=CouplingDirection.NEUTRAL,
            reason=f"no meaningful dimension deviation from overall_score={attribution_record.overall_score:.2f}",
            strongest_positive_dimension=_bucket_label(positive),
            strongest_negative_dimension=_bucket_label(negative),
            enabled=True,
        )

    combined_conf = _compute_combined_confidence(attribution_record, driving_bucket)

    if combined_conf < p.min_confidence:
        return AttributionFeedbackResult(
            factor=p.neutral_factor,
            confidence=combined_conf,
            direction=CouplingDirection.NEUTRAL,
            reason=f"confidence {combined_conf:.2f} below threshold {p.min_confidence:.2f}",
            strongest_positive_dimension=_bucket_label(positive),
            strongest_negative_dimension=_bucket_label(negative),
            enabled=True,
        )

    deviation = driving_bucket.bucket_score - attribution_record.overall_score

    if deviation > 0:
        raw_delta = min(p.max_boost, deviation * 0.5)
        direction = CouplingDirection.BOOST
    elif deviation < 0:
        raw_delta = max(-p.max_penalty, deviation * 0.5)
        direction = CouplingDirection.PENALIZE
    else:
        raw_delta = 0.0
        direction = CouplingDirection.NEUTRAL

    scaled_delta = raw_delta * combined_conf
    factor = p.neutral_factor + scaled_delta
    factor = max(p.neutral_factor - p.max_penalty, min(p.neutral_factor + p.max_boost, factor))

    pos_label = _bucket_label(positive)
    neg_label = _bucket_label(negative)

    reason = (
        f"{direction.value}: "
        f"deviation={deviation:.4f}, "
        f"confidence={combined_conf:.2f}, "
        f"factor={factor:.4f}"
    )
    if pos_label:
        reason += f", positive={pos_label}"
    if neg_label:
        reason += f", negative={neg_label}"

    return AttributionFeedbackResult(
        factor=factor,
        confidence=combined_conf,
        direction=direction,
        reason=reason,
        strongest_positive_dimension=pos_label,
        strongest_negative_dimension=neg_label,
        enabled=True,
    )


def _bucket_label(bucket: AttributionBucket | None) -> str:
    if bucket is None:
        return ""
    return f"{bucket.dimension.value}={bucket.value}"


def combine_feedback_factors(
    base_feedback_factor: float,
    attribution_factor: float,
    max_combined_boost: float = 0.12,
    max_combined_penalty: float = 0.12,
) -> CombinedFeedbackResult:
    max_combined_boost = max(0.0, min(0.25, max_combined_boost))
    max_combined_penalty = max(0.0, min(0.25, max_combined_penalty))

    if attribution_factor == 1.0:
        return CombinedFeedbackResult(
            combined_factor=base_feedback_factor,
            base_factor=base_feedback_factor,
            attribution_factor=attribution_factor,
            reason=f"attribution neutral; combined={base_feedback_factor:.4f} (base only)",
        )

    raw = base_feedback_factor * attribution_factor
    clamped = max(1.0 - max_combined_penalty, min(1.0 + max_combined_boost, raw))

    reason = (
        f"base={base_feedback_factor:.4f} × attribution={attribution_factor:.4f} "
        f"= {raw:.4f}, clamped to {clamped:.4f} "
        f"[{1.0 - max_combined_penalty:.2f}, {1.0 + max_combined_boost:.2f}]"
    )

    return CombinedFeedbackResult(
        combined_factor=clamped,
        base_factor=base_feedback_factor,
        attribution_factor=attribution_factor,
        reason=reason,
    )
