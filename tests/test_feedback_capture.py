"""Tests for ConcreteFeedbackCapture.

Phase 6 invariant verification.
"""
from __future__ import annotations

import uuid
import pytest

from substrate.execution.feedback import ConcreteFeedbackCapture, _QUALITY_MAP
from substrate.execution.trace import ConcreteTraceRecorder
from substrate.types import (
    ExecutionOutcome,
    ExecutionResult,
    FeedbackRecord,
    FeedbackType,
    GovernanceDecision,
    RiskClass,
    TraceRecord,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(**kwargs) -> ExecutionResult:
    sig_id = uuid.uuid4()
    trace_id = uuid.uuid4()
    defaults = dict(
        signal_id=sig_id,
        trace_id=trace_id,
        outcome=ExecutionOutcome.SUCCESS,
        output="this is the output",
        provider="gemini",
        model="gemini-2.5-flash",
        duration_ms=350,
        risk_class=RiskClass.LOW,
        governance_decision=GovernanceDecision.APPROVE,
        memory_candidates=[],
    )
    defaults.update(kwargs)
    return ExecutionResult(**defaults)


async def _make_trace() -> TraceRecord:
    recorder = ConcreteTraceRecorder()
    trace = await recorder.start(uuid.uuid4())
    await recorder.complete(trace.id, success=True)
    retrieved = await recorder.get(trace.id)
    return retrieved


# ---------------------------------------------------------------------------
# FeedbackCapture tests
# ---------------------------------------------------------------------------

class TestFeedbackCapture:
    @pytest.fixture
    def capture(self):
        return ConcreteFeedbackCapture()

    @pytest.mark.asyncio
    async def test_capture_returns_feedback_record(self, capture):
        trace = await _make_trace()
        result = _make_result()
        feedback = await capture.capture(trace, result)
        assert isinstance(feedback, FeedbackRecord)

    @pytest.mark.asyncio
    async def test_capture_links_trace_id(self, capture):
        trace = await _make_trace()
        result = _make_result()
        feedback = await capture.capture(trace, result)
        assert feedback.trace_id == trace.id

    @pytest.mark.asyncio
    async def test_capture_links_signal_id(self, capture):
        trace = await _make_trace()
        result = _make_result()
        feedback = await capture.capture(trace, result)
        assert feedback.signal_id == result.signal_id

    @pytest.mark.asyncio
    async def test_capture_quality_success(self, capture):
        trace = await _make_trace()
        result = _make_result(outcome=ExecutionOutcome.SUCCESS)
        feedback = await capture.capture(trace, result)
        assert feedback.outcome_quality == _QUALITY_MAP[ExecutionOutcome.SUCCESS]

    @pytest.mark.asyncio
    async def test_capture_quality_failure(self, capture):
        trace = await _make_trace()
        result = _make_result(outcome=ExecutionOutcome.FAILURE, output="", error="something broke")
        feedback = await capture.capture(trace, result)
        assert feedback.outcome_quality == _QUALITY_MAP[ExecutionOutcome.FAILURE]

    @pytest.mark.asyncio
    async def test_capture_quality_timeout(self, capture):
        trace = await _make_trace()
        result = _make_result(outcome=ExecutionOutcome.TIMEOUT, output="")
        feedback = await capture.capture(trace, result)
        assert feedback.outcome_quality == _QUALITY_MAP[ExecutionOutcome.TIMEOUT]

    @pytest.mark.asyncio
    async def test_capture_learning_signal_with_error(self, capture):
        trace = await _make_trace()
        result = _make_result(outcome=ExecutionOutcome.FAILURE, output="", error="timeout error")
        feedback = await capture.capture(trace, result)
        assert "timeout error" in feedback.learning_signal

    @pytest.mark.asyncio
    async def test_capture_learning_signal_with_output(self, capture):
        trace = await _make_trace()
        result = _make_result(output="some output text")
        feedback = await capture.capture(trace, result)
        assert "Output length" in feedback.learning_signal

    @pytest.mark.asyncio
    async def test_capture_feedback_type_implicit(self, capture):
        trace = await _make_trace()
        result = _make_result()
        feedback = await capture.capture(trace, result)
        assert feedback.feedback_type == FeedbackType.IMPLICIT

    @pytest.mark.asyncio
    async def test_persist_stable_without_db(self, capture):
        trace = await _make_trace()
        result = _make_result()
        feedback = await capture.capture(trace, result)
        try:
            await capture.persist(feedback)
        except Exception as exc:
            pytest.fail(f"persist() raised unexpectedly: {exc}")

    def test_quality_map_covers_all_outcomes(self):
        for outcome in ExecutionOutcome:
            assert outcome in _QUALITY_MAP
