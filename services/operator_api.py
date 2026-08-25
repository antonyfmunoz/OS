#!/usr/bin/env python3
# ruff: noqa: E402
"""UMH Operator Workstation API — FastAPI backend for the operator UI."""

import faulthandler
import os
import signal
import sys

faulthandler.enable()
faulthandler.register(signal.SIGUSR1, all_threads=True)

from substrate.execution.cpu_gate import gated_subprocess_run

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


import asyncio
import concurrent.futures
import json
import logging
import subprocess
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

UMH_ROOT = Path(os.getenv("UMH_ROOT", "/opt/OS"))
sys.path.insert(0, str(UMH_ROOT))

from substrate.state.runtime_paths import runtime_state_dir, runtime_state_path  # noqa: E402
from transports.api.governed import governed_mutation  # noqa: E402

load_dotenv(UMH_ROOT / "services" / ".env")
load_dotenv(UMH_ROOT / ".env", override=False)

API_KEY = os.getenv("UMH_OPERATOR_API_KEY", "")

logger = logging.getLogger("operator_api")
logging.basicConfig(level=logging.INFO)

_loop_registry = None
_organism_daemon = None
_tick_task = None
_voice_warmup_task: asyncio.Task | None = None
_tick_executor: concurrent.futures.ThreadPoolExecutor | None = None
_api_executor: concurrent.futures.ThreadPoolExecutor | None = None
_voice_warmup_status: dict[str, Any] = {
    "state": "NOT_STARTED",
    "started_at": None,
    "ended_at": None,
    "error": None,
    "shutdown_waiting": False,
    "shutdown_slow": False,
    "cancel_requested": False,
}
_VOICE_WARMUP_SHUTDOWN_DRAIN_SECONDS = 30.0


def _wire_spine_to_cockpit_ws(daemon) -> None:
    """Subscribe the EventSpine to push events to cockpit WebSocket clients."""
    try:
        from transports.api.cockpit import push_organism_event

        def _on_organism_event(event) -> None:
            push_organism_event(event.to_dict())

        daemon.event_spine.subscribe(
            "cockpit_ws_bridge",
            _on_organism_event,
        )
        logger.info("organism EventSpine → cockpit WS bridge wired")
    except Exception as exc:
        logger.warning("cockpit WS bridge not wired: %s", exc)


async def _tick_loop(daemon, executor: concurrent.futures.ThreadPoolExecutor) -> None:
    """Background async loop that drives the organism metabolism.

    Uses a dedicated executor so the tick never competes with API request threads.
    """
    loop = asyncio.get_running_loop()
    while True:
        try:
            await loop.run_in_executor(executor, daemon.tick)
        except Exception as exc:
            logger.warning("organism tick failed: %s", exc)
        interval = daemon.autonomous_tick.current_interval
        await asyncio.sleep(interval)


def voice_warmup_status() -> dict[str, Any]:
    return dict(_voice_warmup_status)


