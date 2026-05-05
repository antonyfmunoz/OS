"""Multi-signal regime aggregation — per-dimension regime classification and composite state.

Computes regime per dimension (trend, risk, stability, urgency) independently
across all signals, then aggregates into a composite state with alignment
and conflict scoring.

Key concepts:
    - DimensionRegime: regime classification for one dimension
    - AggregatedRegimeState: composite of all per-dimension regimes
    - alignment_score: how many dimensions agree directionally (0–1)
    - conflict_score: how many dimensions oppose (0–1)
    - dominant_dimension: strongest signal × confidence (deterministic)

Aggregation model: simple normalized counts — no weighted explosion.
Bounded [0, 1] for all scores. Deterministic, explainable.

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DimensionName(Enum):
    """The four regime dimensions."""

    TREND = "trend"
    RISK = "risk"
    STABILITY = "stability"
    URGENCY = "urgency"


class DirectionCategory(Enum):
    """Simplified directional bucket for alignment/conflict computation."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class DimensionRegime:
    """Regime classification for a single dimension."""

    dimension: DimensionName
    regime_label: str
    direction: DirectionCategory
    strength: float = 0.0
    confidence: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "strength", max(0.0, min(1.0, self.strength)))
        object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))

    @property
    def effective_strength(self) -> float:
        return self.strength * self.confidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "regime_label": self.regime_label,
            "direction": self.direction.value,
            "strength": round(self.strength, 4),
            "confidence": round(self.confidence, 4),
            "effective_strength": round(self.effective_strength, 4),
        }


_NEUTRAL_REGIME_LABEL = "neutral"


def _make_neutral(dim: DimensionName) -> DimensionRegime:
    return DimensionRegime(
        dimension=dim,
        regime_label=_NEUTRAL_REGIME_LABEL,
        direction=DirectionCategory.NEUTRAL,
        strength=0.0,
        confidence=0.0,
    )


NEUTRAL_TREND = _make_neutral(DimensionName.TREND)
NEUTRAL_RISK = _make_neutral(DimensionName.RISK)
NEUTRAL_STABILITY = _make_neutral(DimensionName.STABILITY)
NEUTRAL_URGENCY = _make_neutral(DimensionName.URGENCY)


# ── Per-dimension classification ──────────────────────────────────────


_TREND_DIRECTION_MAP: dict[str, DirectionCategory] = {
    "stable": DirectionCategory.NEUTRAL,
    "trend_up": DirectionCategory.POSITIVE,
    "trend_down": DirectionCategory.NEGATIVE,
    "spike_up": DirectionCategory.POSITIVE,
    "spike_down": DirectionCategory.NEGATIVE,
}

_TREND_STRENGTH_MAP: dict[str, float] = {
    "stable": 0.0,
    "trend_up": 0.5,
    "trend_down": 0.5,
    "spike_up": 1.0,
    "spike_down": 1.0,
}

_RISK_DIRECTION_MAP: dict[str, DirectionCategory] = {
    "low": DirectionCategory.POSITIVE,
    "medium": DirectionCategory.NEUTRAL,
    "high": DirectionCategory.NEGATIVE,
}

_RISK_STRENGTH_MAP: dict[str, float] = {
    "low": 0.2,
    "medium": 0.5,
    "high": 1.0,
}

_STABILITY_DIRECTION_MAP: dict[str, DirectionCategory] = {
    "high": DirectionCategory.POSITIVE,
    "medium": DirectionCategory.NEUTRAL,
    "low": DirectionCategory.NEGATIVE,
}

_STABILITY_STRENGTH_MAP: dict[str, float] = {
    "high": 0.2,
    "medium": 0.5,
    "low": 1.0,
}

_URGENCY_DIRECTION_MAP: dict[str, DirectionCategory] = {
    "low": DirectionCategory.POSITIVE,
    "medium": DirectionCategory.NEUTRAL,
    "high": DirectionCategory.NEGATIVE,
}

_URGENCY_STRENGTH_MAP: dict[str, float] = {
    "low": 0.2,
    "medium": 0.5,
    "high": 1.0,
}


