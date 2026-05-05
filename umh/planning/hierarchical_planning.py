"""
Hierarchical Planning — multi-step goal sequences with temporal dependencies.

Enables the system to plan, evaluate, and execute ordered goal sequences
where later steps depend on earlier steps completing successfully.

Plan generation triggers:
    A. MetaGoalEngine produces related goals (shared parent or criteria overlap)
    B. CounterfactualEvaluator detects strong trajectory chains
    C. Horizon signal indicates delayed payoff potential

Plan scoring::

    plan_score = product(step_utilities)
              * alignment_consistency
              * resource_feasibility
              * horizon_value

Plans compete against single goals in GoalArbitrator via plan_to_utility()
which converts a plan's next-step into a comparable utility value.

No LLM calls. No randomness. Deterministic plan lifecycle.

Usage::

    from umh.planning.hierarchical_planning import (
        PlanEngine, get_plan_engine, reset_plan_engine,
    )

    engine = get_plan_engine()
    new_plans = engine.generate_plans(registry, traces, current_turn)
    next_action = engine.get_next_action(registry)
    engine.record_step_outcome(plan_id, goal_id, success_score)
"""

from __future__ import annotations

import hashlib
import logging
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.decision.trace import DecisionTrace
    from umh.goals.state import GoalRegistry

_log = logging.getLogger(__name__)

# ─── Constants ──────────────────────────────────────────────────────────────

MAX_PLANS = 4
MAX_STEPS = 6
PLAN_COOLDOWN = 8
MIN_GOALS_FOR_PLAN = 2
PLAN_CONFIDENCE_FLOOR = 0.1
PLAN_DECAY_RATE = 0.05
PLAN_FAILURE_PENALTY = 0.3
REPLAN_THRESHOLD = 0.25
PLAN_UTILITY_BONUS = 0.05
TRAJECTORY_CHAIN_THRESHOLD = 0.6
HORIZON_TRIGGER_THRESHOLD = 0.4
CRITERIA_OVERLAP_THRESHOLD = 0.4

# ─── Step recovery constants ──────────────────────────────────────────────

MAX_STEP_RETRIES = 2
RETRY_COOLDOWN = 1
MAX_FAILURE_STREAK = 2
PLAN_STALE_TURNS = 10

# ─── Data models ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PlanStep:
    """A single step in a plan: a goal to execute at a given position."""

    goal_id: str
    position: int
    dependency_ids: tuple[str, ...] = ()
    expected_delta: float = 0.0

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "position": self.position,
            "dependency_ids": list(self.dependency_ids),
            "expected_delta": round(self.expected_delta, 4),
        }


@dataclass(frozen=True)
class Plan:
    """Immutable multi-step goal execution plan."""

    plan_id: str
    root_goal_id: str
    steps: tuple[PlanStep, ...]
    dependencies: tuple[tuple[str, str], ...]
    expected_value: float
    confidence: float
    horizon: int
    creation_turn: int
    generation_reason: str = ""
    origin: str = ""

    def to_dict(self) -> dict:
        d = {
            "plan_id": self.plan_id,
            "root_goal_id": self.root_goal_id,
            "steps": [s.to_dict() for s in self.steps],
            "dependencies": list(self.dependencies),
            "expected_value": round(self.expected_value, 4),
            "confidence": round(self.confidence, 4),
            "horizon": self.horizon,
            "creation_turn": self.creation_turn,
            "generation_reason": self.generation_reason,
        }
        if self.origin:
            d["origin"] = self.origin
        return d

    @property
    def goal_ids(self) -> tuple[str, ...]:
        return tuple(s.goal_id for s in self.steps)


@dataclass
class StepRecoveryState:
    """Per-step retry and failure tracking."""

    retry_count: int = 0
    last_attempt_turn: int = -1
    failure_streak: int = 0
    status: str = "pending"

    def to_dict(self) -> dict:
        return {
            "retry_count": self.retry_count,
            "last_attempt_turn": self.last_attempt_turn,
            "failure_streak": self.failure_streak,
            "status": self.status,
        }


