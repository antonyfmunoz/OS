#!/usr/bin/env python3
"""Browser relay — streams a headless Chromium viewport to cockpit viewers.

Listens on ws://0.0.0.0:8086/browser.

Uses Playwright to launch headless Chromium and CDP (Chrome DevTools Protocol)
to capture frames via Page.startScreencast and replay input via Input.dispatch*.

Protocol:
  Relay -> Cockpit (binary):
    raw JPEG bytes for live viewport frames
  Relay -> Cockpit (JSON):
    {"type": "url_changed", "url": str}
    {"type": "title_changed", "title": str}
    {"type": "loading", "loading": bool}
    {"type": "viewport", "width": int, "height": int}
    {"type": "cursor", "cursor": str}
    {"type": "error", "error": str}
  Cockpit -> Relay (JSON):
    {"type": "navigate", "url": str}
    {"type": "back"}
    {"type": "forward"}
    {"type": "reload"}
    {"type": "mouse", "action": str, "x": int, "y": int, ...}
    {"type": "key", "action": str, "key": str, "code": str, ...}
    {"type": "resize", "width": int, "height": int}
"""

from __future__ import annotations

import asyncio
import base64
import hmac
import json
import logging
import os
import sys
import time
from typing import Any

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

import websockets
import websockets.server

from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format="[browser-relay] %(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("browser_relay")

HOST = os.getenv("BROWSER_RELAY_HOST", "0.0.0.0")
PORT = int(os.getenv("BROWSER_RELAY_PORT", "8086"))
MAX_FRAME_BYTES = 2 * 1024 * 1024
_AUTH_TOKEN = os.getenv("BROWSER_RELAY_TOKEN", "")
_ALLOWED_ORIGINS = {
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "https://universalmetaharness.tech",
}

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
JPEG_QUALITY = 80

# ── Global state ──────────────────────────────────────────────

_clients: set[Any] = set()
_page: Any = None
_cdp: Any = None
_browser: Any = None
_context: Any = None
_pw: Any = None
_current_url: str = "about:blank"
_current_title: str = ""
_loading: bool = False
_viewport_width: int = DEFAULT_WIDTH
_viewport_height: int = DEFAULT_HEIGHT
_frame_count: int = 0
_last_frame_at: float = 0.0
_screencast_active: bool = False


# ── Auth ──────────────────────────────────────────────────────

def _check_auth(ws: Any) -> bool:
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


# ── Broadcast ─────────────────────────────────────────────────

async def send_json(ws: Any, data: dict[str, Any]) -> None:
    try:
        await ws.send(json.dumps(data))
    except Exception as exc:
        log.debug("send_json failed (%s): %s", data.get("type", "?"), exc)


async def broadcast_json(data: dict[str, Any]) -> None:
    if not _clients:
        return
    msg = json.dumps(data)
    clients = list(_clients)
    results = await asyncio.gather(
        *(ws.send(msg) for ws in clients),
        return_exceptions=True,
    )
    dead = {clients[i] for i, r in enumerate(results) if isinstance(r, Exception)}
    if dead:
        _clients.difference_update(dead)


async def broadcast_frame(jpeg_bytes: bytes) -> None:
    global _frame_count, _last_frame_at

    if len(jpeg_bytes) > MAX_FRAME_BYTES:
        log.warning("frame too large: %d bytes, dropping", len(jpeg_bytes))
        return

    _frame_count += 1
    _last_frame_at = time.time()

    if not _clients:
        return

    clients = list(_clients)
    results = await asyncio.gather(
        *(ws.send(jpeg_bytes) for ws in clients),
        return_exceptions=True,
    )
    dead = {clients[i] for i, r in enumerate(results) if isinstance(r, Exception)}
    if dead:
        log.debug("cleaned %d stale viewer(s)", len(dead))
        _clients.difference_update(dead)


# ── CDP screencast ────────────────────────────────────────────

