"""Propagation Graph Builder — extracts nodes and edges from real system state.

Reads work packets, workcells, self-build items, roadmap phases, templates,
knowledge models, role contracts, production truth deltas, API routes,
and world model entities to build the propagation graph.

Phase 12.0. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from uuid import uuid4

from substrate.organism.propagation_graph import (
    PropagationGraph,
    PropagationNode,
    PropagationEdge,
    PropagationNodeType,
    PropagationEdgeType,
    PropagationMode,
    EdgeStrength,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class PropagationGraphBuilder:
    """Builds propagation graph from current system state."""

    def __init__(self, repo_root: str | None = None) -> None:
        self._root = repo_root or _REPO_ROOT
        self._graph = PropagationGraph()
        self._node_id_map: dict[str, str] = {}

    def build(self) -> PropagationGraph:
        self._graph = PropagationGraph()
        self._graph.built_at = time.time()
        self._node_id_map = {}

        self._extract_work_packets()
        self._extract_workcells()
        self._extract_self_build_items()
        self._extract_roadmap_phases()
        self._extract_templates()
        self._extract_knowledge_models()
        self._extract_role_contracts()
        self._extract_production_truth_deltas()
        self._extract_api_routes()
        self._extract_world_model_entities()
        self._extract_entity_metadata()

        self._link_packets_to_workcells()
        self._link_packets_to_roadmap()
        self._link_packets_to_self_build()
        self._link_roadmap_phases()
        self._link_production_truth()

        sources = []
        if self._graph.nodes:
            sources.append(f"{len(self._graph.nodes)} nodes")
        if self._graph.edges:
            sources.append(f"{len(self._graph.edges)} edges")
        self._graph.source_summary = f"Built from live system state: {', '.join(sources)}"

        return self._graph

    def _make_node_id(self, prefix: str, source_id: str) -> str:
        key = f"{prefix}:{source_id}"
        if key in self._node_id_map:
            return self._node_id_map[key]
        import hashlib
        short_hash = hashlib.sha256(source_id.encode()).hexdigest()[:10]
        node_id = f"pgn-{prefix}-{short_hash}"
        self._node_id_map[key] = node_id
        return node_id

    def _extract_work_packets(self) -> None:
        path = os.path.join(self._root, "data", "umh", "universal_work", "work_packets.jsonl")
        if not os.path.exists(path):
            return
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                pid = d.get("packet_id", "")
                node_id = self._make_node_id("wp", pid)
                node = PropagationNode(
                    node_id=node_id,
                    node_type=PropagationNodeType.WORK_PACKET,
                    title=d.get("title", ""),
                    description=d.get("user_intent", ""),
                    source_type="work_packet",
                    source_id=pid,
                    source_path=path,
                    domain=d.get("domain", ""),
                    projection=d.get("projection", ""),
                    status=d.get("status", ""),
                    metadata={
                        "risk_class": d.get("risk_class", ""),
                        "leverage_score": d.get("leverage_score", 0),
                    },
                    evidence=[{"type": "work_packet_store", "path": path}],
                )
                self._graph.add_node(node)

    def _extract_workcells(self) -> None:
        path = os.path.join(self._root, "data", "umh", "universal_work", "workcells.jsonl")
        if not os.path.exists(path):
            return
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                wid = d.get("workcell_id", "")
                node_id = self._make_node_id("wc", wid)
                node = PropagationNode(
                    node_id=node_id,
                    node_type=PropagationNodeType.WORKCELL,
                    title=d.get("title", ""),
                    description=d.get("brief", ""),
                    source_type="workcell",
                    source_id=wid,
                    source_path=path,
                    domain=d.get("domain", ""),
                    status=d.get("status", ""),
                    metadata={"packet_id": d.get("packet_id", "")},
                    evidence=[{"type": "workcell_store", "path": path}],
                )
                self._graph.add_node(node)
                for branch in d.get("advisor_branches", []):
                    adv_id = branch.get("advisor_id", "")
                    adv_node_id = self._make_node_id("adv", adv_id)
                    adv_node = PropagationNode(
                        node_id=adv_node_id,
                        node_type=PropagationNodeType.ADVISOR_BRANCH,
                        title=branch.get("perspective", ""),
                        source_type="advisor_branch",
                        source_id=adv_id,
                        status=branch.get("status", ""),
                        metadata={"workcell_id": wid},
                        evidence=[{"type": "workcell_store", "path": path}],
                    )
                    self._graph.add_node(adv_node)
                    self._graph.add_edge(PropagationEdge(
                        from_node_id=node_id,
                        to_node_id=adv_node_id,
                        edge_type=PropagationEdgeType.OWNS,
                        propagation_mode=PropagationMode.RECOMPUTE,
                        strength=EdgeStrength.HARD,
                        reason="workcell owns advisor branch",
                    ))

    def _extract_self_build_items(self) -> None:
        path = os.path.join(self._root, "data", "umh", "self_build", "work_items.jsonl")
        if not os.path.exists(path):
            return
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                sid = d.get("work_item_id", "")
                node_id = self._make_node_id("sb", sid)
                node = PropagationNode(
                    node_id=node_id,
                    node_type=PropagationNodeType.SELF_BUILD_ITEM,
                    title=d.get("title", ""),
                    description=d.get("description", ""),
                    source_type="self_build_item",
                    source_id=sid,
                    source_path=path,
                    domain="self_build",
                    status=d.get("status", ""),
                    metadata={"risk_class": d.get("risk_class", "")},
                    evidence=[{"type": "self_build_store", "path": path}],
                )
                self._graph.add_node(node)

    def _extract_roadmap_phases(self) -> None:
        path = os.path.join(self._root, "data", "umh", "self_build", "roadmap_phases.jsonl")
        if not os.path.exists(path):
            return
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                pid = d.get("phase_id", "")
                node_id = self._make_node_id("rp", pid)
                node = PropagationNode(
                    node_id=node_id,
                    node_type=PropagationNodeType.ROADMAP_PHASE,
                    title=d.get("title", ""),
                    description=d.get("objective", ""),
                    source_type="roadmap_phase",
                    source_id=pid,
                    source_path=path,
                    domain="roadmap",
                    status=d.get("status", ""),
                    metadata={
                        "prerequisites": d.get("prerequisites", []),
                        "success_criteria": d.get("success_criteria", []),
                    },
                    evidence=[{"type": "roadmap_store", "path": path}],
                )
                self._graph.add_node(node)

    def _extract_templates(self) -> None:
        path = os.path.join(self._root, "data", "umh", "autonomous_lane", "templates.jsonl")
        if not os.path.exists(path):
            return
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                tid = d.get("template_id", "")
                node_id = self._make_node_id("tmpl", tid)
                node = PropagationNode(
                    node_id=node_id,
                    node_type=PropagationNodeType.TEMPLATE,
                    title=d.get("title", d.get("pattern_name", "")),
                    source_type="template",
                    source_id=tid,
                    source_path=path,
                    status=d.get("status", ""),
                    metadata={"confidence": d.get("confidence", 0)},
                    evidence=[{"type": "template_store", "path": path}],
                )
                self._graph.add_node(node)

    def _extract_knowledge_models(self) -> None:
        path = os.path.join(self._root, "data", "umh", "universal_work", "knowledge_models.jsonl")
        if not os.path.exists(path):
            path2 = os.path.join(self._root, "data", "umh", "knowledge_models.jsonl")
            if not os.path.exists(path2):
                return
            path = path2
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                kid = d.get("model_id", d.get("knowledge_model_id", ""))
                node_id = self._make_node_id("km", kid)
                node = PropagationNode(
                    node_id=node_id,
                    node_type=PropagationNodeType.KNOWLEDGE_MODEL,
                    title=d.get("title", d.get("name", "")),
                    source_type="knowledge_model",
                    source_id=kid,
                    source_path=path,
                    domain=d.get("domain", ""),
                    status=d.get("status", ""),
                    evidence=[{"type": "knowledge_model_store", "path": path}],
                )
                self._graph.add_node(node)

    def _extract_role_contracts(self) -> None:
        path = os.path.join(self._root, "data", "umh", "universal_work", "role_contracts.jsonl")
        if not os.path.exists(path):
            return
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                rid = d.get("role_id", "")
                node_id = self._make_node_id("rc", rid)
                node = PropagationNode(
                    node_id=node_id,
                    node_type=PropagationNodeType.ROLE_CONTRACT,
                    title=d.get("title", d.get("role_name", "")),
                    source_type="role_contract",
                    source_id=rid,
                    source_path=path,
                    status=d.get("status", ""),
                    evidence=[{"type": "role_contract_store", "path": path}],
                )
                self._graph.add_node(node)

    def _extract_production_truth_deltas(self) -> None:
        verification_path = os.path.join(
            self._root, "data", "umh", "universal_work", "phase11_1r_production_verification.json",
        )
        if os.path.exists(verification_path):
            with open(verification_path) as f:
                d = json.load(f)
            ptd_id = d.get("production_truth_delta_id", "ptd-85fb7318")
            node_id = self._make_node_id("ptd", ptd_id)
            node = PropagationNode(
                node_id=node_id,
                node_type=PropagationNodeType.PRODUCTION_TRUTH_DELTA,
                title=f"Production Truth Delta {ptd_id}",
                description=f"PR #{d.get('pr', '')} merge verification",
                source_type="production_truth_delta",
                source_id=ptd_id,
                source_path=verification_path,
                domain="production",
                status="verified" if d.get("test_result") == "PASS" else "pending",
                metadata={
                    "pr": d.get("pr", ""),
                    "merge_commit": d.get("merge_commit_short", ""),
                    "files_match": d.get("files_match", False),
                    "py_compile_pass": d.get("py_compile_pass", False),
                },
                evidence=[{"type": "production_verification", "path": verification_path}],
            )
            self._graph.add_node(node)

            poc_id = "poc-532ce3d"
            poc_node_id = self._make_node_id("poc", poc_id)
            poc_node = PropagationNode(
                node_id=poc_node_id,
                node_type=PropagationNodeType.OUTCOME,
                title=f"ProductionOutcomeCommitted {poc_id}",
                description="Phase 11.1R production outcome",
                source_type="production_outcome",
                source_id=poc_id,
                domain="production",
                status="committed",
                evidence=[{"type": "production_verification", "path": verification_path}],
            )
            self._graph.add_node(poc_node)
            self._graph.add_edge(PropagationEdge(
                from_node_id=node_id,
                to_node_id=poc_node_id,
                edge_type=PropagationEdgeType.CREATES,
                propagation_mode=PropagationMode.NOTIFY_ONLY,
                strength=EdgeStrength.HARD,
                reason="PTD creates ProductionOutcomeCommitted",
            ))

    def _extract_api_routes(self) -> None:
        routes_file = os.path.join(
            self._root, "transports", "api", "cockpit_universal_work_routes.py",
        )
        if not os.path.exists(routes_file):
            return
        route_prefixes = [
            ("/organism/universal-work", "Universal Work Overview"),
            ("/organism/universal-work/summary", "Universal Work Summary"),
            ("/organism/universal-work/packets", "Work Packets List"),
            ("/organism/universal-work/next", "Next Best Packet"),
            ("/organism/universal-work/blocked", "Blocked Packets"),
            ("/organism/universal-work/human-required", "Human Required Packets"),
            ("/organism/universal-work/approval-required", "Approval Required Packets"),
            ("/organism/universal-work/create", "Create Packet"),
            ("/organism/universal-work/domain/{domain}", "Packets By Domain"),
            ("/organism/universal-work/packets/{packet_id}", "Packet Detail"),
        ]
        for route_path, title in route_prefixes:
            route_id = route_path.replace("/", "-").strip("-")
            node_id = self._make_node_id("api", route_id)
            node = PropagationNode(
                node_id=node_id,
                node_type=PropagationNodeType.API_ROUTE,
                title=title,
                description=f"API route: /api/umh{route_path}",
                source_type="api_route",
                source_id=route_id,
                source_path=routes_file,
                domain="api",
                status="active",
                evidence=[{"type": "route_file", "path": routes_file}],
            )
            self._graph.add_node(node)

    def _extract_world_model_entities(self) -> None:
        wm_path = os.path.join(self._root, "data", "umh", "world_model.json")
        if not os.path.exists(wm_path):
            return
        with open(wm_path) as f:
            data = json.load(f)
        for entity in data.get("entities", []):
            eid = entity.get("id", "")
            node_id = self._make_node_id("wme", eid)
            node = PropagationNode(
                node_id=node_id,
                node_type=PropagationNodeType.WORLD_MODEL_ENTITY,
                title=entity.get("name", ""),
                description=entity.get("description", ""),
                source_type="world_model_entity",
                source_id=eid,
                source_path=wm_path,
                domain=entity.get("category", ""),
                status=entity.get("status", ""),
                evidence=[{"type": "world_model", "path": wm_path}],
            )
            self._graph.add_node(node)

    def _extract_entity_metadata(self) -> None:
        path = os.path.join(self._root, "data", "umh", "config", "entity_metadata.json")
        if not os.path.exists(path):
            return
        with open(path) as f:
            data = json.load(f)
        for entity in data.get("entities", []):
            eid = entity.get("entity_id", entity.get("id", ""))
            etype = entity.get("type", "company")
            node_type_map = {
                "company": PropagationNodeType.COMPANY,
                "product": PropagationNodeType.PRODUCT,
                "offer": PropagationNodeType.OFFER,
                "entity": PropagationNodeType.ENTITY,
                "portfolio": PropagationNodeType.PORTFOLIO,
            }
            nt = node_type_map.get(etype, PropagationNodeType.ENTITY)
            node_id = self._make_node_id("ent", eid)
            node = PropagationNode(
                node_id=node_id,
                node_type=nt,
                title=entity.get("name", entity.get("title", "")),
                description=entity.get("description", ""),
                source_type="entity_metadata",
                source_id=eid,
                source_path=path,
                domain=entity.get("domain", ""),
                projection=entity.get("projection", ""),
                status=entity.get("status", "active"),
                evidence=[{"type": "entity_metadata", "path": path}],
            )
            self._graph.add_node(node)

    def _link_packets_to_workcells(self) -> None:
        for node in list(self._graph.nodes.values()):
            if node.node_type == PropagationNodeType.WORKCELL:
                packet_id = node.metadata.get("packet_id", "")
                if packet_id:
                    wp_key = f"wp:{packet_id}"
                    if wp_key in self._node_id_map:
                        wp_node_id = self._node_id_map[wp_key]
                        self._graph.add_edge(PropagationEdge(
                            from_node_id=wp_node_id,
                            to_node_id=node.node_id,
                            edge_type=PropagationEdgeType.OWNS,
                            propagation_mode=PropagationMode.RECOMPUTE,
                            strength=EdgeStrength.HARD,
                            reason="work packet owns workcell",
                        ))

    def _link_packets_to_roadmap(self) -> None:
        roadmap_nodes = [
            n for n in self._graph.nodes.values()
            if n.node_type == PropagationNodeType.ROADMAP_PHASE
        ]
        wp_nodes = [
            n for n in self._graph.nodes.values()
            if n.node_type == PropagationNodeType.WORK_PACKET
        ]
        for rp in roadmap_nodes:
            linked = rp.metadata.get("linked_work_items", [])
            for wp in wp_nodes:
                if wp.source_id in linked:
                    self._graph.add_edge(PropagationEdge(
                        from_node_id=rp.node_id,
                        to_node_id=wp.node_id,
                        edge_type=PropagationEdgeType.FEEDS,
                        propagation_mode=PropagationMode.RECOMPUTE,
                        strength=EdgeStrength.HARD,
                        reason="roadmap phase feeds work packet",
                    ))

    def _link_packets_to_self_build(self) -> None:
        for node in list(self._graph.nodes.values()):
            if node.node_type == PropagationNodeType.WORK_PACKET:
                if node.domain == "self_build" and node.metadata.get("source_id"):
                    sb_key = f"sb:{node.metadata['source_id']}"
                    if sb_key in self._node_id_map:
                        sb_node_id = self._node_id_map[sb_key]
                        self._graph.add_edge(PropagationEdge(
                            from_node_id=sb_node_id,
                            to_node_id=node.node_id,
                            edge_type=PropagationEdgeType.DERIVES_FROM,
                            propagation_mode=PropagationMode.RECOMPUTE,
                            strength=EdgeStrength.HARD,
                            reason="work packet derives from self-build item",
                        ))

    def _link_roadmap_phases(self) -> None:
        roadmap_nodes = {
            n.source_id: n for n in self._graph.nodes.values()
            if n.node_type == PropagationNodeType.ROADMAP_PHASE
        }
        for rp in roadmap_nodes.values():
            prereqs = rp.metadata.get("prerequisites", [])
            for prereq_id in prereqs:
                if prereq_id in roadmap_nodes:
                    self._graph.add_edge(PropagationEdge(
                        from_node_id=roadmap_nodes[prereq_id].node_id,
                        to_node_id=rp.node_id,
                        edge_type=PropagationEdgeType.UNLOCKS,
                        propagation_mode=PropagationMode.NOTIFY_ONLY,
                        strength=EdgeStrength.HARD,
                        reason="prerequisite phase unlocks this phase",
                    ))

    def _link_production_truth(self) -> None:
        ptd_nodes = [
            n for n in self._graph.nodes.values()
            if n.node_type == PropagationNodeType.PRODUCTION_TRUTH_DELTA
        ]
        api_nodes = [
            n for n in self._graph.nodes.values()
            if n.node_type == PropagationNodeType.API_ROUTE
        ]
        for ptd in ptd_nodes:
            for api in api_nodes:
                self._graph.add_edge(PropagationEdge(
                    from_node_id=ptd.node_id,
                    to_node_id=api.node_id,
                    edge_type=PropagationEdgeType.VALIDATES,
                    propagation_mode=PropagationMode.REVALIDATE,
                    strength=EdgeStrength.SOFT,
                    reason="production truth validates API routes",
                ))
