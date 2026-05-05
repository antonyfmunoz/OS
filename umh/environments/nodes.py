"""Node registry — dynamic registration of execution nodes.

Nodes represent physical or virtual machines where execution can occur.
The registry is a simple in-memory store with thread-safe operations.

No imports from umh/cells, umh/adapters, or umh/execution.
"""

from __future__ import annotations

import threading
from typing import Any

from umh.environments.models import Node, NodeStatus, NodeType


class NodeRegistry:
    """Thread-safe registry of execution nodes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._nodes: dict[str, Node] = {}

    def register_node(self, node: Node) -> None:
        with self._lock:
            self._nodes[node.node_id] = node

    def unregister_node(self, node_id: str) -> bool:
        with self._lock:
            return self._nodes.pop(node_id, None) is not None

    def get_node(self, node_id: str) -> Node | None:
        with self._lock:
            return self._nodes.get(node_id)

    def list_nodes(self, node_type: NodeType | None = None) -> list[Node]:
        with self._lock:
            nodes = list(self._nodes.values())
        if node_type:
            nodes = [n for n in nodes if n.node_type == node_type]
        return nodes

    def get_available_nodes(self) -> list[Node]:
        with self._lock:
            return [n for n in self._nodes.values() if n.status == NodeStatus.AVAILABLE]

    def clear(self) -> None:
        with self._lock:
            self._nodes.clear()
