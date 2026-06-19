"""Cockpit routes for SessionMachineRuntime — Campaign 19.2."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.session_machine_runtime import (
                SessionMachineRuntime,
            )
            _runtime = SessionMachineRuntime()
        except Exception:
            pass
    return _runtime


def get_router() -> APIRouter:
    router = APIRouter(prefix="/session-machine", tags=["session-machine"])

    @router.get("/snapshot")
    def get_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "SessionMachineRuntime unavailable"}
        return rt.snapshot().to_dict()

    @router.get("/bindings")
    def get_bindings() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"bindings": []}
        return {"bindings": [b.to_dict() for b in rt.bindings()]}

    @router.get("/workspaces")
    def get_workspaces() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"workspaces": []}
        return {"workspaces": rt.active_workspaces()}

    @router.get("/primary")
    def get_primary() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"primary": None}
        return {"primary": rt.primary_session()}

    @router.get("/handoffs")
    def get_handoffs() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"handoffs": []}
        return {"handoffs": rt.pending_handoffs()}

    return router
