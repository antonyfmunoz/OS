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

HOST = os.getenv("VISION_RELAY_HOST", "0.0.0.0")
PORT = int(os.getenv("VISION_RELAY_PORT", "8097"))
MAX_FRAME_BYTES = 2 * 1024 * 1024
_AUTH_TOKEN = os.getenv("VISION_RELAY_TOKEN", "")
_FRAME_INGEST_TOKEN = os.getenv("VISION_FRAME_TOKEN", "")
_ALLOWED_ORIGINS = {
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "https://universalmetaharness.tech",
}

def _check_origin(connection: Any, request: Any) -> None:
    """Reject cross-origin WebSocket connections (CSWSH defense).

    Allows: connections with no Origin header (server-to-server proxy),
    and connections from allowed origins. Rejects all others.
    """
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


_clients: set[Any] = set()
_latest_frame: bytes | None = None
_latest_frame_meta: dict[str, Any] = {}
_stream_active = False
_stream_task: asyncio.Task[None] | None = None
_stream_fps = 2
_stream_width = 640
_stream_height = 480
_stream_quality = 60
_mesh_dispatch_url = os.getenv(
    "MESH_DISPATCH_URL",
    "http://localhost:8095/dispatch",
)


async def send_json(ws: Any, data: dict[str, Any]) -> None:
    try:
        await ws.send(json.dumps(data))
    except Exception:
        pass


def _check_auth(ws: Any) -> bool:
    """Validate auth token via Sec-WebSocket-Protocol subprotocol header."""
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


def _direction_to_delta(direction: str, speed: int = 1) -> dict[str, int]:
    """Convert a PTZ direction string into pan/tilt deltas."""
    step = 5 * speed
    deltas: dict[str, dict[str, int]] = {
        "up":         {"tilt": step},
        "down":       {"tilt": -step},
        "left":       {"pan": -step},
        "right":      {"pan": step},
        "up_left":    {"pan": -step, "tilt": step},
        "up_right":   {"pan": step, "tilt": step},
        "down_left":  {"pan": -step, "tilt": -step},
        "down_right": {"pan": step, "tilt": -step},
    }
    d = deltas.get(direction, {})
    return {"pan": d.get("pan", 0), "tilt": d.get("tilt", 0)}


async def _send_control_result(
    ws: Any, request_id: str, operation: str, result: dict[str, Any] | None,
) -> None:
    """Send a structured control result back to the cockpit."""
    if result is None:
        await send_json(ws, {
            "type": "camera_control_result",
            "request_id": request_id,
            "operation": operation,
            "ok": False,
            "error": "dispatch failed",
        })
        return
    ok = result.get("success", False)
    payload: dict[str, Any] = {
        "type": "camera_control_result",
        "request_id": request_id,
        "operation": operation,
        "ok": ok,
    }
    if ok:
        for k in ("pan", "tilt", "zoom", "preset", "label"):
            if k in result:
                payload[k] = result[k]
    else:
        payload["error"] = result.get("error", "unknown error")
    await send_json(ws, payload)


