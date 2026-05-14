"""Constitutional Boundary Policies v1.

Prevents subsystem semantic drift, replay/lifecycle/topology/continuity/
observability drift, governance bypass, and execution outside spine.

8 limits, 8 forbidden actions. Override capping: min(override, default).

UMH substrate subsystem. Phase 96.8CG.
"""

from __future__ import annotations

from typing import Any

CONSTITUTIONAL_LIMITS: dict[str, int] = {
    "max_invariants": 100,
    "max_violations": 50,
    "max_topology_domains": 10,
    "max_continuity_layers": 10,
    "max_lifecycle_layers": 25,
    "max_observability_layers": 25,
    "max_replay_layers": 25,
    "max_drift_domains": 10,
}

FORBIDDEN_CONSTITUTIONAL_ACTIONS: list[str] = [
    "subsystem_semantic_drift",
    "replay_semantic_drift",
    "lifecycle_semantic_drift",
    "topology_semantic_drift",
    "continuity_semantic_drift",
    "observability_semantic_drift",
    "governance_bypass",
    "execution_outside_spine",
]


def enforce_limit(name: str, override: int | None = None) -> int:
    default = CONSTITUTIONAL_LIMITS.get(name)
    if default is None:
        raise ValueError(f"Unknown limit: {name}")
    if override is None:
        return default
    return min(override, default)


def is_forbidden(action: str) -> bool:
    return action in FORBIDDEN_CONSTITUTIONAL_ACTIONS


def get_all_limits() -> dict[str, int]:
    return dict(CONSTITUTIONAL_LIMITS)


def get_all_forbidden() -> list[str]:
    return list(FORBIDDEN_CONSTITUTIONAL_ACTIONS)


def validate_boundaries() -> dict[str, Any]:
    return {
        "limits_count": len(CONSTITUTIONAL_LIMITS),
        "forbidden_count": len(FORBIDDEN_CONSTITUTIONAL_ACTIONS),
        "all_limits": dict(CONSTITUTIONAL_LIMITS),
        "all_forbidden": list(FORBIDDEN_CONSTITUTIONAL_ACTIONS),
    }
