"""Node heartbeat protocol — temporal liveness tracking for distributed nodes.

Records heartbeats from nodes and determines staleness. Supports
deterministic time injection for testing. Pure in-memory store.

No imports from umh/cells, umh/adapters, subprocess, or shell.
No network calls — heartbeats are received, not fetched.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any


@unique
class HeartbeatStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class NodeHeartbeat:
    """Single heartbeat from a node."""

    node_id: str
    timestamp: str
    status: HeartbeatStatus = HeartbeatStatus.OK
    telemetry: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    runtime_version: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "telemetry": self.telemetry,
            "capabilities": self.capabilities,
            "runtime_version": self.runtime_version,
            "metadata": self.metadata,
        }


_DEFAULT_STALE_THRESHOLD_S = 60.0


class HeartbeatMonitor:
    """Tracks heartbeats and determines node liveness.

    Deterministic: accepts `now` parameter for testable time injection.
    """

    def __init__(self, stale_threshold_s: float = _DEFAULT_STALE_THRESHOLD_S) -> None:
        self._lock = threading.Lock()
        self._latest: dict[str, NodeHeartbeat] = {}
        self._stale_threshold_s = stale_threshold_s

    @property
    def stale_threshold_s(self) -> float:
        return self._stale_threshold_s

    def record_heartbeat(self, heartbeat: NodeHeartbeat) -> None:
        with self._lock:
            self._latest[heartbeat.node_id] = heartbeat

    def get_last_heartbeat(self, node_id: str) -> NodeHeartbeat | None:
        with self._lock:
            return self._latest.get(node_id)

    def is_stale(self, node_id: str, *, now: datetime | None = None) -> bool:
        with self._lock:
            hb = self._latest.get(node_id)
        if hb is None:
            return True
        return self._age_seconds(hb, now) > self._stale_threshold_s

    def list_stale_nodes(self, *, now: datetime | None = None) -> list[str]:
        with self._lock:
            all_hbs = list(self._latest.items())
        return [
            node_id
            for node_id, hb in all_hbs
            if self._age_seconds(hb, now) > self._stale_threshold_s
        ]

    def node_status(self, node_id: str, *, now: datetime | None = None) -> HeartbeatStatus:
        with self._lock:
            hb = self._latest.get(node_id)
        if hb is None:
            return HeartbeatStatus.UNKNOWN
        if self._age_seconds(hb, now) > self._stale_threshold_s:
            return HeartbeatStatus.OFFLINE
        if hb.status == HeartbeatStatus.DEGRADED:
            return HeartbeatStatus.DEGRADED
        return HeartbeatStatus.OK

    def list_all_nodes(self) -> list[str]:
        with self._lock:
            return list(self._latest.keys())

    def clear(self) -> None:
        with self._lock:
            self._latest.clear()

    @staticmethod
    def _age_seconds(hb: NodeHeartbeat, now: datetime | None = None) -> float:
        ref = now or datetime.now(timezone.utc)
        try:
            ts = datetime.fromisoformat(hb.timestamp)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return (ref - ts).total_seconds()
        except (ValueError, TypeError):
            return float("inf")
