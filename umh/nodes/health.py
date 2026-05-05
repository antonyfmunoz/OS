"""Node health state machine — tracks node health transitions.

State machine:
  UNKNOWN → HEALTHY (first heartbeat OK)
  HEALTHY → DEGRADED (heartbeat DEGRADED or high load)
  HEALTHY → OFFLINE (stale/missing beyond threshold)
  DEGRADED → HEALTHY (heartbeat OK + recent)
  DEGRADED → OFFLINE (stale)
  OFFLINE → RECOVERING (new heartbeat received)
  RECOVERING → HEALTHY (next OK heartbeat)

Deterministic and testable. No network calls.
No imports from umh/cells, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.nodes.heartbeat import HeartbeatStatus, NodeHeartbeat


@unique
class NodeHealthState(str, Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    RECOVERING = "recovering"


@dataclass
class NodeHealth:
    """Current health record for a single node."""

    node_id: str
    state: NodeHealthState = NodeHealthState.UNKNOWN
    last_seen: str = ""
    failure_count: int = 0
    recovery_count: int = 0
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "state": self.state.value,
            "last_seen": self.last_seen,
            "failure_count": self.failure_count,
            "recovery_count": self.recovery_count,
            "reason": self.reason,
            "metadata": self.metadata,
        }


_HIGH_LOAD_THRESHOLD = 0.85


class NodeHealthManager:
    """Manages health state transitions for all known nodes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._health: dict[str, NodeHealth] = {}

    def update_from_heartbeat(self, heartbeat: NodeHeartbeat) -> NodeHealthState:
        """Process a heartbeat and transition the node's health state."""
        with self._lock:
            health = self._health.get(heartbeat.node_id)
            if health is None:
                health = NodeHealth(node_id=heartbeat.node_id)
                self._health[heartbeat.node_id] = health

            health.last_seen = heartbeat.timestamp
            prev_state = health.state

            if heartbeat.status == HeartbeatStatus.DEGRADED:
                health.state = NodeHealthState.DEGRADED
                health.reason = "heartbeat reported degraded"
            elif heartbeat.status == HeartbeatStatus.OK:
                cpu = heartbeat.telemetry.get("cpu_percent", 0.0)
                mem = heartbeat.telemetry.get("memory_percent", 0.0)
                load = max(cpu / 100.0, mem / 100.0) if cpu or mem else 0.0

                if load > _HIGH_LOAD_THRESHOLD:
                    health.state = NodeHealthState.DEGRADED
                    health.reason = f"high load ({load:.2f})"
                elif prev_state == NodeHealthState.OFFLINE:
                    health.state = NodeHealthState.RECOVERING
                    health.recovery_count += 1
                    health.reason = "heartbeat received after offline"
                elif prev_state == NodeHealthState.RECOVERING:
                    health.state = NodeHealthState.HEALTHY
                    health.reason = "recovered"
                else:
                    health.state = NodeHealthState.HEALTHY
                    health.reason = ""
            elif heartbeat.status == HeartbeatStatus.OFFLINE:
                health.state = NodeHealthState.OFFLINE
                health.failure_count += 1
                health.reason = "heartbeat reported offline"

            return health.state

    def mark_failure(self, node_id: str, reason: str = "") -> None:
        with self._lock:
            health = self._health.get(node_id)
            if health is None:
                health = NodeHealth(node_id=node_id)
                self._health[node_id] = health
            health.state = NodeHealthState.OFFLINE
            health.failure_count += 1
            health.reason = reason or "marked failed"

    def mark_recovered(self, node_id: str) -> None:
        with self._lock:
            health = self._health.get(node_id)
            if health is None:
                health = NodeHealth(node_id=node_id)
                self._health[node_id] = health
            if health.state in (NodeHealthState.OFFLINE, NodeHealthState.UNKNOWN):
                health.state = NodeHealthState.RECOVERING
                health.recovery_count += 1
                health.reason = "manually marked recovered"

    def mark_stale(self, node_id: str) -> None:
        with self._lock:
            health = self._health.get(node_id)
            if health is None:
                health = NodeHealth(node_id=node_id)
                self._health[node_id] = health
            if health.state not in (NodeHealthState.OFFLINE,):
                health.state = NodeHealthState.OFFLINE
                health.failure_count += 1
                health.reason = "heartbeat stale"

    def get_health(self, node_id: str) -> NodeHealth | None:
        with self._lock:
            return self._health.get(node_id)

    def list_healthy(self) -> list[NodeHealth]:
        with self._lock:
            return [h for h in self._health.values() if h.state == NodeHealthState.HEALTHY]

    def list_available(self) -> list[NodeHealth]:
        """Nodes that can accept work: HEALTHY or DEGRADED."""
        with self._lock:
            return [
                h
                for h in self._health.values()
                if h.state in (NodeHealthState.HEALTHY, NodeHealthState.DEGRADED)
            ]

    def list_all(self) -> list[NodeHealth]:
        with self._lock:
            return list(self._health.values())

    def clear(self) -> None:
        with self._lock:
            self._health.clear()
