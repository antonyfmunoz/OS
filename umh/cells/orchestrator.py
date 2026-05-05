"""Cell orchestrator — multi-cell workflow coordination.

Manages workflow lifecycle: starting workflows, advancing steps,
handling signals, and coordinating cell spawning/resuming.

The orchestrator does NOT execute anything. It coordinates cells
through the CellRuntime and routes results through signals.

Divergent execution, convergent authority:
- Multiple cells may work in parallel (DAG branches).
- All execution requests go through the bridge.
- Only the control plane decides and executes.

No imports from execution, adapters, tools, or shell.
"""

from __future__ import annotations

import threading
from typing import Any

from umh.cells.models import (
    CellContext,
    CellStatus,
    CellType,
    _gen_id,
)
from umh.cells.persistence import CheckpointStore, InMemoryCheckpointStore
from umh.cells.router import RoutingAction, RoutingDecision, SignalRouter
from umh.cells.runtime import (
    activate_cell,
    fail_cell,
    get_cell_status,
    hydrate_cell,
    resume_cell,
    spawn_cell,
    terminate_cell,
)
from umh.cells.workflow import (
    CellWorkflow,
    CellWorkflowStep,
    WorkflowRun,
    WorkflowStatus,
    WorkflowStepStatus,
    _WORKFLOW_TERMINAL,
    runnable_steps,
)
from umh.core.clock import iso_now as _iso_now


def _emit(signal_type: str, payload: dict[str, Any]) -> None:
    """Best-effort signal emission."""
    try:
        from umh.brains.signals import emit_signal

        emit_signal("cell_orchestrator", signal_type, payload)
    except Exception:
        pass


def _publish_event(event_type: str, payload: dict[str, Any]) -> None:
    """Best-effort event publishing."""
    try:
        from umh.events.stream import publish

        publish(event_type, payload=payload, actor_id="cell_orchestrator")
    except Exception:
        pass


