"""UMH Trace Store — append-only persistence for run traces.

Every MVP run produces a trace that records governance decisions,
backend selection, execution results, and timing.  The trace store
persists these records and makes them queryable.

Two implementations:
  - SQLiteTraceStore  — durable, default for production
  - InMemoryTraceStore — fast, default for tests

Usage:
    store = get_trace_store()
    trace_id = store.create_trace(user_id="id_abc", input_summary="hello")
    store.append_event(trace_id, "governance_decision", {"allowed": True})
    store.complete_trace(trace_id, {"response": "world"})
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


@dataclass
class TraceEvent:
    event_type: str
    payload: dict[str, Any]
    timestamp: str


@dataclass
class TraceRecord:
    trace_id: str
    user_id: str
    input_summary: str
    status: str
    events: list[TraceEvent] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    created_at: str = ""
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "input_summary": self.input_summary,
            "status": self.status,
            "events": [
                {"event_type": e.event_type, "payload": e.payload, "timestamp": e.timestamp}
                for e in self.events
            ],
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


_DEFAULT_TRACE_DB = "/opt/OS/data/runtime/traces.sqlite"


class SQLiteTraceStore:
    """Append-only SQLite trace store."""

    def __init__(self, db_path: str = _DEFAULT_TRACE_DB) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    trace_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    input_summary TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'running',
                    result_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trace_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL REFERENCES traces(trace_id),
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trace_events_trace
                ON trace_events(trace_id)
            """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=3000")
        conn.row_factory = sqlite3.Row
        return conn

    def create_trace(
        self,
        user_id: str = "",
        input_summary: str = "",
    ) -> str:
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        now = _iso_now()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO traces (trace_id, user_id, input_summary, status, created_at) "
                    "VALUES (?, ?, ?, 'running', ?)",
                    (trace_id, user_id, input_summary[:500], now),
                )
                conn.commit()
        return trace_id

    def append_event(
        self,
        trace_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        now = _iso_now()
        payload_json = json.dumps(payload or {}, default=str)
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO trace_events (trace_id, event_type, payload_json, timestamp) "
                    "VALUES (?, ?, ?, ?)",
                    (trace_id, event_type, payload_json, now),
                )
                conn.commit()

    def complete_trace(
        self,
        trace_id: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        now = _iso_now()
        result_json = json.dumps(result or {}, default=str)
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE traces SET status = 'completed', result_json = ?, completed_at = ? "
                    "WHERE trace_id = ?",
                    (result_json, now, trace_id),
                )
                conn.commit()

    def fail_trace(self, trace_id: str, error: str) -> None:
        now = _iso_now()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE traces SET status = 'failed', error = ?, completed_at = ? "
                    "WHERE trace_id = ?",
                    (error, now, trace_id),
                )
                conn.commit()

    def get_trace(self, trace_id: str) -> TraceRecord | None:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM traces WHERE trace_id = ?", (trace_id,)
                ).fetchone()
                if row is None:
                    return None

                event_rows = conn.execute(
                    "SELECT * FROM trace_events WHERE trace_id = ? ORDER BY id",
                    (trace_id,),
                ).fetchall()

                events = [
                    TraceEvent(
                        event_type=er["event_type"],
                        payload=json.loads(er["payload_json"]),
                        timestamp=er["timestamp"],
                    )
                    for er in event_rows
                ]

                return TraceRecord(
                    trace_id=row["trace_id"],
                    user_id=row["user_id"],
                    input_summary=row["input_summary"],
                    status=row["status"],
                    events=events,
                    result=json.loads(row["result_json"]),
                    error=row["error"],
                    created_at=row["created_at"],
                    completed_at=row["completed_at"],
                )

    def list_traces(self, limit: int = 50) -> list[TraceRecord]:
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM traces ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                results = []
                for row in rows:
                    results.append(
                        TraceRecord(
                            trace_id=row["trace_id"],
                            user_id=row["user_id"],
                            input_summary=row["input_summary"],
                            status=row["status"],
                            result=json.loads(row["result_json"]),
                            error=row["error"],
                            created_at=row["created_at"],
                            completed_at=row["completed_at"],
                        )
                    )
                return results


class InMemoryTraceStore:
    """In-memory trace store for testing."""

    def __init__(self) -> None:
        self._traces: dict[str, TraceRecord] = {}

    def create_trace(
        self,
        user_id: str = "",
        input_summary: str = "",
    ) -> str:
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        self._traces[trace_id] = TraceRecord(
            trace_id=trace_id,
            user_id=user_id,
            input_summary=input_summary[:500],
            status="running",
            created_at=_iso_now(),
        )
        return trace_id

    def append_event(
        self,
        trace_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        record = self._traces.get(trace_id)
        if record is None:
            return
        record.events.append(
            TraceEvent(event_type=event_type, payload=payload or {}, timestamp=_iso_now())
        )

    def complete_trace(
        self,
        trace_id: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        record = self._traces.get(trace_id)
        if record is None:
            return
        record.status = "completed"
        record.result = result or {}
        record.completed_at = _iso_now()

    def fail_trace(self, trace_id: str, error: str) -> None:
        record = self._traces.get(trace_id)
        if record is None:
            return
        record.status = "failed"
        record.error = error
        record.completed_at = _iso_now()

    def get_trace(self, trace_id: str) -> TraceRecord | None:
        return self._traces.get(trace_id)

    def list_traces(self, limit: int = 50) -> list[TraceRecord]:
        all_traces = sorted(
            self._traces.values(),
            key=lambda t: t.created_at,
            reverse=True,
        )
        return all_traces[:limit]


_store: SQLiteTraceStore | InMemoryTraceStore | None = None
_store_lock = threading.Lock()


def get_trace_store() -> SQLiteTraceStore | InMemoryTraceStore:
    """Return the process-global trace store (lazy-initialized)."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                if (
                    os.environ.get("PYTEST_CURRENT_TEST")
                    or os.environ.get("UMH_TRACE_BACKEND") == "memory"
                ):
                    _store = InMemoryTraceStore()
                else:
                    _store = SQLiteTraceStore()
    return _store


def reset_trace_store(store=None) -> None:
    """Replace the global store (useful for tests)."""
    global _store
    with _store_lock:
        _store = store


def export_storage_descriptors(
    store: SQLiteTraceStore | InMemoryTraceStore | None = None,
    limit: int = 200,
) -> list[Any]:
    from umh.storage.contracts import (
        StorageBackendType,
        StorageMutability,
        StorageRecordDescriptor,
        StorageRecordType,
        StorageScope,
        StorageSource,
    )

    if store is None:
        store = get_trace_store()

    traces = store.list_traces(limit=limit)
    descriptors: list[StorageRecordDescriptor] = []
    is_sqlite = isinstance(store, SQLiteTraceStore)

    for t in traces:
        descriptors.append(
            StorageRecordDescriptor(
                record_id=t.trace_id,
                record_type=StorageRecordType.TRACE,
                scope=StorageScope.USER if t.user_id else StorageScope.SYSTEM,
                mutability=StorageMutability.APPEND_ONLY,
                source=StorageSource.EXECUTION,
                backend_type=StorageBackendType.SQLITE if is_sqlite else StorageBackendType.MEMORY,
                owner_id=t.user_id,
                created_at=t.created_at,
                updated_at=t.completed_at or t.created_at,
            )
        )

    return descriptors
