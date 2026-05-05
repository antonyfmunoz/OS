"""
PlanMutationEngine — deterministic plan evolution for EOS.

Provides bounded structural improvement of plans through mutation and
recombination. Plans can narrow (remove weak steps), expand (add support),
reorder (swap independent steps), substitute (replace failing goals),
split (decompose overloaded steps), compress (merge redundant steps),
or recombine (merge fragments from compatible parents).

No LLM calls. No randomness. Deterministic operator selection.
At most 1 mutation and 1 recombination per evaluation cycle.

Usage::

    from umh.runtime_engine.plan_mutation import get_plan_mutation_engine

    engine = get_plan_mutation_engine()
    result = engine.evaluate(plan_engine, registry, current_turn)
    if result is not None:
        plan_engine.register_evolved_plan(result.plan)
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field

_log = logging.getLogger(__name__)

# ─── Constants ──────────────────────────────────────────────────────────────

MUTATION_COOLDOWN = 8
MIN_STEPS_FOR_MUTATION = 2
UNDERPERFORMANCE_THRESHOLD = 0.3
NEAR_MISS_COMPLETION_RATIO = 0.7
BLOAT_SCORE_THRESHOLD = 0.25
RETRY_EXHAUSTION_THRESHOLD = 2
RECOMBINATION_COOLDOWN = 12
MIN_OVERLAP_FOR_RECOMBINATION = 1
MAX_EVOLVED_PLANS = 2

# ─── Data models ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PlanMutation:
    """Immutable record of a plan mutation."""

    mutated_plan_id: str
    parent_plan_id: str
    mutation_type: str
    mutation_reason: str
    affected_step_goal_id: str
    creation_turn: int

    def to_dict(self) -> dict:
        return {
            "mutated_plan_id": self.mutated_plan_id,
            "parent_plan_id": self.parent_plan_id,
            "mutation_type": self.mutation_type,
            "mutation_reason": self.mutation_reason,
            "affected_step_goal_id": self.affected_step_goal_id,
            "creation_turn": self.creation_turn,
        }


@dataclass(frozen=True)
class PlanMutationResult:
    """Result of a plan evolution evaluation cycle."""

    mutation: PlanMutation | None = None
    mutated_plan: object | None = None
    recombination: PlanRecombination | None = None
    recombined_plan: object | None = None

    @property
    def has_mutation(self) -> bool:
        return self.mutation is not None

    @property
    def has_recombination(self) -> bool:
        return self.recombination is not None

    @property
    def has_changes(self) -> bool:
        return self.has_mutation or self.has_recombination


@dataclass(frozen=True)
class PlanRecombination:
    """Immutable record of a plan recombination."""

    recombined_plan_id: str
    parent_plan_ids: tuple[str, str]
    recombination_reason: str
    creation_turn: int

    def to_dict(self) -> dict:
        return {
            "recombined_plan_id": self.recombined_plan_id,
            "parent_plan_ids": list(self.parent_plan_ids),
            "recombination_reason": self.recombination_reason,
            "creation_turn": self.creation_turn,
        }


# ─── Mutation operators ────────────────────────────────────────────────────


def _op_narrow(plan: object, target_goal_id: str) -> object | None:
    """Remove the target step if it has no dependents."""
    from umh.runtime_engine.hierarchical_planning import Plan, PlanStep, _valid_step_ordering

    dependents = set()
    for step in plan.steps:
        for dep in step.dependency_ids:
            dependents.add(dep)

    if target_goal_id in dependents:
        return None

    new_steps = []
    for step in plan.steps:
        if step.goal_id == target_goal_id:
            continue
        cleaned_deps = tuple(d for d in step.dependency_ids if d != target_goal_id)
        new_steps.append(
            PlanStep(
                goal_id=step.goal_id,
                position=len(new_steps),
                dependency_ids=cleaned_deps,
                expected_delta=step.expected_delta,
            )
        )

    if len(new_steps) < 1:
        return None

    steps_tuple = tuple(new_steps)
    if not _valid_step_ordering(steps_tuple):
        return None

    new_deps = tuple(
        (a, b)
        for a, b in plan.dependencies
        if a != target_goal_id and b != target_goal_id
    )

    return Plan(
        plan_id=_make_evolved_plan_id(plan.plan_id, "narrow", plan.creation_turn),
        root_goal_id=new_steps[0].goal_id,
        steps=steps_tuple,
        dependencies=new_deps,
        expected_value=plan.expected_value,
        confidence=plan.confidence * 0.9,
        horizon=len(new_steps),
        creation_turn=plan.creation_turn,
        generation_reason=plan.generation_reason,
        origin=f"mutated:narrow:{plan.plan_id}",
    )


def _op_reorder(plan: object, step_a_idx: int, step_b_idx: int) -> object | None:
    """Swap two adjacent steps if dependency-safe."""
    from umh.runtime_engine.hierarchical_planning import Plan, PlanStep, _valid_step_ordering

    steps = list(plan.steps)
    if step_a_idx < 0 or step_b_idx < 0:
        return None
    if step_a_idx >= len(steps) or step_b_idx >= len(steps):
        return None
    if abs(step_a_idx - step_b_idx) != 1:
        return None

    steps[step_a_idx], steps[step_b_idx] = steps[step_b_idx], steps[step_a_idx]

    reindexed = []
    for i, s in enumerate(steps):
        reindexed.append(
            PlanStep(
                goal_id=s.goal_id,
                position=i,
                dependency_ids=s.dependency_ids,
                expected_delta=s.expected_delta,
            )
        )

    steps_tuple = tuple(reindexed)
    if not _valid_step_ordering(steps_tuple):
        return None

    return Plan(
        plan_id=_make_evolved_plan_id(plan.plan_id, "reorder", plan.creation_turn),
        root_goal_id=reindexed[0].goal_id,
        steps=steps_tuple,
        dependencies=plan.dependencies,
        expected_value=plan.expected_value,
        confidence=plan.confidence * 0.95,
        horizon=plan.horizon,
        creation_turn=plan.creation_turn,
        generation_reason=plan.generation_reason,
        origin=f"mutated:reorder:{plan.plan_id}",
    )


def _op_substitute(
    plan: object, target_goal_id: str, replacement_goal_id: str
) -> object | None:
    """Replace a step's goal with a related goal."""
    from umh.runtime_engine.hierarchical_planning import Plan, PlanStep, _valid_step_ordering

    if replacement_goal_id in plan.goal_ids:
        return None

    new_steps = []
    for step in plan.steps:
        if step.goal_id == target_goal_id:
            new_steps.append(
                PlanStep(
                    goal_id=replacement_goal_id,
                    position=step.position,
                    dependency_ids=step.dependency_ids,
                    expected_delta=step.expected_delta,
                )
            )
        else:
            updated_deps = tuple(
                replacement_goal_id if d == target_goal_id else d
                for d in step.dependency_ids
            )
            new_steps.append(
                PlanStep(
                    goal_id=step.goal_id,
                    position=step.position,
                    dependency_ids=updated_deps,
                    expected_delta=step.expected_delta,
                )
            )

    steps_tuple = tuple(new_steps)
    if not _valid_step_ordering(steps_tuple):
        return None

    new_deps = tuple(
        (
            replacement_goal_id if a == target_goal_id else a,
            replacement_goal_id if b == target_goal_id else b,
        )
        for a, b in plan.dependencies
    )

    return Plan(
        plan_id=_make_evolved_plan_id(plan.plan_id, "substitute", plan.creation_turn),
        root_goal_id=new_steps[0].goal_id,
        steps=steps_tuple,
        dependencies=new_deps,
        expected_value=plan.expected_value,
        confidence=plan.confidence * 0.85,
        horizon=plan.horizon,
        creation_turn=plan.creation_turn,
        generation_reason=plan.generation_reason,
        origin=f"mutated:substitute:{plan.plan_id}",
    )


