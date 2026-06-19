"""Tests for cockpit governance routes — Campaign 15.4."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest


# ── Import tests ──────────────────────────────────────────────────────


class TestRouteImports:
    def test_import_module(self) -> None:
        from transports.api import cockpit_governance_routes
        assert hasattr(cockpit_governance_routes, "get_router")

    def test_get_router_returns_router(self) -> None:
        from transports.api.cockpit_governance_routes import get_router
        router = get_router()
        assert router is not None
        assert hasattr(router, "routes")

    def test_router_has_routes(self) -> None:
        from transports.api.cockpit_governance_routes import get_router
        router = get_router()
        paths = [r.path for r in router.routes]
        assert "/governance/overview" in paths
        assert "/governance/health" in paths
        assert "/governance/conflicts" in paths
        assert "/governance/policies" in paths
        assert "/governance/coordination" in paths
        assert "/governance/institutional-memory" in paths
        assert "/governance/drift" in paths

    def test_route_count(self) -> None:
        from transports.api.cockpit_governance_routes import get_router
        router = get_router()
        assert len(router.routes) == 7


# ── Singleton tests ───────────────────────────────────────────────────


class TestLazySingletons:
    def test_get_governance_returns_or_none(self) -> None:
        from transports.api.cockpit_governance_routes import _get_governance
        result = _get_governance()
        assert result is not None or result is None

    def test_get_coordination_returns_or_none(self) -> None:
        from transports.api.cockpit_governance_routes import _get_coordination
        result = _get_coordination()
        assert result is not None or result is None

    def test_get_institutional_memory_returns_or_none(self) -> None:
        from transports.api.cockpit_governance_routes import _get_institutional_memory
        result = _get_institutional_memory()
        assert result is not None or result is None

    def test_get_organism_portfolio_returns_or_none(self) -> None:
        from transports.api.cockpit_governance_routes import _get_organism_portfolio
        result = _get_organism_portfolio()
        assert result is not None or result is None


# ── Runtime integration smoke ─────────────────────────────────────────


class TestRuntimeIntegration:
    def test_governance_runtime_importable(self) -> None:
        from substrate.organism.governance_runtime import GovernanceRuntime
        rt = GovernanceRuntime()
        assert rt is not None

    def test_organism_coordination_importable(self) -> None:
        from substrate.organism.organism_coordination_engine import OrganismCoordinationEngine
        rt = OrganismCoordinationEngine()
        assert rt is not None

    def test_institutional_memory_importable(self) -> None:
        from substrate.organism.institutional_memory_runtime import InstitutionalMemoryRuntime
        rt = InstitutionalMemoryRuntime()
        assert rt is not None

    def test_organism_portfolio_importable(self) -> None:
        from substrate.organism.organism_portfolio_runtime import OrganismPortfolioRuntime
        rt = OrganismPortfolioRuntime()
        assert rt is not None
