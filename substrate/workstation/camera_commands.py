"""Camera command dispatcher — routes CAMERA_CONTROL intents to operations.

Deterministic sub-intent classification (no LLM). Dispatches operations
through the node mesh to the Beast camera adapter. Snapshot analysis
uses call_with_fallback with vision/image attachment.

Phase 14.14E extends this with PTZ movement, zoom, quality mode,
tracking, watch mode, follow mode, and visual query commands.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── Pattern definitions ──────────────────────────────────────────────

_PRESET_PATTERN = re.compile(
    r"\blook\s+at\s+(?:my\s+)?(keyboard|desk|me|the\s+desk|the\s+room|hands|the\s+monitor|my\s+hands|room)\b",
    re.IGNORECASE,
)
_SNAPSHOT_PATTERN = re.compile(
    r"\b(?:what\s+(?:do|can)\s+you\s+see|describe\s+what\s+you\s+see|"
    r"take\s+a\s+snapshot|analyze\s+this\s+frame|"
    r"am\s+i\s+at\s+my\s+desk|is\s+my\s+posture|"
    r"what\s+is\s+on\s+my\s+desk|what\s+changed)\b",
    re.IGNORECASE,
)
_SAVE_PRESET_PATTERN = re.compile(
    r"\bsave\s+(?:this\s+)?(?:camera\s+)?(?:position|preset)\s*(?:as\s+(.+))?\b",
    re.IGNORECASE,
)
_UPDATE_PRESET_PATTERN = re.compile(
    r"\bupdate\s+(?:the\s+)?(\w+)\s+preset\b",
    re.IGNORECASE,
)
_START_PATTERN = re.compile(
    r"\b(?:camera\s+on|turn\s+on\s+(?:the\s+)?camera|start\s+(?:the\s+)?camera|open\s+camera)\b",
    re.IGNORECASE,
)
_STOP_PATTERN = re.compile(
    r"\b(?:camera\s+off|turn\s+off\s+(?:the\s+)?camera|stop\s+(?:the\s+)?camera)\b",
    re.IGNORECASE,
)
_STATUS_PATTERN = re.compile(
    r"\b(?:camera\s+status|where\s+is\s+the\s+camera\s+looking|what\s+preset\s+am\s+i\s+on|show\s+my\s+camera\s+presets)\b",
    re.IGNORECASE,
)

# PTZ movement patterns
_PTZ_MOVE_PATTERN = re.compile(
    r"\b(?:move\s+(?:the\s+)?camera\s+(left|right|up|down)(?:\s+(a\s+little|more))?"
    r"|pan\s+(left|right)"
    r"|tilt\s+(up|down))\b",
    re.IGNORECASE,
)
_PTZ_CENTER_PATTERN = re.compile(
    r"\b(?:center\s+the\s+camera|stop\s+moving)\b",
    re.IGNORECASE,
)
_ZOOM_PATTERN = re.compile(
    r"\bzoom\s+(in|out)(?:\s+(a\s+little|more))?\b",
    re.IGNORECASE,
)

# Quality mode patterns
_QUALITY_PATTERN = re.compile(
    r"\b(?:switch\s+to\s+(smooth|sharp|balanced|analysis)(?:\s+mode)?"
    r"|make\s+the\s+camera\s+(clearer|smoother))\b",
    re.IGNORECASE,
)

# Tracking patterns
_TRACK_START_PATTERN = re.compile(
    r"\b(?:track\s+(?:my\s+|this\s+|the\s+)?(.+?)(?:\s*$|\s+and\b))\b",
    re.IGNORECASE,
)
_TRACK_STOP_PATTERN = re.compile(
    r"\bstop\s+tracking(?:\s+(?:my\s+|the\s+)?(.+))?\b",
    re.IGNORECASE,
)
_LABEL_ITEM_PATTERN = re.compile(
    r"\b(?:this\s+is\s+my\s+(.+)|remember\s+this\s+as\s+(?:my\s+)?(.+))\b",
    re.IGNORECASE,
)

# Watch mode patterns
_WATCH_PATTERN = re.compile(
    r"\b(?:watch\s+(?:my\s+)?(.+)"
    r"|keep\s+an?\s+eye\s+on\s+(?:this\s+|my\s+|the\s+)?(.+)"
    r"|tell\s+me\s+if\s+(?:my\s+|the\s+)?(.+?)(?:\s+(?:moves?|disappears?|changes?))?)\b",
    re.IGNORECASE,
)
_WATCH_STOP_PATTERN = re.compile(
    r"\bstop\s+watch(?:ing)?(?:\s+(?:my\s+|the\s+)?(.+))?\b",
    re.IGNORECASE,
)

# Follow mode patterns
_FOLLOW_START_PATTERN = re.compile(
    r"\b(?:follow\s+(?:me|the\s+(.+))|keep\s+me\s+centered|track\s+my\s+hands)\b",
    re.IGNORECASE,
)
_FOLLOW_STOP_PATTERN = re.compile(
    r"\bstop\s+following\b",
    re.IGNORECASE,
)

# Visual query patterns
_VISUAL_QUERY_PATTERN = re.compile(
    r"\b(?:where\s+is\s+(?:my\s+)?(.+)"
    r"|is\s+(?:my\s+)?(.+?)\s+visible"
    r"|did\s+(?:the\s+)?(?:item|(.+?))\s+move"
    r"|detected\s+items"
    r"|what\s+items)\b",
    re.IGNORECASE,
)

_PHRASE_TO_PRESET = {
    "me": "operator",
    "keyboard": "keyboard",
    "desk": "desk",
    "the desk": "desk",
    "the room": "room",
    "room": "room",
    "hands": "keyboard",
    "my hands": "keyboard",
    "the monitor": "monitor",
}

_DIRECTION_DELTAS = {
    "left": {"pan_delta": -5, "tilt_delta": 0, "zoom_delta": 0},
    "right": {"pan_delta": 5, "tilt_delta": 0, "zoom_delta": 0},
    "up": {"pan_delta": 0, "tilt_delta": 5, "zoom_delta": 0},
    "down": {"pan_delta": 0, "tilt_delta": -5, "zoom_delta": 0},
}

_QUALITY_ALIASES = {
    "clearer": "sharp",
    "smoother": "smooth",
}


@dataclass
class CameraCommand:
    """Parsed camera sub-command."""

    operation: str
    preset_name: str = ""
    save_name: str = ""
    needs_ai: bool = False
    params: dict[str, Any] = field(default_factory=dict)
    source: str = "voice"


def classify_camera_command(transcript: str) -> CameraCommand:
    """Deterministically classify a camera intent into a specific operation."""
    # Follow mode (check before tracking to avoid false matches)
    if _FOLLOW_STOP_PATTERN.search(transcript):
        return CameraCommand(operation="follow_stop")

    m = _FOLLOW_START_PATTERN.search(transcript)
    if m:
        target = m.group(1) or "operator"
        return CameraCommand(
            operation="follow_start",
            params={"target": target.strip().lower()},
        )

    # Watch stop (before watch start)
    m = _WATCH_STOP_PATTERN.search(transcript)
    if m:
        item = (m.group(1) or "").strip().lower()
        return CameraCommand(operation="watch_stop", params={"target": item})

    # Presets (before tracking patterns to avoid "look at my X" hitting track)
    m = _PRESET_PATTERN.search(transcript)
    if m:
        phrase = m.group(1).lower()
        preset = _PHRASE_TO_PRESET.get(phrase, phrase)
        return CameraCommand(operation="preset", preset_name=preset)

    # Update preset
    m = _UPDATE_PRESET_PATTERN.search(transcript)
    if m:
        name = m.group(1).lower()
        return CameraCommand(operation="save_preset", save_name=name)

    # Save preset
    m = _SAVE_PRESET_PATTERN.search(transcript)
    if m:
        name_raw = m.group(1) or "custom"
        name = name_raw.strip().lower().replace(" ", "_")
        return CameraCommand(operation="save_preset", save_name=name)

    # PTZ center / stop moving
    if _PTZ_CENTER_PATTERN.search(transcript):
        return CameraCommand(operation="ptz_home")

    # PTZ directional movement
    m = _PTZ_MOVE_PATTERN.search(transcript)
    if m:
        direction = (m.group(1) or m.group(3) or m.group(4) or "").lower()
        modifier = (m.group(2) or "").lower().strip()
        deltas = dict(_DIRECTION_DELTAS.get(direction, {}))
        if modifier == "a little":
            deltas = {k: v // 2 or (1 if v > 0 else -1) for k, v in deltas.items()}
        elif modifier == "more":
            deltas = {k: v * 2 for k, v in deltas.items()}
        return CameraCommand(operation="ptz_relative", params=deltas)

    # Zoom
    m = _ZOOM_PATTERN.search(transcript)
    if m:
        direction = m.group(1).lower()
        modifier = (m.group(2) or "").lower().strip()
        step = 10
        if modifier == "a little":
            step = 5
        elif modifier == "more":
            step = 20
        zoom_delta = step if direction == "in" else -step
        return CameraCommand(
            operation="ptz_relative",
            params={"pan_delta": 0, "tilt_delta": 0, "zoom_delta": zoom_delta},
        )

    # Quality mode
    m = _QUALITY_PATTERN.search(transcript)
    if m:
        mode = (m.group(1) or "").lower()
        alias = (m.group(2) or "").lower()
        quality = mode or _QUALITY_ALIASES.get(alias, "balanced")
        return CameraCommand(operation="quality_mode", params={"mode": quality})

    # Label item ("this is my X" / "remember this as X")
    m = _LABEL_ITEM_PATTERN.search(transcript)
    if m:
        label = (m.group(1) or m.group(2) or "").strip().lower()
        return CameraCommand(
            operation="label_item",
            params={"label": label},
            needs_ai=False,
        )

    # Track stop
    m = _TRACK_STOP_PATTERN.search(transcript)
    if m:
        item = (m.group(1) or "").strip().lower()
        return CameraCommand(operation="track_stop", params={"target": item})

    # Watch mode
    m = _WATCH_PATTERN.search(transcript)
    if m:
        target = (m.group(1) or m.group(2) or m.group(3) or "").strip().lower()
        return CameraCommand(
            operation="watch_start",
            params={"target": target},
        )

    # Visual query (where is my X, is X visible, detected items)
    m = _VISUAL_QUERY_PATTERN.search(transcript)
    if m:
        target = (m.group(1) or m.group(2) or m.group(3) or "").strip().lower()
        return CameraCommand(
            operation="visual_query",
            params={"target": target},
            needs_ai=False,
        )

    # Track start
    m = _TRACK_START_PATTERN.search(transcript)
    if m:
        target = m.group(1).strip().lower()
        return CameraCommand(
            operation="track_start",
            params={"target": target},
        )

    # Snapshot / AI analysis
    if _SNAPSHOT_PATTERN.search(transcript):
        return CameraCommand(operation="analyze", needs_ai=True)

    # Start / stop / status
    if _START_PATTERN.search(transcript):
        return CameraCommand(operation="start")

    if _STOP_PATTERN.search(transcript):
        return CameraCommand(operation="stop")

    if _STATUS_PATTERN.search(transcript):
        return CameraCommand(operation="status")

    return CameraCommand(operation="snapshot")


def dispatch_camera_command(
    cmd: CameraCommand,
    mesh_dispatch_fn: Any = None,
    target_node: str = "beast_windows",
) -> dict[str, Any]:
    """Execute a camera command via the node mesh.

    mesh_dispatch_fn: callable(node_id, capability_name, params) -> dict
    """
    if mesh_dispatch_fn is None:
        return {"success": False, "error": "no mesh dispatch available"}

    if cmd.operation == "preset":
        return mesh_dispatch_fn(target_node, "camera.set_preset", {"name": cmd.preset_name})

    if cmd.operation == "save_preset":
        return mesh_dispatch_fn(target_node, "camera.save_preset", {"name": cmd.save_name})

    if cmd.operation == "ptz_relative":
        return mesh_dispatch_fn(target_node, "camera.ptz_relative", cmd.params)

    if cmd.operation == "ptz_home":
        return mesh_dispatch_fn(target_node, "camera.set_position", {"pan": 0, "tilt": 0, "zoom": 100})

    if cmd.operation == "quality_mode":
        return {"success": True, "mode": cmd.params.get("mode", "balanced"), "target": "cockpit"}

    if cmd.operation in ("snapshot", "analyze"):
        return mesh_dispatch_fn(target_node, "camera.snapshot", {"quality": 80})

    if cmd.operation == "start":
        return mesh_dispatch_fn(target_node, "camera.stream_start", {"fps": 2, "quality": 60})

    if cmd.operation == "stop":
        return mesh_dispatch_fn(target_node, "camera.stream_stop", {})

    if cmd.operation == "status":
        return mesh_dispatch_fn(target_node, "camera.status", {})

    if cmd.operation in ("track_start", "track_stop", "label_item",
                         "watch_start", "watch_stop",
                         "follow_start", "follow_stop",
                         "visual_query"):
        return {"success": True, "operation": cmd.operation, "params": cmd.params}

    return {"success": False, "error": f"unknown camera operation: {cmd.operation}"}


def analyze_snapshot(
    image_base64: str,
    transcript: str = "",
    width: int = 0,
    height: int = 0,
) -> str:
    """Send a camera snapshot to the LLM for visual analysis.

    Uses call_with_fallback with images parameter. Falls back to a
    deterministic description if all LLM providers fail.
    """
    import base64

    from adapters.models.model_router import call_with_fallback

    context_hint = ""
    if "posture" in transcript.lower():
        context_hint = "Focus on the person's posture and body position."
    elif "desk" in transcript.lower():
        context_hint = "Focus on what's on the desk and the workspace setup."
    elif "keyboard" in transcript.lower():
        context_hint = "Focus on the keyboard area and what the hands are doing."

    prompt = (
        "You are looking through a webcam. Describe what you see concisely (2-3 sentences). "
        "Be observational and helpful. "
        "Include confidence levels (high/medium/low) for each observation. "
        "If you cannot clearly identify something, say so. Never invent details. "
        f"{context_hint}"
    ).strip()

    try:
        image_bytes = base64.b64decode(image_base64)
    except Exception:
        return "Failed to decode the camera frame."

    result = call_with_fallback(
        prompt=prompt,
        images=[(image_bytes, "image/jpeg")],
        agent_type="ceo",
    )

    if result and result.output:
        return result.output

    dim_info = f" ({width}x{height})" if width and height else ""
    return f"I captured a frame{dim_info} but couldn't analyze it right now. The image is saved for review."
