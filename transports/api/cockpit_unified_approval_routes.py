"""Cockpit routes for Unified Approval Runtime — Campaign 4.2.

Exposes the unified approval queue to the cockpit Top HUD.
"""

from __future__ import annotations

import logging
from typing import Any

from transports.api.cockpit_audit import emit_mutation_audit

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
        surface: str = "cockpit"

    class RejectRequest(BaseModel):
        approval_id: str
        source_type: str
        reason: str = ""
        decided_by: str = "operator"
        surface: str = "cockpit"

    class ClaimRequest(BaseModel):
        approval_id: str
        surface: str = "cockpit"

    class ResolveRequest(BaseModel):
        approval_id: str
        decision: str
        surface: str = "cockpit"
        input_text: str = ""
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
        emit_mutation_audit(
            "approvals",
            "approve",
            req.approval_id,
            actor=req.decided_by,
            new_value={"source_type": req.source_type},
        )
        try:
            from transports.api.cockpit_core_routes import push_mutation_event

            if push_mutation_event is not None:
                push_mutation_event("approvals", "approved", {"id": req.approval_id})
        except Exception:
            pass
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
        emit_mutation_audit(
            "approvals",
            "reject",
            req.approval_id,
            actor=req.decided_by,
            new_value={"source_type": req.source_type, "reason": req.reason},
        )
        try:
            from transports.api.cockpit_core_routes import push_mutation_event

            if push_mutation_event is not None:
                push_mutation_event("approvals", "rejected", {"id": req.approval_id})
        except Exception:
            pass
        return action.to_dict()

    @router.get("/snapshot")
    def get_snapshot() -> dict[str, Any]:
        rt = _get_approval_runtime()
        return rt.snapshot().to_dict()

    @router.get("/decisions")
    def get_decisions(limit: int = 20) -> list[dict[str, Any]]:
        rt = _get_approval_runtime()
        return [d.to_dict() for d in rt.recent_decisions(limit=limit)]

    @router.post("/claim")
    def claim_approval(req: ClaimRequest) -> dict[str, Any]:
        """Atomically claim a pending approval from a surface (CAS)."""
        try:
            from substrate.organism.approval_gate import OperatorApprovalGate

            gate = OperatorApprovalGate()
            ok = gate.claim_approval(req.approval_id, req.surface)
            return {"claimed": ok, "approval_id": req.approval_id, "surface": req.surface}
        except Exception as exc:
            logger.debug("claim_approval failed: %s", exc)
            return {"claimed": False, "error": str(exc)}

    @router.post("/resolve")
    def resolve_approval(req: ResolveRequest) -> dict[str, Any]:
        """Resolve a claimed approval (approve/reject/provide_input)."""
        try:
            from substrate.organism.approval_gate import OperatorApprovalGate

            gate = OperatorApprovalGate()
            ok = gate.resolve_approval(
                packet_id=req.approval_id,
                decision=req.decision,
                surface=req.surface,
                input_text=req.input_text,
                decided_by=req.decided_by,
            )
            emit_mutation_audit(
                "approvals",
                req.decision,
                req.approval_id,
                actor=req.decided_by,
                new_value={"surface": req.surface, "input": req.input_text[:200]},
            )
            try:
                from transports.api.cockpit_core_routes import push_mutation_event

                if push_mutation_event is not None:
                    push_mutation_event("approvals", req.decision, {
                        "id": req.approval_id,
                        "surface": req.surface,
                    })
            except Exception:
                pass
            return {"resolved": ok, "approval_id": req.approval_id, "decision": req.decision}
        except Exception as exc:
            logger.debug("resolve_approval failed: %s", exc)
            return {"resolved": False, "error": str(exc)}

    @router.get("/status/{approval_id}")
    def approval_status(approval_id: str) -> dict[str, Any]:
        """Poll current approval state from any surface."""
        try:
            from substrate.organism.approval_gate import OperatorApprovalGate

            gate = OperatorApprovalGate()
            return gate.get_approval_status(approval_id)
        except Exception as exc:
            logger.debug("approval_status failed: %s", exc)
            return {"found": False, "error": str(exc)}

    return router
