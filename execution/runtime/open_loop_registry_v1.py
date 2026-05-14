"""Open Loop Registry v1.

Tracks unfinished operations, unresolved decisions, pending governance,
failed executions, interrupted workflows, and deferred actions.

Deterministic. Append-only ledger with resolution tracking.

UMH substrate subsystem. Phase 96.8BN.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .runtime_cognition_contracts_v1 import _deterministic_id


class LoopStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    STALE = "stale"
    SUPERSEDED = "superseded"
    DISMISSED = "dismissed"


class LoopType(str, Enum):
    UNFINISHED_OPERATION = "unfinished_operation"
    UNRESOLVED_DECISION = "unresolved_decision"
    PENDING_GOVERNANCE = "pending_governance"
    FAILED_EXECUTION = "failed_execution"
    INTERRUPTED_WORKFLOW = "interrupted_workflow"
    UNRESOLVED_CONTRADICTION = "unresolved_contradiction"
    DEFERRED_ACTION = "deferred_action"


@dataclass
class OpenLoop:
    """A tracked unresolved item in the operational substrate."""

    loop_id: str
    loop_type: LoopType
    description: str
    source_event_id: str = ""
    source_trace_id: str = ""
    correlation_id: str = ""
    session_id: str = ""
    status: LoopStatus = LoopStatus.OPEN
    priority: int = 0
    resolution: str = ""
    resolved_by: str = ""
    opened_at: str = ""
    resolved_at: str = ""
    stale_after_hours: int = 24

    def __post_init__(self) -> None:
        if not self.opened_at:
            self.opened_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "loop_id": self.loop_id,
            "loop_type": self.loop_type.value,
            "description": self.description,
            "source_event_id": self.source_event_id,
            "source_trace_id": self.source_trace_id,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "priority": self.priority,
            "resolution": self.resolution,
            "resolved_by": self.resolved_by,
            "opened_at": self.opened_at,
            "resolved_at": self.resolved_at,
            "stale_after_hours": self.stale_after_hours,
        }


class OpenLoopRegistry:
    """Persists and manages open loops."""

    def __init__(self, store_dir: str | Path = "data/runtime/open_loop_registry"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.store_dir / "open_loops.jsonl"
        self.index_path = self.store_dir / "loop_index.json"

    def register_loop(self, loop: OpenLoop) -> OpenLoop:
        """Register a new open loop."""
        with open(self.ledger_path, "a") as f:
            f.write(json.dumps(loop.to_dict(), separators=(",", ":")) + "\n")
        self._update_index(loop)
        return loop

    def create_loop(
        self,
        loop_type: LoopType,
        description: str,
        source_event_id: str = "",
        source_trace_id: str = "",
        correlation_id: str = "",
        session_id: str = "",
        priority: int = 0,
    ) -> OpenLoop:
        """Create and register a new open loop."""
        loop_id = _deterministic_id(
            "loop", f"{loop_type.value}:{description[:100]}:{source_event_id}"
        )
        loop = OpenLoop(
            loop_id=loop_id,
            loop_type=loop_type,
            description=description,
            source_event_id=source_event_id,
            source_trace_id=source_trace_id,
            correlation_id=correlation_id,
            session_id=session_id,
            priority=priority,
        )
        return self.register_loop(loop)

    def resolve_loop(self, loop_id: str, resolution: str, resolved_by: str = "system") -> bool:
        """Mark an open loop as resolved."""
        records = self._load_all()
        found = False
        for r in records:
            if r["loop_id"] == loop_id and r["status"] == LoopStatus.OPEN.value:
                r["status"] = LoopStatus.RESOLVED.value
                r["resolution"] = resolution
                r["resolved_by"] = resolved_by
                r["resolved_at"] = datetime.now(timezone.utc).isoformat()
                found = True
                break
        if found:
            self._rewrite(records)
            self._rebuild_index(records)
        return found

    def mark_stale(self, loop_id: str) -> bool:
        """Mark an open loop as stale."""
        records = self._load_all()
        found = False
        for r in records:
            if r["loop_id"] == loop_id and r["status"] == LoopStatus.OPEN.value:
                r["status"] = LoopStatus.STALE.value
                r["resolved_at"] = datetime.now(timezone.utc).isoformat()
                found = True
                break
        if found:
            self._rewrite(records)
            self._rebuild_index(records)
        return found

    def get_open_loops(self) -> list[dict[str, Any]]:
        """Return all open (unresolved) loops."""
        return [r for r in self._load_all() if r.get("status") == LoopStatus.OPEN.value]

    def get_all_loops(self) -> list[dict[str, Any]]:
        return self._load_all()

    def get_loop_by_id(self, loop_id: str) -> dict[str, Any] | None:
        for r in self._load_all():
            if r["loop_id"] == loop_id:
                return r
        return None

    def get_stats(self) -> dict[str, Any]:
        records = self._load_all()
        open_count = sum(1 for r in records if r["status"] == LoopStatus.OPEN.value)
        resolved_count = sum(1 for r in records if r["status"] == LoopStatus.RESOLVED.value)
        stale_count = sum(1 for r in records if r["status"] == LoopStatus.STALE.value)
        return {
            "total": len(records),
            "open": open_count,
            "resolved": resolved_count,
            "stale": stale_count,
        }

    def _load_all(self) -> list[dict[str, Any]]:
        if not self.ledger_path.exists():
            return []
        records = []
        with open(self.ledger_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def _rewrite(self, records: list[dict[str, Any]]) -> None:
        with open(self.ledger_path, "w") as f:
            for r in records:
                f.write(json.dumps(r, separators=(",", ":")) + "\n")

    def _update_index(self, loop: OpenLoop) -> None:
        index = {}
        if self.index_path.exists():
            with open(self.index_path) as f:
                index = json.load(f)
        if "open" not in index:
            index["open"] = []
        if loop.status == LoopStatus.OPEN:
            index["open"].append(loop.loop_id)
        index["total"] = index.get("total", 0) + 1
        index["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(self.index_path, "w") as f:
            json.dump(index, f, indent=2)

    def _rebuild_index(self, records: list[dict[str, Any]]) -> None:
        open_ids = [r["loop_id"] for r in records if r["status"] == LoopStatus.OPEN.value]
        index = {
            "open": open_ids,
            "total": len(records),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        with open(self.index_path, "w") as f:
            json.dump(index, f, indent=2)