def _op_compress(plan: object, step_a_idx: int, step_b_idx: int) -> object | None:
    """Collapse two adjacent steps with the same goal into one."""
    from umh.runtime_engine.hierarchical_planning import Plan, PlanStep, _valid_step_ordering

    steps = list(plan.steps)
    if step_a_idx < 0 or step_b_idx < 0:
        return None
    if step_a_idx >= len(steps) or step_b_idx >= len(steps):
        return None
    if steps[step_a_idx].goal_id != steps[step_b_idx].goal_id:
        return None

    keep_idx = min(step_a_idx, step_b_idx)
    drop_idx = max(step_a_idx, step_b_idx)
    kept = steps[keep_idx]
    dropped = steps[drop_idx]

    merged_deps = set(kept.dependency_ids) | set(dropped.dependency_ids)
    merged_deps.discard(kept.goal_id)

    new_steps = []
    for i, s in enumerate(steps):
        if i == drop_idx:
            continue
        if i == keep_idx:
            new_steps.append(
                PlanStep(
                    goal_id=kept.goal_id,
                    position=len(new_steps),
                    dependency_ids=tuple(sorted(merged_deps)),
                    expected_delta=max(kept.expected_delta, dropped.expected_delta),
                )
            )
        else:
            cleaned_deps = tuple(d for d in s.dependency_ids if d != dropped.goal_id)
            new_steps.append(
                PlanStep(
                    goal_id=s.goal_id,
                    position=len(new_steps),
                    dependency_ids=cleaned_deps,
                    expected_delta=s.expected_delta,
                )
            )

    steps_tuple = tuple(new_steps)
    if not _valid_step_ordering(steps_tuple):
        return None

    new_deps = tuple(
        (a, b)
        for a, b in plan.dependencies
        if a != dropped.goal_id and b != dropped.goal_id
    )

    return Plan(
        plan_id=_make_evolved_plan_id(plan.plan_id, "compress", plan.creation_turn),
        root_goal_id=new_steps[0].goal_id,
        steps=steps_tuple,
        dependencies=new_deps,
        expected_value=plan.expected_value,
        confidence=plan.confidence * 0.9,
        horizon=len(new_steps),
        creation_turn=plan.creation_turn,
        generation_reason=plan.generation_reason,
        origin=f"mutated:compress:{plan.plan_id}",
    )


