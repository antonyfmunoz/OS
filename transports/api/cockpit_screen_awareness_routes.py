"""Cockpit Screen Awareness Routes — operator visual workspace context.

Phase 33. Read-only routes for screen awareness with provider preference
ordering (OBSERVED > REPORTED > INFERRED).

UMH transport layer. Instance-agnostic.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

screen_awareness_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    screen_awareness_router.include_router(_router)


def _get_engine() -> Any:
    if not hasattr(_get_engine, "_instance"):
        from substrate.operator.screen_observation_engine import ScreenObservationEngine

        _get_engine._instance = ScreenObservationEngine()
    return _get_engine._instance


def _get_resolver() -> Any:
    if not hasattr(_get_resolver, "_instance"):
        from substrate.operator.repository_context_resolver import RepositoryContextResolver

        _get_resolver._instance = RepositoryContextResolver()
    return _get_resolver._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    router = APIRouter(
        prefix="/screen",
        tags=["screen-awareness"],
        dependencies=[Depends(require_operator_dep)],
    )

    @router.get("")
    async def screen_snapshot() -> dict[str, Any]:
        engine = _get_engine()
        return engine.current_snapshot().to_dict()

    @router.get("/current")
    async def screen_current() -> dict[str, Any]:
        engine = _get_engine()
        snap = engine.current_snapshot()
        result: dict[str, Any] = {
            "source_type": snap.source_type.value,
            "status": snap.status.value,
            "source_node_id": snap.source_node_id,
            "source_confidence": snap.source_confidence,
        }
        if snap.active_application:
            result["active_application"] = snap.active_application.to_dict()
        if snap.active_window:
            result["active_window"] = snap.active_window.to_dict()
        return result

    @router.get("/application")
    async def screen_application() -> dict[str, Any]:
        engine = _get_engine()
        app = engine.active_application()
        return app.to_dict() if app else {}

    @router.get("/file")
    async def screen_file() -> dict[str, Any]:
        engine = _get_engine()
        fc = engine.active_file()
        return fc.to_dict() if fc else {}

    @router.get("/repository")
    async def screen_repository() -> dict[str, Any]:
        engine = _get_engine()
        repo = engine.active_repository()
        return repo.to_dict() if repo else {}

    @router.get("/repositories")
    async def screen_repositories() -> dict[str, Any]:
        resolver = _get_resolver()
        repos = resolver.active_repositories()
        return {
            "count": len(repos),
            "repositories": [r.to_dict() for r in repos],
        }

    @router.get("/providers")
    async def screen_providers() -> dict[str, Any]:
        engine = _get_engine()
        return engine.provider_status()

    return router
