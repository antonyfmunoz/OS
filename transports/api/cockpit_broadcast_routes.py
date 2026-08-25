"""Broadcast API — start/stop/status + WebSocket health push.

All endpoints prefixed /api/umh/broadcast/ and registered via include_router.
Models defined locally (not substrate/) for Slice 0.

Node-aware: every mutating endpoint accepts an optional `target_node`
query param.  "local" (default) runs FFmpeg on the VPS; any other value
dispatches to that mesh node via the HTTP relay on port 8095.
"""
# ruff: noqa: E402, I001

from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

_app_root = os.environ.get("UMH_ROOT", "/opt/OS")
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from transports.api.cockpit_auth import require_clerk_auth, validate_ws_clerk_token

from adapters.broadcast.scene_model import (
    CompositeConfig,
    Scene,
    SourceEntry,
    SourceLayout,
)

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

broadcast_router = APIRouter(prefix="/broadcast", tags=["broadcast"])
broadcast_ws_router = APIRouter(prefix="/broadcast", tags=["broadcast-ws"])

_LOCAL = "local"
_MESH_RELAY_PORT = 8095
_REMOTE_TIMEOUT_S = 30


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


# ── Local engine singleton ──

_engine = None
_engine_lock = asyncio.Lock()


def _get_engine():
    global _engine
    if _engine is None:
        from adapters.broadcast.engine import BroadcastEngine

        _engine = BroadcastEngine()
    return _engine


# ── Active node tracking ──

_active_node: str = _LOCAL
_active_node_lock = asyncio.Lock()


# ── WebSocket health push ──

_ws_clients: set[WebSocket] = set()
_latest_health: dict[str, Any] = {}


def _on_engine_health(health: dict[str, Any]) -> None:
    global _latest_health
    _latest_health = health


# ── Mesh dispatch helper ──


async def _dispatch_remote(
    node_id: str,
    capability: str,
    params: dict[str, Any],
    timeout: int = _REMOTE_TIMEOUT_S,
) -> dict[str, Any]:
    """Dispatch a broadcast capability to a remote mesh node via the mesh relay.

    Authenticates to the relay with the bearer secret and, for write-class
    broadcast operations (everything except read-only health), attaches a
    signed governance verdict bound to node+capability so the relay and node
    validate before executing. Fail-closed on missing secrets.
    """
    import os
    from uuid import uuid4

    import aiohttp

    from substrate.execution.mesh_verdict import get_verdict_secret, is_write_class, sign_verdict

    full_cap = f"broadcast.{capability}"
    risk_class = "read_only" if capability in ("health", "status") else "reversible_write"

    relay_secret = os.environ.get("UMH_MESH_RELAY_SECRET", "").strip()
    if not relay_secret:
        raise HTTPException(status_code=503, detail="mesh relay secret unset (fail-closed)")
    req_headers = {"Authorization": f"Bearer {relay_secret}"}

    verdict_token = ""
    if is_write_class(risk_class):
        if not get_verdict_secret():
            raise HTTPException(status_code=503, detail="mesh verdict secret unset (fail-closed)")
        verdict_token = sign_verdict(
            verdict_id=uuid4().hex,
            node_id=node_id,
            capability=full_cap,
            risk_class=risk_class,
            ttl_seconds=timeout + 30,
        )

    relay_url = f"http://127.0.0.1:{_MESH_RELAY_PORT}/dispatch"
    payload = {
        "node_id": node_id,
        "capability": full_cap,
        "params": params,
        "risk_class": risk_class,
        "verdict_token": verdict_token,
        "timeout": timeout,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                relay_url,
                json=payload,
                headers=req_headers,
                timeout=aiohttp.ClientTimeout(total=timeout + 5),
            ) as resp:
                result = await resp.json()
    except Exception as exc:
        logger.error("[BroadcastRoutes] mesh dispatch failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach node {node_id}: {exc}",
        )

    if not result.get("ok"):
        error = result.get("error", "unknown error")
        status = result.get("status", "failed")
        if status == "timeout":
            raise HTTPException(status_code=504, detail=f"Node {node_id} timed out: {error}")
        raise HTTPException(status_code=502, detail=f"Node {node_id}: {error}")

    return result.get("result_data", result)


