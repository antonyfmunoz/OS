"""Epistemology schemas — how the substrate knows, believes, and tracks certainty."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EpistemicStatus(str, Enum):
    """The knowledge status of a proposition."""

    KNOWN = "known"
    BELIEVED = "believed"
    HYPOTHESIZED = "hypothesized"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"
    RETRACTED = "retracted"


class EvidenceType(str, Enum):
    """How evidence was obtained."""

    DIRECT_OBSERVATION = "direct_observation"
    INFERENCE = "inference"
    TESTIMONY = "testimony"
    MEASUREMENT = "measurement"
    DERIVATION = "derivation"
    ASSUMPTION = "assumption"


class ConfidenceLevel(BaseModel):
    """Quantified epistemic confidence with justification."""

    value: float = Field(ge=0.0, le=1.0)
    basis: EvidenceType
    justification: str = Field(max_length=300)
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Belief(BaseModel):
    """A proposition held by the substrate with tracked epistemic status."""

    id: UUID = Field(default_factory=uuid4)
    proposition: str = Field(max_length=500)
    status: EpistemicStatus = EpistemicStatus.HYPOTHESIZED
    confidence: ConfidenceLevel
    source_signal_id: UUID | None = None
    supporting_evidence: list[UUID] = Field(default_factory=list)
    contradicting_evidence: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_actionable(self) -> bool:
        return (
            self.status in (EpistemicStatus.KNOWN, EpistemicStatus.BELIEVED)
            and self.confidence.value >= 0.6
        )


class EpistemicRevision(BaseModel):
    """Records a change in epistemic status — belief revision event."""

    id: UUID = Field(default_factory=uuid4)
    belief_id: UUID
    previous_status: EpistemicStatus
    new_status: EpistemicStatus
    previous_confidence: float
    new_confidence: float
    reason: str = Field(max_length=300)
    trigger_signal_id: UUID | None = None
    revised_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeGap(BaseModel):
    """An identified gap in the substrate's knowledge that may require action."""

    id: UUID = Field(default_factory=uuid4)
    domain: str = Field(max_length=120)
    question: str = Field(max_length=500)
    importance: float = Field(ge=0.0, le=1.0, default=0.5)
    blocking_goals: list[UUID] = Field(default_factory=list)
    identified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
