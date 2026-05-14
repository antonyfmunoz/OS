"""Deployment Orchestration Boundary Policies v1.

Enforces hard limits and forbidden actions for deployment orchestration.
8 limits, 10 forbidden actions. Override capping: min(override, default).

UMH substrate subsystem. Phase 96.8CF.
"""

from __future__ import annotations

from typing import Any

ORCHESTRATION_LIMITS: dict[str, int] = {
    "max_operations": 50,
    "max_graph_nodes": 50,
    "max_graph_edges": 100,
    "max_checkpoints": 50,
    "max_routing_depth": 3,
    "max_fanout": 3,
    "max_pending_recoveries": 20,
    "max_sync_operations": 100,
}

FORBIDDEN_ORCHESTRATION_ACTIONS: list[str] = [
    "autonomous_deployment",
    "autonomous_scaling",
    "autonomous_rollback",
    "autonomous_recovery",
    "recursive_orchestration",
    "hidden_topology_mutation",
    "hidden_deployment_mutation",
    "hidden_rollout_expansion",
    "execution_outside_spine",
    "governance_bypass",
]


def enforce_limit(name: str, override: int | None = None) -> int:
    default = ORCHESTRATION_LIMITS.get(name)
    if default is None:
        raise ValueError(f"Unknown limit: {name}")
    if override is None:
        return default
    return min(override, default)


def is_forbidden(action: str) -> bool:
    return action in FORBIDDEN_ORCHESTRATION_ACTIONS


def get_all_limits() -> dict[str, int]:
    return dict(ORCHESTRATION_LIMITS)


def get_all_forbidden() -> list[str]:
    return list(FORBIDDEN_ORCHESTRATION_ACTIONS)


def validate_boundaries() -> dict[str, Any]:
    return {
        "limits_count": len(ORCHESTRATION_LIMITS),
        "forbidden_count": len(FORBIDDEN_ORCHESTRATION_ACTIONS),
        "all_limits": dict(ORCHESTRATION_LIMITS),
        "all_forbidden": list(FORBIDDEN_ORCHESTRATION_ACTIONS),
    }
