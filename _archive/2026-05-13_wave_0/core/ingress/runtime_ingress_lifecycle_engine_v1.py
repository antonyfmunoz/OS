"""Runtime Ingress Lifecycle Engine v1.

7-state lifecycle for ingress sessions:
  initialized -> authenticated -> active -> suspended
                                         -> expired -> terminated
                               -> resumed -> active
  terminated (final)

All transitions validated. Lineage persisted to JSONL.

UMH substrate subsystem. Phase 96.8BU.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.ingress.live_runtime_ingress_contracts_v1 import (
    IngressSessionState,
    IngressSource,
    _new_id,
    _now_iso,
)


VALID_INGRESS_TRANSITIONS: dict[str, list[str]] = {
    "initialized": ["authenticated", "terminated"],
    "authenticated": ["active", "terminated"],
    "active": ["suspended", "expired", "terminated"],
    "suspended": ["resumed", "expired", "terminated"],
    "resumed": ["active", "terminated"],
    "expired": ["terminated"],
    "terminated": [],
}

TERMINAL_STATES: set[str] = {"terminated"}


@dataclass
class IngressLifecycleTransition:
    """A recorded ingress lifecycle transition."""

    transition_id: str = ""
    session_id: str = ""
    from_state: str = ""
    to_state: str = ""
    reason: str = ""
    source: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.transition_id:
            self.transition_id = _new_id("inglt")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "session_id": self.session_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "reason": self.reason,
            "source": self.source,
            "timestamp": self.timestamp,
        }


class RuntimeIngressLifecycleEngine:
    """Manages ingress session lifecycle transitions.

    All transitions validated. Invalid transitions rejected.
    Lineage persisted to JSONL.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/ingress_lifecycle",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, dict[str, Any]] = {}
        self._transitions: list[IngressLifecycleTransition] = []
        self._total_transitions: int = 0
        self._invalid_transitions: int = 0

    def register_session(
        self,
        session_id: str,
        source: IngressSource = IngressSource.DISCORD,
    ) -> dict[str, Any]:
        """Register a new ingress session."""
        session = {
            "session_id": session_id,
            "source": source.value,
            "state": IngressSessionState.INITIALIZED.value,
            "started_at": _now_iso(),
            "last_activity": _now_iso(),
            "transitions": 0,
        }
        self._sessions[session_id] = session
        return session

    def transition(
        self,
        session_id: str,
        to_state: IngressSessionState,
        reason: str = "",
    ) -> bool:
        """Transition a session to a new state."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        from_state = session["state"]
        valid = VALID_INGRESS_TRANSITIONS.get(from_state, [])

        if to_state.value not in valid:
            self._invalid_transitions += 1
            return False

        trans = IngressLifecycleTransition(
            session_id=session_id,
            from_state=from_state,
            to_state=to_state.value,
            reason=reason,
            source=session.get("source", ""),
        )

        session["state"] = to_state.value
        session["last_activity"] = _now_iso()
        session["transitions"] += 1
        self._transitions.append(trans)
        self._total_transitions += 1

        path = self._state_dir / "ingress_lifecycle_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(trans.to_dict(), default=str) + "\n")

        return True

    def get_state(self, session_id: str) -> str | None:
        session = self._sessions.get(session_id)
        return session["state"] if session else None

    def is_terminal(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        return session["state"] in TERMINAL_STATES if session else False

    def get_active_sessions(self) -> list[dict[str, Any]]:
        return [
            s for s in self._sessions.values()
            if s["state"] not in TERMINAL_STATES
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
