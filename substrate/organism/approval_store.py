"""Approval store — JSONL persistence for governance-blocked signals."""

from __future__ import annotations

import fcntl
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from substrate.sockets.notification import alert_approval
from substrate.state.runtime_paths import runtime_state_dir

logger = logging.getLogger(__name__)


class ApprovalStore:
    def __init__(self, store_dir: str | Path | None = None) -> None:
        self._dir = Path(store_dir) if store_dir else runtime_state_dir("organism")
        self._dir.mkdir(parents=True, exist_ok=True)
        self._approvals = self._dir / "approvals.jsonl"

    @property
    def _lock_path(self) -> Path:
        return self._approvals.with_suffix(".lock")

    def _append(self, record: dict[str, Any]) -> None:
        lock_path = str(self._lock_path)
        with open(lock_path, "w") as lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            try:
                with open(self._approvals, "a") as f:
                    f.write(json.dumps(record, default=str, separators=(",", ":")) + "\n")
            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)

    def _read_all(self) -> list[dict[str, Any]]:
        if not self._approvals.exists():
            return []
        entries: list[dict[str, Any]] = []
        with open(self._approvals) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def _rewrite_all(self, entries: list[dict[str, Any]]) -> None:
        lock_path = str(self._lock_path)
        tmp_path = str(self._approvals) + ".tmp"
        with open(lock_path, "w") as lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            try:
                with open(tmp_path, "w") as f:
                    for e in entries:
                        f.write(json.dumps(e, default=str, separators=(",", ":")) + "\n")
                os.replace(tmp_path, str(self._approvals))
            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)

    def create_approval(
        self,
        *,
        title: str,
        description: str,
        agent: str = "system",
        risk_level: str = "medium",
        trace_id: str | None = None,
        signal_content: str = "",
        governance_rationale: str = "",
    ) -> dict[str, Any]:
        record = {
            "id": str(uuid4()),
            "title": title[:200],
            "description": description[:500],
            "agent": agent,
            "risk_level": risk_level,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "decided_at": None,
            "decided_by": None,
            "trace_id": trace_id,
            "signal_content": signal_content[:500],
            "governance_rationale": governance_rationale,
        }
        self._append(record)
        try:
            alert_approval({"event": "created", **record})
        except Exception as exc:
            logger.warning("approval alert failed: %s", exc)
        return record

    def list_approvals(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        all_a = self._read_all()
        if status:
            all_a = [a for a in all_a if a.get("status") == status]
        return all_a[-limit:]

    def decide(
        self, approval_id: str, decision: str, decided_by: str = "operator"
    ) -> dict[str, Any] | None:
        entries = self._read_all()
        target = None
        for e in entries:
            if e.get("id") == approval_id:
                e["status"] = decision
                e["decided_at"] = datetime.now(timezone.utc).isoformat()
                e["decided_by"] = decided_by
                target = e
                break
        if target is None:
            return None
        self._rewrite_all(entries)
        try:
            alert_approval({"event": "decided", **target})
        except Exception as exc:
            logger.warning("approval decision alert failed: %s", exc)
        return target

    def list_pending(self) -> list[dict[str, Any]]:
        """All pending approval records. Used by the canonical ApprovalAuthority
        projection (WP-P1-007) to surface this store's approvals in the unified
        pending view."""
        return [a for a in self._read_all() if a.get("status") == "pending"]

    def pending_count(self) -> int:
        return len(self.list_pending())
