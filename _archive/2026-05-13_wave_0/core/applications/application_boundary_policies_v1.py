"""Application Boundary Policies v1.

Enforces hard limits and forbidden actions for application projections.
8 limits, 8 forbidden actions. Override capping: min(override, default).

UMH substrate subsystem. Phase 96.8CD.
"""

from __future__ import annotations

from typing import Any

APPLICATION_LIMITS: dict[str, int] = {
    "max_applications": 20,
    "max_projections_per_app": 10,
    "max_capabilities_per_app": 9,
    "max_active_contexts": 10,
    "max_checkpoints_per_app": 20,
    "max_bindings_per_app": 50,
    "max_session_chain": 50,
    "max_topology_nodes": 30,
}

FORBIDDEN_APPLICATION_ACTIONS: list[str] = [
    "application_owned_orchestration",
    "application_owned_cognition",
    "application_owned_governance",
    "application_owned_canonical_memory",
    "application_owned_learning_mutation",
    "direct_adapter_execution",
    "substrate_bypass",
    "hidden_domain_escalation",
]


def enforce_limit(name: str, override: int | None = None) -> int:
    default = APPLICATION_LIMITS.get(name)
    if default is None:
        raise ValueError(f"Unknown limit: {name}")
    if override is None:
        return default
    return min(override, default)


def is_forbidden(action: str) -> bool:
    return action in FORBIDDEN_APPLICATION_ACTIONS


def get_all_limits() -> dict[str, int]:
    return dict(APPLICATION_LIMITS)


def get_all_forbidden() -> list[str]:
    return list(FORBIDDEN_APPLICATION_ACTIONS)


def validate_boundaries() -> dict[str, Any]:
    return {
        "limits_count": len(APPLICATION_LIMITS),
        "forbidden_count": len(FORBIDDEN_APPLICATION_ACTIONS),
        "all_limits": dict(APPLICATION_LIMITS),
        "all_forbidden": list(FORBIDDEN_APPLICATION_ACTIONS),
    }
