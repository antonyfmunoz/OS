"""Cockpit routes for Work Intelligence — Campaign 11.3.

Exposes work readiness, delegation feasibility, portfolio health,
velocity metrics, and drift detection to the cockpit frontend.
9 endpoints under /work-intelligence/ prefix. Read-only.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Lazy Singletons ───────────────────────────────────────────────────────

_readiness_runtime: Any = None
_delegation_runtime: Any = None
_portfolio_runtime: Any = None


def _get_readiness() -> Any:
    global _readiness_runtime
    if _readiness_runtime is None:
        try:
            from substrate.organism.work_readiness_runtime import WorkReadinessRuntime
            _readiness_runtime = WorkReadinessRuntime()
        except Exception:
            logger.debug("Failed to init WorkReadinessRuntime", exc_info=True)
    return _readiness_runtime


def _get_delegation() -> Any:
    global _delegation_runtime
    if _delegation_runtime is None:
        try:
            from substrate.organism.delegation_readiness_runtime import DelegationReadinessRuntime
            _delegation_runtime = DelegationReadinessRuntime(
                work_readiness=_get_readiness(),
            )
        except Exception:
            logger.debug("Failed to init DelegationReadinessRuntime", exc_info=True)
    return _delegation_runtime


def _get_portfolio() -> Any:
    global _portfolio_runtime
    if _portfolio_runtime is None:
        try:
            from substrate.organism.work_portfolio_runtime import WorkPortfolioRuntime
            _portfolio_runtime = WorkPortfolioRuntime(
                work_readiness=_get_readiness(),
                delegation_readiness=_get_delegation(),
            )
        except Exception:
            logger.debug("Failed to init WorkPortfolioRuntime", exc_info=True)
    return _portfolio_runtime


def configure(
    readiness: Any = None,
    delegation: Any = None,
    portfolio: Any = None,
) -> None:
    """Override lazy singletons for testing."""
    global _readiness_runtime, _delegation_runtime, _portfolio_runtime
    if readiness is not None:
        _readiness_runtime = readiness
    if delegation is not None:
        _delegation_runtime = delegation
    if portfolio is not None:
        _portfolio_runtime = portfolio


# ── Router ────────────────────────────────────────────────────────────────


def get_router() -> Any:
    from fastapi import APIRouter

    router = APIRouter(
        prefix="/work-intelligence",
        tags=["work-intelligence"],
    )

    @router.get("/overview")
    def overview() -> dict[str, Any]:
        rt = _get_portfolio()
        if not rt:
            return {"error": "portfolio runtime unavailable"}
        try:
            snap = rt.snapshot()
            return {"portfolio": snap.to_dict()}
        except Exception:
            logger.debug("Portfolio snapshot failed", exc_info=True)
            return {"error": "snapshot failed"}

    @router.get("/ready")
    def ready_work() -> dict[str, Any]:
        rt = _get_readiness()
        if not rt:
            return {"ready": []}
        try:
            items = rt.ready_work()
            return {"ready": [a.to_dict() for a in items], "count": len(items)}
        except Exception:
            logger.debug("Ready work query failed", exc_info=True)
            return {"ready": []}

    @router.get("/blocked")
    def blocked_work() -> dict[str, Any]:
        rt = _get_readiness()
        if not rt:
            return {"blocked": []}
        try:
            items = rt.blocked_work()
            return {"blocked": [a.to_dict() for a in items], "count": len(items)}
        except Exception:
            logger.debug("Blocked work query failed", exc_info=True)
            return {"blocked": []}

    @router.get("/blocked/{work_id}")
    def blocked_detail(work_id: str) -> dict[str, Any]:
        rt = _get_readiness()
        if not rt:
            return {"error": "readiness runtime unavailable"}
        try:
            assessment = rt.assess(work_id)
            return {"assessment": assessment.to_dict()}
        except Exception:
            logger.debug("Assessment failed for %s", work_id, exc_info=True)
            return {"error": "assessment failed"}

    @router.get("/delegation")
    def delegation_overview() -> dict[str, Any]:
        rt = _get_delegation()
        if not rt:
            return {"error": "delegation runtime unavailable"}
        try:
            snap = rt.snapshot()
            return {"delegation": snap.to_dict()}
        except Exception:
            logger.debug("Delegation snapshot failed", exc_info=True)
            return {"error": "snapshot failed"}

    @router.get("/delegation/{work_id}")
    def delegation_detail(work_id: str) -> dict[str, Any]:
        rt = _get_delegation()
        if not rt:
            return {"error": "delegation runtime unavailable"}
        try:
            dr = rt.assess(work_id=work_id)
            return {"delegation": dr.to_dict()}
        except Exception:
            logger.debug("Delegation assess failed for %s", work_id, exc_info=True)
            return {"error": "assessment failed"}

    @router.get("/drift")
    def drift_warnings() -> dict[str, Any]:
        rt = _get_portfolio()
        if not rt:
            return {"drift": []}
        try:
            warnings = rt.detect_drift()
            return {"drift": [w.to_dict() for w in warnings], "count": len(warnings)}
        except Exception:
            logger.debug("Drift detection failed", exc_info=True)
            return {"drift": []}

    @router.get("/velocity")
    def velocity_metrics() -> dict[str, Any]:
        rt = _get_portfolio()
        if not rt:
            return {"velocity": {}}
        try:
            return {"velocity": rt.velocity()}
        except Exception:
            logger.debug("Velocity query failed", exc_info=True)
            return {"velocity": {}}

    @router.get("/health")
    def health_summary() -> dict[str, Any]:
        rt = _get_portfolio()
        if not rt:
            return {"health": "unknown"}
        try:
            snap = rt.snapshot()
            h = snap.health
            return {
                "health": h.value if hasattr(h, "value") else str(h),
                "capability_health": snap.capability_health,
                "goals_at_risk": snap.goals_at_risk,
                "goals_at_risk_count": len(snap.goals_at_risk),
            }
        except Exception:
            logger.debug("Health query failed", exc_info=True)
            return {"health": "unknown"}

    return router
