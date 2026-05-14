"""Application Topology Engine v1.

Tracks application relationships, shared substrate bindings,
capability dependencies, continuity dependencies, and
domain isolation boundaries.

UMH substrate subsystem. Phase 96.8CD.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.applications.application_projection_contracts_v1 import (
    ApplicationTopologyState,
    _now_iso,
)

MAX_TOPOLOGY_NODES = 30
MAX_EDGES = 100


class ApplicationTopologyEngine:
    """Tracks application topology and relationships."""

    def __init__(self, state_dir: str | Path = "data/runtime/applications") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []
        self._isolation_boundaries: dict[str, list[str]] = {}

    def register_node(
        self,
        app_id: str,
        domain_context: str = "",
        capabilities: list[str] | None = None,
    ) -> dict[str, Any] | None:
        if len(self._nodes) >= MAX_TOPOLOGY_NODES:
            return None

        if app_id in self._nodes:
            return self._nodes[app_id]

        node = {
            "app_id": app_id,
            "domain_context": domain_context,
            "capabilities": capabilities or [],
            "registered_at": _now_iso(),
        }
        self._nodes[app_id] = node

        if domain_context:
            if domain_context not in self._isolation_boundaries:
                self._isolation_boundaries[domain_context] = []
            if app_id not in self._isolation_boundaries[domain_context]:
                self._isolation_boundaries[domain_context].append(app_id)

        return node

    def add_edge(
        self,
        from_app: str,
        to_app: str,
        relationship: str = "shares_substrate",
    ) -> dict[str, Any] | None:
        if from_app not in self._nodes or to_app not in self._nodes:
            return None
        if from_app == to_app:
            return None
        if len(self._edges) >= MAX_EDGES:
            return None

        for edge in self._edges:
            if (edge["from_app"] == from_app
                    and edge["to_app"] == to_app
                    and edge["relationship"] == relationship):
                return edge

        edge = {
            "from_app": from_app,
            "to_app": to_app,
            "relationship": relationship,
            "created_at": _now_iso(),
        }
        self._edges.append(edge)
        return edge

    def get_node(self, app_id: str) -> dict[str, Any] | None:
        return self._nodes.get(app_id)

    def get_edges_for_app(self, app_id: str) -> list[dict[str, Any]]:
        return [
            e for e in self._edges
            if e["from_app"] == app_id or e["to_app"] == app_id
        ]

    def get_isolation_boundary(
        self,
        domain_context: str,
    ) -> list[str]:
        return list(self._isolation_boundaries.get(domain_context, []))

    def verify_domain_isolation(
        self,
        domain_a: str,
        domain_b: str,
    ) -> bool:
        apps_a = set(self._isolation_boundaries.get(domain_a, []))
        apps_b = set(self._isolation_boundaries.get(domain_b, []))
        return len(apps_a & apps_b) == 0

    def get_topology_snapshot(self) -> ApplicationTopologyState:
        apps = sorted(self._nodes.keys())
        shared = sorted(set(
            f"{e['from_app']}↔{e['to_app']}" for e in self._edges
        ))
        boundaries = sorted(self._isolation_boundaries.keys())
        return ApplicationTopologyState(
            applications=apps,
            shared_bindings=shared,
            isolation_boundaries=boundaries,
        )

    def get_topology_hash(self) -> str:
        apps = sorted(self._nodes.keys())
        edges_str = ",".join(
            f"{e['from_app']}-{e['to_app']}" for e in sorted(
                self._edges, key=lambda x: (x["from_app"], x["to_app"])
            )
        )
        content = f"{','.join(apps)}:{edges_str}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "isolation_boundaries": len(self._isolation_boundaries),
            "max_topology_nodes": MAX_TOPOLOGY_NODES,
        }
