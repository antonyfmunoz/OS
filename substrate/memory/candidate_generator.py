"""MemoryCandidateGenerator — stages memory candidates from completed traces.

Memory candidates are NOT canonical memories. They are proposals that
could be promoted via the canonical memory store's governance contract.
This module generates and persists candidates without writing to canonical memory.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from substrate.observability.jsonl_rotation import rotate_if_needed

logger = logging.getLogger(__name__)


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

    def __init__(self, store_dir: str | Path | None = None):
        # Default to the writable runtime-state root (honors UMH_STATE_DIR) so
        # the store never lands on a repo-relative path — which resolves under a
        # read-only /app mount in the candidate container and crashed the whole
        # operator API at import (transports/api/app.py builds ExecutionPipeline
        # at module scope). Gate 15 runtime-state boundary.
        #
        # NO eager mkdir on ANY branch (finding SEC-W2): the original crash was a
        # mkdir in __init__, and leaving it on the explicit-store_dir branch
        # reproduced the same failure for any caller passing a non-writable path.
        # Directories are created lazily, only when something is actually
        # written.
        if store_dir is None:
            from substrate.state.runtime_paths import runtime_state_dir

            self.store_dir = runtime_state_dir("memory_candidates", create=False)
        else:
            self.store_dir = Path(store_dir)
        self.candidates_path = self.store_dir / "candidates.jsonl"

    @property
    def legacy_candidates_path(self) -> Path:
        """The pre-relocation store path (repo-relative ``data/umh/...``).

        Retained for READ-THROUGH only (finding SEC-W1): relocating the default
        would otherwise orphan the records written before the move — they are not
        deleted, but dedup/promotion logic reading an empty store would re-promote
        already-processed candidates. Never written to.
        """
        umh_root = os.environ.get("UMH_ROOT") or "/opt/OS"
        return Path(umh_root) / "data" / "umh" / "memory_candidates" / "candidates.jsonl"

    def _append_jsonl(self, record: dict[str, Any]) -> None:
        # Lazily create the store dir at WRITE time, never at construction.
        self.store_dir.mkdir(parents=True, exist_ok=True)
        rotate_if_needed(self.candidates_path)
        with open(self.candidates_path, "a") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")

    def _iter_records(self) -> "list[dict[str, Any]]":
        """All candidate records: legacy store first, then the current store.

        Reads THROUGH to the legacy location so records written before the
        relocation stay visible, keeping identity, attribution and ordering
        intact. Duplicate candidate_ids resolve to the newest record.
        """
        records: list[dict[str, Any]] = []
        seen: dict[str, int] = {}
        for path in (self.legacy_candidates_path, self.candidates_path):
            if not path.is_file():
                continue
            try:
                with open(path) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                        except ValueError:
                            continue
                        cid = str(rec.get("candidate_id", "") or "")
                        if cid and cid in seen:
                            records[seen[cid]] = rec  # newer record supersedes
                            continue
                        if cid:
                            seen[cid] = len(records)
                        records.append(rec)
            except OSError as exc:
                logger.debug("candidate store unreadable at %s: %s", path, exc)
        return records

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
        """Query persisted candidates by status or trace ID.

        Reads the legacy store as well as the current one, so records written
        before the runtime-state relocation remain queryable (finding SEC-W1).
        """
        results: list[MemoryCandidate] = []
        for data in self._iter_records():
            if status and data.get("promotion_status") != status:
                continue
            if trace_id and data.get("source_trace_id") != trace_id:
                continue
            results.append(MemoryCandidate.from_dict(data))
            if len(results) >= limit:
                break
        return results

    def count(self) -> int:
        """Total number of candidates across the legacy and current stores."""
        return len(self._iter_records())
