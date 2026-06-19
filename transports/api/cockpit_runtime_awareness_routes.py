"""Cockpit routes for Runtime Awareness — Campaign 6.3.

Read-only access to live runtime state (processes, containers, work packets).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        from substrate.organism.runtime_awareness_runtime import RuntimeAwarenessRuntime
        _runtime = RuntimeAwarenessRuntime()
    return _runtime


def configure(runtime: Any) -> None:
    global _runtime
    _runtime = runtime


def _build_router() -> Any:
    from fastapi import APIRouter

    router = APIRouter(prefix="/runtime-awareness", tags=["runtime-awareness"])

    @router.get("/snapshot")
    def get_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        snap = rt.snapshot()
        if isinstance(snap, dict):
            return snap
        return snap.to_dict() if hasattr(snap, "to_dict") else {"error": "no snapshot"}

    @router.get("/active-work")
    def active_work() -> dict[str, Any]:
        items = _get_runtime().active_work()
        return {"active_work": items, "count": len(items)}

    @router.get("/blocked-work")
    def blocked_work() -> dict[str, Any]:
        items = _get_runtime().blocked_work()
        return {"blocked_work": items, "count": len(items)}

    @router.get("/health")
    def health() -> dict[str, Any]:
        return _get_runtime().environment_health()

    return router


router = _build_router()
