"""Tests for ConcreteTraceRecorder.

Phase 6 invariant verification.
"""
from __future__ import annotations

import uuid
import pytest

from substrate.execution.trace import ConcreteTraceRecorder
from substrate.types import TraceRecord, TraceEvent, TraceEventType


class TestTraceRecorder:
    @pytest.fixture
    def recorder(self):
        return ConcreteTraceRecorder()

    @pytest.mark.asyncio
    async def test_start_returns_trace(self, recorder):
        sig_id = uuid.uuid4()
        trace = await recorder.start(sig_id)
        assert isinstance(trace, TraceRecord)

    @pytest.mark.asyncio
    async def test_start_records_signal_id(self, recorder):
        sig_id = uuid.uuid4()
        trace = await recorder.start(sig_id)
        assert trace.signal_id == sig_id

    @pytest.mark.asyncio
    async def test_start_has_initial_event(self, recorder):
        trace = await recorder.start(uuid.uuid4())
        assert len(trace.events) >= 1

    @pytest.mark.asyncio
    async def test_get_returns_trace(self, recorder):
        trace = await recorder.start(uuid.uuid4())
        retrieved = await recorder.get(trace.id)
        assert retrieved is not None
        assert retrieved.id == trace.id

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self, recorder):
        result = await recorder.get(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_add_event(self, recorder):
        trace = await recorder.start(uuid.uuid4())
        event = await recorder.add_event(
            trace.id,
            TraceEventType.GOVERNANCE_DECIDED,
            "classified as question",
        )
        assert isinstance(event, TraceEvent)

    @pytest.mark.asyncio
    async def test_add_event_to_missing_trace_raises(self, recorder):
        with pytest.raises(ValueError):
            await recorder.add_event(
                uuid.uuid4(),
                TraceEventType.GOVERNANCE_DECIDED,
                "should fail",
            )

    @pytest.mark.asyncio
    async def test_complete_marks_trace(self, recorder):
        trace = await recorder.start(uuid.uuid4())
        await recorder.complete(trace.id, success=True)
        retrieved = await recorder.get(trace.id)
        assert retrieved.success is True
        assert retrieved.completed_at is not None

    @pytest.mark.asyncio
    async def test_complete_failure(self, recorder):
        trace = await recorder.start(uuid.uuid4())
        await recorder.complete(trace.id, success=False)
        retrieved = await recorder.get(trace.id)
        assert retrieved.success is False

    @pytest.mark.asyncio
    async def test_persist_stable_without_db(self, recorder):
        trace = await recorder.start(uuid.uuid4())
        await recorder.complete(trace.id, success=True)
        try:
            await recorder.persist(trace)
        except Exception as exc:
            pytest.fail(f"persist() raised unexpectedly: {exc}")
