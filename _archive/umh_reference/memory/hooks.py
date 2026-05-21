"""UMH Memory Hooks — explicit task completion recording.

These functions are called by the API layer or CLI to record task
outcomes as persistent memories. They do NOT hook into the task
system automatically — no event subscriptions, no triggers.
"""

from __future__ import annotations

from umh.memory.persistent_store import get_memory_store
from umh.orchestrator.task import Task, TaskStatus


def record_task_completion(task: Task) -> str | None:
    """Record a completed/failed task as a memory entry.

    Returns the memory ID if saved, None if task is not in terminal state.
    Only records tasks in COMPLETED or FAILED status.
    """
    if task.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED):
        return None

    operations = [step.operation for step in task.steps]

    if task.status == TaskStatus.COMPLETED:
        ops_str = ", ".join(operations)
        content = f"Task {task.id} completed. {len(task.steps)} steps. Operations: {ops_str}"
    else:
        # FAILED — find the failed step index
        failed_step = 0
        error = task.error or "unknown"
        for i, step in enumerate(task.steps):
            from umh.orchestrator.task import StepStatus

            if step.status == StepStatus.FAILED:
                failed_step = i
                break
        content = f"Task {task.id} failed at step {failed_step}. Error: {error}"

    metadata = {
        "task_id": task.id,
        "status": task.status.value,
        "step_count": len(task.steps),
        "created_at": task.created_at,
    }

    tags = [task.status.value, "auto-recorded"] + operations

    store = get_memory_store()
    memory = store.save_memory(
        type="task",
        content=content,
        metadata=metadata,
        tags=tags,
    )
    return memory.id


def record_task_summary(task_id: str, summary: dict) -> str | None:
    """Record a task summary as a memory entry.

    Takes the dict output from summarize_task().
    Returns the memory ID if saved, None on failure.
    """
    content = summary.get("final_summary", "")
    metadata = {
        "task_id": task_id,
        "status": summary.get("status", ""),
        "steps": summary.get("step_summaries", []),
    }
    tags = ["summary", task_id]

    store = get_memory_store()
    memory = store.save_memory(
        type="summary",
        content=content,
        metadata=metadata,
        tags=tags,
    )
    return memory.id
