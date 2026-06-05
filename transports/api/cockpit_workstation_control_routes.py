"""Cockpit workstation control routes — execution pause/resume/stop with environment awareness.

Mounted under /api/umh/ via include_router in cockpit.py.
Replaces execution_pause/execution_resume/execution_stop stubs from cockpit.py.

Phase 14.11A. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import platform
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

workstation_control_router: APIRouter = APIRouter()

_configured: bool = False


def configure(require_operator_dep: Any) -> None:
    global _configured, workstation_control_router
    _configured = True
    workstation_control_router = _build_router(require_operator_dep)


def _get_manager() -> Any:
    from substrate.organism.runtime_manager import RuntimeManager
    return RuntimeManager()


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    r.add_api_route(
        "/workstation/execution/pause",
        _execution_pause,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/workstation/execution/resume",
        _execution_resume,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/workstation/execution/stop",
        _execution_stop,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/workstation/execution/status",
        _execution_status,
        methods=["GET"],
        dependencies=auth,
    )

    return r


def _resolve_adapter(session_id: str) -> tuple[Any, Any, dict[str, Any] | None]:
    """Resolve the RuntimeManager, adapter, and session for a given session_id.

    Returns (manager, adapter, error_dict). error_dict is None on success.
    """
    mgr = _get_manager()
    from substrate.organism.runtime_session import get_session
    session = get_session(session_id)
    if not session:
        return mgr, None, {"ok": False, "error": f"session {session_id} not found"}

    adapter = mgr._adapters.get(session.runtime_type)
    if not adapter:
        return mgr, None, {"ok": False, "error": f"no adapter for runtime_type={session.runtime_type}"}

    return mgr, adapter, None


async def _execution_pause(request: Request) -> dict[str, Any]:
    body = await request.json()
    packet_id = body.get("packet_id", "")
    session_id = body.get("session_id", "")
    reason = body.get("reason", "operator requested pause")

    if not packet_id and not session_id:
        return {"ok": False, "error": "packet_id or session_id is required"}

    result: dict[str, Any] = {
        "ok": False,
        "packet_id": packet_id,
        "session_id": session_id,
        "environment": platform.system().lower(),
    }

    if session_id:
        _, adapter, err = _resolve_adapter(session_id)
        if err:
            result.update(err)
            return result

        pause_result = adapter.pause(session_id, reason=reason)
        result["runtime_pause"] = pause_result
        result["ok"] = pause_result.get("paused", False)
        result["supported"] = pause_result.get("supported", False)
    else:
        result["supported"] = False
        result["runtime_pause"] = {"paused": False, "reason": "no session_id — packet-only pause"}

    if packet_id:
        from substrate.organism.work_packet_engine import WorkPacketEngine
        from substrate.organism.work_packet import PacketLifecycleStatus
        wpe = WorkPacketEngine()
        pkt = wpe.get_packet(packet_id)
        if pkt and pkt.status == PacketLifecycleStatus.EXECUTING:
            ok = wpe.update_packet_status(packet_id, PacketLifecycleStatus.PAUSED, reason)
            result["packet_status_updated"] = ok
            result["ok"] = result.get("ok", False) or ok
        elif pkt:
            result["packet_status_updated"] = False
            result["packet_status_reason"] = f"cannot pause from status '{pkt.status.value}'"
        else:
            result["packet_status_updated"] = False
            result["packet_status_reason"] = f"packet {packet_id} not found"

    return result


async def _execution_resume(request: Request) -> dict[str, Any]:
    body = await request.json()
    packet_id = body.get("packet_id", "")
    session_id = body.get("session_id", "")
    reason = body.get("reason", "operator requested resume")

    if not packet_id and not session_id:
        return {"ok": False, "error": "packet_id or session_id is required"}

    result: dict[str, Any] = {
        "ok": False,
        "packet_id": packet_id,
        "session_id": session_id,
        "environment": platform.system().lower(),
    }

    if session_id:
        _, adapter, err = _resolve_adapter(session_id)
        if err:
            result.update(err)
            return result

        resume_result = adapter.resume(session_id, reason=reason)
        result["runtime_resume"] = resume_result
        result["ok"] = resume_result.get("resumed", False)
        result["supported"] = resume_result.get("supported", False)
    else:
        result["supported"] = False
        result["runtime_resume"] = {"resumed": False, "reason": "no session_id — packet-only resume"}

    if packet_id:
        from substrate.organism.work_packet_engine import WorkPacketEngine
        from substrate.organism.work_packet import PacketLifecycleStatus
        wpe = WorkPacketEngine()
        pkt = wpe.get_packet(packet_id)
        if pkt and pkt.status == PacketLifecycleStatus.PAUSED:
            ok = wpe.update_packet_status(packet_id, PacketLifecycleStatus.EXECUTING, reason)
            result["packet_status_updated"] = ok
            result["ok"] = result.get("ok", False) or ok
        elif pkt:
            result["packet_status_updated"] = False
            result["packet_status_reason"] = f"cannot resume from status '{pkt.status.value}'"
        else:
            result["packet_status_updated"] = False
            result["packet_status_reason"] = f"packet {packet_id} not found"

    return result


async def _execution_stop(request: Request) -> dict[str, Any]:
    body = await request.json()
    packet_id = body.get("packet_id", "")
    session_id = body.get("session_id", "")
    reason = body.get("reason", "operator requested stop")

    if not packet_id and not session_id:
        return {"ok": False, "error": "packet_id or session_id is required"}

    result: dict[str, Any] = {
        "ok": False,
        "packet_id": packet_id,
        "session_id": session_id,
        "environment": platform.system().lower(),
    }

    if session_id:
        _, adapter, err = _resolve_adapter(session_id)
        if err:
            result.update(err)
            return result

        stop_result = adapter.stop(session_id, reason=reason)
        result["runtime_stop"] = stop_result
        result["ok"] = stop_result.get("stopped", False)
    else:
        result["runtime_stop"] = {"stopped": False, "reason": "no session_id — packet-only stop"}

    if packet_id:
        from substrate.organism.work_packet_engine import WorkPacketEngine
        from substrate.organism.work_packet import PacketLifecycleStatus
        wpe = WorkPacketEngine()
        ok = wpe.update_packet_status(packet_id, PacketLifecycleStatus.BLOCKED, reason)
        result["packet_status_updated"] = ok
        result["ok"] = result.get("ok", False) or ok

    return result


async def _execution_status(request: Request) -> dict[str, Any]:
    session_id = request.query_params.get("session_id", "")
    if not session_id:
        return {"ok": False, "error": "session_id query param is required"}

    _, adapter, err = _resolve_adapter(session_id)
    if err:
        return err

    status_result = adapter.status(session_id)
    return {
        "ok": True,
        "session_id": session_id,
        "environment": platform.system().lower(),
        "status": status_result,
    }
