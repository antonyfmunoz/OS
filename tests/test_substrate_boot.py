import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

import pytest
from substrate import Substrate
from substrate.types import ComponentType


class TestSubstrateBoot:
    @pytest.fixture
    def substrate(self):
        return Substrate()

    def test_substrate_initializes(self, substrate):
        assert substrate is not None

    def test_status_returns_healthy(self, substrate):
        status = substrate.status()
        assert status.healthy is True

    @pytest.mark.asyncio
    async def test_llm_adapter_registered(self, substrate):
        adapters = await substrate.registry.lookup(component_type=ComponentType.ADAPTER)
        names = [a.name for a in adapters]
        assert "model_router" in names

    @pytest.mark.asyncio
    async def test_execute_with_simple_signal(self, substrate):
        from substrate.types import SignalEnvelope, SignalSource

        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="hello",
            user_id="test",
            organization_id="test-org",
        )
        result = await substrate.execute(signal)
        assert result is not None
        assert result.output != ""
        assert result.trace_id is not None
