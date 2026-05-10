"""Feedback Dynamics — model delayed, nonlinear, and compounding outcomes.

Real-world outcomes are rarely immediate or linear:
- Content may convert viewers days later
- Outreach replies arrive over a week
- Habits compound slowly then accelerate
- Markets saturate

This module models these dynamics so the system doesn't
prematurely judge a run as failed or successful.

Usage:
    from core.dynamics import FeedbackDynamics, DelayedScore

    dynamics = FeedbackDynamics(
        lag_steps=3,
        decay_rate=0.1,
        compounding_factor=1.05,
    )

    delayed = dynamics.project_score(
        immediate_score=0.4,
        elapsed_steps=1,
        historical_trajectory=[0.2, 0.3, 0.35],
    )
    print(delayed.projected)  # projected future score
    print(delayed.matured)    # False — still within lag window
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Dynamics configuration
# ---------------------------------------------------------------------------


@dataclass
class FeedbackDynamics:
    """Models how feedback evolves over time.

    Args:
        lag_steps:          How many evaluation cycles before full impact is visible.
        decay_rate:         How fast signal strength decays per step (0.0 = no decay).
        compounding_factor: Multiplier per step for compounding effects (1.0 = linear).
        saturation_threshold: Score above which diminishing returns kick in.
        volatility:         Expected variance in scores (0.0 = stable, 1.0 = chaotic).
    """

    lag_steps: int = 0
    decay_rate: float = 0.0
    compounding_factor: float = 1.0
    saturation_threshold: float = 1.0
    volatility: float = 0.0

    def project_score(
        self,
        immediate_score: float,
        elapsed_steps: int = 0,
        historical_trajectory: list[float] | None = None,
    ) -> DelayedScore:
        """Project what the score will be once feedback fully matures.

        Args:
            immediate_score:       Score measured right now.
            elapsed_steps:         How many steps since the run executed.
            historical_trajectory: Previous scores for this metric over time.

        Returns:
            DelayedScore with immediate, projected, and confidence values.
        """
        trajectory = historical_trajectory or []
        matured = elapsed_steps >= self.lag_steps

        # Start with immediate score
        projected = immediate_score

        if not matured:
            # We're still in the lag window — project forward
            remaining_steps = self.lag_steps - elapsed_steps

            # Apply compounding
            if self.compounding_factor != 1.0:
                projected *= self.compounding_factor**remaining_steps

            # Apply trend extrapolation from trajectory
            if len(trajectory) >= 2:
                trend = self._compute_trend(trajectory)
                projected += trend * remaining_steps

            # Apply decay
            if self.decay_rate > 0:
                projected *= (1 - self.decay_rate) ** remaining_steps

        # Apply saturation (diminishing returns)
        if self.saturation_threshold < 1.0 and projected > self.saturation_threshold:
            excess = projected - self.saturation_threshold
            # Logarithmic dampening above threshold
            projected = self.saturation_threshold + math.log1p(excess) * 0.1

        # Clamp to valid range
        projected = max(0.0, min(projected, 1.0))

        # Confidence decreases with lag and volatility
        confidence = self._compute_confidence(elapsed_steps, len(trajectory), matured)

        return DelayedScore(
            immediate=immediate_score,
            projected=projected,
            matured=matured,
            elapsed_steps=elapsed_steps,
            lag_steps=self.lag_steps,
            confidence=confidence,
            dynamics_applied={
                "compounding": self.compounding_factor != 1.0,
                "decay": self.decay_rate > 0,
                "saturation": self.saturation_threshold < 1.0,
                "trend_extrapolation": len(trajectory) >= 2,
            },
        )

    def should_wait(self, elapsed_steps: int) -> bool:
        """True if the run hasn't matured yet and shouldn't be judged."""
        return elapsed_steps < self.lag_steps

    def apply_compounding(self, base_score: float, steps: int) -> float:
        """Apply compounding effect over N steps."""
        result = base_score * (self.compounding_factor**steps)
        return max(0.0, min(result, 1.0))

    def apply_decay(self, score: float, steps: int) -> float:
        """Apply decay over N steps."""
        result = score * ((1 - self.decay_rate) ** steps)
        return max(0.0, result)

    def apply_saturation(self, score: float) -> float:
        """Apply diminishing returns above saturation threshold."""
        if score <= self.saturation_threshold:
            return score
        excess = score - self.saturation_threshold
        return self.saturation_threshold + math.log1p(excess) * 0.1

    def _compute_trend(self, trajectory: list[float]) -> float:
        """Simple linear trend from trajectory (slope of last N points)."""
        if len(trajectory) < 2:
            return 0.0
        # Use last 5 points max for trend
        recent = trajectory[-5:]
        n = len(recent)
        x_mean = (n - 1) / 2
        y_mean = sum(recent) / n
        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(recent))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        if denominator == 0:
            return 0.0
        return numerator / denominator

    def _compute_confidence(
        self, elapsed: int, trajectory_len: int, matured: bool
    ) -> float:
        """Confidence in the projected score."""
        if matured:
            return 0.95  # matured scores are high confidence

        # Base confidence decreases with remaining lag
        remaining = max(self.lag_steps - elapsed, 1)
        base = 1.0 / (1 + remaining * 0.3)

        # More trajectory data → more confidence
        data_factor = min(trajectory_len / 5, 1.0) * 0.3

        # High volatility → less confidence
        volatility_penalty = self.volatility * 0.2

        return max(0.1, min(base + data_factor - volatility_penalty, 0.95))

    def to_dict(self) -> dict[str, Any]:
        return {
            "lag_steps": self.lag_steps,
            "decay_rate": self.decay_rate,
            "compounding_factor": self.compounding_factor,
            "saturation_threshold": self.saturation_threshold,
            "volatility": self.volatility,
        }


# ---------------------------------------------------------------------------
# Delayed score result
# ---------------------------------------------------------------------------


@dataclass
class DelayedScore:
    """Result of projecting a score through feedback dynamics."""

    immediate: float  # score measured now
    projected: float  # projected score after maturation
    matured: bool  # True if lag window has passed
    elapsed_steps: int
    lag_steps: int
    confidence: float  # 0-1 confidence in projection
    dynamics_applied: dict[str, bool] = field(default_factory=dict)

    @property
    def pending(self) -> bool:
        """True if score hasn't matured and shouldn't be used for final judgment."""
        return not self.matured

    def to_dict(self) -> dict[str, Any]:
        return {
            "immediate": round(self.immediate, 4),
            "projected": round(self.projected, 4),
            "matured": self.matured,
            "pending": self.pending,
            "elapsed_steps": self.elapsed_steps,
            "lag_steps": self.lag_steps,
            "confidence": round(self.confidence, 4),
            "dynamics_applied": self.dynamics_applied,
        }


# ---------------------------------------------------------------------------
# Pre-built dynamics profiles
# ---------------------------------------------------------------------------


def outreach_dynamics() -> FeedbackDynamics:
    """Outreach: replies lag 2-5 days, no compounding, moderate decay."""
    return FeedbackDynamics(
        lag_steps=3,
        decay_rate=0.05,
        compounding_factor=1.0,
        saturation_threshold=0.8,
        volatility=0.3,
    )


def content_dynamics() -> FeedbackDynamics:
    """Content: engagement compounds, saturates, low decay."""
    return FeedbackDynamics(
        lag_steps=5,
        decay_rate=0.02,
        compounding_factor=1.08,
        saturation_threshold=0.9,
        volatility=0.4,
    )


def habit_dynamics() -> FeedbackDynamics:
    """Habits: slow compounding, very delayed, low volatility."""
    return FeedbackDynamics(
        lag_steps=14,
        decay_rate=0.01,
        compounding_factor=1.03,
        saturation_threshold=0.95,
        volatility=0.1,
    )


__all__ = [
    "FeedbackDynamics",
    "DelayedScore",
    "outreach_dynamics",
    "content_dynamics",
    "habit_dynamics",
]
