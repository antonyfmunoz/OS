"""Phase 86 Tomorrow Loop views — UI-safe read models for loop data.

No sensitive data exposed. No execution. No mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


@dataclass
class TomorrowLoopView:
    """UI-safe view of the current day's operating loop."""

    loop_id: str = ""
    date: str = ""
    phase: str = ""
    template_name: str = ""
    objective_count: int = 0
    completed_count: int = 0
    completion_rate: float = 0.0
    review_outcome: str = ""
    has_handoff: bool = False
    blocker_count: int = 0
    warning_count: int = 0
    phase_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "loop_id": self.loop_id,
            "date": self.date,
            "phase": self.phase,
            "template_name": self.template_name,
            "objective_count": self.objective_count,
            "completed_count": self.completed_count,
            "completion_rate": round(self.completion_rate, 3),
            "review_outcome": self.review_outcome,
            "has_handoff": self.has_handoff,
            "blocker_count": self.blocker_count,
            "warning_count": self.warning_count,
            "phase_count": self.phase_count,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowTemplateView:
    """UI-safe view of a workflow template."""

    template_id: str = ""
    name: str = ""
    description: str = ""
    stage_count: int = 0
    kpi_count: int = 0
    cadence: str = ""
    owner: str = ""
    entity: str = ""
    stage_names: list[str] = field(default_factory=list)
    kpi_names: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "stage_count": self.stage_count,
            "kpi_count": self.kpi_count,
            "cadence": self.cadence,
            "owner": self.owner,
            "entity": self.entity,
            "stage_names": self.stage_names,
            "kpi_names": self.kpi_names,
            "metadata": self.metadata,
        }


@dataclass
class DailyBriefView:
    """UI-safe view of the morning briefing."""

    date: str = ""
    objective_count: int = 0
    active_stage_count: int = 0
    blocked_stage_count: int = 0
    active_stages: list[str] = field(default_factory=list)
    blocked_stages: list[str] = field(default_factory=list)
    carried_warnings: list[str] = field(default_factory=list)
    kpi_targets: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "objective_count": self.objective_count,
            "active_stage_count": self.active_stage_count,
            "blocked_stage_count": self.blocked_stage_count,
            "active_stages": self.active_stages,
            "blocked_stages": self.blocked_stages,
            "carried_warnings": self.carried_warnings,
            "kpi_targets": self.kpi_targets,
            "metadata": self.metadata,
        }


def loop_state_to_view(
    state: Any,
    template_name: str = "",
) -> TomorrowLoopView:
    """Convert a TomorrowLoopState to a UI-safe view."""
    phase = getattr(state, "phase", None)
    review = getattr(state, "review", None)
    handoff = getattr(state, "handoff", None)

    review_outcome = ""
    blocker_count = 0
    if review:
        outcome_obj = getattr(review, "outcome", None)
        review_outcome = (
            outcome_obj.value if hasattr(outcome_obj, "value") else str(outcome_obj or "")
        )
        blocker_count = len(getattr(review, "blockers", []))

    return TomorrowLoopView(
        loop_id=getattr(state, "loop_id", ""),
        date=getattr(state, "date", ""),
        phase=phase.value if hasattr(phase, "value") else str(phase or ""),
        template_name=template_name,
        objective_count=getattr(state, "objective_count", 0),
        completed_count=getattr(state, "completed_count", 0),
        completion_rate=(
            state.completed_count / state.objective_count
            if getattr(state, "objective_count", 0) > 0
            else 0.0
        ),
        review_outcome=review_outcome,
        has_handoff=handoff is not None,
        blocker_count=blocker_count,
        warning_count=len(getattr(state, "warnings", [])),
        phase_count=len(getattr(state, "phase_transitions", [])),
    )


def template_to_view(template: Any) -> WorkflowTemplateView:
    """Convert a WorkflowTemplate to a UI-safe view."""
    cadence = getattr(template, "cadence", None)
    stages = getattr(template, "stages", [])
    kpis = getattr(template, "kpis", [])

    return WorkflowTemplateView(
        template_id=getattr(template, "template_id", ""),
        name=getattr(template, "name", ""),
        description=getattr(template, "description", ""),
        stage_count=len(stages),
        kpi_count=len(kpis),
        cadence=cadence.value if hasattr(cadence, "value") else str(cadence or ""),
        owner=getattr(template, "owner", ""),
        entity=getattr(template, "entity", ""),
        stage_names=[getattr(s, "name", "") for s in stages],
        kpi_names=[getattr(k, "name", "") for k in kpis],
    )


def brief_from_state(state: Any) -> DailyBriefView:
    """Extract the briefing view from a TomorrowLoopState's metadata."""
    brief_data = getattr(state, "metadata", {}).get("brief", {})

    return DailyBriefView(
        date=brief_data.get("date", ""),
        objective_count=brief_data.get("objective_count", 0),
        active_stage_count=brief_data.get("active_stage_count", 0),
        blocked_stage_count=brief_data.get("blocked_stage_count", 0),
        active_stages=brief_data.get("active_stages", []),
        blocked_stages=brief_data.get("blocked_stages", []),
        carried_warnings=brief_data.get("carried_warnings", []),
        kpi_targets=brief_data.get("kpi_targets", []),
    )


def enrich_brief_with_leverage(
    brief: DailyBriefView,
    leverage_recommendations: list[Any] | None = None,
    bottlenecks: list[str] | None = None,
) -> DailyBriefView:
    """Optionally enrich a DailyBriefView with Phase 87 leverage data.

    Additive only — never modifies existing fields, only adds to metadata.
    If leverage_recommendations is None, returns the brief unchanged.
    """
    if leverage_recommendations is None:
        return brief

    brief.metadata["leverage"] = {
        "recommendation_count": len(leverage_recommendations),
        "top_actions": [getattr(r, "summary", str(r)) for r in leverage_recommendations[:5]],
        "bottlenecks": bottlenecks or [],
    }
    return brief
