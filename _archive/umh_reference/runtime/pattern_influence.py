"""Pattern influence — bounded scoring adjustment from recognized patterns.

Given a PatternResult from Phase 67, computes a multiplicative factor
that nudges candidate scores based on historical pattern performance.

Design principles:
    - Off by default (enabled must be explicitly True)
    - 4-gate check: enabled, min_samples, min_confidence, similarity_threshold
    - Signal = pattern avg_score - candidate baseline
    - Factor = 1.0 + clamp(signal, -max_adjustment, +max_adjustment)
    - Hard safety clamp: factor ∈ [0.9, 1.1]
    - Read-only: never mutates pattern memory (inv 330, 331)
    - Deterministic (inv 328)

Invariants 323-333.

Pure computation — no I/O, no child processes.
No imports from cell, environment, or adapter layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.runtime.pattern_matching import PatternResult

_FACTOR_FLOOR: float = 0.9
_FACTOR_CEILING: float = 1.1


@dataclass(frozen=True)
class PatternInfluenceConfig:
    """Configuration for pattern influence layer."""

    enabled: bool = False
    min_samples: int = 10
    min_confidence: float = 0.6
    max_adjustment: float = 0.10
    similarity_threshold: float = 0.75

    def __post_init__(self) -> None:
        object.__setattr__(self, "min_samples", max(1, self.min_samples))
        object.__setattr__(self, "min_confidence", max(0.0, min(1.0, self.min_confidence)))
        object.__setattr__(self, "max_adjustment", max(0.0, min(0.2, self.max_adjustment)))
        object.__setattr__(
            self, "similarity_threshold", max(0.0, min(1.0, self.similarity_threshold))
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "min_samples": self.min_samples,
            "min_confidence": round(self.min_confidence, 4),
            "max_adjustment": round(self.max_adjustment, 4),
            "similarity_threshold": round(self.similarity_threshold, 4),
        }


@dataclass(frozen=True)
class PatternInfluenceResult:
    """Result of pattern influence computation."""

    factor: float = 1.0
    applied: bool = False
    reason_if_not_applied: str = ""
    contributing_pattern_key: str = ""
    sample_size: int = 0
    confidence: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "factor", max(_FACTOR_FLOOR, min(_FACTOR_CEILING, self.factor)))
        object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))
        object.__setattr__(self, "sample_size", max(0, self.sample_size))

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor": round(self.factor, 6),
            "applied": self.applied,
            "reason_if_not_applied": self.reason_if_not_applied,
            "contributing_pattern_key": self.contributing_pattern_key,
            "sample_size": self.sample_size,
            "confidence": round(self.confidence, 4),
        }


_NEUTRAL = PatternInfluenceResult(factor=1.0)


def _neutral(reason: str) -> PatternInfluenceResult:
    return PatternInfluenceResult(factor=1.0, applied=False, reason_if_not_applied=reason)


def compute_pattern_influence(
    pattern_result: PatternResult | None = None,
    candidate_score: float = 0.0,
    config: PatternInfluenceConfig | None = None,
) -> PatternInfluenceResult:
    """Compute pattern influence factor for a candidate score.

    Returns factor=1.0 (neutral) if any gate fails.
    Otherwise computes bounded adjustment from pattern signal.

    Gate order (inv 323-326):
        1. config.enabled must be True
        2. best_match.sample_size >= config.min_samples
        3. pattern_result.confidence >= config.min_confidence
        4. best_match.similarity >= config.similarity_threshold

    Signal (inv 327, 333):
        pattern_signal = pattern_avg_score - candidate_score
        factor = 1.0 + clamp(signal, -max_adjustment, +max_adjustment)
        factor = clamp(factor, 0.9, 1.1)
    """
    cfg = config or PatternInfluenceConfig()

    if not cfg.enabled:
        return _neutral("pattern influence disabled")

    if pattern_result is None:
        return _neutral("no pattern result provided")

    if not pattern_result.matched:
        return _neutral("no pattern matched")

    best = pattern_result.best_match
    if best is None:
        return _neutral("no best match in pattern result")

    if best.sample_size < cfg.min_samples:
        return _neutral(f"sample_size {best.sample_size} < min_samples {cfg.min_samples}")

    if pattern_result.confidence < cfg.min_confidence:
        return _neutral(
            f"confidence {pattern_result.confidence:.4f} < min_confidence {cfg.min_confidence:.4f}"
        )

    if best.similarity < cfg.similarity_threshold:
        return _neutral(
            f"similarity {best.similarity:.4f} < threshold {cfg.similarity_threshold:.4f}"
        )

    if best.stats is None:
        return _neutral("matched pattern has no stats")

    pattern_signal = best.stats.avg_score - candidate_score
    clamped_signal = max(-cfg.max_adjustment, min(cfg.max_adjustment, pattern_signal))
    raw_factor = 1.0 + clamped_signal
    factor = max(_FACTOR_FLOOR, min(_FACTOR_CEILING, raw_factor))

    key_str = str(best.matched_key.to_tuple())

    return PatternInfluenceResult(
        factor=factor,
        applied=True,
        contributing_pattern_key=key_str,
        sample_size=best.sample_size,
        confidence=pattern_result.confidence,
    )
