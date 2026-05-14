"""Scaling Lifecycle Engine v1.

9-state lifecycle for operational scaling:
  stable → elevated → pressured → throttled →
  degraded → recovering → stabilized → suspended → archived

UMH substrate subsystem. Phase 96.8BY.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.scaling.operational_scaling_contracts_v1 import (
    ScalingLifecycleState,
    _now_iso,
)


VALID_SCALING_TRANSITIONS: dict[str, set[str]] = {
    "stable": {"elevated", "suspended"},
    "elevated": {"stable", "pressured", "suspended"},
    "pressured": {"elevated", "throttled", "degraded", "suspended"},
    "throttled": {"pressured", "elevated", "degraded", "suspended"},
    "degraded": {"recovering", "suspended"},
    "recovering": {"stabilized", "degraded", "suspended"},
    "stabilized": {"stable", "elevated", "suspended"},
    "suspended": {"stable", "archived"},
    "archived": set(),
}

TERMINAL_STATES: set[str] = {"archived"}


class ScalingLifecycleEngine:
    """Manages the 9-state scaling lifecycle."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/scaling",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state: str = ScalingLifecycleState.STABLE.value
        self._total_transitions: int = 0

    @property
    def current_state(self) -> str:
        return self._state

    def transition(
        self,
        target: ScalingLifecycleState,
        reason: str = "",
    ) -> bool:
        target_val = target.value
        valid = VALID_SCALING_TRANSITIONS.get(self._state, set())
        if target_val not in valid:
            return False

        from_state = self._state
        self._state = target_val
        self._total_transitions += 1
        self._persist_transition(from_state, target_val, reason)
        return True

    def is_terminal(self) -> bool:
        return self._state in TERMINAL_STATES

    def is_under_pressure(self) -> bool:
        return self._state in ("pressured", "throttled", "degraded")

    def _persist_transition(
        self,
        from_state: str,
        to_state: str,
        reason: str = "",
    ) -> None:
        record = {
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
            "timestamp": _now_iso(),
        }
        path = self._state_dir / "scaling_lifecycle_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def get_stats(self) -> dict[str, Any]:
        return {
            "current_state": self._state,
            "total_transitions": self._total_transitions,
        }
