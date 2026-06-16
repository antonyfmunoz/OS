"""Cockpit Voice Query Routes — context-grounded query resolution.

Phase 35. Accepts text queries, runs IntentRouter classification,
then resolves through VoiceQueryEngine against the subsystem stack.

All routes are read-only. No execution authority.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

voice_router: APIRouter = APIRouter()
_configured = False

_MAX_HISTORY = 50
_history: deque[dict[str, Any]] = deque(maxlen=_MAX_HISTORY)


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    voice_router.include_router(_router)


def _get_engine() -> Any:
    if not hasattr(_get_engine, "_instance"):
        from substrate.operator.voice_query_engine import VoiceQueryEngine

        _get_engine._instance = VoiceQueryEngine()
    return _get_engine._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.post("/voice/query", dependencies=auth)
    async def voice_query(request: Request) -> dict[str, Any]:
        body = await request.json()
        text = body.get("text", "").strip()
        if not text:
            return {"success": False, "error": "text is required"}

        engine = _get_engine()
        resolution = engine.resolve(text)
        result = {
            "success": True,
            "classification": {
                "route_type": resolution.route_type,
                "route_confidence": resolution.route_confidence,
            },
            "resolution": resolution.to_dict(),
        }
        _history.appendleft({
            "text": text,
            "domain": resolution.domain,
            "answer_text": resolution.answer_text,
            "confidence": resolution.confidence,
            "resolved_at": resolution.resolved_at,
        })
        return result

    @r.get("/voice/domains", dependencies=auth)
    async def voice_domains() -> dict[str, Any]:
        from substrate.operator.voice_query_engine import QueryDomain

        domains = []
        for d in QueryDomain:
            domains.append({"value": d.value, "name": d.name})
        return {"success": True, "domains": domains}

    @r.get("/voice/history", dependencies=auth)
    async def voice_history() -> dict[str, Any]:
        return {"success": True, "history": list(_history)}

    return r
