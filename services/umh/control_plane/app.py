"""UMH API server — FastAPI surface matching existing UMH service conventions."""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..governance.risk_classes import RiskClass
from ..protocols.signal import Signal, SignalSource, SignalUrgency
from ..sockets.capability_socket import CapabilitySocket
from ..sockets.envelopes import OutcomeEnvelope
from ..sockets.outcome_socket import OutcomeSocket
from ..sockets.registry import IntegrationManifest, IntegrationRegistry
from ..sockets.signal_socket import SignalSocket
from ..sockets.view.broadcaster import ViewFrameBroadcaster, make_pipeline_listener
from ..sockets.view.websocket import broadcast_frame, ws_endpoint
from ..sockets.view_socket import ViewSocket
from ..execution.executor import build_default_executor
from ..integrations.notion.correlation import CorrelationMap, WritebackTarget
from .pipeline import ExecutionPipeline
from .runtime import SubstrateRuntime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

_runtime = SubstrateRuntime()
_view_socket = ViewSocket()
_executor = build_default_executor()
_pipeline = ExecutionPipeline(executor=_executor)
_broadcaster: ViewFrameBroadcaster | None = None
_correlation_map = CorrelationMap()
_notion_outcome_receiver: Any = None


def _register_notion_integration() -> None:
    """Wire the Notion integration through IntegrationRegistry."""
    global _notion_outcome_receiver
    try:
        from ..integrations.notion.auth import get_notion_client
        from ..integrations.notion.handlers import NotionCapabilityHandler
        from ..integrations.notion.outcomes import NotionOutcomeReceiver
        from ..integrations.notion.signals import NotionSignalEmitter

        client = get_notion_client()
        _notion_outcome_receiver = NotionOutcomeReceiver(client, _correlation_map)

        signal_socket = SignalSocket()
        capability_socket = CapabilitySocket()
        outcome_socket = OutcomeSocket()

        registry = IntegrationRegistry(
            signal_socket, capability_socket, outcome_socket, _view_socket
        )

        manifest = IntegrationManifest(
            integration_id="notion",
            signal_emitter=NotionSignalEmitter(),
            capability_handler=NotionCapabilityHandler(),
            outcome_receiver=_notion_outcome_receiver,
        )

        adapter = registry.register(manifest)
        if adapter is not None:
            _executor.register_adapter(adapter)
            logger.info("notion integration adapter registered with executor")
    except Exception as exc:
        logger.warning("notion integration not loaded: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _broadcaster

    await _runtime.start()
    logger.info("UMH substrate runtime started")

    _register_notion_integration()

    loop = asyncio.get_running_loop()
    _broadcaster = ViewFrameBroadcaster(loop=loop, async_callback=broadcast_frame)
    _view_socket.subscribe(_broadcaster)
    _pipeline.on_event(make_pipeline_listener(_view_socket))
    logger.info("view socket broadcaster wired to WebSocket endpoint")

    yield

    _view_socket.unsubscribe("ws_broadcaster")
    await _runtime.shutdown()
    logger.info("UMH substrate runtime shut down")


app = FastAPI(
    title="UMH — UMH Layer 0 Substrate",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://100.77.233.50:5173",
        "http://localhost:5174",
        "http://100.77.233.50:5174",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_api_websocket_route("/ws", ws_endpoint)


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


class WritebackTo(BaseModel):
    """Target for outcome writeback."""

    page_id: str
    integration: str = "notion"


class SubmitRequest(BaseModel):
    """Direct pipeline submission — runs the full 10-stage pipeline."""

    content: str = Field(max_length=500)
    risk_class: str = "READ_ONLY"
    adapter_name: str = "shell"
    operation: str = "generic"
    params: dict[str, Any] = Field(default_factory=dict)
    pre_approved: bool = False
    writeback_to: WritebackTo | None = None


@app.post("/api/umh/submit")
async def pipeline_submit(req: SubmitRequest):
    """Submit a signal through the full ExecutionPipeline.

    Runs synchronously in a thread pool. ViewFrames are emitted at
    every pipeline stage and broadcast to WebSocket clients.
    If writeback_to is set, the outcome is written back to the target Notion page.
    """
    if not _runtime.is_running:
        raise HTTPException(status_code=503, detail="Substrate runtime not started")

    try:
        risk = RiskClass[req.risk_class]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown risk_class: {req.risk_class}")

    correlation_id = uuid4() if req.writeback_to else None

    if req.writeback_to and correlation_id:
        _correlation_map.register(
            correlation_id,
            WritebackTarget(
                page_id=req.writeback_to.page_id,
                integration=req.writeback_to.integration,
            ),
        )

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _pipeline.submit_signal(
            req.content,
            risk_class=risk,
            adapter_name=req.adapter_name,
            operation=req.operation,
            params=req.params,
            pre_approved=req.pre_approved,
        ),
    )

    if correlation_id and _notion_outcome_receiver and result.outcome_type:
        envelope = OutcomeEnvelope(
            outcome_id=uuid4(),
            signal_id=result.signal_id,
            trace_id=result.trace_id,
            integration_id="notion",
            outcome_type=result.outcome_type,
            summary=f"{result.outcome_type}: {req.content[:200]}",
            correlation_id=correlation_id,
        )
        try:
            _notion_outcome_receiver.on_outcome(envelope)
        except Exception as exc:
            logger.error("outcome writeback dispatch failed: %s", exc)

    return {
        "trace_id": str(result.trace_id),
        "signal_id": str(result.signal_id),
        "governance_approved": result.governance_approved,
        "governance_rationale": result.governance_rationale,
        "executed": result.executed,
        "success": result.success,
        "outcome_type": result.outcome_type,
    }


def get_runtime() -> SubstrateRuntime:
    """Access the runtime from other modules."""
    return _runtime
