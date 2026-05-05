"""Workflow definitions — multi-cell pipeline coordination.

Defines the shape of cell workflows: sequential or DAG-based pipelines
where each step spawns a cell type with an objective. Steps can depend
on other steps, enabling parallel branches that converge.

No imports from execution, adapters, tools, or shell.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any

from umh.cells.models import CellType, _gen_id
from umh.core.clock import iso_now as _iso_now


@unique
class WorkflowStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_WORKFLOW_TERMINAL = frozenset(
    {WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED}
)


@unique
class WorkflowStepStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class CellWorkflowStep:
    """A single step in a cell workflow."""

    step_id: str
    cell_type: CellType
    objective: str
    depends_on: tuple[str, ...] = ()
    input_keys: tuple[str, ...] = ()
    output_key: str | None = None
    required: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "cell_type": self.cell_type.value,
            "objective": self.objective,
            "depends_on": list(self.depends_on),
            "input_keys": list(self.input_keys),
            "output_key": self.output_key,
            "required": self.required,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CellWorkflowStep:
        return cls(
            step_id=data["step_id"],
            cell_type=CellType(data["cell_type"]),
            objective=data["objective"],
            depends_on=tuple(data.get("depends_on", ())),
            input_keys=tuple(data.get("input_keys", ())),
            output_key=data.get("output_key"),
            required=data.get("required", True),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CellWorkflow:
    """Definition of a multi-cell pipeline."""

    workflow_id: str
    objective: str
    steps: list[CellWorkflowStep]
    status: WorkflowStatus = WorkflowStatus.CREATED
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = _iso_now()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "objective": self.objective,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CellWorkflow:
        return cls(
            workflow_id=data["workflow_id"],
            objective=data["objective"],
            steps=[CellWorkflowStep.from_dict(s) for s in data["steps"]],
            status=WorkflowStatus(data.get("status", "created")),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            metadata=data.get("metadata", {}),
        )

    def step_by_id(self, step_id: str) -> CellWorkflowStep | None:
        for s in self.steps:
            if s.step_id == step_id:
                return s
        return None


@dataclass
class WorkflowRun:
    """Live execution state of a workflow instance."""

    run_id: str
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.CREATED
    step_statuses: dict[str, WorkflowStepStatus] = field(default_factory=dict)
    step_cell_ids: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = _iso_now()
        if not self.updated_at:
            self.updated_at = self.created_at

    @property
    def active_step_ids(self) -> list[str]:
        return [sid for sid, st in self.step_statuses.items() if st == WorkflowStepStatus.ACTIVE]

    @property
    def completed_step_ids(self) -> list[str]:
        return [sid for sid, st in self.step_statuses.items() if st == WorkflowStepStatus.COMPLETED]

    @property
    def failed_step_ids(self) -> list[str]:
        return [sid for sid, st in self.step_statuses.items() if st == WorkflowStepStatus.FAILED]

    @property
    def is_terminal(self) -> bool:
        return self.status in _WORKFLOW_TERMINAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "step_statuses": {k: v.value for k, v in self.step_statuses.items()},
            "step_cell_ids": self.step_cell_ids,
            "outputs": self.outputs,
            "errors": self.errors,
            "active_step_ids": self.active_step_ids,
            "completed_step_ids": self.completed_step_ids,
            "failed_step_ids": self.failed_step_ids,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowRun:
        return cls(
            run_id=data["run_id"],
            workflow_id=data["workflow_id"],
            status=WorkflowStatus(data.get("status", "created")),
            step_statuses={
                k: WorkflowStepStatus(v) for k, v in data.get("step_statuses", {}).items()
            },
            step_cell_ids=data.get("step_cell_ids", {}),
            outputs=data.get("outputs", {}),
            errors=data.get("errors", {}),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            metadata=data.get("metadata", {}),
        )


def runnable_steps(workflow: CellWorkflow, run: WorkflowRun) -> list[CellWorkflowStep]:
    """Return steps whose dependencies are all completed and that are still PENDING."""
    result: list[CellWorkflowStep] = []
    for step in workflow.steps:
        step_status = run.step_statuses.get(step.step_id, WorkflowStepStatus.PENDING)
        if step_status != WorkflowStepStatus.PENDING:
            continue
        deps_met = all(
            run.step_statuses.get(dep) == WorkflowStepStatus.COMPLETED for dep in step.depends_on
        )
        if deps_met:
            result.append(step)
    return result
