"""Learning Boundary Policies v1.

Enforces hard limits and forbidden actions for adaptive learning.
8 limits, 8 forbidden actions. Override capping: min(override, default).

UMH substrate subsystem. Phase 96.8CC.
"""

from __future__ import annotations

from typing import Any

LEARNING_LIMITS: dict[str, int] = {
    "max_pending_proposals": 50,
    "max_total_proposals": 500,
    "max_patterns": 100,
    "max_signals": 1000,
    "max_corrections": 200,
    "max_signals_per_pattern": 50,
    "max_confidence": 1,
    "max_provenance_chain": 20,
}

FORBIDDEN_LEARNING_ACTIONS: list[str] = [
    "autonomous_self_improvement",
    "silent_canonical_mutation",
    "silent_policy_mutation",
    "silent_template_mutation",
    "hidden_routing_mutation",
    "learning_owned_execution",
    "self_authored_objectives",
    "uncontrolled_pattern_promotion",
]


def enforce_limit(name: str, override: int | None = None) -> int:
    default = LEARNING_LIMITS.get(name)
    if default is None:
        raise ValueError(f"Unknown limit: {name}")
    if override is None:
        return default
    return min(override, default)


def is_forbidden(action: str) -> bool:
    return action in FORBIDDEN_LEARNING_ACTIONS


def get_all_limits() -> dict[str, int]:
    return dict(LEARNING_LIMITS)


def get_all_forbidden() -> list[str]:
    return list(FORBIDDEN_LEARNING_ACTIONS)


def validate_boundaries() -> dict[str, Any]:
    return {
        "limits_count": len(LEARNING_LIMITS),
        "forbidden_count": len(FORBIDDEN_LEARNING_ACTIONS),
        "all_limits": dict(LEARNING_LIMITS),
        "all_forbidden": list(FORBIDDEN_LEARNING_ACTIONS),
    }
