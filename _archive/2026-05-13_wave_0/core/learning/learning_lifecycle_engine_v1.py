"""Learning Lifecycle Engine v1.

8-state lifecycle for adaptive learning:
observed → candidate → proposed → reviewed →
approved/denied → applied_by_operator → archived.

UMH substrate subsystem. Phase 96.8CC.
"""

from __future__ import annotations

from core.learning.adaptive_learning_contracts_v1 import (
    LearningLifecycleState,
    _now_iso,
)

VALID_TRANSITIONS: dict[str, list[str]] = {
    "observed": ["candidate"],
    "candidate": ["proposed"],
    "proposed": ["reviewed"],
    "reviewed": ["approved", "denied"],
    "approved": ["applied_by_operator"],
    "denied": ["archived"],
    "applied_by_operator": ["archived"],
    "archived": [],
}

TERMINAL_STATES = {"archived"}


class LearningLifecycleEngine:
    """Manages learning lifecycle state transitions."""

    def __init__(self, state_dir: str | None = None) -> None:
        self._current = "observed"
        self._transitions: list[dict[str, str]] = []
        self._total_transitions = 0

    @property
    def current_state(self) -> str:
        return self._current

    def transition(self, target: LearningLifecycleState) -> str:
        target_val = target.value
        allowed = VALID_TRANSITIONS.get(self._current, [])
        if target_val not in allowed:
            raise ValueError(
                f"Cannot transition from {self._current} to {target_val}. "
                f"Allowed: {allowed}"
            )

        old = self._current
        self._current = target_val
        self._total_transitions += 1
        self._transitions.append({
            "from": old,
            "to": target_val,
            "timestamp": _now_iso(),
        })
        return target_val

    def get_transitions(self, limit: int = 10) -> list[dict[str, str]]:
        return self._transitions[-limit:]

    def get_stats(self) -> dict[str, object]:
        return {
            "current_state": self._current,
            "total_transitions": self._total_transitions,
            "is_terminal": self._current in TERMINAL_STATES,
        }
