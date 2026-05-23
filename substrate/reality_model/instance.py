"""Instance Reality Model — live operational truth of one user/company/environment."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class InstanceObservation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content: str = Field(max_length=2000)
    domain: str = Field(default="general", max_length=100)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    source_signal_id: UUID | None = None
    source_trace_id: UUID | None = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class InstanceRealityModel:
    def __init__(self, user_id: str, org_id: str) -> None:
        self.user_id = user_id
        self.org_id = org_id
        self._observations: list[InstanceObservation] = []

    def record(self, observation: InstanceObservation) -> UUID:
        self._observations.append(observation)
        return observation.id

    def query(self, text: str, limit: int = 10) -> list[InstanceObservation]:
        text_lower = text.lower()
        matches = [
            obs
            for obs in self._observations
            if text_lower in obs.content.lower() or text_lower in obs.domain.lower()
        ]
        return matches[:limit]

    def list_by_domain(self, domain: str) -> list[InstanceObservation]:
        return [obs for obs in self._observations if obs.domain == domain]

    def all(self) -> list[InstanceObservation]:
        return list(self._observations)

    def count(self) -> int:
        return len(self._observations)
