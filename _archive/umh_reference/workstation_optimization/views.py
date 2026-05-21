"""Phase 87C workstation optimization views — UI-safe read models.

No sensitive data exposed. No execution. No mutation. Advisory only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeviceBaselineCategoryView:
    category_id: str = ""
    area: str = ""
    name: str = ""
    description: str = ""
    audit_mode: str = ""
    risk: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category_id": self.category_id,
            "area": self.area,
            "name": self.name,
            "description": self.description,
            "audit_mode": self.audit_mode,
            "risk": self.risk,
            "metadata": self.metadata,
        }


@dataclass
class WorkstationBaselinePlanView:
    plan_id: str = ""
    node_id: str = ""
    audit_mode: str = ""
    category_count: int = 0
    blocked_count: int = 0
    warning_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "node_id": self.node_id,
            "audit_mode": self.audit_mode,
            "category_count": self.category_count,
            "blocked_count": self.blocked_count,
            "warning_count": self.warning_count,
            "metadata": self.metadata,
        }


@dataclass
class OptimizationCandidateView:
    candidate_id: str = ""
    area: str = ""
    action_type: str = ""
    title: str = ""
    risk_level: str = ""
    approval_required: str = ""
    reversibility: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "area": self.area,
            "action_type": self.action_type,
            "title": self.title,
            "risk_level": self.risk_level,
            "approval_required": self.approval_required,
            "reversibility": self.reversibility,
            "metadata": self.metadata,
        }


@dataclass
class DeviceLiteracyExplanationView:
    explanation_id: str = ""
    area: str = ""
    topic: str = ""
    plain_language_summary: str = ""
    why_it_matters: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "explanation_id": self.explanation_id,
            "area": self.area,
            "topic": self.topic,
            "plain_language_summary": self.plain_language_summary,
            "why_it_matters": self.why_it_matters,
            "metadata": self.metadata,
        }


@dataclass
class PerformanceTuningAdvisoryView:
    advisory_id: str = ""
    category: str = ""
    summary: str = ""
    risk: str = ""
    approval: str = ""
    stability_test: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "advisory_id": self.advisory_id,
            "category": self.category,
            "summary": self.summary,
            "risk": self.risk,
            "approval": self.approval,
            "stability_test": self.stability_test,
            "metadata": self.metadata,
        }


@dataclass
class WorkstationOptimizationReportView:
    report_id: str = ""
    node_id: str = ""
    category_count: int = 0
    literacy_count: int = 0
    candidate_count: int = 0
    high_risk_count: int = 0
    preserved_count: int = 0
    warning_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "node_id": self.node_id,
            "category_count": self.category_count,
            "literacy_count": self.literacy_count,
            "candidate_count": self.candidate_count,
            "high_risk_count": self.high_risk_count,
            "preserved_count": self.preserved_count,
            "warning_count": self.warning_count,
            "metadata": self.metadata,
        }


@dataclass
class WorkstationOptimizationDashboardView:
    total_categories: int = 0
    total_candidates: int = 0
    total_literacy_items: int = 0
    high_risk_count: int = 0
    preserved_count: int = 0
    audit_mode: str = ""
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_categories": self.total_categories,
            "total_candidates": self.total_candidates,
            "total_literacy_items": self.total_literacy_items,
            "high_risk_count": self.high_risk_count,
            "preserved_count": self.preserved_count,
            "audit_mode": self.audit_mode,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def _ev(v: Any) -> str:
    return v.value if hasattr(v, "value") else str(v)


def baseline_category_to_view(cat: Any) -> DeviceBaselineCategoryView:
    return DeviceBaselineCategoryView(
        category_id=getattr(cat, "category_id", ""),
        area=_ev(getattr(cat, "area", "")),
        name=getattr(cat, "name", ""),
        description=getattr(cat, "description", ""),
        audit_mode=_ev(getattr(cat, "audit_mode", "")),
        risk=_ev(getattr(cat, "default_risk", "")),
    )


def baseline_plan_to_view(plan: Any) -> WorkstationBaselinePlanView:
    return WorkstationBaselinePlanView(
        plan_id=getattr(plan, "plan_id", ""),
        node_id=getattr(plan, "node_id", ""),
        audit_mode=_ev(getattr(plan, "audit_mode", "")),
        category_count=len(getattr(plan, "categories", [])),
        blocked_count=len(getattr(plan, "blocked_observations", [])),
        warning_count=len(getattr(plan, "warnings", [])),
    )


def optimization_candidate_to_view(cand: Any) -> OptimizationCandidateView:
    return OptimizationCandidateView(
        candidate_id=getattr(cand, "candidate_id", ""),
        area=_ev(getattr(cand, "area", "")),
        action_type=_ev(getattr(cand, "action_type", "")),
        title=getattr(cand, "title", ""),
        risk_level=_ev(getattr(cand, "risk_level", "")),
        approval_required=_ev(getattr(cand, "approval_required", "")),
        reversibility=_ev(getattr(cand, "reversibility", "")),
    )


def literacy_explanation_to_view(exp: Any) -> DeviceLiteracyExplanationView:
    return DeviceLiteracyExplanationView(
        explanation_id=getattr(exp, "explanation_id", ""),
        area=_ev(getattr(exp, "area", "")),
        topic=getattr(exp, "topic", ""),
        plain_language_summary=getattr(exp, "plain_language_summary", ""),
        why_it_matters=getattr(exp, "why_it_matters", ""),
    )


def performance_advisory_to_view(adv: Any) -> PerformanceTuningAdvisoryView:
    return PerformanceTuningAdvisoryView(
        advisory_id=getattr(adv, "advisory_id", ""),
        category=_ev(getattr(adv, "category", "")),
        summary=getattr(adv, "summary", ""),
        risk=_ev(getattr(adv, "approval_required", "")),
        approval=_ev(getattr(adv, "approval_required", "")),
        stability_test=getattr(adv, "stability_testing_required", False),
    )


def report_to_view(rpt: Any) -> WorkstationOptimizationReportView:
    return WorkstationOptimizationReportView(
        report_id=getattr(rpt, "report_id", ""),
        node_id=getattr(rpt, "node_id", ""),
        category_count=len(
            getattr(rpt.baseline_plan, "categories", []) if rpt.baseline_plan else []
        ),
        literacy_count=len(getattr(rpt, "device_literacy_items", [])),
        candidate_count=len(getattr(rpt, "optimization_candidates", [])),
        high_risk_count=len(getattr(rpt, "high_risk_items", [])),
        preserved_count=len(getattr(rpt, "preserved_items", [])),
        warning_count=len(getattr(rpt, "warnings", [])),
    )


def build_workstation_optimization_dashboard_view(
    report: Any,
) -> WorkstationOptimizationDashboardView:
    bp = getattr(report, "baseline_plan", None)
    return WorkstationOptimizationDashboardView(
        total_categories=len(getattr(bp, "categories", []) if bp else []),
        total_candidates=len(getattr(report, "optimization_candidates", [])),
        total_literacy_items=len(getattr(report, "device_literacy_items", [])),
        high_risk_count=len(getattr(report, "high_risk_items", [])),
        preserved_count=len(getattr(report, "preserved_items", [])),
        audit_mode=_ev(getattr(bp, "audit_mode", "unknown") if bp else "unknown"),
        warnings=getattr(report, "warnings", []),
    )
