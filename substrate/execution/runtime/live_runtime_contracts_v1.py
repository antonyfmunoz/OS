"""Live Runtime Contracts v1.

Data shapes for the live substrate runtime spine:
  RuntimeSignal → RuntimeContext → RuntimeDecision →
  RuntimeExecutionPlan → RuntimeExecutionStep →
  RuntimeOutcome → RuntimeContinuation → RuntimeLineageReceipt

These sit above the base execution contracts,
adding cognition, planning, continuation, and lineage dimensions.

All contracts are immutable after creation. All carry provenance.
All serialize deterministically.

UMH substrate subsystem.
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


class RuntimeSignalSource(str, Enum):
    DISCORD = "discord"
    SPINE = "spine"
    ORCHESTRATOR = "orchestrator"
    CRON = "cron"
    API = "api"
    MANUAL = "manual"
    WORKFLOW = "workflow"
    CONTINUATION = "continuation"


class RuntimePhase(str, Enum):
    SIGNAL_RECEIVED = "signal_received"
    COGNITION = "cognition"
    ROUTING = "routing"
    GOVERNANCE = "governance"
    PLANNING = "planning"
    EXECUTION = "execution"
    OBSERVATION = "observation"
    CONTINUITY = "continuity"
    COMPLETE = "complete"
    FAILED = "failed"


class RuntimeDecisionType(str, Enum):
    ROUTE = "route"
    GOVERN = "govern"
    PLAN = "plan"
    EXECUTE = "execute"
    CONTINUE = "continue"
    DEFER = "defer"
    DENY = "deny"


class RuntimeStepType(str, Enum):
    SHELL = "shell"
    BROWSER = "browser"
    GUI = "gui"
    TMUX = "tmux"
    MEMORY = "memory"
    REPORT = "report"
    INSPECT = "inspect"


class RuntimeOutcomeStatus(str, Enum):
    SUCCESS = "success"
    DENIED = "denied"
    FAILED = "failed"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    DEFERRED = "deferred"


class RuntimeContinuationType(str, Enum):
    COMPLETE = "complete"
    OPEN_LOOP = "open_loop"
    RESUME_REQUIRED = "resume_required"
    DEFERRED = "deferred"


# ---------------------------------------------------------------------------
# Contract 1: RuntimeSignal
# ---------------------------------------------------------------------------


@dataclass
class RuntimeSignal:
    """The entry point into the live runtime spine.

    Wraps a raw command/event with source context and
    correlation tracking.
    """

    signal_id: str = ""
    source: RuntimeSignalSource = RuntimeSignalSource.MANUAL
    raw_input: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    user_id: str = ""
    channel_id: str = ""
    correlation_id: str = ""
    session_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.signal_id:
            self.signal_id = _new_id("lsig")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.correlation_id:
            self.correlation_id = _new_id("lcorr")

    def content_hash(self) -> str:
        return _content_hash(
            {
                "source": self.source.value,
                "raw_input": self.raw_input,
                "payload": self.payload,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "source": self.source.value,
            "raw_input": self.raw_input,
            "payload": self.payload,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 2: RuntimeContext
# ---------------------------------------------------------------------------


@dataclass
class RuntimeContext:
    """Accumulated context carried through the runtime pipeline.

    Built up incrementally: cognition adds interpretation,
    routing adds capability/environment, governance adds verdict,
    planning adds steps.
    """

    context_id: str = ""
    signal_id: str = ""
    correlation_id: str = ""
    session_id: str = ""
    current_phase: RuntimePhase = RuntimePhase.SIGNAL_RECEIVED

    command_name: str = ""
    command_args: dict[str, Any] = field(default_factory=dict)
    intent_type: str = ""
    domain: str = ""

    capability_resolved: str = ""
    environment_resolved: str = ""
    embodiment_path: str = ""
    governance_verdict: str = ""
    governance_rules: list[str] = field(default_factory=list)
    risk_class: str = "safe"

    memory_context: list[dict[str, Any]] = field(default_factory=list)
    continuity_context: dict[str, Any] = field(default_factory=dict)
    open_loops: list[dict[str, Any]] = field(default_factory=list)

    decisions: list[dict[str, Any]] = field(default_factory=list)
    lineage_receipts: list[str] = field(default_factory=list)

    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.context_id:
            self.context_id = _new_id("lctx")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def add_decision(self, decision: RuntimeDecision) -> None:
        self.decisions.append(decision.to_dict())

    def add_lineage_receipt(self, receipt_id: str) -> None:
        self.lineage_receipts.append(receipt_id)

    def content_hash(self) -> str:
        return _content_hash(
            {
                "signal_id": self.signal_id,
                "command_name": self.command_name,
                "capability_resolved": self.capability_resolved,
                "governance_verdict": self.governance_verdict,
                "embodiment_path": self.embodiment_path,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "signal_id": self.signal_id,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "current_phase": self.current_phase.value,
            "command_name": self.command_name,
            "command_args": self.command_args,
            "intent_type": self.intent_type,
            "domain": self.domain,
            "capability_resolved": self.capability_resolved,
            "environment_resolved": self.environment_resolved,
            "embodiment_path": self.embodiment_path,
            "governance_verdict": self.governance_verdict,
            "governance_rules": self.governance_rules,
            "risk_class": self.risk_class,
            "memory_context_count": len(self.memory_context),
            "open_loops_count": len(self.open_loops),
            "decisions_count": len(self.decisions),
            "lineage_receipts": self.lineage_receipts,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 3: RuntimeDecision
# ---------------------------------------------------------------------------


@dataclass
class RuntimeDecision:
    """A recorded decision made during runtime pipeline traversal."""

    decision_id: str = ""
    decision_type: RuntimeDecisionType = RuntimeDecisionType.ROUTE
    phase: RuntimePhase = RuntimePhase.ROUTING
    input_summary: str = ""
    output_summary: str = ""
    rules_applied: list[str] = field(default_factory=list)
    approved: bool = True
    denial_reason: str = ""
    correlation_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.decision_id:
            self.decision_id = _new_id("ldec")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "decision_type": self.decision_type.value,
                "input_summary": self.input_summary,
                "approved": self.approved,
                "rules_applied": self.rules_applied,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type.value,
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
# Contract 4: RuntimeExecutionPlan
# ---------------------------------------------------------------------------


@dataclass
class RuntimeExecutionPlan:
    """A plan of execution steps derived from cognition and routing."""

    plan_id: str = ""
    signal_id: str = ""
    correlation_id: str = ""
    steps: list[RuntimeExecutionStep] = field(default_factory=list)
    total_steps: int = 0
    governance_approved: bool = False
    embodiment_path: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.plan_id:
            self.plan_id = _new_id("lplan")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def finalize(self) -> None:
        self.total_steps = len(self.steps)

    def content_hash(self) -> str:
        step_hashes = [s.content_hash() for s in self.steps]
        return _content_hash(
            {
                "signal_id": self.signal_id,
                "steps": step_hashes,
                "embodiment_path": self.embodiment_path,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        self.finalize()
        return {
            "plan_id": self.plan_id,
            "signal_id": self.signal_id,
            "correlation_id": self.correlation_id,
            "total_steps": self.total_steps,
            "steps": [s.to_dict() for s in self.steps],
            "governance_approved": self.governance_approved,
            "embodiment_path": self.embodiment_path,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 5: RuntimeExecutionStep
# ---------------------------------------------------------------------------


@dataclass
class RuntimeExecutionStep:
    """A single step within a runtime execution plan."""

    step_id: str = ""
    step_index: int = 0
    step_type: RuntimeStepType = RuntimeStepType.INSPECT
    command: str = ""
    target: str = ""
    adapter: str = ""
    environment: str = ""
    governance_verdict: str = "approved"
    risk_class: str = "safe"
    completed: bool = False
    result_summary: str = ""
    error_message: str = ""
    duration_ms: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.step_id:
            self.step_id = _new_id("lstep")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "step_type": self.step_type.value,
                "command": self.command,
                "target": self.target,
                "adapter": self.adapter,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_index": self.step_index,
            "step_type": self.step_type.value,
            "command": self.command,
            "target": self.target,
            "adapter": self.adapter,
            "environment": self.environment,
            "governance_verdict": self.governance_verdict,
            "risk_class": self.risk_class,
            "completed": self.completed,
            "result_summary": self.result_summary,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 6: RuntimeOutcome
# ---------------------------------------------------------------------------


@dataclass
class RuntimeOutcome:
    """The final outcome of a runtime spine traversal."""

    outcome_id: str = ""
    signal_id: str = ""
    correlation_id: str = ""
    session_id: str = ""
    status: RuntimeOutcomeStatus = RuntimeOutcomeStatus.SUCCESS
    command_name: str = ""
    embodiment_path: str = ""
    steps_completed: int = 0
    steps_total: int = 0
    governance_verdict: str = ""
    governance_rules: list[str] = field(default_factory=list)
    result_data: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    duration_ms: float = 0.0
    memory_promotions: list[str] = field(default_factory=list)
    lineage_receipts: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.outcome_id:
            self.outcome_id = _new_id("lout")
        if not self.timestamp:
            self.timestamp = _now_iso()

    @property
    def succeeded(self) -> bool:
        return self.status == RuntimeOutcomeStatus.SUCCESS

    def content_hash(self) -> str:
        return _content_hash(
            {
                "signal_id": self.signal_id,
                "status": self.status.value,
                "command_name": self.command_name,
                "governance_verdict": self.governance_verdict,
                "embodiment_path": self.embodiment_path,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "signal_id": self.signal_id,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "command_name": self.command_name,
            "embodiment_path": self.embodiment_path,
            "steps_completed": self.steps_completed,
            "steps_total": self.steps_total,
            "governance_verdict": self.governance_verdict,
            "governance_rules": self.governance_rules,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "memory_promotions": self.memory_promotions,
            "lineage_receipts": self.lineage_receipts,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 7: RuntimeContinuation
# ---------------------------------------------------------------------------


@dataclass
class RuntimeContinuation:
    """Continuation state after a runtime spine traversal.

    Captures whether execution is complete, has open loops,
    requires resume, or was deferred.
    """

    continuation_id: str = ""
    outcome_id: str = ""
    correlation_id: str = ""
    session_id: str = ""
    continuation_type: RuntimeContinuationType = RuntimeContinuationType.COMPLETE
    open_loop_ids: list[str] = field(default_factory=list)
    resume_context: dict[str, Any] = field(default_factory=dict)
    deferred_reason: str = ""
    next_actions: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.continuation_id:
            self.continuation_id = _new_id("lcont")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "outcome_id": self.outcome_id,
                "continuation_type": self.continuation_type.value,
                "open_loop_ids": self.open_loop_ids,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "continuation_id": self.continuation_id,
            "outcome_id": self.outcome_id,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "continuation_type": self.continuation_type.value,
            "open_loop_ids": self.open_loop_ids,
            "resume_context": self.resume_context,
            "deferred_reason": self.deferred_reason,
            "next_actions": self.next_actions,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 8: RuntimeLineageReceipt
# ---------------------------------------------------------------------------


@dataclass
class RuntimeLineageReceipt:
    """Proof that a runtime step went through the canonical spine.

    Every routing, governance, execution, continuity, and
    observability step emits a receipt. The collection of
    receipts for one signal proves single-spine traversal.
    """

    receipt_id: str = ""
    signal_id: str = ""
    correlation_id: str = ""
    phase: RuntimePhase = RuntimePhase.SIGNAL_RECEIVED
    action: str = ""
    component: str = ""
    input_hash: str = ""
    output_hash: str = ""
    decision_id: str = ""
    approved: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = _new_id("lrcpt")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "signal_id": self.signal_id,
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
            "signal_id": self.signal_id,
            "correlation_id": self.correlation_id,
            "phase": self.phase.value,
            "action": self.action,
            "component": self.component,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "decision_id": self.decision_id,
            "approved": self.approved,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }
