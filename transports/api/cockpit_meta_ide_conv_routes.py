"""Cockpit Meta IDE convergence routes — unified development surface.

Mounted under /api/umh/ via include_router in cockpit.py.
Full development loop: inspect → plan → assign → review → merge.

W2. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

meta_ide_conv_router: APIRouter = APIRouter()

_configured: bool = False
_ide_instance: Any = None


def configure(*, require_operator_dep: Any) -> None:
    global _configured, meta_ide_conv_router
    if _configured:
        return
    _configured = True
    meta_ide_conv_router = _build_router(require_operator_dep)


def _get_ide() -> Any:
    global _ide_instance
    if _ide_instance is not None:
        return _ide_instance
    try:
        from substrate.organism.agent_capability_model import AgentCapabilityModel
        from substrate.organism.agent_fleet_runtime import AgentFleetRuntime
        from substrate.organism.agent_registry import AgentRegistry
        from substrate.organism.compute_fabric_runtime import ComputeFabricRuntime
        from substrate.organism.distributed_runtime import DistributedRuntime
        from substrate.organism.meta_ide_runtime import MetaIDERuntime
        from substrate.meta_ide.shared_planner import get_shared_planner

        dr = DistributedRuntime()
        fabric = ComputeFabricRuntime(dr)
        capability_model = AgentCapabilityModel()
        registry = AgentRegistry()
        fleet = AgentFleetRuntime(
            capability_model=capability_model,
            compute_fabric=fabric,
            agent_registry=registry,
        )
        _ide_instance = MetaIDERuntime(
            agent_fleet=fleet,
            engineering_planner=get_shared_planner(),
        )
        return _ide_instance
    except Exception as exc:
        logger.debug("meta ide routes: failed to create runtime: %s", exc)
        return None


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter(dependencies=[Depends(require_operator_dep)])

    @r.get("/ide/workspace")
    def ide_workspace() -> dict:
        ide = _get_ide()
        if ide is None:
            return {"error": "meta ide unavailable"}
        return ide.workspace_snapshot().to_dict()

    @r.get("/ide/repos/{repo_id}")
    def ide_repo_status(repo_id: str) -> dict:
        ide = _get_ide()
        if ide is None:
            return {"error": "meta ide unavailable"}
        return ide.repo_status(repo_id)

    @r.post("/ide/plan")
    def ide_plan(payload: dict) -> dict:
        ide = _get_ide()
        if ide is None:
            raise HTTPException(status_code=503, detail="meta ide unavailable")
        intent = str(payload.get("intent_text", ""))
        if not intent:
            raise HTTPException(status_code=400, detail="intent_text required")
        plan = ide.plan_from_intent(intent)
        return plan.to_dict()

    @r.post("/ide/assign")
    def ide_assign(payload: dict) -> dict:
        ide = _get_ide()
        if ide is None:
            raise HTTPException(status_code=503, detail="meta ide unavailable")
        plan_id = str(payload.get("plan_id", ""))
        if not plan_id:
            raise HTTPException(status_code=400, detail="plan_id required")
        assignments = ide.assign_plan(plan_id)
        return {"assignments": assignments}

    @r.post("/ide/dispatch")
    def ide_dispatch(payload: dict) -> dict:
        ide = _get_ide()
        if ide is None:
            raise HTTPException(status_code=503, detail="meta ide unavailable")
        plan_id = str(payload.get("plan_id", ""))
        if not plan_id:
            raise HTTPException(status_code=400, detail="plan_id required")
        dispatches = ide.dispatch_plan(plan_id)
        return {"dispatches": dispatches}

    @r.get("/ide/active")
    def ide_active() -> dict:
        ide = _get_ide()
        if ide is None:
            return {"streams": []}
        return {"streams": [s.to_dict() for s in ide.active_development()]}

    @r.get("/ide/reviews")
    async def ide_reviews(status: str = "pending") -> dict:
        reviews: list[dict] = []
        ide = _get_ide()
        if ide is not None:
            reviews.extend([rv.to_dict() for rv in ide.review_packages(status)])
        from transports.api._mesh_dispatch import get_proof_packages
        for proof in get_proof_packages().values():
            if status == "pending" and proof.get("review_status") == "pending":
                reviews.append(proof)
            elif status != "pending":
                reviews.append(proof)
        return {"reviews": reviews}

    @r.get("/ide/reviews/{review_id}")
    def ide_review_detail(review_id: str) -> dict:
        ide = _get_ide()
        if ide is not None:
            review = ide.review_detail(review_id)
            if review:
                return review.to_dict()
        from transports.api._mesh_dispatch import get_proof_packages
        proof = get_proof_packages().get(review_id)
        if proof:
            return proof
        raise HTTPException(status_code=404, detail="review not found")

    @r.post("/ide/reviews/{review_id}/approve")
    def ide_approve(review_id: str) -> dict:
        ide = _get_ide()
        if ide is None:
            raise HTTPException(status_code=503, detail="meta ide unavailable")
        result = ide.approve_and_merge(review_id)
        if result.error:
            raise HTTPException(status_code=400, detail=result.error)
        return result.to_dict()

    @r.post("/ide/reviews/{review_id}/reject")
    def ide_reject(review_id: str, payload: dict) -> dict:
        ide = _get_ide()
        if ide is None:
            raise HTTPException(status_code=503, detail="meta ide unavailable")
        reason = str(payload.get("reason", ""))
        ok = ide.reject_review(review_id, reason)
        if not ok:
            raise HTTPException(status_code=404, detail="review not found")
        return {"status": "rejected", "review_id": review_id}

    @r.get("/ide/status")
    def ide_status() -> dict:
        ide = _get_ide()
        if ide is None:
            return {"error": "meta ide unavailable"}
        return ide.ide_status().to_dict()

    return r
