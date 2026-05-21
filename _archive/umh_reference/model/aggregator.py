"""Behavior aggregator — computes trait values from observed data.

Derives traits from job feedback, prediction records, and pattern
weights. All computation is deterministic and explainable (invariant 62).

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import math
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from umh.learning.feedback import ExecutionFeedback
from umh.model.behavior import UserBehaviorModel
from umh.model.traits import TraitValue, confidence_from_samples
from umh.prediction.store import PredictionRecord, PredictionStatus


class BehaviorAggregator:
    """Computes behavioral traits from raw data.

    All traits are derived from data, never manually injected.
    Deterministic: same data → same model.
    """

    def build_model(
        self,
        feedback: list[ExecutionFeedback] | None = None,
        predictions: list[PredictionRecord] | None = None,
        pattern_weights: list[dict[str, Any]] | None = None,
    ) -> UserBehaviorModel:
        """Build a complete behavior model from available data."""
        model = UserBehaviorModel()
        fb = feedback or []
        preds = predictions or []
        pw = pattern_weights or []

        total = len(fb) + len(preds) + len(pw)
        model.total_observations = total

        self._compute_execution_rate(model, fb)
        self._compute_completion_rate(model, fb)
        self._compute_consistency_score(model, fb)
        self._compute_latency_score(model, fb)
        self._compute_pattern_stability(model, pw)
        self._compute_time_preference(model, fb)
        self._compute_volatility_index(model, preds)

        return model

    def update_model(
        self,
        model: UserBehaviorModel,
        new_feedback: list[ExecutionFeedback] | None = None,
        new_predictions: list[PredictionRecord] | None = None,
        pattern_weights: list[dict[str, Any]] | None = None,
    ) -> UserBehaviorModel:
        """Incrementally update an existing model with new data."""
        fb = new_feedback or []
        preds = new_predictions or []
        pw = pattern_weights or []

        model.total_observations += len(fb) + len(preds) + len(pw)

        if fb:
            self._compute_execution_rate(model, fb)
            self._compute_completion_rate(model, fb)
            self._compute_consistency_score(model, fb)
            self._compute_latency_score(model, fb)
            self._compute_time_preference(model, fb)
        if pw:
            self._compute_pattern_stability(model, pw)
        if preds:
            self._compute_volatility_index(model, preds)

        return model

    def _compute_execution_rate(
        self,
        model: UserBehaviorModel,
        feedback: list[ExecutionFeedback],
    ) -> None:
        if not feedback:
            return
        n = len(feedback)
        model.set_trait(
            "execution_rate",
            value=1.0,
            confidence=confidence_from_samples(n),
            sample_count=n,
        )

    def _compute_completion_rate(
        self,
        model: UserBehaviorModel,
        feedback: list[ExecutionFeedback],
    ) -> None:
        if not feedback:
            return
        n = len(feedback)
        succeeded = sum(1 for f in feedback if f.success)
        rate = succeeded / n
        model.set_trait(
            "completion_rate",
            value=rate,
            confidence=confidence_from_samples(n),
            sample_count=n,
        )

    def _compute_consistency_score(
        self,
        model: UserBehaviorModel,
        feedback: list[ExecutionFeedback],
    ) -> None:
        hours = self._extract_hours(feedback)
        if len(hours) < 2:
            return

        mean = sum(hours) / len(hours)
        variance = sum((h - mean) ** 2 for h in hours) / len(hours)
        std_dev = math.sqrt(variance)

        score = max(0.0, 1.0 - std_dev / 12.0)

        model.set_trait(
            "consistency_score",
            value=score,
            confidence=confidence_from_samples(len(hours)),
            sample_count=len(hours),
        )

    def _compute_latency_score(
        self,
        model: UserBehaviorModel,
        feedback: list[ExecutionFeedback],
    ) -> None:
        durations = [f.duration_ms for f in feedback if f.duration_ms > 0]
        if not durations:
            return

        avg_ms = sum(durations) / len(durations)
        score = 1.0 / (1.0 + avg_ms / 1000.0)

        model.set_trait(
            "latency_score",
            value=score,
            confidence=confidence_from_samples(len(durations)),
            sample_count=len(durations),
        )

    def _compute_pattern_stability(
        self,
        model: UserBehaviorModel,
        pattern_weights: list[dict[str, Any]],
    ) -> None:
        if not pattern_weights:
            return

        weights = [pw.get("weight", 1.0) for pw in pattern_weights]
        n = len(weights)

        high_weight_count = sum(1 for w in weights if w > 1.2)
        stability = high_weight_count / n if n > 0 else 0.5

        model.set_trait(
            "pattern_stability",
            value=stability,
            confidence=confidence_from_samples(n, required=10),
            sample_count=n,
        )

    def _compute_time_preference(
        self,
        model: UserBehaviorModel,
        feedback: list[ExecutionFeedback],
    ) -> None:
        hours = self._extract_hours(feedback)
        if not hours:
            return

        morning_count = sum(1 for h in hours if 5 <= h < 12)
        total = len(hours)
        preference = morning_count / total

        model.set_trait(
            "time_preference",
            value=preference,
            confidence=confidence_from_samples(total),
            sample_count=total,
        )

    def _compute_volatility_index(
        self,
        model: UserBehaviorModel,
        predictions: list[PredictionRecord],
    ) -> None:
        if not predictions:
            return

        n = len(predictions)
        sources = Counter(p.source for p in predictions if p.source)
        unique_sources = len(sources)
        volatility = min(1.0, unique_sources / max(n, 1) * 2.0)

        model.set_trait(
            "volatility_index",
            value=volatility,
            confidence=confidence_from_samples(n),
            sample_count=n,
        )

    def _extract_hours(self, feedback: list[ExecutionFeedback]) -> list[float]:
        hours: list[float] = []
        for f in feedback:
            if not f.timestamp:
                continue
            try:
                ts = datetime.fromisoformat(f.timestamp.replace("Z", "+00:00"))
                hours.append(float(ts.hour) + ts.minute / 60.0)
            except (ValueError, AttributeError):
                continue
        return hours
