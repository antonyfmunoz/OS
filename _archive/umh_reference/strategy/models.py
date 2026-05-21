"""UMH Strategy Models — goal decomposition data structures.

Defines Strategy and StrategyStep for deterministic goal-to-task decomposition.
Strategies are pure data — no execution, no side effects, no tool calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum

from umh.core.clock import iso_now as _iso_now


class ApproachType(str, Enum):
    """How strategy steps relate to each other."""

    LINEAR = "linear"
    PARALLEL = "parallel"
    PHASED = "phased"


class StepType(str, Enum):
    """Classification of what a strategy step does."""

    RESEARCH = "research"
    EXECUTION = "execution"
    VALIDATION = "validation"
    DECISION = "decision"


class StepComplexity(str, Enum):
    """Estimated complexity of a strategy step."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StepStatus(str, Enum):
    """Execution status of a strategy step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class StrategyStep:
    """A single step in a goal decomposition strategy."""

    description: str
    type: StepType = StepType.EXECUTION
    id: str = ""
    dependencies: list[str] = field(default_factory=list)
    estimated_complexity: StepComplexity = StepComplexity.MEDIUM
    generates_tasks: bool = True
    status: StepStatus = StepStatus.PENDING
    task_ids: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"step_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "type": self.type.value,
            "dependencies": self.dependencies,
            "estimated_complexity": self.estimated_complexity.value,
            "generates_tasks": self.generates_tasks,
            "status": self.status.value,
            "task_ids": self.task_ids,
            "metadata": self.metadata,
        }


@dataclass
class Strategy:
    """A decomposition plan for achieving a goal through structured steps."""

    goal_id: str
    objective: str
    approach_type: ApproachType = ApproachType.LINEAR
    steps: list[StrategyStep] = field(default_factory=list)
    confidence: float = 1.0
    reasoning: str = ""
    id: str = ""
    created_at: str = ""
    updated_at: str = ""
    template_used: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"strat_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = _iso_now()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "objective": self.objective,
            "approach_type": self.approach_type.value,
            "steps": [s.to_dict() for s in self.steps],
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "template_used": self.template_used,
            "metadata": self.metadata,
        }

    def pending_steps(self) -> list[StrategyStep]:
        """Return steps that are pending and have generates_tasks=True."""
        return [s for s in self.steps if s.status == StepStatus.PENDING and s.generates_tasks]

    def ready_steps(self) -> list[StrategyStep]:
        """Return pending task-generating steps whose dependencies are satisfied."""
        completed_ids = {s.id for s in self.steps if s.status == StepStatus.COMPLETED}
        result = []
        for step in self.pending_steps():
            if all(dep in completed_ids for dep in step.dependencies):
                result.append(step)
        return result

    def progress(self) -> float:
        """Compute completion ratio (0.0–1.0)."""
        if not self.steps:
            return 0.0
        done = sum(1 for s in self.steps if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED))
        return done / len(self.steps)

    def mark_step_completed(self, step_id: str) -> bool:
        """Mark a step as completed. Returns True if found."""
        for step in self.steps:
            if step.id == step_id:
                step.status = StepStatus.COMPLETED
                self.updated_at = _iso_now()
                return True
        return False

    def mark_step_failed(self, step_id: str) -> bool:
        """Mark a step as failed. Returns True if found."""
        for step in self.steps:
            if step.id == step_id:
                step.status = StepStatus.FAILED
                self.updated_at = _iso_now()
                return True
        return False

    def add_task_to_step(self, step_id: str, task_id: str) -> bool:
        """Record a task_id against a step. Returns True if step found."""
        for step in self.steps:
            if step.id == step_id:
                step.task_ids.append(task_id)
                step.status = StepStatus.IN_PROGRESS
                self.updated_at = _iso_now()
                return True
        return False
