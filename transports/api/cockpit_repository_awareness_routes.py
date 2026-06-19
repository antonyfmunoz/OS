"""Cockpit routes for Repository Awareness — Campaign 6.1.

Read-only access to file-level repository awareness.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        from substrate.organism.repository_awareness_runtime import RepositoryAwarenessRuntime
        _runtime = RepositoryAwarenessRuntime()
    return _runtime


def configure(runtime: Any) -> None:
    global _runtime
    _runtime = runtime


def _build_router() -> Any:
    from fastapi import APIRouter

    router = APIRouter(prefix="/repository-awareness", tags=["repository-awareness"])

    @router.get("/snapshot")
    def get_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        snap = rt.snapshot()
        if isinstance(snap, dict):
            return snap
        return snap.to_dict() if hasattr(snap, "to_dict") else {"error": "no snapshot"}

    @router.get("/files")
    def list_files(category: str | None = None, limit: int = 100) -> dict[str, Any]:
        rt = _get_runtime()
        if hasattr(rt, "list_files"):
            files = rt.list_files(category=category, limit=limit)
        else:
            files = []
        return {"files": [f.to_dict() if hasattr(f, "to_dict") else f for f in files], "count": len(files)}

    @router.get("/important-files")
    def important_files() -> dict[str, Any]:
        rt = _get_runtime()
        if hasattr(rt, "detect_important_files"):
            files = rt.detect_important_files()
        else:
            files = []
        return {"files": [f.to_dict() if hasattr(f, "to_dict") else f for f in files], "count": len(files)}

    @router.get("/entity-files/{entity_id}")
    def entity_files(entity_id: str) -> dict[str, Any]:
        rt = _get_runtime()
        files = rt.find_files_for_entity(entity_id)
        return {"files": [f.to_dict() if hasattr(f, "to_dict") else f for f in files], "count": len(files)}

    return router


router = _build_router()
