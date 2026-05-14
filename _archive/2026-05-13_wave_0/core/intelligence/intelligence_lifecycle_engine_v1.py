"""Intelligence Lifecycle Engine v1.

11-state lifecycle for operational intelligence coordination:
  inactive → observing → synthesizing → contextualizing →
  prioritizing → compressing → projecting → validating →
  replaying → suspended → archived

UMH substrate subsystem. Phase 96.8CA.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.intelligence.operational_intelligence_contracts_v1 import (
    IntelligenceLifecycleState,
    _now_iso,
)


VALID_TRANSITIONS: dict[str, set[str]] = {
    "inactive": {"observing", "suspended"},
    "observing": {"synthesizing", "inactive"},
    "synthesizing": {"contextualizing", "observing"},
    "contextualizing": {"prioritizing", "synthesizing"},
    "prioritizing": {"compressing", "contextualizing"},
    "compressing": {"projecting", "prioritizing"},
    "projecting": {"validating", "compressing"},
    "validating": {"observing", "replaying"},
    "replaying": {"validating", "observing"},
    "suspended": {"inactive", "archived"},
    "archived": set(),
}

TERMINAL_STATES: set[str] = {"archived"}


class IntelligenceLifecycleEngine:
    """Manages 11-state intelligence lifecycle transitions."""

    def __init__(self, state_dir: str | Path = "data/runtime/intelligence") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._current: str = "inactive"
        self._history: list[dict[str, Any]] = []
        self._total_transitions: int = 0

    @property
    def current_state(self) -> str:
        return self._current

    def transition(self, target: IntelligenceLifecycleState) -> bool:
        target_val = target.value
        if target_val not in VALID_TRANSITIONS.get(self._current, set()):
            return False
        if self._current in TERMINAL_STATES:
            return False

        old = self._current
        self._current = target_val
        self._total_transitions += 1

        record = {
            "from_state": old,
            "to_state": target_val,
            "timestamp": _now_iso(),
        }
        self._history.append(record)

        path = self._state_dir / "intelligence_lifecycle_transitions.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        return True

    def can_transition(self, target: IntelligenceLifecycleState) -> bool:
        if self._current in TERMINAL_STATES:
            return False
        return target.value in VALID_TRANSITIONS.get(self._current, set())

    def get_valid_transitions(self) -> set[str]:
        if self._current in TERMINAL_STATES:
            return set()
        return VALID_TRANSITIONS.get(self._current, set())

    def get_stats(self) -> dict[str, Any]:
        return {
            "current_state": self._current,
            "total_transitions": self._total_transitions,
            "history_length": len(self._history),
        }
