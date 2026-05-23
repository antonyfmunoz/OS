"""Tests for ConcreteComponentRegistry.

Phase 6 invariant verification.
"""
from __future__ import annotations

import uuid
import pytest

from substrate.control_plane.registry import ConcreteComponentRegistry
from substrate.types import Component, ComponentStatus, ComponentType, RegistrationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_component(**kwargs) -> Component:
    defaults = dict(
        component_type=ComponentType.AGENT,
        name="test-agent",
        version="1.0.0",
        status=ComponentStatus.ACTIVE,
        capabilities=["text_generation"],
    )
    defaults.update(kwargs)
    return Component(**defaults)


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

class TestComponentRegistry:
    @pytest.fixture
    def registry(self):
        return ConcreteComponentRegistry()

    @pytest.mark.asyncio
    async def test_register_returns_result(self, registry):
        comp = _make_component()
        result = await registry.register(comp)
        assert isinstance(result, RegistrationResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_register_stores_component(self, registry):
        comp = _make_component(name="stored-agent")
        await registry.register(comp)
        retrieved = await registry.get(comp.id)
        assert retrieved is not None
        assert retrieved.name == "stored-agent"

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self, registry):
        result = await registry.get(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_type(self, registry):
        agent = _make_component(component_type=ComponentType.AGENT, name="agent-a")
        skill = _make_component(component_type=ComponentType.SKILL, name="skill-b")
        await registry.register(agent)
        await registry.register(skill)
        agents = await registry.lookup(component_type=ComponentType.AGENT)
        names = [c.name for c in agents]
        assert "agent-a" in names
        assert "skill-b" not in names

    @pytest.mark.asyncio
    async def test_lookup_by_capability(self, registry):
        comp_a = _make_component(name="cap-agent", capabilities=["text_generation", "summarize"])
        comp_b = _make_component(name="no-cap-agent", capabilities=["image_processing"])
        await registry.register(comp_a)
        await registry.register(comp_b)
        results = await registry.lookup(capabilities=["text_generation"])
        names = [c.name for c in results]
        assert "cap-agent" in names
        assert "no-cap-agent" not in names

    @pytest.mark.asyncio
    async def test_deregister_removes_from_lookup(self, registry):
        comp = _make_component(name="to-deregister")
        await registry.register(comp)
        success = await registry.deregister(comp.id)
        assert success is True
        retrieved = await registry.get(comp.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_deregister_missing_returns_false(self, registry):
        result = await registry.deregister(uuid.uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_load_from_neon_returns_int(self, registry):
        count = await registry.load_from_neon()
        assert isinstance(count, int)
        assert count >= 0

    @pytest.mark.asyncio
    async def test_lookup_empty_registry(self, registry):
        results = await registry.lookup()
        assert isinstance(results, list)
