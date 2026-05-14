"""Workflow Observability Pipeline v1.

Observability layer for operational workflows:
  - Workflow trace recording
  - Step execution events
  - Governance decision events
  - Boundary violation events
  - Checkpoint events
  - Continuation events
  - Workflow completion events
  - Workflow denial events
  - Workflow failure events

9 event types. JSONL persistence.

UMH substrate subsystem. Phase 96.8BS.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.workflows.operational_workflow_contracts_v1 import (
    OperationalWorkflow,
    WorkflowContext,
    WorkflowOutcome,
    _content_hash,
    _new_id,
    _now_iso,
)


class WorkflowObservabilityPipeline:
    """Observability pipeline for operational workflows.

    Records workflow-level traces, step events, governance
    decisions, boundary violations, and continuity events
    to JSONL files.
    """

    def __init__(
        self,
        obs_dir: str | Path = "data/runtime/workflow_observability",
    ) -> None:
        self._obs_dir = Path(obs_dir)
        self._obs_dir.mkdir(parents=True, exist_ok=True)
        self._traces: list[dict[str, Any]] = []
        self._step_events: list[dict[str, Any]] = []
        self._governance_events: list[dict[str, Any]] = []
        self._boundary_events: list[dict[str, Any]] = []
        self._checkpoint_events: list[dict[str, Any]] = []
        self._continuation_events: list[dict[str, Any]] = []
        self._completion_events: list[dict[str, Any]] = []
        self._denial_events: list[dict[str, Any]] = []
        self._failure_events: list[dict[str, Any]] = []

    def record_workflow_trace(
        self,
        workflow: OperationalWorkflow,
        outcome: WorkflowOutcome,
    ) -> None:
        """Record a complete workflow trace."""
        trace = {
            "trace_id": _new_id("wtrace"),
            "workflow_id": workflow.workflow_id,
            "workflow_type": workflow.workflow_type.value,
            "name": workflow.name,
            "operational_mode": workflow.operational_mode.value,
            "correlation_id": workflow.correlation_id,
            "session_id": workflow.session_id,
            "status": outcome.status.value,
            "steps_completed": outcome.steps_completed,
            "steps_total": outcome.steps_total,
            "spine_traversals": outcome.spine_traversals,
            "embodiment_transitions": outcome.embodiment_transitions,
            "governance_decisions": outcome.governance_decisions,
            "checkpoints_created": outcome.checkpoints_created,
            "duration_ms": outcome.duration_ms,
            "error_message": outcome.error_message,
            "timestamp": _now_iso(),
        }

        self._traces.append(trace)
        self._append_jsonl("workflow_traces.jsonl", trace)

    def record_step_event(
        self,
        workflow_id: str,
        step_id: str,
        step_type: str,
        command: str,
        completed: bool,
        summary: str = "",
        error: str = "",
        duration_ms: float = 0.0,
    ) -> None:
        """Record a step execution event."""
        event = {
            "event_id": _new_id("wstepev"),
            "event_type": "step_execution",
            "workflow_id": workflow_id,
            "step_id": step_id,
            "step_type": step_type,
            "command": command,
            "completed": completed,
            "summary": summary,
            "error": error,
            "duration_ms": duration_ms,
            "timestamp": _now_iso(),
        }

        self._step_events.append(event)
        self._append_jsonl("workflow_step_events.jsonl", event)

    def record_governance_event(
        self,
        workflow_id: str,
        decision_type: str,
        approved: bool,
        rules: list[str],
        denial_reason: str = "",
    ) -> None:
        """Record a governance decision event."""
        event = {
            "event_id": _new_id("wgovev"),
            "event_type": "governance_decision",
            "workflow_id": workflow_id,
            "decision_type": decision_type,
            "approved": approved,
            "rules": rules,
            "denial_reason": denial_reason,
            "timestamp": _now_iso(),
        }

        self._governance_events.append(event)
        self._append_jsonl("workflow_governance_events.jsonl", event)

    def record_boundary_event(
        self,
        workflow_id: str,
        violations: list[str],
        context_summary: dict[str, Any],
    ) -> None:
        """Record a boundary violation event."""
        event = {
            "event_id": _new_id("wbndev"),
            "event_type": "boundary_violation",
            "workflow_id": workflow_id,
            "violations": violations,
            "context_summary": context_summary,
            "timestamp": _now_iso(),
        }

        self._boundary_events.append(event)
        self._append_jsonl("workflow_boundary_events.jsonl", event)

    def record_checkpoint_event(
        self,
        workflow_id: str,
        checkpoint_id: str,
        step_index: int,
    ) -> None:
        """Record a checkpoint creation event."""
        event = {
            "event_id": _new_id("wchkev"),
            "event_type": "checkpoint_created",
            "workflow_id": workflow_id,
            "checkpoint_id": checkpoint_id,
            "step_index": step_index,
            "timestamp": _now_iso(),
        }

        self._checkpoint_events.append(event)
        self._append_jsonl("workflow_checkpoint_events.jsonl", event)

    def record_continuation_event(
        self,
        workflow_id: str,
        continuation_type: str,
        checkpoint_id: str = "",
        open_loop_ids: list[str] | None = None,
    ) -> None:
        """Record a continuation event."""
        event = {
            "event_id": _new_id("wcontev"),
            "event_type": "continuation",
            "workflow_id": workflow_id,
            "continuation_type": continuation_type,
            "checkpoint_id": checkpoint_id,
            "open_loop_ids": open_loop_ids or [],
            "timestamp": _now_iso(),
        }

        self._continuation_events.append(event)
        self._append_jsonl("workflow_continuation_events.jsonl", event)

    def record_completion_event(
        self,
        workflow_id: str,
        workflow_type: str,
        steps_completed: int,
        steps_total: int,
        duration_ms: float,
    ) -> None:
        """Record a workflow completion event."""
        event = {
            "event_id": _new_id("wcompev"),
            "event_type": "workflow_completed",
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "steps_completed": steps_completed,
            "steps_total": steps_total,
            "duration_ms": duration_ms,
            "timestamp": _now_iso(),
        }

        self._completion_events.append(event)
        self._append_jsonl("workflow_completion_events.jsonl", event)

    def record_denial_event(
        self,
        workflow_id: str,
        workflow_type: str,
        denial_reason: str,
    ) -> None:
        """Record a workflow denial event."""
        event = {
            "event_id": _new_id("wdenyev"),
            "event_type": "workflow_denied",
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "denial_reason": denial_reason,
            "timestamp": _now_iso(),
        }

        self._denial_events.append(event)
        self._append_jsonl("workflow_denial_events.jsonl", event)

    def record_failure_event(
        self,
        workflow_id: str,
        workflow_type: str,
        error_message: str,
        steps_completed: int,
        steps_total: int,
    ) -> None:
        """Record a workflow failure event."""
        event = {
            "event_id": _new_id("wfailev"),
            "event_type": "workflow_failed",
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "error_message": error_message,
            "steps_completed": steps_completed,
            "steps_total": steps_total,
            "timestamp": _now_iso(),
        }

        self._failure_events.append(event)
        self._append_jsonl("workflow_failure_events.jsonl", event)

    def get_recent_traces(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._traces[-limit:]

    def get_recent_step_events(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._step_events[-limit:]

    def get_recent_governance_events(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._governance_events[-limit:]

    def _append_jsonl(self, filename: str, data: dict[str, Any]) -> None:
        """Append a record to a JSONL file."""
        path = self._obs_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, default=str) + "\n")

    def get_stats(self) -> dict[str, Any]:
        return {
            "traces": len(self._traces),
            "step_events": len(self._step_events),
            "governance_events": len(self._governance_events),
            "boundary_events": len(self._boundary_events),
            "checkpoint_events": len(self._checkpoint_events),
            "continuation_events": len(self._continuation_events),
            "completion_events": len(self._completion_events),
            "denial_events": len(self._denial_events),
            "failure_events": len(self._failure_events),
        }
