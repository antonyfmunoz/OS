"""Signal protocol — the universal intake type. Everything enters as a Signal."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SignalSource(str, Enum):
    """Where the signal originated."""

    USER = "user"
    SYSTEM = "system"
    EXTERNAL_API = "external_api"
    SCHEDULED = "scheduled"
    INTERNAL_EVENT = "internal_event"
    ADAPTER = "adapter"


class SignalUrgency(str, Enum):
    """How time-sensitive the signal is."""

    IMMEDIATE = "immediate"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class Signal(BaseModel):
    """The universal intake type — all external input enters as a Signal."""

    id: UUID = Field(default_factory=uuid4)
    source: SignalSource
    urgency: SignalUrgency = SignalUrgency.NORMAL
    content_type: str = Field(max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)
    raw_content: str | None = None
    source_identifier: str | None = Field(default=None, max_length=200)
    correlation_id: UUID | None = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_user_initiated(self) -> bool:
        return self.source == SignalSource.USER
