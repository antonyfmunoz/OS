"""Cockpit Organism Map Routes — unified topology for the organism map instrument.

Composes existing data from:
  - UMHNodeRegistry (nodes, services, capabilities)
  - ServiceDependencyGraph (dependencies, blast radius)
  - StateCoherenceEngine (domain authority, drift)
  - ServiceFailureEngine (health, active failures)

into a single graph-shaped API that the Organism Map panel consumes.
Click a node -> services/state/blast-radius/deps inline.

Gate 4 — Workstation Convergence. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

organism_map_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    organism_map_router.include_router(_router)


def _get_node_registry() -> Any:
    if not hasattr(_get_node_registry, "_instance"):
        try:
            from substrate.organism.umh_node_topology import UMHNodeRegistry
            _get_node_registry._instance = UMHNodeRegistry()
        except Exception:
            logger.debug("UMHNodeRegistry unavailable")
            _get_node_registry._instance = None
    return _get_node_registry._instance


def _get_service_graph() -> Any:
    if not hasattr(_get_service_graph, "_instance"):
        try:
            from substrate.organism.service_dependency_graph import ServiceDependencyGraph
            _get_service_graph._instance = ServiceDependencyGraph()
        except Exception:
            logger.debug("ServiceDependencyGraph unavailable")
            _get_service_graph._instance = None
    return _get_service_graph._instance


def _get_state_engine() -> Any:
    if not hasattr(_get_state_engine, "_instance"):
        try:
            from substrate.organism.state_coherence_engine import StateCoherenceEngine
            _get_state_engine._instance = StateCoherenceEngine()
        except Exception:
            logger.debug("StateCoherenceEngine unavailable")
            _get_state_engine._instance = None
    return _get_state_engine._instance


def _get_failure_engine() -> Any:
    if not hasattr(_get_failure_engine, "_instance"):
        try:
            from substrate.organism.service_failure_engine import ServiceFailureEngine
            _get_failure_engine._instance = ServiceFailureEngine()
        except Exception:
            logger.debug("ServiceFailureEngine unavailable")
            _get_failure_engine._instance = None
    return _get_failure_engine._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.get("/organism-map/topology", dependencies=auth)
    async def topology() -> dict[str, Any]:
        """Full organism topology — nodes + services + edges for graph rendering."""
        nodes_data: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        nr = _get_node_registry()
        if nr is not None:
            try:
                all_nodes = nr.all_nodes()
                for node in all_nodes:
                    nd = node.to_dict() if hasattr(node, "to_dict") else dict(node) if isinstance(node, dict) else {"id": str(node)}
                    nd["type"] = "node"
                    nodes_data.append(nd)
            except Exception:
                logger.debug("UMHNodeRegistry.all_nodes failed")

        sg = _get_service_graph()
        if sg is not None:
            try:
                services = sg.all_services()
                for svc in services:
                    sd = svc.to_dict() if hasattr(svc, "to_dict") else dict(svc) if isinstance(svc, dict) else {"id": str(svc)}
                    sd["type"] = "service"
                    nodes_data.append(sd)
            except Exception:
                logger.debug("ServiceDependencyGraph.all_services failed")

            try:
                deps = sg.all_dependencies()
                for dep in deps:
                    dd = dep.to_dict() if hasattr(dep, "to_dict") else dict(dep) if isinstance(dep, dict) else {}
                    edges.append(dd)
            except Exception:
                logger.debug("ServiceDependencyGraph.all_dependencies failed")

        return {
            "success": True,
            "nodes": nodes_data,
            "edges": edges,
            "node_count": len(nodes_data),
            "edge_count": len(edges),
        }

    @r.get("/organism-map/health", dependencies=auth)
    async def health() -> dict[str, Any]:
        """Organism health overlay — failures + coherence status."""
        failures: list[dict[str, Any]] = []
        coherence: dict[str, Any] = {}

        fe = _get_failure_engine()
        if fe is not None:
            try:
                active = fe.active_failures()
                if isinstance(active, list):
                    failures = [
                        f.to_dict() if hasattr(f, "to_dict") else dict(f) if isinstance(f, dict) else {"id": str(f)}
                        for f in active
                    ]
            except Exception:
                logger.debug("ServiceFailureEngine.active_failures failed")

        se = _get_state_engine()
        if se is not None:
            try:
                coh = se.coherence_status()
                coherence = coh.to_dict() if hasattr(coh, "to_dict") else dict(coh) if isinstance(coh, dict) else {}
            except Exception:
                logger.debug("StateCoherenceEngine.coherence_status failed")

        return {
            "success": True,
            "failures": failures,
            "failure_count": len(failures),
            "coherence": coherence,
            "healthy": len(failures) == 0,
        }

    @r.get("/organism-map/node/{node_id}", dependencies=auth)
    async def node_detail(node_id: str) -> dict[str, Any]:
        """Click a node -> services, state, blast radius, deps inline."""
        node_data: dict[str, Any] = {}
        services: list[dict[str, Any]] = []
        blast_radius: dict[str, Any] = {}
        state_domains: list[dict[str, Any]] = []

        nr = _get_node_registry()
        if nr is not None:
            try:
                node = nr.get_node(node_id)
                if node is not None:
                    node_data = node.to_dict() if hasattr(node, "to_dict") else dict(node) if isinstance(node, dict) else {}
            except Exception:
                logger.debug("UMHNodeRegistry.get_node failed")

            try:
                node_services = nr.services_for_node(node_id)
                services = [
                    s.to_dict() if hasattr(s, "to_dict") else dict(s) if isinstance(s, dict) else {"id": str(s)}
                    for s in node_services
                ]
            except Exception:
                logger.debug("UMHNodeRegistry.services_for_node failed")

        sg = _get_service_graph()
        if sg is not None:
            try:
                impact = sg.blast_radius(node_id)
                blast_radius = impact.to_dict() if hasattr(impact, "to_dict") else dict(impact) if isinstance(impact, dict) else {}
            except Exception:
                logger.debug("ServiceDependencyGraph.blast_radius failed for node")

        se = _get_state_engine()
        if se is not None:
            try:
                domains = se.domains_for_node(node_id)
                state_domains = [
                    d.to_dict() if hasattr(d, "to_dict") else dict(d) if isinstance(d, dict) else {"id": str(d)}
                    for d in domains
                ]
            except Exception:
                logger.debug("StateCoherenceEngine.domains_for_node failed")

        return {
            "success": True,
            "node": node_data,
            "services": services,
            "blast_radius": blast_radius,
            "state_domains": state_domains,
        }

    @r.get("/organism-map/service/{service_role}/blast-radius", dependencies=auth)
    async def service_blast_radius(service_role: str) -> dict[str, Any]:
        """Blast radius for a specific service."""
        sg = _get_service_graph()
        if sg is None:
            return {"success": True, "blast_radius": {}}
        try:
            impact = sg.blast_radius(service_role)
            result = impact.to_dict() if hasattr(impact, "to_dict") else dict(impact) if isinstance(impact, dict) else {}
            return {"success": True, "blast_radius": result}
        except Exception:
            logger.debug("ServiceDependencyGraph.blast_radius failed")
            return {"success": True, "blast_radius": {}}

    return r
