"""Node registry — tracks connected mesh nodes and their state."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NodeCapability:
    name: str
    category: str
    risk_class: str
    max_risk_class: str


@dataclass
class ConnectedNode:
    node_id: str
    hostname: str
    os: str
    os_version: str
    capabilities: list[NodeCapability]
    daemon_version: str
    tailscale_ip: str
    ws: Any
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: float = field(default_factory=time.monotonic)
    status: str = "connected"
    latest_metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def connected_at_iso(self) -> str:
        return self.connected_at.isoformat()

    @property
    def last_heartbeat_iso(self) -> str:
        age = time.monotonic() - self.last_heartbeat
        dt = datetime.now(timezone.utc)
        return dt.isoformat()

    def update_heartbeat(self, metrics: dict[str, Any] | None = None) -> None:
        self.last_heartbeat = time.monotonic()
        self.status = "connected"
        if metrics:
            self.latest_metrics = metrics

    def heartbeat_age_s(self) -> float:
        return time.monotonic() - self.last_heartbeat

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "name": self.hostname,
            "os": self.os,
            "os_version": self.os_version,
            "status": self.status,
            "capabilities": [c.name for c in self.capabilities],
            "metrics": self.latest_metrics,
            "last_heartbeat": self.last_heartbeat_iso,
            "tailscale_ip": self.tailscale_ip,
            "connected_at": self.connected_at_iso,
            "daemon_version": self.daemon_version,
        }


class NodeRegistry:
    """Thread-safe registry of connected mesh nodes."""

    def __init__(self, heartbeat_timeout_s: float = 90.0) -> None:
        self._nodes: dict[str, ConnectedNode] = {}
        self._lock = threading.Lock()
        self._heartbeat_timeout_s = heartbeat_timeout_s

    def add(self, node: ConnectedNode) -> None:
        with self._lock:
            self._nodes[node.node_id] = node
        logger.info("node registered: %s (%s %s)", node.node_id, node.os, node.hostname)

    def remove(self, node_id: str) -> ConnectedNode | None:
        with self._lock:
            node = self._nodes.pop(node_id, None)
        if node:
            logger.info("node removed: %s", node_id)
        return node

    def get(self, node_id: str) -> ConnectedNode | None:
        with self._lock:
            return self._nodes.get(node_id)

    def all_nodes(self) -> list[ConnectedNode]:
        with self._lock:
            return list(self._nodes.values())

    def update_heartbeat(self, node_id: str, metrics: dict[str, Any] | None = None) -> bool:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.update_heartbeat(metrics)
            return True

    def stale_nodes(self) -> list[str]:
        """Return node_ids that have exceeded the heartbeat timeout."""
        now = time.monotonic()
        with self._lock:
            return [
                nid
                for nid, node in self._nodes.items()
                if (now - node.last_heartbeat) > self._heartbeat_timeout_s
            ]

    def node_count(self) -> int:
        with self._lock:
            return len(self._nodes)
