"""Long-Horizon Operational Contracts v1.

Data shapes for governed long-horizon operational execution:
  OperationalObjective       — operator-defined goal
  OperationalCampaign        — bounded multi-stage execution plan
  ExecutionStage             — single bounded stage within a campaign
  DeferredExecutionState     — paused/scheduled execution state
  ExecutionDependency        — dependency between stages
  OperationalCheckpoint      — deterministic campaign snapshot
  OperationalConstraint      — structural execution limit
  OperationalApprovalState   — approval gate state
  OperationalExecutionReceipt — immutable execution lineage
  OperationalProgressState   — campaign progress tracking
  OperationalWaitingState    — governed waiting state
  OperationalContinuationState — resumable continuation state

Long-horizon execution is a governed sequence of bounded spine
traversals across time. The operator still owns intentionality.

All contracts are immutable after creation. All carry provenance.
All serialize deterministically.

UMH substrate subsystem. Phase 96.8BW.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:16]}"


def _content_hash(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class OperationalLifecycleState(str, Enum):
    INITIALIZED = "initialized"
    STAGED = "staged"
    WAITING = "waiting"
    APPROVED = "approved"
    EXECUTING = "executing"
    DEFERRED = "deferred"
    RESUMED = "resumed"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
    TERMINATED = "terminated"


class OperationalEventType(str, Enum):
    OBJECTIVE_CREATED = "objective_created"
    CAMPAIGN_STARTED = "campaign_started"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    STAGE_DEFERRED = "stage_deferred"
    CONTINUATION_RESTORED = "continuation_restored"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RECEIVED = "approval_received"
    EXECUTION_SUSPENDED = "execution_suspended"
    EXECUTION_RESUMED = "execution_resumed"
    EXECUTION_TERMINATED = "execution_terminated"


class DependencyType(str, Enum):
    STAGE = "stage"
    WORKFLOW = "workflow"
    CHECKPOINT = "checkpoint"
    GOVERNANCE = "governance"
    CHRONOLOGY = "chronology"
    APPROVAL = "approval"


class ChronologyEventKind(str, Enum):
    OBJECTIVE_CREATION = "objective_creation"
    CAMPAIGN_CREATION = "campaign_creation"
    STAGE_TRANSITION = "stage_transition"
    DEFERRED_EXECUTION = "deferred_execution"
    CONTINUATION_RESTORATION = "continuation_restoration"
    APPROVAL = "approval"
    GOVERNANCE_ESCALATION = "governance_escalation"
    STAGE_COMPLETION = "stage_completion"
    EXECUTION_SUSPENSION = "execution_suspension"
    EXECUTION_TERMINATION = "execution_termination"


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------


@dataclass
class OperationalObjective:
    """Operator-defined goal for long-horizon execution."""

    objective_id: str = ""
    operator_id: str = ""
    description: str = ""
    success_criteria: list[str] = field(default_factory=list)
    max_stages: int = 10
    max_duration_hours: int = 72
    created_at: str = ""
    set_by: str = "operator"

    def __post_init__(self) -> None:
        if not self.objective_id:
            self.objective_id = _new_id("opobj")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "operator_id": self.operator_id,
            "description": self.description,
            "success_criteria": list(self.success_criteria),
            "max_stages": self.max_stages,
            "max_duration_hours": self.max_duration_hours,
            "created_at": self.created_at,
            "set_by": self.set_by,
        }


@dataclass
class ExecutionStage:
    """Single bounded stage within an operational campaign."""

    stage_id: str = ""
    campaign_id: str = ""
    name: str = ""
    description: str = ""
    sequence: int = 0
    state: str = field(default=OperationalLifecycleState.INITIALIZED.value)
    depends_on: list[str] = field(default_factory=list)
    requires_approval: bool = False
    approved: bool = False
    started_at: str = ""
    completed_at: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.stage_id:
            self.stage_id = _new_id("opstg")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "campaign_id": self.campaign_id,
            "name": self.name,
            "description": self.description,
            "sequence": self.sequence,
            "state": self.state,
            "depends_on": list(self.depends_on),
            "requires_approval": self.requires_approval,
            "approved": self.approved,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "timestamp": self.timestamp,
        }


@dataclass
class OperationalCampaign:
    """Bounded multi-stage execution plan."""

    campaign_id: str = ""
    objective_id: str = ""
    session_id: str = ""
    operator_id: str = ""
    stages: list[ExecutionStage] = field(default_factory=list)
    state: str = field(default=OperationalLifecycleState.INITIALIZED.value)
    current_stage_index: int = 0
    max_fanout: int = 3
    created_at: str = ""
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.campaign_id:
            self.campaign_id = _new_id("opcmp")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "objective_id": self.objective_id,
            "session_id": self.session_id,
            "operator_id": self.operator_id,
            "stages": [s.to_dict() for s in self.stages],
            "state": self.state,
            "current_stage_index": self.current_stage_index,
            "max_fanout": self.max_fanout,
            "created_at": self.created_at,
            "content_hash": self.content_hash,
        }


@dataclass
class ExecutionDependency:
    """Dependency between execution stages."""

    dependency_id: str = ""
    source_stage_id: str = ""
    target_stage_id: str = ""
    dependency_type: str = field(default=DependencyType.STAGE.value)
    satisfied: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.dependency_id:
            self.dependency_id = _new_id("opdep")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "dependency_id": self.dependency_id,
            "source_stage_id": self.source_stage_id,
            "target_stage_id": self.target_stage_id,
            "dependency_type": self.dependency_type,
            "satisfied": self.satisfied,
            "timestamp": self.timestamp,
        }


@dataclass
class DeferredExecutionState:
    """Paused or scheduled execution state."""

    deferred_id: str = ""
    campaign_id: str = ""
    stage_id: str = ""
    reason: str = ""
    resume_condition: str = ""
    deferred_at: str = ""
    resume_after: str = ""
    resumed: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.deferred_id:
            self.deferred_id = _new_id("opdef")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.deferred_at:
            self.deferred_at = self.timestamp

    def to_dict(self) -> dict[str, Any]:
        return {
            "deferred_id": self.deferred_id,
            "campaign_id": self.campaign_id,
            "stage_id": self.stage_id,
            "reason": self.reason,
            "resume_condition": self.resume_condition,
            "deferred_at": self.deferred_at,
            "resume_after": self.resume_after,
            "resumed": self.resumed,
            "timestamp": self.timestamp,
        }


@dataclass
class OperationalCheckpoint:
    """Deterministic campaign snapshot."""

    checkpoint_id: str = ""
    campaign_id: str = ""
    stage_index: int = 0
    campaign_state: str = ""
    stage_states: list[dict[str, Any]] = field(default_factory=list)
    content_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.checkpoint_id:
            self.checkpoint_id = _new_id("opchkp")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.content_hash:
            self.content_hash = _content_hash(self._hashable())

    def _hashable(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "stage_index": self.stage_index,
            "campaign_state": self.campaign_state,
            "stage_states": self.stage_states,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "campaign_id": self.campaign_id,
            "stage_index": self.stage_index,
            "campaign_state": self.campaign_state,
            "stage_states": list(self.stage_states),
            "content_hash": self.content_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class OperationalConstraint:
    """Structural execution limit."""

    constraint_id: str = ""
    constraint_type: str = ""
    limit: int = 0
    current: int = 0
    passed: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.constraint_id:
            self.constraint_id = _new_id("opcon")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "constraint_type": self.constraint_type,
            "limit": self.limit,
            "current": self.current,
            "passed": self.passed,
            "timestamp": self.timestamp,
        }


@dataclass
class OperationalApprovalState:
    """Approval gate state."""

    approval_id: str = ""
    campaign_id: str = ""
    stage_id: str = ""
    requested_by: str = ""
    approved_by: str = ""
    approved: bool = False
    reason: str = ""
    requested_at: str = ""
    approved_at: str = ""

    def __post_init__(self) -> None:
        if not self.approval_id:
            self.approval_id = _new_id("opapv")
        if not self.requested_at:
            self.requested_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "campaign_id": self.campaign_id,
            "stage_id": self.stage_id,
            "requested_by": self.requested_by,
            "approved_by": self.approved_by,
            "approved": self.approved,
            "reason": self.reason,
            "requested_at": self.requested_at,
            "approved_at": self.approved_at,
        }


@dataclass
class OperationalExecutionReceipt:
    """Immutable execution lineage record."""

    receipt_id: str = ""
    campaign_id: str = ""
    stage_id: str = ""
    operation: str = ""
    from_state: str = ""
    to_state: str = ""
    content_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = _new_id("oprcpt")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.content_hash:
            self.content_hash = _content_hash({
                "campaign_id": self.campaign_id,
                "stage_id": self.stage_id,
                "operation": self.operation,
                "from_state": self.from_state,
                "to_state": self.to_state,
            })

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "campaign_id": self.campaign_id,
            "stage_id": self.stage_id,
            "operation": self.operation,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "content_hash": self.content_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class OperationalProgressState:
    """Campaign progress tracking."""

    campaign_id: str = ""
    total_stages: int = 0
    completed_stages: int = 0
    failed_stages: int = 0
    deferred_stages: int = 0
    current_stage_id: str = ""
    progress_pct: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()
        if self.total_stages > 0:
            self.progress_pct = round(
                self.completed_stages / self.total_stages * 100, 1
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "total_stages": self.total_stages,
            "completed_stages": self.completed_stages,
            "failed_stages": self.failed_stages,
            "deferred_stages": self.deferred_stages,
            "current_stage_id": self.current_stage_id,
            "progress_pct": self.progress_pct,
            "timestamp": self.timestamp,
        }


@dataclass
class OperationalWaitingState:
    """Governed waiting state."""

    waiting_id: str = ""
    campaign_id: str = ""
    stage_id: str = ""
    waiting_for: str = ""
    wait_type: str = ""
    entered_at: str = ""
    max_wait_hours: int = 24
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.waiting_id:
            self.waiting_id = _new_id("opwait")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.entered_at:
            self.entered_at = self.timestamp

    def to_dict(self) -> dict[str, Any]:
        return {
            "waiting_id": self.waiting_id,
            "campaign_id": self.campaign_id,
            "stage_id": self.stage_id,
            "waiting_for": self.waiting_for,
            "wait_type": self.wait_type,
            "entered_at": self.entered_at,
            "max_wait_hours": self.max_wait_hours,
            "timestamp": self.timestamp,
        }


@dataclass
class OperationalContinuationState:
    """Resumable continuation state."""

    continuation_id: str = ""
    campaign_id: str = ""
    checkpoint_id: str = ""
    session_id: str = ""
    stage_index: int = 0
    continuation_type: str = ""
    content_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.continuation_id:
            self.continuation_id = _new_id("opcont")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.content_hash:
            self.content_hash = _content_hash({
                "campaign_id": self.campaign_id,
                "checkpoint_id": self.checkpoint_id,
                "stage_index": self.stage_index,
            })

    def to_dict(self) -> dict[str, Any]:
        return {
            "continuation_id": self.continuation_id,
            "campaign_id": self.campaign_id,
            "checkpoint_id": self.checkpoint_id,
            "session_id": self.session_id,
            "stage_index": self.stage_index,
            "continuation_type": self.continuation_type,
            "content_hash": self.content_hash,
            "timestamp": self.timestamp,
        }