def _is_remote(target_node: str) -> bool:
    return target_node != _LOCAL


# ── HTTP Endpoints ──


@broadcast_router.post("/start")
async def start_broadcast(
    req: BroadcastStartRequest,
    _user=Depends(require_clerk_auth),
    target_node: str = Query(default=_LOCAL, description="Node to run engine on"),
):
    global _active_node

    gov_resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"start broadcast on {target_node}",
        execute_fn=lambda: ("governance check passed", True),
        source="cockpit",
        metadata={"target_node": target_node, "source_type": req.source_type.value},
    )
    if not gov_resp.success:
        return gov_resp.to_http_dict()

    if _is_remote(target_node):
        params = req.model_dump()
        params["source_type"] = req.source_type.value
        result = await _dispatch_remote(target_node, "start", params)
        async with _active_node_lock:
            _active_node = target_node
        return {"status": "started", "node": target_node, **result}

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

    async with _active_node_lock:
        _active_node = _LOCAL
    return {
        "status": "started",
        "node": _LOCAL,
        "pid": engine._lifecycle.pid if engine._lifecycle else None,
    }


@broadcast_router.post("/stop")
async def stop_broadcast(
    _user=Depends(require_clerk_auth),
    target_node: str = Query(default="", description="Node to stop; empty = active node"),
):
    global _active_node

    node = target_node or _active_node
    gov_resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"stop broadcast on {node}",
        execute_fn=lambda: ("governance check passed", True),
        source="cockpit",
        metadata={"target_node": node},
    )
    if not gov_resp.success:
        return gov_resp.to_http_dict()

    if _is_remote(node):
        result = await _dispatch_remote(node, "stop", {})
        async with _active_node_lock:
            _active_node = _LOCAL
        return {"status": "stopped", "node": node, **result}

    engine = _get_engine()
    async with _engine_lock:
        if engine.state == "idle":
            return {"status": "already_stopped", "node": _LOCAL}
        code = await engine.stop()

    async with _active_node_lock:
        _active_node = _LOCAL
    return {"status": "stopped", "node": _LOCAL, "exit_code": code}


@broadcast_router.get("/status")
async def get_broadcast_status(
    _user=Depends(require_clerk_auth),
    target_node: str = Query(default="", description="Node to query; empty = active node"),
):
    node = target_node or _active_node
    if _is_remote(node):
        try:
            result = await _dispatch_remote(node, "status", {}, timeout=10)
            result["node"] = node
            return result
        except HTTPException:
            return {"state": "unreachable", "node": node}

    engine = _get_engine()
    status = engine.get_status()
    status["node"] = _LOCAL
    return status


# ── Composite (multi-source + scene switching) ──


class SourceEntryRequest(BaseModel):
    source_id: str
    source_type: str = Field(default="test_pattern")
    source_config: dict[str, Any] = Field(default_factory=dict)
    x: int = Field(default=0)
    y: int = Field(default=0)
    width: int = Field(default=640)
    height: int = Field(default=480)
    z_order: int = Field(default=0)
    enabled: bool = Field(default=True)


class SourceLayoutRequest(BaseModel):
    x: int = Field(default=0)
    y: int = Field(default=0)
    width: int = Field(default=640)
    height: int = Field(default=480)
    enabled: bool = Field(default=True)


class SceneRequest(BaseModel):
    scene_id: str
    name: str
    source_layouts: dict[str, SourceLayoutRequest] = Field(default_factory=dict)


