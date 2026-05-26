"""Node registry — tracks connected mesh nodes and their state."""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

from transports.node_mesh.integration.types import ConnectedNode, NodeCapability  # noqa: F401 — re-exported

_SNAPSHOT_PATH = Path("/opt/OS/data/runtime/mesh_nodes.json")

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
        self._write_snapshot()

    def remove(self, node_id: str) -> ConnectedNode | None:
        with self._lock:
            node = self._nodes.pop(node_id, None)
        if node:
            logger.info("node removed: %s", node_id)
            self._write_snapshot()
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
            self._write_snapshot()
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

    def _write_snapshot(self) -> None:
        try:
            with self._lock:
                data = [n.to_api_dict() for n in self._nodes.values()]
            _SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
            _SNAPSHOT_PATH.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass
