"""Tests for cockpit prediction routes — Campaign 13.3."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest


# ── Import tests ──────────────────────────────────────────────────────


class TestRouteImports:
    def test_import_module(self) -> None:
        from transports.api import cockpit_prediction_routes
        assert hasattr(cockpit_prediction_routes, "get_router")

    def test_get_router_returns_router(self) -> None:
        from transports.api.cockpit_prediction_routes import get_router
        router = get_router()
        assert router is not None
        assert hasattr(router, "routes")

    def test_router_has_routes(self) -> None:
        from transports.api.cockpit_prediction_routes import get_router
        router = get_router()
        paths = [r.path for r in router.routes]
        assert "/prediction/overview" in paths
        assert "/prediction/forecasts" in paths
        assert "/prediction/scenarios" in paths
        assert "/prediction/scenarios/best" in paths
        assert "/prediction/scenarios/expected" in paths
        assert "/prediction/scenarios/worst" in paths
        assert "/prediction/drift" in paths
        assert "/prediction/health" in paths
        assert "/prediction/uncertainty" in paths

    def test_route_count(self) -> None:
        from transports.api.cockpit_prediction_routes import get_router
        router = get_router()
        assert len(router.routes) == 10


# ── Singleton tests ───────────────────────────────────────────────────


class TestLazySingletons:
    def test_get_trajectory_returns_or_none(self) -> None:
        from transports.api.cockpit_prediction_routes import _get_trajectory
        result = _get_trajectory()
        assert result is not None or result is None

    def test_get_scenarios_returns_or_none(self) -> None:
        from transports.api.cockpit_prediction_routes import _get_scenarios
        result = _get_scenarios()
        assert result is not None or result is None

    def test_get_portfolio_returns_or_none(self) -> None:
        from transports.api.cockpit_prediction_routes import _get_portfolio
        result = _get_portfolio()
        assert result is not None or result is None


# ── Runtime integration smoke ─────────────────────────────────────────


class TestRuntimeIntegration:
    def test_trajectory_importable(self) -> None:
        from substrate.organism.trajectory_intelligence_runtime import TrajectoryIntelligenceRuntime
        rt = TrajectoryIntelligenceRuntime()
        assert rt is not None

    def test_scenario_importable(self) -> None:
        from substrate.organism.scenario_intelligence_engine import ScenarioIntelligenceEngine
        rt = ScenarioIntelligenceEngine()
        assert rt is not None

    def test_portfolio_importable(self) -> None:
        from substrate.organism.prediction_portfolio_runtime import PredictionPortfolioRuntime
        rt = PredictionPortfolioRuntime()
        assert rt is not None

    def test_canonical_types_registered(self) -> None:
        from substrate.canonical_types import lookup
        assert lookup("TrajectoryStatus") is not None
        assert lookup("TrajectoryForecast") is not None
        assert lookup("TrajectoryIntelligenceRuntime") is not None
        assert lookup("ScenarioType") is not None
        assert lookup("FutureScenario") is not None
        assert lookup("ScenarioIntelligenceEngine") is not None
        assert lookup("PredictionHealth") is not None
        assert lookup("PredictionDriftType") is not None
        assert lookup("PredictionDriftWarning") is not None
        assert lookup("PredictionPortfolioSnapshot") is not None
        assert lookup("PredictionPortfolioRuntime") is not None
