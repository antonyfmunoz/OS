"""UMH Goals — persistence interface for goal tracker state.

Defines the contract for saving/loading GoalTracker runtime signals
across session restarts. Concrete implementations live in EOS
(e.g. umh/adapters/umh_goals.py).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GoalPersistence(Protocol):
    """Contract for persisting GoalTracker state."""

    def save_goal_trackers(self, tracker_data: dict[str, dict], registry_turn: int) -> None: ...

    def load_goal_trackers(self) -> dict[str, Any] | None: ...


class NullGoalPersistence:
    """No-op persistence — used when no backend is configured."""

    def save_goal_trackers(self, tracker_data: dict[str, dict], registry_turn: int) -> None:
        pass

    def load_goal_trackers(self) -> dict[str, Any] | None:
        return None


_PERSISTENCE: GoalPersistence | None = None


def get_goal_persistence() -> GoalPersistence:
    """Get the configured goal persistence backend.

    Falls back to EOS adapter if available, then NullGoalPersistence.
    """
    global _PERSISTENCE
    if _PERSISTENCE is None:
        _PERSISTENCE = _default_persistence()
    return _PERSISTENCE


def set_goal_persistence(backend: GoalPersistence) -> None:
    """Override the goal persistence backend."""
    global _PERSISTENCE
    _PERSISTENCE = backend


def reset_goal_persistence() -> None:
    """Clear the persistence singleton (for testing)."""
    global _PERSISTENCE
    _PERSISTENCE = None


def _default_persistence() -> GoalPersistence:
    from umh.adapters.bridge import discover_platform_adapter

    adapter = discover_platform_adapter("umh.adapters.umh_goals", "get_goal_persistence_adapter")
    if adapter is not None:
        return adapter
    return NullGoalPersistence()
