"""UMH Task Timeline — read-only query module for task event history.

Builds a chronological timeline of all events associated with a task,
combining real events from the event stream with synthesized entries
from task state. Pure query — no mutation, no execution.

Usage:
    from umh.orchestrator.timeline import build_task_timeline

    entries = build_task_timeline("task_abc123")
    for entry in entries:
        print(f"{entry.timestamp} | {entry.summary}")
"""

from __future__ import annotations

from dataclasses import dataclass

from umh.events.stream import Event, get_event_stream
from umh.orchestrator.task import TaskStatus, get_task


@dataclass
class TimelineEntry:
    """Single entry in a task's chronological timeline."""

    timestamp: str
    event_type: str
    summary: str
    details: dict

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "summary": self.summary,
            "details": self.details,
        }


def _summarize_event(event: Event) -> str:
    """Map event type to a human-readable one-liner."""
    payload = event.payload
    t = event.type

    if t == "task.enqueued":
        return "Task enqueued for background execution"
    if t == "task.started":
        return "Task execution started"
    if t == "task.step.started":
        idx = payload.get("step_index", "?")
        op = payload.get("operation", "")
        return f"Step {idx} started: {op}"
    if t == "task.step.completed":
        idx = payload.get("step_index", "?")
        status = payload.get("status", "completed")
        return f"Step {idx} {status}"
    if t == "task.paused":
        reason = payload.get("reason", "awaiting approval")
        return f"Task paused: {reason}"
    if t == "task.resumed":
        return "Task resumed after approval"
    if t == "task.completed":
        status = payload.get("status", "completed")
        return f"Task {status}"
    if t == "task.cancelled":
        return "Task cancelled by operator"
    if t == "task.retried":
        new_id = payload.get("new_task_id", "")
        return f"Task retry requested → {new_id}"

    return t


def build_task_timeline(task_id: str) -> list[TimelineEntry]:
    """Build a chronological timeline for a given task.

    Combines events from the event stream with synthesized entries
    from task state. Returns entries sorted by timestamp, deduplicated.

    Args:
        task_id: The task ID to build timeline for.

    Returns:
        Ordered list of TimelineEntry, ascending by timestamp.
        Empty list if task not found.
    """
    task = get_task(task_id)
    if task is None:
        return []

    # Collect real events from the stream
    all_events = get_event_stream().list_events(limit=10000)
    task_events = [e for e in all_events if e.payload.get("task_id") == task_id]

    entries: list[TimelineEntry] = []

    for event in task_events:
        entries.append(
            TimelineEntry(
                timestamp=event.timestamp,
                event_type=event.type,
                summary=_summarize_event(event),
                details=event.payload,
            )
        )

    # Synthesize entries from task state if events are missing
    existing_types = {e.event_type for e in entries}

    # Always include task.created if not already present
    if "task.created" not in existing_types:
        entries.append(
            TimelineEntry(
                timestamp=task.created_at,
                event_type="task.created",
                summary="Task created",
                details={
                    "task_id": task.id,
                    "step_count": len(task.steps),
                    "issued_by": task.issued_by,
                },
            )
        )

    # If task is paused and no pause event present, synthesize
    if task.status == TaskStatus.PAUSED and "task.paused" not in existing_types:
        entries.append(
            TimelineEntry(
                timestamp=task.updated_at,
                event_type="task.paused",
                summary=f"Task paused: {task.paused_reason or 'awaiting approval'}",
                details={
                    "task_id": task.id,
                    "paused_step_index": task.paused_step_index,
                    "approval_id": task.paused_approval_id,
                    "reason": task.paused_reason,
                },
            )
        )

    # If task is completed/failed and no completion event present, synthesize
    if (
        task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
        and "task.completed" not in existing_types
    ):
        entries.append(
            TimelineEntry(
                timestamp=task.updated_at,
                event_type="task.completed",
                summary=f"Task {task.status.value}",
                details={
                    "task_id": task.id,
                    "status": task.status.value,
                    "error": task.error,
                },
            )
        )

    # If task is cancelled and no cancellation event present, synthesize
    if task.status == TaskStatus.CANCELLED and "task.cancelled" not in existing_types:
        entries.append(
            TimelineEntry(
                timestamp=task.updated_at,
                event_type="task.cancelled",
                summary="Task cancelled by operator",
                details={"task_id": task.id},
            )
        )

    # Sort by timestamp ascending
    entries.sort(key=lambda e: e.timestamp)

    # Deduplicate: same event_type + same timestamp = keep first
    seen: set[tuple[str, str]] = set()
    deduped: list[TimelineEntry] = []
    for entry in entries:
        key = (entry.event_type, entry.timestamp)
        if key not in seen:
            seen.add(key)
            deduped.append(entry)

    return deduped
