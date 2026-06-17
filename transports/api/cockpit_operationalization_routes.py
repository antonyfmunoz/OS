"""Cockpit Operationalization Routes — API surface for reusable capability artifacts.

Exposes OperationalizationRuntime operations: create, list, get, lineage,
reuse scoring, template linkage.

Answers operator question #11: "What has been operationalized?"

Gate 6 — Operationalization Runtime. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

operationalization_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    operationalization_router.include_router(_router)


def _get_runtime() -> Any:
    if not hasattr(_get_runtime, "_instance"):
        from substrate.organism.operationalization_runtime import (
            OperationalizationRuntime,
        )

        _get_runtime._instance = OperationalizationRuntime()
    return _get_runtime._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.get("/operationalizations", dependencies=auth)
    async def list_operationalizations(
        capability_id: str | None = None,
        form: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
            OperationalizationStatus,
        )

        rt = _get_runtime()
        f = None
        if form:
            try:
                f = OperationalizationForm(form)
            except ValueError:
                return {"error": f"invalid form: {form}"}
        s = None
        if status:
            try:
                s = OperationalizationStatus(status)
            except ValueError:
                return {"error": f"invalid status: {status}"}
        ops = rt.list_operationalizations(capability_id=capability_id, form=f, status=s)
        return {"operationalizations": [o.to_dict() for o in ops], "count": len(ops)}

    @r.get("/operationalizations/summary", dependencies=auth)
    async def operationalization_summary() -> dict[str, Any]:
        return _get_runtime().summary()

    @r.get("/operationalizations/most-reused", dependencies=auth)
    async def most_reused(n: int = 10) -> dict[str, Any]:
        rt = _get_runtime()
        ops = rt.most_reused(n=n)
        return {"operationalizations": [o.to_dict() for o in ops], "count": len(ops)}

    @r.get("/operationalizations/{op_id}", dependencies=auth)
    async def get_operationalization(op_id: str) -> dict[str, Any]:
        rt = _get_runtime()
        op = rt.get(op_id)
        if op is None:
            return {"error": f"operationalization {op_id} not found"}
        return {
            "operationalization": op.to_dict(),
            "lineage": rt.lineage(op_id),
            "reuse_score": rt.reuse_score(op_id),
        }

    @r.post("/operationalizations/create", dependencies=auth)
    async def create_operationalization(request: Request) -> dict[str, Any]:
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
        )

        body = await request.json()
        name = body.get("name", "")
        capability_id = body.get("capability_id", "")
        if not name:
            return {"error": "name is required"}
        form_str = body.get("form", "template")
        try:
            form = OperationalizationForm(form_str)
        except ValueError:
            return {"error": f"invalid form: {form_str}"}
        rt = _get_runtime()
        op = rt.create(
            capability_id=capability_id,
            form=form,
            name=name,
            description=body.get("description", ""),
            template_id=body.get("template_id", ""),
            invariants=body.get("invariants"),
            variables=body.get("variables"),
        )
        return {"operationalization": op.to_dict()}

    @r.post("/operationalizations/{op_id}/use", dependencies=auth)
    async def record_use(op_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        success = body.get("success", True)
        rt = _get_runtime()
        if rt.record_use(op_id, success=success):
            return {"status": "recorded"}
        return {"error": f"operationalization {op_id} not found"}

    return r
