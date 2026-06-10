"""Security Harden mode — governed security posture for the cockpit.

Activated by trigger chains (e.g., unknown person detected) or
explicit operator command. Elevates governance gates, increases
audit logging, and restricts autonomous actions.

Structural safety constraints:
- May NOT trigger physical harm, targeting, or weapon systems
- May NOT dox, publicly post, or message externally without approval
- May NOT store continuous video by default
- May NOT identify unknown people by name
- All actions are auditable and reversible
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

MAX_EVENT_HISTORY = 50

ALLOWED_SECURITY_ACTIONS = [
    "lock_sensitive_controls",
    "increase_audit_logging",
    "notify_operator",
    "switch_camera_preset",
    "pause_autonomous_actions",
    "require_approval_for_sensitive",
    "show_security_hud",
    "record_event_metadata",
    "capture_proof_frame",
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


@dataclass
class SecurityEvent:
    """Record of a security-related event."""

    event_id: str
    event_type: str
    triggered_by: str
    confidence: float
    frame_id: str
    timestamp: float
    actions_taken: list[str] = field(default_factory=list)
    resolved: bool = False
    resolved_at: float = 0.0
    resolved_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "triggered_by": self.triggered_by,
            "confidence": self.confidence,
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "actions_taken": self.actions_taken,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
        }


@dataclass
class SecurityModeState:
    """Current state of security harden mode."""

    active: bool = False
    risk: str = "high"
    triggered_by: str = ""
    started_at: float = 0.0
    actions_taken: list[str] = field(default_factory=list)
    requires_review: bool = True
    previous_profile_mode: str = ""
    previous_preset_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": "security_harden" if self.active else "normal",
            "active": self.active,
            "risk": self.risk,
            "triggered_by": self.triggered_by,
            "started_at": self.started_at,
            "actions_taken": self.actions_taken,
            "requires_review": self.requires_review,
            "previous_profile_mode": self.previous_profile_mode,
            "previous_preset_id": self.previous_preset_id,
        }


class SecurityModeManager:
    """Manages security harden mode activation/deactivation."""

    def __init__(self) -> None:
        self._state = SecurityModeState()
        self._events: list[SecurityEvent] = []

    @property
    def is_active(self) -> bool:
        return self._state.active

    @property
    def state(self) -> SecurityModeState:
        return self._state

    def activate(
        self,
        triggered_by: str,
        confidence: float = 1.0,
        frame_id: str = "",
        current_profile_mode: str = "",
        current_preset_id: str = "",
    ) -> SecurityModeState:
        """Activate security harden mode. Saves previous state for restoration."""
        now = time.time()
        self._state = SecurityModeState(
            active=True,
            risk="high",
            triggered_by=triggered_by,
            started_at=now,
            requires_review=True,
            previous_profile_mode=current_profile_mode,
            previous_preset_id=current_preset_id,
        )

        default_actions = [
            "lock_sensitive_controls",
            "increase_audit_logging",
            "require_approval_for_sensitive",
            "show_security_hud",
            "record_event_metadata",
        ]
        self._state.actions_taken = default_actions

        event = SecurityEvent(
            event_id=f"sec_{int(now * 1000)}",
            event_type="security_harden_activated",
            triggered_by=triggered_by,
            confidence=confidence,
            frame_id=frame_id,
            timestamp=now,
            actions_taken=default_actions,
        )
        self._events.append(event)
        if len(self._events) > MAX_EVENT_HISTORY:
            self._events = self._events[-MAX_EVENT_HISTORY:]

        logger.warning(
            "SECURITY HARDEN activated: trigger=%s confidence=%.0f%%",
            triggered_by, confidence * 100,
        )
        return self._state

    def deactivate(self, resolved_by: str = "operator") -> dict[str, Any]:
        """Deactivate security harden mode. Returns previous state for restoration."""
        if not self._state.active:
            return {"success": False, "error": "security mode not active"}

        previous = {
            "profile_mode": self._state.previous_profile_mode,
            "preset_id": self._state.previous_preset_id,
        }

        now = time.time()
        if self._events:
            last = self._events[-1]
            if last.event_type == "security_harden_activated" and not last.resolved:
                last.resolved = True
                last.resolved_at = now
                last.resolved_by = resolved_by

        self._state = SecurityModeState()
        logger.info("SECURITY HARDEN deactivated by %s", resolved_by)
        return {"success": True, "previous": previous}

    def validate_action(self, action: str) -> tuple[bool, str]:
        """Check if a proposed security action is allowed."""
        if action in FORBIDDEN_SECURITY_ACTIONS:
            return False, f"action '{action}' is forbidden in security mode"
        if action in ALLOWED_SECURITY_ACTIONS:
            return True, f"action '{action}' is allowed"
        return False, f"action '{action}' is not recognized as a security action"

    def get_recent_events(self, limit: int = 10) -> list[SecurityEvent]:
        return self._events[-limit:]

    def get_state_summary(self) -> dict[str, Any]:
        return {
            **self._state.to_dict(),
            "recent_events": [e.to_dict() for e in self._events[-5:]],
            "event_count": len(self._events),
        }


_security_mgr: SecurityModeManager | None = None


def get_security_manager() -> SecurityModeManager:
    global _security_mgr
    if _security_mgr is None:
        _security_mgr = SecurityModeManager()
    return _security_mgr
