"""Phase 13: Execution Coordinator route handlers.

Extracted from cockpit_operator_loop_routes.py to respect
the 3000-line file limit.
"""

from __future__ import annotations

import logging
from fastapi import Request

logger = logging.getLogger(__name__)


def _get_execution_coordinator():
    from substrate.organism.execution_coordinator import get_execution_coordinator

    return get_execution_coordinator()


def _audit_log(action: str, details: dict | None = None) -> None:
    logger.info("AUDIT [execcoord] %s %s", action, details or {})


async def execcoord_state(request: Request) -> dict:
    try:
        coord = _get_execution_coordinator()
        snap = coord.snapshot()
        return {
            "success": True,
            "snapshot": snap.to_dict(),
            "queue": [p.to_dict() for p in coord.queue_state()],
            "active": [p.to_dict() for p in coord.active_plans()],
            "awaiting_approval": [p.to_dict() for p in coord.awaiting_approval()],
            "history": [p.to_dict() for p in coord.plan_history(20)],
            "lifecycle": [e.to_dict() for e in coord.recent_lifecycle(50)],
            "executors": [e.to_dict() for e in coord.executors()],
        }
    except Exception as exc:
        logger.error("execcoord state failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def execcoord_queue(request: Request) -> dict:
    try:
        coord = _get_execution_coordinator()
        return {"success": True, "queue": [p.to_dict() for p in coord.queue_state()]}
    except Exception as exc:
        logger.error("execcoord queue failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def execcoord_active(request: Request) -> dict:
    try:
        coord = _get_execution_coordinator()
        return {"success": True, "active": [p.to_dict() for p in coord.active_plans()]}
    except Exception as exc:
        logger.error("execcoord active failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def execcoord_awaiting(request: Request) -> dict:
    try:
        coord = _get_execution_coordinator()
        return {
            "success": True,
            "awaiting": [p.to_dict() for p in coord.awaiting_approval()],
        }
    except Exception as exc:
        logger.error("execcoord awaiting failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def execcoord_history(request: Request) -> dict:
    try:
        coord = _get_execution_coordinator()
        limit = int(request.query_params.get("limit", "50"))
        return {
            "success": True,
            "history": [p.to_dict() for p in coord.plan_history(limit)],
        }
    except Exception as exc:
        logger.error("execcoord history failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def execcoord_lifecycle(request: Request) -> dict:
    try:
        coord = _get_execution_coordinator()
        plan_id = request.query_params.get("plan_id", "")
        if plan_id:
            events = coord.lifecycle_for_plan(plan_id)
        else:
            limit = int(request.query_params.get("limit", "50"))
            events = coord.recent_lifecycle(limit)
        return {"success": True, "events": [e.to_dict() for e in events]}
    except Exception as exc:
        logger.error("execcoord lifecycle failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def execcoord_executors(request: Request) -> dict:
    try:
        coord = _get_execution_coordinator()
        return {
            "success": True,
            "executors": [e.to_dict() for e in coord.executors()],
        }
    except Exception as exc:
        logger.error("execcoord executors failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def execcoord_create(request: Request) -> dict:
    try:
        body = await request.json()
        wp_id = body.get("source_workpacket_id", "")
        target = body.get("target_executor", "")
        if not wp_id or not target:
            return {"success": False, "error": "source_workpacket_id and target_executor required"}
        coord = _get_execution_coordinator()
        plan = coord.create_plan(
            wp_id, target,
            profile_id=body.get("profile_id", ""),
            session_id=body.get("session_id", ""),
            execution_mode=body.get("execution_mode", "asynchronous"),
            priority=body.get("priority", "normal"),
            risk_class=body.get("risk_class", "low"),
            description=body.get("description", ""),
        )
        _audit_log("plan_created", {
            "plan_id": plan.execution_plan_id,
            "workpacket_id": wp_id,
            "target": target,
        })
        return {"success": True, "plan": plan.to_dict()}
    except Exception as exc:
        logger.error("execcoord create failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def execcoord_approve(request: Request) -> dict:
    try:
        body = await request.json()
        plan_id = body.get("execution_plan_id", "")
        if not plan_id:
            return {"success": False, "error": "execution_plan_id required"}
        coord = _get_execution_coordinator()
        plan = coord.approve_plan(plan_id)
        if not plan:
            return {"success": False, "error": "plan not found"}
        _audit_log("plan_approved", {"plan_id": plan_id})
        return {"success": True, "plan": plan.to_dict()}
    except Exception as exc:
        logger.error("execcoord approve failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def execcoord_deny(request: Request) -> dict:
    try:
        body = await request.json()
        plan_id = body.get("execution_plan_id", "")
        reason = body.get("reason", "")
        if not plan_id:
            return {"success": False, "error": "execution_plan_id required"}
        coord = _get_execution_coordinator()
        plan = coord.deny_plan(plan_id, reason=reason)
        if not plan:
            return {"success": False, "error": "plan not found"}
        _audit_log("plan_denied", {"plan_id": plan_id, "reason": reason})
        return {"success": True, "plan": plan.to_dict()}
    except Exception as exc:
        logger.error("execcoord deny failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def execcoord_enqueue(request: Request) -> dict:
    try:
        body = await request.json()
        plan_id = body.get("execution_plan_id", "")
        if not plan_id:
            return {"success": False, "error": "execution_plan_id required"}
        coord = _get_execution_coordinator()
        plan = coord.enqueue_plan(plan_id)
        if not plan:
            return {"success": False, "error": "enqueue failed (approval required or invalid state)"}
        _audit_log("plan_enqueued", {"plan_id": plan_id})
        return {"success": True, "plan": plan.to_dict()}
    except Exception as exc:
        logger.error("execcoord enqueue failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def execcoord_dispatch(request: Request) -> dict:
    try:
        coord = _get_execution_coordinator()
        plan = coord.dispatch_next()
        if not plan:
            return {"success": False, "error": "no dispatchable plan in queue"}
        _audit_log("plan_dispatched", {
            "plan_id": plan.execution_plan_id,
            "target": plan.target_executor,
        })
        return {"success": True, "plan": plan.to_dict()}
    except Exception as exc:
        logger.error("execcoord dispatch failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def execcoord_cancel(request: Request) -> dict:
    try:
        body = await request.json()
        plan_id = body.get("execution_plan_id", "")
        if not plan_id:
            return {"success": False, "error": "execution_plan_id required"}
        coord = _get_execution_coordinator()
        plan = coord.cancel_plan(plan_id)
        if not plan:
            return {"success": False, "error": "cancel failed (plan not found or already terminal)"}
        _audit_log("plan_cancelled", {"plan_id": plan_id})
        return {"success": True, "plan": plan.to_dict()}
    except Exception as exc:
        logger.error("execcoord cancel failed: %s", exc)
        return {"success": False, "error": str(exc)}
