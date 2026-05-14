"""Environment Execution Graph Engine v1.

Graph:
  environment → operational campaign → workflows →
  spine traversals → execution lineage → checkpoints →
  replay receipts

Supports:
  deterministic reconstruction, delegation traversal,
  topology replay, continuity replay.

UMH substrate subsystem. Phase 96.8BX.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.environments.live_environment_topology_contracts_v1 import (
    _content_hash,
    _new_id,
    _now_iso,
)


class EnvironmentExecutionGraphEngine:
    """Manages environment execution graphs."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/environment_coordination",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._graphs: dict[str, dict[str, Any]] = {}
        self._total_nodes: int = 0

    def create_graph(
        self,
        environment_id: str,
        campaign_id: str = "",
        operator_id: str = "",
    ) -> dict[str, Any]:
        graph = {
            "graph_id": _new_id("envgraph"),
            "environment_id": environment_id,
            "campaign_id": campaign_id,
            "operator_id": operator_id,
            "nodes": [],
            "edges": [],
            "created_at": _now_iso(),
        }
        self._graphs[environment_id] = graph
        return graph

    def add_node(
        self,
        environment_id: str,
        node_type: str,
        node_id: str,
        label: str = "",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        graph = self._graphs.get(environment_id)
        if not graph:
            return None

        node = {
            "node_id": node_id,
            "node_type": node_type,
            "label": label,
            "data": data or {},
            "timestamp": _now_iso(),
        }
        graph["nodes"].append(node)
        self._total_nodes += 1
        return node

    def add_edge(
        self,
        environment_id: str,
        from_id: str,
        to_id: str,
        edge_type: str = "sequence",
    ) -> dict[str, Any] | None:
        graph = self._graphs.get(environment_id)
        if not graph:
            return None

        edge = {
            "from_id": from_id,
            "to_id": to_id,
            "edge_type": edge_type,
            "timestamp": _now_iso(),
        }
        graph["edges"].append(edge)
        return edge

    def get_graph(self, environment_id: str) -> dict[str, Any] | None:
        return self._graphs.get(environment_id)

    def get_graph_hash(self, environment_id: str) -> str:
        graph = self._graphs.get(environment_id)
        if not graph:
            return ""
        return _content_hash({
            "nodes": graph["nodes"],
            "edges": graph["edges"],
        })

    def persist_graph(self, environment_id: str) -> bool:
        graph = self._graphs.get(environment_id)
        if not graph:
            return False

        path = self._state_dir / f"env_exec_graph_{environment_id}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2, default=str)

        ledger = self._state_dir / "environment_execution_graphs.jsonl"
        with ledger.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "graph_id": graph["graph_id"],
                "environment_id": environment_id,
                "node_count": len(graph["nodes"]),
                "edge_count": len(graph["edges"]),
                "content_hash": self.get_graph_hash(environment_id),
                "timestamp": _now_iso(),
            }, default=str) + "\n")

        return True

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_graphs": len(self._graphs),
            "total_nodes": self._total_nodes,
        }