@dataclass
class PlanProgress:
    """Mutable tracker for plan execution progress."""

    plan_id: str
    completed_steps: list[str] = field(default_factory=list)
    failed_steps: list[str] = field(default_factory=list)
    skipped_steps: list[str] = field(default_factory=list)
    step_scores: dict[str, float] = field(default_factory=dict)
    step_recovery: dict[str, StepRecoveryState] = field(default_factory=dict)
    confidence: float = 0.5
    active: bool = True
    last_activity_turn: int = 0

    def is_step_ready(self, step: PlanStep) -> bool:
        """Check if all dependencies for a step are satisfied."""
        return all(
            d in self.completed_steps or d in self.skipped_steps
            for d in step.dependency_ids
        )

    def is_complete(self, plan: Plan) -> bool:
        """Check if all steps are completed or skipped."""
        return all(
            s.goal_id in self.completed_steps or s.goal_id in self.skipped_steps
            for s in plan.steps
        )

    def get_recovery(self, goal_id: str) -> StepRecoveryState:
        if goal_id not in self.step_recovery:
            self.step_recovery[goal_id] = StepRecoveryState()
        return self.step_recovery[goal_id]

    def record_success(self, goal_id: str, score: float) -> None:
        if goal_id not in self.completed_steps:
            self.completed_steps.append(goal_id)
        if goal_id in self.failed_steps:
            self.failed_steps.remove(goal_id)
        self.step_scores[goal_id] = score
        rec = self.get_recovery(goal_id)
        rec.status = "completed"
        rec.failure_streak = 0

    def record_failure(self, goal_id: str, score: float) -> None:
        if goal_id not in self.failed_steps:
            self.failed_steps.append(goal_id)
        self.step_scores[goal_id] = score
        self.confidence = max(
            PLAN_CONFIDENCE_FLOOR,
            self.confidence - PLAN_FAILURE_PENALTY,
        )

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "completed_steps": list(self.completed_steps),
            "failed_steps": list(self.failed_steps),
            "skipped_steps": list(self.skipped_steps),
            "step_scores": {k: round(v, 4) for k, v in self.step_scores.items()},
            "step_recovery": {k: v.to_dict() for k, v in self.step_recovery.items()},
            "confidence": round(self.confidence, 4),
            "active": self.active,
            "last_activity_turn": self.last_activity_turn,
        }


# ─── Plan scoring ──────────────────────────────────────────────────────────


def compute_plan_score(
    plan: Plan,
    registry: GoalRegistry,
    plan_transfer_score: float = 0.0,
) -> float:
    """Deterministic plan scoring.

    plan_score = product(step_utilities) * alignment * feasibility * horizon
                 + plan_transfer_score
    """
    step_utilities: list[float] = []
    for step in plan.steps:
        tracker = registry.get_tracker(step.goal_id)
        if tracker is not None and tracker.uses > 0:
            step_utilities.append(max(0.01, tracker.success_score))
        else:
            step_utilities.append(0.5)

    if not step_utilities:
        return 0.0

    utility_product = 1.0
    for u in step_utilities:
        utility_product *= u

    n = len(step_utilities)
    geometric_mean = utility_product ** (1.0 / n) if n > 0 else 0.0

    alignment = _compute_alignment_consistency(plan, registry)
    feasibility = _compute_resource_feasibility(plan, registry)
    horizon_factor = max(0.1, 1.0 - PLAN_DECAY_RATE * plan.horizon)

    score = (
        geometric_mean * alignment * feasibility * horizon_factor + plan_transfer_score
    )
    return max(0.0, min(1.0, score))


def _compute_alignment_consistency(plan: Plan, registry: GoalRegistry) -> float:
    """How consistent are the goals in the plan with each other?

    Uses pairwise criteria overlap. Higher overlap = more aligned plan.
    """
    goals = [registry.get_goal(s.goal_id) for s in plan.steps]
    goals = [g for g in goals if g is not None and g.success_criteria]
    if len(goals) < 2:
        return 0.8

    overlaps: list[float] = []
    for i in range(len(goals)):
        for j in range(i + 1, len(goals)):
            ka = set(goals[i].success_criteria.keys())
            kb = set(goals[j].success_criteria.keys())
            if ka or kb:
                overlap = len(ka & kb) / len(ka | kb) if (ka | kb) else 0.0
                overlaps.append(overlap)

    if not overlaps:
        return 0.8

    avg_overlap = sum(overlaps) / len(overlaps)
    return max(0.3, min(1.0, 0.5 + avg_overlap))


def _compute_resource_feasibility(plan: Plan, registry: GoalRegistry) -> float:
    """Estimate whether the plan's goals can realistically all execute.

    More steps = lower feasibility (each step has a chance of failure).
    """
    n = len(plan.steps)
    base_feasibility = 0.95**n
    return max(0.3, base_feasibility)


def plan_to_utility(
    plan: Plan,
    progress: PlanProgress,
    registry: GoalRegistry,
    current_turn: int,
    plan_transfer_score: float = 0.0,
) -> float:
    """Convert a plan's next executable step into a utility comparable to single goals.

    Returns the effective utility of the best available next step.
    """
    plan_score = compute_plan_score(
        plan, registry, plan_transfer_score=plan_transfer_score
    )
    plan_age = max(0, current_turn - plan.creation_turn)
    freshness = math.exp(-PLAN_DECAY_RATE * plan_age)

    next_step = _get_next_ready_step(plan, progress)
    if next_step is None:
        return 0.0

    step_utility = 0.5
    tracker = registry.get_tracker(next_step.goal_id)
    if tracker is not None and tracker.uses > 0:
        step_utility = tracker.success_score

    return (
        step_utility * plan_score * progress.confidence * freshness + PLAN_UTILITY_BONUS
    )


