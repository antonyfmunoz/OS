"""
ObjectiveOptimizer — safely adjust system behavior from objective trajectory.

Reads the history of objective_value from previous turns (via DecisionTrace),
computes an EMA-smoothed trend, and produces bounded additive adjustments
for downstream subsystems (policy, exploration, plan confidence).

Trend detection::

    IMPROVING  — EMA delta > DEAD_ZONE  → exploit more, explore less
    DEGRADING  — EMA delta < -DEAD_ZONE → explore more, reduce confidence
    FLAT       — |EMA delta| <= DEAD_ZONE → no adjustment

Safety guarantees::

    - Previous-turn data only (one-turn delay)
    - EMA smoothing prevents oscillation
    - All outputs clamped to tight ranges
    - Additive only — never overrides
    - NO_SIGNAL default when insufficient history
    - MIN_HISTORY gate: no signal until 3+ turns

No LLM calls.  No randomness.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Trend(Enum):
    IMPROVING = "improving"
    DEGRADING = "degrading"
    FLAT = "flat"


EMA_ALPHA = 0.15
DEAD_ZONE = 0.005
MIN_HISTORY = 3

MAX_EXPLORATION_ADJUSTMENT = 0.03
MAX_POLICY_BIAS = 0.02
MAX_CONFIDENCE_ADJUSTMENT = 0.03


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


@dataclass(frozen=True)
class OptimizationSignal:
    """Bounded additive adjustments derived from objective trajectory."""

    trend: Trend
    ema_delta: float
    exploration_adjustment: float
    policy_bias: float
    confidence_adjustment: float

    def to_dict(self) -> dict:
        return {
            "trend": self.trend.value,
            "ema_delta": round(self.ema_delta, 6),
            "exploration_adjustment": round(self.exploration_adjustment, 4),
            "policy_bias": round(self.policy_bias, 4),
            "confidence_adjustment": round(self.confidence_adjustment, 4),
        }

    @property
    def is_active(self) -> bool:
        return (
            self.exploration_adjustment != 0.0
            or self.policy_bias != 0.0
            or self.confidence_adjustment != 0.0
        )


NO_SIGNAL = OptimizationSignal(
    trend=Trend.FLAT,
    ema_delta=0.0,
    exploration_adjustment=0.0,
    policy_bias=0.0,
    confidence_adjustment=0.0,
)


def compute_optimization_signal(
    objective_history: list[float],
) -> OptimizationSignal:
    """Compute optimization adjustments from a history of objective values.

    objective_history is a list of objective_value floats from previous turns,
    ordered oldest-first.  Only previous-turn data — current turn not included.

    Returns NO_SIGNAL when history has fewer than MIN_HISTORY entries.

    EMA smoothing (alpha=0.15) prevents oscillation.  Dead zone (±0.005)
    prevents reaction to noise.  All outputs clamped.

    Deterministic: same history → same signal.
    """
    if len(objective_history) < MIN_HISTORY:
        return NO_SIGNAL

    ema_delta = _compute_ema_delta(objective_history)
    trend = _detect_trend(ema_delta)

    exploration_adjustment = _compute_exploration_adjustment(trend, ema_delta)
    policy_bias = _compute_policy_bias(trend, ema_delta)
    confidence_adjustment = _compute_confidence_adjustment(trend, ema_delta)

    return OptimizationSignal(
        trend=trend,
        ema_delta=ema_delta,
        exploration_adjustment=_clamp(
            exploration_adjustment,
            -MAX_EXPLORATION_ADJUSTMENT,
            MAX_EXPLORATION_ADJUSTMENT,
        ),
        policy_bias=_clamp(policy_bias, -MAX_POLICY_BIAS, MAX_POLICY_BIAS),
        confidence_adjustment=_clamp(
            confidence_adjustment,
            -MAX_CONFIDENCE_ADJUSTMENT,
            MAX_CONFIDENCE_ADJUSTMENT,
        ),
    )


def _compute_ema_delta(history: list[float]) -> float:
    """Compute EMA of turn-over-turn deltas.

    Each delta is (value[i] - value[i-1]).  EMA smooths these with
    alpha=0.15 so recent deltas weigh more but old deltas still contribute.
    """
    ema = 0.0
    for i in range(1, len(history)):
        delta = history[i] - history[i - 1]
        ema = EMA_ALPHA * delta + (1.0 - EMA_ALPHA) * ema
    return ema


def _detect_trend(ema_delta: float) -> Trend:
    """Classify EMA delta into a trend category."""
    if ema_delta > DEAD_ZONE:
        return Trend.IMPROVING
    elif ema_delta < -DEAD_ZONE:
        return Trend.DEGRADING
    else:
        return Trend.FLAT


def _compute_exploration_adjustment(trend: Trend, ema_delta: float) -> float:
    """Exploration adjustment based on trend.

    Improving → reduce exploration (exploit the gains).
    Degrading → increase exploration (current path isn't working).
    Flat → no change.
    """
    if trend == Trend.IMPROVING:
        return _clamp(-abs(ema_delta) * 2.0, -MAX_EXPLORATION_ADJUSTMENT, 0.0)
    elif trend == Trend.DEGRADING:
        return _clamp(abs(ema_delta) * 2.0, 0.0, MAX_EXPLORATION_ADJUSTMENT)
    return 0.0


def _compute_policy_bias(trend: Trend, ema_delta: float) -> float:
    """Policy bias based on trend.

    Improving → positive bias (toward exploitation).
    Degrading → negative bias (toward exploration).
    Flat → no change.
    """
    if trend == Trend.IMPROVING:
        return _clamp(abs(ema_delta) * 1.5, 0.0, MAX_POLICY_BIAS)
    elif trend == Trend.DEGRADING:
        return _clamp(-abs(ema_delta) * 1.5, -MAX_POLICY_BIAS, 0.0)
    return 0.0


def _compute_confidence_adjustment(trend: Trend, ema_delta: float) -> float:
    """Plan confidence adjustment based on trend.

    Improving → nudge confidence up (current plan is working).
    Degrading → nudge confidence down (plan may need revision).
    Flat → no change.
    """
    if trend == Trend.IMPROVING:
        return _clamp(abs(ema_delta) * 1.0, 0.0, MAX_CONFIDENCE_ADJUSTMENT)
    elif trend == Trend.DEGRADING:
        return _clamp(-abs(ema_delta) * 1.0, -MAX_CONFIDENCE_ADJUSTMENT, 0.0)
    return 0.0
