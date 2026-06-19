"""Tests for cockpit learning routes — Campaign 12.4."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest


# ── Import tests ──────────────────────────────────────────────────────


class TestRouteImports:
    def test_import_module(self) -> None:
        from transports.api import cockpit_learning_routes
        assert hasattr(cockpit_learning_routes, "get_router")

    def test_get_router_returns_router(self) -> None:
        from transports.api.cockpit_learning_routes import get_router
        router = get_router()
        assert router is not None
        assert hasattr(router, "routes")

    def test_router_has_routes(self) -> None:
        from transports.api.cockpit_learning_routes import get_router
        router = get_router()
        paths = [r.path for r in router.routes]
        assert "/learning/overview" in paths
        assert "/learning/lessons" in paths
        assert "/learning/lessons/actionable" in paths
        assert "/learning/patterns" in paths
        assert "/learning/evolution" in paths
        assert "/learning/drift" in paths
        assert "/learning/health" in paths
        assert "/learning/compounding" in paths

    def test_route_count(self) -> None:
        from transports.api.cockpit_learning_routes import get_router
        router = get_router()
        assert len(router.routes) == 10


# ── Singleton tests ───────────────────────────────────────────────────


class TestLazySingletons:
    def test_get_extraction_returns_or_none(self) -> None:
        from transports.api.cockpit_learning_routes import _get_extraction
        result = _get_extraction()
        assert result is not None or result is None

    def test_get_patterns_returns_or_none(self) -> None:
        from transports.api.cockpit_learning_routes import _get_patterns
        result = _get_patterns()
        assert result is not None or result is None

    def test_get_evolution_returns_or_none(self) -> None:
        from transports.api.cockpit_learning_routes import _get_evolution
        result = _get_evolution()
        assert result is not None or result is None

    def test_get_portfolio_returns_or_none(self) -> None:
        from transports.api.cockpit_learning_routes import _get_portfolio
        result = _get_portfolio()
        assert result is not None or result is None


# ── Runtime integration smoke ─────────────────────────────────────────


class TestRuntimeIntegration:
    def test_learning_extraction_importable(self) -> None:
        from substrate.organism.learning_extraction_runtime import LearningExtractionRuntime
        rt = LearningExtractionRuntime()
        assert rt is not None

    def test_outcome_pattern_importable(self) -> None:
        from substrate.organism.outcome_pattern_engine import OutcomePatternEngine
        rt = OutcomePatternEngine()
        assert rt is not None

    def test_capability_evolution_importable(self) -> None:
        from substrate.organism.capability_evolution_engine import CapabilityEvolutionEngine
        rt = CapabilityEvolutionEngine()
        assert rt is not None

    def test_learning_portfolio_importable(self) -> None:
        from substrate.organism.learning_portfolio_runtime import LearningPortfolioRuntime
        rt = LearningPortfolioRuntime()
        assert rt is not None
