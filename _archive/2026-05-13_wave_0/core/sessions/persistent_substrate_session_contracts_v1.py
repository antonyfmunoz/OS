"""Persistent Substrate Session Contracts v1.

Data shapes for persistent operational substrate sessions:
  SubstrateSession          — governed continuity container
  SessionChronology         — ordered event history
  SessionCheckpoint         — deterministic state snapshot
  SessionContinuityState    — unified continuity across layers
  SessionEmbodimentState    — embodiment layer state
  SessionWorkflowState      — workflow layer state
  SessionCognitionState     — cognition layer state
  SessionIngressState       — ingress layer state
  SessionLifecycleState     — lifecycle position
  SessionLineageReceipt     — immutable lineage record

A substrate session is a governed continuity container
around operational runtime state. The session does NOT
own intentionality — the operator still owns intentionality.

All contracts are immutable after creation. All carry provenance.
All serialize deterministically.

UMH substrate subsystem. Phase 96.8BV.
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


class SessionState(str, Enum):
    INITIALIZED = "initialized"
    ACTIVE = "active"
    CHECKPOINTED = "checkpointed"
    SUSPENDED = "suspended"
    RESUMED = "resumed"
    ARCHIVED = "archived"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class SessionEventType(str, Enum):
    SESSION_CREATED = "session_created"
    SESSION_RESTORED = "session_restored"
    SESSION_CHECKPOINTED = "session_checkpointed"
    SESSION_SUSPENDED = "session_suspended"
    SESSION_RESUMED = "session_resumed"
    SESSION_ARCHIVED = "session_archived"
    SESSION_TERMINATED = "session_terminated"
    SESSION_EXPIRED = "session_expired"
    CHRONOLOGY_UPDATED = "chronology_updated"


class ChronologyEventKind(str, Enum):
    SESSION_CREATION = "session_creation"
    RUNTIME_TRAVERSAL = "runtime_traversal"
    COGNITION_TRANSITION = "cognition_transition"
    WORKFLOW_TRANSITION = "workflow_transition"
    EMBODIMENT_TRANSITION = "embodiment_transition"
    INGRESS_TRANSITION = "ingress_transition"
    CONTINUITY_RESTORATION = "continuity_restoration"
    OPERATOR_RESUMPTION = "operator_resumption"


class CheckpointType(str, Enum):
    RESUMABLE = "resumable"
    REPLAYABLE = "replayable"
    LINEAGE_COMPLETE = "lineage_complete"


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------


@dataclass
class SessionLifecycleState:
    """Current lifecycle position of a substrate session."""

    session_id: str = ""
    state: str = field(default=SessionState.INITIALIZED.value)
    previous_state: str = ""
    transitions: int = 0
    entered_at: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.entered_at:
            self.entered_at = self.timestamp

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state,
            "previous_state": self.previous_state,
            "transitions": self.transitions,
            "entered_at": self.entered_at,
            "timestamp": self.timestamp,
        }


@dataclass
class SessionCognitionState:
    """Cognition layer state within a session."""

    session_id: str = ""
    operator_mode: str = ""
    cognition_phase: str = ""
    open_loops: int = 0
    focus_id: str = ""
    attention_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "operator_mode": self.operator_mode,
            "cognition_phase": self.cognition_phase,
            "open_loops": self.open_loops,
            "focus_id": self.focus_id,
            "attention_hash": self.attention_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class SessionWorkflowState:
    """Workflow layer state within a session."""

    session_id: str = ""
    active_workflows: int = 0
    completed_workflows: int = 0
    checkpointed_workflows: int = 0
    workflow_ids: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "active_workflows": self.active_workflows,
            "completed_workflows": self.completed_workflows,
            "checkpointed_workflows": self.checkpointed_workflows,
            "workflow_ids": list(self.workflow_ids),
            "timestamp": self.timestamp,
        }


@dataclass
class SessionEmbodimentState:
    """Embodiment layer state within a session."""

    session_id: str = ""
    workstation_mode: str = ""
    browser_mode: str = ""
    active_adapters: list[str] = field(default_factory=list)
    embodiment_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "workstation_mode": self.workstation_mode,
            "browser_mode": self.browser_mode,
            "active_adapters": list(self.active_adapters),
            "embodiment_hash": self.embodiment_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class SessionIngressState:
    """Ingress layer state within a session."""

    session_id: str = ""
    active_sources: list[str] = field(default_factory=list)
    total_signals: int = 0
    last_signal_id: str = ""
    ingress_session_ids: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "active_sources": list(self.active_sources),
            "total_signals": self.total_signals,
            "last_signal_id": self.last_signal_id,
            "ingress_session_ids": list(self.ingress_session_ids),
            "timestamp": self.timestamp,
        }


@dataclass
class SessionContinuityState:
    """Unified continuity state across all substrate layers."""

    session_id: str = ""
    continuity_id: str = ""
    cognition: SessionCognitionState | None = None
    workflow: SessionWorkflowState | None = None
    embodiment: SessionEmbodimentState | None = None
    ingress: SessionIngressState | None = None
    lifecycle: SessionLifecycleState | None = None
    previous_session_id: str = ""
    continuity_chain: list[str] = field(default_factory=list)
    content_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.continuity_id:
            self.continuity_id = _new_id("sscont")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.content_hash:
            self.content_hash = _content_hash(self._hashable())

    def _hashable(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "cognition": self.cognition.to_dict() if self.cognition else {},
            "workflow": self.workflow.to_dict() if self.workflow else {},
            "embodiment": self.embodiment.to_dict() if self.embodiment else {},
            "ingress": self.ingress.to_dict() if self.ingress else {},
            "lifecycle": self.lifecycle.to_dict() if self.lifecycle else {},
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "continuity_id": self.continuity_id,
            "cognition": self.cognition.to_dict() if self.cognition else {},
            "workflow": self.workflow.to_dict() if self.workflow else {},
            "embodiment": self.embodiment.to_dict() if self.embodiment else {},
            "ingress": self.ingress.to_dict() if self.ingress else {},
            "lifecycle": self.lifecycle.to_dict() if self.lifecycle else {},
            "previous_session_id": self.previous_session_id,
            "continuity_chain": list(self.continuity_chain),
            "content_hash": self.content_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class SessionChronology:
    """Ordered event history for a substrate session."""

    event_id: str = ""
    session_id: str = ""
    kind: str = ""
    description: str = ""
    source_layer: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    sequence_number: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = _new_id("sschron")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "kind": self.kind,
            "description": self.description,
            "source_layer": self.source_layer,
            "data": dict(self.data),
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp,
        }


@dataclass
class SessionCheckpoint:
    """Deterministic state snapshot of a substrate session."""

    checkpoint_id: str = ""
    session_id: str = ""
    checkpoint_type: str = field(default=CheckpointType.RESUMABLE.value)
    continuity_state: SessionContinuityState | None = None
    chronology_snapshot: list[dict[str, Any]] = field(default_factory=list)
    content_hash: str = ""
    sequence_number: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.checkpoint_id:
            self.checkpoint_id = _new_id("sschkp")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.content_hash:
            self.content_hash = _content_hash(self._hashable())

    def _hashable(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "checkpoint_type": self.checkpoint_type,
            "continuity_state": (
                self.continuity_state.to_dict()
                if self.continuity_state else {}
            ),
            "chronology_snapshot": self.chronology_snapshot,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "session_id": self.session_id,
            "checkpoint_type": self.checkpoint_type,
            "continuity_state": (
                self.continuity_state.to_dict()
                if self.continuity_state else {}
            ),
            "chronology_snapshot": list(self.chronology_snapshot),
            "content_hash": self.content_hash,
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp,
        }


@dataclass
class SessionLineageReceipt:
    """Immutable lineage record for session operations."""

    receipt_id: str = ""
    session_id: str = ""
    operation: str = ""
    from_state: str = ""
    to_state: str = ""
    checkpoint_id: str = ""
    content_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = _new_id("ssrcpt")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.content_hash:
            self.content_hash = _content_hash({
                "session_id": self.session_id,
                "operation": self.operation,
                "from_state": self.from_state,
                "to_state": self.to_state,
            })

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "session_id": self.session_id,
            "operation": self.operation,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "checkpoint_id": self.checkpoint_id,
            "content_hash": self.content_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class SubstrateSession:
    """Governed continuity container around operational runtime state.

    Does NOT own intentionality — the operator owns intentionality.
    Does NOT execute workflows — routes through canonical spine.
    """

    session_id: str = ""
    operator_id: str = ""
    lifecycle: SessionLifecycleState | None = None
    continuity: SessionContinuityState | None = None
    cognition: SessionCognitionState | None = None
    workflow: SessionWorkflowState | None = None
    embodiment: SessionEmbodimentState | None = None
    ingress: SessionIngressState | None = None
    chronology_count: int = 0
    checkpoint_count: int = 0
    previous_session_id: str = ""
    created_at: str = ""
    last_activity: str = ""
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = _new_id("sssess")
        if not self.created_at:
            self.created_at = _now_iso()
        if not self.last_activity:
            self.last_activity = self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "operator_id": self.operator_id,
            "lifecycle": self.lifecycle.to_dict() if self.lifecycle else {},
            "continuity": self.continuity.to_dict() if self.continuity else {},
            "cognition": self.cognition.to_dict() if self.cognition else {},
            "workflow": self.workflow.to_dict() if self.workflow else {},
            "embodiment": self.embodiment.to_dict() if self.embodiment else {},
            "ingress": self.ingress.to_dict() if self.ingress else {},
            "chronology_count": self.chronology_count,
            "checkpoint_count": self.checkpoint_count,
            "previous_session_id": self.previous_session_id,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "content_hash": self.content_hash,
        }
