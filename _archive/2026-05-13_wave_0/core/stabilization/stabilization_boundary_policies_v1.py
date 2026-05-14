"""Stabilization Boundary Policies v1.

8 limits and 8 forbidden actions for operational fabric stabilization.
Override capping via min(override, default).

UMH substrate subsystem. Phase 96.8CH.
"""

from __future__ import annotations

from typing import Any

from core.stabilization.constitutional_operational_fabric_contracts_v1 import (
    StabilityBoundaryState,
    _now_iso,
)


STABILIZATION_LIMITS: dict[str, int] = {
    "max_concurrent_validations": 50,
    "max_replay_validations": 50,
    "max_continuity_validations": 50,
    "max_topology_validations": 50,
    "max_recovery_validations": 50,
    "max_stress_scenarios": 100,
    "max_stabilization_runs": 50,
    "max_boundary_checks": 200,
}

FORBIDDEN_STABILIZATION_ACTIONS: list[str] = [
    "autonomous_topology_mutation",
    "autonomous_execution",
    "autonomous_scaling",
    "autonomous_recovery",
    "hidden_state_mutation",
    "governance_bypass",
    "execution_outside_spine",
    "recursive_stabilization",
]


class StabilizationBoundaryPolicies:
    """Enforces stabilization boundary policies."""

    def __init__(
        self, overrides: dict[str, int] | None = None,
    ) -> None:
        self._limits = dict(STABILIZATION_LIMITS)
        if overrides:
            for key, value in overrides.items():
                if key in self._limits:
                    self._limits[key] = min(value, STABILIZATION_LIMITS[key])
        self._checks: list[StabilityBoundaryState] = []

    def check_limit(
        self, limit_name: str, current_value: int,
    ) -> dict[str, Any]:
        max_value = self._limits.get(limit_name, 0)
        exceeded = current_value >= max_value

        state = StabilityBoundaryState(
            limit_name=limit_name,
            current_value=current_value,
            max_value=max_value,
            exceeded=exceeded,
        )
        self._checks.append(state)

        return state.to_dict()

    def is_forbidden(self, action: str) -> bool:
        return action in FORBIDDEN_STABILIZATION_ACTIONS

    def get_limits(self) -> dict[str, int]:
        return dict(self._limits)

    def get_forbidden_actions(self) -> list[str]:
        return list(FORBIDDEN_STABILIZATION_ACTIONS)

    def get_all_checks(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._checks]

    def get_exceeded_checks(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._checks if c.exceeded]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_limits": len(self._limits),
            "total_forbidden": len(FORBIDDEN_STABILIZATION_ACTIONS),
            "total_checks": len(self._checks),
            "exceeded_checks": len(self.get_exceeded_checks()),
        }
