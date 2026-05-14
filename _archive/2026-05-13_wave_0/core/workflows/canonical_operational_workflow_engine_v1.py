"""Canonical Operational Workflow Engine v1.

Executes operational workflows exclusively through the
canonical live substrate runtime spine. No direct adapter
execution. No bypassing the spine pipeline.

Pipeline per workflow:
  1. Governance check (workflow-level)
  2. Boundary initialization
  3. For each step:
     a. Boundary check
     b. Step governance check
     c. Spine traversal (or internal operation)
     d. Result collection
     e. Checkpoint (if flagged)
  4. Outcome aggregation
  5. Continuity persistence
  6. Workflow completion

UMH substrate subsystem. Phase 96.8BS.
"""

from __future__ import annotations

import time
from typing import Any

from core.workflows.operational_workflow_contracts_v1 import (
    OperationalWorkflow,
    SupervisedOperationalMode,
    WorkflowCheckpoint,
    WorkflowContext,
    WorkflowContinuation,
    WorkflowContinuationType,
    WorkflowDecision,
    WorkflowDecisionType,
    WorkflowOutcome,
    WorkflowPhase,
    WorkflowReceipt,
    WorkflowStep,
    WorkflowStepType,
    WorkflowType,
    _content_hash,
    _new_id,
    _now_iso,
)
from core.workflows.workflow_governance_bridge_v1 import WorkflowGovernanceBridge
from core.workflows.workflow_boundary_policies_v1 import WorkflowBoundaryEnforcer
from core.runtime.live_substrate_runtime_spine_v1 import LiveSubstrateRuntimeSpine
from core.runtime.live_runtime_contracts_v1 import RuntimeSignalSource


