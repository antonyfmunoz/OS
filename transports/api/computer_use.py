"""Execution substrate API — governed multi-layer agent execution.

Endpoints prefixed /api/umh/execution, registered in app.py.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/umh/execution")

_active_slots: dict[int, dict[str, Any]] = {}
_slot_tasks: dict[int, asyncio.Task[Any]] = {}


class StartRequest(BaseModel):
    task: str
    layer: str = "container"
    slot: int = 0


class SlotRequest(BaseModel):
    slot: int = 0


LAYER_AUTHORITY: dict[str, dict[str, str]] = {
    "native": {
        "authority_class": "supervised_execute",
        "risk_class": "medium",
        "approval_requirement": "founder_approval",
    },
    "container": {
        "authority_class": "approve_execute",
        "risk_class": "low",
        "approval_requirement": "system_approval",
    },
    "wsl": {
        "authority_class": "notify_execute",
        "risk_class": "low",
        "approval_requirement": "system_approval",
    },
    "vm": {
        "authority_class": "autonomous_execute",
        "risk_class": "negligible",
        "approval_requirement": "none",
    },
}


@router.post("/start")
async def start_execution(req: StartRequest) -> dict[str, Any]:
    authority = LAYER_AUTHORITY.get(req.layer)
    if not authority:
        return {"success": False, "error": f"unknown layer: {req.layer}"}

    if req.slot in _active_slots:
        return {"success": False, "error": f"slot {req.slot} already active"}

    _active_slots[req.slot] = {
        "layer": req.layer,
        "task": req.task,
        "status": "running",
        "step_count": 0,
        "authority_class": authority["authority_class"],
        "risk_class": authority["risk_class"],
        "approval_status": authority["approval_requirement"],
        "action_log": [],
    }

    return {
        "success": True,
        "slot": req.slot,
        "layer": req.layer,
        "authority": authority,
    }


@router.post("/stop")
async def stop_execution(req: SlotRequest) -> dict[str, Any]:
    if req.slot not in _active_slots:
        return {"success": False, "error": f"slot {req.slot} not active"}

    _active_slots[req.slot]["status"] = "stopped"
    task = _slot_tasks.pop(req.slot, None)
    if task and not task.done():
        task.cancel()
    del _active_slots[req.slot]

    return {"success": True, "slot": req.slot}


@router.post("/pause")
async def pause_execution(req: SlotRequest) -> dict[str, Any]:
    if req.slot not in _active_slots:
        return {"success": False, "error": f"slot {req.slot} not active"}

    _active_slots[req.slot]["status"] = "paused"
    return {"success": True, "slot": req.slot}


@router.post("/resume")
async def resume_execution(req: SlotRequest) -> dict[str, Any]:
    if req.slot not in _active_slots:
        return {"success": False, "error": f"slot {req.slot} not active"}

    _active_slots[req.slot]["status"] = "running"
    return {"success": True, "slot": req.slot}


@router.get("/status")
async def get_status() -> dict[str, Any]:
    slots = []
    for slot_id, state in sorted(_active_slots.items()):
        slots.append({
            "slot": slot_id,
            "layer": state["layer"],
            "task": state["task"],
            "status": state["status"],
            "step_count": state["step_count"],
            "authority_class": state["authority_class"],
            "risk_class": state["risk_class"],
            "approval_status": state["approval_status"],
        })
    return {"slots": slots}


@router.get("/log")
async def get_log(slot: int = 0) -> dict[str, Any]:
    state = _active_slots.get(slot)
    if not state:
        return {"slot": slot, "log": []}
    return {"slot": slot, "log": state.get("action_log", [])}


@router.get("/authority")
async def preview_authority(layer: str = "container") -> dict[str, Any]:
    authority = LAYER_AUTHORITY.get(layer)
    if not authority:
        return {"error": f"unknown layer: {layer}"}
    return {"layer": layer, **authority}


@router.post("/container/start")
async def start_container(
    image: str = "umh-computer-use:latest",
    slot: int = 0,
    mem_limit: str = "2g",
) -> dict[str, Any]:
    try:
        from nodes.windows.umh_node.adapters.container import ContainerAdapter

        adapter = ContainerAdapter()
        return adapter.handle(
            "container.spawn",
            {"image": image, "slot": slot, "mem_limit": mem_limit},
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.post("/container/stop")
async def stop_container(container_name: str = "") -> dict[str, Any]:
    try:
        from nodes.windows.umh_node.adapters.container import ContainerAdapter

        adapter = ContainerAdapter()
        return adapter.handle("container.stop", {"container_name": container_name})
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.get("/containers")
async def list_containers() -> dict[str, Any]:
    try:
        from nodes.windows.umh_node.adapters.container import ContainerAdapter

        adapter = ContainerAdapter()
        return adapter.handle("container.list", {})
    except Exception as exc:
        return {"success": False, "error": str(exc)}
