"""Goal state — persistent active objective tracking across ticks.

Maintains the currently committed objective, its start tick, progress,
and commitment score. GoalStateManager provides explicit get/set/update
semantics — no hidden mutation.

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.runtime.arbitration import Objective


_DEFAULT_PROGRESS = 0.0
_MAX_PROGRESS = 1.0
_MIN_PROGRESS = 0.0
_DEFAULT_COMMITMENT = 0.5


@dataclass(frozen=True)
class GoalState:
    """Immutable snapshot of the currently active objective."""

    active_objective: Objective
    start_tick: int
    progress: float
    commitment_score: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "progress",
            max(_MIN_PROGRESS, min(_MAX_PROGRESS, self.progress)),
        )
        object.__setattr__(
            self,
            "commitment_score",
            max(0.0, min(1.0, self.commitment_score)),
        )

    @property
    def objective_id(self) -> str:
        return self.active_objective.objective_id

    @property
    def ticks_invested(self) -> int:
        return 0

    def elapsed_ticks(self, current_tick: int) -> int:
        return max(0, current_tick - self.start_tick)

    def with_progress(self, new_progress: float) -> GoalState:
        """Return a new GoalState with updated progress."""
        return GoalState(
            active_objective=self.active_objective,
            start_tick=self.start_tick,
            progress=new_progress,
            commitment_score=self.commitment_score,
        )

    def with_commitment(self, new_commitment: float) -> GoalState:
        """Return a new GoalState with updated commitment score."""
        return GoalState(
            active_objective=self.active_objective,
            start_tick=self.start_tick,
            progress=self.progress,
            commitment_score=new_commitment,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "objective": self.active_objective.to_dict(),
            "start_tick": self.start_tick,
            "progress": round(self.progress, 4),
            "commitment_score": round(self.commitment_score, 4),
        }


class GoalStateManager:
    """Manages the persistent active objective state.

    Provides explicit get/set/update/clear. No hidden mutation —
    every state change goes through a named method.
    """

    def __init__(self) -> None:
        self._active: GoalState | None = None
        self._history: list[GoalState] = []

    @property
    def active(self) -> GoalState | None:
        return self._active

    @property
    def has_active(self) -> bool:
        return self._active is not None

    @property
    def history_count(self) -> int:
        return len(self._history)

    def get_active(self) -> GoalState | None:
        """Return the current active goal state, or None."""
        return self._active

    def set_active(
        self,
        objective: Objective,
        start_tick: int,
        *,
        commitment_score: float = _DEFAULT_COMMITMENT,
    ) -> GoalState:
        """Set a new active objective. Archives the previous one if any."""
        if self._active is not None:
            self._history.append(self._active)

        state = GoalState(
            active_objective=objective,
            start_tick=start_tick,
            progress=_DEFAULT_PROGRESS,
            commitment_score=commitment_score,
        )
        self._active = state
        return state

    def update_progress(self, new_progress: float) -> GoalState | None:
        """Explicitly update progress on the active goal.

        Returns the new state, or None if no active goal.
        """
        if self._active is None:
            return None
        self._active = self._active.with_progress(new_progress)
        return self._active

    def update_commitment(self, new_commitment: float) -> GoalState | None:
        """Explicitly update commitment score on the active goal.

        Returns the new state, or None if no active goal.
        """
        if self._active is None:
            return None
        self._active = self._active.with_commitment(new_commitment)
        return self._active

    def abandon(self) -> GoalState | None:
        """Abandon the active goal. Archives it and clears active."""
        if self._active is None:
            return None
        abandoned = self._active
        self._history.append(abandoned)
        self._active = None
        return abandoned

    def clear(self) -> None:
        """Clear all state — active and history."""
        self._active = None
        self._history.clear()

    def get_history(self) -> list[GoalState]:
        """Return a copy of the goal history."""
        return list(self._history)

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self._active.to_dict() if self._active else None,
            "history_count": len(self._history),
        }
