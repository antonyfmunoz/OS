"""Capability Matcher — selects the best execution resource for a composition.

Given a set of primitives, an objective, and constraints, the matcher
scores every registered capability and returns a ranked selection.
Scoring is a weighted combination of:

    task_fit       (0.4) — does this capability support the required task type?
    constraint_fit (0.3) — does it meet budget/latency/quality constraints?
    quality_score  (0.3) — effective quality (static baseline + adaptive learning)

Every decision is fully traceable: the CapabilitySelection includes the
reasoning, per-dimension scores, and ranked alternatives.

Usage:
    from core.matcher import match_capability

    selection = match_capability(
        primitives={PrimitiveTag.STATE, PrimitiveTag.GOAL, PrimitiveTag.ACTION},
        objective="generate outreach for ICP",
        constraints={"budget": "low", "quality": "high"},
    )
    print(selection.selected.name, selection.score, selection.reasoning)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.capabilities import Capability, list_capabilities
from core.primitives import PrimitiveTag


# ---------------------------------------------------------------------------
# Primitive → task type mapping
# ---------------------------------------------------------------------------

# Maps primitive tags to the task types they typically require.
# A composition with STATE + GOAL + SIGNAL → {"analysis", "strategy", "reasoning"}.
_PRIMITIVE_TASK_MAP: dict[PrimitiveTag, set[str]] = {
    PrimitiveTag.STATE: {"analysis", "reasoning"},
    PrimitiveTag.CHANGE: {"execution", "transformation"},
    PrimitiveTag.CONSTRAINT: {"reasoning", "analysis"},
    PrimitiveTag.RESOURCE: {"computation", "execution"},
    PrimitiveTag.TIME: {"computation", "execution"},
    PrimitiveTag.SIGNAL: {"analysis", "generation", "composition"},
    PrimitiveTag.FEEDBACK: {"analysis", "reasoning"},
    PrimitiveTag.GOAL: {"strategy", "planning", "reasoning"},
    PrimitiveTag.ACTION: {"execution", "generation", "composition"},
    PrimitiveTag.OUTCOME: {"analysis", "computation"},
}

# Objective keywords → additional required task types.
_OBJECTIVE_TASK_MAP: list[tuple[list[str], set[str]]] = [
    (["strategy", "plan", "decide"], {"strategy", "planning", "reasoning"}),
    (
        ["generate", "write", "compose", "create", "draft"],
        {"generation", "composition"},
    ),
    (["execute", "run", "deploy", "send"], {"execution"}),
    (["analyse", "analyze", "evaluate", "assess", "review"], {"analysis", "reasoning"}),
    (["format", "transform", "convert"], {"formatting", "transformation"}),
    (["track", "measure", "compute", "calculate"], {"computation"}),
    (["approve", "review", "judge"], {"approval", "review"}),
]


def _derive_required_tasks(
    primitives: set[PrimitiveTag],
    objective: str,
) -> set[str]:
    """Determine which task types this composition requires."""
    tasks: set[str] = set()

    # From primitives
    for prim in primitives:
        tasks.update(_PRIMITIVE_TASK_MAP.get(prim, set()))

    # From objective keywords
    obj_lower = objective.lower()
    for keywords, task_set in _OBJECTIVE_TASK_MAP:
        if any(kw in obj_lower for kw in keywords):
            tasks.update(task_set)

    return tasks or {"execution"}  # fallback


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------


def _task_fit_score(cap: Capability, required_tasks: set[str]) -> float:
    """How well the capability covers the required task types (0.0–1.0)."""
    if not required_tasks:
        return 0.5
    supported = set(cap.supported_tasks)
    overlap = required_tasks & supported
    return len(overlap) / len(required_tasks)


def _constraint_fit_score(cap: Capability, constraints: dict[str, Any]) -> float:
    """How well the capability meets explicit constraints (0.0–1.0).

    Recognised constraint keys:
        budget:  "low" | "medium" | "high" | float (0-1 threshold)
        latency: "low" | "medium" | "high" | float (0-1 threshold)
        quality: "low" | "medium" | "high" | float (0-1 threshold)
    """
    if not constraints:
        return 0.8  # no constraints = mildly favorable

    scores: list[float] = []

    # Budget constraint
    budget = constraints.get("budget")
    if budget is not None:
        threshold = _to_threshold(budget, invert=True)
        scores.append(1.0 if cap.cost <= threshold else max(0.0, 1.0 - cap.cost))

    # Latency constraint
    latency = constraints.get("latency")
    if latency is not None:
        threshold = _to_threshold(latency, invert=True)
        scores.append(1.0 if cap.latency <= threshold else max(0.0, 1.0 - cap.latency))

    # Quality constraint
    quality = constraints.get("quality")
    if quality is not None:
        threshold = _to_threshold(quality, invert=False)
        eq = cap.effective_quality()
        scores.append(1.0 if eq >= threshold else eq / threshold if threshold else 0.0)

    return sum(scores) / len(scores) if scores else 0.8


def _to_threshold(value: Any, *, invert: bool) -> float:
    """Convert a constraint value to a 0-1 threshold.

    For budget/latency (invert=True): "low" → 0.3, "high" → 0.8.
    For quality (invert=False): "low" → 0.3, "high" → 0.8.
    """
    if isinstance(value, (int, float)):
        return float(value)
    level_map = {"low": 0.3, "medium": 0.5, "high": 0.8}
    return level_map.get(str(value).lower(), 0.5)


# ---------------------------------------------------------------------------
# Selection result
# ---------------------------------------------------------------------------


@dataclass
class CapabilityScore:
    """Detailed score breakdown for a single capability."""

    capability: Capability
    task_fit: float
    constraint_fit: float
    quality: float
    final_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability.name,
            "task_fit": round(self.task_fit, 4),
            "constraint_fit": round(self.constraint_fit, 4),
            "quality": round(self.quality, 4),
            "final_score": round(self.final_score, 4),
        }


@dataclass
class CapabilitySelection:
    """The output of match_capability() — a scored, ranked selection.

    Includes the winner, its reasoning, and all ranked alternatives
    so the router can fall back if the primary fails.
    """

    selected: Capability
    score: float
    reasoning: list[str]
    required_tasks: set[str]
    alternatives: list[CapabilityScore]
    all_scores: list[CapabilityScore] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": self.selected.name,
            "selected_type": self.selected.type,
            "score": round(self.score, 4),
            "reasoning": self.reasoning,
            "required_tasks": sorted(self.required_tasks),
            "alternatives": [a.to_dict() for a in self.alternatives],
            "all_scores": [s.to_dict() for s in self.all_scores],
        }


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

# Scoring weights
_W_TASK = 0.4
_W_CONSTRAINT = 0.3
_W_QUALITY = 0.3


def match_capability(
    primitives: set[PrimitiveTag],
    objective: str,
    constraints: dict[str, Any] | None = None,
    *,
    type_filter: str | None = None,
    exclude: set[str] | None = None,
) -> CapabilitySelection:
    """Select the best capability for executing a primitive composition.

    Args:
        primitives:   Active L0 primitive tags.
        objective:    Natural-language description of the goal.
        constraints:  Budget/latency/quality constraints.
        type_filter:  Optional — only consider capabilities of this type.
        exclude:      Capability names to exclude (e.g. after a failure).

    Returns:
        CapabilitySelection with the best match, score, reasoning,
        and ranked alternatives.
    """
    constraints = constraints or {}
    exclude = exclude or set()

    required_tasks = _derive_required_tasks(primitives, objective)
    candidates = list_capabilities(type_filter=type_filter)
    candidates = [c for c in candidates if c.name not in exclude]

    if not candidates:
        # No candidates at all — create a minimal fallback
        from core.capabilities import CAPABILITY_REGISTRY

        fallback = next(iter(CAPABILITY_REGISTRY.values()))
        return CapabilitySelection(
            selected=fallback,
            score=0.0,
            reasoning=["no candidates available — using registry fallback"],
            required_tasks=required_tasks,
            alternatives=[],
        )

    scored: list[CapabilityScore] = []
    reasoning: list[str] = []

    for cap in candidates:
        tf = _task_fit_score(cap, required_tasks)
        cf = _constraint_fit_score(cap, constraints)
        eq = cap.effective_quality()
        final = tf * _W_TASK + cf * _W_CONSTRAINT + eq * _W_QUALITY

        scored.append(
            CapabilityScore(
                capability=cap,
                task_fit=tf,
                constraint_fit=cf,
                quality=eq,
                final_score=final,
            )
        )

    # Sort by score descending
    scored.sort(key=lambda s: s.final_score, reverse=True)
    best = scored[0]

    # Build reasoning
    reasoning.append(f"required tasks: {sorted(required_tasks)}")
    reasoning.append(
        f"selected {best.capability.name} "
        f"(task_fit={best.task_fit:.2f}, constraint_fit={best.constraint_fit:.2f}, "
        f"quality={best.quality:.2f}, final={best.final_score:.2f})"
    )
    if len(scored) > 1:
        runner_up = scored[1]
        reasoning.append(
            f"runner-up: {runner_up.capability.name} "
            f"(final={runner_up.final_score:.2f})"
        )
    if best.capability.performance.total_runs > 0:
        perf = best.capability.performance
        reasoning.append(
            f"adaptive data: {perf.total_runs} runs, "
            f"success_rate={perf.success_rate:.2f}, "
            f"avg_latency={perf.avg_latency_s:.2f}s"
        )

    return CapabilitySelection(
        selected=best.capability,
        score=best.final_score,
        reasoning=reasoning,
        required_tasks=required_tasks,
        alternatives=scored[1:],
        all_scores=scored,
    )


def match_for_step(
    step_description: str,
    primitives: set[PrimitiveTag],
    constraints: dict[str, Any] | None = None,
    *,
    exclude: set[str] | None = None,
) -> CapabilitySelection:
    """Match a capability for a single pipeline step.

    Convenience wrapper that uses the step description as the objective.
    """
    return match_capability(
        primitives=primitives,
        objective=step_description,
        constraints=constraints,
        exclude=exclude,
    )


__all__ = [
    "CapabilitySelection",
    "CapabilityScore",
    "match_capability",
    "match_for_step",
]
