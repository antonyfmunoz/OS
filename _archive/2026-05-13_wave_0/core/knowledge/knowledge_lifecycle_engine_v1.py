"""Knowledge Lifecycle Engine v1.

Manages knowledge state transitions through the 10-state lifecycle.
Transitions are governed — no skipping states, no terminal re-entry.

UMH substrate subsystem. Phase 96.8CB.
"""

from __future__ import annotations

from core.knowledge.knowledge_fabric_contracts_v1 import (
    KnowledgeLifecycleState,
    _now_iso,
)

VALID_TRANSITIONS: dict[str, list[str]] = {
    "observed": ["contextualized"],
    "contextualized": ["reconciled"],
    "reconciled": ["corroborated"],
    "corroborated": ["promotable"],
    "promotable": ["canonical"],
    "canonical": ["evolved", "deprecated"],
    "evolved": ["canonical", "deprecated"],
    "deprecated": ["archived", "superseded"],
    "archived": [],
    "superseded": [],
}

TERMINAL_STATES = {"archived", "superseded"}


class KnowledgeLifecycleEngine:
    """Manages knowledge lifecycle state transitions."""

    def __init__(self, state_dir: str | None = None) -> None:
        self._current = "observed"
        self._transitions: list[dict[str, str]] = []
        self._total_transitions = 0

    @property
    def current_state(self) -> str:
        return self._current

    def transition(self, target: KnowledgeLifecycleState) -> str:
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
