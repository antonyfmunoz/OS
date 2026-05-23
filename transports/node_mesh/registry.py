"""Node registry — tracks connected mesh nodes and their state."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from substrate.integrations.node_mesh.types import ConnectedNode, NodeCapability  # noqa: F401 — re-exported

logger = logging.getLogger(__name__)


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
