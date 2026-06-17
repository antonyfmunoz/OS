"""Cockpit routes for Knowledge Awareness — Campaign 6.4.

Read-only access to extracted decisions, constraints, conventions, lessons.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        from substrate.organism.knowledge_awareness_runtime import KnowledgeAwarenessRuntime
        _runtime = KnowledgeAwarenessRuntime()
    return _runtime


def configure(runtime: Any) -> None:
    global _runtime
    _runtime = runtime


def _build_router() -> Any:
    from fastapi import APIRouter

    router = APIRouter(prefix="/knowledge-awareness", tags=["knowledge-awareness"])

    @router.get("/snapshot")
    def get_snapshot() -> dict[str, Any]:
        return _get_runtime().snapshot()

    @router.get("/entries")
    def list_entries(
        knowledge_type: str | None = None,
        entity_id: str | None = None,
    ) -> dict[str, Any]:
        rt = _get_runtime()
        entries = rt.list_entries(knowledge_type=knowledge_type, entity_id=entity_id)
        return {"entries": [e.to_dict() for e in entries], "count": len(entries)}

    @router.get("/decisions")
    def decisions() -> dict[str, Any]:
        entries = _get_runtime().find_decisions()
        return {"decisions": [e.to_dict() for e in entries], "count": len(entries)}

    @router.get("/constraints")
    def constraints() -> dict[str, Any]:
        entries = _get_runtime().find_constraints()
        return {"constraints": [e.to_dict() for e in entries], "count": len(entries)}

    return router


router = _build_router()
