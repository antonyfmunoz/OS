"""UMH Goal Store — thread-safe in-memory store for persistent goals."""

from __future__ import annotations

import threading

from umh.core.clock import iso_now as _iso_now
from umh.goals.models import Goal, GoalStatus


class GoalStore:
    """Thread-safe in-memory store for Goal instances."""

    def __init__(self) -> None:
        self._goals: dict[str, Goal] = {}
        self._lock = threading.Lock()

    def create(self, goal: Goal) -> Goal:
        """Store a new goal. Returns the stored instance."""
        with self._lock:
            self._goals[goal.id] = goal
        return goal

    def get(self, goal_id: str) -> Goal | None:
        """Return a goal by ID or None if not found."""
        with self._lock:
            return self._goals.get(goal_id)

    def list_all(self) -> list[Goal]:
        """Return all goals."""
        with self._lock:
            return list(self._goals.values())

    def list_active(self) -> list[Goal]:
        """Return only active goals."""
        with self._lock:
            return [g for g in self._goals.values() if g.status == GoalStatus.ACTIVE]

    def delete(self, goal_id: str) -> bool:
        """Remove a goal. Returns True if it existed."""
        with self._lock:
            return self._goals.pop(goal_id, None) is not None

    def pause(self, goal_id: str) -> Goal | None:
        """Pause a goal. Returns updated goal or None if not found."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            goal.status = GoalStatus.PAUSED
            goal.updated_at = _iso_now()
            return goal

    def resume(self, goal_id: str) -> Goal | None:
        """Resume a paused goal. Returns updated goal or None if not found."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            goal.status = GoalStatus.ACTIVE
            goal.updated_at = _iso_now()
            return goal

    def update_progress(
        self, goal_id: str, progress: float, tasks_created: int, tasks_completed: int
    ) -> None:
        """Update progress tracking fields for a goal."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return
            goal.progress = progress
            goal.tasks_created = tasks_created
            goal.tasks_completed = tasks_completed
            goal.updated_at = _iso_now()

    def complete(self, goal_id: str) -> Goal | None:
        """Mark a goal as completed. Returns updated goal or None if not found."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            goal.status = GoalStatus.COMPLETED
            goal.progress = 1.0
            goal.updated_at = _iso_now()
            return goal

    def fail(self, goal_id: str) -> Goal | None:
        """Mark a goal as failed. Returns updated goal or None if not found."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            goal.status = GoalStatus.FAILED
            goal.updated_at = _iso_now()
            return goal

    def update_evaluation(self, goal_id: str) -> None:
        """Record that a goal was just evaluated."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return
            goal.last_evaluated_at = _iso_now()
            goal.updated_at = goal.last_evaluated_at


_store: GoalStore | None = None
_store_lock = threading.Lock()


def get_goal_store() -> GoalStore:
    """Return the singleton GoalStore, creating it if needed."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = GoalStore()
    return _store


def reset_goal_store() -> GoalStore:
    """Reset the singleton store. Returns the new instance."""
    global _store
    with _store_lock:
        _store = GoalStore()
    return _store
