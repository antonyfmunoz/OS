"""Environment reconciliation — continuous drift correction.

Compares the actual execution environment (Docker containers, tmux
sessions, model endpoints) against the RuntimeGraph and corrects
drift: removes dead runtimes, discovers new ones, updates status.

Designed to run as an AutonomousTick stage.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from substrate.organism.event_spine import EventDomain, EventSpine
from substrate.organism.runtime_graph import AvailabilityStatus, RuntimeGraph

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationReport:
    """Result of a single reconciliation cycle."""

    timestamp: float = 0.0
    discovered: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    status_changes: list[dict[str, Any]] = field(default_factory=list)
    elapsed_ms: float = 0.0

    @property
    def had_changes(self) -> bool:
        return bool(self.discovered or self.removed or self.status_changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "discovered": self.discovered,
            "removed": self.removed,
            "status_changes": self.status_changes,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "had_changes": self.had_changes,
        }


class EnvironmentReconciler:
    """Reconciles RuntimeGraph against actual environment state.

    Each reconcile() call:
      1. Probes all registered runtimes for availability
      2. Discovers new Docker containers / tmux sessions
      3. Removes stale runtimes that no longer exist
      4. Emits events for all changes
    """

    def __init__(
        self,
        graph: RuntimeGraph,
        spine: EventSpine | None = None,
    ) -> None:
        self._graph = graph
        self._spine = spine
        self._last_report: ReconciliationReport | None = None
        self._reconcile_count = 0

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        if self._spine is not None:
            self._spine.emit(
                EventDomain.RUNTIME,
                event_type,
                "environment_reconciler",
                data,
            )

    def reconcile(self) -> ReconciliationReport:
        """Run one reconciliation cycle."""
        start = time.monotonic_ns()
        report = ReconciliationReport(timestamp=time.time())
        self._reconcile_count += 1

        old_statuses = {n.runtime_id: n.status for n in self._graph.all_nodes()}
        new_statuses = self._graph.refresh_availability()

        for rid, new_status in new_statuses.items():
            old = old_statuses.get(rid)
            if old is not None and old != new_status:
                report.status_changes.append(
                    {
                        "runtime_id": rid,
                        "old_status": old.value,
                        "new_status": new_status.value,
                    }
                )

        from substrate.organism.runtime_adapters import (
            _discover_docker_containers,
            _discover_tmux_sessions,
        )
        from substrate.organism.runtime_graph import CostProfile

        for docker_adapter in _discover_docker_containers():
            if self._graph.get(docker_adapter.runtime_id) is None:
                self._graph.register(
                    docker_adapter.runtime_id,
                    docker_adapter.runtime_class,
                    docker_adapter.capabilities,
                    cost=CostProfile(),
                    adapter=docker_adapter,
                )
                self._graph.update_status(
                    docker_adapter.runtime_id,
                    AvailabilityStatus.AVAILABLE,
                )
                report.discovered.append(docker_adapter.runtime_id)

        for tmux_adapter in _discover_tmux_sessions():
            if self._graph.get(tmux_adapter.runtime_id) is None:
                self._graph.register(
                    tmux_adapter.runtime_id,
                    tmux_adapter.runtime_class,
                    tmux_adapter.capabilities,
                    cost=CostProfile(),
                    adapter=tmux_adapter,
                )
                self._graph.update_status(
                    tmux_adapter.runtime_id,
                    AvailabilityStatus.AVAILABLE,
                )
                report.discovered.append(tmux_adapter.runtime_id)

        stale_ids = []
        for node in self._graph.all_nodes():
            if node.status == AvailabilityStatus.UNAVAILABLE:
                is_dynamic = node.runtime_id.startswith("docker:") or node.runtime_id.startswith(
                    "tmux:"
                )
                if is_dynamic and node.adapter is not None:
                    try:
                        if not node.adapter.check_available():
                            stale_ids.append(node.runtime_id)
                    except Exception:
                        stale_ids.append(node.runtime_id)

        for rid in stale_ids:
            self._graph.unregister(rid)
            report.removed.append(rid)

        elapsed_ms = (time.monotonic_ns() - start) / 1_000_000
        report.elapsed_ms = elapsed_ms

        if report.had_changes:
            self._emit("environment_reconciled", report.to_dict())
            logger.info(
                "reconciliation: +%d discovered, -%d removed, %d status changes (%.1fms)",
                len(report.discovered),
                len(report.removed),
                len(report.status_changes),
                elapsed_ms,
            )

        self._last_report = report
        return report

    def reconcile_tick(self) -> bool:
        """Tick-compatible wrapper — returns True if changes occurred."""
        report = self.reconcile()
        return report.had_changes

    @property
    def last_report(self) -> ReconciliationReport | None:
        return self._last_report

    @property
    def reconcile_count(self) -> int:
        return self._reconcile_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "reconcile_count": self._reconcile_count,
            "last_report": self._last_report.to_dict() if self._last_report else None,
        }
