"""Node registry — multi-device node tracking with telemetry.

Manages LOCAL and VPS nodes. Detects the local node automatically
and allows manual VPS registration. Stores last heartbeat and
telemetry per node.

No imports from umh/cells, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.environments.telemetry import NodeTelemetry, TelemetryCollector


@unique
class DeviceType(str, Enum):
    LOCAL = "local"
    VPS = "vps"


@dataclass
class DeviceNode:
    node_id: str
    device_type: DeviceType
    hostname: str = ""
    capabilities: dict[str, Any] = field(default_factory=dict)
    last_heartbeat: str = ""
    telemetry: NodeTelemetry | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.last_heartbeat:
            self.last_heartbeat = _iso_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "device_type": self.device_type.value,
            "hostname": self.hostname,
            "capabilities": self.capabilities,
            "last_heartbeat": self.last_heartbeat,
            "telemetry": self.telemetry.to_dict() if self.telemetry else None,
            "metadata": self.metadata,
        }


class DeviceNodeRegistry:
    """Registry of physical/virtual nodes available for execution."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._nodes: dict[str, DeviceNode] = {}
        self._collector = TelemetryCollector()

    def register_node(self, node: DeviceNode) -> None:
        with self._lock:
            self._nodes[node.node_id] = node

    def unregister_node(self, node_id: str) -> bool:
        with self._lock:
            return self._nodes.pop(node_id, None) is not None

    def get_node(self, node_id: str) -> DeviceNode | None:
        with self._lock:
            return self._nodes.get(node_id)

    def list_nodes(self, device_type: DeviceType | None = None) -> list[DeviceNode]:
        with self._lock:
            nodes = list(self._nodes.values())
        if device_type:
            nodes = [n for n in nodes if n.device_type == device_type]
        return nodes

    def update_telemetry(self, node_id: str) -> NodeTelemetry | None:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return None
        try:
            t = self._collector.collect_local()
            with self._lock:
                node = self._nodes.get(node_id)
                if node:
                    node.telemetry = t
                    node.last_heartbeat = _iso_now()
            return t
        except Exception:
            return None

    def detect_local_node(self) -> DeviceNode:
        import platform

        node = DeviceNode(
            node_id=f"local_{uuid.uuid4().hex[:8]}",
            device_type=DeviceType.LOCAL,
            hostname=platform.node(),
            capabilities={"python": True, "docker": False},
        )
        try:
            t = self._collector.collect_local()
            node.telemetry = t
        except Exception:
            pass
        self.register_node(node)
        return node

    def clear(self) -> None:
        with self._lock:
            self._nodes.clear()
