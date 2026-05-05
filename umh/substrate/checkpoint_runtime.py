"""
Durable checkpoint runtime for lifecycle state snapshots.

Checkpoints capture a point-in-time snapshot of the minimal canonical
runtime state at lifecycle boundaries (typically after clear_confirmed
or terminal_seal_applied). They enable replay-from-checkpoint: load
the latest checkpoint, then replay events after its sequence number.

Design:
- Append-only checkpoint index file (JSONL, one line per checkpoint).
- Each checkpoint references the event log sequence_number it was taken at.
- snapshot_hash is sha256 of canonical JSON of state_snapshot.
- fsync-durable writes. Auto-creates directories.
- Thread-safe via threading.Lock.

Invariants:
- Checkpoints are ordered by sequence_number (monotonically increasing).
- load_latest_checkpoint() returns the highest sequence_number checkpoint.
- load_checkpoint_at_or_before(seq) returns the highest checkpoint with
  sequence_number <= seq, or None if no such checkpoint exists.
- snapshot_hash is deterministic for the same state_snapshot content.
"""

from __future__ import annotations

import hashlib
import json
import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOG_PREFIX = "[substrate.checkpoint_runtime]"
_DEFAULT_CHECKPOINT_DIR = Path("/opt/OS/logs/checkpoints")
_INDEX_FILENAME = "checkpoint_index.jsonl"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no whitespace, ensure_ascii."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_snapshot_hash(state_snapshot: dict) -> str:
    """SHA-256 of canonical JSON of state_snapshot."""
    canonical = _canonical_json(state_snapshot)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ─── Data structures ─────────────────────────────────────────────────────


@dataclass
class RuntimeCheckpoint:
    """Point-in-time snapshot of canonical runtime state.

    Taken at lifecycle boundaries. References the event log sequence
    number so replay can resume from this point.
    """

    sequence_number: int
    checkpoint_id: str
    event_id: str
    created_at: str
    state_snapshot: dict = field(default_factory=dict)
    completed_keys: list[str] = field(default_factory=list)
    in_flight_execution_ids: list[str] = field(default_factory=list)
    snapshot_hash: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CheckpointWriteResult:
    """Result of a checkpoint write operation."""

    ok: bool
    checkpoint_id: str = ""
    sequence_number: int = -1
    error: str = ""


# ─── Checkpoint runtime ─────────────────────────────────────────────────


class CheckpointRuntime:
    """Durable checkpoint storage with append-only index.

    Thread-safe. fsync-durable. Auto-creates checkpoint directory
    and index file on first write.
    """

    def __init__(self, checkpoint_dir: Path | str | None = None) -> None:
        self._dir = Path(checkpoint_dir) if checkpoint_dir else _DEFAULT_CHECKPOINT_DIR
        self._index_path = self._dir / _INDEX_FILENAME
        self._lock = threading.Lock()

    def write_checkpoint(
        self,
        *,
        sequence_number: int,
        event_id: str,
        state_snapshot: dict,
        completed_keys: list[str] | None = None,
        in_flight_execution_ids: list[str] | None = None,
        metadata: dict | None = None,
        checkpoint_id: str | None = None,
    ) -> CheckpointWriteResult:
        """Write a checkpoint to the index file.

        Returns CheckpointWriteResult with ok=True on success.
        Never raises into caller — returns error in result.
        """
        cp = RuntimeCheckpoint(
            sequence_number=sequence_number,
            checkpoint_id=checkpoint_id or f"cp_{uuid.uuid4().hex[:12]}",
            event_id=event_id,
            created_at=_utcnow(),
            state_snapshot=state_snapshot,
            completed_keys=completed_keys or [],
            in_flight_execution_ids=in_flight_execution_ids or [],
            snapshot_hash=compute_snapshot_hash(state_snapshot),
            metadata=metadata or {},
        )

        with self._lock:
            try:
                self._dir.mkdir(parents=True, exist_ok=True)
                line = _canonical_json(cp.to_dict()) + "\n"
                with open(self._index_path, "a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
                    import os

                    os.fsync(f.fileno())
                return CheckpointWriteResult(
                    ok=True,
                    checkpoint_id=cp.checkpoint_id,
                    sequence_number=cp.sequence_number,
                )
            except Exception as exc:
                _log(f"ERROR: checkpoint write failed: {exc}")
                return CheckpointWriteResult(ok=False, error=str(exc))

    def _read_all_checkpoints(self) -> list[RuntimeCheckpoint]:
        """Read all checkpoints from the index file. Internal, no lock."""
        if not self._index_path.exists():
            return []
        results: list[RuntimeCheckpoint] = []
        try:
            with open(self._index_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        data = json.loads(stripped)
                        results.append(RuntimeCheckpoint(**data))
        except Exception as exc:
            _log(f"WARNING: checkpoint index read failure: {exc}")
        return results

    def load_latest_checkpoint(self) -> RuntimeCheckpoint | None:
        """Load the checkpoint with the highest sequence number.

        Returns None if no checkpoints exist.
        """
        with self._lock:
            checkpoints = self._read_all_checkpoints()
        if not checkpoints:
            return None
        return max(checkpoints, key=lambda cp: cp.sequence_number)

    def load_checkpoint_at_or_before(self, seq: int) -> RuntimeCheckpoint | None:
        """Load the highest checkpoint with sequence_number <= seq.

        Returns None if no such checkpoint exists.
        """
        with self._lock:
            checkpoints = self._read_all_checkpoints()
        candidates = [cp for cp in checkpoints if cp.sequence_number <= seq]
        if not candidates:
            return None
        return max(candidates, key=lambda cp: cp.sequence_number)

    def list_checkpoints(self) -> list[RuntimeCheckpoint]:
        """Return all checkpoints, ordered by sequence_number ascending."""
        with self._lock:
            checkpoints = self._read_all_checkpoints()
        return sorted(checkpoints, key=lambda cp: cp.sequence_number)
