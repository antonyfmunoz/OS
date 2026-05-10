"""Phase 88 workflow views — UI-safe read models.

No sensitive data exposed. No execution. No mutation. Advisory only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowDefinitionView:
    workflow_id: str = ""
    name: str = ""
    purpose: str = ""
    stage_count: int = 0
    primary_company: str = ""
    product: str = ""
    owner: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "purpose": self.purpose,
            "stage_count": self.stage_count,
            "primary_company": self.primary_company,
            "product": self.product,
            "owner": self.owner,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowTaskView:
    task_id: str = ""
    stage: str = ""
    title: str = ""
    priority: str = ""
    status: str = ""
    estimated_minutes: int = 0
    leverage_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "stage": self.stage,
            "title": self.title,
            "priority": self.priority,
            "status": self.status,
            "estimated_minutes": self.estimated_minutes,
            "leverage_type": self.leverage_type,
            "metadata": self.metadata,
        }


@dataclass
class DailyWorkflowPlanView:
    plan_id: str = ""
    date: str = ""
    task_count: int = 0
    kpi_count: int = 0
    highest_leverage_actions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "date": self.date,
            "task_count": self.task_count,
            "kpi_count": self.kpi_count,
            "highest_leverage_actions": self.highest_leverage_actions,
            "risks": self.risks,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowKPIRecordView:
    kpi_name: str = ""
    value: float = 0.0
    unit: str = ""
    stage: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kpi_name": self.kpi_name,
            "value": self.value,
            "unit": self.unit,
            "stage": self.stage,
            "metadata": self.metadata,
        }


@dataclass
class DailyWorkflowResultView:
    result_id: str = ""
    date: str = ""
    completed_count: int = 0
    skipped_count: int = 0
    kpi_count: int = 0
    objection_count: int = 0
    bottleneck_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "date": self.date,
            "completed_count": self.completed_count,
            "skipped_count": self.skipped_count,
            "kpi_count": self.kpi_count,
            "objection_count": self.objection_count,
            "bottleneck_count": self.bottleneck_count,
            "metadata": self.metadata,
        }


@dataclass
class DailyWorkflowReviewView:
    review_id: str = ""
    date: str = ""
    summary: str = ""
    bottleneck_count: int = 0
    lesson_count: int = 0
    next_action_count: int = 0
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "date": self.date,
            "summary": self.summary,
            "bottleneck_count": self.bottleneck_count,
            "lesson_count": self.lesson_count,
            "next_action_count": self.next_action_count,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class FirstWorkflowDashboardView:
    workflow_name: str = ""
    stage_count: int = 0
    task_count: int = 0
    kpi_count: int = 0
    completed_count: int = 0
    objection_count: int = 0
    bottleneck_count: int = 0
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "stage_count": self.stage_count,
            "task_count": self.task_count,
            "kpi_count": self.kpi_count,
            "completed_count": self.completed_count,
            "objection_count": self.objection_count,
            "bottleneck_count": self.bottleneck_count,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def _ev(v: Any) -> str:
    return v.value if hasattr(v, "value") else str(v)


def workflow_to_view(wf: Any) -> WorkflowDefinitionView:
    return WorkflowDefinitionView(
        workflow_id=getattr(wf, "workflow_id", ""),
        name=getattr(wf, "name", ""),
        purpose=getattr(wf, "purpose", ""),
        stage_count=len(getattr(wf, "stages", [])),
        primary_company=getattr(wf, "primary_company", ""),
        product=getattr(wf, "product", ""),
        owner=getattr(wf, "owner", ""),
    )


def task_to_view(task: Any) -> WorkflowTaskView:
    return WorkflowTaskView(
        task_id=getattr(task, "task_id", ""),
        stage=_ev(getattr(task, "stage", "")),
        title=getattr(task, "title", ""),
        priority=getattr(task, "priority", ""),
        status=_ev(getattr(task, "status", "")),
        estimated_minutes=getattr(task, "estimated_minutes", 0),
        leverage_type=getattr(task, "leverage_type", ""),
    )


def plan_to_view(plan: Any) -> DailyWorkflowPlanView:
    return DailyWorkflowPlanView(
        plan_id=getattr(plan, "plan_id", ""),
        date=getattr(plan, "date", ""),
        task_count=len(getattr(plan, "tasks", [])),
        kpi_count=len(getattr(plan, "kpis_to_track", [])),
        highest_leverage_actions=getattr(plan, "highest_leverage_actions", []),
        risks=getattr(plan, "risks", []),
    )


def kpi_record_to_view(record: Any) -> WorkflowKPIRecordView:
    return WorkflowKPIRecordView(
        kpi_name=_ev(getattr(record, "kpi_name", "")),
        value=getattr(record, "value", 0.0),
        unit=getattr(record, "unit", ""),
        stage=_ev(getattr(record, "stage", "")),
    )


def result_to_view(result: Any) -> DailyWorkflowResultView:
    return DailyWorkflowResultView(
        result_id=getattr(result, "result_id", ""),
        date=getattr(result, "date", ""),
        completed_count=len(getattr(result, "completed_tasks", [])),
        skipped_count=len(getattr(result, "skipped_tasks", [])),
        kpi_count=len(getattr(result, "kpi_records", [])),
        objection_count=len(getattr(result, "objections", [])),
        bottleneck_count=len(getattr(result, "bottlenecks", [])),
    )


def review_to_view(review: Any) -> DailyWorkflowReviewView:
    return DailyWorkflowReviewView(
        review_id=getattr(review, "review_id", ""),
        date=getattr(review, "date", ""),
        summary=getattr(review, "summary", ""),
        bottleneck_count=len(getattr(review, "bottlenecks", [])),
        lesson_count=len(getattr(review, "lessons", [])),
        next_action_count=len(getattr(review, "next_actions", [])),
        confidence=getattr(review, "confidence", 0.0),
    )


def build_first_workflow_dashboard_view(
    plan: Any = None,
    result: Any = None,
    review: Any = None,
) -> FirstWorkflowDashboardView:
    warnings: list[str] = []
    wf = getattr(plan, "workflow", None) if plan else None
    workflow_name = getattr(wf, "name", "Unknown") if wf else "No plan loaded"
    stage_count = len(getattr(wf, "stages", [])) if wf else 0
    task_count = len(getattr(plan, "tasks", [])) if plan else 0
    kpi_count = len(getattr(plan, "kpis_to_track", [])) if plan else 0
    completed_count = len(getattr(result, "completed_tasks", [])) if result else 0
    objection_count = len(getattr(result, "objections", [])) if result else 0
    bottleneck_count = len(getattr(result, "bottlenecks", [])) if result else 0
    confidence = getattr(review, "confidence", 0.0) if review else 0.0

    if not plan:
        warnings.append("No daily plan loaded")
    if not result:
        warnings.append("No results captured yet")
    if not review:
        warnings.append("No review completed yet")

    return FirstWorkflowDashboardView(
        workflow_name=workflow_name,
        stage_count=stage_count,
        task_count=task_count,
        kpi_count=kpi_count,
        completed_count=completed_count,
        objection_count=objection_count,
        bottleneck_count=bottleneck_count,
        confidence=confidence,
        warnings=warnings,
    )


# ─── North Star Views ───────────────────────────────────────────────


@dataclass
class IntegratedOperatingPlanView:
    plan_id: str = ""
    date: str = ""
    track_count: int = 0
    business_task_count: int = 0
    self_build_task_count: int = 0
    highest_leverage_actions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    required_manual_inputs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "date": self.date,
            "track_count": self.track_count,
            "business_task_count": self.business_task_count,
            "self_build_task_count": self.self_build_task_count,
            "highest_leverage_actions": self.highest_leverage_actions,
            "risks": self.risks,
            "required_manual_inputs": self.required_manual_inputs,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowResultView:
    result_id: str = ""
    date: str = ""
    track: str = ""
    completed_count: int = 0
    skipped_count: int = 0
    kpi_count: int = 0
    objection_count: int = 0
    bottleneck_count: int = 0
    artifact_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "date": self.date,
            "track": self.track,
            "completed_count": self.completed_count,
            "skipped_count": self.skipped_count,
            "kpi_count": self.kpi_count,
            "objection_count": self.objection_count,
            "bottleneck_count": self.bottleneck_count,
            "artifact_count": self.artifact_count,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowReviewView:
    review_id: str = ""
    date: str = ""
    track: str = ""
    summary: str = ""
    bottleneck_count: int = 0
    lesson_count: int = 0
    next_action_count: int = 0
    template_candidate_count: int = 0
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "date": self.date,
            "track": self.track,
            "summary": self.summary,
            "bottleneck_count": self.bottleneck_count,
            "lesson_count": self.lesson_count,
            "next_action_count": self.next_action_count,
            "template_candidate_count": self.template_candidate_count,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class NorthStarTestReportView:
    report_id: str = ""
    date: str = ""
    business_completed: int = 0
    self_build_completed: int = 0
    integrated_lesson_count: int = 0
    system_gap_count: int = 0
    next_day_action_count: int = 0
    next_build_rec_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "date": self.date,
            "business_completed": self.business_completed,
            "self_build_completed": self.self_build_completed,
            "integrated_lesson_count": self.integrated_lesson_count,
            "system_gap_count": self.system_gap_count,
            "next_day_action_count": self.next_day_action_count,
            "next_build_rec_count": self.next_build_rec_count,
            "metadata": self.metadata,
        }


@dataclass
class NorthStarDashboardView:
    date: str = ""
    business_track_name: str = ""
    self_build_track_name: str = ""
    business_task_count: int = 0
    self_build_task_count: int = 0
    business_completed: int = 0
    self_build_completed: int = 0
    total_kpis: int = 0
    total_objections: int = 0
    total_bottlenecks: int = 0
    system_gap_count: int = 0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "business_track_name": self.business_track_name,
            "self_build_track_name": self.self_build_track_name,
            "business_task_count": self.business_task_count,
            "self_build_task_count": self.self_build_task_count,
            "business_completed": self.business_completed,
            "self_build_completed": self.self_build_completed,
            "total_kpis": self.total_kpis,
            "total_objections": self.total_objections,
            "total_bottlenecks": self.total_bottlenecks,
            "system_gap_count": self.system_gap_count,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def integrated_plan_to_view(plan: Any) -> IntegratedOperatingPlanView:
    bp = getattr(plan, "business_plan", None)
    sbp = getattr(plan, "self_build_plan", None)
    return IntegratedOperatingPlanView(
        plan_id=getattr(plan, "plan_id", ""),
        date=getattr(plan, "date", ""),
        track_count=len(getattr(plan, "tracks", [])),
        business_task_count=len(getattr(bp, "tasks", [])) if bp else 0,
        self_build_task_count=len(getattr(sbp, "tasks", [])) if sbp else 0,
        highest_leverage_actions=getattr(plan, "highest_leverage_actions", []),
        risks=getattr(plan, "risks", []),
        required_manual_inputs=getattr(plan, "required_manual_inputs", []),
    )


def workflow_result_to_view(result: Any) -> WorkflowResultView:
    return WorkflowResultView(
        result_id=getattr(result, "result_id", ""),
        date=getattr(result, "date", ""),
        track=_ev(getattr(result, "track", "")),
        completed_count=len(getattr(result, "completed_tasks", [])),
        skipped_count=len(getattr(result, "skipped_tasks", [])),
        kpi_count=len(getattr(result, "kpi_records", [])),
        objection_count=len(getattr(result, "objections", [])),
        bottleneck_count=len(getattr(result, "bottlenecks", [])),
        artifact_count=len(getattr(result, "artifacts", [])),
    )


def workflow_review_to_view(review: Any) -> WorkflowReviewView:
    return WorkflowReviewView(
        review_id=getattr(review, "review_id", ""),
        date=getattr(review, "date", ""),
        track=_ev(getattr(review, "track", "")),
        summary=getattr(review, "summary", ""),
        bottleneck_count=len(getattr(review, "bottlenecks", [])),
        lesson_count=len(getattr(review, "lessons", [])),
        next_action_count=len(getattr(review, "next_actions", [])),
        template_candidate_count=len(getattr(review, "template_candidates", [])),
        confidence=getattr(review, "confidence", 0.0),
    )


def report_to_view(report: Any) -> NorthStarTestReportView:
    br = getattr(report, "business_result", None)
    sbr = getattr(report, "self_build_result", None)
    return NorthStarTestReportView(
        report_id=getattr(report, "report_id", ""),
        date=getattr(report, "date", ""),
        business_completed=len(getattr(br, "completed_tasks", [])) if br else 0,
        self_build_completed=len(getattr(sbr, "completed_tasks", [])) if sbr else 0,
        integrated_lesson_count=len(getattr(report, "integrated_lessons", [])),
        system_gap_count=len(getattr(report, "system_gaps", [])),
        next_day_action_count=len(getattr(report, "next_day_plan", [])),
        next_build_rec_count=len(getattr(report, "next_build_recommendations", [])),
    )


def build_north_star_dashboard_view(
    plan: Any = None,
    business_result: Any = None,
    self_build_result: Any = None,
    report: Any = None,
) -> NorthStarDashboardView:
    warnings: list[str] = []
    bp = getattr(plan, "business_plan", None) if plan else None
    sbp = getattr(plan, "self_build_plan", None) if plan else None

    biz_wf = getattr(bp, "workflow", None) if bp else None
    sb_wf = getattr(sbp, "workflow", None) if sbp else None

    if not plan:
        warnings.append("No integrated plan loaded")
    if not business_result:
        warnings.append("No business results captured")
    if not self_build_result:
        warnings.append("No self-build results captured")

    return NorthStarDashboardView(
        date=getattr(plan, "date", "") if plan else "",
        business_track_name=getattr(biz_wf, "name", "Unknown") if biz_wf else "No business plan",
        self_build_track_name=getattr(sb_wf, "name", "Unknown") if sb_wf else "No self-build plan",
        business_task_count=len(getattr(bp, "tasks", [])) if bp else 0,
        self_build_task_count=len(getattr(sbp, "tasks", [])) if sbp else 0,
        business_completed=len(getattr(business_result, "completed_tasks", [])) if business_result else 0,
        self_build_completed=len(getattr(self_build_result, "completed_tasks", [])) if self_build_result else 0,
        total_kpis=(
            len(getattr(business_result, "kpi_records", [])) if business_result else 0
        ) + (
            len(getattr(self_build_result, "kpi_records", [])) if self_build_result else 0
        ),
        total_objections=len(getattr(business_result, "objections", [])) if business_result else 0,
        total_bottlenecks=(
            len(getattr(business_result, "bottlenecks", [])) if business_result else 0
        ) + (
            len(getattr(self_build_result, "bottlenecks", [])) if self_build_result else 0
        ),
        system_gap_count=len(getattr(report, "system_gaps", [])) if report else 0,
        warnings=warnings,
    )
