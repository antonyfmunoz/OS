"""Live Runtime Ingress Contracts v1.

Data shapes for live runtime ingress integration:
  RuntimeIngressSignal    — normalized ingress from any surface
  RuntimeIngressSession   — ingress session with operator binding
  RuntimeIngressContext   — contextual state at ingress time
  RuntimeIngressIdentity  — operator identity from ingress surface
  RuntimeIngressReceipt   — proof of ingress processing
  RuntimeIngressResponse  — normalized response to ingress surface
  RuntimeIngressBoundary  — boundary check result for ingress
  RuntimeIngressLineage   — lineage record for ingress traversal

Every ingress surface (Discord, CLI, API, future) produces
the same normalized signal. The ingress is NOT the runtime —
it is a signal entrypoint into the canonical substrate.

All contracts are immutable after creation. All carry provenance.
All serialize deterministically.

UMH substrate subsystem. Phase 96.8BU.
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


class IngressSource(str, Enum):
    DISCORD = "discord"
    CLI = "cli"
    API = "api"
    WEBHOOK = "webhook"
    CRON = "cron"
    INTERNAL = "internal"


class IngressPhase(str, Enum):
    RECEIVED = "received"
    NORMALIZED = "normalized"
    AUTHENTICATED = "authenticated"
    ROUTED = "routed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    DENIED = "denied"
    FAILED = "failed"
    EXPIRED = "expired"


class IngressSessionState(str, Enum):
    INITIALIZED = "initialized"
    AUTHENTICATED = "authenticated"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RESUMED = "resumed"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class IngressEventType(str, Enum):
    INGRESS_RECEIVED = "ingress_received"
    INGRESS_NORMALIZED = "ingress_normalized"
    INGRESS_AUTHENTICATED = "ingress_authenticated"
    INGRESS_ROUTED = "ingress_routed"
    INGRESS_DENIED = "ingress_denied"
    INGRESS_COMPLETED = "ingress_completed"
    INGRESS_RESUMED = "ingress_resumed"
    INGRESS_EXPIRED = "ingress_expired"


# ---------------------------------------------------------------------------
# Contract 1: RuntimeIngressSignal
# ---------------------------------------------------------------------------


@dataclass
class RuntimeIngressSignal:
    """A normalized ingress signal from any surface."""

    signal_id: str = ""
    source: IngressSource = IngressSource.DISCORD
    raw_input: str = ""
    normalized_command: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    operator_id: str = ""
    channel_id: str = ""
    session_id: str = ""
    correlation_id: str = ""
    ingress_phase: IngressPhase = IngressPhase.RECEIVED
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.signal_id:
            self.signal_id = _new_id("ingsig")
        if not self.correlation_id:
            self.correlation_id = _new_id("ingcorr")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash({
            "source": self.source.value,
            "raw_input": self.raw_input,
            "normalized_command": self.normalized_command,
            "operator_id": self.operator_id,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "source": self.source.value,
            "raw_input": self.raw_input,
            "normalized_command": self.normalized_command,
            "payload": self.payload,
            "operator_id": self.operator_id,
            "channel_id": self.channel_id,
            "session_id": self.session_id,
            "correlation_id": self.correlation_id,
            "ingress_phase": self.ingress_phase.value,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 2: RuntimeIngressSession
# ---------------------------------------------------------------------------


@dataclass
class RuntimeIngressSession:
    """An ingress session binding operator to runtime."""

    session_id: str = ""
    source: IngressSource = IngressSource.DISCORD
    operator_id: str = ""
    state: IngressSessionState = IngressSessionState.INITIALIZED
    started_at: str = ""
    last_activity: str = ""
    signals_processed: int = 0
    active_workflow_ids: list[str] = field(default_factory=list)
    continuity_chain_ids: list[str] = field(default_factory=list)
    cognition_session_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = _new_id("ingsess")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.started_at:
            self.started_at = self.timestamp
        if not self.last_activity:
            self.last_activity = self.timestamp

    def content_hash(self) -> str:
        return _content_hash({
            "source": self.source.value,
            "operator_id": self.operator_id,
            "state": self.state.value,
            "signals_processed": self.signals_processed,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "source": self.source.value,
            "operator_id": self.operator_id,
            "state": self.state.value,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
            "signals_processed": self.signals_processed,
            "active_workflow_ids": self.active_workflow_ids,
            "continuity_chain_ids": self.continuity_chain_ids,
            "cognition_session_id": self.cognition_session_id,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 3: RuntimeIngressContext
# ---------------------------------------------------------------------------


@dataclass
class RuntimeIngressContext:
    """Contextual state captured at ingress time."""

    context_id: str = ""
    session_id: str = ""
    source: IngressSource = IngressSource.DISCORD
    active_focus_id: str = ""
    active_workflow_id: str = ""
    open_loop_count: int = 0
    continuity_chain_length: int = 0
    operator_mode: str = ""
    cognition_phase: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.context_id:
            self.context_id = _new_id("ingctx")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash({
            "source": self.source.value,
            "active_focus_id": self.active_focus_id,
            "open_loop_count": self.open_loop_count,
            "operator_mode": self.operator_mode,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "session_id": self.session_id,
            "source": self.source.value,
            "active_focus_id": self.active_focus_id,
            "active_workflow_id": self.active_workflow_id,
            "open_loop_count": self.open_loop_count,
            "continuity_chain_length": self.continuity_chain_length,
            "operator_mode": self.operator_mode,
            "cognition_phase": self.cognition_phase,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 4: RuntimeIngressIdentity
# ---------------------------------------------------------------------------


@dataclass
class RuntimeIngressIdentity:
    """Operator identity from an ingress surface."""

    identity_id: str = ""
    operator_id: str = ""
    source: IngressSource = IngressSource.DISCORD
    display_name: str = ""
    source_specific_id: str = ""
    authenticated: bool = False
    roles: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.identity_id:
            self.identity_id = _new_id("ingid")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash({
            "operator_id": self.operator_id,
            "source": self.source.value,
            "source_specific_id": self.source_specific_id,
            "authenticated": self.authenticated,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity_id": self.identity_id,
            "operator_id": self.operator_id,
            "source": self.source.value,
            "display_name": self.display_name,
            "source_specific_id": self.source_specific_id,
            "authenticated": self.authenticated,
            "roles": self.roles,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 5: RuntimeIngressReceipt
# ---------------------------------------------------------------------------


@dataclass
class RuntimeIngressReceipt:
    """Proof that an ingress signal was processed through governed channels."""

    receipt_id: str = ""
    signal_id: str = ""
    session_id: str = ""
    source: IngressSource = IngressSource.DISCORD
    ingress_phase: IngressPhase = IngressPhase.COMPLETED
    spine_outcome_id: str = ""
    governance_verdict: str = ""
    duration_ms: float = 0.0
    approved: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = _new_id("ingrcpt")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash({
            "signal_id": self.signal_id,
            "source": self.source.value,
            "ingress_phase": self.ingress_phase.value,
            "spine_outcome_id": self.spine_outcome_id,
            "approved": self.approved,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "signal_id": self.signal_id,
            "session_id": self.session_id,
            "source": self.source.value,
            "ingress_phase": self.ingress_phase.value,
            "spine_outcome_id": self.spine_outcome_id,
            "governance_verdict": self.governance_verdict,
            "duration_ms": round(self.duration_ms, 2),
            "approved": self.approved,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 6: RuntimeIngressResponse
# ---------------------------------------------------------------------------


@dataclass
class RuntimeIngressResponse:
    """Normalized response from substrate back to ingress surface."""

    response_id: str = ""
    signal_id: str = ""
    session_id: str = ""
    source: IngressSource = IngressSource.DISCORD
    status: str = "success"
    command_name: str = ""
    result_data: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    receipt_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.response_id:
            self.response_id = _new_id("ingresp")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash({
            "signal_id": self.signal_id,
            "status": self.status,
            "command_name": self.command_name,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id": self.response_id,
            "signal_id": self.signal_id,
            "session_id": self.session_id,
            "source": self.source.value,
            "status": self.status,
            "command_name": self.command_name,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "receipt_id": self.receipt_id,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 7: RuntimeIngressBoundary
# ---------------------------------------------------------------------------


@dataclass
class RuntimeIngressBoundary:
    """Boundary check result for an ingress signal."""

    boundary_id: str = ""
    signal_id: str = ""
    check_type: str = ""
    passed: bool = True
    current_value: int = 0
    limit_value: int = 0
    violation_message: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.boundary_id:
            self.boundary_id = _new_id("ingbnd")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash({
            "check_type": self.check_type,
            "passed": self.passed,
            "current_value": self.current_value,
            "limit_value": self.limit_value,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "signal_id": self.signal_id,
            "check_type": self.check_type,
            "passed": self.passed,
            "current_value": self.current_value,
            "limit_value": self.limit_value,
            "violation_message": self.violation_message,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 8: RuntimeIngressLineage
# ---------------------------------------------------------------------------


@dataclass
class RuntimeIngressLineage:
    """Lineage record linking ingress to runtime traversal."""

    lineage_id: str = ""
    signal_id: str = ""
    session_id: str = ""
    source: IngressSource = IngressSource.DISCORD
    spine_signal_id: str = ""
    spine_outcome_id: str = ""
    cognition_session_id: str = ""
    workflow_id: str = ""
    continuity_record_id: str = ""
    ingress_phase: IngressPhase = IngressPhase.COMPLETED
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.lineage_id:
            self.lineage_id = _new_id("inglin")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash({
            "signal_id": self.signal_id,
            "source": self.source.value,
            "spine_signal_id": self.spine_signal_id,
            "spine_outcome_id": self.spine_outcome_id,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "lineage_id": self.lineage_id,
            "signal_id": self.signal_id,
            "session_id": self.session_id,
            "source": self.source.value,
            "spine_signal_id": self.spine_signal_id,
            "spine_outcome_id": self.spine_outcome_id,
            "cognition_session_id": self.cognition_session_id,
            "workflow_id": self.workflow_id,
            "continuity_record_id": self.continuity_record_id,
            "ingress_phase": self.ingress_phase.value,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }
