"""Runtime Certification Lifecycle Engine v1.

5-state lifecycle for runtime certification:
defined → staged → validating → certified → archived

UMH substrate subsystem. Phase 96.8CI.
"""

from __future__ import annotations

from typing import Any

from core.certification.runtime_certification_contracts_v1 import (
    CertificationPhase,
    _now_iso,
)


VALID_TRANSITIONS: dict[str, list[str]] = {
    CertificationPhase.DEFINED: [CertificationPhase.STAGED],
    CertificationPhase.STAGED: [CertificationPhase.VALIDATING],
    CertificationPhase.VALIDATING: [CertificationPhase.CERTIFIED],
    CertificationPhase.CERTIFIED: [CertificationPhase.ARCHIVED],
    CertificationPhase.ARCHIVED: [],
}

TERMINAL_STATES: set[str] = {CertificationPhase.ARCHIVED}


class RuntimeCertificationLifecycleEngine:
    """Manages certification lifecycle progression."""

    def __init__(self) -> None:
        self._phase: str = CertificationPhase.DEFINED
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
            raise ValueError(
                f"Cannot transition from terminal state: {self._phase}"
            )
        if not self.can_transition(target):
            raise ValueError(
                f"Invalid transition: {self._phase} → {target}"
            )

        prev = self._phase
        self._phase = target
        self._transitions += 1

        record = {
            "from": prev,
            "to": target,
            "transition_number": self._transitions,
            "timestamp": _now_iso(),
        }
        self._history.append(record)
        return record

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def get_stats(self) -> dict[str, Any]:
        return {
            "current_phase": self._phase,
            "transitions": self._transitions,
            "is_terminal": self.is_terminal,
            "history_length": len(self._history),
        }
