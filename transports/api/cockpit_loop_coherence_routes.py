"""Cockpit routes for Operating Loop Coherence Runtime — Campaign 4.3.

Exposes coherence detection, scoring, and reporting to the cockpit frontend.
"""

from __future__ import annotations

import logging
from typing import Any

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

_coherence_runtime: Any = None


def _get_coherence_runtime() -> Any:
    global _coherence_runtime
    if _coherence_runtime is None:
        from substrate.organism.operating_loop_coherence_runtime import OperatingLoopCoherenceRuntime
        _coherence_runtime = OperatingLoopCoherenceRuntime()
    return _coherence_runtime


def configure(runtime: Any) -> None:
    global _coherence_runtime
    _coherence_runtime = runtime


def _build_router() -> Any:
    from fastapi import APIRouter, HTTPException

    router = APIRouter(prefix="/loop-coherence", tags=["loop-coherence"])

    @router.get("/report")
    def get_report() -> dict[str, Any]:
        rt = _get_coherence_runtime()
        return rt.full_report().to_dict()

    @router.get("/score")
    def get_score() -> dict[str, Any]:
        rt = _get_coherence_runtime()
        return {"coherence_score": rt.coherence_score()}

    @router.get("/orphans")
    def get_orphans() -> list[dict[str, Any]]:
        rt = _get_coherence_runtime()
        return [i.to_dict() for i in rt.detect_orphans()]

    @router.get("/broken-chains")
    def get_broken_chains() -> list[dict[str, Any]]:
        rt = _get_coherence_runtime()
        return [i.to_dict() for i in rt.detect_broken_chains()]

    @router.get("/stale-approvals")
    def get_stale_approvals() -> list[dict[str, Any]]:
        rt = _get_coherence_runtime()
        return [i.to_dict() for i in rt.detect_stale_approvals()]

    @router.get("/contradictions")
    def get_contradictions() -> list[dict[str, Any]]:
        rt = _get_coherence_runtime()
        return [i.to_dict() for i in rt.detect_contradictions()]

    @router.post("/validate/{loop_id}")
    def validate_loop(loop_id: str) -> dict[str, Any]:
        rt = _get_coherence_runtime()
        loop_rt = getattr(rt, "_loops", None)
        if loop_rt is None:
            raise HTTPException(status_code=400, detail="No loop runtime configured")
        loop = None
        get_fn = getattr(loop_rt, "get", None)
        if get_fn:
            loop = get_fn(loop_id)
        if loop is None:
            raise HTTPException(status_code=404, detail="Loop not found")

        def _do_validate():
            rt.validate_loop(loop)
            return f"loop {loop_id} validated", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"validate loop coherence: {loop_id}",
            execute_fn=_do_validate,
            source="cockpit",
        )
        return resp.to_http_dict()

    return router
