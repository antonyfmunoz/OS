"""Execution result protocol — the outcome of a work packet's execution."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ExecutionOutcome(str, Enum):
    """High-level execution outcome."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    REJECTED = "rejected"


class ExecutionResult(BaseModel):
    """The complete result of executing a work packet."""

    id: UUID = Field(default_factory=uuid4)
    work_packet_id: UUID
    trace_id: UUID
    outcome: ExecutionOutcome
    output_data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0
    resources_consumed: dict[str, float] = Field(default_factory=dict)
    side_effects: list[str] = Field(default_factory=list)
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_success(self) -> bool:
        return self.outcome in (ExecutionOutcome.SUCCESS, ExecutionOutcome.PARTIAL_SUCCESS)
