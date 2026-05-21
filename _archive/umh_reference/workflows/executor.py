"""Workflow executor — cell-based objective decomposition and execution.

Decomposes objectives into cell workflows and executes them through
the existing CellOrchestrator. Each step spawns a cell that may
request_execution() through the bridge.

Uses CellRuntime ONLY. Uses CellOrchestrator ONLY.
No direct environment calls.

No imports from umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import logging
from typing import Any

from umh.cells.models import CellType, _gen_id
from umh.cells.orchestrator import CellOrchestrator
from umh.cells.workflow import CellWorkflow, CellWorkflowStep, WorkflowStatus

_log = logging.getLogger(__name__)


class WorkflowExecutor:
    """Executes objectives by decomposing them into cell workflows."""

    def __init__(self, orchestrator: CellOrchestrator | None = None) -> None:
        self._orchestrator = orchestrator or CellOrchestrator()

    @property
    def orchestrator(self) -> CellOrchestrator:
        return self._orchestrator

    def execute_objective(
        self,
        objective: str,
        *,
        steps: list[dict[str, Any]] | None = None,
    ) -> str:
        """Decompose an objective into a workflow and execute it.

        If steps are provided, uses them directly. Otherwise creates
        a default single-step workflow.

        Returns the workflow run_id.
        """
        workflow_id = _gen_id("wf")

        if steps:
            wf_steps = [
                CellWorkflowStep(
                    step_id=s.get("step_id", _gen_id("step")),
                    cell_type=CellType(s.get("cell_type", "planning")),
                    objective=s.get("objective", objective),
                    depends_on=tuple(s.get("depends_on", ())),
                    metadata=s.get("metadata", {}),
                )
                for s in steps
            ]
        else:
            wf_steps = [
                CellWorkflowStep(
                    step_id=_gen_id("step"),
                    cell_type=CellType.PLANNING,
                    objective=objective,
                ),
            ]

        workflow = CellWorkflow(
            workflow_id=workflow_id,
            objective=objective,
            steps=wf_steps,
        )

        run = self._orchestrator.start_workflow(workflow)
        return run.run_id

    def get_status(self, run_id: str) -> WorkflowStatus | None:
        run = self._orchestrator.get_run(run_id)
        if run is None:
            return None
        return run.status

    def complete_step(
        self, run_id: str, step_id: str, result: dict[str, Any] | None = None
    ) -> bool:
        return self._orchestrator.complete_step(run_id, step_id, result)

    def clear(self) -> None:
        self._orchestrator.clear()
