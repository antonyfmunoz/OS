"""Cockpit universal work queue routes — packets, workcells, roles, knowledge.

Mounted under /api/umh/ via include_router in cockpit.py.

Phase 11.1. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

universal_work_router: APIRouter = APIRouter()

_configured: bool = False


def configure(require_operator_dep: Any) -> None:
    global _configured, universal_work_router
    _configured = True
    universal_work_router = _build_router(require_operator_dep)


def _get_queue():
    from substrate.organism.universal_work_queue import UniversalWorkQueue
    return UniversalWorkQueue()


def _get_workcells():
    from substrate.organism.workcell import load_workcells
    return load_workcells()


def _get_role_contracts():
    from substrate.organism.role_contracts import load_role_contracts, SEED_ROLE_CONTRACTS, RoleContract
    contracts = load_role_contracts()
    if not contracts:
        contracts = [RoleContract.from_dict(d) for d in SEED_ROLE_CONTRACTS]
    return contracts


def _get_knowledge_registry():
    from substrate.organism.knowledge_model_registry import KnowledgeModelRegistry
    return KnowledgeModelRegistry()


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    r.add_api_route("/organism/universal-work", _overview, methods=["GET"])
    r.add_api_route("/organism/universal-work/summary", _summary, methods=["GET"])
    r.add_api_route("/organism/universal-work/packets", _packets, methods=["GET"])
    r.add_api_route("/organism/universal-work/packets/{packet_id}", _packet_detail, methods=["GET"])
    r.add_api_route("/organism/universal-work/next", _next_best, methods=["GET"])
    r.add_api_route("/organism/universal-work/domain/{domain}", _by_domain, methods=["GET"])
    r.add_api_route("/organism/universal-work/blocked", _blocked, methods=["GET"])
    r.add_api_route("/organism/universal-work/human-required", _human_required, methods=["GET"])
    r.add_api_route("/organism/universal-work/approval-required", _approval_required, methods=["GET"])

    r.add_api_route("/organism/universal-work/create", _create_packet, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/universal-work/packets/{packet_id}/status", _update_status, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/universal-work/packets/{packet_id}/link", _link_artifact, methods=["POST"], dependencies=auth)

    r.add_api_route("/organism/workcells", _workcells_list, methods=["GET"])
    r.add_api_route("/organism/workcells/{workcell_id}", _workcell_detail, methods=["GET"])
    r.add_api_route("/organism/role-contracts", _role_contracts_list, methods=["GET"])
    r.add_api_route("/organism/knowledge-models", _knowledge_models_list, methods=["GET"])

    return r


async def _overview():
    queue = _get_queue()
    return queue.compute_queue_summary()


async def _summary():
    return _get_queue().compute_queue_summary()


async def _packets(status: str | None = None, domain: str | None = None, limit: int = 50):
    queue = _get_queue()
    items = queue.all_packets()
    if status:
        items = [p for p in items if p.status.value == status]
    if domain:
        items = [p for p in items if p.domain == domain]
    items.sort(key=lambda x: x.leverage_score, reverse=True)
    return [p.to_safe_dict() for p in items[:limit]]


async def _packet_detail(packet_id: str):
    pkt = _get_queue().get_packet(packet_id)
    if not pkt:
        return {"error": "Not found", "packet_id": packet_id}
    return pkt.to_dict()


async def _next_best():
    pkt = _get_queue().get_next_best_packet()
    if not pkt:
        return {"next": None, "reason": "No eligible work packets"}
    return {"next": pkt.to_safe_dict()}


async def _by_domain(domain: str):
    return [p.to_safe_dict() for p in _get_queue().get_packets_by_domain(domain)]


async def _blocked():
    return [p.to_safe_dict() for p in _get_queue().get_blocked_packets()]


async def _human_required():
    return [p.to_safe_dict() for p in _get_queue().get_packets_requiring_human()]


async def _approval_required():
    return [p.to_safe_dict() for p in _get_queue().get_packets_requiring_approval()]


async def _create_packet(request: Request):
    body = await request.json()
    user_intent = body.get("user_intent", "")
    if not user_intent:
        return {"success": False, "error": "user_intent is required"}
    desired_end_state = body.get("desired_end_state", "")
    constraints = body.get("constraints", [])

    queue = _get_queue()
    packet = queue.ingest_user_intent(
        user_intent=user_intent,
        desired_end_state=desired_end_state,
        constraints=constraints,
    )
    return {"success": True, "packet": packet.to_safe_dict()}


async def _update_status(packet_id: str, request: Request):
    body = await request.json()
    new_status_str = body.get("status", "")
    reason = body.get("reason", "")

    from substrate.organism.work_packet import PacketLifecycleStatus
    try:
        new_status = PacketLifecycleStatus(new_status_str)
    except ValueError:
        return {"success": False, "error": f"Invalid status: {new_status_str}"}

    queue = _get_queue()
    ok = queue.update_packet_status(packet_id, new_status, reason)
    return {"success": ok, "packet_id": packet_id, "new_status": new_status_str}


_MAX_ARTIFACT_ID_LEN = 256


def _validate_artifact_id(value: str, label: str) -> str | None:
    if not value or len(value) > _MAX_ARTIFACT_ID_LEN:
        return f"{label} must be 1-{_MAX_ARTIFACT_ID_LEN} characters"
    if any(ord(c) < 32 for c in value):
        return f"{label} contains non-printable characters"
    return None


async def _link_artifact(packet_id: str, request: Request):
    body = await request.json()
    artifacts = {}
    for key in ("pr_url", "sandbox_id", "approval_packet_id"):
        val = body.get(key, "")
        if val:
            err = _validate_artifact_id(val, key)
            if err:
                return {"success": False, "error": err}
            artifacts[key] = val

    if not artifacts:
        return {"success": False, "error": "No valid artifacts provided"}

    queue = _get_queue()
    ok = queue.link_execution_artifacts(packet_id, artifacts)
    return {"success": ok, "packet_id": packet_id}


async def _workcells_list():
    wcs = _get_workcells()
    return [wc.to_dict() for wc in wcs]


async def _workcell_detail(workcell_id: str):
    wcs = _get_workcells()
    for wc in wcs:
        if wc.workcell_id == workcell_id:
            return wc.to_dict()
    return {"error": "Not found", "workcell_id": workcell_id}


async def _role_contracts_list():
    contracts = _get_role_contracts()
    return [rc.to_dict() for rc in contracts]


async def _knowledge_models_list():
    registry = _get_knowledge_registry()
    return registry.summary()
