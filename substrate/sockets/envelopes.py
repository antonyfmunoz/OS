"""Envelope dataclasses — the data shapes that cross the socket boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from substrate.types import SignalUrgency


class SignalEnvelope(BaseModel):
    """What an integration hands to the Signal socket."""

    model_config = ConfigDict(frozen=True)

    integration_id: str
    content_type: str
    payload: dict[str, Any]
    raw_content: str | None = None
    source_identifier: str | None = None
    correlation_id: UUID | None = None
    urgency: SignalUrgency = SignalUrgency.NORMAL
    metadata: dict[str, Any] = Field(default_factory=dict)


class SignalReceipt(BaseModel):
    """Returned to the integration after a signal is accepted or rejected."""

    model_config = ConfigDict(frozen=True)

    signal_id: UUID
    trace_id: UUID
    accepted: bool
    accepted_at: datetime
    rejection_reason: str | None = None


class CapabilityRequest(BaseModel):
    """UMH asks an integration to do something."""

    model_config = ConfigDict(frozen=True)

    request_id: UUID
    capability_name: str
    integration_id: str
    params: dict[str, Any]
    governance_verdict_id: UUID
    trace_id: UUID
    timeout_seconds: float = 30.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityResponse(BaseModel):
    """Integration's answer to a capability request."""

    model_config = ConfigDict(frozen=True)

    request_id: UUID
    success: bool
    result_data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    raw_error: str | None = None
    latency_ms: float = 0.0
    side_effects: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OutcomeEnvelope(BaseModel):
    """What UMH sends to integrations when a pipeline completes."""

    model_config = ConfigDict(frozen=True)

    outcome_id: UUID
    signal_id: UUID
    trace_id: UUID
    integration_id: str
    outcome_type: str
    summary: str
    result_data: dict[str, Any] = Field(default_factory=dict)
    governance_decision: str = ""
    confidence: float = 1.0
    duration_ms: float = 0.0
    correlation_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ViewFrame(BaseModel):
    """A single frame of pipeline state for external observers."""

    model_config = ConfigDict(frozen=True)

    frame_id: UUID
    timestamp: datetime
    event_type: str
    stage: int
    data: dict[str, Any]
    trace_id: UUID | None = None
    signal_id: UUID | None = None
    integration_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
