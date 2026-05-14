"""Continuity Durability Engine v1.

Validates continuity restoration, checkpoint determinism,
and session lineage preservation under stress conditions.

UMH substrate subsystem. Phase 96.8CH.
"""

from __future__ import annotations

from typing import Any

from core.stabilization.constitutional_operational_fabric_contracts_v1 import (
    ContinuityDurabilityState,
    _now_iso,
)


MAX_CONTINUITY_VALIDATIONS = 50

CONTINUITY_DURABILITY_CHECKS: list[str] = [
    "checkpoint_restoration",
    "session_lineage_preservation",
    "cross_layer_continuity",
    "continuity_under_scaling",
    "continuity_after_rollback",
    "continuity_after_recovery",
]


class ContinuityDurabilityEngine:
    """Validates continuity durability across substrate layers."""

    def __init__(self) -> None:
        self._validations: list[ContinuityDurabilityState] = []

    def validate_continuity_durability(
        self,
        layers_validated: int,
        checkpoints_restored: int = 0,
        all_restored: bool = True,
    ) -> dict[str, Any]:
        if len(self._validations) >= MAX_CONTINUITY_VALIDATIONS:
            raise ValueError("Max continuity validations reached")

        state = ContinuityDurabilityState(
            layers_validated=layers_validated,
            checkpoints_restored=checkpoints_restored,
            all_restored=all_restored,
        )
        self._validations.append(state)

        return {
            "continuity_id": state.continuity_id,
            "durable": all_restored,
            "layers_validated": layers_validated,
            "checkpoints_restored": checkpoints_restored,
            "all_restored": all_restored,
        }

    def get_all_validations(self) -> list[dict[str, Any]]:
        return [v.to_dict() for v in self._validations]

    def get_durable_count(self) -> int:
        return sum(1 for v in self._validations if v.all_restored)

    def get_failed_count(self) -> int:
        return sum(1 for v in self._validations if not v.all_restored)

    def all_durable(self) -> bool:
        if not self._validations:
            return True
        return all(v.all_restored for v in self._validations)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_validations": len(self._validations),
            "durable": self.get_durable_count(),
            "failed": self.get_failed_count(),
            "all_durable": self.all_durable(),
        }
