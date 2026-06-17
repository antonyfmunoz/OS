"""Cockpit routes for Unified Approval Runtime — Campaign 4.2.

Exposes the unified approval queue to the cockpit Top HUD.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_approval_runtime: Any = None


def _get_approval_runtime() -> Any:
    global _approval_runtime
    if _approval_runtime is None:
        from substrate.workstation.unified_approval_runtime import UnifiedApprovalRuntime
        _approval_runtime = UnifiedApprovalRuntime()
    return _approval_runtime


def configure(runtime: Any) -> None:
    global _approval_runtime
    _approval_runtime = runtime


def _build_router() -> Any:
    from fastapi import APIRouter
    from pydantic import BaseModel

    router = APIRouter(prefix="/unified-approval", tags=["unified-approval"])

    class ApproveRequest(BaseModel):
        approval_id: str
        source_type: str
        decided_by: str = "operator"

    class RejectRequest(BaseModel):
        approval_id: str
        source_type: str
        reason: str = ""
        decided_by: str = "operator"

    @router.get("/pending")
    def get_pending(source_type: str = "") -> list[dict[str, Any]]:
        rt = _get_approval_runtime()
        return [a.to_dict() for a in rt.pending(source_type=source_type)]

    @router.get("/by-urgency")
    def get_by_urgency(limit: int = 10) -> list[dict[str, Any]]:
        rt = _get_approval_runtime()
        return [a.to_dict() for a in rt.by_urgency(limit=limit)]

    @router.post("/approve")
    def approve_item(req: ApproveRequest) -> dict[str, Any]:
        rt = _get_approval_runtime()
        action = rt.approve(
            approval_id=req.approval_id,
            source_type=req.source_type,
            decided_by=req.decided_by,
        )
        return action.to_dict()

    @router.post("/reject")
    def reject_item(req: RejectRequest) -> dict[str, Any]:
        rt = _get_approval_runtime()
        action = rt.reject(
            approval_id=req.approval_id,
            source_type=req.source_type,
            reason=req.reason,
            decided_by=req.decided_by,
        )
        return action.to_dict()

    @router.get("/snapshot")
    def get_snapshot() -> dict[str, Any]:
        rt = _get_approval_runtime()
        return rt.snapshot().to_dict()

    @router.get("/decisions")
    def get_decisions(limit: int = 20) -> list[dict[str, Any]]:
        rt = _get_approval_runtime()
        return [d.to_dict() for d in rt.recent_decisions(limit=limit)]

    return router
