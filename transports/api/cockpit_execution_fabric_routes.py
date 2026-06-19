"""Cockpit routes for ExecutionFabricRuntime — Campaign 19.0."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.execution_fabric_runtime import (
                ExecutionFabricRuntime,
            )
            _runtime = ExecutionFabricRuntime()
        except Exception:
            pass
    return _runtime


def get_router() -> APIRouter:
    router = APIRouter(prefix="/execution-fabric", tags=["execution-fabric"])

    @router.get("/snapshot")
    def get_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "ExecutionFabricRuntime unavailable"}
        return rt.snapshot().to_dict()

    @router.get("/state")
    def get_state() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"state": "unknown"}
        return {"state": rt.state().value}

    @router.get("/active")
    def get_active() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"active": []}
        return {"active": rt.active_executions()}

    @router.get("/blocked")
    def get_blocked() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"blocked": []}
        return {"blocked": rt.blocked()}

    @router.get("/capacity")
    def get_capacity() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "ExecutionFabricRuntime unavailable"}
        return rt.capacity()

    @router.get("/sessions")
    def get_sessions() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"sessions": []}
        return {"sessions": rt.session_bindings()}

    return router
