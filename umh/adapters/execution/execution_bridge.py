"""
umh.adapters.execution.execution_bridge — Dispatches batch tasks
to execution and applies results back to batch/workstation lifecycle.

Connects ExecutionBatch tasks → ExecutionWorker adapters, and
maps ExecutionResults back to batch completion/failure mutations.

Public API:
    TaskResult             — per-task dispatch outcome
    DispatchResult         — full batch dispatch outcome
    dispatch_batch         — dispatch all tasks in a batch
    apply_execution_results — build lifecycle mutations from results
    build_batch_summary_artifact — build a summary artifact for a batch

Separation note:
    This module does NOT modify ExecutionWorker internals. It uses
    the existing ExecutionAdapter.execute() interface directly for
    synchronous dispatch. For event-driven dispatch via the scheduler,
    the caller should emit execution_requested events instead.
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from umh.substrate.artifact_contract import (
    artifact_to_mutations,
    build_runtime_artifact,
)
from umh.substrate.execution_batch import (
    BatchTask,
    ExecutionBatch,
    mark_batch_completed,
    mark_batch_failed,
)
from umh.substrate.execution_contract import (
    ExecutionConstraints,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTarget,
)
from umh.substrate.workstation_runtime import (
    WorkstationRun,
    complete_workstation_run,
    fail_workstation_run,
    load_workstation_run,
    list_active_workstation_runs,
)

_LOG_PREFIX = "[adapters.execution.execution_bridge]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_execution_id() -> str:
    return f"exec_{uuid.uuid4().hex[:16]}"


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class TaskResult:
    """Outcome of dispatching a single BatchTask.

    Fields:
        task:    the original BatchTask
        result:  ExecutionResult if dispatch succeeded, None if no adapter
        error:   error message if dispatch failed before reaching adapter
    """

    task: BatchTask
    result: ExecutionResult | None = None
    error: str = ""

    @property
    def succeeded(self) -> bool:
        return (
            self.result is not None and self.result.status == ExecutionStatus.SUCCEEDED
        )


@dataclass
class DispatchResult:
    """Outcome of dispatching all tasks in a batch.

    Fields:
        batch:        the batch that was dispatched
        task_results: per-task outcomes
        all_succeeded: True if every task succeeded
        any_failed:    True if any task failed
    """

    batch: ExecutionBatch
    task_results: list[TaskResult] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        return all(tr.succeeded for tr in self.task_results)

    @property
    def any_failed(self) -> bool:
        return any(not tr.succeeded for tr in self.task_results)

    @property
    def execution_ids(self) -> tuple[str, ...]:
        """Collect execution IDs from successful results."""
        return tuple(
            tr.result.execution_id for tr in self.task_results if tr.result is not None
        )


# ---------------------------------------------------------------------------
# Task → ExecutionRequest builder
# ---------------------------------------------------------------------------


def _build_request_from_task(
    task: BatchTask,
    batch: ExecutionBatch,
    node_id: str = "local",
    transport: str = "local_runtime",
) -> ExecutionRequest:
    """Build an ExecutionRequest from a BatchTask.

    Maps batch task fields to the execution contract. Uses the task's
    execution_class as the primitive_name for routing.
    """
    from umh.substrate.execution_contract import ExecutionClass

    # Map string execution_class to enum, defaulting to PURE
    try:
        exec_class = ExecutionClass(task.execution_class)
    except ValueError:
        exec_class = ExecutionClass.PURE

    return ExecutionRequest(
        execution_id=_new_execution_id(),
        correlation_id=task.correlation_id or batch.batch_id,
        causal_event_id=batch.batch_id,
        session_name=batch.session_id,
        run_id=batch.batch_id,
        primitive_name=task.execution_class,
        inputs=dict(task.payload),
        execution_class=exec_class,
        constraints=ExecutionConstraints(timeout_s=30),
        target=ExecutionTarget(node_id=node_id, transport=transport),
        issued_at=_utcnow(),
        issued_by="batch_drainer",
        idempotency_key=f"{batch.batch_id}:{task.task_id}",
    )


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def dispatch_batch(
    batch: ExecutionBatch,
    adapters: dict[str, Any],
    *,
    default_node_id: str = "local",
    default_transport: str = "local_runtime",
) -> DispatchResult:
    """Dispatch all tasks in a batch to execution adapters.

    Iterates tasks in order. For each task:
    1. Build an ExecutionRequest
    2. Find the appropriate adapter by node_id
    3. Call adapter.execute(request)
    4. Collect the result

    Args:
        batch:             the ExecutionBatch to dispatch
        adapters:          dict mapping node_id → ExecutionAdapter
        default_node_id:   fallback node when task doesn't specify one
        default_transport: fallback transport

    Returns:
        DispatchResult with per-task outcomes.
    """
    result = DispatchResult(batch=batch)

    for task in batch.tasks:
        node_id = default_node_id
        transport = default_transport

        request = _build_request_from_task(
            task,
            batch,
            node_id=node_id,
            transport=transport,
        )

        adapter = adapters.get(node_id)
        if adapter is None:
            _log(f"no adapter for node={node_id}, task={task.task_id} rejected")
            result.task_results.append(
                TaskResult(
                    task=task,
                    error=f"no adapter for node {node_id}",
                )
            )
            continue

        try:
            exec_result = adapter.execute(request)
            result.task_results.append(TaskResult(task=task, result=exec_result))
            _log(
                f"task {task.task_id} → {exec_result.status.value} "
                f"(exec_id={exec_result.execution_id})"
            )
        except Exception as exc:
            _log(f"task {task.task_id} adapter error: {exc}")
            result.task_results.append(
                TaskResult(task=task, error=str(exc)),
            )

    return result


# ---------------------------------------------------------------------------
# Apply results → lifecycle mutations
# ---------------------------------------------------------------------------


def apply_execution_results(
    dispatch_result: DispatchResult,
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build lifecycle mutations from dispatch results.

    1. Update linked workstation runs (if any active runs reference
       this batch)
    2. Mark batch completed or failed based on task outcomes
    3. Build a summary artifact if all tasks succeeded

    Args:
        dispatch_result: output of dispatch_batch()
        state:           current state snapshot

    Returns:
        list of SET/REMOVE mutations to apply.
    """
    mutations: list[dict[str, Any]] = []
    batch = dispatch_result.batch

    # --- 1. Update workstation runs linked to this batch ---
    active_run_ids = list_active_workstation_runs(state)
    for run_id in active_run_ids:
        run = load_workstation_run(state, run_id)
        if run is None:
            continue
        if run.batch_id != batch.batch_id:
            continue

        # This run is linked to the batch
        if dispatch_result.all_succeeded:
            updated, run_muts = complete_workstation_run(
                run,
                execution_ids=dispatch_result.execution_ids,
            )
            mutations.extend(run_muts)
            _log(f"completed workstation run {run_id}")
        else:
            failed_tasks = [
                tr.task.task_id
                for tr in dispatch_result.task_results
                if not tr.succeeded
            ]
            updated, run_muts = fail_workstation_run(
                run,
                reason=f"tasks failed: {', '.join(failed_tasks)}",
            )
            mutations.extend(run_muts)
            _log(f"failed workstation run {run_id}")

    # --- 2. Mark batch completed or failed ---
    if dispatch_result.all_succeeded:
        completed_batch, batch_muts = mark_batch_completed(batch)
        mutations.extend(batch_muts)
        _log(f"batch {batch.batch_id} completed")
    else:
        failed_tasks = [
            tr.task.task_id for tr in dispatch_result.task_results if not tr.succeeded
        ]
        failed_batch, batch_muts = mark_batch_failed(
            batch,
            reason=f"tasks failed: {', '.join(failed_tasks)}",
        )
        mutations.extend(batch_muts)
        _log(f"batch {batch.batch_id} failed")

    # --- 3. Build summary artifact on success ---
    if dispatch_result.all_succeeded:
        art_mutations = _build_batch_summary_mutations(dispatch_result)
        mutations.extend(art_mutations)

    return mutations


