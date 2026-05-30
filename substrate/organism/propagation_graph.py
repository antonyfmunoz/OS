"""Propagation Graph — dependency-aware change propagation model.

Maps how changes to one object propagate across all dependent objects:
work packets, workcells, templates, knowledge models, roadmap phases,
agents, memory, projections, companies, and operating systems.

Phase 12.0. UMH substrate subsystem. Instance-agnostic.
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
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class PropagationNodeType(str, Enum):
    WORK_PACKET = "work_packet"
    WORKCELL = "workcell"
    ADVISOR_BRANCH = "advisor_branch"
    ROLE_CONTRACT = "role_contract"
    KNOWLEDGE_MODEL = "knowledge_model"
    TEMPLATE = "template"
    AGENT_CAPABILITY = "agent_capability"
    MEMORY_ENTRY = "memory_entry"
    ROADMAP_PHASE = "roadmap_phase"
    SELF_BUILD_ITEM = "self_build_item"
    CANDIDATE = "candidate"
    APPROVAL_PACKET = "approval_packet"
    SANDBOX = "sandbox"
    PULL_REQUEST = "pull_request"
    PRODUCTION_TRUTH_DELTA = "production_truth_delta"
    OUTCOME = "outcome"
    WORLD_MODEL_ENTITY = "world_model_entity"
    DEPENDENCY_GRAPH_NODE = "dependency_graph_node"
    COCKPIT_PANEL = "cockpit_panel"
    API_ROUTE = "api_route"
    CONFIG_FILE = "config_file"
    DATA_STORE = "data_store"
    COMPANY = "company"
    ENTITY = "entity"
    PORTFOLIO = "portfolio"
    PRODUCT = "product"
    OFFER = "offer"
    CLIENT = "client"
    CONTENT_ASSET = "content_asset"
    HUMAN_ACTION = "human_action"


class PropagationEdgeType(str, Enum):
    DEPENDS_ON = "depends_on"
    UPDATES = "updates"
    INVALIDATES = "invalidates"
    RECOMPUTES = "recomputes"
    NOTIFIES = "notifies"
    CREATES = "creates"
    SUPERSEDES = "supersedes"
    VALIDATES = "validates"
    BLOCKS = "blocks"
    UNLOCKS = "unlocks"
    REFERENCES = "references"
    OWNS = "owns"
    BELONGS_TO = "belongs_to"
    FEEDS = "feeds"
    DERIVES_FROM = "derives_from"
    MIRRORS = "mirrors"
    PROJECTS_TO = "projects_to"
    REQUIRES_APPROVAL_FROM = "requires_approval_from"
    REQUIRES_HUMAN_ACTION_FROM = "requires_human_action_from"


class PropagationMode(str, Enum):
    NO_OP = "no_op"
    NOTIFY_ONLY = "notify_only"
    RECOMPUTE = "recompute"
    REVALIDATE = "revalidate"
    REGENERATE = "regenerate"
    CREATE_CANDIDATE = "create_candidate"
    CREATE_WORK_PACKET = "create_work_packet"
    REQUIRE_APPROVAL = "require_approval"
    QUEUE_WORK = "queue_work"
    UPDATE_MEMORY = "update_memory"
    UPDATE_TEMPLATE = "update_template"
    UPDATE_RELIABILITY = "update_reliability"
    UPDATE_PROJECTION = "update_projection"
    BLOCK_UNTIL_REVIEW = "block_until_review"


class EdgeStrength(str, Enum):
    HARD = "hard"
    SOFT = "soft"
    OPTIONAL = "optional"
    INFERRED = "inferred"


@dataclass
class PropagationNode:
    node_id: str = field(default_factory=lambda: f"pgn-{uuid4().hex[:12]}")
    node_type: PropagationNodeType = PropagationNodeType.WORK_PACKET
    title: str = ""
    description: str = ""
    source_type: str = ""
    source_id: str = ""
    source_path: str = ""
    entity_ref: str = ""
    domain: str = ""
    projection: str = ""
    status: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value if isinstance(self.node_type, Enum) else self.node_type,
            "title": self.title,
            "description": self.description,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_path": self.source_path,
            "entity_ref": self.entity_ref,
            "domain": self.domain,
            "projection": self.projection,
            "status": self.status,
            "metadata": self.metadata,
            "evidence": self.evidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PropagationNode:
        nt = d.get("node_type", "work_packet")
        try:
            node_type = PropagationNodeType(nt)
        except ValueError:
            node_type = PropagationNodeType.WORK_PACKET
        return cls(
            node_id=d.get("node_id", f"pgn-{uuid4().hex[:12]}"),
            node_type=node_type,
            title=d.get("title", ""),
            description=d.get("description", ""),
            source_type=d.get("source_type", ""),
            source_id=d.get("source_id", ""),
            source_path=d.get("source_path", ""),
            entity_ref=d.get("entity_ref", ""),
            domain=d.get("domain", ""),
            projection=d.get("projection", ""),
            status=d.get("status", ""),
            metadata=d.get("metadata", {}),
            evidence=d.get("evidence", []),
            created_at=d.get("created_at", time.time()),
            updated_at=d.get("updated_at", time.time()),
        )


@dataclass
class PropagationEdge:
    edge_id: str = field(default_factory=lambda: f"pge-{uuid4().hex[:12]}")
    from_node_id: str = ""
    to_node_id: str = ""
    edge_type: PropagationEdgeType = PropagationEdgeType.DEPENDS_ON
    propagation_mode: PropagationMode = PropagationMode.NOTIFY_ONLY
    strength: EdgeStrength = EdgeStrength.SOFT
    reason: str = ""
    evidence: list[dict[str, Any]] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    validation_required: bool = False
    approval_required: bool = False
    idempotency_key: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "edge_type": self.edge_type.value if isinstance(self.edge_type, Enum) else self.edge_type,
            "propagation_mode": self.propagation_mode.value if isinstance(self.propagation_mode, Enum) else self.propagation_mode,
            "strength": self.strength.value if isinstance(self.strength, Enum) else self.strength,
            "reason": self.reason,
            "evidence": self.evidence,
            "conditions": self.conditions,
            "validation_required": self.validation_required,
            "approval_required": self.approval_required,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PropagationEdge:
        et = d.get("edge_type", "depends_on")
        try:
            edge_type = PropagationEdgeType(et)
        except ValueError:
            edge_type = PropagationEdgeType.DEPENDS_ON
        pm = d.get("propagation_mode", "notify_only")
        try:
            prop_mode = PropagationMode(pm)
        except ValueError:
            prop_mode = PropagationMode.NOTIFY_ONLY
        st = d.get("strength", "soft")
        try:
            strength = EdgeStrength(st)
        except ValueError:
            strength = EdgeStrength.SOFT
        return cls(
            edge_id=d.get("edge_id", f"pge-{uuid4().hex[:12]}"),
            from_node_id=d.get("from_node_id", ""),
            to_node_id=d.get("to_node_id", ""),
            edge_type=edge_type,
            propagation_mode=prop_mode,
            strength=strength,
            reason=d.get("reason", ""),
            evidence=d.get("evidence", []),
            conditions=d.get("conditions", []),
            validation_required=d.get("validation_required", False),
            approval_required=d.get("approval_required", False),
            idempotency_key=d.get("idempotency_key", ""),
            created_at=d.get("created_at", time.time()),
            updated_at=d.get("updated_at", time.time()),
        )


class PropagationGraph:
    """Universal propagation graph — nodes, edges, traversal, analysis."""

    def __init__(self) -> None:
        self.nodes: dict[str, PropagationNode] = {}
        self.edges: dict[str, PropagationEdge] = {}
        self.version: str = "12.0.0"
        self.built_at: float = time.time()
        self.source_summary: str = ""
        self._adjacency_out: dict[str, list[str]] = {}
        self._adjacency_in: dict[str, list[str]] = {}

    def add_node(self, node: PropagationNode) -> None:
        self.nodes[node.node_id] = node
        if node.node_id not in self._adjacency_out:
            self._adjacency_out[node.node_id] = []
        if node.node_id not in self._adjacency_in:
            self._adjacency_in[node.node_id] = []

    def add_edge(self, edge: PropagationEdge) -> None:
        self.edges[edge.edge_id] = edge
        if edge.from_node_id not in self._adjacency_out:
            self._adjacency_out[edge.from_node_id] = []
        self._adjacency_out[edge.from_node_id].append(edge.edge_id)
        if edge.to_node_id not in self._adjacency_in:
            self._adjacency_in[edge.to_node_id] = []
        self._adjacency_in[edge.to_node_id].append(edge.edge_id)

    def upstream(self, node_id: str, max_depth: int = 10) -> list[str]:
        visited: set[str] = set()
        result: list[str] = []
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        while queue:
            nid, depth = queue.popleft()
            if depth > max_depth:
                continue
            for edge_id in self._adjacency_in.get(nid, []):
                edge = self.edges[edge_id]
                upstream_id = edge.from_node_id
                if upstream_id not in visited and upstream_id != node_id:
                    visited.add(upstream_id)
                    result.append(upstream_id)
                    queue.append((upstream_id, depth + 1))
        return result

    def downstream(self, node_id: str, max_depth: int = 10) -> list[str]:
        visited: set[str] = set()
        result: list[str] = []
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        while queue:
            nid, depth = queue.popleft()
            if depth > max_depth:
                continue
            for edge_id in self._adjacency_out.get(nid, []):
                edge = self.edges[edge_id]
                downstream_id = edge.to_node_id
                if downstream_id not in visited and downstream_id != node_id:
                    visited.add(downstream_id)
                    result.append(downstream_id)
                    queue.append((downstream_id, depth + 1))
        return result

    def affected_by_change(self, node_id: str, max_depth: int = 10) -> list[str]:
        return self.downstream(node_id, max_depth)

    def impact_radius(self, node_id: str) -> dict[str, Any]:
        downstream_ids = self.downstream(node_id)
        upstream_ids = self.upstream(node_id)
        type_counts: dict[str, int] = {}
        for nid in downstream_ids:
            node = self.nodes.get(nid)
            if node:
                nt = node.node_type.value if isinstance(node.node_type, Enum) else node.node_type
                type_counts[nt] = type_counts.get(nt, 0) + 1
        return {
            "source_node_id": node_id,
            "downstream_count": len(downstream_ids),
            "upstream_count": len(upstream_ids),
            "downstream_ids": downstream_ids,
            "upstream_ids": upstream_ids,
            "affected_type_counts": type_counts,
        }

    def detect_cycles(self) -> list[list[str]]:
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {nid: WHITE for nid in self.nodes}
        cycles: list[list[str]] = []

        def _dfs(nid: str, path: list[str]) -> None:
            color[nid] = GRAY
            path.append(nid)
            for edge_id in self._adjacency_out.get(nid, []):
                edge = self.edges[edge_id]
                target = edge.to_node_id
                if target not in color:
                    continue
                if color[target] == GRAY:
                    cycle_start = path.index(target)
                    cycles.append(path[cycle_start:] + [target])
                elif color[target] == WHITE:
                    _dfs(target, path)
            path.pop()
            color[nid] = BLACK

        for nid in self.nodes:
            if color.get(nid, WHITE) == WHITE:
                _dfs(nid, [])
        return cycles

    def orphaned_nodes(self) -> list[str]:
        orphans = []
        for nid in self.nodes:
            in_edges = self._adjacency_in.get(nid, [])
            out_edges = self._adjacency_out.get(nid, [])
            if not in_edges and not out_edges:
                orphans.append(nid)
        return orphans

    def graph_stats(self) -> dict[str, Any]:
        node_type_counts: dict[str, int] = {}
        for node in self.nodes.values():
            nt = node.node_type.value if isinstance(node.node_type, Enum) else node.node_type
            node_type_counts[nt] = node_type_counts.get(nt, 0) + 1
        edge_type_counts: dict[str, int] = {}
        for edge in self.edges.values():
            et = edge.edge_type.value if isinstance(edge.edge_type, Enum) else edge.edge_type
            edge_type_counts[et] = edge_type_counts.get(et, 0) + 1
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_type_counts": node_type_counts,
            "edge_type_counts": edge_type_counts,
            "orphaned_node_count": len(self.orphaned_nodes()),
            "cycle_count": len(self.detect_cycles()),
            "built_at": self.built_at,
            "version": self.version,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "built_at": self.built_at,
            "source_summary": self.source_summary,
            "graph_stats": self.graph_stats(),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges.values()],
        }

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "built_at": self.built_at,
            "source_summary": self.source_summary,
            "graph_stats": self.graph_stats(),
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "node_ids": list(self.nodes.keys()),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PropagationGraph:
        g = cls()
        g.version = d.get("version", "12.0.0")
        g.built_at = d.get("built_at", time.time())
        g.source_summary = d.get("source_summary", "")
        for nd in d.get("nodes", []):
            g.add_node(PropagationNode.from_dict(nd))
        for ed in d.get("edges", []):
            g.add_edge(PropagationEdge.from_dict(ed))
        return g

    def persist(self, path: str | None = None) -> str:
        path = path or os.path.join(
            _REPO_ROOT, "data", "umh", "propagation_graph", "graph.json",
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = self.to_dict()
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
        logger.info("Propagation graph persisted: %d nodes, %d edges -> %s",
                     len(self.nodes), len(self.edges), path)
        return path

    @classmethod
    def load(cls, path: str | None = None) -> PropagationGraph:
        path = path or os.path.join(
            _REPO_ROOT, "data", "umh", "propagation_graph", "graph.json",
        )
        if not os.path.exists(path):
            return cls()
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)
