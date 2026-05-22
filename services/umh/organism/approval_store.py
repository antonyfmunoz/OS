"""Approval store — JSONL persistence for governance-blocked signals."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class ApprovalStore:
    def __init__(self, store_dir: str | Path = "data/umh/organism") -> None:
        self._dir = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._approvals = self._dir / "approvals.jsonl"

    def _append(self, record: dict[str, Any]) -> None:
        with open(self._approvals, "a") as f:
            f.write(json.dumps(record, default=str, separators=(",", ":")) + "\n")

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
        with open(self._approvals, "w") as f:
            for e in entries:
                f.write(json.dumps(e, default=str, separators=(",", ":")) + "\n")

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
        return target

    def pending_count(self) -> int:
        return len([a for a in self._read_all() if a.get("status") == "pending"])
