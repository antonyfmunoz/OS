"""Tests for substrate control plane components."""

import sys

sys.path.insert(0, "/opt/OS")

import asyncio

from uuid import UUID

from substrate.control_plane.context import ConcreteContextAssembler, ContextAssembler
from substrate.control_plane.governance import ConcreteGovernanceEngine, GovernanceEngine
from substrate.control_plane.identity import ConcreteIdentityResolver, IdentityResolver
from substrate.control_plane.memory import ConcreteMemorySystem, MemorySystem
from substrate.control_plane.registry import ConcreteComponentRegistry, ComponentRegistry
from substrate.types import (
    Component,
    ComponentType,
    ComponentStatus,
    RegistrationResult,
    ExecutionContext,
    ExecutionPlan,
    GovernanceDecision,
    GovernanceVerdict,
    Identity,
    MemoryEntry,
    MemoryQuery,
    MemoryType,
    RiskClass,
    SignalEnvelope,
    SignalSource,
)


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


class TestGovernanceEngine:
    def test_implements_protocol(self):
        engine = ConcreteGovernanceEngine()
        assert isinstance(engine, GovernanceEngine)

    def test_classify_critical_action(self):
        engine = ConcreteGovernanceEngine()
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="send email to all leads",
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
        ctx = ExecutionContext(
            signal_id=signal.id,
            identity=identity,
        )
        verdict = asyncio.run(engine.classify(signal, ctx))
        assert isinstance(verdict, GovernanceVerdict)
        assert verdict.risk_class == RiskClass.CRITICAL
        assert verdict.decision == GovernanceDecision.DENY

    def test_classify_low_risk_action(self):
        engine = ConcreteGovernanceEngine()
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="analyze this data",
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
        ctx = ExecutionContext(signal_id=signal.id, identity=identity)
        verdict = asyncio.run(engine.classify(signal, ctx))
        assert verdict.risk_class == RiskClass.LOW
        assert verdict.decision == GovernanceDecision.APPROVE

    def test_classify_unknown_defaults_low(self):
        engine = ConcreteGovernanceEngine()
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="do something completely novel",
            user_id="test",
            organization_id="org",
        )
        identity = Identity(
            user_id="test",
            organization_id="org",
            ai_name="DEX",
            ai_personality="professional",
            autonomy_level=1,
            business_stage="pre_revenue",
        )
        ctx = ExecutionContext(signal_id=signal.id, identity=identity)
        verdict = asyncio.run(engine.classify(signal, ctx))
        assert verdict.risk_class == RiskClass.LOW


class TestMemorySystem:
    def test_implements_protocol(self):
        system = ConcreteMemorySystem()
        assert isinstance(system, MemorySystem)

    def test_store_returns_uuid(self):
        system = ConcreteMemorySystem()
        entry = MemoryEntry(
            memory_type=MemoryType.FACT,
            content="test fact",
        )
        result_id = asyncio.run(system.store(entry))
        assert isinstance(result_id, UUID)


class TestComponentRegistry:
    def test_implements_protocol(self):
        registry = ConcreteComponentRegistry()
        assert isinstance(registry, ComponentRegistry)

    def test_register_and_lookup(self):
        registry = ConcreteComponentRegistry()
        adapter = Component(
            component_type=ComponentType.ADAPTER,
            name="test-adapter",
            capabilities=["text_generation"],
        )
        result = asyncio.run(registry.register(adapter))
        assert isinstance(result, RegistrationResult)
        assert result.success is True

        found = asyncio.run(registry.lookup(component_type=ComponentType.ADAPTER))
        assert any(c.name == "test-adapter" for c in found)

    def test_lookup_by_type_filters(self):
        registry = ConcreteComponentRegistry()
        adapter1 = Component(component_type=ComponentType.ADAPTER, name="a1")
        adapter2 = Component(component_type=ComponentType.ADAPTER, name="a2")
        agent = Component(component_type=ComponentType.AGENT, name="agent1")
        asyncio.run(registry.register(adapter1))
        asyncio.run(registry.register(adapter2))
        asyncio.run(registry.register(agent))

        adapters = asyncio.run(registry.lookup(component_type=ComponentType.ADAPTER))
        assert len(adapters) == 2
        agents = asyncio.run(registry.lookup(component_type=ComponentType.AGENT))
        assert len(agents) == 1

    def test_deregister(self):
        registry = ConcreteComponentRegistry()
        comp = Component(component_type=ComponentType.SKILL, name="temp-skill")
        asyncio.run(registry.register(comp))
        assert asyncio.run(registry.deregister(comp.id)) is True
        found = asyncio.run(registry.lookup(component_type=ComponentType.SKILL))
        assert not any(c.id == comp.id for c in found)

    def test_get_by_id(self):
        registry = ConcreteComponentRegistry()
        comp = Component(component_type=ComponentType.AGENT, name="lookup-agent")
        asyncio.run(registry.register(comp))
        result = asyncio.run(registry.get(comp.id))
        assert result is not None
        assert result.name == "lookup-agent"

    def test_get_missing_returns_none(self):
        from uuid import uuid4

        registry = ConcreteComponentRegistry()
        result = asyncio.run(registry.get(uuid4()))
        assert result is None
