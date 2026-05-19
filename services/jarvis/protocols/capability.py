"""Capability protocol — what the substrate CAN do and how to invoke it."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CapabilityStatus(str, Enum):
    """Current availability of a capability."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"


class CapabilityCategory(str, Enum):
    """Broad category of capability."""

    COMPUTE = "compute"
    COMMUNICATE = "communicate"
    STORE = "store"
    RETRIEVE = "retrieve"
    TRANSFORM = "transform"
    OBSERVE = "observe"
    DECIDE = "decide"


class Capability(BaseModel):
    """A registered capability the substrate can invoke."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(max_length=120)
    category: CapabilityCategory
    status: CapabilityStatus = CapabilityStatus.AVAILABLE
    adapter_id: UUID | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    cost_per_invocation: float = 0.0
    rate_limit: int | None = None
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_usable(self) -> bool:
        return self.status in (CapabilityStatus.AVAILABLE, CapabilityStatus.DEGRADED)


class CapabilityInvocation(BaseModel):
    """A request to use a specific capability."""

    id: UUID = Field(default_factory=uuid4)
    capability_id: UUID
    governance_verdict_id: UUID
    input_data: dict[str, Any] = Field(default_factory=dict)
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: UUID | None = None
