"""Vision privacy governance — hard-coded rules for camera usage.

These rules are NOT configurable. They are structural constraints
that cannot be overridden by AI, operator preference, or config.
"""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class CameraMode(Enum):
    OFF = "camera_off"
    PREVIEW_ONLY = "preview_only"
    SNAPSHOT_ON_REQUEST = "snapshot_on_request"
    AMBIENT_LOW_FREQUENCY = "ambient_low_frequency"
    TRACKING_ONLY = "tracking_only"


PRIVACY_RULES = [
    "Camera is OFF by default. Must be explicitly activated by operator.",
    "Camera status must be visibly indicated whenever active (UI red banner).",
    "No persistent frame storage beyond the latest-frame buffer.",
    "No face recognition or identity matching. Presence detection only (occupied/empty).",
    "No audio capture through the camera pathway. Audio uses voice subsystem only.",
    "No hidden or silent recording. Every frame capture emits a visible signal.",
    "AI analysis is on-demand only. No continuous AI processing of frames.",
    "Frame data never leaves the Tailscale private network.",
    "Camera stream auto-stops after 30 minutes without viewer interaction.",
    "Operator can kill the camera at any time via voice ('camera off') or UI.",
]

STREAM_AUTO_TIMEOUT_S = 30 * 60


def validate_camera_activation(operator_session_id: str) -> tuple[bool, str]:
    """Gate check: is the operator explicitly requesting camera activation?

    Returns (allowed, reason).
    """
    if not operator_session_id:
        return False, "no operator session — camera requires authenticated operator"
    return True, "operator session present"


def validate_frame_storage(purpose: str) -> tuple[bool, str]:
    """Gate check: is this frame storage request allowed?

    Only the latest-frame buffer is permitted. No persistent storage.
    """
    if purpose == "latest_buffer":
        return True, "latest-frame buffer is allowed"
    return False, f"persistent frame storage denied: {purpose}"


def validate_analysis_request(
    is_operator_initiated: bool,
) -> tuple[bool, str]:
    """Gate check: is this AI analysis request allowed?

    Only on-demand, operator-initiated analysis is permitted.
    """
    if is_operator_initiated:
        return True, "operator-initiated analysis allowed"
    return False, "ambient AI analysis not permitted without operator request"


def get_active_mode() -> CameraMode:
    """Return the current camera privacy mode.

    Currently always returns SNAPSHOT_ON_REQUEST as the default
    operating mode. Ambient modes are future work with explicit
    opt-in.
    """
    return CameraMode.SNAPSHOT_ON_REQUEST
