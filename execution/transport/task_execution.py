"""
Real task execution pipeline — binds tasks to tmux-backed Claude sessions.

Replaces the v1 stub (immediate completion) with actual dispatch through
the existing claude_session_bridge infrastructure. Tasks are routed via
capability_routing, sent to the correct tmux session, and their output
is captured and analyzed for human-block signals.

Design rules (mirror substrate conventions):
- Additive only — never imported on the hot path.
- Best-effort — execution failures are captured, never raised.
- Deterministic state transitions — no ambiguous intermediate states.
- Bounded — configurable timeouts and retry limits.
- Restart-safe — all state persisted via TaskStore.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from execution.transport.operator_session import OperatorSession

from execution.transport.task_system import (
    Task,
    TaskExecutionPolicy,
    TaskStatus,
    TaskStore,
)


# ─── Constants ───────────────────────────────────────────────────────────────

_MAX_RETRIES = 2
_POLL_INTERVAL_S = 2.0
_MAX_POLLS = 60  # 2 min max wait for a single task

# Human-block detection phrases in execution output
_HUMAN_BLOCK_RE = re.compile(
    r"(need your input|need approval|choose between|which option"
    r"|confirm before|waiting for.*decision|requires.*human"
    r"|operator.*required|manual.*step|cannot proceed without"
    r"|please (choose|select|decide|confirm|approve))",
    re.IGNORECASE,
)


def _log(msg: str) -> None:
    print(f"[substrate.task_execution] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Target Resolution ──────────────────────────────────────────────────────


# Map ExecutionTarget enum values to (tmux_target, session_name) pairs.
# Uses the same session naming convention as discord_mode_routing.
_TARGET_MAP: dict[str, tuple[str, str]] = {
    "local_product": ("local", "dex_product_main"),
    "local_builder": ("local", "dex_builder_main"),
    "vps_product": ("vps", "dex_product_main"),
    "vps_builder": ("vps", "dex_builder_main"),
}


def _resolve_tmux_target(chosen_target: Optional[str]) -> tuple[str, str]:
    """Convert an ExecutionTarget value to (tmux_target, session_name).

    Falls back to VPS builder if target is unknown — safe default for
    autonomous dev tasks.
    """
    if chosen_target and chosen_target in _TARGET_MAP:
        return _TARGET_MAP[chosen_target]
    return ("vps", "dex_builder_main")


# ─── Human-Block Detection ──────────────────────────────────────────────────


def detect_human_block(text: str) -> Optional[str]:
    """Check execution output for signals that human input is needed.

    Returns the matched phrase if a block is detected, None otherwise.
    Deterministic regex matching — no LLM calls.
    """
    if not text:
        return None
    match = _HUMAN_BLOCK_RE.search(text)
    return match.group(0) if match else None


# ─── Single Task Execution ──────────────────────────────────────────────────


def execute_task(
    task: Task,
    session: Optional["OperatorSession"] = None,
    *,
    local_available: bool = False,
    dry_run: bool = False,
    use_pipeline: bool = True,
) -> Task:
    """Execute a single autonomous task, optionally through the pipeline engine.

    When use_pipeline=True (default), tasks are decomposed into multi-step
    pipelines and executed step-by-step. Pipeline state is mirrored back to
    the task. When use_pipeline=False, falls through to legacy single-shot
    execution for backward compatibility.

    State transitions:
    - READY/OVERNIGHT_QUEUED → IN_PROGRESS → COMPLETED (success)
    - READY/OVERNIGHT_QUEUED → IN_PROGRESS → WAITING_ON_OPERATOR (human block)
    - READY/OVERNIGHT_QUEUED → IN_PROGRESS → READY (transient failure, retryable)
    - READY/OVERNIGHT_QUEUED → IN_PROGRESS → WAITING_ON_OPERATOR (hard failure)

    Only processes AUTONOMOUS tasks. Non-autonomous tasks are returned unchanged.

    Args:
        task: The task to execute.
        session: Current operator session for routing context.
        local_available: Whether a local node is reachable.
        dry_run: If True, route and mark IN_PROGRESS but skip actual dispatch.
        use_pipeline: If True, decompose into pipeline and execute step-by-step.

    Returns:
        The updated task (also persisted in the store).
    """
    store = TaskStore.default()

    # Guard: only execute autonomous tasks
    if task.execution_policy != TaskExecutionPolicy.AUTONOMOUS:
        _log(f"skip {task.task_id}: not autonomous ({task.execution_policy.value})")
        return task

    # Guard: only execute from READY or OVERNIGHT_QUEUED
    if task.status not in (TaskStatus.READY, TaskStatus.OVERNIGHT_QUEUED):
        _log(f"skip {task.task_id}: wrong status ({task.status.value})")
        return task

    # ── Pipeline-based execution (v3) ───────────────────────────────────────
    if use_pipeline:
        try:
            return _execute_via_pipeline(
                task,
                session,
                local_available=local_available,
                dry_run=dry_run,
                advance_all=True,
            )
        except Exception as exc:  # noqa: BLE001
            _log(
                f"pipeline execution failed for {task.task_id}, "
                f"falling back to legacy: {exc}"
            )
            # Fall through to legacy execution

    # ── Legacy single-shot execution ────────────────────────────────────────
    return _execute_legacy(
        task,
        session,
        local_available=local_available,
        dry_run=dry_run,
    )


def _execute_via_pipeline(
    task: Task,
    session: Optional["OperatorSession"] = None,
    *,
    local_available: bool = False,
    dry_run: bool = False,
    advance_all: bool = False,
) -> Task:
    """Execute a task through the pipeline engine.

    Creates or loads the task's pipeline, executes it, and mirrors the
    pipeline state back to the task.
    """
    from execution.transport.task_pipeline import (
        PipelineStatus,
        PipelineStore,
    )
    from execution.transport.task_decomposition import decompose_task
    from execution.transport.pipeline_execution import execute_pipeline

    store = TaskStore.default()
    pipe_store = PipelineStore.default()

    # Load existing pipeline or decompose a new one
    pipeline = None
    if task.pipeline_id:
        pipeline = pipe_store.get(task.pipeline_id)

    if pipeline is None:
        pipeline = decompose_task(task)
        pipe_store.put(pipeline)
        task.pipeline_id = pipeline.pipeline_id
        task.agent_owner = pipeline.agent_owner.value

    # Execute the pipeline
    task.status = TaskStatus.IN_PROGRESS
    task.execution_started_at = task.execution_started_at or _utcnow()
    store.put(task)

    pipeline = execute_pipeline(
        pipeline,
        session,
        local_available=local_available,
        dry_run=dry_run,
        advance_all=advance_all,
    )

    # Mirror pipeline state back to task
    _sync_pipeline_to_task(task, pipeline)
    store.put(task)

    return task


def _sync_pipeline_to_task(task: Task, pipeline: "TaskPipeline") -> None:
    """Mirror pipeline status and routing metadata back to the task.

    Ensures task-level fields (chosen_target, required_capabilities,
    routing_reason, execution_result) stay populated for backward
    compatibility with code that reads tasks but not pipelines.
    """
    from execution.transport.task_pipeline import PipelineStatus

    status_map = {
        PipelineStatus.COMPLETED: TaskStatus.COMPLETED,
        PipelineStatus.WAITING_ON_OPERATOR: TaskStatus.WAITING_ON_OPERATOR,
        PipelineStatus.IN_PROGRESS: TaskStatus.IN_PROGRESS,
        PipelineStatus.FAILED: TaskStatus.WAITING_ON_OPERATOR,
        PipelineStatus.PAUSED: TaskStatus.IN_PROGRESS,
        PipelineStatus.READY: TaskStatus.READY,
        PipelineStatus.PENDING: TaskStatus.PENDING,
    }

    task.status = status_map.get(pipeline.status, TaskStatus.IN_PROGRESS)

    # ── Sync routing metadata from first step that has it ────────────────
    if not task.chosen_target:
        for step in pipeline.steps:
            if step.chosen_target:
                task.chosen_target = step.chosen_target
                task.routing_reason = step.routing_reason
                break

    # ── Sync required_capabilities from routing ──────────────────────────
    if not task.required_capabilities:
        try:
            from execution.transport.capability_routing import infer_task_capabilities

            caps = infer_task_capabilities(task)
            task.required_capabilities = [
                c.value for c in sorted(caps, key=lambda c: c.value)
            ]
        except Exception:  # noqa: BLE001
            pass

    # ── Sync execution results ───────────────────────────────────────────
    if pipeline.status == PipelineStatus.COMPLETED:
        task.execution_finished_at = _utcnow()
        task.execution_result = pipeline.summary or "pipeline completed"
        task.result = task.execution_result
    elif pipeline.status == PipelineStatus.WAITING_ON_OPERATOR:
        current = pipeline.current_step()
        if current and current.requires_input_prompt:
            task.requires_input_prompt = current.requires_input_prompt
    elif pipeline.status == PipelineStatus.FAILED:
        task.execution_error = pipeline.summary
        task.requires_input_prompt = f"Pipeline failed: {pipeline.summary}"


def _execute_legacy(
    task: Task,
    session: Optional["OperatorSession"] = None,
    *,
    local_available: bool = False,
    dry_run: bool = False,
) -> Task:
    """Legacy single-shot execution (pre-pipeline)."""
    store = TaskStore.default()

    # ── Route the task ──────────────────────────────────────────────────────
    from execution.transport.capability_routing import route_task

    route_task(task, session, local_available)

    # ── Transition to IN_PROGRESS ───────────────────────────────────────────
    task.status = TaskStatus.IN_PROGRESS
    task.execution_started_at = _utcnow()
    store.put(task)
    _log(f"executing {task.task_id} → {task.chosen_target}")

    if dry_run:
        task.status = TaskStatus.COMPLETED
        task.execution_result = "dry_run — no dispatch"
        task.execution_finished_at = _utcnow()
        task.result = task.execution_result  # keep legacy field in sync
        store.put(task)
        return task

    # ── Dispatch to tmux session ────────────────────────────────────────────
    tmux_target, session_name = _resolve_tmux_target(task.chosen_target)
    dispatch_text = _build_dispatch_text(task)

    try:
        from execution.transport.claude_session_bridge import ask_session

        result = ask_session(
            tmux_target,
            session_name,
            dispatch_text,
            ensure=True,
            poll_interval_s=_POLL_INTERVAL_S,
            max_polls=_MAX_POLLS,
        )
    except Exception as exc:
        result = {"ok": False, "reason": f"dispatch_exception: {exc}"}
        _log(f"dispatch exception for {task.task_id}: {exc}")

    # ── Process result ──────────────────────────────────────────────────────
    if result.get("ok"):
        reply_text = result.get("reply_text", "")
        task.execution_result = reply_text or "completed (no output)"

        # Check for human-block signals in the output
        block_signal = detect_human_block(reply_text)
        if block_signal:
            task.status = TaskStatus.WAITING_ON_OPERATOR
            task.requires_input_prompt = f"Execution paused: {block_signal}"
            _log(f"human block detected in {task.task_id}: {block_signal}")
        else:
            task.status = TaskStatus.COMPLETED

        task.execution_finished_at = _utcnow()
        task.result = task.execution_result  # keep legacy field in sync
    else:
        # Execution failed
        reason = result.get("reason", "unknown")
        task.execution_error = reason
        task.retry_count += 1

        if task.retry_count <= _MAX_RETRIES:
            # Transient failure — put back in READY for retry
            task.status = TaskStatus.READY
            _log(
                f"transient failure for {task.task_id} (retry {task.retry_count}): {reason}"
            )
        else:
            # Exhausted retries — surface to operator
            task.status = TaskStatus.WAITING_ON_OPERATOR
            task.requires_input_prompt = (
                f"Execution failed after {task.retry_count} attempts: {reason}"
            )
            task.execution_finished_at = _utcnow()
            _log(f"exhausted retries for {task.task_id}: {reason}")

    store.put(task)
    return task


def _build_dispatch_text(task: Task) -> str:
    """Build the text to send to the tmux session for execution."""
    parts = [task.title]
    if task.description:
        parts.append(task.description)
    return " — ".join(parts)


# ─── Overnight Executor ─────────────────────────────────────────────────────


def run_overnight_execution(
    session: Optional["OperatorSession"] = None,
    *,
    local_available: bool = False,
    dry_run: bool = False,
    max_tasks: int = 50,
) -> dict:
    """Process queued autonomous tasks in priority order via pipelines.

    Called when session.day_mode == OVERNIGHT. Tasks are executed through
    their pipelines with advance_all=True so each pipeline progresses as
    far as possible. Pipelines that block on operator input are paused.
    Existing pipelines are resumed from their saved step, not restarted.

    Args:
        session: Current operator session for routing context.
        local_available: Whether a local node is reachable.
        dry_run: If True, route tasks but skip actual dispatch.
        max_tasks: Maximum tasks to process in one batch.

    Returns:
        {
            "executed": int,
            "completed": int,
            "blocked": int,
            "failed": int,
            "skipped": int,
            "task_results": [{"task_id": str, "status": str, "target": str}, ...],
        }
    """
    from execution.transport.task_queue import get_tasks_sorted_for_execution

    tasks = get_tasks_sorted_for_execution()[:max_tasks]

    results: dict = {
        "executed": 0,
        "completed": 0,
        "blocked": 0,
        "failed": 0,
        "skipped": 0,
        "task_results": [],
    }

    for task in tasks:
        # Skip non-autonomous tasks that ended up in executable queue
        if task.execution_policy != TaskExecutionPolicy.AUTONOMOUS:
            results["skipped"] += 1
            continue

        results["executed"] += 1

        # For pipeline-enabled tasks, use advance_all to push through
        # all steps in one batch. Resume existing pipelines from saved state.
        if task.pipeline_id:
            try:
                executed = _execute_via_pipeline(
                    task,
                    session,
                    local_available=local_available,
                    dry_run=dry_run,
                    advance_all=True,
                )
            except Exception as exc:  # noqa: BLE001
                _log(f"pipeline overnight execution failed for {task.task_id}: {exc}")
                executed = execute_task(
                    task,
                    session,
                    local_available=local_available,
                    dry_run=dry_run,
                    use_pipeline=False,
                )
        else:
            # New task — decompose into pipeline and advance all steps
            try:
                executed = _execute_via_pipeline(
                    task,
                    session,
                    local_available=local_available,
                    dry_run=dry_run,
                    advance_all=True,
                )
            except Exception as exc:  # noqa: BLE001
                _log(f"pipeline decomposition failed for {task.task_id}: {exc}")
                executed = execute_task(
                    task,
                    session,
                    local_available=local_available,
                    dry_run=dry_run,
                    use_pipeline=False,
                )

        task_result = {
            "task_id": executed.task_id,
            "status": executed.status.value,
            "target": executed.chosen_target,
        }
        results["task_results"].append(task_result)

        if executed.status == TaskStatus.COMPLETED:
            results["completed"] += 1
        elif executed.status == TaskStatus.WAITING_ON_OPERATOR:
            results["blocked"] += 1
        elif executed.status in (TaskStatus.READY, TaskStatus.IN_PROGRESS):
            # Transient failure or paused pipeline
            results["failed"] += 1

    _log(
        f"overnight batch: {results['executed']} executed, "
        f"{results['completed']} completed, "
        f"{results['blocked']} blocked, "
        f"{results['failed']} failed"
    )

    return results


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "execute_task",
    "detect_human_block",
    "run_overnight_execution",
]
