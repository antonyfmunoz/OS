"""Accountability Boundary Policies v1.

8 limits, 7 forbidden actions for sovereign accountability.
Override capping: min(override, default).

UMH substrate subsystem. Phase 96.8CL.
"""

from __future__ import annotations

from typing import Any

from core.accountability.sovereign_operational_accountability_contracts_v1 import (
    _now_iso,
)

ACCOUNTABILITY_LIMITS: dict[str, int] = {
    "max_chronology_entries": 200,
    "max_governance_history": 200,
    "max_replay_history": 200,
    "max_continuity_history": 200,
    "max_provenance_history": 100,
    "max_audits": 200,
    "max_integrity_checks": 100,
    "max_accountability_runs": 50,
}

FORBIDDEN_ACCOUNTABILITY_ACTIONS: list[str] = [
    "hidden_chronology_mutation",
    "retroactive_lineage_rewriting",
    "fabricated_accountability",
    "replay_bypass",
    "governance_bypass",
    "recursive_accountability_reconstruction",
    "execution_outside_spine",
]


class AccountabilityBoundaryPolicies:
    def __init__(self) -> None:
        self._checks: list[dict[str, Any]] = []

    def check_limit(self, limit_name: str, current_value: int, override: int | None = None) -> dict[str, Any]:
        default_max = ACCOUNTABILITY_LIMITS.get(limit_name, 0)
        effective_max = min(override, default_max) if override is not None else default_max
        exceeded = current_value > effective_max
        result = {
            "limit_name": limit_name,
            "current_value": current_value,
            "max_value": effective_max,
            "exceeded": exceeded,
        }
        self._checks.append(result)
        return result

    def is_forbidden(self, action: str) -> bool:
        return action in FORBIDDEN_ACCOUNTABILITY_ACTIONS

    def check_all_limits(self, current_values: dict[str, int]) -> dict[str, Any]:
        results = []
        for limit_name in ACCOUNTABILITY_LIMITS:
            val = current_values.get(limit_name, 0)
            r = self.check_limit(limit_name, val)
            results.append(r)
        return {"any_exceeded": any(r["exceeded"] for r in results), "checks": results, "total": len(results)}

    def get_exceeded(self) -> list[dict[str, Any]]:
        return [c for c in self._checks if c["exceeded"]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_checks": len(self._checks),
            "exceeded": sum(1 for c in self._checks if c["exceeded"]),
            "within_bounds": sum(1 for c in self._checks if not c["exceeded"]),
            "forbidden_actions_count": len(FORBIDDEN_ACCOUNTABILITY_ACTIONS),
        }
