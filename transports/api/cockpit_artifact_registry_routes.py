"""Cockpit routes for Artifact Registry — Campaign 6.0.

Read-only access to the artifact index.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_registry: Any = None


def _get_registry() -> Any:
    global _registry
    if _registry is None:
        from substrate.organism.artifact_registry import ArtifactRegistry
        _registry = ArtifactRegistry()
    return _registry


def configure(registry: Any) -> None:
    global _registry
    _registry = registry


def _build_router() -> Any:
    from fastapi import APIRouter, HTTPException

    router = APIRouter(prefix="/artifact-registry", tags=["artifact-registry"])

    @router.get("/summary")
    def get_summary() -> dict[str, Any]:
        return _get_registry().summary()

    @router.get("/artifacts")
    def list_artifacts(
        artifact_type: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        r = _get_registry()
        items = r.list_artifacts(artifact_type=artifact_type, status=status)
        return {"artifacts": [a.to_dict() for a in items], "count": len(items)}

    @router.get("/artifact/{artifact_id}")
    def get_artifact(artifact_id: str) -> dict[str, Any]:
        r = _get_registry()
        a = r.get(artifact_id)
        if a is None:
            raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")
        return a.to_dict()

    @router.get("/by-entity/{entity_id}")
    def by_entity(entity_id: str) -> dict[str, Any]:
        items = _get_registry().find_by_entity(entity_id)
        return {"artifacts": [a.to_dict() for a in items], "count": len(items)}

    return router


router = _build_router()
