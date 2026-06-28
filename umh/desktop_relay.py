#!/usr/bin/env python3
"""Desktop relay server — bridges Beast desktop frames to cockpit viewers.

Listens on ws://0.0.0.0:8100/desktop.

Receives desktop screenshots from the node mesh (via binary WS ingest)
and fans them out to all connected cockpit WebSocket clients.

Protocol:
  Cockpit -> Relay (JSON):
    {"type": "desktop_subscribe", "monitor": "M0"}
    {"type": "desktop_unsubscribe"}
  Relay -> Cockpit (JSON):
    {"type": "desktop_status", "streaming": bool, "monitor": str}
  Relay -> Cockpit (binary):
    raw JPEG bytes for live preview
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import struct
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
    format="[desktop] %(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("desktop_relay")

HOST = os.getenv("DESKTOP_RELAY_HOST", "0.0.0.0")
PORT = int(os.getenv("DESKTOP_RELAY_PORT", "8100"))
MAX_FRAME_BYTES = 2 * 1024 * 1024
_AUTH_TOKEN = os.getenv("DESKTOP_RELAY_TOKEN", "")
_FRAME_INGEST_TOKEN = os.getenv("DESKTOP_FRAME_TOKEN", "")
_ALLOWED_ORIGINS = {
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "https://universalmetaharness.tech",
}

_JPEG_SOI = b'\xff\xd8'

_clients: dict[Any, str | None] = {}  # ws -> subscribed monitor (None = all)
_latest_frames: dict[str, bytes] = {}  # monitor -> latest JPEG
_latest_metas: dict[str, dict[str, Any]] = {}  # monitor -> latest meta (width/height/etc)
_last_frame_at: float = 0.0
_frame_count: int = 0
_event_loop: asyncio.AbstractEventLoop | None = None


def _check_origin(connection: Any, request: Any) -> None:
    from http import HTTPStatus

    origin = None
    try:
        origin = request.headers.get("Origin")
    except Exception:
        pass

    if origin is None:
        return
    if origin in _ALLOWED_ORIGINS:
        return

    log.warning("origin rejected: %s", origin)
    raise websockets.exceptions.InvalidOrigin(origin)


def _check_auth(ws: Any) -> bool:
    import hmac

    if not _AUTH_TOKEN:
        return True
    try:
        protocols = ws.request.headers.get_all("Sec-WebSocket-Protocol")
        for proto in protocols:
            for part in proto.split(","):
                candidate = part.strip()
                if candidate.startswith("auth."):
                    token = candidate[5:]
                    if hmac.compare_digest(token, _AUTH_TOKEN):
                        return True
    except Exception:
        pass
    return False


async def send_json(ws: Any, data: dict[str, Any]) -> None:
    try:
        await ws.send(json.dumps(data))
    except Exception as exc:
        log.debug("send_json failed (%s): %s", data.get("type", "?"), exc)


async def broadcast_frame(jpeg_bytes: bytes, meta: dict[str, Any]) -> None:
    """Fan out JPEG frame to viewers subscribed to the matching monitor."""
    global _last_frame_at, _frame_count

    if len(jpeg_bytes) > MAX_FRAME_BYTES:
        log.warning("frame too large: %d bytes, dropping", len(jpeg_bytes))
        return

    frame_monitor = meta.get("monitor", "M0")
    _latest_frames[frame_monitor] = jpeg_bytes
    _latest_metas[frame_monitor] = meta
    _last_frame_at = time.time()
    _frame_count += 1

    if not _clients:
        return

    targets = [ws for ws, mon in _clients.items() if mon is None or mon == frame_monitor]
    if not targets:
        return

    async def _send_to(ws: Any) -> bool:
        try:
            await ws.send(jpeg_bytes)
            return True
        except Exception:
            return False

    results = await asyncio.gather(*(_send_to(ws) for ws in targets), return_exceptions=True)

    dead = {targets[i] for i, ok in enumerate(results) if ok is not True}
    if dead:
        log.debug("cleaned %d stale viewer(s)", len(dead))
        for ws in dead:
            _clients.pop(ws, None)


def receive_binary_frame(jpeg_bytes: bytes, meta_json: str = "") -> None:
    """Binary frame ingest — raw JPEG bytes."""
    if len(jpeg_bytes) < 2 or jpeg_bytes[:2] != _JPEG_SOI:
        log.warning("binary frame rejected: not JPEG (size=%d)", len(jpeg_bytes))
        return
    meta: dict[str, Any] = {}
    if meta_json:
        try:
            meta = json.loads(meta_json)
        except Exception:
            pass
    loop = _event_loop
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_frame(jpeg_bytes, meta), loop)


async def handle_desktop(ws: Any) -> None:
    """Handle a cockpit viewer WS connection."""
    if not _check_auth(ws):
        log.warning("viewer rejected: invalid auth from %s", ws.remote_address)
        await send_json(ws, {"type": "desktop_error", "error": "authentication required"})
        await ws.close(4001, "authentication required")
        return

    log.info("desktop viewer connected: %s", ws.remote_address)
    _clients[ws] = None
    try:
        await send_json(ws, {"type": "connected"})
        await send_json(ws, {
            "type": "desktop_status",
            "streaming": _last_frame_at > 0 and (time.time() - _last_frame_at) < 10,
            "monitors": list(_latest_metas.keys()),
            "viewers": len(_clients),
        })

        async for message in ws:
            if not isinstance(message, str):
                continue
            try:
                msg = json.loads(message)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await send_json(ws, {"type": "pong"})
            elif msg_type == "desktop_subscribe":
                monitor = msg.get("monitor", "M0")
                _clients[ws] = monitor
                log.info("viewer subscribed: monitor=%s", monitor)
                mon_meta = _latest_metas.get(monitor, {})
                status: dict[str, Any] = {
                    "type": "desktop_status",
                    "streaming": _last_frame_at > 0 and (time.time() - _last_frame_at) < 10,
                    "monitor": monitor,
                }
                if mon_meta.get("width"):
                    status["width"] = mon_meta["width"]
                if mon_meta.get("height"):
                    status["height"] = mon_meta["height"]
                await send_json(ws, status)
                cached = _latest_frames.get(monitor)
                if cached:
                    try:
                        await ws.send(cached)
                    except Exception:
                        pass
            elif msg_type == "desktop_unsubscribe":
                _clients[ws] = None
                log.info("viewer unsubscribed")

    except websockets.exceptions.ConnectionClosed:
        log.info("desktop viewer disconnected: %s", ws.remote_address)
    except Exception as e:
        log.error("desktop viewer error: %s", e)
    finally:
        _clients.pop(ws, None)


async def _frame_ingest_ws_handler(ws: Any) -> None:
    """Handle persistent WS from mesh server for frame ingest."""
    if _FRAME_INGEST_TOKEN:
        try:
            token = await asyncio.wait_for(ws.recv(), timeout=5)
            if not isinstance(token, str) or token != _FRAME_INGEST_TOKEN:
                await ws.close(4001, "invalid token")
                return
        except Exception:
            return
    await ws.send("ok")

    log.info("desktop frame ingest WS connected")
    frame_n = 0
    try:
        async for msg in ws:
            if not isinstance(msg, bytes) or len(msg) < 6:
                continue
            meta_len = struct.unpack(">I", msg[:4])[0]
            if meta_len > 65536 or 4 + meta_len > len(msg):
                continue
            meta_json = msg[4:4 + meta_len]
            jpeg_bytes = msg[4 + meta_len:]
            if len(jpeg_bytes) < 2 or jpeg_bytes[:2] != _JPEG_SOI:
                continue
            try:
                meta = json.loads(meta_json) if meta_json else {}
                if not isinstance(meta, dict):
                    meta = {}
            except Exception:
                meta = {}
            frame_n += 1
            if frame_n <= 3 or frame_n % 500 == 0:
                log.info("ingest-ws frame %d: %d bytes jpeg, %d clients", frame_n, len(jpeg_bytes), len(_clients))
            await broadcast_frame(jpeg_bytes, meta)
    except websockets.ConnectionClosed:
        pass
    except Exception as exc:
        log.warning("desktop frame ingest WS error: %s", exc)
    log.info("desktop frame ingest WS disconnected after %d frames", frame_n)


async def _health_server() -> None:
    """Tiny HTTP health endpoint on PORT+1."""
    from http import HTTPStatus

    health_port = PORT + 1

    async def _handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            await asyncio.wait_for(reader.readline(), timeout=5)
        except Exception:
            writer.close()
            return
        body = json.dumps({
            "status": "ok",
            "service": "desktop_relay",
            "port": PORT,
            "clients": len(_clients),
            "frames": _frame_count,
            "last_frame_age_s": round(time.time() - _last_frame_at, 1) if _last_frame_at else None,
        })
        response = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"\r\n{body}"
        )
        writer.write(response.encode())
        await writer.drain()
        writer.close()

    try:
        srv = await asyncio.start_server(_handler, "127.0.0.1", health_port)
        log.info("health server on http://127.0.0.1:%d", health_port)
        async with srv:
            await srv.serve_forever()
    except Exception as exc:
        log.warning("health server failed: %s", exc)


async def main() -> None:
    global _event_loop
    _event_loop = asyncio.get_event_loop()

    if not _AUTH_TOKEN:
        log.warning("DESKTOP_RELAY_TOKEN not set — auth DISABLED")
    if not _FRAME_INGEST_TOKEN:
        log.warning("DESKTOP_FRAME_TOKEN not set — frame ingest auth DISABLED")

    ingest_port = PORT + 2
    log.info("Desktop relay starting on ws://%s:%d/desktop", HOST, PORT)
    log.info("Frame ingest WS on ws://%s:%d (persistent push)", HOST, ingest_port)
    asyncio.create_task(_health_server())

    await websockets.serve(
        _frame_ingest_ws_handler, "127.0.0.1", ingest_port,
        ping_interval=10, ping_timeout=20, max_size=MAX_FRAME_BYTES + 65536,
    )

    async with websockets.serve(
        handle_desktop, HOST, PORT,
        ping_interval=20, ping_timeout=20, max_size=MAX_FRAME_BYTES + 1024,
        process_request=_check_origin,
    ):
        log.info("Desktop relay ready — frame fan-out mode")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
