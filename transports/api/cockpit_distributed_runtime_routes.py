"""Cockpit distributed runtime routes — organism worker routing surface.

Mounted under /api/umh/ via include_router in cockpit.py.
Read-only queries + governed worker registration and packet routing.
No execution authority.

Phase 24. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

distributed_runtime_router: APIRouter = APIRouter()

_configured: bool = False
_runtime_instance: Any = None


def configure(require_operator_dep: Any) -> None:
    global _configured, distributed_runtime_router
    _configured = True
    distributed_runtime_router = _build_router(require_operator_dep)


def _get_runtime() -> Any:
    global _runtime_instance
    if _runtime_instance is not None:
        return _runtime_instance
    try:
        from substrate.organism.distributed_runtime import DistributedRuntime

        _runtime_instance = DistributedRuntime()
        return _runtime_instance
    except Exception as exc:
        logger.debug("distributed runtime routes: failed to create runtime: %s", exc)
        return None


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()

    @r.get("/organism/distributed-runtime")
    async def overview() -> dict:
        rt = _get_runtime()
        if rt is None:
            return {"error": "distributed runtime unavailable"}
        return rt.overview()

    @r.get("/organism/distributed-runtime/devices")
    async def devices() -> dict:
        rt = _get_runtime()
        if rt is None:
            return {"devices": []}
        return {"devices": rt.device_summary()}

    @r.get("/organism/distributed-runtime/workers")
    async def workers(device_id: str = "") -> dict:
        rt = _get_runtime()
        if rt is None:
            return {"workers": []}
        return {"workers": rt.workers(device_id=device_id or None)}

    @r.get("/organism/distributed-runtime/capacity")
    async def capacity() -> dict:
        rt = _get_runtime()
        if rt is None:
            return {"capacity": []}
        return {"capacity": rt.capacity()}

    @r.get("/organism/distributed-runtime/assignments")
    async def assignments(limit: int = 50) -> dict:
        rt = _get_runtime()
        if rt is None:
            return {"assignments": []}
        return {"assignments": rt.assignments(limit=limit)}

    @r.get("/organism/distributed-runtime/capabilities")
    async def capabilities() -> dict:
        rt = _get_runtime()
        if rt is None:
            return {"capabilities": [], "devices": [], "matrix": {}}
        return rt.capabilities_matrix()

    @r.post("/organism/distributed-runtime/workers/register")
    async def register_worker(
        payload: dict,
        principal: str = Depends(require_operator_dep),
    ) -> dict:
        rt = _get_runtime()
        if rt is None:
            raise HTTPException(status_code=503, detail="distributed runtime unavailable")
        worker_id = payload.get("worker_id", "")
        device_id = payload.get("device_id", "")
        runtime_id = payload.get("runtime_id", "")
        if not worker_id or not device_id:
            raise HTTPException(status_code=400, detail="worker_id and device_id required")
        caps = payload.get("capabilities", [])
        meta = payload.get("metadata", {})
        meta["registered_by"] = principal
        worker = rt.register_worker(
            worker_id=worker_id,
            device_id=device_id,
            runtime_id=runtime_id,
            capabilities=caps,
            metadata=meta,
        )
        return {"ok": True, "worker": worker.to_dict()}

    @r.post("/organism/distributed-runtime/workers/heartbeat")
    async def heartbeat(payload: dict) -> dict:
        rt = _get_runtime()
        if rt is None:
            return {"ok": False}
        worker_id = payload.get("worker_id", "")
        if not worker_id:
            raise HTTPException(status_code=400, detail="worker_id required")
        ok = rt.worker_heartbeat(worker_id)
        return {"ok": ok}

    @r.delete("/organism/distributed-runtime/workers/{worker_id}")
    async def unregister_worker(
        worker_id: str,
        principal: str = Depends(require_operator_dep),
    ) -> dict:
        rt = _get_runtime()
        if rt is None:
            raise HTTPException(status_code=503, detail="distributed runtime unavailable")
        ok = rt.unregister_worker(worker_id)
        return {"ok": ok}

    @r.post("/organism/distributed-runtime/route")
    async def route_packet(
        payload: dict,
        principal: str = Depends(require_operator_dep),
    ) -> dict:
        rt = _get_runtime()
        if rt is None:
            raise HTTPException(status_code=503, detail="distributed runtime unavailable")

        class _Packet:
            pass

        pkt = _Packet()
        for k, v in payload.items():
            setattr(pkt, k, v)
        placement = rt.route_packet(pkt)
        return {"placement": placement.to_dict()}

    return r
