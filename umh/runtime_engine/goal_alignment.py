"""
GoalAlignmentEvaluator — higher-order utility and system-level alignment gate.

Previous behavior: GoalValidator checks structural validity (redundancy,
degenerate, dominated, cycles, capacity). Valid goals enter GoalRegistry
unconditionally. No check on whether a goal is *globally desirable*.

This module scores goals on alignment signals derived from existing
runtime data — no new data sources, no LLM calls, no randomness:

    A. Historical consistency — unstable delta history → penalty
    B. Outcome-adjusted utility — poor outcome correlation → penalty
    C. Resource efficiency — high budget consumption with low wins → penalty
    D. Conflict detection — negative impact on other goals → penalty
    E. Persistence bias — long-surviving consistent goals → boost

AlignmentResult carries:
    - alignment_score (0.0–1.0)
    - penalties (what was penalized and why)
    - adjusted_priority (post-alignment priority)
    - allowed (whether goal may enter registry)

Usage::

    from umh.runtime_engine.goal_alignment import GoalAlignmentEvaluator, AlignmentResult

    evaluator = GoalAlignmentEvaluator()
    result = evaluator.evaluate_alignment(meta_goal, registry, traces)
    if result.allowed:
        registry.add_goal(goal_state_with_adjusted_priority)
    else:
        log_rejection(result.penalties)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.runtime_engine.decision_trace import DecisionTrace
    from umh.goals.state import GoalRegistry
    from umh.runtime_engine.meta_goal import MetaGoal

_log = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

ALIGNMENT_FLOOR = 0.0
ALIGNMENT_CEILING = 1.0

DISALLOW_THRESHOLD = 0.25
DOWNWEIGHT_THRESHOLD = 0.50

# Signal A: Historical consistency
CONSISTENCY_WINDOW = 10
CONSISTENCY_PENALTY_THRESHOLD = 0.35

# Signal B: Outcome-adjusted utility
OUTCOME_WINDOW = 10
OUTCOME_PENALTY_THRESHOLD = 0.30

# Signal C: Resource efficiency
EFFICIENCY_MIN_USES = 3
EFFICIENCY_PENALTY_THRESHOLD = 0.25

# Signal D: Conflict detection
CONFLICT_DELTA_THRESHOLD = -0.10

# Signal E: Persistence bias
PERSISTENCE_MIN_USES = 5
PERSISTENCE_SCORE_THRESHOLD = 0.55
PERSISTENCE_BOOST = 0.08

# Signal weights (sum to 1.0)
W_CONSISTENCY = 0.25
W_OUTCOME = 0.20
W_EFFICIENCY = 0.20
W_CONFLICT = 0.20
W_PERSISTENCE = 0.15


# ─── Data model ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AlignmentResult:
    """Outcome of evaluating a goal's system-level alignment."""

    alignment_score: float
    penalties: tuple[str, ...]
    adjusted_priority: float
    allowed: bool

    def to_dict(self) -> dict:
        return {
            "alignment_score": round(self.alignment_score, 4),
            "penalties": list(self.penalties),
            "adjusted_priority": round(self.adjusted_priority, 4),
            "allowed": self.allowed,
        }


# ─── Evaluator ───────────────────────────────────────────────────────────────


