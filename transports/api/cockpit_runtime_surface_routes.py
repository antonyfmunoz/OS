"""Cockpit runtime surface routes — session lifecycle, events, adapters.

Mounted under /api/umh/ via include_router in cockpit.py.

Phase 13.2. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

runtime_surface_router: APIRouter = APIRouter()

_configured: bool = False


def configure(require_operator_dep: Any) -> None:
    global _configured, runtime_surface_router
    _configured = True
    runtime_surface_router = _build_router(require_operator_dep)


def _get_manager() -> Any:
    from substrate.organism.runtime_manager import RuntimeManager
    return RuntimeManager()


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    r.add_api_route("/organism/runtime-surface", _overview, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/runtime-surface/sessions", _sessions, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/runtime-surface/sessions/{session_id}", _session_detail, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/runtime-surface/sessions/{session_id}/events", _session_events, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/runtime-surface/adapters", _adapters, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/runtime-surface/create", _create_session, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/runtime-surface/sessions/{session_id}/start", _start_session, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/runtime-surface/sessions/{session_id}/inject", _inject_message, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/runtime-surface/sessions/{session_id}/stop", _stop_session, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/runtime-surface/handoff-preview", _handoff_preview, methods=["POST"], dependencies=auth)

    return r


async def _overview(request: Request) -> dict[str, Any]:
    mgr = _get_manager()
    return mgr.get_overview()


async def _sessions(request: Request) -> dict[str, Any]:
    mgr = _get_manager()
    return {"sessions": mgr.list_sessions()}


async def _session_detail(request: Request, session_id: str) -> dict[str, Any]:
    mgr = _get_manager()
    session = mgr.get_session(session_id)
    if not session:
        return {"error": "session not found", "session_id": session_id}
    return session


async def _session_events(request: Request, session_id: str) -> dict[str, Any]:
    mgr = _get_manager()
    events = mgr.get_events(session_id)
    return {"session_id": session_id, "events": events, "count": len(events)}


async def _adapters(request: Request) -> dict[str, Any]:
    mgr = _get_manager()
    return {"adapters": mgr.get_adapters()}


async def _create_session(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {"error": "invalid JSON body"}

    mgr = _get_manager()
    session, policy = mgr.create_runtime_session(
        runtime_type=body.get("runtime_type", "shell"),
        command=body.get("command", ""),
        prompt=body.get("prompt", ""),
        work_packet_id=body.get("work_packet_id", ""),
        operator_session_id=body.get("operator_session_id", ""),
        workcell_id=body.get("workcell_id", ""),
        risk_class=body.get("risk_class", "low"),
        cwd=body.get("cwd", ""),
        idempotency_key=body.get("idempotency_key", ""),
    )
    return {
        "session": session.to_dict(),
        "policy": policy,
    }


async def _start_session(request: Request, session_id: str) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        body = {}

    mgr = _get_manager()
    result = mgr.start_session(session_id, approved_by=body.get("approved_by", "operator"))
    return {
        "session_id": result.session_id,
        "started": result.started,
        "status": result.status,
        "output": result.output[:2000] if result.output else "",
        "error": result.error,
    }


async def _inject_message(request: Request, session_id: str) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {"error": "invalid JSON body"}

    mgr = _get_manager()
    return mgr.inject_message(
        session_id=session_id,
        message=body.get("message", ""),
        mode=body.get("mode", "stdin"),
    )


async def _stop_session(request: Request, session_id: str) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        body = {}

    mgr = _get_manager()
    return mgr.stop_session(session_id, reason=body.get("reason", "operator_requested"))


async def _handoff_preview(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {"error": "invalid JSON body"}

    from substrate.organism.runtime_handoff import create_handoff_preview
    preview = create_handoff_preview(
        work_packet_id=body.get("work_packet_id", ""),
        workcell_id=body.get("workcell_id", ""),
        operator_session_id=body.get("operator_session_id", ""),
        operator_input=body.get("input", ""),
        intent_type=body.get("intent_type", "create_work"),
        risk_class=body.get("risk_class", "low"),
        command=body.get("command", ""),
        prompt=body.get("prompt", ""),
    )
    return preview.to_dict()
