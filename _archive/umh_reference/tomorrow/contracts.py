"""Phase 86 Tomorrow Loop contracts — shared enums, types, and base structures.

Defines the typed vocabulary for the EOS Tomorrow Operating Loop:
loop states, stage types, workflow stage tracking, KPI types, and
the core data structures consumed by the orchestrator and views.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


# ─── Enums ──────────────────────────────────────────────────────────


class LoopPhase(str, Enum):
    """Which phase of the daily loop is active."""

    NOT_STARTED = "not_started"
    PREPARE = "prepare"
    BRIEF = "brief"
    EXECUTE = "execute"
    REVIEW = "review"
    CLOSE = "close"
    HANDOFF = "handoff"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"


class WorkflowStageStatus(str, Enum):
    """Tracking status for a single stage in the operating workflow."""

    NOT_STARTED = "not_started"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


class KPIType(str, Enum):
    """Types of KPIs tracked by the operating loop."""

    COUNT = "count"
    RATE = "rate"
    CURRENCY = "currency"
    DURATION = "duration"
    PERCENTAGE = "percentage"
    BOOLEAN = "boolean"
    UNKNOWN = "unknown"


class ReviewOutcome(str, Enum):
    """Outcome of daily or weekly review."""

    ON_TRACK = "on_track"
    NEEDS_ADJUSTMENT = "needs_adjustment"
    BLOCKED = "blocked"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class LoopCadence(str, Enum):
    """Cadence for loop execution."""

    DAILY = "daily"
    WEEKLY = "weekly"
    UNKNOWN = "unknown"


# ─── Normalization ──────────────────────────────────────────────────


def normalize_loop_phase(value: str) -> LoopPhase:
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    for m in LoopPhase:
        if m.value == v:
            return m
    return LoopPhase.UNKNOWN


def normalize_stage_status(value: str) -> WorkflowStageStatus:
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    for m in WorkflowStageStatus:
        if m.value == v:
            return m
    return WorkflowStageStatus.UNKNOWN


def normalize_kpi_type(value: str) -> KPIType:
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    for m in KPIType:
        if m.value == v:
            return m
    return KPIType.UNKNOWN


def normalize_review_outcome(value: str) -> ReviewOutcome:
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    for m in ReviewOutcome:
        if m.value == v:
            return m
    return ReviewOutcome.UNKNOWN


# ─── ID Generation ──────────────────────────────────────────────────


def _loop_id(prefix: str = "loop") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── Core Data Structures ──────────────────────────────────────────


@dataclass
class KPIDefinition:
    """A single KPI tracked by the operating loop."""

    kpi_id: str = ""
    name: str = ""
    kpi_type: KPIType = KPIType.UNKNOWN
    target: str = ""
    current_value: str = ""
    stage_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kpi_id": self.kpi_id,
            "name": self.name,
            "kpi_type": self.kpi_type.value,
            "target": self.target,
            "current_value": self.current_value,
            "stage_ids": self.stage_ids,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowStage:
    """A single stage in the operating workflow (e.g., Content Strategy, Publishing)."""

    stage_id: str = ""
    stage_number: int = 0
    name: str = ""
    objective: str = ""
    owner: str = ""
    status: WorkflowStageStatus = WorkflowStageStatus.NOT_STARTED
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    kpi_ids: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    data_to_capture: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "stage_number": self.stage_number,
            "name": self.name,
            "objective": self.objective,
            "owner": self.owner,
            "status": self.status.value,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "kpi_ids": self.kpi_ids,
            "failure_modes": self.failure_modes,
            "data_to_capture": self.data_to_capture,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowTemplate:
    """A typed workflow template — maps a business process into trackable stages."""

    template_id: str = ""
    name: str = ""
    description: str = ""
    stages: list[WorkflowStage] = field(default_factory=list)
    kpis: list[KPIDefinition] = field(default_factory=list)
    cadence: LoopCadence = LoopCadence.DAILY
    owner: str = ""
    entity: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "stages": [s.to_dict() for s in self.stages],
            "kpis": [k.to_dict() for k in self.kpis],
            "cadence": self.cadence.value,
            "owner": self.owner,
            "entity": self.entity,
            "metadata": self.metadata,
        }

    @property
    def stage_count(self) -> int:
        return len(self.stages)

    @property
    def kpi_count(self) -> int:
        return len(self.kpis)


@dataclass
class DailyObjective:
    """A single objective for today's execution cycle."""

    objective_id: str = ""
    description: str = ""
    stage_id: str = ""
    priority: str = "medium"
    completed: bool = False
    result: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "description": self.description,
            "stage_id": self.stage_id,
            "priority": self.priority,
            "completed": self.completed,
            "result": self.result,
            "metadata": self.metadata,
        }


@dataclass
class DailyReview:
    """Result of the end-of-day review."""

    review_id: str = ""
    date: str = ""
    objectives_completed: int = 0
    objectives_total: int = 0
    outcome: ReviewOutcome = ReviewOutcome.UNKNOWN
    what_worked: list[str] = field(default_factory=list)
    what_didnt: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    tomorrow_priorities: list[str] = field(default_factory=list)
    kpi_updates: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "date": self.date,
            "objectives_completed": self.objectives_completed,
            "objectives_total": self.objectives_total,
            "outcome": self.outcome.value,
            "what_worked": self.what_worked,
            "what_didnt": self.what_didnt,
            "blockers": self.blockers,
            "tomorrow_priorities": self.tomorrow_priorities,
            "kpi_updates": self.kpi_updates,
            "metadata": self.metadata,
        }

    @property
    def completion_rate(self) -> float:
        if self.objectives_total == 0:
            return 0.0
        return self.objectives_completed / self.objectives_total


@dataclass
class TomorrowHandoff:
    """Handoff data from today to tomorrow's session."""

    handoff_id: str = ""
    date: str = ""
    continuity_notes: list[str] = field(default_factory=list)
    tomorrow_objectives: list[DailyObjective] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    blockers_carried: list[str] = field(default_factory=list)
    kpi_snapshot: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "handoff_id": self.handoff_id,
            "date": self.date,
            "continuity_notes": self.continuity_notes,
            "tomorrow_objectives": [o.to_dict() for o in self.tomorrow_objectives],
            "unresolved": self.unresolved,
            "blockers_carried": self.blockers_carried,
            "kpi_snapshot": self.kpi_snapshot,
            "metadata": self.metadata,
        }


@dataclass
class TomorrowLoopState:
    """Full state of a single day's operating loop."""

    loop_id: str = ""
    date: str = ""
    phase: LoopPhase = LoopPhase.NOT_STARTED
    template_id: str = ""
    objectives: list[DailyObjective] = field(default_factory=list)
    review: DailyReview | None = None
    handoff: TomorrowHandoff | None = None
    phase_transitions: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "loop_id": self.loop_id,
            "date": self.date,
            "phase": self.phase.value,
            "template_id": self.template_id,
            "objectives": [o.to_dict() for o in self.objectives],
            "review": self.review.to_dict() if self.review else None,
            "handoff": self.handoff.to_dict() if self.handoff else None,
            "phase_transitions": self.phase_transitions,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    @property
    def is_terminal(self) -> bool:
        return self.phase in (LoopPhase.COMPLETED, LoopPhase.FAILED)

    @property
    def objective_count(self) -> int:
        return len(self.objectives)

    @property
    def completed_count(self) -> int:
        return sum(1 for o in self.objectives if o.completed)
