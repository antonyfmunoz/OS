"""
Adaptive signal sensitivity — dynamic responsiveness to signal strength.

Adjusts how aggressively the system responds to orchestrated signals
based on consistency, noise level, context, and signal density.

Boosts weak-but-consistent signals so improvements appear earlier.
Dampens noisy signals to prevent instability.
Degrades to identity (factor=1.0) when uncertain.

Stateless. Deterministic. Bounded. No LLM calls. No randomness.
"""

from __future__ import annotations

from dataclasses import dataclass

# ─── Constants ──────────────────────────────────────────────────────

MIN_SENSITIVITY = 0.5
MAX_SENSITIVITY = 1.5
DEFAULT_SENSITIVITY = 1.0
MAX_BIAS = 0.05

LOW_DATA_BOOST_MAX = 1.5
LOW_DATA_BOOST_MIN = 1.1
NOISE_SUPPRESS_MIN = 0.5
NOISE_SUPPRESS_MAX = 0.9
DENSITY_BOOST_MAX = 1.3
DENSITY_BOOST_MIN = 1.1

CONSISTENCY_THRESHOLD = 0.5
NOISE_VARIANCE_THRESHOLD = 0.001
LOW_CONFIDENCE_CEILING = 0.5
MIN_CONFIDENCE_FOR_BOOST = 0.05
DENSITY_THRESHOLD = 3


# ─── Helpers ────────────────────────────────────────────────────────


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _bias_variance_from_dict(biases: dict[str, float]) -> float:
    """Variance of bias values within a single action-bias dict."""
    if not biases:
        return 0.0
    vals = list(biases.values())
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    return sum((v - mean) ** 2 for v in vals) / len(vals)


def _bias_consistency(biases: dict[str, float]) -> float:
    """How consistently biases point in one direction. [0, 1]."""
    if not biases:
        return 0.0
    vals = list(biases.values())
    if not vals:
        return 0.0
    pos = sum(1 for v in vals if v > 1e-9)
    neg = sum(1 for v in vals if v < -1e-9)
    total = pos + neg
    if total == 0:
        return 0.0
    return max(pos, neg) / total


# ─── Data structures ───────────────────────────────────────────────


@dataclass(frozen=True)
class SensitivityResult:
    """Output of sensitivity computation."""

    sensitivity_factor: float
    reason: str
    applied: bool
    low_data_boost: float
    noise_suppression: float
    density_boost: float

    def to_dict(self) -> dict:
        return {
            "sensitivity_factor": round(self.sensitivity_factor, 4),
            "reason": self.reason,
            "applied": self.applied,
            "low_data_boost": round(self.low_data_boost, 4),
            "noise_suppression": round(self.noise_suppression, 4),
            "density_boost": round(self.density_boost, 4),
        }


NO_SENSITIVITY = SensitivityResult(
    sensitivity_factor=DEFAULT_SENSITIVITY,
    reason="no_data",
    applied=False,
    low_data_boost=1.0,
    noise_suppression=1.0,
    density_boost=1.0,
)


# ─── Engine ─────────────────────────────────────────────────────────


