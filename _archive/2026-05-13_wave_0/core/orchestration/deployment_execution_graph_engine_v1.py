"""Deployment Execution Graph Engine v1.

Tracks deployment dependencies, orchestration edges,
environment/workflow/continuity/rollback bindings.

Prevents recursive execution graphs, uncontrolled fanout,
and orphan deployment chains.

UMH substrate subsystem. Phase 96.8CF.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.orchestration.live_operational_deployment_contracts_v1 import (
    DeploymentExecutionGraph,
    _now_iso,
)

MAX_NODES = 50
MAX_EDGES = 100
MAX_FANOUT = 3


class DeploymentExecutionGraphEngine:
    """Manages deployment execution graphs."""

    def __init__(self, state_dir: str | Path = "data/runtime/orchestration") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._nodes: list[str] = []
        self._edges: list[tuple[str, str]] = []

    def add_node(self, node_id: str) -> bool:
        if len(self._nodes) >= MAX_NODES:
            return False
        if node_id in self._nodes:
            return True
        self._nodes.append(node_id)
        return True

    def add_edge(self, source: str, target: str) -> bool:
        if source == target:
            return False
        if source not in self._nodes or target not in self._nodes:
            return False
        if len(self._edges) >= MAX_EDGES:
            return False

        fanout = sum(1 for s, _ in self._edges if s == source)
        if fanout >= MAX_FANOUT:
            return False

        if self._would_create_cycle(source, target):
            return False

        self._edges.append((source, target))
        return True

    def _would_create_cycle(self, source: str, target: str) -> bool:
        visited: set[str] = set()
        stack = [target]
        while stack:
            node = stack.pop()
            if node == source:
                return True
            if node in visited:
                continue
            visited.add(node)
            for s, t in self._edges:
                if s == node:
                    stack.append(t)
        return False

    def get_snapshot(self) -> DeploymentExecutionGraph:
        return DeploymentExecutionGraph(
            nodes=list(self._nodes),
            edges=list(self._edges),
        )

    def get_graph_hash(self) -> str:
        content = json.dumps(
            {"nodes": sorted(self._nodes),
             "edges": sorted([list(e) for e in self._edges])},
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_dependencies(self, node_id: str) -> list[str]:
        return [s for s, t in self._edges if t == node_id]

    def get_dependents(self, node_id: str) -> list[str]:
        return [t for s, t in self._edges if s == node_id]

    def get_orphans(self) -> list[str]:
        connected: set[str] = set()
        for s, t in self._edges:
            connected.add(s)
            connected.add(t)
        return [n for n in self._nodes if n not in connected]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "orphan_count": len(self.get_orphans()),
        }
