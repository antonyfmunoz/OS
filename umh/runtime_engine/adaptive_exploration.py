"""
AdaptiveExploration — dynamic control of exploration vs exploitation.

Previous behavior: exploration is binary (on/off) via influence_orchestrator.
The system either rotates stale strategies or doesn't. This creates two
failure modes:
    - Over-exploration: unstable systems keep sampling new strategies when
      they should converge on what works.
    - Premature convergence: stable systems lock into a strategy too early
      when uncertainty is still high.

This module computes a continuous exploration_rate in [MIN_EXPLORATION,
MAX_EXPLORATION] from real-time performance signals, then feeds that rate
into multi_strategy (how many diverse candidates to generate) and
execution_budget (how to distribute candidate slots).

Key design:
    - ExplorationState is frozen (immutable snapshot per turn).
    - Computation is deterministic: same signals → same rate.
    - Four signal dimensions: goal_delta, convergence_status,
      blended_entropy, candidate_score_variance.
    - No LLM calls. No randomness. Pure arithmetic.

Usage::

    from umh.runtime_engine.adaptive_exploration import (
        ExplorationController,
        ExplorationState,
    )

    controller = ExplorationController()
    state = controller.compute(
        goal_deltas=[-0.02, 0.05, 0.03],
        convergence_status="stable",
        blended_entropy=0.4,
        candidate_scores=[0.72, 0.68, 0.75],
    )
    # state.exploration_rate → 0.25
    # state.reason → "stable_positive_progress"
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

_log = logging.getLogger(__name__)

MIN_EXPLORATION = 0.05
MAX_EXPLORATION = 0.80
DEFAULT_EXPLORATION = 0.40

PERFORMANCE_EMA_ALPHA = 0.3
DELTA_WINDOW = 5

INSTABILITY_BOOST = 0.25
RECOVERY_BOOST = 0.10
CONVERGENCE_PENALTY = -0.20
POSITIVE_DELTA_PENALTY = -0.10
NEGATIVE_DELTA_BOOST = 0.15
OSCILLATION_MODERATE = 0.05
HIGH_ENTROPY_BOOST = 0.15
HIGH_VARIANCE_BOOST = 0.10
COUNTERFACTUAL_UNCERTAINTY_BOOST = 0.12
HORIZON_FUTURE_BOOST = 0.08


@dataclass(frozen=True)
class ExplorationState:
    """Immutable snapshot of the exploration controller's output."""

    exploration_rate: float
    uncertainty_score: float
    recent_performance: float
    convergence_state: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "exploration_rate": round(self.exploration_rate, 4),
            "uncertainty_score": round(self.uncertainty_score, 4),
            "recent_performance": round(self.recent_performance, 4),
            "convergence_state": self.convergence_state,
            "reason": self.reason,
        }


NO_EXPLORATION_STATE = ExplorationState(
    exploration_rate=DEFAULT_EXPLORATION,
    uncertainty_score=0.0,
    recent_performance=0.0,
    convergence_state="unknown",
    reason="no_signals",
)


