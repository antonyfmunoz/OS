"""Worker Supervisor v1 for the UMH substrate layer.

Autonomous worker lifecycle management: health checks, startup
plans, autostart policies, and structured remediation.

The founder should NOT manually switch terminals, restart adapters,
invoke relay scripts, or trigger local workers — except where
explicit governance requires human approval or visual confirmation.

UMH substrate subsystem. Phase 96.8AB.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from core.runtime.worker_runtime_contracts import (
    EnvironmentType,
    ProofStatus,
    WorkerHeartbeat,
    WorkerRuntimeDescriptor,
)


class WorkerType(str, Enum):
    LOCAL_RUNTIME_DAEMON = "local_runtime_daemon"
    DISCORD_ADAPTER = "discord_adapter"
    WINDOWS_RELAY = "windows_relay"
    DRIVE_ADAPTER = "drive_adapter"
    DOCS_ADAPTER = "docs_adapter"
    CHROME_BROWSER = "chrome_browser"


class WorkerHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


class AutostartDecision(str, Enum):
    ALLOWED = "allowed"
    BLOCKED_GOVERNANCE = "blocked_governance"
    BLOCKED_DEPENDENCY = "blocked_dependency"
    BLOCKED_CONFIG = "blocked_config"
    REQUIRES_HUMAN = "requires_human"


class RecoveryAction(str, Enum):
    AUTOSTART = "autostart"
    RESTART = "restart"
    WAIT_DEPENDENCY = "wait_dependency"
    ESCALATE_TO_FOUNDER = "escalate_to_founder"
    NO_ACTION = "no_action"


WORKER_DEPENDENCIES: dict[WorkerType, list[WorkerType]] = {
    WorkerType.LOCAL_RUNTIME_DAEMON: [],
    WorkerType.DISCORD_ADAPTER: [],
    WorkerType.WINDOWS_RELAY: [WorkerType.LOCAL_RUNTIME_DAEMON],
    WorkerType.CHROME_BROWSER: [WorkerType.WINDOWS_RELAY],
    WorkerType.DRIVE_ADAPTER: [WorkerType.CHROME_BROWSER],
    WorkerType.DOCS_ADAPTER: [WorkerType.CHROME_BROWSER],
}

AUTOSTART_ALLOWED_WORKERS = frozenset(
    {
        WorkerType.LOCAL_RUNTIME_DAEMON,
        WorkerType.DISCORD_ADAPTER,
    }
)

REQUIRES_HUMAN_CONFIRMATION = frozenset(
    {
        WorkerType.CHROME_BROWSER,
        WorkerType.WINDOWS_RELAY,
    }
)


@dataclass
class WorkerHealthCheck:
    """Result of checking a single worker's health."""

    worker_type: WorkerType
    status: WorkerHealthStatus
    last_heartbeat: str = ""
    heartbeat_age_seconds: float = -1.0
    connectivity_ok: bool = False
    dependencies_met: bool = True
    unmet_dependencies: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_type": self.worker_type.value,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat,
            "heartbeat_age_seconds": self.heartbeat_age_seconds,
            "connectivity_ok": self.connectivity_ok,
            "dependencies_met": self.dependencies_met,
            "unmet_dependencies": self.unmet_dependencies,
            "notes": self.notes,
        }


@dataclass
class WorkerStartupPlan:
    """Plan for starting a single worker."""

    worker_type: WorkerType
    autostart_decision: AutostartDecision
    recovery_action: RecoveryAction
    reason: str = ""
    dependency_chain: list[str] = field(default_factory=list)
    estimated_startup_seconds: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_type": self.worker_type.value,
            "autostart_decision": self.autostart_decision.value,
            "recovery_action": self.recovery_action.value,
            "reason": self.reason,
            "dependency_chain": self.dependency_chain,
            "estimated_startup_seconds": self.estimated_startup_seconds,
            "notes": self.notes,
        }


@dataclass
class WorkerProcessRef:
    """Reference to a running worker process."""

    worker_type: WorkerType
    pid: int = 0
    started_at: str = ""
    runtime_id: str = ""
    environment: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_type": self.worker_type.value,
            "pid": self.pid,
            "started_at": self.started_at,
            "runtime_id": self.runtime_id,
            "environment": self.environment,
        }


