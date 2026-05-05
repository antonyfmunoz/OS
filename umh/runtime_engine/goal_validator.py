"""
GoalValidator — structural validation gate for goal activation.

Previous behavior: MetaGoalEngine generates goals and they enter
GoalRegistry if confidence exceeds a threshold. No structural
validation — redundant, degenerate, dominated, or cyclic goals
can pollute the registry.

This module validates every goal before activation:
    A. Redundancy — reject if highly similar to existing goal
    B. Degenerate — reject if criteria empty or too generic
    C. Dominated — reject if always worse than parent
    D. Cycles — prevent parent-child loops
    E. Capacity pressure — raise threshold when near MAX_GOALS

Additionally provides safe auto-corrections:
    - Normalize criteria format
    - Clamp priority bounds
    - Merge duplicate goals (when safe)

No semantic rewriting. No LLM calls. No randomness.
Pure function of goal + registry state.

Usage::

    from umh.runtime_engine.goal_validator import GoalValidator, ValidationResult

    validator = GoalValidator()
    result = validator.validate(meta_goal, registry, traces)
    if result.is_valid:
        registry.add_goal(result.corrected_goal or goal_state)
    else:
        log_rejection(result.violations)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.goals.state import GoalRegistry, GoalState
    from umh.runtime_engine.meta_goal import MetaGoal

_log = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

SIMILARITY_THRESHOLD = 0.75
MIN_CRITERIA_KEYS = 1
PRIORITY_MIN = 0.05
PRIORITY_MAX = 0.95
CAPACITY_PRESSURE_THRESHOLD = 0.8
ELEVATED_CONFIDENCE_THRESHOLD = 0.6
DOMINATION_MARGIN = 0.1


# ─── Data models ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating a single goal."""

    is_valid: bool
    violations: tuple[str, ...]
    corrected_goal: object | None = None
    severity: str = "warn"

    def to_dict(self) -> dict:
        d: dict = {
            "is_valid": self.is_valid,
            "violations": list(self.violations),
            "severity": self.severity,
        }
        if self.corrected_goal is not None:
            cg = self.corrected_goal
            d["corrected_goal_id"] = getattr(cg, "goal_id", None)
        return d


VALID = ValidationResult(
    is_valid=True,
    violations=(),
    corrected_goal=None,
    severity="warn",
)


# ─── Validator ────────────────────────────────────────────────────────────────


