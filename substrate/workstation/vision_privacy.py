"""Vision privacy governance — hard-coded rules for camera usage.

These rules are NOT configurable. They are structural constraints
that cannot be overridden by AI, operator preference, or config.

Phase 14.14E extends with tracking/watch/follow privacy boundaries.
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

TRACKING_PRIVACY_RULES = [
    "Tracking requires explicit operator activation ('track my phone').",
    "No identity recognition from faces — presence detection only.",
    "No emotion, mood, or health claims from visual data.",
    "Scene state expires after 5 minutes without fresh frames.",
    "Operator-labeled items require explicit confirmation.",
    "Watch mode requires explicit opt-in per item.",
    "Watch mode auto-expires after 60 minutes.",
    "Follow mode requires explicit activation ('follow me').",
    "Follow mode shows active indicator in cockpit UI.",
    "No biometric memory — no persistent face/body templates.",
    "No continuous video recording. Only latest-frame buffer.",
    "Lost objects reported as 'lost', never guessed at.",
]

OVERLAY_PRIVACY_RULES = [
    "Overlay data is ephemeral — no persistent overlay recording.",
    "Face tracking shows bounding box only — no identity labels by default.",
    "Operator enrollment is local-only and explicit.",
    "Unknown persons are labeled 'unknown_person', never identified.",
    "Gesture control requires explicit opt-in and visible HUD indicator.",
    "Trigger chains are auditable — every fire has event, confidence, frame_id.",
    "Security harden mode may NOT trigger physical harm or doxxing.",
    "Continuous video recording is forbidden in all modes.",
]

STREAM_AUTO_TIMEOUT_S = 30 * 60
WATCH_DEFAULT_EXPIRY_M = 60
SCENE_EXPIRY_S = 300

FORBIDDEN_CLAIMS = [
    "identity_recognition",
    "emotion_detection",
    "health_diagnosis",
    "age_estimation",
    "gender_classification",
    "ethnicity_classification",
    "biometric_storage",
]

FORBIDDEN_SECURITY_ACTIONS = [
    "weapon_targeting",
    "physical_defense",
    "doxxing",
    "public_posting",
    "external_messaging_without_approval",
    "continuous_video_recording",
    "identity_recognition_of_strangers",
    "biometric_enrollment_without_consent",
]


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
    allowed_purposes = ("latest_buffer", "proof_frame")
    if purpose in allowed_purposes:
        return True, f"{purpose} is allowed"
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


def validate_tracking_activation(
    is_explicit: bool,
    operator_session_id: str = "",
) -> tuple[bool, str]:
    """Gate check: is tracking activation allowed?

    Tracking requires explicit operator opt-in. Silent activation is blocked.
    """
    if not operator_session_id:
        return False, "no operator session — tracking requires authenticated operator"
    if not is_explicit:
        return False, "tracking requires explicit operator command"
    return True, "explicit operator tracking activation"


def validate_watch_activation(
    is_explicit: bool,
    active_watch_count: int = 0,
    max_watches: int = 10,
) -> tuple[bool, str]:
    """Gate check: is watch mode activation allowed?"""
    if not is_explicit:
        return False, "watch mode requires explicit opt-in"
    if active_watch_count >= max_watches:
        return False, f"maximum active watches ({max_watches}) reached"
    return True, "explicit watch activation allowed"


def validate_follow_activation(
    is_explicit: bool,
) -> tuple[bool, str]:
    """Gate check: is follow mode activation allowed?"""
    if not is_explicit:
        return False, "follow mode requires explicit activation"
    return True, "explicit follow activation"


def validate_visual_claim(claim_type: str) -> tuple[bool, str]:
    """Gate check: is this type of visual claim allowed?"""
    if claim_type in FORBIDDEN_CLAIMS:
        return False, f"visual claim type '{claim_type}' is forbidden"
    return True, f"visual claim type '{claim_type}' is allowed"


def validate_operator_enrollment(
    is_explicit: bool,
    storage_local_only: bool = True,
) -> tuple[bool, str]:
    """Gate check: is operator face enrollment allowed?"""
    if not is_explicit:
        return False, "operator enrollment requires explicit opt-in"
    if not storage_local_only:
        return False, "enrollment data must be local-only (never uploaded)"
    return True, "explicit local-only enrollment allowed"


def validate_gesture_control(
    is_explicit: bool,
    risk_level: str = "low",
) -> tuple[bool, str]:
    """Gate check: is gesture-based control allowed?"""
    if not is_explicit:
        return False, "gesture control requires explicit opt-in"
    if risk_level == "high":
        return False, "high-risk actions cannot be approved by gesture"
    return True, f"gesture control allowed for {risk_level}-risk actions"


def validate_trigger_chain_action(action_type: str) -> tuple[bool, str]:
    """Gate check: is this trigger chain action type allowed?"""
    if action_type in FORBIDDEN_SECURITY_ACTIONS:
        return False, f"action '{action_type}' is forbidden"
    return True, f"action '{action_type}' is allowed"


def get_active_mode() -> CameraMode:
    """Return the current camera privacy mode.

    Currently always returns SNAPSHOT_ON_REQUEST as the default
    operating mode. Ambient modes are future work with explicit
    opt-in.
    """
    return CameraMode.SNAPSHOT_ON_REQUEST
