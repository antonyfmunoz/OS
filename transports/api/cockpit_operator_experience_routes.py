"""Cockpit operator experience routes — session, send, preview, status.

Mounted under /api/umh/ via include_router in cockpit.py.

Phase 13.0. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

operator_experience_router: APIRouter = APIRouter()

_configured: bool = False
_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


def configure(require_operator_dep: Any) -> None:
    global _configured, operator_experience_router
    _configured = True
    operator_experience_router = _build_router(require_operator_dep)


def _get_orchestrator():
    from substrate.organism.dex_orchestrator import DexOrchestrator
    return DexOrchestrator()


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    r.add_api_route("/organism/operator-experience", _overview, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/operator-experience/sessions", _sessions, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/operator-experience/sessions/{session_id}", _session_detail, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/operator-experience/status", _status, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/operator-experience/approvals", _approvals, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/operator-experience/send", _send, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/operator-experience/packet-preview", _packet_preview, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/operator-experience/propagation-preview", _propagation_preview, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/operator-experience/topology-preview", _topology_preview, methods=["POST"], dependencies=auth)

    return r


async def _overview(request: Request) -> dict[str, Any]:
    orch = _get_orchestrator()
    sessions = orch.list_sessions(limit=10)
    return {
        "status": "operational",
        "phase": "13.0",
        "session_count": len(sessions),
        "recent_sessions": sessions,
    }


async def _sessions(request: Request) -> dict[str, Any]:
    orch = _get_orchestrator()
    limit = int(request.query_params.get("limit", "20"))
    return {
        "sessions": orch.list_sessions(limit=limit),
    }


async def _session_detail(request: Request) -> dict[str, Any]:
    session_id = request.path_params.get("session_id", "")
    orch = _get_orchestrator()
    session = orch.get_session(session_id)
    if not session:
        return {"error": "session_not_found"}
    return session.to_dict()


async def _status(request: Request) -> dict[str, Any]:
    orch = _get_orchestrator()
    roadmap = orch.query_roadmap_status()
    approvals = orch.query_pending_approvals()
    return {
        "roadmap": roadmap,
        "approvals": approvals,
        "system_state": "operational",
    }


async def _approvals(request: Request) -> dict[str, Any]:
    orch = _get_orchestrator()
    return orch.query_pending_approvals()


async def _send(request: Request) -> dict[str, Any]:
    body = await request.json()
    user_input = body.get("input", "")
    session_id = body.get("session_id")
    if not user_input:
        return {"error": "input_required"}
    orch = _get_orchestrator()
    response = orch.receive_operator_input(user_input, session_id=session_id)
    return response.to_dict()


async def _packet_preview(request: Request) -> dict[str, Any]:
    body = await request.json()
    user_input = body.get("input", "")
    if not user_input:
        return {"error": "input_required"}
    orch = _get_orchestrator()
    response = orch.receive_operator_input(user_input)
    return response.to_dict()


async def _propagation_preview(request: Request) -> dict[str, Any]:
    body = await request.json()
    description = body.get("description", "")
    source_node_id = body.get("source_node_id", "")
    if not description:
        return {"error": "description_required"}
    orch = _get_orchestrator()
    try:
        preview = orch.preview_propagation_impact(description, source_node_id)
        return preview
    except Exception as e:
        logger.warning("propagation preview failed: %s", e)
        return {"error": str(e)}


async def _topology_preview(request: Request) -> dict[str, Any]:
    body = await request.json()
    user_input = body.get("input", "")
    if not user_input:
        return {"error": "input_required"}
    orch = _get_orchestrator()
    intent = orch.classify_intent(user_input)
    try:
        result = orch.preview_delegation_topology(intent)
        return result
    except Exception as e:
        logger.warning("topology preview failed: %s", e)
        return {"error": str(e)}
