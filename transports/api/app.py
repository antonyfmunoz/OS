"""UMH API server — FastAPI surface matching existing UMH service conventions."""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from substrate.governance.risk_classes import RiskClass
from substrate.types import Signal, SignalSource, SignalUrgency
from substrate.sockets.capability_socket import CapabilitySocket
from substrate.sockets.envelopes import OutcomeEnvelope
from substrate.sockets.outcome_socket import OutcomeSocket
from substrate.sockets.registry import IntegrationManifest, IntegrationRegistry
from substrate.sockets.signal_socket import SignalSocket
from substrate.sockets.view.broadcaster import ViewFrameBroadcaster, make_pipeline_listener
from substrate.sockets.view.websocket import broadcast_frame, ws_endpoint
from substrate.sockets.view_socket import ViewSocket
from substrate.execution.executor import build_default_executor
from substrate.integrations.notion.correlation import CorrelationMap, WritebackTarget
from substrate.execution.pipeline import ExecutionPipeline
from transports.api.runtime import SubstrateRuntime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

_runtime = SubstrateRuntime()
_view_socket = ViewSocket()
_executor = build_default_executor()
_pipeline = ExecutionPipeline(executor=_executor)
_broadcaster: ViewFrameBroadcaster | None = None
_correlation_map = CorrelationMap()
_notion_outcome_receiver: Any = None
_notion_poller: Any = None
_notion_poller_thread: threading.Thread | None = None
_eos_poller: Any = None
_eos_poller_thread: threading.Thread | None = None
_mesh_server: Any = None
_organism: Any = None


def _register_notion_integration() -> None:
    """Wire the Notion integration through IntegrationRegistry."""
    global _notion_outcome_receiver, _notion_poller
    try:
        from substrate.integrations.notion.auth import get_notion_client
        from substrate.integrations.notion.handlers import NotionCapabilityHandler
        from substrate.integrations.notion.manifest import load_signal_sources
        from substrate.integrations.notion.outcomes import NotionOutcomeReceiver
        from substrate.integrations.notion.poller import NotionPoller
        from substrate.integrations.notion.signals import NotionSignalEmitter

        client = get_notion_client()
        emitter = NotionSignalEmitter()
        _notion_outcome_receiver = NotionOutcomeReceiver(client, _correlation_map)

        signal_socket = SignalSocket()
        capability_socket = CapabilitySocket()
        outcome_socket = OutcomeSocket()

        registry = IntegrationRegistry(
            signal_socket, capability_socket, outcome_socket, _view_socket
        )

        manifest = IntegrationManifest(
            integration_id="notion",
            signal_emitter=emitter,
            capability_handler=NotionCapabilityHandler(),
            outcome_receiver=_notion_outcome_receiver,
        )

        adapter = registry.register(manifest)
        if adapter is not None:
            _executor.register_adapter(adapter)
            logger.info("notion integration adapter registered with executor")

        signal_sources = load_signal_sources()
        if signal_sources:
            _notion_poller = NotionPoller(
                client=client,
                correlation_map=_correlation_map,
                signal_emitter=emitter,
                pipeline_submit_fn=_pipeline.submit_signal,
                outcome_receiver=_notion_outcome_receiver,
                signal_sources=signal_sources,
            )
            logger.info(
                "notion poller configured: %d signal source(s): %s",
                len(signal_sources),
                ", ".join(s["logical_name"] for s in signal_sources),
            )
        else:
            logger.info("notion poller not started: NOTION_SIGNAL_SOURCES not set")
    except Exception as exc:
        logger.warning("notion integration not loaded: %s", exc)


