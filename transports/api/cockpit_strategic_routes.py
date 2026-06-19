"""Cockpit routes for Strategic Context — Campaign 7.6.

Exposes the executive synthesis layer to the cockpit frontend.
12 endpoints under /strategic/ prefix. Read-only.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_strategic_context: Any = None
_priority_engine: Any = None
_risk_engine: Any = None
_recommendation_engine: Any = None
_drift_engine: Any = None
_brief_runtime: Any = None


def _get_strategic_context() -> Any:
    global _strategic_context
    if _strategic_context is None:
        from substrate.organism.strategic_context_runtime import StrategicContextRuntime
        _strategic_context = StrategicContextRuntime()
    return _strategic_context


def _get_priority_engine() -> Any:
    global _priority_engine
    if _priority_engine is None:
        from substrate.organism.priority_engine import PriorityEngine
        _priority_engine = PriorityEngine()
    return _priority_engine


def _get_risk_engine() -> Any:
    global _risk_engine
    if _risk_engine is None:
        from substrate.organism.risk_engine import RiskEngine
        _risk_engine = RiskEngine()
    return _risk_engine


def _get_recommendation_engine() -> Any:
    global _recommendation_engine
    if _recommendation_engine is None:
        from substrate.organism.recommendation_engine import RecommendationEngine
        _recommendation_engine = RecommendationEngine()
    return _recommendation_engine


def _get_drift_engine() -> Any:
    global _drift_engine
    if _drift_engine is None:
        from substrate.organism.drift_detection_engine import DriftDetectionEngine
        _drift_engine = DriftDetectionEngine()
    return _drift_engine


def _get_brief_runtime() -> Any:
    global _brief_runtime
    if _brief_runtime is None:
        from substrate.organism.executive_brief_runtime import ExecutiveBriefRuntime
        _brief_runtime = ExecutiveBriefRuntime(
            strategic_context=_get_strategic_context(),
            priority_engine=_get_priority_engine(),
            risk_engine=_get_risk_engine(),
            recommendation_engine=_get_recommendation_engine(),
            drift_engine=_get_drift_engine(),
        )
    return _brief_runtime


def configure(
    strategic_context: Any = None,
    priority_engine: Any = None,
    risk_engine: Any = None,
    recommendation_engine: Any = None,
    drift_engine: Any = None,
    brief_runtime: Any = None,
) -> None:
    global _strategic_context, _priority_engine, _risk_engine
    global _recommendation_engine, _drift_engine, _brief_runtime
    if strategic_context is not None:
        _strategic_context = strategic_context
    if priority_engine is not None:
        _priority_engine = priority_engine
    if risk_engine is not None:
        _risk_engine = risk_engine
    if recommendation_engine is not None:
        _recommendation_engine = recommendation_engine
    if drift_engine is not None:
        _drift_engine = drift_engine
    if brief_runtime is not None:
        _brief_runtime = brief_runtime


def _build_router() -> Any:
    from fastapi import APIRouter

    router = APIRouter(prefix="/strategic", tags=["strategic"])

    @router.get("/context")
    def get_context() -> dict[str, Any]:
        ctx = _get_strategic_context()
        return ctx.snapshot()

    @router.get("/health")
    def get_health() -> dict[str, Any]:
        ctx = _get_strategic_context()
        h = ctx.health()
        return {"health": h.value if hasattr(h, "value") else str(h)}

    @router.get("/priorities")
    def get_priorities() -> dict[str, Any]:
        eng = _get_priority_engine()
        items = eng.compute_priorities()
        return {"priorities": [p.to_dict() for p in items]}

    @router.get("/priorities/top")
    def get_top_priorities(limit: int = 5) -> dict[str, Any]:
        eng = _get_priority_engine()
        items = eng.top(limit=limit)
        return {"priorities": [p.to_dict() for p in items]}

    @router.get("/risks")
    def get_risks() -> dict[str, Any]:
        eng = _get_risk_engine()
        items = eng.detect_risks()
        return {"risks": [r.to_dict() for r in items]}

    @router.get("/risks/high")
    def get_high_risks() -> dict[str, Any]:
        eng = _get_risk_engine()
        items = eng.high_risks()
        return {"risks": [r.to_dict() for r in items]}

    @router.get("/recommendations")
    def get_recommendations() -> dict[str, Any]:
        eng = _get_recommendation_engine()
        items = eng.generate_recommendations()
        return {"recommendations": [r.to_dict() for r in items]}

    @router.get("/recommendations/next")
    def get_next_recommendation() -> dict[str, Any]:
        eng = _get_recommendation_engine()
        item = eng.next()
        if item is None:
            return {"recommendation": None}
        return {"recommendation": item.to_dict()}

    @router.get("/drift")
    def get_drift() -> dict[str, Any]:
        eng = _get_drift_engine()
        items = eng.detect_drift()
        return {"drift_warnings": [d.to_dict() for d in items]}

    @router.get("/drift/high")
    def get_high_drift() -> dict[str, Any]:
        eng = _get_drift_engine()
        items = eng.high_drift()
        return {"drift_warnings": [d.to_dict() for d in items]}

    @router.get("/brief")
    def get_brief() -> dict[str, Any]:
        rt = _get_brief_runtime()
        brief = rt.generate()
        return brief.to_dict()

    @router.get("/brief/summary")
    def get_brief_summary() -> dict[str, Any]:
        rt = _get_brief_runtime()
        return rt.summary()

    return router


_router = None


def get_router() -> Any:
    global _router
    if _router is None:
        _router = _build_router()
    return _router
