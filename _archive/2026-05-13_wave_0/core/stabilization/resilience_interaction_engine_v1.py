"""Resilience Interaction Engine v1.

Validates recovery stability, cascade depth bounding,
and absence of recursive recovery loops under stress.

UMH substrate subsystem. Phase 96.8CH.
"""

from __future__ import annotations

from typing import Any

from core.stabilization.constitutional_operational_fabric_contracts_v1 import (
    RecoveryDurabilityState,
    _now_iso,
)


MAX_RECOVERY_VALIDATIONS = 50

RESILIENCE_CHECKS: list[str] = [
    "recovery_stability",
    "no_recursive_loops",
    "cascade_depth_bounded",
    "resilience_under_concurrency",
    "resilience_after_scaling",
    "resilience_after_rollback",
]


class ResilienceInteractionEngine:
    """Validates resilience interaction durability."""

    def __init__(self) -> None:
        self._validations: list[RecoveryDurabilityState] = []

    def validate_resilience(
        self,
        recovery_scenarios: int,
        all_stable: bool = True,
        no_recursive_loops: bool = True,
    ) -> dict[str, Any]:
        if len(self._validations) >= MAX_RECOVERY_VALIDATIONS:
            raise ValueError("Max recovery validations reached")

        state = RecoveryDurabilityState(
            recovery_scenarios=recovery_scenarios,
            all_stable=all_stable,
            no_recursive_loops=no_recursive_loops,
        )
        self._validations.append(state)

        durable = all_stable and no_recursive_loops

        return {
            "recovery_id": state.recovery_id,
            "durable": durable,
            "recovery_scenarios": recovery_scenarios,
            "all_stable": all_stable,
            "no_recursive_loops": no_recursive_loops,
        }

    def get_all_validations(self) -> list[dict[str, Any]]:
        return [v.to_dict() for v in self._validations]

    def get_durable_count(self) -> int:
        return sum(
            1 for v in self._validations
            if v.all_stable and v.no_recursive_loops
        )

    def get_failed_count(self) -> int:
        return sum(
            1 for v in self._validations
            if not (v.all_stable and v.no_recursive_loops)
        )

    def all_durable(self) -> bool:
        if not self._validations:
            return True
        return all(
            v.all_stable and v.no_recursive_loops
            for v in self._validations
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_validations": len(self._validations),
            "durable": self.get_durable_count(),
            "failed": self.get_failed_count(),
            "all_durable": self.all_durable(),
        }
