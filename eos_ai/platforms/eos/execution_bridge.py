"""
ExecutionBridge — immediate task/pipeline execution from EAResponse.

Bridges the EOS platform layer into substrate task_execution and
pipeline_execution.  Called after EA creates work items so they begin
executing without waiting for the next scheduler tick.

Design rules:
- Best-effort — never raises into callers.  Errors are captured per-item.
- Lazy imports — all substrate modules imported inside functions.
- Additive — removing this file leaves the platform layer intact.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field


# ─── Logging ────────────────────────────────────────────────────────────────


def _log(msg: str) -> None:
    print(f"[platform.eos.execution_bridge] {msg}", file=sys.stderr)


# ─── Result Dataclass ───────────────────────────────────────────────────────


@dataclass
class ExecutionBridgeResult:
    """Outcome of an immediate execution batch."""

    executed_task_ids: list[str] = field(default_factory=list)
    executed_pipeline_ids: list[str] = field(default_factory=list)
    blocked_task_ids: list[str] = field(default_factory=list)
    execution_summaries: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict."""
        return {
            "executed_task_ids": list(self.executed_task_ids),
            "executed_pipeline_ids": list(self.executed_pipeline_ids),
            "blocked_task_ids": list(self.blocked_task_ids),
            "execution_summaries": dict(self.execution_summaries),
            "errors": dict(self.errors),
        }


# ─── Helpers ────────────────────────────────────────────────────────────────


def _is_local_available() -> bool:
    """Check station_presence for local node availability."""
    try:
        from eos_ai.substrate.station_presence import StationPresenceStore

        return StationPresenceStore.default().get().local_available
    except Exception as exc:  # noqa: BLE001
        _log(f"station_presence check failed: {exc}")
        return False


def _get_operator_session():
    """Return the current OperatorSession, or None."""
    try:
        from eos_ai.substrate.operator_session import OperatorSessionStore

        return OperatorSessionStore.default().get()
    except Exception as exc:  # noqa: BLE001
        _log(f"operator_session check failed: {exc}")
        return None


# ─── Single-Item Executors ──────────────────────────────────────────────────


def _execute_single_task(
    task_id: str,
    result: ExecutionBridgeResult,
    *,
    session,
    local_available: bool,
    dry_run: bool,
) -> None:
    """Attempt to execute one task.  All outcomes written to *result*."""
    try:
        from eos_ai.substrate.task_system import (
            TaskExecutionPolicy,
            TaskStatus,
            TaskStore,
        )

        store = TaskStore.default()
        task = store.get(task_id)

        if task is None:
            result.errors[task_id] = "task not found"
            _log(f"task {task_id}: not found")
            return

        if task.execution_policy != TaskExecutionPolicy.AUTONOMOUS:
            result.blocked_task_ids.append(task_id)
            result.execution_summaries[task_id] = (
                f"blocked — {task.execution_policy.value}: {task.title}"
            )
            _log(f"task {task_id}: blocked ({task.execution_policy.value})")
            return

        if task.status != TaskStatus.READY:
            result.errors[task_id] = f"wrong status: {task.status.value}"
            _log(f"task {task_id}: wrong status ({task.status.value})")
            return

        from eos_ai.substrate.task_execution import execute_task

        executed = execute_task(
            task,
            session,
            local_available=local_available,
            dry_run=dry_run,
        )
        result.executed_task_ids.append(task_id)
        result.execution_summaries[task_id] = (
            f"executed — {executed.status.value}: {executed.title}"
        )
        _log(f"task {task_id}: executed ({executed.status.value})")

    except Exception as exc:  # noqa: BLE001
        result.errors[task_id] = str(exc)
        _log(f"task {task_id}: exception — {exc}")


def _execute_single_pipeline(
    pipeline_id: str,
    result: ExecutionBridgeResult,
    *,
    session,
    local_available: bool,
    dry_run: bool,
) -> None:
    """Attempt to execute one pipeline.  All outcomes written to *result*."""
    try:
        from eos_ai.substrate.task_pipeline import PipelineStore
        from eos_ai.substrate.pipeline_execution import execute_pipeline

        store = PipelineStore.default()
        pipeline = store.get(pipeline_id)

        if pipeline is None:
            result.errors[pipeline_id] = "pipeline not found"
            _log(f"pipeline {pipeline_id}: not found")
            return

        if pipeline.is_terminal():
            result.errors[pipeline_id] = f"terminal state: {pipeline.status.value}"
            _log(f"pipeline {pipeline_id}: terminal ({pipeline.status.value})")
            return

        executed = execute_pipeline(
            pipeline,
            session,
            local_available=local_available,
            dry_run=dry_run,
            advance_all=True,
        )
        result.executed_pipeline_ids.append(pipeline_id)
        result.execution_summaries[pipeline_id] = (
            f"executed — {executed.status.value}: {executed.title}"
        )
        _log(f"pipeline {pipeline_id}: executed ({executed.status.value})")

    except Exception as exc:  # noqa: BLE001
        result.errors[pipeline_id] = str(exc)
        _log(f"pipeline {pipeline_id}: exception — {exc}")


# ─── Main Entry ─────────────────────────────────────────────────────────────


def execute_created_work_immediately(
    task_ids: list[str] | None = None,
    pipeline_ids: list[str] | None = None,
    *,
    dry_run: bool = False,
    prefer_local: bool = True,
) -> ExecutionBridgeResult:
    """Execute newly-created tasks and pipelines without waiting for the scheduler.

    Best-effort — individual failures are captured in the result, never raised.

    Args:
        task_ids: Task IDs to execute immediately.
        pipeline_ids: Pipeline IDs to execute immediately.
        dry_run: If True, route but skip actual tmux dispatch.
        prefer_local: If True and local is available, prefer local execution.

    Returns:
        ExecutionBridgeResult with per-item outcomes.
    """
    task_ids = task_ids or []
    pipeline_ids = pipeline_ids or []
    result = ExecutionBridgeResult()

    if not task_ids and not pipeline_ids:
        return result

    local_available = _is_local_available() if prefer_local else False
    session = _get_operator_session()

    _log(
        f"executing {len(task_ids)} tasks, {len(pipeline_ids)} pipelines "
        f"(dry_run={dry_run}, local_available={local_available})"
    )

    for task_id in task_ids:
        _execute_single_task(
            task_id,
            result,
            session=session,
            local_available=local_available,
            dry_run=dry_run,
        )

    for pipeline_id in pipeline_ids:
        _execute_single_pipeline(
            pipeline_id,
            result,
            session=session,
            local_available=local_available,
            dry_run=dry_run,
        )

    _log(
        f"done — {len(result.executed_task_ids)} tasks executed, "
        f"{len(result.executed_pipeline_ids)} pipelines executed, "
        f"{len(result.blocked_task_ids)} blocked, "
        f"{len(result.errors)} errors"
    )

    return result


# ─── Exports ────────────────────────────────────────────────────────────────

__all__ = [
    "ExecutionBridgeResult",
    "execute_created_work_immediately",
]
