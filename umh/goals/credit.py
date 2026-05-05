"""ExecutionCredit — deterministic credit assignment and policy learning.

Translates ExecutionFeedback into structured learning signals that
influence future decisions through strategy memory, objective
arbitration, and multi-world policy — without breaking determinism,
safety, or architecture purity.

This is NOT RL. This is NOT stochastic training.
This IS: deterministic credit assignment, outcome attribution,
and bounded policy bias shaping.

Pipeline position:
    ExecutionFeedback → CreditAssignment → PolicyLearningSignal
    → StrategyPatternMemory (record_execution_credit)
    → ObjectiveArbiter (bounded weight nudge)
    → MultiWorldPolicy (risk penalty shaping)

All biases are:
    - bounded: [-0.05, +0.05]
    - additive
    - slow-changing

Unknown outcomes → zero learning. Always.

Usage::

    from umh.goals.credit import (
        compute_credit_assignment,
        credit_to_learning_signal,
        apply_learning_signal,
    )

    credit = compute_credit_assignment(action, feedback, trace)
    signal = credit_to_learning_signal(credit)
    apply_learning_signal(signal, strategy_memory, arbiter)
"""

from __future__ import annotations

from dataclasses import dataclass


# ─── Constants ────────────────────────────────────────────────────

BASE_CREDIT_MAP: dict[str, float] = {
    "success": 1.0,
    "failure": -1.0,
    "partial": 0.2,
    "unknown": 0.0,
}

BIAS_BOUND = 0.05
BIAS_SCALE = 0.03

MIN_CONFIDENCE_FOR_LEARNING = 0.2

ATTRIBUTION_UNCERTAINTY_PENALTY = 0.6
ATTRIBUTION_SYNTHESIS_PENALTY = 0.7
ATTRIBUTION_EXPLORATION_PENALTY = 0.7
ATTRIBUTION_META_CONTROL_PENALTY = 0.8


# ─── Data models ─────────────────────────────────────────────────


@dataclass(frozen=True)
class CreditAssignment:
    """Structured credit for a single execution outcome."""

    action_id: str
    outcome_type: str
    credit_score: float  # [-1, 1]
    confidence: float  # [0, 1]
    attribution: float  # [0, 1]
    effective_credit: float  # credit_score * attribution * confidence
    reason: str

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "outcome_type": self.outcome_type,
            "credit_score": round(self.credit_score, 4),
            "confidence": round(self.confidence, 4),
            "attribution": round(self.attribution, 4),
            "effective_credit": round(self.effective_credit, 4),
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CreditAssignment:
        return cls(
            action_id=d["action_id"],
            outcome_type=d["outcome_type"],
            credit_score=d["credit_score"],
            confidence=d["confidence"],
            attribution=d["attribution"],
            effective_credit=d["effective_credit"],
            reason=d["reason"],
        )


@dataclass(frozen=True)
class PolicyLearningSignal:
    """Bounded bias adjustments for policy layers."""

    action_id: str
    reward_bias: float  # [-0.05, +0.05]
    risk_bias: float  # [-0.05, +0.05]
    stability_bias: float  # [-0.05, +0.05]
    confidence: float  # [0, 1]
    source: str  # always "execution_credit"

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "reward_bias": round(self.reward_bias, 6),
            "risk_bias": round(self.risk_bias, 6),
            "stability_bias": round(self.stability_bias, 6),
            "confidence": round(self.confidence, 4),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> PolicyLearningSignal:
        return cls(
            action_id=d["action_id"],
            reward_bias=d["reward_bias"],
            risk_bias=d["risk_bias"],
            stability_bias=d["stability_bias"],
            confidence=d["confidence"],
            source=d.get("source", "execution_credit"),
        )


@dataclass(frozen=True)
class CreditComputationResult:
    """Combined output from full credit computation pipeline."""

    credit: CreditAssignment
    learning_signal: PolicyLearningSignal
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "credit": self.credit.to_dict(),
            "learning_signal": self.learning_signal.to_dict(),
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, d: dict) -> CreditComputationResult:
        return cls(
            credit=CreditAssignment.from_dict(d["credit"]),
            learning_signal=PolicyLearningSignal.from_dict(d["learning_signal"]),
            warnings=tuple(d.get("warnings", ())),
        )


# ─── Attribution computation ─────────────────────────────────────


