"""
GoalArbitrator — deterministic multi-goal selection engine.

Given a pool of goals with their runtime trackers, computes a utility
score for each and selects the one with highest utility as the active
goal for the current turn.

Utility function (deterministic, no randomness)::

    utility = W_PRIORITY * priority
            + W_SCORE * success_score
            + W_DELTA * clamp(latest_delta, -1, 1)
            + W_RECENCY * recency_weight

Tie-breaking: alphabetical goal_id (deterministic ordering).

Priority: Control > Convergence > Goal arbitration.
Arbitration only selects which goal is active — it does not override
any layer's gating decisions.

No LLM calls. No randomness. Pure function of goal pool + trackers.

Usage::

    from umh.runtime_engine.goal_arbitrator import GoalArbitrator

    arbitrator = GoalArbitrator()
    selected = arbitrator.select_active_goal(registry)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.goals.state import GoalRegistry, GoalState

_log = logging.getLogger(__name__)

# ─── Utility weights (deterministic constants) ────────────────────────────────

W_PRIORITY = 0.35
W_SCORE = 0.30
W_DELTA = 0.20
W_RECENCY = 0.15

SWITCH_COST = 0.10
GOAL_INFLUENCE_SCALE = 0.20

# ─── Blending constants ──────────────────────────────────────────────────────

DEFAULT_BLEND_K = 3
SOFTMAX_TEMPERATURE = 1.0


@dataclass(frozen=True)
class ArbitrationResult:
    """Immutable record of a goal arbitration decision."""

    selected_goal_id: str | None
    utilities: dict[str, float]
    reason: str

    def to_dict(self) -> dict:
        return {
            "selected_goal_id": self.selected_goal_id,
            "utilities": {k: round(v, 4) for k, v in self.utilities.items()},
            "reason": self.reason,
        }


NO_ARBITRATION = ArbitrationResult(
    selected_goal_id=None,
    utilities={},
    reason="no_goals",
)


@dataclass(frozen=True)
class BlendedGoalState:
    """Immutable weighted mixture of top-K goals for a single turn."""

    goals: tuple[tuple[str, float], ...]
    primary_goal_id: str
    entropy: float

    def to_dict(self) -> dict:
        return {
            "goals": [(gid, round(w, 4)) for gid, w in self.goals],
            "primary_goal_id": self.primary_goal_id,
            "entropy": round(self.entropy, 4),
        }

    @property
    def weights(self) -> dict[str, float]:
        return dict(self.goals)

    def weight_for(self, goal_id: str) -> float:
        for gid, w in self.goals:
            if gid == goal_id:
                return w
        return 0.0


NO_BLEND = BlendedGoalState(
    goals=(),
    primary_goal_id="",
    entropy=0.0,
)


def _stable_softmax(
    values: list[float], temperature: float = SOFTMAX_TEMPERATURE
) -> list[float]:
    """Numerically stable softmax: subtract max before exp to prevent overflow."""
    if not values:
        return []
    max_v = max(values)
    exps = [math.exp((v - max_v) / temperature) for v in values]
    total = sum(exps)
    if total == 0.0:
        n = len(values)
        return [1.0 / n] * n
    return [e / total for e in exps]


def _shannon_entropy(weights: list[float]) -> float:
    """Shannon entropy of a probability distribution. 0 = concentrated, log(n) = uniform."""
    return -sum(w * math.log(w) if w > 0 else 0.0 for w in weights)


class GoalArbitrator:
    """Deterministic multi-goal selection engine.

    Computes utility for each active goal and selects the maximum.
    When only one goal exists, selects it directly (fast path).
    When no goals exist, returns NO_ARBITRATION.
    """

    def select_active_goal(
        self,
        registry: GoalRegistry,
        previous_active_goal_id: str | None = None,
        influence_score: float = 0.0,
    ) -> ArbitrationResult:
        """Select the active goal from the registry.

        Updates recency weights for all goals based on current turn,
        then computes utility and picks the winner. Applies switch_penalty
        to goals that differ from previous_active_goal_id.

        When ``influence_score`` is provided (from prior turn's influence
        scoring), each goal's utility is scaled multiplicatively by
        ``(1 + influence_score * GOAL_INFLUENCE_SCALE)``. This uniformly
        amplifies or dampens all goals' utilities based on system-wide
        confidence without changing relative ordering.
        """
        goals = registry.get_all_goals()

        if not goals:
            return NO_ARBITRATION

        if len(goals) == 1:
            goal = goals[0]
            return ArbitrationResult(
                selected_goal_id=goal.goal_id,
                utilities={goal.goal_id: 1.0},
                reason="single_goal",
            )

        current_turn = registry.turn
        trackers = registry.get_all_trackers()
        utilities: dict[str, float] = {}

        for goal in goals:
            tracker = trackers.get(goal.goal_id)
            if tracker is None:
                base_util = goal.priority * W_PRIORITY
                if influence_score > 0:
                    base_util *= 1.0 + influence_score * GOAL_INFLUENCE_SCALE
                utilities[goal.goal_id] = base_util
                continue

            tracker.compute_recency(current_turn)

            delta_clamped = max(-1.0, min(1.0, tracker.latest_delta))

            utility = (
                W_PRIORITY * goal.priority
                + W_SCORE * tracker.success_score
                + W_DELTA * delta_clamped
                + W_RECENCY * tracker.recency_weight
            )
            if influence_score > 0:
                utility *= 1.0 + influence_score * GOAL_INFLUENCE_SCALE
            utilities[goal.goal_id] = utility

        # Apply switch penalty during arbitration (not stored in utilities)
        final_scores: dict[str, float] = {}
        for gid, util in utilities.items():
            if previous_active_goal_id and gid != previous_active_goal_id:
                final_scores[gid] = util - SWITCH_COST
            else:
                final_scores[gid] = util

        best_id = max(
            final_scores,
            key=lambda gid: (final_scores[gid], gid),
        )

        _switch_applied = (
            previous_active_goal_id is not None and best_id != previous_active_goal_id
        )
        _reason = "max_utility"
        if _switch_applied:
            _reason = "max_utility_switched"
        elif previous_active_goal_id is not None:
            _reason = "max_utility_committed"

        _log.debug(
            "Goal arbitration: selected %s (utility=%.4f, final=%.4f) from %d goals",
            best_id,
            utilities[best_id],
            final_scores[best_id],
            len(goals),
        )

        return ArbitrationResult(
            selected_goal_id=best_id,
            utilities=utilities,
            reason=_reason,
        )

    def blend_goals(
        self,
        registry: GoalRegistry,
        k: int = DEFAULT_BLEND_K,
        previous_active_goal_id: str | None = None,
        influence_score: float = 0.0,
    ) -> BlendedGoalState:
        """Compute a weighted blend of top-K goals.

        1. Run select_active_goal to get utilities for all goals.
        2. Pick top-K by utility (deterministic tie-break: alphabetical).
        3. Apply stable softmax to normalize utilities into weights.
        4. Return BlendedGoalState with weights summing to 1.0.

        Single goal or empty → degrades gracefully.
        """
        arb = self.select_active_goal(
            registry,
            previous_active_goal_id=previous_active_goal_id,
            influence_score=influence_score,
        )

        if arb.selected_goal_id is None:
            return NO_BLEND

        utilities = arb.utilities
        if len(utilities) == 1:
            gid = arb.selected_goal_id
            return BlendedGoalState(
                goals=((gid, 1.0),),
                primary_goal_id=gid,
                entropy=0.0,
            )

        sorted_goals = sorted(
            utilities.items(),
            key=lambda item: (-item[1], item[0]),
        )
        top_k = sorted_goals[:k]

        ids = [gid for gid, _ in top_k]
        raw_utils = [u for _, u in top_k]
        weights = _stable_softmax(raw_utils)

        goal_weights = tuple(zip(ids, weights))

        primary_id = ids[0]
        entropy = _shannon_entropy(weights)

        return BlendedGoalState(
            goals=goal_weights,
            primary_goal_id=primary_id,
            entropy=entropy,
        )

    def compute_utility(
        self,
        goal: GoalState,
        registry: GoalRegistry,
        previous_active_goal_id: str | None = None,
    ) -> float:
        """Compute utility for a single goal (for inspection/testing).

        Returns raw utility without switch_penalty (penalty is arbitration-only).
        """
        tracker = registry.get_tracker(goal.goal_id)
        if tracker is None:
            return goal.priority * W_PRIORITY

        tracker.compute_recency(registry.turn)
        delta_clamped = max(-1.0, min(1.0, tracker.latest_delta))

        return (
            W_PRIORITY * goal.priority
            + W_SCORE * tracker.success_score
            + W_DELTA * delta_clamped
            + W_RECENCY * tracker.recency_weight
        )