# ---------------------------------------------------------------------------
# Artifact builder
# ---------------------------------------------------------------------------


def _build_batch_summary_mutations(
    dispatch_result: DispatchResult,
) -> list[dict[str, Any]]:
    """Build mutations for a batch completion summary artifact."""
    batch = dispatch_result.batch
    lines = [
        f"batch {batch.batch_id} completed",
        f"session: {batch.session_id}",
        f"tasks: {len(batch.tasks)}",
    ]
    for tr in dispatch_result.task_results:
        status = "ok" if tr.succeeded else "fail"
        lines.append(f"  - {tr.task.task_id}: {status}")

    artifact = build_runtime_artifact(
        session_id=batch.session_id,
        artifact_type="batch_summary",
        title=f"batch {batch.batch_id} summary",
        body="\n".join(lines),
        source="execution_bridge",
        correlation_id=batch.batch_id,
    )
    return artifact_to_mutations(artifact)


def build_batch_summary_artifact(
    dispatch_result: DispatchResult,
) -> Any:
    """Build a RuntimeArtifact for a completed batch.

    Public convenience wrapper — returns the artifact object itself
    (not mutations). Use artifact_to_mutations() if you need mutations.
    """
    batch = dispatch_result.batch
    lines = [
        f"batch {batch.batch_id} completed",
        f"session: {batch.session_id}",
        f"tasks: {len(batch.tasks)}",
    ]
    for tr in dispatch_result.task_results:
        status = "ok" if tr.succeeded else "fail"
        lines.append(f"  - {tr.task.task_id}: {status}")

    return build_runtime_artifact(
        session_id=batch.session_id,
        artifact_type="batch_summary",
        title=f"batch {batch.batch_id} summary",
        body="\n".join(lines),
        source="execution_bridge",
        correlation_id=batch.batch_id,
    )
