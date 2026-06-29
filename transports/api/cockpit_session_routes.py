"""Cockpit routes for Workstation Session Runtime — Campaign 4.4.

Exposes session lifecycle and resume context to the cockpit frontend.
"""

from __future__ import annotations

import logging
from typing import Any

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

_session_runtime: Any = None


def _get_session_runtime() -> Any:
    global _session_runtime
    if _session_runtime is None:
        from substrate.operator.workstation_session_runtime import WorkstationSessionRuntime
        _session_runtime = WorkstationSessionRuntime()
    return _session_runtime


def configure(runtime: Any) -> None:
    global _session_runtime
    _session_runtime = runtime


def _build_router() -> Any:
    from fastapi import APIRouter, HTTPException

    router = APIRouter(prefix="/wk-session", tags=["wk-session"])

    @router.post("/start")
    def start_session() -> dict[str, Any]:
        captured: dict = {}

        def _do():
            rt = _get_session_runtime()
            captured.update(rt.start_session().to_dict())
            return "session started", True

        resp = governed_mutation(mutation_name="state_mutate", intent="start workstation session", execute_fn=_do, source="cockpit")
        if not resp.success:
            return resp.to_http_dict()
        return captured

    @router.post("/{session_id}/checkpoint")
    def create_checkpoint(session_id: str) -> dict[str, Any]:
        captured: dict = {}

        def _do():
            rt = _get_session_runtime()
            captured.update(rt.checkpoint(session_id).to_dict())
            return f"checkpoint created for {session_id}", True

        resp = governed_mutation(mutation_name="state_mutate", intent=f"checkpoint session {session_id}", execute_fn=_do, source="cockpit")
        if not resp.success:
            return resp.to_http_dict()
        return captured

    @router.post("/{session_id}/pause")
    def pause_session(session_id: str) -> dict[str, Any]:
        captured: dict = {}

        def _do():
            rt = _get_session_runtime()
            captured.update(rt.pause(session_id).to_dict())
            return f"session {session_id} paused", True

        resp = governed_mutation(mutation_name="state_mutate", intent=f"pause session {session_id}", execute_fn=_do, source="cockpit")
        if not resp.success:
            return resp.to_http_dict()
        return captured

    @router.post("/{session_id}/resume")
    def resume_session(session_id: str) -> dict[str, Any]:
        captured: dict = {}

        def _do():
            rt = _get_session_runtime()
            captured.update(rt.resume(session_id).to_dict())
            return f"session {session_id} resumed", True

        resp = governed_mutation(mutation_name="state_mutate", intent=f"resume session {session_id}", execute_fn=_do, source="cockpit")
        if not resp.success:
            return resp.to_http_dict()
        return captured

    @router.post("/{session_id}/close")
    def close_session(session_id: str) -> dict[str, Any]:
        captured: dict = {}

        def _do():
            rt = _get_session_runtime()
            captured.update(rt.close(session_id).to_dict())
            return f"session {session_id} closed", True

        resp = governed_mutation(mutation_name="state_mutate", intent=f"close session {session_id}", execute_fn=_do, source="cockpit")
        if not resp.success:
            return resp.to_http_dict()
        return captured

    @router.get("/active")
    def get_active_session() -> dict[str, Any]:
        rt = _get_session_runtime()
        session = rt.active_session()
        if session is None:
            return {"session": None}
        return session.to_dict()

    @router.get("/history")
    def get_session_history(limit: int = 20) -> list[dict[str, Any]]:
        rt = _get_session_runtime()
        return [s.to_dict() for s in rt.session_history(limit=limit)]

    @router.get("/{session_id}/checkpoint")
    def get_last_checkpoint(session_id: str) -> dict[str, Any]:
        rt = _get_session_runtime()
        chk = rt.last_checkpoint(session_id)
        if chk is None:
            raise HTTPException(status_code=404, detail="No checkpoint found")
        return chk.to_dict()

    return router
