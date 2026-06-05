"""Continuity state machine — unified lifecycle for operator presence/absence.

Composes the 4 existing mode systems (OperatorMode, OperatorDayMode,
StationPresenceMode, OperationalMode) into a single continuity lifecycle
without replacing any of them. Each transition records source metadata,
reason, timestamp, and active context.

Phase 14.11B. Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ContinuityState(str, Enum):
    """Unified continuity lifecycle states.

    ACTIVE           — operator present, actively working
    IDLE             — operator present but no recent interaction
    AWAY             — operator left the workstation
    REMOTE           — operator working from a remote device
    NIGHT_SLEEPING   — day closed, system in overnight autonomous mode
    EXTENDED_ABSENCE — multi-day absence or vacation
    RETURNING        — operator returning, system preparing resume brief
    RESUME_BRIEF     — presenting what happened during absence
    """

    ACTIVE = "active"
    IDLE = "idle"
    AWAY = "away"
    REMOTE = "remote"
    NIGHT_SLEEPING = "night_sleeping"
    EXTENDED_ABSENCE = "extended_absence"
    RETURNING = "returning"
    RESUME_BRIEF = "resume_brief"


_VALID_TRANSITIONS: dict[ContinuityState, frozenset[ContinuityState]] = {
    ContinuityState.ACTIVE: frozenset({
        ContinuityState.IDLE,
        ContinuityState.AWAY,
        ContinuityState.REMOTE,
        ContinuityState.NIGHT_SLEEPING,
        ContinuityState.EXTENDED_ABSENCE,
    }),
    ContinuityState.IDLE: frozenset({
        ContinuityState.ACTIVE,
        ContinuityState.AWAY,
        ContinuityState.NIGHT_SLEEPING,
        ContinuityState.EXTENDED_ABSENCE,
    }),
    ContinuityState.AWAY: frozenset({
        ContinuityState.RETURNING,
        ContinuityState.REMOTE,
        ContinuityState.NIGHT_SLEEPING,
        ContinuityState.EXTENDED_ABSENCE,
    }),
    ContinuityState.REMOTE: frozenset({
        ContinuityState.ACTIVE,
        ContinuityState.AWAY,
        ContinuityState.NIGHT_SLEEPING,
    }),
    ContinuityState.NIGHT_SLEEPING: frozenset({
        ContinuityState.RETURNING,
        ContinuityState.EXTENDED_ABSENCE,
    }),
    ContinuityState.EXTENDED_ABSENCE: frozenset({
        ContinuityState.RETURNING,
    }),
    ContinuityState.RETURNING: frozenset({
        ContinuityState.RESUME_BRIEF,
        ContinuityState.ACTIVE,
    }),
    ContinuityState.RESUME_BRIEF: frozenset({
        ContinuityState.ACTIVE,
        ContinuityState.REMOTE,
    }),
}


@dataclass
class ContinuityTransition:
    """Record of a single continuity state transition."""

    transition_id: str = ""
    from_state: str = ""
    to_state: str = ""
    reason: str = ""
    timestamp: str = ""
    active_node: str = ""
    active_environment: str = ""
    active_work_packet_id: str = ""
    active_session_id: str = ""
    pending_approvals_count: int = 0
    safe_work_constraints: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.transition_id:
            self.transition_id = f"ct_{uuid.uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContinuityStateMachine:
    """Unified continuity state machine.

    Manages transitions between continuity states with validation,
    audit trail, and context preservation. Does not replace the 4
    existing mode systems — reads from them as inputs to determine
    recommended transitions.
    """

    def __init__(self, initial_state: ContinuityState = ContinuityState.ACTIVE) -> None:
        self._current = initial_state
        self._history: list[ContinuityTransition] = []

    @property
    def current_state(self) -> ContinuityState:
        return self._current

    @property
    def history(self) -> list[ContinuityTransition]:
        return list(self._history)

    def can_transition(self, target: ContinuityState) -> bool:
        """Check if transition to target is valid from current state."""
        allowed = _VALID_TRANSITIONS.get(self._current, frozenset())
        return target in allowed

    def valid_transitions(self) -> list[ContinuityState]:
        """Return all states reachable from the current state."""
        return sorted(_VALID_TRANSITIONS.get(self._current, frozenset()), key=lambda s: s.value)

    def transition(
        self,
        target: ContinuityState,
        reason: str = "",
        active_node: str = "",
        active_environment: str = "",
        active_work_packet_id: str = "",
        active_session_id: str = "",
        pending_approvals_count: int = 0,
        safe_work_constraints: dict[str, Any] | None = None,
    ) -> ContinuityTransition:
        """Execute a state transition.

        Raises ValueError if the transition is not valid.
        Returns the transition record.
        """
        if not self.can_transition(target):
            allowed = [s.value for s in self.valid_transitions()]
            raise ValueError(
                f"Invalid transition: {self._current.value} -> {target.value}. "
                f"Allowed from {self._current.value}: {allowed}"
            )

        record = ContinuityTransition(
            from_state=self._current.value,
            to_state=target.value,
            reason=reason,
            active_node=active_node,
            active_environment=active_environment,
            active_work_packet_id=active_work_packet_id,
            active_session_id=active_session_id,
            pending_approvals_count=pending_approvals_count,
            safe_work_constraints=safe_work_constraints or {},
        )

        logger.info(
            "Continuity transition: %s -> %s (reason: %s)",
            self._current.value, target.value, reason,
        )

        self._current = target
        self._history.append(record)
        return record

    def last_transition(self) -> ContinuityTransition | None:
        """Return the most recent transition, or None."""
        return self._history[-1] if self._history else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_state": self._current.value,
            "history": [t.to_dict() for t in self._history],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContinuityStateMachine:
        """Restore from serialized form."""
        state_val = data.get("current_state", "active")
        try:
            initial = ContinuityState(state_val)
        except ValueError:
            initial = ContinuityState.ACTIVE

        machine = cls(initial_state=initial)
        for h in data.get("history", []):
            machine._history.append(ContinuityTransition(**{
                k: v for k, v in h.items()
                if k in ContinuityTransition.__dataclass_fields__
            }))
        return machine
