"""Cockpit Operator Presence Routes — presence and continuity API.

Exposes the ContinuityEngine through the cockpit API.
All routes auth-protected. Read-only. Observation only.

Phase 32. Transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

operator_presence_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    operator_presence_router.include_router(_router)


def _get_engine() -> Any:
    if not hasattr(_get_engine, "_instance"):
        from substrate.operator.continuity_engine import ContinuityEngine
        _get_engine._instance = ContinuityEngine()
    return _get_engine._instance


def _get_timeline() -> Any:
    if not hasattr(_get_timeline, "_instance"):
        from substrate.operator.presence_timeline import PresenceTimeline
        _get_timeline._instance = PresenceTimeline()
    return _get_timeline._instance


def _get_device_tracker() -> Any:
    if not hasattr(_get_device_tracker, "_instance"):
        from substrate.operator.device_continuity import DeviceContinuityTracker
        _get_device_tracker._instance = DeviceContinuityTracker()
    return _get_device_tracker._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    router = APIRouter(
        prefix="/presence",
        tags=["operator-presence"],
        dependencies=[Depends(require_operator_dep)],
    )

    @router.get("")
    async def presence_snapshot() -> dict[str, Any]:
        engine = _get_engine()
        return engine.snapshot().to_dict()

    @router.get("/current")
    async def presence_current() -> dict[str, Any]:
        engine = _get_engine()
        presence = engine.current_presence()
        context = engine.active_context()
        return {
            "presence": presence.to_dict(),
            "context": context.to_dict(),
        }

    @router.get("/checkpoints")
    async def presence_checkpoints() -> dict[str, Any]:
        engine = _get_engine()
        checkpoints = engine.continuity_checkpoints()
        return {
            "count": len(checkpoints),
            "checkpoints": [c.to_dict() for c in checkpoints],
        }

    @router.get("/timeline")
    async def presence_timeline() -> dict[str, Any]:
        timeline = _get_timeline()
        transitions = timeline.recent()
        return {
            "count": len(transitions),
            "transitions": [t.to_dict() for t in transitions],
        }

    @router.get("/devices")
    async def presence_devices() -> dict[str, Any]:
        tracker = _get_device_tracker()
        return tracker.to_dict()

    @router.get("/resume")
    async def presence_resume() -> dict[str, Any]:
        engine = _get_engine()
        return engine.resume_suggestion()

    return router
