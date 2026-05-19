"""Adapter protocol — mediated access to external systems."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AdapterType(str, Enum):
    """What kind of external system the adapter connects to."""

    LLM = "llm"
    DATABASE = "database"
    API = "api"
    FILESYSTEM = "filesystem"
    MESSAGING = "messaging"
    BROWSER = "browser"
    TOOL = "tool"


class AdapterStatus(str, Enum):
    """Adapter health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    DISCONNECTED = "disconnected"


class AdapterConfig(BaseModel):
    """Configuration for an adapter instance."""

    id: UUID = Field(default_factory=uuid4)
    adapter_type: AdapterType
    name: str = Field(max_length=120)
    endpoint: str | None = None
    status: AdapterStatus = AdapterStatus.DISCONNECTED
    timeout_seconds: float = 30.0
    retry_count: int = 3
    auth_required: bool = False
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdapterRequest(BaseModel):
    """A request to interact with an external system through an adapter."""

    id: UUID = Field(default_factory=uuid4)
    adapter_id: UUID
    operation: str = Field(max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)
    governance_verdict_id: UUID | None = None
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timeout_override: float | None = None


class AdapterResponse(BaseModel):
    """Response from an adapter after interacting with external system."""

    id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    adapter_id: UUID
    success: bool
    response_data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    latency_ms: float = 0.0
    responded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
