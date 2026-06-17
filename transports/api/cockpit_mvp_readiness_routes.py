"""Cockpit routes for MVP Readiness Runtime — Campaign 4.5.

Exposes 14-dimension MVP readiness scoring to the cockpit frontend.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_mvp_runtime: Any = None


def _get_mvp_runtime() -> Any:
    global _mvp_runtime
    if _mvp_runtime is None:
        from substrate.workstation.mvp_readiness_runtime import MVPReadinessRuntime
        _mvp_runtime = MVPReadinessRuntime()
    return _mvp_runtime


def configure(runtime: Any) -> None:
    global _mvp_runtime
    _mvp_runtime = runtime


def _build_router() -> Any:
    from fastapi import APIRouter, HTTPException

    router = APIRouter(prefix="/mvp-readiness", tags=["mvp-readiness"])

    @router.get("/assess")
    def assess() -> dict[str, Any]:
        rt = _get_mvp_runtime()
        return rt.assess().to_dict()

    @router.get("/score")
    def get_score() -> dict[str, float]:
        rt = _get_mvp_runtime()
        return {"score": rt.score()}

    @router.get("/dimension/{name}")
    def get_dimension(name: str) -> dict[str, Any]:
        rt = _get_mvp_runtime()
        return rt.dimension(name).to_dict()

    @router.get("/blockers")
    def get_blockers() -> list[str]:
        rt = _get_mvp_runtime()
        return rt.blockers()

    @router.get("/escape-points")
    def get_escape_points() -> list[dict[str, Any]]:
        rt = _get_mvp_runtime()
        return [e.to_dict() for e in rt.escape_points()]

    @router.get("/next")
    def get_next(limit: int = 5) -> list[str]:
        rt = _get_mvp_runtime()
        return rt.recommended_next(limit=limit)

    return router
