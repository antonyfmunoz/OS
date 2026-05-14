"""Memory Conflict Governance v1.

Handles conflicts detected by the reconciliation engine.
Surfaces conflicts for human review. Does NOT auto-resolve.

Conflicts are persisted, queryable, and linked to their
reconciliation receipts.

UMH substrate subsystem. Phase 96.8BM.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .memory_identity_v1 import deterministic_id


class ConflictResolution(str, Enum):
    PENDING = "pending"
    KEEP_EXISTING = "keep_existing"
    ACCEPT_NEW = "accept_new"
    MANUAL_MERGE = "manual_merge"
    DISMISSED = "dismissed"


@dataclass
class ConflictRecord:
    """A detected conflict between a candidate and an existing memory."""

    conflict_id: str
    candidate_id: str
    existing_memory_id: str
    candidate_content: str
    existing_content: str
    candidate_label: str
    existing_label: str
    primitive_type: str
    source_document_id: str
    reconciliation_receipt_id: str
    resolution: ConflictResolution = ConflictResolution.PENDING
    resolution_reason: str = ""
    resolved_by: str = ""
    detected_at: str = ""
    resolved_at: str = ""

    def __post_init__(self) -> None:
        if not self.detected_at:
            self.detected_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "candidate_id": self.candidate_id,
            "existing_memory_id": self.existing_memory_id,
            "candidate_content": self.candidate_content,
            "existing_content": self.existing_content,
            "candidate_label": self.candidate_label,
            "existing_label": self.existing_label,
            "primitive_type": self.primitive_type,
            "source_document_id": self.source_document_id,
            "reconciliation_receipt_id": self.reconciliation_receipt_id,
            "resolution": self.resolution.value,
            "resolution_reason": self.resolution_reason,
            "resolved_by": self.resolved_by,
            "detected_at": self.detected_at,
            "resolved_at": self.resolved_at,
        }


class ConflictGovernance:
    """Persists and manages memory conflict records."""

    def __init__(self, store_dir: str | Path = "data/runtime/memory_conflicts"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.conflicts_path = self.store_dir / "conflicts.jsonl"

    def record_conflict(
        self,
        candidate: dict[str, Any],
        existing_memory: dict[str, Any],
        receipt_id: str,
    ) -> ConflictRecord:
        """Record a conflict for human review."""
        conflict_id = deterministic_id(
            "conflict",
            f"{candidate.get('candidate_id', '')}:{existing_memory.get('memory_id', '')}",
        )

        record = ConflictRecord(
            conflict_id=conflict_id,
            candidate_id=candidate.get("candidate_id", ""),
            existing_memory_id=existing_memory.get("memory_id", ""),
            candidate_content=candidate.get("content", ""),
            existing_content=existing_memory.get("content", ""),
            candidate_label=candidate.get("label", ""),
            existing_label=existing_memory.get("label", ""),
            primitive_type=candidate.get("primitive_type", ""),
            source_document_id=candidate.get("source_document_id", ""),
            reconciliation_receipt_id=receipt_id,
        )

        with open(self.conflicts_path, "a") as f:
            f.write(json.dumps(record.to_dict(), separators=(",", ":")) + "\n")

        return record

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: ConflictResolution,
        reason: str,
        resolved_by: str = "human",
    ) -> ConflictRecord | None:
        """Resolve a pending conflict."""
        records = self._load_all()
        updated = None

        for r in records:
            if r["conflict_id"] == conflict_id:
                r["resolution"] = resolution.value
                r["resolution_reason"] = reason
                r["resolved_by"] = resolved_by
                r["resolved_at"] = datetime.now(timezone.utc).isoformat()
                updated = r
                break

        if updated:
            self._rewrite(records)
            return ConflictRecord(
                **{
                    k: (ConflictResolution(v) if k == "resolution" else v)
                    for k, v in updated.items()
                }
            )
        return None

    def get_pending(self) -> list[dict[str, Any]]:
        """Return all unresolved conflicts."""
        return [
            r for r in self._load_all() if r.get("resolution") == ConflictResolution.PENDING.value
        ]

    def get_all(self) -> list[dict[str, Any]]:
        return self._load_all()

    def _load_all(self) -> list[dict[str, Any]]:
        if not self.conflicts_path.exists():
            return []
        records = []
        with open(self.conflicts_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def _rewrite(self, records: list[dict[str, Any]]) -> None:
        with open(self.conflicts_path, "w") as f:
            for r in records:
                f.write(json.dumps(r, separators=(",", ":")) + "\n")
