"""UMH API server — FastAPI surface matching existing UMH service conventions."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..protocols.signal import Signal, SignalSource, SignalUrgency
from .runtime import SubstrateRuntime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

_runtime = SubstrateRuntime()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _runtime.start()
    logger.info("UMH substrate runtime started")
    yield
    await _runtime.shutdown()
    logger.info("UMH substrate runtime shut down")


app = FastAPI(
    title="UMH — UMH Layer 0 Substrate",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://100.77.233.50:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SignalRequest(BaseModel):
    """Incoming signal payload for the intake endpoint."""

    source: SignalSource = SignalSource.EXTERNAL_API
    urgency: SignalUrgency = SignalUrgency.NORMAL
    content_type: str = Field(max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)
    raw_content: str | None = None
    source_identifier: str | None = None


class SignalResponse(BaseModel):
    """Response after signal intake."""

    signal_id: str
    trace_id: str
    status: str = "accepted"
    received_at: str


@app.get("/api/umh/health")
async def health():
    """Health check endpoint."""
    return _runtime.health()


@app.post("/api/umh/signal", response_model=SignalResponse)
async def signal_intake(req: SignalRequest):
    """Universal signal intake — all external input enters here."""
    if not _runtime.is_running:
        raise HTTPException(status_code=503, detail="Substrate runtime not started")

    signal = Signal(
        source=req.source,
        urgency=req.urgency,
        content_type=req.content_type,
        payload=req.payload,
        raw_content=req.raw_content,
        source_identifier=req.source_identifier,
    )

    trace = await _runtime.ingest_signal(signal)

    return SignalResponse(
        signal_id=str(signal.id),
        trace_id=str(trace.id),
        received_at=signal.received_at.isoformat(),
    )


@app.get("/api/umh/events")
async def recent_events(event_type: str | None = None, limit: int = 50):
    """View recent events on the bus."""
    events = _runtime.event_bus.recent_events(event_type=event_type, limit=limit)
    return [e.model_dump(mode="json") for e in events]


@app.get("/api/umh/violations")
async def violations():
    """View recorded invariant violations."""
    return [
        {"law": v.law.name, "severity": v.law.severity.value, "context": v.context}
        for v in _runtime.invariant_checker.violations
    ]


def get_runtime() -> SubstrateRuntime:
    """Access the runtime from other modules."""
    return _runtime
