"""Runtime Presence State v1 for the UMH substrate layer.

Workstation presence model: tracks whether the local execution
environment is active, idle, executing, awaiting approval,
disconnected, or recovering. This is the foundation of
persistent Jarvis-style operational continuity.

UMH substrate subsystem. Phase 96.8AE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class WorkstationPresenceState(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    EXECUTING = "executing"
    AWAITING_APPROVAL = "awaiting_approval"
    DISCONNECTED = "disconnected"
    RECOVERING = "recovering"


VALID_PRESENCE_TRANSITIONS: dict[WorkstationPresenceState, frozenset[WorkstationPresenceState]] = {
    WorkstationPresenceState.ACTIVE: frozenset(
        {
            WorkstationPresenceState.IDLE,
            WorkstationPresenceState.EXECUTING,
            WorkstationPresenceState.DISCONNECTED,
        }
    ),
    WorkstationPresenceState.IDLE: frozenset(
        {
            WorkstationPresenceState.ACTIVE,
            WorkstationPresenceState.EXECUTING,
            WorkstationPresenceState.DISCONNECTED,
        }
    ),
    WorkstationPresenceState.EXECUTING: frozenset(
        {
            WorkstationPresenceState.ACTIVE,
            WorkstationPresenceState.AWAITING_APPROVAL,
            WorkstationPresenceState.DISCONNECTED,
            WorkstationPresenceState.RECOVERING,
        }
    ),
    WorkstationPresenceState.AWAITING_APPROVAL: frozenset(
        {
            WorkstationPresenceState.EXECUTING,
            WorkstationPresenceState.ACTIVE,
            WorkstationPresenceState.DISCONNECTED,
        }
    ),
    WorkstationPresenceState.DISCONNECTED: frozenset(
        {
            WorkstationPresenceState.RECOVERING,
            WorkstationPresenceState.ACTIVE,
        }
    ),
    WorkstationPresenceState.RECOVERING: frozenset(
        {
            WorkstationPresenceState.ACTIVE,
            WorkstationPresenceState.DISCONNECTED,
            WorkstationPresenceState.EXECUTING,
        }
    ),
}


@dataclass
class PresenceTransitionRecord:
    """Immutable record of a presence state change."""

    from_state: WorkstationPresenceState
    to_state: WorkstationPresenceState
    reason: str = ""
    timestamp: str = ""
    packet_id: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "packet_id": self.packet_id,
        }


@dataclass
class WorkstationPresence:
    """Tracks workstation presence with transition history."""

    current_state: WorkstationPresenceState = WorkstationPresenceState.DISCONNECTED
    last_transition: str = ""
    active_since: str = ""
    history: list[PresenceTransitionRecord] = field(default_factory=list)

    def transition(
        self,
        to_state: WorkstationPresenceState,
        reason: str = "",
        packet_id: str = "",
    ) -> PresenceTransitionRecord | None:
        """Attempt a presence transition. Returns record if valid, None if invalid."""
        valid = VALID_PRESENCE_TRANSITIONS.get(self.current_state, frozenset())
        if to_state not in valid:
            return None

        record = PresenceTransitionRecord(
            from_state=self.current_state,
            to_state=to_state,
            reason=reason,
            packet_id=packet_id,
        )
        self.current_state = to_state
        self.last_transition = record.timestamp
        if to_state == WorkstationPresenceState.ACTIVE:
            self.active_since = record.timestamp
        self.history.append(record)
        return record

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_state": self.current_state.value,
            "last_transition": self.last_transition,
            "active_since": self.active_since,
            "transition_count": len(self.history),
        }


def is_execution_capable(state: WorkstationPresenceState) -> bool:
    return state in {
        WorkstationPresenceState.ACTIVE,
        WorkstationPresenceState.IDLE,
        WorkstationPresenceState.EXECUTING,
    }
