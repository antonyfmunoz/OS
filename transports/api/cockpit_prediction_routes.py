"""Cockpit routes for Prediction Intelligence — Campaign 13.3."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── Lazy Singletons ───────────────────────────────────────────────────────

_trajectory_runtime: Any = None
_scenario_engine: Any = None
_portfolio_runtime: Any = None


def _get_trajectory() -> Any:
    global _trajectory_runtime
    if _trajectory_runtime is None:
        try:
            from substrate.organism.trajectory_intelligence_runtime import TrajectoryIntelligenceRuntime
            _trajectory_runtime = TrajectoryIntelligenceRuntime()
        except Exception:
            logger.debug("Failed to init TrajectoryIntelligenceRuntime", exc_info=True)
    return _trajectory_runtime


def _get_scenarios() -> Any:
    global _scenario_engine
    if _scenario_engine is None:
        try:
            from substrate.organism.scenario_intelligence_engine import ScenarioIntelligenceEngine
            _scenario_engine = ScenarioIntelligenceEngine()
        except Exception:
            logger.debug("Failed to init ScenarioIntelligenceEngine", exc_info=True)
    return _scenario_engine


def _get_portfolio() -> Any:
    global _portfolio_runtime
    if _portfolio_runtime is None:
        try:
            from substrate.organism.prediction_portfolio_runtime import PredictionPortfolioRuntime
            _portfolio_runtime = PredictionPortfolioRuntime()
        except Exception:
            logger.debug("Failed to init PredictionPortfolioRuntime", exc_info=True)
    return _portfolio_runtime


# ── Router Factory ────────────────────────────────────────────────────────


def get_router():
    from fastapi import APIRouter

    router = APIRouter(prefix="/prediction", tags=["prediction"])

    @router.get("/overview")
    async def prediction_overview() -> dict[str, Any]:
        port = _get_portfolio()
        if port is None:
            return {"error": "Prediction portfolio unavailable"}
        try:
            snap = port.snapshot()
            return snap.to_dict() if hasattr(snap, "to_dict") else snap
        except Exception as exc:
            logger.debug("prediction overview failed: %s", exc)
            return {"error": str(exc)}

    @router.get("/forecasts")
    async def prediction_forecasts() -> dict[str, Any]:
        tr = _get_trajectory()
        if tr is None:
            return {"forecasts": []}
        try:
            forecasts = tr.forecast_all()
            return {
                "forecasts": [
                    f.to_dict() if hasattr(f, "to_dict") else f
                    for f in forecasts
                ],
                "count": len(forecasts),
            }
        except Exception as exc:
            logger.debug("prediction forecasts failed: %s", exc)
            return {"forecasts": [], "error": str(exc)}

    @router.get("/forecast/{entity_id}")
    async def prediction_forecast_detail(entity_id: str) -> dict[str, Any]:
        tr = _get_trajectory()
        if tr is None:
            return {"error": "Trajectory runtime unavailable"}
        try:
            forecasts = tr.forecast_all()
            for f in forecasts:
                eid = f.entity_id if hasattr(f, "entity_id") else f.get("entity_id", "")
                if eid == entity_id:
                    return f.to_dict() if hasattr(f, "to_dict") else f
            return {"error": f"No forecast found for {entity_id}"}
        except Exception as exc:
            logger.debug("prediction forecast detail failed: %s", exc)
            return {"error": str(exc)}

    @router.get("/scenarios")
    async def prediction_scenarios() -> dict[str, Any]:
        se = _get_scenarios()
        if se is None:
            return {"scenarios": []}
        try:
            scenarios = se.generate()
            return {
                "scenarios": [
                    s.to_dict() if hasattr(s, "to_dict") else s
                    for s in scenarios
                ],
                "count": len(scenarios),
            }
        except Exception as exc:
            logger.debug("prediction scenarios failed: %s", exc)
            return {"scenarios": [], "error": str(exc)}

    @router.get("/scenarios/best")
    async def prediction_scenarios_best() -> dict[str, Any]:
        se = _get_scenarios()
        if se is None:
            return {"error": "Scenario engine unavailable"}
        try:
            s = se.best_case()
            return s.to_dict() if hasattr(s, "to_dict") else s
        except Exception as exc:
            logger.debug("prediction best case failed: %s", exc)
            return {"error": str(exc)}

    @router.get("/scenarios/expected")
    async def prediction_scenarios_expected() -> dict[str, Any]:
        se = _get_scenarios()
        if se is None:
            return {"error": "Scenario engine unavailable"}
        try:
            s = se.expected_case()
            return s.to_dict() if hasattr(s, "to_dict") else s
        except Exception as exc:
            logger.debug("prediction expected case failed: %s", exc)
            return {"error": str(exc)}

    @router.get("/scenarios/worst")
    async def prediction_scenarios_worst() -> dict[str, Any]:
        se = _get_scenarios()
        if se is None:
            return {"error": "Scenario engine unavailable"}
        try:
            s = se.worst_case()
            return s.to_dict() if hasattr(s, "to_dict") else s
        except Exception as exc:
            logger.debug("prediction worst case failed: %s", exc)
            return {"error": str(exc)}

    @router.get("/drift")
    async def prediction_drift() -> dict[str, Any]:
        port = _get_portfolio()
        if port is None:
            return {"drift_warnings": []}
        try:
            warnings = port.drift_warnings()
            return {
                "drift_warnings": [
                    w.to_dict() if hasattr(w, "to_dict") else w
                    for w in warnings
                ],
                "count": len(warnings),
            }
        except Exception as exc:
            logger.debug("prediction drift failed: %s", exc)
            return {"drift_warnings": [], "error": str(exc)}

    @router.get("/health")
    async def prediction_health() -> dict[str, Any]:
        port = _get_portfolio()
        if port is None:
            return {"health": "unknown"}
        try:
            h = port.health()
            return {"health": h.value if hasattr(h, "value") else str(h)}
        except Exception as exc:
            logger.debug("prediction health failed: %s", exc)
            return {"health": "unknown", "error": str(exc)}

    @router.get("/uncertainty")
    async def prediction_uncertainty() -> dict[str, Any]:
        port = _get_portfolio()
        if port is None:
            return {"uncertainty_index": 1.0}
        try:
            return {"uncertainty_index": port.uncertainty_index()}
        except Exception as exc:
            logger.debug("prediction uncertainty failed: %s", exc)
            return {"uncertainty_index": 1.0, "error": str(exc)}

    return router