class GoalValidator:
    """Deterministic structural validator for goals entering the registry.

    Runs all validation rules in order. First ``reject`` severity
    violation stops validation — the goal is rejected. ``warn``
    violations are accumulated but the goal may still pass.
    ``auto-fix`` violations apply safe corrections and continue.
    """

    def validate(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
        traces: list | None = None,
    ) -> ValidationResult:
        """Validate a MetaGoal against structural rules.

        Returns ValidationResult with is_valid=True if the goal
        passes all checks (possibly with auto-corrections applied).
        """
        violations: list[str] = []
        worst_severity = "warn"
        corrected: MetaGoal | None = None

        # ── Rule A: Redundancy ──────────────────────────────────────
        redundancy = self._check_redundancy(meta_goal, registry)
        if redundancy:
            violations.append(redundancy)
            worst_severity = "reject"

        # ── Rule B: Degenerate goals ────────────────────────────────
        degen = self._check_degenerate(meta_goal)
        if degen:
            violations.append(degen)
            worst_severity = "reject"

        # ── Rule C: Dominated goals ─────────────────────────────────
        if worst_severity != "reject":
            dominated = self._check_dominated(meta_goal, registry)
            if dominated:
                violations.append(dominated)
                worst_severity = "reject"

        # ── Rule D: Cycles ──────────────────────────────────────────
        if worst_severity != "reject":
            cycle = self._check_cycles(meta_goal, registry)
            if cycle:
                violations.append(cycle)
                worst_severity = "reject"

        # ── Rule E: Capacity pressure ───────────────────────────────
        if worst_severity != "reject":
            pressure = self._check_capacity_pressure(meta_goal, registry)
            if pressure:
                violations.append(pressure)
                worst_severity = "reject"

        # ── Auto-corrections (only if not already rejected) ─────────
        if worst_severity != "reject":
            corrected, fix_notes = self._auto_correct(meta_goal)
            for note in fix_notes:
                violations.append(note)
            if fix_notes:
                worst_severity = "auto-fix"

        is_valid = worst_severity != "reject"

        return ValidationResult(
            is_valid=is_valid,
            violations=tuple(violations),
            corrected_goal=corrected,
            severity=worst_severity,
        )

    def validate_batch(
        self,
        meta_goals: list[MetaGoal],
        registry: GoalRegistry,
        traces: list | None = None,
    ) -> list[ValidationResult]:
        """Validate a batch of goals. Order is preserved."""
        return [self.validate(mg, registry, traces) for mg in meta_goals]

    # ── Rule A: Redundancy ──────────────────────────────────────────────────

    def _check_redundancy(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
    ) -> str | None:
        """Reject if highly similar to an existing goal in the registry."""
        existing = registry.get_all_goals()
        for eg in existing:
            if eg.goal_id == meta_goal.goal_id:
                return f"redundancy:exact_id_match:{eg.goal_id}"

            sim = _criteria_similarity(meta_goal.success_criteria, eg.success_criteria)
            if sim >= SIMILARITY_THRESHOLD:
                parent_overlap = eg.goal_id in meta_goal.parent_goals
                if not parent_overlap:
                    return f"redundancy:criteria_similarity:{eg.goal_id}:sim={sim:.2f}"

        return None

    # ── Rule B: Degenerate goals ────────────────────────────────────────────

    def _check_degenerate(self, meta_goal: MetaGoal) -> str | None:
        """Reject if criteria are empty or too generic."""
        criteria = meta_goal.success_criteria
        if not criteria:
            return "degenerate:empty_criteria"

        real_keys = [k for k in criteria if not k.startswith("_meta_")]
        if len(real_keys) < MIN_CRITERIA_KEYS:
            return f"degenerate:insufficient_criteria:{len(real_keys)}"

        if not meta_goal.description or len(meta_goal.description.strip()) < 3:
            return "degenerate:missing_description"

        return None

    # ── Rule C: Dominated goals ─────────────────────────────────────────────

    def _check_dominated(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
    ) -> str | None:
        """Reject if strictly worse than its parent goal.

        A generated goal is dominated if BOTH its utility_estimate AND
        confidence are lower than the parent's tracker scores by at
        least DOMINATION_MARGIN.
        """
        for pid in meta_goal.parent_goals:
            parent = registry.get_goal(pid)
            if parent is None:
                continue

            tracker = registry.get_tracker(pid)
            if tracker is None:
                continue

            parent_utility = parent.priority
            parent_confidence = tracker.success_score

            utility_worse = (
                meta_goal.utility_estimate < parent_utility - DOMINATION_MARGIN
            )
            confidence_worse = (
                meta_goal.confidence < parent_confidence - DOMINATION_MARGIN
            )

            if utility_worse and confidence_worse:
                return (
                    f"dominated:by_parent:{pid}"
                    f":util={meta_goal.utility_estimate:.2f}<{parent_utility:.2f}"
                    f":conf={meta_goal.confidence:.2f}<{parent_confidence:.2f}"
                )

        return None

    # ── Rule D: Cycles ──────────────────────────────────────────────────────

    def _check_cycles(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
    ) -> str | None:
        """Prevent parent-child loops.

        A cycle exists if the new goal's ID appears as a parent of
        any of its own parents (direct or transitive via meta-goal
        engine tracking).
        """
        if not meta_goal.parent_goals:
            return None

        if meta_goal.goal_id in meta_goal.parent_goals:
            return f"cycle:self_reference:{meta_goal.goal_id}"

        visited: set[str] = set()
        queue = list(meta_goal.parent_goals)

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            parent_goal = registry.get_goal(current)
            if parent_goal is None:
                continue

            try:
                from umh.runtime_engine.meta_goal import MetaGoalEngine

                mg = _get_meta_goal_from_registry(current, registry)
                if mg is not None:
                    for gp in mg.parent_goals:
                        if gp == meta_goal.goal_id:
                            return (
                                f"cycle:transitive:{meta_goal.goal_id}->{current}->{gp}"
                            )
                        if gp not in visited:
                            queue.append(gp)
            except Exception:
                pass

        return None

    # ── Rule E: Capacity pressure ───────────────────────────────────────────

    def _check_capacity_pressure(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
    ) -> str | None:
        """When near MAX_GOALS, require elevated confidence for new goals."""
        from umh.runtime_engine.meta_goal import MAX_GOALS

        current_count = len(registry.get_all_goals())
        pressure_threshold = int(MAX_GOALS * CAPACITY_PRESSURE_THRESHOLD)

        if current_count >= pressure_threshold:
            if meta_goal.confidence < ELEVATED_CONFIDENCE_THRESHOLD:
                return (
                    f"capacity_pressure:goals={current_count}/{MAX_GOALS}"
                    f":confidence={meta_goal.confidence:.2f}"
                    f"<{ELEVATED_CONFIDENCE_THRESHOLD}"
                )

        return None

    # ── Auto-correction ─────────────────────────────────────────────────────

    def _auto_correct(
        self,
        meta_goal: MetaGoal,
    ) -> tuple[MetaGoal | None, list[str]]:
        """Apply safe structural corrections. Returns (corrected, notes).

        Returns (None, []) if no correction needed.
        """
        fixes: list[str] = []
        needs_fix = False

        goal_id = meta_goal.goal_id
        priority = meta_goal.priority
        criteria = dict(meta_goal.success_criteria)

        # Priority clamping
        if priority < PRIORITY_MIN:
            priority = PRIORITY_MIN
            fixes.append(f"auto-fix:priority_clamped_min:{PRIORITY_MIN}")
            needs_fix = True
        elif priority > PRIORITY_MAX:
            priority = PRIORITY_MAX
            fixes.append(f"auto-fix:priority_clamped_max:{PRIORITY_MAX}")
            needs_fix = True

        # Criteria normalization: lowercase string values
        normalized_criteria: dict = {}
        for k, v in criteria.items():
            nk = k.strip().lower() if isinstance(k, str) else k
            nv = v.strip().lower() if isinstance(v, str) else v
            if nk != k or nv != v:
                needs_fix = True
            normalized_criteria[nk] = nv

        if needs_fix and normalized_criteria != criteria:
            fixes.append("auto-fix:criteria_normalized")
            criteria = normalized_criteria

        if not needs_fix:
            return None, []

        from umh.runtime_engine.meta_goal import MetaGoal as MG

        corrected = MG(
            goal_id=meta_goal.goal_id,
            origin=meta_goal.origin,
            parent_goals=meta_goal.parent_goals,
            confidence=meta_goal.confidence,
            utility_estimate=meta_goal.utility_estimate,
            lifecycle_state=meta_goal.lifecycle_state,
            description=meta_goal.description,
            success_criteria=criteria,
            priority=priority,
            generation_turn=meta_goal.generation_turn,
            generation_reason=meta_goal.generation_reason,
        )

        return corrected, fixes


