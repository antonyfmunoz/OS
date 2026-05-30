"""Impact Analyzer — computes change impact across the propagation graph.

Given a ChangeEvent, determines affected nodes, impact depth/radius,
required waves, parallelizable groups, validation/approval/human gates,
and reconvergence points.

Phase 12.0. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from substrate.organism.propagation_graph import (
    PropagationGraph,
    PropagationNode,
    PropagationEdge,
    PropagationNodeType,
    PropagationEdgeType,
    PropagationMode,
    EdgeStrength,
)
from substrate.organism.change_event import ChangeEvent

logger = logging.getLogger(__name__)

_RISK_WEIGHTS = {
    "hard": 1.0,
    "soft": 0.6,
    "optional": 0.3,
    "inferred": 0.2,
}

_NODE_TYPE_RISK_MULTIPLIER = {
    PropagationNodeType.PRODUCTION_TRUTH_DELTA: 1.5,
    PropagationNodeType.APPROVAL_PACKET: 1.3,
    PropagationNodeType.HUMAN_ACTION: 1.2,
    PropagationNodeType.API_ROUTE: 1.1,
    PropagationNodeType.WORK_PACKET: 1.0,
    PropagationNodeType.WORKCELL: 0.9,
    PropagationNodeType.ROADMAP_PHASE: 1.0,
    PropagationNodeType.TEMPLATE: 0.8,
    PropagationNodeType.KNOWLEDGE_MODEL: 0.7,
    PropagationNodeType.MEMORY_ENTRY: 0.5,
}


@dataclass
class ImpactedNode:
    node_id: str = ""
    node_type: str = ""
    title: str = ""
    impact_depth: int = 0
    impact_score: float = 0.0
    edge_path: list[str] = field(default_factory=list)
    propagation_mode: str = "notify_only"
    requires_validation: bool = False
    requires_approval: bool = False
    requires_human: bool = False
    is_blocked: bool = False
    is_no_op: bool = False
    is_stale: bool = False
    risk_class: str = "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "title": self.title,
            "impact_depth": self.impact_depth,
            "impact_score": round(self.impact_score, 4),
            "edge_path": self.edge_path,
            "propagation_mode": self.propagation_mode,
            "requires_validation": self.requires_validation,
            "requires_approval": self.requires_approval,
            "requires_human": self.requires_human,
            "is_blocked": self.is_blocked,
            "is_no_op": self.is_no_op,
            "is_stale": self.is_stale,
            "risk_class": self.risk_class,
        }


@dataclass
class ImpactAnalysis:
    analysis_id: str = ""
    change_event_id: str = ""
    source_node_id: str = ""
    affected_nodes: list[ImpactedNode] = field(default_factory=list)
    affected_edges: list[str] = field(default_factory=list)
    direct_impact: list[str] = field(default_factory=list)
    indirect_impact: list[str] = field(default_factory=list)
    impact_depth: int = 0
    impact_radius: int = 0
    required_waves: int = 0
    parallelizable_groups: list[list[str]] = field(default_factory=list)
    validation_required: list[str] = field(default_factory=list)
    approval_required: list[str] = field(default_factory=list)
    human_required: list[str] = field(default_factory=list)
    reconvergence_required: list[str] = field(default_factory=list)
    no_op_nodes: list[str] = field(default_factory=list)
    stale_nodes: list[str] = field(default_factory=list)
    blocked_nodes: list[str] = field(default_factory=list)
    risk_summary: dict[str, Any] = field(default_factory=dict)
    computed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "change_event_id": self.change_event_id,
            "source_node_id": self.source_node_id,
            "affected_nodes": [n.to_dict() for n in self.affected_nodes],
            "affected_edges": self.affected_edges,
            "direct_impact": self.direct_impact,
            "indirect_impact": self.indirect_impact,
            "impact_depth": self.impact_depth,
            "impact_radius": self.impact_radius,
            "required_waves": self.required_waves,
            "parallelizable_groups": self.parallelizable_groups,
            "validation_required": self.validation_required,
            "approval_required": self.approval_required,
            "human_required": self.human_required,
            "reconvergence_required": self.reconvergence_required,
            "no_op_nodes": self.no_op_nodes,
            "stale_nodes": self.stale_nodes,
            "blocked_nodes": self.blocked_nodes,
            "risk_summary": self.risk_summary,
            "computed_at": self.computed_at,
        }


class ImpactAnalyzer:
    """Computes change impact across the propagation graph."""

    def __init__(self, graph: PropagationGraph) -> None:
        self._graph = graph

    def analyze(self, event: ChangeEvent) -> ImpactAnalysis:
        from uuid import uuid4
        analysis = ImpactAnalysis(
            analysis_id=f"ia-{uuid4().hex[:12]}",
            change_event_id=event.change_id,
            source_node_id=event.source_node_id,
        )

        if event.source_node_id not in self._graph.nodes:
            logger.warning("Source node %s not in graph", event.source_node_id)
            return analysis

        visited: dict[str, int] = {}
        edge_trail: dict[str, list[str]] = {}
        queue: deque[tuple[str, int, list[str]]] = deque()

        for edge_id in self._graph._adjacency_out.get(event.source_node_id, []):
            edge = self._graph.edges[edge_id]
            target = edge.to_node_id
            if target not in visited:
                visited[target] = 1
                edge_trail[target] = [edge_id]
                queue.append((target, 1, [edge_id]))
                analysis.direct_impact.append(target)
                analysis.affected_edges.append(edge_id)

        while queue:
            nid, depth, path = queue.popleft()
            for edge_id in self._graph._adjacency_out.get(nid, []):
                edge = self._graph.edges[edge_id]
                target = edge.to_node_id
                if target not in visited:
                    visited[target] = depth + 1
                    new_path = path + [edge_id]
                    edge_trail[target] = new_path
                    queue.append((target, depth + 1, new_path))
                    analysis.indirect_impact.append(target)
                    analysis.affected_edges.append(edge_id)

        max_depth = 0
        for nid, depth in visited.items():
            node = self._graph.nodes.get(nid)
            if not node:
                continue

            if depth > max_depth:
                max_depth = depth

            impacted = self._classify_node(node, depth, edge_trail.get(nid, []), event)
            analysis.affected_nodes.append(impacted)

            if impacted.requires_validation:
                analysis.validation_required.append(nid)
            if impacted.requires_approval:
                analysis.approval_required.append(nid)
            if impacted.requires_human:
                analysis.human_required.append(nid)
            if impacted.is_blocked:
                analysis.blocked_nodes.append(nid)
            if impacted.is_no_op:
                analysis.no_op_nodes.append(nid)
            if impacted.is_stale:
                analysis.stale_nodes.append(nid)

        analysis.impact_depth = max_depth
        analysis.impact_radius = len(visited)
        analysis.parallelizable_groups = self._compute_parallel_groups(visited)
        analysis.required_waves = len(analysis.parallelizable_groups)
        analysis.reconvergence_required = self._find_reconvergence_points(visited)
        analysis.risk_summary = self._compute_risk_summary(analysis, event)

        return analysis

    def _classify_node(
        self,
        node: PropagationNode,
        depth: int,
        edge_path: list[str],
        event: ChangeEvent,
    ) -> ImpactedNode:
        nt = node.node_type.value if isinstance(node.node_type, Enum) else node.node_type

        risk_multiplier = _NODE_TYPE_RISK_MULTIPLIER.get(
            node.node_type if isinstance(node.node_type, PropagationNodeType) else PropagationNodeType.WORK_PACKET,
            1.0,
        )

        edge_strength_score = 0.0
        prop_mode = "notify_only"
        for eid in edge_path:
            edge = self._graph.edges.get(eid)
            if edge:
                st = edge.strength.value if isinstance(edge.strength, Enum) else edge.strength
                edge_strength_score += _RISK_WEIGHTS.get(st, 0.5)
                pm = edge.propagation_mode.value if isinstance(edge.propagation_mode, Enum) else edge.propagation_mode
                if pm != "no_op":
                    prop_mode = pm

        impact_score = risk_multiplier * (edge_strength_score / max(len(edge_path), 1)) * (1.0 / max(depth, 1))

        requires_approval = (
            node.node_type == PropagationNodeType.APPROVAL_PACKET
            or any(
                self._graph.edges[eid].edge_type == PropagationEdgeType.REQUIRES_APPROVAL_FROM
                for eid in edge_path
                if eid in self._graph.edges
            )
        )
        requires_human = (
            node.node_type == PropagationNodeType.HUMAN_ACTION
            or any(
                self._graph.edges[eid].edge_type == PropagationEdgeType.REQUIRES_HUMAN_ACTION_FROM
                for eid in edge_path
                if eid in self._graph.edges
            )
        )
        requires_validation = any(
            self._graph.edges[eid].validation_required
            for eid in edge_path
            if eid in self._graph.edges
        )
        is_blocked = event.risk_class == "medium" and prop_mode not in ("no_op", "notify_only")

        risk_class = "low"
        if impact_score > 1.0:
            risk_class = "high"
        elif impact_score > 0.5:
            risk_class = "medium"

        return ImpactedNode(
            node_id=node.node_id,
            node_type=nt,
            title=node.title,
            impact_depth=depth,
            impact_score=impact_score,
            edge_path=edge_path,
            propagation_mode=prop_mode,
            requires_validation=requires_validation,
            requires_approval=requires_approval,
            requires_human=requires_human,
            is_blocked=is_blocked,
            is_no_op=prop_mode == "no_op",
            risk_class=risk_class,
        )

    def _compute_parallel_groups(self, visited: dict[str, int]) -> list[list[str]]:
        by_depth: dict[int, list[str]] = {}
        for nid, depth in visited.items():
            by_depth.setdefault(depth, []).append(nid)
        return [by_depth[d] for d in sorted(by_depth.keys())]

    def _find_reconvergence_points(self, visited: dict[str, int]) -> list[str]:
        reconvergence = []
        for nid in visited:
            in_edges = self._graph._adjacency_in.get(nid, [])
            affected_parents = sum(
                1 for eid in in_edges
                if self._graph.edges[eid].from_node_id in visited
            )
            if affected_parents > 1:
                reconvergence.append(nid)
        return reconvergence

    def _compute_risk_summary(self, analysis: ImpactAnalysis, event: ChangeEvent) -> dict[str, Any]:
        risk_counts: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
        for n in analysis.affected_nodes:
            risk_counts[n.risk_class] = risk_counts.get(n.risk_class, 0) + 1
        return {
            "event_risk_class": event.risk_class,
            "total_affected": len(analysis.affected_nodes),
            "direct_count": len(analysis.direct_impact),
            "indirect_count": len(analysis.indirect_impact),
            "approval_required_count": len(analysis.approval_required),
            "human_required_count": len(analysis.human_required),
            "validation_required_count": len(analysis.validation_required),
            "blocked_count": len(analysis.blocked_nodes),
            "no_op_count": len(analysis.no_op_nodes),
            "risk_distribution": risk_counts,
            "max_depth": analysis.impact_depth,
            "wave_count": analysis.required_waves,
        }
