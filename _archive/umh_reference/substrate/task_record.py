"""
Task Record — append-only JSONL store for task lifecycle indexing.

Indexes the full lifecycle of a task from creation through completion
or failure.  Cross-references with the interaction archive (via
interaction_ids) and event spine (via correlation_id).

Separate from interaction archive and event spine by design:
  - Event spine = structured machine events (what happened)
  - Interaction archive = verbatim human/AI text (what was said)
  - Task record = lifecycle envelope (what was requested, how it ended)
  - They cross-reference via correlation_id

Design rules:
  - Append-only for creation.  Status updates rewrite the file (same
    pattern as event_store.update_status).
  - Thread-safe.  Single file lock, moderate throughput.
  - Best-effort.  Write failures are logged to stderr, never raised.
  - No DB dependency.  JSONL flat file.
  - Bounded retrieval.  Query helpers cap results by default.

File: logs/task_records.jsonl
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional

# ─── Config ──────────────────────────────────────────────────────────────────

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_DEFAULT_STORE_PATH = os.path.join(_REPO_ROOT, "logs", "task_records.jsonl")
_LOG_PREFIX = "[substrate.task_record]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _new_task_id() -> str:
    return uuid.uuid4().hex


# ─── Enums ───────────────────────────────────────────────────────────────────


class TaskRecordStatus(str, Enum):
    """Lifecycle status of a tracked task."""

    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


# ─── Data Model ──────────────────────────────────────────────────────────────


@dataclass
class TaskRecord:
    """One task lifecycle record in the task record store.

    Attributes:
        task_id: Globally unique identifier for this task.
        correlation_id: Workflow-level ID shared with event spine
            and interaction archive.
        status: Current lifecycle status (TaskRecordStatus value).
        input_summary: Short description of what was requested.
        final_report: Full text or reference, filled on completion.
        interaction_ids: archive_ids from interaction_archive linked
            to this task.
        interface: Source interface (discord, workstation, internal, etc).
        created_at: ISO timestamp of task creation.
        completed_at: ISO timestamp of completion, empty until done.
        metadata: Bounded additional context.
    """

    task_id: str = field(default_factory=_new_task_id)
    correlation_id: str = ""
    status: str = TaskRecordStatus.CREATED.value
    input_summary: str = ""
    final_report: str = ""
    interaction_ids: list[str] = field(default_factory=list)
    interface: str = "discord"
    created_at: str = field(default_factory=_now_iso)
    completed_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def serialize(self) -> dict[str, Any]:
        """JSON-safe dict for JSONL storage."""
        return asdict(self)

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "TaskRecord":
        """Reconstruct from a serialized dict."""
        return cls(
            task_id=data.get("task_id", _new_task_id()),
            correlation_id=data.get("correlation_id", ""),
            status=data.get("status", TaskRecordStatus.CREATED.value),
            input_summary=data.get("input_summary", ""),
            final_report=data.get("final_report", ""),
            interaction_ids=data.get("interaction_ids", []),
            interface=data.get("interface", "discord"),
            created_at=data.get("created_at", _now_iso()),
            completed_at=data.get("completed_at", ""),
            metadata=data.get("metadata", {}),
        )


# ─── Task Record Store ──────────────────────────────────────────────────────


class TaskRecordStore:
    """Append-only JSONL store for task lifecycle records.

    Thread-safe.  New tasks are appended; status transitions rewrite
    the file (same pattern as event_store.update_status).  Query
    helpers provide bounded retrieval by various dimensions.
    """

    def __init__(self, path: str = _DEFAULT_STORE_PATH) -> None:
        self._path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    @property
    def path(self) -> str:
        return self._path

    # ─── Write ────────────────────────────────────────────────────────────

    def create_task(
        self,
        input_summary: str,
        correlation_id: str = "",
        interface: str = "discord",
        metadata: Optional[dict[str, Any]] = None,
    ) -> TaskRecord:
        """Create a new task record with status=CREATED.

        Generates a task_id, appends to JSONL immediately, and returns
        the TaskRecord.  Best-effort: failures logged, never raised.
        """
        record = TaskRecord(
            correlation_id=correlation_id,
            status=TaskRecordStatus.CREATED.value,
            input_summary=input_summary,
            interface=interface,
            metadata=metadata or {},
        )
        with self._lock:
            try:
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record.serialize()) + "\n")
            except Exception as exc:
                _log(f"create_task failed: {exc}")
        return record

    def complete_task(
        self,
        task_id: str,
        final_report: str = "",
        interaction_ids: Optional[list[str]] = None,
    ) -> bool:
        """Mark a task as completed.

        Updates status to COMPLETED, sets completed_at, final_report,
        and interaction_ids.  Rewrites the file.  Returns True if the
        task was found and updated.
        """
        with self._lock:
            items = self._read_all()
            found = False
            for item in items:
                if item.get("task_id") == task_id:
                    item["status"] = TaskRecordStatus.COMPLETED.value
                    item["completed_at"] = _now_iso()
                    item["final_report"] = final_report
                    if interaction_ids is not None:
                        item["interaction_ids"] = interaction_ids
                    found = True
                    break
            if found:
                self._write_all(items)
        return found

    def fail_task(self, task_id: str, reason: str = "") -> bool:
        """Mark a task as failed.

        Updates status to FAILED, sets completed_at, and stores the
        failure reason in metadata.  Rewrites the file.  Returns True
        if the task was found and updated.
        """
        with self._lock:
            items = self._read_all()
            found = False
            for item in items:
                if item.get("task_id") == task_id:
                    item["status"] = TaskRecordStatus.FAILED.value
                    item["completed_at"] = _now_iso()
                    meta = item.get("metadata", {})
                    meta["failure_reason"] = reason
                    item["metadata"] = meta
                    found = True
                    break
            if found:
                self._write_all(items)
        return found

    def mark_in_progress(self, task_id: str) -> bool:
        """Update a task's status to IN_PROGRESS.

        Rewrites the file.  Returns True if the task was found
        and updated.
        """
        with self._lock:
            items = self._read_all()
            found = False
            for item in items:
                if item.get("task_id") == task_id:
                    item["status"] = TaskRecordStatus.IN_PROGRESS.value
                    found = True
                    break
            if found:
                self._write_all(items)
        return found

    def add_interaction(self, task_id: str, archive_id: str) -> bool:
        """Append an archive_id to a task's interaction_ids list.

        Rewrites the file.  Returns True if the task was found
        and updated.
        """
        with self._lock:
            items = self._read_all()
            found = False
            for item in items:
                if item.get("task_id") == task_id:
                    ids = item.get("interaction_ids", [])
                    ids.append(archive_id)
                    item["interaction_ids"] = ids
                    found = True
                    break
            if found:
                self._write_all(items)
        return found

    # ─── Read helpers ─────────────────────────────────────────────────────

    def recent(self, limit: int = 20) -> list[TaskRecord]:
        """Retrieve the most recent N task records.

        Returns newest-last ordering.
        """
        with self._lock:
            items = self._read_all()

        results: list[TaskRecord] = []
        for item in items[-limit:]:
            try:
                results.append(TaskRecord.deserialize(item))
            except Exception:
                pass
        return results

    def by_time_window(
        self,
        start_iso: str,
        end_iso: Optional[str] = None,
        *,
        limit: int = 100,
    ) -> list[TaskRecord]:
        """Retrieve tasks created within an ISO time window.

        If end_iso is None, retrieves from start_iso to now.
        Returns chronological order.
        """
        end = end_iso or _now_iso()

        with self._lock:
            items = self._read_all()

        results: list[TaskRecord] = []
        for item in items:
            created = item.get("created_at", "")
            if created >= start_iso and created <= end:
                try:
                    results.append(TaskRecord.deserialize(item))
                except Exception:
                    pass
                if len(results) >= limit:
                    break
        return results

    def by_status(self, status: str, *, limit: int = 50) -> list[TaskRecord]:
        """Filter task records by status value.

        Returns newest-last ordering.
        """
        with self._lock:
            items = self._read_all()

        filtered = [i for i in items if i.get("status") == status]

        results: list[TaskRecord] = []
        for item in filtered[-limit:]:
            try:
                results.append(TaskRecord.deserialize(item))
            except Exception:
                pass
        return results

    def by_correlation_id(self, correlation_id: str) -> Optional[TaskRecord]:
        """Find a task by correlation_id.

        Returns the first matching task, or None.
        """
        with self._lock:
            items = self._read_all()

        for item in items:
            if item.get("correlation_id") == correlation_id:
                try:
                    return TaskRecord.deserialize(item)
                except Exception:
                    return None
        return None

    def search_text(self, query: str, *, limit: int = 20) -> list[TaskRecord]:
        """Simple case-insensitive substring match against input_summary
        and final_report.

        Returns newest-last ordering within matches.
        """
        q = query.lower()

        with self._lock:
            items = self._read_all()

        matched: list[dict[str, Any]] = []
        for item in items:
            summary = item.get("input_summary", "").lower()
            report = item.get("final_report", "").lower()
            if q in summary or q in report:
                matched.append(item)

        results: list[TaskRecord] = []
        for item in matched[-limit:]:
            try:
                results.append(TaskRecord.deserialize(item))
            except Exception:
                pass
        return results

    def get(self, task_id: str) -> Optional[TaskRecord]:
        """Get a single task record by ID."""
        with self._lock:
            for item in self._read_all():
                if item.get("task_id") == task_id:
                    try:
                        return TaskRecord.deserialize(item)
                    except Exception:
                        return None
        return None

    def count(self) -> int:
        """Return total number of task records."""
        with self._lock:
            items = self._read_all()
        return len(items)

    # ─── Internal I/O ─────────────────────────────────────────────────────

    def _read_all(self) -> list[dict[str, Any]]:
        """Read all records from disk.  Must hold self._lock."""
        items: list[dict[str, Any]] = []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            items.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except FileNotFoundError:
            pass
        return items

    def _write_all(self, items: list[dict[str, Any]]) -> None:
        """Rewrite entire store.  Must hold self._lock."""
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                for item in items:
                    f.write(json.dumps(item) + "\n")
        except Exception as exc:
            _log(f"write failed: {exc}")


# ─── Factory helpers ─────────────────────────────────────────────────────────


def record_task_start(
    input_summary: str,
    correlation_id: str = "",
    interface: str = "discord",
    metadata: Optional[dict[str, Any]] = None,
) -> str:
    """Create a task via the singleton store and return the task_id.

    Convenience wrapper for one-liner task creation.
    """
    record = get_task_record_store().create_task(
        input_summary=input_summary,
        correlation_id=correlation_id,
        interface=interface,
        metadata=metadata,
    )
    return record.task_id


def record_task_complete(
    task_id: str,
    final_report: str = "",
    interaction_ids: Optional[list[str]] = None,
) -> bool:
    """Mark a task as completed via the singleton store.

    Convenience wrapper. Returns True if found and updated.
    """
    return get_task_record_store().complete_task(
        task_id=task_id,
        final_report=final_report,
        interaction_ids=interaction_ids,
    )


def record_task_failure(task_id: str, reason: str = "") -> bool:
    """Mark a task as failed via the singleton store.

    Convenience wrapper. Returns True if found and updated.
    """
    return get_task_record_store().fail_task(task_id=task_id, reason=reason)


# ─── Module-level singleton ─────────────────────────────────────────────────

_store: Optional[TaskRecordStore] = None
_store_lock = threading.Lock()


def get_task_record_store() -> TaskRecordStore:
    """Get the module-level task record store singleton.

    Thread-safe lazy initialization.
    """
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = TaskRecordStore()
    return _store


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "TaskRecordStatus",
    "TaskRecord",
    "TaskRecordStore",
    "get_task_record_store",
    "record_task_start",
    "record_task_complete",
    "record_task_failure",
]
