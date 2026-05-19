"""Memory candidate protocol — the pathway for durable state writes."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """What kind of memory is being written."""

    FACT = "fact"
    BELIEF = "belief"
    DECISION = "decision"
    OBSERVATION = "observation"
    COMMITMENT = "commitment"
    FEEDBACK = "feedback"
    RELATIONSHIP = "relationship"


class MemoryCandidate(BaseModel):
    """A proposed write to durable memory — must pass governance."""

    id: UUID = Field(default_factory=uuid4)
    memory_type: MemoryType
    content: str = Field(max_length=1000)
    source_signal_id: UUID | None = None
    source_trace_id: UUID | None = None
    governance_verdict_id: UUID | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    tags: list[str] = Field(default_factory=list)
    supersedes: list[UUID] = Field(default_factory=list)
    proposed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryUpdate(BaseModel):
    """A modification to an existing memory entry."""

    id: UUID = Field(default_factory=uuid4)
    target_memory_id: UUID
    update_type: str = Field(max_length=60)
    previous_value: Any = None
    new_value: Any = None
    reason: str = Field(max_length=300)
    governance_verdict_id: UUID | None = None
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryWriteResult(BaseModel):
    """Confirmation that a memory candidate was persisted."""

    candidate_id: UUID
    memory_id: UUID
    written_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    error: str | None = None
