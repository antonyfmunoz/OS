"""Cockpit routes for VoiceSessionManager — Campaign 20.1."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from transports.api.governed import governed_mutation


class SessionStartRequest(BaseModel):
    source_type: str = "right_rail"
    device_id: str = ""
    speaker_id: str = ""
    activation_mode: str = ""


_manager: Any = None


def _get_manager() -> Any:
    global _manager
    if _manager is None:
        try:
            from substrate.workstation.voice_session_manager import (
                VoiceSessionManager,
            )
            _manager = VoiceSessionManager()
        except Exception:
            pass
    return _manager


def get_router() -> APIRouter:
    router = APIRouter(prefix="/voice/sessions", tags=["voice-sessions"])

    @router.get("")
    def voice_sessions_list() -> dict[str, Any]:
        mgr = _get_manager()
        if mgr is None:
            return {"error": "VoiceSessionManager unavailable"}
        return mgr.snapshot().to_dict()

    @router.post("/start")
    def voice_session_start(body: SessionStartRequest) -> dict[str, Any]:
        mgr = _get_manager()
        if mgr is None:
            return {"error": "VoiceSessionManager unavailable"}

        def _do_start():
            from substrate.workstation.voice_ingress_runtime import (
                VoiceIngressEvent,
            )
            event = VoiceIngressEvent(
                source_type=body.source_type,
                device_id=body.device_id,
                speaker_id=body.speaker_id,
                activation_mode=body.activation_mode,
            )
            mgr.start_session(event)
            return "voice session started", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"start voice session: {body.source_type}",
            execute_fn=_do_start,
            source="cockpit",
        )
        return resp.to_http_dict()

    @router.post("/{session_id}/end")
    def voice_session_end(session_id: str) -> dict[str, Any]:
        mgr = _get_manager()
        if mgr is None:
            return {"error": "VoiceSessionManager unavailable"}

        def _do_end():
            success = mgr.end_session(session_id)
            return f"voice session {session_id} ended", success

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"end voice session {session_id}",
            execute_fn=_do_end,
            source="cockpit",
        )
        return resp.to_http_dict()

    return router
