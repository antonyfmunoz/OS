"""Canonical Reality Model — compressed, reusable intelligence.

Sacred — updated only through governed promotion.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CanonicalPattern(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(max_length=200)
    domain: str = Field(max_length=100)
    description: str = Field(max_length=1000)
    evidence_count: int = Field(ge=0, default=0)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    promoted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalRealityModel:
    """In-memory canonical store. Neon persistence added in later phase."""

    def __init__(self) -> None:
        self._patterns: dict[str, CanonicalPattern] = {}

    def store(self, pattern: CanonicalPattern) -> UUID:
        self._patterns[pattern.name] = pattern
        return pattern.id

    def get_by_name(self, name: str) -> CanonicalPattern | None:
        return self._patterns.get(name)

    def list_by_domain(self, domain: str) -> list[CanonicalPattern]:
        return [p for p in self._patterns.values() if p.domain == domain]

    def all(self) -> list[CanonicalPattern]:
        return list(self._patterns.values())

    def update(
        self, name: str, governance_approved: bool = False, **fields: Any
    ) -> CanonicalPattern:
        if not governance_approved:
            raise ValueError(
                "Canonical patterns require governance approval to update. "
                "Pass governance_approved=True after governance gate."
            )
        pattern = self._patterns.get(name)
        if pattern is None:
            raise KeyError(f"Pattern '{name}' not found")
        for key, value in fields.items():
            if hasattr(pattern, key):
                object.__setattr__(pattern, key, value)
        return pattern
