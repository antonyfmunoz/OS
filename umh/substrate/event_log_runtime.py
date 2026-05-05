"""
Append-only durable event log for lifecycle boundary events.

This module provides a JSONL-based event log that records terminal
lifecycle transitions (finalization, publication, clear, seal).
It is the audit trail for the run state machine — separate from
the operational event spine (event_store.py) which tracks pipeline
telemetry.

Design rules:
- Append-only. No truncation. No rewriting prior lines.
- Monotonic, gap-free sequence numbers.
- Thread-safe via threading.Lock on the append path.
- fsync after every append for durability.
- Canonical JSON serialization for deterministic hashing.
- Best-effort — never raises into caller on I/O failure.

Invariants:
- sequence_number N is always followed by N+1 (gap-free).
- mutation_hash is sha256 of canonical JSON of state_mutations.
- log_time is always set at append time, event_time is caller-supplied.
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

_LOG_PREFIX = "[substrate.event_log_runtime]"
_DEFAULT_LOG_PATH = Path("/opt/OS/logs/harness_event_log.jsonl")


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no whitespace, ensure_ascii."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_mutation_hash(state_mutations: list[dict]) -> str:
    """SHA-256 of canonical JSON of state_mutations list."""
    canonical = _canonical_json(state_mutations)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ─── Data structures ─────────────────────────────────────────────────────


@dataclass
class EventEnvelope:
    """Single event in the lifecycle event log.

    Fields follow the spec: sequence_number is assigned at append time.
    event_id is generated if not supplied. causal_event_id links to the
    prior event in the same lifecycle flow (None when not obvious).
    """

    sequence_number: int
    event_id: str
    causal_event_id: str | None
    session_name: str
    run_id: str | None
    event_type: str
    source: str
    event_time: str
    log_time: str
    payload: dict = field(default_factory=dict)
    state_mutations: list[dict] = field(default_factory=list)
    mutation_hash: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EventAppendResult:
    """Result of an append operation."""

    ok: bool
    sequence_number: int = -1
    event_id: str = ""
    error: str = ""


# ─── Event log runtime ──────────────────────────────────────────────────


class EventLogRuntime:
    """Append-only JSONL event log with monotonic sequence numbers.

    Thread-safe. fsync-durable. Recovers sequence counter from disk
    on init if the file already exists.
    """

    def __init__(self, log_path: Path | str | None = None) -> None:
        self._path = Path(log_path) if log_path else _DEFAULT_LOG_PATH
        self._lock = threading.Lock()
        self._next_seq: int = 0
        self._recover_counter_from_disk()

    def _recover_counter_from_disk(self) -> None:
        """Read the last line of the log file to recover sequence counter."""
        if not self._path.exists():
            self._next_seq = 0
            return
        try:
            last_line = ""
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        last_line = stripped
            if last_line:
                data = json.loads(last_line)
                self._next_seq = data.get("sequence_number", -1) + 1
            else:
                self._next_seq = 0
        except Exception as exc:
            _log(f"WARNING: could not recover counter from {self._path}: {exc}")
            self._next_seq = 0

    def append(
        self,
        *,
        event_type: str,
        session_name: str,
        source: str,
        run_id: str | None = None,
        causal_event_id: str | None = None,
        event_time: str | None = None,
        payload: dict | None = None,
        state_mutations: list[dict] | None = None,
        metadata: dict | None = None,
        event_id: str | None = None,
    ) -> EventAppendResult:
        """Append an event to the log. Returns result with sequence number.

        This is the ONLY write path. All parameters except event_type,
        session_name, and source are optional with sane defaults.
        """
        mutations = state_mutations or []
        envelope = EventEnvelope(
            sequence_number=-1,  # assigned under lock
            event_id=event_id or f"evt_{uuid.uuid4().hex[:12]}",
            causal_event_id=causal_event_id,
            session_name=session_name,
            run_id=run_id,
            event_type=event_type,
            source=source,
            event_time=event_time or _utcnow(),
            log_time=_utcnow(),
            payload=payload or {},
            state_mutations=mutations,
            mutation_hash=compute_mutation_hash(mutations),
            metadata=metadata or {},
        )

        with self._lock:
            envelope.sequence_number = self._next_seq
            line = _canonical_json(envelope.to_dict()) + "\n"
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
                    import os

                    os.fsync(f.fileno())
                self._next_seq += 1
                return EventAppendResult(
                    ok=True,
                    sequence_number=envelope.sequence_number,
                    event_id=envelope.event_id,
                )
            except Exception as exc:
                _log(f"ERROR: append failed: {exc}")
                return EventAppendResult(
                    ok=False,
                    error=str(exc),
                )

    def read_all(self) -> list[EventEnvelope]:
        """Read all events from the log file."""
        if not self._path.exists():
            return []
        results: list[EventEnvelope] = []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        data = json.loads(stripped)
                        results.append(EventEnvelope(**data))
        except Exception as exc:
            _log(f"WARNING: read_all partial failure: {exc}")
        return results

    def tail(self, n: int) -> list[EventEnvelope]:
        """Return the last N events from the log."""
        if not self._path.exists():
            return []
        # Read all lines (simple for JSONL — no index)
        lines: list[str] = []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        lines.append(stripped)
        except Exception as exc:
            _log(f"WARNING: tail read failure: {exc}")
            return []
        tail_lines = lines[-n:] if n > 0 else []
        results: list[EventEnvelope] = []
        for raw in tail_lines:
            try:
                data = json.loads(raw)
                results.append(EventEnvelope(**data))
            except Exception:
                continue
        return results

    def get_last_sequence(self) -> int:
        """Return the last assigned sequence number, or -1 if empty."""
        with self._lock:
            return self._next_seq - 1

    def recover_counter_from_disk(self) -> int:
        """Public interface to force counter recovery. Returns next_seq."""
        with self._lock:
            self._recover_counter_from_disk()
            return self._next_seq
