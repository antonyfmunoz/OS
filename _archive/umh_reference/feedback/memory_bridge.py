"""Phase 78 memory bridge — conservative memory candidate creation.

Memory candidates are created from outcomes but NEVER promoted automatically.
Default status is CANDIDATE. No canonical/semantic memory mutation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.feedback.outcome import OutcomeRecord, OutcomeStatus, clamp_score
from umh.feedback.records import FeedbackRecord, FeedbackSignalType


class MemoryCandidateType(str, Enum):
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    BEHAVIORAL = "behavioral"
    TRACE_SUMMARY = "trace_summary"
    USER_PREFERENCE = "user_preference"
    ERROR_PATTERN = "error_pattern"
    CAPABILITY_OBSERVATION = "capability_observation"
    ADAPTER_OBSERVATION = "adapter_observation"


class MemoryPromotionStatus(str, Enum):
    CANDIDATE = "candidate"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"
    PROMOTED = "promoted"


@dataclass
class MemoryCandidate:
    candidate_id: str
    trace_id: str
    outcome_id: str
    user_id: str
    session_id: str = ""
    memory_type: MemoryCandidateType = MemoryCandidateType.EPISODIC
    content: str = ""
    confidence: float = 0.0
    reason: str = ""
    evidence: list[str] = field(default_factory=list)
    promotion_status: MemoryPromotionStatus = MemoryPromotionStatus.CANDIDATE
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "trace_id": self.trace_id,
            "outcome_id": self.outcome_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
            "evidence": self.evidence,
            "promotion_status": self.promotion_status.value,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryCandidate:
        return cls(
            candidate_id=data["candidate_id"],
            trace_id=data.get("trace_id", ""),
            outcome_id=data.get("outcome_id", ""),
            user_id=data.get("user_id", ""),
            session_id=data.get("session_id", ""),
            memory_type=MemoryCandidateType(data.get("memory_type", "episodic")),
            content=data.get("content", ""),
            confidence=clamp_score(data.get("confidence", 0.0)),
            reason=data.get("reason", ""),
            evidence=data.get("evidence", []),
            promotion_status=MemoryPromotionStatus(data.get("promotion_status", "candidate")),
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata", {}),
        )


_STATUS_TO_CANDIDATE_TYPE: dict[OutcomeStatus, MemoryCandidateType] = {
    OutcomeStatus.SUCCESS: MemoryCandidateType.EPISODIC,
    OutcomeStatus.PARTIAL_SUCCESS: MemoryCandidateType.EPISODIC,
    OutcomeStatus.FAILURE: MemoryCandidateType.ERROR_PATTERN,
    OutcomeStatus.DENIED: MemoryCandidateType.TRACE_SUMMARY,
    OutcomeStatus.VALIDATION_FAILED: MemoryCandidateType.ERROR_PATTERN,
    OutcomeStatus.TIMEOUT: MemoryCandidateType.ERROR_PATTERN,
    OutcomeStatus.CANCELLED: MemoryCandidateType.TRACE_SUMMARY,
}


def should_create_memory_candidate(outcome: OutcomeRecord) -> bool:
    if outcome.status in (OutcomeStatus.UNKNOWN, OutcomeStatus.INSUFFICIENT_DATA):
        return False
    if outcome.confidence < 0.2:
        return False
    return True


def create_memory_candidate_from_outcome(
    outcome: OutcomeRecord,
    feedback: FeedbackRecord | None = None,
) -> MemoryCandidate | None:
    if not should_create_memory_candidate(outcome):
        if outcome.status == OutcomeStatus.INSUFFICIENT_DATA:
            return MemoryCandidate(
                candidate_id=f"mc_{uuid.uuid4().hex[:12]}",
                trace_id=outcome.trace_id,
                outcome_id=outcome.outcome_id,
                user_id=outcome.user_id,
                session_id=outcome.session_id,
                memory_type=MemoryCandidateType.TRACE_SUMMARY,
                content=f"Insufficient data for trace {outcome.trace_id}",
                confidence=outcome.confidence,
                reason="insufficient_data",
                promotion_status=MemoryPromotionStatus.NEEDS_REVIEW,
                created_at=_iso_now(),
            )
        return None

    memory_type = _STATUS_TO_CANDIDATE_TYPE.get(outcome.status, MemoryCandidateType.TRACE_SUMMARY)

    if feedback and feedback.signal_type == FeedbackSignalType.USER_CORRECTION:
        memory_type = MemoryCandidateType.USER_PREFERENCE

    content_parts = [f"Outcome: {outcome.status.value}"]
    if outcome.summary:
        content_parts.append(outcome.summary)
    if outcome.errors:
        content_parts.append(f"Errors: {'; '.join(outcome.errors[:3])}")
    content = " | ".join(content_parts)

    return MemoryCandidate(
        candidate_id=f"mc_{uuid.uuid4().hex[:12]}",
        trace_id=outcome.trace_id,
        outcome_id=outcome.outcome_id,
        user_id=outcome.user_id,
        session_id=outcome.session_id,
        memory_type=memory_type,
        content=content[:500],
        confidence=outcome.confidence,
        reason=f"auto_from_{outcome.status.value}",
        evidence=list(outcome.evidence[:5]),
        promotion_status=MemoryPromotionStatus.CANDIDATE,
        created_at=_iso_now(),
    )
