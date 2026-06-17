"""Cockpit routes for Operating Loop Runtime — Campaign 4.1.

Exposes loop tracking, visibility, and lineage to the cockpit frontend.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_loop_runtime: Any = None


def _get_loop_runtime() -> Any:
    global _loop_runtime
    if _loop_runtime is None:
        from substrate.workstation.operating_loop_runtime import OperatingLoopRuntime
        _loop_runtime = OperatingLoopRuntime()
    return _loop_runtime


def configure(runtime: Any) -> None:
    global _loop_runtime
    _loop_runtime = runtime


def _build_router() -> Any:
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/operating-loop", tags=["operating-loop"])

    class TrackRequest(BaseModel):
        intent_text: str
        intent_id: str = ""

    class TransitionRequest(BaseModel):
        to_stage: str
        subsystem: str
        metadata: dict[str, Any] = {}

    @router.post("/track")
    def track_loop(req: TrackRequest) -> dict[str, Any]:
        rt = _get_loop_runtime()
        loop = rt.track(req.intent_text, intent_id=req.intent_id)
        return loop.to_dict()

    @router.post("/{loop_id}/transition")
    def record_transition(loop_id: str, req: TransitionRequest) -> dict[str, Any]:
        from substrate.workstation.operating_loop_runtime import OperatingLoopStage
        try:
            stage = OperatingLoopStage(req.to_stage)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {req.to_stage}")
        rt = _get_loop_runtime()
        loop = rt.record_transition(loop_id, stage, req.subsystem, req.metadata)
        return loop.to_dict()

    @router.get("/active")
    def get_active() -> list[dict[str, Any]]:
        rt = _get_loop_runtime()
        return [l.to_dict() for l in rt.active_loops()]

    @router.get("/completed")
    def get_completed(limit: int = 20) -> list[dict[str, Any]]:
        rt = _get_loop_runtime()
        return [l.to_dict() for l in rt.completed_loops(limit=limit)]

    @router.get("/snapshot")
    def get_snapshot() -> dict[str, Any]:
        rt = _get_loop_runtime()
        return rt.snapshot().to_dict()

    @router.get("/{loop_id}")
    def get_loop(loop_id: str) -> dict[str, Any]:
        rt = _get_loop_runtime()
        loop = rt.get(loop_id)
        if loop is None:
            raise HTTPException(status_code=404, detail="Loop not found")
        return loop.to_dict()

    @router.get("/{loop_id}/trace")
    def get_trace(loop_id: str) -> list[dict[str, Any]]:
        rt = _get_loop_runtime()
        return [t.to_dict() for t in rt.trace(loop_id)]

    @router.get("/{loop_id}/lineage")
    def get_lineage(loop_id: str) -> dict[str, Any]:
        rt = _get_loop_runtime()
        return rt.lineage_for(loop_id)

    return router
