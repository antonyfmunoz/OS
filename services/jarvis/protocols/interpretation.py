"""Interpretation protocol — transforms a Signal into structured meaning."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class InterpretationType(str, Enum):
    """What kind of meaning was extracted."""

    REQUEST = "request"
    INFORMATION = "information"
    FEEDBACK = "feedback"
    QUESTION = "question"
    COMMAND = "command"
    NOTIFICATION = "notification"
    CONSTRAINT = "constraint"


class Intent(BaseModel):
    """A recognized intent within the interpretation."""

    action: str = Field(max_length=120)
    target: str | None = Field(default=None, max_length=120)
    parameters: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)


class Interpretation(BaseModel):
    """The structured meaning derived from a Signal."""

    id: UUID = Field(default_factory=uuid4)
    signal_id: UUID
    interpretation_type: InterpretationType
    summary: str = Field(max_length=300)
    intents: list[Intent] = Field(default_factory=list)
    entities_referenced: list[str] = Field(default_factory=list)
    requires_action: bool = False
    requires_response: bool = False
    context_dependencies: list[UUID] = Field(default_factory=list)
    interpreted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def primary_intent(self) -> Intent | None:
        if not self.intents:
            return None
        return max(self.intents, key=lambda i: i.confidence)
