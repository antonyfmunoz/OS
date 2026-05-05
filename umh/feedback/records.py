"""Phase 78 feedback records — append-only execution feedback artifacts.

FeedbackRecord captures a single feedback signal linked to an outcome.
Score bounded [0.0, 1.0]. Source must be explicit. User vs system
feedback is distinguishable by source field.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.feedback.outcome import OutcomeRecord, OutcomeSource, OutcomeStatus, clamp_score


class FeedbackSignalType(str, Enum):
    EXECUTION_SUCCESS = "execution_success"
    EXECUTION_FAILURE = "execution_failure"
    USER_POSITIVE = "user_positive"
    USER_NEGATIVE = "user_negative"
    USER_CORRECTION = "user_correction"
    USER_NOTE = "user_note"
    SYSTEM_OBSERVATION = "system_observation"
    QUALITY_SIGNAL = "quality_signal"
    SAFETY_SIGNAL = "safety_signal"


class FeedbackSource(str, Enum):
    SYSTEM = "system"
    USER = "user"
    TRACE = "trace"
    ADAPTER = "adapter"
    GOVERNANCE = "governance"
    WORKSTATION = "workstation"


@dataclass
class FeedbackRecord:
    feedback_id: str
    trace_id: str
    outcome_id: str
    user_id: str
    session_id: str = ""
    signal_type: FeedbackSignalType = FeedbackSignalType.SYSTEM_OBSERVATION
    score: float = 0.0
    confidence: float = 0.0
    source: FeedbackSource = FeedbackSource.SYSTEM
    notes: str = ""
    evidence: list[str] = field(default_factory=list)
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "trace_id": self.trace_id,
            "outcome_id": self.outcome_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "signal_type": self.signal_type.value,
            "score": round(self.score, 4),
            "confidence": round(self.confidence, 4),
            "source": self.source.value,
            "notes": self.notes,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeedbackRecord:
        return cls(
            feedback_id=data["feedback_id"],
            trace_id=data.get("trace_id", ""),
            outcome_id=data.get("outcome_id", ""),
            user_id=data.get("user_id", ""),
            session_id=data.get("session_id", ""),
            signal_type=FeedbackSignalType(data.get("signal_type", "system_observation")),
            score=clamp_score(data.get("score", 0.0)),
            confidence=clamp_score(data.get("confidence", 0.0)),
            source=FeedbackSource(data.get("source", "system")),
            notes=data.get("notes", ""),
            evidence=data.get("evidence", []),
            timestamp=data.get("timestamp", ""),
            metadata=data.get("metadata", {}),
        )


_OUTCOME_TO_SIGNAL: dict[OutcomeStatus, FeedbackSignalType] = {
    OutcomeStatus.SUCCESS: FeedbackSignalType.EXECUTION_SUCCESS,
    OutcomeStatus.PARTIAL_SUCCESS: FeedbackSignalType.QUALITY_SIGNAL,
    OutcomeStatus.FAILURE: FeedbackSignalType.EXECUTION_FAILURE,
    OutcomeStatus.DENIED: FeedbackSignalType.SAFETY_SIGNAL,
    OutcomeStatus.VALIDATION_FAILED: FeedbackSignalType.SAFETY_SIGNAL,
    OutcomeStatus.TIMEOUT: FeedbackSignalType.EXECUTION_FAILURE,
    OutcomeStatus.CANCELLED: FeedbackSignalType.SYSTEM_OBSERVATION,
    OutcomeStatus.UNKNOWN: FeedbackSignalType.SYSTEM_OBSERVATION,
    OutcomeStatus.INSUFFICIENT_DATA: FeedbackSignalType.SYSTEM_OBSERVATION,
}


def create_feedback_id(trace_id: str, signal_type: str, source: str) -> str:
    return f"fb_{trace_id}_{signal_type[:8]}_{source[:4]}_{uuid.uuid4().hex[:6]}"


def normalize_feedback_signal(value: str) -> FeedbackSignalType:
    value = value.strip().lower()
    for member in FeedbackSignalType:
        if member.value == value:
            return member
    return FeedbackSignalType.SYSTEM_OBSERVATION


def feedback_from_outcome(outcome: OutcomeRecord) -> FeedbackRecord:
    signal_type = _OUTCOME_TO_SIGNAL.get(outcome.status, FeedbackSignalType.SYSTEM_OBSERVATION)
    return FeedbackRecord(
        feedback_id=create_feedback_id(
            outcome.trace_id, signal_type.value, OutcomeSource.SYSTEM.value
        ),
        trace_id=outcome.trace_id,
        outcome_id=outcome.outcome_id,
        user_id=outcome.user_id,
        session_id=outcome.session_id,
        signal_type=signal_type,
        score=outcome.success_score,
        confidence=outcome.confidence,
        source=FeedbackSource.SYSTEM,
        notes=outcome.summary,
        evidence=list(outcome.evidence),
        timestamp=_iso_now(),
    )
