"""
CausalAttribution — distributes outcome credit across contributing factors.

Previous behavior: outcomes applied fully to the winning strategy, assuming
the winner is the sole cause of success/failure. This creates misattribution
that distorts learning — a mediocre strategy riding a strong goal gets
unearned credit, while a strong directive paired with a weak strategy gets
none.

This module computes per-factor attribution weights from the DecisionTrace's
own signal strengths, then distributes outcome credit proportionally.

Key design:
    - AttributionWeights is frozen (immutable snapshot per outcome).
    - Weights always sum to 1.0 (enforced by normalization).
    - Computation is deterministic: same trace → same attribution.
    - Fallback to equal split when signals are absent or unclear.
    - No LLM calls. No randomness. Pure arithmetic.

Usage::

    from umh.reasoning.causal_attribution import compute_attribution, AttributionWeights

    weights = compute_attribution(trace)
    # weights.strategy_weight = 0.45
    # weights.directive_weight = 0.30
    # weights.goal_weight = 0.25
    # weights.context_weight = 0.00
    # sum = 1.0

    # Apply weighted outcome:
    strategy_credit = outcome.success * weights.strategy_weight
    directive_credit = outcome.success * weights.directive_weight
    goal_credit = outcome.success * weights.goal_weight
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

_log = logging.getLogger(__name__)

EQUAL_WEIGHT = 1.0 / 3.0


@dataclass(frozen=True)
class AttributionWeights:
    """Immutable per-outcome credit distribution across contributing factors."""

    strategy_weight: float
    directive_weight: float
    goal_weight: float
    context_weight: float = 0.0
    reason: str = "equal_split"

    def sum(self) -> float:
        return (
            self.strategy_weight
            + self.directive_weight
            + self.goal_weight
            + self.context_weight
        )

    def to_dict(self) -> dict:
        d = {
            "strategy_weight": round(self.strategy_weight, 4),
            "directive_weight": round(self.directive_weight, 4),
            "goal_weight": round(self.goal_weight, 4),
            "reason": self.reason,
        }
        if self.context_weight > 0.0:
            d["context_weight"] = round(self.context_weight, 4)
        return d


EQUAL_ATTRIBUTION = AttributionWeights(
    strategy_weight=EQUAL_WEIGHT,
    directive_weight=EQUAL_WEIGHT,
    goal_weight=EQUAL_WEIGHT,
    context_weight=0.0,
    reason="equal_split",
)


def compute_attribution(trace: object) -> AttributionWeights:
    """Compute attribution weights from a DecisionTrace.

    Signal extraction:
        - strategy_signal: the selected strategy's score from strategy_scores.
          Higher score → more credit to strategy for this turn's outcome.
        - directive_signal: from strategy_selection.directive_scores for the
          winning directive. Falls back to strategy_signal * 0.8 heuristic.
        - goal_signal: from blended_goals weight for the active goal.
          Falls back to goal_score if present, else 0.

    When all signals are zero or absent, returns EQUAL_ATTRIBUTION.
    When only some signals are present, absent ones get a floor value
    so they still receive some credit (prevents zero-weight starvation).

    Normalization ensures sum = 1.0 always.
    """
    strategy_signal = _extract_strategy_signal(trace)
    directive_signal = _extract_directive_signal(trace, strategy_signal)
    goal_signal = _extract_goal_signal(trace)

    total = strategy_signal + directive_signal + goal_signal

    if total < 1e-9:
        return EQUAL_ATTRIBUTION

    strategy_weight = strategy_signal / total
    directive_weight = directive_signal / total
    goal_weight = goal_signal / total

    reason = _build_reason(strategy_signal, directive_signal, goal_signal)

    return AttributionWeights(
        strategy_weight=strategy_weight,
        directive_weight=directive_weight,
        goal_weight=goal_weight,
        context_weight=0.0,
        reason=reason,
    )


SIGNAL_FLOOR = 0.1


def _extract_strategy_signal(trace: object) -> float:
    """Extract the winning strategy's contribution signal from the trace."""
    selected = getattr(trace, "selected_strategy", "")
    if not selected:
        return SIGNAL_FLOOR

    scores = getattr(trace, "strategy_scores", {})
    if not scores:
        return SIGNAL_FLOOR

    score = scores.get(selected, 0.0)
    return max(score, SIGNAL_FLOOR)


def _extract_directive_signal(trace: object, strategy_signal: float) -> float:
    """Extract the directive's contribution signal from the trace."""
    strat_sel = getattr(trace, "strategy_selection", None)
    if strat_sel is not None and isinstance(strat_sel, dict):
        directive_scores = strat_sel.get("directive_scores", {})
        selected = getattr(trace, "selected_strategy", "")
        if selected and selected in directive_scores:
            score = directive_scores[selected]
            return max(score, SIGNAL_FLOOR)

    if strategy_signal > SIGNAL_FLOOR:
        return max(strategy_signal * 0.8, SIGNAL_FLOOR)

    return SIGNAL_FLOOR


def _extract_goal_signal(trace: object) -> float:
    """Extract the goal's contribution signal from the trace."""
    blended = getattr(trace, "blended_goals", None)
    active_id = getattr(trace, "active_goal_id", None)

    if blended and active_id:
        for gid, weight in blended:
            if gid == active_id:
                return max(weight, SIGNAL_FLOOR)

    goal_score = getattr(trace, "goal_score", None)
    if goal_score is not None:
        return max(goal_score, SIGNAL_FLOOR)

    return SIGNAL_FLOOR


def _build_reason(
    strategy_signal: float,
    directive_signal: float,
    goal_signal: float,
) -> str:
    """Build a human-readable attribution reason."""
    signals = [
        ("strategy", strategy_signal),
        ("directive", directive_signal),
        ("goal", goal_signal),
    ]
    signals.sort(key=lambda x: x[1], reverse=True)
    dominant = signals[0]

    total = strategy_signal + directive_signal + goal_signal
    dominant_pct = dominant[1] / total if total > 0 else 0

    if dominant_pct > 0.5:
        return f"{dominant[0]}_dominant"
    return "balanced"
