"""Workflow Lifecycle Engine v1.

9-state lifecycle for operational workflows:
  initialized -> active -> checkpointed -> active
                        -> waiting -> resumed -> active
                        -> completed (final)
                        -> denied (final)
                        -> failed (final)
                        -> terminated (final)

All transitions validated against VALID_TRANSITIONS map.
Invalid transitions rejected.

UMH substrate subsystem. Phase 96.8BS.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.workflows.operational_workflow_contracts_v1 import (
    WorkflowPhase,
    _new_id,
    _now_iso,
)


VALID_TRANSITIONS: dict[str, list[str]] = {
    "initialized": ["active", "denied", "terminated"],
    "active": ["checkpointed", "waiting", "completed", "failed", "terminated"],
    "checkpointed": ["active", "resumed", "terminated"],
    "waiting": ["resumed", "active", "terminated"],
    "resumed": ["active", "terminated"],
    "completed": [],
    "denied": [],
    "failed": ["active", "terminated"],
    "terminated": [],
}


@dataclass
class WorkflowLifecycleTransition:
    """A recorded lifecycle transition."""

    transition_id: str = ""
    workflow_id: str = ""
    from_state: str = ""
    to_state: str = ""
    reason: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.transition_id:
            self.transition_id = _new_id("wlct")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "workflow_id": self.workflow_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class WorkflowSession:
    """Tracks an individual workflow session."""

    session_id: str = ""
    workflow_id: str = ""
    workflow_type: str = ""
    state: WorkflowPhase = WorkflowPhase.INITIALIZED
    started_at: str = ""
    last_activity: str = ""
    transitions: int = 0

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = _new_id("wlsess")
        if not self.started_at:
            self.started_at = _now_iso()
        if not self.last_activity:
            self.last_activity = self.started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "state": self.state.value,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
            "transitions": self.transitions,
        }


class WorkflowLifecycleEngine:
    """Manages workflow lifecycle state transitions.

    All transitions validated. Invalid transitions rejected.
    Lineage persisted to JSONL.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/workflow_lifecycle",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, WorkflowSession] = {}
        self._transitions: list[WorkflowLifecycleTransition] = []
        self._total_transitions: int = 0
        self._invalid_transitions: int = 0

    def register_workflow(
        self,
        workflow_id: str,
        workflow_type: str = "",
    ) -> WorkflowSession:
        """Register a new workflow and create its session."""
        session = WorkflowSession(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
        )
        self._sessions[workflow_id] = session
        return session

    def transition(
        self,
        workflow_id: str,
        to_state: WorkflowPhase,
        reason: str = "",
    ) -> bool:
        """Transition a workflow to a new state."""
        session = self._sessions.get(workflow_id)
        if not session:
            return False

        from_state = session.state.value
        valid_targets = VALID_TRANSITIONS.get(from_state, [])

        if to_state.value not in valid_targets:
            self._invalid_transitions += 1
            return False

        transition = WorkflowLifecycleTransition(
            workflow_id=workflow_id,
            from_state=from_state,
            to_state=to_state.value,
            reason=reason,
        )

        session.state = to_state
        session.last_activity = _now_iso()
        session.transitions += 1
        self._transitions.append(transition)
        self._total_transitions += 1

        lineage_path = self._state_dir / "workflow_lifecycle_lineage.jsonl"
        with lineage_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(transition.to_dict(), default=str) + "\n")

        return True

    def get_session(self, workflow_id: str) -> WorkflowSession | None:
        """Get a workflow session."""
        return self._sessions.get(workflow_id)

    def get_state(self, workflow_id: str) -> WorkflowPhase | None:
        """Get current state of a workflow."""
        session = self._sessions.get(workflow_id)
        return session.state if session else None

    def get_active_workflows(self) -> list[WorkflowSession]:
        """Get all workflows in active-like states."""
        active_states = {
            WorkflowPhase.INITIALIZED,
            WorkflowPhase.ACTIVE,
            WorkflowPhase.CHECKPOINTED,
            WorkflowPhase.WAITING,
            WorkflowPhase.RESUMED,
        }
        return [s for s in self._sessions.values() if s.state in active_states]

    def get_completed_workflows(self) -> list[WorkflowSession]:
        """Get all completed workflows."""
        return [s for s in self._sessions.values() if s.state == WorkflowPhase.COMPLETED]

    def get_recent_transitions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent lifecycle transitions."""
        return [t.to_dict() for t in self._transitions[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_sessions": len(self._sessions),
            "active_workflows": len(self.get_active_workflows()),
            "completed_workflows": len(self.get_completed_workflows()),
            "total_transitions": self._total_transitions,
            "invalid_transitions": self._invalid_transitions,
        }
