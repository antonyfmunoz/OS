"""Operational Awareness Engine v1.

Tracks active operational state across all substrate layers:
  subsystem pressure, continuity risks, open loops,
  environment instability, governance constraints,
  operational priorities, replay integrity.

Cannot create objectives. Cannot self-direct.

UMH substrate subsystem. Phase 96.8CA.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.intelligence.operational_intelligence_contracts_v1 import (
    OperationalAwarenessState,
    IntelligenceProjectionState,
    _now_iso,
)


MAX_TRACKED_ITEMS: int = 50


class OperationalAwarenessEngine:
    """Tracks active operational awareness across substrate layers."""

    def __init__(self, state_dir: str | Path = "data/runtime/intelligence") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state = OperationalAwarenessState()
        self._total_updates: int = 0

    def update_subsystems(self, subsystems: list[str]) -> None:
        self._state.active_subsystems = subsystems[:MAX_TRACKED_ITEMS]
        self._state.timestamp = _now_iso()
        self._total_updates += 1

    def update_pressure(self, signals: list[str]) -> None:
        self._state.pressure_signals = signals[:MAX_TRACKED_ITEMS]
        self._state.timestamp = _now_iso()
        self._total_updates += 1

    def update_continuity_risks(self, risks: list[str]) -> None:
        self._state.continuity_risks = risks[:MAX_TRACKED_ITEMS]
        self._state.timestamp = _now_iso()
        self._total_updates += 1

    def update_open_loops(self, loops: list[str]) -> None:
        self._state.open_loops = loops[:MAX_TRACKED_ITEMS]
        self._state.timestamp = _now_iso()
        self._total_updates += 1

    def update_environment_status(self, status: dict[str, str]) -> None:
        self._state.environment_status = dict(
            list(status.items())[:MAX_TRACKED_ITEMS]
        )
        self._state.timestamp = _now_iso()
        self._total_updates += 1

    def update_governance_constraints(self, constraints: list[str]) -> None:
        self._state.governance_constraints = constraints[:MAX_TRACKED_ITEMS]
        self._state.timestamp = _now_iso()
        self._total_updates += 1

    def update_priorities(self, priorities: list[str]) -> None:
        self._state.operational_priorities = priorities[:MAX_TRACKED_ITEMS]
        self._state.timestamp = _now_iso()
        self._total_updates += 1

    def update_replay_integrity(self, intact: bool) -> None:
        self._state.replay_integrity = intact
        self._state.timestamp = _now_iso()
        self._total_updates += 1

    def get_awareness(self) -> OperationalAwarenessState:
        return self._state

    def project(self) -> IntelligenceProjectionState:
        risks = list(self._state.continuity_risks)
        pressures = list(self._state.pressure_signals)

        confidence = 1.0
        if risks:
            confidence -= 0.1 * min(len(risks), 5)
        if pressures:
            confidence -= 0.1 * min(len(pressures), 5)
        confidence = max(0.0, round(confidence, 4))

        return IntelligenceProjectionState(
            projected_risks=risks[:10],
            projected_pressures=pressures[:10],
            confidence=confidence,
            projection_basis=self._state.active_subsystems[:10],
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_updates": self._total_updates,
            "active_subsystems": len(self._state.active_subsystems),
            "pressure_signals": len(self._state.pressure_signals),
            "continuity_risks": len(self._state.continuity_risks),
            "open_loops": len(self._state.open_loops),
            "replay_integrity": self._state.replay_integrity,
        }