class CanonicalOperationalWorkflowEngine:
    """Executes operational workflows through the canonical spine.

    Every spine traversal step calls spine.process().
    No direct adapter execution. No governance bypass.
    All steps bounded and governed.
    """

    def __init__(
        self,
        spine: LiveSubstrateRuntimeSpine | None = None,
        governance: WorkflowGovernanceBridge | None = None,
        boundary_enforcer: WorkflowBoundaryEnforcer | None = None,
    ) -> None:
        self._spine = spine or LiveSubstrateRuntimeSpine()
        self._governance = governance or WorkflowGovernanceBridge()
        self._enforcer = boundary_enforcer or WorkflowBoundaryEnforcer()
        self._workflows_executed: int = 0
        self._workflows_completed: int = 0
        self._workflows_denied: int = 0
        self._workflows_failed: int = 0
        self._checkpoints: list[WorkflowCheckpoint] = []

    def execute_workflow(
        self,
        workflow: OperationalWorkflow,
        session_id: str = "",
    ) -> WorkflowOutcome:
        """Execute an operational workflow through the canonical spine."""
        start = time.monotonic()
        self._workflows_executed += 1

        workflow.finalize()

        context = WorkflowContext(
            workflow_id=workflow.workflow_id,
            correlation_id=workflow.correlation_id,
            session_id=session_id or workflow.session_id,
            operational_mode=workflow.operational_mode,
        )

        gov_decision = self._governance.evaluate_workflow_start(workflow, context)
        context.add_decision(gov_decision)

        if not gov_decision.approved:
            self._workflows_denied += 1
            return self._make_denied_outcome(workflow, context, start, gov_decision)

        context.current_phase = WorkflowPhase.ACTIVE

        step_summaries: list[dict[str, Any]] = []
        steps_completed = 0
        recent_step_types: list[str] = []
        error_message = ""

        for step in workflow.steps:
            elapsed = time.monotonic() - start

            boundary_decision = self._enforcer.check_all_boundaries(
                workflow.boundary,
                context,
                elapsed_seconds=elapsed,
                recent_step_types=recent_step_types,
            )
            context.add_decision(boundary_decision)

            if not boundary_decision.approved:
                error_message = f"Boundary violated at step {step.step_index}: {boundary_decision.denial_reason}"
                break

            step_gov = self._governance.evaluate_step(step, workflow, context)
            context.add_decision(step_gov)

            if not step_gov.approved:
                error_message = (
                    f"Step governance denied at step {step.step_index}: {step_gov.denial_reason}"
                )
                break

            step_result = self._execute_step(step, workflow, context)
            step_summaries.append(step_result)
            recent_step_types.append(step.step_type.value)

            if step_result.get("completed"):
                steps_completed += 1
                step.completed = True
                step.result_summary = step_result.get("summary", "")
            else:
                step.error_message = step_result.get("error", "Step failed")
                error_message = step.error_message
                break

            if step.checkpoint_after:
                checkpoint = self._create_checkpoint(workflow, context, step)
                self._checkpoints.append(checkpoint)
                context.current_phase = WorkflowPhase.CHECKPOINTED
                context.current_phase = WorkflowPhase.ACTIVE

        duration_ms = (time.monotonic() - start) * 1000

        if error_message:
            self._workflows_failed += 1
            status = WorkflowPhase.FAILED
        else:
            self._workflows_completed += 1
            status = WorkflowPhase.COMPLETED

        self._governance.complete_workflow(workflow.workflow_type.value)

        outcome = WorkflowOutcome(
            workflow_id=workflow.workflow_id,
            workflow_type=workflow.workflow_type,
            correlation_id=workflow.correlation_id,
            session_id=context.session_id,
            status=status,
            steps_completed=steps_completed,
            steps_total=workflow.total_steps,
            spine_traversals=context.spine_traversals,
            embodiment_transitions=context.embodiment_transitions,
            governance_decisions=len(context.decisions),
            checkpoints_created=len(
                [c for c in self._checkpoints if c.workflow_id == workflow.workflow_id]
            ),
            operational_mode=workflow.operational_mode,
            result_data=self._aggregate_results(step_summaries),
            step_summaries=step_summaries,
            error_message=error_message,
            duration_ms=duration_ms,
            lineage_receipts=context.lineage_receipts,
        )

        return outcome

    def _execute_step(
        self,
        step: WorkflowStep,
        workflow: OperationalWorkflow,
        context: WorkflowContext,
    ) -> dict[str, Any]:
        """Execute a single workflow step."""
        step_start = time.monotonic()

        if step.step_type == WorkflowStepType.SPINE_TRAVERSAL:
            result = self._dispatch_spine_traversal(step, context)
        elif step.step_type == WorkflowStepType.CONTEXT_RETRIEVAL:
            result = self._dispatch_context_retrieval(step, context)
        elif step.step_type == WorkflowStepType.CONTINUITY_CHECK:
            result = self._dispatch_continuity_check(step, context)
        elif step.step_type == WorkflowStepType.GOVERNANCE_CHECK:
            result = self._dispatch_governance_check(step, context)
        elif step.step_type == WorkflowStepType.CHECKPOINT:
            result = {"completed": True, "summary": "Checkpoint step"}
        elif step.step_type == WorkflowStepType.AGGREGATION:
            result = self._dispatch_aggregation(step, context)
        elif step.step_type == WorkflowStepType.REPORT_GENERATION:
            result = self._dispatch_report_generation(step, context)
        else:
            result = {"completed": False, "error": f"Unknown step type: {step.step_type.value}"}

        step.duration_ms = (time.monotonic() - step_start) * 1000

        receipt = WorkflowReceipt(
            workflow_id=workflow.workflow_id,
            step_id=step.step_id,
            correlation_id=context.correlation_id,
            phase=context.current_phase,
            action=f"execute_{step.step_type.value}",
            component="workflow_engine",
            input_hash=_content_hash({"command": step.command, "step_type": step.step_type.value}),
            output_hash=_content_hash(result),
            approved=result.get("completed", False),
        )
        context.add_lineage_receipt(receipt.receipt_id)

        return result

    def _dispatch_spine_traversal(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
    ) -> dict[str, Any]:
        """Dispatch a step through the canonical spine."""
        command = step.command
        if not command.startswith("!"):
            command = f"!{command}"

        outcome = self._spine.process(
            raw_input=command,
            source=RuntimeSignalSource.WORKFLOW,
            user_id="workflow_engine",
            channel_id="workflow",
        )

        context.record_spine_traversal(outcome.embodiment_path)

        if outcome.succeeded:
            context.accumulated_data[step.command] = outcome.result_data
            return {
                "completed": True,
                "summary": f"Spine traversal: {step.command} -> {outcome.status.value}",
                "outcome_id": outcome.outcome_id,
                "result_data": outcome.result_data,
            }

        return {
            "completed": False,
            "error": f"Spine traversal failed: {outcome.error_message}",
            "outcome_id": outcome.outcome_id,
        }

    def _dispatch_context_retrieval(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
    ) -> dict[str, Any]:
        """Retrieve context from accumulated workflow data."""
        return {
            "completed": True,
            "summary": f"Context retrieved: {len(context.accumulated_data)} data keys",
            "data_keys": list(context.accumulated_data.keys()),
            "spine_traversals": context.spine_traversals,
            "embodiment_transitions": context.embodiment_transitions,
        }

    def _dispatch_continuity_check(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
    ) -> dict[str, Any]:
        """Check continuity state via spine."""
        outcome = self._spine.process(
            raw_input="!runtime-open-loops",
            source=RuntimeSignalSource.WORKFLOW,
            user_id="workflow_engine",
            channel_id="workflow",
        )

        context.record_spine_traversal(outcome.embodiment_path)

        return {
            "completed": True,
            "summary": "Continuity check completed",
            "open_loops": outcome.result_data.get("open_loops", []) if outcome.succeeded else [],
        }

    def _dispatch_governance_check(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
    ) -> dict[str, Any]:
        """Check governance state via spine."""
        outcome = self._spine.process(
            raw_input="!runtime-governance",
            source=RuntimeSignalSource.WORKFLOW,
            user_id="workflow_engine",
            channel_id="workflow",
        )

        context.record_spine_traversal(outcome.embodiment_path)

        return {
            "completed": True,
            "summary": "Governance check completed",
            "governance_data": outcome.result_data if outcome.succeeded else {},
        }

    def _dispatch_aggregation(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
    ) -> dict[str, Any]:
        """Aggregate results from prior steps."""
        return {
            "completed": True,
            "summary": f"Aggregated {len(context.step_outcomes)} step outcomes",
            "aggregated_keys": list(context.accumulated_data.keys()),
            "total_spine_traversals": context.spine_traversals,
        }

    def _dispatch_report_generation(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
    ) -> dict[str, Any]:
        """Generate a report from accumulated workflow data."""
        report = {
            "workflow_id": context.workflow_id,
            "operational_mode": context.operational_mode.value,
            "spine_traversals": context.spine_traversals,
            "embodiment_transitions": context.embodiment_transitions,
            "data_collected": {k: type(v).__name__ for k, v in context.accumulated_data.items()},
            "decisions_made": len(context.decisions),
            "generated_at": _now_iso(),
        }

        context.accumulated_data["_report"] = report

        return {
            "completed": True,
            "summary": f"Report generated with {len(report)} sections",
            "report": report,
        }

    def _create_checkpoint(
        self,
        workflow: OperationalWorkflow,
        context: WorkflowContext,
        step: WorkflowStep,
    ) -> WorkflowCheckpoint:
        """Create a checkpoint at the current workflow state."""
        completed_ids = [s.step_id for s in workflow.steps if s.completed]
        pending_ids = [s.step_id for s in workflow.steps if not s.completed]

        return WorkflowCheckpoint(
            workflow_id=workflow.workflow_id,
            correlation_id=context.correlation_id,
            session_id=context.session_id,
            step_index=step.step_index,
            step_id=step.step_id,
            completed_steps=completed_ids,
            pending_steps=pending_ids,
            context_snapshot=context.to_dict(),
            accumulated_data=dict(context.accumulated_data),
            boundary_state=workflow.boundary.to_dict(),
        )

    def _make_denied_outcome(
        self,
        workflow: OperationalWorkflow,
        context: WorkflowContext,
        start: float,
        decision: WorkflowDecision,
    ) -> WorkflowOutcome:
        """Create a denied outcome."""
        return WorkflowOutcome(
            workflow_id=workflow.workflow_id,
            workflow_type=workflow.workflow_type,
            correlation_id=workflow.correlation_id,
            session_id=context.session_id,
            status=WorkflowPhase.DENIED,
            operational_mode=workflow.operational_mode,
            error_message=decision.denial_reason,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    def _aggregate_results(
        self,
        step_summaries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Aggregate step results into a single result dict."""
        aggregated: dict[str, Any] = {}
        for summary in step_summaries:
            if "result_data" in summary and isinstance(summary["result_data"], dict):
                aggregated.update(summary["result_data"])
        return aggregated

    def get_checkpoints(self, workflow_id: str = "") -> list[dict[str, Any]]:
        """Get checkpoints, optionally filtered by workflow ID."""
        checks = self._checkpoints
        if workflow_id:
            checks = [c for c in checks if c.workflow_id == workflow_id]
        return [c.to_dict() for c in checks]

    def get_stats(self) -> dict[str, Any]:
        return {
            "workflows_executed": self._workflows_executed,
            "workflows_completed": self._workflows_completed,
            "workflows_denied": self._workflows_denied,
            "workflows_failed": self._workflows_failed,
            "total_checkpoints": len(self._checkpoints),
            "governance": self._governance.get_stats(),
            "boundaries": self._enforcer.get_stats(),
        }
