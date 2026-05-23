# tests/test_identity_resolver.py
import sys
from pathlib import Path
_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

import pytest
from substrate.types import Identity, SignalEnvelope, SignalSource
from substrate.control_plane.identity import ConcreteIdentityResolver


def _make_signal(**kwargs) -> SignalEnvelope:
    defaults = dict(
        source=SignalSource.USER,
        content="hello",
        user_id="test-user",
        organization_id="test-org",
    )
    defaults.update(kwargs)
    return SignalEnvelope(**defaults)


class TestIdentityResolver:
    @pytest.fixture
    def resolver(self):
        return ConcreteIdentityResolver()

    @pytest.mark.asyncio
    async def test_resolve_returns_identity(self, resolver):
        signal = _make_signal()
        identity = await resolver.resolve(signal)
        assert isinstance(identity, Identity)
        assert identity.user_id == "test-user"
        assert identity.organization_id == "test-org"

    @pytest.mark.asyncio
    async def test_resolve_has_ai_name(self, resolver):
        signal = _make_signal()
        identity = await resolver.resolve(signal)
        assert isinstance(identity.ai_name, str)
        assert len(identity.ai_name) > 0

    @pytest.mark.asyncio
    async def test_resolve_has_personality(self, resolver):
        signal = _make_signal()
        identity = await resolver.resolve(signal)
        assert isinstance(identity.ai_personality, str)
        assert len(identity.ai_personality) > 0

    @pytest.mark.asyncio
    async def test_resolve_preserves_venture_id(self, resolver):
        signal = _make_signal(venture_id="test-venture")
        identity = await resolver.resolve(signal)
        assert identity.venture_id == "test-venture"

    @pytest.mark.asyncio
    async def test_resolve_fallback_defaults(self, resolver):
        signal = _make_signal()
        identity = await resolver.resolve(signal)
        assert identity.autonomy_level >= 0
        assert identity.business_stage != ""

    def test_foundation_values_exist(self):
        resolver = ConcreteIdentityResolver()
        assert hasattr(resolver, 'FOUNDATION_VALUES')
        values = resolver.FOUNDATION_VALUES
        assert "reality" in values
        assert "intelligence" in values
        assert "personalization" in values
        assert "execution" in values
