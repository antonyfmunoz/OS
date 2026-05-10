"""Temporal weight evolution — time-aware adaptation of dimension weights.

Evolves dimension weights based on historical outcome–dimension signal
correlations.  Weights strengthen when a dimension consistently predicts
outcomes; weaken when inconsistent; decay toward neutral over time.

Key mechanics:
    - WeightObservation: a single (dimension, direction_signal, outcome_score, tick) record
    - quality_score: mean of (outcome_score * direction_signal) — correlation proxy
    - time decay: quality *= decay_rate ^ age — recent data > old data (inv 267)
    - update rule: delta = learning_rate * decayed_quality
    - clamping: evolved weight ∈ [1 - max_adj, 1 + max_adj] (inv 265)
    - sample gate: < min_samples → neutral (inv 268)
    - variance damping: high variance → delta *= 0.5 (stability)

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
No circular dependency: reads dimension_weighting + regime_aggregation types only.
Never mutates historical data (inv 270).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.runtime.dimension_weighting import (
    DimensionWeight,
    DimensionWeightVector,
    default_weight_vector,
)
from umh.runtime.regime_aggregation import DimensionName

_DEFAULT_DECAY_RATE: float = 0.98
_DEFAULT_LEARNING_RATE: float = 0.05
_DEFAULT_MIN_SAMPLES: int = 5
_DEFAULT_MAX_ADJUSTMENT: float = 0.15
_DEFAULT_VARIANCE_DAMPING_THRESHOLD: float = 0.25
_VARIANCE_DAMPING_FACTOR: float = 0.5


@dataclass(frozen=True)
class WeightEvolutionConfig:
    """Configuration for temporal weight evolution."""

    enabled: bool = False
    decay_rate: float = _DEFAULT_DECAY_RATE
    learning_rate: float = _DEFAULT_LEARNING_RATE
    min_samples: int = _DEFAULT_MIN_SAMPLES
    max_adjustment: float = _DEFAULT_MAX_ADJUSTMENT
    variance_damping_threshold: float = _DEFAULT_VARIANCE_DAMPING_THRESHOLD

    def __post_init__(self) -> None:
        object.__setattr__(self, "decay_rate", max(0.0, min(1.0, self.decay_rate)))
        object.__setattr__(self, "learning_rate", max(0.0, min(0.50, self.learning_rate)))
        object.__setattr__(self, "min_samples", max(1, self.min_samples))
        object.__setattr__(self, "max_adjustment", max(0.0, min(0.50, self.max_adjustment)))
        object.__setattr__(
            self,
            "variance_damping_threshold",
            max(0.0, min(1.0, self.variance_damping_threshold)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "decay_rate": round(self.decay_rate, 4),
            "learning_rate": round(self.learning_rate, 4),
            "min_samples": self.min_samples,
            "max_adjustment": round(self.max_adjustment, 4),
            "variance_damping_threshold": round(self.variance_damping_threshold, 4),
        }


DEFAULT_EVOLUTION_CONFIG = WeightEvolutionConfig()


@dataclass(frozen=True)
class WeightObservation:
    """A single observation linking a dimension signal to an outcome.

    direction_signal: [-1.0, 1.0] — the dimension's directional signal at decision time.
        +1.0 = strong positive, -1.0 = strong negative, 0.0 = neutral.
    outcome_score: [0.0, 1.0] — how successful the outcome was.
    tick: monotonic ordering index (higher = more recent).
    """

    dimension: DimensionName
    direction_signal: float = 0.0
    outcome_score: float = 0.0
    tick: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "direction_signal", max(-1.0, min(1.0, self.direction_signal)))
        object.__setattr__(self, "outcome_score", max(0.0, min(1.0, self.outcome_score)))
        object.__setattr__(self, "tick", max(0, self.tick))

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "direction_signal": round(self.direction_signal, 4),
            "outcome_score": round(self.outcome_score, 4),
            "tick": self.tick,
        }


@dataclass(frozen=True)
class DimensionEvolution:
    """Evolution result for a single dimension."""

    dimension: DimensionName
    base_weight: float = 0.25
    evolved_weight: float = 0.25
    quality_score: float = 0.0
    sample_count: int = 0
    decay_applied: bool = False
    variance_damped: bool = False
    sample_gated: bool = False
    explanation: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_weight", max(0.0, min(1.0, self.base_weight)))
        object.__setattr__(self, "evolved_weight", max(0.0, min(1.0, self.evolved_weight)))
        object.__setattr__(self, "quality_score", max(-1.0, min(1.0, self.quality_score)))

    @property
    def delta(self) -> float:
        return self.evolved_weight - self.base_weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "base_weight": round(self.base_weight, 4),
            "evolved_weight": round(self.evolved_weight, 4),
            "quality_score": round(self.quality_score, 4),
            "sample_count": self.sample_count,
            "decay_applied": self.decay_applied,
            "variance_damped": self.variance_damped,
            "sample_gated": self.sample_gated,
            "delta": round(self.delta, 4),
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class WeightEvolutionResult:
    """Complete evolution result across all dimensions."""

    evolutions: dict[str, DimensionEvolution]
    evolved_weights: DimensionWeightVector
    config: WeightEvolutionConfig = DEFAULT_EVOLUTION_CONFIG
    total_observations: int = 0
    explanation: str = ""

    def get(self, dimension: DimensionName) -> DimensionEvolution | None:
        return self.evolutions.get(dimension.value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evolutions": {k: v.to_dict() for k, v in sorted(self.evolutions.items())},
            "evolved_weights": self.evolved_weights.to_dict(),
            "config": self.config.to_dict(),
            "total_observations": self.total_observations,
            "explanation": self.explanation,
        }


# ── Core computation ─────────────────────────────────────────────────


def _compute_decayed_quality(
    observations: list[WeightObservation],
    current_tick: int,
    decay_rate: float,
) -> float:
    """Compute time-decayed quality score for a set of observations.

    quality = weighted_mean(outcome_score * direction_signal),
    weighted by decay_rate ^ (current_tick - obs.tick).
    """
    if not observations:
        return 0.0

    total_weight = 0.0
    total_signal = 0.0

    for obs in observations:
        age = max(0, current_tick - obs.tick)
        decay = decay_rate**age
        signal = obs.outcome_score * obs.direction_signal
        total_signal += signal * decay
        total_weight += decay

    if total_weight <= 0.0:
        return 0.0

    return total_signal / total_weight


def _compute_signal_variance(observations: list[WeightObservation]) -> float:
    """Compute variance of (outcome_score * direction_signal) across observations."""
    if len(observations) < 2:
        return 0.0

    signals = [obs.outcome_score * obs.direction_signal for obs in observations]
    mean = sum(signals) / len(signals)
    return sum((s - mean) ** 2 for s in signals) / len(signals)


def _evolve_single_dimension(
    dimension: DimensionName,
    base_weight: float,
    observations: list[WeightObservation],
    current_tick: int,
    config: WeightEvolutionConfig,
    adaptive_config: Any | None = None,
    confidence: float = 0.0,
    regime_factor: float = 1.0,
) -> DimensionEvolution:
    """Evolve weight for a single dimension from its observations.

    Deterministic (inv 269). No mutation (inv 270).
    When adaptive_config is provided and enabled, learning rate is modulated
    by confidence, signal stability, and regime factor (inv 284-293, 294-302).
    """
    sample_count = len(observations)

    if sample_count < config.min_samples:
        return DimensionEvolution(
            dimension=dimension,
            base_weight=base_weight,
            evolved_weight=base_weight,
            quality_score=0.0,
            sample_count=sample_count,
            sample_gated=True,
            explanation=f"sample_count={sample_count}<{config.min_samples}: gated to base",
        )

    quality = _compute_decayed_quality(observations, current_tick, config.decay_rate)
    variance = _compute_signal_variance(observations)
    decay_applied = config.decay_rate < 1.0

    effective_rate = config.learning_rate
    adaptive_result = None

    if adaptive_config is not None and getattr(adaptive_config, "enabled", False):
        from umh.runtime.adaptive_learning import compute_adaptive_rate

        adaptive_result = compute_adaptive_rate(
            observations=observations,
            confidence=confidence,
            config=adaptive_config,
            regime_factor=regime_factor,
        )
        effective_rate = adaptive_result.adaptive_rate

    delta = effective_rate * quality

    variance_damped = False
    if variance > config.variance_damping_threshold:
        delta *= _VARIANCE_DAMPING_FACTOR
        variance_damped = True

    evolved = base_weight + delta

    lo = max(0.0, 1.0 - config.max_adjustment) * base_weight / 0.25 if base_weight > 0 else 0.0
    hi = min(1.0, 1.0 + config.max_adjustment) * base_weight / 0.25 if base_weight > 0 else 0.0

    lower_bound = max(0.0, base_weight - config.max_adjustment)
    upper_bound = min(1.0, base_weight + config.max_adjustment)
    evolved = max(lower_bound, min(upper_bound, evolved))

    parts = [
        f"quality={quality:.4f}",
        f"delta={delta:.4f}",
        f"samples={sample_count}",
    ]
    if adaptive_result is not None:
        parts.append(f"adaptive_rate={effective_rate:.6f}")
        parts.append(f"conf={adaptive_result.confidence_factor:.3f}")
        parts.append(f"stab={adaptive_result.stability_factor:.3f}")
    if decay_applied:
        parts.append(f"decay={config.decay_rate}")
    if variance_damped:
        parts.append(f"variance={variance:.4f}>threshold, damped")

    return DimensionEvolution(
        dimension=dimension,
        base_weight=base_weight,
        evolved_weight=evolved,
        quality_score=quality,
        sample_count=sample_count,
        decay_applied=decay_applied,
        variance_damped=variance_damped,
        sample_gated=False,
        explanation="; ".join(parts),
    )


def evolve_weights(
    base_weights: DimensionWeightVector | None = None,
    observations: list[WeightObservation] | None = None,
    current_tick: int = 0,
    config: WeightEvolutionConfig | None = None,
    adaptive_config: Any | None = None,
    dimension_confidences: dict[str, float] | None = None,
    regime_factor: float = 1.0,
) -> WeightEvolutionResult:
    """Evolve dimension weights based on historical observations.

    Deterministic (inv 269). Missing history → default weights (inv 272).
    No cross-dimension contamination (inv 273).
    Bounded evolution (inv 265). No runaway amplification (inv 266).
    When adaptive_config is provided and enabled, learning rate adapts per-dimension
    based on confidence and signal stability (inv 284-293).
    """
    cfg = config or DEFAULT_EVOLUTION_CONFIG
    base = base_weights or default_weight_vector()
    obs_list = observations or []
    dim_conf = dimension_confidences or {}

    if not cfg.enabled:
        return WeightEvolutionResult(
            evolutions={
                dim.value: DimensionEvolution(
                    dimension=dim,
                    base_weight=base.get_weight(dim),
                    evolved_weight=base.get_weight(dim),
                    explanation="evolution disabled",
                )
                for dim in DimensionName
            },
            evolved_weights=base,
            config=cfg,
            total_observations=len(obs_list),
            explanation="evolution disabled",
        )

    if not obs_list:
        return WeightEvolutionResult(
            evolutions={
                dim.value: DimensionEvolution(
                    dimension=dim,
                    base_weight=base.get_weight(dim),
                    evolved_weight=base.get_weight(dim),
                    explanation="no observations",
                )
                for dim in DimensionName
            },
            evolved_weights=base,
            config=cfg,
            total_observations=0,
            explanation="no observations: using base weights",
        )

    dim_obs: dict[DimensionName, list[WeightObservation]] = {dim: [] for dim in DimensionName}
    for obs in obs_list:
        dim_obs[obs.dimension].append(obs)

    evolutions: dict[str, DimensionEvolution] = {}
    evolved_weights_dict: dict[str, DimensionWeight] = {}
    explanation_parts: list[str] = []

    for dim in sorted(DimensionName, key=lambda d: d.value):
        bw = base.get_weight(dim)
        evo = _evolve_single_dimension(
            dimension=dim,
            base_weight=bw,
            observations=dim_obs[dim],
            current_tick=current_tick,
            config=cfg,
            adaptive_config=adaptive_config,
            confidence=dim_conf.get(dim.value, 0.0),
            regime_factor=regime_factor,
        )
        evolutions[dim.value] = evo

        base_dw = base.get(dim)
        evolved_weights_dict[dim.value] = DimensionWeight(
            dimension=dim,
            weight=evo.evolved_weight,
            confidence=base_dw.confidence if base_dw else 0.0,
            source="evolved"
            if evo.evolved_weight != bw
            else (base_dw.source if base_dw else "default"),
        )

        if evo.sample_gated:
            explanation_parts.append(f"{dim.value}=gated({evo.sample_count})")
        else:
            explanation_parts.append(
                f"{dim.value}={evo.evolved_weight:.4f}(q={evo.quality_score:.3f})"
            )

    evolved_vector = DimensionWeightVector(
        weights=evolved_weights_dict,
        normalized=False,
        explanation=f"evolved: {'; '.join(explanation_parts)}",
    )

    return WeightEvolutionResult(
        evolutions=evolutions,
        evolved_weights=evolved_vector,
        config=cfg,
        total_observations=len(obs_list),
        explanation=f"evolved from {len(obs_list)} observations at tick={current_tick}",
    )