class CellOrchestrator:
    """Coordinates multi-cell workflows through signal-driven advancement."""

    def __init__(
        self,
        store: CheckpointStore | None = None,
        router: SignalRouter | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._workflows: dict[str, CellWorkflow] = {}
        self._runs: dict[str, WorkflowRun] = {}
        self._store = store or InMemoryCheckpointStore()
        self._router = router or SignalRouter()

    @property
    def router(self) -> SignalRouter:
        return self._router

    # ─── Workflow lifecycle ────────────────────────────────────────

    def start_workflow(self, workflow: CellWorkflow) -> WorkflowRun:
        """Start a workflow, creating a run and advancing initial steps."""
        run = WorkflowRun(
            run_id=_gen_id("wfrun"),
            workflow_id=workflow.workflow_id,
            status=WorkflowStatus.RUNNING,
        )

        for step in workflow.steps:
            run.step_statuses[step.step_id] = WorkflowStepStatus.PENDING

        with self._lock:
            self._workflows[workflow.workflow_id] = workflow
            self._runs[run.run_id] = run

        self._store.save_workflow_run(run)

        _emit(
            "orchestration.started",
            {
                "run_id": run.run_id,
                "workflow_id": workflow.workflow_id,
                "objective": workflow.objective,
            },
        )
        _publish_event(
            "orchestration.started",
            {"run_id": run.run_id, "workflow_id": workflow.workflow_id},
        )

        self._advance_run(run.run_id)
        return run

    def get_run(self, run_id: str) -> WorkflowRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def list_runs(self, workflow_id: str | None = None) -> list[WorkflowRun]:
        with self._lock:
            runs = list(self._runs.values())
        if workflow_id:
            runs = [r for r in runs if r.workflow_id == workflow_id]
        return runs

    # ─── Step completion ───────────────────────────────────────────

    def complete_step(
        self,
        run_id: str,
        step_id: str,
        result: dict[str, Any] | None = None,
    ) -> bool:
        """Mark a step as completed and advance the workflow."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return False
            if run.is_terminal:
                return False
            if run.step_statuses.get(step_id) not in (
                WorkflowStepStatus.ACTIVE,
                WorkflowStepStatus.WAITING,
            ):
                return False

            run.step_statuses[step_id] = WorkflowStepStatus.COMPLETED
            run.updated_at = _iso_now()

            workflow = self._workflows.get(run.workflow_id)
            if workflow:
                step = workflow.step_by_id(step_id)
                if step and step.output_key and result:
                    run.outputs[step.output_key] = result

            cell_id = run.step_cell_ids.get(step_id)

        if cell_id:
            try:
                status = get_cell_status(cell_id)
                if status == CellStatus.WAITING:
                    resume_cell(cell_id, result)
                if status in (CellStatus.ACTIVE, CellStatus.WAITING):
                    terminate_cell(cell_id)
            except Exception:
                pass

        _emit(
            "cell.completed",
            {"run_id": run_id, "step_id": step_id, "cell_id": cell_id or ""},
        )

        self._store.save_workflow_run(run)
        self._advance_run(run_id)
        return True

    def fail_step(self, run_id: str, step_id: str, error: str = "") -> bool:
        """Mark a step as failed."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return False
            if run.is_terminal:
                return False

            run.step_statuses[step_id] = WorkflowStepStatus.FAILED
            run.errors[step_id] = error
            run.updated_at = _iso_now()

            workflow = self._workflows.get(run.workflow_id)
            step = workflow.step_by_id(step_id) if workflow else None
            is_required = step.required if step else True

            cell_id = run.step_cell_ids.get(step_id)

        if cell_id:
            try:
                status = get_cell_status(cell_id)
                if status and status not in (CellStatus.TERMINATED, CellStatus.FAILED):
                    fail_cell(cell_id, error)
            except Exception:
                pass

        if is_required:
            self._fail_workflow(run_id, f"Required step '{step_id}' failed: {error}")
        else:
            run.step_statuses[step_id] = WorkflowStepStatus.SKIPPED
            self._store.save_workflow_run(run)
            self._advance_run(run_id)

        return True

    # ─── Signal handling ───────────────────────────────────────────

    def handle_signal(self, signal_type: str, payload: dict[str, Any]) -> list[RoutingDecision]:
        """Handle an incoming signal through the router.

        Routes the signal and processes routing decisions. Returns
        the decisions taken for observability.
        """
        decisions = self._router.route_signal(signal_type, payload)

        for decision in decisions:
            self._process_decision(decision)

        return decisions

    def _process_decision(self, decision: RoutingDecision) -> None:
        """Process a single routing decision."""
        if decision.action == RoutingAction.COMPLETE_STEP:
            run_id = decision.signal_payload.get("run_id", "")
            step_id = decision.signal_payload.get("step_id", "")
            result = decision.signal_payload.get("result")
            if run_id and step_id:
                self.complete_step(run_id, step_id, result)

        elif decision.action == RoutingAction.FAIL_STEP:
            run_id = decision.signal_payload.get("run_id", "")
            step_id = decision.signal_payload.get("step_id", "")
            error = decision.signal_payload.get("error", "")
            if run_id and step_id:
                self.fail_step(run_id, step_id, error)

        elif decision.action == RoutingAction.RESUME_CELL:
            cell_id = decision.target_cell_id or decision.signal_payload.get("cell_id", "")
            result = decision.signal_payload.get("result")
            if cell_id:
                try:
                    resume_cell(cell_id, result)
                except Exception:
                    pass

        elif decision.action == RoutingAction.SPAWN_CELL:
            if decision.target_cell_type:
                try:
                    spawn_cell(decision.target_cell_type)
                except Exception:
                    pass

    # ─── Checkpoint / resume ───────────────────────────────────────

    def checkpoint_run(self, run_id: str) -> bool:
        """Persist the current run state."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return False

        self._store.save_workflow_run(run)
        _emit("orchestration.checkpointed", {"run_id": run_id})
        return True

    def resume_run(self, run_id: str) -> bool:
        """Resume a run from persisted state."""
        run = self._store.load_workflow_run(run_id)
        if run is None:
            return False
        if run.is_terminal:
            return False

        with self._lock:
            self._runs[run_id] = run

        _publish_event("orchestration.resumed", {"run_id": run_id})
        self._advance_run(run_id)
        return True

    # ─── Internal advancement ──────────────────────────────────────

    def _advance_run(self, run_id: str) -> None:
        """Advance a workflow run by starting all currently runnable steps."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None or run.is_terminal:
                return
            workflow = self._workflows.get(run.workflow_id)
            if workflow is None:
                return

        ready = runnable_steps(workflow, run)

        if not ready and not run.active_step_ids:
            all_done = all(
                st in (WorkflowStepStatus.COMPLETED, WorkflowStepStatus.SKIPPED)
                for st in run.step_statuses.values()
            )
            if all_done:
                self._complete_workflow(run_id)
                return

        for step in ready:
            self._start_step(run_id, workflow, step)

    def _start_step(self, run_id: str, workflow: CellWorkflow, step: CellWorkflowStep) -> None:
        """Start a single workflow step by spawning and hydrating a cell."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None or run.is_terminal:
                return

        identity = spawn_cell(step.cell_type, metadata={"run_id": run_id, "step_id": step.step_id})
        context = CellContext(
            cell_id=identity.cell_id,
            objective=step.objective,
            active_primitives=tuple(step.metadata.get("primitives", ())),
            metadata={
                "run_id": run_id,
                "step_id": step.step_id,
                "workflow_id": workflow.workflow_id,
            },
        )
        hydrate_cell(identity.cell_id, context)
        activate_cell(identity.cell_id)

        with self._lock:
            run = self._runs.get(run_id)
            if run:
                run.step_statuses[step.step_id] = WorkflowStepStatus.ACTIVE
                run.step_cell_ids[step.step_id] = identity.cell_id
                run.updated_at = _iso_now()

        self._store.save_workflow_run(run)

    def _complete_workflow(self, run_id: str) -> None:
        """Mark a workflow run as completed."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None or run.is_terminal:
                return
            run.status = WorkflowStatus.COMPLETED
            run.updated_at = _iso_now()

        self._store.save_workflow_run(run)
        _emit(
            "orchestration.completed",
            {"run_id": run_id, "workflow_id": run.workflow_id},
        )
        _publish_event(
            "orchestration.completed",
            {"run_id": run_id, "workflow_id": run.workflow_id},
        )

    def _fail_workflow(self, run_id: str, reason: str = "") -> None:
        """Mark a workflow run as failed."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None or run.is_terminal:
                return
            run.status = WorkflowStatus.FAILED
            run.updated_at = _iso_now()

        self._store.save_workflow_run(run)
        _emit(
            "orchestration.failed",
            {"run_id": run_id, "workflow_id": run.workflow_id, "reason": reason},
        )
        _publish_event(
            "orchestration.failed",
            {"run_id": run_id, "reason": reason},
        )

    def clear(self) -> None:
        """Reset all state — for testing only."""
        with self._lock:
            self._workflows.clear()
            self._runs.clear()
        self._router.clear()
        self._store.clear()
