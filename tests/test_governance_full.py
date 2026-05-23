"""Tests for GovernanceEngine — risk classification and execution authority.

Phase 6 invariant verification.
"""
from __future__ import annotations

import uuid
import pytest

from substrate.control_plane.governance import ConcreteGovernanceEngine, AUTONOMY_THRESHOLDS
from substrate.types import (
    ExecutionContext,
    ExecutionPlan,
    GovernanceDecision,
    GovernanceVerdict,
    Identity,
    RiskClass,
    SignalEnvelope,
    SignalSource,
    SignalUrgency,
    Modality,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_signal(content: str = "help me draft a message", **kwargs) -> SignalEnvelope:
    defaults = dict(
        source=SignalSource.USER,
        urgency=SignalUrgency.NORMAL,
        modality=Modality.TEXT,
        content=content,
        user_id="user-001",
        organization_id="org-001",
        venture_id="venture-001",
        authority_tier=3,
    )
    defaults.update(kwargs)
    return SignalEnvelope(**defaults)


def _make_identity(autonomy_level: int = 2) -> Identity:
    return Identity(
        user_id="user-001",
        organization_id="org-001",
        venture_id="venture-001",
        ai_name="TestAI",
        ai_personality="direct",
        autonomy_level=autonomy_level,
        business_stage="pre_revenue",
    )


def _make_context(autonomy_level: int = 2) -> ExecutionContext:
    return ExecutionContext(
        signal_id=uuid.uuid4(),
        identity=_make_identity(autonomy_level),
        conversation_history=[],
        relevant_memories=[],
        business_context={},
    )


# ---------------------------------------------------------------------------
# GovernanceEngine
# ---------------------------------------------------------------------------

class TestGovernanceEngine:
    @pytest.fixture
    def engine(self):
        return ConcreteGovernanceEngine()

    @pytest.mark.asyncio
    async def test_classify_returns_verdict(self, engine):
        signal = _make_signal("what is the weather")
        context = _make_context(autonomy_level=2)
        verdict = await engine.classify(signal, context)
        assert isinstance(verdict, GovernanceVerdict)

    @pytest.mark.asyncio
    async def test_low_risk_content_approved_low_autonomy(self, engine):
        signal = _make_signal("what is my schedule")
        context = _make_context(autonomy_level=0)
        verdict = await engine.classify(signal, context)
        assert verdict.risk_class == RiskClass.LOW
        assert verdict.decision == GovernanceDecision.APPROVE

    @pytest.mark.asyncio
    async def test_critical_content_denied_at_autonomy_2(self, engine):
        signal = _make_signal("send email to all clients")
        context = _make_context(autonomy_level=2)
        verdict = await engine.classify(signal, context)
        assert verdict.risk_class == RiskClass.CRITICAL
        assert verdict.decision == GovernanceDecision.DENY

    @pytest.mark.asyncio
    async def test_high_risk_denied_below_threshold(self, engine):
        signal = _make_signal("create outreach for leads")
        context = _make_context(autonomy_level=2)
        verdict = await engine.classify(signal, context)
        assert verdict.risk_class == RiskClass.HIGH
        assert verdict.decision == GovernanceDecision.DENY

    @pytest.mark.asyncio
    async def test_high_risk_approved_above_threshold(self, engine):
        signal = _make_signal("create outreach for leads")
        context = _make_context(autonomy_level=3)
        verdict = await engine.classify(signal, context)
        assert verdict.risk_class == RiskClass.HIGH
        assert verdict.decision == GovernanceDecision.APPROVE

    @pytest.mark.asyncio
    async def test_medium_risk_approved_at_autonomy_1(self, engine):
        signal = _make_signal("draft message for the team")
        context = _make_context(autonomy_level=1)
        verdict = await engine.classify(signal, context)
        assert verdict.risk_class == RiskClass.MEDIUM
        assert verdict.decision == GovernanceDecision.APPROVE

    @pytest.mark.asyncio
    async def test_verdict_contains_signal_id(self, engine):
        signal = _make_signal()
        context = _make_context()
        verdict = await engine.classify(signal, context)
        assert verdict.signal_id == signal.id

    @pytest.mark.asyncio
    async def test_verdict_rationale_populated(self, engine):
        signal = _make_signal("summarize my tasks")
        context = _make_context()
        verdict = await engine.classify(signal, context)
        assert len(verdict.rationale) > 0

    @pytest.mark.asyncio
    async def test_check_execution_approved_verdict(self, engine):
        signal = _make_signal("summarize my day")
        context = _make_context(autonomy_level=2)
        verdict = await engine.classify(signal, context)
        plan = ExecutionPlan(
            signal_id=signal.id,
            governance_verdict_id=verdict.id,
            intent="summarize",
            adapter_id=None,
            model_task_type="fast_response",
            prompt="summarize my day",
        )
        permitted = await engine.check_execution(plan, verdict)
        assert isinstance(permitted, bool)

    def test_autonomy_thresholds_completeness(self):
        for rc in RiskClass:
            assert rc in AUTONOMY_THRESHOLDS
