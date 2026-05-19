"""Work packet protocol — the unit of governed, traceable execution."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WorkPacketStatus(str, Enum):
    """Lifecycle of a work packet."""

    PENDING = "pending"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkPacketPriority(str, Enum):
    """Execution priority."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class WorkPacket(BaseModel):
    """The fundamental unit of execution — carries governance approval and trace context."""

    id: UUID = Field(default_factory=uuid4)
    governance_verdict_id: UUID
    capability_id: UUID
    trace_id: UUID
    description: str = Field(max_length=300)
    status: WorkPacketStatus = WorkPacketStatus.PENDING
    priority: WorkPacketPriority = WorkPacketPriority.NORMAL
    input_data: dict[str, Any] = Field(default_factory=dict)
    assigned_adapter_id: UUID | None = None
    max_retries: int = 1
    attempt: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_terminal(self) -> bool:
        return self.status in (
            WorkPacketStatus.COMPLETED,
            WorkPacketStatus.FAILED,
            WorkPacketStatus.CANCELLED,
        )

    def can_retry(self) -> bool:
        return self.status == WorkPacketStatus.FAILED and self.attempt < self.max_retries
