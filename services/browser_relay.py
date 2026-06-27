#!/usr/bin/env python3
"""Browser relay — streams headless Chromium viewports to cockpit viewers.

Listens on ws://0.0.0.0:8086/browser.

Supports up to 4 independent panes. Each pane is a separate Chromium tab
with its own CDP session, viewport, and client set. Pane ID is passed via
query parameter: ws://.../browser?pane=0

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
from urllib.parse import urlparse, parse_qs

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
MAX_PANES = 4
HEARTBEAT_INTERVAL = 1.0
DEFAULT_HOME_URL = "https://www.google.com"


# ── Pane state ───────────────────────────────────────────────

class PaneState:
    def __init__(self, pane_id: str) -> None:
        self.pane_id: str = pane_id
        self.page: Any = None
        self.cdp: Any = None
        self.clients: set[Any] = set()
        self.current_url: str = DEFAULT_HOME_URL
        self.current_title: str = ""
        self.loading: bool = False
        self.viewport_width: int = DEFAULT_WIDTH
        self.viewport_height: int = DEFAULT_HEIGHT
        self.frame_count: int = 0
        self.last_frame_at: float = 0.0
        self.screencast_active: bool = False
        self.heartbeat_task: Any = None


# ── Global state ─────────────────────────────────────────────

_panes: dict[str, PaneState] = {}
_browser: Any = None
_context: Any = None
_pw: Any = None


# ── Auth ─────────────────────────────────────────────────────

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


# ── Per-pane broadcast ───────────────────────────────────────

async def send_json(ws: Any, data: dict[str, Any]) -> None:
    try:
        await ws.send(json.dumps(data))
    except Exception as exc:
        log.debug("send_json failed (%s): %s", data.get("type", "?"), exc)


async def send_pane_json(pane: PaneState, data: dict[str, Any]) -> None:
    if not pane.clients:
        return
    msg = json.dumps(data)
    clients = list(pane.clients)
    results = await asyncio.gather(
        *(ws.send(msg) for ws in clients),
        return_exceptions=True,
    )
    dead = {clients[i] for i, r in enumerate(results) if isinstance(r, Exception)}
    if dead:
        pane.clients.difference_update(dead)


async def send_pane_frame(pane: PaneState, jpeg_bytes: bytes) -> None:
    if len(jpeg_bytes) > MAX_FRAME_BYTES:
        log.warning("pane %s: frame too large: %d bytes, dropping", pane.pane_id, len(jpeg_bytes))
        return

    pane.frame_count += 1
    pane.last_frame_at = time.time()

    if not pane.clients:
        return

    clients = list(pane.clients)
    results = await asyncio.gather(
        *(ws.send(jpeg_bytes) for ws in clients),
        return_exceptions=True,
    )
    dead = {clients[i] for i, r in enumerate(results) if isinstance(r, Exception)}
    if dead:
        log.debug("pane %s: cleaned %d stale viewer(s)", pane.pane_id, len(dead))
        pane.clients.difference_update(dead)


# ── CDP screencast (per-pane) ────────────────────────────────

async def _start_screencast(pane: PaneState) -> None:
    if pane.screencast_active or not pane.cdp:
        return
    try:
        await pane.cdp.send("Page.startScreencast", {
            "format": "jpeg",
            "quality": JPEG_QUALITY,
            "maxWidth": pane.viewport_width,
            "maxHeight": pane.viewport_height,
        })
        pane.screencast_active = True
        log.info("pane %s: screencast started (%dx%d q%d)",
                 pane.pane_id, pane.viewport_width, pane.viewport_height, JPEG_QUALITY)
    except Exception as exc:
        log.error("pane %s: failed to start screencast: %s", pane.pane_id, exc)


async def _stop_screencast(pane: PaneState) -> None:
    if not pane.screencast_active or not pane.cdp:
        return
    try:
        await pane.cdp.send("Page.stopScreencast")
        pane.screencast_active = False
        log.info("pane %s: screencast stopped", pane.pane_id)
    except Exception:
        pane.screencast_active = False


async def _heartbeat_loop(pane: PaneState) -> None:
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        if not pane.clients or not pane.cdp:
            continue
        elapsed = time.time() - pane.last_frame_at
        if elapsed < HEARTBEAT_INTERVAL:
            continue
        try:
            result = await pane.cdp.send("Page.captureScreenshot", {
                "format": "jpeg",
                "quality": JPEG_QUALITY,
            })
            data = result.get("data", "")
            if data:
                jpeg_bytes = base64.b64decode(data)
                await send_pane_frame(pane, jpeg_bytes)
        except Exception as exc:
            log.debug("pane %s: heartbeat screenshot error: %s", pane.pane_id, exc)


# ── Pane lifecycle ───────────────────────────────────────────

async def _create_pane(pane_id: str) -> PaneState:
    global _context
    pane = PaneState(pane_id)

    pane.page = await _context.new_page()

    def _make_popup_handler(p: PaneState):
        async def _on_popup(popup: Any) -> None:
            try:
                url = popup.url
                if url and p.page:
                    p.loading = True
                    await send_pane_json(p, {"type": "loading", "loading": True})
                    await p.cdp.send("Page.navigate", {"url": url})
                await popup.close()
            except Exception as exc:
                log.debug("pane %s: popup handling error: %s", p.pane_id, exc)
        return _on_popup

    pane.page.on("popup", _make_popup_handler(pane))

    pane.cdp = await _context.new_cdp_session(pane.page)

    def _make_frame_handler(p: PaneState):
        async def _on_frame(params: dict[str, Any]) -> None:
            session_id = params.get("sessionId", 0)
            data = params.get("data", "")
            if not data:
                return
            jpeg_bytes = base64.b64decode(data)
            try:
                await p.cdp.send("Page.screencastFrameAck", {"sessionId": session_id})
            except Exception:
                pass
            await send_pane_frame(p, jpeg_bytes)
        return _on_frame

    def _make_nav_handler(p: PaneState):
        async def _on_nav(params: dict[str, Any]) -> None:
            frame = params.get("frame", {})
            if frame.get("parentId"):
                return
            url = frame.get("url", "")
            if url and url != p.current_url:
                p.current_url = url
                await send_pane_json(p, {"type": "url_changed", "url": p.current_url})
        return _on_nav

    def _make_load_handler(p: PaneState):
        async def _on_load(_params: Any) -> None:
            p.loading = False
            await send_pane_json(p, {"type": "loading", "loading": False})
            try:
                result = await p.cdp.send("Runtime.evaluate", {"expression": "document.title"})
                title = result.get("result", {}).get("value", "")
                if title != p.current_title:
                    p.current_title = title
                    await send_pane_json(p, {"type": "title_changed", "title": p.current_title})
            except Exception:
                pass
        return _on_load

    def _make_dialog_handler(p: PaneState):
        async def _on_dialog(params: dict[str, Any]) -> None:
            try:
                await p.cdp.send("Page.handleJavaScriptDialog", {"accept": True})
            except Exception:
                pass
        return _on_dialog

    pane.cdp.on("Page.screencastFrame", _make_frame_handler(pane))
    pane.cdp.on("Page.frameNavigated", _make_nav_handler(pane))
    pane.cdp.on("Page.loadEventFired", _make_load_handler(pane))
    pane.cdp.on("Page.javascriptDialogOpening", _make_dialog_handler(pane))

    await pane.cdp.send("Page.enable")
    await pane.page.goto(DEFAULT_HOME_URL)

    pane.heartbeat_task = asyncio.create_task(_heartbeat_loop(pane))

    _panes[pane_id] = pane
    log.info("pane %s: created (%d total)", pane_id, len(_panes))
    return pane


async def _destroy_pane(pane_id: str) -> None:
    pane = _panes.pop(pane_id, None)
    if not pane:
        return

    if pane.heartbeat_task:
        pane.heartbeat_task.cancel()
        try:
            await pane.heartbeat_task
        except asyncio.CancelledError:
            pass

    await _stop_screencast(pane)

    try:
        if pane.cdp:
            await pane.cdp.detach()
    except Exception:
        pass

    try:
        if pane.page:
            await pane.page.close()
    except Exception:
        pass

    log.info("pane %s: destroyed (%d remaining)", pane_id, len(_panes))


# ── Input dispatch (per-pane) ────────────────────────────────

async def _handle_mouse(pane: PaneState, msg: dict[str, Any]) -> None:
    if not pane.cdp:
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
        await pane.cdp.send("Input.dispatchMouseEvent", params)
    except Exception as exc:
        log.debug("pane %s: mouse dispatch error: %s", pane.pane_id, exc)


async def _handle_key(pane: PaneState, msg: dict[str, Any]) -> None:
    if not pane.cdp:
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
        await pane.cdp.send("Input.dispatchKeyEvent", params)
    except Exception as exc:
        log.debug("pane %s: key dispatch error: %s", pane.pane_id, exc)


async def _handle_insert_text(pane: PaneState, msg: dict[str, Any]) -> None:
    if not pane.cdp:
        return
    text = msg.get("text", "")
    if not text:
        return
    try:
        await pane.cdp.send("Input.insertText", {"text": text})
    except Exception as exc:
        log.debug("pane %s: insertText error: %s", pane.pane_id, exc)


async def _handle_navigate(pane: PaneState, msg: dict[str, Any]) -> None:
    if not pane.cdp:
        return
    url = msg.get("url", "").strip()
    if not url:
        return
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    pane.loading = True
    await send_pane_json(pane, {"type": "loading", "loading": True})
    try:
        await pane.cdp.send("Page.navigate", {"url": url})
    except Exception as exc:
        log.error("pane %s: navigate error: %s", pane.pane_id, exc)
        pane.loading = False
        await send_pane_json(pane, {"type": "loading", "loading": False})


async def _handle_resize(pane: PaneState, msg: dict[str, Any]) -> None:
    w = max(320, min(msg.get("width", DEFAULT_WIDTH), 3840))
    h = max(240, min(msg.get("height", DEFAULT_HEIGHT), 2160))
    if w == pane.viewport_width and h == pane.viewport_height:
        return
    pane.viewport_width = w
    pane.viewport_height = h
    if pane.page:
        try:
            await pane.page.set_viewport_size({"width": w, "height": h})
        except Exception:
            pass
    await _stop_screencast(pane)
    await _start_screencast(pane)
    await send_pane_json(pane, {"type": "viewport", "width": w, "height": h})


# ── Client handler ───────────────────────────────────────────

async def handle_client(ws: Any) -> None:
    if not _check_auth(ws):
        log.warning("auth failed for client")
        await ws.close(4001, "unauthorized")
        return

    parsed = urlparse(ws.request.path)
    qs = parse_qs(parsed.query)
    pane_id = qs.get("pane", ["0"])[0]

    if pane_id not in _panes:
        if len(_panes) >= MAX_PANES:
            log.warning("max panes reached (%d), rejecting pane %s", MAX_PANES, pane_id)
            await ws.close(4002, "max panes reached")
            return
        try:
            await _create_pane(pane_id)
        except Exception as exc:
            log.error("failed to create pane %s: %s", pane_id, exc)
            await send_json(ws, {"type": "error", "error": str(exc)})
            await ws.close(4003, "pane creation failed")
            return

    pane = _panes[pane_id]
    pane.clients.add(ws)
    log.info("pane %s: viewer connected (%d clients)", pane_id, len(pane.clients))

    await _stop_screencast(pane)
    await _start_screencast(pane)

    try:
        await send_json(ws, {"type": "url_changed", "url": pane.current_url})
        await send_json(ws, {"type": "title_changed", "title": pane.current_title})
        await send_json(ws, {"type": "loading", "loading": pane.loading})
        await send_json(ws, {"type": "viewport", "width": pane.viewport_width, "height": pane.viewport_height})

        async for raw in ws:
            if isinstance(raw, bytes):
                continue
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")
            if msg_type == "navigate":
                await _handle_navigate(pane, msg)
            elif msg_type == "mouse":
                await _handle_mouse(pane, msg)
            elif msg_type == "key":
                await _handle_key(pane, msg)
            elif msg_type == "insertText":
                await _handle_insert_text(pane, msg)
            elif msg_type == "back":
                if pane.page:
                    try:
                        await pane.page.go_back()
                    except Exception:
                        pass
            elif msg_type == "forward":
                if pane.page:
                    try:
                        await pane.page.go_forward()
                    except Exception:
                        pass
            elif msg_type == "reload":
                if pane.page:
                    try:
                        await pane.page.reload()
                    except Exception:
                        pass
            elif msg_type == "resize":
                await _handle_resize(pane, msg)
            elif msg_type == "ping":
                await send_json(ws, {"type": "pong"})

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as exc:
        log.error("pane %s: client handler error: %s", pane_id, exc)
    finally:
        pane.clients.discard(ws)
        remaining = len(pane.clients)
        log.info("pane %s: viewer disconnected (%d remaining)", pane_id, remaining)
        if remaining == 0:
            await _destroy_pane(pane_id)


# ── Browser lifecycle ────────────────────────────────────────

async def _launch_browser() -> None:
    global _pw, _browser, _context

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
        viewport={"width": DEFAULT_WIDTH, "height": DEFAULT_HEIGHT},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    )
    log.info("Chromium ready — awaiting pane connections")


# ── Main ─────────────────────────────────────────────────────

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
