"""Cockpit routes for AgentWorkforceRuntime — Campaign 19.1."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.agent_workforce_runtime import (
                AgentWorkforceRuntime,
            )
            _runtime = AgentWorkforceRuntime()
        except Exception:
            pass
    return _runtime


def get_router() -> APIRouter:
    router = APIRouter(prefix="/agent-workforce", tags=["agent-workforce"])

    @router.get("/snapshot")
    def get_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "AgentWorkforceRuntime unavailable"}
        return rt.snapshot().to_dict()

    @router.get("/health")
    def get_health() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"health": "unknown"}
        return {"health": rt.health().value}

    @router.get("/idle")
    def get_idle() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"idle": []}
        return {"idle": rt.idle()}

    @router.get("/overloaded")
    def get_overloaded() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"overloaded": []}
        return {"overloaded": rt.overloaded()}

    @router.get("/pending")
    def get_pending() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"pending": []}
        return {"pending": rt.pending_delegations()}

    @router.get("/gaps")
    def get_gaps() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"gaps": []}
        return {"gaps": rt.capability_gaps()}

    return router
