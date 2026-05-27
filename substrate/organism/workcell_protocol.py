"""WorkcellV2 — durable inbox/outbox execution cells.

A workcell is a persistent execution boundary that:
  1. Receives work via filesystem inbox (crash-safe)
  2. Executes via a bound RuntimeAdapter
  3. Writes results to outbox
  4. Maintains heartbeat for liveness detection
  5. Supports checkpoint/resume for long-running work
  6. Handles crash recovery via inflight markers

Three-phase message lifecycle (adapted from cortextOS):
  inbox/ → inflight/ → processed/

Each phase transition is an atomic file rename on POSIX,
giving exactly-once delivery semantics without a database.

UMH substrate subsystem.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from substrate.organism.runtime_graph import (
    RuntimeAdapter,
    RuntimeCapability,
    RuntimeResult,
)

logger = logging.getLogger(__name__)

_INFLIGHT_STALE_S = 300.0
_HEARTBEAT_INTERVAL_S = 30.0


class WorkcellStatus(str, Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    CHECKPOINTED = "checkpointed"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


class WorkcellRole(str, Enum):
    RESEARCHER = "researcher"
    BUILDER = "builder"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"
    COORDINATOR = "coordinator"


@dataclass
class WorkcellMessage:
    """A message in the workcell inbox/outbox."""

    id: str = ""
    sender: str = ""
    intent: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"msg-{uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    @property
    def filename(self) -> str:
        ts_ms = int(self.created_at * 1000)
        return f"{self.priority:02d}-{ts_ms}-from-{self.sender}-{self.id}.json"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sender": self.sender,
            "intent": self.intent,
            "payload": self.payload,
            "priority": self.priority,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkcellMessage:
        return cls(
            id=data.get("id", ""),
            sender=data.get("sender", ""),
            intent=data.get("intent", ""),
            payload=data.get("payload", {}),
            priority=data.get("priority", 5),
            created_at=data.get("created_at", 0.0),
        )


@dataclass
class WorkcellCheckpoint:
    """Checkpoint for resumable long-running work."""

    workcell_id: str
    work_unit_id: str
    progress: float = 0.0
    partial_result: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "workcell_id": self.workcell_id,
            "work_unit_id": self.work_unit_id,
            "progress": self.progress,
            "partial_result": self.partial_result[:500],
            "context": self.context,
            "created_at": self.created_at,
        }


class Workcell:
    """A persistent, durable execution cell.

    Each workcell has:
      - An inbox directory for incoming work messages
      - An inflight directory for work being processed
      - A processed directory for completed work
      - An outbox directory for results
      - A heartbeat file for liveness detection
      - A checkpoint file for resumable work
    """

    def __init__(
        self,
        workcell_id: str,
        role: WorkcellRole,
        adapter: RuntimeAdapter | None = None,
        base_dir: str | Path = "data/umh/workcells",
    ) -> None:
        self.workcell_id = workcell_id
        self.role = role
        self._adapter = adapter
        self._status = WorkcellStatus.IDLE
        self._generation: int = 0
        self._messages_processed: int = 0

        self._base = Path(base_dir) / workcell_id
        self._inbox = self._base / "inbox"
        self._inflight = self._base / "inflight"
        self._processed = self._base / "processed"
        self._outbox = self._base / "outbox"
        self._heartbeat_path = self._base / "heartbeat.json"
        self._checkpoint_path = self._base / "checkpoint.json"
        self._state_path = self._base / "state.json"

        for d in [self._inbox, self._inflight, self._processed, self._outbox]:
            d.mkdir(parents=True, exist_ok=True)

        self._last_heartbeat: float = 0.0

    def bind_adapter(self, adapter: RuntimeAdapter) -> None:
        self._adapter = adapter

    @property
    def status(self) -> WorkcellStatus:
        return self._status

    def send_message(self, msg: WorkcellMessage) -> Path:
        """Write a message to this workcell's inbox (atomic)."""
        target = self._inbox / msg.filename
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(msg.to_dict(), indent=2))
        tmp.rename(target)
        return target

    def receive_messages(self, limit: int = 10) -> list[WorkcellMessage]:
        """Read messages from inbox, sorted by priority (lowest number = highest priority)."""
        if not self._inbox.exists():
            return []

        files = sorted(self._inbox.glob("*.json"))[:limit]
        messages: list[WorkcellMessage] = []

        for f in files:
            try:
                data = json.loads(f.read_text())
                messages.append(WorkcellMessage.from_dict(data))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("failed to read inbox message %s: %s", f.name, e)

        return messages

    def claim_message(self, msg: WorkcellMessage) -> bool:
        """Move message from inbox to inflight (atomic rename)."""
        inbox_path = self._inbox / msg.filename
        inflight_path = self._inflight / msg.filename

        if not inbox_path.exists():
            return False

        try:
            inbox_path.rename(inflight_path)
            return True
        except OSError:
            return False

    def complete_message(self, msg: WorkcellMessage, result: dict[str, Any] | None = None) -> None:
        """Move message from inflight to processed and write result to outbox."""
        inflight_path = self._inflight / msg.filename
        processed_path = self._processed / msg.filename

        if inflight_path.exists():
            inflight_path.rename(processed_path)

        if result:
            result_msg = WorkcellMessage(
                sender=self.workcell_id,
                intent="result",
                payload={
                    "original_message_id": msg.id,
                    "result": result,
                },
                priority=msg.priority,
            )
            outbox_path = self._outbox / result_msg.filename
            tmp = outbox_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(result_msg.to_dict(), indent=2))
            tmp.rename(outbox_path)

        self._messages_processed += 1

    def recover_stale_inflight(self) -> int:
        """Move stale inflight messages back to inbox for reprocessing."""
        if not self._inflight.exists():
            return 0

        now = time.time()
        recovered = 0

        for f in self._inflight.glob("*.json"):
            try:
                age = now - f.stat().st_mtime
                if age > _INFLIGHT_STALE_S:
                    inbox_path = self._inbox / f.name
                    f.rename(inbox_path)
                    recovered += 1
                    logger.info(
                        "recovered stale inflight message: %s (%.0fs old)",
                        f.name,
                        age,
                    )
            except OSError:
                pass

        return recovered

    def process_next(self) -> dict[str, Any] | None:
        """Process the next message in the inbox."""
        if self._adapter is None:
            return {"error": "no adapter bound"}

        self.recover_stale_inflight()
        messages = self.receive_messages(limit=1)
        if not messages:
            return None

        msg = messages[0]
        if not self.claim_message(msg):
            return {"error": f"failed to claim message {msg.id}"}

        self._status = WorkcellStatus.PROCESSING
        self._generation += 1
        self.write_heartbeat()

        prompt = msg.payload.get("task", msg.payload.get("prompt", msg.intent))

        try:
            result = self._adapter.execute(prompt)

            if result is not None:
                output = {
                    "output": result.output,
                    "runtime_id": result.runtime_id,
                    "latency_ms": result.latency_ms,
                }
                self.complete_message(msg, output)
                self._status = WorkcellStatus.IDLE
                return {
                    "message_id": msg.id,
                    "status": "completed",
                    **output,
                }

            self.complete_message(msg, {"error": "adapter returned empty"})
            self._status = WorkcellStatus.IDLE
            return {"message_id": msg.id, "status": "empty_result"}

        except Exception as e:
            logger.warning("workcell %s execution failed: %s", self.workcell_id, e)
            self._status = WorkcellStatus.FAILED
            self.complete_message(msg, {"error": str(e)})
            return {"message_id": msg.id, "status": "failed", "error": str(e)}

    def write_heartbeat(self) -> None:
        """Write heartbeat for liveness detection."""
        now = time.time()
        self._last_heartbeat = now
        heartbeat = {
            "workcell_id": self.workcell_id,
            "role": self.role.value,
            "status": self._status.value,
            "generation": self._generation,
            "messages_processed": self._messages_processed,
            "timestamp": now,
            "inbox_depth": len(list(self._inbox.glob("*.json"))) if self._inbox.exists() else 0,
        }
        tmp = self._heartbeat_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(heartbeat, indent=2))
        tmp.rename(self._heartbeat_path)

    def read_heartbeat(self) -> dict[str, Any] | None:
        if not self._heartbeat_path.exists():
            return None
        try:
            return json.loads(self._heartbeat_path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def is_alive(self) -> bool:
        hb = self.read_heartbeat()
        if not hb:
            return False
        age = time.time() - hb.get("timestamp", 0)
        return age < _HEARTBEAT_INTERVAL_S * 3

    def save_checkpoint(self, checkpoint: WorkcellCheckpoint) -> None:
        """Save checkpoint for resumable long-running work."""
        self._status = WorkcellStatus.CHECKPOINTED
        tmp = self._checkpoint_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(checkpoint.to_dict(), indent=2))
        tmp.rename(self._checkpoint_path)

    def load_checkpoint(self) -> WorkcellCheckpoint | None:
        if not self._checkpoint_path.exists():
            return None
        try:
            data = json.loads(self._checkpoint_path.read_text())
            return WorkcellCheckpoint(**data)
        except (json.JSONDecodeError, OSError, TypeError):
            return None

    def clear_checkpoint(self) -> None:
        if self._checkpoint_path.exists():
            self._checkpoint_path.unlink()

    def shutdown(self) -> None:
        self._status = WorkcellStatus.SHUTDOWN
        self.write_heartbeat()

    def collect_outbox(self) -> list[WorkcellMessage]:
        """Read and clear all messages from the outbox."""
        if not self._outbox.exists():
            return []

        results: list[WorkcellMessage] = []
        for f in sorted(self._outbox.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                results.append(WorkcellMessage.from_dict(data))
                f.unlink()
            except (json.JSONDecodeError, OSError):
                pass

        return results

    def to_dict(self) -> dict[str, Any]:
        return {
            "workcell_id": self.workcell_id,
            "role": self.role.value,
            "status": self._status.value,
            "generation": self._generation,
            "messages_processed": self._messages_processed,
            "adapter": self._adapter.runtime_id if self._adapter else None,
            "alive": self.is_alive(),
            "has_checkpoint": self._checkpoint_path.exists(),
            "inbox_depth": len(list(self._inbox.glob("*.json"))) if self._inbox.exists() else 0,
        }
