"""UMH API server — FastAPI surface matching existing UMH service conventions."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from contextlib import asynccontextmanager
from typing import Any, Callable
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from substrate.governance.risk_classes import RiskClass
from substrate.governance.security import (
    get_audit_log,
    get_rate_limiter,
    validate_signal_content,
)
from substrate.types import Signal, SignalSource, SignalUrgency
from substrate.sockets.capability_socket import CapabilitySocket
from substrate.sockets.envelopes import OutcomeEnvelope
from substrate.sockets.outcome_socket import OutcomeSocket
from substrate.sockets.registry import IntegrationManifest, IntegrationRegistry
from substrate.sockets.signal_socket import SignalSocket
from substrate.sockets.view.broadcaster import ViewFrameBroadcaster, make_pipeline_listener
from substrate.sockets.view.websocket import broadcast_frame, manager, ws_endpoint
from substrate.sockets.view_socket import ViewSocket
from substrate.execution.executor import build_default_executor
from adapters.notion.integration.correlation import CorrelationMap, WritebackTarget
from substrate.execution.pipeline import ExecutionPipeline
from substrate.memory.watcher import start_memory_watcher
from transports.api.runtime import SubstrateRuntime
from transports.api.governed import governed_mutation

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
_memory_watcher = None
_eos_poller: Any = None
_eos_poller_thread: threading.Thread | None = None
_mesh_server: Any = None
_organism: Any = None
_loop_registry: Any = None


def _start_persistent_loops() -> None:
    """Load loop definitions and start all enabled persistent loops."""
    global _loop_registry
    try:
        from substrate.execution.loop.persistent_loop import get_registry

        _loop_registry = get_registry()
        loaded = _loop_registry.load_definitions()
        started = _loop_registry.start_all()
        logger.info(
            "persistent loops: %d loaded, %d started — %s",
            loaded,
            len(started),
            started,
        )
    except Exception as exc:
        logger.warning("persistent loops not started: %s", exc)


def _stop_persistent_loops() -> None:
    """Stop all running persistent loops."""
    if _loop_registry is not None:
        stopped = _loop_registry.stop_all()
        logger.info("persistent loops stopped: %s", stopped)


def _register_notion_integration() -> None:
    """Wire the Notion integration through IntegrationRegistry."""
    global _notion_outcome_receiver, _notion_poller
    try:
        from adapters.notion.integration.auth import get_notion_client
        from adapters.notion.integration.handlers import NotionCapabilityHandler
        from adapters.notion.integration.manifest import load_signal_sources
        from adapters.notion.integration.outcomes import NotionOutcomeReceiver
        from adapters.notion.integration.poller import NotionPoller
        from adapters.notion.integration.signals import NotionSignalEmitter

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
        from projections.eos.integration.correlation import EOSCorrelationMap
        from projections.eos.integration.handlers import EOSCapabilityHandler
        from projections.eos.integration.manifest import load_eos_config
        from projections.eos.integration.outcomes import EOSOutcomeReceiver
        from projections.eos.integration.poller import EOSPoller
        from projections.eos.integration.signals import EOSSignalEmitter

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
            user_ids=config["user_ids"] if config["user_ids"] else None,
            poll_interval=config["poll_interval"],
        )
        user_scope = ", ".join(config["user_ids"]) if config["user_ids"] else "all"
        logger.info(
            "eos poller configured: tables=%s, users=%s, interval=%.1fs",
            config["tables"],
            user_scope,
            config["poll_interval"],
        )
    except Exception as exc:
        logger.warning("eos integration not loaded: %s", exc)


def _register_organism() -> None:
    """Start the organism daemon with the shared pipeline and view socket."""
    global _organism
    try:
        from substrate.organism.daemon import OrganismDaemon
        from substrate.organism.runtime_adapters import build_default_graph

        graph = build_default_graph()
        graph.refresh_availability()
        logger.info(
            "runtime graph: %d runtimes, %d available", graph.node_count, graph.available_count
        )
        _organism = OrganismDaemon(pipeline=_pipeline, view_socket=_view_socket, graph=graph)
        _organism.start()
        try:
            from substrate.sockets.organism_port import register_organism_accessor

            register_organism_accessor(lambda: _organism)
            logger.info("organism registered with canonical organism_port")
        except Exception as exc:
            logger.error("failed to register organism accessor: %s", exc)
        logger.info("organism daemon started")
    except Exception as exc:
        logger.warning("organism daemon not started: %s", exc)


def _build_runtime_graph_hook() -> "Callable[[str, list[str], str], None] | None":
    """Build a closure that bridges mesh node lifecycle → RuntimeGraph + Supervisor."""
    if _organism is None or _organism.graph is None:
        return None

    graph = _organism.graph
    supervisor = _organism.supervisor

    def _hook(node_id: str, cap_names: list[str], action: str) -> None:
        from substrate.organism.runtime_adapters import MeshNodeRuntimeAdapter
        from substrate.organism.runtime_graph import (
            AvailabilityStatus,
            CostProfile,
            RuntimeClass,
        )

        rid = f"mesh:{node_id}"

        if action == "connect":
            if graph.get(rid) is not None:
                graph.update_status(rid, AvailabilityStatus.AVAILABLE)
            else:
                adapter = MeshNodeRuntimeAdapter(node_id, cap_names)
                device_id = _resolve_device_id(node_id)
                graph.register(
                    rid,
                    RuntimeClass.REMOTE_NODE,
                    adapter.capabilities,
                    cost=CostProfile(is_subscription=False, cost_per_1k_input=0.0),
                    adapter=adapter,
                    metadata={"device_id": device_id},
                )
                graph.update_status(rid, AvailabilityStatus.AVAILABLE)
            if supervisor is not None:
                supervisor.heartbeat(rid)
            logger.info("mesh node %s registered in runtime graph", rid)

        elif action == "disconnect":
            graph.update_status(rid, AvailabilityStatus.UNAVAILABLE)
            logger.info("mesh node %s marked unavailable in runtime graph", rid)

        elif action == "heartbeat":
            node = graph.get(rid)
            if node is not None:
                node.last_heartbeat = __import__("time").time()
                if node.status != AvailabilityStatus.AVAILABLE:
                    graph.update_status(rid, AvailabilityStatus.AVAILABLE)
            if supervisor is not None:
                supervisor.heartbeat(rid)

    return _hook


def _resolve_device_id(node_id: str) -> str:
    """Map a mesh node_id to its device registry id."""
    import json

    registry_path = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"), "infra", "device_registry.json"
    )
    try:
        with open(registry_path) as f:
            devices = json.load(f)
        for dev in devices:
            if dev.get("mesh_node_id") == node_id or dev.get("id") == node_id:
                return dev["id"]
    except Exception:
        pass
    return node_id


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
        graph_hook = _build_runtime_graph_hook()

        _mesh_server = NodeMeshServer(
            config=config,
            executor=_executor,
            signal_socket=SignalSocket(),
            capability_socket=CapabilitySocket(),
            outcome_socket=OutcomeSocket(),
            view_socket=_view_socket,
            pipeline_submit_fn=_pipeline.submit_signal,
            runtime_graph_hook=graph_hook,
        )
        _mesh_server.start()
        logger.info(
            "node mesh server started on port %d (graph_hook=%s)",
            config.port,
            "wired" if graph_hook is not None else "none",
        )

        _wire_workstation_bridge(_mesh_server)

    except Exception as exc:
        logger.warning("node mesh not started: %s", exc)


def _wire_workstation_bridge(mesh_server: Any) -> None:
    """Wire Beast workstation observation → ScreenObservationEngine."""
    try:
        from substrate.operator.workstation_translator import WorkstationTranslator
        from substrate.operator.screen_observation_engine import ScreenObservationEngine

        translator = WorkstationTranslator()
        engine = ScreenObservationEngine()

        def _on_workstation_state(node_id: str, payload: dict) -> None:
            try:
                snapshot = translator.translate(node_id, payload)
                engine.report_observed(snapshot)
                logger.debug("workstation state received from %s", node_id)
            except Exception as exc:
                logger.warning("workstation translation failed: %s", exc)

        mesh_server.register_workstation_callback(_on_workstation_state)
        logger.info("workstation observation bridge wired")
    except Exception as exc:
        logger.warning("workstation bridge not wired: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _broadcaster, _notion_poller_thread, _eos_poller_thread

    await _runtime.start()
    logger.info("UMH substrate runtime started")

    _register_notion_integration()
    _register_eos_integration()
    _register_organism()
    _register_node_mesh()
    _start_persistent_loops()

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

    global _memory_watcher
    _memory_watcher = start_memory_watcher()
    logger.info("memory watcher started with %d watches", len(_memory_watcher.watches))

    # Wire EventSpine → WebSocket for live mutation lifecycle events
    if _organism is not None:
        _es = _organism.event_spine

        def _event_spine_to_ws(event: Any) -> None:
            try:
                msg = {
                    "type": "organism_event",
                    "data": event.to_dict(),
                }
                asyncio.run_coroutine_threadsafe(manager.broadcast(msg), loop)
            except Exception:
                pass

        _es.subscribe("cockpit_ws_bridge", _event_spine_to_ws)
        logger.info("event spine → websocket bridge active")

    # Register cockpit WebSocket as a notification channel
    from substrate.sockets.notification_engine import (
        get_notification_engine,
        NotificationChannel,
    )

    def _cockpit_notify_handler(title: str, body: str, **kwargs) -> bool:
        try:
            import json as _json

            _view_socket.push(
                "notification",
                _json.dumps({"title": title, "body": body, **kwargs}),
            )
            return True
        except Exception:
            return False

    get_notification_engine().register_channel(NotificationChannel.COCKPIT, _cockpit_notify_handler)
    logger.info("cockpit notification channel registered")

    yield

    _stop_persistent_loops()

    if _memory_watcher is not None:
        _memory_watcher.stop()
        logger.info("memory watcher stopped")

    if _organism is not None:
        _organism.event_spine.unsubscribe("cockpit_ws_bridge")
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

from transports.api.cockpit import router as cockpit_router, ws_router as cockpit_ws_router
from transports.api.computer_use import router as execution_router
from transports.api.distribution import router as distribution_router, wire_pipeline
from transports.api.voice import router as voice_router, wire_pipeline as wire_voice_pipeline
from transports.api.workstation import router as workstation_router

app.include_router(cockpit_router)
app.include_router(cockpit_ws_router)
app.include_router(execution_router)
app.include_router(distribution_router)
app.include_router(voice_router)
app.include_router(workstation_router)

wire_pipeline(_pipeline.submit_signal)
wire_voice_pipeline(_pipeline.submit_signal)
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
    """Health check endpoint with homeostasis."""
    base = _runtime.health()
    try:
        base["homeostasis"] = _pipeline.health_check()
    except Exception:
        pass
    return base


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

    def _do_signal_intake():
        import asyncio as _aio
        loop = _aio.new_event_loop()
        try:
            loop.run_until_complete(_runtime.ingest_signal(signal))
        finally:
            loop.close()
        return f"signal ingested: {req.source}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"ingest signal from {req.source}",
        execute_fn=_do_signal_intake,
        source="api",
    )
    return resp.to_http_dict()


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


@app.get("/api/projections/certification")
async def projection_certifications(projection: str | None = None):
    """Projection certification levels — graduated L0-L5."""
    try:
        from substrate.organism.projection_certification import (
            ProjectionCertificationEngine,
            ProjectionRegistry,
        )
        registry = ProjectionRegistry()
        engine = ProjectionCertificationEngine(registry=registry)

        if projection:
            cert = engine.certify(projection)
            return cert.to_dict()

        results = engine.certify_all()
        return {
            "projections": {
                name: cert.to_dict() for name, cert in results.items()
            },
            "summary": engine.summary(),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Certification check failed: {exc}",
        )


@app.get("/api/trust/scores")
async def trust_scores(work_id: str | None = None):
    """Trust score summary — composite weakest-link scoring."""
    try:
        from substrate.organism.trust_score import TrustScoreEngine
        engine = TrustScoreEngine()

        if work_id:
            score = engine.get_score(work_id)
            if score is None:
                raise HTTPException(status_code=404, detail=f"No trust score for {work_id}")
            return score.to_dict()

        return engine.summary()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Trust score check failed: {exc}",
        )


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
    """Submit a signal through the full ExecutionPipeline."""
    if not _runtime.is_running:
        raise HTTPException(status_code=503, detail="Substrate runtime not started")

    if not get_rate_limiter().allow("submit"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    validation = validate_signal_content(req.content)
    if not validation.valid:
        raise HTTPException(
            status_code=400, detail=f"Validation failed: {', '.join(validation.violations)}"
        )

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

    def _do_submit():
        result = _pipeline.submit_signal(
            req.content,
            risk_class=risk,
            adapter_name=req.adapter_name,
            operation=req.operation,
            params=req.params,
            pre_approved=req.pre_approved,
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

        get_audit_log().record(
            action="pipeline_submit",
            target=req.adapter_name,
            outcome="success" if result.success else "blocked",
            detail=f"risk={req.risk_class} outcome={result.outcome_type}",
            risk_level="high"
            if risk not in (RiskClass.READ_ONLY, RiskClass.REVERSIBLE_WRITE)
            else "low",
        )
        return f"pipeline submitted: {req.content[:50]}", result.success

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"pipeline submit: {req.content[:80]}",
        execute_fn=_do_submit,
        source="api",
    )
    return resp.to_http_dict()


def get_runtime() -> SubstrateRuntime:
    """Access the runtime from other modules."""
    return _runtime
