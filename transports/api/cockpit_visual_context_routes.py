"""Cockpit routes for VisualContextRuntime — Campaign 21.2."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.visual_context_runtime import (
                VisualContextRuntime,
            )

            _runtime = VisualContextRuntime()
        except Exception:
            pass
    return _runtime


def get_router() -> APIRouter:
    router = APIRouter(prefix="/visual/context", tags=["visual-context"])

    @router.get("/snapshot")
    def visual_context_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "VisualContextRuntime unavailable"}
        return rt.snapshot().to_dict()

    @router.get("/binding")
    def visual_context_binding() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "VisualContextRuntime unavailable"}
        return rt.resolve_context().to_dict()

    @router.get("/continue")
    def visual_context_continue() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "VisualContextRuntime unavailable"}
        return rt.continue_work()

    @router.get("/depth")
    def visual_context_depth() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "VisualContextRuntime unavailable"}
        return {"depth": rt.binding_depth().value}

    return router
