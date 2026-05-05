"""ObjectiveArbitration — dynamic objective weighting based on context.

Decouples "what to optimize" from "how to optimize". Different environments
require different priorities: stable growth favors reward, adversarial
conditions favor risk avoidance, plateaus favor novelty and exploration.

The arbiter detects context and smoothly shifts objective weights using EMA,
preventing abrupt flips. All logic is deterministic, bounded, and stateless
beyond the current weight vector.

No LLM calls. No randomness. No recursion.
"""

from __future__ import annotations

from dataclasses import dataclass


# ─── Weight bounds ──────────────────────────────────────────────

REWARD_WEIGHT_MIN = 0.3
REWARD_WEIGHT_MAX = 0.7
RISK_WEIGHT_MIN = 0.1
RISK_WEIGHT_MAX = 0.5
STABILITY_WEIGHT_MIN = 0.1
STABILITY_WEIGHT_MAX = 0.5
EXPLORATION_WEIGHT_MIN = 0.0
EXPLORATION_WEIGHT_MAX = 0.3
NOVELTY_WEIGHT_MIN = 0.0
NOVELTY_WEIGHT_MAX = 0.2

EMA_ALPHA = 0.1

MIN_CONFIDENCE_FOR_ARBITRATION = 0.3


# ─── Objective modes ───────────────────────────────────────────

VALID_MODES = ("default", "stable", "adversarial", "high_uncertainty", "plateau")


# ─── Data models ───────────────────────────────────────────────


@dataclass(frozen=True)
class ObjectiveWeights:
    """Bounded objective weight vector."""

    reward_weight: float
    risk_weight: float
    stability_weight: float
    exploration_weight: float
    novelty_weight: float

    def to_dict(self) -> dict:
        return {
            "reward_weight": round(self.reward_weight, 6),
            "risk_weight": round(self.risk_weight, 6),
            "stability_weight": round(self.stability_weight, 6),
            "exploration_weight": round(self.exploration_weight, 6),
            "novelty_weight": round(self.novelty_weight, 6),
        }


@dataclass(frozen=True)
class ArbitrationResult:
    """Output of the objective arbitration layer."""

    active: bool
    mode: str
    weights: ObjectiveWeights
    shift_reason: str
    confidence: float

    def to_dict(self) -> dict:
        return {
            "active": self.active,
            "mode": self.mode,
            "weights": self.weights.to_dict(),
            "shift_reason": self.shift_reason,
            "confidence": round(self.confidence, 6),
        }


# ─── Default weights ──────────────────────────────────────────

DEFAULT_WEIGHTS = ObjectiveWeights(
    reward_weight=0.5,
    risk_weight=0.3,
    stability_weight=0.3,
    exploration_weight=0.0,
    novelty_weight=0.0,
)


# ─── Context signals ──────────────────────────────────────────


@dataclass(frozen=True)
class ContextSignals:
    """Inputs from world state used to determine objective mode."""

    context_type: str | None = None
    uncertainty: float = 0.0
    calibration_error: float = 0.0
    risk_level: float = 0.0
    improvement_trend: float = 0.0
    exploration_stagnation: float = 0.0

    def to_dict(self) -> dict:
        return {
            "context_type": self.context_type,
            "uncertainty": round(self.uncertainty, 6),
            "calibration_error": round(self.calibration_error, 6),
            "risk_level": round(self.risk_level, 6),
            "improvement_trend": round(self.improvement_trend, 6),
            "exploration_stagnation": round(self.exploration_stagnation, 6),
        }


# ─── Clamping ─────────────────────────────────────────────────


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _clamp_weights(w: ObjectiveWeights) -> ObjectiveWeights:
    return ObjectiveWeights(
        reward_weight=_clamp(w.reward_weight, REWARD_WEIGHT_MIN, REWARD_WEIGHT_MAX),
        risk_weight=_clamp(w.risk_weight, RISK_WEIGHT_MIN, RISK_WEIGHT_MAX),
        stability_weight=_clamp(
            w.stability_weight, STABILITY_WEIGHT_MIN, STABILITY_WEIGHT_MAX
        ),
        exploration_weight=_clamp(
            w.exploration_weight, EXPLORATION_WEIGHT_MIN, EXPLORATION_WEIGHT_MAX
        ),
        novelty_weight=_clamp(w.novelty_weight, NOVELTY_WEIGHT_MIN, NOVELTY_WEIGHT_MAX),
    )


# ─── Mode detection ───────────────────────────────────────────


def detect_objective_mode(signals: ContextSignals) -> str:
    """Determine the objective mode from context signals.

    Priority order: adversarial > high_uncertainty > plateau > stable > default.
    """
    if signals.context_type == "adversarial" or signals.risk_level > 0.7:
        return "adversarial"

    if signals.uncertainty > 0.6 or signals.context_type == "volatile":
        return "high_uncertainty"

    if signals.exploration_stagnation > 0.5 and signals.improvement_trend < 0.1:
        return "plateau"

    if signals.context_type == "stable" and signals.uncertainty < 0.3:
        return "stable"

    return "default"


# ─── Policy: target weights per mode ──────────────────────────

_MODE_TARGETS: dict[str, ObjectiveWeights] = {
    "default": DEFAULT_WEIGHTS,
    "stable": ObjectiveWeights(
        reward_weight=0.65,
        risk_weight=0.15,
        stability_weight=0.2,
        exploration_weight=0.05,
        novelty_weight=0.0,
    ),
    "adversarial": ObjectiveWeights(
        reward_weight=0.35,
        risk_weight=0.45,
        stability_weight=0.45,
        exploration_weight=0.0,
        novelty_weight=0.0,
    ),
    "high_uncertainty": ObjectiveWeights(
        reward_weight=0.4,
        risk_weight=0.25,
        stability_weight=0.4,
        exploration_weight=0.25,
        novelty_weight=0.05,
    ),
    "plateau": ObjectiveWeights(
        reward_weight=0.4,
        risk_weight=0.2,
        stability_weight=0.2,
        exploration_weight=0.2,
        novelty_weight=0.15,
    ),
}


