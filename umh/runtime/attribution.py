"""Contextual outcome attribution — per-dimension performance breakdown.

Links strategy outcomes to composite state dimensions (trend, risk,
urgency, stability, confidence) and computes per-bucket statistics.
Distinguishes global strategy performance from context-specific performance.

Observational only — does not mutate outcomes, planning state, or scoring.
Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.runtime.outcome import OutcomeStatus, StrategyOutcome


class AttributionDimension(Enum):
    STRATEGY = "strategy"
    STATE_SIGNATURE = "state_signature"
    TREND = "trend"
    RISK = "risk"
    URGENCY = "urgency"
    STABILITY = "stability"
    CONFIDENCE = "confidence"
    OBJECTIVE = "objective"
    GOAL_TYPE = "goal_type"


@dataclass(frozen=True)
class AttributionBucket:
    """Stats for one dimension-value bucket."""

    dimension: AttributionDimension
    value: str
    sample_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    partial_count: int = 0
    average_success_score: float = 0.0
    average_latency: float = 0.0
    average_effort: float = 0.0
    confidence: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "sample_count", max(0, self.sample_count))
        object.__setattr__(self, "success_count", max(0, self.success_count))
        object.__setattr__(self, "failure_count", max(0, self.failure_count))
        object.__setattr__(self, "partial_count", max(0, self.partial_count))
        object.__setattr__(
            self, "average_success_score", max(0.0, min(1.0, self.average_success_score))
        )
        object.__setattr__(self, "average_latency", max(0.0, self.average_latency))
        object.__setattr__(self, "average_effort", max(0.0, min(1.0, self.average_effort)))
        object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))

    @property
    def bucket_score(self) -> float:
        return self.average_success_score * self.confidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "value": self.value,
            "sample_count": self.sample_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "partial_count": self.partial_count,
            "average_success_score": round(self.average_success_score, 4),
            "average_latency": round(self.average_latency, 4),
            "average_effort": round(self.average_effort, 4),
            "confidence": round(self.confidence, 4),
            "bucket_score": round(self.bucket_score, 4),
        }


@dataclass(frozen=True)
class ContextAttributionRecord:
    """Attribution breakdown for a strategy under a context."""

    strategy_name: str
    state_signature: str
    dimension_buckets: tuple[AttributionBucket, ...] = ()
    overall_score: float = 0.0
    confidence: float = 0.0
    explanation: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "overall_score", max(0.0, min(1.0, self.overall_score)))
        object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "state_signature": self.state_signature,
            "dimension_buckets": [b.to_dict() for b in self.dimension_buckets],
            "overall_score": round(self.overall_score, 4),
            "confidence": round(self.confidence, 4),
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class ContextFeatures:
    """Extracted context features from an outcome."""

    strategy_name: str = ""
    state_signature: str = ""
    trend: str = ""
    risk: str = ""
    urgency: str = ""
    stability: str = ""
    confidence_level: str = ""
    objective: str = ""
    goal_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "state_signature": self.state_signature,
            "trend": self.trend,
            "risk": self.risk,
            "urgency": self.urgency,
            "stability": self.stability,
            "confidence_level": self.confidence_level,
            "objective": self.objective,
            "goal_type": self.goal_type,
        }


def extract_context_features(outcome: StrategyOutcome) -> ContextFeatures:
    meta = outcome.metadata or {}
    return ContextFeatures(
        strategy_name=outcome.strategy_name,
        state_signature=outcome.state_signature,
        trend=str(meta.get("trend", "")),
        risk=str(meta.get("risk", "")),
        urgency=str(meta.get("urgency", "")),
        stability=str(meta.get("stability", "")),
        confidence_level=str(meta.get("confidence", "")),
        objective=str(meta.get("objective", "")),
        goal_type=str(meta.get("goal_type", "")),
    )


_FEATURE_DIMS: list[tuple[AttributionDimension, str]] = [
    (AttributionDimension.STRATEGY, "strategy_name"),
    (AttributionDimension.STATE_SIGNATURE, "state_signature"),
    (AttributionDimension.TREND, "trend"),
    (AttributionDimension.RISK, "risk"),
    (AttributionDimension.URGENCY, "urgency"),
    (AttributionDimension.STABILITY, "stability"),
    (AttributionDimension.CONFIDENCE, "confidence_level"),
    (AttributionDimension.OBJECTIVE, "objective"),
    (AttributionDimension.GOAL_TYPE, "goal_type"),
]


def _build_bucket(
    dimension: AttributionDimension,
    value: str,
    outcomes: list[StrategyOutcome],
    required_samples: int,
) -> AttributionBucket:
    n = len(outcomes)
    if n == 0:
        return AttributionBucket(dimension=dimension, value=value)

    success = sum(1 for o in outcomes if o.status == OutcomeStatus.SUCCESS)
    failure = sum(1 for o in outcomes if o.status == OutcomeStatus.FAILURE)
    partial = sum(1 for o in outcomes if o.status == OutcomeStatus.PARTIAL)
    avg_score = sum(o.success_score for o in outcomes) / n
    avg_latency = sum(o.latency for o in outcomes) / n
    avg_effort = sum(o.effort for o in outcomes) / n
    conf = min(1.0, n / max(1, required_samples))

    return AttributionBucket(
        dimension=dimension,
        value=value,
        sample_count=n,
        success_count=success,
        failure_count=failure,
        partial_count=partial,
        average_success_score=avg_score,
        average_latency=avg_latency,
        average_effort=avg_effort,
        confidence=conf,
    )


def _group_by_feature(
    outcomes: list[StrategyOutcome],
    dimension: AttributionDimension,
    feature_attr: str,
    required_samples: int,
) -> list[AttributionBucket]:
    groups: dict[str, list[StrategyOutcome]] = {}
    for o in outcomes:
        feat = extract_context_features(o)
        val = getattr(feat, feature_attr, "")
        if not val:
            continue
        groups.setdefault(val, []).append(o)

    buckets: list[AttributionBucket] = []
    for val in sorted(groups.keys()):
        buckets.append(_build_bucket(dimension, val, groups[val], required_samples))
    return buckets


def _build_explanation(
    strategy_name: str,
    state_signature: str,
    buckets: tuple[AttributionBucket, ...],
    overall_score: float,
    confidence: float,
    total_outcomes: int,
) -> str:
    parts: list[str] = []
    parts.append(f"Strategy '{strategy_name}': {total_outcomes} outcomes analyzed")

    if state_signature:
        parts.append(f"context='{state_signature}'")

    scored = [
        b for b in buckets if b.sample_count > 0 and b.dimension != AttributionDimension.STRATEGY
    ]
    if scored:
        best = max(scored, key=lambda b: b.bucket_score)
        worst = min(scored, key=lambda b: b.bucket_score)
        if best.bucket_score > 0:
            parts.append(
                f"strongest: {best.dimension.value}={best.value} (score={best.bucket_score:.2f})"
            )
        if worst.bucket_score < best.bucket_score:
            parts.append(
                f"weakest: {worst.dimension.value}={worst.value} (score={worst.bucket_score:.2f})"
            )

    if total_outcomes == 0:
        parts.append("insufficient data: no outcomes")
    elif confidence < 0.5:
        parts.append(f"insufficient data: confidence={confidence:.2f}")

    parts.append(f"overall_score={overall_score:.2f}, confidence={confidence:.2f}")

    return "; ".join(parts)


class AttributionEngine:
    """Computes contextual attribution from outcome history."""

    def __init__(self, *, required_samples: int = 20) -> None:
        self._required_samples = max(1, required_samples)

    @property
    def required_samples(self) -> int:
        return self._required_samples

    def build_attribution(
        self,
        outcomes: list[StrategyOutcome],
        strategy_name: str | None = None,
        state_signature: str | None = None,
    ) -> ContextAttributionRecord:
        filtered = list(outcomes)
        if strategy_name is not None:
            filtered = [o for o in filtered if o.strategy_name == strategy_name]
        if state_signature is not None:
            filtered = [o for o in filtered if o.state_signature == state_signature]

        if not filtered:
            sig = state_signature or ""
            strat = strategy_name or ""
            return ContextAttributionRecord(
                strategy_name=strat,
                state_signature=sig,
                explanation=f"Strategy '{strat}': 0 outcomes analyzed; insufficient data: no outcomes; overall_score=0.00, confidence=0.00",
            )

        all_buckets: list[AttributionBucket] = []
        for dim, attr in _FEATURE_DIMS:
            all_buckets.extend(_group_by_feature(filtered, dim, attr, self._required_samples))

        n = len(filtered)
        overall_score = sum(o.success_score for o in filtered) / n
        confidence = min(1.0, n / self._required_samples)

        bucket_tuple = tuple(all_buckets)
        sig = state_signature or (filtered[0].state_signature if filtered else "")
        strat = strategy_name or (filtered[0].strategy_name if filtered else "")

        explanation = _build_explanation(
            strat, state_signature or "", bucket_tuple, overall_score, confidence, n
        )

        return ContextAttributionRecord(
            strategy_name=strat,
            state_signature=sig,
            dimension_buckets=bucket_tuple,
            overall_score=overall_score,
            confidence=confidence,
            explanation=explanation,
        )

    def compute_global_strategy_attribution(
        self, outcomes: list[StrategyOutcome], strategy_name: str
    ) -> ContextAttributionRecord:
        return self.build_attribution(outcomes, strategy_name=strategy_name)

    def compute_context_strategy_attribution(
        self,
        outcomes: list[StrategyOutcome],
        strategy_name: str,
        state_signature: str,
    ) -> ContextAttributionRecord:
        return self.build_attribution(
            outcomes, strategy_name=strategy_name, state_signature=state_signature
        )

    def compare_global_vs_context(
        self,
        outcomes: list[StrategyOutcome],
        strategy_name: str,
        state_signature: str,
    ) -> dict[str, Any]:
        g = self.compute_global_strategy_attribution(outcomes, strategy_name)
        c = self.compute_context_strategy_attribution(outcomes, strategy_name, state_signature)
        diff = c.overall_score - g.overall_score

        if abs(diff) < 0.01:
            summary = "context performance matches global"
        elif diff > 0:
            summary = f"context outperforms global by {diff:.2f}"
        else:
            summary = f"context underperforms global by {abs(diff):.2f}"

        return {
            "global": g.to_dict(),
            "context": c.to_dict(),
            "score_difference": round(diff, 4),
            "summary": summary,
        }
