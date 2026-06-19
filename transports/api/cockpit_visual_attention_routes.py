"""Cockpit routes for AttentionVisionRuntime — Campaign 21.3."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.attention_vision_runtime import (
                AttentionVisionRuntime,
            )

            _runtime = AttentionVisionRuntime()
        except Exception:
            pass
    return _runtime


def get_router() -> APIRouter:
    router = APIRouter(prefix="/visual/attention", tags=["visual-attention"])

    @router.get("/snapshot")
    def attention_vision_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "AttentionVisionRuntime unavailable"}
        return rt.snapshot().to_dict()

    @router.get("/signals")
    def attention_vision_signals() -> list[dict[str, Any]]:
        rt = _get_runtime()
        if rt is None:
            return []
        return [s.to_dict() for s in rt.detect_visual_signals()]

    @router.get("/critical")
    def attention_vision_critical() -> list[dict[str, Any]]:
        rt = _get_runtime()
        if rt is None:
            return []
        return [s.to_dict() for s in rt.critical_signals()]

    return router
