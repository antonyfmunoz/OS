import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

import pytest
from substrate.types import (
    ExecutionContext,
    Identity,
    SignalEnvelope,
    SignalSource,
)
from substrate.control_plane.context import ConcreteContextAssembler


def _make_signal() -> SignalEnvelope:
    return SignalEnvelope(
        source=SignalSource.USER,
        content="hello",
        user_id="test-user",
        organization_id="test-org",
    )


def _make_identity() -> Identity:
    return Identity(
        user_id="test-user",
        organization_id="test-org",
        ai_name="DEX",
        ai_personality="professional",
        autonomy_level=1,
        business_stage="pre_revenue",
    )


class TestContextAssembler:
    @pytest.fixture
    def assembler(self):
        return ConcreteContextAssembler()

    @pytest.mark.asyncio
    async def test_assemble_returns_execution_context(self, assembler):
        signal = _make_signal()
        identity = _make_identity()
        ctx = await assembler.assemble(signal, identity)
        assert isinstance(ctx, ExecutionContext)
        assert ctx.signal_id == signal.id
        assert ctx.identity == identity

    @pytest.mark.asyncio
    async def test_context_has_business_context(self, assembler):
        signal = _make_signal()
        identity = _make_identity()
        ctx = await assembler.assemble(signal, identity)
        assert isinstance(ctx.business_context, dict)
        assert "business_stage" in ctx.business_context

    @pytest.mark.asyncio
    async def test_context_has_conversation_history_list(self, assembler):
        signal = _make_signal()
        identity = _make_identity()
        ctx = await assembler.assemble(signal, identity)
        assert isinstance(ctx.conversation_history, list)
