"""Presence Timeline — operator presence transition tracking.

Tracks device switches, workspace switches, session transitions,
node transitions, and operator state transitions. Observation only.
Answers: "Where did I leave off?"

Phase 32. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from substrate.operator.operator_presence import (
    PresenceDeviceType,
    PresenceState,
)


class PresenceTransitionType:
    """Types of presence transitions."""

    DEVICE_SWITCH = "device_switch"
    WORKSPACE_SWITCH = "workspace_switch"
    SESSION_TRANSITION = "session_transition"
    NODE_TRANSITION = "node_transition"
    STATE_TRANSITION = "state_transition"

    ALL = [
        DEVICE_SWITCH,
        WORKSPACE_SWITCH,
        SESSION_TRANSITION,
        NODE_TRANSITION,
        STATE_TRANSITION,
    ]


@dataclass
class PresenceTransition:
    """A single presence transition event."""

    transition_id: str = field(default_factory=lambda: f"ptx-{uuid4().hex[:10]}")
    transition_type: str = ""
    from_value: str = ""
    to_value: str = ""
    device_type: PresenceDeviceType = PresenceDeviceType.UNKNOWN
    detail: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "transition_type": self.transition_type,
            "from_value": self.from_value,
            "to_value": self.to_value,
            "device_type": self.device_type.value,
            "detail": self.detail,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PresenceTransition:
        return cls(
            transition_id=data.get("transition_id", f"ptx-{uuid4().hex[:10]}"),
            transition_type=data.get("transition_type", ""),
            from_value=data.get("from_value", ""),
            to_value=data.get("to_value", ""),
            device_type=PresenceDeviceType(data.get("device_type", "unknown")),
            detail=data.get("detail", ""),
            timestamp=data.get("timestamp", time.time()),
        )


class PresenceTimeline:
    """In-memory presence transition log."""

    def __init__(self, max_entries: int = 200) -> None:
        self._transitions: list[PresenceTransition] = []
        self._max_entries = max_entries

    def record(self, transition: PresenceTransition) -> None:
        """Record a presence transition."""
        self._transitions.append(transition)
        if len(self._transitions) > self._max_entries:
            self._transitions = self._transitions[-self._max_entries:]

    def record_device_switch(
        self,
        from_device: PresenceDeviceType,
        to_device: PresenceDeviceType,
        detail: str = "",
    ) -> PresenceTransition:
        """Record a device switch."""
        t = PresenceTransition(
            transition_type=PresenceTransitionType.DEVICE_SWITCH,
            from_value=from_device.value,
            to_value=to_device.value,
            device_type=to_device,
            detail=detail,
        )
        self.record(t)
        return t

    def record_workspace_switch(
        self,
        from_workspace: str,
        to_workspace: str,
        device_type: PresenceDeviceType = PresenceDeviceType.UNKNOWN,
        detail: str = "",
    ) -> PresenceTransition:
        """Record a workspace switch."""
        t = PresenceTransition(
            transition_type=PresenceTransitionType.WORKSPACE_SWITCH,
            from_value=from_workspace,
            to_value=to_workspace,
            device_type=device_type,
            detail=detail,
        )
        self.record(t)
        return t

    def record_session_transition(
        self,
        from_session: str,
        to_session: str,
        device_type: PresenceDeviceType = PresenceDeviceType.UNKNOWN,
        detail: str = "",
    ) -> PresenceTransition:
        """Record a session transition."""
        t = PresenceTransition(
            transition_type=PresenceTransitionType.SESSION_TRANSITION,
            from_value=from_session,
            to_value=to_session,
            device_type=device_type,
            detail=detail,
        )
        self.record(t)
        return t

    def record_state_transition(
        self,
        from_state: PresenceState,
        to_state: PresenceState,
        device_type: PresenceDeviceType = PresenceDeviceType.UNKNOWN,
        detail: str = "",
    ) -> PresenceTransition:
        """Record an operator state transition."""
        t = PresenceTransition(
            transition_type=PresenceTransitionType.STATE_TRANSITION,
            from_value=from_state.value,
            to_value=to_state.value,
            device_type=device_type,
            detail=detail,
        )
        self.record(t)
        return t

    def recent(self, limit: int = 50) -> list[PresenceTransition]:
        """Recent transitions, newest first."""
        return list(reversed(self._transitions[-limit:]))

    def by_type(self, transition_type: str) -> list[PresenceTransition]:
        """Filter transitions by type."""
        return [
            t for t in self._transitions
            if t.transition_type == transition_type
        ]

    def since(self, timestamp: float) -> list[PresenceTransition]:
        """Transitions since a given timestamp."""
        return [t for t in self._transitions if t.timestamp >= timestamp]

    def count(self) -> int:
        """Total recorded transitions."""
        return len(self._transitions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transitions": [t.to_dict() for t in self._transitions],
            "count": len(self._transitions),
        }
