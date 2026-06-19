"""Cockpit routes for EnvironmentAwarenessRuntime — Campaign 21.1."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.environment_awareness_runtime import (
                EnvironmentAwarenessRuntime,
            )

            _runtime = EnvironmentAwarenessRuntime()
        except Exception:
            pass
    return _runtime


def get_router() -> APIRouter:
    router = APIRouter(prefix="/visual/environment", tags=["visual-environment"])

    @router.get("/snapshot")
    def environment_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "EnvironmentAwarenessRuntime unavailable"}
        return rt.snapshot().to_dict()

    @router.get("/surfaces")
    def environment_surfaces() -> list[dict[str, Any]]:
        rt = _get_runtime()
        if rt is None:
            return []
        return [s.to_dict() for s in rt.surfaces()]

    @router.get("/active")
    def environment_active() -> list[dict[str, Any]]:
        rt = _get_runtime()
        if rt is None:
            return []
        return [s.to_dict() for s in rt.active_surfaces()]

    return router
