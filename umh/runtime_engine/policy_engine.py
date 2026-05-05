"""
PolicyEngine — deterministic per-turn reasoning mode selection.

Selects one of five policies based on observable runtime signals and
produces a coherent set of adjustments that shape downstream behavior
(influence weights, goal scaling, plan confidence).

Policies::

    EXPLOIT  — high confidence, exploit current best path
    EXPLORE  — low confidence or stagnation, widen search
    RECOVER  — failure streak detected, reduce risk
    COMMIT   — strong persistence streak, double down
    PIVOT    — plan confidence collapsed, switch direction

Selection is deterministic: same signals → same policy.
Adjustments are bounded and additive/multiplicative only.

No LLM calls.  No randomness.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Policy(Enum):
    EXPLOIT = "exploit"
    EXPLORE = "explore"
    RECOVER = "recover"
    COMMIT = "commit"
    PIVOT = "pivot"


FAILURE_STREAK_THRESHOLD = 2
PERSISTENCE_STREAK_THRESHOLD = 3
LOW_PLAN_CONFIDENCE = 0.25
HIGH_PLAN_CONFIDENCE = 0.70
LOW_SIMILARITY_DELTA = -0.15
HIGH_EXPLORATION_RATE = 0.60

INFLUENCE_WEIGHT_MODIFIERS: dict[Policy, dict[str, float]] = {
    Policy.EXPLOIT: {
        "goal": 0.05,
        "plan": 0.03,
        "strategy": 0.02,
        "state_bias": 0.0,
        "credit": 0.0,
        "exploration": -0.05,
        "commitment": 0.0,
    },
    Policy.EXPLORE: {
        "goal": -0.03,
        "plan": -0.02,
        "strategy": -0.02,
        "state_bias": 0.02,
        "credit": 0.0,
        "exploration": 0.05,
        "commitment": -0.02,
    },
    Policy.RECOVER: {
        "goal": 0.0,
        "plan": -0.05,
        "strategy": 0.03,
        "state_bias": 0.0,
        "credit": 0.05,
        "exploration": 0.02,
        "commitment": -0.03,
    },
    Policy.COMMIT: {
        "goal": 0.03,
        "plan": 0.05,
        "strategy": 0.0,
        "state_bias": 0.0,
        "credit": 0.0,
        "exploration": -0.03,
        "commitment": 0.05,
    },
    Policy.PIVOT: {
        "goal": -0.05,
        "plan": -0.05,
        "strategy": 0.0,
        "state_bias": 0.03,
        "credit": 0.02,
        "exploration": 0.05,
        "commitment": -0.05,
    },
}

GOAL_SCALING: dict[Policy, float] = {
    Policy.EXPLOIT: 1.0,
    Policy.EXPLORE: 0.90,
    Policy.RECOVER: 0.85,
    Policy.COMMIT: 1.10,
    Policy.PIVOT: 0.80,
}

PLAN_CONFIDENCE_MODIFIER: dict[Policy, float] = {
    Policy.EXPLOIT: 0.05,
    Policy.EXPLORE: -0.05,
    Policy.RECOVER: -0.10,
    Policy.COMMIT: 0.10,
    Policy.PIVOT: -0.15,
}

MAX_INFLUENCE_MODIFIER = 0.05
MAX_PLAN_MODIFIER = 0.15
MIN_GOAL_SCALE = 0.80
MAX_GOAL_SCALE = 1.10


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


@dataclass(frozen=True)
class PolicySignals:
    """Input signals for policy selection."""

    failure_streak: int = 0
    persistence_streak: int = 0
    exploration_rate: float = 0.0
    plan_confidence: float = 0.5
    state_similarity_delta: float = 0.0

    def to_dict(self) -> dict:
        return {
            "failure_streak": self.failure_streak,
            "persistence_streak": self.persistence_streak,
            "exploration_rate": round(self.exploration_rate, 4),
            "plan_confidence": round(self.plan_confidence, 4),
            "state_similarity_delta": round(self.state_similarity_delta, 4),
        }


@dataclass(frozen=True)
class PolicyAdjustments:
    """Computed adjustments from the selected policy."""

    influence_weight_modifiers: dict[str, float]
    goal_scaling: float
    plan_confidence_modifier: float

    def to_dict(self) -> dict:
        return {
            "influence_weight_modifiers": {
                k: round(v, 4) for k, v in self.influence_weight_modifiers.items()
            },
            "goal_scaling": round(self.goal_scaling, 4),
            "plan_confidence_modifier": round(self.plan_confidence_modifier, 4),
        }


@dataclass(frozen=True)
class PolicyResult:
    """Immutable record of policy selection for a single turn."""

    policy: Policy
    reason: str
    signals: PolicySignals
    adjustments: PolicyAdjustments

    def to_dict(self) -> dict:
        return {
            "policy": self.policy.value,
            "reason": self.reason,
            "signals": self.signals.to_dict(),
            "adjustments": self.adjustments.to_dict(),
        }


NO_POLICY_RESULT = PolicyResult(
    policy=Policy.EXPLOIT,
    reason="default",
    signals=PolicySignals(),
    adjustments=PolicyAdjustments(
        influence_weight_modifiers={},
        goal_scaling=1.0,
        plan_confidence_modifier=0.0,
    ),
)


def select_policy(
    signals: PolicySignals,
    analytics_signal: object | None = None,
) -> PolicyResult:
    """Select a policy based on current runtime signals.

    Priority order (first match wins):
        1. RECOVER — failure_streak >= threshold
        2. PIVOT   — plan_confidence < LOW and similarity dropping
        3. COMMIT  — persistence_streak >= threshold and plan confidence high
        4. EXPLORE — high exploration_rate or low plan confidence
        5. EXPLOIT — default (everything else)

    When analytics_signal is provided, its policy_bias and
    confidence_adjustment are applied additively to the signals
    before selection.  All adjustments are bounded.

    Deterministic: same signals → same policy.
    """
    effective_confidence = signals.plan_confidence
    effective_exploration = signals.exploration_rate

    if analytics_signal is not None:
        _p_bias = getattr(analytics_signal, "policy_bias", 0.0)
        _c_adj = getattr(analytics_signal, "confidence_adjustment", 0.0)
        _s_bias = getattr(analytics_signal, "strategy_bias", 0.0)
        effective_confidence = _clamp(effective_confidence + _c_adj, 0.0, 1.0)
        effective_exploration = _clamp(effective_exploration - _s_bias, 0.0, 1.0)

    policy: Policy
    reason: str

    if signals.failure_streak >= FAILURE_STREAK_THRESHOLD:
        policy = Policy.RECOVER
        reason = f"failure_streak={signals.failure_streak}"
    elif (
        effective_confidence < LOW_PLAN_CONFIDENCE
        and signals.state_similarity_delta < LOW_SIMILARITY_DELTA
    ):
        policy = Policy.PIVOT
        reason = (
            f"low_confidence={effective_confidence:.2f},"
            f"sim_delta={signals.state_similarity_delta:.2f}"
        )
    elif (
        signals.persistence_streak >= PERSISTENCE_STREAK_THRESHOLD
        and effective_confidence >= HIGH_PLAN_CONFIDENCE
    ):
        policy = Policy.COMMIT
        reason = (
            f"persistence={signals.persistence_streak},"
            f"confidence={effective_confidence:.2f}"
        )
    elif (
        effective_exploration >= HIGH_EXPLORATION_RATE
        or effective_confidence < LOW_PLAN_CONFIDENCE
    ):
        policy = Policy.EXPLORE
        reason = (
            f"exploration_rate={effective_exploration:.2f},"
            f"confidence={effective_confidence:.2f}"
        )
    else:
        policy = Policy.EXPLOIT
        reason = "default_exploit"

    modifiers = INFLUENCE_WEIGHT_MODIFIERS[policy]
    bounded_modifiers = {
        k: _clamp(v, -MAX_INFLUENCE_MODIFIER, MAX_INFLUENCE_MODIFIER)
        for k, v in modifiers.items()
    }

    adjustments = PolicyAdjustments(
        influence_weight_modifiers=bounded_modifiers,
        goal_scaling=_clamp(GOAL_SCALING[policy], MIN_GOAL_SCALE, MAX_GOAL_SCALE),
        plan_confidence_modifier=_clamp(
            PLAN_CONFIDENCE_MODIFIER[policy],
            -MAX_PLAN_MODIFIER,
            MAX_PLAN_MODIFIER,
        ),
    )

    return PolicyResult(
        policy=policy,
        reason=reason,
        signals=signals,
        adjustments=adjustments,
    )


def apply_influence_modifiers(
    base_weights: dict[str, float],
    modifiers: dict[str, float],
) -> dict[str, float]:
    """Apply policy influence weight modifiers additively, then renormalize.

    Each modifier is clamped, added to the base weight, floored at 0.01,
    then all weights are renormalized to sum to 1.0.
    """
    adjusted: dict[str, float] = {}
    for name, base in base_weights.items():
        mod = modifiers.get(name, 0.0)
        adjusted[name] = max(base + mod, 0.01)

    total = sum(adjusted.values())
    if total <= 0:
        n = len(adjusted)
        return {k: 1.0 / n for k in adjusted} if n > 0 else {}
    return {k: v / total for k, v in adjusted.items()}


def apply_plan_confidence_modifier(
    plan_confidence: float,
    modifier: float,
) -> float:
    """Apply additive plan confidence modifier, clamped to [0, 1]."""
    return _clamp(plan_confidence + modifier, 0.0, 1.0)