async def _run_voice_warmup(
    executor: concurrent.futures.ThreadPoolExecutor,
    preload_fn=None,
) -> None:
    global _voice_warmup_status
    preload = preload_fn
    if preload is None:
        from substrate.execution.voice.warm_engine import preload_warm_engine

        preload = preload_warm_engine

    _voice_warmup_status = {
        "state": "WARMING",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "ended_at": None,
        "error": None,
        "shutdown_waiting": False,
        "shutdown_slow": False,
        "cancel_requested": False,
    }
    work = asyncio.get_running_loop().run_in_executor(executor, preload)
    while True:
        try:
            ok = await asyncio.shield(work)
            break
        except asyncio.CancelledError:
            _voice_warmup_status = {
                **_voice_warmup_status,
                "cancel_requested": True,
                "shutdown_waiting": True,
            }
            logger.info("warm VoiceEngine preload cancellation requested; draining owned work")
            continue
        except Exception as exc:
            _voice_warmup_status = {
                **_voice_warmup_status,
                "state": "FAILED",
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
            }
            logger.warning("warm VoiceEngine preload failed (will lazy-load): %s", exc)
            return

    if ok is False:
        _voice_warmup_status = {
            **_voice_warmup_status,
            "state": "FAILED",
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "error": "preload_warm_engine returned false",
        }
        logger.warning("warm VoiceEngine preload failed (will lazy-load)")
        return

    _voice_warmup_status = {
        **_voice_warmup_status,
        "state": "READY",
        "ended_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("warm VoiceEngine preloaded for governed voice WS")


async def _drain_voice_warmup_task_for_shutdown() -> None:
    global _voice_warmup_task
    task = _voice_warmup_task
    if task is None:
        return
    if not task.done():
        _voice_warmup_status["shutdown_waiting"] = True
        logger.info("waiting for warm VoiceEngine preload to finish before shutdown")
        done, _pending = await asyncio.wait(
            {task},
            timeout=_VOICE_WARMUP_SHUTDOWN_DRAIN_SECONDS,
        )
        if not done:
            _voice_warmup_status.update(
                {
                    "shutdown_slow": True,
                },
            )
            logger.warning("warm VoiceEngine preload exceeded shutdown drain observation budget")
    try:
        await task
    except Exception as exc:
        logger.warning("warm VoiceEngine preload task ended during shutdown: %s", exc)
    finally:
        _voice_warmup_task = None


@asynccontextmanager
async def lifespan(application):
    global _loop_registry, _organism_daemon, _tick_task, _voice_warmup_task, _tick_executor, _api_executor

    # ── Thread pool isolation: tick gets its own thread, API gets 4 ───────
    _tick_executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=1,
        thread_name_prefix="tick",
    )
    _api_executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=16,
        thread_name_prefix="api",
    )
    asyncio.get_running_loop().set_default_executor(_api_executor)
    logger.info("thread pools: tick=1 (dedicated), api=16 (default)")

    # ── Register adapter sockets (intelligence/model router, data, browser…) ──
    # WITHOUT this, substrate.sockets.intelligence_port.call_with_fallback stays a
    # no-op (returns None) → advisor_conversation falls back to "the conversational
    # model is temporarily unavailable" and TTS speaks that canned line. The operator
    # service is a real entry point and MUST wire the sockets like discord_bot does.
    try:
        from adapters.socket_registration import register_all_sockets

        register_all_sockets()
        from substrate.sockets.intelligence_port import _call_with_fallback_fn

        logger.info(
            "adapter sockets registered: intelligence_wired=%s",
            _call_with_fallback_fn is not None,
        )
    except Exception as exc:
        logger.error("adapter socket registration failed: %s", exc)

    # ── Register config store ─────────────────────────────────────────────
    try:
        from substrate.sockets.config_port import register_config_store
        from substrate.state.config.config_store import ConfigStore

        _cfg = ConfigStore()
        register_config_store(_cfg.get, _cfg.set, _cfg.get_all, _cfg.on_change)
        logger.info("config store registered: ai_name=%s", _cfg.get("ai_name"))
    except Exception as exc:
        logger.warning("config store not registered: %s", exc)

    # ── Apply persisted settings overrides + backfill device fields ──────
    try:
        from transports.api.cockpit_settings_mutations import apply_persisted_overrides

        apply_persisted_overrides()
        logger.info("persisted settings overrides applied")
    except Exception as exc:
        logger.warning("persisted settings overrides not applied: %s", exc)

    try:
        from substrate.state.config.settings_persistence import backfill_device_role_fields

        if backfill_device_role_fields():
            logger.info("device role pipeline fields backfilled")
    except Exception as exc:
        logger.warning("device role backfill failed: %s", exc)

    try:
        from substrate.execution.loop.persistent_loop import get_registry

        _loop_registry = get_registry()
        loaded = _loop_registry.load_definitions()
        started = _loop_registry.start_all()
        logger.info("persistent loops: %d loaded, %d started — %s", loaded, len(started), started)
    except Exception as exc:
        logger.warning("persistent loops not started: %s", exc)

    try:
        from substrate.organism.daemon import OrganismDaemon
        from substrate.organism.runtime_adapters import build_default_graph

        graph = build_default_graph()
        graph.refresh_availability()
        avail = graph.available_count
        logger.info("runtime graph built: %d runtimes, %d available", graph.node_count, avail)
        _organism_daemon = OrganismDaemon(graph=graph)
        _organism_daemon.start()
        # Register the running daemon with the CANONICAL organism port so the
        # governed mutation path (transports/api/governed.py -> _get_router) can
        # reach the control plane. Without this the governed path finds no
        # organism, degrades EVERY mutation, and fail-closes HIGH-risk decisions
        # like execution_authorization_decision — the operator can approve
        # execution in the HUD (200) but the grant never activates and no worker
        # ever runs (observed field run 20260725T172540Z-p1). Voice wiring alone
        # (wire_organism) does not populate this port.
        try:
            from substrate.sockets.organism_port import register_organism_accessor

            register_organism_accessor(lambda: _organism_daemon)
            logger.info("organism registered with canonical organism_port (governed path live)")
        except Exception as exc:  # never block startup on the accessor wiring
            logger.error("failed to register organism accessor: %s", exc)
        _wire_spine_to_cockpit_ws(_organism_daemon)
        _tick_task = asyncio.create_task(_tick_loop(_organism_daemon, _tick_executor))
        logger.info("organism daemon started with autonomous tick loop (dedicated thread)")
    except Exception as exc:
        import traceback

        logger.error("organism daemon failed to start: %s\n%s", exc, traceback.format_exc())

    # ── Register notification port implementations ──────────────────────
    try:
        from substrate.sockets.notification import (
            register_approval_alert,
            register_chat_push,
        )
        from transports.api.cockpit import push_chat_message
        from transports.discord.approval_bridge import handle_approval_alert

        register_chat_push(push_chat_message)
        register_approval_alert(handle_approval_alert)
        logger.info("notification ports registered: chat_push, approval_alert")
    except Exception as exc:
        logger.warning("notification port registration failed: %s", exc)

    # ── Preload the warm VoiceEngine (GAP A) ─────────────────────────────────
    # The governed voice WS builds VoiceSession(engine=get_warm_engine()); warm
    # the SAME instance off the startup critical path. This best-effort task is
    # lifecycle-owned so cold model downloads cannot block /health, and shutdown
    # still drains/consumes the work cleanly.
    if _api_executor is not None:
        _voice_warmup_task = asyncio.create_task(_run_voice_warmup(_api_executor))

    yield

    await _drain_voice_warmup_task_for_shutdown()

    if _tick_task is not None:
        _tick_task.cancel()
        try:
            await _tick_task
        except asyncio.CancelledError:
            pass

    if _organism_daemon is not None:
        _organism_daemon.stop()
        logger.info("organism daemon stopped")

    if _tick_executor is not None:
        _tick_executor.shutdown(wait=False)
    if _api_executor is not None:
        _api_executor.shutdown(wait=False)

    # P4S-31C: dedicated read-path isolation pool
    try:
        from transports.api.read_path_isolation import shutdown_read_pool

        shutdown_read_pool()
    except Exception as exc:
        logger.debug("read pool shutdown failed: %s", exc)

    if _loop_registry is not None:
        stopped = _loop_registry.stop_all()
        logger.info("persistent loops stopped: %s", stopped)