class CompositeStartRequest(BaseModel):
    sources: list[SourceEntryRequest]
    scenes: list[SceneRequest] = Field(default_factory=list)
    active_scene_id: str | None = Field(default=None)
    output_url: str
    canvas_width: int = Field(default=1920)
    canvas_height: int = Field(default=1080)
    fps: int = Field(default=30, ge=1, le=120)
    video_codec: str = Field(default="libx264")
    video_bitrate: str = Field(default="4500k")
    audio_codec: str = Field(default="aac")
    audio_bitrate: str = Field(default="128k")
    keyframe_interval: int = Field(default=2, ge=1, le=10)
    preset: str = Field(default="veryfast")
    container_format: str = Field(default="flv")


class SceneSwitchRequest(BaseModel):
    scene_id: str


@broadcast_router.post("/composite/start")
async def start_composite_broadcast(
    req: CompositeStartRequest,
    _user=Depends(require_clerk_auth),
    target_node: str = Query(default=_LOCAL, description="Node to run engine on"),
):
    global _active_node

    gov_resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"start composite broadcast on {target_node}",
        execute_fn=lambda: ("governance check passed", True),
        source="cockpit",
        metadata={"target_node": target_node, "source_count": len(req.sources)},
    )
    if not gov_resp.success:
        return gov_resp.to_http_dict()

    if _is_remote(target_node):
        params = req.model_dump()
        result = await _dispatch_remote(target_node, "start_composite", params, timeout=30)
        async with _active_node_lock:
            _active_node = target_node
        return {"status": "started", "mode": "composite", "node": target_node, **result}

    engine = _get_engine()
    async with _engine_lock:
        if engine.state == "live":
            raise HTTPException(status_code=409, detail="Already broadcasting")

        config = CompositeConfig(
            sources=[SourceEntry(**s.model_dump()) for s in req.sources],
            scenes=[
                Scene(
                    scene_id=s.scene_id,
                    name=s.name,
                    source_layouts={
                        k: SourceLayout(**v.model_dump()) for k, v in s.source_layouts.items()
                    },
                )
                for s in req.scenes
            ],
            active_scene_id=req.active_scene_id,
            output_url=req.output_url,
            canvas_width=req.canvas_width,
            canvas_height=req.canvas_height,
            fps=req.fps,
            video_codec=req.video_codec,
            video_bitrate=req.video_bitrate,
            audio_codec=req.audio_codec,
            audio_bitrate=req.audio_bitrate,
            keyframe_interval=req.keyframe_interval,
            preset=req.preset,
            container_format=req.container_format,
        )

        engine.set_health_callback(_on_engine_health)
        ok = await engine.start_composite(config)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to start composite broadcast")

    async with _active_node_lock:
        _active_node = _LOCAL
    return {
        "status": "started",
        "mode": "composite",
        "node": _LOCAL,
        "pid": engine._lifecycle.pid if engine._lifecycle else None,
        "active_scene_id": req.active_scene_id,
        "source_count": len(req.sources),
        "scene_count": len(req.scenes),
    }


@broadcast_router.post("/scene/switch")
async def switch_scene(
    req: SceneSwitchRequest,
    _user=Depends(require_clerk_auth),
    target_node: str = Query(default="", description="Node; empty = active node"),
):
    node = target_node or _active_node

    gov_resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"switch broadcast scene to {req.scene_id}",
        execute_fn=lambda: ("governance check passed", True),
        source="cockpit",
    )
    if not gov_resp.success:
        return gov_resp.to_http_dict()

    if _is_remote(node):
        result = await _dispatch_remote(node, "switch_scene", {"scene_id": req.scene_id})
        return result

    engine = _get_engine()
    result = await engine.switch_scene(req.scene_id)
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Scene switch failed"),
        )
    return result


