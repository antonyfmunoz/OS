"""Cockpit routes for UnifiedWorkstationRuntime — Campaign 18.0."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.unified_workstation_runtime import (
                UnifiedWorkstationRuntime,
            )
            _runtime = UnifiedWorkstationRuntime()
        except Exception:
            pass
    return _runtime


def get_router() -> APIRouter:
    router = APIRouter(prefix="/unified-workstation", tags=["unified-workstation"])

    @router.get("/snapshot")
    def get_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "UnifiedWorkstationRuntime unavailable"}
        return rt.snapshot().to_dict()

    @router.get("/mode")
    def get_mode() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"state": "unknown"}
        return {"state": rt.mode()}

    @router.get("/attention")
    def get_attention() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"items": []}
        return {"items": rt.attention()}

    @router.get("/risks")
    def get_risks() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"risks": []}
        return {"risks": rt.risks()}

    @router.get("/summary")
    def get_summary() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "UnifiedWorkstationRuntime unavailable"}
        return rt.summary()

    return router
