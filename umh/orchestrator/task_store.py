"""SQLite-backed task persistence for cross-process durability.

Mirrors the approval_persistence.py pattern: WAL mode, thread-safe,
pluggable backend protocol for test/production switching.

Tasks survive process restarts. Paused tasks can be resumed after reboot.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Protocol

from umh.orchestrator.task import (
    StepStatus,
    Task,
    TaskStatus,
    TaskStep,
)

_DEFAULT_DB_PATH = "/opt/OS/data/runtime/tasks.sqlite"


class TaskBackend(Protocol):
    def save(self, task: Task) -> None: ...
    def get(self, task_id: str) -> Task | None: ...
    def list_all(self) -> list[Task]: ...
    def list_by_status(self, status: TaskStatus) -> list[Task]: ...
    def update_status(self, task_id: str, status: TaskStatus) -> None: ...
    def claim_task(self, task_id: str, worker_id: str = "") -> bool: ...
    def list_stuck_tasks(self, timeout_seconds: float = 300) -> list[Task]: ...
    def recover_stuck_task(self, task_id: str) -> bool: ...
    def reset(self) -> None: ...


class InMemoryTaskBackend:
    """In-memory backend for testing."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._claimed: set[str] = set()
        self._claimed_by: dict[str, str] = {}
        self._claimed_at: dict[str, str] = {}

    def save(self, task: Task) -> None:
        self._tasks[task.id] = task

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def list_all(self) -> list[Task]:
        return list(self._tasks.values())

    def list_by_status(self, status: TaskStatus) -> list[Task]:
        return [t for t in self._tasks.values() if t.status == status]

    def update_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks.get(task_id)
        if task is not None:
            task.status = status

    def claim_task(self, task_id: str, worker_id: str = "") -> bool:
        if task_id in self._claimed:
            return False
        task = self._tasks.get(task_id)
        if task is None or task.status != TaskStatus.PENDING:
            return False
        self._claimed.add(task_id)
        self._claimed_by[task_id] = worker_id
        self._claimed_at[task_id] = datetime.now(timezone.utc).isoformat()
        task.status = TaskStatus.RUNNING
        return True

    def list_stuck_tasks(self, timeout_seconds: float = 300) -> list[Task]:
        now = datetime.now(timezone.utc)
        stuck = []
        for task in self._tasks.values():
            if task.status != TaskStatus.RUNNING:
                continue
            claimed_at_str = self._claimed_at.get(task.id, "")
            if not claimed_at_str:
                continue
            claimed_at = datetime.fromisoformat(claimed_at_str)
            if claimed_at.tzinfo is None:
                claimed_at = claimed_at.replace(tzinfo=timezone.utc)
            elapsed = (now - claimed_at).total_seconds()
            if elapsed > timeout_seconds:
                stuck.append(task)
        return stuck

    def recover_stuck_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None or task.status != TaskStatus.RUNNING:
            return False
        task.status = TaskStatus.FAILED
        task.error = "stuck: worker lease expired"
        task.updated_at = datetime.now(timezone.utc).isoformat()
        # Clear claim state so it can be retried
        self._claimed.discard(task_id)
        self._claimed_by.pop(task_id, None)
        self._claimed_at.pop(task_id, None)
        return True

    def reset(self) -> None:
        self._tasks.clear()
        self._claimed.clear()
        self._claimed_by.clear()
        self._claimed_at.clear()


