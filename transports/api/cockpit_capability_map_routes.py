"""Cockpit Capability Map Routes — API surface for cockpit audit.

Exposes CockpitCapabilityMap: snapshot, surfaces, duplications, MVP gaps,
per-subsystem coverage, summary.

Campaign 3.1 — Cockpit Capability Map. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

capability_map_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    capability_map_router.include_router(_router)


def _get_map() -> Any:
    if not hasattr(_get_map, "_instance"):
        from substrate.workstation.cockpit_capability_map import CockpitCapabilityMap

        _get_map._instance = CockpitCapabilityMap()
    return _get_map._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.get("/capability-map/snapshot", dependencies=auth)
    async def snapshot() -> dict[str, Any]:
        return _get_map().snapshot().to_dict()

    @r.get("/capability-map/surfaces", dependencies=auth)
    async def list_surfaces(
        category: str | None = None,
        mvp_status: str | None = None,
    ) -> list[dict[str, Any]]:
        return [s.to_dict() for s in _get_map().surfaces(category=category, mvp_status=mvp_status)]

    @r.get("/capability-map/duplications", dependencies=auth)
    async def list_duplications() -> list[dict[str, Any]]:
        return [d.to_dict() for d in _get_map().duplications()]

    @r.get("/capability-map/mvp-gaps", dependencies=auth)
    async def list_mvp_gaps() -> list[dict[str, Any]]:
        return [s.to_dict() for s in _get_map().mvp_gaps()]

    @r.get("/capability-map/coverage/{subsystem}", dependencies=auth)
    async def coverage_for(subsystem: str) -> dict[str, Any]:
        return _get_map().coverage_for(subsystem)

    @r.get("/capability-map/summary", dependencies=auth)
    async def summary() -> dict[str, Any]:
        return _get_map().summary()

    return r
