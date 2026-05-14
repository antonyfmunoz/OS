"""Workflow Continuity Bridge v1.

Continuity layer for operational workflows:
  - Checkpoint persistence
  - Resume from checkpoint
  - Workflow lineage tracking
  - Session continuity across workflows
  - Open loop tracking at workflow level

Bridges workflow-level continuity to the runtime spine
continuity layer from Phase 96.8BR.

UMH substrate subsystem. Phase 96.8BS.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.workflows.operational_workflow_contracts_v1 import (
    WorkflowCheckpoint,
    WorkflowContinuation,
    WorkflowContinuationType,
    WorkflowContext,
    WorkflowOutcome,
    WorkflowPhase,
    _content_hash,
    _new_id,
    _now_iso,
)


class WorkflowContinuityBridge:
    """Continuity bridge for operational workflows.

    Persists workflow state, checkpoints, and continuations.
    Enables resume from last checkpoint on workflow restart.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/workflow_state",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._session_id: str = ""
        self._checkpoints: list[WorkflowCheckpoint] = []
        self._continuations: list[WorkflowContinuation] = []
        self._events_persisted: int = 0
        self._open_loops: list[dict[str, Any]] = []

    def start_session(self, session_id: str = "") -> str:
        """Start a workflow continuity session."""
        self._session_id = session_id or _new_id("wcsess")
        return self._session_id

    def persist_outcome(
        self,
        outcome: WorkflowOutcome,
    ) -> WorkflowContinuation:
        """Persist a workflow outcome and create continuation."""
        self._events_persisted += 1

        if outcome.succeeded:
            continuation = WorkflowContinuation(
                workflow_id=outcome.workflow_id,
                correlation_id=outcome.correlation_id,
                session_id=outcome.session_id,
                continuation_type=WorkflowContinuationType.COMPLETE,
            )
        elif outcome.denied:
            continuation = WorkflowContinuation(
                workflow_id=outcome.workflow_id,
                correlation_id=outcome.correlation_id,
                session_id=outcome.session_id,
                continuation_type=WorkflowContinuationType.DENIED,
            )
        elif outcome.checkpoints_created > 0:
            last_checkpoint = self._get_last_checkpoint(outcome.workflow_id)
            continuation = WorkflowContinuation(
                workflow_id=outcome.workflow_id,
                correlation_id=outcome.correlation_id,
                session_id=outcome.session_id,
                continuation_type=WorkflowContinuationType.CHECKPOINTED,
                checkpoint_id=last_checkpoint.checkpoint_id if last_checkpoint else "",
                resume_context={
                    "steps_completed": outcome.steps_completed,
                    "steps_total": outcome.steps_total,
                    "error": outcome.error_message,
                },
            )
        else:
            loop_id = _new_id("wloop")
            self._open_loops.append(
                {
                    "loop_id": loop_id,
                    "workflow_id": outcome.workflow_id,
                    "error": outcome.error_message,
                    "steps_completed": outcome.steps_completed,
                    "steps_total": outcome.steps_total,
                    "created_at": _now_iso(),
                }
            )
            continuation = WorkflowContinuation(
                workflow_id=outcome.workflow_id,
                correlation_id=outcome.correlation_id,
                session_id=outcome.session_id,
                continuation_type=WorkflowContinuationType.FAILED,
                open_loop_ids=[loop_id],
                resume_context={
                    "error": outcome.error_message,
                    "steps_completed": outcome.steps_completed,
                },
            )

        self._continuations.append(continuation)

        lineage_path = self._state_dir / "workflow_continuity_lineage.jsonl"
        with lineage_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(continuation.to_dict(), default=str) + "\n")

        return continuation

    def persist_checkpoint(self, checkpoint: WorkflowCheckpoint) -> None:
        """Persist a checkpoint to storage."""
        self._checkpoints.append(checkpoint)

        checkpoint_path = self._state_dir / f"checkpoint_{checkpoint.checkpoint_id}.json"
        checkpoint_path.write_text(
            json.dumps(checkpoint.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

    def get_latest_checkpoint(self, workflow_id: str) -> WorkflowCheckpoint | None:
        """Get the most recent checkpoint for a workflow."""
        return self._get_last_checkpoint(workflow_id)

    def get_open_loops(self) -> list[dict[str, Any]]:
        """Get all open loops across workflows."""
        return list(self._open_loops)

    def resolve_open_loop(self, loop_id: str) -> bool:
        """Resolve an open loop by ID."""
        for i, loop in enumerate(self._open_loops):
            if loop["loop_id"] == loop_id:
                loop["resolved_at"] = _now_iso()
                self._open_loops.pop(i)
                return True
        return False

    def create_resume_packet(self) -> dict[str, Any]:
        """Create a workflow-level resume packet."""
        return {
            "session_id": self._session_id,
            "open_loops": list(self._open_loops),
            "recent_continuations": [c.to_dict() for c in self._continuations[-5:]],
            "available_checkpoints": [
                {
                    "checkpoint_id": c.checkpoint_id,
                    "workflow_id": c.workflow_id,
                    "step_index": c.step_index,
                    "resumable": c.resumable,
                }
                for c in self._checkpoints
                if c.resumable
            ],
            "generated_at": _now_iso(),
        }

    def _get_last_checkpoint(self, workflow_id: str) -> WorkflowCheckpoint | None:
        """Get the most recent checkpoint for a workflow."""
        matching = [c for c in self._checkpoints if c.workflow_id == workflow_id]
        return matching[-1] if matching else None

    def get_stats(self) -> dict[str, Any]:
        return {
            "session_id": self._session_id,
            "events_persisted": self._events_persisted,
            "checkpoints": len(self._checkpoints),
            "continuations": len(self._continuations),
            "open_loops": len(self._open_loops),
        }
