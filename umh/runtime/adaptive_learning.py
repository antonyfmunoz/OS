"""Adaptive learning rate — data-driven learning rate modulation for weight evolution.

Replaces fixed learning_rate with adaptive_rate that scales based on:
    - confidence_factor: clamp(confidence, 0, 1) — high confidence = faster learning (inv 285)
    - stability_factor: 1 / (1 + variance / threshold) — high variance = dampened (inv 287)
    - adaptive_rate = clamp(base_rate * confidence * stability, min_rate, max_rate) (inv 284)

Pure computation — no I/O, no child processes.
No imports from cell, environment, or adapter layers.
No circular dependency: reads weight_evolution types only.
Never mutates historical data (inv 291).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.runtime.weight_evolution import WeightObservation, _compute_signal_variance

_DEFAULT_BASE_RATE: float = 0.05
_DEFAULT_MIN_RATE: float = 0.005
_DEFAULT_MAX_RATE: float = 0.10
_DEFAULT_VARIANCE_THRESHOLD: float = 0.25


@dataclass(frozen=True)
class AdaptiveLearningConfig:
    """Configuration for adaptive learning rate computation."""

    enabled: bool = False
    base_rate: float = _DEFAULT_BASE_RATE
    min_rate: float = _DEFAULT_MIN_RATE
    max_rate: float = _DEFAULT_MAX_RATE
    variance_threshold: float = _DEFAULT_VARIANCE_THRESHOLD

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_rate", max(0.0, min(0.50, self.base_rate)))
        object.__setattr__(self, "min_rate", max(0.0, min(0.50, self.min_rate)))
        object.__setattr__(self, "max_rate", max(0.0, min(0.50, self.max_rate)))
        if self.min_rate > self.max_rate:
            object.__setattr__(self, "min_rate", self.max_rate)
        object.__setattr__(self, "variance_threshold", max(0.01, min(1.0, self.variance_threshold)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "base_rate": round(self.base_rate, 4),
            "min_rate": round(self.min_rate, 4),
            "max_rate": round(self.max_rate, 4),
            "variance_threshold": round(self.variance_threshold, 4),
        }


DEFAULT_ADAPTIVE_LEARNING_CONFIG = AdaptiveLearningConfig()


@dataclass(frozen=True)
class AdaptiveLearningResult:
    """Result of adaptive learning rate computation for a single dimension."""

    adaptive_rate: float = _DEFAULT_BASE_RATE
    base_rate: float = _DEFAULT_BASE_RATE
    confidence_factor: float = 1.0
    stability_factor: float = 1.0
    regime_factor: float = 1.0
    variance: float = 0.0
    confidence_input: float = 0.0
    explanation: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "adaptive_rate", max(0.0, min(0.50, self.adaptive_rate)))
        object.__setattr__(self, "confidence_factor", max(0.0, min(1.0, self.confidence_factor)))
        object.__setattr__(self, "stability_factor", max(0.0, min(1.0, self.stability_factor)))
        object.__setattr__(self, "regime_factor", max(0.0, min(5.0, self.regime_factor)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "adaptive_rate": round(self.adaptive_rate, 6),
            "base_rate": round(self.base_rate, 6),
            "confidence_factor": round(self.confidence_factor, 4),
            "stability_factor": round(self.stability_factor, 4),
            "regime_factor": round(self.regime_factor, 4),
            "variance": round(self.variance, 6),
            "confidence_input": round(self.confidence_input, 4),
            "explanation": self.explanation,
        }


def _compute_confidence_factor(confidence: float) -> float:
    """Confidence factor: clamp(confidence, 0, 1).

    confidence = 0 → no learning (inv 286).
    confidence = 1 → full learning (inv 285).
    """
    return max(0.0, min(1.0, confidence))


def _compute_stability_factor(
    variance: float,
    threshold: float,
) -> float:
    """Stability factor: smooth dampening based on signal variance.

    stability = 1 / (1 + variance / threshold)

    Low variance → ~1.0 (full rate).
    High variance → approaches 0 (dampened) (inv 287).
    """
    if threshold <= 0.0:
        return 1.0
    return 1.0 / (1.0 + variance / threshold)


def compute_adaptive_rate(
    observations: list[WeightObservation] | None = None,
    confidence: float = 0.0,
    config: AdaptiveLearningConfig | None = None,
    regime_factor: float = 1.0,
) -> AdaptiveLearningResult:
    """Compute adaptive learning rate for a single dimension's observations.

    adaptive_rate = clamp(base_rate * confidence_factor * stability_factor * regime_factor,
                          min_rate, max_rate) (inv 284).

    Deterministic (inv 288). No mutation (inv 291).
    Missing data → fallback to base_rate (inv 292).
    Explainable (inv 293).
    """
    cfg = config or DEFAULT_ADAPTIVE_LEARNING_CONFIG
    rf = max(0.0, min(5.0, regime_factor))

    if not cfg.enabled:
        return AdaptiveLearningResult(
            adaptive_rate=cfg.base_rate,
            base_rate=cfg.base_rate,
            regime_factor=rf,
            confidence_input=confidence,
            explanation="adaptive learning disabled: using base_rate",
        )

    obs_list = observations or []

    if not obs_list:
        return AdaptiveLearningResult(
            adaptive_rate=cfg.base_rate,
            base_rate=cfg.base_rate,
            regime_factor=rf,
            confidence_input=confidence,
            explanation="no observations: fallback to base_rate",
        )

    conf_factor = _compute_confidence_factor(confidence)
    variance = _compute_signal_variance(obs_list)
    stab_factor = _compute_stability_factor(variance, cfg.variance_threshold)

    raw_rate = cfg.base_rate * conf_factor * stab_factor * rf
    adaptive_rate = max(cfg.min_rate, min(cfg.max_rate, raw_rate))

    parts = [
        f"base={cfg.base_rate:.4f}",
        f"conf={conf_factor:.3f}",
        f"stab={stab_factor:.3f}",
        f"regime_f={rf:.3f}",
        f"var={variance:.4f}",
        f"raw={raw_rate:.6f}",
        f"clamped={adaptive_rate:.6f}",
    ]

    return AdaptiveLearningResult(
        adaptive_rate=adaptive_rate,
        base_rate=cfg.base_rate,
        confidence_factor=conf_factor,
        stability_factor=stab_factor,
        regime_factor=rf,
        variance=variance,
        confidence_input=confidence,
        explanation="; ".join(parts),
    )
