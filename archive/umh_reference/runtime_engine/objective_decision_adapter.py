"""
ObjectiveDecisionAdapter — objective-aware decision scoring adjustments.

Uses objective_value history and objective_trend from previous turns to
influence decision scoring across three subsystems:

    strategy_shift  — additive bias to strategy scores
    goal_scale      — multiplicative scaling for goal evaluation [0.9, 1.1]
    plan_bias       — additive bias to plan step attribution

Behavioral mapping::

    IMPROVING  → reinforce: boost winning strategy, scale up goals,
                 increase plan attribution
    DEGRADING  → explore: diversify strategy selection, scale down goals,
                 reduce plan attribution
    FLAT       → diversify: small positive strategy shift to break
                 out of local optima, neutral goal/plan

Safety guarantees::

    - Previous-turn data only (one-turn delay)
    - EMA smoothing inherited from objective_optimizer
    - All outputs clamped to tight ranges
    - Additive or bounded multiplicative only — never overrides
    - NO_SIGNAL default when insufficient data
    - MIN_HISTORY gate: 3+ turns required

No LLM calls.  No randomness.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass

MIN_HISTORY = 3
EMA_ALPHA = 0.15
DEAD_ZONE = 0.005

MAX_STRATEGY_SHIFT = 0.04
MIN_GOAL_SCALE = 0.90
MAX_GOAL_SCALE = 1.10
MAX_PLAN_BIAS = 0.03


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


@dataclass(frozen=True)
class ObjectiveDecisionSignal:
    """Bounded adjustments for decision-level scoring."""

    trend: str
    ema_delta: float
    strategy_shift: float
    goal_scale: float
    plan_bias: float

    def to_dict(self) -> dict:
        return {
            "trend": self.trend,
            "ema_delta": round(self.ema_delta, 6),
            "strategy_shift": round(self.strategy_shift, 4),
            "goal_scale": round(self.goal_scale, 4),
            "plan_bias": round(self.plan_bias, 4),
        }

    @property
    def is_active(self) -> bool:
        return (
            self.strategy_shift != 0.0
            or self.goal_scale != 1.0
            or self.plan_bias != 0.0
        )


NO_SIGNAL = ObjectiveDecisionSignal(
    trend="flat",
    ema_delta=0.0,
    strategy_shift=0.0,
    goal_scale=1.0,
    plan_bias=0.0,
)


def compute_decision_signal(
    objective_history: list[float],
    objective_trend: str | None = None,
) -> ObjectiveDecisionSignal:
    """Compute decision-level adjustments from objective trajectory.

    objective_history: list of objective_value floats from previous turns,
    ordered oldest-first.  Only previous-turn data.

    objective_trend: trend string from objective_optimizer ("improving",
    "degrading", "flat").  When None, trend is recomputed from history.

    Returns NO_SIGNAL when history has fewer than MIN_HISTORY entries.

    Deterministic: same inputs → same signal.
    """
    if len(objective_history) < MIN_HISTORY:
        return NO_SIGNAL

    ema_delta = _compute_ema_delta(objective_history)
    trend = objective_trend or _detect_trend(ema_delta)

    strategy_shift = _compute_strategy_shift(trend, ema_delta)
    goal_scale = _compute_goal_scale(trend, ema_delta)
    plan_bias = _compute_plan_bias(trend, ema_delta)

    return ObjectiveDecisionSignal(
        trend=trend,
        ema_delta=ema_delta,
        strategy_shift=_clamp(strategy_shift, -MAX_STRATEGY_SHIFT, MAX_STRATEGY_SHIFT),
        goal_scale=_clamp(goal_scale, MIN_GOAL_SCALE, MAX_GOAL_SCALE),
        plan_bias=_clamp(plan_bias, -MAX_PLAN_BIAS, MAX_PLAN_BIAS),
    )


def _compute_ema_delta(history: list[float]) -> float:
    """EMA of turn-over-turn deltas, identical to objective_optimizer."""
    ema = 0.0
    for i in range(1, len(history)):
        delta = history[i] - history[i - 1]
        ema = EMA_ALPHA * delta + (1.0 - EMA_ALPHA) * ema
    return ema


def _detect_trend(ema_delta: float) -> str:
    """Classify EMA delta into a trend string."""
    if ema_delta > DEAD_ZONE:
        return "improving"
    elif ema_delta < -DEAD_ZONE:
        return "degrading"
    return "flat"


def _compute_strategy_shift(trend: str, ema_delta: float) -> float:
    """Strategy score adjustment.

    Improving → positive shift (reinforce winning strategy).
    Degrading → negative shift (penalize current strategy to explore others).
    Flat → small positive shift (gentle nudge to break stagnation).
    """
    if trend == "improving":
        return _clamp(abs(ema_delta) * 3.0, 0.0, MAX_STRATEGY_SHIFT)
    elif trend == "degrading":
        return _clamp(-abs(ema_delta) * 3.0, -MAX_STRATEGY_SHIFT, 0.0)
    return _clamp(abs(ema_delta) * 0.5, 0.0, MAX_STRATEGY_SHIFT * 0.25)


def _compute_goal_scale(trend: str, ema_delta: float) -> float:
    """Goal evaluation multiplier.

    Improving → scale up slightly (goals are being achieved, reward more).
    Degrading → scale down slightly (reduce goal pressure to allow recovery).
    Flat → neutral (1.0).
    """
    if trend == "improving":
        return _clamp(1.0 + abs(ema_delta) * 2.0, 1.0, MAX_GOAL_SCALE)
    elif trend == "degrading":
        return _clamp(1.0 - abs(ema_delta) * 2.0, MIN_GOAL_SCALE, 1.0)
    return 1.0


def _compute_plan_bias(trend: str, ema_delta: float) -> float:
    """Plan step attribution adjustment.

    Improving → positive bias (current plan is working, attribute more credit).
    Degrading → negative bias (current plan may be wrong, reduce attribution).
    Flat → no adjustment.
    """
    if trend == "improving":
        return _clamp(abs(ema_delta) * 2.0, 0.0, MAX_PLAN_BIAS)
    elif trend == "degrading":
        return _clamp(-abs(ema_delta) * 2.0, -MAX_PLAN_BIAS, 0.0)
    return 0.0


def apply_strategy_shift(
    base_scores: dict[str, float],
    shift: float,
    selected_strategy: str,
) -> dict[str, float]:
    """Apply strategy_shift to strategy scores.

    Adds shift to the currently selected strategy's score.
    Other strategies receive inverse spread: -shift / (n-1).
    All scores remain non-negative via floor at 0.0.
    """
    if not base_scores or shift == 0.0 or not selected_strategy:
        return dict(base_scores) if base_scores else {}

    result: dict[str, float] = {}
    n = len(base_scores)
    inverse = -shift / max(n - 1, 1) if n > 1 else 0.0

    for name, score in base_scores.items():
        if name == selected_strategy:
            result[name] = max(0.0, score + shift)
        else:
            result[name] = max(0.0, score + inverse)

    return result


def apply_goal_scale(
    goal_score: float,
    scale: float,
) -> float:
    """Apply goal_scale multiplicatively, clamped to [0, 1]."""
    return _clamp(goal_score * scale, 0.0, 1.0)


def apply_plan_bias(
    plan_attributed_score: float,
    bias: float,
) -> float:
    """Apply plan_bias additively, clamped to [0, 1]."""
    return _clamp(plan_attributed_score + bias, 0.0, 1.0)
