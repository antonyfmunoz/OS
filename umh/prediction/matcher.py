"""Prediction matcher — multi-level matching for predictions against outcomes.

Matching hierarchy:
  1. Exact match (entity, action, goal — same as Phase 21)
  2. Semantic similarity match (embedding distance)
  3. Pattern-level match (shared pattern cluster)

Exact matches always take priority (invariant 55: embeddings augment,
never replace structured data).

Deterministic: same inputs → same results (invariant 56).

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.learning.feedback import ExecutionFeedback
from umh.patterns.embedding import EmbeddingModel
from umh.patterns.registry import PatternRegistry
from umh.patterns.similarity import SimilarityEngine
from umh.prediction.store import PredictionRecord


@dataclass(frozen=True)
class MatchDetail:
    """Detailed match result with type and confidence."""

    prediction_id: str
    matched: bool
    matched_job_id: str = ""
    match_type: str = ""
    match_reason: str = ""
    similarity_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "matched": self.matched,
            "matched_job_id": self.matched_job_id,
            "match_type": self.match_type,
            "match_reason": self.match_reason,
            "similarity_score": round(self.similarity_score, 4),
        }


class PredictionMatcher:
    """Multi-level matcher: exact → semantic → pattern.

    Exact matches always win. Semantic and pattern matches only
    apply when exact matching finds nothing.
    """

    def __init__(
        self,
        *,
        embedding_model: EmbeddingModel | None = None,
        similarity_engine: SimilarityEngine | None = None,
        pattern_registry: PatternRegistry | None = None,
    ) -> None:
        self._embedder = embedding_model
        self._sim = similarity_engine
        self._registry = pattern_registry

    def match_predictions(
        self,
        pending: list[PredictionRecord],
        completed_feedback: list[ExecutionFeedback],
    ) -> list[MatchDetail]:
        """Match predictions against completed jobs using multi-level matching."""
        results: list[MatchDetail] = []
        used_job_ids: set[str] = set()

        for pred in sorted(pending, key=lambda p: p.prediction_id):
            detail = self._try_match(pred, completed_feedback, used_job_ids)
            results.append(detail)
            if detail.matched:
                used_job_ids.add(detail.matched_job_id)

        return results

    def _try_match(
        self,
        pred: PredictionRecord,
        feedback: list[ExecutionFeedback],
        used: set[str],
    ) -> MatchDetail:
        for fb in feedback:
            if fb.job_id in used:
                continue

            exact = self._exact_match(pred, fb)
            if exact:
                return MatchDetail(
                    prediction_id=pred.prediction_id,
                    matched=True,
                    matched_job_id=fb.job_id,
                    match_type="exact",
                    match_reason=exact,
                    similarity_score=1.0,
                )

        if self._embedder is not None and self._sim is not None:
            for fb in feedback:
                if fb.job_id in used:
                    continue
                sem = self._semantic_match(pred, fb)
                if sem is not None:
                    return sem

        if self._registry is not None and self._embedder is not None:
            for fb in feedback:
                if fb.job_id in used:
                    continue
                pat = self._pattern_match(pred, fb)
                if pat is not None:
                    return pat

        return MatchDetail(
            prediction_id=pred.prediction_id,
            matched=False,
        )

    def _exact_match(
        self,
        pred: PredictionRecord,
        fb: ExecutionFeedback,
    ) -> str:
        task_type = fb.task_type.lower()

        for entity in pred.related_entities:
            if entity.lower() == task_type:
                return f"entity_match:{entity}"

        for action in pred.predicted_actions:
            if task_type in action.lower():
                return f"action_match:{action}"

        if task_type in pred.inferred_goal.lower():
            return f"goal_match:{pred.inferred_goal}"

        return ""

    def _semantic_match(
        self,
        pred: PredictionRecord,
        fb: ExecutionFeedback,
    ) -> MatchDetail | None:
        pred_text = self._prediction_text(pred)
        fb_text = fb.task_type
        pred_vec = self._embedder.embed(pred_text)
        fb_vec = self._embedder.embed(fb_text)
        result = self._sim.compute_similarity(pred_vec, fb_vec)

        if result.above_threshold:
            return MatchDetail(
                prediction_id=pred.prediction_id,
                matched=True,
                matched_job_id=fb.job_id,
                match_type="semantic",
                match_reason=f"semantic_similarity:{result.score:.3f}",
                similarity_score=result.score,
            )
        return None

    def _pattern_match(
        self,
        pred: PredictionRecord,
        fb: ExecutionFeedback,
    ) -> MatchDetail | None:
        pred_text = self._prediction_text(pred)
        fb_text = fb.task_type
        pred_vec = self._embedder.embed(pred_text)
        fb_vec = self._embedder.embed(fb_text)

        pred_pattern = self._registry.find_matching_pattern(pred_vec)
        fb_pattern = self._registry.find_matching_pattern(fb_vec)

        if (
            pred_pattern is not None
            and fb_pattern is not None
            and pred_pattern.pattern_id == fb_pattern.pattern_id
        ):
            return MatchDetail(
                prediction_id=pred.prediction_id,
                matched=True,
                matched_job_id=fb.job_id,
                match_type="pattern",
                match_reason=f"pattern_match:{pred_pattern.pattern_id}",
                similarity_score=0.0,
            )
        return None

    def _prediction_text(self, pred: PredictionRecord) -> str:
        parts = [pred.inferred_goal]
        parts.extend(pred.predicted_actions)
        parts.extend(pred.related_entities)
        return " ".join(parts)