async def _start_screencast() -> None:
    global _screencast_active
    if _screencast_active or not _cdp:
        return
    try:
        await _cdp.send("Page.startScreencast", {
            "format": "jpeg",
            "quality": JPEG_QUALITY,
            "maxWidth": _viewport_width,
            "maxHeight": _viewport_height,
        })
        _screencast_active = True
        log.info("screencast started (%dx%d q%d)", _viewport_width, _viewport_height, JPEG_QUALITY)
    except Exception as exc:
        log.error("failed to start screencast: %s", exc)


async def _stop_screencast() -> None:
    global _screencast_active
    if not _screencast_active or not _cdp:
        return
    try:
        await _cdp.send("Page.stopScreencast")
        _screencast_active = False
        log.info("screencast stopped")
    except Exception:
        _screencast_active = False


async def _on_screencast_frame(params: dict[str, Any]) -> None:
    session_id = params.get("sessionId", 0)
    data = params.get("data", "")
    if not data:
        return

    jpeg_bytes = base64.b64decode(data)

    try:
        await _cdp.send("Page.screencastFrameAck", {"sessionId": session_id})
    except Exception:
        pass

    await broadcast_frame(jpeg_bytes)


# ── Page event handlers ──────────────────────────────────────

async def _on_frame_navigated(params: dict[str, Any]) -> None:
    global _current_url
    frame = params.get("frame", {})
    if frame.get("parentId"):
        return
    url = frame.get("url", "")
    if url and url != _current_url:
        _current_url = url
        await broadcast_json({"type": "url_changed", "url": _current_url})


async def _on_load_event() -> None:
    global _loading, _current_title
    _loading = False
    await broadcast_json({"type": "loading", "loading": False})
    try:
        result = await _cdp.send("Runtime.evaluate", {"expression": "document.title"})
        title = result.get("result", {}).get("value", "")
        if title != _current_title:
            _current_title = title
            await broadcast_json({"type": "title_changed", "title": _current_title})
    except Exception:
        pass


async def _on_dialog(params: dict[str, Any]) -> None:
    try:
        await _cdp.send("Page.handleJavaScriptDialog", {"accept": True})
    except Exception:
        pass


# ── Input dispatch ────────────────────────────────────────────

async def _handle_mouse(msg: dict[str, Any]) -> None:
    if not _cdp:
        return
    params: dict[str, Any] = {
        "type": msg["action"],
        "x": msg["x"],
        "y": msg["y"],
    }
    action = msg["action"]
    if action in ("mousePressed", "mouseReleased"):
        params["button"] = msg.get("button", "left")
        params["clickCount"] = msg.get("clickCount", 1)
    if action == "mouseWheel":
        params["deltaX"] = msg.get("deltaX", 0)
        params["deltaY"] = msg.get("deltaY", 0)
    try:
        await _cdp.send("Input.dispatchMouseEvent", params)
    except Exception as exc:
        log.debug("mouse dispatch error: %s", exc)


async def _handle_key(msg: dict[str, Any]) -> None:
    if not _cdp:
        return
    params: dict[str, Any] = {
        "type": msg["action"],
        "key": msg.get("key", ""),
        "code": msg.get("code", ""),
        "modifiers": msg.get("modifiers", 0),
    }
    if msg["action"] == "keyDown" and msg.get("text"):
        params["text"] = msg["text"]
    try:
        await _cdp.send("Input.dispatchKeyEvent", params)
    except Exception as exc:
        log.debug("key dispatch error: %s", exc)


async def _handle_navigate(msg: dict[str, Any]) -> None:
    global _loading
    if not _cdp:
        return
    url = msg.get("url", "").strip()
    if not url:
        return
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    _loading = True
    await broadcast_json({"type": "loading", "loading": True})
    try:
        await _cdp.send("Page.navigate", {"url": url})
    except Exception as exc:
        log.error("navigate error: %s", exc)
        _loading = False
        await broadcast_json({"type": "loading", "loading": False})


