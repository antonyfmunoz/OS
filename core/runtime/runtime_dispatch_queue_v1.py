"""Runtime Dispatch Queue v1 for the UMH substrate layer.

Filesystem-based dispatch queue for WorkPackets. The VPS control
plane enqueues validated packets; the local runtime supervisor
dequeues and processes them. Idempotent dispatch with dedup.

Composes: core/environment_bridge/queue_paths.py

UMH substrate subsystem. Phase 96.8AE.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class DispatchStatus(str, Enum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class DispatchRecord:
    """A queued work packet dispatch record."""

    dispatch_id: str
    packet_id: str
    action_type: str
    target_environment: str
    target_runtime: str
    authority_class: str = ""
    governance_trace_id: str = ""
    execution_lineage_id: str = ""
    blocked_actions: list[str] = field(default_factory=list)
    proof_requirements: list[str] = field(default_factory=list)
    timeout_seconds: int = 300
    status: DispatchStatus = DispatchStatus.QUEUED
    dispatch_hash: str = ""
    created_at: str = ""
    claimed_at: str = ""
    completed_at: str = ""
    worker_id: str = ""
    session_id: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.dispatch_id:
            self.dispatch_id = f"DISPATCH-{uuid.uuid4().hex[:8]}"
        if not self.dispatch_hash:
            self.dispatch_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = json.dumps(
            {
                "packet_id": self.packet_id,
                "action_type": self.action_type,
                "target_environment": self.target_environment,
                "target_runtime": self.target_runtime,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "dispatch_id": self.dispatch_id,
            "packet_id": self.packet_id,
            "action_type": self.action_type,
            "target_environment": self.target_environment,
            "target_runtime": self.target_runtime,
            "authority_class": self.authority_class,
            "governance_trace_id": self.governance_trace_id,
            "execution_lineage_id": self.execution_lineage_id,
            "blocked_actions": self.blocked_actions,
            "proof_requirements": self.proof_requirements,
            "timeout_seconds": self.timeout_seconds,
            "status": self.status.value,
            "dispatch_hash": self.dispatch_hash,
            "created_at": self.created_at,
            "claimed_at": self.claimed_at,
            "completed_at": self.completed_at,
            "worker_id": self.worker_id,
            "session_id": self.session_id,
            "notes": self.notes,
        }


class RuntimeDispatchQueue:
    """Filesystem-backed dispatch queue for WorkPacket execution.

    Enqueue writes a JSON file to the outbox directory.
    Dequeue reads from inbox (local worker side).
    Idempotent: same packet_id cannot be dispatched twice.
    """

    def __init__(self, queue_dir: Path) -> None:
        self.queue_dir = queue_dir
        self._outbox = queue_dir / "outbox"
        self._inbox = queue_dir / "inbox"
        self._archive = queue_dir / "archive"
        self._results = queue_dir / "results"
        for d in [self._outbox, self._inbox, self._archive, self._results]:
            d.mkdir(parents=True, exist_ok=True)
        self._dispatched: dict[str, DispatchRecord] = {}
        self._dispatch_hashes: set[str] = set()

    def enqueue(self, record: DispatchRecord) -> DispatchRecord | None:
        """Enqueue a dispatch record. Returns None if duplicate."""
        if record.dispatch_hash in self._dispatch_hashes:
            return None
        if record.packet_id in self._dispatched:
            return None

        record.status = DispatchStatus.QUEUED
        self._dispatched[record.packet_id] = record
        self._dispatch_hashes.add(record.dispatch_hash)

        path = self._outbox / f"{record.dispatch_id}.json"
        path.write_text(json.dumps(record.to_dict(), indent=2))
        return record

    def claim(self, packet_id: str, worker_id: str, session_id: str = "") -> bool:
        """Mark a queued packet as claimed by a worker."""
        record = self._dispatched.get(packet_id)
        if not record or record.status != DispatchStatus.QUEUED:
            return False
        record.status = DispatchStatus.CLAIMED
        record.claimed_at = datetime.now(timezone.utc).isoformat()
        record.worker_id = worker_id
        record.session_id = session_id
        return True

    def start_processing(self, packet_id: str) -> bool:
        """Mark a claimed packet as processing."""
        record = self._dispatched.get(packet_id)
        if not record or record.status != DispatchStatus.CLAIMED:
            return False
        record.status = DispatchStatus.PROCESSING
        return True

    def complete(self, packet_id: str) -> bool:
        """Mark a packet as completed and archive it."""
        record = self._dispatched.get(packet_id)
        if not record or record.status not in {DispatchStatus.PROCESSING, DispatchStatus.CLAIMED}:
            return False
        record.status = DispatchStatus.COMPLETED
        record.completed_at = datetime.now(timezone.utc).isoformat()

        archive_path = self._archive / f"{record.dispatch_id}.json"
        archive_path.write_text(json.dumps(record.to_dict(), indent=2))
        return True

    def fail(self, packet_id: str, reason: str = "") -> bool:
        """Mark a packet as failed."""
        record = self._dispatched.get(packet_id)
        if not record:
            return False
        record.status = DispatchStatus.FAILED
        record.completed_at = datetime.now(timezone.utc).isoformat()
        if reason:
            record.notes.append(f"failure: {reason}")
        return True

    def get_queued(self) -> list[DispatchRecord]:
        return [r for r in self._dispatched.values() if r.status == DispatchStatus.QUEUED]

    def get_record(self, packet_id: str) -> DispatchRecord | None:
        return self._dispatched.get(packet_id)

    def get_all(self) -> list[DispatchRecord]:
        return list(self._dispatched.values())

    @property
    def queue_depth(self) -> int:
        return len(self.get_queued())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": len(self._dispatched),
            "queued": self.queue_depth,
            "records": {pid: r.to_dict() for pid, r in self._dispatched.items()},
        }