def _get_next_ready_step(
    plan: Plan,
    progress: PlanProgress,
    current_turn: int = 0,
) -> PlanStep | None:
    """Find the next step whose dependencies are all satisfied.

    Considers retry-pending steps: a step in RETRY_PENDING status is
    eligible once RETRY_COOLDOWN turns have elapsed since last attempt.
    Steps in FAILED_FINAL or skipped status are skipped entirely.
    """
    for step in plan.steps:
        gid = step.goal_id
        if gid in progress.completed_steps or gid in progress.skipped_steps:
            continue

        rec = progress.step_recovery.get(gid)
        if rec is not None:
            if rec.status == "failed_final":
                continue
            if rec.status == "retry_pending":
                if current_turn - rec.last_attempt_turn < RETRY_COOLDOWN:
                    continue

        if progress.is_step_ready(step):
            return step
    return None


# ─── Plan generation triggers ──────────────────────────────────────────────


def _criteria_overlap(
    criteria_a: dict | None,
    criteria_b: dict | None,
) -> float:
    """Jaccard overlap between two criteria dicts."""
    if not criteria_a or not criteria_b:
        return 0.0
    ka = set(criteria_a.keys())
    kb = set(criteria_b.keys())
    union = ka | kb
    if not union:
        return 0.0
    return len(ka & kb) / len(union)


def _make_plan_id(goal_ids: list[str], turn: int) -> str:
    """Deterministic plan ID from constituent goals."""
    sig = "_".join(sorted(goal_ids)) + f"_t{turn}"
    h = hashlib.md5(sig.encode()).hexdigest()[:8]
    return f"plan_{h}"


def _valid_step_ordering(steps: tuple[PlanStep, ...]) -> bool:
    """Check that no step depends on a later-positioned step (no cycles)."""
    position_of: dict[str, int] = {s.goal_id: s.position for s in steps}
    for step in steps:
        for dep in step.dependency_ids:
            dep_pos = position_of.get(dep)
            if dep_pos is not None and dep_pos >= step.position:
                return False
    return True


# ─── Plan Engine ────────────────────────────────────────────────────────────


