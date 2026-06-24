"""Approval Intercept route handlers.

Provides cockpit endpoints for listing, approving, and rejecting
runtime execution intercepts. Field names are mapped to cockpit
conventions for frontend consumption.

Routes:
  GET  /approvals/pending — all pending intercepts
  GET  /approvals/{approval_id} — single intercept details
  POST /approvals/{approval_id}/approve — approve an intercept
  POST /approvals/{approval_id}/reject — reject an intercept
  POST /approvals/{approval_id}/deny — alias for reject
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request

logger = logging.getLogger(__name__)


def _get_service():
    from substrate.organism.executors.approval_intercept import (
        get_approval_intercept_service,
    )
    return get_approval_intercept_service()


def _authenticated_operator(request: Request) -> str:
    """Extract operator identity from auth middleware, never from body."""
    return getattr(request.state, "clerk_user_id", None) or "authenticated-operator"


def _serialize_for_cockpit(approval_dict: dict[str, Any]) -> dict[str, Any]:
    """Map Python field names to cockpit TS interface names."""
    return {
        "id": approval_dict.get("approval_id", ""),
        "risk_level": approval_dict.get("risk_class", ""),
        "agent": approval_dict.get("executor_type", ""),
        "description": approval_dict.get("reason", ""),
        "created_at": approval_dict.get("requested_at", ""),
        "status": approval_dict.get("status", ""),
        "operation": approval_dict.get("operation", ""),
        "details": approval_dict.get("details", {}),
        "execution_id": approval_dict.get("execution_id", ""),
        "expires_at": approval_dict.get("expires_at", 0),
        "decided_by": approval_dict.get("decided_by", ""),
        "decided_at": approval_dict.get("decided_at", 0),
        "rejection_reason": approval_dict.get("rejection_reason", ""),
        "resolution_metadata": approval_dict.get("resolution_metadata", {}),
    }


# ── GET handlers ────────────────────────────────────────────────


async def approvals_pending(request: Request) -> list[dict[str, Any]]:
    """GET /approvals/pending — all pending approval intercepts.

    Returns flat list matching the cockpit Approval[] interface.
    """
    try:
        svc = _get_service()
        pending = svc.pending()
        return [_serialize_for_cockpit(i.to_dict()) for i in pending]
    except Exception as exc:
        logger.error("approvals pending failed: %s", exc)
        return []


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
            "approval": _serialize_for_cockpit(intercept.to_dict()),
        }
    except Exception as exc:
        logger.error("approval detail failed: %s", exc)
        return {"success": False, "error": str(exc)}


# ── POST handlers ──────────────────────────────────────────────


async def approval_approve(request: Request) -> dict:
    """POST /approvals/{approval_id}/approve — approve an intercept.

    Accepts optional JSON body: { "metadata": { ... } }
    Metadata is stored on the intercept for downstream consumers
    (e.g., device onboarding role/type override).
    """
    try:
        approval_id = request.path_params.get("approval_id", "")
        operator_id = _authenticated_operator(request)

        body: dict[str, Any] = {}
        content_type = request.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            try:
                body = await request.json()
            except Exception:
                body = {}

        metadata = body.get("metadata")

        svc = _get_service()
        result = svc.approve(
            approval_id,
            operator_id=operator_id,
            metadata=metadata,
        )
        if not result:
            return {"success": False, "error": "Not found or not pending"}
        return {
            "success": True,
            "approval": _serialize_for_cockpit(result.to_dict()),
        }
    except Exception as exc:
        logger.error("approval approve failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def approval_reject(request: Request) -> dict:
    """POST /approvals/{approval_id}/reject — reject an intercept."""
    try:
        approval_id = request.path_params.get("approval_id", "")
        body: dict[str, Any] = {}
        content_type = request.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            try:
                body = await request.json()
            except Exception:
                body = {}
        operator_id = _authenticated_operator(request)
        reason = body.get("reason", "") or body.get("note", "")

        svc = _get_service()
        result = svc.reject(approval_id, reason=reason, operator_id=operator_id)
        if not result:
            return {"success": False, "error": "Not found or not pending"}
        return {
            "success": True,
            "approval": _serialize_for_cockpit(result.to_dict()),
        }
    except Exception as exc:
        logger.error("approval reject failed: %s", exc)
        return {"success": False, "error": str(exc)}


# /deny is an alias for /reject — used by cockpit frontend
approval_deny = approval_reject
