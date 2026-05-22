"""Organism protocols — typed contracts for the agent society."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    CRITIQUING = "critiquing"
    BLOCKED = "blocked"
    OFFLINE = "offline"


class CritiqueResult(BaseModel):
    score: int = Field(ge=1, le=10)
    reasoning: str = Field(max_length=500)
    iteration: int = 1
    threshold: int = 7

    @property
    def passed(self) -> bool:
        return self.score >= self.threshold


class Deliverable(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    agent_id: str
    task_id: str
    content: str
    self_critique: CritiqueResult
    parent_trace_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentMessage(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    sender: str
    recipient: str
    intent: str = Field(max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)
    conversation_id: UUID = Field(default_factory=uuid4)
    parent_message_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkerSpec(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    parent_agent_id: str
    task: str = Field(max_length=500)
    environment_id: str = "vps-prod"
    tools: list[str] = Field(default_factory=list)
    model_tier: str = "sonnet"
    risk_class: str = "READ_ONLY"
    timeout_s: float = 60.0
    parent_trace_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LearningSignal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    agent_id: str
    deliverable_id: str
    pattern_observed: str = Field(max_length=500)
    generalization_hint: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