@dataclass
class WorkerAutostartPolicy:
    """Policy governing whether a worker can be auto-started."""

    worker_type: WorkerType
    can_autostart: bool
    requires_human_confirmation: bool
    max_restart_attempts: int = 3
    cooldown_seconds: int = 30
    governance_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_type": self.worker_type.value,
            "can_autostart": self.can_autostart,
            "requires_human_confirmation": self.requires_human_confirmation,
            "max_restart_attempts": self.max_restart_attempts,
            "cooldown_seconds": self.cooldown_seconds,
            "governance_notes": self.governance_notes,
        }


@dataclass
class WorkerRecoveryResult:
    """Outcome of a recovery attempt for a worker."""

    worker_type: WorkerType
    action_taken: RecoveryAction
    success: bool
    new_status: WorkerHealthStatus
    message: str = ""
    timestamp: str = ""
    trace_id: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_type": self.worker_type.value,
            "action_taken": self.action_taken.value,
            "success": self.success,
            "new_status": self.new_status.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
        }


class WorkerSupervisor:
    """Manages worker lifecycle: health checks, startup, recovery.

    Workers with unmet dependencies are not started.
    Workers requiring human confirmation produce escalation plans.
    """

    def __init__(
        self,
        autostart_workers: bool = True,
        worker_statuses: dict[str, WorkerHealthStatus] | None = None,
    ) -> None:
        self._autostart_workers = autostart_workers
        self._health_cache: dict[WorkerType, WorkerHealthCheck] = {}
        self._process_refs: dict[WorkerType, WorkerProcessRef] = {}
        self._policies = self._build_policies()
        if worker_statuses:
            for wt_str, status in worker_statuses.items():
                try:
                    wt = WorkerType(wt_str)
                    self._health_cache[wt] = WorkerHealthCheck(worker_type=wt, status=status)
                except ValueError:
                    pass

    def _build_policies(self) -> dict[WorkerType, WorkerAutostartPolicy]:
        policies: dict[WorkerType, WorkerAutostartPolicy] = {}
        for wt in WorkerType:
            policies[wt] = WorkerAutostartPolicy(
                worker_type=wt,
                can_autostart=(self._autostart_workers and wt in AUTOSTART_ALLOWED_WORKERS),
                requires_human_confirmation=wt in REQUIRES_HUMAN_CONFIRMATION,
            )
        return policies

    def check_worker(
        self,
        worker_type: WorkerType,
        heartbeat: WorkerHeartbeat | None = None,
    ) -> WorkerHealthCheck:
        deps = WORKER_DEPENDENCIES.get(worker_type, [])
        unmet = []
        for dep in deps:
            dep_health = self._health_cache.get(dep)
            if not dep_health or dep_health.status != WorkerHealthStatus.HEALTHY:
                unmet.append(dep.value)

        if heartbeat and heartbeat.status == "alive":
            status = WorkerHealthStatus.HEALTHY
            connectivity = True
        elif heartbeat and heartbeat.status == "degraded":
            status = WorkerHealthStatus.DEGRADED
            connectivity = True
        else:
            cached = self._health_cache.get(worker_type)
            if cached:
                status = cached.status
                connectivity = cached.connectivity_ok
            else:
                status = WorkerHealthStatus.UNKNOWN
                connectivity = False

        check = WorkerHealthCheck(
            worker_type=worker_type,
            status=status,
            last_heartbeat=heartbeat.timestamp if heartbeat else "",
            connectivity_ok=connectivity,
            dependencies_met=len(unmet) == 0,
            unmet_dependencies=unmet,
        )
        self._health_cache[worker_type] = check
        return check

    def plan_startup(self, worker_type: WorkerType) -> WorkerStartupPlan:
        health = self._health_cache.get(worker_type)
        policy = self._policies.get(worker_type)

        if health and health.status == WorkerHealthStatus.HEALTHY:
            return WorkerStartupPlan(
                worker_type=worker_type,
                autostart_decision=AutostartDecision.ALLOWED,
                recovery_action=RecoveryAction.NO_ACTION,
                reason="already_healthy",
            )

        if health and not health.dependencies_met:
            return WorkerStartupPlan(
                worker_type=worker_type,
                autostart_decision=AutostartDecision.BLOCKED_DEPENDENCY,
                recovery_action=RecoveryAction.WAIT_DEPENDENCY,
                reason=f"unmet_deps: {health.unmet_dependencies}",
                dependency_chain=[d.value for d in WORKER_DEPENDENCIES.get(worker_type, [])],
            )

        if policy and policy.requires_human_confirmation:
            return WorkerStartupPlan(
                worker_type=worker_type,
                autostart_decision=AutostartDecision.REQUIRES_HUMAN,
                recovery_action=RecoveryAction.ESCALATE_TO_FOUNDER,
                reason="requires_human_visual_confirmation",
            )

        if policy and not policy.can_autostart:
            return WorkerStartupPlan(
                worker_type=worker_type,
                autostart_decision=AutostartDecision.BLOCKED_CONFIG,
                recovery_action=RecoveryAction.ESCALATE_TO_FOUNDER,
                reason="autostart_not_enabled",
            )

        return WorkerStartupPlan(
            worker_type=worker_type,
            autostart_decision=AutostartDecision.ALLOWED,
            recovery_action=RecoveryAction.AUTOSTART,
            reason="autostart_allowed",
            estimated_startup_seconds=5,
        )

    def attempt_recovery(self, worker_type: WorkerType, trace_id: str = "") -> WorkerRecoveryResult:
        plan = self.plan_startup(worker_type)

        if plan.recovery_action == RecoveryAction.NO_ACTION:
            return WorkerRecoveryResult(
                worker_type=worker_type,
                action_taken=RecoveryAction.NO_ACTION,
                success=True,
                new_status=WorkerHealthStatus.HEALTHY,
                message="already_healthy",
                trace_id=trace_id,
            )

        if plan.recovery_action == RecoveryAction.ESCALATE_TO_FOUNDER:
            return WorkerRecoveryResult(
                worker_type=worker_type,
                action_taken=RecoveryAction.ESCALATE_TO_FOUNDER,
                success=False,
                new_status=WorkerHealthStatus.STOPPED,
                message=plan.reason,
                trace_id=trace_id,
            )

        if plan.recovery_action == RecoveryAction.WAIT_DEPENDENCY:
            return WorkerRecoveryResult(
                worker_type=worker_type,
                action_taken=RecoveryAction.WAIT_DEPENDENCY,
                success=False,
                new_status=WorkerHealthStatus.STOPPED,
                message=plan.reason,
                trace_id=trace_id,
            )

        self._health_cache[worker_type] = WorkerHealthCheck(
            worker_type=worker_type,
            status=WorkerHealthStatus.HEALTHY,
            connectivity_ok=True,
            dependencies_met=True,
        )
        return WorkerRecoveryResult(
            worker_type=worker_type,
            action_taken=RecoveryAction.AUTOSTART,
            success=True,
            new_status=WorkerHealthStatus.HEALTHY,
            message="autostarted_successfully",
            trace_id=trace_id,
        )

    def check_all_workers(self) -> dict[str, WorkerHealthCheck]:
        results: dict[str, WorkerHealthCheck] = {}
        for wt in WorkerType:
            if wt not in self._health_cache:
                self._health_cache[wt] = WorkerHealthCheck(
                    worker_type=wt, status=WorkerHealthStatus.UNKNOWN
                )
            results[wt.value] = self._health_cache[wt]
        return results

    def get_startup_plan_all(self) -> list[WorkerStartupPlan]:
        plans: list[WorkerStartupPlan] = []
        for wt in WorkerType:
            plans.append(self.plan_startup(wt))
        return plans

    def get_remediation_report(self) -> dict[str, Any]:
        checks = self.check_all_workers()
        plans = self.get_startup_plan_all()
        blocked = [p for p in plans if p.autostart_decision != AutostartDecision.ALLOWED]
        return {
            "total_workers": len(WorkerType),
            "healthy": sum(1 for c in checks.values() if c.status == WorkerHealthStatus.HEALTHY),
            "unhealthy": sum(1 for c in checks.values() if c.status != WorkerHealthStatus.HEALTHY),
            "blocked_startups": len(blocked),
            "blocked_details": [p.to_dict() for p in blocked],
            "all_checks": {k: v.to_dict() for k, v in checks.items()},
        }