def _register_eos_integration() -> None:
    """Wire the EOS integration through IntegrationRegistry."""
    global _eos_poller
    try:
        from substrate.integrations.eos.correlation import EOSCorrelationMap
        from substrate.integrations.eos.handlers import EOSCapabilityHandler
        from substrate.integrations.eos.manifest import load_eos_config
        from substrate.integrations.eos.outcomes import EOSOutcomeReceiver
        from substrate.integrations.eos.poller import EOSPoller
        from substrate.integrations.eos.signals import EOSSignalEmitter

        config = load_eos_config()
        if not config:
            logger.info("eos integration not loaded: EOS_DATABASE_URL not set")
            return

        eos_correlation_map = EOSCorrelationMap()
        emitter = EOSSignalEmitter()
        outcome_receiver = EOSOutcomeReceiver(
            database_url=config["database_url"],
            correlation_map=eos_correlation_map,
        )

        signal_socket = SignalSocket()
        capability_socket = CapabilitySocket()
        outcome_socket = OutcomeSocket()

        registry = IntegrationRegistry(
            signal_socket, capability_socket, outcome_socket, _view_socket
        )

        manifest = IntegrationManifest(
            integration_id="eos",
            signal_emitter=emitter,
            capability_handler=EOSCapabilityHandler(database_url=config["database_url"]),
            outcome_receiver=outcome_receiver,
        )

        adapter = registry.register(manifest)
        if adapter is not None:
            _executor.register_adapter(adapter)
            logger.info("eos integration adapter registered with executor")

        _eos_poller = EOSPoller(
            database_url=config["database_url"],
            correlation_map=eos_correlation_map,
            signal_emitter=emitter,
            pipeline_submit_fn=_pipeline.submit_signal,
            outcome_receiver=outcome_receiver,
            tables=config["tables"],
            org_ids=config["org_ids"] if config["org_ids"] else None,
            poll_interval=config["poll_interval"],
        )
        org_scope = ", ".join(config["org_ids"]) if config["org_ids"] else "all"
        logger.info(
            "eos poller configured: tables=%s, orgs=%s, interval=%.1fs",
            config["tables"],
            org_scope,
            config["poll_interval"],
        )
    except Exception as exc:
        logger.warning("eos integration not loaded: %s", exc)


def _register_node_mesh() -> None:
    """Start the node mesh WebSocket server for remote device connections."""
    global _mesh_server
    try:
        from transports.node_mesh.config import load_mesh_config
        from transports.node_mesh.server import NodeMeshServer
        from substrate.sockets.capability_socket import CapabilitySocket
        from substrate.sockets.outcome_socket import OutcomeSocket
        from substrate.sockets.signal_socket import SignalSocket

        config = load_mesh_config()
        _mesh_server = NodeMeshServer(
            config=config,
            executor=_executor,
            signal_socket=SignalSocket(),
            capability_socket=CapabilitySocket(),
            outcome_socket=OutcomeSocket(),
            view_socket=_view_socket,
            pipeline_submit_fn=_pipeline.submit_signal,
        )
        _mesh_server.start()
        logger.info("node mesh server started on port %d", config.port)
    except Exception as exc:
        logger.warning("node mesh not started: %s", exc)


def _register_organism() -> None:
    """Start the organism daemon with the shared pipeline and view socket."""
    global _organism
    try:
        from substrate.organism.daemon import OrganismDaemon

        _organism = OrganismDaemon(pipeline=_pipeline, view_socket=_view_socket)
        _organism.start()
        logger.info("organism daemon started")
    except Exception as exc:
        logger.warning("organism daemon not started: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _broadcaster, _notion_poller_thread, _eos_poller_thread

    await _runtime.start()
    logger.info("UMH substrate runtime started")

    _register_notion_integration()
    _register_eos_integration()
    _register_node_mesh()
    _register_organism()

    if _notion_poller is not None:
        _notion_poller_thread = _notion_poller.start()
        logger.info("notion poller thread started")

    if _eos_poller is not None:
        _eos_poller_thread = _eos_poller.start()
        logger.info("eos poller thread started")

    loop = asyncio.get_running_loop()
    _broadcaster = ViewFrameBroadcaster(loop=loop, async_callback=broadcast_frame)
    _view_socket.subscribe(_broadcaster)
    _pipeline.on_event(make_pipeline_listener(_view_socket))
    logger.info("view socket broadcaster wired to WebSocket endpoint")

    yield

    if _organism is not None:
        _organism.stop()
        logger.info("organism daemon stopped")

    if _mesh_server is not None:
        _mesh_server.stop()
        logger.info("node mesh server stopped")

    if _eos_poller is not None:
        _eos_poller.shutdown_event.set()
        if _eos_poller_thread is not None:
            _eos_poller_thread.join(timeout=5)
            logger.info("eos poller thread stopped")

    if _notion_poller is not None:
        _notion_poller.shutdown_event.set()
        if _notion_poller_thread is not None:
            _notion_poller_thread.join(timeout=5)
            logger.info("notion poller thread stopped")

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

from transports.api.cockpit import router as cockpit_router

app.include_router(cockpit_router)
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
