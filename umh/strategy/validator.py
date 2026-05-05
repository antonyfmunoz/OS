"""UMH Strategy Validator — structural validation for strategies.

Ensures strategies meet all hard constraints before use:
- bounded step count
- valid dependencies
- no circular references
- serializable output
"""

from __future__ import annotations

from umh.strategy.models import Strategy, StepStatus


MAX_STEPS = 10
MAX_DEPTH = 2


def validate_strategy(strategy: Strategy) -> list[str]:
    """Validate a strategy against structural constraints.

    Returns a list of error strings. Empty list = valid.
    """
    errors: list[str] = []

    # Must have steps
    if not strategy.steps:
        errors.append("strategy has no steps")
        return errors

    # Bounded step count
    if len(strategy.steps) > MAX_STEPS:
        errors.append(f"strategy has {len(strategy.steps)} steps, max is {MAX_STEPS}")

    # Unique step IDs
    ids = [s.id for s in strategy.steps]
    if len(ids) != len(set(ids)):
        errors.append("duplicate step IDs detected")

    # Valid dependencies (reference existing steps)
    id_set = set(ids)
    for step in strategy.steps:
        for dep in step.dependencies:
            if dep not in id_set:
                errors.append(f"step {step.id} depends on unknown step {dep}")

    # No self-dependencies
    for step in strategy.steps:
        if step.id in step.dependencies:
            errors.append(f"step {step.id} depends on itself")

    # No circular dependencies
    cycle = _detect_cycle(strategy)
    if cycle:
        errors.append(f"circular dependency detected: {' → '.join(cycle)}")

    # Must have goal_id
    if not strategy.goal_id:
        errors.append("strategy missing goal_id")

    # Must have objective
    if not strategy.objective:
        errors.append("strategy missing objective")

    # Confidence in range
    if not (0.0 <= strategy.confidence <= 1.0):
        errors.append(f"confidence {strategy.confidence} out of range [0.0, 1.0]")

    # Serializable check
    try:
        d = strategy.to_dict()
        if not isinstance(d, dict):
            errors.append("strategy.to_dict() did not return a dict")
    except Exception as exc:
        errors.append(f"strategy not serializable: {exc}")

    return errors


def _detect_cycle(strategy: Strategy) -> list[str] | None:
    """Detect circular dependencies using DFS. Returns cycle path or None."""
    adj: dict[str, list[str]] = {}
    for step in strategy.steps:
        adj[step.id] = list(step.dependencies)

    visited: set[str] = set()
    in_stack: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> list[str] | None:
        visited.add(node)
        in_stack.add(node)
        path.append(node)

        for neighbor in adj.get(node, []):
            if neighbor in in_stack:
                cycle_start = path.index(neighbor)
                return path[cycle_start:] + [neighbor]
            if neighbor not in visited:
                result = dfs(neighbor)
                if result:
                    return result

        path.pop()
        in_stack.remove(node)
        return None

    for step_id in adj:
        if step_id not in visited:
            result = dfs(step_id)
            if result:
                return result

    return None
