"""Identity continuity schema — maintains coherent self across time and context switches."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class IdentityAspect(str, Enum):
    """Facets of identity that persist across sessions."""

    CORE_VALUES = "core_values"
    OPERATIONAL_STYLE = "operational_style"
    KNOWLEDGE_DOMAIN = "knowledge_domain"
    RELATIONSHIP_PATTERN = "relationship_pattern"
    DECISION_HEURISTIC = "decision_heuristic"
    BOUNDARY = "boundary"


class ContinuityAnchor(BaseModel):
    """A stable reference point that persists across context boundaries."""

    id: UUID = Field(default_factory=uuid4)
    aspect: IdentityAspect
    statement: str = Field(max_length=300)
    immutable: bool = False
    established_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_reinforced: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reinforcement_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class IdentityState(BaseModel):
    """The full identity state at a point in time."""

    id: UUID = Field(default_factory=uuid4)
    anchors: list[ContinuityAnchor] = Field(default_factory=list)
    active_role: str = Field(default="developer_agent", max_length=80)
    session_id: UUID | None = None
    continuity_score: float = Field(default=1.0, ge=0.0, le=1.0)
    snapshot_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def immutable_anchors(self) -> list[ContinuityAnchor]:
        return [a for a in self.anchors if a.immutable]

    def drift_from(self, other: IdentityState) -> float:
        """Measure identity drift between two states (0=identical, 1=completely diverged)."""
        if not self.anchors or not other.anchors:
            return 1.0
        my_statements = {a.statement for a in self.anchors}
        their_statements = {a.statement for a in other.anchors}
        overlap = len(my_statements & their_statements)
        total = len(my_statements | their_statements)
        return 1.0 - (overlap / total) if total > 0 else 0.0
