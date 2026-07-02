"""Workflow types — shared data structures for all EOS workflows.

Used by WorkflowRunner and individual workflow implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class WorkflowStep:
    """A single step in a governed workflow."""

    name: str
    mutation_name: str
    intent: str
    execute_fn: Callable[[], tuple[str, bool]]
    skip_on_failure: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResult:
    """Outcome of a single workflow step."""

    step_name: str
    success: bool
    output: str = ""
    envelope_id: str = ""
    skipped: bool = False
    error: str = ""


@dataclass
class WorkflowResult:
    """Outcome of a complete workflow execution."""

    workflow_name: str
    steps_completed: int
    steps_total: int
    success: bool
    step_results: list[StepResult] = field(default_factory=list)
    duration_seconds: float = 0.0
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def outputs(self) -> list[str]:
        return [r.output for r in self.step_results if r.output]

    def summary(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return (
            f"{self.workflow_name}: {status} "
            f"({self.steps_completed}/{self.steps_total} steps, "
            f"{self.duration_seconds:.1f}s)"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "steps_completed": self.steps_completed,
            "steps_total": self.steps_total,
            "success": self.success,
            "step_results": [
                {
                    "step_name": r.step_name,
                    "success": r.success,
                    "output": r.output,
                    "envelope_id": r.envelope_id,
                    "skipped": r.skipped,
                    "error": r.error,
                }
                for r in self.step_results
            ],
            "duration_seconds": self.duration_seconds,
            "source": self.source,
            "metadata": self.metadata,
        }
