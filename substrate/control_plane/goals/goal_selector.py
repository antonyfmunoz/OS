"""
GoalSelector — goal selection + system focus layer (Phase 9D + 9E + 9F).

Determines WHICH goals the system pursues, not how to execute them.
Goals compete for attention through a weighted scoring model.
Only ACTIVE goals produce tasks — everything else is silent.

Phase 9E adds outcome-driven reweighting: goals that succeed rise,
goals that fail drop. Performance profiles are updated in real time
via EventBus and scored with exponential time decay.

Phase 9F adds cross-goal learning and opportunity cost:
- Goals are scored RELATIVE to alternatives, not just individually
- Active goals are penalized when deferred alternatives outperform them
- Swap pressure with hysteresis: sustained superiority triggers replacement
- Portfolio-level optimization: best SET of goals, not best individuals

Sits above strategy (8B/8C) and attention (9A).
Feeds task_executor and downstream execution layers.

Usage:
    from substrate.control_plane.goals.goal_selector import (
        GoalSelector, Goal, GoalState, OutcomeTracker, OpportunityCostLayer,
    )

    selector = GoalSelector(org_id=ORG_ID)

    # Add a goal
    goal = selector.add_goal(
        title="Close first Initiate Arena sale",
        expected_impact=0.9,
        estimated_cost=0.3,
        priority=10,
    )

    # Run selection cycle — picks top N goals as ACTIVE
    # Now includes opportunity cost + swap pressure (9F)
    active = selector.run_selection_cycle()

    # Record an outcome (normally via EventBus)
    tracker = OutcomeTracker(org_id=ORG_ID)
    tracker.record_outcome(goal.id, "success", execution_time=12.5)

    # Next cycle: scoring adapts based on outcomes + relative performance
    active = selector.run_selection_cycle()
"""

import json
import math
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from substrate.state.storage.db import get_conn, ORG_ID


# ─── Goal states ─────────────────────────────────────────────────────────────


class GoalState(Enum):
    ACTIVE = "active"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    DROPPED = "dropped"


# Terminal states — goals here never re-enter scoring
_TERMINAL_STATES = frozenset({GoalState.COMPLETED, GoalState.DROPPED})

# States eligible for scoring each cycle
_SCORABLE_STATES = frozenset({GoalState.ACTIVE, GoalState.DEFERRED})


# ─── Scoring weights ────────────────────────────────────────────────────────

DEFAULT_WEIGHTS = {
    "priority": 0.25,
    "expected_impact": 0.20,
    "estimated_cost_inverse": 0.12,
    "confidence": 0.08,
    "recency": 0.08,
    "dependency_unlock": 0.07,
    "performance": 0.20,
}

DEFAULT_FOCUS_BUDGET = 3

# Outcome decay: 24-hour half-life in seconds
DECAY_HALF_LIFE = 86400.0

# Phase 9F: Cross-goal learning + opportunity cost
OPPORTUNITY_COST_WEIGHT = 0.10
SWAP_THRESHOLD = 0.05
SWAP_SUSTAINED_CYCLES = 3

# Phase 9G: Multi-timescale decision + strategic horizon
SHORT_TERM_HALF_LIFE = 21600.0  # 6 hours in seconds
MEDIUM_TERM_HALF_LIFE = 86400.0  # 24 hours (same as original DECAY_HALF_LIFE)
LONG_TERM_HALF_LIFE = 604800.0  # 7 days in seconds

HORIZON_WEIGHTS = {
    "short": 0.40,
    "medium": 0.40,
    "long": 0.20,
}

STABILITY_BONUS_THRESHOLD = 0.6
STABILITY_BONUS_MAX = 0.03

# Phase 9H: Failure-aware priority decay
FAILURE_THRESHOLD = 5
DECAY_FACTOR = 0.7
MIN_PRIORITY_MULTIPLIER = 0.3


# ─── Performance profile ────────────────────────────────────────────────────


