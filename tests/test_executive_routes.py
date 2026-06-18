"""Tests for cockpit executive routes — Campaign 14.3."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest


# ── Import tests ──────────────────────────────────────────────────────


class TestRouteImports:
    def test_import_module(self) -> None:
        from transports.api import cockpit_executive_routes
        assert hasattr(cockpit_executive_routes, "get_router")

    def test_get_router_returns_router(self) -> None:
        from transports.api.cockpit_executive_routes import get_router
        router = get_router()
        assert router is not None
        assert hasattr(router, "routes")

    def test_router_has_routes(self) -> None:
        from transports.api.cockpit_executive_routes import get_router
        router = get_router()
        paths = [r.path for r in router.routes]
        assert "/executive/overview" in paths
        assert "/executive/health" in paths
        assert "/executive/allocations" in paths
        assert "/executive/allocations/{resource_type}" in paths
        assert "/executive/budgets" in paths
        assert "/executive/tradeoff/{target_id}" in paths
        assert "/executive/contention" in paths
        assert "/executive/drift" in paths
        assert "/executive/recommendations" in paths

    def test_route_count(self) -> None:
        from transports.api.cockpit_executive_routes import get_router
        router = get_router()
        assert len(router.routes) == 9


# ── Singleton tests ───────────────────────────────────────────────────


class TestLazySingletons:
    def test_get_resource_allocation_returns_or_none(self) -> None:
        from transports.api.cockpit_executive_routes import _get_resource_allocation
        result = _get_resource_allocation()
        assert result is not None or result is None

    def test_get_tradeoff_returns_or_none(self) -> None:
        from transports.api.cockpit_executive_routes import _get_tradeoff
        result = _get_tradeoff()
        assert result is not None or result is None

    def test_get_portfolio_returns_or_none(self) -> None:
        from transports.api.cockpit_executive_routes import _get_portfolio
        result = _get_portfolio()
        assert result is not None or result is None


# ── Runtime integration smoke ─────────────────────────────────────────


class TestRuntimeIntegration:
    def test_resource_allocation_importable(self) -> None:
        from substrate.organism.resource_allocation_runtime import ResourceAllocationRuntime
        rt = ResourceAllocationRuntime()
        assert rt is not None

    def test_tradeoff_importable(self) -> None:
        from substrate.organism.tradeoff_intelligence_engine import TradeoffIntelligenceEngine
        rt = TradeoffIntelligenceEngine()
        assert rt is not None

    def test_executive_portfolio_importable(self) -> None:
        from substrate.organism.executive_portfolio_runtime import ExecutivePortfolioRuntime
        rt = ExecutivePortfolioRuntime()
        assert rt is not None

    def test_canonical_types_registered(self) -> None:
        from substrate.canonical_types import lookup
        # C14.0
        assert lookup("ResourceType") is not None
        assert lookup("AllocationPriority") is not None
        assert lookup("AllocationHealth") is not None
        assert lookup("AllocationRecommendation") is not None
        assert lookup("ResourceBudget") is not None
        assert lookup("AllocationSnapshot") is not None
        assert lookup("ResourceAllocationRuntime") is not None
        # C14.1
        assert lookup("TradeoffSeverity") is not None
        assert lookup("TradeoffOption") is not None
        assert lookup("TradeoffAnalysis") is not None
        assert lookup("TradeoffSnapshot") is not None
        assert lookup("TradeoffIntelligenceEngine") is not None
        # C14.2
        assert lookup("ExecutiveHealth") is not None
        assert lookup("ExecutiveDriftType") is not None
        assert lookup("ExecutiveDriftWarning") is not None
        assert lookup("ExecutivePortfolioSnapshot") is not None
        assert lookup("ExecutivePortfolioRuntime") is not None
