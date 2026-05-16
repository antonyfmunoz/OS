#!/usr/bin/env python3
"""UMH Operator Workstation API — FastAPI backend for the operator UI."""

import sys

sys.path.insert(0, "/opt/OS")

import asyncio
import json
import logging
import os
import subprocess
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
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

load_dotenv("/opt/OS/services/.env")
load_dotenv("/opt/OS/runtime/.env", override=True)

UMH_ROOT = Path("/opt/OS")
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
    from state.context.context import load_context_from_env

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
        from runtime.ingestion import GenericIngestionOrchestrator

        orchestrator = GenericIngestionOrchestrator()
        result = await asyncio.to_thread(orchestrator.ingest, source=source, path=path)
        return {"triggered": True, "result": str(result)}
    except Exception as e:
        logger.warning(f"Ingestion trigger failed: {e}")
        return {"triggered": False, "error": str(e)}


# ─── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """WebSocket for streaming chat and real-time events."""
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

            if msg_type == "chat":
                message = msg.get("message", "")
                if not message:
                    await ws.send_json({"type": "error", "text": "Empty message"})
                    continue

                if not _HAS_COGNITIVE_LOOP:
                    await ws.send_json(
                        {
                            "type": "chat_response",
                            "text": "CognitiveLoop not available in this context",
                            "model_used": "none",
                            "duration_ms": 0,
                        }
                    )
                    continue

                start = time.time()
                try:
                    result = await asyncio.to_thread(_cognitive_loop.run, raw_prompt=message)
                    duration_ms = int((time.time() - start) * 1000)
                    await ws.send_json(
                        {
                            "type": "chat_response",
                            "text": result.output if hasattr(result, "output") else str(result),
                            "model_used": getattr(result, "model_used", "unknown"),
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
        "services.operator_api:app",
        host="0.0.0.0",
        port=8091,
        reload=False,
        log_level="info",
    )
