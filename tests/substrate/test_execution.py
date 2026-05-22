"""Tests for substrate execution layer components."""

import sys

sys.path.insert(0, "/opt/OS")

import asyncio
from uuid import uuid4

from substrate.execution.feedback import ConcreteFeedbackCapture, FeedbackCapture
from substrate.execution.spine import ConcreteExecutionSpine, ExecutionSpine
from substrate.execution.trace import ConcreteTraceRecorder, TraceRecorder
from substrate.types import (
    ExecutionContext,
    ExecutionOutcome,
    ExecutionResult,
    FeedbackRecord,
    FeedbackType,
    GovernanceDecision,
    GovernanceVerdict,
    Identity,
    RiskClass,
    SignalEnvelope,
    SignalSource,
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


class TestExecutionSpine:
    """Tests for ConcreteExecutionSpine — 8-stage pipeline."""

    def _make_spine(self) -> ConcreteExecutionSpine:
        from substrate.control_plane.memory import ConcreteMemorySystem
        from substrate.control_plane.registry import ConcreteComponentRegistry

        return ConcreteExecutionSpine(
            memory=ConcreteMemorySystem(),
            registry=ConcreteComponentRegistry(),
            trace_recorder=ConcreteTraceRecorder(),
            feedback_capture=ConcreteFeedbackCapture(),
        )

    def _make_signal(self, content: str = "hello test") -> SignalEnvelope:
        return SignalEnvelope(
            source=SignalSource.SYSTEM,
            content=content,
            user_id="test",
            organization_id="test-org",
        )

    def _make_context(self, signal_id) -> ExecutionContext:
        identity = Identity(
            user_id="test",
            organization_id="test-org",
            ai_name="DEX",
            ai_personality="professional",
            autonomy_level=1,
            business_stage="pre_revenue",
        )
        return ExecutionContext(signal_id=signal_id, identity=identity)

    def _make_verdict(
        self,
        signal_id,
        decision: GovernanceDecision = GovernanceDecision.APPROVE,
        risk_class: RiskClass = RiskClass.LOW,
        rationale: str = "test approved",
    ) -> GovernanceVerdict:
        return GovernanceVerdict(
            signal_id=signal_id,
            risk_class=risk_class,
            decision=decision,
            rationale=rationale,
        )

    def test_implements_protocol(self) -> None:
        spine = ConcreteExecutionSpine.__new__(ConcreteExecutionSpine)
        assert isinstance(spine, ExecutionSpine)

    def test_execute_returns_result(self) -> None:
        spine = self._make_spine()
        signal = self._make_signal("hello test")
        context = self._make_context(signal.id)
        verdict = self._make_verdict(signal.id)

        result = asyncio.run(spine.execute(signal, context, verdict))
        assert isinstance(result, ExecutionResult)
        assert result.signal_id == signal.id
        assert result.trace_id is not None
        assert result.outcome == ExecutionOutcome.SUCCESS

    def test_execute_blocked_returns_blocked(self) -> None:
        spine = self._make_spine()
        signal = self._make_signal("send email to everyone")
        context = self._make_context(signal.id)
        verdict = self._make_verdict(
            signal.id,
            decision=GovernanceDecision.DENY,
            risk_class=RiskClass.CRITICAL,
            rationale="too risky",
        )

        result = asyncio.run(spine.execute(signal, context, verdict))
        assert result.outcome == ExecutionOutcome.BLOCKED
        assert result.governance_decision == GovernanceDecision.DENY
        assert result.output == "too risky"

    def test_deterministic_fallback_greeting(self) -> None:
        """Deterministic-first: greeting intent produces a greeting response."""
        spine = self._make_spine()
        signal = self._make_signal("hello there")
        context = self._make_context(signal.id)
        verdict = self._make_verdict(signal.id)

        result = asyncio.run(spine.execute(signal, context, verdict))
        assert result.outcome == ExecutionOutcome.SUCCESS
        # Without live LLM, falls back to deterministic greeting
        assert result.provider == "deterministic"
        assert "Hello" in result.output

    def test_deterministic_fallback_question(self) -> None:
        """Deterministic-first: question intent produces a question response."""
        spine = self._make_spine()
        signal = self._make_signal("what is the current status?")
        context = self._make_context(signal.id)
        verdict = self._make_verdict(signal.id)

        result = asyncio.run(spine.execute(signal, context, verdict))
        assert result.outcome == ExecutionOutcome.SUCCESS
        assert result.provider == "deterministic"

    def test_deterministic_fallback_command(self) -> None:
        """Deterministic-first: command intent produces a command response."""
        spine = self._make_spine()
        signal = self._make_signal("create a new project")
        context = self._make_context(signal.id)
        verdict = self._make_verdict(signal.id)

        result = asyncio.run(spine.execute(signal, context, verdict))
        assert result.outcome == ExecutionOutcome.SUCCESS
        assert result.provider == "deterministic"
        assert "process" in result.output.lower() or "request" in result.output.lower()

    def test_classify_intent_unknown(self) -> None:
        """Unknown content falls back to unknown intent."""
        spine = ConcreteExecutionSpine()
        assert spine._classify_intent("asdf jkl") == "unknown"

    def test_classify_intent_greeting(self) -> None:
        spine = ConcreteExecutionSpine()
        assert spine._classify_intent("hello world") == "greeting"

    def test_classify_intent_question(self) -> None:
        spine = ConcreteExecutionSpine()
        assert spine._classify_intent("what is this?") == "question"

    def test_execute_without_subsystems(self) -> None:
        """Spine works with no memory, no registry, no trace, no feedback."""
        spine = ConcreteExecutionSpine()
        signal = self._make_signal("hey")
        context = self._make_context(signal.id)
        verdict = self._make_verdict(signal.id)

        result = asyncio.run(spine.execute(signal, context, verdict))
        assert result.outcome == ExecutionOutcome.SUCCESS
        assert result.duration_ms > 0

    def test_execute_escalated_is_blocked(self) -> None:
        """Escalated verdict is not executable — returns BLOCKED."""
        spine = ConcreteExecutionSpine()
        signal = self._make_signal("do something dangerous")
        context = self._make_context(signal.id)
        verdict = self._make_verdict(
            signal.id,
            decision=GovernanceDecision.ESCALATE,
            risk_class=RiskClass.HIGH,
            rationale="needs human review",
        )

        result = asyncio.run(spine.execute(signal, context, verdict))
        assert result.outcome == ExecutionOutcome.BLOCKED
