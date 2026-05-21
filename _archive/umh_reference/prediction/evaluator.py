"""Prediction evaluator — matches predictions against actual outcomes.

Deterministic outcome matching: compares predicted actions and entities
against completed job feedback records. No fuzzy matching, no randomness.

Read-only — never mutates the FeedbackStore or PredictionStore directly.
Returns match results for the caller to apply.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.learning.feedback import ExecutionFeedback
from umh.prediction.store import PredictionRecord, PredictionStatus


@dataclass(frozen=True)
class MatchResult:
    """Result of comparing a prediction against an outcome."""

    prediction_id: str
    matched: bool
    matched_job_id: str = ""
    match_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "matched": self.matched,
            "matched_job_id": self.matched_job_id,
            "match_reason": self.match_reason,
        }


class PredictionEvaluator:
    """Matches pending predictions against completed job outcomes.

    Deterministic: same predictions + same feedback → same results.
    Read-only: does not mutate any store.
    """

    def match_predictions(
        self,
        pending: list[PredictionRecord],
        completed_feedback: list[ExecutionFeedback],
    ) -> list[MatchResult]:
        """Compare pending predictions against completed jobs.

        Matching criteria (all deterministic):
        1. Entity overlap: prediction's related_entities ∩ feedback task_type
        2. Action pattern: predicted action contains the task_type

        A prediction is MATCHED if any completed job satisfies criteria.
        Each job can match at most one prediction (first match wins).
        """
        results: list[MatchResult] = []
        used_job_ids: set[str] = set()

        for pred in sorted(pending, key=lambda p: p.prediction_id):
            match_found = False
            for fb in completed_feedback:
                if fb.job_id in used_job_ids:
                    continue

                reason = self._check_match(pred, fb)
                if reason:
                    results.append(
                        MatchResult(
                            prediction_id=pred.prediction_id,
                            matched=True,
                            matched_job_id=fb.job_id,
                            match_reason=reason,
                        )
                    )
                    used_job_ids.add(fb.job_id)
                    match_found = True
                    break

            if not match_found:
                results.append(
                    MatchResult(
                        prediction_id=pred.prediction_id,
                        matched=False,
                    )
                )

        return results

    def _check_match(
        self,
        prediction: PredictionRecord,
        feedback: ExecutionFeedback,
    ) -> str:
        """Check if a prediction matches a feedback record. Returns reason or empty string."""
        task_type = feedback.task_type.lower()

        for entity in prediction.related_entities:
            if entity.lower() == task_type:
                return f"entity_match:{entity}"

        for action in prediction.predicted_actions:
            if task_type in action.lower():
                return f"action_match:{action}"

        goal_lower = prediction.inferred_goal.lower()
        if task_type in goal_lower:
            return f"goal_match:{prediction.inferred_goal}"

        return ""
