"""Cockpit routes for Organism Governance — Campaign 15.4."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── Lazy Singletons ───────────────────────────────────────────────────────

_governance_runtime: Any = None
_coordination_engine: Any = None
_institutional_memory: Any = None
_organism_portfolio: Any = None


def _get_governance() -> Any:
    global _governance_runtime
    if _governance_runtime is None:
        try:
            from substrate.organism.governance_runtime import GovernanceRuntime

            _governance_runtime = GovernanceRuntime()
        except Exception:
            logger.debug("Failed to init GovernanceRuntime", exc_info=True)
    return _governance_runtime


def _get_coordination() -> Any:
    global _coordination_engine
    if _coordination_engine is None:
        try:
            from substrate.organism.organism_coordination_engine import (
                OrganismCoordinationEngine,
            )

            _coordination_engine = OrganismCoordinationEngine()
        except Exception:
            logger.debug("Failed to init OrganismCoordinationEngine", exc_info=True)
    return _coordination_engine


def _get_institutional_memory() -> Any:
    global _institutional_memory
    if _institutional_memory is None:
        try:
            from substrate.organism.institutional_memory_runtime import (
                InstitutionalMemoryRuntime,
            )

            _institutional_memory = InstitutionalMemoryRuntime()
        except Exception:
            logger.debug("Failed to init InstitutionalMemoryRuntime", exc_info=True)
    return _institutional_memory


def _get_organism_portfolio() -> Any:
    global _organism_portfolio
    if _organism_portfolio is None:
        try:
            from substrate.organism.organism_portfolio_runtime import (
                OrganismPortfolioRuntime,
            )

            _organism_portfolio = OrganismPortfolioRuntime()
        except Exception:
            logger.debug("Failed to init OrganismPortfolioRuntime", exc_info=True)
    return _organism_portfolio


# ── Router ────────────────────────────────────────────────────────────────


def get_router():
    from fastapi import APIRouter

    router = APIRouter(prefix="/governance", tags=["governance"])

    @router.get("/overview")
    async def governance_overview() -> dict[str, Any]:
        rt = _get_organism_portfolio()
        if rt is None:
            return {"error": "organism portfolio not available"}
        snap = rt.snapshot()
        return snap.to_dict() if hasattr(snap, "to_dict") else snap

    @router.get("/health")
    async def governance_health() -> dict[str, Any]:
        rt = _get_organism_portfolio()
        if rt is None:
            return {"health": "unknown", "coherence_score": 0.0}
        h = rt.health()
        return {
            "health": h.value if hasattr(h, "value") else str(h),
            "coherence_score": rt.coherence_score(),
        }

    @router.get("/conflicts")
    async def governance_conflicts() -> dict[str, Any]:
        rt = _get_governance()
        if rt is None:
            return {"conflicts": []}
        conflicts = rt.active_conflicts()
        return {
            "conflicts": [c.to_dict() for c in conflicts],
        }

    @router.get("/policies")
    async def governance_policies() -> dict[str, Any]:
        rt = _get_governance()
        if rt is None:
            return {"policies": []}
        policies = rt.active_policies()
        return {
            "policies": [p.to_dict() for p in policies],
        }

    @router.get("/coordination")
    async def governance_coordination() -> dict[str, Any]:
        rt = _get_coordination()
        if rt is None:
            return {"error": "coordination engine not available"}
        snap = rt.snapshot()
        return snap.to_dict() if hasattr(snap, "to_dict") else snap

    @router.get("/institutional-memory")
    async def governance_institutional_memory() -> dict[str, Any]:
        rt = _get_institutional_memory()
        if rt is None:
            return {"error": "institutional memory not available"}
        snap = rt.snapshot()
        return snap.to_dict() if hasattr(snap, "to_dict") else snap

    @router.get("/drift")
    async def governance_drift() -> dict[str, Any]:
        rt = _get_organism_portfolio()
        if rt is None:
            return {"drift_warnings": []}
        warnings = rt.drift_warnings()
        return {
            "drift_warnings": [w.to_dict() for w in warnings],
        }

    return router
