"""Cockpit Execution Routes — canonical execution capability surface.

Composes execution subsystems into a unified API for the Execution capability:
  - GovernedWorkRuntime (work lifecycle: submit, approve, execute)
  - ExecutionTelemetryEmitter/Store (live telemetry stream)
  - ApprovalInterceptService (governance approval gates)
  - ExecutionCoordinator (dispatch, queue, plan)

This is the canonical execution surface. Subsystem-specific route files
(operator_loop, runtime_surface, etc.) remain mounted for backward compat.

Gate 4 — Workstation Convergence. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Query

logger = logging.getLogger(__name__)

execution_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    execution_router.include_router(_router)


def _get_work_runtime() -> Any:
    if not hasattr(_get_work_runtime, "_instance"):
        try:
            from substrate.organism.governed_work_runtime import GovernedWorkRuntime
            _get_work_runtime._instance = GovernedWorkRuntime()
        except Exception:
            logger.debug("GovernedWorkRuntime unavailable")
            _get_work_runtime._instance = None
    return _get_work_runtime._instance


def _get_telemetry_store() -> Any:
    if not hasattr(_get_telemetry_store, "_instance"):
        try:
            from substrate.organism.executors.execution_telemetry import InMemoryExecutionTelemetryStore
            _get_telemetry_store._instance = InMemoryExecutionTelemetryStore()
        except Exception:
            logger.debug("ExecutionTelemetryStore unavailable")
            _get_telemetry_store._instance = None
    return _get_telemetry_store._instance


def _get_approval_service() -> Any:
    if not hasattr(_get_approval_service, "_instance"):
        try:
            from substrate.organism.executors.approval_intercept import ApprovalInterceptService
            _get_approval_service._instance = ApprovalInterceptService()
        except Exception:
            logger.debug("ApprovalInterceptService unavailable")
            _get_approval_service._instance = None
    return _get_approval_service._instance


def _get_event_spine() -> Any:
    if not hasattr(_get_event_spine, "_instance"):
        try:
            from substrate.organism.event_spine import EventSpine
            _get_event_spine._instance = EventSpine()
        except Exception:
            logger.debug("EventSpine unavailable")
            _get_event_spine._instance = None
    return _get_event_spine._instance


def _safe_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return {"value": str(obj)}


def _safe_list(items: Any) -> list[dict[str, Any]]:
    if not items:
        return []
    if not isinstance(items, (list, tuple)):
        return []
    return [_safe_dict(item) for item in items]


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.get("/execution/overview", dependencies=auth)
    def execution_overview() -> dict[str, Any]:
        """Unified execution overview — active work, pending approvals, telemetry."""
        active_work: list[dict[str, Any]] = []
        pending_approvals: list[dict[str, Any]] = []
        recent_telemetry: list[dict[str, Any]] = []

        wr = _get_work_runtime()
        if wr is not None:
            try:
                packets = wr.active_packets() if hasattr(wr, "active_packets") else []
                active_work = _safe_list(packets)
            except Exception:
                logger.debug("GovernedWorkRuntime.active_packets failed")

        ap = _get_approval_service()
        if ap is not None:
            try:
                pending = ap.pending() if hasattr(ap, "pending") else []
                pending_approvals = _safe_list(pending)
            except Exception:
                logger.debug("ApprovalInterceptService.pending failed")

        ts = _get_telemetry_store()
        if ts is not None:
            try:
                events = ts.recent(limit=10) if hasattr(ts, "recent") else []
                recent_telemetry = _safe_list(events)
            except Exception:
                logger.debug("TelemetryStore.recent failed")

        return {
            "success": True,
            "active_work": active_work,
            "active_count": len(active_work),
            "pending_approvals": pending_approvals,
            "approval_count": len(pending_approvals),
            "recent_telemetry": recent_telemetry,
        }

    @r.get("/execution/work", dependencies=auth)
    def execution_work(
        status: str = Query("", description="Filter by status"),
    ) -> dict[str, Any]:
        """All work packets with optional status filter."""
        wr = _get_work_runtime()
        if wr is None:
            return {"success": True, "packets": [], "count": 0}
        try:
            if status and hasattr(wr, "packets_by_status"):
                packets = wr.packets_by_status(status)
            elif hasattr(wr, "all_packets"):
                packets = wr.all_packets()
            else:
                packets = []
            result = _safe_list(packets)
            return {"success": True, "packets": result, "count": len(result)}
        except Exception:
            logger.debug("GovernedWorkRuntime work query failed")
            return {"success": True, "packets": [], "count": 0}

    @r.get("/execution/work/{packet_id}", dependencies=auth)
    def execution_work_detail(packet_id: str) -> dict[str, Any]:
        """Single work packet detail with telemetry and proof."""
        wr = _get_work_runtime()
        if wr is None:
            return {"success": True, "packet": {}}
        try:
            packet = wr.get_packet(packet_id) if hasattr(wr, "get_packet") else None
            if packet is None:
                return {"success": True, "packet": {}}

            detail = _safe_dict(packet)

            ts = _get_telemetry_store()
            if ts is not None and hasattr(ts, "for_execution"):
                try:
                    telem = ts.for_execution(packet_id)
                    detail["telemetry"] = _safe_list(telem)
                except Exception:
                    detail["telemetry"] = []

            return {"success": True, "packet": detail}
        except Exception:
            logger.debug("GovernedWorkRuntime.get_packet failed")
            return {"success": True, "packet": {}}

    @r.get("/execution/approvals", dependencies=auth)
    def execution_approvals() -> dict[str, Any]:
        """Pending approval intercepts requiring operator decision."""
        ap = _get_approval_service()
        if ap is None:
            return {"success": True, "approvals": [], "count": 0}
        try:
            pending = ap.pending() if hasattr(ap, "pending") else []
            result = _safe_list(pending)
            return {"success": True, "approvals": result, "count": len(result)}
        except Exception:
            logger.debug("ApprovalInterceptService.pending failed")
            return {"success": True, "approvals": [], "count": 0}

    @r.post("/execution/approvals/{approval_id}/approve", dependencies=auth)
    def approve_execution(approval_id: str) -> dict[str, Any]:
        """Approve a pending execution intercept."""
        ap = _get_approval_service()
        if ap is None:
            return {"success": False, "error": "Approval service unavailable"}
        try:
            if hasattr(ap, "approve"):
                ap.approve(approval_id)
            elif hasattr(ap, "resolve"):
                ap.resolve(approval_id, approved=True)
            return {"success": True, "approval_id": approval_id, "action": "approved"}
        except Exception as e:
            logger.debug("Approval approve failed: %s", e)
            return {"success": False, "error": str(e)}

    @r.post("/execution/approvals/{approval_id}/reject", dependencies=auth)
    def reject_execution(approval_id: str) -> dict[str, Any]:
        """Reject a pending execution intercept."""
        ap = _get_approval_service()
        if ap is None:
            return {"success": False, "error": "Approval service unavailable"}
        try:
            if hasattr(ap, "reject"):
                ap.reject(approval_id)
            elif hasattr(ap, "resolve"):
                ap.resolve(approval_id, approved=False)
            return {"success": True, "approval_id": approval_id, "action": "rejected"}
        except Exception as e:
            logger.debug("Approval reject failed: %s", e)
            return {"success": False, "error": str(e)}

    @r.get("/execution/telemetry", dependencies=auth)
    def execution_telemetry(
        execution_id: str = Query("", description="Filter by execution ID"),
        limit: int = Query(50, description="Max events"),
    ) -> dict[str, Any]:
        """Execution telemetry events."""
        ts = _get_telemetry_store()
        if ts is None:
            return {"success": True, "events": [], "count": 0}
        try:
            if execution_id and hasattr(ts, "for_execution"):
                events = ts.for_execution(execution_id)
            elif hasattr(ts, "recent"):
                events = ts.recent(limit=limit)
            else:
                events = []
            result = _safe_list(events)
            return {"success": True, "events": result, "count": len(result)}
        except Exception:
            logger.debug("TelemetryStore query failed")
            return {"success": True, "events": [], "count": 0}

    @r.get("/execution/spine-events", dependencies=auth)
    def execution_spine_events(
        limit: int = Query(30, description="Max events"),
        since: float = Query(0, description="Unix timestamp"),
    ) -> dict[str, Any]:
        """Recent organism events from the EventSpine."""
        es = _get_event_spine()
        if es is None:
            return {"success": True, "events": [], "count": 0}
        try:
            events = es.recent(limit=limit)
            if since > 0:
                events = [e for e in events if getattr(e, "timestamp", 0) >= since]
            result = _safe_list(events)
            return {"success": True, "events": result, "count": len(result)}
        except Exception:
            logger.debug("EventSpine.recent failed")
            return {"success": True, "events": [], "count": 0}

    return r
