"""Constitutional Lifecycle Engine v1.

7-state lifecycle for constitutional runtime consolidation:
defined → validated → consolidated → hardened → verified → operational → archived

UMH substrate subsystem. Phase 96.8CG.
"""

from __future__ import annotations

from typing import Any

from core.constitutional.constitutional_runtime_contracts_v1 import (
    ConstitutionalPhase,
    _now_iso,
)

VALID_TRANSITIONS: dict[str, list[str]] = {
    "defined": ["validated"],
    "validated": ["consolidated"],
    "consolidated": ["hardened"],
    "hardened": ["verified"],
    "verified": ["operational"],
    "operational": ["archived"],
    "archived": [],
}

TERMINAL_STATES: set[str] = {"archived"}


class ConstitutionalLifecycleEngine:
    """Manages constitutional runtime lifecycle transitions."""

    def __init__(self) -> None:
        self._current_phase = ConstitutionalPhase.DEFINED.value
        self._transitions: list[dict[str, Any]] = []

    @property
    def current_phase(self) -> str:
        return self._current_phase

    def transition(self, target: str) -> dict[str, Any]:
        valid_phases = {p.value for p in ConstitutionalPhase}
        if target not in valid_phases:
            raise ValueError(
                f"Unknown phase: {target}. Known: {sorted(valid_phases)}"
            )

        allowed = VALID_TRANSITIONS.get(self._current_phase, [])
        if target not in allowed:
            raise ValueError(
                f"Cannot transition from {self._current_phase} to {target}. "
                f"Allowed: {allowed}"
            )

        record = {
            "from": self._current_phase,
            "to": target,
            "timestamp": _now_iso(),
        }
        self._transitions.append(record)
        self._current_phase = target
        return record

    def is_terminal(self) -> bool:
        return self._current_phase in TERMINAL_STATES

    def get_transitions(self) -> list[dict[str, Any]]:
        return list(self._transitions)

    def get_stats(self) -> dict[str, object]:
        return {
            "current_phase": self._current_phase,
            "total_transitions": len(self._transitions),
            "is_terminal": self.is_terminal(),
        }
