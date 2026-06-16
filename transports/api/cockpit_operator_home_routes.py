"""Cockpit Operator Home Routes — unified operator context API.

Exposes the aggregation façade through the cockpit API.
All routes auth-protected. Read-only.

Phase 31. Transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

operator_home_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    operator_home_router.include_router(_router)


def _get_engine() -> Any:
    if not hasattr(_get_engine, "_instance"):
        from substrate.operator.operator_context_engine import OperatorContextEngine

        _get_engine._instance = OperatorContextEngine()
    return _get_engine._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    router = APIRouter(
        prefix="/operator",
        tags=["operator-home"],
        dependencies=[Depends(require_operator_dep)],
    )

    @router.get("/home")
    async def operator_home() -> dict[str, Any]:
        engine = _get_engine()
        return engine.snapshot().to_dict()

    @router.get("/health")
    async def operator_health() -> dict[str, Any]:
        engine = _get_engine()
        return engine.health_summary().to_dict()

    @router.get("/attention")
    async def operator_attention() -> dict[str, Any]:
        engine = _get_engine()
        items = engine.attention_items()
        return {
            "count": len(items),
            "items": [i.to_dict() for i in items],
        }

    @router.get("/timeline")
    async def operator_timeline() -> dict[str, Any]:
        engine = _get_engine()
        events = engine.timeline()
        return {
            "count": len(events),
            "events": [e.to_dict() for e in events],
        }

    @router.get("/approvals")
    async def operator_approvals() -> dict[str, Any]:
        engine = _get_engine()
        return engine.pending_approvals()

    @router.get("/services")
    async def operator_services() -> dict[str, Any]:
        engine = _get_engine()
        alerts = engine.service_alerts()
        return {
            "count": len(alerts),
            "alerts": alerts,
        }

    @router.get("/nodes")
    async def operator_nodes() -> dict[str, Any]:
        engine = _get_engine()
        nodes = engine.node_status()
        return {
            "count": len(nodes),
            "nodes": nodes,
        }

    @router.get("/workspaces")
    async def operator_workspaces() -> dict[str, Any]:
        engine = _get_engine()
        workspaces = engine.active_workspaces()
        return {
            "count": len(workspaces),
            "workspaces": workspaces,
        }

    return router
