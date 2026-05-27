"""Runtime Presence State v1 — workstation presence tracking.

Tracks whether the local workstation is available, active, executing,
or disconnected. Used by the Local Runtime Supervisor to gate execution
and report state.

UMH substrate subsystem.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class WorkstationPresenceState(str, Enum):
    UNKNOWN = "unknown"
    DISCONNECTED = "disconnected"
    IDLE = "idle"
    ACTIVE = "active"
    EXECUTING = "executing"
    LOCKED = "locked"


class WorkstationPresence:
    """Tracks the current presence state of a workstation."""

    def __init__(self) -> None:
        self._state = WorkstationPresenceState.UNKNOWN
        self._last_transition = datetime.now(timezone.utc).isoformat()
        self._reason = ""
        self._active_packet_id = ""

    @property
    def current_state(self) -> WorkstationPresenceState:
        return self._state

    @property
    def last_transition(self) -> str:
        return self._last_transition

    def transition(
        self,
        new_state: WorkstationPresenceState,
        reason: str = "",
        packet_id: str = "",
    ) -> None:
        old = self._state
        self._state = new_state
        self._last_transition = datetime.now(timezone.utc).isoformat()
        self._reason = reason
        if packet_id:
            self._active_packet_id = packet_id
        logger.debug("presence: %s → %s (%s)", old.value, new_state.value, reason)

    def to_dict(self) -> dict:
        return {
            "state": self._state.value,
            "last_transition": self._last_transition,
            "reason": self._reason,
            "active_packet_id": self._active_packet_id,
        }


def is_execution_capable(presence: WorkstationPresence) -> bool:
    """Return True if the workstation can accept new execution."""
    return presence.current_state in (
        WorkstationPresenceState.ACTIVE,
        WorkstationPresenceState.IDLE,
    )
