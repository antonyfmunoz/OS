"""Cockpit routes for Workspace Topology (Phase 27).

Read-only workspace topology: graph, health, runtimes, repositories,
build targets. Follows standard configure() + _build_router() pattern.

UMH transport layer.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

workspace_topology_router: APIRouter = APIRouter()

_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True

    _router = _build_router(require_operator_dep)
    workspace_topology_router.include_router(_router)


def _get_engine() -> Any:
    from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

    if not hasattr(_get_engine, "_instance"):
        _get_engine._instance = WorkspaceTopologyEngine()
    return _get_engine._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    router = APIRouter(
        prefix="/workspace-topology",
        tags=["workspace-topology"],
        dependencies=[Depends(require_operator_dep)],
    )

    @router.get("")
    async def get_topology() -> dict[str, Any]:
        engine = _get_engine()
        graph = engine.topology()
        return graph.to_dict()

    @router.get("/{workspace_id}")
    async def get_workspace(workspace_id: str) -> dict[str, Any]:
        engine = _get_engine()
        summary = engine.workspace_summary(workspace_id)
        if not summary:
            raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")
        return summary

    @router.get("/{workspace_id}/health")
    async def get_workspace_health(workspace_id: str) -> dict[str, Any]:
        engine = _get_engine()
        ws = engine.registry.get(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")
        health = engine.workspace_health(workspace_id)
        return {"workspace_id": workspace_id, "health": health.value}

    @router.get("/{workspace_id}/runtimes")
    async def get_workspace_runtimes(workspace_id: str) -> dict[str, Any]:
        engine = _get_engine()
        ws = engine.registry.get(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")
        return {
            "workspace_id": workspace_id,
            "runtimes": [r.to_dict() for r in ws.runtimes],
            "count": len(ws.runtimes),
        }

    @router.get("/{workspace_id}/repositories")
    async def get_workspace_repositories(workspace_id: str) -> dict[str, Any]:
        engine = _get_engine()
        ws = engine.registry.get(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")
        return {
            "workspace_id": workspace_id,
            "repositories": [r.to_dict() for r in ws.repositories],
            "count": len(ws.repositories),
        }

    @router.get("/{workspace_id}/build-targets")
    async def get_workspace_build_targets(workspace_id: str) -> dict[str, Any]:
        engine = _get_engine()
        ws = engine.registry.get(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")
        return {
            "workspace_id": workspace_id,
            "build_targets": [b.to_dict() for b in ws.build_targets],
            "count": len(ws.build_targets),
        }

    return router
