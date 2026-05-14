"""Convergence Lifecycle Engine v1.

7-state lifecycle:
scanned → classified → verified → quarantined → converged → ingestion_ready → archived

UMH substrate subsystem. Phase 96.8CO.
"""

from __future__ import annotations

from typing import Any

from core.convergence.repository_topology_contracts_v1 import (
    ConvergencePhase,
    _now_iso,
)


CONVERGENCE_LIFECYCLE_ORDER = [
    ConvergencePhase.SCANNED,
    ConvergencePhase.CLASSIFIED,
    ConvergencePhase.VERIFIED,
    ConvergencePhase.QUARANTINED,
    ConvergencePhase.CONVERGED,
    ConvergencePhase.INGESTION_READY,
    ConvergencePhase.ARCHIVED,
]

_CONVERGENCE_PHASE_INDEX = {p: i for i, p in enumerate(CONVERGENCE_LIFECYCLE_ORDER)}

TERMINAL_CONVERGENCE_PHASES = {ConvergencePhase.ARCHIVED}


class ConvergenceLifecycleEngine:
    """Manages convergence lifecycle transitions."""

    def __init__(self) -> None:
        self._transitions: list[dict[str, Any]] = []

    def can_transition(self, current: ConvergencePhase, target: ConvergencePhase) -> bool:
        ci = _CONVERGENCE_PHASE_INDEX.get(current)
        ti = _CONVERGENCE_PHASE_INDEX.get(target)
        if ci is None or ti is None:
            return False
        return ti == ci + 1

    def transition(self, current: ConvergencePhase, target: ConvergencePhase) -> dict[str, Any]:
        if current in TERMINAL_CONVERGENCE_PHASES:
            raise ValueError(f"Cannot transition from terminal phase: {current.value}")
        if not self.can_transition(current, target):
            raise ValueError(f"Invalid transition: {current.value} → {target.value}")
        entry = {
            "from": current.value,
            "to": target.value,
            "timestamp": _now_iso(),
        }
        self._transitions.append(entry)
        return entry

    def get_stats(self) -> dict[str, Any]:
        return {"total_transitions": len(self._transitions)}
