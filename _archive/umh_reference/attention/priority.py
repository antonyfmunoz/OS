"""UMH Attention Priority — task prioritization model.

Pure data model for priority scoring. No execution, no side effects.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum

from umh.core.clock import iso_now as _iso_now


class AttentionState(str, Enum):
    """Attention states for queued items."""

    READY = "ready"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    RUNNING = "running"
    STARVED = "starved"


@dataclass
class PriorityBreakdown:
    """Explainable priority scoring breakdown."""

    importance: float = 0.0
    recency: float = 0.0
    failure_pressure: float = 0.0
    dependency_value: float = 0.0
    cost_penalty: float = 0.0

    def to_dict(self) -> dict:
        return {
            "importance": round(self.importance, 3),
            "recency": round(self.recency, 3),
            "failure_pressure": round(self.failure_pressure, 3),
            "dependency_value": round(self.dependency_value, 3),
            "cost_penalty": round(self.cost_penalty, 3),
        }


@dataclass
class PriorityEntry:
    """A task's priority state in the attention system."""

    task_id: str
    goal_id: str = ""
    priority_score: float = 0.0
    breakdown: PriorityBreakdown = field(default_factory=PriorityBreakdown)
    state: AttentionState = AttentionState.READY
    age_seconds: float = 0.0
    starvation_boost: float = 0.0
    created_at: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"pri_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = _iso_now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "goal_id": self.goal_id,
            "priority_score": round(self.priority_score, 3),
            "breakdown": self.breakdown.to_dict(),
            "state": self.state.value,
            "age_seconds": round(self.age_seconds, 1),
            "starvation_boost": round(self.starvation_boost, 3),
            "created_at": self.created_at,
        }