async def handle_vision(ws: Any) -> None:
    if not _check_auth(ws):
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
                await _start_stream(
                    fps=msg.get("fps", 2),
                    width=msg.get("width", 640),
                    height=msg.get("height", 480),
                    quality=msg.get("quality", 60),
                )

            elif msg_type == "camera_stop":
                await _stop_stream()

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
                request_id = msg.get("request_id", "")
                result = await _dispatch_to_beast("camera.get_position", {})
                if result:
                    result["has_ptz_hardware"] = result.get("success", False)
                    await send_json(ws, {"type": "camera_position", **result})

            elif msg_type == "camera_status":
                result = await _dispatch_to_beast("camera.status", {})
                if result:
                    await send_json(ws, {"type": "vision_status", **result})

            elif msg_type == "camera_ptz_move":
                request_id = msg.get("request_id", "")
                delta = _direction_to_delta(msg.get("direction", ""), msg.get("speed", 1))
                pos_result = await _dispatch_to_beast("camera.get_position", {})
                if pos_result and pos_result.get("success"):
                    result = await _dispatch_to_beast("camera.set_position", {
                        "pan": pos_result["pan"] + delta.get("pan", 0),
                        "tilt": pos_result["tilt"] + delta.get("tilt", 0),
                        "zoom": pos_result.get("zoom", 100),
                    })
                else:
                    result = pos_result
                await _send_control_result(ws, request_id, "camera.ptz.move", result)

            elif msg_type == "camera_ptz_set_position":
                request_id = msg.get("request_id", "")
                result = await _dispatch_to_beast("camera.set_position", {
                    "pan": msg.get("pan", 0),
                    "tilt": msg.get("tilt", 0),
                    "zoom": msg.get("zoom", 100),
                })
                await _send_control_result(ws, request_id, "camera.ptz.set_position", result)

            elif msg_type == "camera_ptz_relative":
                request_id = msg.get("request_id", "")
                pos_result = await _dispatch_to_beast("camera.get_position", {})
                if pos_result and pos_result.get("success"):
                    new_pan = pos_result["pan"] + msg.get("pan_delta", 0)
                    new_tilt = pos_result["tilt"] + msg.get("tilt_delta", 0)
                    new_zoom = max(100, pos_result["zoom"] + msg.get("zoom_delta", 0))
                    result = await _dispatch_to_beast("camera.set_position", {
                        "pan": new_pan,
                        "tilt": new_tilt,
                        "zoom": new_zoom,
                    })
                else:
                    result = pos_result
                await _send_control_result(ws, request_id, "camera.ptz.relative", result)

            elif msg_type == "camera_ptz_stop":
                request_id = msg.get("request_id", "")
                await _send_control_result(ws, request_id, "camera.ptz.stop", {"success": True})

            elif msg_type == "vision_scene_state":
                state = _get_scene_state()
                await send_json(ws, {"type": "vision_scene_state", **state})

            elif msg_type == "vision_analyze":
                result = await _analyze_current_frame(msg.get("transcript", ""))
                await send_json(ws, {"type": "vision_analysis_result", **result})

            elif msg_type == "vision_track_start":
                label = msg.get("label", "")
                result = _track_start(label, msg.get("hint", ""))
                await send_json(ws, {"type": "vision_track_result", **result})

            elif msg_type == "vision_track_stop":
                label = msg.get("label", "")
                result = _track_stop(label)
                await send_json(ws, {"type": "vision_track_result", **result})

            elif msg_type == "vision_label_item":
                label = msg.get("label", "")
                result = _label_item(label, msg.get("frame_id", ""))
                await send_json(ws, {"type": "vision_label_result", **result})

            elif msg_type == "vision_watch_start":
                target = msg.get("target", "")
                condition = msg.get("condition", "moved")
                result = _watch_start(target, condition)
                await send_json(ws, {"type": "vision_watch_result", **result})

            elif msg_type == "vision_watch_stop":
                target = msg.get("target", "")
                result = _watch_stop(target)
                await send_json(ws, {"type": "vision_watch_result", **result})

            elif msg_type == "vision_follow_start":
                target = msg.get("target", "operator")
                result = _follow_start(target)
                await send_json(ws, {"type": "vision_follow_result", **result})

            elif msg_type == "vision_follow_stop":
                result = _follow_stop()
                await send_json(ws, {"type": "vision_follow_result", **result})

            elif msg_type == "vision_query":
                target = msg.get("target", "")
                result = _visual_query(target)
                await send_json(ws, {"type": "vision_query_result", **result})

    except websockets.exceptions.ConnectionClosed:
        log.info("viewer disconnected: %s", ws.remote_address)
    except Exception as e:
        log.error("viewer session error: %s", e)
    finally:
        _clients.discard(ws)


async def _start_stream(
    fps: int = 2, width: int = 640, height: int = 480, quality: int = 60,
) -> None:
    global _stream_active, _stream_fps, _stream_width, _stream_height, _stream_quality
    _stream_fps = min(fps, 30)
    _stream_width = width
    _stream_height = height
    _stream_quality = quality
    if _stream_active:
        log.info("stream already active, updating params")
        return
    _stream_active = True
    result = await _dispatch_to_beast("camera.stream_start", {
        "fps": _stream_fps,
        "width": _stream_width,
        "height": _stream_height,
        "quality": _stream_quality,
    })
    if result and result.get("success"):
        log.info("Beast stream started: %dx%d @%dfps q%d", width, height, _stream_fps, quality)
    else:
        log.warning("Beast stream_start failed: %s", result)
    for ws in list(_clients):
        await send_json(ws, {"type": "vision_status", "streaming": True, "fps": _stream_fps})


async def _stop_stream() -> None:
    global _stream_active
    _stream_active = False
    await _dispatch_to_beast("camera.stream_stop", {})
    log.info("stream stopped")
    for ws in list(_clients):
        await send_json(ws, {"type": "vision_status", "streaming": False})


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


_BEAST_NODE_ID = os.getenv("VISION_BEAST_NODE_ID", "windows-desktop")


# ── Scene manager integration ───────────────────────────────────────

def _get_scene_manager():
    """Lazy-import scene manager to avoid circular deps at module load."""
    try:
        from substrate.workstation.vision_scene import get_scene_manager
        return get_scene_manager()
    except Exception as exc:
        log.warning("scene manager unavailable: %s", exc)
        return None


def _get_scene_state() -> dict:
    mgr = _get_scene_manager()
    if not mgr:
        return {"error": "scene manager unavailable"}
    return mgr.get_state_summary()


def _track_start(label: str, hint: str = "") -> dict:
    mgr = _get_scene_manager()
    if not mgr:
        return {"success": False, "error": "scene manager unavailable"}
    obj = mgr.start_tracking(label, track_hint=hint)
    if obj:
        return {"success": True, "track_id": obj.track_id, "label": obj.label, "status": obj.status}
    return {"success": False, "error": f"could not start tracking '{label}'"}


