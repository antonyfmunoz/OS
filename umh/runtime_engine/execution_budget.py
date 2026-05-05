"""
ExecutionBudget — deterministic effort allocation across blended goals.

Converts BlendedGoalState weights into concrete execution parameters:
    - candidate_slots: how many LLM candidates each goal gets
    - token_budget_ratio: proportional token allocation per goal
    - reasoning_depth_weight: how much reasoning depth to invest

The budget shapes the *inputs* to multi_strategy's generate_candidates()
without modifying the ExecutionSpine. The spine remains stateless and
unaware of goal allocation.

Rounding: largest-remainder method (deterministic, fair, always sums to
total). Same algorithm used for parliamentary seat allocation.

No LLM calls. No randomness. Pure function of blend weights + constants.

Usage::

    from umh.runtime_engine.execution_budget import derive_budget, BudgetAllocation

    budget = derive_budget(blended_goal_state, total_candidates=6)
    # budget.allocations → list of ExecutionBudget per goal
    # budget.total_candidates → 6
    # sum of candidate_slots == total_candidates
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.runtime_engine.goal_arbitrator import BlendedGoalState

# ─── Constants ────────────────────────────────────────────────────────────────

MIN_CANDIDATES_PER_GOAL = 1
DEFAULT_TOTAL_CANDIDATES = 4
MAX_TOTAL_CANDIDATES = 8
MIN_REASONING_DEPTH = 0.3


@dataclass(frozen=True)
class ExecutionBudget:
    """Per-goal execution allocation for a single turn."""

    goal_id: str
    weight: float
    token_budget_ratio: float
    candidate_slots: int
    reasoning_depth_weight: float

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "weight": round(self.weight, 4),
            "token_budget_ratio": round(self.token_budget_ratio, 4),
            "candidate_slots": self.candidate_slots,
            "reasoning_depth_weight": round(self.reasoning_depth_weight, 4),
        }


@dataclass(frozen=True)
class BudgetAllocation:
    """Complete per-turn budget allocation across all blended goals."""

    allocations: tuple[ExecutionBudget, ...]
    total_candidates: int
    primary_goal_id: str

    def to_dict(self) -> dict:
        return {
            "allocations": [a.to_dict() for a in self.allocations],
            "total_candidates": self.total_candidates,
            "primary_goal_id": self.primary_goal_id,
        }

    def get_budget(self, goal_id: str) -> ExecutionBudget | None:
        for a in self.allocations:
            if a.goal_id == goal_id:
                return a
        return None

    @property
    def candidate_distribution(self) -> dict[str, int]:
        return {a.goal_id: a.candidate_slots for a in self.allocations}


NO_BUDGET = BudgetAllocation(
    allocations=(),
    total_candidates=0,
    primary_goal_id="",
)


def _largest_remainder_round(
    weights: list[float],
    total: int,
    minimum: int = MIN_CANDIDATES_PER_GOAL,
) -> list[int]:
    """Deterministic rounding that preserves the total.

    1. Assign each entry at least ``minimum``.
    2. Distribute remaining slots by weight using largest-remainder.
    3. Tie-break: lower index wins (deterministic — index order matches
       weight-descending sort from BlendedGoalState).

    Always returns a list summing to exactly ``total``.
    """
    n = len(weights)
    if n == 0:
        return []

    floor_total = minimum * n
    if floor_total >= total:
        result = [minimum] * n
        overflow = floor_total - total
        for i in range(n - 1, -1, -1):
            if overflow <= 0:
                break
            can_remove = result[i] - 0
            remove = min(can_remove, overflow)
            result[i] -= remove
            overflow -= remove
        return result

    remaining = total - floor_total

    raw = [w * remaining for w in weights]
    floors = [math.floor(r) for r in raw]
    remainders = [(raw[i] - floors[i], i) for i in range(n)]

    allocated = sum(floors)
    leftover = remaining - allocated

    remainders.sort(key=lambda x: (-x[0], x[1]))
    for j in range(leftover):
        idx = remainders[j][1]
        floors[idx] += 1

    return [minimum + floors[i] for i in range(n)]


def derive_budget(
    blended: BlendedGoalState,
    total_candidates: int = DEFAULT_TOTAL_CANDIDATES,
    exploration_modifier: float = 1.0,
) -> BudgetAllocation:
    """Convert BlendedGoalState into concrete execution allocations.

    Each goal in the blend receives:
        - candidate_slots: integer count from largest-remainder rounding
        - token_budget_ratio: same as blend weight (continuous)
        - reasoning_depth_weight: max(weight, MIN_REASONING_DEPTH)

    When ``exploration_modifier`` > 1.0, secondary goals get relatively
    more slots (spreading exploration). When < 1.0, the primary goal
    concentrates slots (exploitation). Modifier is applied to weights
    before rounding.

    Single goal → all slots. Empty blend → NO_BUDGET.
    """
    goals = getattr(blended, "goals", ())
    primary = getattr(blended, "primary_goal_id", "")

    if not goals:
        return NO_BUDGET

    total_candidates = max(total_candidates, len(goals))
    total_candidates = min(total_candidates, MAX_TOTAL_CANDIDATES)

    if len(goals) == 1:
        gid, w = goals[0]
        return BudgetAllocation(
            allocations=(
                ExecutionBudget(
                    goal_id=gid,
                    weight=w,
                    token_budget_ratio=1.0,
                    candidate_slots=total_candidates,
                    reasoning_depth_weight=1.0,
                ),
            ),
            total_candidates=total_candidates,
            primary_goal_id=primary,
        )

    raw_weights = [w for _, w in goals]
    # Apply exploration modifier: boost secondary goals relative to primary
    if exploration_modifier != 1.0 and len(raw_weights) > 1:
        modified = []
        for i, (gid, w) in enumerate(goals):
            if gid == primary:
                modified.append(w)
            else:
                modified.append(w * max(0.1, exploration_modifier))
        total_w = sum(modified)
        weights = [mw / total_w for mw in modified] if total_w > 0 else raw_weights
    else:
        weights = raw_weights
    slots = _largest_remainder_round(weights, total_candidates)

    allocations: list[ExecutionBudget] = []
    for i, (gid, w) in enumerate(goals):
        allocations.append(
            ExecutionBudget(
                goal_id=gid,
                weight=w,
                token_budget_ratio=w,
                candidate_slots=slots[i],
                reasoning_depth_weight=max(w, MIN_REASONING_DEPTH),
            )
        )

    return BudgetAllocation(
        allocations=tuple(allocations),
        total_candidates=total_candidates,
        primary_goal_id=primary,
    )
