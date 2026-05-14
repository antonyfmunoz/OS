"""Convergence Boundary Policies v1.

8 limits and 10 forbidden actions for convergence operations.

UMH substrate subsystem. Phase 96.8CO.
"""

from __future__ import annotations

from typing import Any

from core.convergence.repository_topology_contracts_v1 import _now_iso


CONVERGENCE_LIMITS: dict[str, int] = {
    "max_convergence_runs": 50,
    "max_scans": 50,
    "max_namespace_checks": 100,
    "max_detections": 200,
    "max_quarantines": 200,
    "max_graph_checks": 100,
    "max_entrypoint_checks": 100,
    "max_readiness_checks": 50,
}

FORBIDDEN_CONVERGENCE_ACTIONS = [
    "alternate_runtime_spines",
    "parallel_orchestrators",
    "hidden_runtime_roots",
    "duplicate_governance_layers",
    "duplicate_cognition_systems",
    "duplicate_memory_systems",
    "duplicate_ingestion_systems",
    "shadow_topology_mutation",
    "hidden_namespace_mutation",
    "speculative_runtime_branching",
]


class ConvergenceBoundaryPolicies:
    """Enforces convergence operation boundaries."""

    def __init__(self) -> None:
        self._denied: list[dict[str, Any]] = []

    def check_limit(self, limit_name: str, current_value: int, override: int | None = None) -> dict[str, Any]:
        default = CONVERGENCE_LIMITS.get(limit_name)
        if default is None:
            raise ValueError(f"Unknown limit: {limit_name}")
        effective = min(override, default) if override is not None else default
        allowed = current_value < effective
        result = {
            "limit_name": limit_name,
            "current_value": current_value,
            "effective_limit": effective,
            "allowed": allowed,
            "timestamp": _now_iso(),
        }
        if not allowed:
            self._denied.append(result)
        return result

    def check_forbidden(self, action: str) -> dict[str, Any]:
        forbidden = action in FORBIDDEN_CONVERGENCE_ACTIONS
        result = {
            "action": action,
            "forbidden": forbidden,
            "timestamp": _now_iso(),
        }
        if forbidden:
            self._denied.append(result)
        return result

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_limits": len(CONVERGENCE_LIMITS),
            "total_forbidden": len(FORBIDDEN_CONVERGENCE_ACTIONS),
            "total_denied": len(self._denied),
        }
