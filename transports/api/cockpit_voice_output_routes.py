"""Cockpit routes for VoiceOutputRuntime — Campaign 20.3."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.voice_output_runtime import (
                VoiceOutputRuntime,
            )
            _runtime = VoiceOutputRuntime()
        except Exception:
            pass
    return _runtime


def get_router() -> APIRouter:
    router = APIRouter(prefix="/voice/output", tags=["voice-output"])

    @router.get("/status")
    def voice_output_status() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "VoiceOutputRuntime unavailable"}
        return rt.snapshot().to_dict()

    return router
