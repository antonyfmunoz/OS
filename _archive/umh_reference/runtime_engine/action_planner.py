"""
Multi-trajectory action selection — bounded forward evaluation of candidate actions.

Evaluates a small set of candidate actions (K ≤ 3) using adaptive-horizon forward
rollouts and selects the action with the best projected trajectory score.
Returns an optional override recommendation with uncertainty-aware confidence gating.

Sits AFTER foresight and BEFORE signal orchestration in the pipeline.

Adaptive horizon: planning depth scales inversely with uncertainty.
High uncertainty → short horizon (avoid overcommitment).
Low uncertainty + stable context → deeper planning.

NOT planning. NOT tree search. NOT recursive.
Deterministic. Bounded. No state mutation. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass

from umh.runtime_engine.risk_model import (
    CounterfactualEstimate,
    RiskAssessment,
    assess_actions,
    apply_risk_adjustment,
)

# ─── Constants ──────────────────────────────────────────────────────

MAX_CANDIDATES = 3
MIN_HORIZON = 1
MAX_HORIZON = 7
DEFAULT_HORIZON = 3
GAMMA = 0.9
REWARD_WEIGHT = 0.5
OBJECTIVE_WEIGHT = 0.5
CONFIDENCE_THRESHOLD = 0.6
MIN_DATA_OBSERVATIONS = 5
MIN_CREDIT_OBSERVATIONS = 2
STABILITY_BONUS_WEIGHT = 0.15
RISK_PENALTY_WEIGHT = 0.20
VARIANCE_PENALTY_SCALE = 3.0
REGIME_INSTABILITY_PENALTY = 0.3
TRAP_PENALTY = 0.25
SCORE_MARGIN_THRESHOLD = 0.01
UNCERTAINTY_PENALTY_SCALE = 0.10
UNCERTAINTY_HIGH = 0.7
UNCERTAINTY_LOW = 0.3
CONSISTENCY_PENALTY_SCALE = 0.25
EXPLORATION_PROXIMITY_THRESHOLD = 0.02


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


# ─── Data structures ───────────────────────────────────────────────


@dataclass(frozen=True)
class TrajectoryStep:
    """Single simulated step in a trajectory."""

    step: int
    discount: float
    reward_estimate: float
    objective_estimate: float
    cumulative_value: float


@dataclass(frozen=True)
class TrajectoryResult:
    """Full trajectory evaluation for one candidate action."""

    action: str
    steps: tuple[TrajectoryStep, ...]
    raw_score: float
    stability_bonus: float
    risk_penalty: float
    uncertainty_penalty: float
    trajectory_score: float
    confidence: float
    step_consistency: float
    counterfactual_risk_score: float = 0.0
    worst_case_estimate: float = 0.0
    irreversibility_factor: float = 0.0
    risk_adjusted_score: float = 0.0

    def to_dict(self) -> dict:
        d: dict = {
            "action": self.action,
            "steps_used": len(self.steps),
            "raw_score": round(self.raw_score, 6),
            "stability_bonus": round(self.stability_bonus, 6),
            "risk_penalty": round(self.risk_penalty, 6),
            "uncertainty_penalty": round(self.uncertainty_penalty, 6),
            "trajectory_score": round(self.trajectory_score, 6),
            "confidence": round(self.confidence, 4),
            "step_consistency": round(self.step_consistency, 4),
        }
        if self.counterfactual_risk_score > 0.0:
            d["counterfactual_risk_score"] = round(self.counterfactual_risk_score, 6)
            d["worst_case_estimate"] = round(self.worst_case_estimate, 6)
            d["irreversibility_factor"] = round(self.irreversibility_factor, 4)
            d["risk_adjusted_score"] = round(self.risk_adjusted_score, 6)
        return d


@dataclass(frozen=True)
class PlannerResult:
    """Output of the action planner: optional override + trajectory analysis."""

    active: bool
    selected_action_override: str | None
    trajectory_scores: dict[str, float]
    planner_confidence: float
    reason: str
    horizon_used: int
    uncertainty: float
    consistency: float
    adjusted_confidence: float
    trajectories: tuple[TrajectoryResult, ...] = ()

    def to_dict(self) -> dict:
        d: dict = {
            "active": self.active,
            "selected_action_override": self.selected_action_override,
            "trajectory_scores": {
                k: round(v, 6) for k, v in self.trajectory_scores.items()
            },
            "planner_confidence": round(self.planner_confidence, 4),
            "reason": self.reason,
            "horizon_used": self.horizon_used,
            "uncertainty": round(self.uncertainty, 4),
            "consistency": round(self.consistency, 4),
            "adjusted_confidence": round(self.adjusted_confidence, 4),
        }
        if self.trajectories:
            d["trajectories"] = [t.to_dict() for t in self.trajectories]
        return d


NO_PLANNER_RESULT = PlannerResult(
    active=False,
    selected_action_override=None,
    trajectory_scores={},
    planner_confidence=0.0,
    reason="planner_inactive",
    horizon_used=0,
    uncertainty=0.0,
    consistency=0.0,
    adjusted_confidence=0.0,
)


# ─── Uncertainty computation ───────────────────────────────────────


def compute_uncertainty(
    strategy_scores: dict[str, float] | None,
) -> float:
    """Compute uncertainty from strategy score distribution.

    Uses the same logic as RelativeUncertainty from score_distribution.py
    but self-contained to avoid circular import. Returns [0, 1].
    """
    if not strategy_scores or not isinstance(strategy_scores, dict):
        return 1.0

    values = sorted(strategy_scores.values(), reverse=True)
    n = len(values)
    if n < 2:
        return 0.0

    max_score = values[0]
    second_best = values[1]

    if max_score <= 0 and second_best <= 0:
        return 0.0

    raw_gap = max_score - second_best
    if raw_gap == 0.0:
        return 1.0

    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    std = variance**0.5 if variance > 0 else 0.0

    epsilon = 1e-9
    normalized_gap = raw_gap / (std + epsilon)

    gap_factor = 1.0 - _clamp(normalized_gap / 3.0, 0.0, 1.0)
    dispersion = std / (abs(mean) + epsilon) if abs(mean) > epsilon else 0.0
    dispersion_boost = _clamp(dispersion / 2.0, 0.0, 0.3)

    return _clamp(gap_factor + dispersion_boost, 0.0, 1.0)


# ─── Adaptive horizon ──────────────────────────────────────────────


def compute_adaptive_horizon(
    uncertainty: float,
    context_type: str | None,
) -> int:
    """Compute planning horizon based on uncertainty and context stability.

    High uncertainty → short horizon (1-2): avoid overcommitment.
    Low uncertainty + stable → deep horizon (5-7): confident forward planning.
    Medium → default range (3-5).
    """
    if uncertainty > UNCERTAINTY_HIGH:
        return _clamp_int(round(2.0 - uncertainty), MIN_HORIZON, 2)

    if uncertainty < UNCERTAINTY_LOW and context_type == "stable":
        depth = round(5.0 + (UNCERTAINTY_LOW - uncertainty) * 6.67)
        return _clamp_int(depth, 5, MAX_HORIZON)

    mid = round(3.0 + (0.5 - uncertainty) * 4.0)
    return _clamp_int(mid, 3, 5)


def _clamp_int(v: int | float, lo: int, hi: int) -> int:
    v_int = int(v)
    if v_int < lo:
        return lo
    if v_int > hi:
        return hi
    return v_int


# ─── Risk model ────────────────────────────────────────────────────


def _compute_variance_penalty(step_values: list[float]) -> float:
    """Penalize high-variance trajectories — unstable projected paths."""
    if len(step_values) < 2:
        return 0.0
    mean = sum(step_values) / len(step_values)
    variance = sum((v - mean) ** 2 for v in step_values) / len(step_values)
    return _clamp(variance * VARIANCE_PENALTY_SCALE, 0.0, 1.0)


def _compute_regime_penalty(
    context_signal: object | None,
) -> float:
    """Penalize when regime instability signals are present."""
    if context_signal is None:
        return 0.0
    regime = getattr(context_signal, "regime_change_likelihood", 0.0) or 0.0
    adversarial = getattr(context_signal, "adversarial_likelihood", 0.0) or 0.0
    instability = max(float(regime), float(adversarial))
    if instability < 0.05:
        return 0.0
    return _clamp(
        instability * REGIME_INSTABILITY_PENALTY, 0.0, REGIME_INSTABILITY_PENALTY
    )


def _compute_trap_penalty(
    trap_signal_active: bool | None,
) -> float:
    """Penalize when trap detection flags are active."""
    if trap_signal_active:
        return TRAP_PENALTY
    return 0.0


def _compute_uncertainty_penalty(
    uncertainty: float,
    horizon: int,
) -> float:
    """Penalize proportional to uncertainty × horizon length.

    Longer plans under high uncertainty should be penalized more heavily.
    """
    return _clamp(
        uncertainty * horizon * UNCERTAINTY_PENALTY_SCALE,
        0.0,
        1.0,
    )


# ─── Step consistency ──────────────────────────────────────────────


def _compute_step_consistency(step_values: list[float]) -> float:
    """Measure how consistent the trajectory direction is across steps.

    Returns [0, 1] where 1.0 = all steps have the same sign direction.
    Low consistency means the trajectory oscillates — the plan is unstable.
    """
    if len(step_values) < 2:
        return 1.0

    positive = sum(1 for v in step_values if v > 1e-9)
    negative = sum(1 for v in step_values if v < -1e-9)
    total = positive + negative
    if total == 0:
        return 1.0

    return max(positive, negative) / total


# ─── Trajectory simulation ────────────────────────────────────────


def _simulate_trajectory(
    action: str,
    context: str,
    causal_stats: dict | None,
    credit_accumulators: dict | None,
    horizon: int,
    uncertainty: float = 0.0,
    context_signal: object | None = None,
    trap_signal_active: bool | None = None,
    recovery_history: dict[str, float] | None = None,
) -> TrajectoryResult:
    """Simulate a single action's trajectory over H steps.

    Each step uses causal and credit data to estimate reward/objective.
    No real state mutation — all projected.
    """
    horizon = _clamp_int(horizon, MIN_HORIZON, MAX_HORIZON)

    causal_reward = 0.0
    causal_objective = 0.0
    causal_available = False
    causal_count = 0

    if causal_stats and isinstance(causal_stats, dict):
        key = f"{context}|{action}"
        stat = causal_stats.get(key)
        if stat and isinstance(stat, dict):
            count = int(stat.get("count", 0))
            if count >= MIN_DATA_OBSERVATIONS:
                causal_reward = float(stat.get("ema_reward_delta", 0.0))
                causal_objective = float(stat.get("ema_objective_delta", 0.0))
                causal_available = True
                causal_count = count

    credit_reward = 0.0
    credit_objective = 0.0
    credit_available = False
    credit_count = 0

    if credit_accumulators and isinstance(credit_accumulators, dict):
        acc = credit_accumulators.get(action)
        if acc and isinstance(acc, dict):
            obs = int(acc.get("observation_count", 0))
            if obs >= MIN_CREDIT_OBSERVATIONS:
                credit_reward = float(acc.get("reward_credit", 0.0)) / max(obs, 1)
                credit_objective = float(acc.get("objective_credit", 0.0)) / max(obs, 1)
                credit_available = True
                credit_count = obs

    signals_found = int(causal_available) + int(credit_available)
    if signals_found == 0:
        return TrajectoryResult(
            action=action,
            steps=(),
            raw_score=0.0,
            stability_bonus=0.0,
            risk_penalty=0.0,
            uncertainty_penalty=0.0,
            trajectory_score=0.0,
            confidence=0.0,
            step_consistency=1.0,
        )

    steps: list[TrajectoryStep] = []
    cumulative = 0.0
    step_values: list[float] = []

    for k in range(1, horizon + 1):
        discount = GAMMA**k

        step_reward = 0.0
        step_objective = 0.0
        contrib = 0

        if causal_available:
            step_reward += causal_reward
            step_objective += causal_objective
            contrib += 1

        if credit_available:
            step_reward += credit_reward
            step_objective += credit_objective
            contrib += 1

        if contrib > 1:
            step_reward /= contrib
            step_objective /= contrib

        step_value = discount * (
            REWARD_WEIGHT * step_reward + OBJECTIVE_WEIGHT * step_objective
        )
        cumulative += step_value
        step_values.append(step_value)

        steps.append(
            TrajectoryStep(
                step=k,
                discount=discount,
                reward_estimate=step_reward,
                objective_estimate=step_objective,
                cumulative_value=cumulative,
            )
        )

    raw_score = cumulative

    # Stability bonus: consistent positive trajectory gets a boost
    positive_steps = sum(1 for v in step_values if v > 0)
    stability_ratio = positive_steps / max(len(step_values), 1)
    stability_bonus = STABILITY_BONUS_WEIGHT * stability_ratio

    # Risk penalty: variance + regime + trap
    variance_penalty = _compute_variance_penalty(step_values)
    regime_penalty = _compute_regime_penalty(context_signal)
    trap_penalty = _compute_trap_penalty(trap_signal_active)
    risk_penalty = RISK_PENALTY_WEIGHT * (
        variance_penalty + regime_penalty + trap_penalty
    )

    # Uncertainty penalty: proportional to uncertainty × horizon
    u_penalty = _compute_uncertainty_penalty(uncertainty, horizon)

    # Step consistency
    consistency = _compute_step_consistency(step_values)

    trajectory_score = raw_score + stability_bonus - risk_penalty - u_penalty

    # Per-trajectory confidence from data quality, modulated by uncertainty
    data_quality = _clamp(
        (causal_count + credit_count) / (MIN_DATA_OBSERVATIONS * 4),
        0.0,
        1.0,
    )
    signal_agreement = 1.0 if signals_found == 2 else 0.5
    step_stability = 1.0 - _compute_variance_penalty(step_values)
    base_confidence = _clamp(
        0.3 * data_quality + 0.4 * signal_agreement + 0.3 * step_stability,
        0.0,
        1.0,
    )
    confidence = base_confidence * (1.0 - uncertainty)

    # Counterfactual risk: compute worst-case gap × irreversibility
    from umh.runtime_engine.risk_model import compute_counterfactual_risk as _cfr

    regime_active = bool(
        context_signal
        and (getattr(context_signal, "regime_change_likelihood", 0.0) or 0.0) > 0.05
    )
    cf_estimate = _cfr(
        action=action,
        expected_reward=raw_score,
        causal_stats=causal_stats,
        context_type=context,
        uncertainty=uncertainty,
        regime_active=regime_active,
        trap_signal_active=bool(trap_signal_active),
        recovery_history=recovery_history,
        confidence=confidence,
    )

    return TrajectoryResult(
        action=action,
        steps=tuple(steps),
        raw_score=raw_score,
        stability_bonus=stability_bonus,
        risk_penalty=risk_penalty,
        uncertainty_penalty=u_penalty,
        trajectory_score=trajectory_score,
        confidence=confidence,
        step_consistency=consistency,
        counterfactual_risk_score=cf_estimate.risk_score,
        worst_case_estimate=cf_estimate.worst_case_reward,
        irreversibility_factor=cf_estimate.irreversibility_factor,
        risk_adjusted_score=cf_estimate.risk_adjusted_score,
    )


# ─── Safety gating ─────────────────────────────────────────────────


def _check_gating(
    context_type: str | None,
    context_signal: object | None,
    trap_signal_active: bool | None,
    stability_guard_active: bool | None,
    causal_stats: dict | None,
    credit_accumulators: dict | None,
    uncertainty: float = 0.0,
) -> str | None:
    """Return a reason string if the planner should be gated off, else None."""
    if context_type != "stable":
        return f"context_not_stable:{context_type}"

    if uncertainty >= UNCERTAINTY_HIGH:
        return f"uncertainty_too_high:{uncertainty:.3f}"

    if trap_signal_active:
        return "trap_active"

    if stability_guard_active:
        return "stability_guard_active"

    # Check minimum data across at least one action
    has_causal = False
    if causal_stats and isinstance(causal_stats, dict):
        for stat in causal_stats.values():
            if (
                isinstance(stat, dict)
                and int(stat.get("count", 0)) >= MIN_DATA_OBSERVATIONS
            ):
                has_causal = True
                break

    has_credit = False
    if credit_accumulators and isinstance(credit_accumulators, dict):
        for acc in credit_accumulators.values():
            if (
                isinstance(acc, dict)
                and int(acc.get("observation_count", 0)) >= MIN_CREDIT_OBSERVATIONS
            ):
                has_credit = True
                break

    if not has_causal and not has_credit:
        return "insufficient_data"

    return None


# ─── Confidence model ──────────────────────────────────────────────


def _compute_planner_confidence(
    trajectories: list[TrajectoryResult],
    uncertainty: float,
) -> tuple[float, float, float]:
    """Compute planner confidence from trajectory agreement, margin, and uncertainty.

    Returns (raw_confidence, consistency, adjusted_confidence).

    adjusted_confidence = agreement × margin_factor × (1 - uncertainty)
    """
    if not trajectories:
        return 0.0, 1.0, 0.0

    scored = [t for t in trajectories if len(t.steps) > 0]
    if not scored:
        return 0.0, 1.0, 0.0

    # Agreement across steps: average step_consistency of all trajectories
    avg_consistency = sum(t.step_consistency for t in scored) / len(scored)

    # Trajectory margin: how separated is the best from the rest
    scores = sorted([t.trajectory_score for t in scored], reverse=True)
    if len(scores) >= 2:
        margin = scores[0] - scores[1]
        total_range = scores[0] - scores[-1] if scores[0] != scores[-1] else 1.0
        margin_factor = _clamp(margin / (abs(total_range) + 1e-9), 0.0, 1.0)
    else:
        margin_factor = 0.0

    raw_confidence = avg_consistency * margin_factor
    adjusted = raw_confidence * (1.0 - uncertainty)
    adjusted = _clamp(adjusted, 0.0, 1.0)

    return raw_confidence, avg_consistency, adjusted


# ─── Main entry point ──────────────────────────────────────────────


def evaluate_trajectories(
    candidate_actions: list[str],
    context_type: str | None,
    causal_stats: dict | None = None,
    credit_accumulators: dict | None = None,
    context_signal: object | None = None,
    trap_signal_active: bool | None = None,
    stability_guard_active: bool | None = None,
    strategy_scores: dict[str, float] | None = None,
    horizon: int | None = None,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    recovery_history: dict[str, float] | None = None,
) -> PlannerResult:
    """Evaluate candidate actions via bounded trajectory comparison.

    Returns an override recommendation only when adjusted confidence exceeds
    threshold. Otherwise returns inactive result — system falls back to base policy.

    When strategy_scores is provided, uncertainty is computed from the score
    distribution and used to adapt horizon and confidence.
    """
    if not candidate_actions:
        return NO_PLANNER_RESULT

    # Limit to top K candidates
    actions = candidate_actions[:MAX_CANDIDATES]

    # Compute uncertainty from score distribution
    uncertainty = compute_uncertainty(strategy_scores)

    # Adaptive horizon
    if horizon is not None:
        effective_horizon = _clamp_int(horizon, MIN_HORIZON, MAX_HORIZON)
    else:
        effective_horizon = compute_adaptive_horizon(uncertainty, context_type)

    # Safety gate check (now includes uncertainty)
    gate_reason = _check_gating(
        context_type=context_type,
        context_signal=context_signal,
        trap_signal_active=trap_signal_active,
        stability_guard_active=stability_guard_active,
        causal_stats=causal_stats,
        credit_accumulators=credit_accumulators,
        uncertainty=uncertainty,
    )
    if gate_reason is not None:
        return PlannerResult(
            active=False,
            selected_action_override=None,
            trajectory_scores={},
            planner_confidence=0.0,
            reason=f"gated:{gate_reason}",
            horizon_used=effective_horizon,
            uncertainty=uncertainty,
            consistency=0.0,
            adjusted_confidence=0.0,
        )

    # Simulate trajectories for each candidate
    trajectories: list[TrajectoryResult] = []
    for action in actions:
        traj = _simulate_trajectory(
            action=action,
            context=context_type or "stable",
            causal_stats=causal_stats,
            credit_accumulators=credit_accumulators,
            horizon=effective_horizon,
            uncertainty=uncertainty,
            context_signal=context_signal,
            trap_signal_active=trap_signal_active,
            recovery_history=recovery_history,
        )
        trajectories.append(traj)

    # Build score map
    scored = [t for t in trajectories if len(t.steps) > 0]
    if not scored:
        return PlannerResult(
            active=False,
            selected_action_override=None,
            trajectory_scores={},
            planner_confidence=0.0,
            reason="no_scorable_trajectories",
            horizon_used=effective_horizon,
            uncertainty=uncertainty,
            consistency=0.0,
            adjusted_confidence=0.0,
            trajectories=tuple(trajectories),
        )

    trajectory_scores = {t.action: t.trajectory_score for t in scored}

    # Counterfactual risk adjustment: prefer safer actions under uncertainty
    regime_active = bool(
        context_signal
        and (getattr(context_signal, "regime_change_likelihood", 0.0) or 0.0) > 0.05
    )
    risk_assessment = assess_actions(
        actions=[t.action for t in scored],
        expected_rewards=trajectory_scores,
        causal_stats=causal_stats,
        context_type=context_type or "stable",
        uncertainty=uncertainty,
        regime_active=regime_active,
        trap_signal_active=bool(trap_signal_active),
        recovery_history=recovery_history,
        confidences={t.action: t.confidence for t in scored},
    )
    trajectory_scores = apply_risk_adjustment(trajectory_scores, risk_assessment)

    # Compute uncertainty-aware confidence
    raw_confidence, consistency, adjusted_confidence = _compute_planner_confidence(
        scored, uncertainty
    )

    # Find best action
    best_action = max(trajectory_scores, key=trajectory_scores.get)  # type: ignore[arg-type]
    best_score = trajectory_scores[best_action]

    # Check score margin — override only if meaningfully better
    second_best = max(
        (s for a, s in trajectory_scores.items() if a != best_action),
        default=best_score,
    )
    margin = best_score - second_best

    # Exploration interplay: high uncertainty + close scores → defer to exploration
    if uncertainty > 0.5 and margin < EXPLORATION_PROXIMITY_THRESHOLD:
        return PlannerResult(
            active=False,
            selected_action_override=None,
            trajectory_scores=trajectory_scores,
            planner_confidence=raw_confidence,
            reason=f"defer_to_exploration:uncertainty={uncertainty:.3f},margin={margin:.4f}",
            horizon_used=effective_horizon,
            uncertainty=uncertainty,
            consistency=consistency,
            adjusted_confidence=adjusted_confidence,
            trajectories=tuple(trajectories),
        )

    # Confidence gate (uses adjusted confidence, not raw)
    if adjusted_confidence < confidence_threshold:
        return PlannerResult(
            active=False,
            selected_action_override=None,
            trajectory_scores=trajectory_scores,
            planner_confidence=raw_confidence,
            reason=f"confidence_below_threshold:{adjusted_confidence:.3f}<{confidence_threshold}",
            horizon_used=effective_horizon,
            uncertainty=uncertainty,
            consistency=consistency,
            adjusted_confidence=adjusted_confidence,
            trajectories=tuple(trajectories),
        )

    # Margin gate — don't override if actions are essentially tied
    if margin < SCORE_MARGIN_THRESHOLD:
        return PlannerResult(
            active=False,
            selected_action_override=None,
            trajectory_scores=trajectory_scores,
            planner_confidence=raw_confidence,
            reason=f"insufficient_margin:{margin:.4f}",
            horizon_used=effective_horizon,
            uncertainty=uncertainty,
            consistency=consistency,
            adjusted_confidence=adjusted_confidence,
            trajectories=tuple(trajectories),
        )

    # Consistency check: if best trajectory has poor step consistency, reduce confidence
    best_traj = next(t for t in scored if t.action == best_action)
    if best_traj.step_consistency < 0.5:
        penalized_confidence = adjusted_confidence * (
            1.0 - CONSISTENCY_PENALTY_SCALE * (1.0 - best_traj.step_consistency)
        )
        if penalized_confidence < confidence_threshold:
            return PlannerResult(
                active=False,
                selected_action_override=None,
                trajectory_scores=trajectory_scores,
                planner_confidence=raw_confidence,
                reason=f"inconsistent_trajectory:{best_traj.step_consistency:.3f}",
                horizon_used=effective_horizon,
                uncertainty=uncertainty,
                consistency=consistency,
                adjusted_confidence=penalized_confidence,
                trajectories=tuple(trajectories),
            )
        adjusted_confidence = penalized_confidence

    return PlannerResult(
        active=True,
        selected_action_override=best_action,
        trajectory_scores=trajectory_scores,
        planner_confidence=raw_confidence,
        reason="trajectory_selected",
        horizon_used=effective_horizon,
        uncertainty=uncertainty,
        consistency=consistency,
        adjusted_confidence=adjusted_confidence,
        trajectories=tuple(trajectories),
    )


# ─── Pipeline integration ──────────────────────────────────────────


def apply_planner_override(
    strategy_scores: dict[str, float],
    planner_result: PlannerResult,
) -> dict[str, float]:
    """Apply planner override to strategy scores if active.

    When the planner selects an action, boosts it to be the clear leader.
    Does NOT modify scores if planner is inactive.
    """
    if not planner_result.active or not planner_result.selected_action_override:
        return strategy_scores

    if not strategy_scores:
        return strategy_scores

    override_action = planner_result.selected_action_override
    if override_action not in strategy_scores:
        return strategy_scores

    current_max = max(strategy_scores.values())
    current_override_score = strategy_scores[override_action]

    if current_override_score >= current_max:
        return strategy_scores

    # Boost the selected action to lead by a small margin
    boost_margin = 0.02
    adjusted = dict(strategy_scores)
    adjusted[override_action] = current_max + boost_margin

    return adjusted
