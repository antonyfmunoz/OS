"""UMH Strategy Decomposer — goal-to-strategy transformation.

Converts a Goal into a Strategy using deterministic templates first,
then falls back to a structured LLM call if no template matches.

This module is PURE: no execution, no side effects, no tool calls.
It only transforms data structures.
"""

from __future__ import annotations

import logging
import threading

from umh.core.clock import iso_now as _iso_now
from umh.events.stream import publish as _publish_event
from umh.goals.models import Goal
from umh.strategy.models import (
    ApproachType,
    StepComplexity,
    StepType,
    Strategy,
    StrategyStep,
)
from umh.strategy.templates import match_template
from umh.strategy.validator import validate_strategy

_log = logging.getLogger(__name__)


def decompose_goal(goal: Goal) -> Strategy:
    """Decompose a goal into a structured strategy.

    1. Tries deterministic templates first.
    2. Falls back to structured LLM call if no template matches.
    3. Validates the strategy before returning.

    Returns a validated Strategy. Raises ValueError on validation failure.
    """
    # Step 1: Try templates (deterministic, no LLM)
    strategy = match_template(goal.id, goal.objective)
    if strategy is not None:
        _log.info("Goal %s matched template '%s'", goal.id, strategy.template_used)
        errors = validate_strategy(strategy)
        if errors:
            raise ValueError(f"Template strategy validation failed: {'; '.join(errors)}")
        _publish_event(
            "strategy.created",
            payload={
                "goal_id": goal.id,
                "strategy_id": strategy.id,
                "template": strategy.template_used,
                "steps": len(strategy.steps),
            },
            actor_id=f"goal:{goal.id}",
        )
        return strategy

    # Step 2: Fallback to structured LLM decomposition
    strategy = _llm_decompose(goal)
    errors = validate_strategy(strategy)
    if errors:
        raise ValueError(f"LLM strategy validation failed: {'; '.join(errors)}")

    _publish_event(
        "strategy.created",
        payload={
            "goal_id": goal.id,
            "strategy_id": strategy.id,
            "template": "llm_fallback",
            "steps": len(strategy.steps),
        },
        actor_id=f"goal:{goal.id}",
    )
    return strategy


def _llm_decompose(goal: Goal) -> Strategy:
    """Fallback LLM-based decomposition with strict schema enforcement.

    Uses a structured prompt to generate strategy steps. The LLM output
    is parsed into fixed StrategyStep objects — no freeform content.

    If the LLM call fails or returns unparseable output, falls back to
    a generic 3-step strategy (research → execute → validate).
    """
    try:
        from umh.planning.planner import _call_llm_for_plan
    except ImportError:
        _log.warning("LLM planning not available, using generic fallback")
        return _generic_fallback(goal)

    prompt = (
        f"Decompose this goal into 3-6 concrete steps.\n"
        f"Goal: {goal.objective}\n"
        f"Priority: {goal.priority.value}\n"
        f"Constraints: {goal.constraints}\n\n"
        f"For each step, provide:\n"
        f"- description (one sentence)\n"
        f"- type (research|execution|validation|decision)\n"
        f"- complexity (low|medium|high)\n\n"
        f"Format each step as: STEP|description|type|complexity\n"
        f"One step per line. No other output."
    )

    try:
        raw = _call_llm_for_plan(prompt)
        steps = _parse_llm_steps(raw)
        if not steps:
            return _generic_fallback(goal)
    except Exception:
        _log.warning("LLM decomposition failed for goal %s, using generic fallback", goal.id)
        return _generic_fallback(goal)

    strategy = Strategy(
        goal_id=goal.id,
        objective=goal.objective,
        approach_type=ApproachType.LINEAR,
        steps=steps,
        confidence=0.7,
        reasoning="LLM-generated decomposition with strict schema",
        template_used="llm_fallback",
    )

    # Wire sequential dependencies
    if len(strategy.steps) > 1:
        for i in range(1, len(strategy.steps)):
            strategy.steps[i].dependencies = [strategy.steps[i - 1].id]

    return strategy


def _parse_llm_steps(raw: str) -> list[StrategyStep]:
    """Parse structured LLM output into StrategyStep list.

    Expected format: STEP|description|type|complexity (one per line)
    """
    steps: list[StrategyStep] = []
    type_map = {
        "research": StepType.RESEARCH,
        "execution": StepType.EXECUTION,
        "validation": StepType.VALIDATION,
        "decision": StepType.DECISION,
    }
    complexity_map = {
        "low": StepComplexity.LOW,
        "medium": StepComplexity.MEDIUM,
        "high": StepComplexity.HIGH,
    }

    for line in raw.strip().splitlines():
        line = line.strip()
        if not line.startswith("STEP|"):
            continue
        parts = line.split("|")
        if len(parts) < 4:
            continue
        desc = parts[1].strip()
        step_type = type_map.get(parts[2].strip().lower(), StepType.EXECUTION)
        complexity = complexity_map.get(parts[3].strip().lower(), StepComplexity.MEDIUM)

        if desc:
            steps.append(
                StrategyStep(
                    description=desc,
                    type=step_type,
                    estimated_complexity=complexity,
                    generates_tasks=True,
                )
            )

    return steps[:6]  # Cap at 6 steps max


def _generic_fallback(goal: Goal) -> Strategy:
    """Produce a minimal 3-step strategy when templates and LLM both fail."""
    return Strategy(
        goal_id=goal.id,
        objective=goal.objective,
        approach_type=ApproachType.LINEAR,
        confidence=0.5,
        reasoning="Generic fallback: no template match and LLM unavailable",
        template_used="generic_fallback",
        steps=[
            StrategyStep(
                description=f"Research and plan approach for: {goal.objective}",
                type=StepType.RESEARCH,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Execute primary actions for: {goal.objective}",
                type=StepType.EXECUTION,
                estimated_complexity=StepComplexity.HIGH,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Validate results for: {goal.objective}",
                type=StepType.VALIDATION,
                estimated_complexity=StepComplexity.LOW,
                generates_tasks=True,
            ),
        ],
    )


# ── Strategy Cache ───────────────────────────────────────────────

_cache: dict[str, Strategy] = {}
_cache_lock = threading.Lock()


def get_cached_strategy(goal_id: str) -> Strategy | None:
    """Return cached strategy for a goal, or None."""
    with _cache_lock:
        return _cache.get(goal_id)


def cache_strategy(strategy: Strategy) -> None:
    """Cache a strategy by its goal_id."""
    with _cache_lock:
        _cache[strategy.goal_id] = strategy


def invalidate_strategy(goal_id: str) -> bool:
    """Remove cached strategy. Returns True if it existed."""
    with _cache_lock:
        return _cache.pop(goal_id, None) is not None


def reset_strategy_cache() -> None:
    """Clear all cached strategies (for testing)."""
    with _cache_lock:
        _cache.clear()
