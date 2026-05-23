"""Possibility space schema — models what COULD happen, not just what IS."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PossibilityStatus(str, Enum):
    """Lifecycle of a possibility."""

    OPEN = "open"
    EXPLORED = "explored"
    SELECTED = "selected"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REALIZED = "realized"


class ActionType(str, Enum):
    """Categories of possible actions."""

    OBSERVE = "observe"
    COMMUNICATE = "communicate"
    COMPUTE = "compute"
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    DELEGATE = "delegate"
    WAIT = "wait"


class Possibility(BaseModel):
    """A single possible action or state transition the substrate could take."""

    id: UUID = Field(default_factory=uuid4)
    action_type: ActionType
    description: str = Field(max_length=300)
    status: PossibilityStatus = PossibilityStatus.OPEN
    estimated_value: float = Field(default=0.0)
    estimated_cost: float = Field(default=0.0)
    estimated_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    preconditions: list[str] = Field(default_factory=list)
    consequences: list[str] = Field(default_factory=list)
    deadline: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def net_value(self) -> float:
        return self.estimated_value - self.estimated_cost

    def is_viable(self) -> bool:
        return self.status == PossibilityStatus.OPEN and self.estimated_risk < 0.9


class PossibilitySpace(BaseModel):
    """The set of all currently recognized possibilities."""

    id: UUID = Field(default_factory=uuid4)
    possibilities: list[Possibility] = Field(default_factory=list)
    context_id: UUID | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def viable(self) -> list[Possibility]:
        return [p for p in self.possibilities if p.is_viable()]

    def best_by_value(self) -> Possibility | None:
        viable = self.viable()
        if not viable:
            return None
        return max(viable, key=lambda p: p.net_value())

    def expired(self, now: datetime | None = None) -> list[Possibility]:
        now = now or datetime.now(timezone.utc)
        return [
            p
            for p in self.possibilities
            if p.deadline and p.deadline < now and p.status == PossibilityStatus.OPEN
        ]
