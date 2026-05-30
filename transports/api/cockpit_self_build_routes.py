"""Cockpit self-build queue routes — summary, items, next, blocked, ready,
item detail, status updates, artifact linking, roadmap.

Mounted under /api/umh/ via include_router in cockpit.py.

Auth model: configure() must be called before include_router(). It receives
the real operator-auth dependency from cockpit.py.

Phase 11.0. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

self_build_router: APIRouter = APIRouter()

_get_organism: Callable[[], Any] = lambda: None
_configured: bool = False


def configure(
    get_organism_fn: Callable[[], Any],
    require_operator_dep: Any,
) -> None:
    global _get_organism, _configured, self_build_router

    _get_organism = get_organism_fn
    _configured = True
    self_build_router = _build_router(require_operator_dep)


def _get_queue():
    from substrate.organism.self_build_queue import SelfBuildQueueEngine
    return SelfBuildQueueEngine()


def _get_roadmap():
    from substrate.organism.roadmap_engine import RoadmapEngine
    return RoadmapEngine()


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    r.add_api_route("/organism/self-build", _self_build_overview, methods=["GET"])
    r.add_api_route("/organism/self-build/summary", _self_build_summary, methods=["GET"])
    r.add_api_route("/organism/self-build/items", _self_build_items, methods=["GET"])
    r.add_api_route("/organism/self-build/next", _self_build_next, methods=["GET"])
    r.add_api_route("/organism/self-build/blocked", _self_build_blocked, methods=["GET"])
    r.add_api_route("/organism/self-build/ready-for-approval", _self_build_ready, methods=["GET"])
    r.add_api_route("/organism/self-build/items/{item_id}", _self_build_item_detail, methods=["GET"])
    r.add_api_route("/organism/roadmap", _roadmap_overview, methods=["GET"])
    r.add_api_route("/organism/roadmap/{phase_id}", _roadmap_phase_detail, methods=["GET"])

    r.add_api_route("/organism/self-build/items/{item_id}/status", _self_build_update_status, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/self-build/items/{item_id}/link", _self_build_link_artifact, methods=["POST"], dependencies=auth)

    return r


async def _self_build_overview():
    queue = _get_queue()
    roadmap = _get_roadmap()
    return {
        "queue": queue.compute_queue_summary(),
        "roadmap": roadmap.summary(),
    }


async def _self_build_summary():
    return _get_queue().compute_queue_summary()


async def _self_build_items(status: str | None = None, limit: int = 50):
    queue = _get_queue()
    items = queue.all_items()
    if status:
        items = [i for i in items if i.status.value == status]
    items.sort(key=lambda x: x.weighted_score, reverse=True)
    return [i.to_safe_dict() for i in items[:limit]]


async def _self_build_next():
    item = _get_queue().get_next_best_work()
    if not item:
        return {"next": None, "reason": "No eligible work items"}
    return {"next": item.to_dict()}


async def _self_build_blocked():
    return [i.to_safe_dict() for i in _get_queue().get_blocked_work()]


async def _self_build_ready():
    return [i.to_safe_dict() for i in _get_queue().get_ready_for_approval()]


async def _self_build_item_detail(item_id: str):
    item = _get_queue().get_item(item_id)
    if not item:
        return {"error": "Not found", "item_id": item_id}
    return item.to_dict()


async def _roadmap_overview():
    return _get_roadmap().summary()


async def _roadmap_phase_detail(phase_id: str):
    phase = _get_roadmap().get_phase(phase_id)
    if not phase:
        return {"error": "Not found", "phase_id": phase_id}
    return phase.to_dict()


async def _self_build_update_status(item_id: str, request: Request):
    body = await request.json()
    new_status_str = body.get("status", "")
    reason = body.get("reason", "")

    from substrate.organism.self_build_queue import WorkItemStatus
    try:
        new_status = WorkItemStatus(new_status_str)
    except ValueError:
        return {"success": False, "error": f"Invalid status: {new_status_str}"}

    queue = _get_queue()
    ok = queue.update_status(item_id, new_status, reason)
    return {"success": ok, "item_id": item_id, "new_status": new_status_str}


async def _self_build_link_artifact(item_id: str, request: Request):
    body = await request.json()
    artifact_type = body.get("type", "")
    queue = _get_queue()

    if artifact_type == "approval_packet":
        ok = queue.link_approval_packet(item_id, body.get("packet_id", ""))
    elif artifact_type == "sandbox":
        ok = queue.link_sandbox(item_id, body.get("sandbox_id", ""), body.get("branch_name", ""))
    elif artifact_type == "pr":
        ok = queue.link_pr(item_id, body.get("pr_url", ""))
    elif artifact_type == "production_truth":
        ok = queue.link_production_truth(item_id, body.get("delta_id", ""))
    else:
        return {"success": False, "error": f"Unknown artifact type: {artifact_type}"}

    return {"success": ok, "item_id": item_id, "artifact_type": artifact_type}
