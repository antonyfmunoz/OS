"""Cockpit routes for Documentation Awareness — Campaign 6.2.

Read-only access to documentation metadata and awareness.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        from substrate.organism.documentation_awareness_runtime import DocumentationAwarenessRuntime
        _runtime = DocumentationAwarenessRuntime()
    return _runtime


def configure(runtime: Any) -> None:
    global _runtime
    _runtime = runtime


def _build_router() -> Any:
    from fastapi import APIRouter

    router = APIRouter(prefix="/documentation-awareness", tags=["documentation-awareness"])

    @router.get("/snapshot")
    def get_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        snap = rt.snapshot()
        if isinstance(snap, dict):
            return snap
        return snap.to_dict() if hasattr(snap, "to_dict") else {"error": "no snapshot"}

    @router.get("/documents")
    def list_documents(status: str | None = None, source_type: str | None = None) -> dict[str, Any]:
        rt = _get_runtime()
        if hasattr(rt, "list_documents"):
            docs = rt.list_documents(status=status, source_type=source_type)
        else:
            docs = []
        return {"documents": [d.to_dict() if hasattr(d, "to_dict") else d for d in docs], "count": len(docs)}

    @router.get("/entity-docs/{entity_id}")
    def entity_docs(entity_id: str) -> dict[str, Any]:
        rt = _get_runtime()
        docs = rt.find_docs_for_entity(entity_id)
        return {"documents": [d.to_dict() if hasattr(d, "to_dict") else d for d in docs], "count": len(docs)}

    @router.get("/stale")
    def stale_docs(max_age_days: int = 30) -> dict[str, Any]:
        rt = _get_runtime()
        docs = rt.find_stale_docs(max_age_days=max_age_days)
        return {"documents": [d.to_dict() if hasattr(d, "to_dict") else d for d in docs], "count": len(docs)}

    return router


router = _build_router()
