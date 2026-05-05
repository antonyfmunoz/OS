"""Phase 78 outcome contracts — trace-derived execution outcome artifacts.

OutcomeRecord represents the interpretable result of a governed execution.
Classification is deterministic and derived from trace/result data only.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class OutcomeStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    DENIED = "denied"
    VALIDATION_FAILED = "validation_failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"
    INSUFFICIENT_DATA = "insufficient_data"


class OutcomeSource(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ADAPTER = "adapter"
    GOVERNANCE = "governance"
    TRACE = "trace"
    WORKSTATION = "workstation"


@dataclass
class OutcomeRecord:
    outcome_id: str
    trace_id: str
    user_id: str
    session_id: str = ""
    status: OutcomeStatus = OutcomeStatus.UNKNOWN
    success_score: float = 0.0
    confidence: float = 0.0
    summary: str = ""
    evidence: list[str] = field(default_factory=list)
    observed_outputs: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    source: OutcomeSource = OutcomeSource.SYSTEM
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "success_score": round(self.success_score, 4),
            "confidence": round(self.confidence, 4),
            "summary": self.summary,
            "evidence": self.evidence,
            "observed_outputs": self.observed_outputs,
            "errors": self.errors,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "source": self.source.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OutcomeRecord:
        return cls(
            outcome_id=data["outcome_id"],
            trace_id=data.get("trace_id", ""),
            user_id=data.get("user_id", ""),
            session_id=data.get("session_id", ""),
            status=OutcomeStatus(data.get("status", "unknown")),
            success_score=clamp_score(data.get("success_score", 0.0)),
            confidence=clamp_score(data.get("confidence", 0.0)),
            summary=data.get("summary", ""),
            evidence=data.get("evidence", []),
            observed_outputs=data.get("observed_outputs", {}),
            errors=data.get("errors", []),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            source=OutcomeSource(data.get("source", "system")),
            metadata=data.get("metadata", {}),
        )


def create_outcome_id(trace_id: str) -> str:
    return f"oc_{trace_id}_{uuid.uuid4().hex[:8]}"


def clamp_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_outcome_status(value: str) -> OutcomeStatus:
    value = value.strip().lower()
    for member in OutcomeStatus:
        if member.value == value:
            return member
    return OutcomeStatus.UNKNOWN
