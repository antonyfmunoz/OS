"""Environment protocol — models the substrate's awareness of its operating context."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EnvironmentDomain(str, Enum):
    """Which aspect of the environment is being tracked."""

    COMPUTE = "compute"
    NETWORK = "network"
    STORAGE = "storage"
    TIME = "time"
    USER_CONTEXT = "user_context"
    SYSTEM_STATE = "system_state"


class ResourceStatus(str, Enum):
    """Status of an environmental resource."""

    NOMINAL = "nominal"
    CONSTRAINED = "constrained"
    CRITICAL = "critical"
    UNAVAILABLE = "unavailable"


class EnvironmentFact(BaseModel):
    """A single observation about the current environment."""

    domain: EnvironmentDomain
    key: str = Field(max_length=120)
    value: Any
    status: ResourceStatus = ResourceStatus.NOMINAL
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EnvironmentSnapshot(BaseModel):
    """A point-in-time view of the operating environment."""

    id: UUID = Field(default_factory=uuid4)
    facts: list[EnvironmentFact] = Field(default_factory=list)
    constraints_active: list[str] = Field(default_factory=list)
    taken_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_healthy(self) -> bool:
        return all(
            f.status in (ResourceStatus.NOMINAL, ResourceStatus.CONSTRAINED) for f in self.facts
        )

    def critical_resources(self) -> list[EnvironmentFact]:
        return [f for f in self.facts if f.status == ResourceStatus.CRITICAL]
