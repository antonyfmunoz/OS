"""Runtime Lifecycle Engine v1.

Manages the lifecycle of the live substrate runtime:
  - initialize → active → waiting → suspended → resumed → degraded → terminated

Tracks:
  - active runtime sessions
  - embodiment sessions
  - continuity sessions
  - runtime lineage

UMH substrate subsystem. Phase 96.8BR.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .live_runtime_contracts_v1 import (
    RuntimeLineageReceipt,
    RuntimePhase,
    _new_id,
    _now_iso,
)


class LifecycleState(str, Enum):
    INITIALIZE = "initialize"
    ACTIVE = "active"
    WAITING = "waiting"
    SUSPENDED = "suspended"
    RESUMED = "resumed"
    DEGRADED = "degraded"
    TERMINATED = "terminated"


VALID_TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.INITIALIZE: frozenset({LifecycleState.ACTIVE, LifecycleState.TERMINATED}),
    LifecycleState.ACTIVE: frozenset(
        {
            LifecycleState.WAITING,
            LifecycleState.SUSPENDED,
            LifecycleState.DEGRADED,
            LifecycleState.TERMINATED,
        }
    ),
    LifecycleState.WAITING: frozenset(
        {LifecycleState.ACTIVE, LifecycleState.SUSPENDED, LifecycleState.TERMINATED}
    ),
    LifecycleState.SUSPENDED: frozenset({LifecycleState.RESUMED, LifecycleState.TERMINATED}),
    LifecycleState.RESUMED: frozenset({LifecycleState.ACTIVE, LifecycleState.TERMINATED}),
    LifecycleState.DEGRADED: frozenset({LifecycleState.ACTIVE, LifecycleState.TERMINATED}),
    LifecycleState.TERMINATED: frozenset(),
}


@dataclass
class LifecycleTransition:
    """Record of a lifecycle state transition."""

    transition_id: str = ""
    from_state: LifecycleState = LifecycleState.INITIALIZE
    to_state: LifecycleState = LifecycleState.ACTIVE
    reason: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.transition_id:
            self.transition_id = _new_id("ltrans")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class RuntimeSession:
    """A tracked runtime session."""

    session_id: str = ""
    session_type: str = "runtime"
    state: LifecycleState = LifecycleState.INITIALIZE
    started_at: str = ""
    last_activity: str = ""
    events_count: int = 0

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = _new_id("rsess")
        if not self.started_at:
            self.started_at = _now_iso()
        if not self.last_activity:
            self.last_activity = self.started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_type": self.session_type,
            "state": self.state.value,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
            "events_count": self.events_count,
        }


class RuntimeLifecycleEngine:
    """Manages lifecycle state of the live substrate runtime."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/live_runtime_state",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state = LifecycleState.INITIALIZE
        self._transitions: list[LifecycleTransition] = []
        self._sessions: dict[str, RuntimeSession] = {}
        self._lineage_path = self._state_dir / "lifecycle_lineage.jsonl"

    @property
    def state(self) -> LifecycleState:
        return self._state

    def initialize(self, session_id: str = "") -> RuntimeSession:
        """Initialize the runtime and create the primary session."""
        session = RuntimeSession(
            session_id=session_id or _new_id("rsess"),
            session_type="runtime",
            state=LifecycleState.ACTIVE,
        )
        self._sessions[session.session_id] = session
        self._transition(LifecycleState.ACTIVE, "runtime_initialized")
        return session

    def transition(self, to_state: LifecycleState, reason: str = "") -> bool:
        """Attempt a lifecycle state transition."""
        return self._transition(to_state, reason)

    def register_session(
        self,
        session_type: str,
        session_id: str = "",
    ) -> RuntimeSession:
        """Register a subsystem session (embodiment, continuity, etc.)."""
        session = RuntimeSession(
            session_id=session_id or _new_id("rsess"),
            session_type=session_type,
            state=LifecycleState.ACTIVE,
        )
        self._sessions[session.session_id] = session
        return session

    def record_activity(self, session_id: str) -> None:
        """Record activity on a session."""
        session = self._sessions.get(session_id)
        if session:
            session.last_activity = _now_iso()
            session.events_count += 1

    def terminate_session(self, session_id: str) -> bool:
        """Terminate a specific session."""
        session = self._sessions.get(session_id)
        if session:
            session.state = LifecycleState.TERMINATED
            return True
        return False

    def get_active_sessions(self) -> list[RuntimeSession]:
        return [
            s
            for s in self._sessions.values()
            if s.state not in (LifecycleState.TERMINATED, LifecycleState.SUSPENDED)
        ]

    def get_session(self, session_id: str) -> RuntimeSession | None:
        return self._sessions.get(session_id)

    def get_transitions(self) -> list[LifecycleTransition]:
        return list(self._transitions)

    def get_stats(self) -> dict[str, Any]:
        active = sum(1 for s in self._sessions.values() if s.state == LifecycleState.ACTIVE)
        return {
            "current_state": self._state.value,
            "total_transitions": len(self._transitions),
            "total_sessions": len(self._sessions),
            "active_sessions": active,
        }

    def get_state_map(self) -> dict[str, Any]:
        """Get the full runtime state map for persistence."""
        return {
            "lifecycle_state": self._state.value,
            "transitions": [t.to_dict() for t in self._transitions],
            "sessions": {k: v.to_dict() for k, v in self._sessions.items()},
            "stats": self.get_stats(),
            "timestamp": _now_iso(),
        }

    def persist_state_map(self) -> None:
        """Persist the runtime state map to disk."""
        state_map = self.get_state_map()
        path = self._state_dir / "runtime_state_map.json"
        path.write_text(json.dumps(state_map, indent=2, default=str), encoding="utf-8")

    def _transition(self, to_state: LifecycleState, reason: str) -> bool:
        """Execute a validated lifecycle transition."""
        allowed = VALID_TRANSITIONS.get(self._state, frozenset())
        if to_state not in allowed:
            return False

        transition = LifecycleTransition(
            from_state=self._state,
            to_state=to_state,
            reason=reason,
        )
        self._transitions.append(transition)
        self._state = to_state

        self._append_lineage(transition)
        return True

    def _append_lineage(self, transition: LifecycleTransition) -> None:
        with open(self._lineage_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(transition.to_dict(), default=str) + "\n")
