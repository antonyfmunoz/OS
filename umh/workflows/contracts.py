"""Phase 88 workflow contracts — enums, types, and base structures.

Defines the typed vocabulary for the North Star Integrated Operating Test
Harness: workflow tracks, stages, statuses, KPI names, and the core
dataclasses consumed by the test harness, daily results, reviews, and views.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


# ─── Enums ──────────────────────────────────────────────────────────


class WorkflowTrack(str, Enum):
    BUSINESS_REVENUE = "business_revenue"
    SELF_BUILD = "self_build"
    UNKNOWN = "unknown"


class WorkflowStage(str, Enum):
    CONTEXT_LOAD = "context_load"
    STRATEGY_REVIEW = "strategy_review"
    LEVERAGE_REVIEW = "leverage_review"
    PLAN_GENERATION = "plan_generation"
    TASK_SELECTION = "task_selection"
    MANUAL_EXECUTION = "manual_execution"
    KPI_CAPTURE = "kpi_capture"
    RESULT_CAPTURE = "result_capture"
    OBJECTION_CAPTURE = "objection_capture"
    BOTTLENECK_CAPTURE = "bottleneck_capture"
    REVIEW = "review"
    TEMPLATE_CANDIDATE_EXTRACTION = "template_candidate_extraction"
    NEXT_DAY_RECOMMENDATION = "next_day_recommendation"
    CONTENT_STRATEGY = "content_strategy"
    CONTENT_PRODUCTION = "content_production"
    PUBLISHING = "publishing"
    ENGAGEMENT_CAPTURE = "engagement_capture"
    DM_CONVERSATION = "dm_conversation"
    LEAD_CAPTURE = "lead_capture"
    QUALIFICATION = "qualification"
    SALES_CONVERSATION = "sales_conversation"
    CLOSE_PAYMENT = "close_payment"
    ONBOARDING = "onboarding"
    FULFILLMENT = "fulfillment"
    PROGRESS_TRACKING = "progress_tracking"
    TESTIMONIAL_CAPTURE = "testimonial_capture"
    UPSELL_PATH = "upsell_path"
    END_OF_DAY_REVIEW = "end_of_day_review"
    WEEKLY_IMPROVEMENT = "weekly_improvement"
    UNKNOWN = "unknown"


class BusinessStage(str, Enum):
    CONTENT_STRATEGY = "content_strategy"
    CONTENT_PRODUCTION = "content_production"
    PUBLISHING = "publishing"
    ENGAGEMENT_CAPTURE = "engagement_capture"
    DM_CONVERSATION = "dm_conversation"
    LEAD_CAPTURE = "lead_capture"
    QUALIFICATION = "qualification"
    SALES_CONVERSATION = "sales_conversation"
    CLOSE_PAYMENT = "close_payment"
    ONBOARDING = "onboarding"
    FULFILLMENT = "fulfillment"
    PROGRESS_TRACKING = "progress_tracking"
    TESTIMONIAL_CAPTURE = "testimonial_capture"
    UPSELL_PATH = "upsell_path"
    END_OF_DAY_REVIEW = "end_of_day_review"
    WEEKLY_IMPROVEMENT = "weekly_improvement"
    UNKNOWN = "unknown"


class SelfBuildStage(str, Enum):
    PHASE_SELECTION = "phase_selection"
    DOC_CONTEXT_LOAD = "doc_context_load"
    ARCHITECTURE_REVIEW = "architecture_review"
    IMPLEMENTATION_PLAN = "implementation_plan"
    CODE_CHANGE = "code_change"
    TESTING = "testing"
    SAFETY_VALIDATION = "safety_validation"
    REPORTING = "reporting"
    ROADMAP_UPDATE = "roadmap_update"
    DRIFT_DETECTION = "drift_detection"
    NEXT_PHASE_RECOMMENDATION = "next_phase_recommendation"
    UNKNOWN = "unknown"


class WorkflowStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETE = "complete"
    SKIPPED = "skipped"
    NEEDS_REVIEW = "needs_review"
    UNKNOWN = "unknown"


class KPIName(str, Enum):
    POSTS_PUBLISHED = "posts_published"
    COMMENTS_GENERATED = "comments_generated"
    DMS_OPENED = "dms_opened"
    LEADS_CAPTURED = "leads_captured"
    QUALIFIED_LEADS = "qualified_leads"
    CALLS_BOOKED = "calls_booked"
    SHOW_UP_RATE = "show_up_rate"
    CLOSE_RATE = "close_rate"
    REVENUE_COLLECTED = "revenue_collected"
    ONBOARDING_COMPLETED = "onboarding_completed"
    FULFILLMENT_COMPLETED = "fulfillment_completed"
    TESTIMONIALS_CAPTURED = "testimonials_captured"
    OBJECTIONS_CAPTURED = "objections_captured"
    FOLLOWUPS_SENT = "followups_sent"
    MANUAL_HOURS_SPENT = "manual_hours_spent"
    BOTTLENECKS_FOUND = "bottlenecks_found"
    FILES_CHANGED = "files_changed"
    TESTS_ADDED = "tests_added"
    TESTS_PASSED = "tests_passed"
    REGRESSION_STATUS = "regression_status"
    SAFETY_VIOLATIONS = "safety_violations"
    PHASE_COMPLETION = "phase_completion"
    ARCHITECTURE_DRIFT_FOUND = "architecture_drift_found"
    TEMPLATE_CANDIDATES_FOUND = "template_candidates_found"
    UNKNOWN = "unknown"


# ─── Normalization ──────────────────────────────────────────────────


def _normalize(value: str, enum_cls: type[Enum]) -> Enum:
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    for m in enum_cls:
        if m.value == v:
            return m
    return enum_cls["UNKNOWN"]


def normalize_workflow_track(value: str) -> WorkflowTrack:
    return _normalize(value, WorkflowTrack)  # type: ignore[return-value]


def normalize_workflow_stage(value: str) -> WorkflowStage:
    return _normalize(value, WorkflowStage)  # type: ignore[return-value]


def normalize_business_stage(value: str) -> BusinessStage:
    return _normalize(value, BusinessStage)  # type: ignore[return-value]


def normalize_self_build_stage(value: str) -> SelfBuildStage:
    return _normalize(value, SelfBuildStage)  # type: ignore[return-value]


def normalize_workflow_status(value: str) -> WorkflowStatus:
    return _normalize(value, WorkflowStatus)  # type: ignore[return-value]


def normalize_kpi_name(value: str) -> KPIName:
    return _normalize(value, KPIName)  # type: ignore[return-value]


# ─── ID Generation ──────────────────────────────────────────────────


def _wf_id(prefix: str = "wf") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── Core Data Structures ──────────────────────────────────────────


@dataclass
class WorkflowDefinition:
    workflow_id: str = ""
    track: WorkflowTrack = WorkflowTrack.UNKNOWN
    name: str = ""
    purpose: str = ""
    stages: list[WorkflowStageDefinition] = field(default_factory=list)
    primary_company: str = ""
    product: str = ""
    owner: str = ""
    success_criteria: list[str] = field(default_factory=list)
    kpis: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "track": self.track.value,
            "name": self.name,
            "purpose": self.purpose,
            "stages": [s.to_dict() for s in self.stages],
            "primary_company": self.primary_company,
            "product": self.product,
            "owner": self.owner,
            "success_criteria": self.success_criteria,
            "kpis": self.kpis,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkflowDefinition:
        stages = [WorkflowStageDefinition.from_dict(s) for s in d.get("stages", [])]
        return cls(
            workflow_id=d.get("workflow_id", ""),
            track=normalize_workflow_track(d.get("track", "unknown")),
            name=d.get("name", ""),
            purpose=d.get("purpose", ""),
            stages=stages,
            primary_company=d.get("primary_company", ""),
            product=d.get("product", ""),
            owner=d.get("owner", ""),
            success_criteria=d.get("success_criteria", []),
            kpis=d.get("kpis", []),
            metadata=d.get("metadata", {}),
        )


@dataclass
class WorkflowStageDefinition:
    stage: WorkflowStage = WorkflowStage.UNKNOWN
    name: str = ""
    objective: str = ""
    expected_output: str = ""
    kpi: str = ""
    common_bottlenecks: list[str] = field(default_factory=list)
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "name": self.name,
            "objective": self.objective,
            "expected_output": self.expected_output,
            "kpi": self.kpi,
            "common_bottlenecks": self.common_bottlenecks,
            "notes": self.notes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkflowStageDefinition:
        return cls(
            stage=normalize_workflow_stage(d.get("stage", "unknown")),
            name=d.get("name", ""),
            objective=d.get("objective", ""),
            expected_output=d.get("expected_output", ""),
            kpi=d.get("kpi", ""),
            common_bottlenecks=d.get("common_bottlenecks", []),
            notes=d.get("notes", ""),
            metadata=d.get("metadata", {}),
        )


@dataclass
class WorkflowTask:
    task_id: str = ""
    track: WorkflowTrack = WorkflowTrack.UNKNOWN
    stage: WorkflowStage = WorkflowStage.UNKNOWN
    title: str = ""
    description: str = ""
    priority: str = "medium"
    estimated_minutes: int = 0
    leverage_type: str = ""
    owner: str = ""
    status: WorkflowStatus = WorkflowStatus.PLANNED
    expected_output: str = ""
    manual_only: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "track": self.track.value,
            "stage": self.stage.value,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "estimated_minutes": self.estimated_minutes,
            "leverage_type": self.leverage_type,
            "owner": self.owner,
            "status": self.status.value,
            "expected_output": self.expected_output,
            "manual_only": self.manual_only,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkflowTask:
        return cls(
            task_id=d.get("task_id", ""),
            track=normalize_workflow_track(d.get("track", "unknown")),
            stage=normalize_workflow_stage(d.get("stage", "unknown")),
            title=d.get("title", ""),
            description=d.get("description", ""),
            priority=d.get("priority", "medium"),
            estimated_minutes=d.get("estimated_minutes", 0),
            leverage_type=d.get("leverage_type", ""),
            owner=d.get("owner", ""),
            status=normalize_workflow_status(d.get("status", "planned")),
            expected_output=d.get("expected_output", ""),
            manual_only=d.get("manual_only", True),
            metadata=d.get("metadata", {}),
        )


@dataclass
class WorkflowKPIRecord:
    kpi_name: KPIName = KPIName.UNKNOWN
    value: float = 0.0
    unit: str = ""
    stage: WorkflowStage = WorkflowStage.UNKNOWN
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kpi_name": self.kpi_name.value,
            "value": self.value,
            "unit": self.unit,
            "stage": self.stage.value,
            "notes": self.notes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkflowKPIRecord:
        return cls(
            kpi_name=normalize_kpi_name(d.get("kpi_name", "unknown")),
            value=d.get("value", 0.0),
            unit=d.get("unit", ""),
            stage=normalize_workflow_stage(d.get("stage", "unknown")),
            notes=d.get("notes", ""),
            metadata=d.get("metadata", {}),
        )


@dataclass
class DailyWorkflowPlan:
    plan_id: str = ""
    date: str = ""
    workflow: WorkflowDefinition | None = None
    tasks: list[WorkflowTask] = field(default_factory=list)
    kpis_to_track: list[str] = field(default_factory=list)
    highest_leverage_actions: list[str] = field(default_factory=list)
    non_actions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "date": self.date,
            "workflow": self.workflow.to_dict() if self.workflow else None,
            "tasks": [t.to_dict() for t in self.tasks],
            "kpis_to_track": self.kpis_to_track,
            "highest_leverage_actions": self.highest_leverage_actions,
            "non_actions": self.non_actions,
            "risks": self.risks,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DailyWorkflowPlan:
        wf_data = d.get("workflow")
        workflow = WorkflowDefinition.from_dict(wf_data) if wf_data else None
        tasks = [WorkflowTask.from_dict(t) for t in d.get("tasks", [])]
        return cls(
            plan_id=d.get("plan_id", ""),
            date=d.get("date", ""),
            workflow=workflow,
            tasks=tasks,
            kpis_to_track=d.get("kpis_to_track", []),
            highest_leverage_actions=d.get("highest_leverage_actions", []),
            non_actions=d.get("non_actions", []),
            risks=d.get("risks", []),
            metadata=d.get("metadata", {}),
        )


@dataclass
class DailyWorkflowResult:
    result_id: str = ""
    date: str = ""
    completed_tasks: list[str] = field(default_factory=list)
    skipped_tasks: list[dict[str, str]] = field(default_factory=list)
    kpi_records: list[WorkflowKPIRecord] = field(default_factory=list)
    objections: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    bottlenecks: list[str] = field(default_factory=list)
    wins: list[str] = field(default_factory=list)
    losses: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "date": self.date,
            "completed_tasks": self.completed_tasks,
            "skipped_tasks": self.skipped_tasks,
            "kpi_records": [k.to_dict() for k in self.kpi_records],
            "objections": self.objections,
            "notes": self.notes,
            "bottlenecks": self.bottlenecks,
            "wins": self.wins,
            "losses": self.losses,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DailyWorkflowResult:
        kpi_records = [WorkflowKPIRecord.from_dict(k) for k in d.get("kpi_records", [])]
        return cls(
            result_id=d.get("result_id", ""),
            date=d.get("date", ""),
            completed_tasks=d.get("completed_tasks", []),
            skipped_tasks=d.get("skipped_tasks", []),
            kpi_records=kpi_records,
            objections=d.get("objections", []),
            notes=d.get("notes", []),
            bottlenecks=d.get("bottlenecks", []),
            wins=d.get("wins", []),
            losses=d.get("losses", []),
            metadata=d.get("metadata", {}),
        )


@dataclass
class DailyWorkflowReview:
    review_id: str = ""
    date: str = ""
    summary: str = ""
    what_worked: list[str] = field(default_factory=list)
    what_failed: list[str] = field(default_factory=list)
    bottlenecks: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    recommended_changes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "date": self.date,
            "summary": self.summary,
            "what_worked": self.what_worked,
            "what_failed": self.what_failed,
            "bottlenecks": self.bottlenecks,
            "lessons": self.lessons,
            "next_actions": self.next_actions,
            "recommended_changes": self.recommended_changes,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DailyWorkflowReview:
        return cls(
            review_id=d.get("review_id", ""),
            date=d.get("date", ""),
            summary=d.get("summary", ""),
            what_worked=d.get("what_worked", []),
            what_failed=d.get("what_failed", []),
            bottlenecks=d.get("bottlenecks", []),
            lessons=d.get("lessons", []),
            next_actions=d.get("next_actions", []),
            recommended_changes=d.get("recommended_changes", []),
            confidence=d.get("confidence", 0.0),
            metadata=d.get("metadata", {}),
        )


# ─── North Star Integrated Contracts ────────────────────────────────


@dataclass
class IntegratedOperatingPlan:
    plan_id: str = ""
    date: str = ""
    tracks: list[str] = field(default_factory=list)
    business_plan: DailyWorkflowPlan | None = None
    self_build_plan: DailyWorkflowPlan | None = None
    highest_leverage_actions: list[str] = field(default_factory=list)
    non_actions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    required_manual_inputs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "date": self.date,
            "tracks": self.tracks,
            "business_plan": self.business_plan.to_dict() if self.business_plan else None,
            "self_build_plan": self.self_build_plan.to_dict() if self.self_build_plan else None,
            "highest_leverage_actions": self.highest_leverage_actions,
            "non_actions": self.non_actions,
            "risks": self.risks,
            "required_manual_inputs": self.required_manual_inputs,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IntegratedOperatingPlan:
        bp = d.get("business_plan")
        sbp = d.get("self_build_plan")
        return cls(
            plan_id=d.get("plan_id", ""),
            date=d.get("date", ""),
            tracks=d.get("tracks", []),
            business_plan=DailyWorkflowPlan.from_dict(bp) if bp else None,
            self_build_plan=DailyWorkflowPlan.from_dict(sbp) if sbp else None,
            highest_leverage_actions=d.get("highest_leverage_actions", []),
            non_actions=d.get("non_actions", []),
            risks=d.get("risks", []),
            required_manual_inputs=d.get("required_manual_inputs", []),
            metadata=d.get("metadata", {}),
        )


@dataclass
class WorkflowResult:
    result_id: str = ""
    date: str = ""
    track: WorkflowTrack = WorkflowTrack.UNKNOWN
    completed_tasks: list[str] = field(default_factory=list)
    skipped_tasks: list[dict[str, str]] = field(default_factory=list)
    kpi_records: list[WorkflowKPIRecord] = field(default_factory=list)
    objections: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    bottlenecks: list[str] = field(default_factory=list)
    wins: list[str] = field(default_factory=list)
    losses: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "date": self.date,
            "track": self.track.value,
            "completed_tasks": self.completed_tasks,
            "skipped_tasks": self.skipped_tasks,
            "kpi_records": [k.to_dict() for k in self.kpi_records],
            "objections": self.objections,
            "notes": self.notes,
            "bottlenecks": self.bottlenecks,
            "wins": self.wins,
            "losses": self.losses,
            "artifacts": self.artifacts,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkflowResult:
        kpi_records = [WorkflowKPIRecord.from_dict(k) for k in d.get("kpi_records", [])]
        return cls(
            result_id=d.get("result_id", ""),
            date=d.get("date", ""),
            track=normalize_workflow_track(d.get("track", "unknown")),
            completed_tasks=d.get("completed_tasks", []),
            skipped_tasks=d.get("skipped_tasks", []),
            kpi_records=kpi_records,
            objections=d.get("objections", []),
            notes=d.get("notes", []),
            bottlenecks=d.get("bottlenecks", []),
            wins=d.get("wins", []),
            losses=d.get("losses", []),
            artifacts=d.get("artifacts", []),
            metadata=d.get("metadata", {}),
        )


@dataclass
class WorkflowReview:
    review_id: str = ""
    date: str = ""
    track: WorkflowTrack = WorkflowTrack.UNKNOWN
    summary: str = ""
    what_worked: list[str] = field(default_factory=list)
    what_failed: list[str] = field(default_factory=list)
    bottlenecks: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    recommended_changes: list[str] = field(default_factory=list)
    template_candidates: list[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "date": self.date,
            "track": self.track.value,
            "summary": self.summary,
            "what_worked": self.what_worked,
            "what_failed": self.what_failed,
            "bottlenecks": self.bottlenecks,
            "lessons": self.lessons,
            "next_actions": self.next_actions,
            "recommended_changes": self.recommended_changes,
            "template_candidates": self.template_candidates,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkflowReview:
        return cls(
            review_id=d.get("review_id", ""),
            date=d.get("date", ""),
            track=normalize_workflow_track(d.get("track", "unknown")),
            summary=d.get("summary", ""),
            what_worked=d.get("what_worked", []),
            what_failed=d.get("what_failed", []),
            bottlenecks=d.get("bottlenecks", []),
            lessons=d.get("lessons", []),
            next_actions=d.get("next_actions", []),
            recommended_changes=d.get("recommended_changes", []),
            template_candidates=d.get("template_candidates", []),
            confidence=d.get("confidence", 0.0),
            metadata=d.get("metadata", {}),
        )


@dataclass
class NorthStarTestReport:
    report_id: str = ""
    date: str = ""
    business_result: WorkflowResult | None = None
    self_build_result: WorkflowResult | None = None
    business_review: WorkflowReview | None = None
    self_build_review: WorkflowReview | None = None
    integrated_lessons: list[str] = field(default_factory=list)
    system_gaps: list[str] = field(default_factory=list)
    next_day_plan: list[str] = field(default_factory=list)
    next_build_recommendations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "date": self.date,
            "business_result": self.business_result.to_dict() if self.business_result else None,
            "self_build_result": self.self_build_result.to_dict() if self.self_build_result else None,
            "business_review": self.business_review.to_dict() if self.business_review else None,
            "self_build_review": self.self_build_review.to_dict() if self.self_build_review else None,
            "integrated_lessons": self.integrated_lessons,
            "system_gaps": self.system_gaps,
            "next_day_plan": self.next_day_plan,
            "next_build_recommendations": self.next_build_recommendations,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> NorthStarTestReport:
        br = d.get("business_result")
        sbr = d.get("self_build_result")
        brev = d.get("business_review")
        sbrev = d.get("self_build_review")
        return cls(
            report_id=d.get("report_id", ""),
            date=d.get("date", ""),
            business_result=WorkflowResult.from_dict(br) if br else None,
            self_build_result=WorkflowResult.from_dict(sbr) if sbr else None,
            business_review=WorkflowReview.from_dict(brev) if brev else None,
            self_build_review=WorkflowReview.from_dict(sbrev) if sbrev else None,
            integrated_lessons=d.get("integrated_lessons", []),
            system_gaps=d.get("system_gaps", []),
            next_day_plan=d.get("next_day_plan", []),
            next_build_recommendations=d.get("next_build_recommendations", []),
            metadata=d.get("metadata", {}),
        )
