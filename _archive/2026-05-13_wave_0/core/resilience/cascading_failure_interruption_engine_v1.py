"""Cascading Failure Interruption Engine v1.

Detects and interrupts cascading failures across subsystems.
Tracks propagation depth and applies containment boundaries.

Cannot repair — only contains and interrupts propagation.

UMH substrate subsystem. Phase 96.8BZ.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.resilience.adaptive_resilience_contracts_v1 import (
    CascadingFailureState,
    FaultContainmentState,
    _now_iso,
)


MAX_PROPAGATION_DEPTH: int = 3
MAX_AFFECTED_SUBSYSTEMS: int = 10
MAX_ACTIVE_CASCADES: int = 5


class CascadingFailureInterruptionEngine:
    """Interrupts cascading failures before they propagate beyond bounds."""

    def __init__(self, state_dir: str | Path = "data/runtime/resilience") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._active_cascades: dict[str, CascadingFailureState] = {}
        self._containments: list[FaultContainmentState] = []
        self._total_interruptions: int = 0
        self._total_containments: int = 0

    def report_failure(
        self,
        subsystem_id: str,
        upstream_subsystem: str = "",
    ) -> CascadingFailureState:
        if upstream_subsystem and upstream_subsystem in self._active_cascades:
            cascade = self._active_cascades[upstream_subsystem]
            if subsystem_id not in cascade.affected_subsystems:
                cascade.affected_subsystems.append(subsystem_id)
            cascade.propagation_depth += 1
            cascade.timestamp = _now_iso()

            if (
                cascade.propagation_depth >= MAX_PROPAGATION_DEPTH
                or len(cascade.affected_subsystems) >= MAX_AFFECTED_SUBSYSTEMS
            ):
                self._interrupt(cascade)

            return cascade

        if len(self._active_cascades) >= MAX_ACTIVE_CASCADES:
            oldest_key = next(iter(self._active_cascades))
            self._interrupt(self._active_cascades[oldest_key])

        cascade = CascadingFailureState(
            origin_subsystem=subsystem_id,
            affected_subsystems=[subsystem_id],
            propagation_depth=0,
        )
        self._active_cascades[subsystem_id] = cascade

        self._persist_cascade(cascade)
        return cascade

    def contain_fault(
        self,
        fault_source: str,
        boundary: str,
        affected: list[str] | None = None,
    ) -> FaultContainmentState:
        containment = FaultContainmentState(
            fault_source=fault_source,
            affected_subsystems=affected or [],
            contained=True,
            containment_boundary=boundary,
            propagation_blocked=True,
        )

        self._containments.append(containment)
        self._total_containments += 1

        if fault_source in self._active_cascades:
            cascade = self._active_cascades[fault_source]
            cascade.interrupted = True
            cascade.interruption_point = boundary

        path = self._state_dir / "fault_containments.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(containment.to_dict(), default=str) + "\n")

        return containment

    def get_active_cascades(self) -> list[CascadingFailureState]:
        return [
            c for c in self._active_cascades.values()
            if not c.interrupted
        ]

    def get_cascade(self, origin: str) -> CascadingFailureState | None:
        return self._active_cascades.get(origin)

    def clear_cascade(self, origin: str) -> bool:
        if origin in self._active_cascades:
            del self._active_cascades[origin]
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        return {
            "active_cascades": len(self.get_active_cascades()),
            "total_cascades": len(self._active_cascades),
            "total_interruptions": self._total_interruptions,
            "total_containments": self._total_containments,
        }

    def _interrupt(self, cascade: CascadingFailureState) -> None:
        cascade.interrupted = True
        cascade.interruption_point = f"depth:{cascade.propagation_depth}"
        cascade.timestamp = _now_iso()
        self._total_interruptions += 1

        path = self._state_dir / "cascade_interruptions.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(cascade.to_dict(), default=str) + "\n")

    def _persist_cascade(self, cascade: CascadingFailureState) -> None:
        path = self._state_dir / "cascading_failures.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(cascade.to_dict(), default=str) + "\n")
