import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

import pytest
from uuid import uuid4

from substrate.types import (
    Component,
    ComponentStatus,
    ComponentType,
    RegistrationResult,
)
from substrate.control_plane.registry import ConcreteComponentRegistry


class TestComponentRegistry:
    @pytest.fixture
    def registry(self):
        return ConcreteComponentRegistry()

    @pytest.mark.asyncio
    async def test_register_returns_result(self, registry):
        component = Component(
            component_type=ComponentType.ADAPTER,
            name="test-adapter",
            capabilities=["text_generation"],
        )
        result = await registry.register(component)
        assert isinstance(result, RegistrationResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_register_result_contains_component_id(self, registry):
        component = Component(
            component_type=ComponentType.ADAPTER,
            name="test-adapter",
        )
        result = await registry.register(component)
        assert result.component_id == component.id

    @pytest.mark.asyncio
    async def test_lookup_by_type(self, registry):
        for i in range(3):
            ctype = ComponentType.ADAPTER if i < 2 else ComponentType.AGENT
            await registry.register(
                Component(
                    component_type=ctype,
                    name=f"test-{i}",
                )
            )
        adapters = await registry.lookup(component_type=ComponentType.ADAPTER)
        assert len(adapters) == 2

    @pytest.mark.asyncio
    async def test_lookup_returns_all_when_no_filter(self, registry):
        for i in range(3):
            await registry.register(
                Component(
                    component_type=ComponentType.SKILL,
                    name=f"skill-{i}",
                )
            )
        all_comps = await registry.lookup()
        assert len(all_comps) == 3

    @pytest.mark.asyncio
    async def test_lookup_by_capabilities(self, registry):
        await registry.register(
            Component(
                component_type=ComponentType.ADAPTER,
                name="capable-adapter",
                capabilities=["text_generation", "summarization"],
            )
        )
        await registry.register(
            Component(
                component_type=ComponentType.ADAPTER,
                name="limited-adapter",
                capabilities=["text_generation"],
            )
        )
        results = await registry.lookup(capabilities=["summarization"])
        assert len(results) == 1
        assert results[0].name == "capable-adapter"

    @pytest.mark.asyncio
    async def test_lookup_excludes_deregistered(self, registry):
        comp = Component(
            component_type=ComponentType.ADAPTER,
            name="will-be-removed",
        )
        await registry.register(comp)
        await registry.deregister(comp.id)
        results = await registry.lookup(component_type=ComponentType.ADAPTER)
        assert all(c.id != comp.id for c in results)

    @pytest.mark.asyncio
    async def test_deregister(self, registry):
        component = Component(
            component_type=ComponentType.ADAPTER,
            name="to-remove",
        )
        await registry.register(component)
        removed = await registry.deregister(component.id)
        assert removed is True
        found = await registry.get(component.id)
        # get() returns None for DEREGISTERED components
        assert found is None

    @pytest.mark.asyncio
    async def test_deregister_unknown_id_returns_false(self, registry):
        result = await registry.deregister(uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_get_by_id(self, registry):
        component = Component(
            component_type=ComponentType.SKILL,
            name="test-skill",
        )
        await registry.register(component)
        found = await registry.get(component.id)
        assert found is not None
        assert found.name == "test-skill"

    @pytest.mark.asyncio
    async def test_get_unknown_id_returns_none(self, registry):
        result = await registry.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_preserves_component_type(self, registry):
        component = Component(
            component_type=ComponentType.WORKFLOW,
            name="test-workflow",
        )
        await registry.register(component)
        found = await registry.get(component.id)
        assert found.component_type == ComponentType.WORKFLOW

    @pytest.mark.asyncio
    async def test_load_from_neon_returns_int(self, registry):
        # load_from_neon silently catches DB errors and returns a count
        count = await registry.load_from_neon()
        assert isinstance(count, int)
        assert count >= 0

    @pytest.mark.asyncio
    async def test_multiple_registrations_independent(self, registry):
        ids = []
        for i in range(5):
            comp = Component(
                component_type=ComponentType.TRANSPORT,
                name=f"transport-{i}",
            )
            result = await registry.register(comp)
            assert result.success is True
            ids.append(comp.id)

        for cid in ids:
            found = await registry.get(cid)
            assert found is not None
