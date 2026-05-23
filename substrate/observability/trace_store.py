"""TraceStore — append-only JSONL trace persistence.

Every UMH execution produces a trace. Traces are observability data,
not memory. They record what happened, when, and what the outcome was.

File-backed JSONL as MVP — DB-upgradeable later.
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


class TraceStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class Trace:
    """A single execution trace in the UMH system."""

    trace_id: str
    input_signal: str
    interpretation_ref: str = ""
    governance_decision: str = ""
    work_packet: dict[str, Any] = field(default_factory=dict)
    adapter_used: str = ""
    environment: str = ""
    execution_result: dict[str, Any] = field(default_factory=dict)
    proof_artifact_id: str = ""
    outcome: str = ""
    outcome_detail: str = ""
    memory_candidate_ref: str = ""
    status: str = TraceStatus.PENDING
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Trace:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class TraceStore:
    """Append-only JSONL trace store with index for queries."""

    def __init__(self, store_dir: str | Path = "data/umh/traces"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.traces_path = self.store_dir / "traces.jsonl"
        self.index_path = self.store_dir / "index.json"
        self._index: dict[str, dict[str, Any]] | None = None

    def _load_index(self) -> dict[str, dict[str, Any]]:
        if self._index is not None:
            return self._index
        if self.index_path.exists():
            self._index = json.loads(self.index_path.read_text())
        else:
            self._index = {}
        return self._index

    def _save_index(self) -> None:
        idx = self._load_index()
        self.index_path.write_text(json.dumps(idx, indent=2))

    def _append_jsonl(self, record: dict[str, Any]) -> None:
        with open(self.traces_path, "a") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")

    def create_trace(
        self,
        input_signal: str,
        *,
        interpretation_ref: str = "",
        governance_decision: str = "",
        work_packet: dict[str, Any] | None = None,
        adapter_used: str = "",
        environment: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Trace:
        """Create and persist a new trace. Returns the Trace object."""
        trace_id = _deterministic_id(
            "trace",
            f"{input_signal}:{datetime.now(timezone.utc).isoformat()}",
        )
        trace = Trace(
            trace_id=trace_id,
            input_signal=input_signal,
            interpretation_ref=interpretation_ref,
            governance_decision=governance_decision,
            work_packet=work_packet or {},
            adapter_used=adapter_used,
            environment=environment,
            metadata=metadata or {},
        )
        self._append_jsonl(trace.to_dict())
        idx = self._load_index()
        idx[trace_id] = {
            "status": trace.status,
            "created_at": trace.created_at,
            "outcome": trace.outcome,
            "input_signal_preview": input_signal[:120],
        }
        self._save_index()
        return trace

    def update_trace(
        self,
        trace_id: str,
        *,
        status: str | None = None,
        execution_result: dict[str, Any] | None = None,
        proof_artifact_id: str | None = None,
        outcome: str | None = None,
        outcome_detail: str | None = None,
        memory_candidate_ref: str | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
    ) -> dict[str, Any]:
        """Append an update record to the trace log. Returns the update."""
        now = datetime.now(timezone.utc).isoformat()
        update: dict[str, Any] = {
            "_type": "trace_update",
            "trace_id": trace_id,
            "updated_at": now,
        }
        if status is not None:
            update["status"] = status
        if execution_result is not None:
            update["execution_result"] = execution_result
        if proof_artifact_id is not None:
            update["proof_artifact_id"] = proof_artifact_id
        if outcome is not None:
            update["outcome"] = outcome
        if outcome_detail is not None:
            update["outcome_detail"] = outcome_detail
        if memory_candidate_ref is not None:
            update["memory_candidate_ref"] = memory_candidate_ref
        if started_at is not None:
            update["started_at"] = started_at
        if completed_at is not None:
            update["completed_at"] = completed_at

        self._append_jsonl(update)

        idx = self._load_index()
        if trace_id in idx:
            if status:
                idx[trace_id]["status"] = status
            if outcome:
                idx[trace_id]["outcome"] = outcome
            if completed_at:
                idx[trace_id]["completed_at"] = completed_at
            self._save_index()

        return update

    def get_trace(self, trace_id: str) -> Trace | None:
        """Reconstruct a trace by replaying all JSONL records for that ID."""
        if not self.traces_path.exists():
            return None
        base: dict[str, Any] = {}
        with open(self.traces_path) as f:
            for line in f:
                record = json.loads(line)
                if record.get("trace_id") == trace_id:
                    if record.get("_type") == "trace_update":
                        updates = {
                            k: v
                            for k, v in record.items()
                            if k not in ("_type", "trace_id", "updated_at")
                        }
                        base.update(updates)
                    else:
                        base = record
        if not base:
            return None
        return Trace.from_dict(base)

    def query_traces(
        self,
        *,
        status: str | None = None,
        outcome: str | None = None,
        limit: int = 50,
        since: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query traces from the index. Returns index entries (lightweight)."""
        idx = self._load_index()
        results = []
        for tid, entry in idx.items():
            if status and entry.get("status") != status:
                continue
            if outcome and entry.get("outcome") != outcome:
                continue
            if since and entry.get("created_at", "") < since:
                continue
            results.append({"trace_id": tid, **entry})
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results[:limit]

    def recent_traces(self, n: int = 10) -> list[dict[str, Any]]:
        """Get the N most recent traces from the index."""
        return self.query_traces(limit=n)

    def count(self) -> int:
        """Total number of traces in the index."""
        return len(self._load_index())
