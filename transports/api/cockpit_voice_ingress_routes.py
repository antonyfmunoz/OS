"""Cockpit routes for VoiceIngressRuntime — Campaign 20.0."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.voice_ingress_runtime import (
                VoiceIngressRuntime,
            )
            _runtime = VoiceIngressRuntime()
        except Exception:
            pass
    return _runtime


def get_router() -> APIRouter:
    router = APIRouter(prefix="/voice/ingress", tags=["voice-ingress"])

    @router.get("/status")
    def voice_ingress_status() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "VoiceIngressRuntime unavailable"}
        return rt.snapshot().to_dict()

    @router.get("/sources")
    def voice_ingress_sources() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"sources": []}
        return {"sources": rt.active_sources()}

    return router
