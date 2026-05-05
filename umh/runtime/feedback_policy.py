"""Feedback policy — controlled, bounded influence on scoring.

Computes a feedback factor from strategy statistics with explicit policy control.
Disabled by default — returns neutral (1.0) unless explicitly enabled.

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.runtime.outcome import StrategyStats


@dataclass(frozen=True)
class FeedbackPolicy:
    """Policy controlling feedback influence on scoring."""

    enabled: bool = False
    min_effective_samples: int = 10
    max_boost: float = 0.10
    max_penalty: float = 0.10
    neutral_factor: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "min_effective_samples", max(1, self.min_effective_samples))
        object.__setattr__(self, "max_boost", max(0.0, min(0.25, self.max_boost)))
        object.__setattr__(self, "max_penalty", max(0.0, min(0.25, self.max_penalty)))


@dataclass(frozen=True)
class FeedbackInfluenceResult:
    """Result of computing feedback influence."""

    factor: float
    confidence: float
    reason: str
    effective_samples: int
    weighted_success_rate: float
    enabled: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor": round(self.factor, 4),
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
            "effective_samples": self.effective_samples,
            "weighted_success_rate": round(self.weighted_success_rate, 4),
            "enabled": self.enabled,
        }


def compute_feedback_factor(
    stats: StrategyStats,
    policy: FeedbackPolicy | None = None,
    learning_strength: float = 1.0,
) -> FeedbackInfluenceResult:
    p = policy or FeedbackPolicy()

    if not p.enabled:
        return FeedbackInfluenceResult(
            factor=p.neutral_factor,
            confidence=0.0,
            reason="feedback disabled",
            effective_samples=stats.total_count,
            weighted_success_rate=stats.success_rate,
            enabled=False,
        )

    if stats.total_count < p.min_effective_samples:
        return FeedbackInfluenceResult(
            factor=p.neutral_factor,
            confidence=stats.total_count / p.min_effective_samples
            if p.min_effective_samples > 0
            else 0.0,
            reason=f"insufficient samples ({stats.total_count}/{p.min_effective_samples})",
            effective_samples=stats.total_count,
            weighted_success_rate=stats.success_rate,
            enabled=True,
        )

    deviation = stats.average_success_score - 0.5
    if deviation > 0:
        raw_delta = min(p.max_boost, deviation * 0.2)
    else:
        raw_delta = max(-p.max_penalty, deviation * 0.2)

    ls = max(0.0, min(1.0, learning_strength))
    effective_delta = raw_delta * ls

    factor = p.neutral_factor + effective_delta
    factor = max(p.neutral_factor - p.max_penalty, min(p.neutral_factor + p.max_boost, factor))

    confidence = min(1.0, stats.total_count / p.min_effective_samples)

    if effective_delta > 0:
        direction = "boost"
    elif effective_delta < 0:
        direction = "penalty"
    else:
        direction = "neutral"

    reason = (
        f"{direction}: avg_score={stats.average_success_score:.2f}, "
        f"samples={stats.total_count}, "
        f"learning_strength={ls:.2f}, "
        f"confidence={confidence:.2f}"
    )

    return FeedbackInfluenceResult(
        factor=factor,
        confidence=confidence,
        reason=reason,
        effective_samples=stats.total_count,
        weighted_success_rate=stats.success_rate,
        enabled=True,
    )
