"""TraceRecorder — records execution traces for every signal lifecycle.

In-memory trace store with Neon persistence. Every signal gets a TraceRecord
that captures each stage of processing.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from substrate.types import TraceEvent, TraceEventType, TraceRecord


@runtime_checkable
class TraceRecorder(Protocol):
    """Protocol for recording execution traces."""

    async def start(self, signal_id: UUID) -> TraceRecord: ...

    async def add_event(
        self,
        trace_id: UUID,
        event_type: TraceEventType,
        description: str,
        **kwargs: Any,
    ) -> TraceEvent: ...

    async def complete(self, trace_id: UUID, success: bool) -> None: ...

    async def persist(self, trace: TraceRecord) -> None: ...

    async def get(self, trace_id: UUID) -> TraceRecord | None: ...


class ConcreteTraceRecorder:
    """In-memory trace recorder with Neon persistence."""

    def __init__(self) -> None:
        self._traces: dict[UUID, TraceRecord] = {}

    def count(self) -> int:
        return len(self._traces)

    async def start(self, signal_id: UUID) -> TraceRecord:
        """Start a new trace for the given signal."""
        trace = TraceRecord(signal_id=signal_id)
        trace.add_event(
            TraceEventType.SIGNAL_RECEIVED,
            f"Trace started for signal {signal_id}",
        )
        self._traces[trace.id] = trace
        return trace

    async def add_event(
        self,
        trace_id: UUID,
        event_type: TraceEventType,
        description: str,
        **kwargs: Any,
    ) -> TraceEvent:
        """Add an event to an existing trace."""
        trace = self._traces.get(trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")
        return trace.add_event(event_type, description, **kwargs)

    async def complete(self, trace_id: UUID, success: bool) -> None:
        """Mark a trace as completed."""
        trace = self._traces.get(trace_id)
        if trace:
            trace.complete(success)

    async def get(self, trace_id: UUID) -> TraceRecord | None:
        """Retrieve a trace by ID."""
        return self._traces.get(trace_id)

    async def persist(self, trace: TraceRecord) -> None:
        """Write trace to Neon traces table."""
        self._traces[trace.id] = trace
        try:
            sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))
            from dotenv import load_dotenv

            load_dotenv("/opt/OS/runtime/.env", override=True)
            from substrate.state.storage.db import get_conn

            events_json = [
                {
                    "id": str(e.id),
                    "event_type": e.event_type.value,
                    "description": e.description,
                    "data": e.data,
                    "parent_event_id": str(e.parent_event_id) if e.parent_event_id else None,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in trace.events
            ]
            with get_conn() as cur:
                cur.execute(
                    """INSERT INTO traces
                       (id, signal_id, events, started_at, completed_at,
                        success, duration_ms, org_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s,
                               current_setting('app.current_org_id', true)::uuid)
                       ON CONFLICT (id) DO UPDATE SET
                           events = EXCLUDED.events,
                           completed_at = EXCLUDED.completed_at,
                           success = EXCLUDED.success,
                           duration_ms = EXCLUDED.duration_ms""",
                    (
                        str(trace.id),
                        str(trace.signal_id),
                        json.dumps(events_json),
                        trace.started_at,
                        trace.completed_at,
                        trace.success,
                        trace.duration_ms,
                    ),
                )
        except Exception:
            # Persistence is best-effort — traces are always in memory
            pass
