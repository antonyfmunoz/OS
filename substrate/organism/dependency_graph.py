"""Dependency Graph — subsystem dependency model for UMH.

Answers:
  - What depends on what?
  - What breaks if this node fails?
  - What is upstream/downstream?
  - What is on the critical path?
  - What dependencies are missing or weak?

Built deterministically from WorldModel entities and observed imports.
No LLM required.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class DependencyType(str, Enum):
    RUNTIME = "runtime"
    CODE = "code"
    DATA = "data"
    GOVERNANCE = "governance"
    INTERFACE = "interface"
    DEPLOYMENT = "deployment"
    MEMORY = "memory"
    EVENT = "event"
    EXECUTION = "execution"
    OPERATOR = "operator"


class DependencyStrength(str, Enum):
    HARD = "hard"
    SOFT = "soft"
    OPTIONAL = "optional"


@dataclass
class DependencyNode:
    id: str
    name: str
    category: str = ""
    status: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "status": self.status,
        }


@dataclass
class DependencyEdge:
    source: str
    target: str
    dep_type: DependencyType
    strength: DependencyStrength = DependencyStrength.HARD
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.dep_type.value,
            "strength": self.strength.value,
            "evidence": self.evidence,
        }


@dataclass
class CriticalPath:
    path: list[str] = field(default_factory=list)
    length: int = 0
    risk: str = "low"
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "length": self.length,
            "risk": self.risk,
            "description": self.description,
        }


@dataclass
class DependencyGraph:
    nodes: dict[str, DependencyNode] = field(default_factory=dict)
    edges: list[DependencyEdge] = field(default_factory=list)
    extracted_at: float = field(default_factory=time.time)

    def add_node(self, node: DependencyNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: DependencyEdge) -> None:
        self.edges.append(edge)

    def get_node(self, node_id: str) -> DependencyNode | None:
        return self.nodes.get(node_id)

    def upstream(self, node_id: str) -> list[str]:
        """What this node depends on (targets of edges where source == node_id)."""
        return [e.target for e in self.edges if e.source == node_id]

    def downstream(self, node_id: str) -> list[str]:
        """What depends on this node (sources of edges where target == node_id)."""
        return [e.source for e in self.edges if e.target == node_id]

    def edges_from(self, node_id: str) -> list[DependencyEdge]:
        return [e for e in self.edges if e.source == node_id]

    def edges_to(self, node_id: str) -> list[DependencyEdge]:
        return [e for e in self.edges if e.target == node_id]

    def orphaned_nodes(self) -> list[str]:
        """Nodes with no incoming or outgoing edges."""
        connected = set()
        for e in self.edges:
            connected.add(e.source)
            connected.add(e.target)
        return [nid for nid in self.nodes if nid not in connected]

    def circular_dependencies(self) -> list[list[str]]:
        """Detect cycles using DFS."""
        cycles: list[list[str]] = []
        visited: set[str] = set()
        on_stack: set[str] = set()
        path: list[str] = []

        adj: dict[str, list[str]] = {nid: [] for nid in self.nodes}
        for e in self.edges:
            if e.source in adj:
                adj[e.source].append(e.target)

        def dfs(node: str) -> None:
            visited.add(node)
            on_stack.add(node)
            path.append(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in on_stack:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
            path.pop()
            on_stack.discard(node)

        for nid in self.nodes:
            if nid not in visited:
                dfs(nid)
        return cycles

    def critical_paths(self) -> list[CriticalPath]:
        """Find longest paths in the graph (approximate critical paths)."""
        adj: dict[str, list[str]] = {nid: [] for nid in self.nodes}
        in_degree: dict[str, int] = {nid: 0 for nid in self.nodes}
        for e in self.edges:
            if e.source in adj:
                adj[e.source].append(e.target)
            if e.target in in_degree:
                in_degree[e.target] = in_degree.get(e.target, 0) + 1

        roots = [nid for nid, deg in in_degree.items() if deg == 0]
        if not roots:
            return []

        longest: dict[str, list[str]] = {}
        for root in roots:
            queue = deque([(root, [root])])
            while queue:
                node, path = queue.popleft()
                if node not in longest or len(path) > len(longest[node]):
                    longest[node] = path
                for neighbor in adj.get(node, []):
                    if neighbor in self.nodes:
                        queue.append((neighbor, path + [neighbor]))

        if not longest:
            return []

        max_len = max(len(p) for p in longest.values())
        result = []
        for node, path in longest.items():
            if len(path) == max_len:
                result.append(CriticalPath(
                    path=path, length=len(path),
                    risk="high" if max_len > 4 else "medium" if max_len > 2 else "low",
                    description=f"Longest chain: {' → '.join(path)}",
                ))
        return result[:5]

    def weak_dependencies(self) -> list[DependencyEdge]:
        """Edges marked as soft or optional."""
        return [e for e in self.edges if e.strength in (DependencyStrength.SOFT, DependencyStrength.OPTIONAL)]

    def missing_dependencies(self) -> list[dict[str, str]]:
        """Edges pointing to nodes not in the graph."""
        known = set(self.nodes.keys())
        missing = []
        for e in self.edges:
            if e.target not in known:
                missing.append({"source": e.source, "missing_target": e.target, "type": e.dep_type.value})
            if e.source not in known:
                missing.append({"missing_source": e.source, "target": e.target, "type": e.dep_type.value})
        return missing

    def summary(self) -> dict[str, Any]:
        type_counts: dict[str, int] = {}
        for e in self.edges:
            type_counts[e.dep_type.value] = type_counts.get(e.dep_type.value, 0) + 1
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "edge_types": type_counts,
            "orphaned": len(self.orphaned_nodes()),
            "cycles": len(self.circular_dependencies()),
            "critical_path_length": max((len(cp.path) for cp in self.critical_paths()), default=0),
            "extracted_at": self.extracted_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "orphaned": self.orphaned_nodes(),
            "cycles": self.circular_dependencies(),
            "critical_paths": [cp.to_dict() for cp in self.critical_paths()],
            "weak_dependencies": [e.to_dict() for e in self.weak_dependencies()],
            "missing_dependencies": self.missing_dependencies(),
            "extracted_at": self.extracted_at,
        }

    def to_safe_dict(self) -> dict[str, Any]:
        """HTTP-safe serialization — strips internal wiring evidence."""
        safe_edges = []
        for e in self.edges:
            safe_edges.append({
                "source": e.source, "target": e.target,
                "type": e.dep_type.value, "strength": e.strength.value,
            })
        return {
            "summary": self.summary(),
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": safe_edges,
            "orphaned": self.orphaned_nodes(),
            "cycles": self.circular_dependencies(),
            "critical_paths": [cp.to_dict() for cp in self.critical_paths()],
            "extracted_at": self.extracted_at,
        }


# ---------------------------------------------------------------------------
# Deterministic extraction from WorldModel
# ---------------------------------------------------------------------------

_KNOWN_DEPENDENCIES: list[tuple[str, str, DependencyType, DependencyStrength, str]] = [
    ("organism_daemon", "event_spine", DependencyType.EVENT, DependencyStrength.HARD,
     "Daemon emits/subscribes to EventSpine events"),
    ("organism_daemon", "execution_journal", DependencyType.DATA, DependencyStrength.HARD,
     "Daemon logs all mutations to journal"),
    ("organism_daemon", "mutation_registry", DependencyType.GOVERNANCE, DependencyStrength.HARD,
     "Daemon validates mutations via registry"),
    ("organism_daemon", "autonomous_gateway", DependencyType.EXECUTION, DependencyStrength.HARD,
     "Daemon funnels autonomous actions through gateway"),
    ("organism_daemon", "readiness_model", DependencyType.RUNTIME, DependencyStrength.HARD,
     "Daemon computes readiness on each tick"),
    ("organism_daemon", "bottleneck_engine", DependencyType.RUNTIME, DependencyStrength.HARD,
     "Daemon runs bottleneck detection"),
    ("organism_daemon", "advisor", DependencyType.RUNTIME, DependencyStrength.HARD,
     "Daemon delegates to advisor hub"),
    ("organism_daemon", "coordinator", DependencyType.EXECUTION, DependencyStrength.HARD,
     "Daemon uses coordinator for DAG execution"),
    ("organism_daemon", "homeostasis", DependencyType.RUNTIME, DependencyStrength.HARD,
     "Daemon runs homeostasis checks"),
    ("advisor", "coordinator", DependencyType.EXECUTION, DependencyStrength.HARD,
     "Advisor delegates complex objectives to coordinator"),
    ("advisor", "event_spine", DependencyType.EVENT, DependencyStrength.HARD,
     "Advisor emits events via spine"),
    ("advisor", "adapter_model_router", DependencyType.RUNTIME, DependencyStrength.SOFT,
     "Advisor uses LLM routing for cognitive tasks"),
    ("governed_spine", "mutation_registry", DependencyType.GOVERNANCE, DependencyStrength.HARD,
     "GovernedSpine consults registry before execution"),
    ("governed_spine", "execution_journal", DependencyType.DATA, DependencyStrength.HARD,
     "GovernedSpine logs to journal"),
    ("governed_spine", "autonomous_gateway", DependencyType.GOVERNANCE, DependencyStrength.HARD,
     "GovernedSpine enforces gateway policy"),
    ("assisted_executor", "governed_spine", DependencyType.EXECUTION, DependencyStrength.HARD,
     "AssistedExecutor routes through governed spine"),
    ("maintenance_loop", "workload_runner", DependencyType.EXECUTION, DependencyStrength.HARD,
     "MaintenanceLoop runs workloads via runner"),
    ("maintenance_loop", "bottleneck_engine", DependencyType.RUNTIME, DependencyStrength.SOFT,
     "MaintenanceLoop uses bottleneck data for prioritization"),
    ("workload_runner", "adapter_model_router", DependencyType.RUNTIME, DependencyStrength.OPTIONAL,
     "WorkloadRunner may use LLM for analysis"),
    ("adapter_model_router", "adapter_cc_sdk", DependencyType.RUNTIME, DependencyStrength.SOFT,
     "ModelRouter falls back through CC SDK first"),
    ("adapter_model_router", "adapter_llm_adapter", DependencyType.CODE, DependencyStrength.HARD,
     "ModelRouter wrapped by LLMAdapter"),
    ("next_action_engine", "bottleneck_engine", DependencyType.DATA, DependencyStrength.HARD,
     "NextAction uses bottleneck data for recommendations"),
    ("next_action_engine", "readiness_model", DependencyType.DATA, DependencyStrength.HARD,
     "NextAction uses readiness for prioritization"),
    ("leverage_engine", "execution_economy", DependencyType.DATA, DependencyStrength.HARD,
     "LeverageEngine reads execution economics"),
    ("recursion_governance", "execution_journal", DependencyType.DATA, DependencyStrength.HARD,
     "RecursionGovernor tracks depth via journal"),
    ("transport_discord_bot", "adapter_model_router", DependencyType.RUNTIME, DependencyStrength.HARD,
     "Discord bot uses model_router for responses"),
    ("transport_cockpit_api", "transport_discord_bot", DependencyType.INTERFACE, DependencyStrength.OPTIONAL,
     "Cockpit shows Discord status"),
    ("governance_spine", "governance_control_plane", DependencyType.GOVERNANCE, DependencyStrength.HARD,
     "Execution spine depends on control plane governance"),
]


def build_dependency_graph(world_model=None) -> DependencyGraph:
    """Build dependency graph from WorldModel + known relationships."""
    graph = DependencyGraph()

    if world_model is None:
        from substrate.organism.world_model import extract_world_model
        world_model = extract_world_model()

    for eid, entity in world_model.entities.items():
        graph.add_node(DependencyNode(
            id=eid, name=entity.name,
            category=entity.category.value,
            status=entity.status.value,
        ))

    known_nodes = set(graph.nodes.keys())
    for src, tgt, dtype, strength, evidence in _KNOWN_DEPENDENCIES:
        if src in known_nodes and tgt in known_nodes:
            graph.add_edge(DependencyEdge(
                source=src, target=tgt,
                dep_type=dtype, strength=strength,
                evidence=evidence,
            ))

    for eid, entity in world_model.entities.items():
        for dep_id in entity.depends_on:
            if dep_id in known_nodes and not any(
                e.source == eid and e.target == dep_id for e in graph.edges
            ):
                graph.add_edge(DependencyEdge(
                    source=eid, target=dep_id,
                    dep_type=DependencyType.CODE,
                    strength=DependencyStrength.HARD,
                    evidence=f"Declared dependency from WorldModel",
                ))

    return graph


def persist_dependency_graph(graph: DependencyGraph, path: str | None = None) -> str:
    """Persist dependency graph snapshot to JSONL."""
    if path is None:
        path = os.path.join(_REPO_ROOT, "data", "umh", "organism", "dependency_graph.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(graph.to_dict(), default=str) + "\n")
    return path


if __name__ == "__main__":
    import sys
    sys.path.insert(0, _REPO_ROOT)
    os.chdir(_REPO_ROOT)
    graph = build_dependency_graph()
    s = graph.summary()
    print(json.dumps(s, indent=2))
    print(f"\nOrphaned nodes: {graph.orphaned_nodes()[:10]}")
    print(f"Cycles: {graph.circular_dependencies()[:5]}")
    paths = graph.critical_paths()
    for cp in paths[:3]:
        print(f"Critical path ({cp.length}): {' → '.join(cp.path)}")
