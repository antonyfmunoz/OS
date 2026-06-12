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
_last_frame_at: float = 0.0
_frame_count: int = 0
_last_overlay_at: float = 0.0
_overlay_count: int = 0
_latest_detector_status: dict[str, Any] = {}
_mesh_dispatch_url = os.getenv(
    "MESH_DISPATCH_URL",
    "http://localhost:8095/dispatch",
)

# ── Diagnostic overlay state ─────────────────────────────────────

_diagnostic_overlay_active = False
_diagnostic_overlay_task: asyncio.Task | None = None

# ── Realtime PTZ motion loop state ────────────────────────────────

_motion_active = False
_motion_id: str = ""
_motion_pan_velocity: float = 0.0
_motion_tilt_velocity: float = 0.0
_motion_zoom_velocity: float = 0.0
_motion_speed: float = 1.0
_motion_last_update: float = 0.0
_motion_guard_ms: int = 500
_motion_task: asyncio.Task | None = None
_motion_loop_hz: float = 0.0
_motion_guard_timeouts: int = 0
_motion_coalesced: int = 0
_motion_dropped: int = 0

# ── Digital ROI state ────────────────────────────────────────────
_roi_x: float = 0.0
_roi_y: float = 0.0
_roi_zoom: float = 1.0
_ROI_MIN_ZOOM = 1.0
_ROI_MAX_ZOOM = 5.0


def _get_roi() -> dict[str, float]:
    return {"x": round(_roi_x, 4), "y": round(_roi_y, 4), "zoom": round(_roi_zoom, 2)}


def _apply_roi_delta(pan_delta: float, tilt_delta: float, zoom_delta: float) -> None:
    global _roi_x, _roi_y, _roi_zoom
    viewport = 1.0 / _roi_zoom
    _roi_x = max(0.0, min(1.0 - viewport, _roi_x + pan_delta * 0.02))
    _roi_y = max(0.0, min(1.0 - viewport, _roi_y + tilt_delta * 0.02))
    _roi_zoom = max(_ROI_MIN_ZOOM, min(_ROI_MAX_ZOOM, _roi_zoom + zoom_delta * 0.1))
    new_viewport = 1.0 / _roi_zoom
    _roi_x = max(0.0, min(1.0 - new_viewport, _roi_x))
    _roi_y = max(0.0, min(1.0 - new_viewport, _roi_y))


def _is_physical_ptz_available() -> bool:
    """True if Beast is on mesh — we can dispatch hardware PTZ commands."""
    return _latest_detector_status.get("loaded", False) or _last_frame_at > 0


async def _motion_loop() -> None:
    """PTZ motion loop — dispatches to Beast hardware or updates digital ROI."""
    global _motion_active, _motion_pan_velocity, _motion_tilt_velocity
    global _motion_zoom_velocity, _motion_loop_hz, _motion_guard_timeouts

    cadence_hz = 20
    interval = 1.0 / cadence_hz
    guard_timeout_s = _motion_guard_ms / 1000.0
    use_physical = _is_physical_ptz_available()

    log.info("motion loop started: motion_id=%s cadence=%dHz guard=%dms mode=%s",
             _motion_id, cadence_hz, _motion_guard_ms,
             "physical_ptz" if use_physical else "digital_roi")

    loop_count = 0
    loop_start = time.time()

    try:
        while _motion_active:
            t0 = time.monotonic()
            now = time.time()

            if now - _motion_last_update > guard_timeout_s:
                log.warning("motion guard timeout: no update for %.1fs, stopping motion_id=%s",
                            now - _motion_last_update, _motion_id)
                _motion_guard_timeouts += 1
                _motion_active = False
                if use_physical:
                    await _dispatch_motion_stop()
                await _broadcast_motion_state("idle")
                break

            pan_delta = 0
            tilt_delta = 0
            zoom_delta = 0

            if abs(_motion_pan_velocity) > 0.01 or abs(_motion_tilt_velocity) > 0.01:
                step_scale = _motion_speed * 8
                pan_delta = round(_motion_pan_velocity * step_scale)
                tilt_delta = round(_motion_tilt_velocity * step_scale)

            if abs(_motion_zoom_velocity) > 0.01:
                zoom_delta = round(_motion_zoom_velocity * _motion_speed * 10)

            if pan_delta != 0 or tilt_delta != 0 or zoom_delta != 0:
                if use_physical:
                    await _dispatch_to_beast("camera.set_position_relative", {
                        "pan_delta": pan_delta,
                        "tilt_delta": tilt_delta,
                        "zoom_delta": zoom_delta,
                    })
                else:
                    _apply_roi_delta(
                        float(pan_delta),
                        float(tilt_delta),
                        float(zoom_delta),
                    )

            loop_count += 1
            elapsed_total = time.time() - loop_start
            if elapsed_total > 0:
                _motion_loop_hz = round(loop_count / elapsed_total, 1)

            if loop_count % 20 == 0:
                await _broadcast_motion_state("moving")

            elapsed = time.monotonic() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            else:
                _motion_dropped += 1

    except asyncio.CancelledError:
        pass
    except Exception as exc:
        log.error("motion loop error: %s", exc)
    finally:
        _motion_active = False
        log.info("motion loop ended: motion_id=%s loops=%d avg_hz=%.1f",
                 _motion_id, loop_count, _motion_loop_hz)


