import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

import pytest
from uuid import uuid4

from substrate.types import TraceEventType, TraceRecord
from substrate.execution.trace import ConcreteTraceRecorder


class TestTraceRecorder:
    @pytest.fixture
    def recorder(self):
        return ConcreteTraceRecorder()

    @pytest.mark.asyncio
    async def test_start_creates_trace(self, recorder):
        signal_id = uuid4()
        trace = await recorder.start(signal_id)
        assert isinstance(trace, TraceRecord)
        assert trace.signal_id == signal_id

    @pytest.mark.asyncio
    async def test_add_event(self, recorder):
        signal_id = uuid4()
        trace = await recorder.start(signal_id)
        event = await recorder.add_event(trace.id, TraceEventType.SIGNAL_RECEIVED, "test event")
        assert event.event_type == TraceEventType.SIGNAL_RECEIVED

    @pytest.mark.asyncio
    async def test_complete_sets_fields(self, recorder):
        signal_id = uuid4()
        trace = await recorder.start(signal_id)
        await recorder.complete(trace.id, success=True)
        completed = await recorder.get(trace.id)
        assert completed is not None
        assert completed.success is True
        assert completed.completed_at is not None
        assert completed.duration_ms is not None

    @pytest.mark.asyncio
    async def test_get_returns_none_for_unknown(self, recorder):
        result = await recorder.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_trace_has_at_least_two_events_after_completion(self, recorder):
        signal_id = uuid4()
        trace = await recorder.start(signal_id)
        await recorder.add_event(trace.id, TraceEventType.SIGNAL_RECEIVED, "received")
        await recorder.add_event(trace.id, TraceEventType.EXECUTION_COMPLETED, "done")
        await recorder.complete(trace.id, success=True)
        completed = await recorder.get(trace.id)
        assert len(completed.events) >= 2
