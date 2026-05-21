"""Pattern-specific half-life — per-pattern memory speed adjustment.

Refines the global/regime half-life on a per-pattern basis using each
pattern's historical reliability. Reliable patterns (consistent outcomes)
get longer memory; noisy patterns (high outcome variance) get shorter
memory. Patterns with insufficient samples fall back to the global
half-life.

Design principles:
    - Off by default (enabled must be explicitly True)
    - Multiplicative: pattern_hl = base_hl × multiplier
    - Reliability = 1 - noise, where noise = variance / 0.25
    - Low-sample patterns → fallback (inv 374)
    - Reliable patterns → longer memory (inv 375)
    - Noisy patterns → shorter memory (inv 376)
    - Clamped to [min_half_life, max_half_life] (inv 382)
    - No mutation of pattern records (inv 377)
    - Deterministic (inv 378)
    - Missing stats → neutral fallback (inv 379)
    - Explainable (inv 380)
    - No scoring feedback loop (inv 381)

Invariants 373-382.

Pure computation — no I/O, no child processes.
No imports from cell, environment, or adapter layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MAX_VARIANCE: float = 0.25


@dataclass(frozen=True)
class PatternHalfLifeConfig:
    """Configuration for pattern-specific half-life adjustment."""

    enabled: bool = False
    min_samples: int = 10
    base_multiplier: float = 1.0
    reliable_multiplier: float = 1.5
    noisy_multiplier: float = 0.6
    min_half_life: int = 10
    max_half_life: int = 250
    reliability_threshold: float = 0.70
    noise_threshold: float = 0.30

    def __post_init__(self) -> None:
        object.__setattr__(self, "min_samples", max(1, self.min_samples))
        object.__setattr__(self, "base_multiplier", max(0.01, min(10.0, self.base_multiplier)))
        object.__setattr__(
            self, "reliable_multiplier", max(0.01, min(10.0, self.reliable_multiplier))
        )
        object.__setattr__(self, "noisy_multiplier", max(0.01, min(10.0, self.noisy_multiplier)))
        object.__setattr__(self, "min_half_life", max(1, self.min_half_life))
        object.__setattr__(self, "max_half_life", max(self.min_half_life, self.max_half_life))
        object.__setattr__(
            self,
            "reliability_threshold",
            max(0.0, min(1.0, self.reliability_threshold)),
        )
        object.__setattr__(self, "noise_threshold", max(0.0, min(1.0, self.noise_threshold)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "min_samples": self.min_samples,
            "base_multiplier": round(self.base_multiplier, 4),
            "reliable_multiplier": round(self.reliable_multiplier, 4),
            "noisy_multiplier": round(self.noisy_multiplier, 4),
            "min_half_life": self.min_half_life,
            "max_half_life": self.max_half_life,
            "reliability_threshold": round(self.reliability_threshold, 4),
            "noise_threshold": round(self.noise_threshold, 4),
        }


@dataclass(frozen=True)
class PatternHalfLifeResult:
    """Result of pattern-specific half-life computation (inv 380)."""

    pattern_key: str = ""
    base_half_life: int = 50
    pattern_half_life: int = 50
    multiplier: float = 1.0
    sample_count: int = 0
    reliability: float = 0.0
    noise: float = 0.0
    used_fallback: bool = True
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_key": self.pattern_key,
            "base_half_life": self.base_half_life,
            "pattern_half_life": self.pattern_half_life,
            "multiplier": round(self.multiplier, 6),
            "sample_count": self.sample_count,
            "reliability": round(self.reliability, 6),
            "noise": round(self.noise, 6),
            "used_fallback": self.used_fallback,
            "explanation": self.explanation,
        }


def compute_pattern_noise(scores: list[float]) -> float:
    """Compute normalized noise from pattern outcome scores.

    noise = clamp(variance / 0.25, 0, 1)
    """
    if len(scores) < 2:
        return 0.0
    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    normalized = variance / _MAX_VARIANCE
    return max(0.0, min(1.0, normalized))


def compute_pattern_reliability(scores: list[float]) -> float:
    """Compute reliability from pattern outcome scores.

    reliability = 1 - noise
    """
    return 1.0 - compute_pattern_noise(scores)


def compute_pattern_half_life(
    pattern_key: str,
    pattern_scores: list[float],
    base_half_life: int,
    config: PatternHalfLifeConfig | None = None,
) -> PatternHalfLifeResult:
    """Compute pattern-specific half-life from outcome reliability.

    base_half_life comes from the upstream stack (config/adaptive/regime).
    Pattern-specific half-life is the final refinement.
    """
    cfg = config or PatternHalfLifeConfig()

    if not cfg.enabled:
        return PatternHalfLifeResult(
            pattern_key=pattern_key,
            base_half_life=base_half_life,
            pattern_half_life=base_half_life,
            multiplier=1.0,
            sample_count=len(pattern_scores),
            used_fallback=True,
            explanation="pattern half-life disabled",
        )

    n = len(pattern_scores)

    if n < cfg.min_samples:
        return PatternHalfLifeResult(
            pattern_key=pattern_key,
            base_half_life=base_half_life,
            pattern_half_life=base_half_life,
            multiplier=cfg.base_multiplier,
            sample_count=n,
            used_fallback=True,
            explanation=f"insufficient samples ({n} < {cfg.min_samples})",
        )

    noise = compute_pattern_noise(pattern_scores)
    reliability = 1.0 - noise

    if reliability >= cfg.reliability_threshold:
        multiplier = cfg.reliable_multiplier
        explanation = f"reliable (reliability={reliability:.4f} >= {cfg.reliability_threshold})"
    elif noise >= cfg.noise_threshold:
        multiplier = cfg.noisy_multiplier
        explanation = f"noisy (noise={noise:.4f} >= {cfg.noise_threshold})"
    else:
        multiplier = cfg.base_multiplier
        explanation = "neutral"

    raw = base_half_life * multiplier
    clamped = max(cfg.min_half_life, min(cfg.max_half_life, int(round(raw))))

    return PatternHalfLifeResult(
        pattern_key=pattern_key,
        base_half_life=base_half_life,
        pattern_half_life=clamped,
        multiplier=multiplier,
        sample_count=n,
        reliability=reliability,
        noise=noise,
        used_fallback=False,
        explanation=explanation,
    )


def compute_all_pattern_half_lives(
    pattern_keys: list[str],
    pattern_scores_map: dict[str, list[float]],
    base_half_life: int,
    config: PatternHalfLifeConfig | None = None,
) -> list[PatternHalfLifeResult]:
    """Compute pattern-specific half-lives for a batch of patterns."""
    results: list[PatternHalfLifeResult] = []
    for key in pattern_keys:
        scores = pattern_scores_map.get(key, [])
        results.append(compute_pattern_half_life(key, scores, base_half_life, config))
    return results