def get_target_weights(mode: str) -> ObjectiveWeights:
    """Return the target weight vector for a given objective mode."""
    return _MODE_TARGETS.get(mode, DEFAULT_WEIGHTS)


# ─── EMA smoothing ────────────────────────────────────────────


def smooth_weights(
    prev: ObjectiveWeights,
    target: ObjectiveWeights,
    alpha: float = EMA_ALPHA,
) -> ObjectiveWeights:
    """EMA blend from previous weights toward target weights."""
    return _clamp_weights(
        ObjectiveWeights(
            reward_weight=(1.0 - alpha) * prev.reward_weight
            + alpha * target.reward_weight,
            risk_weight=(1.0 - alpha) * prev.risk_weight + alpha * target.risk_weight,
            stability_weight=(1.0 - alpha) * prev.stability_weight
            + alpha * target.stability_weight,
            exploration_weight=(1.0 - alpha) * prev.exploration_weight
            + alpha * target.exploration_weight,
            novelty_weight=(1.0 - alpha) * prev.novelty_weight
            + alpha * target.novelty_weight,
        )
    )


# ─── Scoring functions ────────────────────────────────────────


def compute_weighted_score(
    weights: ObjectiveWeights,
    improvement: float,
    risk: float,
    stability: float = 0.0,
    exploration_bonus: float = 0.0,
    novelty_bonus: float = 0.0,
) -> float:
    """Compute the objective-weighted score for an action.

    Replaces the static: improvement - risk
    With:    reward_weight * improvement
           - risk_weight * risk
           + stability_weight * stability
           + exploration_weight * exploration_bonus
           + novelty_weight * novelty_bonus
    """
    return (
        weights.reward_weight * improvement
        - weights.risk_weight * risk
        + weights.stability_weight * stability
        + weights.exploration_weight * exploration_bonus
        + weights.novelty_weight * novelty_bonus
    )


# ─── Arbiter engine ───────────────────────────────────────────


class ObjectiveArbiter:
    """Stateful objective weight manager with EMA smoothing.

    Maintains current weights and smoothly transitions toward
    target weights determined by context signals.
    """

    def __init__(self) -> None:
        self._weights: ObjectiveWeights = DEFAULT_WEIGHTS
        self._mode: str = "default"
        self._update_count: int = 0

    @property
    def weights(self) -> ObjectiveWeights:
        return self._weights

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def update_count(self) -> int:
        return self._update_count

    def update(
        self,
        signals: ContextSignals,
        confidence: float = 1.0,
    ) -> ArbitrationResult:
        """Update objective weights based on context signals.

        Returns an ArbitrationResult describing the new state.
        When confidence is below threshold, returns inactive result
        with default weights preserved.
        """
        if confidence < MIN_CONFIDENCE_FOR_ARBITRATION:
            return ArbitrationResult(
                active=False,
                mode=self._mode,
                weights=self._weights,
                shift_reason=f"confidence_too_low:{confidence:.3f}",
                confidence=confidence,
            )

        new_mode = detect_objective_mode(signals)
        target = get_target_weights(new_mode)
        new_weights = smooth_weights(self._weights, target)

        old_mode = self._mode
        self._weights = new_weights
        self._mode = new_mode
        self._update_count += 1

        if new_mode != old_mode:
            reason = f"mode_shift:{old_mode}->{new_mode}"
        else:
            reason = f"mode_sustained:{new_mode}"

        return ArbitrationResult(
            active=True,
            mode=new_mode,
            weights=new_weights,
            shift_reason=reason,
            confidence=confidence,
        )

    def apply_execution_credit_bias(
        self,
        reward_bias: float,
        risk_bias: float,
        stability_bias: float,
    ) -> bool:
        """Apply bounded execution credit bias to objective weights.

        All biases are additive and clamped by _clamp_weights.
        Returns True if any weight changed.
        """
        new = ObjectiveWeights(
            reward_weight=self._weights.reward_weight + reward_bias,
            risk_weight=self._weights.risk_weight + risk_bias,
            stability_weight=self._weights.stability_weight + stability_bias,
            exploration_weight=self._weights.exploration_weight,
            novelty_weight=self._weights.novelty_weight,
        )
        clamped = _clamp_weights(new)
        changed = clamped != self._weights
        self._weights = clamped
        return changed

    def reset(self) -> None:
        """Reset to default weights and mode."""
        self._weights = DEFAULT_WEIGHTS
        self._mode = "default"
        self._update_count = 0

    def get_trace_fields(self) -> dict:
        """Return trace-compatible fields for DecisionTrace."""
        return {
            "objective_arb_mode": self._mode,
            "objective_arb_reward_weight": self._weights.reward_weight,
            "objective_arb_risk_weight": self._weights.risk_weight,
            "objective_arb_stability_weight": self._weights.stability_weight,
            "objective_arb_shift_reason": f"mode_sustained:{self._mode}",
        }


# ─── Inactive result ──────────────────────────────────────────

NO_ARBITRATION_RESULT = ArbitrationResult(
    active=False,
    mode="default",
    weights=DEFAULT_WEIGHTS,
    shift_reason="arbitration_inactive",
    confidence=0.0,
)
