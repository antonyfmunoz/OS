"""Device presence registry for active cockpit sessions.

Tracks which operator surfaces are currently connected, their audio
capabilities, and which mesh nodes they can reach.  The registry is an
in-memory singleton with a thread-safe lock; sessions expire after
`_STALE_AFTER_SECONDS` without a heartbeat.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_STALE_AFTER_SECONDS = 60


@dataclass
class DeviceSession:
    """A single active operator surface registered with the presence registry."""

    device_id: str
    session_id: str
    operator_id: str = "default"
    # mobile_browser | desktop_browser | electron | terminal
    client_type: str = "desktop_browser"
    device_label: str = ""
    # fly_cockpit | local_cockpit | electron_cockpit | terminal
    control_surface: str = "fly_cockpit"
    current_panel: str = ""
    can_capture_audio: bool = True
    can_play_audio: bool = True
    reachable_nodes: list[str] = field(default_factory=lambda: ["cockpit", "vps"])
    last_seen: str = ""
    status: str = "active"  # active | idle | disconnected

    def __post_init__(self) -> None:
        if not self.last_seen:
            self.last_seen = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceSession:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def _age_seconds(self) -> float:
        try:
            last = datetime.fromisoformat(self.last_seen.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return (now - last).total_seconds()
        except Exception:
            return 0.0

    def is_stale(self, max_age_seconds: int = _STALE_AFTER_SECONDS) -> bool:
        return self._age_seconds() > max_age_seconds


class DevicePresenceRegistry:
    """Thread-safe in-memory registry of active device sessions.

    All mutation goes through the public API methods; the internal lock
    prevents races between heartbeat and cleanup calls.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, DeviceSession] = {}
        self._lock = threading.Lock()

    def register_session(self, session: DeviceSession) -> None:
        """Add or replace a session.  Refreshes last_seen on re-registration."""
        session.last_seen = datetime.now(timezone.utc).isoformat()
        session.status = "active"
        with self._lock:
            self._sessions[session.session_id] = session
        logger.debug(
            "[DevicePresence] registered session=%s device=%s surface=%s",
            session.session_id,
            session.device_id,
            session.control_surface,
        )

    def heartbeat(self, session_id: str, updates: dict[str, Any] | None = None) -> bool:
        """Refresh last_seen and apply optional field updates.

        Returns True if the session exists, False if unknown.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.last_seen = datetime.now(timezone.utc).isoformat()
            session.status = "active"
            if updates:
                for key, value in updates.items():
                    if hasattr(session, key) and key not in ("session_id", "device_id"):
                        setattr(session, key, value)
            return True

    def get_session(self, session_id: str) -> DeviceSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def get_active_sessions(self) -> list[DeviceSession]:
        """Return all sessions that are not disconnected and not stale."""
        with self._lock:
            return [
                s for s in self._sessions.values()
                if s.status != "disconnected" and not s.is_stale()
            ]

    def get_default_audio_output(self, source_session_id: str) -> str:
        """Return the session_id that should receive TTS audio.

        Default: audio returns to source.  Falls back to any session that
        can play audio if the source session is not found or cannot play.
        """
        with self._lock:
            source = self._sessions.get(source_session_id)
            if source and source.can_play_audio and source.status == "active":
                return source_session_id

            # Fallback to first active audio-capable session
            for s in self._sessions.values():
                if s.status == "active" and s.can_play_audio and not s.is_stale():
                    return s.session_id

        return ""

    def mark_disconnected(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.status = "disconnected"
                logger.debug("[DevicePresence] disconnected session=%s", session_id)

    def cleanup_stale(self, max_age_seconds: int = _STALE_AFTER_SECONDS) -> int:
        """Mark stale sessions as disconnected.  Returns count of sessions marked."""
        count = 0
        with self._lock:
            for session in self._sessions.values():
                if session.status == "active" and session.is_stale(max_age_seconds):
                    session.status = "disconnected"
                    count += 1
        if count:
            logger.debug("[DevicePresence] marked %d stale sessions disconnected", count)
        return count


# Module-level singleton
_registry = DevicePresenceRegistry()


def get_registry() -> DevicePresenceRegistry:
    """Return the shared module-level registry."""
    return _registry
