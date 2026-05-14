"""Runtime Execution Queue v1 for the canonical runtime spine.

Governed execution queue with priority, dedup, and JSONL persistence.
Wraps execution envelopes with queue lifecycle tracking.

Queue states: PENDING → IN_PROGRESS → COMPLETED | FAILED | EXPIRED

UMH substrate subsystem. Phase 96.8BO.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .execution_contracts_v1 import (
    ExecutionEnvelope,
    _new_id,
    _now_iso,
    _content_hash,
)


class QueueEntryStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class QueuePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


PRIORITY_ORDER = {
    QueuePriority.CRITICAL: 0,
    QueuePriority.HIGH: 1,
    QueuePriority.NORMAL: 2,
    QueuePriority.LOW: 3,
}


@dataclass
class QueueEntry:
    """A single entry in the execution queue."""

    entry_id: str = ""
    envelope_id: str = ""
    command_name: str = ""
    correlation_id: str = ""
    priority: QueuePriority = QueuePriority.NORMAL
    status: QueueEntryStatus = QueueEntryStatus.PENDING
    envelope: ExecutionEnvelope | None = None
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    error_message: str = ""
    dedup_hash: str = ""
    retry_count: int = 0
    max_retries: int = 0

    def __post_init__(self) -> None:
        if not self.entry_id:
            self.entry_id = _new_id("qe")
        if not self.created_at:
            self.created_at = _now_iso()
        if not self.dedup_hash:
            self.dedup_hash = _content_hash(
                {"envelope_id": self.envelope_id, "command": self.command_name}
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "envelope_id": self.envelope_id,
            "command_name": self.command_name,
            "correlation_id": self.correlation_id,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
            "dedup_hash": self.dedup_hash,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }


class RuntimeExecutionQueue:
    """Governed execution queue with priority ordering and JSONL persistence."""

    def __init__(self, queue_dir: str | Path = "data/runtime/execution_queue") -> None:
        self._queue_dir = Path(queue_dir)
        self._queue_dir.mkdir(parents=True, exist_ok=True)
        self._ledger_path = self._queue_dir / "queue_ledger.jsonl"
        self._entries: dict[str, QueueEntry] = {}
        self._dedup_hashes: set[str] = set()

    def enqueue(
        self,
        envelope: ExecutionEnvelope,
        priority: QueuePriority = QueuePriority.NORMAL,
    ) -> QueueEntry | None:
        """Add an execution envelope to the queue. Returns None if duplicate."""
        command = envelope.intent.command_name if envelope.intent else ""
        entry = QueueEntry(
            envelope_id=envelope.envelope_id,
            command_name=command,
            correlation_id=envelope.correlation_id,
            priority=priority,
            envelope=envelope,
        )

        if entry.dedup_hash in self._dedup_hashes:
            return None

        self._entries[entry.entry_id] = entry
        self._dedup_hashes.add(entry.dedup_hash)
        self._persist_entry(entry)
        return entry

    def dequeue(self) -> QueueEntry | None:
        """Get the next pending entry by priority."""
        pending = [e for e in self._entries.values() if e.status == QueueEntryStatus.PENDING]
        if not pending:
            return None
        pending.sort(key=lambda e: PRIORITY_ORDER.get(e.priority, 2))
        entry = pending[0]
        entry.status = QueueEntryStatus.IN_PROGRESS
        entry.started_at = _now_iso()
        return entry

    def complete(self, entry_id: str) -> bool:
        entry = self._entries.get(entry_id)
        if not entry or entry.status != QueueEntryStatus.IN_PROGRESS:
            return False
        entry.status = QueueEntryStatus.COMPLETED
        entry.completed_at = _now_iso()
        return True

    def fail(self, entry_id: str, error_message: str = "") -> bool:
        entry = self._entries.get(entry_id)
        if not entry:
            return False
        entry.status = QueueEntryStatus.FAILED
        entry.completed_at = _now_iso()
        entry.error_message = error_message
        return True

    def cancel(self, entry_id: str) -> bool:
        entry = self._entries.get(entry_id)
        if not entry or entry.status not in (
            QueueEntryStatus.PENDING,
            QueueEntryStatus.IN_PROGRESS,
        ):
            return False
        entry.status = QueueEntryStatus.CANCELLED
        entry.completed_at = _now_iso()
        return True

    def get_entry(self, entry_id: str) -> QueueEntry | None:
        return self._entries.get(entry_id)

    def get_pending(self) -> list[QueueEntry]:
        return [e for e in self._entries.values() if e.status == QueueEntryStatus.PENDING]

    def get_in_progress(self) -> list[QueueEntry]:
        return [e for e in self._entries.values() if e.status == QueueEntryStatus.IN_PROGRESS]

    def get_all(self) -> list[QueueEntry]:
        return list(self._entries.values())

    @property
    def depth(self) -> int:
        return len(self.get_pending())

    def get_stats(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        for e in self._entries.values():
            by_status[e.status.value] = by_status.get(e.status.value, 0) + 1
        return {
            "total": len(self._entries),
            "pending": len(self.get_pending()),
            "in_progress": len(self.get_in_progress()),
            "by_status": by_status,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self._entries.values()],
            "stats": self.get_stats(),
        }

    def _persist_entry(self, entry: QueueEntry) -> None:
        with open(self._ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), default=str) + "\n")
