"""Organism Observability — unified dashboard snapshot.

Aggregates state from all organism subsystems into a single
cockpit-ready snapshot:
  - Active objectives and work units
  - Runtime health and selection patterns
  - Workcell status and throughput
  - Failures, retries, bottlenecks
  - System mode (from homeostasis)

Designed as a read-only aggregation layer. Does not own state;
it reads from coordinator, runtime graph, supervisor, workcell
daemon, and homeostasis engine.

UMH substrate subsystem.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from substrate.organism.coordinator import (
    ObjectiveStatus,
    OrganismCoordinator,
    WorkUnitStatus,
)
from substrate.organism.homeostasis import HomeostasisEngine, SystemMode
from substrate.organism.runtime_graph import AvailabilityStatus, RuntimeGraph
from substrate.organism.runtime_supervisor import RuntimeSupervisor, SupervisedHealth
from substrate.organism.workcell_daemon import WorkcellDaemon

logger = logging.getLogger(__name__)


@dataclass
class BottleneckReport:
    """Identifies a system bottleneck."""

    subsystem: str
    description: str
    severity: str = "low"
    metric_value: float = 0.0
    threshold: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "subsystem": self.subsystem,
            "description": self.description,
            "severity": self.severity,
            "metric_value": round(self.metric_value, 3),
            "threshold": round(self.threshold, 3),
        }


@dataclass
class OrganismSnapshot:
    """Point-in-time snapshot of the entire organism state."""

    timestamp: float = 0.0
    system_mode: str = "unknown"

    objectives_active: int = 0
    objectives_completed: int = 0
    objectives_failed: int = 0

    work_units_pending: int = 0
    work_units_running: int = 0
    work_units_completed: int = 0
    work_units_failed: int = 0
    work_units_blocked: int = 0

    runtimes_total: int = 0
    runtimes_available: int = 0
    runtimes_degraded: int = 0
    runtimes_unavailable: int = 0

    supervised_alive: int = 0
    supervised_dead: int = 0
    supervised_paused: int = 0

    workcells_active: int = 0
    workcells_idle: int = 0
    workcells_processing: int = 0
    daemon_messages_processed: int = 0
    daemon_messages_failed: int = 0
    daemon_throughput_per_min: float = 0.0

    bottlenecks: list[BottleneckReport] = field(default_factory=list)
    runtime_rankings: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "system_mode": self.system_mode,
            "objectives": {
                "active": self.objectives_active,
                "completed": self.objectives_completed,
                "failed": self.objectives_failed,
            },
            "work_units": {
                "pending": self.work_units_pending,
                "running": self.work_units_running,
                "completed": self.work_units_completed,
                "failed": self.work_units_failed,
                "blocked": self.work_units_blocked,
            },
            "runtimes": {
                "total": self.runtimes_total,
                "available": self.runtimes_available,
                "degraded": self.runtimes_degraded,
                "unavailable": self.runtimes_unavailable,
            },
            "supervision": {
                "alive": self.supervised_alive,
                "dead": self.supervised_dead,
                "paused": self.supervised_paused,
            },
            "workcells": {
                "active": self.workcells_active,
                "idle": self.workcells_idle,
                "processing": self.workcells_processing,
            },
            "daemon": {
                "messages_processed": self.daemon_messages_processed,
                "messages_failed": self.daemon_messages_failed,
                "throughput_per_min": round(self.daemon_throughput_per_min, 2),
            },
            "bottlenecks": [b.to_dict() for b in self.bottlenecks],
            "runtime_rankings": self.runtime_rankings,
        }


class OrganismObserver:
    """Read-only aggregation layer that produces cockpit snapshots.

    Takes references to subsystems at construction time. Call snapshot()
    to get a point-in-time view of the entire organism.
    """

    def __init__(
        self,
        coordinator: OrganismCoordinator | None = None,
        graph: RuntimeGraph | None = None,
        supervisor: RuntimeSupervisor | None = None,
        daemon: WorkcellDaemon | None = None,
        homeostasis: HomeostasisEngine | None = None,
    ) -> None:
        self._coordinator = coordinator
        self._graph = graph
        self._supervisor = supervisor
        self._daemon = daemon
        self._homeostasis = homeostasis
        self._snapshots: list[OrganismSnapshot] = []
        self._max_history = 100

    def snapshot(self) -> OrganismSnapshot:
        """Produce a point-in-time snapshot of the organism."""
        snap = OrganismSnapshot(timestamp=time.time())

        if self._homeostasis:
            snap.system_mode = self._homeostasis.current_mode.value

        self._collect_objectives(snap)
        self._collect_runtimes(snap)
        self._collect_supervision(snap)
        self._collect_workcells(snap)
        self._detect_bottlenecks(snap)
        self._rank_runtimes(snap)

        self._snapshots.append(snap)
        if len(self._snapshots) > self._max_history:
            self._snapshots = self._snapshots[-self._max_history:]

        return snap

    def _collect_objectives(self, snap: OrganismSnapshot) -> None:
        if not self._coordinator:
            return

        for obj_dict in self._coordinator.list_objectives():
            status = obj_dict.get("status", "")
            if status == ObjectiveStatus.EXECUTING.value:
                snap.objectives_active += 1
            elif status == ObjectiveStatus.COMPLETED.value:
                snap.objectives_completed += 1
            elif status in {ObjectiveStatus.FAILED.value, ObjectiveStatus.PARTIAL.value}:
                snap.objectives_failed += 1

        for obj in self._coordinator._objectives.values():
            for wu in obj.work_units:
                if wu.status == WorkUnitStatus.PENDING:
                    snap.work_units_pending += 1
                elif wu.status == WorkUnitStatus.RUNNING:
                    snap.work_units_running += 1
                elif wu.status == WorkUnitStatus.COMPLETED:
                    snap.work_units_completed += 1
                elif wu.status == WorkUnitStatus.FAILED:
                    snap.work_units_failed += 1
                elif wu.status == WorkUnitStatus.BLOCKED:
                    snap.work_units_blocked += 1

    def _collect_runtimes(self, snap: OrganismSnapshot) -> None:
        if not self._graph:
            return

        for node in self._graph.all_nodes():
            snap.runtimes_total += 1
            if node.status == AvailabilityStatus.AVAILABLE:
                snap.runtimes_available += 1
            elif node.status == AvailabilityStatus.DEGRADED:
                snap.runtimes_degraded += 1
            else:
                snap.runtimes_unavailable += 1

    def _collect_supervision(self, snap: OrganismSnapshot) -> None:
        if not self._supervisor:
            return

        sup_dict = self._supervisor.to_dict()
        snap.supervised_alive = sup_dict.get("alive", 0)
        snap.supervised_dead = sup_dict.get("dead", 0)
        snap.supervised_paused = sup_dict.get("paused", 0)

    def _collect_workcells(self, snap: OrganismSnapshot) -> None:
        if not self._daemon:
            return

        daemon_dict = self._daemon.to_dict()
        stats = daemon_dict.get("stats", {})
        snap.daemon_messages_processed = stats.get("messages_processed", 0)
        snap.daemon_messages_failed = stats.get("messages_failed", 0)
        snap.daemon_throughput_per_min = stats.get("throughput_per_min", 0.0)

        for wc_dict in daemon_dict.get("workcells", {}).values():
            snap.workcells_active += 1
            status = wc_dict.get("status", "")
            if status == "idle":
                snap.workcells_idle += 1
            elif status == "processing":
                snap.workcells_processing += 1

    def _detect_bottlenecks(self, snap: OrganismSnapshot) -> None:
        if snap.runtimes_available == 0 and snap.runtimes_total > 0:
            snap.bottlenecks.append(
                BottleneckReport(
                    subsystem="runtime_graph",
                    description="No runtimes available — all execution blocked",
                    severity="critical",
                    metric_value=0,
                    threshold=1,
                )
            )

        if snap.work_units_blocked > 0 and snap.work_units_running == 0:
            snap.bottlenecks.append(
                BottleneckReport(
                    subsystem="coordinator",
                    description=f"{snap.work_units_blocked} blocked work units with nothing running",
                    severity="high",
                    metric_value=snap.work_units_blocked,
                )
            )

        if snap.supervised_dead > 0:
            snap.bottlenecks.append(
                BottleneckReport(
                    subsystem="supervisor",
                    description=f"{snap.supervised_dead} supervised runtimes are dead",
                    severity="high",
                    metric_value=snap.supervised_dead,
                )
            )

        fail_total = snap.daemon_messages_processed + snap.daemon_messages_failed
        if fail_total > 10:
            fail_rate = snap.daemon_messages_failed / fail_total
            if fail_rate > 0.3:
                snap.bottlenecks.append(
                    BottleneckReport(
                        subsystem="workcell_daemon",
                        description=f"High failure rate: {fail_rate:.0%}",
                        severity="high",
                        metric_value=fail_rate,
                        threshold=0.3,
                    )
                )

    def _rank_runtimes(self, snap: OrganismSnapshot) -> None:
        if not self._graph:
            return

        nodes = self._graph.all_nodes()
        ranked = sorted(nodes, key=lambda n: n.score(), reverse=True)
        snap.runtime_rankings = [
            {
                "runtime_id": n.runtime_id,
                "score": round(n.score(), 4),
                "status": n.status.value,
                "success_rate": round(n.reliability.success_rate, 3),
                "avg_latency_ms": round(n.reliability.avg_latency_ms, 1),
            }
            for n in ranked[:10]
        ]

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent snapshots for trend analysis."""
        return [s.to_dict() for s in self._snapshots[-limit:]]

    def trend(self, metric: str, window: int = 10) -> list[float]:
        """Extract a metric trend from recent snapshots.

        Supports dot-notation: 'work_units.completed', 'runtimes.available'.
        """
        values: list[float] = []
        for snap in self._snapshots[-window:]:
            d = snap.to_dict()
            parts = metric.split(".")
            obj: Any = d
            for part in parts:
                if isinstance(obj, dict):
                    obj = obj.get(part, 0)
                else:
                    obj = 0
                    break
            values.append(float(obj) if isinstance(obj, (int, float)) else 0.0)
        return values
