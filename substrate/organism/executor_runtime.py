"""Executor Runtime — canonical execution contract layer (Phase 14).

UMH now knows WHO (Profile), HOW AVAILABLE (Presence), WHERE (Session),
WHAT (Command), WHY (Goals + Gap + Projection), MEMORY (Continuity),
and DO (Execution Coordinator).

This phase adds the universal Executor Runtime — the contract that every
future executor must implement.  The coordinator (P13) dispatches plans;
the executor runtime validates, prepares, executes, monitors, and cleans up.

The SimulationExecutor is the reference implementation:  exercises the
full lifecycle without performing real work.  Every future executor
(workstation, agent, container, etc.) implements the same contract.

Composes:
  - P3  Empire WorkPacket Engine (WorkPacket as execution contract)
  - P6  Projection Engine (projection context)
  - P7  Continuity Runtime (continuity snapshot)
  - P8  Presence Runtime (operator availability)
  - P10 Workstation Runtime (workspace context)
  - P11 Profile Runtime (profile constraints)
  - P12 Session Runtime (session binding)
  - P13 Execution Coordinator (plan dispatch → executor request)

Governance: fail closed.  No execution without approval + valid context.
Deterministic-first.  No LLM calls in any code path.
Substrate layer.  Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────


def _repo_root() -> str:
    return os.environ.get("UMH_ROOT", "/opt/OS")


def _executor_data_dir() -> str:
    return os.path.join(_repo_root(), "data", "umh", "executor_runtime")


def _ensure_dirs() -> None:
    d = _executor_data_dir()
    for sub in ("requests", "results", "lifecycle", "snapshots"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Canonical Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExecutorLifecycleStatus(str, Enum):
    """Lifecycle stages of an executor request."""
    CREATED = "created"
    VALIDATED = "validated"
    PREPARED = "prepared"
    DISPATCHED = "dispatched"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CLEANED_UP = "cleaned_up"


class ExecutorType(str, Enum):
    """Canonical executor target types."""
    WORKSTATION = "workstation"
    AGENT = "agent"
    CONTAINER = "container"
    VPS = "vps"
    BROWSER = "browser"
    MOBILE = "mobile"
    EXTERNAL = "external"


class ExecutorRequestStatus(str, Enum):
    """Status of an executor request through the runtime."""
    PENDING = "pending"
    VALIDATING = "validating"
    PREPARING = "preparing"
    READY = "ready"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CLEANING_UP = "cleaning_up"
    CLEANED_UP = "cleaned_up"


class ExecutorEventType(str, Enum):
    """Event types in the executor lifecycle."""
    REQUEST_CREATED = "request_created"
    VALIDATION_STARTED = "validation_started"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    PREPARATION_STARTED = "preparation_started"
    PREPARATION_COMPLETED = "preparation_completed"
    PREPARATION_FAILED = "preparation_failed"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_PROGRESS = "execution_progress"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    MONITORING_HEARTBEAT = "monitoring_heartbeat"
    CANCELLATION_REQUESTED = "cancellation_requested"
    CANCELLED = "cancelled"
    CLEANUP_STARTED = "cleanup_started"
    CLEANUP_COMPLETED = "cleanup_completed"


class ExecutorApprovalState(str, Enum):
    """Approval state for executor requests."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    AUTO_APPROVED = "auto_approved"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class ExecutorRuntimeContext:
    """Assembled execution context from P3-P12 without duplication."""

    profile_snapshot: dict[str, Any] = field(default_factory=dict)
    presence_snapshot: dict[str, Any] = field(default_factory=dict)
    session_snapshot: dict[str, Any] = field(default_factory=dict)
    workstation_snapshot: dict[str, Any] = field(default_factory=dict)
    workpacket: dict[str, Any] = field(default_factory=dict)
    objectives: list[str] = field(default_factory=list)
    risk_class: str = "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_snapshot": self.profile_snapshot,
            "presence_snapshot": self.presence_snapshot,
            "session_snapshot": self.session_snapshot,
            "workstation_snapshot": self.workstation_snapshot,
            "workpacket": self.workpacket,
            "objectives": self.objectives,
            "risk_class": self.risk_class,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutorRuntimeContext:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class ExecutorRequest:
    """Canonical request from coordinator to executor."""

    request_id: str = field(
        default_factory=lambda: f"exrq-{uuid4().hex[:12]}"
    )
    execution_plan_id: str = ""
    executor_type: str = ExecutorType.WORKSTATION.value
    context: dict[str, Any] = field(default_factory=dict)
    approval_state: str = ExecutorApprovalState.PENDING.value
    risk_class: str = "low"
    created_at: float = field(default_factory=time.time)
    status: str = ExecutorRequestStatus.PENDING.value
    description: str = ""
    profile_id: str = ""
    session_id: str = ""
    priority: str = "normal"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "execution_plan_id": self.execution_plan_id,
            "executor_type": self.executor_type,
            "context": self.context,
            "approval_state": self.approval_state,
            "risk_class": self.risk_class,
            "created_at": self.created_at,
            "status": self.status,
            "description": self.description,
            "profile_id": self.profile_id,
            "session_id": self.session_id,
            "priority": self.priority,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutorRequest:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class ExecutorArtifact:
    """An artifact produced by execution."""

    artifact_id: str = field(
        default_factory=lambda: f"exart-{uuid4().hex[:12]}"
    )
    artifact_type: str = ""
    name: str = ""
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "name": self.name,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutorArtifact:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class ExecutorResult:
    """Canonical result from executor."""

    result_id: str = field(
        default_factory=lambda: f"exrs-{uuid4().hex[:12]}"
    )
    request_id: str = ""
    executor_type: str = ""
    success: bool = False
    outcome: str = ""
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: float = 0.0
    completed_at: float = 0.0
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "request_id": self.request_id,
            "executor_type": self.executor_type,
            "success": self.success,
            "outcome": self.outcome,
            "artifacts": self.artifacts,
            "errors": self.errors,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutorResult:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class ExecutorLifecycleEvent:
    """An event in the executor lifecycle."""

    event_id: str = field(
        default_factory=lambda: f"exlce-{uuid4().hex[:12]}"
    )
    request_id: str = ""
    event_type: str = ""
    timestamp: float = field(default_factory=time.time)
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "request_id": self.request_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutorLifecycleEvent:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class ExecutorRuntimeSnapshot:
    """Point-in-time snapshot of the executor runtime state."""

    snapshot_id: str = field(
        default_factory=lambda: f"exsnap-{uuid4().hex[:12]}"
    )
    timestamp: float = field(default_factory=time.time)
    total_requests: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    active_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    registered_executors: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "total_requests": self.total_requests,
            "by_status": self.by_status,
            "active_count": self.active_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "registered_executors": self.registered_executors,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Executor Contract (Abstract Base)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExecutorContract(ABC):
    """Universal executor contract.

    Every future executor (workstation, agent, container, etc.) must
    implement this interface.  The runtime calls these methods in order:
    validate → prepare → execute → monitor → cleanup.

    cancel() may be called at any point to abort.
    """

    @abstractmethod
    def validate(self, request: ExecutorRequest) -> tuple[bool, str]:
        """Validate the request can be executed.

        Returns (success, reason).  If success is False, reason explains why.
        """

    @abstractmethod
    def prepare(self, request: ExecutorRequest) -> tuple[bool, str]:
        """Prepare the execution environment.

        Returns (success, reason).
        """

    @abstractmethod
    def execute(self, request: ExecutorRequest) -> ExecutorResult:
        """Execute the request and return result."""

    @abstractmethod
    def monitor(self, request: ExecutorRequest) -> dict[str, Any]:
        """Return monitoring data for the active execution."""

    @abstractmethod
    def cancel(self, request: ExecutorRequest) -> bool:
        """Cancel an in-progress execution.  Returns True if cancelled."""

    @abstractmethod
    def cleanup(self, request: ExecutorRequest) -> bool:
        """Clean up execution resources.  Returns True if cleanup succeeded."""

    @property
    @abstractmethod
    def executor_type(self) -> str:
        """The type of executor this implements."""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Simulation Executor (Reference Implementation)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SimulationExecutor(ExecutorContract):
    """Exercises the full lifecycle without performing real work.

    Produces simulated artifacts and outcomes.  Used as acceptance-test
    executor and as a template for real implementations.
    """

    @property
    def executor_type(self) -> str:
        return ExecutorType.WORKSTATION.value

    def validate(self, request: ExecutorRequest) -> tuple[bool, str]:
        if not request.execution_plan_id:
            return False, "No execution_plan_id"
        if not request.executor_type:
            return False, "No executor_type"
        return True, "Simulation validation passed"

    def prepare(self, request: ExecutorRequest) -> tuple[bool, str]:
        return True, "Simulation environment prepared"

    def execute(self, request: ExecutorRequest) -> ExecutorResult:
        started = time.time()
        artifacts = [
            ExecutorArtifact(
                artifact_type="simulation_report",
                name="simulation_output.json",
                content=json.dumps({
                    "request_id": request.request_id,
                    "simulated": True,
                    "executor_type": request.executor_type,
                    "description": request.description,
                }),
            ).to_dict(),
        ]
        completed = time.time()
        return ExecutorResult(
            request_id=request.request_id,
            executor_type=request.executor_type,
            success=True,
            outcome="Simulation completed successfully",
            artifacts=artifacts,
            started_at=started,
            completed_at=completed,
            duration_seconds=completed - started,
        )

    def monitor(self, request: ExecutorRequest) -> dict[str, Any]:
        return {
            "request_id": request.request_id,
            "status": "simulated_monitoring",
            "progress_pct": 100,
        }

    def cancel(self, request: ExecutorRequest) -> bool:
        return True

    def cleanup(self, request: ExecutorRequest) -> bool:
        return True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Executor Implementation Registry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExecutorImplementationRegistry:
    """Maps executor types to concrete ExecutorContract implementations.

    The simulation executor is pre-registered.  Future phases register
    real executors (workstation, agent, container, etc.) at startup.
    """

    def __init__(self) -> None:
        self._implementations: dict[str, ExecutorContract] = {}
        self._register_simulation()

    def _register_simulation(self) -> None:
        sim = SimulationExecutor()
        for etype in ExecutorType:
            self._implementations[etype.value] = sim

    def register(self, executor_type: str, impl: ExecutorContract) -> None:
        self._implementations[executor_type] = impl
        logger.info("Registered executor implementation: %s", executor_type)

    def unregister(self, executor_type: str) -> bool:
        if executor_type in self._implementations:
            del self._implementations[executor_type]
            return True
        return False

    def get(self, executor_type: str) -> ExecutorContract | None:
        return self._implementations.get(executor_type)

    def available_types(self) -> list[str]:
        return list(self._implementations.keys())

    def has(self, executor_type: str) -> bool:
        return executor_type in self._implementations


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Request Store
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExecutorRequestStore:
    """Persistent store for executor requests."""

    def __init__(self, store_dir: str | None = None) -> None:
        self._store_dir = store_dir or os.path.join(
            _executor_data_dir(), "requests"
        )
        os.makedirs(self._store_dir, exist_ok=True)

    def _path(self, request_id: str) -> str:
        return os.path.join(self._store_dir, f"{request_id}.json")

    def save(self, request: ExecutorRequest) -> None:
        with open(self._path(request.request_id), "w") as f:
            json.dump(request.to_dict(), f, indent=2)

    def get(self, request_id: str) -> ExecutorRequest | None:
        p = self._path(request_id)
        if not os.path.exists(p):
            return None
        try:
            with open(p) as f:
                return ExecutorRequest.from_dict(json.load(f))
        except (json.JSONDecodeError, OSError):
            return None

    def all_requests(self) -> list[ExecutorRequest]:
        results: list[ExecutorRequest] = []
        if not os.path.isdir(self._store_dir):
            return results
        for fname in os.listdir(self._store_dir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(self._store_dir, fname)) as f:
                    results.append(ExecutorRequest.from_dict(json.load(f)))
            except (json.JSONDecodeError, OSError):
                continue
        return results

    def by_status(self, status: str) -> list[ExecutorRequest]:
        return [r for r in self.all_requests() if r.status == status]

    def by_executor_type(self, executor_type: str) -> list[ExecutorRequest]:
        return [r for r in self.all_requests() if r.executor_type == executor_type]

    def by_plan(self, plan_id: str) -> list[ExecutorRequest]:
        return [r for r in self.all_requests() if r.execution_plan_id == plan_id]

    def active(self) -> list[ExecutorRequest]:
        active_statuses = {
            ExecutorRequestStatus.VALIDATING.value,
            ExecutorRequestStatus.PREPARING.value,
            ExecutorRequestStatus.READY.value,
            ExecutorRequestStatus.EXECUTING.value,
            ExecutorRequestStatus.MONITORING.value,
            ExecutorRequestStatus.COMPLETING.value,
        }
        return [r for r in self.all_requests() if r.status in active_statuses]

    def completed(self) -> list[ExecutorRequest]:
        return self.by_status(ExecutorRequestStatus.COMPLETED.value)

    def failed(self) -> list[ExecutorRequest]:
        return self.by_status(ExecutorRequestStatus.FAILED.value)

    def history(self, limit: int = 50) -> list[ExecutorRequest]:
        terminal = {
            ExecutorRequestStatus.COMPLETED.value,
            ExecutorRequestStatus.FAILED.value,
            ExecutorRequestStatus.CANCELLED.value,
            ExecutorRequestStatus.CLEANED_UP.value,
        }
        items = [r for r in self.all_requests() if r.status in terminal]
        items.sort(key=lambda r: r.created_at, reverse=True)
        return items[:limit]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Result Store
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExecutorResultStore:
    """Persistent store for executor results."""

    def __init__(self, store_dir: str | None = None) -> None:
        self._store_dir = store_dir or os.path.join(
            _executor_data_dir(), "results"
        )
        os.makedirs(self._store_dir, exist_ok=True)

    def _path(self, result_id: str) -> str:
        return os.path.join(self._store_dir, f"{result_id}.json")

    def save(self, result: ExecutorResult) -> None:
        with open(self._path(result.result_id), "w") as f:
            json.dump(result.to_dict(), f, indent=2)

    def get(self, result_id: str) -> ExecutorResult | None:
        p = self._path(result_id)
        if not os.path.exists(p):
            return None
        try:
            with open(p) as f:
                return ExecutorResult.from_dict(json.load(f))
        except (json.JSONDecodeError, OSError):
            return None

    def by_request(self, request_id: str) -> ExecutorResult | None:
        for fname in os.listdir(self._store_dir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(self._store_dir, fname)) as f:
                    data = json.load(f)
                    if data.get("request_id") == request_id:
                        return ExecutorResult.from_dict(data)
            except (json.JSONDecodeError, OSError):
                continue
        return None

    def all_results(self) -> list[ExecutorResult]:
        results: list[ExecutorResult] = []
        if not os.path.isdir(self._store_dir):
            return results
        for fname in os.listdir(self._store_dir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(self._store_dir, fname)) as f:
                    results.append(ExecutorResult.from_dict(json.load(f)))
            except (json.JSONDecodeError, OSError):
                continue
        return results

    def successes(self) -> list[ExecutorResult]:
        return [r for r in self.all_results() if r.success]

    def failures(self) -> list[ExecutorResult]:
        return [r for r in self.all_results() if not r.success]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Lifecycle Tracker
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExecutorLifecycleTracker:
    """Append-only lifecycle event recording for executor requests."""

    def __init__(self, log_path: str | None = None) -> None:
        self._log_path = log_path or os.path.join(
            _executor_data_dir(), "lifecycle", "events.jsonl"
        )
        os.makedirs(os.path.dirname(self._log_path), exist_ok=True)

    def record(
        self,
        request_id: str,
        event_type: str,
        summary: str = "",
        details: dict[str, Any] | None = None,
    ) -> ExecutorLifecycleEvent:
        event = ExecutorLifecycleEvent(
            request_id=request_id,
            event_type=event_type,
            summary=summary,
            details=details or {},
        )
        try:
            with open(self._log_path, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except OSError:
            logger.debug("Failed to persist lifecycle event %s", event.event_id)
        return event

    def events_for_request(self, request_id: str) -> list[ExecutorLifecycleEvent]:
        return [e for e in self._load_all() if e.request_id == request_id]

    def recent(self, limit: int = 50) -> list[ExecutorLifecycleEvent]:
        events = self._load_all()
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def by_type(self, event_type: str) -> list[ExecutorLifecycleEvent]:
        return [e for e in self._load_all() if e.event_type == event_type]

    def _load_all(self) -> list[ExecutorLifecycleEvent]:
        events: list[ExecutorLifecycleEvent] = []
        if not os.path.exists(self._log_path):
            return events
        try:
            with open(self._log_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(
                            ExecutorLifecycleEvent.from_dict(json.loads(line))
                        )
                    except (json.JSONDecodeError, KeyError):
                        continue
        except OSError:
            pass
        return events


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Governance Enforcement
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExecutorGovernanceGate:
    """Validates execution prerequisites.  Fail-closed — no bypass paths."""

    _RISK_ORDER = {
        "negligible": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }

    _AUTO_APPROVE_THRESHOLD = 1  # low and below auto-approve

    @staticmethod
    def can_execute(request: ExecutorRequest) -> tuple[bool, str]:
        """Check all governance prerequisites before execution."""
        if request.approval_state not in (
            ExecutorApprovalState.APPROVED.value,
            ExecutorApprovalState.AUTO_APPROVED.value,
        ):
            return False, f"Not approved: {request.approval_state}"

        risk_level = ExecutorGovernanceGate._RISK_ORDER.get(
            request.risk_class, 99
        )
        if risk_level >= 3 and request.approval_state != ExecutorApprovalState.APPROVED.value:
            return False, f"High-risk ({request.risk_class}) requires explicit approval"

        if not request.execution_plan_id:
            return False, "No execution_plan_id — cannot execute without coordinator plan"

        return True, "All governance checks passed"

    @staticmethod
    def auto_approve_eligible(request: ExecutorRequest) -> bool:
        """Check if request qualifies for auto-approval."""
        risk_level = ExecutorGovernanceGate._RISK_ORDER.get(
            request.risk_class, 99
        )
        return risk_level <= ExecutorGovernanceGate._AUTO_APPROVE_THRESHOLD

    @staticmethod
    def requires_approval(risk_class: str) -> bool:
        """Check if a risk class requires explicit operator approval."""
        risk_level = ExecutorGovernanceGate._RISK_ORDER.get(risk_class, 99)
        return risk_level > ExecutorGovernanceGate._AUTO_APPROVE_THRESHOLD

    @staticmethod
    def validate_authority(
        request: ExecutorRequest,
        operator_authority: str = "primary",
    ) -> tuple[bool, str]:
        """Validate operator has authority for this request."""
        risk_level = ExecutorGovernanceGate._RISK_ORDER.get(
            request.risk_class, 99
        )
        if risk_level >= 4 and operator_authority != "primary":
            return False, "Critical-risk requires primary operator authority"
        return True, "Authority validated"

    @staticmethod
    def validate_profile_restrictions(
        request: ExecutorRequest,
        profile_restrictions: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        """Validate request against profile restrictions."""
        if not profile_restrictions:
            return True, "No profile restrictions"
        blocked_types = profile_restrictions.get("blocked_executor_types", [])
        if request.executor_type in blocked_types:
            return False, f"Executor type {request.executor_type} blocked by profile"
        return True, "Profile restrictions passed"

    @staticmethod
    def validate_session_restrictions(
        request: ExecutorRequest,
        session_restrictions: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        """Validate request against session restrictions."""
        if not session_restrictions:
            return True, "No session restrictions"
        max_concurrent = session_restrictions.get("max_concurrent_executions", 10)
        current_count = session_restrictions.get("current_execution_count", 0)
        if current_count >= max_concurrent:
            return False, f"Session at max concurrent executions ({max_concurrent})"
        return True, "Session restrictions passed"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cross-Runtime Context Assembler
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExecutorContextAssembler:
    """Assembles execution context from P3-P12 by composition."""

    @staticmethod
    def assemble(
        workpacket: dict[str, Any] | None = None,
        risk_class: str = "low",
    ) -> ExecutorRuntimeContext:
        ctx = ExecutorRuntimeContext(
            workpacket=workpacket or {},
            risk_class=risk_class,
        )
        ctx.profile_snapshot = ExecutorContextAssembler._gather_profile()
        ctx.presence_snapshot = ExecutorContextAssembler._gather_presence()
        ctx.session_snapshot = ExecutorContextAssembler._gather_session()
        ctx.workstation_snapshot = ExecutorContextAssembler._gather_workstation()
        ctx.objectives = ExecutorContextAssembler._gather_objectives()
        return ctx

    @staticmethod
    def _gather_profile() -> dict[str, Any]:
        try:
            from substrate.organism.profile_runtime import get_profile_runtime
            pr = get_profile_runtime()
            return pr.snapshot().to_dict()
        except Exception:
            return {"error": "profile_runtime unavailable"}

    @staticmethod
    def _gather_presence() -> dict[str, Any]:
        try:
            from substrate.organism.presence_runtime import PresenceRuntime
            pr = PresenceRuntime()
            return pr.snapshot()
        except Exception:
            return {"error": "presence_runtime unavailable"}

    @staticmethod
    def _gather_session() -> dict[str, Any]:
        try:
            from substrate.organism.session_runtime import get_session_runtime
            sr = get_session_runtime()
            return sr.snapshot().to_dict()
        except Exception:
            return {"error": "session_runtime unavailable"}

    @staticmethod
    def _gather_workstation() -> dict[str, Any]:
        try:
            from substrate.organism.workstation_runtime import get_workstation_runtime
            wr = get_workstation_runtime()
            return wr.snapshot().to_dict()
        except Exception:
            return {"error": "workstation_runtime unavailable"}

    @staticmethod
    def _gather_objectives() -> list[str]:
        try:
            from substrate.organism.strategic_gap_engine import get_strategic_gap_engine
            sg = get_strategic_gap_engine()
            goals = sg.active_goals()
            return [g.name for g in goals[:10]]
        except Exception:
            return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Executor Runtime (top-level orchestrator)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExecutorRuntime:
    """Top-level executor runtime.

    Receives dispatched plans from the Execution Coordinator (P13),
    creates executor requests, runs them through the canonical lifecycle
    (validate → prepare → execute → monitor → cleanup), records results,
    and feeds status back to the coordinator.

    Never makes decisions about WHAT to execute — only HOW.
    """

    def __init__(
        self,
        data_dir: str | None = None,
        telemetry_emitter: Any | None = None,
    ) -> None:
        dd = data_dir or _executor_data_dir()
        _ensure_dirs()

        self._request_store = ExecutorRequestStore(os.path.join(dd, "requests"))
        self._result_store = ExecutorResultStore(os.path.join(dd, "results"))
        self._lifecycle = ExecutorLifecycleTracker(
            os.path.join(dd, "lifecycle", "events.jsonl")
        )
        self._impl_registry = ExecutorImplementationRegistry()
        self._gate = ExecutorGovernanceGate()
        self._assembler = ExecutorContextAssembler()
        self._telemetry = telemetry_emitter

    # ── Request Creation ────────────────────────────────

    def create_request(
        self,
        execution_plan_id: str,
        executor_type: str,
        *,
        risk_class: str = "low",
        description: str = "",
        profile_id: str = "",
        session_id: str = "",
        priority: str = "normal",
        workpacket: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutorRequest:
        """Create a new executor request from a coordinator plan."""
        ctx = self._assembler.assemble(
            workpacket=workpacket,
            risk_class=risk_class,
        )

        approval = ExecutorApprovalState.PENDING.value
        if self._gate.auto_approve_eligible(
            ExecutorRequest(risk_class=risk_class)
        ):
            approval = ExecutorApprovalState.AUTO_APPROVED.value

        request = ExecutorRequest(
            execution_plan_id=execution_plan_id,
            executor_type=executor_type,
            context=ctx.to_dict(),
            approval_state=approval,
            risk_class=risk_class,
            description=description,
            profile_id=profile_id,
            session_id=session_id,
            priority=priority,
            metadata=metadata or {},
        )
        self._request_store.save(request)
        self._lifecycle.record(
            request.request_id,
            ExecutorEventType.REQUEST_CREATED.value,
            summary=f"Request for plan {execution_plan_id[:12]} → {executor_type}",
            details={
                "executor_type": executor_type,
                "risk_class": risk_class,
                "auto_approved": approval == ExecutorApprovalState.AUTO_APPROVED.value,
            },
        )
        logger.info(
            "Created request %s for plan %s → %s",
            request.request_id, execution_plan_id[:12], executor_type,
        )
        return request

    # ── Approval ────────────────────────────────────────

    def approve_request(
        self,
        request_id: str,
        approved_by: str = "operator",
    ) -> ExecutorRequest | None:
        request = self._request_store.get(request_id)
        if not request:
            return None
        if request.approval_state not in (
            ExecutorApprovalState.PENDING.value,
        ):
            return request

        request.approval_state = ExecutorApprovalState.APPROVED.value
        self._request_store.save(request)
        self._lifecycle.record(
            request_id,
            ExecutorEventType.VALIDATION_PASSED.value,
            summary=f"Approved by {approved_by}",
        )
        return request

    def deny_request(
        self,
        request_id: str,
        reason: str = "",
    ) -> ExecutorRequest | None:
        request = self._request_store.get(request_id)
        if not request:
            return None
        request.approval_state = ExecutorApprovalState.DENIED.value
        request.status = ExecutorRequestStatus.CANCELLED.value
        self._request_store.save(request)
        self._lifecycle.record(
            request_id,
            ExecutorEventType.CANCELLED.value,
            summary=f"Denied: {reason}",
        )
        return request

    # ── Telemetry ─────────────────────────────────────────

    def _tel(
        self,
        event_type: str,
        request: ExecutorRequest,
        **payload: Any,
    ) -> None:
        """Emit telemetry event. Never raises."""
        if not self._telemetry:
            return
        try:
            self._telemetry.emit(
                event_type,
                execution_id=request.request_id,
                request_id=request.request_id,
                executor_type=request.executor_type,
                operation=request.metadata.get("operation", ""),
                status=request.status,
                payload=payload if payload else {},
            )
        except Exception:
            logger.debug("Telemetry emit failed", exc_info=True)

    @property
    def telemetry(self) -> Any:
        """Access the telemetry emitter (may be None)."""
        return self._telemetry

    @telemetry.setter
    def telemetry(self, emitter: Any) -> None:
        self._telemetry = emitter

    # ── Full Lifecycle Execution ────────────────────────

    def run_lifecycle(
        self,
        request_id: str,
    ) -> ExecutorResult | None:
        """Run the full executor lifecycle for a request.

        validate → prepare → execute → cleanup.
        Each step is recorded.  Governance gate checked before execute.
        Telemetry emitted at each boundary if emitter is configured.
        """
        request = self._request_store.get(request_id)
        if not request:
            logger.warning("Request %s not found", request_id)
            return None

        impl = self._impl_registry.get(request.executor_type)
        if not impl:
            self._fail_request(request, f"No executor for type: {request.executor_type}")
            return None

        self._tel("execution_requested", request, message="Lifecycle started")

        # Gate check
        can_exec, gate_reason = self._gate.can_execute(request)
        if not can_exec:
            self._tel("execution_failed", request, error=gate_reason)
            self._fail_request(request, f"Governance gate: {gate_reason}")
            return None

        self._tel("execution_approved", request, message="Governance passed")

        # Validate
        request.status = ExecutorRequestStatus.VALIDATING.value
        self._request_store.save(request)
        self._lifecycle.record(
            request_id, ExecutorEventType.VALIDATION_STARTED.value,
            summary="Validation started",
        )
        self._tel("execution_validating", request, message="Validation started")

        valid, reason = impl.validate(request)
        if not valid:
            self._lifecycle.record(
                request_id, ExecutorEventType.VALIDATION_FAILED.value,
                summary=f"Validation failed: {reason}",
            )
            self._tel("execution_failed", request, error=f"Validation: {reason}")
            self._fail_request(request, f"Validation failed: {reason}")
            return None

        self._lifecycle.record(
            request_id, ExecutorEventType.VALIDATION_PASSED.value,
            summary="Validation passed",
        )

        # Prepare
        request.status = ExecutorRequestStatus.PREPARING.value
        self._request_store.save(request)
        self._lifecycle.record(
            request_id, ExecutorEventType.PREPARATION_STARTED.value,
            summary="Preparation started",
        )
        self._tel("execution_preparing", request, message="Preparation started")

        prepared, prep_reason = impl.prepare(request)
        if not prepared:
            self._lifecycle.record(
                request_id, ExecutorEventType.PREPARATION_FAILED.value,
                summary=f"Preparation failed: {prep_reason}",
            )
            self._tel("execution_failed", request, error=f"Preparation: {prep_reason}")
            self._fail_request(request, f"Preparation failed: {prep_reason}")
            return None

        self._lifecycle.record(
            request_id, ExecutorEventType.PREPARATION_COMPLETED.value,
            summary="Preparation completed",
        )
        request.status = ExecutorRequestStatus.READY.value
        self._request_store.save(request)

        # Execute
        request.status = ExecutorRequestStatus.EXECUTING.value
        self._request_store.save(request)
        self._lifecycle.record(
            request_id, ExecutorEventType.EXECUTION_STARTED.value,
            summary="Execution started",
        )
        self._tel("execution_started", request, message="Execution started")

        try:
            result = impl.execute(request)
        except Exception as exc:
            self._lifecycle.record(
                request_id, ExecutorEventType.EXECUTION_FAILED.value,
                summary=f"Execution error: {exc}",
            )
            self._tel("execution_failed", request, error=str(exc))
            self._fail_request(request, f"Execution error: {exc}")
            return None

        if result.success:
            request.status = ExecutorRequestStatus.COMPLETED.value
            self._lifecycle.record(
                request_id, ExecutorEventType.EXECUTION_COMPLETED.value,
                summary=result.outcome,
                details={"artifacts_count": len(result.artifacts)},
            )
            proof = result.metadata.get("proof", {})
            if proof:
                self._tel(
                    "proof_generated", request,
                    proof_id=proof.get("proof_id", ""),
                    duration_ms=proof.get("duration_ms", 0),
                )
            self._tel(
                "execution_completed", request,
                message=result.outcome,
                duration_ms=result.duration_seconds * 1000,
                artifact_count=len(result.artifacts),
            )
        else:
            request.status = ExecutorRequestStatus.FAILED.value
            self._lifecycle.record(
                request_id, ExecutorEventType.EXECUTION_FAILED.value,
                summary=f"Failed: {'; '.join(result.errors)}",
            )
            self._tel("execution_failed", request, error="; ".join(result.errors))

        self._request_store.save(request)
        self._result_store.save(result)

        # Cleanup
        self._lifecycle.record(
            request_id, ExecutorEventType.CLEANUP_STARTED.value,
            summary="Cleanup started",
        )
        self._tel("execution_cleaning_up", request, message="Cleanup started")
        try:
            impl.cleanup(request)
        except Exception as exc:
            logger.debug("Cleanup error for %s: %s", request_id, exc)

        request.status = (
            ExecutorRequestStatus.CLEANED_UP.value
            if result.success
            else ExecutorRequestStatus.FAILED.value
        )
        self._request_store.save(request)
        self._lifecycle.record(
            request_id, ExecutorEventType.CLEANUP_COMPLETED.value,
            summary="Cleanup completed",
        )

        # Feed status back to coordinator
        self._notify_coordinator(request, result)

        return result

    def _fail_request(self, request: ExecutorRequest, reason: str) -> None:
        request.status = ExecutorRequestStatus.FAILED.value
        request.metadata["failure_reason"] = reason
        self._request_store.save(request)
        logger.warning("Request %s failed: %s", request.request_id, reason)

    def _notify_coordinator(
        self,
        request: ExecutorRequest,
        result: ExecutorResult,
    ) -> None:
        """Feed execution outcome back to the coordinator (P13)."""
        try:
            from substrate.organism.execution_coordinator import (
                get_execution_coordinator,
            )
            coord = get_execution_coordinator()
            if result.success:
                coord.mark_completed(
                    request.execution_plan_id,
                    proof_id=result.result_id,
                )
            else:
                coord.mark_failed(
                    request.execution_plan_id,
                    reason=request.metadata.get("failure_reason", "Unknown"),
                )
        except Exception:
            logger.debug("Could not notify coordinator for %s", request.request_id)

    # ── Approval Intercepts ─────────────────────────────

    def request_approval(
        self,
        request: ExecutorRequest,
        *,
        reason: str = "",
        details: dict[str, Any] | None = None,
        timeout_seconds: float = 900.0,
    ) -> tuple[bool, str]:
        """Request runtime approval intercept. Blocks until decided.

        Returns (approved: bool, message: str).
        If no intercept service is available, auto-approves (fail-open
        for backwards compatibility with executors that don't use intercepts).
        """
        try:
            from substrate.organism.executors.approval_intercept import (
                get_approval_intercept_service,
            )
            svc = get_approval_intercept_service()
        except Exception:
            return True, "No intercept service — auto-approved"

        intercept = svc.request_approval(
            execution_id=request.request_id,
            request_id=request.request_id,
            executor_type=request.executor_type,
            operation=request.metadata.get("operation", ""),
            risk_class=request.risk_class,
            reason=reason,
            details=details,
            timeout_seconds=timeout_seconds,
        )

        request.status = "pending_approval"
        self._request_store.save(request)
        self._tel("approval_requested", request, approval_id=intercept.approval_id, reason=reason)

        result = svc.await_decision(intercept.approval_id, timeout=timeout_seconds)
        if not result:
            request.status = ExecutorRequestStatus.FAILED.value
            self._request_store.save(request)
            return False, "Approval intercept lost"

        if result.status == "approved":
            request.status = ExecutorRequestStatus.EXECUTING.value
            self._request_store.save(request)
            self._tel("approval_granted", request, approval_id=intercept.approval_id)
            return True, f"Approved by {result.decided_by}"

        if result.status == "rejected":
            request.status = ExecutorRequestStatus.FAILED.value
            request.metadata["failure_reason"] = (
                f"Rejected by {result.decided_by}: {result.rejection_reason}"
            )
            self._request_store.save(request)
            self._tel(
                "approval_rejected", request,
                approval_id=intercept.approval_id,
                reason=result.rejection_reason,
            )
            return False, f"Rejected by {result.decided_by}: {result.rejection_reason}"

        # expired
        request.status = ExecutorRequestStatus.FAILED.value
        request.metadata["failure_reason"] = "Approval timed out"
        self._request_store.save(request)
        self._tel("approval_expired", request, approval_id=intercept.approval_id)
        return False, "Approval timed out"

    # ── Cancel ──────────────────────────────────────────

    def cancel_request(self, request_id: str) -> ExecutorRequest | None:
        request = self._request_store.get(request_id)
        if not request:
            return None
        if request.status in (
            ExecutorRequestStatus.COMPLETED.value,
            ExecutorRequestStatus.CLEANED_UP.value,
        ):
            return None

        impl = self._impl_registry.get(request.executor_type)
        if impl:
            try:
                impl.cancel(request)
            except Exception:
                pass

        request.status = ExecutorRequestStatus.CANCELLED.value
        self._request_store.save(request)
        self._lifecycle.record(
            request_id, ExecutorEventType.CANCELLED.value,
            summary="Request cancelled",
        )
        self._tel("execution_cancelled", request, message="Cancelled by operator")
        return request

    # ── Monitor ─────────────────────────────────────────

    def monitor_request(self, request_id: str) -> dict[str, Any]:
        request = self._request_store.get(request_id)
        if not request:
            return {"error": "Request not found"}

        impl = self._impl_registry.get(request.executor_type)
        if not impl:
            return {"error": "No executor implementation"}

        try:
            mon = impl.monitor(request)
            self._lifecycle.record(
                request_id,
                ExecutorEventType.MONITORING_HEARTBEAT.value,
                summary="Monitoring heartbeat",
                details=mon,
            )
            return mon
        except Exception as exc:
            return {"error": str(exc)}

    # ── Queries ─────────────────────────────────────────

    def get_request(self, request_id: str) -> ExecutorRequest | None:
        return self._request_store.get(request_id)

    def get_result(self, result_id: str) -> ExecutorResult | None:
        return self._result_store.get(result_id)

    def result_for_request(self, request_id: str) -> ExecutorResult | None:
        return self._result_store.by_request(request_id)

    def requests_by_status(self, status: str) -> list[ExecutorRequest]:
        return self._request_store.by_status(status)

    def requests_by_type(self, executor_type: str) -> list[ExecutorRequest]:
        return self._request_store.by_executor_type(executor_type)

    def active_requests(self) -> list[ExecutorRequest]:
        return self._request_store.active()

    def completed_requests(self) -> list[ExecutorRequest]:
        return self._request_store.completed()

    def failed_requests(self) -> list[ExecutorRequest]:
        return self._request_store.failed()

    def request_history(self, limit: int = 50) -> list[ExecutorRequest]:
        return self._request_store.history(limit)

    def all_results(self) -> list[ExecutorResult]:
        return self._result_store.all_results()

    def lifecycle_for_request(self, request_id: str) -> list[ExecutorLifecycleEvent]:
        return self._lifecycle.events_for_request(request_id)

    def recent_lifecycle(self, limit: int = 50) -> list[ExecutorLifecycleEvent]:
        return self._lifecycle.recent(limit)

    # ── Executor Management ─────────────────────────────

    def register_executor(self, executor_type: str, impl: ExecutorContract) -> None:
        self._impl_registry.register(executor_type, impl)

    def unregister_executor(self, executor_type: str) -> bool:
        return self._impl_registry.unregister(executor_type)

    def registered_executor_types(self) -> list[str]:
        return self._impl_registry.available_types()

    def has_executor(self, executor_type: str) -> bool:
        return self._impl_registry.has(executor_type)

    # ── Context Assembly ────────────────────────────────

    def assemble_context(
        self,
        workpacket: dict[str, Any] | None = None,
        risk_class: str = "low",
    ) -> ExecutorRuntimeContext:
        return self._assembler.assemble(workpacket=workpacket, risk_class=risk_class)

    # ── Snapshot ─────────────────────────────────────────

    def snapshot(self) -> ExecutorRuntimeSnapshot:
        all_reqs = self._request_store.all_requests()
        by_status: dict[str, int] = {}
        for r in all_reqs:
            by_status[r.status] = by_status.get(r.status, 0) + 1

        return ExecutorRuntimeSnapshot(
            total_requests=len(all_reqs),
            by_status=by_status,
            active_count=len(self._request_store.active()),
            completed_count=len(self._request_store.completed()),
            failed_count=len(self._request_store.failed()),
            registered_executors=len(self._impl_registry.available_types()),
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Singleton
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_singleton: ExecutorRuntime | None = None


def get_executor_runtime() -> ExecutorRuntime:
    global _singleton
    if _singleton is None:
        try:
            from substrate.organism.executors.execution_telemetry import (
                get_telemetry_emitter,
            )
            emitter = get_telemetry_emitter()
        except Exception:
            emitter = None
        _singleton = ExecutorRuntime(telemetry_emitter=emitter)
    return _singleton


def reset_executor_runtime() -> None:
    global _singleton
    _singleton = None
