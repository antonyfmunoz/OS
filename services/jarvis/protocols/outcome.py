"""Outcome protocol — the final result of a complete signal-to-action cycle."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class OutcomeType(str, Enum):
    """Category of outcome."""

    ACTION_COMPLETED = "action_completed"
    INFORMATION_DELIVERED = "information_delivered"
    STATE_CHANGED = "state_changed"
    NO_ACTION_NEEDED = "no_action_needed"
    ESCALATED = "escalated"
    FAILED = "failed"


class Outcome(BaseModel):
    """The final result of processing a signal through the full pipeline."""

    id: UUID = Field(default_factory=uuid4)
    signal_id: UUID
    trace_id: UUID
    outcome_type: OutcomeType
    summary: str = Field(max_length=300)
    results: list[UUID] = Field(default_factory=list)
    goals_affected: list[UUID] = Field(default_factory=list)
    beliefs_updated: list[UUID] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_successful(self) -> bool:
        return self.outcome_type not in (OutcomeType.FAILED, OutcomeType.ESCALATED)
