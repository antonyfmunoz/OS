"""Pattern abstraction — groups similar prediction records into higher-level patterns.

Derives abstract behavioral patterns from concrete prediction history.
Patterns are always derived from data, never manually injected (invariant 57).

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.patterns.embedding import EmbeddingModel
from umh.patterns.registry import Pattern, PatternRegistry
from umh.prediction.store import PredictionRecord


@dataclass(frozen=True)
class AbstractedPattern:
    """A higher-level behavioral pattern derived from prediction records."""

    pattern_id: str
    label: str
    member_count: int
    success_rate: float
    source_predictions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "label": self.label,
            "member_count": self.member_count,
            "success_rate": round(self.success_rate, 4),
            "source_predictions": list(self.source_predictions),
        }


class PatternAbstractor:
    """Groups similar prediction records into behavioral patterns.

    Uses embeddings to find similarity, then registers clusters
    in the PatternRegistry.
    """

    def __init__(
        self,
        embedding_model: EmbeddingModel,
        registry: PatternRegistry,
    ) -> None:
        self._embedder = embedding_model
        self._registry = registry

    @property
    def registry(self) -> PatternRegistry:
        return self._registry

    def abstract(
        self,
        records: list[PredictionRecord],
    ) -> list[AbstractedPattern]:
        """Group records into abstract patterns. Returns new abstractions."""
        abstractions: list[AbstractedPattern] = []
        pattern_members: dict[str, list[str]] = {}

        for rec in records:
            text = self._record_to_text(rec)
            vec = self._embedder.embed(text)
            pattern = self._registry.register_pattern(
                vector=vec,
                label=self._derive_label(rec),
                example=rec.prediction_id,
            )

            if pattern.pattern_id not in pattern_members:
                pattern_members[pattern.pattern_id] = []
            pattern_members[pattern.pattern_id].append(rec.prediction_id)

        for pid, members in pattern_members.items():
            pattern = self._registry.get_pattern(pid)
            if pattern is None:
                continue
            abstractions.append(
                AbstractedPattern(
                    pattern_id=pid,
                    label=pattern.label,
                    member_count=len(pattern.examples),
                    success_rate=pattern.success_rate,
                    source_predictions=tuple(members),
                )
            )

        return abstractions

    def _record_to_text(self, rec: PredictionRecord) -> str:
        parts = [rec.inferred_goal]
        parts.extend(rec.predicted_actions)
        parts.extend(rec.related_entities)
        if rec.source:
            parts.append(rec.source)
        return " ".join(parts)

    def _derive_label(self, rec: PredictionRecord) -> str:
        if rec.source and rec.inferred_goal:
            return f"{rec.source}:{rec.inferred_goal}"
        return rec.inferred_goal or rec.source or "unknown"
