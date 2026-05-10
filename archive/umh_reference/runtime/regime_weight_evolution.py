"""Regime-scoped weight evolution — per-regime temporal adaptation of dimension weights.

Extends Phase 62 (global temporal evolution) with regime-conditioned learning.
Weights evolve independently per regime (STABLE, TREND_UP, etc.), with smooth
blending between regime-specific and global weights based on sample availability.

Key mechanics:
    - Per-regime observation tracking: each observation tagged with its regime
    - Regime-specific evolution: reuses Phase 62 _evolve_single_dimension
    - Blend factor: clamp(regime_samples / (2 * min_samples), 0, 1)
    - Final weight = blend * regime_weight + (1 - blend) * global_weight
    - Step-change clamping: |weight_t - weight_t-1| <= max_step_change (inv 281)
    - Neutral regime always neutral (inv 282)

Pure computation — no I/O, no child processes.
No imports from cell, environment, or adapter layers.
No circular dependency: reads weight_evolution, dimension_weighting, regime types only.
Never mutates historical data (inv 279).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.runtime.dimension_weighting import (
    DimensionWeight,
    DimensionWeightVector,
    default_weight_vector,
)
from umh.runtime.regime import RegimeType
from umh.runtime.regime_aggregation import DimensionName
from umh.runtime.weight_evolution import (
    DEFAULT_EVOLUTION_CONFIG,
    WeightEvolutionConfig,
    WeightObservation,
    _compute_decayed_quality,
    _compute_signal_variance,
    _evolve_single_dimension,
    evolve_weights,
)

_DEFAULT_MAX_STEP_CHANGE: float = 0.05
_DEFAULT_BLEND_SCALE: float = 2.0


@dataclass(frozen=True)
class RegimeWeightEvolutionConfig:
    """Configuration for regime-scoped weight evolution."""

    enabled: bool = False
    evolution_config: WeightEvolutionConfig = DEFAULT_EVOLUTION_CONFIG
    max_step_change: float = _DEFAULT_MAX_STEP_CHANGE
    blend_scale: float = _DEFAULT_BLEND_SCALE

    def __post_init__(self) -> None:
        object.__setattr__(self, "max_step_change", max(0.001, min(0.50, self.max_step_change)))
        object.__setattr__(self, "blend_scale", max(1.0, min(10.0, self.blend_scale)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "evolution_config": self.evolution_config.to_dict(),
            "max_step_change": round(self.max_step_change, 4),
            "blend_scale": round(self.blend_scale, 4),
        }


DEFAULT_REGIME_EVOLUTION_CONFIG = RegimeWeightEvolutionConfig()


@dataclass(frozen=True)
class RegimeObservation:
    """A weight observation tagged with its regime context."""

    observation: WeightObservation
    regime: RegimeType

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation": self.observation.to_dict(),
            "regime": self.regime.value,
        }


@dataclass(frozen=True)
class RegimeDimensionEvolution:
    """Evolution result for a single dimension within a specific regime context."""

    dimension: DimensionName
    regime: RegimeType | None = None
    global_weight: float = 0.25
    regime_weight: float = 0.25
    blended_weight: float = 0.25
    final_weight: float = 0.25
    blend_factor: float = 0.0
    regime_sample_count: int = 0
    global_sample_count: int = 0
    regime_quality: float = 0.0
    global_quality: float = 0.0
    step_clamped: bool = False
    explanation: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "global_weight", max(0.0, min(1.0, self.global_weight)))
        object.__setattr__(self, "regime_weight", max(0.0, min(1.0, self.regime_weight)))
        object.__setattr__(self, "blended_weight", max(0.0, min(1.0, self.blended_weight)))
        object.__setattr__(self, "final_weight", max(0.0, min(1.0, self.final_weight)))
        object.__setattr__(self, "blend_factor", max(0.0, min(1.0, self.blend_factor)))
        object.__setattr__(self, "regime_quality", max(-1.0, min(1.0, self.regime_quality)))
        object.__setattr__(self, "global_quality", max(-1.0, min(1.0, self.global_quality)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "regime": self.regime.value if self.regime else None,
            "global_weight": round(self.global_weight, 4),
            "regime_weight": round(self.regime_weight, 4),
            "blended_weight": round(self.blended_weight, 4),
            "final_weight": round(self.final_weight, 4),
            "blend_factor": round(self.blend_factor, 4),
            "regime_sample_count": self.regime_sample_count,
            "global_sample_count": self.global_sample_count,
            "regime_quality": round(self.regime_quality, 4),
            "global_quality": round(self.global_quality, 4),
            "step_clamped": self.step_clamped,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class RegimeWeightEvolutionResult:
    """Complete regime-scoped evolution result."""

    evolutions: dict[str, RegimeDimensionEvolution]
    evolved_weights: DimensionWeightVector
    active_regime: RegimeType | None = None
    config: RegimeWeightEvolutionConfig = DEFAULT_REGIME_EVOLUTION_CONFIG
    total_observations: int = 0
    regime_observation_counts: dict[str, int] = field(default_factory=dict)
    explanation: str = ""

    def get(self, dimension: DimensionName) -> RegimeDimensionEvolution | None:
        return self.evolutions.get(dimension.value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evolutions": {k: v.to_dict() for k, v in sorted(self.evolutions.items())},
            "evolved_weights": self.evolved_weights.to_dict(),
            "active_regime": self.active_regime.value if self.active_regime else None,
            "config": self.config.to_dict(),
            "total_observations": self.total_observations,
            "regime_observation_counts": dict(sorted(self.regime_observation_counts.items())),
            "explanation": self.explanation,
        }


# ── Core computation ─────────────────────────────────────────────────


def _compute_blend_factor(
    regime_sample_count: int,
    min_samples: int,
    blend_scale: float,
) -> float:
    """Compute blend factor for regime vs global weight mixing.

    blend = clamp(regime_samples / (blend_scale * min_samples), 0, 1)
    0 = pure global, 1 = pure regime-specific.
    """
    if min_samples <= 0:
        return 0.0
    denominator = blend_scale * min_samples
    if denominator <= 0.0:
        return 0.0
    return max(0.0, min(1.0, regime_sample_count / denominator))


def _apply_step_change_clamp(
    new_weight: float,
    previous_weight: float,
    max_step_change: float,
) -> tuple[float, bool]:
    """Clamp weight change to max_step_change per evolution step.

    Returns (clamped_weight, was_clamped).
    """
    delta = new_weight - previous_weight
    if abs(delta) <= max_step_change:
        return new_weight, False
    clamped = previous_weight + max_step_change * (1.0 if delta > 0 else -1.0)
    return max(0.0, min(1.0, clamped)), True


def _is_neutral_regime(regime: RegimeType) -> bool:
    return regime is RegimeType.STABLE


def evolve_regime_weights(
    base_weights: DimensionWeightVector | None = None,
    observations: list[RegimeObservation] | None = None,
    current_tick: int = 0,
    active_regime: RegimeType | None = None,
    previous_weights: DimensionWeightVector | None = None,
    config: RegimeWeightEvolutionConfig | None = None,
    adaptive_config: Any | None = None,
    dimension_confidences: dict[str, float] | None = None,
    regime_adaptive_config: Any | None = None,
    previous_regime_factor: float = 1.0,
) -> RegimeWeightEvolutionResult:
    """Evolve dimension weights with regime-specific conditioning.

    Algorithm:
        1. Split observations by regime
        2. Evolve global weights (all observations, Phase 62 logic)
        3. Evolve regime-specific weights (regime observations only)
        4. Blend: final = blend * regime + (1 - blend) * global
        5. Apply step-change clamp against previous weights
        6. Neutral regime → no regime-specific evolution (inv 282)

    Deterministic (inv 278). No mutation (inv 279). Bounded (inv 274, 275).
    No cross-regime contamination (inv 277). Explainable (inv 280).
    When adaptive_config is provided and enabled, learning rate adapts
    per-dimension based on confidence and signal stability (inv 284-293).
    When regime_adaptive_config is provided and enabled, learning rate is
    further modulated by regime-specific factors (inv 294-302).
    """
    cfg = config or DEFAULT_REGIME_EVOLUTION_CONFIG
    base = base_weights or default_weight_vector()
    obs_list = observations or []
    prev = previous_weights or base
    regime = active_regime

    if not cfg.enabled:
        return _disabled_result(base, regime, cfg, obs_list)

    all_weight_obs = [ro.observation for ro in obs_list]

    global_evo_config = WeightEvolutionConfig(
        enabled=True,
        decay_rate=cfg.evolution_config.decay_rate,
        learning_rate=cfg.evolution_config.learning_rate,
        min_samples=cfg.evolution_config.min_samples,
        max_adjustment=cfg.evolution_config.max_adjustment,
        variance_damping_threshold=cfg.evolution_config.variance_damping_threshold,
    )

    regime_obs_map: dict[RegimeType, list[WeightObservation]] = {rt: [] for rt in RegimeType}
    for ro in obs_list:
        regime_obs_map[ro.regime].append(ro.observation)
    regime_obs_counts: dict[str, int] = {rt.value: len(obs) for rt, obs in regime_obs_map.items()}

    resolved_regime_factor = 1.0
    if regime_adaptive_config is not None and getattr(regime_adaptive_config, "enabled", False):
        from umh.runtime.regime_adaptive_learning import (
            _resolve_regime_factor,
            _smooth_regime_factor,
        )

        active_count = regime_obs_counts.get(regime.value, 0) if regime else 0
        raw_factor = _resolve_regime_factor(
            regime=regime,
            regime_sample_count=active_count,
            min_regime_samples=regime_adaptive_config.min_regime_samples,
            regime_factors=regime_adaptive_config.regime_factors,
        )
        resolved_regime_factor, _ = _smooth_regime_factor(
            target_factor=raw_factor,
            previous_factor=previous_regime_factor,
            max_delta=regime_adaptive_config.max_factor_delta,
        )

    global_result = evolve_weights(
        base_weights=base,
        observations=all_weight_obs,
        current_tick=current_tick,
        config=global_evo_config,
        adaptive_config=adaptive_config,
        dimension_confidences=dimension_confidences,
        regime_factor=resolved_regime_factor,
    )

    if regime is None or not obs_list:
        return _global_only_result(
            base,
            global_result,
            regime,
            cfg,
            obs_list,
            regime_obs_counts,
        )

    if _is_neutral_regime(regime):
        return _neutral_regime_result(
            base,
            global_result,
            regime,
            cfg,
            obs_list,
            regime_obs_counts,
            prev,
            cfg.max_step_change,
        )

    active_regime_obs = regime_obs_map[regime]

    regime_evo_result = evolve_weights(
        base_weights=base,
        observations=active_regime_obs,
        current_tick=current_tick,
        config=global_evo_config,
        adaptive_config=adaptive_config,
        dimension_confidences=dimension_confidences,
        regime_factor=resolved_regime_factor,
    )

    evolutions: dict[str, RegimeDimensionEvolution] = {}
    evolved_weights_dict: dict[str, DimensionWeight] = {}
    explanation_parts: list[str] = []

    for dim in sorted(DimensionName, key=lambda d: d.value):
        global_evo = global_result.get(dim)
        regime_evo = regime_evo_result.get(dim)

        g_weight = global_evo.evolved_weight if global_evo else base.get_weight(dim)
        r_weight = regime_evo.evolved_weight if regime_evo else base.get_weight(dim)
        g_quality = global_evo.quality_score if global_evo else 0.0
        r_quality = regime_evo.quality_score if regime_evo else 0.0
        g_samples = global_evo.sample_count if global_evo else 0
        r_samples = regime_evo.sample_count if regime_evo else 0

        dim_regime_obs_count = sum(1 for o in active_regime_obs if o.dimension is dim)

        blend = _compute_blend_factor(
            dim_regime_obs_count,
            cfg.evolution_config.min_samples,
            cfg.blend_scale,
        )

        blended = blend * r_weight + (1.0 - blend) * g_weight

        lower_bound = max(0.0, base.get_weight(dim) - cfg.evolution_config.max_adjustment)
        upper_bound = min(1.0, base.get_weight(dim) + cfg.evolution_config.max_adjustment)
        blended = max(lower_bound, min(upper_bound, blended))

        prev_w = prev.get_weight(dim)
        final, step_clamped = _apply_step_change_clamp(
            blended,
            prev_w,
            cfg.max_step_change,
        )

        parts = [f"blend={blend:.3f}"]
        if blend > 0:
            parts.append(f"regime_q={r_quality:.3f}")
        parts.append(f"global_q={g_quality:.3f}")
        if step_clamped:
            parts.append("step_clamped")

        evo = RegimeDimensionEvolution(
            dimension=dim,
            regime=regime,
            global_weight=g_weight,
            regime_weight=r_weight,
            blended_weight=blended,
            final_weight=final,
            blend_factor=blend,
            regime_sample_count=dim_regime_obs_count,
            global_sample_count=g_samples,
            regime_quality=r_quality,
            global_quality=g_quality,
            step_clamped=step_clamped,
            explanation="; ".join(parts),
        )
        evolutions[dim.value] = evo

        base_dw = base.get(dim)
        evolved_weights_dict[dim.value] = DimensionWeight(
            dimension=dim,
            weight=final,
            confidence=base_dw.confidence if base_dw else 0.0,
            source="regime_evolved"
            if final != base.get_weight(dim)
            else (base_dw.source if base_dw else "default"),
        )

        explanation_parts.append(f"{dim.value}={final:.4f}(b={blend:.2f})")

    evolved_vector = DimensionWeightVector(
        weights=evolved_weights_dict,
        normalized=False,
        explanation=f"regime_evolved({regime.value}): {'; '.join(explanation_parts)}",
    )

    return RegimeWeightEvolutionResult(
        evolutions=evolutions,
        evolved_weights=evolved_vector,
        active_regime=regime,
        config=cfg,
        total_observations=len(obs_list),
        regime_observation_counts=regime_obs_counts,
        explanation=(
            f"regime={regime.value}, "
            f"regime_obs={len(active_regime_obs)}, "
            f"global_obs={len(obs_list)}, "
            f"tick={current_tick}"
        ),
    )


# ── Internal result builders ─────────────────────────────────────────


def _disabled_result(
    base: DimensionWeightVector,
    regime: RegimeType | None,
    cfg: RegimeWeightEvolutionConfig,
    obs_list: list[RegimeObservation],
) -> RegimeWeightEvolutionResult:
    evolutions = {
        dim.value: RegimeDimensionEvolution(
            dimension=dim,
            regime=regime,
            global_weight=base.get_weight(dim),
            regime_weight=base.get_weight(dim),
            blended_weight=base.get_weight(dim),
            final_weight=base.get_weight(dim),
            explanation="regime evolution disabled",
        )
        for dim in DimensionName
    }
    return RegimeWeightEvolutionResult(
        evolutions=evolutions,
        evolved_weights=base,
        active_regime=regime,
        config=cfg,
        total_observations=len(obs_list),
        explanation="regime evolution disabled",
    )


def _global_only_result(
    base: DimensionWeightVector,
    global_result: Any,
    regime: RegimeType | None,
    cfg: RegimeWeightEvolutionConfig,
    obs_list: list[RegimeObservation],
    regime_obs_counts: dict[str, int],
) -> RegimeWeightEvolutionResult:
    evolutions: dict[str, RegimeDimensionEvolution] = {}
    evolved_weights_dict: dict[str, DimensionWeight] = {}

    for dim in sorted(DimensionName, key=lambda d: d.value):
        g_evo = global_result.get(dim)
        g_weight = g_evo.evolved_weight if g_evo else base.get_weight(dim)
        g_quality = g_evo.quality_score if g_evo else 0.0
        g_samples = g_evo.sample_count if g_evo else 0

        evolutions[dim.value] = RegimeDimensionEvolution(
            dimension=dim,
            regime=regime,
            global_weight=g_weight,
            regime_weight=g_weight,
            blended_weight=g_weight,
            final_weight=g_weight,
            blend_factor=0.0,
            global_sample_count=g_samples,
            global_quality=g_quality,
            explanation="global only: no regime context or no observations",
        )

        base_dw = base.get(dim)
        evolved_weights_dict[dim.value] = DimensionWeight(
            dimension=dim,
            weight=g_weight,
            confidence=base_dw.confidence if base_dw else 0.0,
            source="evolved"
            if g_weight != base.get_weight(dim)
            else (base_dw.source if base_dw else "default"),
        )

    evolved_vector = DimensionWeightVector(
        weights=evolved_weights_dict,
        normalized=False,
        explanation="global only: "
        + ("no regime context" if regime is None else "no observations"),
    )

    return RegimeWeightEvolutionResult(
        evolutions=evolutions,
        evolved_weights=evolved_vector,
        active_regime=regime,
        config=cfg,
        total_observations=len(obs_list),
        regime_observation_counts=regime_obs_counts,
        explanation="global only: " + ("no active regime" if regime is None else "no observations"),
    )


def _neutral_regime_result(
    base: DimensionWeightVector,
    global_result: Any,
    regime: RegimeType,
    cfg: RegimeWeightEvolutionConfig,
    obs_list: list[RegimeObservation],
    regime_obs_counts: dict[str, int],
    prev: DimensionWeightVector,
    max_step_change: float,
) -> RegimeWeightEvolutionResult:
    """Neutral regime (STABLE) uses global weights only, with step clamping."""
    evolutions: dict[str, RegimeDimensionEvolution] = {}
    evolved_weights_dict: dict[str, DimensionWeight] = {}

    for dim in sorted(DimensionName, key=lambda d: d.value):
        g_evo = global_result.get(dim)
        g_weight = g_evo.evolved_weight if g_evo else base.get_weight(dim)
        g_quality = g_evo.quality_score if g_evo else 0.0
        g_samples = g_evo.sample_count if g_evo else 0

        prev_w = prev.get_weight(dim)
        final, step_clamped = _apply_step_change_clamp(
            g_weight,
            prev_w,
            max_step_change,
        )

        evolutions[dim.value] = RegimeDimensionEvolution(
            dimension=dim,
            regime=regime,
            global_weight=g_weight,
            regime_weight=g_weight,
            blended_weight=g_weight,
            final_weight=final,
            blend_factor=0.0,
            global_sample_count=g_samples,
            global_quality=g_quality,
            step_clamped=step_clamped,
            explanation="neutral regime: global weights only"
            + ("; step_clamped" if step_clamped else ""),
        )

        base_dw = base.get(dim)
        evolved_weights_dict[dim.value] = DimensionWeight(
            dimension=dim,
            weight=final,
            confidence=base_dw.confidence if base_dw else 0.0,
            source="evolved"
            if final != base.get_weight(dim)
            else (base_dw.source if base_dw else "default"),
        )

    evolved_vector = DimensionWeightVector(
        weights=evolved_weights_dict,
        normalized=False,
        explanation=f"neutral regime ({regime.value}): global weights only",
    )

    return RegimeWeightEvolutionResult(
        evolutions=evolutions,
        evolved_weights=evolved_vector,
        active_regime=regime,
        config=cfg,
        total_observations=len(obs_list),
        regime_observation_counts=regime_obs_counts,
        explanation=f"neutral regime ({regime.value}): using global evolution only",
    )
