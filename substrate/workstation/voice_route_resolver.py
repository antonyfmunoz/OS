"""Voice route resolver — separates execution target from audio output device.

Doctrine:
  - Voice belongs to the operator session
  - Execution belongs to the target node
  - Audio returns to the source device unless explicitly redirected

All logic is deterministic — no LLM calls.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Patterns for target node detection
_BEAST_PATTERNS = [
    r"\bon\s+(?:the\s+)?(?:workstation|beast|beast\s+pc|pc|desktop|windows)\b",
    r"\bopen\s+.+\s+on\s+(?:the\s+)?(?:workstation|beast|windows)\b",
    r"\busing\s+(?:the\s+)?(?:workstation|beast)\b",
]

_VPS_PATTERNS = [
    r"\bon\s+(?:the\s+)?(?:vps|server|cloud|remote\s+server|linux|vps\s+server)\b",
    r"\brun\s+.+\s+on\s+(?:the\s+)?(?:vps|server)\b",
    r"\bshow\s+(?:docker|containers|services)\b",
    r"\bcheck\s+(?:the\s+)?server\b",
    r"\bdocker\s+(?:containers|ps|status)\b",
]

# Patterns for audio override
_AUDIO_BEAST_PATTERNS = [
    r"\bspeak\s+(?:from|on|through)\s+(?:the\s+)?(?:workstation|beast|windows|desktop)\b",
    r"\btalk\s+(?:from|through)\s+(?:the\s+)?(?:workstation|beast)\b",
    r"\bplay\s+(?:audio|sound|voice)\s+on\s+(?:the\s+)?(?:workstation|beast)\b",
    r"\bsay\s+it\s+on\s+(?:the\s+)?(?:workstation|beast)\b",
]

_AUDIO_PHONE_PATTERNS = [
    r"\bspeak\s+(?:from|on|through)\s+(?:my\s+)?(?:phone|mobile|iphone)\b",
    r"\bsay\s+it\s+on\s+(?:my\s+)?(?:phone|mobile)\b",
    r"\btalk\s+(?:to\s+me\s+)?on\s+(?:my\s+)?(?:phone|mobile|iphone)\b",
    r"\bplay\s+(?:audio|sound|voice)\s+on\s+(?:my\s+)?(?:phone|mobile)\b",
]

_AUDIO_HERE_PATTERNS = [
    r"\bspeak\s+(?:back\s+)?here\b",
    r"\btalk\s+back\s+here\b",
    r"\banswer\s+here\b",
    r"\bplay\s+(?:audio|sound|voice)\s+here\b",
]

_CAMERA_TARGET_PATTERNS = [
    r"\blook\s+at\s+(?:me|my\s+keyboard|the\s+desk|my\s+desk|the\s+room)\b",
    r"\bwatch\s+the\s+room\b",
    r"\bcamera\s+(?:on|off|start|stop|status|preset|snapshot)\b",
    r"\bturn\s+(?:on|off)\s+(?:the\s+)?camera\b",
    r"\bwhat\s+(?:do|can)\s+you\s+see\b",
    r"\bdescribe\s+what\s+you\s+see\b",
    r"\banalyze\s+this\s+frame\b",
    r"\bsave\s+this\s+(?:camera\s+)?(?:position|preset)\b",
    r"\bam\s+i\s+at\s+my\s+desk\b",
    r"\bis\s+my\s+posture\b",
    r"\btake\s+a\s+snapshot\b",
]


def parse_target_node(transcript: str) -> str:
    """Deterministically extract execution target from transcript.

    Returns: 'beast_windows', 'vps', or '' (empty = stay on cockpit/conversation).
    """
    lower = transcript.lower()

    # Camera commands always route to Beast (that's where the hardware is)
    for pattern in _CAMERA_TARGET_PATTERNS:
        if re.search(pattern, lower):
            return "beast_windows"

    for pattern in _BEAST_PATTERNS:
        if re.search(pattern, lower):
            return "beast_windows"

    for pattern in _VPS_PATTERNS:
        if re.search(pattern, lower):
            return "vps"

    return ""


def parse_audio_override(transcript: str) -> str:
    """Detect explicit audio output override in transcript.

    Returns: 'beast_windows', 'source_device', or '' (empty = no override).
    """
    lower = transcript.lower()

    for pattern in _AUDIO_BEAST_PATTERNS:
        if re.search(pattern, lower):
            return "beast_windows"

    for pattern in _AUDIO_PHONE_PATTERNS:
        if re.search(pattern, lower):
            return "source_device"

    for pattern in _AUDIO_HERE_PATTERNS:
        if re.search(pattern, lower):
            return "source_device"

    return ""


@dataclass
class VoiceRoute:
    """Resolved voice routing contract for a single operator utterance."""

    input_device: str
    control_surface: str
    execution_target: str
    audio_output_device: str
    audio_output_session: str
    response_render_surface: str
    # conversation | remote_control
    handoff_mode: str = "conversation"
    route_reason: str = ""
    requires_approval: bool = False

    def to_dict(self) -> dict:
        return {
            "input_device": self.input_device,
            "control_surface": self.control_surface,
            "execution_target": self.execution_target,
            "audio_output_device": self.audio_output_device,
            "audio_output_session": self.audio_output_session,
            "response_render_surface": self.response_render_surface,
            "handoff_mode": self.handoff_mode,
            "route_reason": self.route_reason,
            "requires_approval": self.requires_approval,
        }


def resolve_voice_route(
    transcript: str,
    source_session_id: str,
    view_context: dict | None = None,
    requested_target_node: str | None = None,
) -> VoiceRoute:
    """Resolve the full voice route for an utterance.

    Resolution rules (in order):
    1. Audio returns to source session by default.
    2. Target node detected from transcript keywords.
    3. Explicit audio override detected from transcript.
    4. If source session cannot play audio -> text_only audio path.
    5. If no audio session exists -> text_only.
    6. Non-conversation target nodes -> remote_control handoff mode.
    """
    from substrate.workstation.device_presence import get_registry

    registry = get_registry()
    source_session = registry.get_session(source_session_id)

    # Determine input device / control surface from registered session
    input_device = source_session.device_id if source_session else "unknown"
    control_surface = source_session.control_surface if source_session else "fly_cockpit"
    can_play_audio = source_session.can_play_audio if source_session else True

    # Detect target node
    if requested_target_node:
        execution_target = requested_target_node
    else:
        execution_target = parse_target_node(transcript)

    # Detect audio override
    audio_override = parse_audio_override(transcript)

    # Determine audio output
    if not can_play_audio or control_surface == "terminal":
        # Terminal sessions and non-audio surfaces get text-only
        audio_output_device = "text_only"
        audio_output_session = ""
        route_reason = "source cannot play audio"
    elif audio_override == "beast_windows":
        audio_output_device = "beast_windows"
        audio_output_session = ""  # Real hardware session not tracked yet
        route_reason = "explicit audio override to workstation"
    else:
        # Default: audio returns to source
        audio_output_session = registry.get_default_audio_output(source_session_id)
        audio_output_device = input_device if audio_output_session else "text_only"
        if not audio_output_session:
            route_reason = "no audio-capable session found"
        else:
            route_reason = "audio returns to source"

    # Handoff mode: remote control if sending to a different node
    if execution_target in ("beast_windows", "vps") and execution_target != "cockpit":
        handoff_mode = "remote_control"
    else:
        handoff_mode = "conversation"

    response_render_surface = control_surface

    route = VoiceRoute(
        input_device=input_device,
        control_surface=control_surface,
        execution_target=execution_target or "cockpit",
        audio_output_device=audio_output_device,
        audio_output_session=audio_output_session,
        response_render_surface=response_render_surface,
        handoff_mode=handoff_mode,
        route_reason=route_reason,
    )

    logger.debug(
        "[VoiceRoute] session=%s target=%s audio=%s mode=%s reason=%s",
        source_session_id,
        route.execution_target,
        route.audio_output_device,
        route.handoff_mode,
        route_reason,
    )

    return route
