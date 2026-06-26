"""Cockpit Infrastructure Routes — API surface for infrastructure registry.

Exposes InfrastructureRuntime operations: register, list, get, lineage,
health, dependencies.

Answers operator question #12: "What infrastructure exists?"

Gate 7 — Infrastructure Runtime. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

infrastructure_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    infrastructure_router.include_router(_router)


def _get_runtime() -> Any:
    if not hasattr(_get_runtime, "_instance"):
        from substrate.organism.infrastructure_runtime import InfrastructureRuntime

        _get_runtime._instance = InfrastructureRuntime()
    return _get_runtime._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.get("/infrastructure", dependencies=auth)
    def list_infrastructure(
        infra_type: str | None = None,
        health: str | None = None,
        system_only: bool = False,
        institutional_only: bool = False,
    ) -> dict[str, Any]:
        from substrate.organism.infrastructure_runtime import (
            InfrastructureHealth,
            InfrastructureType,
        )

        rt = _get_runtime()
        it = None
        if infra_type:
            try:
                it = InfrastructureType(infra_type)
            except ValueError:
                return {"error": f"invalid infra_type: {infra_type}"}
        h = None
        if health:
            try:
                h = InfrastructureHealth(health)
            except ValueError:
                return {"error": f"invalid health: {health}"}
        entities = rt.list_entities(
            infra_type=it,
            health=h,
            system_only=system_only,
            institutional_only=institutional_only,
        )
        return {"infrastructure": [e.to_dict() for e in entities], "count": len(entities)}

    @r.get("/infrastructure/summary", dependencies=auth)
    def infrastructure_summary() -> dict[str, Any]:
        return _get_runtime().summary()

    @r.get("/infrastructure/health", dependencies=auth)
    def infrastructure_health() -> dict[str, Any]:
        return _get_runtime().health_check()

    @r.get("/infrastructure/{infra_id}", dependencies=auth)
    def get_infrastructure(infra_id: str) -> dict[str, Any]:
        rt = _get_runtime()
        ent = rt.get(infra_id)
        if ent is None:
            return {"error": f"infrastructure {infra_id} not found"}
        return {
            "infrastructure": ent.to_dict(),
            "lineage": rt.full_lineage(infra_id),
            "dependents": rt.dependents_of(infra_id),
            "dependencies": rt.dependencies_of(infra_id),
        }

    @r.post("/infrastructure/register", dependencies=auth)
    async def register_infrastructure(request: Request) -> dict[str, Any]:
        from substrate.organism.infrastructure_runtime import (
            InfrastructureHealth,
            InfrastructureType,
        )

        body = await request.json()
        name = body.get("name", "")
        if not name:
            return {"error": "name is required"}
        it_str = body.get("infra_type", "runtime")
        try:
            it = InfrastructureType(it_str)
        except ValueError:
            return {"error": f"invalid infra_type: {it_str}"}
        h_str = body.get("health", "unknown")
        try:
            h = InfrastructureHealth(h_str)
        except ValueError:
            h = InfrastructureHealth.UNKNOWN
        rt = _get_runtime()
        ent = rt.register(
            name=name,
            infra_type=it,
            description=body.get("description", ""),
            origin_capability_ids=body.get("origin_capability_ids"),
            operationalization_ids=body.get("operationalization_ids"),
            health=h,
            dependencies=body.get("dependencies"),
            evidence=body.get("evidence"),
        )
        return {"infrastructure": ent.to_dict()}

    @r.post("/infrastructure/sync/services", dependencies=auth)
    def sync_from_services() -> dict[str, Any]:
        count = _get_runtime().sync_from_service_graph()
        return {"synced": count}

    @r.post("/infrastructure/sync/nodes", dependencies=auth)
    def sync_from_nodes() -> dict[str, Any]:
        count = _get_runtime().sync_from_node_registry()
        return {"synced": count}

    return r
