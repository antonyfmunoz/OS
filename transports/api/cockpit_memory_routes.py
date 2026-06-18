"""Cockpit routes for Decision Intelligence & Strategic Memory — Campaign 9.6.

Exposes decision registry, lineage, assumptions, validity, memory, and impact
to the cockpit frontend. 12 endpoints under /memory/ prefix. Read-only.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Lazy Singletons ───────────────────────────────────────────────────────

_decision_registry: Any = None
_lineage_engine: Any = None
_assumption_tracking: Any = None
_validity_engine: Any = None
_memory_engine: Any = None
_impact_engine: Any = None


def _get_decision_registry() -> Any:
    global _decision_registry
    if _decision_registry is None:
        try:
            from substrate.organism.decision_registry import DecisionRegistry
            from substrate.organism.reality_graph import RealityGraph

            rg = RealityGraph()
            _decision_registry = DecisionRegistry(reality_graph=rg)
        except Exception:
            logger.debug("Failed to init DecisionRegistry", exc_info=True)
            from substrate.organism.decision_registry import DecisionRegistry

            _decision_registry = DecisionRegistry()
    return _decision_registry


def _get_assumption_tracking() -> Any:
    global _assumption_tracking
    if _assumption_tracking is None:
        try:
            from substrate.organism.assumption_tracking_runtime import (
                AssumptionTrackingRuntime,
            )

            _assumption_tracking = AssumptionTrackingRuntime()
        except Exception:
            logger.debug("Failed to init AssumptionTrackingRuntime", exc_info=True)
    return _assumption_tracking


def _get_lineage_engine() -> Any:
    global _lineage_engine
    if _lineage_engine is None:
        try:
            from substrate.organism.decision_lineage_engine import (
                DecisionLineageEngine,
            )

            _lineage_engine = DecisionLineageEngine(
                decision_registry=_get_decision_registry(),
            )
        except Exception:
            logger.debug("Failed to init DecisionLineageEngine", exc_info=True)
    return _lineage_engine


def _get_validity_engine() -> Any:
    global _validity_engine
    if _validity_engine is None:
        try:
            from substrate.organism.decision_validity_engine import (
                DecisionValidityEngine,
            )

            _validity_engine = DecisionValidityEngine(
                decision_registry=_get_decision_registry(),
                assumption_tracking=_get_assumption_tracking(),
            )
        except Exception:
            logger.debug("Failed to init DecisionValidityEngine", exc_info=True)
    return _validity_engine


def _get_memory_engine() -> Any:
    global _memory_engine
    if _memory_engine is None:
        try:
            from substrate.organism.strategic_memory_engine import (
                StrategicMemoryEngine,
            )

            _memory_engine = StrategicMemoryEngine(
                decision_registry=_get_decision_registry(),
                assumption_tracking=_get_assumption_tracking(),
                validity_engine=_get_validity_engine(),
            )
        except Exception:
            logger.debug("Failed to init StrategicMemoryEngine", exc_info=True)
    return _memory_engine


def _get_impact_engine() -> Any:
    global _impact_engine
    if _impact_engine is None:
        try:
            from substrate.organism.decision_impact_engine import (
                DecisionImpactEngine,
            )

            _impact_engine = DecisionImpactEngine(
                decision_registry=_get_decision_registry(),
                decision_lineage=_get_lineage_engine(),
                assumption_tracking=_get_assumption_tracking(),
            )
        except Exception:
            logger.debug("Failed to init DecisionImpactEngine", exc_info=True)
    return _impact_engine


def configure(
    decision_registry: Any = None,
    lineage_engine: Any = None,
    assumption_tracking: Any = None,
    validity_engine: Any = None,
    memory_engine: Any = None,
    impact_engine: Any = None,
) -> None:
    global _decision_registry, _lineage_engine, _assumption_tracking
    global _validity_engine, _memory_engine, _impact_engine
    if decision_registry is not None:
        _decision_registry = decision_registry
    if lineage_engine is not None:
        _lineage_engine = lineage_engine
    if assumption_tracking is not None:
        _assumption_tracking = assumption_tracking
    if validity_engine is not None:
        _validity_engine = validity_engine
    if memory_engine is not None:
        _memory_engine = memory_engine
    if impact_engine is not None:
        _impact_engine = impact_engine


# ── Router ────────────────────────────────────────────────────────────────


def get_router() -> Any:
    from fastapi import APIRouter, Query

    router = APIRouter(prefix="/memory", tags=["memory"])

    # ── Decision endpoints ────────────────────────────────────────────

    @router.get("/decisions")
    def list_decisions(status: str | None = None) -> dict[str, Any]:
        reg = _get_decision_registry()
        if not reg:
            return {"decisions": []}
        decisions = reg.list_decisions(status=status)
        return {"decisions": [d.to_dict() for d in decisions]}

    @router.get("/decisions/{decision_id}")
    def get_decision(decision_id: str) -> dict[str, Any]:
        reg = _get_decision_registry()
        if not reg:
            return {"error": "registry unavailable"}
        d = reg.get(decision_id)
        if not d:
            return {"error": "not found"}
        return {"decision": d.to_dict()}

    @router.get("/decisions/{decision_id}/lineage")
    def get_lineage(decision_id: str) -> dict[str, Any]:
        engine = _get_lineage_engine()
        if not engine:
            return {"error": "lineage engine unavailable"}
        try:
            lineage = engine.trace(decision_id)
            return {"lineage": lineage.to_dict()}
        except Exception:
            logger.debug("Lineage trace failed", exc_info=True)
            return {"error": "trace failed"}

    @router.get("/decisions/{decision_id}/validity")
    def get_validity(decision_id: str) -> dict[str, Any]:
        engine = _get_validity_engine()
        if not engine:
            return {"error": "validity engine unavailable"}
        try:
            v = engine.evaluate(decision_id)
            return {"validity": v.to_dict()}
        except Exception:
            logger.debug("Validity evaluation failed", exc_info=True)
            return {"error": "evaluation failed"}

    @router.get("/decisions/{decision_id}/impact")
    def get_impact(decision_id: str) -> dict[str, Any]:
        engine = _get_impact_engine()
        if not engine:
            return {"error": "impact engine unavailable"}
        try:
            impact = engine.assess(decision_id)
            return {"impact": impact.to_dict()}
        except Exception:
            logger.debug("Impact assessment failed", exc_info=True)
            return {"error": "assessment failed"}

    # ── Assumption endpoints ──────────────────────────────────────────

    @router.get("/assumptions")
    def list_assumptions(status: str | None = None) -> dict[str, Any]:
        tracking = _get_assumption_tracking()
        if not tracking:
            return {"assumptions": []}
        assumptions = tracking.list_assumptions(status=status)
        return {"assumptions": [a.to_dict() for a in assumptions]}

    @router.get("/assumptions/invalidated")
    def list_invalidated() -> dict[str, Any]:
        tracking = _get_assumption_tracking()
        if not tracking:
            return {"assumptions": []}
        assumptions = tracking.invalidated()
        return {"assumptions": [a.to_dict() for a in assumptions]}

    # ── Memory endpoints ──────────────────────────────────────────────

    @router.get("/snapshot")
    def get_snapshot() -> dict[str, Any]:
        engine = _get_memory_engine()
        if not engine:
            return {"snapshot": None}
        current = engine.get_current()
        return {"snapshot": current.to_dict() if current else None}

    @router.get("/timeline")
    def get_timeline(since: float = 0.0) -> dict[str, Any]:
        engine = _get_memory_engine()
        if not engine:
            return {"events": []}
        return {"events": engine.decision_timeline(since=since)}

    @router.get("/history")
    def get_history(limit: int = 10) -> dict[str, Any]:
        engine = _get_memory_engine()
        if not engine:
            return {"snapshots": []}
        snapshots = engine.get_history(limit=limit)
        return {"snapshots": [s.to_dict() for s in snapshots]}

    # ── Aggregation ───────────────────────────────────────────────────

    @router.get("/summary")
    def get_summary() -> dict[str, Any]:
        parts: dict[str, Any] = {}
        reg = _get_decision_registry()
        if reg:
            parts["decisions"] = reg.summary()
        tracking = _get_assumption_tracking()
        if tracking:
            parts["assumptions"] = tracking.summary()
        validity = _get_validity_engine()
        if validity:
            parts["validity"] = validity.summary()
        memory = _get_memory_engine()
        if memory:
            parts["memory"] = memory.summary()
        impact = _get_impact_engine()
        if impact:
            parts["impact"] = impact.summary()
        return parts

    @router.get("/health")
    def get_health() -> dict[str, Any]:
        health: dict[str, Any] = {"overall": "unknown"}
        reg = _get_decision_registry()
        if reg:
            s = reg.summary()
            health["total_decisions"] = s.get("total", 0)
        tracking = _get_assumption_tracking()
        if tracking:
            s = tracking.summary()
            health["total_assumptions"] = s.get("total", 0)
            health["invalidated_assumptions"] = s.get("invalidated_count", 0)
        validity = _get_validity_engine()
        if validity:
            s = validity.summary()
            health["at_risk_decisions"] = s.get("at_risk_count", 0)
            health["invalid_decisions"] = s.get("invalid_count", 0)

        at_risk = health.get("at_risk_decisions", 0)
        invalid = health.get("invalid_decisions", 0)
        inv_asm = health.get("invalidated_assumptions", 0)

        if invalid > 0 or inv_asm > 3:
            health["overall"] = "degraded"
        elif at_risk > 0 or inv_asm > 0:
            health["overall"] = "watch"
        elif health.get("total_decisions", 0) > 0:
            health["overall"] = "healthy"

        return health

    return router
