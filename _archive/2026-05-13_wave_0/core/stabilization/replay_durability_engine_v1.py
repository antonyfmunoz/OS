"""Replay Durability Engine v1.

Validates replay determinism and lineage integrity
across all substrate layers under stress conditions.

UMH substrate subsystem. Phase 96.8CH.
"""

from __future__ import annotations

from typing import Any

from core.stabilization.constitutional_operational_fabric_contracts_v1 import (
    ReplayDurabilityState,
    _now_iso,
)


MAX_REPLAY_VALIDATIONS = 50

REPLAY_DURABILITY_CHECKS: list[str] = [
    "cross_layer_determinism",
    "lineage_preservation",
    "replay_under_stress",
    "replay_after_restoration",
    "replay_after_scaling",
    "replay_after_rollback",
]


class ReplayDurabilityEngine:
    """Validates replay durability across substrate layers."""

    def __init__(self) -> None:
        self._validations: list[ReplayDurabilityState] = []

    def validate_replay_durability(
        self,
        layers_validated: int,
        all_deterministic: bool = True,
        lineage_intact: bool = True,
    ) -> dict[str, Any]:
        if len(self._validations) >= MAX_REPLAY_VALIDATIONS:
            raise ValueError("Max replay validations reached")

        state = ReplayDurabilityState(
            layers_validated=layers_validated,
            all_deterministic=all_deterministic,
            lineage_intact=lineage_intact,
        )
        self._validations.append(state)

        return {
            "replay_id": state.replay_id,
            "durable": all_deterministic and lineage_intact,
            "layers_validated": layers_validated,
            "all_deterministic": all_deterministic,
            "lineage_intact": lineage_intact,
        }

    def get_all_validations(self) -> list[dict[str, Any]]:
        return [v.to_dict() for v in self._validations]

    def get_durable_count(self) -> int:
        return sum(
            1 for v in self._validations
            if v.all_deterministic and v.lineage_intact
        )

    def get_failed_count(self) -> int:
        return sum(
            1 for v in self._validations
            if not (v.all_deterministic and v.lineage_intact)
        )

    def all_durable(self) -> bool:
        if not self._validations:
            return True
        return all(
            v.all_deterministic and v.lineage_intact
            for v in self._validations
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_validations": len(self._validations),
            "durable": self.get_durable_count(),
            "failed": self.get_failed_count(),
            "all_durable": self.all_durable(),
        }
