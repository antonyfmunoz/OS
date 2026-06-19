"""Cockpit routes for Orchestrator Awareness Runtime — Campaign 4.0.

Exposes the synthesized reality model to the cockpit frontend.
All endpoints are read-only.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_awareness: Any = None


def _get_awareness() -> Any:
    global _awareness
    if _awareness is None:
        from substrate.organism.orchestrator_awareness_runtime import (
            OrchestratorAwarenessRuntime,
        )
        _awareness = OrchestratorAwarenessRuntime()
    return _awareness


def configure(awareness: Any) -> None:
    global _awareness
    _awareness = awareness


def _build_router() -> Any:
    from fastapi import APIRouter, HTTPException

    router = APIRouter(prefix="/orchestrator", tags=["orchestrator-awareness"])

    @router.get("/context")
    def get_context() -> dict[str, Any]:
        rt = _get_awareness()
        return rt.context().to_dict()

    @router.get("/snapshot")
    def get_snapshot() -> dict[str, Any]:
        rt = _get_awareness()
        return rt.snapshot().to_dict()

    @router.get("/awareness/{domain}")
    def get_domain_awareness(domain: str) -> dict[str, Any]:
        rt = _get_awareness()
        method_name = f"{domain}_awareness"
        fn = getattr(rt, method_name, None)
        if fn is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown awareness domain: {domain}",
            )
        return fn()

    @router.get("/health")
    def get_health() -> list[dict[str, Any]]:
        rt = _get_awareness()
        return [d.to_dict() for d in rt.domain_health()]

    @router.get("/score")
    def get_score() -> dict[str, Any]:
        rt = _get_awareness()
        return {"awareness_score": rt.awareness_score()}

    return router