@broadcast_router.get("/scenes")
async def list_scenes(
    _user=Depends(require_clerk_auth),
    target_node: str = Query(default="", description="Node; empty = active node"),
):
    node = target_node or _active_node
    if _is_remote(node):
        try:
            result = await _dispatch_remote(node, "status", {}, timeout=10)
            return {
                "scenes": result.get("scenes", []),
                "active_scene_id": result.get("active_scene_id"),
                "composite": result.get("composite", False),
                "node": node,
            }
        except HTTPException:
            return {"scenes": [], "active_scene_id": None, "composite": False, "node": node}

    engine = _get_engine()
    status = engine.get_status()
    return {
        "scenes": status.get("scenes", []),
        "active_scene_id": status.get("active_scene_id"),
        "composite": status.get("composite", False),
        "node": _LOCAL,
    }


# ── Node discovery ──


@broadcast_router.get("/nodes")
async def list_broadcast_nodes(_user=Depends(require_clerk_auth)):
    """List mesh nodes that advertise broadcast capability."""
    import os

    import aiohttp

    nodes = [{"node_id": _LOCAL, "status": "available", "local": True}]

    relay_secret = os.environ.get("UMH_MESH_RELAY_SECRET", "").strip()
    if not relay_secret:
        # /nodes now requires relay auth (fail-closed) — return local only.
        return {"nodes": nodes, "active_node": _active_node}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://127.0.0.1:{_MESH_RELAY_PORT}/nodes",
                headers={"Authorization": f"Bearer {relay_secret}"},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                all_nodes = await resp.json()
    except Exception:
        return {"nodes": nodes, "active_node": _active_node}

    for n in all_nodes:
        caps = [c.get("name", "") if isinstance(c, dict) else c for c in n.get("capabilities", [])]
        if "broadcast" in caps:
            nodes.append(
                {
                    "node_id": n.get("node_id", ""),
                    "hostname": n.get("hostname", ""),
                    "os": n.get("os", ""),
                    "status": n.get("status", "connected"),
                    "local": False,
                }
            )

    return {"nodes": nodes, "active_node": _active_node}


def _extract_ws_subprotocol(ws: WebSocket) -> str | None:
    """Return the bearer subprotocol if the client sent one, else None."""
    for proto in (ws.headers.get("sec-websocket-protocol") or "").split(","):
        proto = proto.strip()
        if proto.startswith("bearer."):
            return proto
    return None


# ── WebSocket health endpoint ──


@broadcast_ws_router.websocket("/ws")
async def broadcast_ws(ws: WebSocket):
    user = validate_ws_clerk_token(ws)
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

    subprotocol = _extract_ws_subprotocol(ws)
    await ws.accept(subprotocol=subprotocol)
    _ws_clients.add(ws)
    logger.info("[BroadcastWS] client connected (%d total)", len(_ws_clients))

    try:
        while True:
            node = _active_node
            if _is_remote(node):
                status = await _get_remote_health(node)
            else:
                engine = _get_engine()
                status = engine.get_status()
                status["latest_health"] = _latest_health
            status["active_node"] = node
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


async def _get_remote_health(node_id: str) -> dict[str, Any]:
    """Poll remote engine health via mesh relay — best-effort."""
    import os

    import aiohttp

    relay_secret = os.environ.get("UMH_MESH_RELAY_SECRET", "").strip()
    if not relay_secret:
        return {"state": "unknown", "error": "mesh relay secret unset (fail-closed)"}
    req_headers = {"Authorization": f"Bearer {relay_secret}"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://127.0.0.1:{_MESH_RELAY_PORT}/dispatch",
                json={
                    "node_id": node_id,
                    "capability": "broadcast.health",
                    "params": {},
                    "risk_class": "read_only",
                    "timeout": 5,
                },
                headers=req_headers,
                timeout=aiohttp.ClientTimeout(total=8),
            ) as resp:
                result = await resp.json()
        if result.get("ok"):
            data = result.get("result_data", {})
            return {
                "state": data.get("state", "unknown"),
                "health": data.get("health"),
                "latest_health": data.get("health", {}),
            }
    except Exception as exc:
        logger.debug("[BroadcastWS] remote health poll failed: %s", exc)

    return {"state": "unreachable", "health": None, "latest_health": {}}
