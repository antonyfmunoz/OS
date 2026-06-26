"""Cockpit distributed runtime routes — organism worker routing surface.

Mounted under /api/umh/ via include_router in cockpit.py.
Read-only queries + governed worker registration and packet routing.
No execution authority.

Phase 24. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import re
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
    r = APIRouter(dependencies=[Depends(require_operator_dep)])

    @r.get("/organism/distributed-runtime")
    def overview() -> dict:
        rt = _get_runtime()
        if rt is None:
            return {"error": "distributed runtime unavailable"}
        return rt.overview()

    @r.get("/organism/distributed-runtime/devices")
    def devices() -> dict:
        rt = _get_runtime()
        if rt is None:
            return {"devices": []}
        return {"devices": rt.device_summary()}

    @r.get("/organism/distributed-runtime/workers")
    def workers(device_id: str = "") -> dict:
        rt = _get_runtime()
        if rt is None:
            return {"workers": []}
        return {"workers": rt.workers(device_id=device_id or None)}

    @r.get("/organism/distributed-runtime/capacity")
    def capacity() -> dict:
        rt = _get_runtime()
        if rt is None:
            return {"capacity": []}
        return {"capacity": rt.capacity()}

    @r.get("/organism/distributed-runtime/assignments")
    def assignments(limit: int = 50) -> dict:
        rt = _get_runtime()
        if rt is None:
            return {"assignments": []}
        clamped = max(1, min(limit, 500))
        return {"assignments": rt.assignments(limit=clamped)}

    @r.get("/organism/distributed-runtime/capabilities")
    def capabilities() -> dict:
        rt = _get_runtime()
        if rt is None:
            return {"capabilities": [], "devices": [], "matrix": {}}
        return rt.capabilities_matrix()

    _SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-]{1,128}$")
    _ALLOWED_CAPABILITIES = frozenset(
        {
            "code_write",
            "code_review",
            "code_execution",
            "react_build",
            "electron_build",
            "browser_automation",
            "gpu_compute",
            "media_generation",
            "deployment",
            "documentation",
        }
    )

    @r.post("/organism/distributed-runtime/workers/register")
    def register_worker(
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
        if not _SAFE_ID_PATTERN.match(worker_id) or not _SAFE_ID_PATTERN.match(device_id):
            raise HTTPException(status_code=400, detail="invalid worker_id or device_id format")
        caps = payload.get("capabilities", [])
        if not isinstance(caps, list) or not all(
            isinstance(c, str) and c in _ALLOWED_CAPABILITIES for c in caps
        ):
            raise HTTPException(
                status_code=400, detail="capabilities must be a list of known capability strings"
            )
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
    def heartbeat(payload: dict) -> dict:
        rt = _get_runtime()
        if rt is None:
            return {"ok": False}
        worker_id = payload.get("worker_id", "")
        if not worker_id:
            raise HTTPException(status_code=400, detail="worker_id required")
        if not _SAFE_ID_PATTERN.match(worker_id):
            raise HTTPException(status_code=400, detail="invalid worker_id format")
        ok = rt.worker_heartbeat(worker_id)
        return {"ok": ok}

    @r.delete("/organism/distributed-runtime/workers/{worker_id}")
    def unregister_worker(
        worker_id: str,
        principal: str = Depends(require_operator_dep),
    ) -> dict:
        rt = _get_runtime()
        if rt is None:
            raise HTTPException(status_code=503, detail="distributed runtime unavailable")
        if not _SAFE_ID_PATTERN.match(worker_id):
            raise HTTPException(status_code=400, detail="invalid worker_id format")
        worker = rt._worker_registry.get(worker_id) if hasattr(rt, "_worker_registry") else None
        if worker is not None:
            registered_by = (worker.metadata or {}).get("registered_by", "")
            if registered_by and registered_by != principal:
                raise HTTPException(
                    status_code=403, detail="not authorized to unregister this worker"
                )
        ok = rt.unregister_worker(worker_id)
        return {"ok": ok}

    @r.post("/organism/distributed-runtime/route")
    def route_packet(
        payload: dict,
        principal: str = Depends(require_operator_dep),
    ) -> dict:
        rt = _get_runtime()
        if rt is None:
            raise HTTPException(status_code=503, detail="distributed runtime unavailable")

        class _Packet:
            def __init__(
                self, packet_id: str, description: str, target_repo: str, action_type: str
            ) -> None:
                self.packet_id = packet_id
                self.description = description
                self.target_repo = target_repo
                self.action_type = action_type

        pkt = _Packet(
            packet_id=str(payload.get("packet_id", "")),
            description=str(payload.get("description", "")),
            target_repo=str(payload.get("target_repo", "")),
            action_type=str(payload.get("action_type", "")),
        )
        placement = rt.route_packet(pkt)
        return {"placement": placement.to_dict()}

    return r