app = FastAPI(title="UMH Operator API", version="1.0.0", lifespan=lifespan)

from starlette.middleware.base import BaseHTTPMiddleware

from substrate.integrations.cors import cors_origins


class _RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Kill requests that exceed the server-side deadline.

    Prevents thread pile-up when the pool is busy. Default 55s is under
    the frontend's 60s AbortController so the client gets a real 504
    instead of an opaque abort error.
    """

    _LONG_TIMEOUT_PATHS = (
        "/advisor/converse",
        "/dex/converse",
        "/chat/converse",
        "/bootstrap",
        "/bootstrap-slow",
    )

    async def dispatch(self, request: Request, call_next):
        if request.url.path.endswith("/health") or request.url.path.endswith("/ws"):
            return await call_next(request)
        timeout = (
            120.0 if any(request.url.path.endswith(p) for p in self._LONG_TIMEOUT_PATHS) else 55.0
        )
        try:
            return await asyncio.wait_for(call_next(request), timeout=timeout)
        except asyncio.TimeoutError:
            return JSONResponse(
                {"error": "request timeout", "detail": f"Request took longer than {int(timeout)}s"},
                status_code=504,
            )


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(_RequestTimeoutMiddleware)

# ─── ExecutionSpine import (production path) ──────────────────────────────────
_HAS_SPINE = False
try:
    from substrate.control_plane.context.context_builder import ContextBuilder
    from substrate.execution.runtime.execution_spine import ExecutionSpine
    from substrate.state.context.context import try_load_context_from_env

    _spine = ExecutionSpine()
    _ctx_builder = ContextBuilder()
    _ctx = try_load_context_from_env()
    _HAS_SPINE = True
    logger.info("ExecutionSpine loaded — chat via spine")
except Exception as e:
    logger.warning(f"ExecutionSpine not available: {e}")
    _spine = None
    _ctx_builder = None
    _ctx = None


# ─── Auth dependency ───────────────────────────────────────────────────────────
async def verify_api_key(request: Request) -> None:
    """Check X-API-Key header against configured key."""
    key = request.headers.get("X-API-Key", "")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ─── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """Health check — no auth required.

    Tests actual event loop responsiveness by scheduling a short async sleep.
    If the loop is blocked (threads saturated, sync calls piling up), this
    will time out and Docker will mark the container unhealthy.
    """
    try:
        await asyncio.wait_for(asyncio.sleep(0), timeout=3.0)
    except asyncio.TimeoutError:
        return JSONResponse(
            {"status": "degraded", "detail": "event loop blocked"},
            status_code=503,
        )
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "voice_warmup": voice_warmup_status(),
    }


# ─── Knowledge endpoints ───────────────────────────────────────────────────────
MEMORIES_PATH = runtime_state_path(
    "memory/canonical_memory_store", "memories.jsonl", create_parent=False
)


def _load_memories() -> list[dict[str, Any]]:
    """Load all memory entries from JSONL file."""
    if not MEMORIES_PATH.exists():
        return []
    entries: list[dict[str, Any]] = []
    with open(MEMORIES_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


@app.get("/api/knowledge/entries", dependencies=[Depends(verify_api_key)])
async def knowledge_entries(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """Paginated memory entries."""
    all_entries = _load_memories()
    total = len(all_entries)
    page = all_entries[offset : offset + limit]
    return {"total": total, "offset": offset, "limit": limit, "entries": page}


@app.get("/api/knowledge/stats", dependencies=[Depends(verify_api_key)])
async def knowledge_stats() -> dict[str, Any]:
    """Aggregate stats over memory entries."""
    entries = _load_memories()
    by_type: dict[str, int] = {}
    by_tier: dict[str, int] = {}
    by_domain: dict[str, int] = {}
    for e in entries:
        ptype = e.get("primitive_type", "unknown")
        by_type[ptype] = by_type.get(ptype, 0) + 1
        tier = e.get("authority_tier", "default")
        by_tier[str(tier)] = by_tier.get(str(tier), 0) + 1
        domain = e.get("domain_id", "none")
        by_domain[domain] = by_domain.get(domain, 0) + 1
    return {"total": len(entries), "by_type": by_type, "by_tier": by_tier, "by_domain": by_domain}


@app.get("/api/knowledge/search", dependencies=[Depends(verify_api_key)])
async def knowledge_search(q: str = "") -> dict[str, Any]:
    """Simple text search over memory entries."""
    if not q:
        return {"results": [], "query": q}
    entries = _load_memories()
    q_lower = q.lower()
    results = [
        e
        for e in entries
        if q_lower in e.get("label", "").lower()
        or q_lower in e.get("content", "").lower()
        or q_lower in e.get("primitive_type", "").lower()
    ]
    return {"results": results, "query": q, "count": len(results)}


# ─── System endpoints ──────────────────────────────────────────────────────────
COST_LOG_PATH = runtime_state_path("logs", "cost_log.json", create_parent=False)


@app.get("/api/system/costs", dependencies=[Depends(verify_api_key)])
async def system_costs() -> dict[str, Any]:
    """Read cost log (handle missing gracefully)."""
    if not COST_LOG_PATH.exists():
        return {"available": False, "message": "cost_log.json not found", "entries": []}
    try:
        data = json.loads(COST_LOG_PATH.read_text())
        return {"available": True, "data": data}
    except (json.JSONDecodeError, OSError) as e:
        return {"available": False, "message": str(e), "entries": []}


@app.get("/api/system/containers", dependencies=[Depends(verify_api_key)])
async def system_containers() -> dict[str, Any]:
    """List running Docker containers."""
    try:
        result = gated_subprocess_run(
            ["docker", "ps", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        containers = []
        for line in result.stdout.strip().split("\n"):
            if line:
                try:
                    containers.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return {"containers": containers, "count": len(containers)}
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"containers": [], "count": 0, "error": str(e)}


@app.get("/api/system/ingestion-status", dependencies=[Depends(verify_api_key)])
async def system_ingestion_status() -> dict[str, Any]:
    """Read latest ingestion status from proofs directory."""
    proofs_dir = runtime_state_dir("memory/canonical_memory_store/proofs", create=False)
    if not proofs_dir.exists():
        return {"available": False, "message": "No proofs directory"}
    # List proof directories sorted by name (date-prefixed)
    proof_dirs = sorted(proofs_dir.iterdir(), reverse=True)
    latest = []
    for d in proof_dirs[:5]:
        if d.is_dir():
            latest.append({"name": d.name, "path": str(d)})
    return {"available": True, "latest_proofs": latest}


# ─── Chat endpoint ─────────────────────────────────────────────────────────────
@app.post("/api/chat", dependencies=[Depends(verify_api_key)])
async def chat(request: Request) -> dict[str, Any]:
    """Send a message through ExecutionSpine."""
    body = await request.json()
    message = body.get("message", "")
    if not message:
        raise HTTPException(status_code=400, detail="message field required")

    if not _HAS_SPINE:
        return {
            "text": "ExecutionSpine not available in this context",
            "model_used": "none",
            "duration_ms": 0,
        }

    def _do_chat():
        try:
            uc = _ctx_builder.build(_ctx, message, "operator_ui_session")
            _spine.run(
                message=message,
                unified_context=uc,
                agent_type="executive_assistant",
                session_id="operator_ui_session",
                channel_id="operator_ui",
                org_id=str(_ctx.org_id),
                user_id=str(_ctx.user_id),
            )
            return f"chat processed: {message[:50]}", True
        except Exception as e:
            return str(e), False

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"operator chat: {message[:80]}",
        execute_fn=_do_chat,
        source="operator",
    )
    return resp.to_http_dict()


# ─── Ingest trigger ───────────────────────────────────────────────────────────
@app.post("/api/ingest/trigger", dependencies=[Depends(verify_api_key)])
async def ingest_trigger(request: Request) -> dict[str, Any]:
    """Trigger an ingestion run."""
    body = await request.json()
    source = body.get("source", "")
    path = body.get("path", "")
    if not source:
        raise HTTPException(status_code=400, detail="source field required")

    def _do_ingest():
        try:
            from substrate.understanding.perception.orchestrator import GenericIngestionOrchestrator

            orchestrator = GenericIngestionOrchestrator()
            orchestrator.ingest(source=source, path=path)
            return f"ingestion triggered: {source}", True
        except Exception as e:
            return str(e), False

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"trigger ingestion: {source}",
        execute_fn=_do_ingest,
        source="operator",
    )
    return resp.to_http_dict()


# ─── Voice-first helpers ──────────────────────────────────────────────────────

_VOICE_ACK_DIR = runtime_state_dir("voice_acks", create=False)


# P4S31 Voice Convergence: the rival voice runtime (the espeak TTS helper, the
# model_router voice-respond helper, the operator TTS POST endpoint, and the
# chat-WS voice branch) was REMOVED. Voice STT/TTS/response now flow ONLY through
# the canonical VoiceSession behind the governed WS (see transports/api/voice.py).
# This deletes a second STT/TTS engine and a second response path.


# ─── Vision helpers ──────────────────────────────────────────────────────────

_MAX_VISION_FRAME_BYTES = 2 * 1024 * 1024  # 2 MB cap per frame


async def _vision_analyze(
    image_b64: str,
    prompt: str = "",
    mime_type: str = "image/jpeg",
) -> dict[str, Any]:
    """Route an image + prompt through model_router with vision."""
    import base64

    start = time.time()
    image_bytes = base64.b64decode(image_b64)
    if len(image_bytes) > _MAX_VISION_FRAME_BYTES:
        return {"text": "Image too large (max 2 MB).", "duration_ms": 0}

    vision_prompt = prompt or "Describe what you see in this image concisely."

    try:
        from adapters.models.model_router import call_with_fallback

        result = await asyncio.to_thread(
            call_with_fallback,
            prompt=vision_prompt,
            task_type="multimodal",
            images=[(image_bytes, mime_type)],
        )
        duration_ms = int((time.time() - start) * 1000)
        output = result.output if hasattr(result, "output") else str(result)
        return {
            "text": output or "No vision response.",
            "provider": getattr(result, "provider", "unknown"),
            "duration_ms": duration_ms,
        }
    except Exception as e:
        logger.warning(f"Vision analysis failed: {e}")
        duration_ms = int((time.time() - start) * 1000)
        return {"text": f"Vision error: {e}", "duration_ms": duration_ms}


@app.post("/api/vision/analyze", dependencies=[Depends(verify_api_key)])
async def vision_analyze(request: Request) -> dict[str, Any]:
    """Analyze an image. Accepts base64 JPEG/PNG + optional text prompt."""
    body = await request.json()
    image_b64 = body.get("image", "")
    prompt = body.get("prompt", "")
    mime_type = body.get("mime_type", "image/jpeg")

    if not image_b64:
        raise HTTPException(status_code=400, detail="image field required (base64)")

    def _do_vision():
        import base64

        image_bytes = base64.b64decode(image_b64)
        if len(image_bytes) > _MAX_VISION_FRAME_BYTES:
            return "Image too large (max 2 MB)", False
        vision_prompt = prompt or "Describe what you see in this image concisely."
        try:
            from adapters.models.model_router import call_with_fallback

            call_with_fallback(
                prompt=vision_prompt,
                task_type="multimodal",
                images=[(image_bytes, mime_type)],
            )
            return "vision analysis complete", True
        except Exception as e:
            return str(e), False

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"analyze vision: {prompt[:50] if prompt else 'default'}",
        execute_fn=_do_vision,
        source="operator",
    )
    return resp.to_http_dict()


# ─── WebSocket ─────────────────────────────────────────────────────────────────
_WS_TOKEN = os.getenv("UMH_WS_TOKEN", "") or API_KEY
_DEV_BYPASS = os.getenv("UMH_DEV_BYPASS", "").lower() in ("1", "true", "yes")

import hmac as _hmac
import ipaddress as _ipaddress

_TAILSCALE_CGNAT = _ipaddress.ip_network("100.64.0.0/10")


def _is_private_ip(ip: str) -> bool:
    if not ip:
        return False
    try:
        addr = _ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr in _TAILSCALE_CGNAT
    except ValueError:
        return False


def _extract_ws_token(ws: WebSocket) -> str:
    for proto in (ws.headers.get("sec-websocket-protocol") or "").split(","):
        proto = proto.strip()
        if proto.startswith("bearer."):
            return proto[7:]
    return ws.query_params.get("token", "")


_TRUSTED_PROXIES = {"127.0.0.1", "::1"}
_docker_bridge = os.getenv("UMH_DOCKER_BRIDGE_IP", "172.20.0.1")
if _docker_bridge:
    _TRUSTED_PROXIES.add(_docker_bridge)


def _real_ws_client_ip(ws: WebSocket) -> str:
    """Real client IP for WebSocket, accounting for trusted reverse proxies."""
    tcp_ip = ws.client.host if ws.client else ""
    if tcp_ip in _TRUSTED_PROXIES:
        forwarded = ws.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return tcp_ip


def _validate_ws_auth(ws: WebSocket) -> bool:
    if not _WS_TOKEN:
        client_ip = _real_ws_client_ip(ws)
        return _DEV_BYPASS and _is_private_ip(client_ip)
    token = _extract_ws_token(ws)
    if token and _hmac.compare_digest(token, _WS_TOKEN):
        return True
    client_ip = _real_ws_client_ip(ws)
    if _DEV_BYPASS and _is_private_ip(client_ip):
        return True
    return False


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """WebSocket for streaming chat, voice transcripts, and real-time events."""
    if not _validate_ws_auth(ws):
        await ws.close(code=4001, reason="Authentication required")
        logger.warning("Chat WS auth rejected from %s", ws.client.host if ws.client else "unknown")
        return
    token = _extract_ws_token(ws)
    subprotocol = f"bearer.{token}" if token else None
    await ws.accept(subprotocol=subprotocol)
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "text": "Invalid JSON"})
                continue

            msg_type = msg.get("type", "")

            # P4S31 Voice Convergence: the voice-transcript branch was REMOVED.
            # Voice now flows through the canonical governed voice WS
            # (transports/api/voice.py), never through this chat WS. This closes a
            # rival voice-response path.
            if msg_type == "chat":
                message = msg.get("message", "")
                if not message:
                    await ws.send_json({"type": "error", "text": "Empty message"})
                    continue

                # Route through model_router (fixes _HAS_COGNITIVE_LOOP NameError)
                start = time.time()
                try:
                    from adapters.models.model_router import call_with_fallback

                    result = await asyncio.to_thread(
                        call_with_fallback,
                        prompt=message,
                        task_type="conversation",
                    )
                    duration_ms = int((time.time() - start) * 1000)
                    await ws.send_json(
                        {
                            "type": "chat_response",
                            "text": result or "No response from model router",
                            "model_used": "model_router",
                            "duration_ms": duration_ms,
                        }
                    )
                except Exception as e:
                    await ws.send_json(
                        {
                            "type": "chat_response",
                            "text": f"Error: {e}",
                            "model_used": "none",
                            "duration_ms": 0,
                        }
                    )

            elif msg_type == "vision_frame":
                image_b64 = msg.get("image", "")
                prompt = msg.get("prompt", "")
                mime_type = msg.get("mime_type", "image/jpeg")

                if not image_b64:
                    await ws.send_json({"type": "error", "text": "Empty image"})
                    continue

                await ws.send_json({"type": "vision_ack", "text": "analyzing"})

                try:
                    result = await _vision_analyze(image_b64, prompt, mime_type)
                    await ws.send_json(
                        {
                            "type": "vision_response",
                            "text": result.get("text", ""),
                            "provider": result.get("provider", "unknown"),
                            "duration_ms": result.get("duration_ms", 0),
                        }
                    )
                except Exception as e:
                    await ws.send_json(
                        {
                            "type": "vision_response",
                            "text": f"Vision error: {e}",
                            "duration_ms": 0,
                        }
                    )

            elif msg_type == "ping":
                await ws.send_json({"type": "pong"})
            else:
                await ws.send_json({"type": "error", "text": f"Unknown message type: {msg_type}"})
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


# ─── Cockpit API (substrate command center) ───────────────────────────────────
try:
    from transports.api.cockpit import router as cockpit_router
    from transports.api.cockpit import ws_router as cockpit_ws_router

    app.include_router(cockpit_router)
    app.include_router(cockpit_ws_router)
    logger.info("cockpit router mounted at /api/umh/")
except Exception as e:
    logger.warning(f"cockpit router not available: {e}")

# ─── Governed voice router (the ONE voice ingress: /api/umh/voice/ws) ──────────
# P4S31 Voice Convergence: mount the canonical governed voice surface on the
# DEPLOYED API backend so every capture edge reaches the one runtime here, not
# the retired standalone voice_server bridge.
try:
    from transports.api.voice import router as voice_router
    from transports.api.voice import wire_organism

    app.include_router(voice_router)
    # Inject the running-organism accessor so the WS drives governed converse.
    wire_organism(lambda: _organism_daemon)
    logger.info("governed voice router mounted at /api/umh/voice")
except Exception as e:
    logger.warning(f"voice router not available: {e}")


# ─── Static files (cockpit build) ─────────────────────────────────────────────
cockpit_dist = UMH_ROOT / "cockpit" / "dist-web"
if cockpit_dist.exists():
    app.mount("/", StaticFiles(directory=str(cockpit_dist), html=True), name="cockpit")

# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "services.operator_api:app",
        host="0.0.0.0",
        port=8091,
        reload=False,
        log_level="info",
    )
