"""Cockpit routes for Workstation Presence — Campaign 17.2."""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ── Lazy Singleton ───────────────────────────────────────────────────────

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.workstation_presence_runtime import (
                WorkstationPresenceRuntime,
            )

            _runtime = WorkstationPresenceRuntime()
        except Exception:
            logger.debug("Failed to init WorkstationPresenceRuntime", exc_info=True)
    return _runtime


# ── Request Models ───────────────────────────────────────────────────────


class PanelUpdate(BaseModel):
    panel_id: str


class DeviceUpdate(BaseModel):
    device_id: str


class ContextUpdate(BaseModel):
    ctx: dict[str, Any]


# ── Router ────────────────────────────────────────────────────────────────


def get_router():
    from fastapi import APIRouter

    router = APIRouter(prefix="/workstation-presence", tags=["workstation-presence"])

    @router.get("/snapshot")
    async def workstation_presence_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "workstation presence not available"}
        return rt.snapshot().to_dict()

    @router.post("/panel")
    async def workstation_presence_panel(body: PanelUpdate) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "workstation presence not available"}
        rt.update_panel(body.panel_id)
        return {"ok": True, "panel_id": body.panel_id}

    @router.post("/device")
    async def workstation_presence_device(body: DeviceUpdate) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "workstation presence not available"}
        rt.update_device(body.device_id)
        return {"ok": True, "device_id": body.device_id}

    @router.post("/context")
    async def workstation_presence_context(body: ContextUpdate) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "workstation presence not available"}
        rt.update_context(body.ctx)
        return {"ok": True}

    return router
