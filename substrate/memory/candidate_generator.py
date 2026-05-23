"""MemoryCandidateGenerator — stages memory candidates from completed traces.

Memory candidates are NOT canonical memories. They are proposals that
could be promoted via the canonical memory store's governance contract.
This module generates and persists candidates without writing to canonical memory.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _deterministic_id(namespace: str, content: str) -> str:
    h = hashlib.sha256(f"{namespace}:{content}".encode("utf-8")).hexdigest()[:16]
    return f"{namespace}-{h}"


class PromotionStatus:
    STAGED = "staged"
    PROMOTED = "promoted"
    REJECTED = "rejected"
    DEFERRED = "deferred"


@dataclass
class MemoryCandidate:
    """A memory candidate generated from a trace."""

    candidate_id: str
    source_trace_id: str
    content: str
    reason: str
    confidence: float
    scope: str  # e.g. "session", "project", "global"
    tags: list[str] = field(default_factory=list)
    promotion_status: str = PromotionStatus.STAGED
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryCandidate:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class MemoryCandidateGenerator:
    """Generates and persists memory candidates from traces.

    Candidates are written to an append-only JSONL file.
    The generator does NOT write to canonical memory.
    """

    def __init__(self, store_dir: str | Path = "data/umh/memory_candidates"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.candidates_path = self.store_dir / "candidates.jsonl"

    def _append_jsonl(self, record: dict[str, Any]) -> None:
        with open(self.candidates_path, "a") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")

    def generate_candidate(
        self,
        source_trace_id: str,
        content: str,
        reason: str,
        *,
        confidence: float = 0.5,
        scope: str = "session",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryCandidate:
        """Generate and persist a memory candidate from a trace."""
        candidate_id = _deterministic_id(
            "memcand",
            f"{source_trace_id}:{content[:128]}",
        )
        candidate = MemoryCandidate(
            candidate_id=candidate_id,
            source_trace_id=source_trace_id,
            content=content,
            reason=reason,
            confidence=confidence,
            scope=scope,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._append_jsonl(candidate.to_dict())
        return candidate

    def generate_from_trace(
        self,
        trace_id: str,
        input_signal: str,
        outcome: str,
        outcome_detail: str,
        *,
        execution_result: dict[str, Any] | None = None,
    ) -> MemoryCandidate | None:
        """Auto-generate a memory candidate from trace fields.

        Only generates candidates for successful or partial outcomes
        with meaningful content.
        """
        if outcome not in ("success", "partial"):
            return None

        content_parts = [f"Signal: {input_signal[:200]}"]
        if outcome_detail:
            content_parts.append(f"Result: {outcome_detail[:200]}")

        output = (execution_result or {}).get("output", "")
        if output:
            content_parts.append(f"Output: {str(output)[:200]}")

        content = " | ".join(content_parts)
        reason = f"auto-generated from {outcome} trace {trace_id}"
        confidence = 0.7 if outcome == "success" else 0.4

        tags = ["auto-generated", outcome]
        if execution_result:
            if execution_result.get("adapter"):
                tags.append(f"adapter:{execution_result['adapter']}")

        return self.generate_candidate(
            source_trace_id=trace_id,
            content=content,
            reason=reason,
            confidence=confidence,
            scope="session",
            tags=tags,
        )

    def get_candidates(
        self,
        *,
        status: str | None = None,
        trace_id: str | None = None,
        limit: int = 50,
    ) -> list[MemoryCandidate]:
        """Query persisted candidates by status or trace ID."""
        if not self.candidates_path.exists():
            return []
        results: list[MemoryCandidate] = []
        with open(self.candidates_path) as f:
            for line in f:
                data = json.loads(line)
                if status and data.get("promotion_status") != status:
                    continue
                if trace_id and data.get("source_trace_id") != trace_id:
                    continue
                results.append(MemoryCandidate.from_dict(data))
                if len(results) >= limit:
                    break
        return results

    def count(self) -> int:
        """Total number of candidates."""
        if not self.candidates_path.exists():
            return 0
        with open(self.candidates_path) as f:
            return sum(1 for _ in f)
