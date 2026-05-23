"""Tests for ConcreteExecutionSpine — 8-stage pipeline.

Phase 6 invariant verification.
Tests the deterministic path (no LLM required).
"""
from __future__ import annotations

import uuid
import pytest

from substrate.execution.spine import ConcreteExecutionSpine
from substrate.types import (
    ExecutionContext,
    ExecutionOutcome,
    ExecutionResult,
    GovernanceDecision,
    GovernanceVerdict,
    Identity,
    Modality,
    RiskClass,
    SignalEnvelope,
    SignalSource,
    SignalUrgency,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_signal(content: str = "what is my focus today", **kwargs) -> SignalEnvelope:
    defaults = dict(
        source=SignalSource.USER,
        urgency=SignalUrgency.NORMAL,
        modality=Modality.TEXT,
        content=content,
        user_id="user-sp",
        organization_id="org-sp",
        venture_id="venture-sp",
        authority_tier=3,
    )
    defaults.update(kwargs)
    return SignalEnvelope(**defaults)


def _make_identity(autonomy_level: int = 2) -> Identity:
    return Identity(
        user_id="user-sp",
        organization_id="org-sp",
        venture_id="venture-sp",
        ai_name="TestAI",
        ai_personality="direct",
        autonomy_level=autonomy_level,
        business_stage="pre_revenue",
    )


def _make_context(signal: SignalEnvelope, autonomy_level: int = 2) -> ExecutionContext:
    return ExecutionContext(
        signal_id=signal.id,
        identity=_make_identity(autonomy_level),
        conversation_history=[],
        relevant_memories=[],
        business_context={"business_stage": "pre_revenue"},
    )


def _make_verdict(signal: SignalEnvelope, decision: GovernanceDecision = GovernanceDecision.APPROVE) -> GovernanceVerdict:
    return GovernanceVerdict(
        signal_id=signal.id,
        risk_class=RiskClass.LOW,
        decision=decision,
        rationale="test verdict",
    )


# ---------------------------------------------------------------------------
# ExecutionSpine tests
# ---------------------------------------------------------------------------

class TestExecutionSpine:
    @pytest.fixture
    def spine(self):
        # No injected memory/registry — tests deterministic path only
        return ConcreteExecutionSpine()

    @pytest.mark.asyncio
    async def test_execute_returns_result(self, spine):
        signal = _make_signal()
        context = _make_context(signal)
        verdict = _make_verdict(signal)
        result = await spine.execute(signal, context, verdict)
        assert isinstance(result, ExecutionResult)

    @pytest.mark.asyncio
    async def test_execute_approved_signal_succeeds_or_partial(self, spine):
        signal = _make_signal("what is my schedule")
        context = _make_context(signal)
        verdict = _make_verdict(signal, GovernanceDecision.APPROVE)
        result = await spine.execute(signal, context, verdict)
        assert result.outcome in (ExecutionOutcome.SUCCESS, ExecutionOutcome.PARTIAL_SUCCESS)

    @pytest.mark.asyncio
    async def test_execute_blocked_verdict_returns_blocked(self, spine):
        signal = _make_signal("send email to all users")
        context = _make_context(signal)
        verdict = _make_verdict(signal, GovernanceDecision.DENY)
        result = await spine.execute(signal, context, verdict)
        assert result.outcome == ExecutionOutcome.BLOCKED

    @pytest.mark.asyncio
    async def test_execute_output_non_empty(self, spine):
        signal = _make_signal("summarize my goals")
        context = _make_context(signal)
        verdict = _make_verdict(signal)
        result = await spine.execute(signal, context, verdict)
        assert result.output  # deterministic fallback always produces output

    @pytest.mark.asyncio
    async def test_execute_result_links_signal_id(self, spine):
        signal = _make_signal()
        context = _make_context(signal)
        verdict = _make_verdict(signal)
        result = await spine.execute(signal, context, verdict)
        assert result.signal_id == signal.id

    @pytest.mark.asyncio
    async def test_execute_records_duration(self, spine):
        signal = _make_signal()
        context = _make_context(signal)
        verdict = _make_verdict(signal)
        result = await spine.execute(signal, context, verdict)
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_greeting_intent(self, spine):
        signal = _make_signal("hello there")
        context = _make_context(signal)
        verdict = _make_verdict(signal)
        result = await spine.execute(signal, context, verdict)
        assert result.outcome in (ExecutionOutcome.SUCCESS, ExecutionOutcome.PARTIAL_SUCCESS)

    @pytest.mark.asyncio
    async def test_execute_question_intent(self, spine):
        signal = _make_signal("what is my revenue target?")
        context = _make_context(signal)
        verdict = _make_verdict(signal)
        result = await spine.execute(signal, context, verdict)
        assert result.outcome in (ExecutionOutcome.SUCCESS, ExecutionOutcome.PARTIAL_SUCCESS)

    @pytest.mark.asyncio
    async def test_execute_blocked_output_contains_rationale(self, spine):
        signal = _make_signal("execute payment to vendor")
        context = _make_context(signal)
        verdict = GovernanceVerdict(
            signal_id=signal.id,
            risk_class=RiskClass.CRITICAL,
            decision=GovernanceDecision.DENY,
            rationale="payment blocked at current autonomy level",
        )
        result = await spine.execute(signal, context, verdict)
        assert "blocked" in result.output.lower() or "autonomy" in result.output.lower()
