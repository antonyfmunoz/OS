"""Runtime Ingress Session Manager v1.

Tracks active ingress sessions across all surfaces.

Manages:
  - Active ingress sessions (Discord, CLI, API)
  - Operator continuity chains
  - Session chronology
  - Active workflow bindings
  - Session lifecycle transitions

Persists to data/runtime/ingress_sessions/.

UMH substrate subsystem. Phase 96.8BU.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.ingress.live_runtime_ingress_contracts_v1 import (
    IngressSessionState,
    IngressSource,
    RuntimeIngressSession,
    _new_id,
    _now_iso,
)


VALID_SESSION_TRANSITIONS: dict[str, list[str]] = {
    "initialized": ["authenticated", "terminated"],
    "authenticated": ["active", "terminated"],
    "active": ["suspended", "expired", "terminated"],
    "suspended": ["resumed", "expired", "terminated"],
    "resumed": ["active", "terminated"],
    "expired": ["terminated"],
    "terminated": [],
}


class RuntimeIngressSessionManager:
    """Manages ingress sessions across all surfaces."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/ingress_sessions",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, RuntimeIngressSession] = {}
        self._total_created: int = 0
        self._total_transitions: int = 0
        self._invalid_transitions: int = 0

    def create_session(
        self,
        source: IngressSource,
        operator_id: str = "",
        cognition_session_id: str = "",
    ) -> RuntimeIngressSession:
        """Create a new ingress session."""
        session = RuntimeIngressSession(
            source=source,
            operator_id=operator_id,
            cognition_session_id=cognition_session_id,
        )
        self._sessions[session.session_id] = session
        self._total_created += 1
        self._persist_event("session_created", session)
        return session

    def get_session(self, session_id: str) -> RuntimeIngressSession | None:
        return self._sessions.get(session_id)

    def get_or_create_session(
        self,
        source: IngressSource,
        operator_id: str = "",
        cognition_session_id: str = "",
    ) -> RuntimeIngressSession:
        """Find an active session for operator+source, or create one."""
        for sess in self._sessions.values():
            if (
                sess.source == source
                and sess.operator_id == operator_id
                and sess.state in (
                    IngressSessionState.ACTIVE,
                    IngressSessionState.AUTHENTICATED,
                    IngressSessionState.INITIALIZED,
                )
            ):
                return sess
        return self.create_session(source, operator_id, cognition_session_id)

    def transition(
        self,
        session_id: str,
        to_state: IngressSessionState,
    ) -> bool:
        """Transition a session to a new state."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        valid = VALID_SESSION_TRANSITIONS.get(session.state.value, [])
        if to_state.value not in valid:
            self._invalid_transitions += 1
            return False

        session.state = to_state
        session.last_activity = _now_iso()
        self._total_transitions += 1
        self._persist_event(
            f"session_transition:{to_state.value}", session,
        )
        return True

    def record_signal(self, session_id: str) -> None:
        """Record that a signal was processed in this session."""
        session = self._sessions.get(session_id)
        if session:
            session.signals_processed += 1
            session.last_activity = _now_iso()

    def bind_workflow(self, session_id: str, workflow_id: str) -> None:
        """Bind a workflow to this session."""
        session = self._sessions.get(session_id)
        if session and workflow_id not in session.active_workflow_ids:
            session.active_workflow_ids.append(workflow_id)

    def add_continuity_chain(self, session_id: str, chain_id: str) -> None:
        """Add a continuity chain ID to this session."""
        session = self._sessions.get(session_id)
        if session and chain_id not in session.continuity_chain_ids:
            session.continuity_chain_ids.append(chain_id)

    def get_active_sessions(self) -> list[RuntimeIngressSession]:
        active_states = {
            IngressSessionState.INITIALIZED,
            IngressSessionState.AUTHENTICATED,
            IngressSessionState.ACTIVE,
            IngressSessionState.RESUMED,
        }
        return [s for s in self._sessions.values() if s.state in active_states]

    def get_sessions_by_source(
        self, source: IngressSource,
    ) -> list[RuntimeIngressSession]:
        return [s for s in self._sessions.values() if s.source == source]

    def get_sessions_by_operator(
        self, operator_id: str,
    ) -> list[RuntimeIngressSession]:
        return [s for s in self._sessions.values() if s.operator_id == operator_id]

    def _persist_event(
        self, event_type: str, session: RuntimeIngressSession,
    ) -> None:
        record = {
            "event_type": event_type,
            "session_id": session.session_id,
            "source": session.source.value,
            "operator_id": session.operator_id,
            "state": session.state.value,
            "timestamp": _now_iso(),
        }
        path = self._state_dir / "ingress_session_events.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_created": self._total_created,
            "total_transitions": self._total_transitions,
            "invalid_transitions": self._invalid_transitions,
            "active_sessions": len(self.get_active_sessions()),
            "total_sessions": len(self._sessions),
        }
