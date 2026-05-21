"""WorldDynamicsAdapter — calibration-driven simulation parameter adjustment.

Closes the loop: calibration error signals → bias accumulation →
simulation parameter modification. Adjusts the laws of the simulated
world based on observed reality, not parameter fitting.

All logic is deterministic, bounded, and additive only.
No ML/NN. No randomness. No mutation of historical data.
Adjustments are small, stable, and reversible.
"""

from __future__ import annotations

from dataclasses import dataclass

from umh.world.calibration import CalibrationSummary

# ─── Constants ───────────────────────────────────────────────────

ADAPTER_EMA_ALPHA = 0.05

BIAS_MIN = -0.3
BIAS_MAX = 0.3

TREND_MULTIPLIER_MIN = 0.7
TREND_MULTIPLIER_MAX = 1.3

RISK_MULTIPLIER_MIN = 0.7
RISK_MULTIPLIER_MAX = 1.3

STABILITY_DECAY_MODIFIER_MIN = -0.02
STABILITY_DECAY_MODIFIER_MAX = 0.02

CONFIDENCE_SCALE_MIN = 0.8
CONFIDENCE_SCALE_MAX = 1.2

MIN_CALIBRATION_CONFIDENCE = 0.3
MAX_UNCERTAINTY_FOR_ADAPTATION = 0.6

# ─── Data models ─────────────────────────────────────────────────


@dataclass(frozen=True)
class DynamicsAdjustmentState:
    """Current bias accumulation state from calibration history."""

    trend_bias: float
    risk_bias: float
    stability_bias: float
    confidence_bias: float
    last_update_step: int

    def to_dict(self) -> dict:
        return {
            "trend_bias": round(self.trend_bias, 6),
            "risk_bias": round(self.risk_bias, 6),
            "stability_bias": round(self.stability_bias, 6),
            "confidence_bias": round(self.confidence_bias, 6),
            "last_update_step": self.last_update_step,
        }


@dataclass(frozen=True)
class DynamicsAdjustment:
    """Concrete multipliers/modifiers to apply to simulation dynamics."""

    trend_multiplier: float
    risk_multiplier: float
    stability_decay_modifier: float
    confidence_scale: float

    def to_dict(self) -> dict:
        return {
            "trend_multiplier": round(self.trend_multiplier, 6),
            "risk_multiplier": round(self.risk_multiplier, 6),
            "stability_decay_modifier": round(self.stability_decay_modifier, 6),
            "confidence_scale": round(self.confidence_scale, 6),
        }


NEUTRAL_ADJUSTMENT = DynamicsAdjustment(
    trend_multiplier=1.0,
    risk_multiplier=1.0,
    stability_decay_modifier=0.0,
    confidence_scale=1.0,
)

NEUTRAL_STATE = DynamicsAdjustmentState(
    trend_bias=0.0,
    risk_bias=0.0,
    stability_bias=0.0,
    confidence_bias=0.0,
    last_update_step=0,
)


# ─── Clamping helpers ────────────────────────────────────────────


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _clamp_bias(v: float) -> float:
    return _clamp(v, BIAS_MIN, BIAS_MAX)


# ─── Bias → Adjustment mapping ──────────────────────────────────


def bias_to_adjustment(state: DynamicsAdjustmentState) -> DynamicsAdjustment:
    """Convert accumulated bias state into concrete simulation adjustments."""
    trend_mult = _clamp(
        1.0 + state.trend_bias, TREND_MULTIPLIER_MIN, TREND_MULTIPLIER_MAX
    )
    risk_mult = _clamp(1.0 + state.risk_bias, RISK_MULTIPLIER_MIN, RISK_MULTIPLIER_MAX)
    stab_mod = _clamp(
        state.stability_bias * 0.1,
        STABILITY_DECAY_MODIFIER_MIN,
        STABILITY_DECAY_MODIFIER_MAX,
    )
    conf_scale = _clamp(
        1.0 + state.confidence_bias * 0.5,
        CONFIDENCE_SCALE_MIN,
        CONFIDENCE_SCALE_MAX,
    )
    return DynamicsAdjustment(
        trend_multiplier=trend_mult,
        risk_multiplier=risk_mult,
        stability_decay_modifier=stab_mod,
        confidence_scale=conf_scale,
    )


# ─── WorldDynamicsAdapter ───────────────────────────────────────


class WorldDynamicsAdapter:
    """Adapts simulation dynamics parameters based on calibration signals.

    Maintains a DynamicsAdjustmentState that accumulates EMA-smoothed
    bias from CalibrationSummary inputs. Produces DynamicsAdjustment
    for use by WorldSimulationEngine.

    Safety:
    - Only updates when context_type == "stable"
    - Refuses update when uncertainty > MAX_UNCERTAINTY_FOR_ADAPTATION
    - Refuses update when calibration confidence < MIN_CALIBRATION_CONFIDENCE
    - All values bounded, all changes additive, all state reversible
    """

    def __init__(self) -> None:
        self._state = NEUTRAL_STATE

    @property
    def state(self) -> DynamicsAdjustmentState:
        return self._state

    def update_from_calibration(
        self,
        summary: CalibrationSummary,
        context_type: str | None = None,
        uncertainty: float = 0.0,
    ) -> bool:
        """Update bias state from a calibration summary.

        Returns True if the update was applied, False if gated off.
        """
        if context_type != "stable":
            return False
        if uncertainty > MAX_UNCERTAINTY_FOR_ADAPTATION:
            return False
        if summary.confidence_score < MIN_CALIBRATION_CONFIDENCE:
            return False

        alpha = ADAPTER_EMA_ALPHA
        old = self._state

        new_trend = _clamp_bias(
            (1.0 - alpha) * old.trend_bias + alpha * summary.trend_error
        )
        new_risk = _clamp_bias(
            (1.0 - alpha) * old.risk_bias + alpha * summary.avg_error
        )
        new_stability = _clamp_bias(
            (1.0 - alpha) * old.stability_bias + alpha * summary.stability_error
        )
        new_confidence = _clamp_bias(
            (1.0 - alpha) * old.confidence_bias
            + alpha * (summary.confidence_score - 0.5)
        )

        self._state = DynamicsAdjustmentState(
            trend_bias=new_trend,
            risk_bias=new_risk,
            stability_bias=new_stability,
            confidence_bias=new_confidence,
            last_update_step=summary.timestamp_step,
        )
        return True

    def get_adjustments(self) -> DynamicsAdjustment:
        """Return current simulation adjustments derived from accumulated bias."""
        return bias_to_adjustment(self._state)

    def is_active(self) -> bool:
        """True if any bias has accumulated (state differs from neutral)."""
        s = self._state
        return (
            s.trend_bias != 0.0
            or s.risk_bias != 0.0
            or s.stability_bias != 0.0
            or s.confidence_bias != 0.0
        )

    def reset(self) -> None:
        """Reset to neutral state."""
        self._state = NEUTRAL_STATE

    def get_trace_fields(self) -> dict:
        """Extract trace-ready fields from current adapter state."""
        adj = self.get_adjustments()
        return {
            "dynamics_trend_multiplier": adj.trend_multiplier,
            "dynamics_risk_multiplier": adj.risk_multiplier,
            "dynamics_stability_modifier": adj.stability_decay_modifier,
            "dynamics_confidence_scale": adj.confidence_scale,
        }
