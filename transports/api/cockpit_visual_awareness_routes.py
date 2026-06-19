"""Cockpit routes for ScreenAwarenessRuntime — Campaign 21.0."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.screen_awareness_runtime import (
                ScreenAwarenessRuntime,
            )

            _runtime = ScreenAwarenessRuntime()
        except Exception:
            pass
    return _runtime


def get_router() -> APIRouter:
    router = APIRouter(prefix="/visual/awareness", tags=["visual-awareness"])

    @router.get("/snapshot")
    def visual_awareness_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "ScreenAwarenessRuntime unavailable"}
        return rt.snapshot().to_dict()

    @router.get("/health")
    def visual_awareness_health() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"health": "offline"}
        return {"health": rt.health().value}

    @router.get("/screen")
    def visual_awareness_screen() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "ScreenAwarenessRuntime unavailable"}
        return rt.current_screen()

    @router.get("/application")
    def visual_awareness_application() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "ScreenAwarenessRuntime unavailable"}
        return rt.application()

    @router.get("/repository")
    def visual_awareness_repository() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "ScreenAwarenessRuntime unavailable"}
        return rt.repository()

    return router
