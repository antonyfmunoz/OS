"""Camera command dispatcher — routes CAMERA_CONTROL intents to operations.

Deterministic sub-intent classification (no LLM). Dispatches operations
through the node mesh to the Beast camera adapter. Snapshot analysis
uses call_with_fallback with vision/image attachment.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_PRESET_PATTERN = re.compile(
    r"\blook\s+at\s+(?:my\s+)?(keyboard|desk|me|the\s+desk|the\s+room)\b",
    re.IGNORECASE,
)
_SNAPSHOT_PATTERN = re.compile(
    r"\b(?:what\s+(?:do|can)\s+you\s+see|describe\s+what\s+you\s+see|"
    r"take\s+a\s+snapshot|analyze\s+this\s+frame|"
    r"am\s+i\s+at\s+my\s+desk|is\s+my\s+posture)\b",
    re.IGNORECASE,
)
_SAVE_PRESET_PATTERN = re.compile(
    r"\bsave\s+(?:this\s+)?(?:camera\s+)?(?:position|preset)\s*(?:as\s+(\w+))?\b",
    re.IGNORECASE,
)
_START_PATTERN = re.compile(
    r"\b(?:camera\s+on|turn\s+on\s+(?:the\s+)?camera|start\s+(?:the\s+)?camera)\b",
    re.IGNORECASE,
)
_STOP_PATTERN = re.compile(
    r"\b(?:camera\s+off|turn\s+off\s+(?:the\s+)?camera|stop\s+(?:the\s+)?camera)\b",
    re.IGNORECASE,
)
_STATUS_PATTERN = re.compile(
    r"\bcamera\s+status\b",
    re.IGNORECASE,
)

_PHRASE_TO_PRESET = {
    "me": "operator",
    "keyboard": "keyboard",
    "desk": "desk",
    "the desk": "desk",
    "the room": "room",
}


@dataclass
class CameraCommand:
    """Parsed camera sub-command."""

    operation: str  # preset | snapshot | analyze | start | stop | status | save_preset
    preset_name: str = ""
    save_name: str = ""
    needs_ai: bool = False


def classify_camera_command(transcript: str) -> CameraCommand:
    """Deterministically classify a camera intent into a specific operation."""
    m = _PRESET_PATTERN.search(transcript)
    if m:
        phrase = m.group(1).lower()
        preset = _PHRASE_TO_PRESET.get(phrase, phrase)
        return CameraCommand(operation="preset", preset_name=preset)

    m = _SAVE_PRESET_PATTERN.search(transcript)
    if m:
        name = m.group(1) or "custom"
        return CameraCommand(operation="save_preset", save_name=name.lower())

    if _SNAPSHOT_PATTERN.search(transcript):
        return CameraCommand(operation="analyze", needs_ai=True)

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

    if cmd.operation in ("snapshot", "analyze"):
        return mesh_dispatch_fn(target_node, "camera.snapshot", {"quality": 80})

    if cmd.operation == "start":
        return mesh_dispatch_fn(target_node, "camera.stream_start", {"fps": 2, "quality": 60})

    if cmd.operation == "stop":
        return mesh_dispatch_fn(target_node, "camera.stream_stop", {})

    if cmd.operation == "status":
        return mesh_dispatch_fn(target_node, "camera.status", {})

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