def classify_dimension(
    dimension: DimensionName,
    regime_label: str,
    confidence: float = 1.0,
) -> DimensionRegime:
    """Classify a single dimension from its regime label.

    Deterministic, stateless. Unknown labels produce neutral.
    """
    label = regime_label.lower()
    conf = max(0.0, min(1.0, confidence))

    if dimension is DimensionName.TREND:
        direction = _TREND_DIRECTION_MAP.get(label, DirectionCategory.NEUTRAL)
        strength = _TREND_STRENGTH_MAP.get(label, 0.0)
    elif dimension is DimensionName.RISK:
        direction = _RISK_DIRECTION_MAP.get(label, DirectionCategory.NEUTRAL)
        strength = _RISK_STRENGTH_MAP.get(label, 0.0)
    elif dimension is DimensionName.STABILITY:
        direction = _STABILITY_DIRECTION_MAP.get(label, DirectionCategory.NEUTRAL)
        strength = _STABILITY_STRENGTH_MAP.get(label, 0.0)
    elif dimension is DimensionName.URGENCY:
        direction = _URGENCY_DIRECTION_MAP.get(label, DirectionCategory.NEUTRAL)
        strength = _URGENCY_STRENGTH_MAP.get(label, 0.0)
    else:
        direction = DirectionCategory.NEUTRAL
        strength = 0.0

    return DimensionRegime(
        dimension=dimension,
        regime_label=label if label in _all_known_labels(dimension) else _NEUTRAL_REGIME_LABEL,
        direction=direction,
        strength=strength,
        confidence=conf,
    )


def _all_known_labels(dimension: DimensionName) -> set[str]:
    if dimension is DimensionName.TREND:
        return set(_TREND_DIRECTION_MAP.keys())
    if dimension is DimensionName.RISK:
        return set(_RISK_DIRECTION_MAP.keys())
    if dimension is DimensionName.STABILITY:
        return set(_STABILITY_DIRECTION_MAP.keys())
    if dimension is DimensionName.URGENCY:
        return set(_URGENCY_DIRECTION_MAP.keys())
    return set()


# ── Aggregated regime state ───────────────────────────────────────────


@dataclass(frozen=True)
class AggregatedRegimeState:
    """Composite state from per-dimension regime classifications."""

    regimes: dict[str, DimensionRegime]
    dominant_dimension: DimensionName | None = None
    alignment_score: float = 0.0
    conflict_score: float = 0.0
    explanation: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "alignment_score", max(0.0, min(1.0, self.alignment_score)))
        object.__setattr__(self, "conflict_score", max(0.0, min(1.0, self.conflict_score)))

    def get(self, dimension: DimensionName) -> DimensionRegime | None:
        return self.regimes.get(dimension.value)

    def get_or_neutral(self, dimension: DimensionName) -> DimensionRegime:
        return self.regimes.get(dimension.value, _make_neutral(dimension))

    @property
    def is_aligned(self) -> bool:
        return self.alignment_score > self.conflict_score

    @property
    def is_conflicted(self) -> bool:
        return self.conflict_score > self.alignment_score

    @property
    def is_neutral(self) -> bool:
        return self.alignment_score == 0.0 and self.conflict_score == 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "regimes": {k: v.to_dict() for k, v in sorted(self.regimes.items())},
            "dominant_dimension": self.dominant_dimension.value
            if self.dominant_dimension
            else None,
            "alignment_score": round(self.alignment_score, 4),
            "conflict_score": round(self.conflict_score, 4),
            "explanation": self.explanation,
            "is_aligned": self.is_aligned,
            "is_conflicted": self.is_conflicted,
            "is_neutral": self.is_neutral,
        }


NEUTRAL_AGGREGATED = AggregatedRegimeState(
    regimes={
        DimensionName.TREND.value: NEUTRAL_TREND,
        DimensionName.RISK.value: NEUTRAL_RISK,
        DimensionName.STABILITY.value: NEUTRAL_STABILITY,
        DimensionName.URGENCY.value: NEUTRAL_URGENCY,
    },
    explanation="all dimensions neutral",
)


# ── Aggregation logic ─────────────────────────────────────────────────


def _compute_alignment_conflict(
    regimes: dict[str, DimensionRegime],
) -> tuple[float, float]:
    """Compute alignment and conflict from per-dimension directions.

    alignment = (count of dimensions agreeing with majority direction) / total
    conflict  = (count of dimensions opposing majority direction) / total

    Only non-neutral dimensions participate. All-neutral = (0.0, 0.0).
    """
    non_neutral: list[DirectionCategory] = [
        r.direction for r in regimes.values() if r.direction is not DirectionCategory.NEUTRAL
    ]

    if not non_neutral:
        return 0.0, 0.0

    total = len(non_neutral)
    pos_count = sum(1 for d in non_neutral if d is DirectionCategory.POSITIVE)
    neg_count = sum(1 for d in non_neutral if d is DirectionCategory.NEGATIVE)

    if pos_count == 0 and neg_count == 0:
        return 0.0, 0.0

    majority_count = max(pos_count, neg_count)
    minority_count = min(pos_count, neg_count)

    alignment = majority_count / total
    conflict = minority_count / total

    return alignment, conflict


