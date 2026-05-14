"""Canonical Substrate Session Manager v1.

Single canonical session manager for all substrate sessions.
Composes lifecycle, chronology, continuity, checkpoint, and
observability into a unified session interface.

The session manager:
  - creates sessions
  - restores sessions
  - checkpoints sessions
  - suspends sessions
  - resumes sessions
  - terminates sessions
  - archives sessions

The session manager CANNOT execute workflows directly.
The operator still owns intentionality.

UMH substrate subsystem. Phase 96.8BV.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.sessions.persistent_substrate_session_contracts_v1 import (
    CheckpointType,
    ChronologyEventKind,
    SessionCognitionState,
    SessionContinuityState,
    SessionEmbodimentState,
    SessionIngressState,
    SessionLifecycleState,
    SessionLineageReceipt,
    SessionState,
    SessionWorkflowState,
    SubstrateSession,
    _content_hash,
    _new_id,
    _now_iso,
)
from core.sessions.session_checkpoint_engine_v1 import SessionCheckpointEngine
from core.sessions.session_chronology_engine_v1 import SessionChronologyEngine
from core.sessions.session_continuity_engine_v1 import SessionContinuityEngine
from core.sessions.session_lifecycle_engine_v1 import SessionLifecycleEngine


class CanonicalSubstrateSessionManager:
    """Single canonical session manager for substrate sessions.

    Composes lifecycle, chronology, continuity, and checkpoint
    engines into a unified session interface. Cannot execute
    workflows — only manages session state.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/substrate_sessions",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._lifecycle = SessionLifecycleEngine(state_dir=self._state_dir)
        self._chronology = SessionChronologyEngine(state_dir=self._state_dir)
        self._continuity = SessionContinuityEngine(state_dir=self._state_dir)
        self._checkpoints = SessionCheckpointEngine(state_dir=self._state_dir)

        self._sessions: dict[str, SubstrateSession] = {}
        self._operator_sessions: dict[str, list[str]] = {}
        self._receipts: list[SessionLineageReceipt] = []

    def create_session(
        self,
        operator_id: str = "",
        previous_session_id: str = "",
    ) -> SubstrateSession:
        """Create a new substrate session."""
        session = SubstrateSession(
            operator_id=operator_id,
            previous_session_id=previous_session_id,
        )
        sid = session.session_id

        lifecycle = SessionLifecycleState(
            session_id=sid,
            state=SessionState.INITIALIZED.value,
        )
        session.lifecycle = lifecycle

        self._lifecycle.register(sid)
        self._lifecycle.transition(sid, SessionState.ACTIVE, reason="session_created")

        lifecycle.state = SessionState.ACTIVE.value
        lifecycle.previous_state = SessionState.INITIALIZED.value
        lifecycle.transitions = 1

        self._continuity.capture(
            session_id=sid,
            lifecycle=lifecycle,
            previous_session_id=previous_session_id,
            continuity_chain=[previous_session_id] if previous_session_id else [],
        )

        self._chronology.record_session_creation(sid, operator_id)

        self._sessions[sid] = session

        if operator_id:
            if operator_id not in self._operator_sessions:
                self._operator_sessions[operator_id] = []
            self._operator_sessions[operator_id].append(sid)

        self._emit_receipt(sid, "create", "", SessionState.ACTIVE.value)

        session.last_activity = _now_iso()
        return session

    def restore_session(
        self,
        session_id: str,
        checkpoint_id: str = "",
    ) -> SubstrateSession | None:
        """Restore a session from a checkpoint."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        checkpoint = None
        if checkpoint_id:
            checkpoint = self._checkpoints.get_checkpoint_by_id(checkpoint_id)
        else:
            checkpoint = self._checkpoints.get_latest_checkpoint(session_id)

        if checkpoint and checkpoint.continuity_state:
            self._continuity.restore(session_id, checkpoint.continuity_state)
            session.continuity = checkpoint.continuity_state

        current_state = self._lifecycle.get_state(session_id)
        if current_state == SessionState.SUSPENDED.value:
            self._lifecycle.transition(session_id, SessionState.RESUMED)
            self._lifecycle.transition(session_id, SessionState.ACTIVE)
        elif current_state == SessionState.CHECKPOINTED.value:
            self._lifecycle.transition(session_id, SessionState.ACTIVE)

        if session.lifecycle:
            session.lifecycle.state = SessionState.ACTIVE.value
            session.lifecycle.transitions += 1

        self._chronology.record_continuity_restoration(
            session_id,
            previous_session_id=session.previous_session_id,
        )

        self._emit_receipt(
            session_id, "restore", current_state or "",
            SessionState.ACTIVE.value,
            checkpoint_id=checkpoint.checkpoint_id if checkpoint else "",
        )

        session.last_activity = _now_iso()
        return session

    def checkpoint_session(
        self,
        session_id: str,
        checkpoint_type: CheckpointType = CheckpointType.RESUMABLE,
    ) -> dict[str, Any] | None:
        """Create a checkpoint for a session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        continuity_state = self._continuity.get_state(session_id)
        if not continuity_state:
            continuity_state = SessionContinuityState(session_id=session_id)

        chronology_snapshot = self._chronology.get_chronology_snapshot(session_id)

        checkpoint = self._checkpoints.create_checkpoint(
            session_id=session_id,
            continuity_state=continuity_state,
            chronology_snapshot=chronology_snapshot,
            checkpoint_type=checkpoint_type,
        )

        current_state = self._lifecycle.get_state(session_id)
        if current_state == SessionState.ACTIVE.value:
            self._lifecycle.transition(session_id, SessionState.CHECKPOINTED)
            if session.lifecycle:
                session.lifecycle.state = SessionState.CHECKPOINTED.value
                session.lifecycle.transitions += 1

        session.checkpoint_count += 1

        self._emit_receipt(
            session_id, "checkpoint", current_state or "",
            SessionState.CHECKPOINTED.value,
            checkpoint_id=checkpoint.checkpoint_id,
        )

        session.last_activity = _now_iso()
        return checkpoint.to_dict()

    def suspend_session(
        self,
        session_id: str,
        reason: str = "",
    ) -> bool:
        """Suspend a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        current_state = self._lifecycle.get_state(session_id)

        if current_state == SessionState.CHECKPOINTED.value:
            ok = self._lifecycle.transition(session_id, SessionState.SUSPENDED, reason)
        elif current_state == SessionState.ACTIVE.value:
            self._lifecycle.transition(session_id, SessionState.CHECKPOINTED)
            ok = self._lifecycle.transition(session_id, SessionState.SUSPENDED, reason)
        else:
            ok = self._lifecycle.transition(session_id, SessionState.SUSPENDED, reason)

        if not ok:
            return False

        if session.lifecycle:
            session.lifecycle.state = SessionState.SUSPENDED.value
            session.lifecycle.transitions += 1

        self._emit_receipt(
            session_id, "suspend", current_state or "",
            SessionState.SUSPENDED.value,
        )

        session.last_activity = _now_iso()
        return True

    def resume_session(
        self,
        session_id: str,
        operator_id: str = "",
    ) -> SubstrateSession | None:
        """Resume a suspended session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        current_state = self._lifecycle.get_state(session_id)

        ok = self._lifecycle.transition(session_id, SessionState.RESUMED)
        if not ok:
            return None

        self._lifecycle.transition(session_id, SessionState.ACTIVE)

        if session.lifecycle:
            session.lifecycle.state = SessionState.ACTIVE.value
            session.lifecycle.transitions += 1

        self._chronology.record_operator_resumption(session_id, operator_id)

        self._emit_receipt(
            session_id, "resume", current_state or "",
            SessionState.ACTIVE.value,
        )

        session.last_activity = _now_iso()
        return session

    def terminate_session(
        self,
        session_id: str,
        reason: str = "",
    ) -> bool:
        """Terminate a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        current_state = self._lifecycle.get_state(session_id)
        ok = self._lifecycle.transition(session_id, SessionState.TERMINATED, reason)
        if not ok:
            return False

        if session.lifecycle:
            session.lifecycle.state = SessionState.TERMINATED.value
            session.lifecycle.transitions += 1

        self._emit_receipt(
            session_id, "terminate", current_state or "",
            SessionState.TERMINATED.value,
        )

        session.last_activity = _now_iso()
        return True

    def archive_session(
        self,
        session_id: str,
        reason: str = "",
    ) -> bool:
        """Archive an active session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        current_state = self._lifecycle.get_state(session_id)
        ok = self._lifecycle.transition(session_id, SessionState.ARCHIVED, reason)
        if not ok:
            return False

        if session.lifecycle:
            session.lifecycle.state = SessionState.ARCHIVED.value
            session.lifecycle.transitions += 1

        self._emit_receipt(
            session_id, "archive", current_state or "",
            SessionState.ARCHIVED.value,
        )

        session.last_activity = _now_iso()
        return True

    def update_cognition(
        self, session_id: str, cognition: SessionCognitionState,
    ) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.cognition = cognition
        self._continuity.update_cognition(session_id, cognition)
        self._chronology.record_cognition_transition(
            session_id,
            from_phase=session.cognition.cognition_phase if session.cognition else "",
            to_phase=cognition.cognition_phase,
        )
        session.last_activity = _now_iso()
        return True

    def update_workflow(
        self, session_id: str, workflow: SessionWorkflowState,
    ) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.workflow = workflow
        self._continuity.update_workflow(session_id, workflow)
        self._chronology.record_workflow_transition(session_id)
        session.last_activity = _now_iso()
        return True

    def update_embodiment(
        self, session_id: str, embodiment: SessionEmbodimentState,
    ) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.embodiment = embodiment
        self._continuity.update_embodiment(session_id, embodiment)
        self._chronology.record_embodiment_transition(session_id)
        session.last_activity = _now_iso()
        return True

    def update_ingress(
        self, session_id: str, ingress: SessionIngressState,
    ) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.ingress = ingress
        self._continuity.update_ingress(session_id, ingress)
        self._chronology.record_ingress_transition(session_id)
        session.last_activity = _now_iso()
        return True

    def get_session(self, session_id: str) -> SubstrateSession | None:
        return self._sessions.get(session_id)

    def get_operator_sessions(self, operator_id: str) -> list[str]:
        return list(self._operator_sessions.get(operator_id, []))

    def get_active_sessions(self) -> list[str]:
        return self._lifecycle.get_active_sessions()

    def get_session_chronology(
        self, session_id: str, limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self._chronology.get_chronology(session_id, limit)

    def get_session_checkpoints(
        self, session_id: str,
    ) -> list[dict[str, Any]]:
        return self._checkpoints.get_checkpoints(session_id)

    def get_continuity_state(
        self, session_id: str,
    ) -> SessionContinuityState | None:
        return self._continuity.get_state(session_id)

    def get_resume_packet(
        self, session_id: str,
    ) -> dict[str, Any]:
        return self._continuity.build_resume_packet(session_id)

    def get_recent_receipts(self, limit: int = 10) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._receipts[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": len(self.get_active_sessions()),
            "total_operators": len(self._operator_sessions),
            "lifecycle": self._lifecycle.get_stats(),
            "chronology": self._chronology.get_stats(),
            "continuity": self._continuity.get_stats(),
            "checkpoints": self._checkpoints.get_stats(),
        }

    def _emit_receipt(
        self,
        session_id: str,
        operation: str,
        from_state: str,
        to_state: str,
        checkpoint_id: str = "",
    ) -> SessionLineageReceipt:
        receipt = SessionLineageReceipt(
            session_id=session_id,
            operation=operation,
            from_state=from_state,
            to_state=to_state,
            checkpoint_id=checkpoint_id,
        )
        self._receipts.append(receipt)

        path = self._state_dir / "session_receipts.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(receipt.to_dict(), default=str) + "\n")

        return receipt