# ─── Recombination ──────────────────────────────────────────────────────────


def _recombine_plans(plan_a: object, plan_b: object, turn: int) -> object | None:
    """Combine strongest prefix from plan_a with strongest suffix from plan_b."""
    from umh.runtime_engine.hierarchical_planning import (
        Plan,
        PlanStep,
        MAX_STEPS,
        _valid_step_ordering,
    )

    goals_a = set(plan_a.goal_ids)
    goals_b = set(plan_b.goal_ids)
    overlap = goals_a & goals_b
    if len(overlap) < MIN_OVERLAP_FOR_RECOMBINATION:
        return None

    split_a = len(plan_a.steps) // 2 + 1
    split_b = len(plan_b.steps) // 2

    prefix = list(plan_a.steps[:split_a])
    suffix_candidates = [
        s
        for s in plan_b.steps[split_b:]
        if s.goal_id not in {p.goal_id for p in prefix}
    ]

    combined_goals = {s.goal_id for s in prefix}
    suffix = []
    for s in suffix_candidates:
        if s.goal_id not in combined_goals:
            suffix.append(s)
            combined_goals.add(s.goal_id)

    all_steps_raw = prefix + suffix
    if len(all_steps_raw) > MAX_STEPS:
        all_steps_raw = all_steps_raw[:MAX_STEPS]
    if len(all_steps_raw) < 1:
        return None

    valid_ids = {s.goal_id for s in all_steps_raw}
    new_steps = []
    for i, s in enumerate(all_steps_raw):
        cleaned_deps = tuple(d for d in s.dependency_ids if d in valid_ids)
        new_steps.append(
            PlanStep(
                goal_id=s.goal_id,
                position=i,
                dependency_ids=cleaned_deps,
                expected_delta=s.expected_delta,
            )
        )

    steps_tuple = tuple(new_steps)
    if not _valid_step_ordering(steps_tuple):
        return None

    deps = []
    for s in new_steps:
        for d in s.dependency_ids:
            deps.append((d, s.goal_id))

    recombined_id = _make_recombined_plan_id(plan_a.plan_id, plan_b.plan_id, turn)

    return Plan(
        plan_id=recombined_id,
        root_goal_id=new_steps[0].goal_id,
        steps=steps_tuple,
        dependencies=tuple(deps),
        expected_value=(plan_a.expected_value + plan_b.expected_value) / 2,
        confidence=min(plan_a.confidence, plan_b.confidence) * 0.9,
        horizon=len(new_steps),
        creation_turn=turn,
        generation_reason=f"recombined:{plan_a.plan_id}+{plan_b.plan_id}",
        origin=f"recombined:{plan_a.plan_id}+{plan_b.plan_id}",
    )


