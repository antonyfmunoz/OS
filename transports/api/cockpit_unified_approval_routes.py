"""Cockpit routes for Unified Approval Runtime — Campaign 4.2.

Exposes the unified approval queue to the cockpit Top HUD.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from transports.api.cockpit_audit import emit_mutation_audit
from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

_approval_runtime: Any = None
_SOURCE_OWNED_GOVERNED_APPROVALS = {"objective_plan", "execution_authorization"}


def _get_approval_runtime() -> Any:
    global _approval_runtime
    if _approval_runtime is None:
        from substrate.workstation.unified_approval_runtime import UnifiedApprovalRuntime

        # WP-P1-007: wire real sources so the cockpit pending list actually
        # spans channels. Previously this was UnifiedApprovalRuntime() with zero
        # sources — every collector iterated None and the list was always empty.
        # Each source is best-effort: a missing one degrades the view, it does
        # not blank it.
        approval_gate = None
        approval_intercept = None
        try:
            from substrate.organism.approval_gate import OperatorApprovalGate

            approval_gate = OperatorApprovalGate()
        except Exception:  # noqa: BLE001
            approval_gate = None
        try:
            from substrate.organism.executors.approval_intercept import (
                get_approval_intercept_service,
            )

            approval_intercept = get_approval_intercept_service()
        except Exception:  # noqa: BLE001
            approval_intercept = None

        _approval_runtime = UnifiedApprovalRuntime(
            approval_gate=approval_gate,
            approval_intercept=approval_intercept,
        )
    return _approval_runtime


def configure(runtime: Any) -> None:
    global _approval_runtime
    _approval_runtime = runtime


def _source_owns_governed_decision(source_type: str) -> bool:
    """True when the routed source already performs the canonical governed write.

    Objective-plan acceptance and Wave 2 execution authorization each have their
    own source-specific mutation (`objective_plan_decision` and
    `execution_authorization_decision`). Wrapping them in the generic
    `approval_decide` mutation adds a second gate in front of the real authority
    and can block the source before its fail-closed contract runs.
    """
    return source_type in _SOURCE_OWNED_GOVERNED_APPROVALS


# Request models live at MODULE scope. With `from __future__ import
# annotations` (PEP 563) every annotation is a string that FastAPI resolves
# against module globals — a model class defined inside _build_router() is
# invisible to that lookup, so FastAPI silently degraded each body param to a
# required QUERY param and every JSON call 422'd with loc ["query","req"]
# (Wave-1 field run 20260722T185410Z captured the response body; the
# approve/reject endpoints had NEVER accepted a request body).
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


def _build_router() -> Any:
    from fastapi import APIRouter, HTTPException

    router = APIRouter(prefix="/unified-approval", tags=["unified-approval"])

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
        captured: dict = {}

        def _do_approve():
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
            captured.update(action.to_dict())
            return f"approved {req.approval_id}", True

        if _source_owns_governed_decision(req.source_type):
            _out, _ok = _do_approve()
            if captured.get("action") != "approved":
                raise HTTPException(status_code=409, detail=captured)
            return captured

        resp = governed_mutation(
            mutation_name="approval_decide",
            intent=f"unified approve {req.approval_id}",
            execute_fn=_do_approve,
            source="cockpit",
        )
        if not resp.success:
            return resp.to_http_dict()
        return captured

    @router.post("/reject")
    def reject_item(req: RejectRequest) -> dict[str, Any]:
        captured: dict = {}

        def _do_reject():
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
            captured.update(action.to_dict())
            return f"rejected {req.approval_id}", True

        if _source_owns_governed_decision(req.source_type):
            _out, _ok = _do_reject()
            if captured.get("action") != "rejected":
                raise HTTPException(status_code=409, detail=captured)
            return captured

        resp = governed_mutation(
            mutation_name="approval_decide",
            intent=f"unified reject {req.approval_id}: {req.reason[:80]}",
            execute_fn=_do_reject,
            source="cockpit",
        )
        if not resp.success:
            return resp.to_http_dict()
        return captured

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

        def _do_claim():
            from substrate.organism.approval_gate import OperatorApprovalGate

            gate = OperatorApprovalGate()
            ok = gate.claim_approval(req.approval_id, req.surface)
            return f"claimed {req.approval_id}", ok

        try:
            resp = governed_mutation(
                mutation_name="state_mutate",
                intent=f"claim approval {req.approval_id} from {req.surface}",
                execute_fn=_do_claim,
                source="cockpit",
            )
            if not resp.success:
                return resp.to_http_dict()
            return {"claimed": True, "approval_id": req.approval_id, "surface": req.surface}
        except Exception as exc:
            logger.debug("claim_approval failed: %s", exc)
            return {"claimed": False, "error": str(exc)}

    @router.post("/resolve")
    def resolve_approval(req: ResolveRequest) -> dict[str, Any]:
        """Resolve a claimed approval (approve/reject/provide_input)."""

        def _do_resolve():
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
                    push_mutation_event(
                        "approvals",
                        req.decision,
                        {
                            "id": req.approval_id,
                            "surface": req.surface,
                        },
                    )
            except Exception:
                pass
            return f"resolved {req.approval_id}: {req.decision}", ok

        try:
            resp = governed_mutation(
                mutation_name="approval_decide",
                intent=f"resolve approval {req.approval_id}: {req.decision}",
                execute_fn=_do_resolve,
                source="cockpit",
            )
            if not resp.success:
                return resp.to_http_dict()
            return {"resolved": True, "approval_id": req.approval_id, "decision": req.decision}
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
