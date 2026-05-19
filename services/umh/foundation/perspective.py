"""Perspective schema — the lens through which the substrate interprets signals."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PerspectiveType(str, Enum):
    """The type of interpretive frame."""

    STRATEGIC = "strategic"
    OPERATIONAL = "operational"
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    ADVERSARIAL = "adversarial"
    EMPATHIC = "empathic"


class PriorityFrame(str, Enum):
    """What the perspective optimizes for."""

    REVENUE = "revenue"
    GROWTH = "growth"
    RISK_MITIGATION = "risk_mitigation"
    LEARNING = "learning"
    EFFICIENCY = "efficiency"
    RELATIONSHIP = "relationship"
    SURVIVAL = "survival"


class Perspective(BaseModel):
    """An active interpretive lens that shapes how signals are processed."""

    id: UUID = Field(default_factory=uuid4)
    perspective_type: PerspectiveType
    priority_frame: PriorityFrame
    active: bool = True
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    context_constraints: list[str] = Field(default_factory=list)
    activated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class PerspectiveStack(BaseModel):
    """The ordered set of active perspectives — determines interpretation priority."""

    id: UUID = Field(default_factory=uuid4)
    perspectives: list[Perspective] = Field(default_factory=list)
    primary_frame: PriorityFrame = PriorityFrame.REVENUE
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def active_perspectives(self) -> list[Perspective]:
        return [p for p in self.perspectives if p.active]

    def dominant_perspective(self) -> Perspective | None:
        active = self.active_perspectives()
        if not active:
            return None
        return max(active, key=lambda p: p.weight)
