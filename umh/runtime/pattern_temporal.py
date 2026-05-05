"""Temporal pattern weighting — exponential decay for pattern age.

Introduces time-based decay so recent patterns weigh more than older ones
while old patterns fade gradually without hard cutoffs or deletion.
Supports adaptive half-life (Phase 71), regime-specific half-life
(Phase 72), and pattern-specific half-life (Phase 73) for
environment-responsive and pattern-responsive decay.

Design principles:
    - Off by default (enabled must be explicitly True)
    - Exponential decay: decay_factor = exp(-ln(2) * age / half_life)
    - Age = current_observation_index - pattern_last_seen_index
    - Index-based, not wall-clock — deterministic (inv 347)
    - Floor: weight >= min_weight × similarity — old patterns never zero (inv 350)
    - No mutation of stored records (inv 348)
    - Decay independent of scoring (inv 349)
    - Explainable: each pattern reports age, decay_factor, pre/post weights (inv 351)
    - Optional adaptive half-life override (Phase 71, inv 353-362)
    - Optional regime-specific half-life override (Phase 72, inv 363-372)
    - Optional pattern-specific half-life override (Phase 73, inv 373-382)

Invariants 344-382.

Pure computation — no I/O, no child processes.
No imports from cell, environment, or adapter layers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from umh.runtime.adaptive_half_life import AdaptiveHalfLifeResult
from umh.runtime.pattern_half_life import PatternHalfLifeResult
from umh.runtime.regime_half_life import RegimeHalfLifeResult


@dataclass(frozen=True)
class TemporalPatternConfig:
    """Configuration for temporal pattern weighting."""

    enabled: bool = False
    half_life: int = 50
    min_weight: float = 0.05
    max_weight: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "half_life", max(1, self.half_life))
        object.__setattr__(self, "min_weight", max(0.0, min(1.0, self.min_weight)))
        object.__setattr__(self, "max_weight", max(self.min_weight, min(1.0, self.max_weight)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "half_life": self.half_life,
            "min_weight": round(self.min_weight, 4),
            "max_weight": round(self.max_weight, 4),
        }


@dataclass(frozen=True)
class TemporalContribution:
    """Per-pattern temporal decay details for explainability (inv 351)."""

    key: str = ""
    age: int = 0
    decay_factor: float = 1.0
    pre_decay_weight: float = 0.0
    final_weight: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "age": self.age,
            "decay_factor": round(self.decay_factor, 6),
            "pre_decay_weight": round(self.pre_decay_weight, 6),
            "final_weight": round(self.final_weight, 6),
        }


@dataclass(frozen=True)
class TemporalWeightingResult:
    """Result of applying temporal decay to pattern weights."""

    applied: bool = False
    weights: tuple[float, ...] = ()
    contributions: tuple[TemporalContribution, ...] = ()
    effective_half_life: int = 50
    adaptive_applied: bool = False
    regime_applied: bool = False
    pattern_applied: bool = False
    reason_if_not_applied: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "applied": self.applied,
            "weights": tuple(round(w, 6) for w in self.weights),
            "contributions": [c.to_dict() for c in self.contributions],
            "effective_half_life": self.effective_half_life,
            "adaptive_applied": self.adaptive_applied,
            "regime_applied": self.regime_applied,
            "pattern_applied": self.pattern_applied,
            "reason_if_not_applied": self.reason_if_not_applied,
        }


_LN2: float = math.log(2.0)


def compute_decay_factor(
    age: int,
    half_life: int,
) -> float:
    """Compute exponential decay factor for a given age (inv 344, 347)."""
    if age <= 0:
        return 1.0
    if half_life <= 0:
        return 1.0
    raw = math.exp(-_LN2 * age / half_life)
    return max(0.0, min(1.0, raw))


def apply_temporal_weights(
    raw_weights: list[float],
    pattern_keys: list[str],
    pattern_ages: list[int],
    similarities: list[float],
    config: TemporalPatternConfig | None = None,
    adaptive_result: AdaptiveHalfLifeResult | None = None,
    regime_result: RegimeHalfLifeResult | None = None,
    pattern_half_life_results: list[PatternHalfLifeResult] | None = None,
) -> TemporalWeightingResult:
    """Apply temporal decay to raw pattern weights.

    raw_weights: similarity × confidence per pattern (from Phase 69)
    pattern_keys: string key per pattern (for explainability)
    pattern_ages: age in observations per pattern (current_index - last_seen)
    similarities: per-pattern similarity (for floor computation)
    config: temporal config (defaults to disabled)
    adaptive_result: optional Phase 71 adaptive half-life override
    regime_result: optional Phase 72 regime-specific half-life override
    pattern_half_life_results: optional Phase 73 per-pattern half-life

    Half-life priority:
        1. config.half_life (base)
        2. adaptive_result (volatility adjustment)
        3. regime_result (regime adjustment)
        4. pattern_half_life_results (per-pattern refinement)

    Returns decayed weights (not yet normalized — caller normalizes).
    """
    cfg = config or TemporalPatternConfig()

    if not cfg.enabled:
        return TemporalWeightingResult(
            applied=False,
            weights=tuple(raw_weights),
            effective_half_life=cfg.half_life,
            reason_if_not_applied="temporal weighting disabled",
        )

    n = len(raw_weights)
    if n == 0:
        return TemporalWeightingResult(
            applied=False,
            weights=(),
            effective_half_life=cfg.half_life,
            reason_if_not_applied="no patterns to weight",
        )

    if len(pattern_ages) != n or len(similarities) != n or len(pattern_keys) != n:
        return TemporalWeightingResult(
            applied=False,
            weights=tuple(raw_weights),
            effective_half_life=cfg.half_life,
            reason_if_not_applied="array length mismatch",
        )

    adaptive_applied = False
    regime_applied = False

    if regime_result is not None and regime_result.applied:
        global_hl = regime_result.final_half_life
        regime_applied = True
        adaptive_applied = regime_result.volatility_half_life != regime_result.base_half_life
    elif adaptive_result is not None and adaptive_result.applied:
        global_hl = adaptive_result.computed_half_life
        adaptive_applied = True
    else:
        global_hl = cfg.half_life

    pattern_applied = False
    per_pattern_hl: list[int] | None = None
    if pattern_half_life_results is not None and len(pattern_half_life_results) == n:
        per_pattern_hl = []
        for phr in pattern_half_life_results:
            if not phr.used_fallback:
                per_pattern_hl.append(phr.pattern_half_life)
                pattern_applied = True
            else:
                per_pattern_hl.append(global_hl)

    decayed: list[float] = []
    contributions: list[TemporalContribution] = []

    for i in range(n):
        effective_hl = per_pattern_hl[i] if per_pattern_hl is not None else global_hl
        age = max(0, pattern_ages[i])
        decay = compute_decay_factor(age, effective_hl)
        decay = max(cfg.min_weight, min(cfg.max_weight, decay))

        pre_decay = raw_weights[i]
        weighted = pre_decay * decay
        floor = cfg.min_weight * similarities[i]
        final = max(weighted, floor)

        decayed.append(final)
        contributions.append(
            TemporalContribution(
                key=pattern_keys[i],
                age=age,
                decay_factor=decay,
                pre_decay_weight=pre_decay,
                final_weight=final,
            )
        )

    return TemporalWeightingResult(
        applied=True,
        weights=tuple(decayed),
        contributions=tuple(contributions),
        effective_half_life=global_hl,
        adaptive_applied=adaptive_applied,
        regime_applied=regime_applied,
        pattern_applied=pattern_applied,
    )