def _compute_attribution(
    outcome_type: str,
    trace: object | None,
) -> float:
    """Compute how much of the outcome is attributable to the decision.

    Starts at 1.0, reduces for conditions that weaken causal link.
    Unknown outcomes always get 0.0 — we refuse to attribute ambiguity.
    """
    if outcome_type == "unknown":
        return 0.0

    attribution = 1.0

    if trace is not None:
        planner_uncertainty = getattr(trace, "planner_uncertainty", None)
        if planner_uncertainty is not None and planner_uncertainty > 0.5:
            attribution *= ATTRIBUTION_UNCERTAINTY_PENALTY

        synthesized = getattr(trace, "synthesized_strategy", None)
        if synthesized is not None:
            attribution *= ATTRIBUTION_SYNTHESIS_PENALTY

        exploration_rate = getattr(trace, "exploration_rate", None)
        if exploration_rate is not None and exploration_rate > 0.3:
            attribution *= ATTRIBUTION_EXPLORATION_PENALTY

        mc_mode = getattr(trace, "meta_control_mode", None)
        if mc_mode is not None and mc_mode != "full":
            attribution *= ATTRIBUTION_META_CONTROL_PENALTY

    return max(0.0, min(1.0, attribution))


# ─── Credit assignment ────────────────────────────────────────────


def compute_credit_assignment(
    action: object,
    feedback: object,
    trace: object | None = None,
) -> CreditAssignment:
    """Compute deterministic credit assignment for an execution outcome.

    Args:
        action: ExecutableAction (or any object with .confidence).
        feedback: ExecutionFeedback (or any object with .outcome_type, .signal_strength, .action_id).
        trace: DecisionTrace from the turn that produced this action.

    Returns:
        CreditAssignment with bounded effective_credit in [-1, 1].
    """
    action_id = getattr(feedback, "action_id", "") or getattr(action, "action_id", "")
    outcome_type = getattr(feedback, "outcome_type", "unknown")
    signal_strength = getattr(feedback, "signal_strength", 0.0)
    action_confidence = getattr(action, "confidence", 0.5)

    base_credit = BASE_CREDIT_MAP.get(outcome_type, 0.0)

    _ac = action_confidence if action_confidence is not None else 0.5
    _ac = max(0.0, min(1.0, _ac))
    _ss = abs(signal_strength) if signal_strength is not None else 0.0
    _ss = max(0.0, min(1.0, _ss))
    confidence = (_ac + _ss) / 2.0

    attribution = _compute_attribution(outcome_type, trace)

    effective_credit = base_credit * attribution * confidence
    effective_credit = max(-1.0, min(1.0, effective_credit))

    reason = _build_reason(outcome_type, attribution, confidence)

    return CreditAssignment(
        action_id=action_id,
        outcome_type=outcome_type,
        credit_score=base_credit,
        confidence=confidence,
        attribution=attribution,
        effective_credit=effective_credit,
        reason=reason,
    )


def _build_reason(outcome_type: str, attribution: float, confidence: float) -> str:
    if outcome_type == "unknown":
        return "unknown outcome — no attribution"

    attr_label = "high" if attribution > 0.7 else "moderate" if attribution > 0.3 else "low"
    conf_label = "high" if confidence > 0.7 else "moderate" if confidence > 0.3 else "low"

    return f"{outcome_type} with {attr_label} attribution under {conf_label} confidence"


# ─── Learning signal generation ───────────────────────────────────


def _clamp_bias(v: float) -> float:
    return max(-BIAS_BOUND, min(BIAS_BOUND, v))


def credit_to_learning_signal(
    credit: CreditAssignment,
    trace: object | None = None,
) -> PolicyLearningSignal:
    """Convert credit assignment into bounded policy bias adjustments.

    All biases are clamped to [-0.05, +0.05]. Low-confidence signals
    produce near-zero bias. Unknown outcomes produce zero everywhere.
    """
    ec = credit.effective_credit

    if credit.outcome_type == "unknown" or credit.confidence < MIN_CONFIDENCE_FOR_LEARNING:
        return PolicyLearningSignal(
            action_id=credit.action_id,
            reward_bias=0.0,
            risk_bias=0.0,
            stability_bias=0.0,
            confidence=credit.confidence,
            source="execution_credit",
        )

    reward_bias = _clamp_bias(ec * BIAS_SCALE)

    if credit.outcome_type == "failure":
        risk_bias = _clamp_bias(abs(ec) * BIAS_SCALE)
    elif credit.outcome_type == "success":
        risk_bias = _clamp_bias(-abs(ec) * BIAS_SCALE * 0.3)
    else:
        risk_bias = 0.0

    stability_bias = 0.0
    if trace is not None:
        mc_instability = getattr(trace, "meta_control_instability", None)
        if credit.outcome_type == "failure" and mc_instability is not None and mc_instability > 0.3:
            stability_bias = _clamp_bias(abs(ec) * BIAS_SCALE * 0.5)
        elif credit.outcome_type == "success":
            stability_bias = _clamp_bias(abs(ec) * BIAS_SCALE * 0.2)

    return PolicyLearningSignal(
        action_id=credit.action_id,
        reward_bias=reward_bias,
        risk_bias=risk_bias,
        stability_bias=stability_bias,
        confidence=credit.confidence,
        source="execution_credit",
    )


