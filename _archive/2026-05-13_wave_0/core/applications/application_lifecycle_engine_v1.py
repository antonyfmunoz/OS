"""Application Lifecycle Engine v1.

6-state lifecycle for application projections:
registered → projected → active → suspended → restored → archived

UMH substrate subsystem. Phase 96.8CD.
"""

from __future__ import annotations

from typing import Any

from core.applications.application_projection_contracts_v1 import (
    ApplicationLifecycleState,
    _now_iso,
)

VALID_TRANSITIONS: dict[str, list[str]] = {
    "registered": ["projected"],
    "projected": ["active", "archived"],
    "active": ["suspended", "archived"],
    "suspended": ["restored", "archived"],
    "restored": ["active", "archived"],
    "archived": [],
}

TERMINAL_STATES: set[str] = {"archived"}


class ApplicationLifecycleEngine:
    """Manages application lifecycle transitions."""

    def __init__(self) -> None:
        self._current_state = ApplicationLifecycleState.REGISTERED.value
        self._transitions: list[dict[str, Any]] = []

    @property
    def current_state(self) -> str:
        return self._current_state

    def transition(self, to_state: str) -> dict[str, Any]:
        valid = VALID_TRANSITIONS.get(self._current_state, [])
        if to_state not in valid:
            raise ValueError(
                f"Invalid transition: {self._current_state} → {to_state}. "
                f"Valid: {valid}"
            )

        record = {
            "from_state": self._current_state,
            "to_state": to_state,
            "timestamp": _now_iso(),
        }
        self._transitions.append(record)
        self._current_state = to_state
        return record

    def get_transitions(self) -> list[dict[str, Any]]:
        return list(self._transitions)

    def get_stats(self) -> dict[str, object]:
        return {
            "current_state": self._current_state,
            "total_transitions": len(self._transitions),
            "is_terminal": self._current_state in TERMINAL_STATES,
        }
