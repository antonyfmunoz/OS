"""Tests for substrate execution layer components."""

import sys

sys.path.insert(0, "/opt/OS")

import asyncio
from uuid import uuid4

from substrate.execution.trace import ConcreteTraceRecorder, TraceRecorder
from substrate.types import TraceEventType, TraceRecord


class TestTraceRecorder:
    """Tests for ConcreteTraceRecorder."""

    def test_implements_protocol(self) -> None:
        recorder = ConcreteTraceRecorder()
        assert isinstance(recorder, TraceRecorder)

    def test_start_creates_trace(self) -> None:
        recorder = ConcreteTraceRecorder()
        signal_id = uuid4()
        trace = asyncio.run(recorder.start(signal_id))
        assert isinstance(trace, TraceRecord)
        assert trace.signal_id == signal_id
        # start() adds a SIGNAL_RECEIVED event automatically
        assert len(trace.events) >= 1
        assert trace.events[0].event_type == TraceEventType.SIGNAL_RECEIVED

    def test_add_event(self) -> None:
        recorder = ConcreteTraceRecorder()
        signal_id = uuid4()
        trace = asyncio.run(recorder.start(signal_id))
        event = asyncio.run(
            recorder.add_event(trace.id, TraceEventType.GOVERNANCE_DECIDED, "approved")
        )
        assert event.trace_id == trace.id
        assert event.event_type == TraceEventType.GOVERNANCE_DECIDED
        assert event.description == "approved"
        # trace should now have 2 events (SIGNAL_RECEIVED + GOVERNANCE_DECIDED)
        assert len(trace.events) == 2

    def test_add_event_unknown_trace_raises(self) -> None:
        recorder = ConcreteTraceRecorder()
        try:
            asyncio.run(recorder.add_event(uuid4(), TraceEventType.ERROR, "should fail"))
            assert False, "Expected ValueError"
        except ValueError:
            pass

    def test_complete_sets_fields(self) -> None:
        recorder = ConcreteTraceRecorder()
        signal_id = uuid4()
        trace = asyncio.run(recorder.start(signal_id))
        asyncio.run(recorder.complete(trace.id, success=True))
        completed = recorder._traces.get(trace.id)
        assert completed is not None
        assert completed.success is True
        assert completed.completed_at is not None
        assert completed.duration_ms is not None
        assert completed.duration_ms >= 0

    def test_get_returns_trace(self) -> None:
        recorder = ConcreteTraceRecorder()
        signal_id = uuid4()
        trace = asyncio.run(recorder.start(signal_id))
        retrieved = asyncio.run(recorder.get(trace.id))
        assert retrieved is not None
        assert retrieved.id == trace.id

    def test_get_missing_returns_none(self) -> None:
        recorder = ConcreteTraceRecorder()
        result = asyncio.run(recorder.get(uuid4()))
        assert result is None
