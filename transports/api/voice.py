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

from transports.api.governed import governed_mutation
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

    def _do_start():
        global _session
        _session = VoiceSession(
            session_id=req.session_id,
            pipeline_submit_fn=_pipeline_submit_fn,
            max_exchanges=req.max_exchanges,
        )
        _session.start()
        return f"voice session started: {_session.state.session_id}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent="start voice session",
        execute_fn=_do_start,
        source="cockpit",
    )
    return resp.to_http_dict()


@router.post("/session/stop")
async def stop_session():
    """Stop the active voice session."""
    if _session is None:
        raise HTTPException(status_code=404, detail="No active session")

    def _do_stop():
        _session.stop()
        return f"voice session stopped, {_session.state.exchange_count} exchanges", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent="stop voice session",
        execute_fn=_do_stop,
        source="cockpit",
    )
    return resp.to_http_dict()


@router.post("/process")
async def process_text(req: ProcessRequest):
    """Process text input through the voice pipeline (skip STT)."""
    if _session is None or _session.state.status.value == "idle":
        raise HTTPException(status_code=400, detail="No active session — call /session/start first")

    def _do_process():
        exchange = _session.process_text(req.text)
        return f"processed: {exchange.classification}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"process voice text: {req.text[:50]}",
        execute_fn=_do_process,
        source="cockpit",
    )
    return resp.to_http_dict()


@router.get("/session/status")
async def session_status():
    """Get current voice session state."""
    if _session is None:
        return {"active": False, "status": "idle"}

    state = _session.state.to_dict()
    state["active"] = _session.state.status.value != "idle"
    return state
