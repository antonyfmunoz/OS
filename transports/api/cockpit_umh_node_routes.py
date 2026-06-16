"""Cockpit UMH Node Topology Routes — read-only node topology API.

Exposes UMH organism node topology, service activation, and version
coherence through the cockpit API. All routes auth-protected.

Phase 28. Transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

umh_node_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    umh_node_router.include_router(_router)


def _get_registry() -> Any:
    if not hasattr(_get_registry, "_instance"):
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        _get_registry._instance = UMHNodeRegistry()
    return _get_registry._instance


def _get_coherence() -> Any:
    if not hasattr(_get_coherence, "_instance"):
        from substrate.organism.umh_version_coherence import UMHVersionCoherenceEngine

        _get_coherence._instance = UMHVersionCoherenceEngine(registry=_get_registry())
    return _get_coherence._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    router = APIRouter(
        prefix="/umh-nodes",
        tags=["umh-nodes"],
        dependencies=[Depends(require_operator_dep)],
    )

    @router.get("")
    async def node_topology() -> dict[str, Any]:
        reg = _get_registry()
        return reg.topology().to_dict()

    @router.get("/version/status")
    async def version_status() -> dict[str, Any]:
        engine = _get_coherence()
        return {"status": engine.overall_status().value}

    @router.get("/version/drift")
    async def version_drift() -> dict[str, Any]:
        engine = _get_coherence()
        return engine.drift_report()

    @router.get("/by-role/{role}")
    async def nodes_by_role(role: str) -> dict[str, Any]:
        reg = _get_registry()
        nodes = reg.nodes_for_role(role)
        return {"role": role, "nodes": [n.to_dict() for n in nodes]}

    @router.get("/by-service/{service_role}")
    async def nodes_by_service(service_role: str) -> dict[str, Any]:
        reg = _get_registry()
        nodes = reg.nodes_for_service(service_role)
        return {"service_role": service_role, "nodes": [n.to_dict() for n in nodes]}

    @router.get("/{node_id}")
    async def node_detail(node_id: str) -> dict[str, Any]:
        reg = _get_registry()
        node = reg.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        return node.to_dict()

    @router.get("/{node_id}/services")
    async def node_services(node_id: str) -> dict[str, Any]:
        reg = _get_registry()
        node = reg.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        return {
            "node_id": node_id,
            "services": [s.to_dict() for s in node.active_services],
        }

    return router
