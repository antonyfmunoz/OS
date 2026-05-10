"""
AnalyticsAdapter — safely bridges Fabric Analytics → Policy Engine.

Reads a previous turn's fabric_analytics_summary (dict) and produces
a bounded AnalyticsSignal that the policy engine can accept as an
additive modifier.  Never writes to the fabric.  Never mutates any
subsystem.  Fully optional — disabled by default.

Safety guarantees::

    - MIN_OBSERVATIONS gate: no signal until 10+ fabric entries
    - All outputs clamped to bounded ranges
    - Default is zero signal (no effect)
    - Only reads previous-turn analytics (one-turn delay)
    - Feature flag: analytics_adapter_enabled

No LLM calls.  No randomness.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass

MIN_OBSERVATIONS = 10

MAX_STRATEGY_BIAS = 0.03
MAX_POLICY_BIAS = 0.02
MAX_DIRECTIVE_BIAS = 0.02
MAX_CONFIDENCE_ADJUSTMENT = 0.05

SUCCESS_RATE_BASELINE = 0.50
CORRELATION_SCALE = 0.10


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


@dataclass(frozen=True)
class AnalyticsSignal:
    """Bounded signal from analytics to policy engine.

    All fields are additive modifiers with tight clamps.
    Zero values mean "no effect" — the safe default.
    """

    strategy_bias: float
    policy_bias: float
    directive_bias: float
    confidence_adjustment: float

    def to_dict(self) -> dict:
        return {
            "strategy_bias": round(self.strategy_bias, 4),
            "policy_bias": round(self.policy_bias, 4),
            "directive_bias": round(self.directive_bias, 4),
            "confidence_adjustment": round(self.confidence_adjustment, 4),
        }

    @property
    def is_active(self) -> bool:
        return (
            self.strategy_bias != 0.0
            or self.policy_bias != 0.0
            or self.directive_bias != 0.0
            or self.confidence_adjustment != 0.0
        )


NO_SIGNAL = AnalyticsSignal(
    strategy_bias=0.0,
    policy_bias=0.0,
    directive_bias=0.0,
    confidence_adjustment=0.0,
)


def build_analytics_signal(
    analytics_summary: dict | None,
) -> AnalyticsSignal:
    """Convert a fabric_analytics_summary dict into a bounded signal.

    Returns NO_SIGNAL when:
    - summary is None or empty
    - total_entries < MIN_OBSERVATIONS
    - no actionable data present

    All outputs are clamped to tight ranges.  Deterministic.
    """
    if not analytics_summary:
        return NO_SIGNAL

    total = analytics_summary.get("total_entries", 0)
    if total < MIN_OBSERVATIONS:
        return NO_SIGNAL

    strategy_bias = _compute_strategy_bias(analytics_summary)
    policy_bias = _compute_policy_bias(analytics_summary)
    directive_bias = _compute_directive_bias(analytics_summary)
    confidence_adj = _compute_confidence_adjustment(analytics_summary)

    return AnalyticsSignal(
        strategy_bias=_clamp(strategy_bias, -MAX_STRATEGY_BIAS, MAX_STRATEGY_BIAS),
        policy_bias=_clamp(policy_bias, -MAX_POLICY_BIAS, MAX_POLICY_BIAS),
        directive_bias=_clamp(directive_bias, -MAX_DIRECTIVE_BIAS, MAX_DIRECTIVE_BIAS),
        confidence_adjustment=_clamp(
            confidence_adj, -MAX_CONFIDENCE_ADJUSTMENT, MAX_CONFIDENCE_ADJUSTMENT
        ),
    )


def _compute_strategy_bias(summary: dict) -> float:
    """Strategy bias from top_strategies performance spread.

    If the best strategy EMA is significantly above average, produce
    a small positive bias toward exploitation.  If strategies are
    clustered, produce slight negative bias (explore more).
    """
    top = summary.get("top_strategies")
    if not top or not isinstance(top, dict):
        return 0.0

    values = [v for v in top.values() if isinstance(v, (int, float))]
    if len(values) < 2:
        return 0.0

    best = max(values)
    avg = sum(values) / len(values)
    spread = best - avg

    return spread * CORRELATION_SCALE


def _compute_policy_bias(summary: dict) -> float:
    """Policy bias from signal correlations.

    If the top signal correlation is strongly positive, bias toward
    exploitation.  If correlations are weak/negative, bias toward
    exploration.
    """
    corrs = summary.get("top_signal_correlations")
    if not corrs or not isinstance(corrs, dict):
        return 0.0

    values = [v for v in corrs.values() if isinstance(v, (int, float))]
    if not values:
        return 0.0

    avg_corr = sum(values) / len(values)
    return avg_corr * CORRELATION_SCALE


def _compute_directive_bias(summary: dict) -> float:
    """Directive bias from directive success rates.

    If directives are generally succeeding (above baseline),
    produce a positive bias.  Below baseline → negative.
    """
    rates = summary.get("directive_success")
    if not rates or not isinstance(rates, dict):
        return 0.0

    values = [v for v in rates.values() if isinstance(v, (int, float))]
    if not values:
        return 0.0

    avg_rate = sum(values) / len(values)
    deviation = avg_rate - SUCCESS_RATE_BASELINE
    return deviation * CORRELATION_SCALE


def _compute_confidence_adjustment(summary: dict) -> float:
    """Confidence adjustment from plan and goal success data.

    If plans are producing good outcomes, nudge confidence up.
    If plan_count is high but goal_count is low, nudge down
    (many plans, few goals = fragmentation signal).
    """
    plan_count = summary.get("plan_count", 0)
    goal_count = summary.get("goal_count", 0)

    if not isinstance(plan_count, (int, float)) or plan_count < 1:
        return 0.0
    if not isinstance(goal_count, (int, float)) or goal_count < 1:
        return 0.0

    ratio = float(goal_count) / float(plan_count)

    if ratio >= 0.5:
        return 0.01
    else:
        return -0.01


def apply_analytics_to_policy(
    plan_confidence: float,
    signal: AnalyticsSignal,
) -> float:
    """Apply analytics confidence adjustment to plan confidence.

    Additive, clamped to [0, 1].  Zero signal = no change.
    """
    if not signal.is_active:
        return plan_confidence
    return _clamp(plan_confidence + signal.confidence_adjustment, 0.0, 1.0)