async def _handle_resize(msg: dict[str, Any]) -> None:
    global _viewport_width, _viewport_height
    w = max(320, min(msg.get("width", DEFAULT_WIDTH), 3840))
    h = max(240, min(msg.get("height", DEFAULT_HEIGHT), 2160))
    if w == _viewport_width and h == _viewport_height:
        return
    _viewport_width = w
    _viewport_height = h
    if _page:
        try:
            await _page.set_viewport_size({"width": w, "height": h})
        except Exception:
            pass
    await _stop_screencast()
    await _start_screencast()
    await broadcast_json({"type": "viewport", "width": w, "height": h})


# ── Client handler ────────────────────────────────────────────

async def handle_client(ws: Any) -> None:
    if not _check_auth(ws):
        log.warning("auth failed for client")
        await ws.close(4001, "unauthorized")
        return

    _clients.add(ws)
    client_count = len(_clients)
    log.info("viewer connected (%d total)", client_count)

    if not _screencast_active:
        await _start_screencast()

    try:
        await send_json(ws, {"type": "url_changed", "url": _current_url})
        await send_json(ws, {"type": "title_changed", "title": _current_title})
        await send_json(ws, {"type": "loading", "loading": _loading})
        await send_json(ws, {"type": "viewport", "width": _viewport_width, "height": _viewport_height})

        async for raw in ws:
            if isinstance(raw, bytes):
                continue
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")
            if msg_type == "navigate":
                await _handle_navigate(msg)
            elif msg_type == "mouse":
                await _handle_mouse(msg)
            elif msg_type == "key":
                await _handle_key(msg)
            elif msg_type == "back":
                if _page:
                    try:
                        await _page.go_back()
                    except Exception:
                        pass
            elif msg_type == "forward":
                if _page:
                    try:
                        await _page.go_forward()
                    except Exception:
                        pass
            elif msg_type == "reload":
                if _page:
                    try:
                        await _page.reload()
                    except Exception:
                        pass
            elif msg_type == "resize":
                await _handle_resize(msg)
            elif msg_type == "ping":
                await send_json(ws, {"type": "pong"})

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as exc:
        log.error("client handler error: %s", exc)
    finally:
        _clients.discard(ws)
        remaining = len(_clients)
        log.info("viewer disconnected (%d remaining)", remaining)


# ── Browser lifecycle ─────────────────────────────────────────

async def _launch_browser() -> None:
    global _pw, _browser, _context, _page, _cdp

    log.info("launching headless Chromium via Playwright...")
    _pw = await async_playwright().start()
    _browser = await _pw.chromium.launch(
        headless=True,
        args=[
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
        ],
    )
    _context = await _browser.new_context(
        viewport={"width": _viewport_width, "height": _viewport_height},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    )
    _page = await _context.new_page()

    _page.on("popup", _on_popup)

    _cdp = await _context.new_cdp_session(_page)

    _cdp.on("Page.screencastFrame", _on_screencast_frame)
    _cdp.on("Page.frameNavigated", _on_frame_navigated)
    _cdp.on("Page.loadEventFired", lambda _: asyncio.ensure_future(_on_load_event()))
    _cdp.on("Page.javascriptDialogOpening", _on_dialog)

    await _cdp.send("Page.enable")

    await _page.goto("about:blank")
    log.info("Chromium ready (%dx%d)", _viewport_width, _viewport_height)


async def _on_popup(popup: Any) -> None:
    global _loading
    try:
        url = popup.url
        if url and _page:
            _loading = True
            await broadcast_json({"type": "loading", "loading": True})
            await _cdp.send("Page.navigate", {"url": url})
        await popup.close()
    except Exception as exc:
        log.debug("popup handling error: %s", exc)


# ── Main ──────────────────────────────────────────────────────

async def main() -> None:
    if not _AUTH_TOKEN:
        log.warning(
            "BROWSER_RELAY_TOKEN not set — authentication DISABLED. "
            "Set BROWSER_RELAY_TOKEN env var to enable auth."
        )

    await _launch_browser()

    log.info("starting WebSocket server on ws://%s:%d/browser", HOST, PORT)

    async with websockets.serve(
        handle_client,
        HOST,
        PORT,
        ping_interval=20,
        ping_timeout=20,
        max_size=65536,
        process_request=_check_origin,
    ):
        log.info("browser relay ready — accepting viewers")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
