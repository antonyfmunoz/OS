"""EOS → UMH goal persistence adapter.

Wraps the existing umh.persistence goal tracker functions to satisfy
the UMH GoalPersistence protocol.
"""

from __future__ import annotations

from typing import Any


class GoalPersistenceAdapter:
    """Adapts umh.persistence goal functions to UMH GoalPersistence protocol."""

    def save_goal_trackers(
        self, tracker_data: dict[str, dict], registry_turn: int
    ) -> None:
        from umh.runtime_engine.persistence import save_goal_trackers

        save_goal_trackers(tracker_data, registry_turn=registry_turn)

    def load_goal_trackers(self) -> dict[str, Any] | None:
        from umh.runtime_engine.persistence import load_goal_trackers

        return load_goal_trackers()


_ADAPTER_INSTANCE: GoalPersistenceAdapter | None = None


def get_goal_persistence_adapter() -> GoalPersistenceAdapter:
    """Get the singleton goal persistence adapter."""
    global _ADAPTER_INSTANCE
    if _ADAPTER_INSTANCE is None:
        _ADAPTER_INSTANCE = GoalPersistenceAdapter()
    return _ADAPTER_INSTANCE
