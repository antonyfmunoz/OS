"""Pattern registry — stores and retrieves behavioral patterns by similarity.

Patterns are clusters of similar prediction records. Each pattern
has a centroid vector, examples, and performance metrics.

Centroids update incrementally as new examples join.
Patterns are derived from data, never manually injected (invariant 57).

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

from umh.patterns.similarity import SimilarityEngine


_DEFAULT_MAX_EXAMPLES = 50
_DEFAULT_MAX_PATTERNS = 200


def _make_pattern_id() -> str:
    return f"pat_{uuid.uuid4().hex[:12]}"


@dataclass
class Pattern:
    """A behavioral pattern cluster with centroid vector and metrics."""

    pattern_id: str
    label: str
    centroid: list[float]
    examples: list[str] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    weight: float = 1.0

    @property
    def total(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.5
        return self.success_count / self.total

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "label": self.label,
            "centroid_dim": len(self.centroid),
            "example_count": len(self.examples),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_rate, 4),
            "weight": round(self.weight, 4),
        }


class PatternRegistry:
    """Stores behavioral patterns and finds matches by vector similarity.

    Thread-safe. Patterns are derived from data (invariant 57).
    """

    def __init__(
        self,
        similarity_engine: SimilarityEngine,
        *,
        max_examples_per_pattern: int = _DEFAULT_MAX_EXAMPLES,
        max_patterns: int = _DEFAULT_MAX_PATTERNS,
    ) -> None:
        self._sim = similarity_engine
        self._lock = threading.Lock()
        self._patterns: dict[str, Pattern] = {}
        self._max_examples = max_examples_per_pattern
        self._max_patterns = max_patterns

    @property
    def pattern_count(self) -> int:
        with self._lock:
            return len(self._patterns)

    def register_pattern(
        self,
        vector: list[float],
        label: str,
        example: str = "",
    ) -> Pattern:
        """Find matching pattern or create new one. Returns the pattern."""
        with self._lock:
            match = self._find_match_locked(vector)
            if match is not None:
                self._update_centroid(match, vector)
                if example and len(match.examples) < self._max_examples:
                    match.examples.append(example)
                return match

            if len(self._patterns) >= self._max_patterns:
                self._evict_smallest_locked()

            pattern = Pattern(
                pattern_id=_make_pattern_id(),
                label=label,
                centroid=list(vector),
                examples=[example] if example else [],
            )
            self._patterns[pattern.pattern_id] = pattern
            return pattern

    def find_matching_pattern(self, vector: list[float]) -> Pattern | None:
        """Find the most similar pattern above threshold. Returns None if no match."""
        with self._lock:
            return self._find_match_locked(vector)

    def get_pattern(self, pattern_id: str) -> Pattern | None:
        with self._lock:
            return self._patterns.get(pattern_id)

    def list_patterns(self) -> list[Pattern]:
        with self._lock:
            return list(self._patterns.values())

    def record_outcome(self, pattern_id: str, *, matched: bool) -> None:
        with self._lock:
            pattern = self._patterns.get(pattern_id)
            if pattern is None:
                return
            if matched:
                pattern.success_count += 1
            else:
                pattern.failure_count += 1

    def clear(self) -> None:
        with self._lock:
            self._patterns.clear()

    def get_state(self) -> dict[str, Any]:
        with self._lock:
            return {
                "pattern_count": len(self._patterns),
                "max_patterns": self._max_patterns,
                "max_examples_per_pattern": self._max_examples,
                "patterns": {
                    pid: p.to_dict() for pid, p in sorted(self._patterns.items())
                },
            }

    def _find_match_locked(self, vector: list[float]) -> Pattern | None:
        best: Pattern | None = None
        best_score = -1.0

        for pattern in self._patterns.values():
            result = self._sim.compute_similarity(vector, pattern.centroid)
            if result.above_threshold and result.score > best_score:
                best = pattern
                best_score = result.score

        return best

    def _update_centroid(self, pattern: Pattern, new_vector: list[float]) -> None:
        """Incremental centroid update: weighted average."""
        n = len(pattern.examples) + 1
        for i in range(len(pattern.centroid)):
            if i < len(new_vector):
                pattern.centroid[i] = (
                    pattern.centroid[i] * (n - 1) + new_vector[i]
                ) / n

    def _evict_smallest_locked(self) -> None:
        """Remove the pattern with fewest examples (least evidence)."""
        if not self._patterns:
            return
        smallest_id = min(
            self._patterns,
            key=lambda pid: len(self._patterns[pid].examples),
        )
        del self._patterns[smallest_id]
