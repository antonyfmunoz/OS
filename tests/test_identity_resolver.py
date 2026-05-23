"""Tests for ConcreteIdentityResolver.

Phase 6 invariant verification.
"""
from __future__ import annotations

import pytest

from substrate.control_plane.identity import ConcreteIdentityResolver
from substrate.types import Identity, SignalEnvelope, SignalSource, SignalUrgency, Modality


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_signal(**kwargs) -> SignalEnvelope:
    defaults = dict(
        source=SignalSource.USER,
        urgency=SignalUrgency.NORMAL,
        modality=Modality.TEXT,
        content="what should I focus on today",
        user_id="user-abc",
        organization_id="org-xyz",
        venture_id="venture-123",
        authority_tier=3,
    )
    defaults.update(kwargs)
    return SignalEnvelope(**defaults)


# ---------------------------------------------------------------------------
# Identity resolution
# ---------------------------------------------------------------------------

class TestIdentityResolver:
    @pytest.fixture
    def resolver(self):
        return ConcreteIdentityResolver()

    @pytest.mark.asyncio
    async def test_resolve_returns_identity(self, resolver):
        signal = _make_signal()
        identity = await resolver.resolve(signal)
        assert isinstance(identity, Identity)

    @pytest.mark.asyncio
    async def test_resolve_propagates_user_id(self, resolver):
        signal = _make_signal(user_id="user-test-42")
        identity = await resolver.resolve(signal)
        assert identity.user_id == "user-test-42"

    @pytest.mark.asyncio
    async def test_resolve_propagates_org_id(self, resolver):
        signal = _make_signal(organization_id="org-test-99")
        identity = await resolver.resolve(signal)
        assert identity.organization_id == "org-test-99"

    @pytest.mark.asyncio
    async def test_resolve_propagates_venture_id(self, resolver):
        signal = _make_signal(venture_id="venture-test-77")
        identity = await resolver.resolve(signal)
        assert identity.venture_id == "venture-test-77"

    @pytest.mark.asyncio
    async def test_resolve_returns_non_empty_ai_name(self, resolver):
        signal = _make_signal()
        identity = await resolver.resolve(signal)
        assert identity.ai_name  # not empty

    @pytest.mark.asyncio
    async def test_resolve_autonomy_level_in_range(self, resolver):
        signal = _make_signal()
        identity = await resolver.resolve(signal)
        assert 0 <= identity.autonomy_level <= 4

    @pytest.mark.asyncio
    async def test_resolve_business_stage_non_empty(self, resolver):
        signal = _make_signal()
        identity = await resolver.resolve(signal)
        assert identity.business_stage

    @pytest.mark.asyncio
    async def test_resolve_stable_without_db(self, resolver):
        # Must not raise even if state modules fail
        signal = _make_signal()
        try:
            identity = await resolver.resolve(signal)
            assert identity is not None
        except Exception as exc:
            pytest.fail(f"resolve() raised unexpectedly: {exc}")
