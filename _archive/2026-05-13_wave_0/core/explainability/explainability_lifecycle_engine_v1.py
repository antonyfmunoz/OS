"""Explainability Lifecycle Engine v1.

5-state lifecycle for constitutional explainability:
defined → reconstructing → validating → explained → archived

UMH substrate subsystem. Phase 96.8CK.
"""

from __future__ import annotations

from typing import Any

from core.explainability.constitutional_explainability_contracts_v1 import (
    ExplainabilityPhase,
    _now_iso,
)


VALID_TRANSITIONS: dict[str, list[str]] = {
    ExplainabilityPhase.DEFINED: [ExplainabilityPhase.RECONSTRUCTING],
    ExplainabilityPhase.RECONSTRUCTING: [ExplainabilityPhase.VALIDATING],
    ExplainabilityPhase.VALIDATING: [ExplainabilityPhase.EXPLAINED],
    ExplainabilityPhase.EXPLAINED: [ExplainabilityPhase.ARCHIVED],
    ExplainabilityPhase.ARCHIVED: [],
}

TERMINAL_STATES: set[str] = {ExplainabilityPhase.ARCHIVED}


class ExplainabilityLifecycleEngine:
    def __init__(self) -> None:
        self._phase: str = ExplainabilityPhase.DEFINED
        self._transitions: int = 0
        self._history: list[dict[str, Any]] = []

    @property
    def current_phase(self) -> str:
        return self._phase

    @property
    def is_terminal(self) -> bool:
        return self._phase in TERMINAL_STATES

    def can_transition(self, target: str) -> bool:
        return target in VALID_TRANSITIONS.get(self._phase, [])

    def transition(self, target: str) -> dict[str, Any]:
        if self.is_terminal:
            raise ValueError(f"Cannot transition from terminal state: {self._phase}")
        if not self.can_transition(target):
            raise ValueError(f"Invalid transition: {self._phase} → {target}")
        prev = self._phase
        self._phase = target
        self._transitions += 1
        record = {"from": prev, "to": target, "transition_number": self._transitions, "timestamp": _now_iso()}
        self._history.append(record)
        return record

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def get_stats(self) -> dict[str, Any]:
        return {"current_phase": self._phase, "transitions": self._transitions, "is_terminal": self.is_terminal, "history_length": len(self._history)}
