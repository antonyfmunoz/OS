"""Objective Function System — define TRUE success outside the system.

Objectives are real-world success metrics that override internal scoring.
The system can score its own pipeline execution, but only an Objective
knows whether the real world improved.

Usage:
    from core.objective import Objective, evaluate_objective

    obj = Objective(
        name="outreach_reply_rate",
        success_metric=lambda result, data: data.get("replies", 0) / max(data.get("sent", 1), 1),
        threshold=0.05,  # 5% reply rate
    )

    score = evaluate_objective(pipeline_result, real_data={"sent": 100, "replies": 8}, objective=obj)
    # score.achieved == True (0.08 >= 0.05)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from core.orchestrator.pipeline import PipelineResult


# ---------------------------------------------------------------------------
# Objective definition
# ---------------------------------------------------------------------------


@dataclass
class Objective:
    """A real-world success criterion that overrides internal pipeline scoring.

    The success_metric callable receives:
        (pipeline_result: PipelineResult, real_data: dict) -> float

    The returned float (0.0-1.0) is compared against threshold.
    """

    name: str
    success_metric: Callable[[PipelineResult, dict[str, Any]], float]
    threshold: float  # minimum score to consider successful
    constraints: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def evaluate(
        self,
        result: PipelineResult,
        real_data: dict[str, Any],
    ) -> float:
        """Run the success metric against real data."""
        return self.success_metric(result, real_data)


# ---------------------------------------------------------------------------
# Evaluation result
# ---------------------------------------------------------------------------


@dataclass
class ObjectiveScore:
    """The result of evaluating a pipeline against a real-world objective."""

    objective_name: str
    score: float  # 0.0-1.0
    threshold: float
    achieved: bool  # score >= threshold
    internal_score: float  # the pipeline's self-assessment
    override_active: bool  # True when objective disagrees with internal
    gap: float  # threshold - score (positive = below threshold)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective_name,
            "score": round(self.score, 4),
            "threshold": self.threshold,
            "achieved": self.achieved,
            "internal_score": round(self.internal_score, 4),
            "override_active": self.override_active,
            "gap": round(self.gap, 4),
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Built-in metric functions
# ---------------------------------------------------------------------------


def reply_rate_metric(result: PipelineResult, data: dict[str, Any]) -> float:
    """Outreach success = replies / sent."""
    sent = data.get("sent", 0)
    replies = data.get("replies", 0)
    return replies / max(sent, 1)


def engagement_rate_metric(result: PipelineResult, data: dict[str, Any]) -> float:
    """Content success = engagements / impressions."""
    impressions = data.get("impressions", 0)
    engagements = data.get("engagements", 0)
    return engagements / max(impressions, 1)


def conversion_rate_metric(result: PipelineResult, data: dict[str, Any]) -> float:
    """Offer success = conversions / presentations."""
    presentations = data.get("presentations", 0)
    conversions = data.get("conversions", 0)
    return conversions / max(presentations, 1)


def revenue_metric(result: PipelineResult, data: dict[str, Any]) -> float:
    """Revenue against target (capped at 1.0)."""
    target = data.get("target", 1)
    actual = data.get("actual", 0)
    return min(actual / max(target, 1), 1.0)


# ---------------------------------------------------------------------------
# Objective registry
# ---------------------------------------------------------------------------

OBJECTIVE_REGISTRY: dict[str, Objective] = {
    "outreach_reply_rate": Objective(
        name="outreach_reply_rate",
        success_metric=reply_rate_metric,
        threshold=0.05,
        description="Outreach reply rate >= 5%",
    ),
    "content_engagement": Objective(
        name="content_engagement",
        success_metric=engagement_rate_metric,
        threshold=0.03,
        description="Content engagement rate >= 3%",
    ),
    "offer_conversion": Objective(
        name="offer_conversion",
        success_metric=conversion_rate_metric,
        threshold=0.02,
        description="Offer conversion rate >= 2%",
    ),
    "revenue_target": Objective(
        name="revenue_target",
        success_metric=revenue_metric,
        threshold=0.8,
        description="Revenue at least 80% of target",
    ),
}


def register_objective(objective: Objective) -> None:
    """Register a new objective in the global registry."""
    OBJECTIVE_REGISTRY[objective.name] = objective


def get_objective(name: str) -> Objective | None:
    """Retrieve an objective by name."""
    return OBJECTIVE_REGISTRY.get(name)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_objective(
    result: PipelineResult,
    real_data: dict[str, Any],
    objective: Objective,
    *,
    internal_score: float | None = None,
) -> ObjectiveScore:
    """Evaluate a pipeline result against a real-world objective.

    This is the override mechanism: the objective score replaces the
    pipeline's internal self-assessment when they disagree.

    Args:
        result:         The PipelineResult from execution.
        real_data:      Real-world data (metrics, responses, etc.).
        objective:      The Objective to evaluate against.
        internal_score: The pipeline's own success score (from feedback).
                        If None, derived from result.ok.

    Returns:
        ObjectiveScore with achieved status and override flag.
    """
    score = objective.evaluate(result, real_data)

    if internal_score is None:
        internal_score = 1.0 if result.ok else 0.0

    achieved = score >= objective.threshold
    gap = objective.threshold - score

    # Override is active when real-world disagrees with internal assessment
    # Internal says good but reality says bad, or vice versa
    internal_good = internal_score >= 0.7
    override_active = internal_good != achieved

    return ObjectiveScore(
        objective_name=objective.name,
        score=score,
        threshold=objective.threshold,
        achieved=achieved,
        internal_score=internal_score,
        override_active=override_active,
        gap=max(gap, 0.0),
        metadata={
            "real_data": real_data,
            "constraints": objective.constraints,
        },
    )


__all__ = [
    "Objective",
    "ObjectiveScore",
    "evaluate_objective",
    "register_objective",
    "get_objective",
    "OBJECTIVE_REGISTRY",
    "reply_rate_metric",
    "engagement_rate_metric",
    "conversion_rate_metric",
    "revenue_metric",
]
