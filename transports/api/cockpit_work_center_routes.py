"""Cockpit Work Center Routes — unified API for governed work lifecycle.

All mutation routes call GovernedWorkRuntime — the mandatory execution
gateway. No route may call ExecutionCoordinator or ExecutorRuntime directly.

Gate 3. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

work_center_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    work_center_router.include_router(_router)


def _get_runtime() -> Any:
    if not hasattr(_get_runtime, "_instance"):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        _get_runtime._instance = GovernedWorkRuntime()
    return _get_runtime._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    # ── Query routes ─────────────────────────────────────────

    @r.get("/work/queue", dependencies=auth)
    async def work_queue() -> dict[str, Any]:
        rt = _get_runtime()
        return {"success": True, "queue": rt.queue()}

    @r.get("/work/blocked", dependencies=auth)
    async def work_blocked() -> dict[str, Any]:
        rt = _get_runtime()
        return {"success": True, "blocked": rt.blocked()}

    @r.get("/work/active", dependencies=auth)
    async def work_active() -> dict[str, Any]:
        rt = _get_runtime()
        return {"success": True, "active": rt.active()}

    @r.get("/work/approvals", dependencies=auth)
    async def work_approvals() -> dict[str, Any]:
        rt = _get_runtime()
        if rt.work_graph is not None:
            pending = rt.work_graph.work_by_status("approval_pending")
            return {"success": True, "approvals": [n.to_dict() for n in pending]}
        return {"success": True, "approvals": []}

    @r.get("/work/proof", dependencies=auth)
    async def work_proof_list() -> dict[str, Any]:
        rt = _get_runtime()
        if rt.proof_runtime is not None:
            proofs = rt.proof_runtime.recent(20)
            return {"success": True, "proofs": [p.to_dict() for p in proofs]}
        return {"success": True, "proofs": []}

    @r.get("/work/history", dependencies=auth)
    async def work_history() -> dict[str, Any]:
        rt = _get_runtime()
        return {"success": True, "history": rt.history()}

    @r.get("/work/recovery", dependencies=auth)
    async def work_recovery() -> dict[str, Any]:
        rt = _get_runtime()
        return {"success": True, "recovery": rt.recovery()}

    @r.get("/work/graph", dependencies=auth)
    async def work_graph_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        return {"success": True, "graph": rt.graph_snapshot()}

    @r.get("/work/{work_id}", dependencies=auth)
    async def work_detail(work_id: str) -> dict[str, Any]:
        rt = _get_runtime()
        status = rt.status(work_id)
        return {"success": True, "work": status.to_dict()}

    @r.get("/work/{work_id}/proof", dependencies=auth)
    async def work_item_proof(work_id: str) -> dict[str, Any]:
        rt = _get_runtime()
        proof = rt.proof(work_id)
        return {"success": True, "proof": proof}

    # ── Mutation routes (all through GovernedWorkRuntime) ─────

    _VALID_EXECUTORS = frozenset({"simulation", "workstation", "agent"})

    @r.post("/work/submit", dependencies=auth)
    async def work_submit(request: Request) -> dict[str, Any]:
        body = await request.json()
        intent = body.get("intent", "").strip()
        if not intent:
            return {"success": False, "error": "intent is required"}
        target_executor = body.get("target_executor", "simulation")
        if target_executor not in _VALID_EXECUTORS:
            return {"success": False, "error": f"invalid target_executor: {target_executor}"}
        description = body.get("description", "")

        rt = _get_runtime()
        submission = rt.submit_work(
            intent=intent,
            target_executor=target_executor,
            description=description,
        )
        return {"success": not submission.error, "submission": submission.to_dict()}

    @r.post("/work/approve/{work_id}", dependencies=auth)
    async def work_approve(work_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        decided_by = body.get("decided_by", "operator")
        rt = _get_runtime()
        decision = rt.approve_work(work_id, decided_by=decided_by)
        return {"success": decision.get("status") != "error", "decision": decision}

    @r.post("/work/reject/{work_id}", dependencies=auth)
    async def work_reject(work_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        reason = body.get("reason", "")
        decided_by = body.get("decided_by", "operator")
        rt = _get_runtime()
        decision = rt.reject_work(work_id, reason=reason, decided_by=decided_by)
        return {"success": decision.get("status") != "error", "decision": decision}

    @r.post("/work/execute/{work_id}", dependencies=auth)
    async def work_execute(work_id: str) -> dict[str, Any]:
        rt = _get_runtime()
        receipt = rt.execute_work(work_id)
        return {"success": not receipt.error, "receipt": receipt.to_dict()}

    @r.post("/work/cancel/{work_id}", dependencies=auth)
    async def work_cancel(work_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        reason = body.get("reason", "")
        rt = _get_runtime()
        cancelled = rt.cancel_work(work_id, reason=reason)
        return {"success": cancelled}

    @r.post("/work/retry/{work_id}", dependencies=auth)
    async def work_retry(work_id: str) -> dict[str, Any]:
        rt = _get_runtime()
        submission = rt.retry_work(work_id)
        return {"success": not submission.error, "submission": submission.to_dict()}

    return r
