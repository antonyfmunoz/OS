"""Execution Fabric Runtime — Campaign 19.0.

Composes 6 existing runtimes into a single execution operations truth.
Answers: What is running? Where? What is blocked? What capacity remains?

Read-only. No dispatch. No execute. No approve. No mutate.
Aggregate → normalize → present.

C19 substrate workstation subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class ExecutionFabricState(str, Enum):
    """Overall execution fabric health — derived deterministically."""
    IDLE = "idle"
    ACTIVE = "active"
    SATURATED = "saturated"
    BLOCKED = "blocked"
    DEGRADED = "degraded"


@dataclass
class ExecutionFabricSnapshot:
    fabric_state: str = ExecutionFabricState.IDLE.value
    execution_state: str = "idle"
    organism_health: str = "unknown"
    active_plans: list[dict[str, Any]] = field(default_factory=list)
    queue_depth: int = 0
    awaiting_approval_count: int = 0
    compute_nodes: list[dict[str, Any]] = field(default_factory=list)
    active_sessions: list[dict[str, Any]] = field(default_factory=list)
    online_devices: list[dict[str, Any]] = field(default_factory=list)
    blocked_work: list[dict[str, Any]] = field(default_factory=list)
    work_velocity: dict[str, Any] = field(default_factory=dict)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "fabric_state": self.fabric_state,
            "execution_state": self.execution_state,
            "organism_health": self.organism_health,
            "active_plans": self.active_plans,
            "queue_depth": self.queue_depth,
            "awaiting_approval_count": self.awaiting_approval_count,
            "compute_nodes": self.compute_nodes,
            "active_sessions": self.active_sessions,
            "online_devices": self.online_devices,
            "blocked_work": self.blocked_work,
            "work_velocity": self.work_velocity,
            "generated_at": self.generated_at,
        }


# ── Runtime ─────────────────────────────────────────────────────────


class ExecutionFabricRuntime:
    """Unified execution operations truth — composes 6 runtimes.

    Read-only. Aggregate → normalize → present.
    """

    def __init__(
        self,
        governed_execution: Any | None = None,
        execution_coordinator: Any | None = None,
        compute_fabric: Any | None = None,
        work_portfolio: Any | None = None,
        session_runtime: Any | None = None,
        presence_runtime: Any | None = None,
    ) -> None:
        self._governed_execution = governed_execution
        self._execution_coordinator = execution_coordinator
        self._compute_fabric = compute_fabric
        self._work_portfolio = work_portfolio
        self._session_runtime = session_runtime
        self._presence_runtime = presence_runtime

    # ── Lazy accessors ────────────────────────────────────────────────

    @property
    def _gov_exec(self) -> Any:
        if self._governed_execution is None:
            try:
                from substrate.organism.governed_execution_runtime import (
                    GovernedExecutionRuntime,
                )
                self._governed_execution = GovernedExecutionRuntime()
            except Exception:
                logger.debug("GovernedExecutionRuntime unavailable")
        return self._governed_execution

    @property
    def _coord(self) -> Any:
        if self._execution_coordinator is None:
            try:
                from substrate.organism.execution_coordinator import (
                    ExecutionCoordinator,
                )
                self._execution_coordinator = ExecutionCoordinator()
            except Exception:
                logger.debug("ExecutionCoordinator unavailable")
        return self._execution_coordinator

    @property
    def _compute(self) -> Any:
        if self._compute_fabric is None:
            try:
                from substrate.organism.compute_fabric_runtime import (
                    ComputeFabricRuntime,
                )
                self._compute_fabric = ComputeFabricRuntime()
            except Exception:
                logger.debug("ComputeFabricRuntime unavailable")
        return self._compute_fabric

    @property
    def _portfolio(self) -> Any:
        if self._work_portfolio is None:
            try:
                from substrate.organism.work_portfolio_runtime import (
                    WorkPortfolioRuntime,
                )
                self._work_portfolio = WorkPortfolioRuntime()
            except Exception:
                logger.debug("WorkPortfolioRuntime unavailable")
        return self._work_portfolio

    @property
    def _sessions(self) -> Any:
        if self._session_runtime is None:
            try:
                from substrate.organism.session_runtime import SessionRuntime
                self._session_runtime = SessionRuntime()
            except Exception:
                logger.debug("SessionRuntime unavailable")
        return self._session_runtime

    @property
    def _presence(self) -> Any:
        if self._presence_runtime is None:
            try:
                from substrate.organism.presence_runtime import PresenceRuntime
                self._presence_runtime = PresenceRuntime()
            except Exception:
                logger.debug("PresenceRuntime unavailable")
        return self._presence_runtime

    # ── Helpers ───────────────────────────────────────────────────────

    def _safe_call(self, obj: Any, method: str, *args: Any, **kwargs: Any) -> Any:
        if obj is None:
            return None
        fn = getattr(obj, method, None)
        if fn is None:
            return None
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            logger.debug("ExecutionFabricRuntime._safe_call(%s) failed: %s", method, exc)
            return None

    # ── State derivation ──────────────────────────────────────────────

    def state(self) -> ExecutionFabricState:
        nodes = self._get_compute_nodes()
        unreachable = [n for n in nodes if n.get("health") == "unreachable"]
        if unreachable or (not nodes and self._compute is not None):
            return ExecutionFabricState.DEGRADED

        queue_depth = self._get_queue_depth()
        total_capacity, used_capacity = self._get_capacity_numbers(nodes)
        available = total_capacity - used_capacity

        if queue_depth > 0 and available <= 0:
            return ExecutionFabricState.BLOCKED

        if total_capacity > 0 and (used_capacity / total_capacity) > 0.8:
            return ExecutionFabricState.SATURATED

        active = self._get_active_plans()
        if active:
            return ExecutionFabricState.ACTIVE

        return ExecutionFabricState.IDLE

    # ── Public API ────────────────────────────────────────────────────

    def snapshot(self) -> ExecutionFabricSnapshot:
        now = time.time()
        nodes = self._get_compute_nodes()
        active = self._get_active_plans()
        sessions = self._get_active_sessions()
        devices = self._get_online_devices()
        blocked = self._get_blocked_work()
        velocity = self._get_work_velocity()
        gov_snap = self._safe_call(self._gov_exec, "snapshot")
        exec_state = gov_snap.state if gov_snap and hasattr(gov_snap, "state") else "idle"
        org_health = gov_snap.organism_health if gov_snap and hasattr(gov_snap, "organism_health") else "unknown"
        queue_depth = self._get_queue_depth()
        approval_count = self._get_approval_count()

        return ExecutionFabricSnapshot(
            fabric_state=self.state().value,
            execution_state=exec_state if isinstance(exec_state, str) else str(exec_state),
            organism_health=org_health if isinstance(org_health, str) else str(org_health),
            active_plans=active,
            queue_depth=queue_depth,
            awaiting_approval_count=approval_count,
            compute_nodes=nodes,
            active_sessions=sessions,
            online_devices=devices,
            blocked_work=blocked,
            work_velocity=velocity,
            generated_at=now,
        )

    def active_executions(self) -> list[dict[str, Any]]:
        return self._get_active_plans()

    def blocked(self) -> list[dict[str, Any]]:
        return self._get_blocked_work()

    def capacity(self) -> dict[str, Any]:
        nodes = self._get_compute_nodes()
        total, used = self._get_capacity_numbers(nodes)
        return {
            "total_capacity": total,
            "used_capacity": used,
            "available_capacity": total - used,
            "utilization": round(used / total, 3) if total > 0 else 0.0,
            "node_count": len(nodes),
        }

    def session_bindings(self) -> list[dict[str, Any]]:
        sessions = self._get_active_sessions()
        return sessions

    def summary(self) -> dict[str, Any]:
        snap = self.snapshot()
        return {
            "ok": True,
            "fabric_state": snap.fabric_state,
            "execution_state": snap.execution_state,
            "active_plan_count": len(snap.active_plans),
            "queue_depth": snap.queue_depth,
            "awaiting_approval_count": snap.awaiting_approval_count,
            "compute_node_count": len(snap.compute_nodes),
            "session_count": len(snap.active_sessions),
            "online_device_count": len(snap.online_devices),
            "blocked_count": len(snap.blocked_work),
            "generated_at": snap.generated_at,
        }

    # ── Internal data collection ──────────────────────────────────────

    def _get_compute_nodes(self) -> list[dict[str, Any]]:
        result = self._safe_call(self._compute, "get_all_nodes")
        if result is None:
            return []
        if isinstance(result, list):
            return [n.to_dict() if hasattr(n, "to_dict") else n for n in result]
        return []

    def _get_active_plans(self) -> list[dict[str, Any]]:
        result = self._safe_call(self._coord, "list_plans_by_status", "executing")
        executing = result or []
        result2 = self._safe_call(self._coord, "list_plans_by_status", "dispatched")
        dispatched = result2 or []
        all_plans = list(executing) + list(dispatched)
        return [p.to_dict() if hasattr(p, "to_dict") else (p if isinstance(p, dict) else {}) for p in all_plans]

    def _get_queue_depth(self) -> int:
        result = self._safe_call(self._coord, "queue_depth")
        return result if isinstance(result, int) else 0

    def _get_approval_count(self) -> int:
        result = self._safe_call(self._coord, "pending_approval_count")
        return result if isinstance(result, int) else 0

    def _get_active_sessions(self) -> list[dict[str, Any]]:
        result = self._safe_call(self._sessions, "list_active_sessions")
        if result is None:
            return []
        if isinstance(result, list):
            return [s.to_dict() if hasattr(s, "to_dict") else (s if isinstance(s, dict) else {}) for s in result]
        return []

    def _get_online_devices(self) -> list[dict[str, Any]]:
        result = self._safe_call(self._presence, "online_devices")
        if result is None:
            result = self._safe_call(self._presence, "list_devices")
        if result is None:
            return []
        if isinstance(result, list):
            return [d.to_dict() if hasattr(d, "to_dict") else (d if isinstance(d, dict) else {}) for d in result]
        return []

    def _get_blocked_work(self) -> list[dict[str, Any]]:
        result = self._safe_call(self._portfolio, "blocked_work")
        if result is None:
            result = self._safe_call(self._portfolio, "get_blocked")
        if result is None:
            return []
        if isinstance(result, list):
            return [w.to_dict() if hasattr(w, "to_dict") else (w if isinstance(w, dict) else {}) for w in result]
        return []

    def _get_work_velocity(self) -> dict[str, Any]:
        result = self._safe_call(self._portfolio, "velocity")
        if result is None:
            result = self._safe_call(self._portfolio, "get_velocity")
        if isinstance(result, dict):
            return result
        if result and hasattr(result, "to_dict"):
            return result.to_dict()
        return {}

    def _get_capacity_numbers(self, nodes: list[dict[str, Any]]) -> tuple[int, int]:
        total = 0
        used = 0
        for n in nodes:
            total += n.get("max_workers", 0)
            used += n.get("active_workers", 0)
        return total, used
