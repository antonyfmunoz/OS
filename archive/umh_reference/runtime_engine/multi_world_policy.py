"""MultiWorldPolicy — robust action selection across world variations.

Upgrades simulation from single-path optimization to robust decision-making.
Each candidate action is simulated across K slightly different world models,
and scored for robustness: stability across variations, not peak performance
in one scenario.

All logic is deterministic, bounded, and domain-agnostic.
No recursion. No randomness. No tree search. No LLM calls.
Branching is linear: K worlds × N actions.
"""

from __future__ import annotations

from dataclasses import dataclass

from umh.runtime_engine.objective_arbitration import (
    DEFAULT_WEIGHTS,
    ObjectiveWeights,
    compute_weighted_score,
)
from umh.world.dynamics_adapter import DynamicsAdjustment, NEUTRAL_ADJUSTMENT
from umh.world.simulation import (
    SimulatedAction,
    SimulationResult,
    WorldSimulationEngine,
)
from umh.world.reasoning import WorldUnderstanding
from umh.world.types import Observation, WorldSnapshot

# ─── Constants ───────────────────────────────────────────────────

MAX_WORLDS = 5
MAX_POLICY_ACTIONS = 5

LAMBDA_VARIANCE = 0.2
LAMBDA_DOWNSIDE = 0.3
LAMBDA_RISK = 0.2

TREND_VARIATION_SCALE = 0.10
RISK_VARIATION_SCALE = 0.10
STABILITY_VARIATION_SCALE = 0.10
NOISE_MAGNITUDE = 0.03

MIN_UNCERTAINTY_FOR_POLICY = 0.5
MIN_SIMULATION_HORIZON = 2


# ─── Data models ─────────────────────────────────────────────────


@dataclass(frozen=True)
class WorldVariation:
    """One perturbed world configuration."""

    variation_id: int
    adjustment: DynamicsAdjustment
    label: str

    def to_dict(self) -> dict:
        return {
            "variation_id": self.variation_id,
            "adjustment": self.adjustment.to_dict(),
            "label": self.label,
        }


@dataclass(frozen=True)
class ActionWorldScore:
    """Score for one action in one world variation."""

    action_id: str
    variation_id: int
    improvement: float
    risk: float
    confidence: float
    net_score: float

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "variation_id": self.variation_id,
            "improvement": round(self.improvement, 6),
            "risk": round(self.risk, 6),
            "confidence": round(self.confidence, 6),
            "net_score": round(self.net_score, 6),
        }


@dataclass(frozen=True)
class PolicyEvaluation:
    """Robust evaluation of one action across all world variations."""

    action_id: str
    world_scores: tuple[ActionWorldScore, ...]
    mean_score: float
    worst_case: float
    variance: float
    robust_score: float
    world_count: int

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "mean_score": round(self.mean_score, 6),
            "worst_case": round(self.worst_case, 6),
            "variance": round(self.variance, 6),
            "robust_score": round(self.robust_score, 6),
            "world_count": self.world_count,
        }


@dataclass(frozen=True)
class MultiWorldPolicyResult:
    """Complete result of multi-world policy evaluation."""

    active: bool
    evaluations: tuple[PolicyEvaluation, ...]
    selected_action_id: str | None
    selected_robust_score: float
    world_count: int
    reason: str

    def to_dict(self) -> dict:
        return {
            "active": self.active,
            "selected_action_id": self.selected_action_id,
            "selected_robust_score": round(self.selected_robust_score, 6),
            "world_count": self.world_count,
            "reason": self.reason,
            "evaluations": [e.to_dict() for e in self.evaluations],
        }


NO_POLICY_RESULT = MultiWorldPolicyResult(
    active=False,
    evaluations=(),
    selected_action_id=None,
    selected_robust_score=0.0,
    world_count=0,
    reason="policy_inactive",
)


# ─── Deterministic noise ────────────────────────────────────────


