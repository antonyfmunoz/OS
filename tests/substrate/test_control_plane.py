"""Tests for substrate control plane components."""

import sys

sys.path.insert(0, "/opt/OS")

import asyncio

from substrate.control_plane.identity import ConcreteIdentityResolver, IdentityResolver
from substrate.types import Identity, SignalEnvelope, SignalSource


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
