"""Cockpit routes for Workstation Presence — Campaign 17.2."""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from transports.api.governed import governed_mutation

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
    def workstation_presence_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "workstation presence not available"}
        return rt.snapshot().to_dict()

    @router.post("/panel")
    def workstation_presence_panel(body: PanelUpdate) -> dict[str, Any]:
        def _do():
            rt = _get_runtime()
            if rt is None:
                return "workstation presence not available", False
            rt.update_panel(body.panel_id)
            return f"panel updated to {body.panel_id}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"update workstation panel to {body.panel_id}",
            execute_fn=_do,
            source="cockpit",
        )
        return resp.to_http_dict()

    @router.post("/device")
    def workstation_presence_device(body: DeviceUpdate) -> dict[str, Any]:
        def _do():
            rt = _get_runtime()
            if rt is None:
                return "workstation presence not available", False
            rt.update_device(body.device_id)
            return f"device updated to {body.device_id}", True

        resp = governed_mutation(
            mutation_name="adapter_update",
            intent=f"update workstation device to {body.device_id}",
            execute_fn=_do,
            source="cockpit",
        )
        return resp.to_http_dict()

    @router.post("/context")
    def workstation_presence_context(body: ContextUpdate) -> dict[str, Any]:
        def _do():
            rt = _get_runtime()
            if rt is None:
                return "workstation presence not available", False
            rt.update_context(body.ctx)
            return "context updated", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent="update workstation context",
            execute_fn=_do,
            source="cockpit",
        )
        return resp.to_http_dict()

    return router
