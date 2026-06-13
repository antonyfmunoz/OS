"""Broadcast API — start/stop/status + WebSocket health push.

All endpoints prefixed /api/umh/broadcast/ and registered via include_router.
Models defined locally (not substrate/) for Slice 0.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

_app_root = os.environ.get("UMH_ROOT", "/opt/OS")
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from transports.api.cockpit_auth import require_clerk_auth, validate_ws_clerk_token

logger = logging.getLogger(__name__)

broadcast_router = APIRouter(prefix="/broadcast", tags=["broadcast"])
broadcast_ws_router = APIRouter(prefix="/broadcast", tags=["broadcast-ws"])


# ── Models (local to Slice 0) ──


class SourceType(str, Enum):
    TEST_PATTERN = "test_pattern"
    CAMERA = "camera"
    FILE = "file"
    RTMP_PULL = "rtmp_pull"


class BroadcastStartRequest(BaseModel):
    source_type: SourceType = Field(default=SourceType.TEST_PATTERN)
    source_config: dict[str, Any] = Field(default_factory=dict)
    output_url: str = Field(description="RTMP destination URL")
    video_codec: str = Field(default="libx264")
    video_bitrate: str = Field(default="4500k")
    audio_codec: str = Field(default="aac")
    audio_bitrate: str = Field(default="128k")
    resolution: str = Field(default="1920x1080")
    fps: int = Field(default=30, ge=1, le=120)
    keyframe_interval: int = Field(default=2, ge=1, le=10)
    preset: str = Field(default="veryfast")
    container_format: str = Field(default="flv")


class BroadcastStatusResponse(BaseModel):
    state: str
    health: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    pid: int | None = None


# ── Engine singleton ──

_engine = None
_engine_lock = asyncio.Lock()


def _get_engine():
    global _engine
    if _engine is None:
        from adapters.broadcast.engine import BroadcastEngine
        _engine = BroadcastEngine()
    return _engine


# ── WebSocket health push ──

_ws_clients: set[WebSocket] = set()
_latest_health: dict[str, Any] = {}


def _on_engine_health(health: dict[str, Any]) -> None:
    global _latest_health
    _latest_health = health


# ── HTTP Endpoints ──


@broadcast_router.post("/start")
async def start_broadcast(req: BroadcastStartRequest, _user=Depends(require_clerk_auth)):
    engine = _get_engine()
    async with _engine_lock:
        if engine.state == "live":
            raise HTTPException(status_code=409, detail="Already broadcasting")

        engine.set_health_callback(_on_engine_health)
        config = req.model_dump()
        config["source_type"] = req.source_type.value
        ok = await engine.start(config)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to start broadcast")

    return {"status": "started", "pid": engine._lifecycle.pid if engine._lifecycle else None}


@broadcast_router.post("/stop")
async def stop_broadcast(_user=Depends(require_clerk_auth)):
    engine = _get_engine()
    async with _engine_lock:
        if engine.state == "idle":
            return {"status": "already_stopped"}
        code = await engine.stop()

    return {"status": "stopped", "exit_code": code}


@broadcast_router.get("/status")
async def get_broadcast_status(_user=Depends(require_clerk_auth)):
    engine = _get_engine()
    return engine.get_status()


# ── WebSocket health endpoint ──


@broadcast_ws_router.websocket("/ws")
async def broadcast_ws(ws: WebSocket):
    user = await validate_ws_clerk_token(ws)
    if user is None:
        if os.environ.get("UMH_ALLOW_LOCAL_WS") == "1":
            import ipaddress
            client_host = ws.client.host if ws.client else ""
            try:
                if not ipaddress.ip_address(client_host).is_loopback:
                    await ws.close(code=4001, reason="Unauthorized")
                    return
            except ValueError:
                await ws.close(code=4001, reason="Unauthorized")
                return
        else:
            await ws.close(code=4001, reason="Unauthorized")
            return

    await ws.accept()
    _ws_clients.add(ws)
    logger.info("[BroadcastWS] client connected (%d total)", len(_ws_clients))

    try:
        while True:
            engine = _get_engine()
            status = engine.get_status()
            status["latest_health"] = _latest_health
            await ws.send_json({"type": "broadcast_pulse", **status})

            try:
                await asyncio.wait_for(ws.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.debug("[BroadcastWS] connection error")
    finally:
        _ws_clients.discard(ws)
        logger.info("[BroadcastWS] client disconnected (%d remaining)", len(_ws_clients))