def compute_sensitivity(
    combined_action_bias: dict[str, float],
    consensus_score: float,
    signal_confidences: dict[str, float],
    context_type: str,
    active_signal_count: int,
) -> SensitivityResult:
    """Compute adaptive sensitivity factor for orchestrated signal.

    Returns a multiplicative factor in [0.5, 1.5] that scales the
    orchestrated combined_action_bias before application.
    """

    # ── Context gate: no amplification outside stable ──────────
    if context_type != "stable":
        return SensitivityResult(
            sensitivity_factor=DEFAULT_SENSITIVITY,
            reason="unstable_context",
            applied=False,
            low_data_boost=1.0,
            noise_suppression=1.0,
            density_boost=1.0,
        )

    if not combined_action_bias:
        return NO_SENSITIVITY

    # ── Extract metrics ────────────────────────────────────────
    avg_confidence = 0.0
    if signal_confidences:
        conf_vals = [
            v for v in signal_confidences.values() if isinstance(v, (int, float))
        ]
        if conf_vals:
            avg_confidence = sum(conf_vals) / len(conf_vals)

    bias_var = _bias_variance_from_dict(combined_action_bias)
    consistency = _bias_consistency(combined_action_bias)

    # ── 1. Low data boost ──────────────────────────────────────
    # When confidence is low but signals are consistent, boost.
    low_data_boost = 1.0
    if (
        avg_confidence < LOW_CONFIDENCE_CEILING
        and avg_confidence >= MIN_CONFIDENCE_FOR_BOOST
        and consistency > CONSISTENCY_THRESHOLD
    ):
        confidence_gap = LOW_CONFIDENCE_CEILING - avg_confidence
        consistency_strength = (consistency - CONSISTENCY_THRESHOLD) / (
            1.0 - CONSISTENCY_THRESHOLD
        )
        boost = confidence_gap * consistency_strength
        low_data_boost = LOW_DATA_BOOST_MIN + (
            LOW_DATA_BOOST_MAX - LOW_DATA_BOOST_MIN
        ) * _clamp(boost * 2.0, 0.0, 1.0)

    # ── 2. Noise suppression ───────────────────────────────────
    # When variance is high and agreement is low, dampen.
    noise_suppression = 1.0
    if bias_var > NOISE_VARIANCE_THRESHOLD and consensus_score < CONSISTENCY_THRESHOLD:
        noise_intensity = _clamp(bias_var / (NOISE_VARIANCE_THRESHOLD * 10.0), 0.0, 1.0)
        disagreement = 1.0 - consensus_score
        noise_factor = noise_intensity * disagreement
        noise_suppression = NOISE_SUPPRESS_MAX - (
            NOISE_SUPPRESS_MAX - NOISE_SUPPRESS_MIN
        ) * _clamp(noise_factor, 0.0, 1.0)

    # ── 3. Signal density boost ────────────────────────────────
    # Multiple aligned signals increase responsiveness.
    density_boost = 1.0
    if (
        active_signal_count >= DENSITY_THRESHOLD
        and consensus_score > CONSISTENCY_THRESHOLD
    ):
        density_strength = _clamp(
            (active_signal_count - DENSITY_THRESHOLD) / 3.0, 0.0, 1.0
        )
        agreement_strength = _clamp(
            (consensus_score - CONSISTENCY_THRESHOLD) / (1.0 - CONSISTENCY_THRESHOLD),
            0.0,
            1.0,
        )
        density_boost = (
            DENSITY_BOOST_MIN
            + (DENSITY_BOOST_MAX - DENSITY_BOOST_MIN)
            * density_strength
            * agreement_strength
        )

    # ── Combine factors ────────────────────────────────────────
    raw_factor = low_data_boost * noise_suppression * density_boost
    factor = _clamp(raw_factor, MIN_SENSITIVITY, MAX_SENSITIVITY)

    # ── Safety: no amplification of conflicting signals ────────
    if consensus_score < 0.3 and factor > 1.0:
        factor = DEFAULT_SENSITIVITY

    # ── Build reason ───────────────────────────────────────────
    reasons: list[str] = []
    if low_data_boost > 1.01:
        reasons.append("low_data_boost")
    if noise_suppression < 0.99:
        reasons.append("noise_suppression")
    if density_boost > 1.01:
        reasons.append("density_boost")

    applied = abs(factor - DEFAULT_SENSITIVITY) > 0.01
    reason = "+".join(reasons) if reasons else "neutral"

    return SensitivityResult(
        sensitivity_factor=factor,
        reason=reason,
        applied=applied,
        low_data_boost=low_data_boost,
        noise_suppression=noise_suppression,
        density_boost=density_boost,
    )


# ─── Pipeline integration ──────────────────────────────────────────


def apply_sensitivity(
    combined_action_bias: dict[str, float],
    sensitivity: SensitivityResult,
    strategy_scores: dict[str, float] | None = None,
) -> dict[str, float]:
    """Scale orchestrated biases by the sensitivity factor.

    Rules:
    - multiplicative scaling
    - bounded ±MAX_BIAS
    - leader protection
    """
    if not sensitivity.applied or not combined_action_bias:
        return combined_action_bias

    factor = sensitivity.sensitivity_factor
    scaled: dict[str, float] = {}
    for action, bias in combined_action_bias.items():
        val = _clamp(bias * factor, -MAX_BIAS, MAX_BIAS)
        if abs(val) > 1e-9:
            scaled[action] = val

    # Leader protection
    if strategy_scores and scaled:
        sorted_scores = sorted(strategy_scores.values(), reverse=True)
        if len(sorted_scores) >= 2:
            leader_gap = sorted_scores[0] - sorted_scores[1]
            if leader_gap > MAX_BIAS:
                leader_action = None
                for act, sc in strategy_scores.items():
                    if sc == sorted_scores[0]:
                        leader_action = act
                        break
                if (
                    leader_action
                    and leader_action in scaled
                    and scaled[leader_action] < 0
                ):
                    del scaled[leader_action]

    return scaled
