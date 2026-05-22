"""Tests for substrate control plane components."""

import sys

sys.path.insert(0, "/opt/OS")

import asyncio

from substrate.control_plane.context import ConcreteContextAssembler, ContextAssembler
from substrate.control_plane.identity import ConcreteIdentityResolver, IdentityResolver
from substrate.types import ExecutionContext, Identity, SignalEnvelope, SignalSource


class TestIdentityResolver:
    def test_implements_protocol(self):
        resolver = ConcreteIdentityResolver()
        assert isinstance(resolver, IdentityResolver)

    def test_resolve_returns_identity(self):
        resolver = ConcreteIdentityResolver()
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="test",
            user_id="test-user",
            organization_id="munoz-holdings",
        )
        identity = asyncio.run(resolver.resolve(signal))
        assert isinstance(identity, Identity)
        assert identity.user_id == "test-user"
        assert identity.organization_id == "munoz-holdings"
        assert identity.ai_name != ""
        assert identity.business_stage != ""


class TestContextAssembler:
    def test_implements_protocol(self):
        assembler = ConcreteContextAssembler()
        assert isinstance(assembler, ContextAssembler)

    def test_assemble_returns_execution_context(self):
        assembler = ConcreteContextAssembler()
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="test message",
            user_id="test-user",
            organization_id="munoz-holdings",
        )
        identity = Identity(
            user_id="test-user",
            organization_id="munoz-holdings",
            ai_name="DEX",
            ai_personality="professional",
            autonomy_level=1,
            business_stage="pre_revenue",
        )
        ctx = asyncio.run(assembler.assemble(signal, identity))
        assert isinstance(ctx, ExecutionContext)
        assert ctx.signal_id == signal.id
        assert ctx.identity == identity
