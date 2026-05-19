"""MemoryPromoter — evaluates candidates for promotion to durable storage.

Candidates above the confidence threshold get written to a JSON file.
Deduplicates by content hash to avoid storing identical memories.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from services.umh.memory.candidate_generator import MemoryCandidate


DEFAULT_CONFIDENCE_THRESHOLD = 0.7


class MemoryPromoter:
    """Promotes memory candidates above threshold to durable JSON store."""

    def __init__(
        self,
        path: Path | None = None,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        self._path = path or Path("data/umh/promoted_memories.json")
        self._threshold = confidence_threshold
        self._memories: list[dict[str, Any]] = []
        self._seen_hashes: set[str] = set()
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._memories = json.loads(self._path.read_text())
                self._seen_hashes = {m.get("content_hash", "") for m in self._memories}
            except (json.JSONDecodeError, OSError):
                self._memories = []
                self._seen_hashes = set()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._memories, indent=2, default=str))

    @staticmethod
    def _hash_content(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def evaluate(self, candidate: MemoryCandidate) -> dict[str, Any]:
        """Evaluate a candidate for promotion. Returns promotion result."""
        content_hash = self._hash_content(candidate.content)

        if candidate.confidence < self._threshold:
            return {
                "promoted": False,
                "reason": f"Below threshold ({candidate.confidence:.2f} < {self._threshold})",
                "candidate_id": candidate.candidate_id,
            }

        if content_hash in self._seen_hashes:
            return {
                "promoted": False,
                "reason": "Duplicate content",
                "candidate_id": candidate.candidate_id,
            }

        memory = {
            "memory_id": f"mem-p-{candidate.candidate_id.split('-')[-1]}",
            "candidate_id": candidate.candidate_id,
            "trace_id": candidate.source_trace_id,
            "content": candidate.content,
            "confidence": candidate.confidence,
            "scope": candidate.scope,
            "tags": candidate.tags,
            "content_hash": content_hash,
            "promoted_at": int(time.time()),
        }

        self._memories.append(memory)
        self._seen_hashes.add(content_hash)
        self._save()

        return {
            "promoted": True,
            "memory_id": memory["memory_id"],
            "candidate_id": candidate.candidate_id,
        }

    def list_memories(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._memories[-limit:]

    def stats(self) -> dict[str, int]:
        return {
            "total_memories": len(self._memories),
            "unique_hashes": len(self._seen_hashes),
        }
