"""Cockpit Meta IDE Projection Loop Routes — API surface for build loop.

Exposes MetaIDEProjectionLoopRuntime: submit, advance, review, merge, reject,
status, request detail, active, history.

Campaign 3.4 — Meta IDE Build Loop. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

build_loop_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    build_loop_router.include_router(_router)


def _get_runtime() -> Any:
    if not hasattr(_get_runtime, "_instance"):
        from substrate.workstation.meta_ide_projection_loop_runtime import (
            MetaIDEProjectionLoopRuntime,
        )

        _get_runtime._instance = MetaIDEProjectionLoopRuntime()
    return _get_runtime._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.post("/build-loop/submit", dependencies=auth)
    async def submit(request: Request) -> dict[str, Any]:
        body = await request.json()
        text = body.get("text", "")
        projection_target = body.get("projection_target", "")
        captured: dict = {}

        def _do_submit():
            result = _get_runtime().submit(text, projection_target=projection_target)
            captured.update(result.to_dict())
            return f"build loop submitted: {text[:80]}", True

        resp = governed_mutation(
            mutation_name="work_packet_create",
            intent=f"build loop submit: {text[:80]}",
            execute_fn=_do_submit,
            source="cockpit",
        )
        if not resp.success:
            return resp.to_http_dict()
        return captured

    @r.post("/build-loop/advance/{request_id}", dependencies=auth)
    def advance(request_id: str) -> dict[str, Any]:
        captured: dict = {}

        def _do_advance():
            result = _get_runtime().advance(request_id)
            captured.update(result.to_dict())
            return f"advanced {request_id}", True

        resp = governed_mutation(
            mutation_name="work_packet_update",
            intent=f"build loop advance {request_id}",
            execute_fn=_do_advance,
            source="cockpit",
        )
        if not resp.success:
            return resp.to_http_dict()
        return captured

    @r.post("/build-loop/review/{request_id}", dependencies=auth)
    def review(request_id: str) -> dict[str, Any]:
        captured: dict = {}

        def _do_review():
            result = _get_runtime().review(request_id)
            captured.update(result.to_dict())
            return f"review started for {request_id}", True

        resp = governed_mutation(
            mutation_name="work_packet_update",
            intent=f"build loop review {request_id}",
            execute_fn=_do_review,
            source="cockpit",
        )
        if not resp.success:
            return resp.to_http_dict()
        return captured

    @r.post("/build-loop/merge/{request_id}", dependencies=auth)
    def merge(request_id: str) -> dict[str, Any]:
        captured: dict = {}

        def _do_merge():
            result = _get_runtime().merge(request_id)
            captured.update(result.to_dict())
            return f"merged {request_id}", True

        resp = governed_mutation(
            mutation_name="approval_decide",
            intent=f"build loop merge {request_id}",
            execute_fn=_do_merge,
            source="cockpit",
        )
        if not resp.success:
            return resp.to_http_dict()
        return captured

    @r.post("/build-loop/reject/{request_id}", dependencies=auth)
    async def reject(request_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        reason = body.get("reason", "")
        captured: dict = {}

        def _do_reject():
            result = _get_runtime().reject(request_id, reason)
            captured.update(result.to_dict())
            return f"rejected {request_id}: {reason[:80]}", True

        resp = governed_mutation(
            mutation_name="approval_decide",
            intent=f"build loop reject {request_id}: {reason[:80]}",
            execute_fn=_do_reject,
            source="cockpit",
        )
        if not resp.success:
            return resp.to_http_dict()
        return captured

    @r.get("/build-loop/status", dependencies=auth)
    def status() -> dict[str, Any]:
        return _get_runtime().status().to_dict()

    @r.get("/build-loop/request/{request_id}", dependencies=auth)
    def request_detail(request_id: str) -> dict[str, Any]:
        req = _get_runtime().request_detail(request_id)
        if req is None:
            return {"error": "not_found", "request_id": request_id}
        return req.to_dict()

    @r.get("/build-loop/active", dependencies=auth)
    def active() -> list[dict[str, Any]]:
        return [r.to_dict() for r in _get_runtime().active_requests()]

    @r.get("/build-loop/history", dependencies=auth)
    def history(limit: int = 50) -> list[dict[str, Any]]:
        return [r.to_dict() for r in _get_runtime().history(limit=limit)]

    return r
