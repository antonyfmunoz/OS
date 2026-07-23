"""Cockpit Work Center Routes — unified API for governed work lifecycle.

All mutation routes call GovernedWorkRuntime — the mandatory execution
gateway. No route may call ExecutionCoordinator or ExecutorRuntime directly.

Gate 3. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from transports.api.governed import governed_mutation

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
    def work_queue() -> dict[str, Any]:
        rt = _get_runtime()
        return {"success": True, "queue": rt.queue()}

    @r.get("/work/blocked", dependencies=auth)
    def work_blocked() -> dict[str, Any]:
        rt = _get_runtime()
        return {"success": True, "blocked": rt.blocked()}

    @r.get("/work/active", dependencies=auth)
    def work_active() -> dict[str, Any]:
        rt = _get_runtime()
        return {"success": True, "active": rt.active()}

    @r.get("/work/approvals", dependencies=auth)
    def work_approvals() -> dict[str, Any]:
        rt = _get_runtime()
        if rt.work_graph is not None:
            pending = rt.work_graph.work_by_status("approval_pending")
            return {"success": True, "approvals": [n.to_dict() for n in pending]}
        return {"success": True, "approvals": []}

    @r.get("/work/proof", dependencies=auth)
    def work_proof_list() -> dict[str, Any]:
        rt = _get_runtime()
        if rt.proof_runtime is not None:
            proofs = rt.proof_runtime.recent(20)
            return {"success": True, "proofs": [p.to_dict() for p in proofs]}
        return {"success": True, "proofs": []}

    @r.get("/work/history", dependencies=auth)
    def work_history() -> dict[str, Any]:
        rt = _get_runtime()
        return {"success": True, "history": rt.history()}

    @r.get("/work/recovery", dependencies=auth)
    def work_recovery() -> dict[str, Any]:
        rt = _get_runtime()
        return {"success": True, "recovery": rt.recovery()}

    @r.get("/work/graph", dependencies=auth)
    def work_graph_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        return {"success": True, "graph": rt.graph_snapshot()}

    @r.get("/work/{work_id}", dependencies=auth)
    def work_detail(work_id: str) -> dict[str, Any]:
        rt = _get_runtime()
        status = rt.status(work_id)
        return {"success": True, "work": status.to_dict()}

    @r.get("/work/{work_id}/proof", dependencies=auth)
    def work_item_proof(work_id: str) -> dict[str, Any]:
        rt = _get_runtime()
        proof = rt.proof(work_id)
        return {"success": True, "proof": proof}

    # ── Mutation routes (all through GovernedWorkRuntime) ─────

    # Wave 2: no ``simulation`` default. Real executors only; ``simulation`` is a
    # test-only compatibility opt-in, never a default and never valid in prod.
    _VALID_EXECUTORS = frozenset({"workstation", "agent"})

    @r.post("/work/submit", dependencies=auth)
    async def work_submit(request: Request) -> dict[str, Any]:
        import os as _os

        body = await request.json()
        intent = body.get("intent", "").strip()
        if not intent:
            return {"success": False, "error": "intent is required"}
        target_executor = body.get("target_executor", "").strip()
        if not target_executor:
            return {"success": False, "error": "target_executor is required"}
        valid = set(_VALID_EXECUTORS)
        if _os.environ.get("UMH_ALLOW_SIMULATION_EXECUTOR") == "1":
            valid.add("simulation")
        if target_executor not in valid:
            return {"success": False, "error": f"invalid target_executor: {target_executor}"}
        description = body.get("description", "")

        def _do_submit():
            rt = _get_runtime()
            submission = rt.submit_work(
                intent=intent,
                target_executor=target_executor,
                description=description,
            )
            if submission.error:
                return str(submission.error), False
            return f"work submitted: {submission.work_id}", True

        resp = governed_mutation(
            mutation_name="work_packet_create",
            intent=f"submit work: {intent[:80]}",
            execute_fn=_do_submit,
            source="cockpit",
            metadata={"target_executor": target_executor},
        )
        return resp.to_http_dict()

    @r.post("/work/approve/{work_id}", dependencies=auth)
    async def work_approve(work_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        decided_by = body.get("decided_by", "operator")

        def _do_approve():
            rt = _get_runtime()
            decision = rt.approve_work(work_id, decided_by=decided_by)
            if decision.get("status") == "error":
                return decision.get("error", "approval failed"), False
            return f"work {work_id} approved", True

        resp = governed_mutation(
            mutation_name="approval_decide",
            intent=f"approve work {work_id}",
            execute_fn=_do_approve,
            source="cockpit",
            metadata={"work_id": work_id, "decided_by": decided_by},
        )
        return resp.to_http_dict()

    @r.post("/work/reject/{work_id}", dependencies=auth)
    async def work_reject(work_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        reason = body.get("reason", "")
        decided_by = body.get("decided_by", "operator")

        def _do_reject():
            rt = _get_runtime()
            decision = rt.reject_work(work_id, reason=reason, decided_by=decided_by)
            if decision.get("status") == "error":
                return decision.get("error", "rejection failed"), False
            return f"work {work_id} rejected: {reason[:100]}", True

        resp = governed_mutation(
            mutation_name="approval_decide",
            intent=f"reject work {work_id}",
            execute_fn=_do_reject,
            source="cockpit",
            metadata={"work_id": work_id, "reason": reason},
        )
        return resp.to_http_dict()

    @r.post("/work/execute/{work_id}", dependencies=auth)
    def work_execute(work_id: str) -> dict[str, Any]:
        def _do_execute():
            rt = _get_runtime()
            receipt = rt.execute_work(work_id)
            if receipt.error:
                return str(receipt.error), False
            return f"work {work_id} executed", True

        resp = governed_mutation(
            mutation_name="work_packet_update",
            intent=f"execute work {work_id}",
            execute_fn=_do_execute,
            source="cockpit",
            metadata={"work_id": work_id},
        )
        return resp.to_http_dict()

    @r.post("/work/cancel/{work_id}", dependencies=auth)
    async def work_cancel(work_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        reason = body.get("reason", "")

        def _do_cancel():
            rt = _get_runtime()
            cancelled = rt.cancel_work(work_id, reason=reason)
            return f"work {work_id} {'cancelled' if cancelled else 'cancel failed'}", cancelled

        resp = governed_mutation(
            mutation_name="work_packet_update",
            intent=f"cancel work {work_id}",
            execute_fn=_do_cancel,
            source="cockpit",
            metadata={"work_id": work_id, "reason": reason},
        )
        return resp.to_http_dict()

    @r.post("/work/retry/{work_id}", dependencies=auth)
    def work_retry(work_id: str) -> dict[str, Any]:
        def _do_retry():
            rt = _get_runtime()
            submission = rt.retry_work(work_id)
            if submission.error:
                return str(submission.error), False
            return f"work {work_id} retried", True

        resp = governed_mutation(
            mutation_name="work_packet_update",
            intent=f"retry work {work_id}",
            execute_fn=_do_retry,
            source="cockpit",
            metadata={"work_id": work_id},
        )
        return resp.to_http_dict()

    return r
