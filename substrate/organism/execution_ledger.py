"""Execution Ledger — canonical record of every execution request and outcome.

JSONL persistence at data/runtime/execution_ledger.jsonl.
Every execution request, executor selected, target, start/end, status, proof_id, error.
API: GET /execution/ledger — paginated, filterable.

C28 Phase 3.3 — source of truth for execution history.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from substrate.state.runtime_paths import runtime_state_path

logger = logging.getLogger(__name__)

_LEDGER_PATH = runtime_state_path("organism", "execution_ledger.jsonl", create_parent=False)


@dataclass
class LedgerEntry:
    entry_id: str = field(default_factory=lambda: f"led-{uuid4().hex[:12]}")
    request_id: str = ""
    executor_type: str = ""
    target_machine: str = ""
    repo: str = ""
    cwd: str = ""
    description: str = ""
    status: str = "created"
    proof_id: str = ""
    error: str = ""
    started_at: float = 0.0
    ended_at: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LedgerEntry:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})

    @property
    def duration_seconds(self) -> float:
        if self.started_at and self.ended_at:
            return round(self.ended_at - self.started_at, 2)
        return 0.0


class ExecutionLedger:
    """Append-only execution ledger with JSONL persistence."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _LEDGER_PATH
        self._entries: list[LedgerEntry] = []
        self._by_id: dict[str, LedgerEntry] = {}
        self._by_request: dict[str, LedgerEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            for line in self._path.read_text().strip().splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    entry = LedgerEntry.from_dict(row)
                    self._entries.append(entry)
                    self._by_id[entry.entry_id] = entry
                    if entry.request_id:
                        self._by_request[entry.request_id] = entry
                except (json.JSONDecodeError, TypeError):
                    continue
            logger.info("Loaded %d ledger entries from %s", len(self._entries), self._path)
        except Exception as exc:
            logger.warning("Failed to load execution ledger: %s", exc)

    def _append(self, entry: LedgerEntry) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a") as f:
                f.write(json.dumps(entry.to_dict(), default=str) + "\n")
        except Exception as exc:
            logger.warning("Failed to persist ledger entry: %s", exc)

    def record(
        self,
        request_id: str = "",
        executor_type: str = "",
        target_machine: str = "",
        repo: str = "",
        cwd: str = "",
        description: str = "",
        status: str = "created",
    ) -> LedgerEntry:
        entry = LedgerEntry(
            request_id=request_id,
            executor_type=executor_type,
            target_machine=target_machine,
            repo=repo,
            cwd=cwd,
            description=description,
            status=status,
            started_at=time.time(),
        )
        self._entries.append(entry)
        self._by_id[entry.entry_id] = entry
        if request_id:
            self._by_request[request_id] = entry
        self._append(entry)
        return entry

    def update_status(
        self,
        entry_id: str,
        status: str,
        proof_id: str = "",
        error: str = "",
    ) -> LedgerEntry | None:
        entry = self._by_id.get(entry_id)
        if entry is None:
            return None
        entry.status = status
        if proof_id:
            entry.proof_id = proof_id
        if error:
            entry.error = error
        if status in ("completed", "failed", "cancelled"):
            entry.ended_at = time.time()
        self._append(entry)
        return entry

    def get(self, entry_id: str) -> LedgerEntry | None:
        return self._by_id.get(entry_id)

    def for_request(self, request_id: str) -> LedgerEntry | None:
        return self._by_request.get(request_id)

    def query(
        self,
        status: str = "",
        executor_type: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> list[LedgerEntry]:
        filtered = self._entries
        if status:
            filtered = [e for e in filtered if e.status == status]
        if executor_type:
            filtered = [e for e in filtered if e.executor_type == executor_type]
        filtered.sort(key=lambda e: e.created_at, reverse=True)
        return filtered[offset : offset + limit]

    def summary(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        by_executor: dict[str, int] = {}
        for entry in self._entries:
            by_status[entry.status] = by_status.get(entry.status, 0) + 1
            if entry.executor_type:
                by_executor[entry.executor_type] = by_executor.get(entry.executor_type, 0) + 1
        return {
            "total": len(self._entries),
            "by_status": by_status,
            "by_executor": by_executor,
        }


_ledger_instance: ExecutionLedger | None = None


def get_execution_ledger() -> ExecutionLedger:
    global _ledger_instance
    if _ledger_instance is None:
        _ledger_instance = ExecutionLedger()
    return _ledger_instance
