"""Similarity engine — cosine similarity between embedding vectors.

Deterministic: same input vectors always produce the same score.
Thread-safe, stateless computation.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


_DEFAULT_THRESHOLD = 0.75


@dataclass(frozen=True)
class SimilarityResult:
    """Result of a similarity comparison."""

    score: float
    above_threshold: bool
    threshold: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "above_threshold": self.above_threshold,
            "threshold": self.threshold,
        }


class SimilarityEngine:
    """Computes cosine similarity between embedding vectors.

    Deterministic: same vectors → same score.
    Score range: [-1.0, 1.0] (1.0 = identical, 0.0 = orthogonal).
    """

    def __init__(self, *, threshold: float = _DEFAULT_THRESHOLD) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be 0.0–1.0")
        self._threshold = threshold

    @property
    def threshold(self) -> float:
        return self._threshold

    def compute_similarity(
        self,
        vec1: list[float],
        vec2: list[float],
    ) -> SimilarityResult:
        """Cosine similarity between two vectors."""
        score = self._cosine(vec1, vec2)
        return SimilarityResult(
            score=score,
            above_threshold=score >= self._threshold,
            threshold=self._threshold,
        )

    def are_similar(self, vec1: list[float], vec2: list[float]) -> bool:
        return self.compute_similarity(vec1, vec2).above_threshold

    def _cosine(self, a: list[float], b: list[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return dot / (norm_a * norm_b)

    def get_state(self) -> dict[str, Any]:
        return {"threshold": self._threshold}
