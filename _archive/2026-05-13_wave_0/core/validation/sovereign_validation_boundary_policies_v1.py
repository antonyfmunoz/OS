"""Sovereign Validation Boundary Policies v1.

8 limits, 8 forbidden actions for sovereign validation.
Override capping: min(override, default).

UMH substrate subsystem. Phase 96.8CJ.
"""

from __future__ import annotations

from typing import Any

from core.validation.sovereign_operational_validation_contracts_v1 import (
    ValidationBoundaryState,
    _now_iso,
)

SOVEREIGN_VALIDATION_LIMITS: dict[str, int] = {
    "max_governance_attacks": 100,
    "max_replay_attacks": 100,
    "max_continuity_attacks": 100,
    "max_topology_attacks": 100,
    "max_semantic_attacks": 100,
    "max_integrity_checks": 100,
    "max_pressure_simulations": 100,
    "max_validation_runs": 50,
}

FORBIDDEN_VALIDATION_ACTIONS: list[str] = [
    "autonomous_adaptation",
    "autonomous_healing",
    "autonomous_defense",
    "governance_bypass",
    "replay_bypass",
    "observability_bypass",
    "execution_outside_spine",
    "recursive_validation",
]


class SovereignValidationBoundaryPolicies:
    def __init__(self) -> None:
        self._checks: list[ValidationBoundaryState] = []

    def check_limit(self, limit_name: str, current_value: int, override: int | None = None) -> dict[str, Any]:
        default_max = SOVEREIGN_VALIDATION_LIMITS.get(limit_name, 0)
        effective_max = min(override, default_max) if override is not None else default_max
        exceeded = current_value > effective_max
        state = ValidationBoundaryState(
            limit_name=limit_name,
            current_value=current_value,
            max_value=effective_max,
            exceeded=exceeded,
        )
        self._checks.append(state)
        return state.to_dict()

    def is_forbidden(self, action: str) -> bool:
        return action in FORBIDDEN_VALIDATION_ACTIONS

    def check_all_limits(self, current_values: dict[str, int]) -> dict[str, Any]:
        results = []
        for limit_name in SOVEREIGN_VALIDATION_LIMITS:
            val = current_values.get(limit_name, 0)
            r = self.check_limit(limit_name, val)
            results.append(r)
        return {"any_exceeded": any(r["exceeded"] for r in results), "checks": results, "total": len(results)}

    def get_exceeded(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._checks if c.exceeded]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_checks": len(self._checks),
            "exceeded": sum(1 for c in self._checks if c.exceeded),
            "within_bounds": sum(1 for c in self._checks if not c.exceeded),
            "forbidden_actions_count": len(FORBIDDEN_VALIDATION_ACTIONS),
        }
