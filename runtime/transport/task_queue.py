"""
Priority queue layer for the task system.

Assigns priority scores and queue names to tasks, provides sorted retrieval
helpers. Tasks remain in the unified TaskStore — queue_name is a filter
dimension, not a separate data structure.

Design rules (mirror substrate conventions):
- Additive only — never imported on the hot path.
- Deterministic — keyword heuristics, zero LLM cost.
- Bounded — fixed priority range (0-100), fixed queue name set.
- Best-effort — never raises into callers.
"""

from __future__ import annotations

import re
import sys
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from runtime.transport.operator_session import OperatorSession

from runtime.transport.task_system import (
    Task,
    TaskExecutionPolicy,
    TaskStatus,
    TaskStore,
)


# ─── Constants ───────────────────────────────────────────────────────────────


def _log(msg: str) -> None:
    print(f"[substrate.task_queue] {msg}", file=sys.stderr)


# ─── Priority Model ─────────────────────────────────────────────────────────


class TaskPriority(IntEnum):
    """Priority levels. Higher value = more urgent."""

    CRITICAL = 100
    HIGH = 75
    NORMAL = 50
    LOW = 25


# Urgency keywords → CRITICAL or HIGH
_URGENT_RE = re.compile(
    r"\b(urgent|asap|critical|blocked|emergency|immediately|now)\b",
    re.IGNORECASE,
)

# Queue name constants
QUEUE_OPERATOR_BLOCKED = "operator_blocked"
QUEUE_AUTONOMOUS_DAY = "autonomous_day"
QUEUE_AUTONOMOUS_OVERNIGHT = "autonomous_overnight"
QUEUE_APPROVAL_WAITING = "approval_waiting"


# ─── Priority Assignment ────────────────────────────────────────────────────


def infer_task_priority(
    task: Task,
    session: Optional["OperatorSession"] = None,
) -> int:
    """Assign a priority score to a task. Deterministic keyword matching.

    Rules:
    - Urgency keywords in text → CRITICAL (100)
    - NEEDS_OPERATOR tasks → HIGH (75) — operator bottleneck, surface quickly
    - AUTONOMOUS tasks → NORMAL (50)
    - Default → LOW (25)
    """
    text = f"{task.title} {task.description or ''}"

    if _URGENT_RE.search(text):
        return TaskPriority.CRITICAL

    if task.execution_policy == TaskExecutionPolicy.NEEDS_OPERATOR:
        return TaskPriority.HIGH

    if task.execution_policy == TaskExecutionPolicy.AUTONOMOUS:
        return TaskPriority.NORMAL

    return TaskPriority.LOW


# ─── Queue Assignment ────────────────────────────────────────────────────────


def assign_queue(
    task: Task,
    is_day_open: bool = False,
) -> str:
    """Assign a queue name based on task policy and session state.

    Rules:
    - NEEDS_OPERATOR or WAITING_ON_OPERATOR → operator_blocked
    - NEEDS_APPROVAL → approval_waiting
    - AUTONOMOUS + day open → autonomous_day
    - AUTONOMOUS + day closed → autonomous_overnight
    """
    if task.execution_policy == TaskExecutionPolicy.NEEDS_APPROVAL:
        return QUEUE_APPROVAL_WAITING
    if task.execution_policy == TaskExecutionPolicy.NEEDS_OPERATOR:
        return QUEUE_OPERATOR_BLOCKED
    if task.status == TaskStatus.WAITING_ON_OPERATOR:
        return QUEUE_OPERATOR_BLOCKED
    if task.execution_policy == TaskExecutionPolicy.AUTONOMOUS:
        return QUEUE_AUTONOMOUS_DAY if is_day_open else QUEUE_AUTONOMOUS_OVERNIGHT
    return QUEUE_AUTONOMOUS_DAY


def prioritize_and_queue(
    task: Task,
    session: Optional["OperatorSession"] = None,
    is_day_open: bool = False,
) -> Task:
    """Assign priority and queue to a task. Mutates and returns."""
    task.priority = infer_task_priority(task, session)
    task.queue_name = assign_queue(task, is_day_open)
    return task


# ─── Retrieval Helpers ───────────────────────────────────────────────────────


