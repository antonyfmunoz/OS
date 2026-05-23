"""Tests for the full 8-stage execution spine."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

import pytest
from substrate.types import (
    ExecutionContext,
    ExecutionOutcome,
    ExecutionResult,
    GovernanceDecision,
    GovernanceVerdict,
    Identity,
    RiskClass,
    SignalEnvelope,
    SignalSource,
    TraceEventType,
)
from substrate.execution.spine import ConcreteExecutionSpine


def _make_signal(content: str = "hello") -> SignalEnvelope:
    return SignalEnvelope(
        source=SignalSource.USER,
        content=content,
        user_id="test",
        organization_id="test-org",
    )


def _make_context() -> ExecutionContext:
    return ExecutionContext(
        signal_id=_make_signal().id,
        identity=Identity(
            user_id="test",
            organization_id="test-org",
            ai_name="DEX",
            ai_personality="professional",
            autonomy_level=1,
            business_stage="pre_revenue",
        ),
    )


def _make_verdict(decision=GovernanceDecision.APPROVE) -> GovernanceVerdict:
    return GovernanceVerdict(
        signal_id=_make_signal().id,
        risk_class=RiskClass.LOW,
        decision=decision,
        rationale="test",
    )


def _run(coro):
    """Run an async coroutine synchronously for testing."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _mock_call_with_fallback(*args, **kwargs):
    """Mock LLM call that returns None to trigger deterministic fallback."""
    return None


class TestSpineExecution:
    @pytest.fixture
    def spine(self):
        return ConcreteExecutionSpine()

    @patch("adapters.models.model_router.call_with_fallback", _mock_call_with_fallback)
    def test_execute_returns_result(self, spine):
        result = _run(spine.execute(_make_signal(), _make_context(), _make_verdict()))
        assert isinstance(result, ExecutionResult)

    @patch("adapters.models.model_router.call_with_fallback", _mock_call_with_fallback)
    def test_blocked_signal_returns_blocked(self, spine):
        verdict = _make_verdict(decision=GovernanceDecision.DENY)
        result = _run(spine.execute(_make_signal(), _make_context(), verdict))
        assert result.outcome == ExecutionOutcome.BLOCKED

    @patch("adapters.models.model_router.call_with_fallback", _mock_call_with_fallback)
    def test_deterministic_fallback_always_produces_output(self, spine):
        result = _run(
            spine.execute(
                _make_signal("hello there"),
                _make_context(),
                _make_verdict(),
            )
        )
        assert result.output != ""
        assert len(result.output) > 0

    def test_intent_classification_greeting(self, spine):
        intent = spine._classify_intent("hello there")
        assert intent == "greeting"

    def test_intent_classification_question(self, spine):
        # "what is the status?" matches "status" pattern first (more specific).
        # Use a pure question without domain keywords.
        intent = spine._classify_intent("what is the meaning of life?")
        assert intent == "question"

    def test_intent_classification_command(self, spine):
        intent = spine._classify_intent("create a new document")
        assert intent == "command"

    def test_intent_classification_unknown(self, spine):
        intent = spine._classify_intent("asdf jkl")
        assert intent == "unknown"

    @patch("adapters.models.model_router.call_with_fallback", _mock_call_with_fallback)
    def test_execute_has_duration(self, spine):
        result = _run(spine.execute(_make_signal(), _make_context(), _make_verdict()))
        assert result.duration_ms > 0

    @patch("adapters.models.model_router.call_with_fallback", _mock_call_with_fallback)
    def test_execute_has_trace_id(self, spine):
        result = _run(spine.execute(_make_signal(), _make_context(), _make_verdict()))
        assert result.trace_id is not None


class TestSpineIntentPatterns:
    """Test the expanded intent patterns from gateway + intent_handler."""

    @pytest.fixture
    def spine(self):
        return ConcreteExecutionSpine()

    @pytest.mark.parametrize(
        "content,expected",
        [
            ("schedule a meeting for tomorrow", "schedule"),
            ("send an email to john", "send"),
            ("check the pipeline status", "status"),
            ("analyze the sales data", "analysis"),
            ("create a new outreach campaign", "command"),
            ("fix the broken import", "command"),
            ("hi how are you", "greeting"),
            ("what time is it?", "question"),
            ("research competitor pricing", "analysis"),
        ],
    )
    def test_intent_patterns(self, spine, content, expected):
        intent = spine._classify_intent(content)
        assert intent == expected
