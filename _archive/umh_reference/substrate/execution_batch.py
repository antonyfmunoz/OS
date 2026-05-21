"""
umh.substrate.execution_batch — Batch execution primitives for
autonomous/background work without product coupling.

Represents a group of related execution tasks that can be dispatched,
tracked, and completed as a unit. All state transitions are expressed
as pure mutation dicts (SET/REMOVE) for replay-safe persistence.

Public API:
    BatchTask                — single task within a batch
    ExecutionBatch           — group of related tasks
    compute_batch_id         — deterministic batch ID
    build_execution_batch    — construct a new batch
    batch_to_mutations       — persistence mutations for a batch
    load_execution_batch     — reconstruct batch from state
    list_pending_batches     — enumerate pending batch IDs
    mark_batch_started       — transition batch to active
    mark_batch_completed     — transition batch to completed
    mark_batch_failed        — transition batch to failed

Separation note:
    This module is harness-only. No transport, UI, or product logic.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_LOG_PREFIX = "[substrate.execution_batch]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# State key helpers
# ---------------------------------------------------------------------------
_BATCH_KEY_PREFIX = "execution_batch."
_PENDING_INDEX_PREFIX = "execution_batch_index.pending."
_ACTIVE_INDEX_PREFIX = "execution_batch_index.active."
_COMPLETED_INDEX_PREFIX = "execution_batch_index.completed."
_FAILED_INDEX_PREFIX = "execution_batch_index.failed."


def _batch_key(batch_id: str) -> str:
    return f"{_BATCH_KEY_PREFIX}{batch_id}"


def _pending_key(batch_id: str) -> str:
    return f"{_PENDING_INDEX_PREFIX}{batch_id}"


def _active_key(batch_id: str) -> str:
    return f"{_ACTIVE_INDEX_PREFIX}{batch_id}"


def _completed_key(batch_id: str) -> str:
    return f"{_COMPLETED_INDEX_PREFIX}{batch_id}"


def _failed_key(batch_id: str) -> str:
    return f"{_FAILED_INDEX_PREFIX}{batch_id}"


# ---------------------------------------------------------------------------
# BatchTask — single unit of work in a batch
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BatchTask:
    """One task within an execution batch.

    Fields:
        task_id:          unique task identifier
        execution_class:  type of execution (e.g. 'local_runtime', 'workstation')
        payload:          task-specific data
        priority:         sort order (lower = higher priority)
        created_at:       ISO timestamp
        source:           originating module/system
        correlation_id:   links task to upstream intent/event
    """

    task_id: str
    execution_class: str
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 100
    created_at: str = ""
    source: str = ""
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
            "execution_class": self.execution_class,
            "payload": dict(self.payload),
            "priority": self.priority,
            "source": self.source,
            "task_id": self.task_id,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> BatchTask:
        return BatchTask(
            task_id=str(d.get("task_id", "")),
            execution_class=str(d.get("execution_class", "")),
            payload=dict(d.get("payload", {})),
            priority=int(d.get("priority", 100)),
            created_at=str(d.get("created_at", "")),
            source=str(d.get("source", "")),
            correlation_id=str(d.get("correlation_id", "")),
        )


# ---------------------------------------------------------------------------
# ExecutionBatch — group of related tasks
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ExecutionBatch:
    """Immutable batch of related execution tasks.

    Fields:
        batch_id:     deterministic batch identifier
        session_id:   owning session
        mode:         runtime mode when batch was created
        created_at:   ISO timestamp
        tasks:        ordered tuple of BatchTask
        status:       pending | active | completed | failed
    """

    batch_id: str
    session_id: str
    mode: str
    created_at: str
    tasks: tuple[BatchTask, ...] = ()
    status: str = "pending"

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "created_at": self.created_at,
            "mode": self.mode,
            "session_id": self.session_id,
            "status": self.status,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> ExecutionBatch:
        tasks_raw = d.get("tasks", [])
        return ExecutionBatch(
            batch_id=str(d.get("batch_id", "")),
            session_id=str(d.get("session_id", "")),
            mode=str(d.get("mode", "")),
            created_at=str(d.get("created_at", "")),
            tasks=tuple(BatchTask.from_dict(t) for t in tasks_raw),
            status=str(d.get("status", "pending")),
        )

    def with_status(self, status: str) -> ExecutionBatch:
        """Return a copy with updated status."""
        d = self.to_dict()
        d["status"] = status
        return ExecutionBatch.from_dict(d)


# ---------------------------------------------------------------------------
# Deterministic ID
# ---------------------------------------------------------------------------


def compute_batch_id(
    session_id: str,
    tasks: tuple[BatchTask, ...],
) -> str:
    """Deterministic batch ID: same session + tasks → same ID.

    Uses SHA-256 of canonical JSON (sorted keys, compact separators).
    """
    task_data = [
        {"task_id": t.task_id, "execution_class": t.execution_class} for t in tasks
    ]
    canonical = json.dumps(
        {"session_id": session_id, "tasks": task_data},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"bat_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_execution_batch(
    *,
    session_id: str,
    mode: str,
    tasks: tuple[BatchTask, ...],
    batch_id: str | None = None,
) -> ExecutionBatch:
    """Construct a new ExecutionBatch with deterministic ID."""
    bid = batch_id or compute_batch_id(session_id, tasks)
    return ExecutionBatch(
        batch_id=bid,
        session_id=session_id,
        mode=mode,
        created_at=_utcnow(),
        tasks=tasks,
        status="pending",
    )


# ---------------------------------------------------------------------------
# Mutation builders — SET / REMOVE only
# ---------------------------------------------------------------------------


def batch_to_mutations(batch: ExecutionBatch) -> list[dict[str, Any]]:
    """Build mutations to persist a new batch.

    Writes:
        1. Batch record: execution_batch.{batch_id}
        2. Pending index: execution_batch_index.pending.{batch_id}
    """
    return [
        {
            "op": "SET",
            "key": _batch_key(batch.batch_id),
            "value": batch.to_dict(),
        },
        {
            "op": "SET",
            "key": _pending_key(batch.batch_id),
            "value": {
                "session_id": batch.session_id,
                "mode": batch.mode,
                "task_count": len(batch.tasks),
                "created_at": batch.created_at,
            },
        },
    ]


def mark_batch_started(
    batch: ExecutionBatch,
) -> tuple[ExecutionBatch, list[dict[str, Any]]]:
    """Transition batch from pending to active.

    Returns (updated_batch, mutations).
    """
    updated = batch.with_status("active")
    mutations = [
        {
            "op": "SET",
            "key": _batch_key(batch.batch_id),
            "value": updated.to_dict(),
        },
        {"op": "REMOVE", "key": _pending_key(batch.batch_id)},
        {
            "op": "SET",
            "key": _active_key(batch.batch_id),
            "value": {
                "session_id": batch.session_id,
                "task_count": len(batch.tasks),
                "started_at": _utcnow(),
            },
        },
    ]
    return updated, mutations


def mark_batch_completed(
    batch: ExecutionBatch,
) -> tuple[ExecutionBatch, list[dict[str, Any]]]:
    """Transition batch to completed.

    Returns (updated_batch, mutations).
    """
    updated = batch.with_status("completed")
    mutations = [
        {
            "op": "SET",
            "key": _batch_key(batch.batch_id),
            "value": updated.to_dict(),
        },
        {"op": "REMOVE", "key": _active_key(batch.batch_id)},
        {
            "op": "SET",
            "key": _completed_key(batch.batch_id),
            "value": {
                "session_id": batch.session_id,
                "completed_at": _utcnow(),
            },
        },
    ]
    return updated, mutations


def mark_batch_failed(
    batch: ExecutionBatch,
    *,
    reason: str = "",
) -> tuple[ExecutionBatch, list[dict[str, Any]]]:
    """Transition batch to failed.

    Returns (updated_batch, mutations).
    """
    updated = batch.with_status("failed")
    mutations = [
        {
            "op": "SET",
            "key": _batch_key(batch.batch_id),
            "value": updated.to_dict(),
        },
        {"op": "REMOVE", "key": _active_key(batch.batch_id)},
        {"op": "REMOVE", "key": _pending_key(batch.batch_id)},
        {
            "op": "SET",
            "key": _failed_key(batch.batch_id),
            "value": {
                "session_id": batch.session_id,
                "failed_at": _utcnow(),
                "reason": reason,
            },
        },
    ]
    return updated, mutations


# ---------------------------------------------------------------------------
# Load / list helpers
# ---------------------------------------------------------------------------


def load_execution_batch(
    state: dict[str, Any],
    batch_id: str,
) -> ExecutionBatch | None:
    """Reconstruct an ExecutionBatch from state, or None if missing."""
    raw = state.get(_batch_key(batch_id))
    if not isinstance(raw, dict):
        return None
    return ExecutionBatch.from_dict(raw)


def list_pending_batches(state: dict[str, Any]) -> tuple[str, ...]:
    """Return sorted tuple of pending batch IDs from state."""
    ids = sorted(
        k[len(_PENDING_INDEX_PREFIX) :]
        for k in state
        if k.startswith(_PENDING_INDEX_PREFIX)
    )
    return tuple(ids)
