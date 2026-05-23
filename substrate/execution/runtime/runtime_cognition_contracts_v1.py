"""Runtime Cognition Contracts v1.

Data contracts for runtime continuity: events, traces, outcomes,
context updates, continuity state, session summaries, resume packets.

All contracts are immutable after creation. All carry provenance.
All serialize deterministically.

UMH substrate subsystem. Phase 96.8BN.
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


class EventSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class OutcomeResult(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    DEFERRED = "deferred"


class ContinuityPhase(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    IDLE = "idle"
    RESUMING = "resuming"
    TERMINATED = "terminated"


@dataclass
class RuntimeEvent:
    """A single runtime event consumed by the continuity engine."""

    event_id: str = field(default_factory=lambda: _new_id("rtevt"))
    event_type: str = ""
    source: str = ""
    severity: EventSeverity = EventSeverity.INFO
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    session_id: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "severity": self.severity.value,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
        }

    def content_hash(self) -> str:
        raw = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


@dataclass
class RuntimeTrace:
    """A processed execution trace with continuity metadata."""

    trace_id: str = field(default_factory=lambda: _new_id("rttrace"))
    source: str = ""
    mode: str = ""
    command: str = ""
    execution_path: str = ""
    provider: str = ""
    model: str = ""
    latency_ms: int | None = None
    result: str = ""
    session_id: str = ""
    correlation_id: str = ""
    raw_trace: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "source": self.source,
            "mode": self.mode,
            "command": self.command,
            "execution_path": self.execution_path,
            "provider": self.provider,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "result": self.result,
            "session_id": self.session_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
        }


@dataclass
class RuntimeOutcome:
    """The outcome of a runtime execution."""

    outcome_id: str = field(default_factory=lambda: _new_id("rtout"))
    trace_id: str = ""
    command: str = ""
    result: OutcomeResult = OutcomeResult.SUCCESS
    error_message: str = ""
    duration_ms: int | None = None
    artifacts_produced: list[str] = field(default_factory=list)
    governance_decision: str = ""
    session_id: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "trace_id": self.trace_id,
            "command": self.command,
            "result": self.result.value,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "artifacts_produced": self.artifacts_produced,
            "governance_decision": self.governance_decision,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
        }


@dataclass
class RuntimeContextUpdate:
    """A change to the operational context (goals, blockers, state)."""

    update_id: str = field(default_factory=lambda: _new_id("rtctx"))
    update_type: str = ""
    field_name: str = ""
    old_value: Any = None
    new_value: Any = None
    reason: str = ""
    source: str = ""
    session_id: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "update_id": self.update_id,
            "update_type": self.update_type,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "source": self.source,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
        }


@dataclass
class RuntimeContinuityState:
    """Snapshot of the current operational continuity state."""

    state_id: str = field(default_factory=lambda: _new_id("rtstate"))
    phase: ContinuityPhase = ContinuityPhase.ACTIVE
    current_session_id: str = ""
    active_goals: list[str] = field(default_factory=list)
    unresolved_blockers: list[str] = field(default_factory=list)
    recent_outcomes: list[str] = field(default_factory=list)
    pending_approvals: list[str] = field(default_factory=list)
    open_loop_count: int = 0
    total_events_ingested: int = 0
    total_traces_ingested: int = 0
    total_outcomes_recorded: int = 0
    memory_store_size: int = 0
    last_activity_at: str = ""
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "phase": self.phase.value,
            "current_session_id": self.current_session_id,
            "active_goals": self.active_goals,
            "unresolved_blockers": self.unresolved_blockers,
            "recent_outcomes": self.recent_outcomes,
            "pending_approvals": self.pending_approvals,
            "open_loop_count": self.open_loop_count,
            "total_events_ingested": self.total_events_ingested,
            "total_traces_ingested": self.total_traces_ingested,
            "total_outcomes_recorded": self.total_outcomes_recorded,
            "memory_store_size": self.memory_store_size,
            "last_activity_at": self.last_activity_at,
            "created_at": self.created_at,
        }

    def content_hash(self) -> str:
        raw = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


@dataclass
class RuntimeSessionSummary:
    """Summary of a completed or paused session."""

    summary_id: str = field(default_factory=lambda: _new_id("rtsum"))
    session_id: str = ""
    summary_type: str = ""
    phase_name: str = ""
    started_at: str = ""
    ended_at: str = ""
    total_events: int = 0
    total_traces: int = 0
    total_outcomes: int = 0
    successes: int = 0
    failures: int = 0
    open_loops_at_end: int = 0
    key_outcomes: list[str] = field(default_factory=list)
    unresolved_items: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "session_id": self.session_id,
            "summary_type": self.summary_type,
            "phase_name": self.phase_name,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "total_events": self.total_events,
            "total_traces": self.total_traces,
            "total_outcomes": self.total_outcomes,
            "successes": self.successes,
            "failures": self.failures,
            "open_loops_at_end": self.open_loops_at_end,
            "key_outcomes": self.key_outcomes,
            "unresolved_items": self.unresolved_items,
            "files_modified": self.files_modified,
            "created_at": self.created_at,
        }


@dataclass
class RuntimeResumePacket:
    """Everything needed to resume operational state after a session break."""

    packet_id: str = field(default_factory=lambda: _new_id("rtresume"))
    continuity_state: dict[str, Any] = field(default_factory=dict)
    active_goals: list[str] = field(default_factory=list)
    unresolved_blockers: list[str] = field(default_factory=list)
    recent_outcomes: list[dict[str, Any]] = field(default_factory=list)
    pending_approvals: list[str] = field(default_factory=list)
    relevant_memories: list[dict[str, Any]] = field(default_factory=list)
    recent_traces: list[dict[str, Any]] = field(default_factory=list)
    open_loops: list[dict[str, Any]] = field(default_factory=list)
    environment_state: dict[str, Any] = field(default_factory=dict)
    suggested_next_actions: list[str] = field(default_factory=list)
    session_summary: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "continuity_state": self.continuity_state,
            "active_goals": self.active_goals,
            "unresolved_blockers": self.unresolved_blockers,
            "recent_outcomes": self.recent_outcomes,
            "pending_approvals": self.pending_approvals,
            "relevant_memories": self.relevant_memories,
            "recent_traces": self.recent_traces,
            "open_loops": self.open_loops,
            "environment_state": self.environment_state,
            "suggested_next_actions": self.suggested_next_actions,
            "session_summary": self.session_summary,
            "created_at": self.created_at,
        }

    def content_hash(self) -> str:
        raw = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
