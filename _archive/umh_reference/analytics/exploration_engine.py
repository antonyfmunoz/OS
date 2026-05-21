"""
Exploration engine — deterministic strategy diversification for EOS.

Addresses the "no exploration" weakness identified in benchmark analysis:
when the system converges on a strategy, it only discovers regime changes
through accumulated failures. This engine proactively boosts under-tested
strategies when degradation signals appear.

Design constraints:
- Deterministic: same inputs → same signal, always.
- No randomness: activation is signal-based, not probabilistic.
- Bounded: all adjustments clamped to tight ranges.
- No overrides: additive adjustments only, never replaces scores.
- No ExecutionSpine changes: operates on strategy scores externally.

Integration point:
    session_runtime → after objective_optimizer, before objective_decision_adapter.

Signal → Activation → Redistribution:
    1. Compute degradation, confidence, and uncertainty signals.
    2. If any signal crosses its threshold, exploration activates.
    3. Top strategy receives a bounded penalty.
    4. Penalty budget is redistributed to under-tested/second-best strategies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.analytics.score_distribution import compute_distribution, compute_relative_uncertainty


# ─── Constants ────────────────────────────────────────────────────

MIN_STRATEGIES = 2
MIN_HISTORY_TURNS = 3

DEGRADATION_THRESHOLD = -0.01
CONFIDENCE_THRESHOLD = 0.3
FAILURE_STREAK_THRESHOLD = 2
UNCERTAINTY_THRESHOLD = 0.15

MAX_TOP_PENALTY = 0.05
MAX_BOOST = 0.03
MAX_TOTAL_REDISTRIBUTION = 0.05

NORMALIZED_GAP_HIGH = 2.0
NORMALIZED_GAP_LOW = 0.5


# ─── Data structures ─────────────────────────────────────────────


@dataclass(frozen=True)
class ExplorationSignal:
    """Result of exploration computation. Immutable snapshot."""

    exploration_active: bool
    exploration_adjustments: dict[str, float]
    exploration_reason: str
    candidates_boosted: tuple[str, ...]
    activation_strength: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "exploration_active": self.exploration_active,
            "exploration_adjustments": {
                k: round(v, 6) for k, v in self.exploration_adjustments.items()
            },
            "exploration_reason": self.exploration_reason,
            "candidates_boosted": list(self.candidates_boosted),
            "activation_strength": round(self.activation_strength, 6),
        }


NO_EXPLORATION = ExplorationSignal(
    exploration_active=False,
    exploration_adjustments={},
    exploration_reason="",
    candidates_boosted=(),
    activation_strength=0.0,
)


# ─── Signal computation ──────────────────────────────────────────


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _compute_degradation_signal(objective_trend: str | None) -> float:
    """Map objective trend to degradation signal [0, 1]."""
    if objective_trend == "degrading":
        return 1.0
    if objective_trend == "flat":
        return 0.3
    return 0.0


def _compute_confidence_signal(plan_confidence: float | None) -> float:
    """Map plan confidence to exploration need [0, 1]. Lower confidence → higher signal."""
    if plan_confidence is None:
        return 0.0
    return _clamp(1.0 - plan_confidence, 0.0, 1.0)


def _compute_failure_signal(failure_streak: int) -> float:
    """Map consecutive failures to exploration urgency [0, 1]."""
    if failure_streak < FAILURE_STREAK_THRESHOLD:
        return 0.0
    return _clamp((failure_streak - FAILURE_STREAK_THRESHOLD + 1) * 0.25, 0.0, 1.0)


def _compute_uncertainty_signal(strategy_scores: dict[str, float]) -> float:
    """Measure how uncertain the system should be about its top choice.

    Uses distribution-aware RelativeUncertainty rather than raw entropy.
    normalized_gap > 2.0 → leader is 2+ std devs ahead → low uncertainty.
    normalized_gap < 0.5 → gap is within noise → high uncertainty.
    All-zero or single strategy → 0.0 (uninformed, not uncertain).
    """
    if len(strategy_scores) < MIN_STRATEGIES:
        return 0.0

    total = sum(strategy_scores.values())
    if total <= 0:
        return 0.0

    ru = compute_relative_uncertainty(strategy_scores)
    return ru.level


def _compute_activation_strength(
    degradation: float,
    confidence_need: float,
    failure_urgency: float,
    uncertainty: float,
) -> float:
    """Combine signals into a single activation strength [0, 1].

    Uses max-of-signals rather than average — any strong signal
    should trigger exploration. Weighted to favor degradation and
    failure streaks (more actionable signals).
    """
    return _clamp(
        max(
            degradation * 0.8,
            confidence_need * 0.5,
            failure_urgency * 0.9,
            uncertainty * 0.4,
        ),
        0.0,
        1.0,
    )


# ─── Score redistribution ────────────────────────────────────────


def _compute_adjustments(
    strategy_scores: dict[str, float],
    activation_strength: float,
) -> tuple[dict[str, float], tuple[str, ...]]:
    """Redistribute score budget from top strategy to under-tested alternatives.

    Uses normalized_gap from score distribution to scale penalty intensity:
    - normalized_gap > 2.0 → leader is 2+ σ ahead → gentle exploration (small penalty)
    - normalized_gap < 0.5 → gap is noise → aggressive exploration (large penalty)
    - dispersion modulates: high dispersion amplifies penalty

    Returns (adjustments_dict, boosted_strategy_names).
    """
    if len(strategy_scores) < MIN_STRATEGIES:
        return {}, ()

    sorted_strategies = sorted(strategy_scores.items(), key=lambda x: -x[1])
    top_name, top_score = sorted_strategies[0]

    others = sorted_strategies[1:]
    if not others:
        return {}, ()

    dist = compute_distribution(strategy_scores)
    second_score = others[0][1]
    gap = top_score - second_score

    if gap <= 0:
        penalty = _clamp(activation_strength * MAX_TOP_PENALTY, 0.0, MAX_TOP_PENALTY)
    else:
        gap_intensity = 1.0 - _clamp(dist.normalized_gap / 3.0, 0.0, 1.0)
        dispersion_boost = _clamp(dist.dispersion / 2.0, 0.0, 0.3)

        if dist.normalized_gap < NORMALIZED_GAP_LOW:
            scale = _clamp(1.0 + dispersion_boost, 1.0, 1.3)
        elif dist.normalized_gap > NORMALIZED_GAP_HIGH:
            scale = _clamp(gap_intensity, 0.1, 0.5)
        else:
            scale = _clamp(gap_intensity + dispersion_boost, 0.3, 1.0)

        narrowing_fraction = _clamp(activation_strength * scale * 0.6, 0.0, 0.6)
        penalty = gap * narrowing_fraction
        penalty = min(penalty, top_score * 0.5)

    boost_per_strategy = penalty / len(others)

    adjustments: dict[str, float] = {top_name: -penalty}
    boosted: list[str] = []

    for name, _ in others:
        adjustments[name] = boost_per_strategy
        boosted.append(name)

    return adjustments, tuple(boosted)


# ─── Public API ───────────────────────────────────────────────────


def compute_exploration_signal(
    plan_confidence: float | None = None,
    objective_trend: str | None = None,
    failure_streak: int = 0,
    strategy_scores: dict[str, float] | None = None,
) -> ExplorationSignal:
    """Compute whether exploration should activate and what adjustments to make.

    Deterministic: same inputs → same signal, always.
    No randomness. No side effects. Pure function.

    Args:
        plan_confidence: Current plan confidence [0, 1]. None if unknown.
        objective_trend: "improving", "degrading", or "flat". None if unavailable.
        failure_streak: Consecutive plan step failures. 0 if none.
        strategy_scores: Current strategy scores {name: score}. None if unavailable.

    Returns:
        ExplorationSignal with adjustments to apply to strategy scores.
    """
    scores = strategy_scores or {}

    if len(scores) < MIN_STRATEGIES:
        return NO_EXPLORATION

    degradation = _compute_degradation_signal(objective_trend)
    confidence_need = _compute_confidence_signal(plan_confidence)
    failure_urgency = _compute_failure_signal(failure_streak)
    uncertainty = _compute_uncertainty_signal(scores)

    strength = _compute_activation_strength(
        degradation, confidence_need, failure_urgency, uncertainty
    )

    should_activate = (
        degradation > 0.5
        or confidence_need > (1.0 - CONFIDENCE_THRESHOLD)
        or failure_urgency > 0.0
        or uncertainty > (1.0 - UNCERTAINTY_THRESHOLD)
    )

    if not should_activate or strength < 0.1:
        return NO_EXPLORATION

    adjustments, boosted = _compute_adjustments(scores, strength)

    if not adjustments:
        return NO_EXPLORATION

    reasons: list[str] = []
    if degradation > 0.5:
        reasons.append("degrading_trend")
    if confidence_need > (1.0 - CONFIDENCE_THRESHOLD):
        reasons.append("low_confidence")
    if failure_urgency > 0.0:
        reasons.append(f"failure_streak_{failure_streak}")
    if uncertainty > (1.0 - UNCERTAINTY_THRESHOLD):
        reasons.append("high_uncertainty")

    return ExplorationSignal(
        exploration_active=True,
        exploration_adjustments=adjustments,
        exploration_reason="+".join(reasons),
        candidates_boosted=boosted,
        activation_strength=strength,
    )


def apply_exploration_adjustments(
    strategy_scores: dict[str, float],
    signal: ExplorationSignal,
) -> dict[str, float]:
    """Apply exploration adjustments to strategy scores.

    Additive only. All scores floored at 0.0.
    Returns a new dict — never mutates the input.
    """
    if not signal.exploration_active:
        return dict(strategy_scores)

    result: dict[str, float] = {}
    for name, score in strategy_scores.items():
        adj = signal.exploration_adjustments.get(name, 0.0)
        result[name] = score + adj

    return result
