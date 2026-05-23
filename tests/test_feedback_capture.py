"""Verify ConcreteFeedbackCapture behaviour.

Tests run against the existing implementation in substrate/execution/feedback.py.
No mocking of the implementation — we test the real deterministic quality map.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

import pytest
from uuid import uuid4

from substrate.types import (
    ExecutionOutcome,
    ExecutionResult,
    FeedbackRecord,
    FeedbackType,
    TraceEventType,
    TraceRecord,
)
from substrate.execution.feedback import ConcreteFeedbackCapture


class TestFeedbackCapture:
    @pytest.fixture
    def capture(self) -> ConcreteFeedbackCapture:
        return ConcreteFeedbackCapture()

    def _make_trace(self) -> TraceRecord:
        trace = TraceRecord(signal_id=uuid4())
        trace.add_event(TraceEventType.SIGNAL_RECEIVED, "test signal")
        trace.complete(success=True)
        return trace

    def _make_result(
        self,
        outcome: ExecutionOutcome = ExecutionOutcome.SUCCESS,
        output: str = "test output",
        error: str | None = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            signal_id=uuid4(),
            trace_id=uuid4(),
            outcome=outcome,
            output=output,
            error=error,
        )

    # ── Core contract ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_capture_returns_feedback_record(self, capture: ConcreteFeedbackCapture) -> None:
        trace = self._make_trace()
        result = self._make_result()
        feedback = await capture.capture(trace, result)
        assert isinstance(feedback, FeedbackRecord)

    @pytest.mark.asyncio
    async def test_feedback_type_is_implicit(self, capture: ConcreteFeedbackCapture) -> None:
        trace = self._make_trace()
        result = self._make_result()
        feedback = await capture.capture(trace, result)
        assert feedback.feedback_type == FeedbackType.IMPLICIT

    @pytest.mark.asyncio
    async def test_feedback_links_trace_and_signal(self, capture: ConcreteFeedbackCapture) -> None:
        trace = self._make_trace()
        result = self._make_result()
        feedback = await capture.capture(trace, result)
        assert feedback.trace_id == trace.id
        assert feedback.signal_id == result.signal_id

    # ── Quality mapping ───────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_success_has_high_quality(self, capture: ConcreteFeedbackCapture) -> None:
        trace = self._make_trace()
        result = self._make_result(ExecutionOutcome.SUCCESS)
        feedback = await capture.capture(trace, result)
        assert feedback.outcome_quality >= 0.7

    @pytest.mark.asyncio
    async def test_failure_has_low_quality(self, capture: ConcreteFeedbackCapture) -> None:
        trace = self._make_trace()
        result = self._make_result(ExecutionOutcome.FAILURE)
        feedback = await capture.capture(trace, result)
        assert feedback.outcome_quality <= 0.3

    @pytest.mark.asyncio
    async def test_partial_success_quality_is_mid_range(
        self, capture: ConcreteFeedbackCapture
    ) -> None:
        trace = self._make_trace()
        result = self._make_result(ExecutionOutcome.PARTIAL_SUCCESS)
        feedback = await capture.capture(trace, result)
        assert 0.4 <= feedback.outcome_quality <= 0.8

    @pytest.mark.asyncio
    async def test_timeout_has_lower_quality_than_failure(
        self, capture: ConcreteFeedbackCapture
    ) -> None:
        trace = self._make_trace()
        timeout_result = self._make_result(ExecutionOutcome.TIMEOUT)
        failure_result = self._make_result(ExecutionOutcome.FAILURE)
        timeout_feedback = await capture.capture(trace, timeout_result)
        failure_feedback = await capture.capture(trace, failure_result)
        assert timeout_feedback.outcome_quality <= failure_feedback.outcome_quality

    @pytest.mark.asyncio
    async def test_blocked_quality_is_between_partial_and_failure(
        self, capture: ConcreteFeedbackCapture
    ) -> None:
        trace = self._make_trace()
        result = self._make_result(ExecutionOutcome.BLOCKED)
        feedback = await capture.capture(trace, result)
        # BLOCKED maps to 0.5 — sits between PARTIAL_SUCCESS (0.6) and FAILURE (0.2)
        assert 0.3 <= feedback.outcome_quality <= 0.7

    # ── Learning signal ───────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_output_produces_learning_signal(self, capture: ConcreteFeedbackCapture) -> None:
        trace = self._make_trace()
        result = self._make_result(output="hello world")
        feedback = await capture.capture(trace, result)
        assert "length" in feedback.learning_signal.lower() or len(feedback.learning_signal) > 0

    @pytest.mark.asyncio
    async def test_error_appears_in_learning_signal(self, capture: ConcreteFeedbackCapture) -> None:
        trace = self._make_trace()
        result = self._make_result(
            outcome=ExecutionOutcome.FAILURE,
            output="",
            error="connection refused",
        )
        feedback = await capture.capture(trace, result)
        assert "connection refused" in feedback.learning_signal

    @pytest.mark.asyncio
    async def test_long_error_is_truncated(self, capture: ConcreteFeedbackCapture) -> None:
        trace = self._make_trace()
        long_error = "x" * 1000
        result = self._make_result(
            outcome=ExecutionOutcome.FAILURE,
            output="",
            error=long_error,
        )
        feedback = await capture.capture(trace, result)
        # learning_signal max_length=500, error truncated to 200 chars + "Error: " prefix
        assert len(feedback.learning_signal) <= 500

    # ── FeedbackRecord validity ───────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_outcome_quality_within_valid_range(
        self, capture: ConcreteFeedbackCapture
    ) -> None:
        """quality is a Pydantic float field with ge=0.0, le=1.0 — verify for all outcomes."""
        trace = self._make_trace()
        for outcome in ExecutionOutcome:
            result = self._make_result(outcome)
            feedback = await capture.capture(trace, result)
            assert 0.0 <= feedback.outcome_quality <= 1.0, f"quality out of range for {outcome}"

    @pytest.mark.asyncio
    async def test_feedback_has_id(self, capture: ConcreteFeedbackCapture) -> None:
        trace = self._make_trace()
        result = self._make_result()
        feedback = await capture.capture(trace, result)
        assert feedback.id is not None

    @pytest.mark.asyncio
    async def test_feedback_has_captured_at_timestamp(
        self, capture: ConcreteFeedbackCapture
    ) -> None:
        trace = self._make_trace()
        result = self._make_result()
        feedback = await capture.capture(trace, result)
        assert feedback.captured_at is not None