def _select_dominant(
    regimes: dict[str, DimensionRegime],
) -> DimensionName | None:
    """Select dominant dimension by highest effective_strength.

    Tie-break: lexicographic by dimension name (ascending).
    Returns None if all effective_strengths are 0.
    """
    best_dim: DimensionName | None = None
    best_strength: float = 0.0

    for key in sorted(regimes.keys()):
        r = regimes[key]
        es = r.effective_strength
        if es > best_strength:
            best_strength = es
            best_dim = r.dimension
        elif es == best_strength and es > 0.0 and best_dim is not None:
            if r.dimension.value < best_dim.value:
                best_dim = r.dimension

    return best_dim


def _build_aggregation_explanation(
    regimes: dict[str, DimensionRegime],
    dominant: DimensionName | None,
    alignment: float,
    conflict: float,
) -> str:
    parts: list[str] = []

    for key in sorted(regimes.keys()):
        r = regimes[key]
        parts.append(f"{r.dimension.value}={r.regime_label}({r.direction.value})")

    if dominant is not None:
        dom_r = regimes.get(dominant.value)
        if dom_r is not None:
            parts.append(f"dominant={dominant.value}(strength={dom_r.effective_strength:.2f})")
    else:
        parts.append("no dominant dimension")

    parts.append(f"alignment={alignment:.2f}")
    parts.append(f"conflict={conflict:.2f}")

    return "; ".join(parts)


def aggregate_regimes(
    trend_label: str | None = None,
    risk_label: str | None = None,
    stability_label: str | None = None,
    urgency_label: str | None = None,
    trend_confidence: float = 1.0,
    risk_confidence: float = 1.0,
    stability_confidence: float = 1.0,
    urgency_confidence: float = 1.0,
) -> AggregatedRegimeState:
    """Aggregate per-dimension regime labels into a composite state.

    Missing labels default to neutral (inv 245).
    Each dimension classified independently (inv 242).
    Aggregation is deterministic (inv 243).
    """
    regimes: dict[str, DimensionRegime] = {}

    if trend_label is not None:
        regimes[DimensionName.TREND.value] = classify_dimension(
            DimensionName.TREND, trend_label, trend_confidence
        )
    else:
        regimes[DimensionName.TREND.value] = NEUTRAL_TREND

    if risk_label is not None:
        regimes[DimensionName.RISK.value] = classify_dimension(
            DimensionName.RISK, risk_label, risk_confidence
        )
    else:
        regimes[DimensionName.RISK.value] = NEUTRAL_RISK

    if stability_label is not None:
        regimes[DimensionName.STABILITY.value] = classify_dimension(
            DimensionName.STABILITY, stability_label, stability_confidence
        )
    else:
        regimes[DimensionName.STABILITY.value] = NEUTRAL_STABILITY

    if urgency_label is not None:
        regimes[DimensionName.URGENCY.value] = classify_dimension(
            DimensionName.URGENCY, urgency_label, urgency_confidence
        )
    else:
        regimes[DimensionName.URGENCY.value] = NEUTRAL_URGENCY

    alignment, conflict = _compute_alignment_conflict(regimes)
    dominant = _select_dominant(regimes)
    explanation = _build_aggregation_explanation(regimes, dominant, alignment, conflict)

    return AggregatedRegimeState(
        regimes=regimes,
        dominant_dimension=dominant,
        alignment_score=alignment,
        conflict_score=conflict,
        explanation=explanation,
    )


def aggregate_from_dict(
    dimension_labels: dict[str, str],
    dimension_confidences: dict[str, float] | None = None,
) -> AggregatedRegimeState:
    """Aggregate from a dict of dimension_name → regime_label.

    Convenience wrapper. Keys must be dimension names: trend, risk, stability, urgency.
    Unknown keys are ignored.
    """
    confs = dimension_confidences or {}

    return aggregate_regimes(
        trend_label=dimension_labels.get("trend"),
        risk_label=dimension_labels.get("risk"),
        stability_label=dimension_labels.get("stability"),
        urgency_label=dimension_labels.get("urgency"),
        trend_confidence=confs.get("trend", 1.0),
        risk_confidence=confs.get("risk", 1.0),
        stability_confidence=confs.get("stability", 1.0),
        urgency_confidence=confs.get("urgency", 1.0),
    )
