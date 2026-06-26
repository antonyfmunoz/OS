"""Cockpit Projection Integration Routes — API surface for projection audit.

Exposes ProjectionIntegrationRuntime: profiles, locations, gaps, readiness,
audit, location registration.

Campaign 3.5 — Projection Integration Runtime. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

projection_integration_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    projection_integration_router.include_router(_router)


def _get_runtime() -> Any:
    if not hasattr(_get_runtime, "_instance"):
        from substrate.organism.projection_integration_runtime import (
            ProjectionIntegrationRuntime,
        )

        _get_runtime._instance = ProjectionIntegrationRuntime()
    return _get_runtime._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.get("/projections/integration", dependencies=auth)
    def list_profiles() -> list[dict[str, Any]]:
        snap = _get_runtime().snapshot()
        return [p.to_dict() for p in snap.projections]

    @r.get("/projections/integration/snapshot", dependencies=auth)
    def snapshot() -> dict[str, Any]:
        return _get_runtime().snapshot().to_dict()

    @r.get("/projections/integration/{projection_id}", dependencies=auth)
    def projection_profile(projection_id: str) -> dict[str, Any]:
        return _get_runtime().projection_profile(projection_id).to_dict()

    @r.get("/projections/integration/{projection_id}/locations", dependencies=auth)
    def code_locations(projection_id: str) -> list[dict[str, Any]]:
        return [loc.to_dict() for loc in _get_runtime().code_locations(projection_id)]

    @r.get("/projections/integration/{projection_id}/gaps", dependencies=auth)
    def integration_gaps(projection_id: str) -> list[dict[str, Any]]:
        return [g.to_dict() for g in _get_runtime().integration_gaps(projection_id)]

    @r.get("/projections/integration/{projection_id}/readiness", dependencies=auth)
    def build_readiness(projection_id: str) -> dict[str, Any]:
        return _get_runtime().build_readiness(projection_id).to_dict()

    @r.post("/projections/integration/{projection_id}/location", dependencies=auth)
    async def register_location(projection_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        loc = _get_runtime().register_projection_location(
            projection_id=projection_id,
            machine=body.get("machine", "unknown"),
            root_path=body.get("root_path", ""),
            repo_url=body.get("repo_url", ""),
            branch=body.get("branch", ""),
            metadata=body.get("metadata"),
        )
        return loc.to_dict()

    @r.post("/projections/integration/{projection_id}/audit", dependencies=auth)
    def audit_projection(projection_id: str) -> dict[str, Any]:
        return _get_runtime().audit_projection(projection_id).to_dict()

    return r
