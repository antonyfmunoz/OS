"""Contextual pattern matching — recognizes similar composite states from memory.

Given a current composite state (as PatternKey), searches pattern memory
for exact and partial matches. Similarity is simple dimension counting:
    similarity = (matching dimensions) / (total dimensions)

Phase 67 is purely observational — matching results are informational only,
never influencing scoring (inv 320). This avoids feedback loops where
pattern recognition biases future outcomes.

Pure computation — no I/O, no child processes.
No imports from cell, environment, or adapter layers.
No circular dependency: reads pattern_memory types only.
Never mutates memory or records (inv 314).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.runtime.pattern_memory import (
    PatternKey,
    PatternMemory,
    PatternStats,
)

_TOTAL_DIMENSIONS: int = 4
_DEFAULT_MIN_SAMPLES: int = 10
_DEFAULT_MIN_SIMILARITY: float = 0.5


@dataclass(frozen=True)
class PatternMatch:
    """A single pattern match candidate with similarity score."""

    matched_key: PatternKey
    similarity: float = 0.0
    stats: PatternStats | None = None
    sample_size: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "similarity", max(0.0, min(1.0, self.similarity)))
        object.__setattr__(self, "sample_size", max(0, self.sample_size))

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched_key": self.matched_key.to_dict(),
            "similarity": round(self.similarity, 4),
            "stats": self.stats.to_dict() if self.stats else None,
            "sample_size": self.sample_size,
        }


@dataclass(frozen=True)
class PatternResult:
    """Complete result of pattern matching against memory."""

    matched: bool = False
    best_match: PatternMatch | None = None
    all_matches: tuple[PatternMatch, ...] = ()
    query_key: PatternKey | None = None
    confidence: float = 0.0
    total_patterns_searched: int = 0
    explanation: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched": self.matched,
            "best_match": self.best_match.to_dict() if self.best_match else None,
            "all_matches": [m.to_dict() for m in self.all_matches],
            "query_key": self.query_key.to_dict() if self.query_key else None,
            "confidence": round(self.confidence, 4),
            "total_patterns_searched": self.total_patterns_searched,
            "explanation": self.explanation,
        }


def _compute_similarity(key_a: PatternKey, key_b: PatternKey) -> float:
    """Compute similarity as fraction of matching dimensions (inv 315, 318).

    Simple rule: similarity = (matching dims) / 4.
    No fuzzy ML — pure discrete comparison.
    """
    dims_a = key_a.to_tuple()
    dims_b = key_b.to_tuple()

    matching = sum(1 for a, b in zip(dims_a, dims_b) if a == b)
    return matching / _TOTAL_DIMENSIONS


def _compute_pattern_confidence(
    sample_size: int,
    min_samples: int,
) -> float:
    """Compute confidence from sample size (inv 322).

    confidence = min(1.0, sample_size / min_samples)
    Low sample → low confidence.
    """
    if min_samples <= 0:
        return 1.0 if sample_size > 0 else 0.0
    return min(1.0, sample_size / min_samples)


def match_pattern(
    query_key: PatternKey | None = None,
    memory: PatternMemory | None = None,
    min_similarity: float = _DEFAULT_MIN_SIMILARITY,
    min_samples: int = _DEFAULT_MIN_SAMPLES,
) -> PatternResult:
    """Match a pattern key against memory.

    Searches all unique keys in memory, computes similarity,
    returns sorted matches above threshold.

    Deterministic (inv 315). No mutation (inv 314). Bounded similarity (inv 318).
    Missing data → no match (inv 317). No scoring impact (inv 320).
    """
    if query_key is None:
        return PatternResult(
            explanation="no query key provided: no match",
        )

    if memory is None or memory.size == 0:
        return PatternResult(
            query_key=query_key,
            explanation="no patterns in memory: no match",
        )

    unique_keys = memory.unique_keys()
    total_searched = len(unique_keys)

    matches: list[PatternMatch] = []

    for key_tuple in sorted(unique_keys):
        from umh.runtime.pattern_memory import (
            RiskLevel,
            StabilityLevel,
            TrendDirection,
            UrgencyLevel,
        )

        candidate_key = PatternKey(
            trend_direction=TrendDirection(key_tuple[0]),
            risk_level=RiskLevel(key_tuple[1]),
            stability_level=StabilityLevel(key_tuple[2]),
            urgency_level=UrgencyLevel(key_tuple[3]),
        )

        similarity = _compute_similarity(query_key, candidate_key)

        if similarity < min_similarity:
            continue

        stats = memory.compute_stats(candidate_key)

        matches.append(
            PatternMatch(
                matched_key=candidate_key,
                similarity=similarity,
                stats=stats,
                sample_size=stats.count,
            )
        )

    if not matches:
        return PatternResult(
            query_key=query_key,
            total_patterns_searched=total_searched,
            explanation=f"no matches above similarity={min_similarity:.2f} "
            f"in {total_searched} patterns",
        )

    matches.sort(key=lambda m: (-m.similarity, m.matched_key.to_tuple()))

    best = matches[0]
    confidence = _compute_pattern_confidence(best.sample_size, min_samples)

    parts = [
        f"best={best.similarity:.2f}",
        f"key={best.matched_key.to_tuple()}",
        f"samples={best.sample_size}",
        f"conf={confidence:.2f}",
        f"matches={len(matches)}/{total_searched}",
    ]
    if best.stats is not None:
        parts.append(f"avg_score={best.stats.avg_score:.3f}")
        parts.append(f"success_rate={best.stats.success_rate:.3f}")

    return PatternResult(
        matched=True,
        best_match=best,
        all_matches=tuple(matches),
        query_key=query_key,
        confidence=confidence,
        total_patterns_searched=total_searched,
        explanation="; ".join(parts),
    )
