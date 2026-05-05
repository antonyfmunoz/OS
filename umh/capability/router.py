"""Capability router — selects the best capability for an operation.

Routes operations to capabilities using multi-dimensional scoring:
  - generation_need vs generation_quality (NL output quality)
  - determinism_need vs determinism (structured/repeatable output)
  - type affinity (operation → capability type preference)
  - performance history (success rate)
  - cost constraints

Produces a ranked list with fallback chain. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.capability.registry import Capability, get_registry


@dataclass(frozen=True)
class RoutingDecision:
    """Result of capability routing."""

    selected: Capability | None
    fallback_chain: tuple[Capability, ...]
    scores: dict[str, float]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": self.selected.name if self.selected else None,
            "fallback_chain": [c.name for c in self.fallback_chain],
            "scores": {k: round(v, 4) for k, v in self.scores.items()},
            "reason": self.reason,
        }


@dataclass(frozen=True)
class _OperationProfile:
    """Scoring weights for an operation type."""

    generation_need: float
    determinism_need: float
    preferred_types: tuple[str, ...]


_OPERATION_PROFILES: dict[str, _OperationProfile] = {
    "answer_query": _OperationProfile(
        generation_need=0.8,
        determinism_need=0.2,
        preferred_types=("llm", "runtime"),
    ),
    "run_analysis": _OperationProfile(
        generation_need=0.7,
        determinism_need=0.4,
        preferred_types=("llm", "runtime"),
    ),
    "execute_action": _OperationProfile(
        generation_need=0.1,
        determinism_need=0.9,
        preferred_types=("runtime", "shell", "browser"),
    ),
    "create_artifact": _OperationProfile(
        generation_need=0.9,
        determinism_need=0.1,
        preferred_types=("llm", "runtime"),
    ),
    "check_status": _OperationProfile(
        generation_need=0.1,
        determinism_need=0.9,
        preferred_types=("runtime", "shell"),
    ),
    "process_input": _OperationProfile(
        generation_need=0.6,
        determinism_need=0.3,
        preferred_types=("llm", "runtime"),
    ),
}

_DEFAULT_PROFILE = _OperationProfile(
    generation_need=0.5,
    determinism_need=0.5,
    preferred_types=("runtime",),
)


def route_to_capability(
    operation: str,
    constraints: dict[str, Any] | None = None,
) -> RoutingDecision:
    """Select the best available capability for the given operation.

    Scoring formula:
      base        = quality_score * 0.3
      generation  = generation_need * generation_quality * 0.3
      determinism = determinism_need * cap_determinism * 0.2
      type_match  = 0.1 if type in preferred_types
      history     = 0.1 * success_rate
      cost_pen    = -0.05 if cost > budget
    """
    registry = get_registry()
    available = registry.list_available()

    if not available:
        return RoutingDecision(
            selected=None,
            fallback_chain=(),
            scores={},
            reason="No capabilities available",
        )

    constraints = constraints or {}
    profile = _OPERATION_PROFILES.get(operation, _DEFAULT_PROFILE)
    budget = constraints.get("max_cost_usd", float("inf"))

    scored: list[tuple[float, Capability]] = []
    score_map: dict[str, float] = {}

    for cap in available:
        gen_q = cap.metadata.get("generation_quality", 0.0)
        det = cap.metadata.get("determinism", 0.5)

        score = cap.quality_score * 0.3
        score += profile.generation_need * gen_q * 0.3
        score += profile.determinism_need * det * 0.2

        if cap.capability_type in profile.preferred_types:
            score += 0.1

        score += 0.1 * cap.performance.success_rate

        if cap.cost_per_call > budget:
            score -= 0.05

        scored.append((score, cap))
        score_map[cap.name] = score

    scored.sort(key=lambda x: x[0], reverse=True)

    selected = scored[0][1]
    fallback = tuple(cap for _, cap in scored[1:])

    return RoutingDecision(
        selected=selected,
        fallback_chain=fallback,
        scores=score_map,
        reason=f"Selected {selected.name} ({selected.capability_type}) "
        f"with score {score_map[selected.name]:.3f}",
    )
