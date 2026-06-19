"""Cockpit routes for VoiceSessionManager — Campaign 20.1."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel


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
        try:
            from substrate.workstation.voice_ingress_runtime import (
                VoiceIngressEvent,
            )
            event = VoiceIngressEvent(
                source_type=body.source_type,
                device_id=body.device_id,
                speaker_id=body.speaker_id,
                activation_mode=body.activation_mode,
            )
            session = mgr.start_session(event)
            return session.to_dict()
        except Exception as exc:
            return {"error": str(exc)}

    @router.post("/{session_id}/end")
    def voice_session_end(session_id: str) -> dict[str, Any]:
        mgr = _get_manager()
        if mgr is None:
            return {"error": "VoiceSessionManager unavailable"}
        success = mgr.end_session(session_id)
        return {"ended": success, "session_id": session_id}

    return router
