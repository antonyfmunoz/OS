"""UMH Feedback Dynamics — model delayed, nonlinear, and compounding outcomes.

Real-world outcomes are rarely immediate or linear:
- Content may convert viewers days later
- Outreach replies arrive over a week
- Habits compound slowly then accelerate
- Markets saturate

This module models these dynamics so the evaluation system doesn't
prematurely judge a run as failed or successful.

Deterministic. Pure math. No I/O, no LLM calls.
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
        """Project what the score will be once feedback fully matures."""
        trajectory = historical_trajectory or []
        matured = elapsed_steps >= self.lag_steps

        projected = immediate_score

        if not matured:
            remaining_steps = self.lag_steps - elapsed_steps

            if self.compounding_factor != 1.0:
                projected *= self.compounding_factor**remaining_steps

            if len(trajectory) >= 2:
                trend = self._compute_trend(trajectory)
                projected += trend * remaining_steps

            if self.decay_rate > 0:
                projected *= (1 - self.decay_rate) ** remaining_steps

        if self.saturation_threshold < 1.0 and projected > self.saturation_threshold:
            excess = projected - self.saturation_threshold
            projected = self.saturation_threshold + math.log1p(excess) * 0.1

        projected = max(0.0, min(projected, 1.0))

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
            return 0.95

        remaining = max(self.lag_steps - elapsed, 1)
        base = 1.0 / (1 + remaining * 0.3)

        data_factor = min(trajectory_len / 5, 1.0) * 0.3

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

    immediate: float
    projected: float
    matured: bool
    elapsed_steps: int
    lag_steps: int
    confidence: float
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
