"""Tests for ConcreteContextAssembler.

Phase 6 invariant verification.
"""
from __future__ import annotations

import pytest

from substrate.control_plane.context import ConcreteContextAssembler
from substrate.types import (
    ExecutionContext,
    Identity,
    SignalEnvelope,
    SignalSource,
    SignalUrgency,
    Modality,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_signal(**kwargs) -> SignalEnvelope:
    defaults = dict(
        source=SignalSource.USER,
        urgency=SignalUrgency.NORMAL,
        modality=Modality.TEXT,
        content="what is my focus today",
        user_id="user-asm",
        organization_id="org-asm",
        venture_id="venture-asm",
        authority_tier=3,
    )
    defaults.update(kwargs)
    return SignalEnvelope(**defaults)


def _make_identity(**kwargs) -> Identity:
    defaults = dict(
        user_id="user-asm",
        organization_id="org-asm",
        venture_id="venture-asm",
        ai_name="TestAI",
        ai_personality="direct",
        autonomy_level=2,
        business_stage="pre_revenue",
    )
    defaults.update(kwargs)
    return Identity(**defaults)


# ---------------------------------------------------------------------------
# ContextAssembler tests
# ---------------------------------------------------------------------------

class TestContextAssembler:
    @pytest.fixture
    def assembler(self):
        return ConcreteContextAssembler(memory_system=None)

    @pytest.mark.asyncio
    async def test_assemble_returns_execution_context(self, assembler):
        signal = _make_signal()
        identity = _make_identity()
        ctx = await assembler.assemble(signal, identity)
        assert isinstance(ctx, ExecutionContext)

    @pytest.mark.asyncio
    async def test_assemble_signal_id_matches(self, assembler):
        signal = _make_signal()
        identity = _make_identity()
        ctx = await assembler.assemble(signal, identity)
        assert ctx.signal_id == signal.id

    @pytest.mark.asyncio
    async def test_assemble_identity_propagated(self, assembler):
        signal = _make_signal()
        identity = _make_identity(ai_name="SpecialAI")
        ctx = await assembler.assemble(signal, identity)
        assert ctx.identity.ai_name == "SpecialAI"

    @pytest.mark.asyncio
    async def test_assemble_conversation_history_is_list(self, assembler):
        signal = _make_signal()
        identity = _make_identity()
        ctx = await assembler.assemble(signal, identity)
        assert isinstance(ctx.conversation_history, list)

    @pytest.mark.asyncio
    async def test_assemble_relevant_memories_is_list(self, assembler):
        signal = _make_signal()
        identity = _make_identity()
        ctx = await assembler.assemble(signal, identity)
        assert isinstance(ctx.relevant_memories, list)

    @pytest.mark.asyncio
    async def test_assemble_business_context_populated(self, assembler):
        signal = _make_signal()
        identity = _make_identity(business_stage="growth")
        ctx = await assembler.assemble(signal, identity)
        assert ctx.business_context.get("business_stage") == "growth"

    @pytest.mark.asyncio
    async def test_assemble_stable_without_db(self, assembler):
        signal = _make_signal()
        identity = _make_identity()
        try:
            ctx = await assembler.assemble(signal, identity)
            assert ctx is not None
        except Exception as exc:
            pytest.fail(f"assemble() raised unexpectedly: {exc}")
