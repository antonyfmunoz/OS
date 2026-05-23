"""
Task autonomy and overnight execution system (v1).

Classifies tasks into execution policies (autonomous / needs_operator /
needs_approval), tracks their lifecycle, and dispatches based on the
current OperatorSession state.  Autonomous tasks execute immediately when
the day is open and queue for overnight processing when it is closed.
Operator-dependent tasks surface in the next open_day briefing.

Design rules (mirror substrate conventions):
- Additive only — never imported on the hot path.
- Best-effort persistence — flush failures log, never raise.
- Deterministic classification — simple keyword heuristics, zero LLM cost.
- Thread-safe singleton store backed by substrate.storage.
- Bounded — configurable max tasks, oldest completed tasks pruned first.
"""

from __future__ import annotations

import re
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

# ─── Constants ────────────────────────────────────────────────────────────────

_STORAGE_KEY = "task_system"
_MAX_TASKS = 500  # prune completed beyond this


def _log(msg: str) -> None:
    print(f"[substrate.task_system] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"task_{uuid.uuid4().hex[:12]}"


# ─── Enums ───────────────────────────────────────────────────────────────────


class TaskExecutionPolicy(str, Enum):
    """How the system should handle this task."""

    AUTONOMOUS = "autonomous"
    NEEDS_OPERATOR = "needs_operator"
    NEEDS_APPROVAL = "needs_approval"


class TaskStatus(str, Enum):
    """Lifecycle state of a task."""

    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    WAITING_ON_OPERATOR = "waiting_on_operator"
    OVERNIGHT_QUEUED = "overnight_queued"
    COMPLETED = "completed"


# ─── Classification ──────────────────────────────────────────────────────────

# Patterns that indicate operator decision-making is required
_NEEDS_OPERATOR_RE = re.compile(
    r"\b(decide|choose|approve|which|should\s+i|pick|select\s+between)\b",
    re.IGNORECASE,
)

# Patterns that indicate human review/confirmation is required
_NEEDS_APPROVAL_RE = re.compile(
    r"\b(review|confirm|sign\s*off|validate|check\s+with)\b",
    re.IGNORECASE,
)


def classify_task(text: str) -> TaskExecutionPolicy:
    """Classify a task using deterministic keyword heuristics.

    Priority order: needs_operator > needs_approval > autonomous.
    No LLM calls — pure regex matching.
    """
    if _NEEDS_OPERATOR_RE.search(text):
        return TaskExecutionPolicy.NEEDS_OPERATOR
    if _NEEDS_APPROVAL_RE.search(text):
        return TaskExecutionPolicy.NEEDS_APPROVAL
    return TaskExecutionPolicy.AUTONOMOUS


# ─── Task Dataclass ──────────────────────────────────────────────────────────


@dataclass
class Task:
    """A unit of work tracked by the task system."""

    task_id: str
    title: str
    description: Optional[str]

    execution_policy: TaskExecutionPolicy
    status: TaskStatus

    created_at: str
    updated_at: str

    # Linkage to the operator session that created this task
    day_session_id: Optional[str] = None

    # Execution output (legacy — prefer execution_result for v2+)
    result: Optional[str] = None

    # Prompt to show the operator when this task is blocked
    requires_input_prompt: Optional[str] = None

    # ── Capability routing (v2) ─────────────────────────────────────────────
    required_capabilities: list[str] = field(default_factory=list)
    chosen_target: Optional[str] = None
    routing_reason: Optional[str] = None

    # ── Priority + queue (v2) ───────────────────────────────────────────────
    priority: int = 50  # 0-100; higher = more urgent
    queue_name: Optional[str] = None

    # ── Execution tracking (v2) ─────────────────────────────────────────────
    execution_started_at: Optional[str] = None
    execution_finished_at: Optional[str] = None
    execution_result: Optional[str] = None
    execution_error: Optional[str] = None
    retry_count: int = 0

    # ── Pipeline linkage (v3) ───────────────────────────────────────────────
    pipeline_id: Optional[str] = None
    agent_owner: Optional[str] = None

    # — factory ──────────────────────────────────────────────────────────────

    @classmethod
    def new(
        cls,
        title: str,
        *,
        description: Optional[str] = None,
        execution_policy: TaskExecutionPolicy = TaskExecutionPolicy.AUTONOMOUS,
        status: TaskStatus = TaskStatus.PENDING,
        day_session_id: Optional[str] = None,
        requires_input_prompt: Optional[str] = None,
    ) -> "Task":
        """Create a new Task with generated ID and current timestamps."""
        now = _utcnow()
        return cls(
            task_id=_new_id(),
            title=title,
            description=description,
            execution_policy=execution_policy,
            status=status,
            created_at=now,
            updated_at=now,
            day_session_id=day_session_id,
            requires_input_prompt=requires_input_prompt,
        )

    # — serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Return a JSON-safe dict. Enums serialized as their .value."""
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "execution_policy": self.execution_policy.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "day_session_id": self.day_session_id,
            "result": self.result,
            "requires_input_prompt": self.requires_input_prompt,
            # v2 fields
            "required_capabilities": list(self.required_capabilities),
            "chosen_target": self.chosen_target,
            "routing_reason": self.routing_reason,
            "priority": self.priority,
            "queue_name": self.queue_name,
            "execution_started_at": self.execution_started_at,
            "execution_finished_at": self.execution_finished_at,
            "execution_result": self.execution_result,
            "execution_error": self.execution_error,
            "retry_count": self.retry_count,
            # v3 fields
            "pipeline_id": self.pipeline_id,
            "agent_owner": self.agent_owner,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        """Deserialize from a dict, reconstructing enums with safe defaults."""
        try:
            policy = TaskExecutionPolicy(d.get("execution_policy", "autonomous"))
        except ValueError:
            policy = TaskExecutionPolicy.AUTONOMOUS

        try:
            status = TaskStatus(d.get("status", "pending"))
        except ValueError:
            status = TaskStatus.PENDING

        raw_caps = d.get("required_capabilities")
        caps: list[str] = list(raw_caps) if isinstance(raw_caps, list) else []

        return cls(
            task_id=str(d.get("task_id") or _new_id()),
            title=str(d.get("title", "")),
            description=d.get("description"),
            execution_policy=policy,
            status=status,
            created_at=str(d.get("created_at") or _utcnow()),
            updated_at=str(d.get("updated_at") or _utcnow()),
            day_session_id=d.get("day_session_id"),
            result=d.get("result"),
            requires_input_prompt=d.get("requires_input_prompt"),
            # v2 fields — all have safe defaults for backward compat
            required_capabilities=caps,
            chosen_target=d.get("chosen_target"),
            routing_reason=d.get("routing_reason"),
            priority=int(d.get("priority", 50)),
            queue_name=d.get("queue_name"),
            execution_started_at=d.get("execution_started_at"),
            execution_finished_at=d.get("execution_finished_at"),
            execution_result=d.get("execution_result"),
            execution_error=d.get("execution_error"),
            retry_count=int(d.get("retry_count", 0)),
            # v3 fields — safe defaults for backward compat
            pipeline_id=d.get("pipeline_id"),
            agent_owner=d.get("agent_owner"),
        )


# ─── Task Store ──────────────────────────────────────────────────────────────


class TaskStore:
    """Durable, thread-safe, singleton store for Task records.

    Dual-layer: in-memory dict + substrate.storage (Neon-backed, JSON fallback).
    Best-effort persistence — flush failures log and the in-memory state
    remains correct.

    Keyed by task_id. Bounded — prunes oldest completed tasks when count
    exceeds _MAX_TASKS.
    """

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._tasks: dict[str, Task] = {}
        self._loaded = False
        if autoload:
            self._load()

    # — persistence ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from substrate.execution.bridge.storage import get_storage

                raw = get_storage().get(_STORAGE_KEY, default=None)
            except Exception as e:  # noqa: BLE001
                _log(f"load failed ({e}); starting empty")
                raw = None
            if isinstance(raw, dict):
                for key, val in raw.items():
                    if isinstance(val, dict):
                        try:
                            self._tasks[key] = Task.from_dict(val)
                        except Exception as e:  # noqa: BLE001
                            _log(f"skip bad task {key}: {e}")
            self._loaded = True

    def _flush(self) -> None:
        try:
            from substrate.execution.bridge.storage import get_storage

            payload = {tid: t.to_dict() for tid, t in self._tasks.items()}
            get_storage().put(_STORAGE_KEY, payload)
        except Exception as e:  # noqa: BLE001
            _log(f"flush failed: {e}")

    def _prune_if_needed(self) -> None:
        """Remove oldest completed tasks if store exceeds _MAX_TASKS."""
        if len(self._tasks) <= _MAX_TASKS:
            return
        completed = [
            t for t in self._tasks.values() if t.status == TaskStatus.COMPLETED
        ]
        completed.sort(key=lambda t: t.updated_at)
        to_remove = len(self._tasks) - _MAX_TASKS
        for task in completed[:to_remove]:
            del self._tasks[task.task_id]

    # — public api ───────────────────────────────────────────────────────────

    def get(self, task_id: str) -> Optional[Task]:
        """Return a task by ID, or None."""
        with self._lock:
            return self._tasks.get(task_id)

    def put(self, task: Task) -> None:
        """Insert or update a task. Flushes to storage."""
        with self._lock:
            task.updated_at = _utcnow()
            self._tasks[task.task_id] = task
            self._prune_if_needed()
            self._flush()

    def all(self) -> list[Task]:
        """Return all tasks, ordered by created_at ascending."""
        with self._lock:
            return sorted(self._tasks.values(), key=lambda t: t.created_at)

    def by_status(self, status: TaskStatus) -> list[Task]:
        """Return tasks with the given status."""
        with self._lock:
            return [t for t in self._tasks.values() if t.status == status]

    def by_policy(self, policy: TaskExecutionPolicy) -> list[Task]:
        """Return tasks with the given execution policy."""
        with self._lock:
            return [t for t in self._tasks.values() if t.execution_policy == policy]

    def count_by_status(self) -> dict[str, int]:
        """Return a {status_value: count} summary dict."""
        with self._lock:
            counts: dict[str, int] = {}
            for task in self._tasks.values():
                counts[task.status.value] = counts.get(task.status.value, 0) + 1
            return counts

    # — singleton ────────────────────────────────────────────────────────────

    _default: Optional["TaskStore"] = None
    _default_lock = threading.Lock()

    @classmethod
    def default(cls) -> "TaskStore":
        """Return the process-level singleton, creating it on first call."""
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        """Tear down the singleton so the next call to default() creates a fresh instance."""
        with cls._default_lock:
            cls._default = None


# ─── Task Creation ───────────────────────────────────────────────────────────


def create_task(
    text: str,
    *,
    session_id: Optional[str] = None,
    description: Optional[str] = None,
) -> Task:
    """Create a task from text, classify it, set initial status, and persist.

    Args:
        text: The task title / natural language description used for classification.
        session_id: The day_session_id to link this task to (optional).
        description: Optional longer description separate from the title.

    Returns:
        The persisted Task.
    """
    policy = classify_task(text)

    # Initial status based on policy
    if policy == TaskExecutionPolicy.AUTONOMOUS:
        status = TaskStatus.READY
    else:
        status = TaskStatus.WAITING_ON_OPERATOR

    # For non-autonomous tasks, generate a prompt for the operator
    input_prompt: Optional[str] = None
    if policy == TaskExecutionPolicy.NEEDS_OPERATOR:
        input_prompt = f"Operator input needed: {text}"
    elif policy == TaskExecutionPolicy.NEEDS_APPROVAL:
        input_prompt = f"Approval needed: {text}"

    task = Task.new(
        title=text,
        description=description,
        execution_policy=policy,
        status=status,
        day_session_id=session_id,
        requires_input_prompt=input_prompt,
    )

    store = TaskStore.default()
    store.put(task)
    _log(f"created {task.task_id} policy={policy.value} status={status.value}")
    return task


# ─── Task Execution Dispatcher ───────────────────────────────────────────────


def process_task(
    task: Task,
    *,
    is_day_open: bool = False,
    session: object = None,
    local_available: bool = False,
    use_v2_execution: bool = False,
) -> Task:
    """Dispatch a task based on its policy and current session state.

    For AUTONOMOUS tasks:
      - Day open + use_v2_execution → real execution via task_execution
      - Day open (v1 fallback) → immediate completion stub
      - Day closed → mark OVERNIGHT_QUEUED

    For NEEDS_OPERATOR / NEEDS_APPROVAL:
      - Leave as WAITING_ON_OPERATOR (surfaced in next open_day)

    Args:
        task: The task to process.
        is_day_open: Whether the operator's day session is currently open.
        session: OperatorSession for v2 routing context (optional).
        local_available: Whether local node is reachable (v2 only).
        use_v2_execution: If True, use real execution pipeline instead of v1 stub.

    Returns:
        The updated task (also persisted in the store).
    """
    store = TaskStore.default()

    # Assign priority and queue if not already set
    try:
        from substrate.execution.bridge.task_queue import prioritize_and_queue

        prioritize_and_queue(task, session=session, is_day_open=is_day_open)
    except Exception:  # noqa: BLE001
        pass  # best-effort — queue/priority are non-critical

    if task.execution_policy == TaskExecutionPolicy.AUTONOMOUS:
        if is_day_open:
            if use_v2_execution:
                # v2: real execution via task_execution pipeline
                try:
                    from substrate.execution.bridge.task_execution import execute_task

                    task = execute_task(
                        task, session=session, local_available=local_available
                    )
                    return task
                except Exception as exc:  # noqa: BLE001
                    _log(f"v2 execution failed, falling back to v1: {exc}")
                    # Fall through to v1 stub

            # v1 fallback: immediate completion
            task.status = TaskStatus.IN_PROGRESS
            store.put(task)
            task.status = TaskStatus.COMPLETED
            task.result = "executed (v1 — immediate completion)"
            store.put(task)
            _log(f"executed {task.task_id} (day open, v1)")
        else:
            task.status = TaskStatus.OVERNIGHT_QUEUED
            store.put(task)
            _log(f"queued {task.task_id} for overnight")

    # NEEDS_OPERATOR and NEEDS_APPROVAL stay as WAITING_ON_OPERATOR
    # — they were set at creation time and require operator action
    return task


# ─── Overnight Processing ────────────────────────────────────────────────────


def run_overnight_tasks(
    *,
    session: object = None,
    local_available: bool = False,
    use_v2_execution: bool = False,
) -> list[Task]:
    """Execute all OVERNIGHT_QUEUED tasks.

    Called from close_day when the session transitions to OVERNIGHT mode.
    Returns the list of tasks that were executed.

    Args:
        session: OperatorSession for v2 routing context (optional).
        local_available: Whether local node is reachable (v2 only).
        use_v2_execution: If True, use real execution pipeline.
    """
    if use_v2_execution:
        try:
            from substrate.execution.bridge.task_execution import run_overnight_execution

            result = run_overnight_execution(
                session=session,
                local_available=local_available,
            )
            # Return the tasks that were processed (for backward compat)
            store = TaskStore.default()
            return [
                store.get(tr["task_id"])
                for tr in result.get("task_results", [])
                if store.get(tr["task_id"]) is not None
            ]
        except Exception as exc:  # noqa: BLE001
            _log(f"v2 overnight execution failed, falling back to v1: {exc}")

    # v1 fallback: immediate completion
    store = TaskStore.default()
    queued = store.by_status(TaskStatus.OVERNIGHT_QUEUED)

    executed: list[Task] = []
    for task in queued:
        task.status = TaskStatus.IN_PROGRESS
        store.put(task)
        task.status = TaskStatus.COMPLETED
        task.result = "executed overnight (v1)"
        store.put(task)
        _log(f"overnight executed {task.task_id}")
        executed.append(task)

    if executed:
        _log(f"overnight batch: {len(executed)} tasks completed")
    return executed


# ─── Task Summary (for open_day briefing) ────────────────────────────────────


def get_task_summary() -> dict:
    """Build a summary dict for the open_day briefing.

    Returns:
        {
            "completed_overnight": int,
            "waiting_on_operator": int,
            "waiting_tasks": [{"task_id": str, "title": str, "prompt": str | None}, ...],
            "total_tasks": int,
        }
    """
    store = TaskStore.default()
    all_tasks = store.all()

    completed_overnight = sum(
        1
        for t in all_tasks
        if t.status == TaskStatus.COMPLETED
        and t.result is not None
        and "overnight" in t.result
    )

    waiting = store.by_status(TaskStatus.WAITING_ON_OPERATOR)
    waiting_details = [
        {
            "task_id": t.task_id,
            "title": t.title,
            "prompt": t.requires_input_prompt,
        }
        for t in waiting
    ]

    return {
        "completed_overnight": completed_overnight,
        "waiting_on_operator": len(waiting),
        "waiting_tasks": waiting_details,
        "total_tasks": len(all_tasks),
    }


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "TaskExecutionPolicy",
    "TaskStatus",
    "Task",
    "TaskStore",
    "classify_task",
    "create_task",
    "process_task",
    "run_overnight_tasks",
    "get_task_summary",
]
