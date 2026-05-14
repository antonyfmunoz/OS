"""Deployment Boundary Policies v1.

Enforces hard limits and forbidden actions for deployments.
8 limits, 10 forbidden actions. Override capping: min(override, default).

UMH substrate subsystem. Phase 96.8CE.
"""

from __future__ import annotations

from typing import Any

DEPLOYMENT_LIMITS: dict[str, int] = {
    "max_deployments": 50,
    "max_manifests": 50,
    "max_environments": 15,
    "max_rollout_stages": 10,
    "max_active_rollouts": 3,
    "max_rollbacks": 20,
    "max_fanout": 3,
    "max_provisioning_checks": 50,
}

FORBIDDEN_DEPLOYMENT_ACTIONS: list[str] = [
    "autonomous_deployment",
    "autonomous_provisioning",
    "hidden_environment_mutation",
    "hidden_rollout_expansion",
    "deployment_owned_orchestration",
    "deployment_owned_cognition",
    "replay_bypass",
    "governance_bypass",
    "uncontrolled_fanout",
    "recursive_rollout_loops",
]


def enforce_limit(name: str, override: int | None = None) -> int:
    default = DEPLOYMENT_LIMITS.get(name)
    if default is None:
        raise ValueError(f"Unknown limit: {name}")
    if override is None:
        return default
    return min(override, default)


def is_forbidden(action: str) -> bool:
    return action in FORBIDDEN_DEPLOYMENT_ACTIONS


def get_all_limits() -> dict[str, int]:
    return dict(DEPLOYMENT_LIMITS)


def get_all_forbidden() -> list[str]:
    return list(FORBIDDEN_DEPLOYMENT_ACTIONS)


def validate_boundaries() -> dict[str, Any]:
    return {
        "limits_count": len(DEPLOYMENT_LIMITS),
        "forbidden_count": len(FORBIDDEN_DEPLOYMENT_ACTIONS),
        "all_limits": dict(DEPLOYMENT_LIMITS),
        "all_forbidden": list(FORBIDDEN_DEPLOYMENT_ACTIONS),
    }
