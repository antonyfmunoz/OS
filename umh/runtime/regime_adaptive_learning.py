"""Regime-dependent adaptive learning — per-regime learning rate modulation.

Extends Phase 64 adaptive learning with regime-specific factors.
Different regimes get different learning speeds:
    - SPIKE regimes → faster adaptation (short-lived, must react quickly)
    - TREND regimes → moderate adaptation (persistent, track steadily)
    - STABLE regime → slower adaptation (noise suppression)

Core formula:
    adaptive_rate = clamp(base_rate * confidence * stability * regime_factor,
                          min_rate, max_rate)

Regime transition smoothing prevents abrupt factor changes on regime switch:
    smoothed = prev_factor + clamp(target - prev_factor, -max_delta, +max_delta)

Pure computation — no I/O, no child processes.
No imports from cell, environment, or adapter layers.
No circular dependency: reads adaptive_learning, regime types only.
Never mutates historical data (inv 298).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.runtime.adaptive_learning import (
    AdaptiveLearningConfig,
    AdaptiveLearningResult,
    DEFAULT_ADAPTIVE_LEARNING_CONFIG,
    _compute_confidence_factor,
    _compute_stability_factor,
    compute_adaptive_rate,
)
from umh.runtime.regime import RegimeType
from umh.runtime.weight_evolution import WeightObservation, _compute_signal_variance

_DEFAULT_REGIME_FACTORS: dict[str, float] = {
    RegimeType.STABLE.value: 0.5,
    RegimeType.TREND_UP.value: 1.0,
    RegimeType.TREND_DOWN.value: 1.0,
    RegimeType.SPIKE_UP.value: 1.5,
    RegimeType.SPIKE_DOWN.value: 1.5,
}

_DEFAULT_MIN_REGIME_SAMPLES: int = 5
_DEFAULT_MAX_FACTOR_DELTA: float = 0.2
_MIN_REGIME_FACTOR: float = 0.1
_MAX_REGIME_FACTOR: float = 3.0


@dataclass(frozen=True)
class RegimeAdaptiveConfig:
    """Configuration for regime-dependent adaptive learning."""

    enabled: bool = False
    regime_factors: dict[str, float] = field(default_factory=lambda: dict(_DEFAULT_REGIME_FACTORS))
    min_regime_samples: int = _DEFAULT_MIN_REGIME_SAMPLES
    max_factor_delta: float = _DEFAULT_MAX_FACTOR_DELTA

    def __post_init__(self) -> None:
        clamped = {
            k: max(_MIN_REGIME_FACTOR, min(_MAX_REGIME_FACTOR, v))
            for k, v in self.regime_factors.items()
        }
        object.__setattr__(self, "regime_factors", clamped)
        object.__setattr__(self, "min_regime_samples", max(1, self.min_regime_samples))
        object.__setattr__(self, "max_factor_delta", max(0.01, min(1.0, self.max_factor_delta)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "regime_factors": {k: round(v, 4) for k, v in sorted(self.regime_factors.items())},
            "min_regime_samples": self.min_regime_samples,
            "max_factor_delta": round(self.max_factor_delta, 4),
        }


DEFAULT_REGIME_ADAPTIVE_CONFIG = RegimeAdaptiveConfig()


@dataclass(frozen=True)
class RegimeAdaptiveResult:
    """Result of regime-dependent adaptive learning rate computation."""

    adaptive_rate: float = 0.05
    base_rate: float = 0.05
    confidence_factor: float = 1.0
    stability_factor: float = 1.0
    regime_factor: float = 1.0
    smoothed_regime_factor: float = 1.0
    variance: float = 0.0
    confidence_input: float = 0.0
    regime: RegimeType | None = None
    regime_sample_count: int = 0
    factor_smoothed: bool = False
    explanation: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "adaptive_rate", max(0.0, min(0.50, self.adaptive_rate)))
        object.__setattr__(self, "confidence_factor", max(0.0, min(1.0, self.confidence_factor)))
        object.__setattr__(self, "stability_factor", max(0.0, min(1.0, self.stability_factor)))
        object.__setattr__(
            self,
            "regime_factor",
            max(_MIN_REGIME_FACTOR, min(_MAX_REGIME_FACTOR, self.regime_factor)),
        )
        object.__setattr__(
            self,
            "smoothed_regime_factor",
            max(_MIN_REGIME_FACTOR, min(_MAX_REGIME_FACTOR, self.smoothed_regime_factor)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "adaptive_rate": round(self.adaptive_rate, 6),
            "base_rate": round(self.base_rate, 6),
            "confidence_factor": round(self.confidence_factor, 4),
            "stability_factor": round(self.stability_factor, 4),
            "regime_factor": round(self.regime_factor, 4),
            "smoothed_regime_factor": round(self.smoothed_regime_factor, 4),
            "variance": round(self.variance, 6),
            "confidence_input": round(self.confidence_input, 4),
            "regime": self.regime.value if self.regime else None,
            "regime_sample_count": self.regime_sample_count,
            "factor_smoothed": self.factor_smoothed,
            "explanation": self.explanation,
        }


def _resolve_regime_factor(
    regime: RegimeType | None,
    regime_sample_count: int,
    min_regime_samples: int,
    regime_factors: dict[str, float],
) -> float:
    """Resolve the regime factor for a given regime.

    Returns 1.0 (neutral) if:
    - regime is None (inv 302)
    - regime is STABLE (inv 300)
    - regime_sample_count < min_regime_samples (inv 296)
    """
    if regime is None:
        return 1.0
    if regime is RegimeType.STABLE:
        return regime_factors.get(regime.value, 0.5)
    if regime_sample_count < min_regime_samples:
        return 1.0
    return regime_factors.get(regime.value, 1.0)


def _smooth_regime_factor(
    target_factor: float,
    previous_factor: float,
    max_delta: float,
) -> tuple[float, bool]:
    """Smooth regime factor transition to prevent abrupt changes.

    Returns (smoothed_factor, was_smoothed).
    """
    delta = target_factor - previous_factor
    if abs(delta) <= max_delta:
        return target_factor, False
    smoothed = previous_factor + max_delta * (1.0 if delta > 0 else -1.0)
    return max(_MIN_REGIME_FACTOR, min(_MAX_REGIME_FACTOR, smoothed)), True


def compute_regime_adaptive_rate(
    observations: list[WeightObservation] | None = None,
    confidence: float = 0.0,
    regime: RegimeType | None = None,
    regime_sample_count: int = 0,
    previous_regime_factor: float = 1.0,
    adaptive_config: AdaptiveLearningConfig | None = None,
    regime_config: RegimeAdaptiveConfig | None = None,
) -> RegimeAdaptiveResult:
    """Compute regime-dependent adaptive learning rate.

    adaptive_rate = clamp(base_rate * confidence * stability * regime_factor,
                          min_rate, max_rate)

    Deterministic (inv 298). No mutation. Bounded (inv 294, 295).
    Missing regime → factor = 1.0 (inv 302). Explainable (inv 299).
    """
    acfg = adaptive_config or DEFAULT_ADAPTIVE_LEARNING_CONFIG
    rcfg = regime_config or DEFAULT_REGIME_ADAPTIVE_CONFIG

    if not rcfg.enabled:
        base_result = compute_adaptive_rate(
            observations=observations,
            confidence=confidence,
            config=acfg,
        )
        return RegimeAdaptiveResult(
            adaptive_rate=base_result.adaptive_rate,
            base_rate=base_result.base_rate,
            confidence_factor=base_result.confidence_factor,
            stability_factor=base_result.stability_factor,
            regime_factor=1.0,
            smoothed_regime_factor=1.0,
            variance=base_result.variance,
            confidence_input=confidence,
            regime=regime,
            regime_sample_count=regime_sample_count,
            explanation=f"regime_adaptive disabled; {base_result.explanation}",
        )

    obs_list = observations or []
    base_rate = acfg.base_rate if acfg.enabled else acfg.base_rate

    if not obs_list:
        return RegimeAdaptiveResult(
            adaptive_rate=acfg.base_rate,
            base_rate=acfg.base_rate,
            confidence_input=confidence,
            regime=regime,
            regime_sample_count=regime_sample_count,
            explanation="no observations: fallback to base_rate",
        )

    conf_factor = _compute_confidence_factor(confidence)
    variance = _compute_signal_variance(obs_list)
    stab_factor = _compute_stability_factor(variance, acfg.variance_threshold)

    raw_regime_factor = _resolve_regime_factor(
        regime=regime,
        regime_sample_count=regime_sample_count,
        min_regime_samples=rcfg.min_regime_samples,
        regime_factors=rcfg.regime_factors,
    )

    smoothed_factor, was_smoothed = _smooth_regime_factor(
        target_factor=raw_regime_factor,
        previous_factor=previous_regime_factor,
        max_delta=rcfg.max_factor_delta,
    )

    raw_rate = acfg.base_rate * conf_factor * stab_factor * smoothed_factor
    adaptive_rate = max(acfg.min_rate, min(acfg.max_rate, raw_rate))

    parts = [
        f"base={acfg.base_rate:.4f}",
        f"conf={conf_factor:.3f}",
        f"stab={stab_factor:.3f}",
        f"regime_f={raw_regime_factor:.3f}",
    ]
    if was_smoothed:
        parts.append(f"smoothed={smoothed_factor:.3f}")
    parts.extend(
        [
            f"var={variance:.4f}",
            f"raw={raw_rate:.6f}",
            f"clamped={adaptive_rate:.6f}",
        ]
    )
    if regime:
        parts.append(f"regime={regime.value}")

    return RegimeAdaptiveResult(
        adaptive_rate=adaptive_rate,
        base_rate=acfg.base_rate,
        confidence_factor=conf_factor,
        stability_factor=stab_factor,
        regime_factor=raw_regime_factor,
        smoothed_regime_factor=smoothed_factor,
        variance=variance,
        confidence_input=confidence,
        regime=regime,
        regime_sample_count=regime_sample_count,
        factor_smoothed=was_smoothed,
        explanation="; ".join(parts),
    )