def _deterministic_offset(action_id: str, variation_id: int) -> float:
    h = hash((action_id, variation_id))
    normalized = ((h % 10000) / 10000.0) * 2.0 - 1.0
    return normalized * NOISE_MAGNITUDE


# ─── World variation generation ─────────────────────────────────


def generate_world_variations(
    base_adjustment: DynamicsAdjustment | None = None,
) -> tuple[WorldVariation, ...]:
    """Generate K bounded world variations around the base adjustment.

    Variations:
    0: baseline (no perturbation)
    1: trend +10%
    2: trend -10%
    3: risk +10%, stability +10%
    4: risk -10%, stability -10%
    """
    base = base_adjustment or NEUTRAL_ADJUSTMENT

    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    variations: list[WorldVariation] = []

    variations.append(
        WorldVariation(
            variation_id=0,
            adjustment=base,
            label="baseline",
        )
    )

    variations.append(
        WorldVariation(
            variation_id=1,
            adjustment=DynamicsAdjustment(
                trend_multiplier=_clamp(
                    base.trend_multiplier * (1.0 + TREND_VARIATION_SCALE), 0.5, 1.5
                ),
                risk_multiplier=base.risk_multiplier,
                stability_decay_modifier=base.stability_decay_modifier,
                confidence_scale=base.confidence_scale,
            ),
            label="trend_up",
        )
    )

    variations.append(
        WorldVariation(
            variation_id=2,
            adjustment=DynamicsAdjustment(
                trend_multiplier=_clamp(
                    base.trend_multiplier * (1.0 - TREND_VARIATION_SCALE), 0.5, 1.5
                ),
                risk_multiplier=base.risk_multiplier,
                stability_decay_modifier=base.stability_decay_modifier,
                confidence_scale=base.confidence_scale,
            ),
            label="trend_down",
        )
    )

    variations.append(
        WorldVariation(
            variation_id=3,
            adjustment=DynamicsAdjustment(
                trend_multiplier=base.trend_multiplier,
                risk_multiplier=_clamp(
                    base.risk_multiplier * (1.0 + RISK_VARIATION_SCALE), 0.5, 1.5
                ),
                stability_decay_modifier=_clamp(
                    base.stability_decay_modifier + STABILITY_VARIATION_SCALE * 0.02,
                    -0.05,
                    0.05,
                ),
                confidence_scale=base.confidence_scale,
            ),
            label="risk_up_stability_up",
        )
    )

    variations.append(
        WorldVariation(
            variation_id=4,
            adjustment=DynamicsAdjustment(
                trend_multiplier=base.trend_multiplier,
                risk_multiplier=_clamp(
                    base.risk_multiplier * (1.0 - RISK_VARIATION_SCALE), 0.5, 1.5
                ),
                stability_decay_modifier=_clamp(
                    base.stability_decay_modifier - STABILITY_VARIATION_SCALE * 0.02,
                    -0.05,
                    0.05,
                ),
                confidence_scale=base.confidence_scale,
            ),
            label="risk_down_stability_down",
        )
    )

    return tuple(variations)


# ─── Policy evaluation ──────────────────────────────────────────