@dataclass
class PerformanceProfile:
    """Accumulated execution outcome data for a goal."""

    success_rate: float = 0.0  # 0.0-1.0
    efficiency: float = 0.0  # 0.0-1.0 (faster = higher)
    reliability: float = 0.0  # 0.0-1.0 (fewer retries = higher)
    impact_score: float = 0.0  # 0.0-1.0 (downstream unlock / task completion)
    total_outcomes: int = 0
    total_successes: int = 0
    total_failures: int = 0
    avg_execution_time: float = 0.0
    last_outcome_at: Optional[datetime] = None

    def composite(self) -> float:
        """Single 0-1 performance signal for scoring."""
        if self.total_outcomes == 0:
            return 0.5  # neutral — no data yet
        return (
            self.success_rate * 0.40
            + self.efficiency * 0.20
            + self.reliability * 0.20
            + self.impact_score * 0.20
        )

    def to_dict(self) -> dict:
        return {
            "success_rate": round(self.success_rate, 4),
            "efficiency": round(self.efficiency, 4),
            "reliability": round(self.reliability, 4),
            "impact_score": round(self.impact_score, 4),
            "total_outcomes": self.total_outcomes,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "avg_execution_time": round(self.avg_execution_time, 2),
            "last_outcome_at": self.last_outcome_at.isoformat() if self.last_outcome_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PerformanceProfile":
        last = data.get("last_outcome_at")
        if isinstance(last, str):
            last = datetime.fromisoformat(last)
        return cls(
            success_rate=float(data.get("success_rate", 0.0)),
            efficiency=float(data.get("efficiency", 0.0)),
            reliability=float(data.get("reliability", 0.0)),
            impact_score=float(data.get("impact_score", 0.0)),
            total_outcomes=int(data.get("total_outcomes", 0)),
            total_successes=int(data.get("total_successes", 0)),
            total_failures=int(data.get("total_failures", 0)),
            avg_execution_time=float(data.get("avg_execution_time", 0.0)),
            last_outcome_at=last,
        )


# ─── Multi-horizon profile (Phase 9G) ─────────────────────────────────────


@dataclass
class MultiHorizonProfile:
    """Performance viewed through three time windows."""

    short_term: PerformanceProfile = field(default_factory=PerformanceProfile)
    medium_term: PerformanceProfile = field(default_factory=PerformanceProfile)
    long_term: PerformanceProfile = field(default_factory=PerformanceProfile)

    def composites(self) -> dict[str, float]:
        return {
            "short": self.short_term.composite(),
            "medium": self.medium_term.composite(),
            "long": self.long_term.composite(),
        }

    def weighted_composite(self, weights: dict[str, float] | None = None) -> float:
        w = weights or HORIZON_WEIGHTS
        c = self.composites()
        return c["short"] * w["short"] + c["medium"] * w["medium"] + c["long"] * w["long"]

    def has_outcomes(self) -> bool:
        return self.medium_term.total_outcomes > 0

    def to_dict(self) -> dict:
        return {
            "short_term": self.short_term.to_dict(),
            "medium_term": self.medium_term.to_dict(),
            "long_term": self.long_term.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MultiHorizonProfile":
        if not data:
            return cls()
        if "short_term" not in data:
            single = PerformanceProfile.from_dict(data)
            return cls(short_term=single, medium_term=single, long_term=single)
        return cls(
            short_term=PerformanceProfile.from_dict(data.get("short_term") or {}),
            medium_term=PerformanceProfile.from_dict(data.get("medium_term") or {}),
            long_term=PerformanceProfile.from_dict(data.get("long_term") or {}),
        )


# ─── Goal dataclass ─────────────────────────────────────────────────────────


@dataclass
class Goal:
    id: str
    org_id: str
    title: str
    description: str = ""
    state: GoalState = GoalState.DEFERRED
    priority: int = 5  # 1-10, user input
    expected_impact: float = 0.5  # 0.0-1.0
    estimated_cost: float = 0.5  # 0.0-1.0 (higher = more expensive)
    confidence: float = 0.5  # 0.0-1.0
    dependency_unlock: int = 0  # how many other goals this unblocks
    venture_id: Optional[str] = None
    blocked_by: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    score: float = 0.0
    base_score: float = 0.0
    performance_adjustment: float = 0.0
    opportunity_cost_adjustment: float = 0.0
    stability_bonus: float = 0.0
    horizon_adjustments: dict[str, float] = field(
        default_factory=lambda: {"short": 0.0, "medium": 0.0, "long": 0.0}
    )
    rank: int = 0
    score_explanation: list[str] = field(default_factory=list)
    performance: PerformanceProfile = field(default_factory=PerformanceProfile)
    horizons: MultiHorizonProfile = field(default_factory=MultiHorizonProfile)
    swap_pressure_cycles: int = 0
    failure_streak: int = 0
    priority_decay_multiplier: float = 1.0


# ─── Opportunity Cost Layer (Phase 9F) ──────────────────────────────────────


class OpportunityCostLayer:
    """
    Cross-goal relative scoring: penalizes active goals when deferred
    alternatives have stronger historical performance.

    Operates on a scored list of goals (base + performance already computed).
    Adds opportunity_cost_adjustment to each scorable goal.
    """

    def __init__(
        self,
        weight: float = OPPORTUNITY_COST_WEIGHT,
        swap_threshold: float = SWAP_THRESHOLD,
        sustained_cycles: int = SWAP_SUSTAINED_CYCLES,
    ):
        self.weight = weight
        self.swap_threshold = swap_threshold
        self.sustained_cycles = sustained_cycles

    def compute_relative_penalties(
        self,
        goals: list[Goal],
        focus_budget: int,
    ) -> list[Goal]:
        """
        For each active goal, compare its performance composite against
        the mean performance of deferred goals. Penalize if below average.

        Mutates goal.opportunity_cost_adjustment and appends to score_explanation.
        """
        active = [g for g in goals if g.state == GoalState.ACTIVE]
        deferred = [g for g in goals if g.state == GoalState.DEFERRED]

        if not deferred:
            for g in goals:
                g.opportunity_cost_adjustment = 0.0
            return goals

        deferred_composites = [g.performance.composite() for g in deferred]
        deferred_mean = sum(deferred_composites) / len(deferred_composites)

        for g in goals:
            if g.state != GoalState.ACTIVE:
                g.opportunity_cost_adjustment = 0.0
                continue

            own_composite = g.performance.composite()

            if g.performance.total_outcomes == 0:
                g.opportunity_cost_adjustment = 0.0
                g.score_explanation.append("opportunity_cost=0 (no outcomes)")
                continue

            # Penalty: how much worse is this goal vs deferred alternatives?
            relative_delta = own_composite - deferred_mean
            if relative_delta >= 0:
                g.opportunity_cost_adjustment = 0.0
                g.score_explanation.append(
                    f"opportunity_cost=0 (outperforms deferred mean {deferred_mean:.2f})"
                )
            else:
                penalty = relative_delta * self.weight
                g.opportunity_cost_adjustment = round(penalty, 4)
                g.score += g.opportunity_cost_adjustment
                g.score = round(g.score, 4)
                g.score_explanation.append(
                    f"opportunity_cost={penalty:.4f} "
                    f"(own={own_composite:.2f} vs deferred_mean={deferred_mean:.2f})"
                )

        return goals

    def evaluate_swap_pressure(
        self,
        active_goals: list[Goal],
        deferred_goals: list[Goal],
    ) -> list[tuple[Goal, Goal]]:
        """
        Identify (active, deferred) pairs where the deferred goal should
        replace the active one, subject to hysteresis.

        Returns list of (demote, promote) pairs.
        """
        if not active_goals or not deferred_goals:
            return []

        swaps: list[tuple[Goal, Goal]] = []

        active_sorted = sorted(active_goals, key=lambda g: g.score)

        for active_g in active_sorted:
            best_deferred = max(deferred_goals, key=lambda g: g.score)

            margin = best_deferred.score - active_g.score
            if margin <= self.swap_threshold:
                active_g.swap_pressure_cycles = 0
                continue

            active_g.swap_pressure_cycles += 1

            if active_g.swap_pressure_cycles >= self.sustained_cycles:
                swaps.append((active_g, best_deferred))
                deferred_goals = [g for g in deferred_goals if g.id != best_deferred.id]
                active_g.swap_pressure_cycles = 0

                if not deferred_goals:
                    break

        return swaps

    def explain_goal(self, goal: Goal, all_goals: list[Goal]) -> dict:
        """Opportunity cost explanation for a single goal."""
        deferred = [g for g in all_goals if g.state == GoalState.DEFERRED]
        deferred_composites = [g.performance.composite() for g in deferred] if deferred else []
        deferred_mean = (
            sum(deferred_composites) / len(deferred_composites) if deferred_composites else 0.0
        )

        return {
            "opportunity_cost_adjustment": goal.opportunity_cost_adjustment,
            "own_composite": goal.performance.composite(),
            "deferred_mean_composite": round(deferred_mean, 4),
            "swap_pressure_cycles": goal.swap_pressure_cycles,
            "swap_threshold": self.swap_threshold,
            "sustained_cycles_required": self.sustained_cycles,
        }


# ─── Strategic Horizon Layer (Phase 9G) ────────────────────────────────────


class StrategicHorizonLayer:
    """
    Multi-timescale scoring: evaluates goals across short/medium/long horizons.

    Replaces single-decay performance adjustment with a weighted blend of
    three decay windows. Adds a stability bonus for goals that perform
    consistently across all horizons, making them harder to displace.
    """

    def __init__(
        self,
        horizon_weights: dict[str, float] | None = None,
        stability_threshold: float = STABILITY_BONUS_THRESHOLD,
        stability_max: float = STABILITY_BONUS_MAX,
        performance_weight: float = 0.20,
    ):
        self.horizon_weights = horizon_weights or dict(HORIZON_WEIGHTS)
        self.stability_threshold = stability_threshold
        self.stability_max = stability_max
        self.performance_weight = performance_weight

    def compute_horizon_adjustment(self, goal: Goal) -> float:
        """
        Compute multi-horizon performance adjustment for a single goal.

        Replaces the single-decay performance_adjustment from 9E.
        Returns the total adjustment and mutates goal.horizon_adjustments,
        goal.stability_bonus, and goal.performance_adjustment.

        Backward compat: if horizons has no data but legacy performance does,
        promote the legacy profile to all three horizons.
        """
        horizons = goal.horizons
        if not horizons.has_outcomes() and goal.performance.total_outcomes > 0:
            horizons = MultiHorizonProfile(
                short_term=goal.performance,
                medium_term=goal.performance,
                long_term=goal.performance,
            )
            goal.horizons = horizons
        if not horizons.has_outcomes():
            goal.horizon_adjustments = {"short": 0.0, "medium": 0.0, "long": 0.0}
            goal.stability_bonus = 0.0
            goal.performance_adjustment = 0.0
            return 0.0

        composites = horizons.composites()
        w = self.horizon_weights

        per_horizon: dict[str, float] = {}
        for horizon_name in ("short", "medium", "long"):
            delta = composites[horizon_name] - 0.5
            adj = delta * self.performance_weight * w[horizon_name]
            per_horizon[horizon_name] = round(adj, 4)

        goal.horizon_adjustments = per_horizon

        total_adj = sum(per_horizon.values())

        # Stability bonus: reward goals that perform well across ALL horizons
        bonus = self._compute_stability_bonus(composites)
        goal.stability_bonus = bonus
        total_adj += bonus

        goal.performance_adjustment = round(total_adj, 4)
        return goal.performance_adjustment

    def _compute_stability_bonus(self, composites: dict[str, float]) -> float:
        """
        Bonus for consistent cross-horizon performance.

        If ALL horizons are above the threshold, the goal earns a bonus
        proportional to how far above threshold the minimum horizon is.
        """
        min_composite = min(composites.values())
        if min_composite <= self.stability_threshold:
            return 0.0
        excess = min_composite - self.stability_threshold
        max_excess = 1.0 - self.stability_threshold
        if max_excess <= 0:
            return 0.0
        return round(self.stability_max * (excess / max_excess), 4)

    def build_explanation(self, goal: Goal) -> list[str]:
        """Generate explanation entries for multi-horizon scoring."""
        if not goal.horizons.has_outcomes():
            return ["performance=neutral (no outcomes)"]

        composites = goal.horizons.composites()
        lines: list[str] = []

        for name in ("short", "medium", "long"):
            adj = goal.horizon_adjustments.get(name, 0.0)
            direction = "+" if adj >= 0 else ""
            lines.append(f"perf_{name}={composites[name]:.2f} → {direction}{adj:.4f}")

        if goal.stability_bonus > 0:
            lines.append(f"stability_bonus=+{goal.stability_bonus:.4f}")
        else:
            lines.append("stability_bonus=0 (below threshold or inconsistent)")

        return lines

    def explain_goal(self, goal: Goal) -> dict:
        """Structured explainability for horizon layer."""
        composites = goal.horizons.composites()
        return {
            "short_term": composites["short"],
            "medium_term": composites["medium"],
            "long_term": composites["long"],
            "horizon_adjustments": goal.horizon_adjustments,
            "stability_bonus": goal.stability_bonus,
            "performance_adjustment": goal.performance_adjustment,
            "horizon_weights": self.horizon_weights,
        }


# ─── GoalSelector ────────────────────────────────────────────────────────────


class GoalSelector:
    """
    Scores, ranks, and selects which goals are ACTIVE.

    Pure selection + scoring layer. No execution, no planner mutation.
    """

    def __init__(
        self,
        org_id: str = ORG_ID,
        focus_budget: int = DEFAULT_FOCUS_BUDGET,
        weights: dict[str, float] | None = None,
        opportunity_cost_weight: float = OPPORTUNITY_COST_WEIGHT,
        swap_threshold: float = SWAP_THRESHOLD,
        swap_sustained_cycles: int = SWAP_SUSTAINED_CYCLES,
        horizon_weights: dict[str, float] | None = None,
    ):
        self.org_id = org_id
        self.focus_budget = focus_budget
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        self.opportunity_cost = OpportunityCostLayer(
            weight=opportunity_cost_weight,
            swap_threshold=swap_threshold,
            sustained_cycles=swap_sustained_cycles,
        )
        self.strategic_horizon = StrategicHorizonLayer(
            horizon_weights=horizon_weights,
            performance_weight=self.weights.get("performance", 0.20),
        )

    # ─── Scoring ─────────────────────────────────────────────────────────────

    def score_goal(self, goal: Goal, all_goals: list[Goal]) -> Goal:
        """
        Compute weighted score for a single goal.
        Mutates goal.score, goal.base_score, goal.performance_adjustment,
        and goal.score_explanation in place.
        """
        w = self.weights
        explanation: list[str] = []

        # Priority: normalized 0-1 from 1-10 scale, with failure-aware decay (9H)
        effective_priority = goal.priority * goal.priority_decay_multiplier
        priority_norm = min(effective_priority, 10) / 10.0
        priority_contrib = priority_norm * w["priority"]
        if goal.priority_decay_multiplier < 1.0:
            explanation.append(
                f"priority={goal.priority}/10 × decay={goal.priority_decay_multiplier:.2f} "
                f"→ eff={effective_priority:.1f} → {priority_contrib:.3f} "
                f"(streak={goal.failure_streak})"
            )
        else:
            explanation.append(f"priority={goal.priority}/10 → {priority_contrib:.3f}")

        # Expected impact: already 0-1
        impact_contrib = goal.expected_impact * w["expected_impact"]
        explanation.append(f"impact={goal.expected_impact:.2f} → {impact_contrib:.3f}")

        # Cost inverse: low cost = high score
        cost_inv = 1.0 - goal.estimated_cost
        cost_contrib = cost_inv * w["estimated_cost_inverse"]
        explanation.append(f"cost_inv={cost_inv:.2f} → {cost_contrib:.3f}")

        # Confidence
        conf_contrib = goal.confidence * w["confidence"]
        explanation.append(f"confidence={goal.confidence:.2f} → {conf_contrib:.3f}")

        # Recency: newer goals get slight boost, decays over 30 days
        age_days = (datetime.now(timezone.utc) - goal.created_at).total_seconds() / 86400
        recency_factor = max(0.0, 1.0 - (age_days / 30.0))
        recency_contrib = recency_factor * w["recency"]
        explanation.append(
            f"recency={recency_factor:.2f} ({age_days:.0f}d) → {recency_contrib:.3f}"
        )

        # Dependency unlock: how many goals this unblocks
        unlock_count = self._count_unlocks(goal.id, all_goals)
        goal.dependency_unlock = unlock_count
        unlock_norm = min(unlock_count / max(len(all_goals), 1), 1.0)
        unlock_contrib = unlock_norm * w["dependency_unlock"]
        explanation.append(f"unlocks={unlock_count} → {unlock_contrib:.3f}")

        base = round(
            priority_contrib
            + impact_contrib
            + cost_contrib
            + conf_contrib
            + recency_contrib
            + unlock_contrib,
            4,
        )
        goal.base_score = base

        # Performance adjustment (Phase 9G: multi-horizon)
        perf_adj = self.strategic_horizon.compute_horizon_adjustment(goal)
        explanation.extend(self.strategic_horizon.build_explanation(goal))

        goal.score = round(base + perf_adj, 4)
        goal.score_explanation = explanation
        return goal

    def _performance_decay(self, perf: PerformanceProfile) -> float:
        """Exponential decay: recent outcomes matter more. Returns 0-1."""
        if not perf.last_outcome_at:
            return 1.0
        age_secs = (datetime.now(timezone.utc) - perf.last_outcome_at).total_seconds()
        if age_secs <= 0:
            return 1.0
        return math.exp(-0.693 * age_secs / DECAY_HALF_LIFE)

    def _count_unlocks(self, goal_id: str, all_goals: list[Goal]) -> int:
        """Count how many other goals list this goal_id in their blocked_by."""
        return sum(1 for g in all_goals if goal_id in g.blocked_by)

    # ─── Selection cycle ─────────────────────────────────────────────────────

    def run_selection_cycle(self, goals: list[Goal] | None = None) -> list[Goal]:
        """
        Score all goals, sort, pick top N → ACTIVE, demote rest → DEFERRED.

        Returns only the ACTIVE goals. Mutates state on all scorable goals.
        Blocked/completed/dropped goals are untouched.
        """
        if goals is None:
            goals = self.load_goals()

        scorable = [g for g in goals if g.state in _SCORABLE_STATES]
        blocked = [g for g in goals if g.state == GoalState.BLOCKED]
        terminal = [g for g in goals if g.state in _TERMINAL_STATES]

        # Auto-unblock: if all blockers are completed/dropped, unblock
        for g in blocked:
            if self._blockers_resolved(g, goals):
                g.state = GoalState.DEFERRED
                scorable.append(g)

        # Score all scorable goals
        for g in scorable:
            self.score_goal(g, goals)

        # Sort descending by score — ties broken by priority then creation date
        scorable.sort(key=lambda g: (-g.score, -g.priority, g.created_at))

        # Initial assignment: top N → ACTIVE, rest → DEFERRED
        for i, g in enumerate(scorable):
            if i < self.focus_budget:
                g.state = GoalState.ACTIVE
            else:
                g.state = GoalState.DEFERRED

        # Phase 9F: Apply opportunity cost penalties to active goals
        self.opportunity_cost.compute_relative_penalties(scorable, self.focus_budget)

        # Phase 9F: Evaluate swap pressure (hysteresis-gated)
        active_goals = [g for g in scorable if g.state == GoalState.ACTIVE]
        deferred_goals = [g for g in scorable if g.state == GoalState.DEFERRED]
        swaps = self.opportunity_cost.evaluate_swap_pressure(active_goals, deferred_goals)

        for demote, promote in swaps:
            demote.state = GoalState.DEFERRED
            promote.state = GoalState.ACTIVE
            self._emit_event("goal_swap_triggered", demote, swap_target=promote)

        # Re-sort after adjustments and assign final ranks
        scorable.sort(key=lambda g: (-g.score, -g.priority, g.created_at))
        active: list[Goal] = []
        for i, g in enumerate(scorable):
            g.rank = i + 1
            if g.state == GoalState.ACTIVE:
                active.append(g)

        # Reset swap pressure on goals that stayed active
        for g in active:
            if not any(g.id == promote.id for _, promote in swaps):
                pass  # preserve cycle count for ongoing pressure tracking

        # Persist all state changes
        all_updated = scorable + blocked + terminal
        self._persist_goals(all_updated)
        self._log_cycle(active, scorable)

        return active

    def _blockers_resolved(self, goal: Goal, all_goals: list[Goal]) -> bool:
        """True if every goal in blocked_by is COMPLETED or DROPPED."""
        if not goal.blocked_by:
            return True
        goal_map = {g.id: g for g in all_goals}
        for blocker_id in goal.blocked_by:
            blocker = goal_map.get(blocker_id)
            if blocker and blocker.state not in _TERMINAL_STATES:
                return False
        return True

    # ─── Explainability ──────────────────────────────────────────────────────

    def explain(self, goal: Goal, all_goals: list[Goal] | None = None) -> dict:
        """Return explainability payload for a single goal."""
        effective_priority = goal.priority * goal.priority_decay_multiplier
        result = {
            "id": goal.id,
            "title": goal.title,
            "score": goal.score,
            "base_score": goal.base_score,
            "performance_adjustment": goal.performance_adjustment,
            "opportunity_cost_adjustment": goal.opportunity_cost_adjustment,
            "stability_bonus": goal.stability_bonus,
            "horizon_adjustments": goal.horizon_adjustments,
            "priority_decay_multiplier": goal.priority_decay_multiplier,
            "failure_streak": goal.failure_streak,
            "effective_priority": effective_priority,
            "rank": goal.rank,
            "state": goal.state.value,
            "why": goal.score_explanation,
            "performance": goal.performance.to_dict(),
            "horizons": goal.horizons.to_dict(),
            "dependency_unlock": goal.dependency_unlock,
            "blocked_by": goal.blocked_by,
        }
        if all_goals is not None:
            result["opportunity_cost"] = self.opportunity_cost.explain_goal(
                goal,
                all_goals,
            )
        result["strategic_horizon"] = self.strategic_horizon.explain_goal(goal)
        return result

    # ─── State transitions ───────────────────────────────────────────────────

    def activate(self, goal_id: str) -> Goal:
        """Force a goal to ACTIVE (manual override). Bumps lowest-ranked active goal if at budget."""
        goals = self.load_goals()
        target = self._find_goal(goal_id, goals)
        if target.state in _TERMINAL_STATES:
            raise ValueError(f"Cannot activate {target.state.value} goal")

        active_goals = [g for g in goals if g.state == GoalState.ACTIVE]
        if len(active_goals) >= self.focus_budget and target.state != GoalState.ACTIVE:
            # Demote lowest-ranked active goal
            active_goals.sort(key=lambda g: g.score)
            demoted = active_goals[0]
            demoted.state = GoalState.DEFERRED
            self._persist_goal(demoted)
            self._emit_event("goal_deferred", demoted)

        target.state = GoalState.ACTIVE
        target.updated_at = datetime.now(timezone.utc)
        self._persist_goal(target)
        self._emit_event("goal_activated", target)
        return target

    def defer(self, goal_id: str) -> Goal:
        """Manually defer a goal."""
        goals = self.load_goals()
        target = self._find_goal(goal_id, goals)
        if target.state in _TERMINAL_STATES:
            raise ValueError(f"Cannot defer {target.state.value} goal")
        target.state = GoalState.DEFERRED
        target.updated_at = datetime.now(timezone.utc)
        self._persist_goal(target)
        self._emit_event("goal_deferred", target)
        return target

    def complete(self, goal_id: str) -> Goal:
        """Mark a goal as completed."""
        goals = self.load_goals()
        target = self._find_goal(goal_id, goals)
        target.state = GoalState.COMPLETED
        target.updated_at = datetime.now(timezone.utc)
        self._persist_goal(target)
        self._emit_event("goal_completed", target)
        return target

    def drop(self, goal_id: str) -> Goal:
        """Drop a goal permanently."""
        goals = self.load_goals()
        target = self._find_goal(goal_id, goals)
        target.state = GoalState.DROPPED
        target.updated_at = datetime.now(timezone.utc)
        self._persist_goal(target)
        self._emit_event("goal_dropped", target)
        return target

    def block(self, goal_id: str, blocked_by: list[str]) -> Goal:
        """Mark a goal as blocked by other goal IDs."""
        goals = self.load_goals()
        target = self._find_goal(goal_id, goals)
        target.state = GoalState.BLOCKED
        target.blocked_by = blocked_by
        target.updated_at = datetime.now(timezone.utc)
        self._persist_goal(target)
        self._emit_event("goal_blocked", target)
        return target

    def is_active(self, goal_id: str) -> bool:
        """The gate: only ACTIVE goals produce tasks."""
        try:
            goals = self.load_goals()
            target = self._find_goal(goal_id, goals)
            return target.state == GoalState.ACTIVE
        except ValueError:
            return False

    def _find_goal(self, goal_id: str, goals: list[Goal]) -> Goal:
        for g in goals:
            if g.id == goal_id:
                return g
        raise ValueError(f"Goal not found: {goal_id}")

    # ─── CRUD ────────────────────────────────────────────────────────────────

    def add_goal(
        self,
        title: str,
        description: str = "",
        priority: int = 5,
        expected_impact: float = 0.5,
        estimated_cost: float = 0.5,
        confidence: float = 0.5,
        venture_id: str | None = None,
        blocked_by: list[str] | None = None,
    ) -> Goal:
        """Create a new goal. Starts as DEFERRED — selection cycle activates it."""
        goal = Goal(
            id=str(uuid.uuid4())[:8],
            org_id=self.org_id,
            title=title,
            description=description,
            priority=priority,
            expected_impact=expected_impact,
            estimated_cost=estimated_cost,
            confidence=confidence,
            venture_id=venture_id,
            blocked_by=blocked_by or [],
            state=GoalState.BLOCKED if blocked_by else GoalState.DEFERRED,
        )
        self._persist_goal(goal)
        return goal

    def list_goals(self, state: GoalState | None = None) -> list[Goal]:
        """List all goals, optionally filtered by state."""
        goals = self.load_goals()
        if state:
            return [g for g in goals if g.state == state]
        return goals

    def get_goal(self, goal_id: str) -> Goal:
        """Get a single goal by ID."""
        goals = self.load_goals()
        return self._find_goal(goal_id, goals)

    # ─── Neon persistence ────────────────────────────────────────────────────

    def _persist_goal(self, goal: Goal) -> None:
        """Upsert a single goal to Neon."""
        try:
            from substrate.state.stores.goal_store import GoalStore
            GoalStore().upsert_goal(
                org_id=goal.org_id,
                goal_id=goal.id,
                title=goal.title,
                description=goal.description,
                state=goal.state.value,
                priority=goal.priority,
                expected_impact=goal.expected_impact,
                estimated_cost=goal.estimated_cost,
                confidence=goal.confidence,
                dependency_unlock=goal.dependency_unlock,
                venture_id=goal.venture_id,
                blocked_by=goal.blocked_by,
                score=goal.score,
                rank=goal.rank,
                score_explanation=goal.score_explanation,
                performance=goal.performance.to_dict(),
                created_at=goal.created_at.isoformat(),
                updated_at=goal.updated_at.isoformat(),
            )
        except Exception as e:
            print(f"[GoalSelector] persist failed: {e}")

    def _persist_goals(self, goals: list[Goal]) -> None:
        """Batch persist — one transaction."""
        try:
            from substrate.state.stores.goal_store import GoalStore
            GoalStore().batch_update_rankings(
                org_id=self.org_id,
                goals=[
                    {
                        "id": g.id,
                        "state": g.state.value,
                        "score": g.score,
                        "rank": g.rank,
                        "score_explanation": g.score_explanation,
                        "dependency_unlock": g.dependency_unlock,
                        "performance": g.performance.to_dict(),
                        "horizons": g.horizons.to_dict(),
                        "updated_at": g.updated_at.isoformat(),
                        "opportunity_cost_adjustment": g.opportunity_cost_adjustment,
                        "swap_pressure_cycles": g.swap_pressure_cycles,
                        "stability_bonus": g.stability_bonus,
                        "horizon_adjustments": g.horizon_adjustments,
                        "failure_streak": g.failure_streak,
                        "priority_decay_multiplier": g.priority_decay_multiplier,
                    }
                    for g in goals
                ],
            )
        except Exception as e:
            print(f"[GoalSelector] batch persist failed: {e}")

    def load_goals(self) -> list[Goal]:
        """Load all goals from Neon for this org."""
        try:
            with get_conn(self.org_id) as cur:
                cur.execute(
                    """
                    SELECT id, org_id, title, description, state,
                           priority, expected_impact, estimated_cost,
                           confidence, dependency_unlock, venture_id,
                           blocked_by, score, rank, score_explanation,
                           performance, created_at, updated_at
                    FROM goals
                    WHERE org_id = %s
                    ORDER BY rank ASC, score DESC
                    """,
                    (self.org_id,),
                )
                rows = cur.fetchall()
        except Exception as e:
            print(f"[GoalSelector] load failed: {e}")
            return []

        goals: list[Goal] = []
        for row in rows:
            blocked_by = row.get("blocked_by") or "[]"
            if isinstance(blocked_by, str):
                blocked_by = json.loads(blocked_by)

            explanation = row.get("score_explanation") or "[]"
            if isinstance(explanation, str):
                explanation = json.loads(explanation)

            perf_raw = row.get("performance") or "{}"
            if isinstance(perf_raw, str):
                perf_raw = json.loads(perf_raw)
            perf = PerformanceProfile.from_dict(perf_raw) if perf_raw else PerformanceProfile()

            horizons_raw = row.get("horizons") or "{}"
            if isinstance(horizons_raw, str):
                horizons_raw = json.loads(horizons_raw)
            horizons = MultiHorizonProfile.from_dict(horizons_raw)

            h_adj_raw = row.get("horizon_adjustments") or "{}"
            if isinstance(h_adj_raw, str):
                h_adj_raw = json.loads(h_adj_raw)
            h_adj = h_adj_raw if h_adj_raw else {"short": 0.0, "medium": 0.0, "long": 0.0}

            created = row["created_at"]
            if isinstance(created, str):
                created = datetime.fromisoformat(created)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            updated = row["updated_at"]
            if isinstance(updated, str):
                updated = datetime.fromisoformat(updated)
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)

            goals.append(
                Goal(
                    id=str(row["id"]),
                    org_id=str(row["org_id"]),
                    title=row["title"],
                    description=row.get("description") or "",
                    state=GoalState(row["state"]),
                    priority=row.get("priority") or 5,
                    expected_impact=float(row.get("expected_impact") or 0.5),
                    estimated_cost=float(row.get("estimated_cost") or 0.5),
                    confidence=float(row.get("confidence") or 0.5),
                    dependency_unlock=row.get("dependency_unlock") or 0,
                    venture_id=row.get("venture_id"),
                    blocked_by=blocked_by,
                    score=float(row.get("score") or 0.0),
                    base_score=float(row.get("base_score") or 0.0),
                    performance_adjustment=float(row.get("performance_adjustment") or 0.0),
                    opportunity_cost_adjustment=float(
                        row.get("opportunity_cost_adjustment") or 0.0
                    ),
                    stability_bonus=float(row.get("stability_bonus") or 0.0),
                    horizon_adjustments=h_adj,
                    rank=row.get("rank") or 0,
                    score_explanation=explanation,
                    performance=perf,
                    horizons=horizons,
                    swap_pressure_cycles=int(row.get("swap_pressure_cycles") or 0),
                    failure_streak=int(row.get("failure_streak") or 0),
                    priority_decay_multiplier=float(row.get("priority_decay_multiplier") or 1.0),
                    created_at=created,
                    updated_at=updated,
                )
            )
        return goals

    # ─── EventBus integration ────────────────────────────────────────────────

    def _emit_event(
        self,
        event_type: str,
        goal: Goal,
        swap_target: Goal | None = None,
    ) -> None:
        """Publish goal state change to EventBus."""
        try:
            from substrate.control_plane.events.event_bus import get_bus

            bus = get_bus()
            payload: dict = {
                "goal_id": goal.id,
                "title": goal.title,
                "state": goal.state.value,
                "score": goal.score,
                "rank": goal.rank,
                "venture_id": goal.venture_id,
            }
            if swap_target is not None:
                payload["swap_target_id"] = swap_target.id
                payload["swap_target_title"] = swap_target.title
                payload["swap_target_score"] = swap_target.score
            bus.publish(event_type, payload)
        except Exception as e:
            print(f"[GoalSelector] event emit failed: {e}")

    def _log_cycle(self, active: list[Goal], all_scored: list[Goal]) -> None:
        """Log selection cycle result to events table."""
        try:
            from substrate.state.memory.memory import AgentMemory
            AgentMemory().log_event(
                org_id=self.org_id,
                event_type="goal_selection_cycle",
                payload={
                    "active_count": len(active),
                    "total_scored": len(all_scored),
                    "focus_budget": self.focus_budget,
                    "active_goals": [
                        {
                            "id": g.id,
                            "title": g.title,
                            "score": g.score,
                            "opportunity_cost": g.opportunity_cost_adjustment,
                        }
                        for g in active
                    ],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as e:
            print(f"[GoalSelector] cycle log failed: {e}")


# ─── OutcomeTracker ──────────────────────────────────────────────────────────


class OutcomeTracker:
    """
    Records execution outcomes and recomputes performance profiles.

    Hooks into EventBus (task_completed, task_failed) to update goal
    performance in real time. The GoalSelector reads these profiles
    during the next selection cycle.
    """

    def __init__(self, org_id: str = ORG_ID):
        self.org_id = org_id

    def record_outcome(
        self,
        goal_id: str,
        outcome_type: str,
        execution_time: float = 0.0,
        impact_delta: float = 0.0,
        task_type: str = "",
        metadata: dict | None = None,
    ) -> None:
        """
        Record a single outcome and recompute the goal's performance profile.

        outcome_type: 'success' | 'failure' | 'partial'
        """
        now = datetime.now(timezone.utc)

        # 1. Persist outcome to goal_outcomes table
        try:
            from substrate.state.stores.goal_store import GoalStore
            GoalStore().insert_outcome(
                org_id=self.org_id,
                goal_id=goal_id,
                outcome_type=outcome_type,
                task_type=task_type,
                execution_time=execution_time,
                impact_delta=impact_delta,
                metadata=metadata or {},
            )
        except Exception as e:
            print(f"[OutcomeTracker] persist outcome failed: {e}")
            return

        # 2. Recompute profiles (medium-term = legacy, plus multi-horizon)
        profile = self._compute_profile(goal_id)
        horizons = self._compute_horizons(goal_id)

        # 3. Update failure streak + priority decay (Phase 9H)
        failure_streak, decay_multiplier = self._update_failure_decay(goal_id, outcome_type)

        # 4. Update goal's performance + horizons + decay columns
        try:
            from substrate.state.stores.goal_store import GoalStore
            GoalStore().update_performance(
                org_id=self.org_id,
                goal_id=goal_id,
                performance=profile.to_dict(),
                horizons=horizons.to_dict(),
                failure_streak=failure_streak,
                priority_decay_multiplier=decay_multiplier,
                updated_at=now.isoformat(),
            )
        except Exception as e:
            print(f"[OutcomeTracker] update performance failed: {e}")

        print(
            f"[OutcomeTracker] {goal_id} {outcome_type} → "
            f"sr={profile.success_rate:.2f} eff={profile.efficiency:.2f} "
            f"rel={profile.reliability:.2f} imp={profile.impact_score:.2f}"
        )

    def _update_failure_decay(
        self,
        goal_id: str,
        outcome_type: str,
    ) -> tuple[int, float]:
        """Update failure streak and priority decay multiplier (Phase 9H).

        Returns (failure_streak, priority_decay_multiplier) for persistence.
        Emits goal_priority_decayed event when decay is applied.
        """
        try:
            with get_conn(self.org_id) as cur:
                cur.execute(
                    """
                    SELECT failure_streak, priority_decay_multiplier
                    FROM goals WHERE id = %s AND org_id = %s
                    """,
                    (goal_id, self.org_id),
                )
                row = cur.fetchone()
        except Exception as e:
            print(f"[OutcomeTracker] load decay state failed: {e}")
            return (0, 1.0)

        if row is None:
            return (0, 1.0)

        streak = int(row.get("failure_streak") or 0)
        multiplier = float(row.get("priority_decay_multiplier") or 1.0)

        if outcome_type == "success":
            streak = 0
            multiplier = 1.0
        else:
            streak += 1
            if streak >= FAILURE_THRESHOLD:
                old_multiplier = multiplier
                multiplier = max(
                    MIN_PRIORITY_MULTIPLIER,
                    multiplier * DECAY_FACTOR,
                )
                if multiplier < old_multiplier:
                    self._emit_decay_event(goal_id, streak, multiplier)

        return (streak, multiplier)

    def _emit_decay_event(
        self,
        goal_id: str,
        failure_streak: int,
        new_multiplier: float,
    ) -> None:
        """Emit goal_priority_decayed event via EventBus."""
        try:
            from substrate.control_plane.events.event_bus import get_bus

            bus = get_bus()
            bus.publish(
                "goal_priority_decayed",
                {
                    "goal_id": goal_id,
                    "failure_streak": failure_streak,
                    "new_multiplier": round(new_multiplier, 4),
                },
            )
        except Exception as e:
            print(f"[OutcomeTracker] decay event emit failed: {e}")

    def _load_outcome_rows(self, goal_id: str) -> list[dict]:
        """Load raw outcome rows from DB."""
        try:
            with get_conn(self.org_id) as cur:
                cur.execute(
                    """
                    SELECT outcome_type, execution_time, impact_delta, created_at
                    FROM goal_outcomes
                    WHERE goal_id = %s AND org_id = %s
                    ORDER BY created_at ASC
                    """,
                    (goal_id, self.org_id),
                )
                return cur.fetchall()
        except Exception as e:
            print(f"[OutcomeTracker] load outcomes failed: {e}")
            return []

    @staticmethod
    def _compute_profile_from_rows(
        rows: list[dict],
        half_life: float,
    ) -> PerformanceProfile:
        """
        Compute performance profile from outcome rows with a given decay half-life.

        Each outcome is weighted by exponential decay based on age.
        """
        if not rows:
            return PerformanceProfile()

        now = datetime.now(timezone.utc)
        total_weight = 0.0
        weighted_success = 0.0
        weighted_efficiency = 0.0
        weighted_impact = 0.0
        total_outcomes = len(rows)
        total_successes = 0
        total_failures = 0
        total_exec_time = 0.0
        retry_count = 0
        last_outcome_at = None

        for row in rows:
            created = row["created_at"]
            if isinstance(created, str):
                created = datetime.fromisoformat(created)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            age_secs = (now - created).total_seconds()
            weight = math.exp(-0.693 * age_secs / half_life)
            total_weight += weight

            otype = row["outcome_type"]
            exec_time = float(row.get("execution_time") or 0.0)
            impact = float(row.get("impact_delta") or 0.0)

            if otype == "success":
                weighted_success += weight
                total_successes += 1
            elif otype == "failure":
                total_failures += 1
                retry_count += 1
            elif otype == "partial":
                weighted_success += weight * 0.5
                total_successes += 1

            if exec_time > 0:
                eff = min(1.0, 60.0 / exec_time)
            else:
                eff = 0.5
            weighted_efficiency += weight * eff

            weighted_impact += weight * min(max(impact, 0.0), 1.0)
            total_exec_time += exec_time
            last_outcome_at = created

        if total_weight == 0:
            return PerformanceProfile()

        success_rate = weighted_success / total_weight
        efficiency = weighted_efficiency / total_weight
        reliability = 1.0 - (retry_count / max(total_outcomes, 1))
        impact_score = weighted_impact / total_weight
        avg_exec = total_exec_time / total_outcomes if total_outcomes > 0 else 0.0

        return PerformanceProfile(
            success_rate=round(min(success_rate, 1.0), 4),
            efficiency=round(min(efficiency, 1.0), 4),
            reliability=round(max(reliability, 0.0), 4),
            impact_score=round(min(impact_score, 1.0), 4),
            total_outcomes=total_outcomes,
            total_successes=total_successes,
            total_failures=total_failures,
            avg_execution_time=round(avg_exec, 2),
            last_outcome_at=last_outcome_at,
        )

    def _compute_profile(
        self,
        goal_id: str,
        half_life: float = MEDIUM_TERM_HALF_LIFE,
    ) -> PerformanceProfile:
        """Recompute a single-horizon performance profile."""
        rows = self._load_outcome_rows(goal_id)
        return self._compute_profile_from_rows(rows, half_life)

    def _compute_horizons(self, goal_id: str) -> MultiHorizonProfile:
        """Compute performance across short/medium/long horizons."""
        rows = self._load_outcome_rows(goal_id)
        if not rows:
            return MultiHorizonProfile()
        return MultiHorizonProfile(
            short_term=self._compute_profile_from_rows(rows, SHORT_TERM_HALF_LIFE),
            medium_term=self._compute_profile_from_rows(rows, MEDIUM_TERM_HALF_LIFE),
            long_term=self._compute_profile_from_rows(rows, LONG_TERM_HALF_LIFE),
        )

    def get_profile(self, goal_id: str) -> PerformanceProfile:
        """Get current medium-term performance profile for a goal."""
        return self._compute_profile(goal_id)

    def get_horizons(self, goal_id: str) -> MultiHorizonProfile:
        """Get multi-horizon performance profile for a goal."""
        return self._compute_horizons(goal_id)

    def get_outcome_history(self, goal_id: str, limit: int = 50) -> list[dict]:
        """Get raw outcome history for a goal."""
        try:
            with get_conn(self.org_id) as cur:
                cur.execute(
                    """
                    SELECT outcome_type, task_type, execution_time,
                           impact_delta, metadata, created_at
                    FROM goal_outcomes
                    WHERE goal_id = %s AND org_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (goal_id, self.org_id, limit),
                )
                rows = cur.fetchall()
        except Exception as e:
            print(f"[OutcomeTracker] load history failed: {e}")
            return []

        return [
            {
                "outcome_type": r["outcome_type"],
                "task_type": r["task_type"],
                "execution_time": r["execution_time"],
                "impact_delta": r["impact_delta"],
                "metadata": r.get("metadata") or {},
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ]


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Goal Selector CLI")
    sub = parser.add_subparsers(dest="command")

    # goals — list all
    sub.add_parser("list", help="List all goals")

    # goal-add
    add_p = sub.add_parser("add", help="Add a goal")
    add_p.add_argument("title")
    add_p.add_argument("--description", default="")
    add_p.add_argument("--priority", type=int, default=5)
    add_p.add_argument("--impact", type=float, default=0.5)
    add_p.add_argument("--cost", type=float, default=0.5)
    add_p.add_argument("--confidence", type=float, default=0.5)
    add_p.add_argument("--venture", default=None)
    add_p.add_argument("--blocked-by", nargs="*", default=[])

    # goal-activate
    act_p = sub.add_parser("activate", help="Activate a goal")
    act_p.add_argument("goal_id")

    # goal-defer
    def_p = sub.add_parser("defer", help="Defer a goal")
    def_p.add_argument("goal_id")

    # goal-complete
    comp_p = sub.add_parser("complete", help="Complete a goal")
    comp_p.add_argument("goal_id")

    # goal-drop
    drop_p = sub.add_parser("drop", help="Drop a goal")
    drop_p.add_argument("goal_id")

    # goal-cycle — run selection
    sub.add_parser("cycle", help="Run selection cycle")

    # goal-explain
    exp_p = sub.add_parser("explain", help="Explain goal scoring")
    exp_p.add_argument("goal_id")

    args = parser.parse_args()
    selector = GoalSelector()

    if args.command == "list":
        goals = selector.list_goals()
        if not goals:
            print("No goals found.")
        for g in goals:
            marker = "●" if g.state == GoalState.ACTIVE else "○"
            print(
                f"  {marker} [{g.id}] {g.title}  "
                f"state={g.state.value}  score={g.score:.3f}  rank={g.rank}"
            )

    elif args.command == "add":
        goal = selector.add_goal(
            title=args.title,
            description=args.description,
            priority=args.priority,
            expected_impact=args.impact,
            estimated_cost=args.cost,
            confidence=args.confidence,
            venture_id=args.venture,
            blocked_by=args.blocked_by,
        )
        print(f"Created goal [{goal.id}]: {goal.title}  state={goal.state.value}")

    elif args.command == "activate":
        goal = selector.activate(args.goal_id)
        print(f"Activated [{goal.id}]: {goal.title}")

    elif args.command == "defer":
        goal = selector.defer(args.goal_id)
        print(f"Deferred [{goal.id}]: {goal.title}")

    elif args.command == "complete":
        goal = selector.complete(args.goal_id)
        print(f"Completed [{goal.id}]: {goal.title}")

    elif args.command == "drop":
        goal = selector.drop(args.goal_id)
        print(f"Dropped [{goal.id}]: {goal.title}")

    elif args.command == "cycle":
        active = selector.run_selection_cycle()
        print(f"Selection cycle complete. {len(active)} active goals:")
        for g in active:
            print(f"  ● [{g.id}] {g.title}  score={g.score:.3f}")

    elif args.command == "explain":
        goal = selector.get_goal(args.goal_id)
        selector.score_goal(goal, selector.load_goals())
        info = selector.explain(goal)
        print(json.dumps(info, indent=2))

    else:
        parser.print_help()
