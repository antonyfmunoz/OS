"""Workstation Contracts v1 for operational embodiment.

Data shapes for workstation-level operational state:
  WorkstationState, WorkstationSession, WorkstationEnvironment,
  WorkstationExecutionRequest, WorkstationExecutionResult,
  WorkstationContinuityState, WorkstationResumeState,
  WorkstationOperationalSnapshot.

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


class WorkstationRole(str, Enum):
    VPS = "vps"
    LOCAL_WORKSTATION = "local_workstation"
    SANDBOX = "sandbox"


class ConnectivityStatus(str, Enum):
    CONNECTED = "connected"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"


class OperationalMode(str, Enum):
    DEVELOPER = "developer_mode"
    RESEARCH = "research_mode"
    AUDIT = "audit_mode"
    OVERNIGHT_SAFE = "overnight_safe_mode"


class ShellCommandVerdict(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"
    REQUIRES_REVIEW = "requires_review"


class WorkstationExecutionOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    DENIED = "denied"
    NOT_AVAILABLE = "not_available"


# ---------------------------------------------------------------------------
# Contract 1: WorkstationState
# ---------------------------------------------------------------------------


@dataclass
class WorkstationState:
    """Current operational state of a workstation."""

    state_id: str = ""
    role: WorkstationRole = WorkstationRole.VPS
    hostname: str = ""
    operational_mode: OperationalMode = OperationalMode.DEVELOPER
    active_tmux_sessions: list[str] = field(default_factory=list)
    active_services: list[str] = field(default_factory=list)
    current_repository: str = ""
    current_branch: str = ""
    working_directory: str = ""
    connectivity: ConnectivityStatus = ConnectivityStatus.CONNECTED
    relay_status: str = ""
    environment_health: str = "healthy"
    last_heartbeat: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.state_id:
            self.state_id = _new_id("wstate")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "role": self.role.value,
                "hostname": self.hostname,
                "operational_mode": self.operational_mode.value,
                "tmux_sessions": sorted(self.active_tmux_sessions),
                "services": sorted(self.active_services),
                "connectivity": self.connectivity.value,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "role": self.role.value,
            "hostname": self.hostname,
            "operational_mode": self.operational_mode.value,
            "active_tmux_sessions": self.active_tmux_sessions,
            "active_services": self.active_services,
            "current_repository": self.current_repository,
            "current_branch": self.current_branch,
            "working_directory": self.working_directory,
            "connectivity": self.connectivity.value,
            "relay_status": self.relay_status,
            "environment_health": self.environment_health,
            "last_heartbeat": self.last_heartbeat,
            "content_hash": self.content_hash(),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 2: WorkstationSession
# ---------------------------------------------------------------------------


@dataclass
class WorkstationSession:
    """A single tmux or shell session on the workstation."""

    session_id: str = ""
    session_name: str = ""
    session_type: str = "tmux"
    panes: list[dict[str, Any]] = field(default_factory=list)
    active_command: str = ""
    working_directory: str = ""
    started_at: str = ""
    is_active: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = _deterministic_id("wsess", f"{self.session_name}:{self.session_type}")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "session_type": self.session_type,
            "panes": self.panes,
            "active_command": self.active_command,
            "working_directory": self.working_directory,
            "started_at": self.started_at,
            "is_active": self.is_active,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 3: WorkstationEnvironment
# ---------------------------------------------------------------------------


@dataclass
class WorkstationEnvironment:
    """Description of the workstation execution environment."""

    environment_id: str = ""
    role: WorkstationRole = WorkstationRole.VPS
    hostname: str = ""
    platform: str = ""
    python_version: str = ""
    working_directory: str = ""
    available_tools: list[str] = field(default_factory=list)
    docker_containers: list[str] = field(default_factory=list)
    connectivity: ConnectivityStatus = ConnectivityStatus.CONNECTED
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.environment_id:
            self.environment_id = _deterministic_id("wenv", f"{self.role.value}:{self.hostname}")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "role": self.role.value,
            "hostname": self.hostname,
            "platform": self.platform,
            "python_version": self.python_version,
            "working_directory": self.working_directory,
            "available_tools": self.available_tools,
            "docker_containers": self.docker_containers,
            "connectivity": self.connectivity.value,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 4: WorkstationExecutionRequest
# ---------------------------------------------------------------------------


@dataclass
class WorkstationExecutionRequest:
    """A request to execute something on the workstation."""

    request_id: str = ""
    command: str = ""
    adapter_type: str = ""
    target_session: str = ""
    working_directory: str = ""
    operational_mode: OperationalMode = OperationalMode.DEVELOPER
    risk_class: str = "safe"
    governance_verdict: ShellCommandVerdict = ShellCommandVerdict.APPROVED
    governance_rules: list[str] = field(default_factory=list)
    correlation_id: str = ""
    session_id: str = ""
    timeout_seconds: int = 30
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.request_id:
            self.request_id = _new_id("wexreq")
        if not self.correlation_id:
            self.correlation_id = _new_id("wcorr")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "command": self.command,
                "adapter_type": self.adapter_type,
                "operational_mode": self.operational_mode.value,
                "risk_class": self.risk_class,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "command": self.command,
            "adapter_type": self.adapter_type,
            "target_session": self.target_session,
            "working_directory": self.working_directory,
            "operational_mode": self.operational_mode.value,
            "risk_class": self.risk_class,
            "governance_verdict": self.governance_verdict.value,
            "governance_rules": self.governance_rules,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "timeout_seconds": self.timeout_seconds,
            "content_hash": self.content_hash(),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 5: WorkstationExecutionResult
# ---------------------------------------------------------------------------


@dataclass
class WorkstationExecutionResult:
    """Result of a workstation execution."""

    result_id: str = ""
    request_id: str = ""
    command: str = ""
    outcome: WorkstationExecutionOutcome = WorkstationExecutionOutcome.SUCCESS
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    adapter_used: str = ""
    environment_id: str = ""
    duration_ms: float = 0.0
    governance_verdict: str = ""
    error_message: str = ""
    correlation_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.result_id:
            self.result_id = _new_id("wexres")
        if not self.timestamp:
            self.timestamp = _now_iso()

    @property
    def succeeded(self) -> bool:
        return self.outcome == WorkstationExecutionOutcome.SUCCESS

    def content_hash(self) -> str:
        return _content_hash(
            {
                "request_id": self.request_id,
                "command": self.command,
                "outcome": self.outcome.value,
                "exit_code": self.exit_code,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "request_id": self.request_id,
            "command": self.command,
            "outcome": self.outcome.value,
            "succeeded": self.succeeded,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "adapter_used": self.adapter_used,
            "environment_id": self.environment_id,
            "duration_ms": self.duration_ms,
            "governance_verdict": self.governance_verdict,
            "error_message": self.error_message,
            "correlation_id": self.correlation_id,
            "content_hash": self.content_hash(),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 6: WorkstationContinuityState
# ---------------------------------------------------------------------------


@dataclass
class WorkstationContinuityState:
    """Continuity state snapshot for the workstation."""

    state_id: str = ""
    workstation_state: WorkstationState | None = None
    active_sessions: list[WorkstationSession] = field(default_factory=list)
    recent_executions: list[str] = field(default_factory=list)
    open_loops: list[str] = field(default_factory=list)
    operational_mode: OperationalMode = OperationalMode.DEVELOPER
    total_executions: int = 0
    total_successes: int = 0
    total_denials: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.state_id:
            self.state_id = _new_id("wcont")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "operational_mode": self.operational_mode.value,
                "total_executions": self.total_executions,
                "sessions": len(self.active_sessions),
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "workstation_state": self.workstation_state.to_dict() if self.workstation_state else None,
            "active_sessions": [s.to_dict() for s in self.active_sessions],
            "recent_executions": self.recent_executions,
            "open_loops": self.open_loops,
            "operational_mode": self.operational_mode.value,
            "total_executions": self.total_executions,
            "total_successes": self.total_successes,
            "total_denials": self.total_denials,
            "content_hash": self.content_hash(),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 7: WorkstationResumeState
# ---------------------------------------------------------------------------


@dataclass
class WorkstationResumeState:
    """Resumable state for operator session continuation."""

    resume_id: str = ""
    session_id: str = ""
    continuity_state: WorkstationContinuityState | None = None
    active_goals: list[str] = field(default_factory=list)
    suggested_next_actions: list[str] = field(default_factory=list)
    environment_summary: dict[str, Any] = field(default_factory=dict)
    last_command: str = ""
    last_outcome: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.resume_id:
            self.resume_id = _new_id("wresume")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "resume_id": self.resume_id,
            "session_id": self.session_id,
            "continuity_state": self.continuity_state.to_dict() if self.continuity_state else None,
            "active_goals": self.active_goals,
            "suggested_next_actions": self.suggested_next_actions,
            "environment_summary": self.environment_summary,
            "last_command": self.last_command,
            "last_outcome": self.last_outcome,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 8: WorkstationOperationalSnapshot
# ---------------------------------------------------------------------------


@dataclass
class WorkstationOperationalSnapshot:
    """Complete snapshot of workstation operational state."""

    snapshot_id: str = ""
    workstation_state: WorkstationState | None = None
    environment: WorkstationEnvironment | None = None
    sessions: list[WorkstationSession] = field(default_factory=list)
    continuity: WorkstationContinuityState | None = None
    operational_mode: OperationalMode = OperationalMode.DEVELOPER
    phase: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            self.snapshot_id = _new_id("wsnap")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "snapshot_id": self.snapshot_id,
                "mode": self.operational_mode.value,
                "sessions": len(self.sessions),
                "phase": self.phase,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "workstation_state": self.workstation_state.to_dict() if self.workstation_state else None,
            "environment": self.environment.to_dict() if self.environment else None,
            "sessions": [s.to_dict() for s in self.sessions],
            "continuity": self.continuity.to_dict() if self.continuity else None,
            "operational_mode": self.operational_mode.value,
            "phase": self.phase,
            "content_hash": self.content_hash(),
            "timestamp": self.timestamp,
        }
