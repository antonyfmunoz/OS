"""ExecutionFeedback — structured feedback from execution results.

Translates ExecutionResult into feedback that can be ingested by the
world substrate and learning layers. Closes the action loop:

    ExecutionResult → ExecutionFeedback → FeedbackObservation

Pure functions, no side effects, no API calls, no new dependencies.

Outcome mapping:
    "success"   → "success"   (+confidence)
    "failed"    → "failure"   (-confidence)
    "skipped"   → "partial"   (0.0)
    "unhandled" → "unknown"   (0.0)

Usage::

    from umh.runtime_engine.execution_feedback import (
        execution_to_feedback,
        feedback_to_observation,
        normalize_execution_feedback,
    )
    from umh.runtime_engine.execution_router import ExecutionResult

    feedback = execution_to_feedback(exec_result, confidence=0.8)
    observation = feedback_to_observation(feedback)
    # or combined:
    result = normalize_execution_feedback(exec_result, confidence=0.8)
"""

from __future__ import annotations

from dataclasses import dataclass


# ─── Outcome mapping ─────────────────────────────────────────────


OUTCOME_MAP: dict[str, str] = {
    "success": "success",
    "failed": "failure",
    "skipped": "partial",
    "unhandled": "unknown",
}

POSITIVE_OUTCOMES: frozenset[str] = frozenset({"success"})
NEGATIVE_OUTCOMES: frozenset[str] = frozenset({"failure"})
NEUTRAL_OUTCOMES: frozenset[str] = frozenset({"partial", "unknown"})


# ─── Data models ─────────────────────────────────────────────────


@dataclass(frozen=True)
class ExecutionFeedback:
    """Structured feedback from a single execution result."""

    action_id: str
    action_name: str
    outcome_type: str  # "success" | "failure" | "partial" | "unknown"
    signal_strength: float  # [-1.0, 1.0]
    handler_name: str | None
    error: str | None
    feedback_signals: dict[str, float | int | str | bool | None]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "action_name": self.action_name,
            "outcome_type": self.outcome_type,
            "signal_strength": round(self.signal_strength, 4),
            "handler_name": self.handler_name,
            "error": self.error,
            "feedback_signals": dict(self.feedback_signals),
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, d: dict) -> ExecutionFeedback:
        return cls(
            action_id=d["action_id"],
            action_name=d["action_name"],
            outcome_type=d["outcome_type"],
            signal_strength=d["signal_strength"],
            handler_name=d.get("handler_name"),
            error=d.get("error"),
            feedback_signals=d.get("feedback_signals", {}),
            warnings=tuple(d.get("warnings", ())),
        )


@dataclass(frozen=True)
class FeedbackObservation:
    """Substrate-compatible text observation from feedback."""

    text: str
    source: str  # always "execution_feedback"
    action_id: str
    outcome_type: str

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "source": self.source,
            "action_id": self.action_id,
            "outcome_type": self.outcome_type,
        }

    @classmethod
    def from_dict(cls, d: dict) -> FeedbackObservation:
        return cls(
            text=d["text"],
            source=d.get("source", "execution_feedback"),
            action_id=d["action_id"],
            outcome_type=d["outcome_type"],
        )


@dataclass(frozen=True)
class FeedbackNormalizationResult:
    """Combined output from normalize_execution_feedback()."""

    feedback: ExecutionFeedback
    observation: FeedbackObservation
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "feedback": self.feedback.to_dict(),
            "observation": self.observation.to_dict(),
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, d: dict) -> FeedbackNormalizationResult:
        return cls(
            feedback=ExecutionFeedback.from_dict(d["feedback"]),
            observation=FeedbackObservation.from_dict(d["observation"]),
            warnings=tuple(d.get("warnings", ())),
        )


# ─── Pure functions ──────────────────────────────────────────────