class SQLiteTaskBackend:
    """SQLite-backed task storage for cross-process durability."""

    def __init__(self, db_path: str = _DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    current_step_index INTEGER NOT NULL DEFAULT 0,
                    steps_json TEXT NOT NULL DEFAULT '[]',
                    context_json TEXT NOT NULL DEFAULT '{}',
                    issued_by TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT '',
                    paused_step_index INTEGER,
                    paused_approval_id TEXT NOT NULL DEFAULT '',
                    paused_request_json TEXT,
                    paused_reason TEXT NOT NULL DEFAULT '',
                    pause_count INTEGER NOT NULL DEFAULT 0,
                    resumed_at TEXT NOT NULL DEFAULT '',
                    claimed_by TEXT NOT NULL DEFAULT '',
                    claimed_at TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            # Migrate existing tables that lack the new columns
            try:
                conn.execute("ALTER TABLE tasks ADD COLUMN claimed_by TEXT NOT NULL DEFAULT ''")
            except sqlite3.OperationalError:
                pass  # column already exists
            try:
                conn.execute("ALTER TABLE tasks ADD COLUMN claimed_at TEXT NOT NULL DEFAULT ''")
            except sqlite3.OperationalError:
                pass  # column already exists
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=3000")
        conn.row_factory = sqlite3.Row
        return conn

    def _task_to_row(self, task: Task) -> tuple:
        steps_json = json.dumps([s.to_dict() for s in task.steps])
        context_json = json.dumps(task.context)
        paused_request_json = json.dumps(task.paused_request) if task.paused_request else None
        plan_id = task.context.get("plan_id", "")
        claimed_by = getattr(task, "_claimed_by", "")
        claimed_at = getattr(task, "_claimed_at", "")
        return (
            task.id,
            plan_id,
            task.status.value,
            task.current_step_index,
            steps_json,
            context_json,
            task.issued_by,
            task.error,
            task.paused_step_index,
            task.paused_approval_id,
            paused_request_json,
            task.paused_reason,
            task.pause_count,
            task.resumed_at,
            claimed_by,
            claimed_at,
            task.created_at,
            task.updated_at,
        )

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        steps_data = json.loads(row["steps_json"])
        steps = []
        for sd in steps_data:
            step = TaskStep(
                operation=sd["operation"],
                inputs_template=sd.get("inputs_template", {}),
                output_key=sd.get("output_key", ""),
                execution_class=sd.get("execution_class", "llm_call"),
                id=sd.get("id", ""),
                status=StepStatus(sd.get("status", "pending")),
                result=sd.get("result"),
            )
            steps.append(step)

        context = json.loads(row["context_json"])
        paused_request = None
        if row["paused_request_json"]:
            paused_request = json.loads(row["paused_request_json"])

        task = Task.__new__(Task)
        task.steps = steps
        task.id = row["id"]
        task.status = TaskStatus(row["status"])
        task.current_step_index = row["current_step_index"]
        task.context = context
        task.created_at = row["created_at"]
        task.updated_at = row["updated_at"]
        task.issued_by = row["issued_by"]
        task.error = row["error"]
        task.paused_step_index = row["paused_step_index"]
        task.paused_approval_id = row["paused_approval_id"]
        task.paused_request = paused_request
        task.paused_reason = row["paused_reason"]
        task.pause_count = row["pause_count"]
        task.resumed_at = row["resumed_at"]
        task._claimed_by = row["claimed_by"]
        task._claimed_at = row["claimed_at"]
        return task

    def save(self, task: Task) -> None:
        row = self._task_to_row(task)
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO tasks
                       (id, plan_id, status, current_step_index, steps_json,
                        context_json, issued_by, error, paused_step_index,
                        paused_approval_id, paused_request_json, paused_reason,
                        pause_count, resumed_at, claimed_by, claimed_at,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    row,
                )
                conn.commit()

    def get(self, task_id: str) -> Task | None:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
                if row is None:
                    return None
                return self._row_to_task(row)

    def list_all(self) -> list[Task]:
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
                return [self._row_to_task(r) for r in rows]

    def list_by_status(self, status: TaskStatus) -> list[Task]:
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY created_at ASC",
                    (status.value,),
                ).fetchall()
                return [self._row_to_task(r) for r in rows]

    def update_status(self, task_id: str, status: TaskStatus) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                    (status.value, now, task_id),
                )
                conn.commit()

    def claim_task(self, task_id: str, worker_id: str = "") -> bool:
        """Atomically claim a PENDING task for execution. Returns True if claimed."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    "UPDATE tasks SET status = 'running', updated_at = ?, "
                    "claimed_by = ?, claimed_at = ? "
                    "WHERE id = ? AND status = 'pending'",
                    (now, worker_id, now, task_id),
                )
                conn.commit()
                return cursor.rowcount > 0

    def list_stuck_tasks(self, timeout_seconds: float = 300) -> list[Task]:
        """Return RUNNING tasks whose claimed_at is older than timeout_seconds."""
        now = datetime.now(timezone.utc)
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM tasks WHERE status = 'running' AND claimed_at != ''",
                ).fetchall()
                stuck = []
                for row in rows:
                    claimed_at = datetime.fromisoformat(row["claimed_at"])
                    if claimed_at.tzinfo is None:
                        claimed_at = claimed_at.replace(tzinfo=timezone.utc)
                    elapsed = (now - claimed_at).total_seconds()
                    if elapsed > timeout_seconds:
                        stuck.append(self._row_to_task(row))
                return stuck

    def recover_stuck_task(self, task_id: str) -> bool:
        """Mark a stuck RUNNING task as FAILED. Returns True if updated."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    "UPDATE tasks SET status = 'failed', "
                    "error = 'stuck: worker lease expired', "
                    "updated_at = ?, claimed_by = '', claimed_at = '' "
                    "WHERE id = ? AND status = 'running'",
                    (now, task_id),
                )
                conn.commit()
                return cursor.rowcount > 0

    def reset(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM tasks")
                conn.commit()


def _default_backend():
    if os.environ.get("UMH_TASK_BACKEND") == "memory":
        return InMemoryTaskBackend()
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("UMH_TASK_BACKEND") == "test":
        return InMemoryTaskBackend()
    return SQLiteTaskBackend()


class TaskStore:
    """Thread-safe task store with pluggable backend."""

    def __init__(self, backend=None) -> None:
        self._backend = backend if backend is not None else _default_backend()
        self._lock = threading.Lock()

    def save(self, task: Task) -> None:
        with self._lock:
            self._backend.save(task)

    def get(self, task_id: str) -> Task | None:
        with self._lock:
            return self._backend.get(task_id)

    def list_all(self) -> list[Task]:
        with self._lock:
            return self._backend.list_all()

    def list_by_status(self, status: TaskStatus) -> list[Task]:
        with self._lock:
            return self._backend.list_by_status(status)

    def claim_task(self, task_id: str, worker_id: str = "") -> bool:
        with self._lock:
            return self._backend.claim_task(task_id, worker_id=worker_id)

    def list_stuck_tasks(self, timeout_seconds: float = 300) -> list[Task]:
        with self._lock:
            return self._backend.list_stuck_tasks(timeout_seconds=timeout_seconds)

    def recover_stuck_task(self, task_id: str) -> bool:
        with self._lock:
            return self._backend.recover_stuck_task(task_id)

    def reset(self) -> None:
        with self._lock:
            self._backend.reset()


_store: TaskStore | None = None
_store_lock = threading.Lock()


def get_task_store() -> TaskStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = TaskStore()
    return _store


def reset_task_store(backend=None) -> TaskStore:
    global _store
    with _store_lock:
        _store = TaskStore(backend=backend)
    return _store
