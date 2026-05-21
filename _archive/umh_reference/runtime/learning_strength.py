"""Learning strength — adaptive dampening of feedback influence.

Computes how strongly feedback should influence scoring based on data
quality: sample size, outcome volatility, and stability.

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from umh.runtime.outcome import StrategyOutcome


@dataclass(frozen=True)
class LearningStrengthConfig:
    """Configuration for adaptive learning strength."""

    min_strength: float = 0.25
    max_strength: float = 1.0
    required_samples: int = 20
    volatility_penalty: float = 0.5

    def __post_init__(self) -> None:
        object.__setattr__(self, "min_strength", max(0.0, min(1.0, self.min_strength)))
        object.__setattr__(
            self, "max_strength", max(self.min_strength, min(1.0, self.max_strength))
        )
        object.__setattr__(self, "required_samples", max(1, self.required_samples))
        object.__setattr__(self, "volatility_penalty", max(0.0, min(1.0, self.volatility_penalty)))


@dataclass(frozen=True)
class LearningStrengthResult:
    """Result of computing adaptive learning strength."""

    strength: float
    confidence: float
    volatility: float
    sample_factor: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "strength": round(self.strength, 4),
            "confidence": round(self.confidence, 4),
            "volatility": round(self.volatility, 4),
            "sample_factor": round(self.sample_factor, 4),
            "reason": self.reason,
        }


def _compute_volatility(outcomes: list[StrategyOutcome]) -> float:
    if len(outcomes) < 2:
        return 0.0
    scores = [o.success_score for o in outcomes]
    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    return math.sqrt(variance)


def compute_learning_strength(
    outcomes: list[StrategyOutcome],
    config: LearningStrengthConfig | None = None,
) -> LearningStrengthResult:
    cfg = config or LearningStrengthConfig()

    if not outcomes:
        return LearningStrengthResult(
            strength=cfg.min_strength,
            confidence=0.0,
            volatility=0.0,
            sample_factor=0.0,
            reason="no outcomes",
        )

    n = len(outcomes)
    sample_factor = min(1.0, n / cfg.required_samples)
    volatility = _compute_volatility(outcomes)

    vol_reduction = volatility * cfg.volatility_penalty
    raw = sample_factor * (1.0 - vol_reduction)
    strength = max(cfg.min_strength, min(cfg.max_strength, raw))
    confidence = sample_factor

    if n < cfg.required_samples:
        reason_parts = f"sparse data ({n}/{cfg.required_samples} samples)"
    elif volatility > 0.3:
        reason_parts = f"high volatility ({volatility:.2f})"
    elif volatility < 0.1 and sample_factor >= 1.0:
        reason_parts = f"stable pattern ({volatility:.2f} vol, {n} samples)"
    else:
        reason_parts = f"moderate ({volatility:.2f} vol, {n} samples)"

    return LearningStrengthResult(
        strength=strength,
        confidence=confidence,
        volatility=volatility,
        sample_factor=sample_factor,
        reason=reason_parts,
    )
