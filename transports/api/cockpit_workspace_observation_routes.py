"""Cockpit workspace observation routes — live engineering runtime observation.

Mounted under /api/umh/ via include_router in cockpit.py.
All routes are GET (read-only). No mutations, no execution.

Phase 25. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

workspace_observation_router: APIRouter = APIRouter()

_configured: bool = False
_engine_instance: Any = None


def configure(require_operator_dep: Any) -> None:
    global _configured, workspace_observation_router
    _configured = True
    workspace_observation_router = _build_router(require_operator_dep)


def _get_engine() -> Any:
    global _engine_instance
    if _engine_instance is not None:
        return _engine_instance
    try:
        from substrate.meta_ide.workspace_observation import WorkspaceObservationEngine

        _engine_instance = WorkspaceObservationEngine()
        return _engine_instance
    except Exception as exc:
        logger.debug("workspace observation routes: failed to create engine: %s", exc)
        return None


def _get_probe() -> Any:
    try:
        from nodes.environments.workspace_probe import WorkspaceProbe

        return WorkspaceProbe()
    except Exception as exc:
        logger.debug("workspace observation routes: failed to create probe: %s", exc)
        return None


def _run_observation(engine: Any) -> dict[str, Any]:
    probe = _get_probe()
    probe_data: dict[str, list[dict[str, Any]]] = {}
    if probe is not None:
        try:
            probe_data = probe.probe_all()
        except Exception as exc:
            logger.debug("workspace observation probe failed: %s", exc)

    snap = engine.observe(
        terminal_data=probe_data.get("terminals"),
        container_data=probe_data.get("containers"),
        preview_data=probe_data.get("previews"),
    )
    return snap.to_dict()


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter(dependencies=[Depends(require_operator_dep)])

    @r.get("/meta-ide/workspace-observation")
    async def workspace_observation() -> dict[str, Any]:
        engine = _get_engine()
        if engine is None:
            return {"error": "workspace observation unavailable"}
        return _run_observation(engine)

    @r.get("/meta-ide/workspace-observation/terminals")
    async def terminals() -> dict[str, Any]:
        engine = _get_engine()
        if engine is None:
            return {"terminals": []}
        snap_data = _run_observation(engine)
        return {"terminals": snap_data.get("terminals", [])}

    @r.get("/meta-ide/workspace-observation/containers")
    async def containers() -> dict[str, Any]:
        engine = _get_engine()
        if engine is None:
            return {"containers": []}
        snap_data = _run_observation(engine)
        return {"containers": snap_data.get("containers", [])}

    @r.get("/meta-ide/workspace-observation/previews")
    async def previews() -> dict[str, Any]:
        engine = _get_engine()
        if engine is None:
            return {"previews": []}
        snap_data = _run_observation(engine)
        return {"previews": snap_data.get("previews", [])}

    @r.get("/meta-ide/workspace-observation/engineering-sessions")
    async def engineering_sessions() -> dict[str, Any]:
        engine = _get_engine()
        if engine is None:
            return {"engineering_sessions": []}
        snap_data = _run_observation(engine)
        return {"engineering_sessions": snap_data.get("engineering_sessions", [])}

    @r.get("/meta-ide/workspace-observation/history")
    async def observation_history(limit: int = 20) -> dict[str, Any]:
        engine = _get_engine()
        if engine is None:
            return {"history": []}
        clamped = max(1, min(limit, 100))
        snapshots = engine.history(limit=clamped)
        return {"history": [s.to_dict() for s in snapshots]}

    return r
