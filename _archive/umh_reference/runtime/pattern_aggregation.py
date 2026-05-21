"""Multi-pattern aggregation — weighted blending of multiple pattern influences.

Given multiple PatternMatch results from Phase 67, computes a single
aggregated factor by blending individual pattern contributions weighted
by similarity × confidence, with optional temporal decay (Phase 70).

Design principles:
    - Off by default (enabled must be explicitly True)
    - All Phase 68 gates apply per-pattern
    - Weights = similarity × confidence, normalized to sum=1.0
    - Optional temporal decay: weight × decay_factor (Phase 70, inv 344-352)
    - Dominance cap: no single pattern > 70% weight (renormalize)
    - Max 5 patterns used
    - Final factor clamped to [0.9, 1.1]
    - Read-only: never mutates pattern memory (inv 339)
    - Deterministic ordering (inv 337)

Invariants 334-352.

Pure computation — no I/O, no child processes.
No imports from cell, environment, or adapter layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.runtime.pattern_influence import PatternInfluenceConfig
from umh.runtime.pattern_matching import PatternMatch, PatternResult
from umh.runtime.pattern_temporal import (
    TemporalContribution,
    TemporalPatternConfig,
    apply_temporal_weights,
)

_FACTOR_FLOOR: float = 0.9
_FACTOR_CEILING: float = 1.1
_MAX_PATTERNS: int = 5
_DOMINANCE_CAP: float = 0.7


@dataclass(frozen=True)
class PatternContribution:
    """One pattern's contribution to the aggregated factor."""

    key: str = ""
    similarity: float = 0.0
    confidence: float = 0.0
    raw_weight: float = 0.0
    normalized_weight: float = 0.0
    individual_factor: float = 1.0
    contribution: float = 0.0
    age: int = 0
    decay_factor: float = 1.0
    pre_decay_weight: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "similarity": round(self.similarity, 4),
            "confidence": round(self.confidence, 4),
            "raw_weight": round(self.raw_weight, 4),
            "normalized_weight": round(self.normalized_weight, 4),
            "individual_factor": round(self.individual_factor, 6),
            "contribution": round(self.contribution, 6),
            "age": self.age,
            "decay_factor": round(self.decay_factor, 6),
            "pre_decay_weight": round(self.pre_decay_weight, 6),
        }


@dataclass(frozen=True)
class PatternAggregationResult:
    """Result of multi-pattern aggregation."""

    final_factor: float = 1.0
    applied: bool = False
    contributions: tuple[PatternContribution, ...] = ()
    patterns_used: int = 0
    dominance_capped: bool = False
    temporal_applied: bool = False
    reason_if_not_applied: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "final_factor", max(_FACTOR_FLOOR, min(_FACTOR_CEILING, self.final_factor))
        )
        object.__setattr__(self, "patterns_used", max(0, self.patterns_used))

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_factor": round(self.final_factor, 6),
            "applied": self.applied,
            "contributions": [c.to_dict() for c in self.contributions],
            "patterns_used": self.patterns_used,
            "dominance_capped": self.dominance_capped,
            "temporal_applied": self.temporal_applied,
            "reason_if_not_applied": self.reason_if_not_applied,
        }


def _neutral(reason: str) -> PatternAggregationResult:
    return PatternAggregationResult(final_factor=1.0, applied=False, reason_if_not_applied=reason)


def _compute_individual_factor(
    avg_score: float,
    baseline_score: float,
    max_adjustment: float,
) -> float:
    signal = avg_score - baseline_score
    clamped = max(-max_adjustment, min(max_adjustment, signal))
    raw = 1.0 + clamped
    return max(_FACTOR_FLOOR, min(_FACTOR_CEILING, raw))


def _apply_dominance_cap(
    weights: list[float],
) -> tuple[list[float], bool]:
    """Renormalize weights so no single weight exceeds _DOMINANCE_CAP.

    Uses iterative cap-and-redistribute: lock weights at cap, redistribute
    remaining budget among uncapped weights proportionally.
    """
    if not weights:
        return weights, False

    if max(weights) <= _DOMINANCE_CAP:
        return weights, False

    n = len(weights)
    result = list(weights)
    locked = [False] * n

    for _ in range(n):
        budget = 1.0
        unlocked_total = 0.0
        for i in range(n):
            if result[i] >= _DOMINANCE_CAP:
                result[i] = _DOMINANCE_CAP
                locked[i] = True
                budget -= _DOMINANCE_CAP
            else:
                unlocked_total += result[i]

        if unlocked_total <= 0:
            for i in range(n):
                if not locked[i]:
                    result[i] = budget / max(1, sum(1 for x in locked if not x))
            break

        scale = budget / unlocked_total
        for i in range(n):
            if not locked[i]:
                result[i] *= scale

        if max(result) <= _DOMINANCE_CAP + 1e-12:
            break

    total = sum(result)
    if total > 0:
        result = [w / total for w in result]

    return result, True


