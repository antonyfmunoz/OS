"""Phase 15C: Approval Intercept route handlers.

Provides cockpit endpoints for listing, approving, and rejecting
runtime execution intercepts.

Routes:
  GET  /approvals/pending — all pending intercepts
  GET  /approvals/{approval_id} — single intercept details
  POST /approvals/{approval_id}/approve — approve an intercept
  POST /approvals/{approval_id}/reject — reject an intercept
"""

from __future__ import annotations

import logging

from fastapi import Request

logger = logging.getLogger(__name__)


def _get_service():
    from substrate.organism.executors.approval_intercept import (
        get_approval_intercept_service,
    )
    return get_approval_intercept_service()


# ── GET handlers ────────────────────────────────────────────────


async def approvals_pending(request: Request) -> dict:
    """GET /approvals/pending — all pending approval intercepts."""
    try:
        svc = _get_service()
        pending = svc.pending()
        return {
            "success": True,
            "approvals": [i.to_dict() for i in pending],
            "count": len(pending),
        }
    except Exception as exc:
        logger.error("approvals pending failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def approval_detail(request: Request) -> dict:
    """GET /approvals/{approval_id} — single intercept details."""
    try:
        approval_id = request.path_params.get("approval_id", "")
        svc = _get_service()
        intercept = svc.get(approval_id)
        if not intercept:
            return {"success": False, "error": "Not found"}
        return {
            "success": True,
            "approval": intercept.to_dict(),
        }
    except Exception as exc:
        logger.error("approval detail failed: %s", exc)
        return {"success": False, "error": str(exc)}


# ── POST handlers ──────────────────────────────────────────────


async def approval_approve(request: Request) -> dict:
    """POST /approvals/{approval_id}/approve — approve an intercept."""
    try:
        approval_id = request.path_params.get("approval_id", "")
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        operator_id = body.get("operator_id", "operator")

        svc = _get_service()
        result = svc.approve(approval_id, operator_id=operator_id)
        if not result:
            return {"success": False, "error": "Not found or not pending"}
        return {
            "success": True,
            "approval": result.to_dict(),
        }
    except Exception as exc:
        logger.error("approval approve failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def approval_reject(request: Request) -> dict:
    """POST /approvals/{approval_id}/reject — reject an intercept."""
    try:
        approval_id = request.path_params.get("approval_id", "")
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        operator_id = body.get("operator_id", "operator")
        reason = body.get("reason", "")

        svc = _get_service()
        result = svc.reject(approval_id, reason=reason, operator_id=operator_id)
        if not result:
            return {"success": False, "error": "Not found or not pending"}
        return {
            "success": True,
            "approval": result.to_dict(),
        }
    except Exception as exc:
        logger.error("approval reject failed: %s", exc)
        return {"success": False, "error": str(exc)}
