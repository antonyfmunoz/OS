"""Cockpit routes for Operating Loop Runtime — Campaign 4.1.

Exposes loop tracking, visibility, and lineage to the cockpit frontend.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)


# MODULE scope: PEP 563 string annotations resolve against module globals;
# nested inside _build_router() these models were invisible to FastAPI and the
# body params degraded to required query params (422 loc ["query","req"] —
# same defect family as the unified-approval routes, field run 20260722).
class TrackRequest(BaseModel):
    intent_text: str
    intent_id: str = ""


class TransitionRequest(BaseModel):
    to_stage: str
    subsystem: str
    metadata: dict[str, Any] = {}


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

    router = APIRouter(prefix="/operating-loop", tags=["operating-loop"])

    @router.post("/track")
    def track_loop(req: TrackRequest) -> dict[str, Any]:
        def _do_track():
            rt = _get_loop_runtime()
            loop = rt.track(req.intent_text, intent_id=req.intent_id)
            return f"loop tracked: {loop.loop_id}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"track operating loop: {req.intent_text[:80]}",
            execute_fn=_do_track,
            source="cockpit",
        )
        return resp.to_http_dict()

    @router.post("/{loop_id}/transition")
    def record_transition(loop_id: str, req: TransitionRequest) -> dict[str, Any]:
        from substrate.workstation.operating_loop_runtime import OperatingLoopStage

        try:
            stage = OperatingLoopStage(req.to_stage)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {req.to_stage}")

        def _do_transition():
            rt = _get_loop_runtime()
            loop = rt.record_transition(loop_id, stage, req.subsystem, req.metadata)
            return f"transition to {req.to_stage}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"transition loop {loop_id} to {req.to_stage}",
            execute_fn=_do_transition,
            source="cockpit",
        )
        return resp.to_http_dict()

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