# ─── ID helpers ─────────────────────────────────────────────────────────────


def _make_evolved_plan_id(parent_id: str, mutation_type: str, turn: int) -> str:
    sig = f"{parent_id}:{mutation_type}:{turn}"
    h = hashlib.md5(sig.encode()).hexdigest()[:8]
    return f"plan_mut_{mutation_type}_{h}"


def _make_recombined_plan_id(parent_a: str, parent_b: str, turn: int) -> str:
    sig = f"{parent_a}+{parent_b}:{turn}"
    h = hashlib.md5(sig.encode()).hexdigest()[:8]
    return f"plan_recomb_{h}"


# ─── Mutation trigger detection ─────────────────────────────────────────────


def _find_underperforming_step(plan: object, progress: object) -> str | None:
    """Find the lowest-scoring step that has been attempted."""
    worst_goal: str | None = None
    worst_score = 1.0
    for step in plan.steps:
        score = progress.step_scores.get(step.goal_id)
        if score is not None and score < UNDERPERFORMANCE_THRESHOLD:
            if score < worst_score:
                worst_score = score
                worst_goal = step.goal_id
    return worst_goal


def _find_retry_exhausted_step(plan: object, progress: object) -> str | None:
    """Find a step that exhausted retries."""
    for step in plan.steps:
        rec = progress.step_recovery.get(step.goal_id)
        if rec is not None and rec.retry_count >= RETRY_EXHAUSTION_THRESHOLD:
            return step.goal_id
    return None


def _is_near_miss(plan: object, progress: object) -> bool:
    """Plan completed most steps but failed late."""
    total = len(plan.steps)
    if total < MIN_STEPS_FOR_MUTATION:
        return False
    completed = len(progress.completed_steps)
    return (
        completed >= total * NEAR_MISS_COMPLETION_RATIO
        and len(progress.failed_steps) > 0
    )


def _find_bloated_step(plan: object, progress: object) -> str | None:
    """Find a low-value step in a plan with enough data."""
    if len(plan.steps) < MIN_STEPS_FOR_MUTATION:
        return None

    scored = []
    for step in plan.steps:
        score = progress.step_scores.get(step.goal_id)
        if score is not None:
            scored.append((step.goal_id, score))

    if len(scored) < MIN_STEPS_FOR_MUTATION:
        return None

    scored.sort(key=lambda x: (x[1], x[0]))

    if scored[0][1] < BLOAT_SCORE_THRESHOLD:
        return scored[0][0]
    return None


def _find_substitute_goal(
    target_goal_id: str,
    plan: object,
    registry: object,
) -> str | None:
    """Find a sibling goal with overlapping criteria."""
    target_goal = registry.get_goal(target_goal_id)
    if target_goal is None:
        return None
    target_criteria = getattr(target_goal, "success_criteria", None)
    if not target_criteria:
        return None

    existing_ids = set(plan.goal_ids)
    best_sub: str | None = None
    best_overlap = 0.0

    try:
        all_goals = registry.get_all_goals()
    except Exception:
        return None

    for goal in all_goals:
        if goal.goal_id == target_goal_id or goal.goal_id in existing_ids:
            continue
        if not getattr(goal, "active", True):
            continue
        goal_criteria = getattr(goal, "success_criteria", None)
        if not goal_criteria:
            continue

        ka = set(target_criteria.keys())
        kb = set(goal_criteria.keys())
        union = ka | kb
        if not union:
            continue
        overlap = len(ka & kb) / len(union)
        if overlap > best_overlap:
            best_overlap = overlap
            best_sub = goal.goal_id

    if best_overlap < 0.3:
        return None
    return best_sub


