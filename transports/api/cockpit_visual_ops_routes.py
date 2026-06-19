"""Cockpit routes for VisualOperationsRuntime — Campaign 21.4."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.visual_operations_runtime import (
                VisualOperationsRuntime,
            )

            _runtime = VisualOperationsRuntime()
        except Exception:
            pass
    return _runtime


def get_router() -> APIRouter:
    router = APIRouter(prefix="/visual/operations", tags=["visual-operations"])

    @router.get("/snapshot")
    def visual_ops_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "VisualOperationsRuntime unavailable"}
        return rt.snapshot().to_dict()

    @router.get("/health")
    def visual_ops_health() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"health": "offline"}
        return {"health": rt.health().value}

    @router.get("/what-am-i-looking-at")
    def what_am_i_looking_at() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "VisualOperationsRuntime unavailable"}
        return rt.what_am_i_looking_at()

    @router.get("/continue")
    def continue_work() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "VisualOperationsRuntime unavailable"}
        return rt.continue_this_work()

    @router.get("/errors")
    def error_awareness() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "VisualOperationsRuntime unavailable"}
        return rt.error_awareness()

    @router.get("/surfaces")
    def all_surfaces() -> list[dict[str, Any]]:
        rt = _get_runtime()
        if rt is None:
            return []
        return rt.all_surfaces()

    @router.get("/capabilities")
    def capabilities() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "VisualOperationsRuntime unavailable"}
        return rt.capabilities().to_dict()

    return router
