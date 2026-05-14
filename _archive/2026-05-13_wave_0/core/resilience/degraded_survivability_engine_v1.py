"""Degraded Survivability Engine v1.

Assesses whether the system can continue operating in degraded mode.
Computes survivability scores based on subsystem health distribution.

Cannot restore subsystems — assessment only.

UMH substrate subsystem. Phase 96.8BZ.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.resilience.adaptive_resilience_contracts_v1 import (
    DegradedSurvivabilityState,
    SurvivabilityScore,
    _now_iso,
)


MINIMUM_SURVIVABILITY: float = 0.3
CRITICAL_SUBSYSTEMS: set[str] = {"spine", "governance", "continuity"}


class DegradedSurvivabilityEngine:
    """Assesses system survivability under degraded conditions."""

    def __init__(self, state_dir: str | Path = "data/runtime/resilience") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._subsystem_status: dict[str, bool] = {}
        self._total_assessments: int = 0

    def register_subsystem(self, subsystem_id: str, healthy: bool = True) -> None:
        self._subsystem_status[subsystem_id] = healthy

    def mark_degraded(self, subsystem_id: str) -> None:
        self._subsystem_status[subsystem_id] = False

    def mark_functional(self, subsystem_id: str) -> None:
        self._subsystem_status[subsystem_id] = True

    def assess_survivability(self) -> DegradedSurvivabilityState:
        self._total_assessments += 1

        degraded = [
            s for s, healthy in self._subsystem_status.items() if not healthy
        ]
        functional = [
            s for s, healthy in self._subsystem_status.items() if healthy
        ]

        total = len(self._subsystem_status)
        if total == 0:
            state = DegradedSurvivabilityState(
                survivability_score=1.0,
                can_continue=True,
                minimum_viable=True,
            )
            self._persist_assessment(state)
            return state

        functional_ratio = len(functional) / total

        critical_healthy = all(
            self._subsystem_status.get(c, True)
            for c in CRITICAL_SUBSYSTEMS
            if c in self._subsystem_status
        )

        score = functional_ratio
        if not critical_healthy:
            score *= 0.5

        can_continue = score >= MINIMUM_SURVIVABILITY
        minimum_viable = critical_healthy and score >= MINIMUM_SURVIVABILITY

        state = DegradedSurvivabilityState(
            degraded_subsystems=degraded,
            functional_subsystems=functional,
            survivability_score=round(score, 4),
            can_continue=can_continue,
            minimum_viable=minimum_viable,
        )

        self._persist_assessment(state)
        return state

    def compute_survivability_score(self) -> SurvivabilityScore:
        total = len(self._subsystem_status)
        if total == 0:
            return SurvivabilityScore()

        functional = sum(1 for v in self._subsystem_status.values() if v)
        degraded = total - functional

        fault_tolerance = max(0.0, 1.0 - (degraded / total))
        recovery_capacity = functional / total if total > 0 else 1.0

        isolation_effectiveness = 1.0
        if degraded > 0:
            isolation_effectiveness = max(
                0.0,
                1.0 - (degraded / (total * 0.5)),
            )

        overall = (
            fault_tolerance * 0.4
            + recovery_capacity * 0.35
            + isolation_effectiveness * 0.25
        )

        per_sub: dict[str, float] = {}
        for sid, healthy in self._subsystem_status.items():
            per_sub[sid] = 1.0 if healthy else 0.0

        return SurvivabilityScore(
            overall_score=round(overall, 4),
            subsystem_scores=per_sub,
            fault_tolerance=round(fault_tolerance, 4),
            recovery_capacity=round(recovery_capacity, 4),
            isolation_effectiveness=round(isolation_effectiveness, 4),
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_subsystems": len(self._subsystem_status),
            "functional_count": sum(
                1 for v in self._subsystem_status.values() if v
            ),
            "degraded_count": sum(
                1 for v in self._subsystem_status.values() if not v
            ),
            "total_assessments": self._total_assessments,
        }

    def _persist_assessment(self, state: DegradedSurvivabilityState) -> None:
        path = self._state_dir / "survivability_assessments.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(state.to_dict(), default=str) + "\n")