def _priority_sort(tasks: list[Task]) -> list[Task]:
    """Sort tasks by priority desc, then created_at asc (FIFO within tier)."""
    return sorted(tasks, key=lambda t: (-t.priority, t.created_at))


def get_ready_tasks(store: Optional[TaskStore] = None) -> list[Task]:
    """Return READY tasks sorted by priority desc, created_at asc."""
    s = store or TaskStore.default()
    return _priority_sort(s.by_status(TaskStatus.READY))


def get_overnight_tasks(store: Optional[TaskStore] = None) -> list[Task]:
    """Return OVERNIGHT_QUEUED tasks sorted by priority desc, created_at asc."""
    s = store or TaskStore.default()
    return _priority_sort(s.by_status(TaskStatus.OVERNIGHT_QUEUED))


def get_waiting_on_operator_tasks(store: Optional[TaskStore] = None) -> list[Task]:
    """Return WAITING_ON_OPERATOR tasks sorted by priority desc, created_at asc."""
    s = store or TaskStore.default()
    return _priority_sort(s.by_status(TaskStatus.WAITING_ON_OPERATOR))


def get_tasks_sorted_for_execution(store: Optional[TaskStore] = None) -> list[Task]:
    """Return all executable tasks (READY + OVERNIGHT_QUEUED), priority-sorted.

    This is the primary retrieval for the execution pipeline — gives the
    executor the next-best task to run regardless of queue name.
    """
    s = store or TaskStore.default()
    ready = s.by_status(TaskStatus.READY)
    overnight = s.by_status(TaskStatus.OVERNIGHT_QUEUED)
    return _priority_sort(ready + overnight)


# ─── Day Workflow Helpers ────────────────────────────────────────────────────


def get_enhanced_task_summary(store: Optional[TaskStore] = None) -> dict:
    """Extended task summary for open_day briefing.

    Returns the base get_task_summary() dict plus:
    - queued_autonomous: count of READY + OVERNIGHT_QUEUED autonomous tasks
    - top_priority_task_title: title of the highest-priority executable task
    """
    from runtime.transport.task_system import get_task_summary

    summary = get_task_summary()
    s = store or TaskStore.default()

    executable = get_tasks_sorted_for_execution(s)
    autonomous_queued = [
        t for t in executable if t.execution_policy == TaskExecutionPolicy.AUTONOMOUS
    ]

    summary["queued_autonomous"] = len(autonomous_queued)
    summary["top_priority_task_title"] = executable[0].title if executable else None

    return summary


def prepare_overnight_queue(store: Optional[TaskStore] = None) -> dict:
    """Move eligible READY autonomous tasks into OVERNIGHT_QUEUED.

    Called at close_day. Returns summary:
    {
        "moved_to_overnight": int,
        "preserved_operator_blocked": int,
        "overnight_task_ids": list[str],
    }
    """
    s = store or TaskStore.default()
    ready = s.by_status(TaskStatus.READY)

    moved: list[str] = []
    for task in ready:
        if task.execution_policy == TaskExecutionPolicy.AUTONOMOUS:
            task.status = TaskStatus.OVERNIGHT_QUEUED
            task.queue_name = QUEUE_AUTONOMOUS_OVERNIGHT
            s.put(task)
            moved.append(task.task_id)

    waiting = len(s.by_status(TaskStatus.WAITING_ON_OPERATOR))

    _log(f"overnight prep: {len(moved)} moved, {waiting} operator-blocked preserved")

    return {
        "moved_to_overnight": len(moved),
        "preserved_operator_blocked": waiting,
        "overnight_task_ids": moved,
    }


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "TaskPriority",
    "QUEUE_OPERATOR_BLOCKED",
    "QUEUE_AUTONOMOUS_DAY",
    "QUEUE_AUTONOMOUS_OVERNIGHT",
    "QUEUE_APPROVAL_WAITING",
    "infer_task_priority",
    "assign_queue",
    "prioritize_and_queue",
    "get_ready_tasks",
    "get_overnight_tasks",
    "get_waiting_on_operator_tasks",
    "get_tasks_sorted_for_execution",
    "get_enhanced_task_summary",
    "prepare_overnight_queue",
]
