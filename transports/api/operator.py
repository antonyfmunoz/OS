#!/usr/bin/env python3
"""UMH Operator Workstation API — FastAPI backend for the operator UI."""

import sys

sys.path.insert(0, "/opt/OS")

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

load_dotenv("/opt/OS/services/.env")
load_dotenv("/opt/OS/runtime/.env", override=True)

UMH_ROOT = Path(os.getenv("UMH_ROOT", "/opt/OS"))
API_KEY = os.getenv("UMH_OPERATOR_API_KEY", "dev-key-change-me")

logger = logging.getLogger("operator_api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="UMH Operator API", version="1.0.0")

# CORS for dev (Vite on 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://100.77.233.50:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── ExecutionSpine import (production path) ──────────────────────────────────
_HAS_SPINE = False
try:
    from execution.runtime.execution_spine import ExecutionSpine
    from control_plane.context.context_builder import ContextBuilder
    from substrate.state.context.context import load_context_from_env

    _spine = ExecutionSpine()
    _ctx_builder = ContextBuilder()
    _ctx = load_context_from_env()
    _HAS_SPINE = True
    logger.info("ExecutionSpine loaded — chat via spine")
except Exception as e:
    logger.warning(f"ExecutionSpine not available: {e}")
    _spine = None
    _ctx_builder = None
    _ctx = None

# ─── Substrate routing ────────────────────────────────────────────────────────
_HAS_SUBSTRATE = False
try:
    from substrate import Substrate
    from transports.api.signal_factory import http_request_to_signal

    _substrate = Substrate()
    _HAS_SUBSTRATE = True
    logger.info("Substrate loaded — ready for signal routing")
except Exception as e:
    logger.warning(f"Substrate not available: {e}")
    _substrate = None


# ─── Auth dependency ───────────────────────────────────────────────────────────
async def verify_api_key(request: Request) -> None:
    """Check X-API-Key header against configured key."""
    key = request.headers.get("X-API-Key", "")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ─── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict[str, str]:
    """Health check — no auth required."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# ─── Knowledge endpoints ───────────────────────────────────────────────────────
MEMORIES_PATH = UMH_ROOT / "data" / "runtime" / "canonical_memory_store" / "memories.jsonl"


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
COST_LOG_PATH = UMH_ROOT / "services" / "cost_log.json"


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
        result = subprocess.run(
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
    proofs_dir = UMH_ROOT / "data" / "runtime" / "canonical_memory_store" / "proofs"
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

    start = time.time()
    try:
        uc = _ctx_builder.build(_ctx, message, "operator_ui_session")
        response = await asyncio.to_thread(
            _spine.run,
            message=message,
            unified_context=uc,
            agent_type="executive_assistant",
            session_id="operator_ui_session",
            channel_id="operator_ui",
            org_id=str(_ctx.org_id),
            user_id=str(_ctx.user_id),
        )
        duration_ms = int((time.time() - start) * 1000)
        return {
            "text": response,
            "model_used": "spine",
            "duration_ms": duration_ms,
            "context_tokens": uc.estimated_tokens,
        }
    except Exception as e:
        logger.error(f"ExecutionSpine error: {e}")
        return {"text": f"Error: {e}", "model_used": "none", "duration_ms": 0}


# ─── Ingest trigger ───────────────────────────────────────────────────────────
@app.post("/api/ingest/trigger", dependencies=[Depends(verify_api_key)])
async def ingest_trigger(request: Request) -> dict[str, Any]:
    """Trigger an ingestion run."""
    body = await request.json()
    source = body.get("source", "")
    path = body.get("path", "")
    if not source:
        raise HTTPException(status_code=400, detail="source field required")

    # Attempt to trigger ingestion via the orchestrator
    try:
        from substrate.understanding.perception.orchestrator import GenericIngestionOrchestrator

        orchestrator = GenericIngestionOrchestrator()
        result = await asyncio.to_thread(orchestrator.ingest, source=source, path=path)
        return {"triggered": True, "result": str(result)}
    except Exception as e:
        logger.warning(f"Ingestion trigger failed: {e}")
        return {"triggered": False, "error": str(e)}


# ─── Voice-first helpers ──────────────────────────────────────────────────────

_VOICE_ACK_DIR = UMH_ROOT / "data" / "voice_acks"


def _generate_tts(text: str) -> str | None:
    """Generate WAV from text via espeak. Returns path or None."""
    try:
        fd, path = tempfile.mkstemp(suffix=".wav", prefix="cockpit_tts_")
        os.close(fd)
        result = subprocess.run(
            ["espeak", "-s", "150", "-w", path, text[:500]],
            capture_output=True,
            timeout=15,
        )
        if result.returncode == 0 and os.path.exists(path):
            return path
        os.unlink(path)
    except Exception as e:
        logger.warning(f"TTS generation failed: {e}")
    return None


async def _voice_respond(transcript: str) -> dict[str, Any]:
    """Route a voice transcript through model_router and prepare voice response."""
    from execution.transport.voice_first import (
        VOICE_SYSTEM_SUFFIX,
        prepare_voice_response,
    )

    start = time.time()

    # Route through model_router (same chain as Discord voice)
    try:
        from adapters.models.model_router import call_with_fallback

        voice_prompt = transcript + VOICE_SYSTEM_SUFFIX
        raw_response = await asyncio.to_thread(
            call_with_fallback,
            prompt=voice_prompt,
            task_type="conversation",
        )
        if not raw_response:
            raw_response = "I couldn't process that right now."
    except Exception as e:
        logger.warning(f"Voice model_router failed: {e}")
        raw_response = "I'm having trouble connecting to the intelligence layer."

    duration_ms = int((time.time() - start) * 1000)
    spoken_text = prepare_voice_response(raw_response)

    # Generate TTS audio
    tts_path = await asyncio.to_thread(_generate_tts, spoken_text)

    return {
        "text": raw_response,
        "spoken_text": spoken_text,
        "duration_ms": duration_ms,
        "tts_path": tts_path,
    }


@app.post("/api/voice/tts", dependencies=[Depends(verify_api_key)])
async def voice_tts(request: Request) -> Any:
    """Generate TTS WAV from text. Returns audio/wav."""
    body = await request.json()
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="text field required")

    from execution.transport.voice_first import prepare_voice_response

    cleaned = prepare_voice_response(text)
    path = await asyncio.to_thread(_generate_tts, cleaned)
    if not path:
        raise HTTPException(status_code=500, detail="TTS generation failed")

    return FileResponse(
        path,
        media_type="audio/wav",
        filename="response.wav",
        background=None,
    )


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
        from execution.runtime.model_router import call_with_fallback

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

    return await _vision_analyze(image_b64, prompt, mime_type)


# ─── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """WebSocket for streaming chat, voice transcripts, and real-time events."""
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "text": "Invalid JSON"})
                continue

            msg_type = msg.get("type", "")

            if msg_type == "voice_transcript":
                # Voice-first: browser sends STT transcript, we respond with
                # text + TTS audio URL
                transcript = msg.get("transcript", "")
                if not transcript:
                    await ws.send_json({"type": "error", "text": "Empty transcript"})
                    continue

                # Send ack immediately (browser plays ack sound client-side)
                await ws.send_json({"type": "voice_ack", "text": "processing"})

                try:
                    result = await _voice_respond(transcript)
                    response_msg: dict[str, Any] = {
                        "type": "voice_response",
                        "text": result["text"],
                        "spoken_text": result["spoken_text"],
                        "duration_ms": result["duration_ms"],
                    }

                    # If TTS was generated, send the audio as binary after the JSON
                    tts_path = result.get("tts_path")
                    if tts_path and os.path.exists(tts_path):
                        response_msg["has_audio"] = True
                        await ws.send_json(response_msg)
                        with open(tts_path, "rb") as f:
                            await ws.send_bytes(f.read())
                        try:
                            os.unlink(tts_path)
                        except Exception:
                            pass
                    else:
                        response_msg["has_audio"] = False
                        await ws.send_json(response_msg)

                except Exception as e:
                    await ws.send_json(
                        {
                            "type": "voice_response",
                            "text": f"Error: {e}",
                            "spoken_text": "",
                            "duration_ms": 0,
                            "has_audio": False,
                        }
                    )

            elif msg_type == "chat":
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


# ─── Static files (frontend dist) ─────────────────────────────────────────────
frontend_dist = UMH_ROOT / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "transports.api.operator:app",
        host="0.0.0.0",
        port=8091,
        reload=False,
        log_level="info",
    )
