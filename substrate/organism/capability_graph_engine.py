"""Capability Graph Engine — explicit dependency/composition edges between capabilities.

Campaign 10.0. UMH substrate layer.

Adds relationship structure to capabilities: which capabilities depend on,
compose from, enable, or conflict with each other. Wraps CapabilityRuntime
+ RealityGraph — does NOT own capability identity or maturity.

Deterministic. No LLM. No execution. No mutation of capabilities.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class CapabilityRelationType(str, Enum):
    DEPENDS_ON = "depends_on"
    COMPOSES = "composes"
    ENABLES = "enables"
    CONFLICTS_WITH = "conflicts_with"


@dataclass
class CapabilityEdge:
    edge_id: str = field(default_factory=lambda: f"cedge-{uuid4().hex[:8]}")
    source_id: str = ""
    target_id: str = ""
    relation: CapabilityRelationType = CapabilityRelationType.DEPENDS_ON
    strength: float = 1.0
    evidence_ids: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation.value,
            "strength": self.strength,
            "evidence_ids": self.evidence_ids,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CapabilityEdge:
        d = dict(d)
        rel = d.get("relation", "depends_on")
        try:
            d["relation"] = CapabilityRelationType(rel)
        except ValueError:
            d["relation"] = CapabilityRelationType.DEPENDS_ON
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class CapabilityGraphEngine:
    """Manages explicit dependency/composition edges between capabilities."""

    def __init__(
        self,
        capability_runtime: Any | None = None,
        reality_graph: Any | None = None,
        data_dir: str = "",
    ) -> None:
        self._capability_runtime = capability_runtime
        self._reality_graph = reality_graph
        self._data_dir = data_dir or os.path.join(
            _REPO_ROOT, "data", "umh", "capabilities"
        )
        self._edges: dict[str, CapabilityEdge] = {}
        self._load()

    # ── Persistence ───────────────────────────────────────────────

    def _edges_path(self) -> str:
        return os.path.join(self._data_dir, "edges.jsonl")

    def _load(self) -> None:
        path = self._edges_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        edge = CapabilityEdge.from_dict(d)
                        self._edges[edge.edge_id] = edge
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.debug("Skip malformed edge line: %s", e)
        except OSError as e:
            logger.debug("Cannot read %s: %s", path, e)

    def _persist(self, edge: CapabilityEdge) -> None:
        os.makedirs(self._data_dir, exist_ok=True)
        with open(self._edges_path(), "a") as f:
            f.write(json.dumps(edge.to_dict(), default=str) + "\n")

    # ── Graph operations ──────────────────────────────────────────

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: CapabilityRelationType = CapabilityRelationType.DEPENDS_ON,
        strength: float = 1.0,
        evidence_ids: list[str] | None = None,
    ) -> CapabilityEdge:
        """Add a directed edge between two capabilities."""
        for existing in self._edges.values():
            if (
                existing.source_id == source_id
                and existing.target_id == target_id
                and existing.relation == relation
            ):
                return existing

        edge = CapabilityEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            strength=max(0.0, min(1.0, strength)),
            evidence_ids=evidence_ids or [],
        )
        self._edges[edge.edge_id] = edge
        self._persist(edge)
        self._register_in_reality_graph(edge)
        return edge

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge by ID. Returns True if found and removed."""
        if edge_id not in self._edges:
            return False
        del self._edges[edge_id]
        self._rewrite()
        return True

    def get_edge(self, edge_id: str) -> CapabilityEdge | None:
        return self._edges.get(edge_id)

    def all_edges(self) -> list[CapabilityEdge]:
        return list(self._edges.values())

    def edges_for(self, capability_id: str) -> list[CapabilityEdge]:
        """All edges where this capability is source or target."""
        return [
            e for e in self._edges.values()
            if e.source_id == capability_id or e.target_id == capability_id
        ]

    def dependencies(self, capability_id: str) -> list[str]:
        """What capabilities does this one depend on? (outgoing DEPENDS_ON)"""
        return [
            e.target_id for e in self._edges.values()
            if e.source_id == capability_id
            and e.relation == CapabilityRelationType.DEPENDS_ON
        ]

    def dependents(self, capability_id: str) -> list[str]:
        """What capabilities depend on this one? (incoming DEPENDS_ON)"""
        return [
            e.source_id for e in self._edges.values()
            if e.target_id == capability_id
            and e.relation == CapabilityRelationType.DEPENDS_ON
        ]

    def composition_tree(self, capability_id: str, max_depth: int = 10) -> dict[str, Any]:
        """Build a tree of what this capability is composed of."""
        visited: set[str] = set()

        def _build(cid: str, depth: int) -> dict[str, Any]:
            if cid in visited or depth > max_depth:
                return {"capability_id": cid, "children": [], "cycle": cid in visited}
            visited.add(cid)
            children_ids = [
                e.target_id for e in self._edges.values()
                if e.source_id == cid
                and e.relation in (
                    CapabilityRelationType.COMPOSES,
                    CapabilityRelationType.DEPENDS_ON,
                )
            ]
            children = [_build(child, depth + 1) for child in children_ids]
            name = self._resolve_name(cid)
            return {
                "capability_id": cid,
                "name": name,
                "children": children,
                "depth": depth,
            }

        return _build(capability_id, 0)

    def critical_path(self, from_id: str, to_id: str) -> list[str]:
        """BFS shortest path from one capability to another via any edge."""
        if from_id == to_id:
            return [from_id]

        adjacency: dict[str, list[str]] = defaultdict(list)
        for e in self._edges.values():
            adjacency[e.source_id].append(e.target_id)

        queue: list[list[str]] = [[from_id]]
        visited: set[str] = {from_id}
        while queue:
            path = queue.pop(0)
            current = path[-1]
            for neighbor in adjacency.get(current, []):
                if neighbor == to_id:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return []

    # ── Analysis ──────────────────────────────────────────────────

    def detect_cycles(self) -> list[list[str]]:
        """Detect dependency cycles using DFS."""
        adjacency: dict[str, list[str]] = defaultdict(list)
        for e in self._edges.values():
            if e.relation in (
                CapabilityRelationType.DEPENDS_ON,
                CapabilityRelationType.COMPOSES,
            ):
                adjacency[e.source_id].append(e.target_id)

        all_nodes = set(adjacency.keys())
        for targets in adjacency.values():
            all_nodes.update(targets)

        cycles: list[list[str]] = []
        visited: set[str] = set()
        in_stack: set[str] = set()
        stack_path: list[str] = []

        def _dfs(node: str) -> None:
            visited.add(node)
            in_stack.add(node)
            stack_path.append(node)
            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    _dfs(neighbor)
                elif neighbor in in_stack:
                    idx = stack_path.index(neighbor)
                    cycle = stack_path[idx:] + [neighbor]
                    cycles.append(cycle)
            stack_path.pop()
            in_stack.discard(node)

        for node in all_nodes:
            if node not in visited:
                _dfs(node)
        return cycles

    def orphans(self) -> list[str]:
        """Capabilities with no edges at all."""
        if not self._capability_runtime:
            return []
        connected: set[str] = set()
        for e in self._edges.values():
            connected.add(e.source_id)
            connected.add(e.target_id)

        all_caps = self._capability_runtime.list_capabilities()
        return [c.capability_id for c in all_caps if c.capability_id not in connected]

    def bottlenecks(self, limit: int = 5) -> list[dict[str, Any]]:
        """Capabilities with the most incoming dependency edges."""
        incoming: dict[str, int] = defaultdict(int)
        for e in self._edges.values():
            if e.relation == CapabilityRelationType.DEPENDS_ON:
                incoming[e.target_id] += 1

        sorted_caps = sorted(incoming.items(), key=lambda x: -x[1])
        result: list[dict[str, Any]] = []
        for cap_id, count in sorted_caps[:limit]:
            name = self._resolve_name(cap_id)
            result.append({
                "capability_id": cap_id,
                "name": name,
                "dependent_count": count,
            })
        return result

    def summary(self) -> dict[str, Any]:
        """Graph summary statistics."""
        by_relation: dict[str, int] = defaultdict(int)
        for e in self._edges.values():
            by_relation[e.relation.value] += 1

        nodes: set[str] = set()
        for e in self._edges.values():
            nodes.add(e.source_id)
            nodes.add(e.target_id)

        return {
            "total_edges": len(self._edges),
            "total_nodes": len(nodes),
            "by_relation": dict(by_relation),
            "cycles": len(self.detect_cycles()),
            "bottlenecks": self.bottlenecks(3),
        }

    # ── Internal ──────────────────────────────────────────────────

    def _resolve_name(self, capability_id: str) -> str:
        if not self._capability_runtime:
            return capability_id
        cap = self._capability_runtime.get(capability_id)
        return cap.name if cap else capability_id

    def _rewrite(self) -> None:
        os.makedirs(self._data_dir, exist_ok=True)
        with open(self._edges_path(), "w") as f:
            for edge in self._edges.values():
                f.write(json.dumps(edge.to_dict(), default=str) + "\n")

    def _register_in_reality_graph(self, edge: CapabilityEdge) -> None:
        if not self._reality_graph:
            return
        try:
            from substrate.organism.reality_graph import (
                RealityRelation,
                RealityRelationType,
            )

            relation_map = {
                CapabilityRelationType.DEPENDS_ON: RealityRelationType.DEPENDS_ON,
                CapabilityRelationType.COMPOSES: RealityRelationType.COMPOSES,
                CapabilityRelationType.ENABLES: RealityRelationType.ENABLES,
                CapabilityRelationType.CONFLICTS_WITH: RealityRelationType.CONFLICTS_WITH,
            }
            rg_type = relation_map.get(edge.relation)
            if not rg_type:
                return

            rel = RealityRelation(
                source_id=edge.source_id,
                target_id=edge.target_id,
                relation_type=rg_type,
            )
            self._reality_graph.add_relation(rel)
        except Exception as exc:
            logger.debug("Failed to register edge in reality graph: %s", exc)
