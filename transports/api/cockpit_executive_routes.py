"""Cockpit routes for Executive Intelligence — Campaign 14.3."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── Lazy Singletons ───────────────────────────────────────────────────────

_resource_allocation: Any = None
_tradeoff_engine: Any = None
_portfolio_runtime: Any = None


def _get_resource_allocation() -> Any:
    global _resource_allocation
    if _resource_allocation is None:
        try:
            from substrate.organism.resource_allocation_runtime import ResourceAllocationRuntime
            _resource_allocation = ResourceAllocationRuntime()
        except Exception:
            logger.debug("Failed to init ResourceAllocationRuntime", exc_info=True)
    return _resource_allocation


def _get_tradeoff() -> Any:
    global _tradeoff_engine
    if _tradeoff_engine is None:
        try:
            from substrate.organism.tradeoff_intelligence_engine import TradeoffIntelligenceEngine
            _tradeoff_engine = TradeoffIntelligenceEngine()
        except Exception:
            logger.debug("Failed to init TradeoffIntelligenceEngine", exc_info=True)
    return _tradeoff_engine


def _get_portfolio() -> Any:
    global _portfolio_runtime
    if _portfolio_runtime is None:
        try:
            from substrate.organism.executive_portfolio_runtime import ExecutivePortfolioRuntime
            _portfolio_runtime = ExecutivePortfolioRuntime()
        except Exception:
            logger.debug("Failed to init ExecutivePortfolioRuntime", exc_info=True)
    return _portfolio_runtime


# ── Router ────────────────────────────────────────────────────────────────


def get_router():
    from fastapi import APIRouter

    router = APIRouter(prefix="/executive", tags=["executive"])

    @router.get("/overview")
    async def executive_overview() -> dict[str, Any]:
        rt = _get_portfolio()
        if rt is None:
            return {"error": "executive portfolio not available"}
        snap = rt.snapshot()
        return snap.to_dict() if hasattr(snap, "to_dict") else snap

    @router.get("/health")
    async def executive_health() -> dict[str, Any]:
        rt = _get_portfolio()
        if rt is None:
            return {"health": "unknown", "focus_score": 0.0, "overcommitment_index": 0.0}
        h = rt.health()
        return {
            "health": h.value if hasattr(h, "value") else str(h),
            "focus_score": rt.focus_score(),
            "overcommitment_index": rt.overcommitment_index(),
        }

    @router.get("/allocations")
    async def executive_allocations() -> dict[str, Any]:
        rt = _get_resource_allocation()
        if rt is None:
            return {"recommendations": []}
        recs = rt.recommend_all()
        return {
            "recommendations": [r.to_dict() for r in recs],
        }

    @router.get("/allocations/{resource_type}")
    async def executive_allocations_by_type(resource_type: str) -> dict[str, Any]:
        rt = _get_resource_allocation()
        if rt is None:
            return {"recommendations": []}
        recs = rt.recommend(resource_type=resource_type)
        return {
            "resource_type": resource_type,
            "recommendations": [r.to_dict() for r in recs],
        }

    @router.get("/budgets")
    async def executive_budgets() -> dict[str, Any]:
        rt = _get_resource_allocation()
        if rt is None:
            return {"budgets": []}
        budgets = rt.budgets()
        return {
            "budgets": [b.to_dict() for b in budgets],
        }

    @router.get("/tradeoff/{target_id}")
    async def executive_tradeoff(target_id: str) -> dict[str, Any]:
        rt = _get_tradeoff()
        if rt is None:
            return {"error": "tradeoff engine not available"}
        analysis = rt.analyze(target_id)
        return analysis.to_dict()

    @router.get("/contention")
    async def executive_contention() -> dict[str, Any]:
        rt = _get_tradeoff()
        if rt is None:
            return {"contention": {}}
        return {"contention": rt.contention_map()}

    @router.get("/drift")
    async def executive_drift() -> dict[str, Any]:
        rt = _get_portfolio()
        if rt is None:
            return {"drift_warnings": []}
        warnings = rt.drift_warnings()
        return {
            "drift_warnings": [w.to_dict() for w in warnings],
        }

    @router.get("/recommendations")
    async def executive_recommendations() -> dict[str, Any]:
        rt = _get_portfolio()
        if rt is None:
            return {"recommendations": []}
        return {
            "recommendations": rt.top_recommendations(limit=10),
        }

    return router
