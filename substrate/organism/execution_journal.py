"""ExecutionJournal — append-only execution ledger for all organism mutations.

Every ActionEnvelope lifecycle transition is recorded as a JournalEntry.
This provides:
  - full audit trail
  - replay capability
  - debugging history
  - reliability statistics
  - learning foundation

Persistence: JSONL file with rotation at 10 MB.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class JournalPhase(str, Enum):
    PROPOSED = "proposed"
    GOVERNANCE_CHECK = "governance_check"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    VERIFICATION_STARTED = "verification_started"
    VERIFICATION_PASSED = "verification_passed"
    VERIFICATION_FAILED = "verification_failed"
    ROLLBACK_STARTED = "rollback_started"
    ROLLBACK_COMPLETED = "rollback_completed"
    ROLLBACK_FAILED = "rollback_failed"
    RETRY = "retry"
    ADAPTATION_TRIGGERED = "adaptation_triggered"


@dataclass(frozen=True)
class JournalEntry:
    envelope_id: str
    phase: JournalPhase
    source: str
    details: dict[str, Any]
    entry_id: str = field(default_factory=lambda: uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    correlation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "envelope_id": self.envelope_id,
            "phase": self.phase.value,
            "source": self.source,
            "details": self.details,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }


_MAX_ENTRIES = 10_000
_MAX_FILE_BYTES = 10 * 1024 * 1024


class ExecutionJournal:
    """Append-only execution ledger.

    Thread-safe. Persists entries to JSONL. Supports replay
    and filtered queries by envelope_id or phase.
    """

    def __init__(self, persist_path: str | None = None) -> None:
        self._entries: deque[JournalEntry] = deque(maxlen=_MAX_ENTRIES)
        self._lock = threading.Lock()
        self._persist_path = Path(persist_path) if persist_path else None
        if self._persist_path is not None:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._total_entries: int = 0

    def record(
        self,
        envelope_id: str,
        phase: JournalPhase,
        source: str,
        details: dict[str, Any] | None = None,
        correlation_id: str = "",
    ) -> JournalEntry:
        entry = JournalEntry(
            envelope_id=envelope_id,
            phase=phase,
            source=source,
            details=details or {},
            correlation_id=correlation_id,
        )
        with self._lock:
            self._entries.append(entry)
            self._total_entries += 1
        self._persist(entry)
        return entry

    def entries_for(self, envelope_id: str) -> list[JournalEntry]:
        with self._lock:
            return [e for e in self._entries if e.envelope_id == envelope_id]

    def entries_by_phase(self, phase: JournalPhase, limit: int = 50) -> list[JournalEntry]:
        with self._lock:
            matching = [e for e in self._entries if e.phase == phase]
        return matching[-limit:]

    def recent(self, limit: int = 50) -> list[JournalEntry]:
        with self._lock:
            entries = list(self._entries)
        return entries[-limit:]

    def replay(
        self,
        since: float | None = None,
        envelope_id: str | None = None,
        phases: set[JournalPhase] | None = None,
    ) -> list[JournalEntry]:
        with self._lock:
            entries = list(self._entries)

        result = []
        for entry in entries:
            if since is not None and entry.timestamp <= since:
                continue
            if envelope_id is not None and entry.envelope_id != envelope_id:
                continue
            if phases is not None and entry.phase not in phases:
                continue
            result.append(entry)
        return result

    def execution_lifecycle(self, envelope_id: str) -> list[dict[str, Any]]:
        entries = self.entries_for(envelope_id)
        return [e.to_dict() for e in entries]

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            entries = list(self._entries)

        by_phase: dict[str, int] = {}
        for e in entries:
            phase = e.phase.value
            by_phase[phase] = by_phase.get(phase, 0) + 1

        completed = by_phase.get(JournalPhase.EXECUTION_COMPLETED.value, 0)
        failed = by_phase.get(JournalPhase.EXECUTION_FAILED.value, 0)
        total_executions = completed + failed

        return {
            "total_entries": self._total_entries,
            "in_memory": len(entries),
            "by_phase": by_phase,
            "success_rate": round(completed / max(total_executions, 1), 4),
            "total_rollbacks": by_phase.get(JournalPhase.ROLLBACK_COMPLETED.value, 0),
            "total_retries": by_phase.get(JournalPhase.RETRY.value, 0),
        }

    def to_dict(self) -> dict[str, Any]:
        stats = self.statistics()
        recent = [e.to_dict() for e in self.recent(10)]
        return {
            **stats,
            "recent": recent,
        }

    def _persist(self, entry: JournalEntry) -> None:
        if self._persist_path is None:
            return
        try:
            self._rotate_if_needed()
            with open(self._persist_path, "a") as f:
                f.write(json.dumps(entry.to_dict(), default=str) + "\n")
        except Exception as exc:
            logger.warning("journal persist failed: %s", exc)

    def _rotate_if_needed(self) -> None:
        if self._persist_path is None or not self._persist_path.exists():
            return
        try:
            size = self._persist_path.stat().st_size
        except OSError:
            return
        if size < _MAX_FILE_BYTES:
            return
        rotated = self._persist_path.with_suffix(".jsonl.old")
        try:
            if rotated.exists():
                rotated.unlink()
            self._persist_path.rename(rotated)
            logger.info("journal rotated: %s", self._persist_path)
        except OSError as exc:
            logger.warning("journal rotation failed: %s", exc)

    def recover(self) -> int:
        if self._persist_path is None or not self._persist_path.exists():
            return 0
        recovered = 0
        try:
            with open(self._persist_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entry = JournalEntry(
                            envelope_id=data["envelope_id"],
                            phase=JournalPhase(data["phase"]),
                            source=data["source"],
                            details=data.get("details", {}),
                            entry_id=data.get("entry_id", uuid4().hex[:12]),
                            timestamp=data.get("timestamp", 0.0),
                            correlation_id=data.get("correlation_id", ""),
                        )
                        with self._lock:
                            self._entries.append(entry)
                        recovered += 1
                    except (KeyError, ValueError) as exc:
                        logger.debug("skipping malformed journal line: %s", exc)
        except Exception as exc:
            logger.warning("journal recovery failed: %s", exc)
        if recovered > 0:
            logger.info("recovered %d journal entries from %s", recovered, self._persist_path)
        return recovered
