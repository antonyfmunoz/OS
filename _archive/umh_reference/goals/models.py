"""UMH Goal Models — persistent goal types, policies, and status tracking.

Defines the data structures for long-lived goals that generate tasks
through the planning pipeline on evaluation cycles.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum

from umh.core.clock import iso_now as _iso_now


class GoalStatus(str, Enum):
    """Lifecycle status of a goal."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class GoalPriority(str, Enum):
    """Priority level for goal scheduling."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class GoalPolicy:
    """Policy constraints governing how a goal generates and executes tasks."""

    max_tasks_per_cycle: int = 3
    require_approval: bool = True
    allow_side_effects: bool = False
    evaluation_interval_sec: int = 300
    max_active_tasks: int = 5
    auto_pause_on_failure: bool = True
    cost_limit_usd: float = 0.0

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "max_tasks_per_cycle": self.max_tasks_per_cycle,
            "require_approval": self.require_approval,
            "allow_side_effects": self.allow_side_effects,
            "evaluation_interval_sec": self.evaluation_interval_sec,
            "max_active_tasks": self.max_active_tasks,
            "auto_pause_on_failure": self.auto_pause_on_failure,
            "cost_limit_usd": self.cost_limit_usd,
        }


@dataclass
class Goal:
    """A persistent goal that drives task generation through evaluation cycles."""

    name: str
    objective: str
    id: str = ""
    status: GoalStatus = GoalStatus.ACTIVE
    priority: GoalPriority = GoalPriority.MEDIUM
    created_at: str = ""
    updated_at: str = ""
    last_evaluated_at: str = ""
    progress: float = 0.0
    success_criteria: list[str] = field(default_factory=list)
    constraints: dict = field(default_factory=dict)
    policy: GoalPolicy = field(default_factory=GoalPolicy)
    metadata: dict = field(default_factory=dict)
    created_by: str = ""
    tasks_created: int = 0
    tasks_completed: int = 0

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"goal_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = _iso_now()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "objective": self.objective,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_evaluated_at": self.last_evaluated_at,
            "progress": self.progress,
            "success_criteria": self.success_criteria,
            "constraints": self.constraints,
            "policy": self.policy.to_dict(),
            "metadata": self.metadata,
            "created_by": self.created_by,
            "tasks_created": self.tasks_created,
            "tasks_completed": self.tasks_completed,
        }
