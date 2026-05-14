"""Session Lifecycle Engine v1.

8-state lifecycle for substrate sessions:
  initialized -> active -> checkpointed -> suspended
                                        -> resumed -> active
                        -> archived
                        -> expired -> terminated
  terminated (final)

All transitions validated. Lineage persisted to JSONL.

UMH substrate subsystem. Phase 96.8BV.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.sessions.persistent_substrate_session_contracts_v1 import (
    SessionState,
    _new_id,
    _now_iso,
)


VALID_SESSION_TRANSITIONS: dict[str, list[str]] = {
    "initialized": ["active", "terminated"],
    "active": ["checkpointed", "suspended", "archived", "expired", "terminated"],
    "checkpointed": ["active", "suspended", "archived", "terminated"],
    "suspended": ["resumed", "expired", "terminated"],
    "resumed": ["active", "terminated"],
    "archived": ["terminated"],
    "expired": ["terminated"],
    "terminated": [],
}

TERMINAL_STATES: set[str] = {"terminated"}


@dataclass
class SessionLifecycleTransition:
    """A recorded session lifecycle transition."""

    transition_id: str = ""
    session_id: str = ""
    from_state: str = ""
    to_state: str = ""
    reason: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.transition_id:
            self.transition_id = _new_id("sslt")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "session_id": self.session_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


class SessionLifecycleEngine:
    """Manages substrate session lifecycle transitions.

    All transitions validated against VALID_SESSION_TRANSITIONS.
    Invalid transitions rejected. Lineage persisted to JSONL.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/substrate_sessions",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, str] = {}
        self._transitions: list[SessionLifecycleTransition] = []
        self._total_transitions: int = 0
        self._invalid_transitions: int = 0

    def register(self, session_id: str) -> str:
        """Register a session at initialized state."""
        self._sessions[session_id] = SessionState.INITIALIZED.value
        return SessionState.INITIALIZED.value

    def transition(
        self,
        session_id: str,
        to_state: SessionState,
        reason: str = "",
    ) -> bool:
        """Transition a session to a new state."""
        current = self._sessions.get(session_id)
        if current is None:
            return False

        valid = VALID_SESSION_TRANSITIONS.get(current, [])
        if to_state.value not in valid:
            self._invalid_transitions += 1
            return False

        trans = SessionLifecycleTransition(
            session_id=session_id,
            from_state=current,
            to_state=to_state.value,
            reason=reason,
        )

        self._sessions[session_id] = to_state.value
        self._transitions.append(trans)
        self._total_transitions += 1

        path = self._state_dir / "session_lifecycle_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(trans.to_dict(), default=str) + "\n")

        return True

    def get_state(self, session_id: str) -> str | None:
        return self._sessions.get(session_id)

    def is_terminal(self, session_id: str) -> bool:
        state = self._sessions.get(session_id)
        return state in TERMINAL_STATES if state else False

    def get_active_sessions(self) -> list[str]:
        return [
            sid for sid, state in self._sessions.items()
            if state not in TERMINAL_STATES
        ]

    def get_recent_transitions(self, limit: int = 10) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._transitions[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": len(self.get_active_sessions()),
            "total_transitions": self._total_transitions,
            "invalid_transitions": self._invalid_transitions,
        }
