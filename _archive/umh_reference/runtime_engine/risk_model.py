"""
Counterfactual Risk + Irreversibility Layer — prevents confident-but-wrong decisions.

For each candidate action, simulates both the expected trajectory and an adverse
(counterfactual worst-case) trajectory. Computes a risk score from the gap between
them, weighted by how hard the adverse outcome is to recover from.

risk_score = (expected_reward - worst_case_reward) × irreversibility_factor

This is NOT pessimism. It protects the system from selecting actions that look
optimal but lead to hard-to-recover states.

Deterministic. Bounded. No LLM calls. No state mutation. No randomness.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ─── Constants ────────────────────────────────────────────────────

LAMBDA_MIN = 0.3
LAMBDA_MAX = 0.7
LAMBDA_DEFAULT = 0.5

RISK_BLOCK_THRESHOLD = 0.8
CONFIDENCE_HIGH = 0.7

IRREVERSIBILITY_BASE = 0.2
IRREVERSIBILITY_RECOVERY_WEIGHT = 0.3
IRREVERSIBILITY_CAUSAL_WEIGHT = 0.2
IRREVERSIBILITY_REGIME_WEIGHT = 0.15
IRREVERSIBILITY_TRAP_WEIGHT = 0.15

VARIANCE_WORST_CASE_MULTIPLIER = 2.0
FAILURE_RATE_FLOOR = 0.1
MIN_OBSERVATIONS_FOR_HISTORY = 5
HISTORICAL_RECOVERY_DECAY = 0.9

EPSILON = 1e-9


# ─── Helpers ──────────────────────────────────────────────────────


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


# ─── Data structures ─────────────────────────────────────────────


@dataclass(frozen=True)
class CounterfactualEstimate:
    """Expected vs worst-case estimate for a single action."""

    action: str
    expected_reward: float
    worst_case_reward: float
    reward_gap: float
    irreversibility_factor: float
    risk_score: float
    risk_adjusted_score: float
    blocked: bool
    block_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "expected_reward": round(self.expected_reward, 6),
            "worst_case_reward": round(self.worst_case_reward, 6),
            "reward_gap": round(self.reward_gap, 6),
            "irreversibility_factor": round(self.irreversibility_factor, 4),
            "risk_score": round(self.risk_score, 6),
            "risk_adjusted_score": round(self.risk_adjusted_score, 6),
            "blocked": self.blocked,
            "block_reason": self.block_reason,
        }


@dataclass(frozen=True)
class RiskAssessment:
    """Full risk assessment across all candidate actions."""

    estimates: tuple[CounterfactualEstimate, ...]
    lambda_used: float
    safest_action: str | None
    riskiest_action: str | None
    any_blocked: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "estimates": [e.to_dict() for e in self.estimates],
            "lambda_used": round(self.lambda_used, 4),
            "safest_action": self.safest_action,
            "riskiest_action": self.riskiest_action,
            "any_blocked": self.any_blocked,
        }

    def get_estimate(self, action: str) -> CounterfactualEstimate | None:
        for e in self.estimates:
            if e.action == action:
                return e
        return None


NO_RISK_ASSESSMENT = RiskAssessment(
    estimates=(),
    lambda_used=LAMBDA_DEFAULT,
    safest_action=None,
    riskiest_action=None,
    any_blocked=False,
)


# ─── Worst-case estimation ───────────────────────────────────────


def _estimate_worst_case_reward(
    expected_reward: float,
    variance: float,
    failure_rate: float,
    historical_worst: float | None,
) -> float:
    """Estimate worst-case reward for an action.

    Uses variance-based lower bound, failure rate, and historical floor.
    The worst case is the minimum of:
    1. Expected minus 2× standard deviation (variance-based)
    2. Weighted blend of expected and historical worst
    3. Expected scaled by failure rate
    """
    std = variance**0.5 if variance > 0 else 0.0
    variance_floor = expected_reward - VARIANCE_WORST_CASE_MULTIPLIER * std

    failure_adjusted = expected_reward * (1.0 - failure_rate)

    if historical_worst is not None:
        historical_floor = 0.3 * historical_worst + 0.7 * expected_reward
    else:
        historical_floor = variance_floor

    return min(variance_floor, failure_adjusted, historical_floor)


# ─── Irreversibility detection ───────────────────────────────────


def _compute_irreversibility(
    action: str,
    causal_stats: dict | None,
    context_type: str,
    regime_active: bool,
    trap_signal_active: bool,
    recovery_history: dict[str, float] | None,
) -> float:
    """Compute irreversibility factor [0, 1] for an action.

    High irreversibility when:
    - Recovery time historically long
    - Causal memory shows repeated failures
    - Regime engine signals instability
    - Trap recovery previously triggered
    """
    factor = IRREVERSIBILITY_BASE

    if recovery_history and action in recovery_history:
        recovery_time = recovery_history[action]
        recovery_contribution = _clamp(
            recovery_time * HISTORICAL_RECOVERY_DECAY, 0.0, 1.0
        )
        factor += IRREVERSIBILITY_RECOVERY_WEIGHT * recovery_contribution

    if causal_stats and isinstance(causal_stats, dict):
        key = f"{context_type}|{action}"
        stat = causal_stats.get(key)
        if stat and isinstance(stat, dict):
            count = int(stat.get("count", 0))
            if count >= MIN_OBSERVATIONS_FOR_HISTORY:
                positive = int(stat.get("positive_count", 0))
                failure_rate = 1.0 - (positive / max(count, 1))
                variance = float(stat.get("ema_variance", 0.0))
                causal_risk = _clamp(failure_rate * 0.6 + variance * 0.4, 0.0, 1.0)
                factor += IRREVERSIBILITY_CAUSAL_WEIGHT * causal_risk

    if regime_active:
        factor += IRREVERSIBILITY_REGIME_WEIGHT

    if trap_signal_active:
        factor += IRREVERSIBILITY_TRAP_WEIGHT

    return _clamp(factor, 0.0, 1.0)


# ─── Lambda computation ─────────────────────────────────────────


def _compute_lambda(
    uncertainty: float,
    regime_active: bool,
    trap_signal_active: bool,
) -> float:
    """Compute adaptive λ for risk penalty scaling.

    λ increases with uncertainty and instability signals.
    Range: [LAMBDA_MIN, LAMBDA_MAX].
    """
    base = LAMBDA_DEFAULT

    uncertainty_shift = (uncertainty - 0.5) * 0.4
    base += uncertainty_shift

    if regime_active:
        base += 0.05
    if trap_signal_active:
        base += 0.1

    return _clamp(base, LAMBDA_MIN, LAMBDA_MAX)


# ─── Core risk computation ───────────────────────────────────────


def compute_counterfactual_risk(
    action: str,
    expected_reward: float,
    causal_stats: dict | None,
    context_type: str,
    uncertainty: float = 0.0,
    regime_active: bool = False,
    trap_signal_active: bool = False,
    recovery_history: dict[str, float] | None = None,
    lambda_override: float | None = None,
    confidence: float = 0.5,
) -> CounterfactualEstimate:
    """Compute counterfactual risk for a single action.

    Simulates the adverse trajectory alongside the expected one and
    produces a risk-adjusted score.
    """
    variance = 0.0
    failure_rate = FAILURE_RATE_FLOOR
    historical_worst: float | None = None

    if causal_stats and isinstance(causal_stats, dict):
        key = f"{context_type}|{action}"
        stat = causal_stats.get(key)
        if stat and isinstance(stat, dict):
            count = int(stat.get("count", 0))
            if count >= MIN_OBSERVATIONS_FOR_HISTORY:
                variance = float(stat.get("ema_variance", 0.0))
                positive = int(stat.get("positive_count", 0))
                failure_rate = max(
                    1.0 - (positive / max(count, 1)),
                    FAILURE_RATE_FLOOR,
                )
                worst_delta = float(stat.get("ema_reward_delta", 0.0)) - 2.0 * (
                    variance**0.5
                )
                historical_worst = worst_delta

    worst_case = _estimate_worst_case_reward(
        expected_reward=expected_reward,
        variance=variance,
        failure_rate=failure_rate,
        historical_worst=historical_worst,
    )

    reward_gap = max(expected_reward - worst_case, 0.0)

    irreversibility = _compute_irreversibility(
        action=action,
        causal_stats=causal_stats,
        context_type=context_type,
        regime_active=regime_active,
        trap_signal_active=trap_signal_active,
        recovery_history=recovery_history,
    )

    risk_score = reward_gap * irreversibility

    lam = (
        lambda_override
        if lambda_override is not None
        else _compute_lambda(
            uncertainty=uncertainty,
            regime_active=regime_active,
            trap_signal_active=trap_signal_active,
        )
    )

    risk_adjusted_score = expected_reward - lam * risk_score

    blocked = False
    block_reason = ""
    if risk_score > RISK_BLOCK_THRESHOLD and confidence < CONFIDENCE_HIGH:
        blocked = True
        block_reason = (
            f"risk_score={risk_score:.4f}>{RISK_BLOCK_THRESHOLD}"
            f",confidence={confidence:.4f}<{CONFIDENCE_HIGH}"
        )

    return CounterfactualEstimate(
        action=action,
        expected_reward=expected_reward,
        worst_case_reward=worst_case,
        reward_gap=reward_gap,
        irreversibility_factor=irreversibility,
        risk_score=risk_score,
        risk_adjusted_score=risk_adjusted_score,
        blocked=blocked,
        block_reason=block_reason,
    )


# ─── Batch assessment ────────────────────────────────────────────


def assess_actions(
    actions: list[str],
    expected_rewards: dict[str, float],
    causal_stats: dict | None = None,
    context_type: str = "stable",
    uncertainty: float = 0.0,
    regime_active: bool = False,
    trap_signal_active: bool = False,
    recovery_history: dict[str, float] | None = None,
    lambda_override: float | None = None,
    confidences: dict[str, float] | None = None,
) -> RiskAssessment:
    """Assess counterfactual risk for a batch of candidate actions.

    Returns a RiskAssessment with per-action estimates, safest/riskiest
    action identification, and whether any action was blocked.
    """
    if not actions or not expected_rewards:
        return NO_RISK_ASSESSMENT

    lam = (
        lambda_override
        if lambda_override is not None
        else _compute_lambda(
            uncertainty=uncertainty,
            regime_active=regime_active,
            trap_signal_active=trap_signal_active,
        )
    )

    estimates: list[CounterfactualEstimate] = []
    for action in actions:
        reward = expected_rewards.get(action, 0.0)
        confidence = (confidences or {}).get(action, 0.5)

        est = compute_counterfactual_risk(
            action=action,
            expected_reward=reward,
            causal_stats=causal_stats,
            context_type=context_type,
            uncertainty=uncertainty,
            regime_active=regime_active,
            trap_signal_active=trap_signal_active,
            recovery_history=recovery_history,
            lambda_override=lam,
            confidence=confidence,
        )
        estimates.append(est)

    non_blocked = [e for e in estimates if not e.blocked]
    all_estimates = estimates

    safest = None
    riskiest = None

    if all_estimates:
        safest_est = min(all_estimates, key=lambda e: e.risk_score)
        riskiest_est = max(all_estimates, key=lambda e: e.risk_score)
        safest = safest_est.action
        riskiest = riskiest_est.action

    any_blocked = any(e.blocked for e in all_estimates)

    return RiskAssessment(
        estimates=tuple(all_estimates),
        lambda_used=lam,
        safest_action=safest,
        riskiest_action=riskiest,
        any_blocked=any_blocked,
    )


# ─── Planner integration ─────────────────────────────────────────


def apply_risk_adjustment(
    trajectory_scores: dict[str, float],
    assessment: RiskAssessment,
) -> dict[str, float]:
    """Apply counterfactual risk penalties to trajectory scores.

    Blocked actions get their score zeroed out.
    Non-blocked actions get risk-proportional penalty.

    Returns a new dict — never mutates the input.
    """
    if not assessment.estimates:
        return dict(trajectory_scores)

    adjusted = dict(trajectory_scores)
    lam = assessment.lambda_used

    for est in assessment.estimates:
        if est.action not in adjusted:
            continue

        if est.blocked:
            adjusted[est.action] = 0.0
            continue

        penalty = lam * est.risk_score
        adjusted[est.action] = adjusted[est.action] - penalty

    return adjusted


def select_safest_action(
    trajectory_scores: dict[str, float],
    assessment: RiskAssessment,
) -> str | None:
    """Select the action that maximizes risk-adjusted score.

    Prefers slightly lower reward if much lower risk.
    Returns None if all actions are blocked.
    """
    if not assessment.estimates:
        return None

    non_blocked = [e for e in assessment.estimates if not e.blocked]
    if not non_blocked:
        return None

    available = {
        e.action: e.risk_adjusted_score
        for e in non_blocked
        if e.action in trajectory_scores
    }

    if not available:
        return None

    return max(available, key=available.get)  # type: ignore[arg-type]
