"""Derived operational constructs — higher-order types built from primitives."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .epistemology import ConfidenceLevel, EpistemicStatus
from .primitives import OntologicalCategory, TemporalMode


class GoalStatus(str, Enum):
    """Lifecycle of a goal."""

    ACTIVE = "active"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"
    BLOCKED = "blocked"
    DEFERRED = "deferred"


class Goal(BaseModel):
    """A desired state the substrate is working toward."""

    id: UUID = Field(default_factory=uuid4)
    statement: str = Field(max_length=300)
    status: GoalStatus = GoalStatus.ACTIVE
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    parent_goal_id: UUID | None = None
    deadline: datetime | None = None
    success_criteria: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    """An ordered sequence of steps toward a goal."""

    id: UUID = Field(default_factory=uuid4)
    goal_id: UUID
    steps: list[PlanStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: ConfidenceLevel | None = None


class PlanStep(BaseModel):
    """A single step in a plan."""

    id: UUID = Field(default_factory=uuid4)
    description: str = Field(max_length=300)
    ordering: int
    dependencies: list[UUID] = Field(default_factory=list)
    completed: bool = False
    capability_required: str | None = None


# Pydantic v2 forward reference resolution
Plan.model_rebuild()


class Context(BaseModel):
    """Operational context — the full situational awareness at a point in time."""

    id: UUID = Field(default_factory=uuid4)
    active_goals: list[UUID] = Field(default_factory=list)
    active_beliefs: list[UUID] = Field(default_factory=list)
    active_constraints: list[UUID] = Field(default_factory=list)
    session_id: UUID | None = None
    environment_snapshot: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Commitment(BaseModel):
    """A binding decision the substrate has made — constrains future action."""

    id: UUID = Field(default_factory=uuid4)
    statement: str = Field(max_length=300)
    goal_id: UUID | None = None
    binding: bool = True
    revocable: bool = True
    made_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_active(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        if self.expires_at and self.expires_at < now:
            return False
        return self.binding
