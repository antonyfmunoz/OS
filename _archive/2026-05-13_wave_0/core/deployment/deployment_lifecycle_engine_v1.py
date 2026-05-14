"""Deployment Lifecycle Engine v1.

9-state lifecycle for deployment projections:
defined → validated → staged → approved → deployed →
observed → restored/rolled_back → archived

UMH substrate subsystem. Phase 96.8CE.
"""

from __future__ import annotations

from typing import Any

from core.deployment.platform_deployment_contracts_v1 import (
    DeploymentLifecyclePhase,
    _now_iso,
)

VALID_TRANSITIONS: dict[str, list[str]] = {
    "defined": ["validated"],
    "validated": ["staged", "archived"],
    "staged": ["approved", "archived"],
    "approved": ["deployed", "archived"],
    "deployed": ["observed", "rolled_back", "archived"],
    "observed": ["restored", "rolled_back", "archived"],
    "restored": ["observed", "archived"],
    "rolled_back": ["archived"],
    "archived": [],
}

TERMINAL_STATES: set[str] = {"archived"}


class DeploymentLifecycleEngine:
    """Manages deployment lifecycle transitions."""

    def __init__(self) -> None:
        self._current_phase = DeploymentLifecyclePhase.DEFINED.value
        self._transitions: list[dict[str, Any]] = []

    @property
    def current_phase(self) -> str:
        return self._current_phase

    def transition(self, to_phase: str) -> dict[str, Any]:
        valid = VALID_TRANSITIONS.get(self._current_phase, [])
        if to_phase not in valid:
            raise ValueError(
                f"Invalid transition: {self._current_phase} → {to_phase}. "
                f"Valid: {valid}"
            )

        record = {
            "from_phase": self._current_phase,
            "to_phase": to_phase,
            "timestamp": _now_iso(),
        }
        self._transitions.append(record)
        self._current_phase = to_phase
        return record

    def get_transitions(self) -> list[dict[str, Any]]:
        return list(self._transitions)

    def get_stats(self) -> dict[str, object]:
        return {
            "current_phase": self._current_phase,
            "total_transitions": len(self._transitions),
            "is_terminal": self._current_phase in TERMINAL_STATES,
        }
