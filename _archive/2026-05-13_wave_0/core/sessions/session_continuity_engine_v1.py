"""Session Continuity Engine v1.

Unifies continuity across all substrate layers within
a substrate session:
  cognition, workflow, embodiment, ingress, lifecycle

Preserves:
  active runtime state, chronology, workflow state,
  cognition state, embodiment state, ingress state

Persist to: data/runtime/substrate_sessions/

UMH substrate subsystem. Phase 96.8BV.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.sessions.persistent_substrate_session_contracts_v1 import (
    SessionCognitionState,
    SessionContinuityState,
    SessionEmbodimentState,
    SessionIngressState,
    SessionLifecycleState,
    SessionWorkflowState,
    _content_hash,
    _new_id,
    _now_iso,
)


class SessionContinuityEngine:
    """Unifies continuity state across all substrate layers.

    Captures, persists, and restores the full operational
    state of a substrate session. Cannot execute — only
    captures and provides state.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/substrate_sessions",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._states: dict[str, SessionContinuityState] = {}
        self._total_captures: int = 0
        self._total_restorations: int = 0

    def capture(
        self,
        session_id: str,
        cognition: SessionCognitionState | None = None,
        workflow: SessionWorkflowState | None = None,
        embodiment: SessionEmbodimentState | None = None,
        ingress: SessionIngressState | None = None,
        lifecycle: SessionLifecycleState | None = None,
        previous_session_id: str = "",
        continuity_chain: list[str] | None = None,
    ) -> SessionContinuityState:
        """Capture unified continuity state for a session."""
        state = SessionContinuityState(
            session_id=session_id,
            cognition=cognition,
            workflow=workflow,
            embodiment=embodiment,
            ingress=ingress,
            lifecycle=lifecycle,
            previous_session_id=previous_session_id,
            continuity_chain=continuity_chain or [],
        )

        self._states[session_id] = state
        self._total_captures += 1

        path = self._state_dir / "session_continuity.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(state.to_dict(), default=str) + "\n")

        return state

    def update_cognition(
        self, session_id: str, cognition: SessionCognitionState,
    ) -> SessionContinuityState | None:
        state = self._states.get(session_id)
        if not state:
            return None
        state.cognition = cognition
        state.content_hash = _content_hash(state._hashable())
        return state

    def update_workflow(
        self, session_id: str, workflow: SessionWorkflowState,
    ) -> SessionContinuityState | None:
        state = self._states.get(session_id)
        if not state:
            return None
        state.workflow = workflow
        state.content_hash = _content_hash(state._hashable())
        return state

    def update_embodiment(
        self, session_id: str, embodiment: SessionEmbodimentState,
    ) -> SessionContinuityState | None:
        state = self._states.get(session_id)
        if not state:
            return None
        state.embodiment = embodiment
        state.content_hash = _content_hash(state._hashable())
        return state

    def update_ingress(
        self, session_id: str, ingress: SessionIngressState,
    ) -> SessionContinuityState | None:
        state = self._states.get(session_id)
        if not state:
            return None
        state.ingress = ingress
        state.content_hash = _content_hash(state._hashable())
        return state

    def update_lifecycle(
        self, session_id: str, lifecycle: SessionLifecycleState,
    ) -> SessionContinuityState | None:
        state = self._states.get(session_id)
        if not state:
            return None
        state.lifecycle = lifecycle
        state.content_hash = _content_hash(state._hashable())
        return state

    def get_state(self, session_id: str) -> SessionContinuityState | None:
        return self._states.get(session_id)

    def restore(
        self, session_id: str, state: SessionContinuityState,
    ) -> SessionContinuityState:
        """Restore continuity state into a session."""
        self._states[session_id] = state
        self._total_restorations += 1
        return state

    def build_resume_packet(
        self, session_id: str,
    ) -> dict[str, Any]:
        """Build a resume packet from current continuity state."""
        state = self._states.get(session_id)
        if not state:
            return {"session_id": session_id, "available": False}

        return {
            "session_id": session_id,
            "available": True,
            "continuity": state.to_dict(),
            "content_hash": state.content_hash,
            "timestamp": _now_iso(),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "tracked_sessions": len(self._states),
            "total_captures": self._total_captures,
            "total_restorations": self._total_restorations,
        }
