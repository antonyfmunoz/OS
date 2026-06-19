"""Cockpit routes for AmbientWakeRuntime — Campaign 20.2."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel


class WakeRequest(BaseModel):
    device_id: str = "local"
    phrase: str = ""


_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.ambient_wake_runtime import (
                AmbientWakeRuntime,
            )
            _runtime = AmbientWakeRuntime()
        except Exception:
            pass
    return _runtime


def get_router() -> APIRouter:
    router = APIRouter(prefix="/voice/ambient", tags=["voice-ambient"])

    @router.get("/status")
    def voice_ambient_status() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "AmbientWakeRuntime unavailable"}
        return rt.snapshot().to_dict()

    @router.post("/wake")
    def voice_ambient_wake(body: WakeRequest) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "AmbientWakeRuntime unavailable"}
        rt.activate()
        transition = rt.on_wake_detected(
            device_id=body.device_id, phrase=body.phrase,
        )
        return transition.to_dict()

    return router