def evaluate_action_across_worlds(
    action: SimulatedAction,
    snapshot: WorldSnapshot,
    understanding: WorldUnderstanding,
    variations: tuple[WorldVariation, ...],
    horizon: int = 3,
    observation_history: tuple[Observation, ...] | None = None,
    objective_weights: ObjectiveWeights | None = None,
) -> PolicyEvaluation:
    """Simulate one action across all world variations and compute robust score."""
    engine = WorldSimulationEngine()
    scores: list[ActionWorldScore] = []
    weights = objective_weights or DEFAULT_WEIGHTS

    for var in variations:
        noise = _deterministic_offset(action.action_id, var.variation_id)

        result = engine.simulate_action(
            snapshot=snapshot,
            understanding=understanding,
            action=action,
            horizon=horizon,
            observation_history=observation_history,
            adjustment=var.adjustment,
        )

        net = (
            compute_weighted_score(
                weights=weights,
                improvement=result.aggregate_improvement,
                risk=result.aggregate_risk,
            )
            + noise
        )

        scores.append(
            ActionWorldScore(
                action_id=action.action_id,
                variation_id=var.variation_id,
                improvement=result.aggregate_improvement,
                risk=result.aggregate_risk,
                confidence=result.confidence,
                net_score=net,
            )
        )

    net_scores = [s.net_score for s in scores]
    n = len(net_scores)
    mean_score = sum(net_scores) / n if n > 0 else 0.0
    worst_case = min(net_scores) if net_scores else 0.0

    if n > 1:
        variance = sum((s - mean_score) ** 2 for s in net_scores) / n
    else:
        variance = 0.0

    avg_risk = sum(s.risk for s in scores) / n if n > 0 else 0.0

    robust = (
        mean_score
        - LAMBDA_VARIANCE * variance
        - LAMBDA_DOWNSIDE * (mean_score - worst_case)
        - LAMBDA_RISK * avg_risk
    )

    return PolicyEvaluation(
        action_id=action.action_id,
        world_scores=tuple(scores),
        mean_score=mean_score,
        worst_case=worst_case,
        variance=variance,
        robust_score=robust,
        world_count=n,
    )


# ─── Safety gating ──────────────────────────────────────────────


def check_policy_gating(
    context_type: str | None,
    uncertainty: float,
    horizon: int,
) -> str | None:
    """Return a reason string if policy evaluation should be skipped."""
    if context_type != "stable":
        return f"context_not_stable:{context_type}"
    if uncertainty >= MIN_UNCERTAINTY_FOR_POLICY:
        return f"uncertainty_too_high:{uncertainty:.3f}"
    if horizon < MIN_SIMULATION_HORIZON:
        return f"horizon_too_shallow:{horizon}"
    return None


# ─── Main entry point ───────────────────────────────────────────


def evaluate_multi_world_policy(
    actions: tuple[SimulatedAction, ...],
    snapshot: WorldSnapshot,
    understanding: WorldUnderstanding,
    base_adjustment: DynamicsAdjustment | None = None,
    horizon: int = 3,
    observation_history: tuple[Observation, ...] | None = None,
    context_type: str | None = None,
    uncertainty: float = 0.0,
    objective_weights: ObjectiveWeights | None = None,
) -> MultiWorldPolicyResult:
    """Evaluate actions across multiple world variations for robust selection.

    When gating conditions are not met, returns NO_POLICY_RESULT and
    the caller falls back to single-world simulation.
    """
    if not actions:
        return NO_POLICY_RESULT

    gate_reason = check_policy_gating(context_type, uncertainty, horizon)
    if gate_reason is not None:
        return MultiWorldPolicyResult(
            active=False,
            evaluations=(),
            selected_action_id=None,
            selected_robust_score=0.0,
            world_count=0,
            reason=f"gated:{gate_reason}",
        )

    capped = actions[:MAX_POLICY_ACTIONS]
    variations = generate_world_variations(base_adjustment)

    evaluations: list[PolicyEvaluation] = []
    for action in capped:
        ev = evaluate_action_across_worlds(
            action=action,
            snapshot=snapshot,
            understanding=understanding,
            variations=variations,
            horizon=horizon,
            observation_history=observation_history,
            objective_weights=objective_weights,
        )
        evaluations.append(ev)

    if not evaluations:
        return NO_POLICY_RESULT

    best = max(evaluations, key=lambda e: e.robust_score)

    return MultiWorldPolicyResult(
        active=True,
        evaluations=tuple(evaluations),
        selected_action_id=best.action_id,
        selected_robust_score=best.robust_score,
        world_count=len(variations),
        reason="robust_selection",
    )
