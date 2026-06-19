"""Cockpit routes for Delegation Runtime — Campaign 4.7.

Exposes delegation proposals, missions, queue, and nested orchestrator
state to the cockpit frontend.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        from substrate.organism.delegation_runtime import DelegationRuntime
        _runtime = DelegationRuntime()
    return _runtime


def configure(runtime: Any) -> None:
    global _runtime
    _runtime = runtime


def _build_router() -> Any:
    from fastapi import APIRouter, HTTPException, Request

    router = APIRouter(prefix="/delegation", tags=["delegation"])

    # ── GET endpoints ────────────────────────────────────────────

    @router.get("/summary")
    def get_summary() -> dict[str, Any]:
        return _get_runtime().summary()

    @router.get("/proposals")
    def list_proposals(status: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        return _get_runtime().list_proposals(status=status, limit=limit)

    @router.get("/proposals/{proposal_id}")
    def get_proposal(proposal_id: str) -> dict[str, Any]:
        result = _get_runtime().get_proposal(proposal_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Proposal not found")
        return result

    @router.get("/missions")
    def list_missions(status: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        return _get_runtime().list_missions(status=status, limit=limit)

    @router.get("/missions/{mission_id}")
    def get_mission(mission_id: str) -> dict[str, Any]:
        result = _get_runtime().get_mission(mission_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Mission not found")
        return result

    @router.get("/missions/{mission_id}/orchestrator")
    def get_nested_orchestrator(mission_id: str) -> dict[str, Any]:
        result = _get_runtime().get_nested_orchestrator(mission_id)
        if result is None:
            raise HTTPException(status_code=404, detail="No nested orchestrator for this mission")
        return result

    @router.get("/queue")
    def get_queue() -> dict[str, Any]:
        return _get_runtime().queue_status()

    @router.get("/active")
    def get_active() -> list[dict[str, Any]]:
        return _get_runtime().active_missions()

    # ── POST endpoints ───────────────────────────────────────────

    @router.post("/propose")
    async def propose(request: Request) -> dict[str, Any]:
        body = await request.json()
        intent = body.get("intent", "")
        clarified = body.get("clarified_intent", "")
        if not intent:
            raise HTTPException(status_code=400, detail="intent is required")

        rt = _get_runtime()
        from substrate.organism.delegation_runtime import classify_intent
        intent_type = classify_intent(intent)
        understanding = rt.explain_understanding(intent, intent_type)
        proposal = rt.propose_delegation(intent, clarified, understanding)
        return {"understanding": understanding, "proposal": proposal.to_dict()}

    @router.post("/proposals/{proposal_id}/approve")
    def approve_proposal(proposal_id: str) -> dict[str, Any]:
        result = _get_runtime().approve_proposal(proposal_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Proposal not found or not pending")
        return result.to_dict()

    @router.post("/proposals/{proposal_id}/reject")
    async def reject_proposal(proposal_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        reason = body.get("reason", "")
        result = _get_runtime().reject_proposal(proposal_id, reason)
        if result is None:
            raise HTTPException(status_code=404, detail="Proposal not found or not pending")
        return result.to_dict()

    @router.post("/missions/{mission_id}/approve-wp")
    def approve_work_packet(mission_id: str) -> dict[str, Any]:
        result = _get_runtime().approve_work_packet(mission_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Mission not found or WP not drafted")
        return result

    @router.post("/missions/{mission_id}/cancel")
    def cancel_mission(mission_id: str) -> dict[str, Any]:
        result = _get_runtime().cancel_mission(mission_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Mission not found or cannot cancel")
        return result.to_dict()

    return router
