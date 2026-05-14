"""Operational Workflow Contracts v1.

Data shapes for autonomous supervised operational workflows:
  OperationalWorkflow → WorkflowStep → WorkflowContext →
  WorkflowBoundary → WorkflowContinuation → WorkflowCheckpoint →
  WorkflowReceipt → WorkflowOutcome

These sit above the Phase 96.8BR live runtime contracts,
adding multi-step workflow orchestration, boundary policies,
checkpoint/resume semantics, and supervised operational modes.

All contracts are immutable after creation. All carry provenance.
All serialize deterministically.

UMH substrate subsystem. Phase 96.8BS.
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


def _deterministic_id(namespace: str, content: str) -> str:
    h = hashlib.sha256(f"{namespace}:{content}".encode("utf-8")).hexdigest()[:16]
    return f"{namespace}-{h}"


def _content_hash(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WorkflowType(str, Enum):
    OPERATIONAL_BRIEFING = "operational_briefing"
    OPERATIONAL_RESUME = "operational_resume"
    RUNTIME_INSPECTION = "runtime_inspection"
    GOVERNED_PLANNING = "governed_planning"
    BROWSER_INSPECTION = "browser_inspection"
    WORKSTATION_INSPECTION = "workstation_inspection"
    GOVERNED_ANALYSIS = "governed_analysis"
    CUSTOM = "custom"


class WorkflowStepType(str, Enum):
    SPINE_TRAVERSAL = "spine_traversal"
    CONTEXT_RETRIEVAL = "context_retrieval"
    CONTINUITY_CHECK = "continuity_check"
    GOVERNANCE_CHECK = "governance_check"
    CHECKPOINT = "checkpoint"
    AGGREGATION = "aggregation"
    REPORT_GENERATION = "report_generation"


class WorkflowPhase(str, Enum):
    INITIALIZED = "initialized"
    ACTIVE = "active"
    CHECKPOINTED = "checkpointed"
    WAITING = "waiting"
    RESUMED = "resumed"
    COMPLETED = "completed"
    DENIED = "denied"
    FAILED = "failed"
    TERMINATED = "terminated"


class WorkflowContinuationType(str, Enum):
    COMPLETE = "complete"
    CHECKPOINTED = "checkpointed"
    WAITING = "waiting"
    FAILED = "failed"
    DENIED = "denied"


class SupervisedOperationalMode(str, Enum):
    INSPECT_ONLY = "inspect_only"
    GOVERNED_ANALYSIS = "governed_analysis"
    OPERATIONAL_ASSISTANCE = "operational_assistance"
    SUPERVISED_EXECUTION = "supervised_execution"


class WorkflowDecisionType(str, Enum):
    START = "start"
    STEP_DISPATCH = "step_dispatch"
    CHECKPOINT = "checkpoint"
    BOUNDARY_CHECK = "boundary_check"
    GOVERNANCE = "governance"
    ESCALATION = "escalation"
    RESUME = "resume"
    COMPLETE = "complete"
    DENY = "deny"


# ---------------------------------------------------------------------------
# Mode permissions
# ---------------------------------------------------------------------------

MODE_PERMISSIONS: dict[str, dict[str, Any]] = {
    "inspect_only": {
        "allowed_step_types": [
            WorkflowStepType.SPINE_TRAVERSAL,
            WorkflowStepType.CONTEXT_RETRIEVAL,
            WorkflowStepType.CONTINUITY_CHECK,
            WorkflowStepType.AGGREGATION,
            WorkflowStepType.REPORT_GENERATION,
        ],
        "can_execute": False,
        "can_mutate": False,
        "max_depth": 6,
        "description": "Read-only inspection of runtime state",
    },
    "governed_analysis": {
        "allowed_step_types": [
            WorkflowStepType.SPINE_TRAVERSAL,
            WorkflowStepType.CONTEXT_RETRIEVAL,
            WorkflowStepType.CONTINUITY_CHECK,
            WorkflowStepType.GOVERNANCE_CHECK,
            WorkflowStepType.AGGREGATION,
            WorkflowStepType.REPORT_GENERATION,
        ],
        "can_execute": False,
        "can_mutate": False,
        "max_depth": 8,
        "description": "Analysis with governance evaluation, no execution",
    },
    "operational_assistance": {
        "allowed_step_types": [
            WorkflowStepType.SPINE_TRAVERSAL,
            WorkflowStepType.CONTEXT_RETRIEVAL,
            WorkflowStepType.CONTINUITY_CHECK,
            WorkflowStepType.GOVERNANCE_CHECK,
            WorkflowStepType.CHECKPOINT,
            WorkflowStepType.AGGREGATION,
            WorkflowStepType.REPORT_GENERATION,
        ],
        "can_execute": True,
        "can_mutate": False,
        "max_depth": 8,
        "description": "Governed operational assistance with checkpoints",
    },
    "supervised_execution": {
        "allowed_step_types": list(WorkflowStepType),
        "can_execute": True,
        "can_mutate": True,
        "max_depth": 10,
        "description": "Full supervised execution with all step types",
    },
}


# ---------------------------------------------------------------------------
# Contract 1: WorkflowBoundary
# ---------------------------------------------------------------------------


@dataclass
class WorkflowBoundary:
    """Boundary policies constraining workflow execution.

    Prevents runaway traversals, unbounded duration, and
    forbidden operational combinations.
    """

    boundary_id: str = ""
    max_traversal_depth: int = 10
    max_duration_seconds: float = 300.0
    max_embodiment_transitions: int = 5
    max_spine_traversals: int = 20
    forbidden_step_sequences: list[list[str]] = field(default_factory=list)
    forbidden_workflow_combinations: list[list[str]] = field(default_factory=list)
    operational_mode: SupervisedOperationalMode = SupervisedOperationalMode.INSPECT_ONLY
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.boundary_id:
            self.boundary_id = _new_id("wbnd")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.forbidden_step_sequences:
            self.forbidden_step_sequences = [
                ["spine_traversal", "spine_traversal", "spine_traversal", "spine_traversal"],
            ]

    def check_depth(self, current_depth: int) -> bool:
        mode_max = MODE_PERMISSIONS.get(self.operational_mode.value, {}).get(
            "max_depth", self.max_traversal_depth
        )
        effective_max = min(self.max_traversal_depth, mode_max)
        return current_depth < effective_max

    def check_traversals(self, current_count: int) -> bool:
        return current_count < self.max_spine_traversals

    def check_transitions(self, current_count: int) -> bool:
        return current_count < self.max_embodiment_transitions

    def check_step_allowed(self, step_type: WorkflowStepType) -> bool:
        mode_perms = MODE_PERMISSIONS.get(self.operational_mode.value, {})
        allowed = mode_perms.get("allowed_step_types", list(WorkflowStepType))
        return step_type in allowed

    def content_hash(self) -> str:
        return _content_hash(
            {
                "max_traversal_depth": self.max_traversal_depth,
                "max_duration_seconds": self.max_duration_seconds,
                "max_embodiment_transitions": self.max_embodiment_transitions,
                "max_spine_traversals": self.max_spine_traversals,
                "operational_mode": self.operational_mode.value,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "max_traversal_depth": self.max_traversal_depth,
            "max_duration_seconds": self.max_duration_seconds,
            "max_embodiment_transitions": self.max_embodiment_transitions,
            "max_spine_traversals": self.max_spine_traversals,
            "forbidden_step_sequences": self.forbidden_step_sequences,
            "forbidden_workflow_combinations": self.forbidden_workflow_combinations,
            "operational_mode": self.operational_mode.value,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 2: WorkflowStep
# ---------------------------------------------------------------------------


@dataclass
class WorkflowStep:
    """A single step within an operational workflow.

    Each step dispatches through the canonical spine or
    performs a governance/continuity check.
    """

    step_id: str = ""
    step_index: int = 0
    step_type: WorkflowStepType = WorkflowStepType.SPINE_TRAVERSAL
    command: str = ""
    description: str = ""
    target_domain: str = ""
    depends_on: list[str] = field(default_factory=list)
    governance_required: bool = True
    checkpoint_after: bool = False
    completed: bool = False
    result_summary: str = ""
    error_message: str = ""
    spine_outcome_id: str = ""
    duration_ms: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.step_id:
            self.step_id = _new_id("wstep")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "step_type": self.step_type.value,
                "command": self.command,
                "target_domain": self.target_domain,
                "governance_required": self.governance_required,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_index": self.step_index,
            "step_type": self.step_type.value,
            "command": self.command,
            "description": self.description,
            "target_domain": self.target_domain,
            "depends_on": self.depends_on,
            "governance_required": self.governance_required,
            "checkpoint_after": self.checkpoint_after,
            "completed": self.completed,
            "result_summary": self.result_summary,
            "error_message": self.error_message,
            "spine_outcome_id": self.spine_outcome_id,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 3: OperationalWorkflow
# ---------------------------------------------------------------------------


@dataclass
class OperationalWorkflow:
    """A multi-step supervised operational workflow.

    Defines an ordered sequence of steps that execute
    exclusively through the canonical spine. Bounded by
    policies and governed at every transition.
    """

    workflow_id: str = ""
    workflow_type: WorkflowType = WorkflowType.CUSTOM
    name: str = ""
    description: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    boundary: WorkflowBoundary = field(default_factory=WorkflowBoundary)
    operational_mode: SupervisedOperationalMode = SupervisedOperationalMode.INSPECT_ONLY
    correlation_id: str = ""
    session_id: str = ""
    initiated_by: str = ""
    total_steps: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.workflow_id:
            self.workflow_id = _new_id("wflow")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.correlation_id:
            self.correlation_id = _new_id("wcorr")

    def finalize(self) -> None:
        self.total_steps = len(self.steps)
        for i, step in enumerate(self.steps):
            step.step_index = i

    def content_hash(self) -> str:
        step_hashes = [s.content_hash() for s in self.steps]
        return _content_hash(
            {
                "workflow_type": self.workflow_type.value,
                "name": self.name,
                "steps": step_hashes,
                "operational_mode": self.operational_mode.value,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        self.finalize()
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type.value,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "boundary": self.boundary.to_dict(),
            "operational_mode": self.operational_mode.value,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "initiated_by": self.initiated_by,
            "total_steps": self.total_steps,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 4: WorkflowContext
# ---------------------------------------------------------------------------


@dataclass
class WorkflowContext:
    """Accumulated context carried through workflow execution.

    Tracks traversal depth, spine outcomes, boundary state,
    decisions, and accumulated results across all steps.
    """

    context_id: str = ""
    workflow_id: str = ""
    correlation_id: str = ""
    session_id: str = ""
    current_phase: WorkflowPhase = WorkflowPhase.INITIALIZED
    current_step_index: int = 0
    traversal_depth: int = 0
    spine_traversals: int = 0
    embodiment_transitions: int = 0
    last_embodiment: str = ""
    operational_mode: SupervisedOperationalMode = SupervisedOperationalMode.INSPECT_ONLY
    step_outcomes: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    lineage_receipts: list[str] = field(default_factory=list)
    accumulated_data: dict[str, Any] = field(default_factory=dict)
    start_time_iso: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.context_id:
            self.context_id = _new_id("wctx")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.start_time_iso:
            self.start_time_iso = self.timestamp

    def record_spine_traversal(self, embodiment_path: str) -> None:
        self.spine_traversals += 1
        self.traversal_depth += 1
        if embodiment_path != self.last_embodiment and self.last_embodiment:
            self.embodiment_transitions += 1
        self.last_embodiment = embodiment_path

    def add_step_outcome(self, step_id: str, outcome: dict[str, Any]) -> None:
        self.step_outcomes.append({"step_id": step_id, **outcome})

    def add_decision(self, decision: WorkflowDecision) -> None:
        self.decisions.append(decision.to_dict())

    def add_lineage_receipt(self, receipt_id: str) -> None:
        self.lineage_receipts.append(receipt_id)

    def content_hash(self) -> str:
        return _content_hash(
            {
                "workflow_id": self.workflow_id,
                "current_phase": self.current_phase.value,
                "spine_traversals": self.spine_traversals,
                "traversal_depth": self.traversal_depth,
                "operational_mode": self.operational_mode.value,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "workflow_id": self.workflow_id,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "current_phase": self.current_phase.value,
            "current_step_index": self.current_step_index,
            "traversal_depth": self.traversal_depth,
            "spine_traversals": self.spine_traversals,
            "embodiment_transitions": self.embodiment_transitions,
            "last_embodiment": self.last_embodiment,
            "operational_mode": self.operational_mode.value,
            "step_outcomes_count": len(self.step_outcomes),
            "decisions_count": len(self.decisions),
            "lineage_receipts": self.lineage_receipts,
            "accumulated_data_keys": list(self.accumulated_data.keys()),
            "start_time_iso": self.start_time_iso,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 5: WorkflowDecision
# ---------------------------------------------------------------------------


@dataclass
class WorkflowDecision:
    """A recorded decision made during workflow execution."""

    decision_id: str = ""
    decision_type: WorkflowDecisionType = WorkflowDecisionType.START
    workflow_id: str = ""
    step_id: str = ""
    phase: WorkflowPhase = WorkflowPhase.ACTIVE
    input_summary: str = ""
    output_summary: str = ""
    rules_applied: list[str] = field(default_factory=list)
    approved: bool = True
    denial_reason: str = ""
    correlation_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.decision_id:
            self.decision_id = _new_id("wdec")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "decision_type": self.decision_type.value,
                "workflow_id": self.workflow_id,
                "input_summary": self.input_summary,
                "approved": self.approved,
                "rules_applied": self.rules_applied,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type.value,
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "phase": self.phase.value,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "rules_applied": self.rules_applied,
            "approved": self.approved,
            "denial_reason": self.denial_reason,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 6: WorkflowCheckpoint
# ---------------------------------------------------------------------------


@dataclass
class WorkflowCheckpoint:
    """A checkpoint capturing workflow state at a specific step.

    Enables resume from the last checkpoint if a workflow
    is interrupted, fails, or needs to be continued later.
    """

    checkpoint_id: str = ""
    workflow_id: str = ""
    correlation_id: str = ""
    session_id: str = ""
    step_index: int = 0
    step_id: str = ""
    phase: WorkflowPhase = WorkflowPhase.CHECKPOINTED
    completed_steps: list[str] = field(default_factory=list)
    pending_steps: list[str] = field(default_factory=list)
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    accumulated_data: dict[str, Any] = field(default_factory=dict)
    boundary_state: dict[str, Any] = field(default_factory=dict)
    resumable: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.checkpoint_id:
            self.checkpoint_id = _new_id("wchk")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "workflow_id": self.workflow_id,
                "step_index": self.step_index,
                "completed_steps": self.completed_steps,
                "pending_steps": self.pending_steps,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "workflow_id": self.workflow_id,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "step_index": self.step_index,
            "step_id": self.step_id,
            "phase": self.phase.value,
            "completed_steps": self.completed_steps,
            "pending_steps": self.pending_steps,
            "context_snapshot": self.context_snapshot,
            "accumulated_data": self.accumulated_data,
            "boundary_state": self.boundary_state,
            "resumable": self.resumable,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 7: WorkflowReceipt
# ---------------------------------------------------------------------------


@dataclass
class WorkflowReceipt:
    """Proof that a workflow step was executed through governed channels.

    Links workflow-level lineage to spine-level lineage receipts,
    creating an auditable chain from workflow initiation to
    individual spine traversals.
    """

    receipt_id: str = ""
    workflow_id: str = ""
    step_id: str = ""
    correlation_id: str = ""
    phase: WorkflowPhase = WorkflowPhase.ACTIVE
    action: str = ""
    component: str = ""
    input_hash: str = ""
    output_hash: str = ""
    spine_receipt_ids: list[str] = field(default_factory=list)
    approved: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = _new_id("wrcpt")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "workflow_id": self.workflow_id,
                "step_id": self.step_id,
                "phase": self.phase.value,
                "action": self.action,
                "component": self.component,
                "input_hash": self.input_hash,
                "output_hash": self.output_hash,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "correlation_id": self.correlation_id,
            "phase": self.phase.value,
            "action": self.action,
            "component": self.component,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "spine_receipt_ids": self.spine_receipt_ids,
            "approved": self.approved,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 8: WorkflowOutcome
# ---------------------------------------------------------------------------


@dataclass
class WorkflowOutcome:
    """The final outcome of an operational workflow execution.

    Aggregates all step outcomes, spine traversals, governance
    decisions, and continuity state into one result.
    """

    outcome_id: str = ""
    workflow_id: str = ""
    workflow_type: WorkflowType = WorkflowType.CUSTOM
    correlation_id: str = ""
    session_id: str = ""
    status: WorkflowPhase = WorkflowPhase.COMPLETED
    steps_completed: int = 0
    steps_total: int = 0
    spine_traversals: int = 0
    embodiment_transitions: int = 0
    governance_decisions: int = 0
    checkpoints_created: int = 0
    operational_mode: SupervisedOperationalMode = SupervisedOperationalMode.INSPECT_ONLY
    result_data: dict[str, Any] = field(default_factory=dict)
    step_summaries: list[dict[str, Any]] = field(default_factory=list)
    error_message: str = ""
    duration_ms: float = 0.0
    lineage_receipts: list[str] = field(default_factory=list)
    boundary_violations: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.outcome_id:
            self.outcome_id = _new_id("wout")
        if not self.timestamp:
            self.timestamp = _now_iso()

    @property
    def succeeded(self) -> bool:
        return self.status == WorkflowPhase.COMPLETED

    @property
    def denied(self) -> bool:
        return self.status == WorkflowPhase.DENIED

    def content_hash(self) -> str:
        return _content_hash(
            {
                "workflow_id": self.workflow_id,
                "workflow_type": self.workflow_type.value,
                "status": self.status.value,
                "steps_completed": self.steps_completed,
                "spine_traversals": self.spine_traversals,
                "operational_mode": self.operational_mode.value,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type.value,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "steps_completed": self.steps_completed,
            "steps_total": self.steps_total,
            "spine_traversals": self.spine_traversals,
            "embodiment_transitions": self.embodiment_transitions,
            "governance_decisions": self.governance_decisions,
            "checkpoints_created": self.checkpoints_created,
            "operational_mode": self.operational_mode.value,
            "result_data": self.result_data,
            "step_summaries": self.step_summaries,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "lineage_receipts": self.lineage_receipts,
            "boundary_violations": self.boundary_violations,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 9: WorkflowContinuation
# ---------------------------------------------------------------------------


@dataclass
class WorkflowContinuation:
    """Continuation state after a workflow completes or is interrupted.

    Bridges workflow-level continuity to the runtime spine
    continuity layer from Phase 96.8BR.
    """

    continuation_id: str = ""
    workflow_id: str = ""
    correlation_id: str = ""
    session_id: str = ""
    continuation_type: WorkflowContinuationType = WorkflowContinuationType.COMPLETE
    checkpoint_id: str = ""
    open_loop_ids: list[str] = field(default_factory=list)
    resume_context: dict[str, Any] = field(default_factory=dict)
    next_actions: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.continuation_id:
            self.continuation_id = _new_id("wcont")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "workflow_id": self.workflow_id,
                "continuation_type": self.continuation_type.value,
                "checkpoint_id": self.checkpoint_id,
                "open_loop_ids": self.open_loop_ids,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "continuation_id": self.continuation_id,
            "workflow_id": self.workflow_id,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "continuation_type": self.continuation_type.value,
            "checkpoint_id": self.checkpoint_id,
            "open_loop_ids": self.open_loop_ids,
            "resume_context": self.resume_context,
            "next_actions": self.next_actions,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }
