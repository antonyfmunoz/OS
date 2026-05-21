"""Phase 87 leverage views — UI-safe read models for leverage data.

No sensitive data exposed. No execution. No mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResourceProfileView:
    resource_id: str = ""
    name: str = ""
    resource_type: str = ""
    description: str = ""
    availability: str = ""
    owner: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "name": self.name,
            "resource_type": self.resource_type,
            "description": self.description,
            "availability": self.availability,
            "owner": self.owner,
            "metadata": self.metadata,
        }


@dataclass
class ToolProfileView:
    tool_id: str = ""
    name: str = ""
    tool_type: str = ""
    description: str = ""
    reliability: str = ""
    dependency_risk: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "tool_type": self.tool_type,
            "description": self.description,
            "reliability": self.reliability,
            "dependency_risk": self.dependency_risk,
            "metadata": self.metadata,
        }


@dataclass
class LeverageOpportunityView:
    opportunity_id: str = ""
    title: str = ""
    leverage_type: str = ""
    description: str = ""
    expected_multiplier: float = 1.0
    risk_level: str = ""
    confidence: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "title": self.title,
            "leverage_type": self.leverage_type,
            "description": self.description,
            "expected_multiplier": self.expected_multiplier,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class LeverageScorecardView:
    scorecard_id: str = ""
    opportunity_id: str = ""
    overall_score: float = 0.0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scorecard_id": self.scorecard_id,
            "opportunity_id": self.opportunity_id,
            "overall_score": round(self.overall_score, 4),
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


@dataclass
class LeverageRecommendationView:
    recommendation_id: str = ""
    action: str = ""
    summary: str = ""
    leverage_type: str = ""
    risk_level: str = ""
    confidence: str = ""
    first_step: str = ""
    guardrails: list[str] = field(default_factory=list)
    non_actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "action": self.action,
            "summary": self.summary,
            "leverage_type": self.leverage_type,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "first_step": self.first_step,
            "guardrails": self.guardrails,
            "non_actions": self.non_actions,
            "metadata": self.metadata,
        }


@dataclass
class LeverageAssessmentView:
    assessment_id: str = ""
    goal: str = ""
    opportunity_count: int = 0
    highest_leverage: str = ""
    bottlenecks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "goal": self.goal,
            "opportunity_count": self.opportunity_count,
            "highest_leverage": self.highest_leverage,
            "bottlenecks": self.bottlenecks,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


@dataclass
class LeverageDashboardView:
    resource_count: int = 0
    tool_count: int = 0
    leverage_type_count: int = 0
    recommendation_count: int = 0
    top_recommendations: list[str] = field(default_factory=list)
    bottlenecks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_count": self.resource_count,
            "tool_count": self.tool_count,
            "leverage_type_count": self.leverage_type_count,
            "recommendation_count": self.recommendation_count,
            "top_recommendations": self.top_recommendations,
            "bottlenecks": self.bottlenecks,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


# ─── Converters ─────────────────────────────────────────────────────


def resource_to_view(resource: Any) -> ResourceProfileView:
    return ResourceProfileView(
        resource_id=getattr(resource, "resource_id", ""),
        name=getattr(resource, "name", ""),
        resource_type=getattr(resource, "resource_type", "").value
        if hasattr(getattr(resource, "resource_type", None), "value")
        else str(getattr(resource, "resource_type", "")),
        description=getattr(resource, "description", ""),
        availability=getattr(resource, "availability", ""),
        owner=getattr(resource, "owner", ""),
    )


def tool_to_view(tool: Any) -> ToolProfileView:
    tt = getattr(tool, "tool_type", "")
    return ToolProfileView(
        tool_id=getattr(tool, "tool_id", ""),
        name=getattr(tool, "name", ""),
        tool_type=tt.value if hasattr(tt, "value") else str(tt),
        description=getattr(tool, "description", ""),
        reliability=getattr(tool, "reliability", ""),
        dependency_risk=getattr(tool, "dependency_risk", ""),
    )


def opportunity_to_view(opp: Any) -> LeverageOpportunityView:
    lt = getattr(opp, "leverage_type", "")
    rl = getattr(opp, "risk_level", "")
    conf = getattr(opp, "confidence", "")
    return LeverageOpportunityView(
        opportunity_id=getattr(opp, "opportunity_id", ""),
        title=getattr(opp, "title", ""),
        leverage_type=lt.value if hasattr(lt, "value") else str(lt),
        description=getattr(opp, "description", ""),
        expected_multiplier=getattr(opp, "expected_multiplier", 1.0),
        risk_level=rl.value if hasattr(rl, "value") else str(rl),
        confidence=conf.value if hasattr(conf, "value") else str(conf),
    )


def scorecard_to_view(sc: Any) -> LeverageScorecardView:
    return LeverageScorecardView(
        scorecard_id=getattr(sc, "scorecard_id", ""),
        opportunity_id=getattr(sc, "opportunity_id", ""),
        overall_score=getattr(sc, "overall_score", 0.0),
        warnings=getattr(sc, "warnings", []),
    )


def recommendation_to_view(rec: Any) -> LeverageRecommendationView:
    action = getattr(rec, "action", "")
    lt = getattr(rec, "leverage_type", "")
    rl = getattr(rec, "risk_level", "")
    conf = getattr(rec, "confidence", "")
    return LeverageRecommendationView(
        recommendation_id=getattr(rec, "recommendation_id", ""),
        action=action.value if hasattr(action, "value") else str(action),
        summary=getattr(rec, "summary", ""),
        leverage_type=lt.value if hasattr(lt, "value") else str(lt),
        risk_level=rl.value if hasattr(rl, "value") else str(rl),
        confidence=conf.value if hasattr(conf, "value") else str(conf),
        first_step=getattr(rec, "first_step", ""),
        guardrails=getattr(rec, "guardrails", []),
        non_actions=getattr(rec, "non_actions", []),
    )


def assessment_to_view(assessment: Any) -> LeverageAssessmentView:
    return LeverageAssessmentView(
        assessment_id=getattr(assessment, "assessment_id", ""),
        goal=getattr(assessment, "goal", ""),
        opportunity_count=len(getattr(assessment, "opportunities", [])),
        highest_leverage=getattr(assessment, "highest_leverage_opportunity", ""),
        bottlenecks=getattr(assessment, "bottlenecks", []),
        warnings=getattr(assessment, "warnings", []),
    )


def build_leverage_dashboard_view(
    resources: list[Any] | None = None,
    tools: list[Any] | None = None,
    recommendations: list[Any] | None = None,
    bottlenecks: list[str] | None = None,
    warnings: list[str] | None = None,
) -> LeverageDashboardView:
    from umh.leverage.contracts import LeverageType

    recs = recommendations or []
    return LeverageDashboardView(
        resource_count=len(resources or []),
        tool_count=len(tools or []),
        leverage_type_count=len(LeverageType) - 1,
        recommendation_count=len(recs),
        top_recommendations=[getattr(r, "summary", str(r)) for r in recs[:5]],
        bottlenecks=bottlenecks or [],
        warnings=warnings or [],
    )