async def _start_motion(
    motion_id: str,
    pan_velocity: float,
    tilt_velocity: float,
    zoom_velocity: float = 0.0,
    speed: float = 1.0,
    guard_ms: int = 2000,
) -> None:
    """Start or replace the active motion loop."""
    global _motion_active, _motion_id, _motion_pan_velocity, _motion_tilt_velocity
    global _motion_zoom_velocity, _motion_speed, _motion_last_update, _motion_guard_ms
    global _motion_task

    if _motion_active and _motion_task and not _motion_task.done():
        _motion_active = False
        _motion_task.cancel()
        try:
            await _motion_task
        except (asyncio.CancelledError, Exception):
            pass

    _motion_id = motion_id
    _motion_pan_velocity = pan_velocity
    _motion_tilt_velocity = tilt_velocity
    _motion_zoom_velocity = zoom_velocity
    _motion_speed = max(0.1, min(speed, 5.0))
    _motion_guard_ms = max(500, min(guard_ms, 5000))
    _motion_last_update = time.time()
    _motion_active = True

    _motion_task = asyncio.create_task(_motion_loop())
    await _broadcast_motion_state("moving")


async def _update_motion(
    motion_id: str,
    pan_velocity: float,
    tilt_velocity: float,
    zoom_velocity: float = 0.0,
    speed: float = 1.0,
) -> None:
    """Update the active motion velocity vector."""
    global _motion_pan_velocity, _motion_tilt_velocity, _motion_zoom_velocity
    global _motion_speed, _motion_last_update, _motion_coalesced

    if not _motion_active or _motion_id != motion_id:
        return

    _motion_pan_velocity = pan_velocity
    _motion_tilt_velocity = tilt_velocity
    _motion_zoom_velocity = zoom_velocity
    _motion_speed = max(0.1, min(speed, 5.0))
    _motion_last_update = time.time()
    _motion_coalesced += 1


async def _stop_motion(motion_id: str = "") -> None:
    """Stop the active motion loop."""
    global _motion_active, _motion_task

    if not _motion_active:
        return

    if motion_id and _motion_id != motion_id:
        return

    _motion_active = False
    if _motion_task and not _motion_task.done():
        _motion_task.cancel()
        try:
            await _motion_task
        except (asyncio.CancelledError, Exception):
            pass

    await _dispatch_motion_stop()
    await _broadcast_motion_state("idle")


async def _dispatch_motion_stop() -> None:
    """Send immediate stop to Beast hardware — zero-delta command."""
    await _dispatch_to_beast("camera.set_position_relative", {
        "pan_delta": 0, "tilt_delta": 0, "zoom_delta": 0,
    })


async def _broadcast_motion_state(state: str) -> None:
    """Broadcast PTZ motion state to all connected cockpit viewers."""
    msg = {
        "type": "ptz_motion_state",
        "motion_id": _motion_id,
        "state": state,
        "pan_velocity": _motion_pan_velocity,
        "tilt_velocity": _motion_tilt_velocity,
        "zoom_velocity": _motion_zoom_velocity,
        "loop_cadence_hz": _motion_loop_hz,
        "guard_timeout_events": _motion_guard_timeouts,
        "coalesced_commands": _motion_coalesced,
        "ptz_mode": "physical_ptz" if _is_physical_ptz_available() else "digital_roi",
        "roi": _get_roi(),
    }
    for ws in list(_clients):
        await send_json(ws, msg)


async def _broadcast_session_state() -> None:
    """Broadcast camera session state to all viewers."""
    msg = {
        "type": "camera_session_state",
        "active": _stream_active,
        "viewer_count": len(_clients),
    }
    for ws in list(_clients):
        await send_json(ws, msg)


async def _broadcast_motion_ack(motion_id: str, operation: str, ok: bool) -> None:
    """Send motion ack to all connected viewers."""
    msg = {
        "type": "ptz_motion_ack",
        "motion_id": motion_id,
        "operation": operation,
        "ok": ok,
    }
    for ws in list(_clients):
        await send_json(ws, msg)


_smooth_preset_task: asyncio.Task | None = None


