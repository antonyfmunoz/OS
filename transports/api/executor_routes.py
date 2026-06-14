"""Phase 14: Executor Runtime route handlers.

Extracted to dedicated file to keep cockpit_operator_loop_routes.py
under the 3000-line limit.  Pattern matches execcoord_routes.py (P13).
"""

from __future__ import annotations

import logging
from fastapi import Request

logger = logging.getLogger(__name__)


def _get_executor_runtime():
    from substrate.organism.executor_runtime import get_executor_runtime

    return get_executor_runtime()


def _audit_log(action: str, details: dict | None = None) -> None:
    logger.info("AUDIT [executor] %s %s", action, details or {})


# ── GET handlers ────────────────────────────────────────────────


async def executor_state(request: Request) -> dict:
    """GET /executor/state — full runtime snapshot."""
    try:
        rt = _get_executor_runtime()
        snap = rt.snapshot()
        return {"success": True, **snap.to_dict()}
    except Exception as exc:
        logger.error("executor state failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def executor_requests_all(request: Request) -> dict:
    """GET /executor/requests — all requests."""
    try:
        rt = _get_executor_runtime()
        reqs = rt._request_store.all_requests()
        return {
            "success": True,
            "requests": [r.to_dict() for r in reqs],
            "total": len(reqs),
        }
    except Exception as exc:
        logger.error("executor requests failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def executor_active(request: Request) -> dict:
    """GET /executor/active — currently active requests."""
    try:
        rt = _get_executor_runtime()
        active = rt.active_requests()
        return {
            "success": True,
            "active": [r.to_dict() for r in active],
            "count": len(active),
        }
    except Exception as exc:
        logger.error("executor active failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def executor_results_all(request: Request) -> dict:
    """GET /executor/results — all results."""
    try:
        rt = _get_executor_runtime()
        results = rt.all_results()
        return {
            "success": True,
            "results": [r.to_dict() for r in results],
            "total": len(results),
        }
    except Exception as exc:
        logger.error("executor results failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def executor_failures(request: Request) -> dict:
    """GET /executor/failures — failed requests."""
    try:
        rt = _get_executor_runtime()
        failed = rt.failed_requests()
        return {
            "success": True,
            "failures": [r.to_dict() for r in failed],
            "count": len(failed),
        }
    except Exception as exc:
        logger.error("executor failures failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def executor_history(request: Request) -> dict:
    """GET /executor/history — terminal requests."""
    try:
        rt = _get_executor_runtime()
        history = rt.request_history(limit=100)
        return {
            "success": True,
            "history": [r.to_dict() for r in history],
            "count": len(history),
        }
    except Exception as exc:
        logger.error("executor history failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def executor_lifecycle(request: Request) -> dict:
    """GET /executor/lifecycle — recent lifecycle events."""
    try:
        rt = _get_executor_runtime()
        events = rt.recent_lifecycle(limit=100)
        return {
            "success": True,
            "events": [e.to_dict() for e in events],
            "count": len(events),
        }
    except Exception as exc:
        logger.error("executor lifecycle failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def executor_types(request: Request) -> dict:
    """GET /executor/types — registered executor types."""
    try:
        rt = _get_executor_runtime()
        types = rt.registered_executor_types()
        return {
            "success": True,
            "executor_types": types,
            "count": len(types),
        }
    except Exception as exc:
        logger.error("executor types failed: %s", exc)
        return {"success": False, "error": str(exc)}


# ── POST handlers ───────────────────────────────────────────────


async def executor_create(request: Request) -> dict:
    """POST /executor/create — create an executor request."""
    try:
        body = await request.json()
        rt = _get_executor_runtime()
        req = rt.create_request(
            execution_plan_id=body.get("execution_plan_id", ""),
            executor_type=body.get("executor_type", "workstation"),
            risk_class=body.get("risk_class", "low"),
            description=body.get("description", ""),
            profile_id=body.get("profile_id", ""),
            session_id=body.get("session_id", ""),
            priority=body.get("priority", "normal"),
            workpacket=body.get("workpacket"),
            metadata=body.get("metadata"),
        )
        _audit_log("create_request", {
            "request_id": req.request_id,
            "plan_id": req.execution_plan_id,
            "executor_type": req.executor_type,
        })
        return {"success": True, **req.to_dict()}
    except Exception as exc:
        logger.error("executor create failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def executor_run(request: Request) -> dict:
    """POST /executor/run — run full lifecycle for a request."""
    try:
        body = await request.json()
        request_id = body.get("request_id", "")
        rt = _get_executor_runtime()
        result = rt.run_lifecycle(request_id)
        if result:
            _audit_log("run_lifecycle", {
                "request_id": request_id,
                "success": result.success,
            })
            return {"success": True, **result.to_dict()}
        return {"success": False, "error": "Lifecycle failed or request not found"}
    except Exception as exc:
        logger.error("executor run failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def executor_approve(request: Request) -> dict:
    """POST /executor/approve — approve a pending request."""
    try:
        body = await request.json()
        request_id = body.get("request_id", "")
        rt = _get_executor_runtime()
        req = rt.approve_request(request_id)
        if req:
            _audit_log("approve_request", {"request_id": request_id})
            return {"success": True, **req.to_dict()}
        return {"success": False, "error": "Request not found"}
    except Exception as exc:
        logger.error("executor approve failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def executor_deny(request: Request) -> dict:
    """POST /executor/deny — deny a pending request."""
    try:
        body = await request.json()
        request_id = body.get("request_id", "")
        reason = body.get("reason", "")
        rt = _get_executor_runtime()
        req = rt.deny_request(request_id, reason)
        if req:
            _audit_log("deny_request", {"request_id": request_id, "reason": reason})
            return {"success": True, **req.to_dict()}
        return {"success": False, "error": "Request not found"}
    except Exception as exc:
        logger.error("executor deny failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def executor_cancel(request: Request) -> dict:
    """POST /executor/cancel — cancel a request."""
    try:
        body = await request.json()
        request_id = body.get("request_id", "")
        rt = _get_executor_runtime()
        req = rt.cancel_request(request_id)
        if req:
            _audit_log("cancel_request", {"request_id": request_id})
            return {"success": True, **req.to_dict()}
        return {"success": False, "error": "Request not found or already terminal"}
    except Exception as exc:
        logger.error("executor cancel failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def executor_monitor(request: Request) -> dict:
    """POST /executor/monitor — get monitoring data for a request."""
    try:
        body = await request.json()
        request_id = body.get("request_id", "")
        rt = _get_executor_runtime()
        mon = rt.monitor_request(request_id)
        return {"success": True, **mon}
    except Exception as exc:
        logger.error("executor monitor failed: %s", exc)
        return {"success": False, "error": str(exc)}
