"""Tests for substrate execution layer components."""

import sys

sys.path.insert(0, "/opt/OS")

import asyncio
from uuid import uuid4

from substrate.execution.feedback import ConcreteFeedbackCapture, FeedbackCapture
from substrate.execution.trace import ConcreteTraceRecorder, TraceRecorder
from substrate.types import (
    ExecutionOutcome,
    ExecutionResult,
    FeedbackRecord,
    FeedbackType,
    TraceEventType,
    TraceRecord,
)


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


class TestFeedbackCapture:
    """Tests for ConcreteFeedbackCapture."""

    def test_implements_protocol(self) -> None:
        capture = ConcreteFeedbackCapture()
        assert isinstance(capture, FeedbackCapture)

    def test_capture_produces_feedback(self) -> None:
        capture = ConcreteFeedbackCapture()
        trace = TraceRecord(signal_id=uuid4())
        trace.add_event(TraceEventType.SIGNAL_RECEIVED, "test")
        trace.complete(success=True)
        result = ExecutionResult(
            signal_id=trace.signal_id,
            trace_id=trace.id,
            outcome=ExecutionOutcome.SUCCESS,
            output="response",
        )
        feedback = asyncio.run(capture.capture(trace, result))
        assert isinstance(feedback, FeedbackRecord)
        assert feedback.trace_id == trace.id

    def test_success_gets_higher_quality(self) -> None:
        capture = ConcreteFeedbackCapture()
        trace = TraceRecord(signal_id=uuid4())
        trace.complete(success=True)
        result = ExecutionResult(
            signal_id=trace.signal_id,
            trace_id=trace.id,
            outcome=ExecutionOutcome.SUCCESS,
            output="good",
        )
        feedback = asyncio.run(capture.capture(trace, result))
        assert feedback.outcome_quality >= 0.5

    def test_failure_gets_lower_quality(self) -> None:
        capture = ConcreteFeedbackCapture()
        trace = TraceRecord(signal_id=uuid4())
        trace.complete(success=False)
        result = ExecutionResult(
            signal_id=trace.signal_id,
            trace_id=trace.id,
            outcome=ExecutionOutcome.FAILURE,
            error="broke",
        )
        feedback = asyncio.run(capture.capture(trace, result))
        assert feedback.outcome_quality < 0.5
