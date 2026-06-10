#!/usr/bin/env python3
"""Vision relay server — bridges Beast camera frames to cockpit viewers.

Listens on ws://0.0.0.0:8097/vision.

Receives camera frames from the node mesh (via internal callback or HTTP POST)
and fans them out to all connected cockpit WebSocket clients.

Protocol:
  Cockpit -> Relay (JSON):
    {"type": "vision_subscribe", "fps": 2, "quality": 60}
    {"type": "vision_unsubscribe"}
    {"type": "camera_preset", "preset": "keyboard"}
    {"type": "camera_snapshot"}
    {"type": "camera_start"}
    {"type": "camera_stop"}
  Relay -> Cockpit (JSON):
    {"type": "vision_status", "streaming": bool, "fps": int, "source": str}
    {"type": "camera_presets", "presets": {...}}
    {"type": "vision_snapshot", "image_base64": str, ...}
    {"type": "vision_error", "error": str}
  Relay -> Cockpit (binary):
    raw JPEG bytes for live preview
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import sys
import time
from typing import Any

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

try:
    import websockets
    import websockets.server
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets>=13.0"])
    import websockets
    import websockets.server

logging.basicConfig(
    level=logging.INFO,
    format="[vision] %(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("vision_relay")

HOST = os.getenv("VISION_RELAY_HOST", "127.0.0.1")
PORT = int(os.getenv("VISION_RELAY_PORT", "8097"))
MAX_FRAME_BYTES = 2 * 1024 * 1024
_AUTH_TOKEN = os.getenv("VISION_RELAY_TOKEN", "")
_ALLOWED_ORIGINS = {
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "file://",
    "https://universalmetaharness.tech",
}

_clients: set[Any] = set()
_latest_frame: bytes | None = None
_latest_frame_meta: dict[str, Any] = {}
_stream_active = False
_mesh_dispatch_url = os.getenv(
    "MESH_DISPATCH_URL",
    "http://localhost:8095/dispatch",
)


async def send_json(ws: Any, data: dict[str, Any]) -> None:
    try:
        await ws.send(json.dumps(data))
    except Exception:
        pass


async def _check_auth(ws: Any) -> bool:
    """Validate auth token from query string if token is configured."""
    if not _AUTH_TOKEN:
        return True
    path = getattr(ws, "request", None)
    if path is None:
        return True
    qs = getattr(path, "path", "")
    if "?" in qs:
        params = dict(p.split("=", 1) for p in qs.split("?", 1)[1].split("&") if "=" in p)
        if params.get("token") == _AUTH_TOKEN:
            return True
    return False


async def handle_vision(ws: Any) -> None:
    if not await _check_auth(ws):
        log.warning("viewer rejected: invalid auth token from %s", ws.remote_address)
        await send_json(ws, {"type": "vision_error", "error": "authentication required"})
        await ws.close(4001, "authentication required")
        return

    log.info("viewer connected: %s", ws.remote_address)
    _clients.add(ws)
    subscribed = False
    try:
        await send_json(ws, {"type": "connected"})

        async for message in ws:
            if not isinstance(message, str):
                continue
            try:
                msg = json.loads(message)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "vision_subscribe":
                subscribed = True
                log.info("viewer subscribed: fps=%s q=%s", msg.get("fps"), msg.get("quality"))
                await send_json(ws, {
                    "type": "vision_status",
                    "streaming": _stream_active,
                    "source": _latest_frame_meta.get("node_id", "none"),
                })

            elif msg_type == "vision_unsubscribe":
                subscribed = False
                log.info("viewer unsubscribed")

            elif msg_type == "camera_start":
                await _dispatch_to_beast("camera.stream_start", {
                    "fps": msg.get("fps", 2),
                    "width": msg.get("width", 640),
                    "height": msg.get("height", 480),
                    "quality": msg.get("quality", 60),
                })

            elif msg_type == "camera_stop":
                await _dispatch_to_beast("camera.stream_stop", {})

            elif msg_type == "camera_preset":
                preset = msg.get("preset", "")
                result = await _dispatch_to_beast("camera.set_preset", {"preset": preset})
                if result and not result.get("success"):
                    await send_json(ws, {"type": "vision_error", "error": result.get("error", "preset failed")})

            elif msg_type == "camera_snapshot":
                result = await _dispatch_to_beast("camera.snapshot", {
                    "width": msg.get("width", 1280),
                    "height": msg.get("height", 720),
                    "quality": msg.get("quality", 75),
                })
                if result and result.get("success"):
                    await send_json(ws, {
                        "type": "vision_snapshot",
                        "image_base64": result.get("image_base64", ""),
                        "width": result.get("width"),
                        "height": result.get("height"),
                    })
                else:
                    await send_json(ws, {
                        "type": "vision_error",
                        "error": result.get("error", "snapshot failed") if result else "dispatch failed",
                    })

            elif msg_type == "camera_list_presets":
                result = await _dispatch_to_beast("camera.list_presets", {})
                if result and result.get("success"):
                    await send_json(ws, {
                        "type": "camera_presets",
                        "presets": result.get("presets", {}),
                    })

            elif msg_type == "camera_save_preset":
                result = await _dispatch_to_beast("camera.save_preset", {
                    "preset": msg.get("preset", ""),
                    "label": msg.get("label", ""),
                    "analysis_hint": msg.get("analysis_hint", ""),
                })
                if result and result.get("success"):
                    await send_json(ws, {"type": "preset_saved", "preset": msg.get("preset")})
                else:
                    await send_json(ws, {
                        "type": "vision_error",
                        "error": result.get("error", "save failed") if result else "dispatch failed",
                    })

            elif msg_type == "camera_get_position":
                result = await _dispatch_to_beast("camera.get_position", {})
                if result:
                    await send_json(ws, {"type": "camera_position", **result})

            elif msg_type == "camera_status":
                result = await _dispatch_to_beast("camera.status", {})
                if result:
                    await send_json(ws, {"type": "vision_status", **result})

    except websockets.exceptions.ConnectionClosed:
        log.info("viewer disconnected: %s", ws.remote_address)
    except Exception as e:
        log.error("viewer session error: %s", e)
    finally:
        _clients.discard(ws)


async def broadcast_frame(jpeg_bytes: bytes, meta: dict[str, Any]) -> None:
    """Called by mesh frame callback — fan out to all subscribed viewers."""
    global _latest_frame, _latest_frame_meta, _stream_active

    if len(jpeg_bytes) > MAX_FRAME_BYTES:
        log.warning("frame too large: %d bytes, dropping", len(jpeg_bytes))
        return

    _latest_frame = jpeg_bytes
    _latest_frame_meta = meta
    _stream_active = True

    dead = set()
    for ws in _clients:
        try:
            await ws.send(jpeg_bytes)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


def receive_mesh_frame(frame_data: dict[str, Any]) -> None:
    """Sync entry point for node mesh callback — decodes base64 and broadcasts."""
    b64 = frame_data.get("image_base64", "")
    if not b64:
        return
    try:
        jpeg_bytes = base64.b64decode(b64)
    except Exception as exc:
        log.warning("invalid base64 frame: %s", exc)
        return

    meta = {k: v for k, v in frame_data.items() if k != "image_base64"}

    loop = _get_loop()
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_frame(jpeg_bytes, meta), loop)


_event_loop: asyncio.AbstractEventLoop | None = None


def _get_loop() -> asyncio.AbstractEventLoop | None:
    return _event_loop


async def _dispatch_to_beast(operation: str, params: dict[str, Any]) -> dict[str, Any] | None:
    """Dispatch a camera command to Beast via the mesh HTTP relay."""
    try:
        import urllib.request

        payload = json.dumps({
            "capability": operation,
            "params": params,
            "timeout": 10,
        }).encode()
        req = urllib.request.Request(
            _mesh_dispatch_url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        log.warning("mesh dispatch failed (%s): %s", operation, exc)
        return None


async def _health_server() -> None:
    """Minimal HTTP health endpoint on PORT+1."""
    from http.server import BaseHTTPRequestHandler
    import socketserver

    health_port = PORT + 1

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/health":
                body = json.dumps({
                    "status": "ok",
                    "viewers": len(_clients),
                    "streaming": _stream_active,
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = socketserver.TCPServer(("127.0.0.1", health_port), Handler)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, server.serve_forever)


async def main() -> None:
    global _event_loop
    _event_loop = asyncio.get_event_loop()

    log.info("Vision relay starting on ws://%s:%d/vision", HOST, PORT)
    asyncio.create_task(_health_server())

    async with websockets.serve(
        handle_vision, HOST, PORT,
        ping_interval=20, ping_timeout=20, max_size=MAX_FRAME_BYTES + 1024,
        origins=list(_ALLOWED_ORIGINS) if _ALLOWED_ORIGINS else None,
    ):
        log.info("Vision relay ready — frame fan-out mode")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