def _track_stop(label: str) -> dict:
    mgr = _get_scene_manager()
    if not mgr:
        return {"success": False, "error": "scene manager unavailable"}
    stopped = mgr.stop_tracking(label)
    return {"success": stopped, "label": label}


def _label_item(label: str, frame_id: str = "") -> dict:
    mgr = _get_scene_manager()
    if not mgr:
        return {"success": False, "error": "scene manager unavailable"}
    obj = mgr.label_item(label, frame_id=frame_id)
    return {"success": True, "track_id": obj.track_id, "label": obj.label}


def _watch_start(target: str, condition: str = "moved") -> dict:
    mgr = _get_scene_manager()
    if not mgr:
        return {"success": False, "error": "scene manager unavailable"}
    watch = mgr.start_watch(target, condition=condition)
    if watch:
        return {"success": True, "watch_id": watch.watch_id, "target": target, "condition": condition}
    return {"success": False, "error": "max watches reached"}


def _watch_stop(target: str) -> dict:
    mgr = _get_scene_manager()
    if not mgr:
        return {"success": False, "error": "scene manager unavailable"}
    stopped = mgr.stop_watch(target)
    return {"success": stopped, "target": target}


def _follow_start(target: str = "operator") -> dict:
    mgr = _get_scene_manager()
    if not mgr:
        return {"success": False, "error": "scene manager unavailable"}
    follow = mgr.start_follow(target)
    return {"success": True, "target": target, "follow": follow.to_dict()}


def _follow_stop() -> dict:
    mgr = _get_scene_manager()
    if not mgr:
        return {"success": False, "error": "scene manager unavailable"}
    mgr.stop_follow()
    return {"success": True}


def _visual_query(target: str) -> dict:
    mgr = _get_scene_manager()
    if not mgr:
        return {"answer": "Scene manager unavailable.", "confidence": "none"}
    return mgr.query_visual(target)


async def _analyze_current_frame(transcript: str = "") -> dict:
    """Analyze the latest frame with VLM if available."""
    global _latest_frame
    if _latest_frame is None:
        return {"answer": "No frame available. Camera may be off.", "confidence": "none", "source": "no_frame"}

    import base64
    b64 = base64.b64encode(_latest_frame).decode()

    try:
        from substrate.workstation.camera_commands import analyze_snapshot
        analysis = analyze_snapshot(image_base64=b64, transcript=transcript)
    except Exception as exc:
        log.warning("VLM analysis failed: %s", exc)
        return {
            "answer": "Frame captured but analysis unavailable right now.",
            "confidence": "low",
            "source": "vlm_failed",
        }

    mgr = _get_scene_manager()
    if mgr:
        import time as _time
        from substrate.workstation.vision_query import _extract_objects_from_vlm
        detected = _extract_objects_from_vlm(analysis)
        mgr.update_scene_from_frame(
            frame_id=f"frame_{int(_time.time() * 1000)}",
            detected_objects=detected,
            summary=analysis,
            vlm_analyzed=True,
        )

    return {"answer": analysis, "confidence": "grounded", "source": "vlm_analysis"}


async def _dispatch_to_beast(operation: str, params: dict[str, Any]) -> dict[str, Any] | None:
    """Dispatch a camera command to Beast via the mesh HTTP relay."""
    try:
        import urllib.request

        payload = json.dumps({
            "node_id": _BEAST_NODE_ID,
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
            data = json.loads(resp.read())
            return data.get("result_data", data)
    except Exception as exc:
        log.warning("mesh dispatch failed (%s): %s", operation, exc)
        return None


async def _health_server() -> None:
    """HTTP server on PORT+1: health check + frame ingestion from mesh."""
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

        def do_POST(self) -> None:
            if self.path == "/frame":
                if _FRAME_INGEST_TOKEN:
                    import hmac
                    provided = self.headers.get("X-Frame-Token", "")
                    if not hmac.compare_digest(provided, _FRAME_INGEST_TOKEN):
                        self.send_response(403)
                        self.end_headers()
                        return
                length = int(self.headers.get("Content-Length", 0))
                if length == 0 or length > MAX_FRAME_BYTES * 2:
                    self.send_response(400)
                    self.end_headers()
                    return
                body = self.rfile.read(length)
                try:
                    data = json.loads(body)
                except Exception:
                    self.send_response(400)
                    self.end_headers()
                    return
                receive_mesh_frame(data)
                self.send_response(204)
                self.end_headers()
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

    if not _AUTH_TOKEN:
        log.warning(
            "VISION_RELAY_TOKEN is not set — authentication DISABLED. "
            "Set VISION_RELAY_TOKEN env var to enable auth."
        )

    log.info("Vision relay starting on ws://%s:%d/vision", HOST, PORT)
    asyncio.create_task(_health_server())

    async with websockets.serve(
        handle_vision, HOST, PORT,
        ping_interval=20, ping_timeout=20, max_size=MAX_FRAME_BYTES + 1024,
        process_request=_check_origin,
    ):
        log.info("Vision relay ready — frame fan-out mode")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