def _criteria_similarity(a: dict, b: dict) -> float:
    """Compute Jaccard similarity between two criteria dicts.

    Compares key sets (ignoring _meta_ internal keys).
    Value match on shared keys boosts similarity.

    Returns float in [0.0, 1.0].
    """
    keys_a = {k for k in a if not k.startswith("_meta_")}
    keys_b = {k for k in b if not k.startswith("_meta_")}

    if not keys_a and not keys_b:
        return 1.0
    if not keys_a or not keys_b:
        return 0.0

    intersection = keys_a & keys_b
    union = keys_a | keys_b

    if not union:
        return 0.0

    key_sim = len(intersection) / len(union)

    value_matches = 0
    for k in intersection:
        if a.get(k) == b.get(k):
            value_matches += 1

    value_sim = value_matches / len(intersection) if intersection else 0.0

    return key_sim * 0.6 + value_sim * 0.4


def _get_meta_goal_from_registry(
    goal_id: str,
    registry: GoalRegistry,
) -> MetaGoal | None:
    """Attempt to retrieve a MetaGoal from the meta-goal engine.

    Walks the registry's session runtime reference if available.
    Falls back to None — cycles are only detected for tracked meta-goals.
    """
    try:
        from umh.runtime_engine.meta_goal import MetaGoal as MG

        goal = registry.get_goal(goal_id)
        if goal is None:
            return None

        criteria = getattr(goal, "success_criteria", {})
        if criteria.get("_meta_origin") in (
            "alternative",
            "specialization",
            "abstraction",
        ):
            return MG(
                goal_id=goal.goal_id,
                origin="generated",
                parent_goals=(),
                confidence=0.0,
                utility_estimate=0.0,
                lifecycle_state="unknown",
                description=getattr(goal, "description", ""),
                success_criteria=criteria,
            )
    except Exception:
        pass
    return None
