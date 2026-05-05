"""Predictor engine — derives user intents from behavioral history.

Heuristic-based: detects repeated workflows, continuation of
unfinished work, and time-based patterns from job history.

Pure computation — no I/O, no state mutation, no subprocess.
All methods are deterministic given the same input and time.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from umh.learning.feedback import ExecutionFeedback, FeedbackStore
from umh.prediction.intent import UserIntent, make_intent_id


_DEFAULT_CONFIDENCE_THRESHOLD = 0.6
_DEFAULT_MAX_PREDICTIONS = 5
_MIN_REPEAT_COUNT = 2
_REPEAT_CONFIDENCE_BASE = 0.65
_REPEAT_CONFIDENCE_PER_OCCURRENCE = 0.05
_CONTINUATION_CONFIDENCE = 0.7
_TIME_PATTERN_CONFIDENCE = 0.6
_TIME_WINDOW_MINUTES = 60


@dataclass(frozen=True)
class PredictionContext:
    """Snapshot of current system state for prediction.

    Immutable — represents a point-in-time view.
    """

    recent_feedback: tuple[ExecutionFeedback, ...] = ()
    active_task_types: tuple[str, ...] = ()
    current_hour: int = 0
    current_day_of_week: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recent_feedback_count": len(self.recent_feedback),
            "active_task_types": list(self.active_task_types),
            "current_hour": self.current_hour,
            "current_day_of_week": self.current_day_of_week,
            "metadata": self.metadata,
        }


class Predictor:
    """Derives user intents from behavioral signals.

    Heuristic engine — no ML, no external I/O.
    Deterministic: same context + same time → same predictions.
    """

    def __init__(
        self,
        *,
        confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD,
        max_predictions: int = _DEFAULT_MAX_PREDICTIONS,
    ) -> None:
        if confidence_threshold < 0.0 or confidence_threshold > 1.0:
            raise ValueError("confidence_threshold must be 0.0–1.0")
        if max_predictions < 1:
            raise ValueError("max_predictions must be >= 1")
        self._threshold = confidence_threshold
        self._max = max_predictions

    @property
    def confidence_threshold(self) -> float:
        return self._threshold

    @property
    def max_predictions(self) -> int:
        return self._max

    def predict_intent(
        self,
        context: PredictionContext,
        *,
        now: datetime | None = None,
    ) -> list[UserIntent]:
        """Predict user intents from context. Pure function."""
        ref = now or datetime.now(timezone.utc)
        intents: list[UserIntent] = []

        intents.extend(self._detect_repeated_workflows(context))
        intents.extend(self._detect_continuations(context))
        intents.extend(self._detect_time_patterns(context, ref))

        filtered = [i for i in intents if i.confidence >= self._threshold]
        filtered.sort(key=lambda i: (-i.confidence, i.intent_id))

        return filtered[: self._max]

    def build_context(
        self,
        store: FeedbackStore,
        *,
        active_task_types: list[str] | None = None,
        now: datetime | None = None,
        limit: int = 100,
    ) -> PredictionContext:
        """Build a PredictionContext from current system state."""
        ref = now or datetime.now(timezone.utc)
        all_feedback = store.get_all()
        recent = tuple(all_feedback[-limit:]) if all_feedback else ()

        return PredictionContext(
            recent_feedback=recent,
            active_task_types=tuple(active_task_types or []),
            current_hour=ref.hour,
            current_day_of_week=ref.weekday(),
        )

    def _detect_repeated_workflows(
        self,
        context: PredictionContext,
    ) -> list[UserIntent]:
        """Detect task types that appear frequently in recent history."""
        if not context.recent_feedback:
            return []

        type_counts = Counter(f.task_type for f in context.recent_feedback)
        intents: list[UserIntent] = []

        for task_type, count in type_counts.most_common():
            if count < _MIN_REPEAT_COUNT:
                continue

            confidence = min(
                1.0,
                _REPEAT_CONFIDENCE_BASE
                + (count - _MIN_REPEAT_COUNT) * _REPEAT_CONFIDENCE_PER_OCCURRENCE,
            )

            successful = sum(
                1 for f in context.recent_feedback
                if f.task_type == task_type and f.success
            )

            intents.append(
                UserIntent(
                    intent_id=make_intent_id(),
                    inferred_goal=f"repeat_{task_type}",
                    confidence=confidence,
                    context_signals=(
                        f"seen_{count}_times",
                        f"success_rate_{successful}/{count}",
                    ),
                    related_entities=(task_type,),
                    predicted_actions=(f"submit_{task_type}",),
                    source="repeated_workflow",
                )
            )

        return intents

    def _detect_continuations(
        self,
        context: PredictionContext,
    ) -> list[UserIntent]:
        """Detect active task types that likely need continuation."""
        if not context.active_task_types:
            return []

        intents: list[UserIntent] = []
        for task_type in context.active_task_types:
            has_history = any(
                f.task_type == task_type for f in context.recent_feedback
            )

            confidence = _CONTINUATION_CONFIDENCE
            signals = [f"active_task_{task_type}"]
            if has_history:
                confidence = min(1.0, confidence + 0.1)
                signals.append("has_prior_execution")

            intents.append(
                UserIntent(
                    intent_id=make_intent_id(),
                    inferred_goal=f"continue_{task_type}",
                    confidence=confidence,
                    context_signals=tuple(signals),
                    related_entities=(task_type,),
                    predicted_actions=(f"resume_{task_type}",),
                    source="continuation",
                )
            )

        return intents

    def _detect_time_patterns(
        self,
        context: PredictionContext,
        ref: datetime,
    ) -> list[UserIntent]:
        """Detect task types that historically run at this time of day."""
        if not context.recent_feedback:
            return []

        hour = ref.hour
        hour_tasks: dict[str, int] = {}

        for fb in context.recent_feedback:
            if not fb.timestamp:
                continue
            try:
                ts = datetime.fromisoformat(fb.timestamp.replace("Z", "+00:00"))
                if abs(ts.hour - hour) <= 1:
                    hour_tasks[fb.task_type] = hour_tasks.get(fb.task_type, 0) + 1
            except (ValueError, AttributeError):
                continue

        intents: list[UserIntent] = []
        for task_type, count in sorted(hour_tasks.items()):
            if count < _MIN_REPEAT_COUNT:
                continue

            intents.append(
                UserIntent(
                    intent_id=make_intent_id(),
                    inferred_goal=f"time_pattern_{task_type}",
                    confidence=_TIME_PATTERN_CONFIDENCE,
                    context_signals=(
                        f"hour_{hour}",
                        f"seen_{count}_times_at_this_hour",
                    ),
                    related_entities=(task_type,),
                    predicted_actions=(f"submit_{task_type}",),
                    source="time_pattern",
                )
            )

        return intents
