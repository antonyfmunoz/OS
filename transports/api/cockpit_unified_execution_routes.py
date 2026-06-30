"""Unified Execution Surface Routes — single API surface across all execution subsystems.

Exposes: active/queued/blocked streams, pending approvals, recent completions,
stream detail, approve/reject actions, full snapshot.

Campaign 3.3 — Unified Execution Surface. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from transports.api.cockpit_audit import emit_mutation_audit
from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

unified_execution_router: APIRouter = APIRouter()
_configured = False


class ApproveRequest(BaseModel):
    approval_id: str
    source_system: str


class RejectRequest(BaseModel):
    approval_id: str
    source_system: str
    reason: str = ""


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    unified_execution_router.include_router(_router)


def _get_runtime() -> Any:
    if not hasattr(_get_runtime, "_instance"):
        from substrate.workstation.unified_execution_surface_runtime import (
            UnifiedExecutionSurfaceRuntime,
        )

        _get_runtime._instance = UnifiedExecutionSurfaceRuntime()
    return _get_runtime._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.get("/unified-execution/snapshot", dependencies=auth)
    def snapshot() -> dict[str, Any]:
        return _get_runtime().snapshot().to_dict()

    @r.get("/unified-execution/active", dependencies=auth)
    def active_streams() -> list[dict[str, Any]]:
        return [s.to_dict() for s in _get_runtime().active_streams()]

    @r.get("/unified-execution/queued", dependencies=auth)
    def queued_streams() -> list[dict[str, Any]]:
        return [s.to_dict() for s in _get_runtime().queued_streams()]

    @r.get("/unified-execution/blocked", dependencies=auth)
    def blocked_streams() -> list[dict[str, Any]]:
        return [s.to_dict() for s in _get_runtime().blocked_streams()]

    @r.get("/unified-execution/approvals", dependencies=auth)
    def pending_approvals() -> list[dict[str, Any]]:
        return [a.to_dict() for a in _get_runtime().pending_approvals()]

    @r.get("/unified-execution/completions", dependencies=auth)
    def recent_completions(limit: int = 20) -> list[dict[str, Any]]:
        return [s.to_dict() for s in _get_runtime().recent_completions(limit=limit)]

    @r.get("/unified-execution/stream/{stream_id}", dependencies=auth)
    def stream_detail(stream_id: str) -> dict[str, Any]:
        return _get_runtime().stream_detail(stream_id)

    @r.post("/unified-execution/approve", dependencies=auth)
    def approve(req: ApproveRequest) -> dict[str, Any]:
        def _do():
            result = _get_runtime().approve(req.approval_id, req.source_system)
            emit_mutation_audit(
                "approvals",
                "approve",
                req.approval_id,
                new_value={"source_system": req.source_system},
                surface="unified_execution",
            )
            try:
                from transports.api.cockpit_core_routes import push_mutation_event

                if push_mutation_event is not None:
                    push_mutation_event("execution", "approved", {"id": req.approval_id})
            except Exception:
                pass
            return f"approved {req.approval_id}", True

        resp = governed_mutation(
            mutation_name="approval_decide",
            intent=f"approve execution {req.approval_id}",
            execute_fn=_do,
            source="cockpit",
            metadata={"approval_id": req.approval_id, "source_system": req.source_system},
        )
        return resp.to_http_dict()

    @r.post("/unified-execution/reject", dependencies=auth)
    def reject(req: RejectRequest) -> dict[str, Any]:
        def _do():
            result = _get_runtime().reject(req.approval_id, req.source_system, req.reason)
            emit_mutation_audit(
                "approvals",
                "reject",
                req.approval_id,
                new_value={"source_system": req.source_system, "reason": req.reason},
                surface="unified_execution",
            )
            try:
                from transports.api.cockpit_core_routes import push_mutation_event

                if push_mutation_event is not None:
                    push_mutation_event("execution", "rejected", {"id": req.approval_id})
            except Exception:
                pass
            return f"rejected {req.approval_id}", True

        resp = governed_mutation(
            mutation_name="approval_decide",
            intent=f"reject execution {req.approval_id}: {req.reason}",
            execute_fn=_do,
            source="cockpit",
            metadata={"approval_id": req.approval_id, "source_system": req.source_system, "reason": req.reason},
        )
        return resp.to_http_dict()

    return r
