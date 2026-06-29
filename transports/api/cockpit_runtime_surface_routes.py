"""Cockpit runtime surface routes — session lifecycle, events, adapters.

Mounted under /api/umh/ via include_router in cockpit.py.

Phase 13.2. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

from transports.api.governed import governed_mutation

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


def _overview(request: Request) -> dict[str, Any]:
    mgr = _get_manager()
    return mgr.get_overview()


def _sessions(request: Request) -> dict[str, Any]:
    mgr = _get_manager()
    return {"sessions": mgr.list_sessions()}


def _session_detail(request: Request, session_id: str) -> dict[str, Any]:
    mgr = _get_manager()
    session = mgr.get_session(session_id)
    if not session:
        return {"error": "session not found", "session_id": session_id}
    return session


def _session_events(request: Request, session_id: str) -> dict[str, Any]:
    mgr = _get_manager()
    events = mgr.get_events(session_id)
    return {"session_id": session_id, "events": events, "count": len(events)}


def _adapters(request: Request) -> dict[str, Any]:
    mgr = _get_manager()
    return {"adapters": mgr.get_adapters()}


async def _create_session(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {"error": "invalid JSON body"}
    captured: dict = {}

    def _do_create():
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
        captured.update({"session": session.to_dict(), "policy": policy})
        return f"session created: {body.get('runtime_type', 'shell')}", True

    resp = governed_mutation(
        mutation_name="sandbox_create",
        intent=f"create runtime session: {body.get('runtime_type', 'shell')}",
        execute_fn=_do_create,
        source="cockpit",
    )
    if not resp.success:
        return resp.to_http_dict()
    return captured


async def _start_session(request: Request, session_id: str) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        body = {}
    captured: dict = {}

    def _do_start():
        mgr = _get_manager()
        result = mgr.start_session(session_id, approved_by=body.get("approved_by", "operator"))
        captured.update({
            "session_id": result.session_id,
            "started": result.started,
            "status": result.status,
            "output": result.output[:2000] if result.output else "",
            "error": result.error,
        })
        return f"session {session_id} started", result.started

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"start runtime session {session_id}",
        execute_fn=_do_start,
        source="cockpit",
    )
    if not resp.success:
        return resp.to_http_dict()
    return captured


async def _inject_message(request: Request, session_id: str) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {"error": "invalid JSON body"}

    def _do_inject():
        mgr = _get_manager()
        mgr.inject_message(
            session_id=session_id,
            message=body.get("message", ""),
            mode=body.get("mode", "stdin"),
        )
        return f"message injected to {session_id}", True

    resp = governed_mutation(
        mutation_name="conversation_send",
        intent=f"inject message to session {session_id}",
        execute_fn=_do_inject,
        source="cockpit",
    )
    return resp.to_http_dict()


async def _stop_session(request: Request, session_id: str) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        body = {}

    def _do_stop():
        mgr = _get_manager()
        mgr.stop_session(session_id, reason=body.get("reason", "operator_requested"))
        return f"session {session_id} stopped", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"stop runtime session {session_id}",
        execute_fn=_do_stop,
        source="cockpit",
    )
    return resp.to_http_dict()


async def _handoff_preview(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {"error": "invalid JSON body"}
    captured: dict = {}

    def _do_preview():
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
        captured.update(preview.to_dict())
        return "handoff preview created", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent="create handoff preview",
        execute_fn=_do_preview,
        source="cockpit",
    )
    if not resp.success:
        return resp.to_http_dict()
    return captured
