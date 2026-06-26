"""Cockpit Intent Routes — API surface for intent preservation runtime.

All routes expose IntentRuntime operations: capture, refine, supersede,
retrieve, lineage, conflict detection, and alignment scoring.

Gate 4 — Workstation Convergence. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

intent_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    intent_router.include_router(_router)


def _get_runtime() -> Any:
    if not hasattr(_get_runtime, "_instance"):
        from substrate.operator.intent_runtime import IntentRuntime
        _get_runtime._instance = IntentRuntime()
    return _get_runtime._instance


_VALID_SCOPES = frozenset({"empire", "product", "architecture", "engineering", "session"})


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    # ── Query routes ─────────────────────────────────────────

    @r.get("/intent/active", dependencies=auth)
    def intent_active() -> dict[str, Any]:
        rt = _get_runtime()
        by_scope = rt.active_by_scope()
        return {
            "success": True,
            "intents": {
                scope: [i.to_dict() for i in intents]
                for scope, intents in by_scope.items()
            },
        }

    @r.get("/intent/summary", dependencies=auth)
    def intent_summary() -> dict[str, Any]:
        rt = _get_runtime()
        return {"success": True, "summary": rt.summary()}

    @r.get("/intent/context", dependencies=auth)
    def intent_context() -> dict[str, Any]:
        rt = _get_runtime()
        return {"success": True, "context": rt.context_for_session()}

    @r.get("/intent/conflicts", dependencies=auth)
    def intent_conflicts() -> dict[str, Any]:
        rt = _get_runtime()
        conflicts = rt.conflicts(include_resolved=False)
        return {
            "success": True,
            "conflicts": [c.to_dict() for c in conflicts],
        }

    @r.get("/intent/{intent_id}", dependencies=auth)
    def intent_detail(intent_id: str) -> dict[str, Any]:
        rt = _get_runtime()
        intent = rt.get(intent_id)
        if intent is None:
            return {"success": False, "error": "Intent not found"}
        return {"success": True, "intent": intent.to_dict()}

    @r.get("/intent/{intent_id}/lineage", dependencies=auth)
    def intent_lineage(intent_id: str) -> dict[str, Any]:
        rt = _get_runtime()
        chain = rt.lineage(intent_id)
        return {
            "success": True,
            "lineage": [i.to_dict() for i in chain],
        }

    @r.get("/intent/{intent_id}/alignment", dependencies=auth)
    def intent_alignment(intent_id: str) -> dict[str, Any]:
        rt = _get_runtime()
        intent = rt.get(intent_id)
        if intent is None:
            return {"success": False, "error": "Intent not found"}
        score = rt.alignment_score(intent.statement)
        return {"success": True, "alignment_score": score}

    # ── Mutation routes ──────────────────────────────────────

    @r.post("/intent/capture", dependencies=auth)
    async def intent_capture(request: Request) -> dict[str, Any]:
        body = await request.json()
        statement = body.get("statement", "").strip()
        if not statement:
            return {"success": False, "error": "statement is required"}

        scope = body.get("scope", "session")
        if scope not in _VALID_SCOPES:
            return {"success": False, "error": f"invalid scope: {scope}"}

        from substrate.operator.intent_runtime import IntentScope
        intent = _get_runtime().capture(
            statement=statement,
            scope=IntentScope(scope),
            rationale=body.get("rationale", ""),
            success_criteria=body.get("success_criteria"),
            parent_id=body.get("parent_id", ""),
            tags=body.get("tags"),
        )
        return {"success": True, "intent": intent.to_dict()}

    @r.post("/intent/refine/{intent_id}", dependencies=auth)
    async def intent_refine(intent_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        rt = _get_runtime()
        refined = rt.refine(
            intent_id=intent_id,
            new_statement=body.get("statement", ""),
            new_rationale=body.get("rationale", ""),
            new_criteria=body.get("success_criteria"),
            new_tags=body.get("tags"),
        )
        if refined is None:
            return {"success": False, "error": "Intent not found or not active"}
        return {"success": True, "intent": refined.to_dict()}

    @r.post("/intent/supersede", dependencies=auth)
    async def intent_supersede(request: Request) -> dict[str, Any]:
        body = await request.json()
        old_id = body.get("intent_id", "")
        replacement_id = body.get("replacement_id", "")
        if not old_id or not replacement_id:
            return {"success": False, "error": "intent_id and replacement_id required"}
        rt = _get_runtime()
        ok = rt.supersede(old_id, replacement_id)
        return {"success": ok}

    @r.post("/intent/achieve/{intent_id}", dependencies=auth)
    async def intent_achieve(intent_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        evidence = body.get("evidence", [])
        rt = _get_runtime()
        ok = rt.achieve(intent_id, evidence=evidence)
        return {"success": ok}

    @r.post("/intent/abandon/{intent_id}", dependencies=auth)
    async def intent_abandon(intent_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        reason = body.get("reason", "")
        rt = _get_runtime()
        ok = rt.abandon(intent_id, reason=reason)
        return {"success": ok}

    @r.post("/intent/resolve-conflict/{conflict_id}", dependencies=auth)
    async def intent_resolve_conflict(conflict_id: str, request: Request) -> dict[str, Any]:
        body = await request.json()
        resolution = body.get("resolution", "")
        if not resolution:
            return {"success": False, "error": "resolution is required"}
        rt = _get_runtime()
        ok = rt.resolve_conflict(conflict_id, resolution)
        return {"success": ok}

    return r
