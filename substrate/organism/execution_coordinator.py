"""Execution Coordinator Runtime — canonical orchestration layer (Phase 13).

UMH now knows WHO (Profile), HOW AVAILABLE (Presence), WHERE (Session),
WHAT (Command), WHY (Goals + Gap + Projection), and MEMORY (Continuity).

This phase adds DO — the coordination layer that receives approved
WorkPackets, creates execution plans, assigns targets, manages approval
gates, queues work, and tracks the full execution lifecycle.

The Execution Coordinator NEVER executes.  It only coordinates.
Actual execution is deferred to executor runtimes (Phase 14+).

Composes:
  - P3  Empire WorkPacket Engine (WorkPacket as execution contract)
  - P4  Strategic Gap Engine (gap → WorkPacket source)
  - P5  Tick Loop (candidate scheduling)
  - P6  Projection Engine (projection context for plans)
  - P7  Continuity Runtime (continuity snapshot)
  - P8  Presence Runtime (operator availability check)
  - P9  Command Runtime (command → execution routing)
  - P10 Workstation Runtime (workspace preparation)
  - P11 Profile Runtime (profile constraints)
  - P12 Session Runtime (session binding)

Governance: fail closed.  No plan dispatches without approval.

Deterministic-first.  No LLM calls in any code path.
Substrate layer.  Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────


def _repo_root() -> str:
    return os.environ.get("UMH_ROOT", "/opt/OS")


def _coord_data_dir() -> str:
    from substrate.state.runtime_paths import runtime_state_dir

    return str(runtime_state_dir("execution_coordinator", create=False))


def _ensure_dirs() -> None:
    d = _coord_data_dir()
    for sub in ("plans", "queue", "lifecycle", "snapshots"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Canonical Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExecutionPlanStatus(str, Enum):
    """Lifecycle of a coordinator-level execution plan."""

    DRAFTED = "drafted"
    APPROVED = "approved"
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionTargetType(str, Enum):
    """Canonical executor targets."""

    WORKSTATION = "workstation"
    AGENT = "agent"
    VPS = "vps"
    CONTAINER = "container"
    BROWSER = "browser"
    MOBILE = "mobile"
    EXTERNAL = "external"


class ExecutionTiming(str, Enum):
    """How the execution should proceed (timing/scheduling)."""

    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    BACKGROUND = "background"
    SCHEDULED = "scheduled"


class ExecutionPriority(str, Enum):
    """Priority within the execution queue."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class CoordinatorApprovalState(str, Enum):
    """Approval state of an execution plan."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class LifecycleEventType(str, Enum):
    """Execution lifecycle event types."""

    PLAN_CREATED = "plan_created"
    PLAN_APPROVED = "plan_approved"
    PLAN_DENIED = "plan_denied"
    PLAN_QUEUED = "plan_queued"
    PLAN_DISPATCHED = "plan_dispatched"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    PLAN_CANCELLED = "plan_cancelled"
    PLAN_REPRIORITIZED = "plan_reprioritized"
    PLAN_EXPIRED = "plan_expired"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class CoordinatorExecutionPlan:
    """A coordinator-level execution plan binding WorkPacket to executor."""

    execution_plan_id: str = field(default_factory=lambda: f"expl-{uuid4().hex[:12]}")
    source_workpacket_id: str = ""
    profile_id: str = ""
    session_id: str = ""
    target_executor: str = ""
    execution_mode: str = ExecutionTiming.ASYNCHRONOUS.value
    approval_state: str = CoordinatorApprovalState.PENDING.value
    priority: str = ExecutionPriority.NORMAL.value
    risk_class: str = "low"
    status: str = ExecutionPlanStatus.DRAFTED.value
    description: str = ""
    created_at: float = field(default_factory=time.time)
    approved_at: float | None = None
    queued_at: float | None = None
    dispatched_at: float | None = None
    started_at: float | None = None
    completed_at: float | None = None
    failed_at: float | None = None
    cancelled_at: float | None = None
    failure_reason: str = ""
    proof_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_plan_id": self.execution_plan_id,
            "source_workpacket_id": self.source_workpacket_id,
            "profile_id": self.profile_id,
            "session_id": self.session_id,
            "target_executor": self.target_executor,
            "execution_mode": self.execution_mode,
            "approval_state": self.approval_state,
            "priority": self.priority,
            "risk_class": self.risk_class,
            "status": self.status,
            "description": self.description,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "queued_at": self.queued_at,
            "dispatched_at": self.dispatched_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "failed_at": self.failed_at,
            "cancelled_at": self.cancelled_at,
            "failure_reason": self.failure_reason,
            "proof_id": self.proof_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CoordinatorExecutionPlan:
        known = {f.name for f in CoordinatorExecutionPlan.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class ExecutorDefinition:
    """Registry entry for a supported executor target."""

    executor_id: str = field(default_factory=lambda: f"extr-{uuid4().hex[:12]}")
    executor_type: str = ""
    name: str = ""
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    available: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "executor_id": self.executor_id,
            "executor_type": self.executor_type,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "available": self.available,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutorDefinition:
        known = {f.name for f in ExecutorDefinition.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class LifecycleEvent:
    """An event in the execution lifecycle."""

    event_id: str = field(default_factory=lambda: f"lcevt-{uuid4().hex[:12]}")
    execution_plan_id: str = ""
    event_type: str = ""
    timestamp: float = field(default_factory=time.time)
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "execution_plan_id": self.execution_plan_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LifecycleEvent:
        known = {f.name for f in LifecycleEvent.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class ExecutionCoordinatorSnapshot:
    """Point-in-time snapshot of the coordinator state."""

    snapshot_id: str = field(default_factory=lambda: f"ecsnap-{uuid4().hex[:12]}")
    timestamp: float = field(default_factory=time.time)
    total_plans: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    queue_depth: int = 0
    active_count: int = 0
    executor_count: int = 0
    awaiting_approval: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "total_plans": self.total_plans,
            "by_status": self.by_status,
            "queue_depth": self.queue_depth,
            "active_count": self.active_count,
            "executor_count": self.executor_count,
            "awaiting_approval": self.awaiting_approval,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Executor Registry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExecutorRegistry:
    """Registry of canonical executor targets."""

    def __init__(self, store_path: str | None = None) -> None:
        self._store_path = store_path or os.path.join(_coord_data_dir(), "executors.json")
        self._executors: dict[str, ExecutorDefinition] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._store_path):
            try:
                with open(self._store_path) as f:
                    data = json.load(f)
                for entry in data:
                    ex = ExecutorDefinition.from_dict(entry)
                    self._executors[ex.executor_id] = ex
            except (json.JSONDecodeError, OSError):
                logger.warning("Failed to load executor registry, starting empty")

    def _persist(self) -> None:
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        with open(self._store_path, "w") as f:
            json.dump(
                [e.to_dict() for e in self._executors.values()],
                f,
                indent=2,
            )

    def register(self, executor: ExecutorDefinition) -> ExecutorDefinition:
        self._executors[executor.executor_id] = executor
        self._persist()
        logger.info("Registered executor %s (%s)", executor.executor_id, executor.executor_type)
        return executor

    def unregister(self, executor_id: str) -> bool:
        if executor_id in self._executors:
            del self._executors[executor_id]
            self._persist()
            return True
        return False

    def get(self, executor_id: str) -> ExecutorDefinition | None:
        return self._executors.get(executor_id)

    def by_type(self, executor_type: str) -> list[ExecutorDefinition]:
        return [e for e in self._executors.values() if e.executor_type == executor_type]

    def available(self) -> list[ExecutorDefinition]:
        return [e for e in self._executors.values() if e.available]

    def all(self) -> list[ExecutorDefinition]:
        return list(self._executors.values())

    def set_availability(self, executor_id: str, available: bool) -> bool:
        ex = self._executors.get(executor_id)
        if ex:
            ex.available = available
            self._persist()
            return True
        return False

    def seed_defaults(self) -> list[ExecutorDefinition]:
        """Seed the canonical executor types if registry is empty."""
        if self._executors:
            return list(self._executors.values())

        defaults = [
            ExecutorDefinition(
                executor_type=ExecutionTargetType.WORKSTATION.value,
                name="Workstation Executor",
                description="Executes on operator workstation",
                capabilities=["code", "build", "test", "deploy"],
            ),
            ExecutorDefinition(
                executor_type=ExecutionTargetType.AGENT.value,
                name="Agent Executor",
                description="Delegated to AI agent",
                capabilities=["code", "research", "analysis", "content"],
            ),
            ExecutorDefinition(
                executor_type=ExecutionTargetType.VPS.value,
                name="VPS Executor",
                description="Executes on VPS infrastructure",
                capabilities=["deploy", "cron", "service", "build"],
            ),
            ExecutorDefinition(
                executor_type=ExecutionTargetType.CONTAINER.value,
                name="Container Executor",
                description="Executes in isolated container",
                capabilities=["build", "test", "sandbox"],
            ),
            ExecutorDefinition(
                executor_type=ExecutionTargetType.BROWSER.value,
                name="Browser Executor",
                description="Browser-based execution",
                capabilities=["web", "scrape", "test"],
            ),
            ExecutorDefinition(
                executor_type=ExecutionTargetType.MOBILE.value,
                name="Mobile Executor",
                description="Mobile device execution",
                capabilities=["notification", "review", "approve"],
            ),
            ExecutorDefinition(
                executor_type=ExecutionTargetType.EXTERNAL.value,
                name="External Executor",
                description="External service or API",
                capabilities=["api", "webhook", "integration"],
            ),
        ]
        for ex in defaults:
            self._executors[ex.executor_id] = ex
        self._persist()
        return defaults


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Execution Queue
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_PRIORITY_ORDER = {
    ExecutionPriority.CRITICAL.value: 0,
    ExecutionPriority.HIGH.value: 1,
    ExecutionPriority.NORMAL.value: 2,
    ExecutionPriority.LOW.value: 3,
    ExecutionPriority.BACKGROUND.value: 4,
}


class ExecutionQueue:
    """Priority queue for approved execution plans."""

    def __init__(self, store_path: str | None = None) -> None:
        self._store_path = store_path or os.path.join(_coord_data_dir(), "queue", "queue.json")
        self._queue: list[CoordinatorExecutionPlan] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._store_path):
            try:
                with open(self._store_path) as f:
                    data = json.load(f)
                self._queue = [CoordinatorExecutionPlan.from_dict(d) for d in data]
            except (json.JSONDecodeError, OSError):
                logger.warning("Failed to load execution queue, starting empty")

    def _persist(self) -> None:
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        with open(self._store_path, "w") as f:
            json.dump([p.to_dict() for p in self._queue], f, indent=2)

    def _sort(self) -> None:
        self._queue.sort(
            key=lambda p: (
                _PRIORITY_ORDER.get(p.priority, 99),
                p.queued_at or p.created_at,
            )
        )

    def enqueue(self, plan: CoordinatorExecutionPlan) -> None:
        plan.status = ExecutionPlanStatus.QUEUED.value
        plan.queued_at = time.time()
        self._queue.append(plan)
        self._sort()
        self._persist()
        logger.info("Enqueued plan %s (priority=%s)", plan.execution_plan_id, plan.priority)

    def dequeue(self) -> CoordinatorExecutionPlan | None:
        if not self._queue:
            return None
        plan = self._queue.pop(0)
        self._persist()
        return plan

    def peek(self) -> CoordinatorExecutionPlan | None:
        return self._queue[0] if self._queue else None

    def cancel(self, execution_plan_id: str) -> CoordinatorExecutionPlan | None:
        for i, p in enumerate(self._queue):
            if p.execution_plan_id == execution_plan_id:
                removed = self._queue.pop(i)
                removed.status = ExecutionPlanStatus.CANCELLED.value
                removed.cancelled_at = time.time()
                self._persist()
                return removed
        return None

    def reprioritize(self, execution_plan_id: str, new_priority: str) -> bool:
        for p in self._queue:
            if p.execution_plan_id == execution_plan_id:
                p.priority = new_priority
                self._sort()
                self._persist()
                return True
        return False

    def inspect(self) -> list[CoordinatorExecutionPlan]:
        return list(self._queue)

    @property
    def depth(self) -> int:
        return len(self._queue)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Execution Lifecycle Tracker
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExecutionLifecycleTracker:
    """Records the full lifecycle of execution plans."""

    def __init__(self, store_path: str | None = None) -> None:
        self._store_path = store_path or os.path.join(
            _coord_data_dir(), "lifecycle", "events.jsonl"
        )
        self._events: list[LifecycleEvent] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._store_path):
            try:
                with open(self._store_path) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self._events.append(LifecycleEvent.from_dict(json.loads(line)))
            except (json.JSONDecodeError, OSError):
                logger.warning("Failed to load lifecycle events")

    def _append(self, event: LifecycleEvent) -> None:
        self._events.append(event)
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        with open(self._store_path, "a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def record(
        self,
        execution_plan_id: str,
        event_type: str,
        summary: str = "",
        details: dict[str, Any] | None = None,
    ) -> LifecycleEvent:
        event = LifecycleEvent(
            execution_plan_id=execution_plan_id,
            event_type=event_type,
            summary=summary,
            details=details or {},
        )
        self._append(event)
        logger.debug("Lifecycle: %s → %s", execution_plan_id[:12], event_type)
        return event

    def events_for_plan(self, execution_plan_id: str) -> list[LifecycleEvent]:
        return [e for e in self._events if e.execution_plan_id == execution_plan_id]

    def recent(self, limit: int = 50) -> list[LifecycleEvent]:
        return list(reversed(self._events[-limit:]))

    def by_type(self, event_type: str) -> list[LifecycleEvent]:
        return [e for e in self._events if e.event_type == event_type]

    def all_events(self) -> list[LifecycleEvent]:
        return list(self._events)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Governance Gate
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


_RISK_REQUIRES_APPROVAL = {
    "critical": True,
    "high": True,
    "medium": True,
    "low": False,
    "negligible": False,
}


class GovernanceGate:
    """Determines whether an execution plan may proceed."""

    @staticmethod
    def requires_approval(plan: CoordinatorExecutionPlan) -> bool:
        return _RISK_REQUIRES_APPROVAL.get(plan.risk_class, True)

    @staticmethod
    def can_dispatch(plan: CoordinatorExecutionPlan) -> tuple[bool, str]:
        if plan.status == ExecutionPlanStatus.CANCELLED.value:
            return False, "plan is cancelled"

        if plan.status in (
            ExecutionPlanStatus.COMPLETED.value,
            ExecutionPlanStatus.FAILED.value,
        ):
            return False, f"plan is already {plan.status}"

        requires = _RISK_REQUIRES_APPROVAL.get(plan.risk_class, True)
        if requires and plan.approval_state != CoordinatorApprovalState.APPROVED.value:
            return False, f"approval required for risk_class={plan.risk_class}"

        if plan.approval_state == CoordinatorApprovalState.DENIED.value:
            return False, "plan was denied"

        if plan.approval_state == CoordinatorApprovalState.EXPIRED.value:
            return False, "approval has expired"

        return True, "clear"

    @staticmethod
    def auto_approve_eligible(plan: CoordinatorExecutionPlan) -> bool:
        # Wave 2 compatibility banner: CoordinatorExecutionPlan is an internal
        # compatibility representation, NOT the operator Plan. Canonical Wave 1/2
        # lineage (a plan carrying plan_record_id or execution_authorization_ref)
        # can NEVER be auto-approved through the coordinator — its authorization
        # is the HUD execution_authorization Decision, never a risk-based
        # coordinator auto-approve. Fail closed for that lineage.
        meta = plan.metadata or {}
        if meta.get("plan_record_id") or meta.get("execution_authorization_ref"):
            return False
        return not _RISK_REQUIRES_APPROVAL.get(plan.risk_class, True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Plan Store
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PlanStore:
    """Persistent store for all execution plans."""

    def __init__(self, store_dir: str | None = None) -> None:
        self._store_dir = store_dir or os.path.join(_coord_data_dir(), "plans")
        os.makedirs(self._store_dir, exist_ok=True)
        self._plans: dict[str, CoordinatorExecutionPlan] = {}
        self._load()

    def _plan_path(self, plan_id: str) -> str:
        return os.path.join(self._store_dir, f"{plan_id}.json")

    def _load(self) -> None:
        if not os.path.isdir(self._store_dir):
            return
        for fname in os.listdir(self._store_dir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(self._store_dir, fname)) as f:
                    data = json.load(f)
                plan = CoordinatorExecutionPlan.from_dict(data)
                self._plans[plan.execution_plan_id] = plan
            except (json.JSONDecodeError, OSError):
                continue

    def _persist(self, plan: CoordinatorExecutionPlan) -> None:
        with open(self._plan_path(plan.execution_plan_id), "w") as f:
            json.dump(plan.to_dict(), f, indent=2)

    def save(self, plan: CoordinatorExecutionPlan) -> None:
        self._plans[plan.execution_plan_id] = plan
        self._persist(plan)

    def get(self, plan_id: str) -> CoordinatorExecutionPlan | None:
        return self._plans.get(plan_id)

    def by_status(self, status: str) -> list[CoordinatorExecutionPlan]:
        return [p for p in self._plans.values() if p.status == status]

    def by_workpacket(self, wp_id: str) -> list[CoordinatorExecutionPlan]:
        return [p for p in self._plans.values() if p.source_workpacket_id == wp_id]

    def by_session(self, session_id: str) -> list[CoordinatorExecutionPlan]:
        return [p for p in self._plans.values() if p.session_id == session_id]

    def by_profile(self, profile_id: str) -> list[CoordinatorExecutionPlan]:
        return [p for p in self._plans.values() if p.profile_id == profile_id]

    def awaiting_approval(self) -> list[CoordinatorExecutionPlan]:
        return [
            p
            for p in self._plans.values()
            if p.approval_state == CoordinatorApprovalState.PENDING.value
            and p.status == ExecutionPlanStatus.DRAFTED.value
        ]

    def active(self) -> list[CoordinatorExecutionPlan]:
        return [
            p
            for p in self._plans.values()
            if p.status
            in (
                ExecutionPlanStatus.DISPATCHED.value,
                ExecutionPlanStatus.EXECUTING.value,
            )
        ]

    def history(self, limit: int = 50) -> list[CoordinatorExecutionPlan]:
        terminal = [
            p
            for p in self._plans.values()
            if p.status
            in (
                ExecutionPlanStatus.COMPLETED.value,
                ExecutionPlanStatus.FAILED.value,
                ExecutionPlanStatus.CANCELLED.value,
            )
        ]
        terminal.sort(
            key=lambda p: p.completed_at or p.failed_at or p.cancelled_at or 0, reverse=True
        )
        return terminal[:limit]

    def all_plans(self) -> list[CoordinatorExecutionPlan]:
        return list(self._plans.values())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cross-Runtime Compositor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CrossRuntimeCompositor:
    """Assembles execution context from P5-P12 without modifying them."""

    @staticmethod
    def gather_profile_context() -> dict[str, Any]:
        try:
            from substrate.organism.profile_runtime import get_profile_runtime

            pr = get_profile_runtime()
            snap = pr.snapshot()
            return snap.to_dict()
        except Exception:
            return {"error": "profile_runtime unavailable"}

    @staticmethod
    def gather_session_context() -> dict[str, Any]:
        try:
            from substrate.organism.session_runtime import get_session_runtime

            sr = get_session_runtime()
            snap = sr.snapshot()
            return snap.to_dict()
        except Exception:
            return {"error": "session_runtime unavailable"}

    @staticmethod
    def gather_presence_context() -> dict[str, Any]:
        try:
            from substrate.organism.presence_runtime import PresenceRuntime

            pr = PresenceRuntime()
            return pr.snapshot()
        except Exception:
            return {"error": "presence_runtime unavailable"}

    @staticmethod
    def gather_workstation_context() -> dict[str, Any]:
        try:
            from substrate.organism.workstation_runtime import get_workstation_runtime

            wr = get_workstation_runtime()
            snap = wr.snapshot()
            return snap.to_dict()
        except Exception:
            return {"error": "workstation_runtime unavailable"}

    @staticmethod
    def gather_projection_context() -> dict[str, Any]:
        try:
            from substrate.organism.projection_engine import get_projection_engine

            pe = get_projection_engine()
            snap = pe.snapshot()
            return snap.to_dict()
        except Exception:
            return {"error": "projection_engine unavailable"}

    @staticmethod
    def gather_continuity_context() -> dict[str, Any]:
        try:
            from substrate.organism.continuity_runtime import get_continuity_runtime

            cr = get_continuity_runtime()
            snap = cr.snapshot()
            return snap.to_dict()
        except Exception:
            return {"error": "continuity_runtime unavailable"}

    @staticmethod
    def full_context() -> dict[str, Any]:
        return {
            "profile": CrossRuntimeCompositor.gather_profile_context(),
            "session": CrossRuntimeCompositor.gather_session_context(),
            "presence": CrossRuntimeCompositor.gather_presence_context(),
            "workstation": CrossRuntimeCompositor.gather_workstation_context(),
            "projection": CrossRuntimeCompositor.gather_projection_context(),
            "continuity": CrossRuntimeCompositor.gather_continuity_context(),
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Execution Coordinator (top-level orchestrator)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExecutionCoordinator:
    """Top-level orchestrator for execution coordination.

    Receives approved WorkPackets, creates execution plans, manages
    approval gates, queues work, assigns targets, and tracks the full
    execution lifecycle.  Never executes — only coordinates.
    """

    def __init__(
        self,
        data_dir: str | None = None,
    ) -> None:
        dd = data_dir or _coord_data_dir()
        _ensure_dirs()

        self._plan_store = PlanStore(os.path.join(dd, "plans"))
        self._queue = ExecutionQueue(os.path.join(dd, "queue", "queue.json"))
        self._lifecycle = ExecutionLifecycleTracker(os.path.join(dd, "lifecycle", "events.jsonl"))
        self._executor_registry = ExecutorRegistry(os.path.join(dd, "executors.json"))
        self._compositor = CrossRuntimeCompositor()
        self._gate = GovernanceGate()

    # ── Plan Creation ────────────────────────────────────

    def create_plan(
        self,
        source_workpacket_id: str,
        target_executor: str,
        *,
        profile_id: str = "",
        session_id: str = "",
        execution_mode: str = ExecutionTiming.ASYNCHRONOUS.value,
        priority: str = ExecutionPriority.NORMAL.value,
        risk_class: str = "low",
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> CoordinatorExecutionPlan:
        """Create a new execution plan for a WorkPacket."""
        plan = CoordinatorExecutionPlan(
            source_workpacket_id=source_workpacket_id,
            target_executor=target_executor,
            profile_id=profile_id,
            session_id=session_id,
            execution_mode=execution_mode,
            priority=priority,
            risk_class=risk_class,
            description=description,
            metadata=metadata or {},
        )

        if self._gate.auto_approve_eligible(plan):
            plan.approval_state = CoordinatorApprovalState.APPROVED.value
            plan.approved_at = time.time()

        self._plan_store.save(plan)
        self._lifecycle.record(
            plan.execution_plan_id,
            LifecycleEventType.PLAN_CREATED.value,
            summary=f"Plan created for WP {source_workpacket_id[:12]}",
            details={
                "target_executor": target_executor,
                "priority": priority,
                "risk_class": risk_class,
                "auto_approved": plan.approval_state == CoordinatorApprovalState.APPROVED.value,
            },
        )

        logger.info(
            "Created plan %s for WP %s → %s",
            plan.execution_plan_id,
            source_workpacket_id[:12],
            target_executor,
        )
        return plan

    # ── Approval ─────────────────────────────────────────

    def approve_plan(
        self,
        execution_plan_id: str,
        approved_by: str = "operator",
    ) -> CoordinatorExecutionPlan | None:
        """Approve an execution plan."""
        plan = self._plan_store.get(execution_plan_id)
        if not plan:
            return None
        if plan.approval_state != CoordinatorApprovalState.PENDING.value:
            logger.warning("Plan %s already %s", execution_plan_id, plan.approval_state)
            return plan

        plan.approval_state = CoordinatorApprovalState.APPROVED.value
        plan.approved_at = time.time()
        plan.status = ExecutionPlanStatus.APPROVED.value
        self._plan_store.save(plan)

        self._lifecycle.record(
            execution_plan_id,
            LifecycleEventType.PLAN_APPROVED.value,
            summary=f"Approved by {approved_by}",
            details={"approved_by": approved_by},
        )
        return plan

    def deny_plan(
        self,
        execution_plan_id: str,
        reason: str = "",
        denied_by: str = "operator",
    ) -> CoordinatorExecutionPlan | None:
        """Deny an execution plan."""
        plan = self._plan_store.get(execution_plan_id)
        if not plan:
            return None
        # WP-P1-007: compare-and-swap guard — only a PENDING plan may be denied.
        # Without this an already-APPROVED plan could be flipped to DENIED
        # (double-resolve race). Mirrors approve_plan's PENDING guard.
        if plan.approval_state != CoordinatorApprovalState.PENDING.value:
            logger.warning(
                "Plan %s already %s — deny refused", execution_plan_id, plan.approval_state
            )
            return plan

        plan.approval_state = CoordinatorApprovalState.DENIED.value
        plan.status = ExecutionPlanStatus.CANCELLED.value
        plan.cancelled_at = time.time()
        self._plan_store.save(plan)

        self._lifecycle.record(
            execution_plan_id,
            LifecycleEventType.PLAN_DENIED.value,
            summary=f"Denied by {denied_by}: {reason}",
            details={"denied_by": denied_by, "reason": reason},
        )
        return plan

    # ── Queueing ─────────────────────────────────────────

    def enqueue_plan(
        self,
        execution_plan_id: str,
    ) -> CoordinatorExecutionPlan | None:
        """Move an approved plan into the execution queue."""
        plan = self._plan_store.get(execution_plan_id)
        if not plan:
            return None

        can, reason = self._gate.can_dispatch(plan)
        if not can:
            logger.warning("Cannot enqueue %s: %s", execution_plan_id, reason)
            return None

        self._queue.enqueue(plan)
        self._plan_store.save(plan)

        self._lifecycle.record(
            execution_plan_id,
            LifecycleEventType.PLAN_QUEUED.value,
            summary=f"Queued at priority {plan.priority}",
        )
        return plan

    # ── Dispatch ─────────────────────────────────────────

    def dispatch_next(self) -> CoordinatorExecutionPlan | None:
        """Dequeue the highest-priority plan and mark dispatched."""
        plan = self._queue.dequeue()
        if not plan:
            return None

        can, reason = self._gate.can_dispatch(plan)
        if not can:
            logger.warning("Gate blocked dispatch of %s: %s", plan.execution_plan_id, reason)
            return None

        plan.status = ExecutionPlanStatus.DISPATCHED.value
        plan.dispatched_at = time.time()
        self._plan_store.save(plan)

        self._lifecycle.record(
            plan.execution_plan_id,
            LifecycleEventType.PLAN_DISPATCHED.value,
            summary=f"Dispatched to {plan.target_executor}",
            details={"target_executor": plan.target_executor},
        )
        return plan

    # ── Execution Status Transitions ─────────────────────

    def mark_started(self, execution_plan_id: str) -> CoordinatorExecutionPlan | None:
        plan = self._plan_store.get(execution_plan_id)
        if not plan:
            return None
        if plan.status != ExecutionPlanStatus.DISPATCHED.value:
            logger.warning("Cannot start %s in status %s", execution_plan_id, plan.status)
            return None

        plan.status = ExecutionPlanStatus.EXECUTING.value
        plan.started_at = time.time()
        self._plan_store.save(plan)

        self._lifecycle.record(
            execution_plan_id,
            LifecycleEventType.EXECUTION_STARTED.value,
            summary="Execution started",
        )
        return plan

    def mark_completed(
        self,
        execution_plan_id: str,
        proof_id: str = "",
    ) -> CoordinatorExecutionPlan | None:
        plan = self._plan_store.get(execution_plan_id)
        if not plan:
            return None
        if plan.status != ExecutionPlanStatus.EXECUTING.value:
            logger.warning("Cannot complete %s in status %s", execution_plan_id, plan.status)
            return None

        plan.status = ExecutionPlanStatus.COMPLETED.value
        plan.completed_at = time.time()
        plan.proof_id = proof_id
        self._plan_store.save(plan)

        self._lifecycle.record(
            execution_plan_id,
            LifecycleEventType.EXECUTION_COMPLETED.value,
            summary="Execution completed",
            details={"proof_id": proof_id} if proof_id else {},
        )
        return plan

    def mark_failed(
        self,
        execution_plan_id: str,
        reason: str = "",
    ) -> CoordinatorExecutionPlan | None:
        plan = self._plan_store.get(execution_plan_id)
        if not plan:
            return None
        if plan.status not in (
            ExecutionPlanStatus.DISPATCHED.value,
            ExecutionPlanStatus.EXECUTING.value,
        ):
            logger.warning("Cannot fail %s in status %s", execution_plan_id, plan.status)
            return None

        plan.status = ExecutionPlanStatus.FAILED.value
        plan.failed_at = time.time()
        plan.failure_reason = reason
        self._plan_store.save(plan)

        self._lifecycle.record(
            execution_plan_id,
            LifecycleEventType.EXECUTION_FAILED.value,
            summary=f"Execution failed: {reason}",
            details={"reason": reason},
        )
        return plan

    def cancel_plan(self, execution_plan_id: str) -> CoordinatorExecutionPlan | None:
        plan = self._plan_store.get(execution_plan_id)
        if not plan:
            return None
        if plan.status in (
            ExecutionPlanStatus.COMPLETED.value,
            ExecutionPlanStatus.FAILED.value,
        ):
            return None

        self._queue.cancel(execution_plan_id)
        plan.status = ExecutionPlanStatus.CANCELLED.value
        plan.cancelled_at = time.time()
        self._plan_store.save(plan)

        self._lifecycle.record(
            execution_plan_id,
            LifecycleEventType.PLAN_CANCELLED.value,
            summary="Plan cancelled",
        )
        return plan

    # ── Reprioritize ─────────────────────────────────────

    def reprioritize(
        self,
        execution_plan_id: str,
        new_priority: str,
    ) -> CoordinatorExecutionPlan | None:
        plan = self._plan_store.get(execution_plan_id)
        if not plan:
            return None

        old_priority = plan.priority
        plan.priority = new_priority
        self._plan_store.save(plan)
        self._queue.reprioritize(execution_plan_id, new_priority)

        self._lifecycle.record(
            execution_plan_id,
            LifecycleEventType.PLAN_REPRIORITIZED.value,
            summary=f"Priority: {old_priority} → {new_priority}",
            details={"old_priority": old_priority, "new_priority": new_priority},
        )
        return plan

    # ── Cross-Runtime Context ────────────────────────────

    def gather_context(self) -> dict[str, Any]:
        return self._compositor.full_context()

    # ── Queries ──────────────────────────────────────────

    def get_plan(self, plan_id: str) -> CoordinatorExecutionPlan | None:
        return self._plan_store.get(plan_id)

    def plans_by_status(self, status: str) -> list[CoordinatorExecutionPlan]:
        return self._plan_store.by_status(status)

    def plans_by_workpacket(self, wp_id: str) -> list[CoordinatorExecutionPlan]:
        return self._plan_store.by_workpacket(wp_id)

    def plans_by_session(self, session_id: str) -> list[CoordinatorExecutionPlan]:
        return self._plan_store.by_session(session_id)

    def plans_by_profile(self, profile_id: str) -> list[CoordinatorExecutionPlan]:
        return self._plan_store.by_profile(profile_id)

    def awaiting_approval(self) -> list[CoordinatorExecutionPlan]:
        return self._plan_store.awaiting_approval()

    def active_plans(self) -> list[CoordinatorExecutionPlan]:
        return self._plan_store.active()

    def plan_history(self, limit: int = 50) -> list[CoordinatorExecutionPlan]:
        return self._plan_store.history(limit)

    def queue_state(self) -> list[CoordinatorExecutionPlan]:
        return self._queue.inspect()

    def queue_depth(self) -> int:
        return self._queue.depth

    def lifecycle_for_plan(self, plan_id: str) -> list[LifecycleEvent]:
        return self._lifecycle.events_for_plan(plan_id)

    def recent_lifecycle(self, limit: int = 50) -> list[LifecycleEvent]:
        return self._lifecycle.recent(limit)

    # ── Executor Registry ────────────────────────────────

    def register_executor(self, executor: ExecutorDefinition) -> ExecutorDefinition:
        return self._executor_registry.register(executor)

    def unregister_executor(self, executor_id: str) -> bool:
        return self._executor_registry.unregister(executor_id)

    def executors(self) -> list[ExecutorDefinition]:
        return self._executor_registry.all()

    def available_executors(self) -> list[ExecutorDefinition]:
        return self._executor_registry.available()

    def executors_by_type(self, executor_type: str) -> list[ExecutorDefinition]:
        return self._executor_registry.by_type(executor_type)

    def seed_executors(self) -> list[ExecutorDefinition]:
        return self._executor_registry.seed_defaults()

    # ── Snapshot ──────────────────────────────────────────

    def snapshot(self) -> ExecutionCoordinatorSnapshot:
        all_plans = self._plan_store.all_plans()
        by_status: dict[str, int] = {}
        for p in all_plans:
            by_status[p.status] = by_status.get(p.status, 0) + 1

        return ExecutionCoordinatorSnapshot(
            total_plans=len(all_plans),
            by_status=by_status,
            queue_depth=self._queue.depth,
            active_count=len(self._plan_store.active()),
            executor_count=len(self._executor_registry.all()),
            awaiting_approval=len(self._plan_store.awaiting_approval()),
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Singleton
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_singleton: ExecutionCoordinator | None = None


def get_execution_coordinator() -> ExecutionCoordinator:
    global _singleton
    if _singleton is None:
        _singleton = ExecutionCoordinator()
    return _singleton


def reset_execution_coordinator() -> None:
    global _singleton
    _singleton = None
