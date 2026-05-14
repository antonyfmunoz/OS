"""Resilience Boundary Policies v1.

Hard limits and forbidden actions for resilience coordination.

UMH substrate subsystem. Phase 96.8BZ.
"""

from __future__ import annotations

from typing import Any


RESILIENCE_LIMITS: dict[str, int | float] = {
    "max_recovery_attempts": 3,
    "max_isolation_depth": 3,
    "max_cascade_propagation": 3,
    "max_affected_subsystems": 10,
    "max_active_cascades": 5,
    "max_pending_recommendations": 20,
    "max_checkpoints_per_subsystem": 10,
    "max_tracked_subsystems": 50,
    "minimum_survivability_score": 0.3,
    "max_instability_score": 1.0,
}


FORBIDDEN_RESILIENCE_ACTIONS: list[str] = [
    "autonomous_repair",
    "automatic_rollback",
    "self_directed_healing",
    "hidden_state_mutation",
    "uncontrolled_restart",
    "recursive_recovery_loops",
    "hidden_isolation_bypass",
    "automatic_escalation_execution",
    "uncontrolled_checkpoint_restoration",
    "hidden_survivability_override",
]


def enforce_recovery_bound(attempts: int) -> bool:
    return attempts < RESILIENCE_LIMITS["max_recovery_attempts"]


def enforce_isolation_depth(depth: int) -> bool:
    return depth <= RESILIENCE_LIMITS["max_isolation_depth"]


def enforce_cascade_depth(depth: int) -> bool:
    return depth < RESILIENCE_LIMITS["max_cascade_propagation"]


def enforce_subsystem_limit(count: int) -> bool:
    return count <= RESILIENCE_LIMITS["max_tracked_subsystems"]


def enforce_survivability_floor(score: float) -> bool:
    return score >= RESILIENCE_LIMITS["minimum_survivability_score"]


def cap_override(override: int | float, default: int | float) -> int | float:
    return min(override, default)


def is_forbidden(action: str) -> bool:
    return action in FORBIDDEN_RESILIENCE_ACTIONS


def get_all_limits() -> dict[str, int | float]:
    return dict(RESILIENCE_LIMITS)


def get_all_forbidden() -> list[str]:
    return list(FORBIDDEN_RESILIENCE_ACTIONS)