# ─── Plan Mutation Engine ───────────────────────────────────────────────────


class PlanMutationEngine:
    """Deterministic plan evolution engine.

    Evaluates active plans for mutation triggers in priority order.
    At most 1 mutation + 1 recombination per cycle.
    """

    def __init__(self) -> None:
        self._last_mutation_turn: int = -MUTATION_COOLDOWN
        self._last_recombination_turn: int = -RECOMBINATION_COOLDOWN
        self._mutation_history: list[str] = []

    def evaluate(
        self,
        plan_engine: object,
        registry: object,
        current_turn: int,
    ) -> PlanMutationResult:
        """Evaluate plans for evolution opportunities.

        Returns at most 1 mutation and 1 recombination per call.
        Does NOT register plans — caller is responsible.
        """
        mutation: PlanMutation | None = None
        mutated_plan: object | None = None
        recombination: PlanRecombination | None = None
        recombined_plan: object | None = None

        # ── Mutation ──────────────────────────────────────────
        if current_turn - self._last_mutation_turn >= MUTATION_COOLDOWN:
            mutation, mutated_plan = self._try_mutation(
                plan_engine, registry, current_turn
            )
            if mutation is not None:
                self._last_mutation_turn = current_turn
                self._mutation_history.append(mutation.mutated_plan_id)

        # ── Recombination ─────────────────────────────────────
        if current_turn - self._last_recombination_turn >= RECOMBINATION_COOLDOWN:
            recombination, recombined_plan = self._try_recombination(
                plan_engine, registry, current_turn
            )
            if recombination is not None:
                self._last_recombination_turn = current_turn

        return PlanMutationResult(
            mutation=mutation,
            mutated_plan=mutated_plan,
            recombination=recombination,
            recombined_plan=recombined_plan,
        )

    def _try_mutation(
        self,
        plan_engine: object,
        registry: object,
        current_turn: int,
    ) -> tuple[PlanMutation | None, object | None]:
        """Try mutation triggers in priority order. Returns first match."""
        plans = plan_engine.get_all_plans()
        if not plans:
            return None, None

        for plan in sorted(plans, key=lambda p: (p.plan_id,)):
            progress = plan_engine.get_progress(plan.plan_id)
            if progress is None or not progress.active:
                continue
            if len(plan.steps) < MIN_STEPS_FOR_MUTATION:
                continue

            # P1: underperforming step → narrow or substitute
            underperf = _find_underperforming_step(plan, progress)
            if underperf is not None:
                sub_goal = _find_substitute_goal(underperf, plan, registry)
                if sub_goal is not None:
                    result = _op_substitute(plan, underperf, sub_goal)
                    if result is not None:
                        mut = PlanMutation(
                            mutated_plan_id=result.plan_id,
                            parent_plan_id=plan.plan_id,
                            mutation_type="substitute",
                            mutation_reason=f"underperforming:{underperf}:sub={sub_goal}",
                            affected_step_goal_id=underperf,
                            creation_turn=current_turn,
                        )
                        return mut, result

                result = _op_narrow(plan, underperf)
                if result is not None:
                    mut = PlanMutation(
                        mutated_plan_id=result.plan_id,
                        parent_plan_id=plan.plan_id,
                        mutation_type="narrow",
                        mutation_reason=f"underperforming:{underperf}",
                        affected_step_goal_id=underperf,
                        creation_turn=current_turn,
                    )
                    return mut, result

            # P2: retry exhaustion → narrow
            exhausted = _find_retry_exhausted_step(plan, progress)
            if exhausted is not None:
                result = _op_narrow(plan, exhausted)
                if result is not None:
                    mut = PlanMutation(
                        mutated_plan_id=result.plan_id,
                        parent_plan_id=plan.plan_id,
                        mutation_type="narrow",
                        mutation_reason=f"retry_exhausted:{exhausted}",
                        affected_step_goal_id=exhausted,
                        creation_turn=current_turn,
                    )
                    return mut, result

            # P3: near-miss → reorder failing step later
            if _is_near_miss(plan, progress):
                failed_goals = progress.failed_steps
                if failed_goals:
                    fail_goal = failed_goals[0]
                    fail_idx = None
                    for i, s in enumerate(plan.steps):
                        if s.goal_id == fail_goal:
                            fail_idx = i
                            break
                    if fail_idx is not None and fail_idx < len(plan.steps) - 1:
                        result = _op_reorder(plan, fail_idx, fail_idx + 1)
                        if result is not None:
                            mut = PlanMutation(
                                mutated_plan_id=result.plan_id,
                                parent_plan_id=plan.plan_id,
                                mutation_type="reorder",
                                mutation_reason=f"near_miss:{fail_goal}",
                                affected_step_goal_id=fail_goal,
                                creation_turn=current_turn,
                            )
                            return mut, result

            # P4: bloated plan → narrow
            bloated = _find_bloated_step(plan, progress)
            if bloated is not None:
                result = _op_narrow(plan, bloated)
                if result is not None:
                    mut = PlanMutation(
                        mutated_plan_id=result.plan_id,
                        parent_plan_id=plan.plan_id,
                        mutation_type="narrow",
                        mutation_reason=f"bloated:{bloated}",
                        affected_step_goal_id=bloated,
                        creation_turn=current_turn,
                    )
                    return mut, result

        return None, None

    def _try_recombination(
        self,
        plan_engine: object,
        registry: object,
        current_turn: int,
    ) -> tuple[PlanRecombination | None, object | None]:
        """Try recombining the highest-confidence compatible pair."""
        plans = plan_engine.get_all_plans()
        active_plans = []
        for p in plans:
            progress = plan_engine.get_progress(p.plan_id)
            if progress is not None and progress.active and progress.confidence > 0.3:
                active_plans.append((p, progress))

        if len(active_plans) < 2:
            return None, None

        active_plans.sort(key=lambda x: (-x[1].confidence, x[0].plan_id))

        for i in range(len(active_plans)):
            for j in range(i + 1, len(active_plans)):
                plan_a, prog_a = active_plans[i]
                plan_b, prog_b = active_plans[j]

                goals_a = set(plan_a.goal_ids)
                goals_b = set(plan_b.goal_ids)
                overlap = goals_a & goals_b
                if len(overlap) < MIN_OVERLAP_FOR_RECOMBINATION:
                    continue

                result = _recombine_plans(plan_a, plan_b, current_turn)
                if result is None:
                    continue

                existing_ids = {p.plan_id for p in plans}
                if result.plan_id in existing_ids:
                    continue

                rec = PlanRecombination(
                    recombined_plan_id=result.plan_id,
                    parent_plan_ids=(plan_a.plan_id, plan_b.plan_id),
                    recombination_reason=(
                        f"compatible_overlap:{len(overlap)}:"
                        f"{plan_a.plan_id}+{plan_b.plan_id}"
                    ),
                    creation_turn=current_turn,
                )
                return rec, result

        return None, None

    @property
    def last_mutation_turn(self) -> int:
        return self._last_mutation_turn

    @property
    def last_recombination_turn(self) -> int:
        return self._last_recombination_turn


# ─── Module-level singleton ─────────────────────────────────────────────────

_engine: PlanMutationEngine | None = None


def get_plan_mutation_engine() -> PlanMutationEngine:
    global _engine
    if _engine is None:
        _engine = PlanMutationEngine()
    return _engine


def reset_plan_mutation_engine() -> None:
    global _engine
    _engine = None
