"""UMH Task Summary — human-readable task state aggregation.

Pure formatting module. Converts task state, results, and timeline
into concise operator-readable summaries. No execution, no LLM calls.
"""

from __future__ import annotations

from umh.orchestrator.task import Task, TaskStatus, StepStatus, get_task


def summarize_task(task: Task, timeline: list | None = None, include_steps: bool = True) -> dict:
    """Build an operator-readable summary of a task."""

    completed_steps = sum(1 for s in task.steps if s.status == StepStatus.COMPLETED)
    failed_steps = sum(1 for s in task.steps if s.status == StepStatus.FAILED)
    waiting_steps = sum(1 for s in task.steps if s.status == StepStatus.WAITING_APPROVAL)

    objective = task.context.get("objective", task.context.get("plan_id", ""))
    if not objective:
        # Derive from first step operation
        objective = task.steps[0].operation if task.steps else "unknown"

    # Build step summaries
    step_summaries = []
    if include_steps:
        for i, step in enumerate(task.steps):
            s: dict = {
                "step": i,
                "operation": step.operation,
                "status": step.status.value,
            }
            if step.result:
                outputs = step.result.get("outputs", {})
                if outputs.get("response"):
                    s["output"] = str(outputs["response"])[:200]
                elif outputs.get("stdout"):
                    s["output"] = str(outputs["stdout"])[:200]
                elif outputs.get("result"):
                    s["output"] = str(outputs["result"])[:200]
            if step.status == StepStatus.FAILED and step.result:
                s["error"] = step.result.get("error", "")
            step_summaries.append(s)

    # Build errors list
    errors: list[str] = []
    if task.error:
        errors.append(task.error)
    for step in task.steps:
        if step.status == StepStatus.FAILED and step.result and step.result.get("error"):
            errors.append(
                f"Step {task.steps.index(step)} ({step.operation}): {step.result['error']}"
            )

    # Build final summary
    final_summary = _build_final_summary(task, completed_steps, failed_steps)

    # Build next action
    next_action = _build_next_action(task)

    return {
        "task_id": task.id,
        "status": task.status.value,
        "objective": objective,
        "current_step": task.current_step_index,
        "total_steps": len(task.steps),
        "completed_steps": completed_steps,
        "failed_steps": failed_steps,
        "waiting_approval": waiting_steps > 0,
        "approval_id": task.paused_approval_id if task.status == TaskStatus.PAUSED else "",
        "final_summary": final_summary,
        "step_summaries": step_summaries,
        "errors": errors,
        "next_action": next_action,
    }


def _build_final_summary(task: Task, completed: int, failed: int) -> str:
    total = len(task.steps)
    if task.status == TaskStatus.COMPLETED:
        return f"All {total} steps completed successfully."
    if task.status == TaskStatus.FAILED:
        return (
            f"Task failed at step {task.current_step_index}. {completed}/{total} steps completed."
        )
    if task.status == TaskStatus.PAUSED:
        return (
            f"Task paused at step {task.paused_step_index}: "
            f"{task.paused_reason or 'awaiting approval'}."
        )
    if task.status == TaskStatus.CANCELLED:
        return f"Task cancelled. {completed}/{total} steps were completed."
    if task.status == TaskStatus.PENDING:
        return "Task is queued for execution."
    if task.status == TaskStatus.RUNNING:
        return f"Task is running. {completed}/{total} steps completed."
    return f"Task status: {task.status.value}"


def _build_next_action(task: Task) -> str:
    if task.status == TaskStatus.PAUSED:
        aid = task.paused_approval_id
        return f"Approve or deny: POST /approvals/{aid}/approve"
    if task.status == TaskStatus.FAILED:
        return f"Retry: POST /tasks/{task.id}/retry"
    if task.status == TaskStatus.PENDING:
        return "Waiting for worker pickup."
    if task.status == TaskStatus.RUNNING:
        return f"Monitor: GET /tasks/{task.id}/timeline"
    if task.status == TaskStatus.CANCELLED:
        return "No action needed."
    if task.status == TaskStatus.COMPLETED:
        return "No action needed."
    return ""


def summarize_task_by_id(task_id: str, include_steps: bool = True) -> dict | None:
    """Convenience: look up task and summarize it."""
    task = get_task(task_id)
    if task is None:
        return None
    return summarize_task(task, include_steps=include_steps)
