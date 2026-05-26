"""Canonical Memory Store v1 — append-only, replay-safe, queryable memory persistence.

Stores promoted canonical and instance memories with full provenance lineage.
JSONL-backed: one record per line, append-only, deterministic IDs.

UMH substrate subsystem.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class PromotionDecision(str, Enum):
    PROMOTED = "promoted"
    REJECTED = "rejected"
    DEFERRED = "deferred"


@dataclass
class PromotionReceipt:
    """Governance record for a promotion decision."""

    receipt_id: str
    candidate_id: str
    decision: PromotionDecision
    reason: str
    confidence: float
    promoter: str
    timestamp: str = ""
    rollback_reference: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "candidate_id": self.candidate_id,
            "decision": self.decision.value,
            "reason": self.reason,
            "confidence": self.confidence,
            "promoter": self.promoter,
            "timestamp": self.timestamp,
            "rollback_reference": self.rollback_reference,
        }


# NOTE: The canonical MemoryEntry is a Pydantic model in substrate.types
# (generic: memory_type enum, content, confidence, tags).
# This is the store-scoped version with provenance lineage and promotion tracking.
from substrate.types import MemoryEntry as CanonicalMemoryEntry  # noqa: F401


@dataclass
class MemoryEntry:
    """A single entry in the canonical memory store."""

    memory_id: str
    candidate_id: str
    memory_type: str  # canonical or instance
    primitive_type: str
    label: str
    content: str
    confidence: float
    source_document_id: str
    source_content_hash: str
    source_decomposition_id: str
    promotion_receipt_id: str
    provenance: dict[str, Any] = field(default_factory=dict)
    lineage: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "candidate_id": self.candidate_id,
            "memory_type": self.memory_type,
            "primitive_type": self.primitive_type,
            "label": self.label,
            "content": self.content,
            "confidence": self.confidence,
            "source_document_id": self.source_document_id,
            "source_content_hash": self.source_content_hash,
            "source_decomposition_id": self.source_decomposition_id,
            "promotion_receipt_id": self.promotion_receipt_id,
            "provenance": self.provenance,
            "lineage": self.lineage,
            "timestamp": self.timestamp,
        }


def _deterministic_id(namespace: str, content: str) -> str:
    h = hashlib.sha256(f"{namespace}:{content}".encode("utf-8")).hexdigest()[:16]
    return f"{namespace}-{h}"


class CanonicalMemoryStore:
    """Append-only JSONL memory store with full provenance."""

    def __init__(self, store_dir: str | Path = "data/runtime/canonical_memory_store"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.memories_path = self.store_dir / "memories.jsonl"
        self.receipts_path = self.store_dir / "promotion_receipts.jsonl"
        self.index_path = self.store_dir / "index.json"

    def _append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        with open(path, "a") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")

    def promote_candidate(
        self,
        candidate: dict[str, Any],
        reason: str,
        promoter: str = "substrate_ingestion_bridge_v1",
    ) -> tuple[MemoryEntry, PromotionReceipt]:
        """Promote a candidate into the memory store."""
        receipt_id = _deterministic_id("receipt", f"{candidate['candidate_id']}:{reason}")
        memory_id = _deterministic_id(
            "mem", f"{candidate['candidate_id']}:{candidate['source_content_hash']}"
        )

        receipt = PromotionReceipt(
            receipt_id=receipt_id,
            candidate_id=candidate["candidate_id"],
            decision=PromotionDecision.PROMOTED,
            reason=reason,
            confidence=candidate["confidence"],
            promoter=promoter,
            rollback_reference=f"candidate:{candidate['candidate_id']}",
        )

        entry = MemoryEntry(
            memory_id=memory_id,
            candidate_id=candidate["candidate_id"],
            memory_type=candidate["memory_type"],
            primitive_type=candidate["primitive_type"],
            label=candidate["label"],
            content=candidate["content"],
            confidence=candidate["confidence"],
            source_document_id=candidate["source_document_id"],
            source_content_hash=candidate["source_content_hash"],
            source_decomposition_id=candidate["source_decomposition_id"],
            promotion_receipt_id=receipt_id,
            provenance=candidate.get("provenance", {}),
            lineage={
                "candidate_id": candidate["candidate_id"],
                "decomposition_id": candidate["source_decomposition_id"],
                "document_id": candidate["source_document_id"],
                "content_hash": candidate["source_content_hash"],
                "classification_reason": candidate.get("classification_reason", ""),
            },
        )

        self._append_jsonl(self.receipts_path, receipt.to_dict())
        self._append_jsonl(self.memories_path, entry.to_dict())
        self._update_index(entry)

        return entry, receipt

    def _update_index(self, entry: MemoryEntry) -> None:
        """Maintain a queryable JSON index."""
        index: dict[str, Any] = {}
        if self.index_path.exists():
            with open(self.index_path) as f:
                index = json.load(f)

        if "entries" not in index:
            index["entries"] = {}
        if "by_type" not in index:
            index["by_type"] = {}
        if "by_document" not in index:
            index["by_document"] = {}
        if "stats" not in index:
            index["stats"] = {"total": 0, "canonical": 0, "instance": 0}

        index["entries"][entry.memory_id] = {
            "memory_type": entry.memory_type,
            "primitive_type": entry.primitive_type,
            "label": entry.label,
            "source_document_id": entry.source_document_id,
            "timestamp": entry.timestamp,
        }

        ptype = entry.primitive_type
        if ptype not in index["by_type"]:
            index["by_type"][ptype] = []
        index["by_type"][ptype].append(entry.memory_id)

        doc_id = entry.source_document_id
        if doc_id not in index["by_document"]:
            index["by_document"][doc_id] = []
        index["by_document"][doc_id].append(entry.memory_id)

        index["stats"]["total"] += 1
        if entry.memory_type == "canonical":
            index["stats"]["canonical"] += 1
        else:
            index["stats"]["instance"] += 1

        index["last_updated"] = datetime.now(timezone.utc).isoformat()

        with open(self.index_path, "w") as f:
            json.dump(index, f, indent=2)

    def query_by_id(self, memory_id: str) -> dict[str, Any] | None:
        """Retrieve a memory entry by ID."""
        if not self.memories_path.exists():
            return None
        with open(self.memories_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry["memory_id"] == memory_id:
                    return entry
        return None

    def query_by_document(self, document_id: str) -> list[dict[str, Any]]:
        """Retrieve all memories from a specific document."""
        results: list[dict[str, Any]] = []
        if not self.memories_path.exists():
            return results
        with open(self.memories_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry["source_document_id"] == document_id:
                    results.append(entry)
        return results

    def query_by_type(self, memory_type: str) -> list[dict[str, Any]]:
        """Retrieve all memories of a specific type (canonical/instance)."""
        results: list[dict[str, Any]] = []
        if not self.memories_path.exists():
            return results
        with open(self.memories_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry["memory_type"] == memory_type:
                    results.append(entry)
        return results

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Keyword search across canonical memory entries."""
        if not query or not self.memories_path.exists():
            return []
        query_words = {w.lower() for w in query.split() if len(w) > 3}
        if not query_words:
            return []
        scored: list[tuple[int, dict[str, Any]]] = []
        with open(self.memories_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                content = (entry.get("content", "") + " " + entry.get("label", "")).lower()
                hits = sum(1 for w in query_words if w in content)
                if hits > 0:
                    scored.append((hits, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:limit]]

    def get_stats(self) -> dict[str, Any]:
        """Return store statistics."""
        if self.index_path.exists():
            with open(self.index_path) as f:
                index = json.load(f)
            return index.get("stats", {})
        return {"total": 0, "canonical": 0, "instance": 0}
