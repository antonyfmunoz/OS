"""UMH Attention Scorer — pure priority scoring functions.

All functions are pure: data in, scores out. No global state, no event
emission, no imports from execution/adapters/tools/planning.
"""

from __future__ import annotations

from dataclasses import replace as _replace

from umh.attention.priority import AttentionState, PriorityBreakdown, PriorityEntry
from umh.goals.models import GoalPriority
from umh.orchestrator.task import StepStatus, Task, TaskStatus

# ── Weights ──────────────────────────────────────────────────────────────
_W_IMPORTANCE = 0.30
_W_RECENCY = 0.20
_W_FAILURE = 0.20
_W_DEPENDENCY = 0.20
_W_COST = 0.10  # applied as penalty (subtracted)

# ── Starvation constants ────────────────────────────────────────────────
_STARVATION_RATE = 0.02  # boost per 60s over threshold
_STARVATION_CAP = 0.3


def _score_importance(goal_priority: GoalPriority) -> float:
    """Map goal priority to importance score.

    HIGH = 1.0, MEDIUM = 0.6, LOW = 0.3.
    """
    return {
        GoalPriority.HIGH: 1.0,
        GoalPriority.MEDIUM: 0.6,
        GoalPriority.LOW: 0.3,
    }.get(goal_priority, 0.3)


def _score_recency(age_seconds: float) -> float:
    """Newer tasks score higher. Exponential decay over 1 hour.

    Returns max(0, 1.0 - (age / 3600)). Tasks older than 1 hour get 0.
    """
    return max(0.0, 1.0 - (age_seconds / 3600.0))


def _score_failure_pressure(task: Task) -> float:
    """Higher pressure when steps have retries or failures.

    Each retry_count adds 0.1 (summed across steps), plus 0.3 if any step
    has status FAILED. Capped at 1.0.
    """
    pressure = 0.0
    for step in task.steps:
        pressure += step.retry_count * 0.1
        if step.status == StepStatus.FAILED:
            pressure += 0.3
    return min(pressure, 1.0)


def _score_dependency_value(task: Task, all_tasks: list[Task]) -> float:
    """How many other PENDING tasks depend on this one.

    Dependency detection: a PENDING task's context contains
    ``{"depends_on": task_id}``. Each dependent adds 0.25, capped at 1.0.
    """
    dependents = 0
    for other in all_tasks:
        if other.id == task.id:
            continue
        if other.status != TaskStatus.PENDING:
            continue
        if other.context.get("depends_on") == task.id:
            dependents += 1
    return min(dependents * 0.25, 1.0)


def _score_cost(task: Task) -> float:
    """Penalty based on step count. More steps = more expensive.

    cost_penalty = min(len(steps) / 10, 1.0) * 0.1
    """
    return min(len(task.steps) / 10.0, 1.0) * 0.1


def score_task(
    task: Task,
    goal_priority: GoalPriority,
    age_seconds: float,
    all_tasks: list[Task] | None = None,
) -> PriorityEntry:
    """Score a task and return a fully populated PriorityEntry.

    Args:
        task: The task to score.
        goal_priority: Priority of the parent goal.
        age_seconds: Seconds since the task was created.
        all_tasks: All known tasks (for dependency scoring). Defaults to
            empty list when not provided.

    Returns:
        PriorityEntry with computed score and breakdown.
    """
    if all_tasks is None:
        all_tasks = []

    importance = _score_importance(goal_priority)
    recency = _score_recency(age_seconds)
    failure_pressure = _score_failure_pressure(task)
    dependency_value = _score_dependency_value(task, all_tasks)
    cost_penalty = _score_cost(task)

    breakdown = PriorityBreakdown(
        importance=importance,
        recency=recency,
        failure_pressure=failure_pressure,
        dependency_value=dependency_value,
        cost_penalty=cost_penalty,
    )

    total = (
        importance * _W_IMPORTANCE
        + recency * _W_RECENCY
        + failure_pressure * _W_FAILURE
        + dependency_value * _W_DEPENDENCY
        - cost_penalty * _W_COST
    )

    # Determine attention state from task status
    state_map: dict[TaskStatus, AttentionState] = {
        TaskStatus.PENDING: AttentionState.READY,
        TaskStatus.RUNNING: AttentionState.RUNNING,
        TaskStatus.PAUSED: AttentionState.BLOCKED,
        TaskStatus.COMPLETED: AttentionState.DEFERRED,
        TaskStatus.FAILED: AttentionState.DEFERRED,
        TaskStatus.CANCELLED: AttentionState.DEFERRED,
    }
    state = state_map.get(task.status, AttentionState.READY)

    return PriorityEntry(
        task_id=task.id,
        goal_id=task.context.get("goal_id", ""),
        priority_score=total,
        breakdown=breakdown,
        state=state,
        age_seconds=age_seconds,
        starvation_boost=0.0,
    )


def score_task_with_controls(
    task: Task,
    goal_priority: GoalPriority,
    age_seconds: float,
    all_tasks: list[Task] | None = None,
) -> tuple[PriorityEntry, "ControlInfluence"]:
    """Score a task with system controls applied.

    Returns (adjusted_entry, control_influence).
    Falls back to unmodified score_task if controls are at defaults.
    """
    from umh.attention.controls import (
        ControlInfluence,
        compute_control_influence,
        compute_weight_modifiers,
        get_system_controls,
    )

    # Get base score first
    base_entry = score_task(task, goal_priority, age_seconds, all_tasks)

    controls = get_system_controls()
    mods = compute_weight_modifiers(controls)

    b = base_entry.breakdown
    adjusted_score = (
        b.importance * _W_IMPORTANCE * mods["importance_mod"]
        + b.recency * _W_RECENCY * mods["recency_mod"]
        + b.failure_pressure * _W_FAILURE * mods["failure_mod"]
        + b.dependency_value * _W_DEPENDENCY * mods["dependency_mod"]
        - b.cost_penalty * _W_COST * mods["cost_mod"]
    )

    # Apply cost_sensitivity: higher sensitivity -> bigger cost penalty
    cost_adjustment = b.cost_penalty * controls.cost_sensitivity * 0.05
    adjusted_score -= cost_adjustment

    # Apply failure_tolerance: higher tolerance -> less failure pressure boost
    if controls.failure_tolerance > 0.5:
        failure_dampening = b.failure_pressure * (controls.failure_tolerance - 0.5) * 0.1
        adjusted_score -= failure_dampening

    influence = compute_control_influence(controls, base_entry.priority_score, adjusted_score)

    adjusted_entry = _replace(
        base_entry,
        priority_score=adjusted_score,
    )

    return adjusted_entry, influence


def apply_starvation_boost(
    entry: PriorityEntry,
    current_age_seconds: float,
    threshold: float = 600.0,
) -> PriorityEntry:
    """Apply starvation boost to a priority entry.

    If current_age > threshold and state is READY, add 0.02 per 60 seconds
    over threshold. Cap boost at 0.3. If boost > 0 and entry was READY,
    change state to STARVED.

    Returns a new PriorityEntry (does not mutate the original).
    """
    if entry.state != AttentionState.READY:
        return entry
    if current_age_seconds <= threshold:
        return entry

    over = current_age_seconds - threshold
    boost = min((over / 60.0) * _STARVATION_RATE, _STARVATION_CAP)

    if boost <= 0:
        return entry

    return _replace(
        entry,
        priority_score=entry.priority_score + boost,
        starvation_boost=boost,
        age_seconds=current_age_seconds,
        state=AttentionState.STARVED,
    )
