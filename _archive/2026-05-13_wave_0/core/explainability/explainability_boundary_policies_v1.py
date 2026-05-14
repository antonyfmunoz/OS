"""Explainability Boundary Policies v1.

8 limits, 8 forbidden actions for constitutional explainability.
Override capping: min(override, default).

UMH substrate subsystem. Phase 96.8CK.
"""

from __future__ import annotations

from typing import Any

from core.explainability.constitutional_explainability_contracts_v1 import (
    _now_iso,
)

EXPLAINABILITY_LIMITS: dict[str, int] = {
    "max_explanations": 200,
    "max_lineage_entries": 200,
    "max_justifications": 200,
    "max_replay_explanations": 200,
    "max_continuity_explanations": 200,
    "max_provenance_graphs": 100,
    "max_reasoning_traces": 200,
    "max_explanation_runs": 50,
}

FORBIDDEN_EXPLAINABILITY_ACTIONS: list[str] = [
    "fabricated_explanations",
    "hallucinated_causality",
    "hidden_provenance_mutation",
    "unstored_reasoning_synthesis",
    "explanation_owned_execution",
    "governance_bypass",
    "replay_bypass",
    "recursive_explainability_loops",
]


class ExplainabilityBoundaryPolicies:
    def __init__(self) -> None:
        self._checks: list[dict[str, Any]] = []

    def check_limit(self, limit_name: str, current_value: int, override: int | None = None) -> dict[str, Any]:
        default_max = EXPLAINABILITY_LIMITS.get(limit_name, 0)
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
        return action in FORBIDDEN_EXPLAINABILITY_ACTIONS

    def check_all_limits(self, current_values: dict[str, int]) -> dict[str, Any]:
        results = []
        for limit_name in EXPLAINABILITY_LIMITS:
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
            "forbidden_actions_count": len(FORBIDDEN_EXPLAINABILITY_ACTIONS),
        }
