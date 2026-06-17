"""Cockpit agent fleet routes — unified agent coordination surface.

Mounted under /api/umh/ via include_router in cockpit.py.
Read queries + assignment + dispatch. No direct execution authority.

W3. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

agent_fleet_router: APIRouter = APIRouter()

_configured: bool = False
_fleet_instance: Any = None


def configure(*, require_operator_dep: Any) -> None:
    global _configured, agent_fleet_router
    if _configured:
        return
    _configured = True
    agent_fleet_router = _build_router(require_operator_dep)


def _get_fleet() -> Any:
    global _fleet_instance
    if _fleet_instance is not None:
        return _fleet_instance
    try:
        from substrate.organism.agent_capability_model import AgentCapabilityModel
        from substrate.organism.agent_fleet_runtime import AgentFleetRuntime
        from substrate.organism.agent_registry import AgentRegistry
        from substrate.organism.compute_fabric_runtime import ComputeFabricRuntime
        from substrate.organism.distributed_runtime import DistributedRuntime

        dr = DistributedRuntime()
        fabric = ComputeFabricRuntime(dr)
        capability_model = AgentCapabilityModel()
        registry = AgentRegistry()

        _fleet_instance = AgentFleetRuntime(
            capability_model=capability_model,
            compute_fabric=fabric,
            agent_registry=registry,
        )
        return _fleet_instance
    except Exception as exc:
        logger.debug("agent fleet routes: failed to create fleet: %s", exc)
        return None


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter(dependencies=[Depends(require_operator_dep)])

    @r.get("/fleet/status")
    async def fleet_status() -> dict:
        fleet = _get_fleet()
        if fleet is None:
            return {"error": "agent fleet unavailable"}
        return fleet.fleet_status().to_dict()

    @r.get("/fleet/health")
    async def fleet_health() -> dict:
        fleet = _get_fleet()
        if fleet is None:
            return {"error": "agent fleet unavailable"}
        return fleet.fleet_health().to_dict()

    @r.get("/fleet/dispatches")
    async def fleet_dispatches() -> dict:
        fleet = _get_fleet()
        if fleet is None:
            return {"dispatches": []}
        return {"dispatches": [d.to_dict() for d in fleet.active_dispatches()]}

    @r.get("/fleet/dispatches/{dispatch_id}")
    async def fleet_dispatch_detail(dispatch_id: str) -> dict:
        fleet = _get_fleet()
        if fleet is None:
            raise HTTPException(status_code=503, detail="agent fleet unavailable")
        result = fleet.dispatch_result(dispatch_id)
        if result is None:
            dispatch = fleet._dispatches.get(dispatch_id)
            if dispatch is None:
                raise HTTPException(status_code=404, detail="dispatch not found")
            return dispatch.to_dict()
        return result.to_dict()

    @r.post("/fleet/assign")
    async def fleet_assign(payload: dict) -> dict:
        fleet = _get_fleet()
        if fleet is None:
            raise HTTPException(status_code=503, detail="agent fleet unavailable")
        caps = payload.get("capabilities_required", [])
        if not isinstance(caps, list) or not all(isinstance(c, str) for c in caps):
            raise HTTPException(
                status_code=400, detail="capabilities_required must be a list of strings"
            )
        risk = str(payload.get("risk_class", "low"))
        domain = str(payload.get("domain", ""))
        assignment = fleet.assign(
            capabilities_required=caps, risk_class=risk, domain=domain,
        )
        return assignment.to_dict()

    @r.post("/fleet/dispatch")
    async def fleet_dispatch(payload: dict) -> dict:
        fleet = _get_fleet()
        if fleet is None:
            raise HTTPException(status_code=503, detail="agent fleet unavailable")
        caps = payload.get("capabilities_required", [])
        if not isinstance(caps, list) or not all(isinstance(c, str) for c in caps):
            raise HTTPException(
                status_code=400, detail="capabilities_required must be a list of strings"
            )
        risk = str(payload.get("risk_class", "low"))
        domain = str(payload.get("domain", ""))
        description = str(payload.get("description", ""))
        assignment = fleet.assign(
            capabilities_required=caps, risk_class=risk, domain=domain,
        )
        if not assignment.agent_type:
            raise HTTPException(status_code=404, detail=assignment.rationale.summary)
        dispatch = fleet.dispatch(assignment, description=description)
        return dispatch.to_dict()

    @r.post("/fleet/wave")
    async def fleet_wave(payload: dict) -> dict:
        fleet = _get_fleet()
        if fleet is None:
            raise HTTPException(status_code=503, detail="agent fleet unavailable")
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise HTTPException(status_code=400, detail="items must be a list")
        assignments = []
        for item in items:
            caps = item.get("capabilities_required", [])
            risk = str(item.get("risk_class", "low"))
            domain = str(item.get("domain", ""))
            a = fleet.assign(capabilities_required=caps, risk_class=risk, domain=domain)
            if a.agent_type:
                assignments.append(a)
        result = fleet.dispatch_wave(assignments)
        return result.to_dict()

    @r.get("/fleet/utilization")
    async def fleet_utilization() -> dict:
        fleet = _get_fleet()
        if fleet is None:
            return {"utilization": {}}
        return {"utilization": fleet.agent_utilization()}

    return r
