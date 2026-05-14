"""Operational Lifecycle Engine v1.

12-state lifecycle for long-horizon operational execution:
  initialized -> staged -> waiting -> approved -> executing
  executing -> deferred | completed | failed | suspended
  deferred -> resumed -> executing
  suspended -> resumed -> executing
  completed -> archived -> terminated
  failed -> terminated
  terminated (final)

All transitions validated. Lineage persisted to JSONL.

UMH substrate subsystem. Phase 96.8BW.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.operations.long_horizon_operational_contracts_v1 import (
    OperationalLifecycleState,
    _new_id,
    _now_iso,
)


VALID_OPERATIONAL_TRANSITIONS: dict[str, list[str]] = {
    "initialized": ["staged", "terminated"],
    "staged": ["waiting", "approved", "executing", "terminated"],
    "waiting": ["approved", "deferred", "suspended", "terminated"],
    "approved": ["executing", "terminated"],
    "executing": ["completed", "failed", "deferred", "suspended", "terminated"],
    "deferred": ["resumed", "terminated"],
    "resumed": ["executing", "staged", "terminated"],
    "completed": ["archived", "terminated"],
    "failed": ["terminated"],
    "suspended": ["resumed", "terminated"],
    "archived": ["terminated"],
    "terminated": [],
}

TERMINAL_STATES: set[str] = {"terminated"}
FINAL_STATES: set[str] = {"completed", "failed", "archived", "terminated"}


class OperationalLifecycleEngine:
    """Manages long-horizon operational lifecycle transitions."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/operations",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._states: dict[str, str] = {}
        self._total_transitions: int = 0
        self._invalid_transitions: int = 0

    def register(self, entity_id: str) -> str:
        self._states[entity_id] = OperationalLifecycleState.INITIALIZED.value
        return OperationalLifecycleState.INITIALIZED.value

    def transition(
        self,
        entity_id: str,
        to_state: OperationalLifecycleState,
        reason: str = "",
    ) -> bool:
        current = self._states.get(entity_id)
        if current is None:
            return False

        valid = VALID_OPERATIONAL_TRANSITIONS.get(current, [])
        if to_state.value not in valid:
            self._invalid_transitions += 1
            return False

        from_state = current
        self._states[entity_id] = to_state.value
        self._total_transitions += 1

        path = self._state_dir / "operational_lifecycle_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "transition_id": _new_id("oplt"),
                "entity_id": entity_id,
                "from_state": from_state,
                "to_state": to_state.value,
                "reason": reason,
                "timestamp": _now_iso(),
            }, default=str) + "\n")

        return True

    def get_state(self, entity_id: str) -> str | None:
        return self._states.get(entity_id)

    def is_terminal(self, entity_id: str) -> bool:
        state = self._states.get(entity_id)
        return state in TERMINAL_STATES if state else False

    def is_final(self, entity_id: str) -> bool:
        state = self._states.get(entity_id)
        return state in FINAL_STATES if state else False

    def get_active(self) -> list[str]:
        return [
            eid for eid, state in self._states.items()
            if state not in FINAL_STATES
        ]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_entities": len(self._states),
            "active_entities": len(self.get_active()),
            "total_transitions": self._total_transitions,
            "invalid_transitions": self._invalid_transitions,
        }
