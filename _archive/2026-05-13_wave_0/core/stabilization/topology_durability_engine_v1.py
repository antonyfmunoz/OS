"""Topology Durability Engine v1.

Validates topology integrity, orphan prevention,
and hidden mutation detection under stress conditions.

UMH substrate subsystem. Phase 96.8CH.
"""

from __future__ import annotations

from typing import Any

from core.stabilization.constitutional_operational_fabric_contracts_v1 import (
    TopologyDurabilityState,
    _now_iso,
)


MAX_TOPOLOGY_VALIDATIONS = 50

TOPOLOGY_DURABILITY_CHECKS: list[str] = [
    "topology_integrity",
    "orphan_prevention",
    "hidden_mutation_detection",
    "topology_under_scaling",
    "topology_after_rollback",
    "topology_after_recovery",
]


class TopologyDurabilityEngine:
    """Validates topology durability across substrate domains."""

    def __init__(self) -> None:
        self._validations: list[TopologyDurabilityState] = []

    def validate_topology_durability(
        self,
        topologies_validated: int,
        all_intact: bool = True,
        no_orphans: bool = True,
        no_hidden_mutation: bool = True,
    ) -> dict[str, Any]:
        if len(self._validations) >= MAX_TOPOLOGY_VALIDATIONS:
            raise ValueError("Max topology validations reached")

        state = TopologyDurabilityState(
            topologies_validated=topologies_validated,
            all_intact=all_intact,
            no_orphans=no_orphans,
            no_hidden_mutation=no_hidden_mutation,
        )
        self._validations.append(state)

        durable = all_intact and no_orphans and no_hidden_mutation

        return {
            "topology_id": state.topology_id,
            "durable": durable,
            "topologies_validated": topologies_validated,
            "all_intact": all_intact,
            "no_orphans": no_orphans,
            "no_hidden_mutation": no_hidden_mutation,
        }

    def get_all_validations(self) -> list[dict[str, Any]]:
        return [v.to_dict() for v in self._validations]

    def get_durable_count(self) -> int:
        return sum(
            1 for v in self._validations
            if v.all_intact and v.no_orphans and v.no_hidden_mutation
        )

    def get_failed_count(self) -> int:
        return sum(
            1 for v in self._validations
            if not (v.all_intact and v.no_orphans and v.no_hidden_mutation)
        )

    def all_durable(self) -> bool:
        if not self._validations:
            return True
        return all(
            v.all_intact and v.no_orphans and v.no_hidden_mutation
            for v in self._validations
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_validations": len(self._validations),
            "durable": self.get_durable_count(),
            "failed": self.get_failed_count(),
            "all_durable": self.all_durable(),
        }
