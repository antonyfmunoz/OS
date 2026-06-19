"""Cockpit routes for AttentionAggregationRuntime — Campaign 18.2."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.attention_aggregation_runtime import (
                AttentionAggregationRuntime,
            )
            _runtime = AttentionAggregationRuntime()
        except Exception:
            pass
    return _runtime


def get_router() -> APIRouter:
    router = APIRouter(prefix="/attention", tags=["attention"])

    @router.get("/queue")
    def get_queue() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"items": [], "total_count": 0, "critical_count": 0}
        return rt.queue().to_dict()

    @router.get("/count")
    def get_count() -> dict[str, int]:
        rt = _get_runtime()
        if rt is None:
            return {"total": 0, "critical": 0}
        return rt.count()

    return router
