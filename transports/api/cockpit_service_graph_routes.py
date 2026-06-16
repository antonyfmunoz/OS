"""Cockpit Service Graph Routes — read-only service dependency API.

Exposes service dependency graph, failure impact analysis, and
critical path through the cockpit API. All routes auth-protected.

Phase 30. Transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

service_graph_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    service_graph_router.include_router(_router)


def _get_registry() -> Any:
    if not hasattr(_get_registry, "_instance"):
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        _get_registry._instance = ServiceDependencyRegistry()
    return _get_registry._instance


def _get_engine() -> Any:
    if not hasattr(_get_engine, "_instance"):
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        _get_engine._instance = ServiceFailureEngine(registry=_get_registry())
    return _get_engine._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    router = APIRouter(
        prefix="/service-graph",
        tags=["service-graph"],
        dependencies=[Depends(require_operator_dep)],
    )

    @router.get("")
    async def service_graph_topology() -> dict[str, Any]:
        reg = _get_registry()
        return reg.topology().to_dict()

    @router.get("/services")
    async def all_services() -> dict[str, Any]:
        reg = _get_registry()
        services = reg.list_services()
        return {
            "service_count": len(services),
            "services": [s.to_dict() for s in services],
        }

    @router.get("/dependencies")
    async def all_dependencies() -> dict[str, Any]:
        reg = _get_registry()
        topo = reg.topology()
        return {
            "dependency_count": len(topo.dependencies),
            "dependencies": [d.to_dict() for d in topo.dependencies],
        }

    @router.get("/impact/{service_role}")
    async def failure_impact(service_role: str) -> dict[str, Any]:
        reg = _get_registry()
        svc = reg.get_service(service_role)
        if not svc:
            raise HTTPException(
                status_code=404, detail=f"Service {service_role} not found"
            )
        engine = _get_engine()
        impact = engine.failure_impact(service_role)
        return impact.to_dict()

    @router.get("/critical-path")
    async def critical_path() -> dict[str, Any]:
        engine = _get_engine()
        path = engine.critical_path()
        return {"services": path}

    @router.get("/leaf-services")
    async def leaf_services() -> dict[str, Any]:
        engine = _get_engine()
        leaves = engine.leaf_services()
        return {"leaf_services": leaves, "count": len(leaves)}

    @router.get("/health")
    async def service_health() -> dict[str, Any]:
        engine = _get_engine()
        return engine.organism_health()

    return router
