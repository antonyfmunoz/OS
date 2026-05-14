"""Sovereign Integrity Engine v1.

Computes composite sovereign integrity across 7 dimensions.
All dimensions must hold for sovereign integrity to be valid.

UMH substrate subsystem. Phase 96.8CJ.
"""

from __future__ import annotations

from typing import Any

from core.validation.sovereign_operational_validation_contracts_v1 import (
    SovereignIntegrityState,
    _now_iso,
)

MAX_INTEGRITY_CHECKS = 100

INTEGRITY_DIMENSIONS: list[str] = [
    "governance_integrity",
    "replay_integrity",
    "continuity_integrity",
    "topology_integrity",
    "constitutional_integrity",
    "observability_integrity",
    "deployment_integrity",
]


class SovereignIntegrityEngine:
    def __init__(self) -> None:
        self._checks: list[SovereignIntegrityState] = []

    def compute_integrity(self, **overrides: bool) -> dict[str, Any]:
        if len(self._checks) >= MAX_INTEGRITY_CHECKS:
            raise ValueError("Max integrity checks reached")
        kwargs: dict[str, bool] = {}
        for dim in INTEGRITY_DIMENSIONS:
            kwargs[dim] = overrides.get(dim, True)
        state = SovereignIntegrityState(**kwargs)
        self._checks.append(state)
        return state.to_dict()

    def compute_full_integrity(self) -> dict[str, Any]:
        return self.compute_integrity()

    def all_sovereign(self) -> bool:
        if not self._checks:
            return True
        return all(c.sovereign_integrity_score == 1.0 for c in self._checks)

    def get_compromised(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._checks if c.sovereign_integrity_score < 1.0]

    def get_stats(self) -> dict[str, Any]:
        scores = [c.sovereign_integrity_score for c in self._checks]
        return {
            "total_checks": len(self._checks),
            "all_sovereign": self.all_sovereign(),
            "min_score": min(scores) if scores else 1.0,
            "max_score": max(scores) if scores else 1.0,
            "avg_score": sum(scores) / len(scores) if scores else 1.0,
        }
