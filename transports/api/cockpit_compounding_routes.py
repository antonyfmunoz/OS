"""Cockpit Compounding Routes — API surface for capability compounding.

Exposes CompoundingEngine operations: detect, approve, reject, promote,
report, summary.

Answers operator questions #9 and #13:
  "What did we learn?" and "What should I do next?"

Gate 9 — Compounding Engine. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

compounding_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    compounding_router.include_router(_router)


def _get_engine() -> Any:
    if not hasattr(_get_engine, "_instance"):
        from substrate.organism.compounding_engine import CompoundingEngine

        _get_engine._instance = CompoundingEngine()
    return _get_engine._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.get("/compounding/candidates", dependencies=auth)
    def list_candidates(
        promotion_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        from substrate.organism.compounding_engine import (
            PromotionStatus,
            PromotionType,
        )

        eng = _get_engine()
        pt = None
        if promotion_type:
            try:
                pt = PromotionType(promotion_type)
            except ValueError:
                return {"error": f"invalid promotion_type: {promotion_type}"}
        st = None
        if status:
            try:
                st = PromotionStatus(status)
            except ValueError:
                return {"error": f"invalid status: {status}"}
        candidates = eng.list_candidates(promotion_type=pt, status=st, limit=limit)
        return {"candidates": [c.to_dict() for c in candidates], "count": len(candidates)}

    @r.get("/compounding/summary", dependencies=auth)
    def compounding_summary() -> dict[str, Any]:
        return _get_engine().summary()

    @r.get("/compounding/report", dependencies=auth)
    def compounding_report(days: int = 90) -> dict[str, Any]:
        return _get_engine().compounding_report(days=days)

    @r.get("/compounding/improvements", dependencies=auth)
    def improvements(n: int = 100) -> dict[str, Any]:
        return _get_engine().improvement_from_executions(n=n)

    @r.get("/compounding/candidates/{candidate_id}", dependencies=auth)
    def get_candidate(candidate_id: str) -> dict[str, Any]:
        eng = _get_engine()
        c = eng.get(candidate_id)
        if c is None:
            return {"error": f"candidate {candidate_id} not found"}
        return {"candidate": c.to_dict()}

    @r.post("/compounding/detect/outcomes", dependencies=auth)
    async def detect_outcomes(request: Request) -> dict[str, Any]:
        body = await request.json()
        outcomes = body.get("outcomes", [])
        eng = _get_engine()
        candidates = eng.detect_outcome_to_insight(
            outcomes,
            min_occurrences=int(body.get("min_occurrences", 3)),
            min_success_rate=float(body.get("min_success_rate", 0.6)),
        )
        return {"candidates": [c.to_dict() for c in candidates], "count": len(candidates)}

    @r.post("/compounding/candidates/{candidate_id}/approve", dependencies=auth)
    def approve_candidate(candidate_id: str) -> dict[str, Any]:
        if _get_engine().approve(candidate_id):
            return {"status": "approved"}
        return {"error": f"cannot approve {candidate_id}"}

    @r.post("/compounding/candidates/{candidate_id}/reject", dependencies=auth)
    async def reject_candidate(candidate_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        reason = body.get("reason", "")
        if _get_engine().reject(candidate_id, reason):
            return {"status": "rejected"}
        return {"error": f"cannot reject {candidate_id}"}

    @r.post("/compounding/candidates/{candidate_id}/promote", dependencies=auth)
    def promote_candidate(candidate_id: str) -> dict[str, Any]:
        return _get_engine().promote(candidate_id)

    return r