class PlanEngine:
    """Stateful engine for generating, tracking, and executing multi-step plans."""

    def __init__(self, persist: bool = False) -> None:
        self._plans: dict[str, Plan] = {}
        self._progress: dict[str, PlanProgress] = {}
        self._active_plan_id: str | None = None
        self._last_generation_turn: int = -PLAN_COOLDOWN
        self._generated_plan_ids: set[str] = set()
        self._persist = persist

        if persist:
            self._load_persisted()

    @property
    def active_plan_id(self) -> str | None:
        return self._active_plan_id

    @property
    def plan_count(self) -> int:
        return len(self._plans)

    def get_plan(self, plan_id: str) -> Plan | None:
        return self._plans.get(plan_id)

    def get_progress(self, plan_id: str) -> PlanProgress | None:
        return self._progress.get(plan_id)

    def get_all_plans(self) -> list[Plan]:
        return list(self._plans.values())

    def get_active_plan(self) -> Plan | None:
        if self._active_plan_id is None:
            return None
        return self._plans.get(self._active_plan_id)

    def get_active_progress(self) -> PlanProgress | None:
        if self._active_plan_id is None:
            return None
        return self._progress.get(self._active_plan_id)

    def generate_plans(
        self,
        registry: GoalRegistry,
        traces: list | None = None,
        current_turn: int = 0,
    ) -> list[Plan]:
        """Generate new plans from registry state and trace history.

        Checks three triggers in priority order:
            A. Related goals (criteria overlap)
            B. Trajectory chains (sequential high-quality traces)
            C. Horizon signals (delayed payoff patterns)

        Returns at most 1 new plan per call.
        """
        traces = traces or []

        if current_turn - self._last_generation_turn < PLAN_COOLDOWN:
            return []

        goals = registry.get_all_goals()
        if len(goals) < MIN_GOALS_FOR_PLAN:
            return []

        if len(self._plans) >= MAX_PLANS:
            self._prune_weakest(registry, current_turn)
            if len(self._plans) >= MAX_PLANS:
                return []

        plan = self._try_related_goals(goals, registry, current_turn)
        if plan is None:
            plan = self._try_trajectory_chain(goals, registry, traces, current_turn)
        if plan is None:
            plan = self._try_horizon_trigger(goals, registry, traces, current_turn)

        if plan is None:
            return []

        if plan.plan_id in self._generated_plan_ids:
            return []

        self._plans[plan.plan_id] = plan
        self._progress[plan.plan_id] = PlanProgress(
            plan_id=plan.plan_id,
            confidence=plan.confidence,
        )
        self._generated_plan_ids.add(plan.plan_id)
        self._last_generation_turn = current_turn

        if self._active_plan_id is None:
            self._active_plan_id = plan.plan_id

        _log.debug("Generated plan %s: %s", plan.plan_id, plan.generation_reason)
        self._maybe_persist()
        return [plan]

    def _try_related_goals(
        self,
        goals: list,
        registry: GoalRegistry,
        current_turn: int,
    ) -> Plan | None:
        """Trigger A: find goals with overlapping criteria and sequence them."""
        related_pairs: list[tuple[str, str, float]] = []

        for i in range(len(goals)):
            for j in range(i + 1, len(goals)):
                overlap = _criteria_overlap(
                    goals[i].success_criteria,
                    goals[j].success_criteria,
                )
                if overlap >= CRITERIA_OVERLAP_THRESHOLD:
                    related_pairs.append((goals[i].goal_id, goals[j].goal_id, overlap))

        if not related_pairs:
            return None

        related_pairs.sort(key=lambda x: (-x[2], x[0], x[1]))
        best = related_pairs[0]

        gid_a, gid_b = best[0], best[1]
        tracker_a = registry.get_tracker(gid_a)
        tracker_b = registry.get_tracker(gid_b)

        priority_a = getattr(registry.get_goal(gid_a), "priority", 0.5)
        priority_b = getattr(registry.get_goal(gid_b), "priority", 0.5)

        if priority_a >= priority_b:
            first, second = gid_a, gid_b
        else:
            first, second = gid_b, gid_a

        steps = (
            PlanStep(
                goal_id=first,
                position=0,
                dependency_ids=(),
                expected_delta=getattr(tracker_a, "latest_delta", 0.0)
                if first == gid_a
                else getattr(tracker_b, "latest_delta", 0.0),
            ),
            PlanStep(
                goal_id=second,
                position=1,
                dependency_ids=(first,),
                expected_delta=getattr(tracker_b, "latest_delta", 0.0)
                if second == gid_b
                else getattr(tracker_a, "latest_delta", 0.0),
            ),
        )

        plan_id = _make_plan_id([first, second], current_turn)
        return Plan(
            plan_id=plan_id,
            root_goal_id=first,
            steps=steps,
            dependencies=((first, second),),
            expected_value=best[2],
            confidence=min(0.8, best[2] + 0.3),
            horizon=2,
            creation_turn=current_turn,
            generation_reason=f"related_goals:overlap={best[2]:.2f}",
        )

    def _try_trajectory_chain(
        self,
        goals: list,
        registry: GoalRegistry,
        traces: list,
        current_turn: int,
    ) -> Plan | None:
        """Trigger B: detect sequential high-quality traces suggesting a chain."""
        if len(traces) < 3:
            return None

        recent = traces[-10:]
        chain_goals: list[str] = []

        for trace in recent:
            active_id = getattr(trace, "active_goal_id", None)
            quality = getattr(trace, "quality_score", 0.0)
            if active_id and quality >= TRAJECTORY_CHAIN_THRESHOLD:
                if not chain_goals or chain_goals[-1] != active_id:
                    chain_goals.append(active_id)

        if len(chain_goals) < MIN_GOALS_FOR_PLAN:
            return None

        chain_goals = chain_goals[:MAX_STEPS]
        valid_goals = [g for g in chain_goals if registry.get_goal(g) is not None]
        if len(valid_goals) < MIN_GOALS_FOR_PLAN:
            return None

        steps: list[PlanStep] = []
        for i, gid in enumerate(valid_goals):
            tracker = registry.get_tracker(gid)
            deps = (valid_goals[i - 1],) if i > 0 else ()
            steps.append(
                PlanStep(
                    goal_id=gid,
                    position=i,
                    dependency_ids=deps,
                    expected_delta=getattr(tracker, "latest_delta", 0.0)
                    if tracker
                    else 0.0,
                )
            )

        dep_edges: list[tuple[str, str]] = []
        for i in range(1, len(valid_goals)):
            dep_edges.append((valid_goals[i - 1], valid_goals[i]))

        plan_id = _make_plan_id(valid_goals, current_turn)
        return Plan(
            plan_id=plan_id,
            root_goal_id=valid_goals[0],
            steps=tuple(steps),
            dependencies=tuple(dep_edges),
            expected_value=0.6,
            confidence=0.6,
            horizon=len(valid_goals),
            creation_turn=current_turn,
            generation_reason=f"trajectory_chain:len={len(valid_goals)}",
        )

    def _try_horizon_trigger(
        self,
        goals: list,
        registry: GoalRegistry,
        traces: list,
        current_turn: int,
    ) -> Plan | None:
        """Trigger C: goals with high horizon value that need sequencing."""
        horizon_goals: list[tuple[str, float]] = []

        for goal in goals:
            tracker = registry.get_tracker(goal.goal_id)
            if tracker is None or tracker.uses < 2:
                continue
            history = tracker.delta_history[-5:]
            if len(history) < 2:
                continue
            first_half = history[: len(history) // 2]
            second_half = history[len(history) // 2 :]
            avg_first = sum(first_half) / len(first_half) if first_half else 0
            avg_second = sum(second_half) / len(second_half) if second_half else 0

            if avg_second > avg_first and avg_second > 0:
                improvement = min(1.0, (avg_second - avg_first) * 5.0)
                if improvement >= HORIZON_TRIGGER_THRESHOLD:
                    horizon_goals.append((goal.goal_id, improvement))

        if len(horizon_goals) < MIN_GOALS_FOR_PLAN:
            return None

        horizon_goals.sort(key=lambda x: (-x[1], x[0]))
        selected = horizon_goals[:MAX_STEPS]

        steps: list[PlanStep] = []
        goal_ids: list[str] = []
        for i, (gid, imp) in enumerate(selected):
            deps = (goal_ids[i - 1],) if i > 0 else ()
            steps.append(
                PlanStep(
                    goal_id=gid,
                    position=i,
                    dependency_ids=deps,
                    expected_delta=imp,
                )
            )
            goal_ids.append(gid)

        dep_edges: list[tuple[str, str]] = []
        for i in range(1, len(goal_ids)):
            dep_edges.append((goal_ids[i - 1], goal_ids[i]))

        plan_id = _make_plan_id(goal_ids, current_turn)
        return Plan(
            plan_id=plan_id,
            root_goal_id=goal_ids[0],
            steps=tuple(steps),
            dependencies=tuple(dep_edges),
            expected_value=sum(imp for _, imp in selected) / len(selected),
            confidence=0.5,
            horizon=len(goal_ids),
            creation_turn=current_turn,
            generation_reason=f"horizon_trigger:goals={len(goal_ids)}",
        )

    # ─── Execution ─────────────────────────────────────────────────────

    def get_next_action(
        self,
        registry: GoalRegistry,
        current_turn: int = 0,
    ) -> tuple[str | None, str | None]:
        """Get the next action: (plan_id, goal_id) or (None, None).

        Returns the next ready step from the active plan,
        or from the highest-scoring plan if no active plan.
        """
        if self._active_plan_id is not None:
            plan = self._plans.get(self._active_plan_id)
            progress = self._progress.get(self._active_plan_id)
            if plan and progress and progress.active:
                step = _get_next_ready_step(plan, progress, current_turn)
                if step is not None:
                    return (plan.plan_id, step.goal_id)

        best_utility = -1.0
        best_plan_id = None
        best_goal_id = None

        for pid, plan in self._plans.items():
            progress = self._progress.get(pid)
            if progress is None or not progress.active:
                continue
            utility = plan_to_utility(plan, progress, registry, current_turn)
            if utility > best_utility:
                step = _get_next_ready_step(plan, progress, current_turn)
                if step is not None:
                    best_utility = utility
                    best_plan_id = pid
                    best_goal_id = step.goal_id

        if best_plan_id is not None:
            self._active_plan_id = best_plan_id

        return (best_plan_id, best_goal_id)

    def record_step_outcome(
        self,
        plan_id: str,
        goal_id: str,
        success_score: float,
        current_turn: int = 0,
    ) -> bool:
        """Record the outcome of executing a plan step.

        On failure, applies retry/skip/deactivate policy:
        - retry_count < MAX_STEP_RETRIES → RETRY_PENDING
        - retry_count exceeded + non-blocking → skip step
        - retry_count exceeded + blocking → deactivate plan

        Returns True if the outcome was recorded, False if plan/step not found.
        """
        progress = self._progress.get(plan_id)
        plan = self._plans.get(plan_id)
        if progress is None or plan is None:
            return False

        progress.last_activity_turn = current_turn
        rec = progress.get_recovery(goal_id)
        rec.last_attempt_turn = current_turn

        if success_score >= REPLAN_THRESHOLD:
            progress.record_success(goal_id, success_score)
        else:
            rec.retry_count += 1
            rec.failure_streak += 1
            progress.record_failure(goal_id, success_score)

            if (
                rec.failure_streak >= MAX_FAILURE_STREAK
                and rec.retry_count >= MAX_STEP_RETRIES
            ):
                blocking = self._is_step_blocking(plan, goal_id)
                if blocking:
                    rec.status = "failed_final"
                    if goal_id not in progress.failed_steps:
                        progress.failed_steps.append(goal_id)
                    progress.active = False
                    if self._active_plan_id == plan_id:
                        self._active_plan_id = None
                    _log.debug(
                        "Plan %s deactivated: blocking step %s failed_final",
                        plan_id,
                        goal_id,
                    )
                else:
                    rec.status = "skipped"
                    if goal_id not in progress.skipped_steps:
                        progress.skipped_steps.append(goal_id)
                    if goal_id in progress.failed_steps:
                        progress.failed_steps.remove(goal_id)
                    _log.debug(
                        "Plan %s: non-blocking step %s skipped after %d retries",
                        plan_id,
                        goal_id,
                        rec.retry_count,
                    )
            elif rec.retry_count < MAX_STEP_RETRIES:
                rec.status = "retry_pending"
            else:
                blocking = self._is_step_blocking(plan, goal_id)
                if blocking:
                    rec.status = "failed_final"
                    if goal_id not in progress.failed_steps:
                        progress.failed_steps.append(goal_id)
                    progress.active = False
                    if self._active_plan_id == plan_id:
                        self._active_plan_id = None
                else:
                    rec.status = "skipped"
                    if goal_id not in progress.skipped_steps:
                        progress.skipped_steps.append(goal_id)
                    if goal_id in progress.failed_steps:
                        progress.failed_steps.remove(goal_id)

            if progress.confidence < REPLAN_THRESHOLD and progress.active:
                progress.active = False
                if self._active_plan_id == plan_id:
                    self._active_plan_id = None
                _log.debug(
                    "Plan %s deactivated: confidence=%.2f", plan_id, progress.confidence
                )

        if progress.is_complete(plan):
            progress.active = False
            if self._active_plan_id == plan_id:
                self._active_plan_id = None
            _log.debug("Plan %s completed", plan_id)

        self._maybe_persist()
        return True

    def _is_step_blocking(self, plan: Plan, goal_id: str) -> bool:
        """A step is blocking if any other step depends on it."""
        for step in plan.steps:
            if goal_id in step.dependency_ids:
                return True
        return False

    def should_replan(
        self,
        plan_id: str,
        state_similarity_delta: float = 0.0,
    ) -> bool:
        """Check if a plan needs re-planning based on failure state.

        When ``state_similarity_delta`` is provided (drop in similarity
        between consecutive world states), the replan threshold is
        lowered, making replanning more likely during state shifts.
        """
        progress = self._progress.get(plan_id)
        if progress is None:
            return False
        adjusted = self.compute_replan_threshold(state_similarity_delta)
        return len(progress.failed_steps) > 0 and progress.confidence < adjusted

    @staticmethod
    def compute_replan_threshold(state_similarity_delta: float = 0.0) -> float:
        """Compute adjusted replan threshold from state similarity delta.

        A large negative delta (state shifted significantly) lowers the
        threshold, making replan more aggressive. Pure arithmetic.
        """
        delta = max(0.0, min(1.0, abs(state_similarity_delta)))
        return max(PLAN_CONFIDENCE_FLOOR, REPLAN_THRESHOLD * (1.0 - delta))

    def register_evolved_plan(self, plan: Plan) -> bool:
        """Register a mutated or recombined plan into the engine.

        Enforces MAX_PLANS by pruning the weakest evolved plan first,
        then the weakest base plan. Returns False if registration failed.
        """
        if plan.plan_id in self._plans:
            return False
        if plan.plan_id in self._generated_plan_ids:
            return False

        if len(self._plans) >= MAX_PLANS:
            self._prune_evolved_first()
            if len(self._plans) >= MAX_PLANS:
                return False

        self._plans[plan.plan_id] = plan
        self._progress[plan.plan_id] = PlanProgress(
            plan_id=plan.plan_id,
            confidence=plan.confidence,
        )
        self._generated_plan_ids.add(plan.plan_id)
        self._maybe_persist()
        return True

    def _prune_evolved_first(self) -> None:
        """Prune weakest evolved plan first, then weakest base plan."""
        evolved = [
            (pid, p) for pid, p in self._plans.items() if p.origin and p.origin != ""
        ]
        if evolved:
            evolved.sort(
                key=lambda x: (
                    self._progress.get(x[0], PlanProgress(plan_id=x[0])).confidence,
                    x[0],
                )
            )
            victim = evolved[0][0]
            del self._plans[victim]
            self._progress.pop(victim, None)
            if self._active_plan_id == victim:
                self._active_plan_id = None
            return

        all_plans = list(self._plans.items())
        if not all_plans:
            return
        all_plans.sort(
            key=lambda x: (
                self._progress.get(x[0], PlanProgress(plan_id=x[0])).confidence,
                x[0],
            )
        )
        victim = all_plans[0][0]
        del self._plans[victim]
        self._progress.pop(victim, None)
        if self._active_plan_id == victim:
            self._active_plan_id = None

    def deactivate_plan(self, plan_id: str) -> None:
        """Manually deactivate a plan."""
        progress = self._progress.get(plan_id)
        if progress is not None:
            progress.active = False
        if self._active_plan_id == plan_id:
            self._active_plan_id = None

    def activate_plan(self, plan_id: str) -> bool:
        """Activate a plan if it exists and isn't complete."""
        plan = self._plans.get(plan_id)
        progress = self._progress.get(plan_id)
        if plan is None or progress is None:
            return False
        if progress.is_complete(plan):
            return False
        progress.active = True
        self._active_plan_id = plan_id
        return True

    # ─── Competition ───────────────────────────────────────────────────

    def get_best_plan_utility(
        self,
        registry: GoalRegistry,
        current_turn: int = 0,
    ) -> tuple[str | None, float]:
        """Get the plan with highest utility for arbitration competition.

        Returns (plan_id, utility) or (None, 0.0).
        """
        best_utility = 0.0
        best_plan_id = None

        for pid, plan in self._plans.items():
            progress = self._progress.get(pid)
            if progress is None or not progress.active:
                continue
            utility = plan_to_utility(plan, progress, registry, current_turn)
            if utility > best_utility:
                best_utility = utility
                best_plan_id = pid

        return (best_plan_id, best_utility)

    # ─── Pruning ───────────────────────────────────────────────────────

    def _prune_weakest(self, registry: GoalRegistry, current_turn: int) -> None:
        """Remove the lowest-scoring inactive or completed plan."""
        candidates: list[tuple[str, float]] = []
        for pid, plan in self._plans.items():
            progress = self._progress.get(pid)
            if progress is None:
                candidates.append((pid, 0.0))
                continue
            if not progress.active or progress.is_complete(plan):
                candidates.append((pid, 0.0))
                continue
            utility = plan_to_utility(plan, progress, registry, current_turn)
            candidates.append((pid, utility))

        if not candidates:
            return

        candidates.sort(key=lambda x: (x[1], x[0]))
        weakest = candidates[0][0]
        del self._plans[weakest]
        self._progress.pop(weakest, None)
        if self._active_plan_id == weakest:
            self._active_plan_id = None

    # ─── Persistence ───────────────────────────────────────────────────

    def snapshot(self) -> dict:
        """Serialize full state for persistence."""
        return {
            "plans": {pid: p.to_dict() for pid, p in self._plans.items()},
            "progress": {pid: p.to_dict() for pid, p in self._progress.items()},
            "active_plan_id": self._active_plan_id,
            "last_generation_turn": self._last_generation_turn,
        }

    def restore(self, data: dict, current_turn: int = 0) -> None:
        """Restore state from persisted snapshot with hardening.

        Drops: corrupted plans, plans exceeding MAX_STEPS, plans with
        impossible step ordering, completed/failed_final plans, stale
        plans (no activity for PLAN_STALE_TURNS). Caps at MAX_PLANS.
        """
        self._active_plan_id = data.get("active_plan_id")
        self._last_generation_turn = data.get("last_generation_turn", -PLAN_COOLDOWN)

        loaded_plans: dict[str, Plan] = {}
        for pid, pdict in data.get("plans", {}).items():
            try:
                raw_steps = pdict.get("steps", [])
                if len(raw_steps) > MAX_STEPS:
                    _log.debug(
                        "Dropping plan %s: %d steps > MAX_STEPS", pid, len(raw_steps)
                    )
                    continue
                if not raw_steps:
                    _log.debug("Dropping plan %s: no steps", pid)
                    continue

                steps = tuple(
                    PlanStep(
                        goal_id=s["goal_id"],
                        position=s["position"],
                        dependency_ids=tuple(s.get("dependency_ids", ())),
                        expected_delta=s.get("expected_delta", 0.0),
                    )
                    for s in raw_steps
                )

                step_ids = {s.goal_id for s in steps}
                for step in steps:
                    for dep in step.dependency_ids:
                        if dep not in step_ids:
                            raise ValueError(f"dependency {dep} not in plan steps")

                if not _valid_step_ordering(steps):
                    _log.debug("Dropping plan %s: impossible step ordering", pid)
                    continue

                plan = Plan(
                    plan_id=pdict["plan_id"],
                    root_goal_id=pdict["root_goal_id"],
                    steps=steps,
                    dependencies=tuple(tuple(d) for d in pdict.get("dependencies", [])),
                    expected_value=pdict.get("expected_value", 0.0),
                    confidence=pdict.get("confidence", 0.5),
                    horizon=pdict.get("horizon", 0),
                    creation_turn=pdict.get("creation_turn", 0),
                    generation_reason=pdict.get("generation_reason", ""),
                    origin=pdict.get("origin", ""),
                )
                loaded_plans[pid] = plan
            except Exception as e:
                _log.debug("Dropping corrupted plan %s: %s", pid, e)
                continue

        loaded_progress: dict[str, PlanProgress] = {}
        for pid, prdict in data.get("progress", {}).items():
            if pid not in loaded_plans:
                continue
            try:
                recovery_raw = prdict.get("step_recovery", {})
                recovery = {}
                for gid, rdict in recovery_raw.items():
                    recovery[gid] = StepRecoveryState(
                        retry_count=rdict.get("retry_count", 0),
                        last_attempt_turn=rdict.get("last_attempt_turn", -1),
                        failure_streak=rdict.get("failure_streak", 0),
                        status=rdict.get("status", "pending"),
                    )

                prog = PlanProgress(
                    plan_id=prdict["plan_id"],
                    completed_steps=list(prdict.get("completed_steps", [])),
                    failed_steps=list(prdict.get("failed_steps", [])),
                    skipped_steps=list(prdict.get("skipped_steps", [])),
                    step_scores={
                        k: v for k, v in prdict.get("step_scores", {}).items()
                    },
                    step_recovery=recovery,
                    confidence=prdict.get("confidence", 0.5),
                    active=prdict.get("active", True),
                    last_activity_turn=prdict.get("last_activity_turn", 0),
                )
                loaded_progress[pid] = prog
            except Exception as e:
                _log.debug("Dropping corrupted progress %s: %s", pid, e)
                loaded_plans.pop(pid, None)
                continue

        # Prune stale, completed, and failed_final plans
        prune_ids: list[str] = []
        for pid, plan in loaded_plans.items():
            prog = loaded_progress.get(pid)
            if prog is None:
                prune_ids.append(pid)
                continue
            if not prog.active:
                prune_ids.append(pid)
                continue
            if prog.is_complete(plan):
                prune_ids.append(pid)
                continue
            if (
                current_turn > 0
                and current_turn - prog.last_activity_turn > PLAN_STALE_TURNS
            ):
                _log.debug(
                    "Pruning stale plan %s: no activity for %d turns",
                    pid,
                    current_turn - prog.last_activity_turn,
                )
                prune_ids.append(pid)
                continue
            # Check for all-failed-final blocking steps
            all_blocked = True
            for step in plan.steps:
                gid = step.goal_id
                if gid in prog.completed_steps or gid in prog.skipped_steps:
                    continue
                rec = prog.step_recovery.get(gid)
                if rec is not None and rec.status == "failed_final":
                    continue
                all_blocked = False
                break
            if all_blocked and not prog.is_complete(plan):
                prune_ids.append(pid)
                continue

        for pid in prune_ids:
            loaded_plans.pop(pid, None)
            loaded_progress.pop(pid, None)

        # Cap at MAX_PLANS — keep highest-confidence
        if len(loaded_plans) > MAX_PLANS:
            sorted_pids = sorted(
                loaded_plans.keys(),
                key=lambda p: (
                    loaded_progress.get(p, PlanProgress(plan_id=p)).confidence
                ),
                reverse=True,
            )
            for pid in sorted_pids[MAX_PLANS:]:
                loaded_plans.pop(pid, None)
                loaded_progress.pop(pid, None)

        self._plans = loaded_plans
        self._progress = loaded_progress
        for pid in loaded_plans:
            self._generated_plan_ids.add(pid)

        # Validate active_plan_id still exists
        if self._active_plan_id not in self._plans:
            self._active_plan_id = None

    def active_snapshot(self) -> dict:
        """Snapshot containing only active plans — used for persistence."""
        active_plans = {
            pid: p.to_dict()
            for pid, p in self._plans.items()
            if pid in self._progress and self._progress[pid].active
        }
        active_progress = {
            pid: self._progress[pid].to_dict()
            for pid in active_plans
            if pid in self._progress
        }
        return {
            "plans": active_plans,
            "progress": active_progress,
            "active_plan_id": self._active_plan_id,
            "last_generation_turn": self._last_generation_turn,
        }

    def _maybe_persist(self) -> None:
        """Save active plan state to the persistence layer if enabled."""
        if not self._persist:
            return
        try:
            from umh.persistence_layer.persistence import save_plans

            save_plans(self.active_snapshot())
        except Exception:
            pass

    def _load_persisted(self) -> None:
        """Restore plan state from the persistence layer on cold start."""
        try:
            from umh.persistence_layer.persistence import load_plans

            data = load_plans()
            if data is None:
                return
            self.restore(data)
        except Exception:
            pass


# ─── Singleton ──────────────────────────────────────────────────────────────

_engine: PlanEngine | None = None


def get_plan_engine(persist: bool = False) -> PlanEngine:
    """Get the singleton PlanEngine instance.

    Pass ``persist=True`` on the first call to enable cross-restart
    persistence. Subsequent calls ignore the flag.
    """
    global _engine
    if _engine is None:
        _engine = PlanEngine(persist=persist)
    return _engine


def reset_plan_engine() -> None:
    """Reset the singleton for testing."""
    global _engine
    _engine = None