def compute_pattern_aggregation(
    pattern_result: PatternResult | None = None,
    baseline_score: float = 0.0,
    config: PatternInfluenceConfig | None = None,
    temporal_config: TemporalPatternConfig | None = None,
    current_observation_index: int = 0,
    pattern_last_seen: dict[str, int] | None = None,
) -> PatternAggregationResult:
    """Compute aggregated pattern factor from multiple pattern matches.

    Uses all qualifying matches from PatternResult (up to _MAX_PATTERNS),
    weights by similarity × confidence, optionally applies temporal decay
    (Phase 70), applies dominance cap, blends individual factors into a
    single aggregated factor.

    Gate order per pattern (Phase 68 gates):
        1. config.enabled must be True
        2. match.sample_size >= config.min_samples
        3. pattern_result.confidence >= config.min_confidence (global)
        4. match.similarity >= config.similarity_threshold
        5. match.stats must exist

    Temporal weighting (Phase 70, applied before normalization):
        - decay_factor = exp(-ln(2) * age / half_life)
        - weight_i = raw_weight_i × decay_factor
        - floor: weight_i >= min_weight × similarity_i
        - Dominance cap applied AFTER temporal weighting
    """
    cfg = config or PatternInfluenceConfig()

    if not cfg.enabled:
        return _neutral("pattern influence disabled")

    if pattern_result is None:
        return _neutral("no pattern result provided")

    if not pattern_result.matched:
        return _neutral("no pattern matched")

    if not pattern_result.all_matches:
        return _neutral("no matches in pattern result")

    qualifying: list[PatternMatch] = []
    for m in pattern_result.all_matches:
        if m.sample_size < cfg.min_samples:
            continue
        if m.similarity < cfg.similarity_threshold:
            continue
        if m.stats is None:
            continue
        qualifying.append(m)

    if not qualifying:
        return _neutral("no qualifying patterns after gating")

    qualifying = sorted(qualifying, key=lambda m: (-m.similarity, m.matched_key.to_tuple()))
    qualifying = qualifying[:_MAX_PATTERNS]

    if pattern_result.confidence < cfg.min_confidence:
        return _neutral(
            f"confidence {pattern_result.confidence:.4f} < min_confidence {cfg.min_confidence:.4f}"
        )

    raw_weights = [m.similarity * pattern_result.confidence for m in qualifying]
    total_raw = sum(raw_weights)

    if total_raw <= 0:
        return _neutral("total raw weight is zero")

    t_cfg = temporal_config or TemporalPatternConfig()
    last_seen = pattern_last_seen or {}
    temporal_applied = False
    temporal_contributions: list[TemporalContribution] = []

    if t_cfg.enabled:
        keys = [str(m.matched_key.to_tuple()) for m in qualifying]
        ages = [
            max(0, current_observation_index - last_seen.get(k, current_observation_index))
            for k in keys
        ]
        sims = [m.similarity for m in qualifying]

        t_result = apply_temporal_weights(
            raw_weights=raw_weights,
            pattern_keys=keys,
            pattern_ages=ages,
            similarities=sims,
            config=t_cfg,
        )
        if t_result.applied:
            raw_weights = list(t_result.weights)
            temporal_applied = True
            temporal_contributions = list(t_result.contributions)
            total_raw = sum(raw_weights)
            if total_raw <= 0:
                return _neutral("total weight is zero after temporal decay")

    norm_weights = [w / total_raw for w in raw_weights]

    norm_weights, dominance_capped = _apply_dominance_cap(norm_weights)

    individual_factors = []
    for m in qualifying:
        assert m.stats is not None
        f = _compute_individual_factor(m.stats.avg_score, baseline_score, cfg.max_adjustment)
        individual_factors.append(f)

    weighted_sum = sum(nw * f for nw, f in zip(norm_weights, individual_factors))
    final_factor = max(_FACTOR_FLOOR, min(_FACTOR_CEILING, weighted_sum))

    contributions = []
    for i, m in enumerate(qualifying):
        tc = temporal_contributions[i] if i < len(temporal_contributions) else None
        contributions.append(
            PatternContribution(
                key=str(m.matched_key.to_tuple()),
                similarity=m.similarity,
                confidence=pattern_result.confidence,
                raw_weight=raw_weights[i] if i < len(raw_weights) else 0.0,
                normalized_weight=norm_weights[i],
                individual_factor=individual_factors[i],
                contribution=norm_weights[i] * individual_factors[i],
                age=tc.age if tc else 0,
                decay_factor=tc.decay_factor if tc else 1.0,
                pre_decay_weight=tc.pre_decay_weight if tc else raw_weights[i],
            )
        )

    return PatternAggregationResult(
        final_factor=final_factor,
        applied=True,
        contributions=tuple(contributions),
        patterns_used=len(qualifying),
        dominance_capped=dominance_capped,
        temporal_applied=temporal_applied,
    )
