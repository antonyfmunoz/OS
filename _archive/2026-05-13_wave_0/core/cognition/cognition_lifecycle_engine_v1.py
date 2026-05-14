"""Cognition Lifecycle Engine v1.

9-state lifecycle for persistent operator cognition:
  initialized -> active -> focused -> checkpointed
                        -> suspended -> resumed -> active
                        -> stale -> archived (final)
                        -> terminated (final)

All transitions validated against VALID_COGNITION_TRANSITIONS.
Invalid transitions rejected. Lineage persisted to JSONL.

UMH substrate subsystem. Phase 96.8BT.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.cognition.persistent_operator_cognition_contracts_v1 import (
    CognitionPhase,
    OperatorMode,
    _new_id,
    _now_iso,
)


VALID_COGNITION_TRANSITIONS: dict[str, list[str]] = {
    "initialized": ["active", "terminated"],
    "active": ["focused", "checkpointed", "suspended", "stale", "archived", "terminated"],
    "focused": ["active", "checkpointed", "suspended", "stale", "archived", "terminated"],
    "checkpointed": ["active", "resumed", "terminated"],
    "suspended": ["resumed", "stale", "archived", "terminated"],
    "resumed": ["active", "focused", "terminated"],
    "stale": ["resumed", "archived", "terminated"],
    "archived": [],
    "terminated": [],
}

TERMINAL_STATES: set[str] = {"archived", "terminated"}


@dataclass
class CognitionLifecycleTransition:
    """A recorded cognition lifecycle transition."""

    transition_id: str = ""
    session_id: str = ""
    from_state: str = ""
    to_state: str = ""
    reason: str = ""
    operator_mode: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.transition_id:
            self.transition_id = _new_id("coglt")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "session_id": self.session_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "reason": self.reason,
            "operator_mode": self.operator_mode,
            "timestamp": self.timestamp,
        }


@dataclass
class CognitionSession:
    """Tracks a cognition session's lifecycle."""

    session_id: str = ""
    state: CognitionPhase = CognitionPhase.INITIALIZED
    operator_mode: OperatorMode = OperatorMode.FOCUSED_EXECUTION
    started_at: str = ""
    last_activity: str = ""
    transitions: int = 0

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = _new_id("cogsess")
        if not self.started_at:
            self.started_at = _now_iso()
        if not self.last_activity:
            self.last_activity = self.started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "operator_mode": self.operator_mode.value,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
            "transitions": self.transitions,
        }


class CognitionLifecycleEngine:
    """Manages cognition lifecycle state transitions.

    All transitions validated. Invalid transitions rejected.
    Lineage persisted to JSONL.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/cognition_lifecycle",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, CognitionSession] = {}
        self._transitions: list[CognitionLifecycleTransition] = []
        self._total_transitions: int = 0
        self._invalid_transitions: int = 0

    def register_session(
        self,
        session_id: str = "",
        operator_mode: OperatorMode = OperatorMode.FOCUSED_EXECUTION,
    ) -> CognitionSession:
        """Register a new cognition session."""
        session = CognitionSession(
            session_id=session_id or _new_id("cogsess"),
            operator_mode=operator_mode,
        )
        self._sessions[session.session_id] = session
        return session

    def transition(
        self,
        session_id: str,
        to_state: CognitionPhase,
        reason: str = "",
    ) -> bool:
        """Transition a session to a new state."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        from_state = session.state.value
        valid_targets = VALID_COGNITION_TRANSITIONS.get(from_state, [])

        if to_state.value not in valid_targets:
            self._invalid_transitions += 1
            return False

        trans = CognitionLifecycleTransition(
            session_id=session_id,
            from_state=from_state,
            to_state=to_state.value,
            reason=reason,
            operator_mode=session.operator_mode.value,
        )

        session.state = to_state
        session.last_activity = _now_iso()
        session.transitions += 1
        self._transitions.append(trans)
        self._total_transitions += 1

        path = self._state_dir / "cognition_lifecycle_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(trans.to_dict(), default=str) + "\n")

        return True

    def get_session(self, session_id: str) -> CognitionSession | None:
        return self._sessions.get(session_id)

    def get_state(self, session_id: str) -> CognitionPhase | None:
        session = self._sessions.get(session_id)
        return session.state if session else None

    def is_terminal(self, session_id: str) -> bool:
        """Check if a session is in a terminal state."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        return session.state.value in TERMINAL_STATES

    def get_active_sessions(self) -> list[CognitionSession]:
        """Get all sessions in non-terminal states."""
        return [
            s for s in self._sessions.values()
            if s.state.value not in TERMINAL_STATES
        ]

    def get_archived_sessions(self) -> list[CognitionSession]:
        return [
            s for s in self._sessions.values()
            if s.state == CognitionPhase.ARCHIVED
        ]

    def get_recent_transitions(self, limit: int = 10) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._transitions[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": len(self.get_active_sessions()),
            "archived_sessions": len(self.get_archived_sessions()),
            "total_transitions": self._total_transitions,
            "invalid_transitions": self._invalid_transitions,
        }
