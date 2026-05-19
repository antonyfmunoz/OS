"""Decomposition protocol — breaks interpretations into actionable components."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    """Type of decomposed component."""

    TASK = "task"
    QUERY = "query"
    CONSTRAINT = "constraint"
    DEPENDENCY = "dependency"
    ASSUMPTION = "assumption"
    RISK = "risk"


class DecomposedComponent(BaseModel):
    """A single atomic component from decomposition."""

    id: UUID = Field(default_factory=uuid4)
    component_type: ComponentType
    description: str = Field(max_length=300)
    ordering: int = 0
    dependencies: list[UUID] = Field(default_factory=list)
    capability_required: str | None = None
    estimated_complexity: float = Field(default=0.5, ge=0.0, le=1.0)


class Decomposition(BaseModel):
    """The result of breaking an interpretation into actionable pieces."""

    id: UUID = Field(default_factory=uuid4)
    interpretation_id: UUID
    components: list[DecomposedComponent] = Field(default_factory=list)
    total_complexity: float = Field(default=0.0, ge=0.0)
    parallelizable: bool = False
    decomposed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def tasks(self) -> list[DecomposedComponent]:
        return [c for c in self.components if c.component_type == ComponentType.TASK]

    def constraints(self) -> list[DecomposedComponent]:
        return [c for c in self.components if c.component_type == ComponentType.CONSTRAINT]

    def critical_path(self) -> list[DecomposedComponent]:
        """Components with no dependencies — they must execute first."""
        return [c for c in self.components if not c.dependencies]
