"""Knowledge Boundary Policies v1.

Enforces hard limits and forbidden actions for the knowledge fabric.
10 limits, 10 forbidden actions. Override capping: min(override, default).

UMH substrate subsystem. Phase 96.8CB.
"""

from __future__ import annotations

from typing import Any

KNOWLEDGE_LIMITS: dict[str, int] = {
    "max_canonical_nodes": 500,
    "max_instance_nodes": 2000,
    "max_relationships": 500,
    "max_clusters": 50,
    "max_conflicts": 100,
    "max_pending_promotions": 50,
    "max_provenance_chain": 20,
    "max_abstraction_levels": 5,
    "max_evolutions_per_node": 50,
    "max_retrieval_results": 50,
}

FORBIDDEN_KNOWLEDGE_ACTIONS: list[str] = [
    "autonomous_truth_generation",
    "unverified_canonical_promotion",
    "hidden_relationship_creation",
    "recursive_knowledge_loops",
    "uncontrolled_knowledge_growth",
    "silent_provenance_mutation",
    "opaque_reconciliation",
    "self_authored_canonical",
    "hidden_ontology_mutation",
    "unrestricted_evolution_fanout",
]


def enforce_limit(name: str, override: int | None = None) -> int:
    default = KNOWLEDGE_LIMITS.get(name)
    if default is None:
        raise ValueError(f"Unknown limit: {name}")
    if override is None:
        return default
    return min(override, default)


def is_forbidden(action: str) -> bool:
    return action in FORBIDDEN_KNOWLEDGE_ACTIONS


def get_all_limits() -> dict[str, int]:
    return dict(KNOWLEDGE_LIMITS)


def get_all_forbidden() -> list[str]:
    return list(FORBIDDEN_KNOWLEDGE_ACTIONS)


def validate_boundaries() -> dict[str, Any]:
    return {
        "limits_count": len(KNOWLEDGE_LIMITS),
        "forbidden_count": len(FORBIDDEN_KNOWLEDGE_ACTIONS),
        "all_limits": dict(KNOWLEDGE_LIMITS),
        "all_forbidden": list(FORBIDDEN_KNOWLEDGE_ACTIONS),
    }
