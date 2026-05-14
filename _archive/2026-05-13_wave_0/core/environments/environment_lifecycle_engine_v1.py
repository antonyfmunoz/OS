"""Environment Lifecycle Engine v1.

10-state lifecycle for operational environments:
  registered → available → synchronized → delegated → executing →
  paused → restored → unavailable → archived → terminated

UMH substrate subsystem. Phase 96.8BX.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.environments.live_environment_topology_contracts_v1 import (
    EnvironmentLifecycleState,
    _now_iso,
)


VALID_ENVIRONMENT_TRANSITIONS: dict[str, set[str]] = {
    "registered": {"available", "terminated"},
    "available": {"synchronized", "executing", "unavailable", "paused", "terminated"},
    "synchronized": {"available", "delegated", "executing", "paused", "terminated"},
    "delegated": {"executing", "paused", "available", "terminated"},
    "executing": {"paused", "available", "unavailable", "terminated"},
    "paused": {"restored", "available", "terminated"},
    "restored": {"available", "synchronized", "executing", "terminated"},
    "unavailable": {"available", "restored", "archived", "terminated"},
    "archived": {"terminated"},
    "terminated": set(),
}

TERMINAL_STATES: set[str] = {"terminated"}
FINAL_STATES: set[str] = {"archived", "terminated"}


class EnvironmentLifecycleEngine:
    """Manages the 10-state environment lifecycle."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/environment_coordination",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._states: dict[str, str] = {}
        self._total_transitions: int = 0

    def register(self, environment_id: str) -> None:
        self._states[environment_id] = EnvironmentLifecycleState.REGISTERED.value
        self._persist_transition(environment_id, "", "registered")

    def transition(
        self,
        environment_id: str,
        target: EnvironmentLifecycleState,
        reason: str = "",
    ) -> bool:
        current = self._states.get(environment_id)
        if current is None:
            return False

        target_val = target.value
        valid = VALID_ENVIRONMENT_TRANSITIONS.get(current, set())
        if target_val not in valid:
            return False

        self._states[environment_id] = target_val
        self._total_transitions += 1
        self._persist_transition(environment_id, current, target_val, reason)
        return True

    def get_state(self, environment_id: str) -> str | None:
        return self._states.get(environment_id)

    def is_terminal(self, environment_id: str) -> bool:
        return self._states.get(environment_id, "") in TERMINAL_STATES

    def is_final(self, environment_id: str) -> bool:
        return self._states.get(environment_id, "") in FINAL_STATES

    def _persist_transition(
        self,
        environment_id: str,
        from_state: str,
        to_state: str,
        reason: str = "",
    ) -> None:
        record = {
            "environment_id": environment_id,
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
            "timestamp": _now_iso(),
        }
        path = self._state_dir / "environment_lifecycle_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_environments": len(self._states),
            "total_transitions": self._total_transitions,
        }