# ─── Integration: apply to downstream systems ────────────────────


def apply_credit_to_strategy_memory(
    credit: CreditAssignment,
    strategy_memory: object,
    selected_strategy: str = "",
) -> bool:
    """Record execution credit in strategy pattern memory.

    Uses the existing apply_outcome() method to adjust EMA
    without incrementing turn/use counters.

    Returns True if credit was applied, False if skipped.
    """
    if credit.outcome_type == "unknown":
        return False
    if credit.confidence < MIN_CONFIDENCE_FOR_LEARNING:
        return False
    if not selected_strategy:
        return False

    apply_fn = getattr(strategy_memory, "apply_outcome", None)
    if apply_fn is None:
        return False

    try:
        apply_fn(
            strategy_name=selected_strategy,
            adjusted_score=credit.effective_credit,
            outcome_confidence=credit.confidence,
        )
        return True
    except Exception:
        return False


def apply_signal_to_arbiter(
    signal: PolicyLearningSignal,
    arbiter: object,
) -> bool:
    """Apply bounded learning signal to objective arbiter weights.

    Only applies when confidence exceeds threshold. Adjustments are
    additive and clamped — the arbiter's own bounds still apply.

    Returns True if applied, False if skipped.
    """
    if signal.confidence < MIN_CONFIDENCE_FOR_LEARNING:
        return False
    if signal.reward_bias == 0.0 and signal.risk_bias == 0.0 and signal.stability_bias == 0.0:
        return False

    weights = getattr(arbiter, "_weights", None)
    if weights is None:
        return False

    try:
        from umh.objectives.arbitration import ObjectiveWeights, _clamp_weights

        new_weights = ObjectiveWeights(
            reward_weight=weights.reward_weight + signal.reward_bias,
            risk_weight=weights.risk_weight + signal.risk_bias,
            stability_weight=weights.stability_weight + signal.stability_bias,
            exploration_weight=weights.exploration_weight,
            novelty_weight=weights.novelty_weight,
        )
        arbiter._weights = _clamp_weights(new_weights)
        return True
    except Exception:
        return False


def compute_risk_penalty_adjustment(
    credit: CreditAssignment,
) -> float:
    """Compute a risk penalty adjustment for multi-world policy.

    Repeated failures increase risk penalty, successes slightly reduce it.
    Returns a bounded adjustment to be applied to LAMBDA_RISK.
    """
    if credit.outcome_type == "unknown":
        return 0.0
    if credit.confidence < MIN_CONFIDENCE_FOR_LEARNING:
        return 0.0

    if credit.outcome_type == "failure":
        return _clamp_bias(abs(credit.effective_credit) * BIAS_SCALE)
    elif credit.outcome_type == "success":
        return _clamp_bias(-abs(credit.effective_credit) * BIAS_SCALE * 0.2)

    return 0.0


# ─── Combined pipeline ───────────────────────────────────────────


def compute_full_credit(
    action: object,
    feedback: object,
    trace: object | None = None,
) -> CreditComputationResult:
    """Full credit computation pipeline: credit + learning signal.

    Equivalent to compute_credit_assignment() + credit_to_learning_signal().
    """
    warnings: list[str] = []

    credit = compute_credit_assignment(action, feedback, trace)

    if credit.outcome_type == "unknown":
        warnings.append("unknown outcome — zero learning applied")

    if credit.confidence < MIN_CONFIDENCE_FOR_LEARNING:
        warnings.append(
            f"confidence {credit.confidence:.3f} below threshold "
            f"{MIN_CONFIDENCE_FOR_LEARNING} — near-zero learning"
        )

    signal = credit_to_learning_signal(credit, trace)

    return CreditComputationResult(
        credit=credit,
        learning_signal=signal,
        warnings=tuple(warnings),
    )


if __name__ == "__main__":
    print("execution_credit import OK")
