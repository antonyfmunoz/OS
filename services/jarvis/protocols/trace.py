"""Trace protocol — every operation must be traceable end-to-end."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TraceEventType(str, Enum):
    """Type of event recorded in a trace."""

    SIGNAL_RECEIVED = "signal_received"
    INTERPRETATION_COMPLETE = "interpretation_complete"
    DECOMPOSITION_COMPLETE = "decomposition_complete"
    GOVERNANCE_REQUESTED = "governance_requested"
    GOVERNANCE_DECIDED = "governance_decided"
    WORK_PACKET_CREATED = "work_packet_created"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    ADAPTER_CALLED = "adapter_called"
    ADAPTER_RESPONDED = "adapter_responded"
    MEMORY_WRITE = "memory_write"
    ERROR = "error"
    CUSTOM = "custom"


class TraceEvent(BaseModel):
    """A single event in an execution trace."""

    id: UUID = Field(default_factory=uuid4)
    trace_id: UUID
    event_type: TraceEventType
    description: str = Field(max_length=300)
    entity_id: UUID | None = None
    parent_event_id: UUID | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Trace(BaseModel):
    """A complete execution trace — from signal intake to outcome."""

    id: UUID = Field(default_factory=uuid4)
    signal_id: UUID
    events: list[TraceEvent] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    success: bool | None = None

    def add_event(self, event_type: TraceEventType, description: str, **kwargs: Any) -> TraceEvent:
        event = TraceEvent(
            trace_id=self.id,
            event_type=event_type,
            description=description,
            **kwargs,
        )
        self.events.append(event)
        return event

    def duration_ms(self) -> float | None:
        if not self.completed_at:
            return None
        delta = self.completed_at - self.started_at
        return delta.total_seconds() * 1000
