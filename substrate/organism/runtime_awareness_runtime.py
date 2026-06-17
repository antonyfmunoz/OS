"""Runtime Awareness Runtime — unified view of active system state.

Facade unifying:
- RuntimeStateRegistry (worktrees, repos, processes, containers)
- ExecutionCoordinator (active WorkPackets, queue state)
- WorkGraph (dependency graph, blocker detection)

One snapshot() call returns "what is running, what is blocked, what is executing."

Read-only observation pattern. Instance-agnostic.

Campaign 6.3. UMH substrate layer.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


@dataclass
class RuntimeAwarenessSnapshot:
    worktrees: list[dict[str, Any]] = field(default_factory=list)
    repositories: list[dict[str, Any]] = field(default_factory=list)
    processes: list[dict[str, Any]] = field(default_factory=list)
    containers: list[dict[str, Any]] = field(default_factory=list)
    active_executions: list[dict[str, Any]] = field(default_factory=list)
    active_work_packets: list[dict[str, Any]] = field(default_factory=list)
    blocked_work: list[dict[str, Any]] = field(default_factory=list)
    detected_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Runtime Awareness Runtime ────────────────────────────────────────────


class RuntimeAwarenessRuntime:
    """Unified view of active system state.

    Pure facade — delegates to existing subsystems, unifies the view.
    Never mutates, only observes.
    """

    def __init__(
        self,
        runtime_state_registry: Any = None,
        execution_coordinator: Any = None,
        work_graph: Any = None,
    ) -> None:
        self._state_registry = runtime_state_registry
        self._execution = execution_coordinator
        self._work_graph = work_graph

    def snapshot(self) -> RuntimeAwarenessSnapshot:
        """Unified point-in-time view from all subsystems."""
        now = time.time()

        return RuntimeAwarenessSnapshot(
            worktrees=self._collect_worktrees(),
            repositories=self._collect_repositories(),
            processes=self._collect_processes(),
            containers=self._collect_containers(),
            active_executions=self._collect_active_executions(),
            active_work_packets=self._collect_active_work_packets(),
            blocked_work=self._collect_blocked_work(),
            detected_at=now,
        )

    def active_work(self) -> list[dict[str, Any]]:
        """Currently executing WorkPackets."""
        return self._collect_active_work_packets()

    def blocked_work(self) -> list[dict[str, Any]]:
        """Blocked work nodes with blocker details."""
        return self._collect_blocked_work()

    def environment_health(self) -> dict[str, Any]:
        """Process and container health summary."""
        processes = self._collect_processes()
        containers = self._collect_containers()

        healthy_containers = sum(
            1 for c in containers
            if c.get("status", "").lower() in ("running", "up", "healthy")
        )
        total_containers = len(containers)

        return {
            "process_count": len(processes),
            "container_count": total_containers,
            "healthy_containers": healthy_containers,
            "unhealthy_containers": total_containers - healthy_containers,
            "active_executions": len(self._collect_active_executions()),
            "blocked_count": len(self._collect_blocked_work()),
        }

    # ── Collectors ────────────────────────────────────────────────────

    def _collect_worktrees(self) -> list[dict[str, Any]]:
        if self._state_registry is None:
            return []
        snap = self._get_latest_snapshot()
        if snap is None:
            return []
        worktrees = getattr(snap, "worktrees", [])
        return [self._to_dict_safe(w) for w in worktrees]

    def _collect_repositories(self) -> list[dict[str, Any]]:
        if self._state_registry is None:
            return []
        snap = self._get_latest_snapshot()
        if snap is None:
            return []
        repos = getattr(snap, "repositories", []) or getattr(snap, "git_repos", [])
        return [self._to_dict_safe(r) for r in repos]

    def _collect_processes(self) -> list[dict[str, Any]]:
        if self._state_registry is None:
            return []
        snap = self._get_latest_snapshot()
        if snap is None:
            return []
        procs = getattr(snap, "processes", [])
        return [self._to_dict_safe(p) for p in procs]

    def _collect_containers(self) -> list[dict[str, Any]]:
        if self._state_registry is None:
            return []
        snap = self._get_latest_snapshot()
        if snap is None:
            return []
        containers = getattr(snap, "containers", [])
        return [self._to_dict_safe(c) for c in containers]

    def _collect_active_executions(self) -> list[dict[str, Any]]:
        if self._state_registry is None:
            return []
        snap = self._get_latest_snapshot()
        if snap is None:
            return []
        executions = getattr(snap, "executions", [])
        return [
            self._to_dict_safe(e) for e in executions
            if getattr(e, "status", "") in ("running", "executing", "in_progress")
        ]

    def _collect_active_work_packets(self) -> list[dict[str, Any]]:
        if self._execution is None:
            return []

        packets = []
        if hasattr(self._execution, "list_active"):
            packets = self._execution.list_active()
        elif hasattr(self._execution, "list_packets"):
            all_packets = self._execution.list_packets()
            packets = [
                p for p in all_packets
                if getattr(p, "status", "") in ("executing", "in_progress", "running", "approved")
            ]
        elif hasattr(self._execution, "_queue"):
            packets = [
                p for p in self._execution._queue
                if getattr(p, "status", "") in ("executing", "in_progress", "running", "approved")
            ]

        return [self._to_dict_safe(p) for p in packets]

    def _collect_blocked_work(self) -> list[dict[str, Any]]:
        if self._work_graph is None:
            return []

        blocked = []
        if hasattr(self._work_graph, "find_blocked"):
            blocked = self._work_graph.find_blocked()
        elif hasattr(self._work_graph, "blocked_nodes"):
            blocked = self._work_graph.blocked_nodes()
        elif hasattr(self._work_graph, "_nodes"):
            blocked = [
                n for n in self._work_graph._nodes.values()
                if getattr(n, "status", "") == "blocked"
            ]

        return [self._to_dict_safe(b) for b in blocked]

    # ── Helpers ───────────────────────────────────────────────────────

    def _get_latest_snapshot(self) -> Any:
        if hasattr(self._state_registry, "latest_snapshot"):
            return self._state_registry.latest_snapshot()
        if hasattr(self._state_registry, "_snapshots"):
            snaps = self._state_registry._snapshots
            if snaps:
                return snaps[-1] if isinstance(snaps, list) else None
        return None

    @staticmethod
    def _to_dict_safe(obj: Any) -> dict[str, Any]:
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "__dataclass_fields__"):
            return asdict(obj)
        return {"repr": str(obj)}
