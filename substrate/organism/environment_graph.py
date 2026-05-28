"""Environment graph — continuously updated operational world-state.

The EnvironmentGraph is the organism's canonical model of its own
execution environment. It aggregates state from RuntimeGraph,
workcells, containers, tmux sessions, API surfaces, and system
metrics into a single queryable topology.

Topology snapshots are append-only for audit trail. Diff detection
identifies what changed between snapshots, enabling reconciliation
events and cockpit live updates.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_MAX_SNAPSHOTS = 100


@dataclass
class TopologyNode:
    """A node in the operational topology."""

    node_id: str
    node_type: str  # runtime | workcell | container | tmux | api | daemon | model
    status: str  # available | unavailable | degraded | unknown
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    last_seen: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "status": self.status,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
            "last_seen": self.last_seen,
        }


@dataclass
class TopologySnapshot:
    """A point-in-time snapshot of the entire operational topology."""

    timestamp: float = 0.0
    nodes: list[TopologyNode] = field(default_factory=list)
    system_metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def available_count(self) -> int:
        return sum(1 for n in self.nodes if n.status == "available")

    def node_ids(self) -> set[str]:
        return {n.node_id for n in self.nodes}

    def to_dict(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for n in self.nodes:
            by_type[n.node_type] = by_type.get(n.node_type, 0) + 1

        return {
            "timestamp": self.timestamp,
            "total_nodes": self.node_count,
            "available_nodes": self.available_count,
            "by_type": by_type,
            "nodes": [n.to_dict() for n in self.nodes],
            "system_metrics": self.system_metrics,
        }


@dataclass
class TopologyDiff:
    """Changes between two topology snapshots."""

    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    status_changes: list[dict[str, str]] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.status_changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "added": self.added,
            "removed": self.removed,
            "status_changes": self.status_changes,
            "has_changes": self.has_changes,
        }


class EnvironmentGraph:
    """Canonical operational topology — the organism's world-model.

    Aggregates runtime, workcell, container, and system state into
    append-only topology snapshots. Diffs between snapshots drive
    reconciliation and cockpit updates.
    """

    def __init__(self) -> None:
        self._snapshots: deque[TopologySnapshot] = deque(maxlen=_MAX_SNAPSHOTS)
        self._snapshot_count = 0

    def capture(
        self,
        graph: Any | None = None,
        workcells: list[dict[str, Any]] | None = None,
        system_metrics: dict[str, Any] | None = None,
    ) -> TopologySnapshot:
        """Capture a new topology snapshot from current state."""
        nodes: list[TopologyNode] = []
        now = time.time()

        if graph is not None:
            for runtime_node in graph.all_nodes():
                nodes.append(
                    TopologyNode(
                        node_id=runtime_node.runtime_id,
                        node_type=runtime_node.runtime_class.value,
                        status=runtime_node.status.value,
                        capabilities=sorted(c.value for c in runtime_node.capabilities),
                        metadata={
                            "score": round(runtime_node.score(), 4),
                            "reliability": round(runtime_node.reliability.success_rate, 3),
                            "avg_latency_ms": round(runtime_node.reliability.avg_latency_ms, 1),
                        },
                        last_seen=runtime_node.last_heartbeat or now,
                    )
                )

        for wc in workcells or []:
            nodes.append(
                TopologyNode(
                    node_id=f"workcell:{wc.get('workcell_id', 'unknown')}",
                    node_type="workcell",
                    status="available" if wc.get("alive", False) else "unavailable",
                    capabilities=[wc.get("role", "executor")],
                    metadata={
                        "generation": wc.get("generation", 0),
                        "messages_processed": wc.get("messages_processed", 0),
                        "inbox_depth": wc.get("inbox_depth", 0),
                    },
                    last_seen=now,
                )
            )

        metrics = system_metrics or {}
        if not metrics:
            try:
                import psutil

                cpu = psutil.cpu_percent(interval=0)
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage("/")
                metrics = {
                    "cpu_percent": cpu,
                    "memory_percent": mem.percent,
                    "memory_available_mb": round(mem.available / 1024 / 1024),
                    "disk_percent": disk.percent,
                    "load_avg": list(os.getloadavg()),
                }
            except Exception:
                pass

        snapshot = TopologySnapshot(
            timestamp=now,
            nodes=nodes,
            system_metrics=metrics,
        )

        self._snapshots.append(snapshot)
        self._snapshot_count += 1
        return snapshot

    def latest(self) -> TopologySnapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def diff(
        self,
        old: TopologySnapshot | None = None,
        new: TopologySnapshot | None = None,
    ) -> TopologyDiff:
        """Compute diff between two snapshots (defaults to last two)."""
        if old is None or new is None:
            if len(self._snapshots) < 2:
                return TopologyDiff()
            old = self._snapshots[-2]
            new = self._snapshots[-1]

        old_ids = old.node_ids()
        new_ids = new.node_ids()
        old_status = {n.node_id: n.status for n in old.nodes}
        new_status = {n.node_id: n.status for n in new.nodes}

        diff = TopologyDiff(
            added=sorted(new_ids - old_ids),
            removed=sorted(old_ids - new_ids),
        )

        for nid in old_ids & new_ids:
            if old_status.get(nid) != new_status.get(nid):
                diff.status_changes.append(
                    {
                        "node_id": nid,
                        "old_status": old_status.get(nid, "unknown"),
                        "new_status": new_status.get(nid, "unknown"),
                    }
                )

        return diff

    def recent_snapshots(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return recent snapshots as dicts (for API consumption)."""
        snaps = list(self._snapshots)
        return [s.to_dict() for s in snaps[-limit:]]

    def to_dict(self) -> dict[str, Any]:
        latest = self.latest()
        last_diff = self.diff()
        return {
            "snapshot_count": self._snapshot_count,
            "latest": latest.to_dict() if latest else None,
            "last_diff": last_diff.to_dict() if last_diff.has_changes else None,
        }
