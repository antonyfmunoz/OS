"""Cockpit routes for Capability Intelligence — Campaign 10.4.

Exposes capability graph, gap analysis, portfolio health, compounding score,
and bottleneck analysis to the cockpit frontend. 7 endpoints under
/capability-intelligence/ prefix. Read-only.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Lazy Singletons ───────────────────────────────────────────────────────

_capability_runtime: Any = None
_graph_engine: Any = None
_gap_engine: Any = None
_portfolio_runtime: Any = None


def _get_capability_runtime() -> Any:
    global _capability_runtime
    if _capability_runtime is None:
        try:
            from substrate.organism.capability_runtime import CapabilityRuntime

            _capability_runtime = CapabilityRuntime()
        except Exception:
            logger.debug("Failed to init CapabilityRuntime", exc_info=True)
    return _capability_runtime


def _get_graph_engine() -> Any:
    global _graph_engine
    if _graph_engine is None:
        try:
            from substrate.organism.capability_graph_engine import CapabilityGraphEngine

            _graph_engine = CapabilityGraphEngine(
                capability_runtime=_get_capability_runtime(),
            )
        except Exception:
            logger.debug("Failed to init CapabilityGraphEngine", exc_info=True)
    return _graph_engine


def _get_gap_engine() -> Any:
    global _gap_engine
    if _gap_engine is None:
        try:
            from substrate.organism.capability_gap_engine import CapabilityGapEngine
            from substrate.organism.strategic_gap_engine import GoalRegistry

            _gap_engine = CapabilityGapEngine(
                capability_runtime=_get_capability_runtime(),
                goal_registry=GoalRegistry(),
            )
        except Exception:
            logger.debug("Failed to init CapabilityGapEngine", exc_info=True)
    return _gap_engine


def _get_portfolio_runtime() -> Any:
    global _portfolio_runtime
    if _portfolio_runtime is None:
        try:
            from substrate.organism.capability_portfolio_runtime import (
                CapabilityPortfolioRuntime,
            )

            _portfolio_runtime = CapabilityPortfolioRuntime(
                capability_runtime=_get_capability_runtime(),
                graph_engine=_get_graph_engine(),
                gap_engine=_get_gap_engine(),
            )
        except Exception:
            logger.debug("Failed to init CapabilityPortfolioRuntime", exc_info=True)
    return _portfolio_runtime


# ── Router ────────────────────────────────────────────────────────────────


def get_router() -> Any:
    from fastapi import APIRouter

    router = APIRouter(
        prefix="/capability-intelligence",
        tags=["capability-intelligence"],
    )

    @router.get("/portfolio")
    def portfolio_snapshot() -> dict[str, Any]:
        rt = _get_portfolio_runtime()
        if not rt:
            return {"error": "portfolio runtime unavailable"}
        try:
            snap = rt.snapshot()
            return {"portfolio": snap.to_dict()}
        except Exception:
            logger.debug("Portfolio snapshot failed", exc_info=True)
            return {"error": "snapshot failed"}

    @router.get("/gaps")
    def all_gaps() -> dict[str, Any]:
        eng = _get_gap_engine()
        if not eng:
            return {"gaps": []}
        try:
            gaps = eng.analyze_gaps()
            return {"gaps": [g.to_dict() for g in gaps]}
        except Exception:
            logger.debug("Gap analysis failed", exc_info=True)
            return {"gaps": []}

    @router.get("/gaps/critical")
    def critical_gaps() -> dict[str, Any]:
        eng = _get_gap_engine()
        if not eng:
            return {"gaps": []}
        try:
            gaps = eng.critical_gaps()
            return {"gaps": [g.to_dict() for g in gaps]}
        except Exception:
            logger.debug("Critical gaps failed", exc_info=True)
            return {"gaps": []}

    @router.get("/graph")
    def capability_graph() -> dict[str, Any]:
        eng = _get_graph_engine()
        if not eng:
            return {"edges": [], "summary": {}}
        try:
            return {"edges": [e.to_dict() for e in eng.all_edges()], "summary": eng.summary()}
        except Exception:
            logger.debug("Graph query failed", exc_info=True)
            return {"edges": [], "summary": {}}

    @router.get("/graph/{capability_id}/tree")
    def composition_tree(capability_id: str) -> dict[str, Any]:
        eng = _get_graph_engine()
        if not eng:
            return {"error": "graph engine unavailable"}
        try:
            tree = eng.composition_tree(capability_id)
            return {"tree": tree}
        except Exception:
            logger.debug("Composition tree failed", exc_info=True)
            return {"error": "tree query failed"}

    @router.get("/compounding")
    def compounding_score() -> dict[str, Any]:
        rt = _get_portfolio_runtime()
        if not rt:
            return {"compounding_score": 0.0, "health": "unknown"}
        try:
            snap = rt.snapshot()
            return {
                "compounding_score": snap.compounding_score,
                "maturity_velocity": snap.maturity_velocity,
                "health": snap.health.value if hasattr(snap.health, "value") else str(snap.health),
                "by_maturity": snap.by_maturity,
            }
        except Exception:
            logger.debug("Compounding score failed", exc_info=True)
            return {"compounding_score": 0.0, "health": "unknown"}

    @router.get("/bottlenecks")
    def bottlenecks() -> dict[str, Any]:
        eng = _get_graph_engine()
        if not eng:
            return {"bottlenecks": []}
        try:
            return {"bottlenecks": eng.bottlenecks(10)}
        except Exception:
            logger.debug("Bottleneck query failed", exc_info=True)
            return {"bottlenecks": []}

    return router
