"""Cockpit compute fabric routes — unified compute body map surface.

Mounted under /api/umh/ via include_router in cockpit.py.
Read-only queries + routing decisions. No execution authority.

W1. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

compute_fabric_router: APIRouter = APIRouter()

_configured: bool = False
_fabric_instance: Any = None


def configure(*, require_operator_dep: Any) -> None:
    global _configured, compute_fabric_router
    if _configured:
        return
    _configured = True
    compute_fabric_router = _build_router(require_operator_dep)


def _get_fabric() -> Any:
    global _fabric_instance
    if _fabric_instance is not None:
        return _fabric_instance
    try:
        from substrate.organism.compute_fabric_runtime import ComputeFabricRuntime
        from substrate.organism.distributed_runtime import DistributedRuntime

        dr = DistributedRuntime()
        _fabric_instance = ComputeFabricRuntime(dr)
        return _fabric_instance
    except Exception as exc:
        logger.debug("compute fabric routes: failed to create fabric: %s", exc)
        return None


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter(dependencies=[Depends(require_operator_dep)])

    @r.get("/compute/fabric")
    def fabric_nodes() -> dict:
        fabric = _get_fabric()
        if fabric is None:
            return {"nodes": [], "error": "compute fabric unavailable"}
        return {"nodes": [n.to_dict() for n in fabric.nodes()]}

    @r.get("/compute/health")
    def fabric_health() -> dict:
        fabric = _get_fabric()
        if fabric is None:
            return {"fabric_status": "unavailable", "total_nodes": 0}
        return fabric.health()

    @r.get("/compute/executions")
    def fabric_executions() -> dict:
        fabric = _get_fabric()
        if fabric is None:
            return {"executions": []}
        return {"executions": fabric.active_executions()}

    @r.post("/compute/route")
    def fabric_route(payload: dict) -> dict:
        fabric = _get_fabric()
        if fabric is None:
            raise HTTPException(status_code=503, detail="compute fabric unavailable")
        capability_needs = payload.get("capability_needs", [])
        if not isinstance(capability_needs, list) or not all(
            isinstance(c, str) for c in capability_needs
        ):
            raise HTTPException(
                status_code=400, detail="capability_needs must be a list of strings"
            )
        risk_level = str(payload.get("risk_level", "low"))
        captured: dict = {}

        def _do_route():
            decision = fabric.route(capability_needs=capability_needs, risk_level=risk_level)
            captured.update(decision.to_dict())
            return f"compute route: {capability_needs}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"compute fabric route: {capability_needs}",
            execute_fn=_do_route,
            source="cockpit",
            metadata={"capability_needs": capability_needs, "risk_level": risk_level},
        )
        if not resp.success:
            return resp.to_http_dict()
        return captured

    return r
