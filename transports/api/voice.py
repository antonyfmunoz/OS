"""Voice session API — exposes the voice pipeline loop over HTTP.

Endpoints:
  POST /voice/session/start  — start a new voice session
  POST /voice/session/stop   — stop the active session
  POST /voice/process        — process text input (skip STT, for testing)
  GET  /voice/session/status — current session state
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from substrate.execution.voice.session import VoiceSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/umh/voice")

_session: VoiceSession | None = None
_pipeline_submit_fn: Any = None


def wire_pipeline(submit_fn: Any) -> None:
    """Inject the pipeline submit function for voice sessions."""
    global _pipeline_submit_fn
    _pipeline_submit_fn = submit_fn


class StartRequest(BaseModel):
    session_id: str = ""
    max_exchanges: int = Field(default=100, ge=1, le=1000)


class ProcessRequest(BaseModel):
    text: str = Field(max_length=2000, min_length=1)


@router.post("/session/start")
async def start_session(req: StartRequest):
    """Start a new voice session."""
    global _session
    if _session is not None and _session.state.status.value != "idle":
        raise HTTPException(status_code=409, detail="Session already active")

    _session = VoiceSession(
        session_id=req.session_id,
        pipeline_submit_fn=_pipeline_submit_fn,
        max_exchanges=req.max_exchanges,
    )
    _session.start()
    logger.info("Voice session started via API: %s", _session.state.session_id)
    return {"session_id": _session.state.session_id, "status": "listening"}


@router.post("/session/stop")
async def stop_session():
    """Stop the active voice session."""
    if _session is None:
        raise HTTPException(status_code=404, detail="No active session")

    _session.stop()
    exchange_count = _session.state.exchange_count
    return {"status": "stopped", "exchange_count": exchange_count}


@router.post("/process")
async def process_text(req: ProcessRequest):
    """Process text input through the voice pipeline (skip STT)."""
    if _session is None or _session.state.status.value == "idle":
        raise HTTPException(status_code=400, detail="No active session — call /session/start first")

    exchange = _session.process_text(req.text)
    return {
        "utterance": exchange.utterance,
        "classification": exchange.classification,
        "responded": exchange.responded,
        "response_text": exchange.response_text,
        "duration_ms": round(exchange.duration_ms, 1),
    }


@router.get("/session/status")
async def session_status():
    """Get current voice session state."""
    if _session is None:
        return {"active": False, "status": "idle"}

    state = _session.state.to_dict()
    state["active"] = _session.state.status.value != "idle"
    return state