class ExplorationController:
    """Stateful controller that tracks performance EMA across turns.

    Call ``compute()`` each turn with current signals.
    The controller maintains a running performance EMA that smooths
    out single-turn noise.
    """

    def __init__(self) -> None:
        self._performance_ema: float = 0.5
        self._turns_computed: int = 0

    def compute(
        self,
        goal_deltas: list[float] | None = None,
        convergence_status: str | None = None,
        blended_entropy: float | None = None,
        candidate_scores: list[float] | None = None,
        counterfactual_uncertainty: float | None = None,
        horizon_value: float | None = None,
    ) -> ExplorationState:
        """Compute exploration state from current signals."""
        self._turns_computed += 1

        # ── 1. Recent performance (EMA of goal deltas) ──────────────
        recent_perf = self._performance_ema
        if goal_deltas:
            window = goal_deltas[-DELTA_WINDOW:]
            avg_delta = sum(window) / len(window)
            if self._turns_computed <= 1:
                self._performance_ema = avg_delta
            else:
                self._performance_ema = (
                    PERFORMANCE_EMA_ALPHA * avg_delta
                    + (1 - PERFORMANCE_EMA_ALPHA) * self._performance_ema
                )
            recent_perf = self._performance_ema

        # ── 2. Uncertainty from candidate score variance ─────────────
        variance = 0.0
        if candidate_scores and len(candidate_scores) >= 2:
            mean_score = sum(candidate_scores) / len(candidate_scores)
            variance = sum((s - mean_score) ** 2 for s in candidate_scores) / len(
                candidate_scores
            )

        uncertainty = min(math.sqrt(variance) * 2.0, 1.0)

        # ── 3. Entropy contribution ─────────────────────────────────
        entropy = blended_entropy if blended_entropy is not None else 0.0

        # ── 4. Convergence state ────────────────────────────────────
        conv_state = convergence_status or "unknown"

        # ── 5. Compute rate adjustments ─────────────────────────────
        rate = DEFAULT_EXPLORATION
        reasons: list[str] = []

        # Convergence-based
        if conv_state == "unstable":
            rate += INSTABILITY_BOOST
            reasons.append("unstable")
        elif conv_state == "recovering":
            rate += RECOVERY_BOOST
            reasons.append("recovering")
        elif conv_state == "stable":
            rate += CONVERGENCE_PENALTY
            reasons.append("stable")

        # Delta-based
        if goal_deltas:
            window = goal_deltas[-DELTA_WINDOW:]
            avg = sum(window) / len(window)
            if avg > 0.03:
                rate += POSITIVE_DELTA_PENALTY
                reasons.append("positive_progress")
            elif avg < -0.03:
                rate += NEGATIVE_DELTA_BOOST
                reasons.append("negative_progress")

            # Oscillation detection: sign changes in recent deltas
            if len(window) >= 3:
                sign_changes = sum(
                    1
                    for i in range(1, len(window))
                    if (window[i] > 0) != (window[i - 1] > 0) and window[i - 1] != 0
                )
                if sign_changes >= len(window) // 2:
                    rate += OSCILLATION_MODERATE
                    reasons.append("oscillating")

        # Entropy-based
        if entropy > 0.5:
            rate += HIGH_ENTROPY_BOOST
            reasons.append("high_entropy")

        # Variance-based
        if uncertainty > 0.3:
            rate += HIGH_VARIANCE_BOOST
            reasons.append("high_variance")

        # Counterfactual uncertainty: high projection uncertainty → explore more
        if counterfactual_uncertainty is not None and counterfactual_uncertainty > 0.3:
            rate += COUNTERFACTUAL_UNCERTAINTY_BOOST
            reasons.append("cf_uncertain")

        # Horizon: high future payoff but low immediate → explore more
        if horizon_value is not None and horizon_value > 0.3:
            rate += HORIZON_FUTURE_BOOST
            reasons.append("horizon_future")

        # ── 6. Clamp ────────────────────────────────────────────────
        rate = max(MIN_EXPLORATION, min(MAX_EXPLORATION, rate))

        reason = "_".join(reasons) if reasons else "default"

        return ExplorationState(
            exploration_rate=rate,
            uncertainty_score=uncertainty,
            recent_performance=recent_perf,
            convergence_state=conv_state,
            reason=reason,
        )

    @property
    def turns_computed(self) -> int:
        return self._turns_computed

    @property
    def performance_ema(self) -> float:
        return self._performance_ema


def exploration_rate_to_num_candidates(
    rate: float,
    base_candidates: int = 2,
    max_candidates: int = 5,
) -> int:
    """Convert exploration rate to a concrete number of candidates.

    Higher exploration → more candidates for diversity.
    Lower exploration → fewer candidates, focused on proven strategies.

    The mapping is linear with clamping:
        candidates = base + round((max - base) * rate)
    """
    extra = round((max_candidates - base_candidates) * rate)
    return min(max(base_candidates, base_candidates + extra), max_candidates)


def exploration_rate_to_budget_modifier(rate: float) -> float:
    """Convert exploration rate to a budget distribution modifier.

    Returns a float in [0.5, 1.5]:
        - rate=0.0 → 0.5 (concentrated allocation to primary goal)
        - rate=0.5 → 1.0 (neutral)
        - rate=1.0 → 1.5 (spread allocation across goals)

    Budget derivation multiplies secondary goal weights by this modifier.
    """
    return 0.5 + rate
