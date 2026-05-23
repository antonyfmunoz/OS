"""Tests for the full governance engine with production risk classes."""

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

import pytest
from substrate.types import (
    ExecutionContext,
    GovernanceDecision,
    GovernanceVerdict,
    Identity,
    RiskClass,
    SignalEnvelope,
    SignalSource,
)
from substrate.control_plane.governance import ConcreteGovernanceEngine


def _make_signal(content: str) -> SignalEnvelope:
    return SignalEnvelope(
        source=SignalSource.USER,
        content=content,
        user_id="test",
        organization_id="test-org",
    )


def _make_context(autonomy: int = 1) -> ExecutionContext:
    return ExecutionContext(
        signal_id=_make_signal("x").id,
        identity=Identity(
            user_id="test",
            organization_id="test-org",
            ai_name="DEX",
            ai_personality="professional",
            autonomy_level=autonomy,
            business_stage="pre_revenue",
        ),
    )


class TestRiskClassification:
    @pytest.fixture
    def engine(self):
        return ConcreteGovernanceEngine()

    @pytest.mark.parametrize(
        "content",
        [
            "send email to john",
            "send message to the channel",
            "execute payment for invoice",
            "delete records from CRM",
            "bulk update all leads",
            "mass outreach campaign",
            "publish content to blog",
        ],
    )
    @pytest.mark.asyncio
    async def test_critical_actions(self, engine, content):
        signal = _make_signal(content)
        context = _make_context(autonomy=4)
        verdict = await engine.classify(signal, context)
        assert verdict.risk_class == RiskClass.CRITICAL

    @pytest.mark.parametrize(
        "content",
        [
            "create outreach for lead",
            "post content on social",
            "book call with prospect",
            "update crm entry",
        ],
    )
    @pytest.mark.asyncio
    async def test_high_actions(self, engine, content):
        signal = _make_signal(content)
        context = _make_context(autonomy=1)
        verdict = await engine.classify(signal, context)
        assert verdict.risk_class == RiskClass.HIGH

    @pytest.mark.parametrize(
        "content",
        [
            "draft message for review",
            "draft content about product",
            "create task for follow up",
            "create document template",
        ],
    )
    @pytest.mark.asyncio
    async def test_medium_actions(self, engine, content):
        signal = _make_signal(content)
        context = _make_context()
        verdict = await engine.classify(signal, context)
        assert verdict.risk_class == RiskClass.MEDIUM

    @pytest.mark.asyncio
    async def test_unknown_defaults_low(self, engine):
        signal = _make_signal("what is the weather today")
        context = _make_context()
        verdict = await engine.classify(signal, context)
        assert verdict.risk_class == RiskClass.LOW

    @pytest.mark.asyncio
    async def test_physical_actuation_is_critical(self, engine):
        signal = _make_signal("activate robotic arm")
        context = _make_context(autonomy=4)
        verdict = await engine.classify(signal, context)
        assert verdict.risk_class == RiskClass.CRITICAL


class TestAutonomyGating:
    @pytest.fixture
    def engine(self):
        return ConcreteGovernanceEngine()

    @pytest.mark.asyncio
    async def test_critical_always_denied(self, engine):
        signal = _make_signal("send email to john")
        context = _make_context(autonomy=4)
        verdict = await engine.classify(signal, context)
        assert verdict.decision == GovernanceDecision.DENY

    @pytest.mark.asyncio
    async def test_low_always_approved(self, engine):
        signal = _make_signal("analyze this data")
        context = _make_context(autonomy=0)
        verdict = await engine.classify(signal, context)
        assert verdict.decision == GovernanceDecision.APPROVE

    @pytest.mark.asyncio
    async def test_high_denied_at_autonomy_2(self, engine):
        signal = _make_signal("create outreach for lead")
        context = _make_context(autonomy=2)
        verdict = await engine.classify(signal, context)
        assert verdict.decision == GovernanceDecision.DENY

    @pytest.mark.asyncio
    async def test_high_approved_at_autonomy_3(self, engine):
        signal = _make_signal("create outreach for lead")
        context = _make_context(autonomy=3)
        verdict = await engine.classify(signal, context)
        assert verdict.decision == GovernanceDecision.APPROVE
