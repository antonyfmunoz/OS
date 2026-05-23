"""Tests for EOS projection entry point.

Phase 7: First application projection on the substrate.
"""

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

import pytest
from substrate import Substrate
from substrate.types import ComponentType


class TestEOSProjection:
    @pytest.fixture
    def substrate(self):
        return Substrate()

    def test_eos_module_importable(self):
        import projections.eos

        assert projections.eos is not None

    @pytest.mark.asyncio
    async def test_eos_agents_can_register(self, substrate):
        from projections.eos.agents.ceo import register_ceo_agent

        result = await register_ceo_agent(substrate)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_registered_eos_agent_discoverable(self, substrate):
        from projections.eos.agents.ceo import register_ceo_agent

        await register_ceo_agent(substrate)
        agents = await substrate.registry.lookup(component_type=ComponentType.AGENT)
        names = [a.name for a in agents]
        assert "eos-ceo" in names


class TestEOSAgentRegistration:
    @pytest.fixture
    def substrate(self):
        return Substrate()

    @pytest.mark.asyncio
    async def test_all_eos_agents_register(self, substrate):
        from projections.eos.agents.ceo import register_ceo_agent
        from projections.eos.agents.sales import register_sales_agent
        from projections.eos.agents.marketing import register_marketing_agent

        r1 = await register_ceo_agent(substrate)
        r2 = await register_sales_agent(substrate)
        r3 = await register_marketing_agent(substrate)

        assert r1.success and r2.success and r3.success

        agents = await substrate.registry.lookup(component_type=ComponentType.AGENT)
        names = {a.name for a in agents}
        assert {"eos-ceo", "eos-sales", "eos-marketing"}.issubset(names)