class GoalAlignmentEvaluator:
    """Deterministic alignment gate for goals entering the registry.

    Scores each goal on 5 alignment signals derived from existing
    runtime data. No LLM calls, no randomness, no new dependencies.
    """

    def evaluate_alignment(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
        traces: list[DecisionTrace] | None = None,
    ) -> AlignmentResult:
        """Score a MetaGoal on system-level alignment.

        Returns AlignmentResult with allowed=True if the goal passes
        the alignment threshold (possibly with adjusted priority).
        """
        traces = traces or []
        penalties: list[str] = []

        # ── Signal A: Historical consistency ───────────────────────
        consistency_score = self._score_consistency(meta_goal, registry)
        if consistency_score < CONSISTENCY_PENALTY_THRESHOLD:
            penalties.append(
                f"consistency:unstable_delta_history:score={consistency_score:.2f}"
            )

        # ── Signal B: Outcome-adjusted utility ─────────────────────
        outcome_score = self._score_outcome_utility(meta_goal, traces)
        if outcome_score < OUTCOME_PENALTY_THRESHOLD:
            penalties.append(
                f"outcome:poor_outcome_correlation:score={outcome_score:.2f}"
            )

        # ── Signal C: Resource efficiency ──────────────────────────
        efficiency_score = self._score_resource_efficiency(meta_goal, registry, traces)
        if efficiency_score < EFFICIENCY_PENALTY_THRESHOLD:
            penalties.append(
                f"efficiency:high_cost_low_return:score={efficiency_score:.2f}"
            )

        # ── Signal D: Conflict detection ───────────────────────────
        conflict_score = self._score_conflict(meta_goal, registry, traces)
        if conflict_score < 0.5:
            penalties.append(
                f"conflict:negative_impact_on_peers:score={conflict_score:.2f}"
            )

        # ── Signal E: Persistence bias ─────────────────────────────
        persistence_score = self._score_persistence(meta_goal, registry)

        # ── Weighted alignment score ───────────────────────────────
        raw_score = (
            W_CONSISTENCY * consistency_score
            + W_OUTCOME * outcome_score
            + W_EFFICIENCY * efficiency_score
            + W_CONFLICT * conflict_score
            + W_PERSISTENCE * persistence_score
        )

        alignment_score = max(ALIGNMENT_FLOOR, min(ALIGNMENT_CEILING, raw_score))

        # ── Priority adjustment ────────────────────────────────────
        adjusted_priority = meta_goal.priority * alignment_score

        from umh.runtime_engine.goal_validator import PRIORITY_MIN

        adjusted_priority = max(adjusted_priority, PRIORITY_MIN)

        # ── Allow/disallow decision ────────────────────────────────
        allowed = alignment_score >= DISALLOW_THRESHOLD

        return AlignmentResult(
            alignment_score=alignment_score,
            penalties=tuple(penalties),
            adjusted_priority=adjusted_priority,
            allowed=allowed,
        )

    # ── Signal A: Historical consistency ──────────────────────────────────

    def _score_consistency(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
    ) -> float:
        """Score based on parent goal's delta stability.

        New goals with no parent history get a neutral 0.5.
        Goals whose parents have stable positive deltas score higher.
        Goals whose parents have volatile/negative deltas score lower.
        """
        if not meta_goal.parent_goals:
            return 0.5

        best_parent_score = 0.0
        found_parent = False

        for pid in meta_goal.parent_goals:
            tracker = registry.get_tracker(pid)
            if tracker is None:
                continue
            found_parent = True

            history = tracker.delta_history[-CONSISTENCY_WINDOW:]
            if not history:
                best_parent_score = max(best_parent_score, 0.5)
                continue

            mean_delta = sum(history) / len(history)
            variance = sum((d - mean_delta) ** 2 for d in history) / len(history)
            std_dev = math.sqrt(variance)

            stability = max(0.0, 1.0 - std_dev * 2.0)
            direction = 0.5 + min(max(mean_delta, -0.5), 0.5)

            parent_score = stability * 0.6 + direction * 0.4
            best_parent_score = max(best_parent_score, parent_score)

        return best_parent_score if found_parent else 0.5

    # ── Signal B: Outcome-adjusted utility ────────────────────────────────

    def _score_outcome_utility(
        self,
        meta_goal: MetaGoal,
        traces: list,
    ) -> float:
        """Score based on outcome correlation for parent goals.

        Looks at recent traces where parent goals were active and
        had outcome feedback. Goals from parents with good outcomes
        score higher.

        New goals with no outcome history get neutral 0.5.
        """
        if not meta_goal.parent_goals:
            return 0.5

        parent_ids = set(meta_goal.parent_goals)
        outcome_scores: list[float] = []

        recent = traces[-OUTCOME_WINDOW:] if traces else []
        for trace in recent:
            active_id = getattr(trace, "active_goal_id", None)
            if active_id not in parent_ids:
                continue
            outcome = getattr(trace, "outcome_score", None)
            if outcome is not None:
                outcome_scores.append(outcome)

        if not outcome_scores:
            return 0.5

        return sum(outcome_scores) / len(outcome_scores)

    # ── Signal C: Resource efficiency ─────────────────────────────────────

    def _score_resource_efficiency(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
        traces: list,
    ) -> float:
        """Score based on budget consumption vs performance.

        A parent goal that consumed budget slots but maintained low
        success_score is resource-inefficient. Its children inherit
        that penalty.

        New goals with insufficient history get neutral 0.5.
        """
        if not meta_goal.parent_goals:
            return 0.5

        parent_ids = set(meta_goal.parent_goals)
        efficiency_scores: list[float] = []

        for pid in parent_ids:
            tracker = registry.get_tracker(pid)
            if tracker is None:
                continue
            if tracker.uses < EFFICIENCY_MIN_USES:
                continue

            success = tracker.success_score

            budget_usage = _compute_budget_usage(pid, traces)

            if budget_usage > 0.0:
                efficiency = success / max(budget_usage, 0.01)
                efficiency = min(efficiency, 1.0)
            else:
                efficiency = success

            efficiency_scores.append(efficiency)

        if not efficiency_scores:
            return 0.5

        return sum(efficiency_scores) / len(efficiency_scores)

    # ── Signal D: Conflict detection ──────────────────────────────────────

    def _score_conflict(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
        traces: list,
    ) -> float:
        """Score based on whether this goal's parents harmed peers.

        When a parent goal was active and OTHER goals' deltas went
        negative, that signals conflict. Higher conflict → lower score.

        No conflict history → neutral 1.0 (no penalty).
        """
        if not meta_goal.parent_goals:
            return 1.0

        parent_ids = set(meta_goal.parent_goals)
        all_goal_ids = {g.goal_id for g in registry.get_all_goals()}
        peer_ids = all_goal_ids - parent_ids - {meta_goal.goal_id}

        if not peer_ids:
            return 1.0

        conflict_count = 0
        relevant_turns = 0

        recent = traces[-OUTCOME_WINDOW:] if traces else []
        for trace in recent:
            active_id = getattr(trace, "active_goal_id", None)
            if active_id not in parent_ids:
                continue
            relevant_turns += 1

            pool = getattr(trace, "goal_pool_snapshot", None)
            if not pool or "trackers" not in pool:
                continue

            for peer_id in peer_ids:
                peer_tracker = pool["trackers"].get(peer_id)
                if peer_tracker is None:
                    continue
                peer_delta = peer_tracker.get("latest_delta", 0.0)
                if peer_delta < CONFLICT_DELTA_THRESHOLD:
                    conflict_count += 1

        if relevant_turns == 0:
            return 1.0

        max_conflicts = relevant_turns * max(len(peer_ids), 1)
        conflict_ratio = conflict_count / max_conflicts
        return max(0.0, 1.0 - conflict_ratio * 2.0)

    # ── Signal E: Persistence bias ────────────────────────────────────────

    def _score_persistence(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
    ) -> float:
        """Boost for parent goals with long, consistent performance.

        If any parent has been used >= PERSISTENCE_MIN_USES times
        and has success_score >= PERSISTENCE_SCORE_THRESHOLD, the
        child gets a persistence boost above neutral.

        Otherwise returns neutral 0.5.
        """
        if not meta_goal.parent_goals:
            return 0.5

        for pid in meta_goal.parent_goals:
            tracker = registry.get_tracker(pid)
            if tracker is None:
                continue
            if (
                tracker.uses >= PERSISTENCE_MIN_USES
                and tracker.success_score >= PERSISTENCE_SCORE_THRESHOLD
            ):
                return 0.5 + PERSISTENCE_BOOST

        return 0.5


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _compute_budget_usage(
    goal_id: str,
    traces: list,
) -> float:
    """Average budget ratio allocated to a goal across recent traces.

    Returns 0.0 if no budget data found.
    """
    ratios: list[float] = []

    recent = traces[-OUTCOME_WINDOW:] if traces else []
    for trace in recent:
        budget_dict = getattr(trace, "execution_budget", None)
        if not budget_dict:
            continue

        allocations = budget_dict.get("allocations")
        if not allocations:
            continue

        for alloc in allocations:
            if isinstance(alloc, dict) and alloc.get("goal_id") == goal_id:
                ratios.append(alloc.get("token_budget_ratio", 0.0))
                break

    if not ratios:
        return 0.0

    return sum(ratios) / len(ratios)