def _compute_signal_strength(outcome_type: str, confidence: float) -> float:
    """Compute signal strength from outcome and confidence.

    Positive outcomes scale with +confidence.
    Negative outcomes scale with -confidence.
    Neutral outcomes always produce 0.0.
    Clamped to [-1.0, 1.0].
    """
    if outcome_type in POSITIVE_OUTCOMES:
        raw = confidence
    elif outcome_type in NEGATIVE_OUTCOMES:
        raw = -confidence
    else:
        return 0.0
    return max(-1.0, min(1.0, raw))


def _build_feedback_signals(
    outcome_type: str,
    signal_strength: float,
    confidence: float,
    handler_name: str | None,
    error: str | None,
) -> dict[str, float | int | str | bool | None]:
    """Build the standardized feedback_signals dict."""
    return {
        "execution_success": 1 if outcome_type == "success" else 0,
        "execution_failure": 1 if outcome_type == "failure" else 0,
        "execution_partial": 1 if outcome_type == "partial" else 0,
        "execution_unknown": 1 if outcome_type == "unknown" else 0,
        "execution_confidence": round(confidence, 4),
        "execution_signal_strength": round(signal_strength, 4),
        "execution_handler_present": handler_name is not None,
        "execution_error_present": error is not None,
    }


def execution_to_feedback(
    execution_result: object,
    confidence: float = 0.5,
) -> ExecutionFeedback:
    """Normalize an ExecutionResult into structured feedback.

    Args:
        execution_result: An ExecutionResult (or any object with the same shape).
        confidence: Pipeline confidence [0.0, 1.0], used to scale signal_strength.

    Returns:
        ExecutionFeedback with deterministic outcome mapping and signal strength.
    """
    action_id = getattr(execution_result, "action_id", "")
    action_name = getattr(execution_result, "action_name", "")
    status = getattr(execution_result, "status", "")
    handler_name = getattr(execution_result, "handler_name", None)
    error = getattr(execution_result, "error", None)

    warnings: list[str] = []

    outcome_type = OUTCOME_MAP.get(status)
    if outcome_type is None:
        warnings.append(f"Unknown execution status '{status}' mapped to 'unknown'")
        outcome_type = "unknown"

    _conf = confidence if confidence is not None else 0.5
    _conf = max(0.0, min(1.0, _conf))

    signal_strength = _compute_signal_strength(outcome_type, _conf)

    feedback_signals = _build_feedback_signals(
        outcome_type=outcome_type,
        signal_strength=signal_strength,
        confidence=_conf,
        handler_name=handler_name,
        error=error,
    )

    return ExecutionFeedback(
        action_id=action_id,
        action_name=action_name,
        outcome_type=outcome_type,
        signal_strength=signal_strength,
        handler_name=handler_name,
        error=error,
        feedback_signals=feedback_signals,
        warnings=tuple(warnings),
    )


def feedback_to_observation(feedback: ExecutionFeedback) -> FeedbackObservation:
    """Convert ExecutionFeedback into a substrate-compatible text observation.

    Text format:
        execution action=<id> outcome=<type> execution_success=<0|1> execution_signal_strength=<float>
    """
    parts = [
        "execution",
        f"action={feedback.action_id}",
        f"outcome={feedback.outcome_type}",
        f"execution_success={feedback.feedback_signals.get('execution_success', 0)}",
        f"execution_signal_strength={feedback.feedback_signals.get('execution_signal_strength', 0.0)}",
    ]
    text = " ".join(parts)

    return FeedbackObservation(
        text=text,
        source="execution_feedback",
        action_id=feedback.action_id,
        outcome_type=feedback.outcome_type,
    )


def normalize_execution_feedback(
    execution_result: object,
    confidence: float = 0.5,
) -> FeedbackNormalizationResult:
    """Combined helper: ExecutionResult → feedback + observation.

    Equivalent to calling execution_to_feedback() then feedback_to_observation().
    Merges warnings from both steps.
    """
    feedback = execution_to_feedback(execution_result, confidence=confidence)
    observation = feedback_to_observation(feedback)

    all_warnings = list(feedback.warnings)

    return FeedbackNormalizationResult(
        feedback=feedback,
        observation=observation,
        warnings=tuple(all_warnings),
    )


if __name__ == "__main__":
    print("execution_feedback import OK")
