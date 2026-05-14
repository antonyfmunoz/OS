"""Intelligence Boundary Policies v1.

Hard limits and forbidden actions for intelligence coordination.

UMH substrate subsystem. Phase 96.8CA.
"""

from __future__ import annotations

from typing import Any


INTELLIGENCE_LIMITS: dict[str, int | float] = {
    "max_context_window": 50,
    "max_reasoning_depth": 5,
    "max_reasoning_chain": 10,
    "max_signal_clusters": 20,
    "max_synthesis_sources": 9,
    "max_routing_depth": 5,
    "max_routing_fanout": 3,
    "max_priority_signals": 20,
    "max_compression_ratio": 1.0,
    "max_anchors": 50,
}


FORBIDDEN_INTELLIGENCE_ACTIONS: list[str] = [
    "autonomous_reasoning",
    "recursive_cognition_loops",
    "uncontrolled_context_growth",
    "hidden_planning",
    "self_authored_goals",
    "hidden_prioritization_mutation",
    "cognition_owned_execution",
    "unrestricted_synthesis_fanout",
    "silent_intent_mutation",
    "opaque_reasoning_generation",
]


def enforce_context_window(size: int) -> bool:
    return size <= INTELLIGENCE_LIMITS["max_context_window"]


def enforce_reasoning_depth(depth: int) -> bool:
    return depth <= INTELLIGENCE_LIMITS["max_reasoning_depth"]


def enforce_routing_depth(depth: int) -> bool:
    return depth <= INTELLIGENCE_LIMITS["max_routing_depth"]


def enforce_routing_fanout(fanout: int) -> bool:
    return fanout <= INTELLIGENCE_LIMITS["max_routing_fanout"]


def enforce_signal_clusters(count: int) -> bool:
    return count <= INTELLIGENCE_LIMITS["max_signal_clusters"]


def enforce_synthesis_sources(count: int) -> bool:
    return count <= INTELLIGENCE_LIMITS["max_synthesis_sources"]


def cap_override(override: int | float, default: int | float) -> int | float:
    return min(override, default)


def is_forbidden(action: str) -> bool:
    return action in FORBIDDEN_INTELLIGENCE_ACTIONS


def get_all_limits() -> dict[str, int | float]:
    return dict(INTELLIGENCE_LIMITS)


def get_all_forbidden() -> list[str]:
    return list(FORBIDDEN_INTELLIGENCE_ACTIONS)