async def _smooth_preset_transition(preset: str, duration_s: float = 1.0) -> None:
    """Smoothly interpolate from current PTZ position to a preset target.

    Uses the Beast hardware's set_position at 20Hz with linear interpolation.
    Falls back to instant jump if current position can't be read.
    """
    global _smooth_preset_task

    if _smooth_preset_task and not _smooth_preset_task.done():
        _smooth_preset_task.cancel()
        try:
            await _smooth_preset_task
        except (asyncio.CancelledError, Exception):
            pass

    await _stop_motion()

    current = await _dispatch_to_beast("camera.get_position", {})
    if not current or not current.get("success"):
        await _dispatch_to_beast("camera.set_preset", {"preset": preset})
        return

    target = await _dispatch_to_beast("camera.list_presets", {})
    if not target or not target.get("success"):
        await _dispatch_to_beast("camera.set_preset", {"preset": preset})
        return

    presets = target.get("presets", {})
    if preset not in presets:
        await _dispatch_to_beast("camera.set_preset", {"preset": preset})
        return

    p = presets[preset]
    target_pan = p.get("pan", 0)
    target_tilt = p.get("tilt", 0)
    target_zoom = p.get("zoom", 100)
    start_pan = current.get("pan", 0)
    start_tilt = current.get("tilt", 0)
    start_zoom = current.get("zoom", 100)

    delta_pan = abs(target_pan - start_pan)
    delta_tilt = abs(target_tilt - start_tilt)
    delta_zoom = abs(target_zoom - start_zoom)
    if delta_pan < 2 and delta_tilt < 2 and delta_zoom < 5:
        await _dispatch_to_beast("camera.set_preset", {"preset": preset})
        return

    async def _interpolate():
        cadence = 20
        interval = 1.0 / cadence
        total_steps = max(1, int(duration_s * cadence))
        for step in range(1, total_steps + 1):
            t = step / total_steps
            t_smooth = t * t * (3 - 2 * t)
            pan = int(start_pan + (target_pan - start_pan) * t_smooth)
            tilt = int(start_tilt + (target_tilt - start_tilt) * t_smooth)
            zoom = int(start_zoom + (target_zoom - start_zoom) * t_smooth)
            await _dispatch_to_beast("camera.set_position", {
                "pan": pan, "tilt": tilt, "zoom": zoom,
            })
            await asyncio.sleep(interval)
        await _dispatch_to_beast("camera.set_position", {
            "pan": target_pan, "tilt": target_tilt, "zoom": target_zoom,
        })
        await _broadcast_motion_state("idle")

    await _broadcast_motion_state("moving")
    _smooth_preset_task = asyncio.create_task(_interpolate())


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
        await _broadcast_session_state()

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
                continue

            elif msg_type == "vision_subscribe":
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
                smooth = msg.get("smooth", False)
                if smooth:
                    duration = max(0.3, min(float(msg.get("duration", 1.0)), 3.0))
                    await _smooth_preset_transition(preset, duration)
                else:
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

            elif msg_type == "camera_delete_preset":
                preset = msg.get("preset", "")
                result = await _dispatch_to_beast("camera.delete_preset", {
                    "preset": preset,
                })
                if result and result.get("success"):
                    await send_json(ws, {"type": "preset_deleted", "preset": preset})
                else:
                    await send_json(ws, {
                        "type": "vision_error",
                        "error": result.get("error", "delete failed") if result else "dispatch failed",
                    })

            elif msg_type == "vision_correct_label":
                track_id = msg.get("track_id", "")
                corrected = msg.get("corrected_label", "")
                raw = msg.get("raw_label", "")
                result = await _dispatch_to_beast("camera.correct_label", {
                    "track_id": track_id,
                    "corrected_label": corrected,
                    "raw_label": raw,
                })
                if result and result.get("success"):
                    await send_json(ws, {
                        "type": "label_corrected",
                        "track_id": track_id,
                        "corrected_label": corrected,
                        "raw_label": raw,
                    })
                else:
                    await send_json(ws, {
                        "type": "vision_error",
                        "error": result.get("error", "label correction failed") if result else "dispatch failed",
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
                await _stop_motion()
                await _send_control_result(ws, request_id, "camera.ptz.stop", {"success": True})

            # ── Realtime PTZ motion protocol ──────────────────

            elif msg_type == "camera_ptz_start_motion":
                motion_id = msg.get("motion_id", "")
                await _start_motion(
                    motion_id=motion_id,
                    pan_velocity=float(msg.get("pan_velocity", 0)),
                    tilt_velocity=float(msg.get("tilt_velocity", 0)),
                    zoom_velocity=float(msg.get("zoom_velocity", 0)),
                    speed=float(msg.get("speed", 1)),
                    guard_ms=int(msg.get("duration_guard_ms", 500)),
                )
                await _broadcast_motion_ack(motion_id, "start_motion", True)

            elif msg_type == "camera_ptz_update_motion":
                motion_id = msg.get("motion_id", "")
                await _update_motion(
                    motion_id=motion_id,
                    pan_velocity=float(msg.get("pan_velocity", 0)),
                    tilt_velocity=float(msg.get("tilt_velocity", 0)),
                    zoom_velocity=float(msg.get("zoom_velocity", 0)),
                    speed=float(msg.get("speed", 1)),
                )

            elif msg_type == "camera_ptz_stop_motion":
                motion_id = msg.get("motion_id", "")
                await _stop_motion(motion_id)
                await _broadcast_motion_ack(motion_id, "stop_motion", True)

            elif msg_type == "camera_zoom_start":
                motion_id = msg.get("motion_id", "")
                await _start_motion(
                    motion_id=motion_id,
                    pan_velocity=0,
                    tilt_velocity=0,
                    zoom_velocity=float(msg.get("zoom_velocity", 0)),
                    speed=float(msg.get("speed", 1)),
                    guard_ms=int(msg.get("duration_guard_ms", 500)),
                )
                await _broadcast_motion_ack(motion_id, "zoom_start", True)

            elif msg_type == "camera_zoom_update":
                motion_id = msg.get("motion_id", "")
                await _update_motion(
                    motion_id=motion_id,
                    pan_velocity=0,
                    tilt_velocity=0,
                    zoom_velocity=float(msg.get("zoom_velocity", 0)),
                    speed=float(msg.get("speed", 1)),
                )

            elif msg_type == "camera_zoom_stop":
                motion_id = msg.get("motion_id", "")
                await _stop_motion(motion_id)
                await _broadcast_motion_ack(motion_id, "zoom_stop", True)

            elif msg_type == "vision_scene_state":
                state = _get_scene_state()
                await send_json(ws, {"type": "vision_scene_state", **state})

            elif msg_type == "vision_scene_describe":
                result = await _dispatch_to_beast("camera.scene_describe", {})
                if result and result.get("success"):
                    await send_json(ws, {"type": "vision_scene_describe_result", "description": result["description"], "success": True})
                else:
                    state = _get_scene_state()
                    summary = state.get("scene", {}).get("summary", "") if isinstance(state.get("scene"), dict) else ""
                    await send_json(ws, {"type": "vision_scene_describe_result", "description": summary or "Scene data unavailable.", "success": bool(summary)})

            elif msg_type == "vision_active_tracks":
                result = await _dispatch_to_beast("camera.active_tracks", {})
                if result and result.get("success"):
                    await send_json(ws, {"type": "vision_active_tracks_result", "tracks": result["tracks"], "success": True})
                else:
                    await send_json(ws, {"type": "vision_active_tracks_result", "tracks": [], "success": False})

            elif msg_type == "vision_track_query":
                label = msg.get("label", "")
                result = await _dispatch_to_beast("camera.track_query", {"label": label})
                if result and result.get("success"):
                    await send_json(ws, {"type": "vision_track_query_result", "track": result["track"], "success": True, "label": label})
                else:
                    await send_json(ws, {"type": "vision_track_query_result", "track": None, "success": False, "label": label, "error": result.get("error", "not found") if result else "dispatch failed"})

            elif msg_type == "vision_look_at":
                label = msg.get("label", "")
                track_result = await _dispatch_to_beast("camera.track_query", {"label": label})
                if track_result and track_result.get("success"):
                    track = track_result["track"]
                    cx, cy = track.get("center", [0.5, 0.5])
                    pan_delta = int((cx - 0.5) * 40)
                    tilt_delta = int((0.5 - cy) * 40)
                    ptz_result = await _dispatch_to_beast("camera.set_position_relative", {
                        "pan_delta": pan_delta,
                        "tilt_delta": tilt_delta,
                        "zoom_delta": 0,
                    })
                    await send_json(ws, {
                        "type": "vision_look_at_result",
                        "success": bool(ptz_result and ptz_result.get("success")),
                        "label": label,
                        "track_id": track.get("track_id"),
                        "ptz_result": ptz_result,
                    })
                else:
                    await send_json(ws, {
                        "type": "vision_look_at_result",
                        "success": False,
                        "label": label,
                        "error": f"no active track for '{label}'",
                    })

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

            # ── Tracker stack ──────────────────────────────────────
            elif msg_type == "vision_tracker_enable":
                category = msg.get("category", "")
                result = _tracker_enable(category)
                await send_json(ws, {"type": "vision_tracker_result", **result})

            elif msg_type == "vision_tracker_disable":
                category = msg.get("category", "")
                result = _tracker_disable(category)
                await send_json(ws, {"type": "vision_tracker_result", **result})

            elif msg_type == "vision_tracker_stack":
                categories = msg.get("categories", [])
                result = _tracker_stack_set(categories)
                await send_json(ws, {"type": "vision_tracker_result", **result})

            elif msg_type == "vision_tracker_state":
                result = _tracker_state()
                await send_json(ws, {"type": "vision_tracker_state", **result})

            elif msg_type == "vision_stop_all_tracking":
                result = _stop_all_tracking()
                await send_json(ws, {"type": "vision_tracker_result", **result})

            # ── Preset CRUD ────────────────────────────────────────
            elif msg_type == "vision_preset_create":
                result = _preset_create(
                    msg.get("preset_id", ""),
                    msg.get("label", ""),
                    msg.get("description", ""),
                    msg.get("ptz"),
                )
                await send_json(ws, {"type": "vision_preset_result", **result})

            elif msg_type == "vision_preset_rename":
                result = _preset_rename(msg.get("preset_id", ""), msg.get("new_label", ""))
                await send_json(ws, {"type": "vision_preset_result", **result})

            elif msg_type == "vision_preset_delete":
                result = _preset_delete(msg.get("preset_id", ""))
                await send_json(ws, {"type": "vision_preset_result", **result})

            elif msg_type == "vision_preset_activate":
                result = _preset_activate(msg.get("preset_id", ""))
                await send_json(ws, {"type": "vision_preset_result", **result})

            elif msg_type == "vision_preset_update_ptz":
                result = _preset_update_ptz(msg.get("preset_id", ""), msg.get("ptz", {}))
                await send_json(ws, {"type": "vision_preset_result", **result})

            elif msg_type == "vision_preset_nudge":
                result = _preset_nudge(
                    msg.get("preset_id", ""),
                    msg.get("pan_delta", 0),
                    msg.get("tilt_delta", 0),
                    msg.get("zoom_delta", 0),
                )
                await send_json(ws, {"type": "vision_preset_result", **result})

            elif msg_type == "vision_preset_state":
                result = _preset_state()
                await send_json(ws, {"type": "vision_preset_state", **result})

            # ── Trigger chains ─────────────────────────────────────
            elif msg_type == "vision_chain_create":
                result = _chain_create(msg)
                await send_json(ws, {"type": "vision_chain_result", **result})

            elif msg_type == "vision_chain_delete":
                result = _chain_delete(msg.get("chain_id", ""))
                await send_json(ws, {"type": "vision_chain_result", **result})

            elif msg_type == "vision_chain_enable":
                result = _chain_enable(msg.get("chain_id", ""))
                await send_json(ws, {"type": "vision_chain_result", **result})

            elif msg_type == "vision_chain_disable":
                result = _chain_disable(msg.get("chain_id", ""))
                await send_json(ws, {"type": "vision_chain_result", **result})

            elif msg_type == "vision_chain_explain":
                result = _chain_explain(msg.get("chain_id", ""))
                await send_json(ws, {"type": "vision_chain_explain", **result})

            elif msg_type == "vision_chain_state":
                result = _chain_state()
                await send_json(ws, {"type": "vision_chain_state", **result})

            # ── Security mode ──────────────────────────────────────
            elif msg_type == "vision_security_activate":
                result = _security_activate(msg.get("triggered_by", "operator_command"))
                await send_json(ws, {"type": "vision_security_result", **result})

            elif msg_type == "vision_security_deactivate":
                result = _security_deactivate()
                await send_json(ws, {"type": "vision_security_result", **result})

            elif msg_type == "vision_security_state":
                result = _security_state()
                await send_json(ws, {"type": "vision_security_state", **result})

            elif msg_type == "vision_diagnostic_overlay":
                enabled = bool(msg.get("enabled", False))
                await _toggle_diagnostic_overlay(enabled)

            elif msg_type == "vision_health":
                health = _build_health()
                await send_json(ws, {"type": "vision_health", **health})

    except websockets.exceptions.ConnectionClosed:
        log.info("viewer disconnected: %s", ws.remote_address)
    except Exception as e:
        log.error("viewer session error: %s", e)
    finally:
        _clients.discard(ws)
        if len(_clients) == 0 and _motion_active:
            log.warning("last viewer disconnected while motion active, stopping motion")
            await _stop_motion()
        await _broadcast_session_state()


def _build_diagnostic_overlays() -> list[dict[str, Any]]:
    """Generate synthetic overlay data for render chain calibration."""
    t = time.time()
    phase = (t % 4.0) / 4.0  # 0..1 over 4 seconds
    return [
        {
            "type": "object",
            "track_id": "diag_center",
            "label": "DIAG: center",
            "confidence": 0.99,
            "bbox": {"x": 0.35, "y": 0.3, "w": 0.3, "h": 0.4},
            "color": "#facc15",
        },
        {
            "type": "object",
            "track_id": "diag_tl",
            "label": "DIAG: top-left",
            "confidence": 0.80,
            "bbox": {"x": 0.02, "y": 0.02, "w": 0.12, "h": 0.1},
            "color": "#f97316",
        },
        {
            "type": "object",
            "track_id": "diag_br",
            "label": "DIAG: bottom-right",
            "confidence": 0.80,
            "bbox": {"x": 0.86, "y": 0.88, "w": 0.12, "h": 0.1},
            "color": "#f97316",
        },
        {
            "type": "object",
            "track_id": "diag_moving",
            "label": f"DIAG: sweep ({phase:.0%})",
            "confidence": 0.95,
            "bbox": {"x": 0.05 + phase * 0.7, "y": 0.45, "w": 0.1, "h": 0.1},
            "color": "#22d3ee",
        },
    ]


async def _diagnostic_overlay_loop() -> None:
    """Broadcast synthetic overlays at 4Hz while diagnostic mode is active."""
    global _diagnostic_overlay_active
    log.info("diagnostic overlay loop started")
    try:
        while _diagnostic_overlay_active:
            overlays = _build_diagnostic_overlays()
            payload = json.dumps({"type": "vision_overlay", "overlays": overlays})
            dead: set[Any] = set()
            for ws in _clients:
                try:
                    await ws.send(payload)
                except Exception:
                    dead.add(ws)
            _clients.difference_update(dead)
            await asyncio.sleep(0.25)
    except asyncio.CancelledError:
        pass
    finally:
        log.info("diagnostic overlay loop stopped")


async def _toggle_diagnostic_overlay(enabled: bool) -> None:
    """Start or stop the diagnostic overlay broadcast loop."""
    global _diagnostic_overlay_active, _diagnostic_overlay_task
    if enabled and not _diagnostic_overlay_active:
        _diagnostic_overlay_active = True
        _diagnostic_overlay_task = asyncio.ensure_future(_diagnostic_overlay_loop())
        log.info("diagnostic overlay enabled")
    elif not enabled and _diagnostic_overlay_active:
        _diagnostic_overlay_active = False
        if _diagnostic_overlay_task and not _diagnostic_overlay_task.done():
            _diagnostic_overlay_task.cancel()
            try:
                await _diagnostic_overlay_task
            except asyncio.CancelledError:
                pass
        _diagnostic_overlay_task = None
        # Send empty overlays to clear the display
        payload = json.dumps({"type": "vision_overlay", "overlays": []})
        for ws in list(_clients):
            try:
                await ws.send(payload)
            except Exception:
                pass
        log.info("diagnostic overlay disabled")


async def _start_stream(
    fps: int = 2, width: int = 640, height: int = 480, quality: int = 60,
) -> None:
    global _stream_active, _stream_fps, _stream_width, _stream_height, _stream_quality
    _stream_fps = min(fps, 30)
    _stream_width = width
    _stream_height = height
    _stream_quality = quality
    frame_age = (time.time() - _last_frame_at) if _last_frame_at else float("inf")
    stale = frame_age > 15.0
    if _stream_active and not stale:
        log.info("stream already active, updating params")
        return
    if _stream_active and stale:
        log.info("stream marked active but frames stale (%.1fs) — re-dispatching to Beast", frame_age)
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
        _stream_active = False
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
    """Called by mesh frame callback — fan out to all subscribed viewers.

    Sends to all clients concurrently via gather to prevent one slow
    client from blocking the others (the original sequential await
    caused visible stutter at higher FPS).
    """
    global _latest_frame, _latest_frame_meta, _stream_active
    global _last_frame_at, _frame_count, _last_overlay_at, _overlay_count
    global _latest_detector_status

    if len(jpeg_bytes) > MAX_FRAME_BYTES:
        log.warning("frame too large: %d bytes, dropping", len(jpeg_bytes))
        return

    _latest_frame = jpeg_bytes
    _latest_frame_meta = meta
    _stream_active = True
    _last_frame_at = time.time()
    _frame_count += 1

    det_status = meta.get("detector_status")
    if det_status:
        _latest_detector_status = det_status

    overlays = meta.get("overlays")
    if overlays:
        _last_overlay_at = time.time()
        _overlay_count += 1

    if not _clients:
        return

    overlay_msg: dict[str, Any] | None = None
    if overlays:
        overlay_msg = {"type": "vision_overlay", "overlays": overlays}
        if det_status:
            overlay_msg["detector_status"] = det_status
    overlay_json = json.dumps(overlay_msg) if overlay_msg else None

    async def _send_to(ws: Any) -> bool:
        try:
            await ws.send(jpeg_bytes)
            if overlay_json:
                await ws.send(overlay_json)
            return True
        except Exception:
            return False

    clients = list(_clients)
    results = await asyncio.gather(*(_send_to(ws) for ws in clients), return_exceptions=True)

    dead = {clients[i] for i, ok in enumerate(results) if ok is not True}
    if dead:
        log.info("cleaned %d stale viewer(s), %d remaining", len(dead), len(_clients) - len(dead))
        _clients.difference_update(dead)


_JPEG_SOI = b'\xff\xd8'

def receive_mesh_frame(frame_data: dict[str, Any]) -> None:
    """Sync entry point for node mesh callback — decodes base64 and broadcasts."""
    if not isinstance(frame_data, dict):
        log.warning("malformed frame data: expected dict, got %s", type(frame_data).__name__)
        return
    b64 = frame_data.get("image_base64", "")
    if not b64:
        return
    try:
        jpeg_bytes = base64.b64decode(b64)
    except Exception as exc:
        log.warning("invalid base64 frame: %s", exc)
        return

    if len(jpeg_bytes) < 2 or jpeg_bytes[:2] != _JPEG_SOI:
        log.warning("frame rejected: not a valid JPEG (header=%s, size=%d)", jpeg_bytes[:2].hex() if jpeg_bytes else "empty", len(jpeg_bytes))
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


# ── Tracker stack handlers ────────────────────────────────────────

def _get_tracker_manager():
    try:
        from substrate.workstation.tracker_stack import get_tracker_manager
        mgr = get_tracker_manager()
        if not mgr.active_stack:
            mgr.create_stack("default", "Default Stack")
            mgr.activate_stack("default")
        return mgr
    except Exception as exc:
        log.warning("tracker manager unavailable: %s", exc)
        return None


def _tracker_enable(category: str) -> dict:
    mgr = _get_tracker_manager()
    if not mgr:
        return {"success": False, "error": "tracker manager unavailable"}
    ok = mgr.enable_tracker(category)
    return {"success": ok, "category": category, "operation": "enable"}


def _tracker_disable(category: str) -> dict:
    mgr = _get_tracker_manager()
    if not mgr:
        return {"success": False, "error": "tracker manager unavailable"}
    ok = mgr.disable_tracker(category)
    return {"success": ok, "category": category, "operation": "disable"}


def _tracker_stack_set(categories: list[str]) -> dict:
    mgr = _get_tracker_manager()
    if not mgr:
        return {"success": False, "error": "tracker manager unavailable"}
    stack = mgr.active_stack
    if not stack:
        return {"success": False, "error": "no active stack"}
    for cat in stack.trackers:
        if cat in categories:
            mgr.enable_tracker(cat)
        else:
            mgr.disable_tracker(cat)
    enabled = [t.category for t in mgr.get_enabled_trackers()]
    return {"success": True, "enabled": enabled}


def _stop_all_tracking() -> dict:
    mgr = _get_tracker_manager()
    if not mgr:
        return {"success": False, "error": "tracker manager unavailable"}
    stack = mgr.active_stack
    if stack:
        for cat in stack.trackers:
            mgr.disable_tracker(cat)
    return {"success": True, "operation": "stop_all"}


def _tracker_state() -> dict:
    mgr = _get_tracker_manager()
    if not mgr:
        return {"error": "tracker manager unavailable"}
    return mgr.get_state_summary()


# ── Preset CRUD handlers ─────────────────────────────────────────

def _get_preset_manager():
    try:
        from substrate.workstation.vision_presets import get_preset_manager
        return get_preset_manager()
    except Exception as exc:
        log.warning("preset manager unavailable: %s", exc)
        return None


def _preset_create(preset_id: str, label: str, description: str = "", ptz: dict | None = None) -> dict:
    mgr = _get_preset_manager()
    if not mgr:
        return {"success": False, "error": "preset manager unavailable"}
    p = mgr.create(preset_id, label or preset_id, description, ptz)
    if p:
        return {"success": True, "preset_id": p.preset_id, "label": p.label}
    return {"success": False, "error": "could not create preset"}


def _preset_rename(preset_id: str, new_label: str) -> dict:
    mgr = _get_preset_manager()
    if not mgr:
        return {"success": False, "error": "preset manager unavailable"}
    ok = mgr.rename(preset_id, new_label)
    return {"success": ok, "preset_id": preset_id, "new_label": new_label}


def _preset_delete(preset_id: str) -> dict:
    mgr = _get_preset_manager()
    if not mgr:
        return {"success": False, "error": "preset manager unavailable"}
    ok, affected = mgr.delete(preset_id)
    return {"success": ok, "preset_id": preset_id, "affected_chains": affected}


def _preset_activate(preset_id: str) -> dict:
    mgr = _get_preset_manager()
    if not mgr:
        return {"success": False, "error": "preset manager unavailable"}
    ok = mgr.activate(preset_id)
    return {"success": ok, "preset_id": preset_id}


def _preset_update_ptz(preset_id: str, ptz: dict) -> dict:
    mgr = _get_preset_manager()
    if not mgr:
        return {"success": False, "error": "preset manager unavailable"}
    ok = mgr.update_ptz(preset_id, ptz)
    return {"success": ok, "preset_id": preset_id}


def _preset_nudge(preset_id: str, pan_delta: int, tilt_delta: int, zoom_delta: int) -> dict:
    mgr = _get_preset_manager()
    if not mgr:
        return {"success": False, "error": "preset manager unavailable"}
    ok = mgr.nudge_ptz(preset_id, pan_delta, tilt_delta, zoom_delta)
    return {"success": ok, "preset_id": preset_id}


def _preset_state() -> dict:
    mgr = _get_preset_manager()
    if not mgr:
        return {"error": "preset manager unavailable"}
    return mgr.get_state_summary()


# ── Trigger chain handlers ────────────────────────────────────────

def _get_chain_manager():
    try:
        from substrate.workstation.trigger_chains import get_chain_manager
        return get_chain_manager()
    except Exception as exc:
        log.warning("chain manager unavailable: %s", exc)
        return None


def _chain_create(msg: dict) -> dict:
    mgr = _get_chain_manager()
    if not mgr:
        return {"success": False, "error": "chain manager unavailable"}
    chain = mgr.create_chain(
        label=msg.get("label", ""),
        trigger_event=msg.get("trigger_event", ""),
        actions=msg.get("actions", []),
        conditions=msg.get("conditions"),
        trigger_zone=msg.get("trigger_zone", ""),
        confidence_min=msg.get("confidence_min", 0.5),
        debounce_seconds=msg.get("debounce_seconds", 3.0),
        governance=msg.get("governance"),
    )
    if chain:
        return {"success": True, "chain_id": chain.chain_id, "label": chain.label}
    return {"success": False, "error": "could not create chain"}


def _chain_delete(chain_id: str) -> dict:
    mgr = _get_chain_manager()
    if not mgr:
        return {"success": False, "error": "chain manager unavailable"}
    ok = mgr.delete_chain(chain_id)
    return {"success": ok, "chain_id": chain_id}


def _chain_enable(chain_id: str) -> dict:
    mgr = _get_chain_manager()
    if not mgr:
        return {"success": False, "error": "chain manager unavailable"}
    ok = mgr.enable_chain(chain_id)
    return {"success": ok, "chain_id": chain_id}


def _chain_disable(chain_id: str) -> dict:
    mgr = _get_chain_manager()
    if not mgr:
        return {"success": False, "error": "chain manager unavailable"}
    if chain_id:
        ok = mgr.disable_chain(chain_id)
        return {"success": ok, "chain_id": chain_id}
    for chain in mgr.list_chains():
        if chain.enabled:
            mgr.disable_chain(chain.chain_id)
    return {"success": True, "operation": "disable_all"}


def _chain_explain(chain_id: str = "") -> dict:
    mgr = _get_chain_manager()
    if not mgr:
        return {"explanation": "Chain manager unavailable."}
    explanation = mgr.explain_last_fire(chain_id)
    return {"explanation": explanation}


def _chain_state() -> dict:
    mgr = _get_chain_manager()
    if not mgr:
        return {"error": "chain manager unavailable"}
    return mgr.get_state_summary()


# ── Security mode handlers ────────────────────────────────────────

def _get_security_manager():
    try:
        from substrate.workstation.security_mode import get_security_manager
        return get_security_manager()
    except Exception as exc:
        log.warning("security manager unavailable: %s", exc)
        return None


def _security_activate(triggered_by: str = "operator_command") -> dict:
    mgr = _get_security_manager()
    if not mgr:
        return {"success": False, "error": "security manager unavailable"}
    state = mgr.activate(triggered_by=triggered_by)
    return {"success": True, "mode": "security_harden", **state.to_dict()}


def _security_deactivate() -> dict:
    mgr = _get_security_manager()
    if not mgr:
        return {"success": False, "error": "security manager unavailable"}
    result = mgr.deactivate(resolved_by="operator")
    return result


def _security_state() -> dict:
    mgr = _get_security_manager()
    if not mgr:
        return {"error": "security manager unavailable"}
    return mgr.get_state_summary()


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


def _dispatch_to_beast_sync(operation: str, params: dict[str, Any]) -> dict[str, Any] | None:
    """Blocking mesh dispatch — runs in thread pool via _dispatch_to_beast."""
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


async def _dispatch_to_beast(operation: str, params: dict[str, Any]) -> dict[str, Any] | None:
    """Non-blocking mesh dispatch — offloads to thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _dispatch_to_beast_sync, operation, params)


def _build_health() -> dict[str, Any]:
    """Build comprehensive vision chain health report."""
    now = time.time()
    frame_age_ms = int((now - _last_frame_at) * 1000) if _last_frame_at else -1
    overlay_age_ms = int((now - _last_overlay_at) * 1000) if _last_overlay_at else -1

    stale_frame_threshold_ms = 15000
    stale_overlay_threshold_ms = 30000

    frame_stale = frame_age_ms > stale_frame_threshold_ms if _last_frame_at else True

    # Beast connectivity: check mesh
    beast_connected = False
    try:
        import urllib.request
        req = urllib.request.Request(
            _mesh_dispatch_url.replace("/dispatch", "/health"),
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            mesh_data = json.loads(resp.read())
            node_ids = mesh_data.get("node_ids", [])
            if not node_ids:
                node_ids = [
                    n.get("node_id", "") if isinstance(n, dict) else str(n)
                    for n in mesh_data.get("nodes", [])
                ]
            beast_connected = any(
                nid.startswith("windows") or nid == "beast_windows"
                for nid in node_ids
            )
    except Exception:
        pass

    # Tracker state
    tracker_mgr = None
    try:
        tracker_mgr = _get_tracker_manager()
    except Exception:
        pass
    tracker_available = tracker_mgr is not None
    active_trackers = []
    if tracker_mgr:
        active_trackers = [t.category for t in tracker_mgr.get_enabled_trackers()]

    # Chain state
    chain_mgr = None
    try:
        chain_mgr = _get_chain_manager()
    except Exception:
        pass
    chain_available = chain_mgr is not None
    active_chains = []
    if chain_mgr:
        active_chains = [c.label for c in chain_mgr.list_chains() if c.enabled]

    # Security state
    sec_mgr = None
    try:
        sec_mgr = _get_security_manager()
    except Exception:
        pass
    security_active = sec_mgr.is_active if sec_mgr else False

    # Camera status from last frame metadata
    camera_available = _latest_frame is not None
    camera_streaming = _stream_active and not frame_stale

    # Derive overall status
    blockers: list[str] = []
    recovery_action = ""

    if not beast_connected:
        blockers.append("Beast daemon not connected to mesh")
        recovery_action = "check Beast daemon and network"
    elif not camera_available and not _stream_active:
        blockers.append("no frames received from Beast camera")
        recovery_action = "start camera stream or check camera hardware"
    elif frame_stale:
        blockers.append(f"last frame is {frame_age_ms}ms old (stale)")
        recovery_action = "restart camera stream on Beast"

    if len(_clients) == 0:
        blockers.append("no cockpit viewers connected")

    if _stream_active and not frame_stale and len(_clients) > 0:
        status = "healthy"
    elif _stream_active and frame_stale:
        status = "stream_stale"
    elif beast_connected and not _stream_active:
        status = "connected_no_frames"
    elif not beast_connected:
        status = "beast_offline"
    elif len(_clients) == 0:
        status = "relay_idle"
    else:
        status = "degraded"

    physical_ptz_available = beast_connected
    digital_roi_available = True
    ptz_mode = "physical_ptz" if physical_ptz_available else "digital_roi"
    command_path_ready = True

    return {
        "status": status,
        "relay_running": True,
        "cockpit_connected": len(_clients) > 0,
        "websocket_authenticated": True,
        "viewer_count": len(_clients),
        "motion_active": _motion_active,
        "motion_id": _motion_id if _motion_active else "",
        "motion_loop_hz": _motion_loop_hz,
        "motion_guard_timeouts": _motion_guard_timeouts,
        "motion_coalesced": _motion_coalesced,
        "beast_connected": beast_connected,
        "camera_available": camera_available,
        "camera_streaming": camera_streaming,
        "last_frame_at": _last_frame_at,
        "last_frame_age_ms": frame_age_ms,
        "frame_count": _frame_count,
        "frame_fps": _stream_fps if camera_streaming else 0,
        "tracker_runtime_available": tracker_available,
        "active_trackers": active_trackers,
        "last_overlay_at": _last_overlay_at,
        "last_overlay_age_ms": overlay_age_ms,
        "overlay_count": _overlay_count,
        "trigger_chain_engine_available": chain_available,
        "active_chains": active_chains,
        "security_mode": "security_harden" if security_active else "normal",
        "diagnostic_overlay_active": _diagnostic_overlay_active,
        "detector_status": _latest_detector_status,
        "ptz_mode": ptz_mode,
        "physical_ptz_available": physical_ptz_available,
        "digital_roi_available": digital_roi_available,
        "command_path_ready": command_path_ready,
        "roi": _get_roi(),
        "blockers": blockers,
        "recovery_action": recovery_action,
    }


async def _health_server() -> None:
    """HTTP server on PORT+1: health check + frame ingestion from mesh."""
    from http.server import BaseHTTPRequestHandler
    import socketserver

    health_port = PORT + 1

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/health":
                body = json.dumps(_build_health()).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/latest-frame":
                if _latest_frame is None:
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"error": "no frame available"}')
                    return
                body = json.dumps({
                    "image_base64": base64.b64encode(_latest_frame).decode(),
                    "mime_type": "image/jpeg",
                    "meta": _latest_frame_meta,
                    "timestamp": _latest_frame_meta.get("timestamp", ""),
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

    socketserver.TCPServer.allow_reuse_address = True
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
