"""Cockpit routes for VoiceOperationsRuntime — Campaign 20.4."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from transports.api.governed import governed_mutation


class ProcessRequest(BaseModel):
    text: str = ""
    source_type: str = ""
    device_id: str = ""


_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.voice_operations_runtime import (
                VoiceOperationsRuntime,
            )
            _runtime = VoiceOperationsRuntime()
        except Exception:
            pass
    return _runtime


def get_router() -> APIRouter:
    router = APIRouter(prefix="/voice/operations", tags=["voice-operations"])

    @router.get("/snapshot")
    def voice_operations_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "VoiceOperationsRuntime unavailable"}
        return rt.snapshot().to_dict()

    @router.get("/health")
    def voice_operations_health() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"health": "offline"}
        return {"health": rt.health().value}

    @router.post("/process")
    def voice_operations_process(body: ProcessRequest) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "VoiceOperationsRuntime unavailable"}

        def _do_process():
            source_event = {"text": body.text, "source_type": body.source_type, "device_id": body.device_id}
            rt.process_utterance(source_event, body.text)
            return f"voice utterance processed: {body.text[:50]}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"process voice utterance: {body.text[:50]}",
            execute_fn=_do_process,
            source="cockpit",
        )
        return resp.to_http_dict()

    return router
