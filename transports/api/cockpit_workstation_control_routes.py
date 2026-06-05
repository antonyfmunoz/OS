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
    r.add_api_route(
        "/workstation/nodes",
        _workstation_nodes,
        methods=["GET"],
        dependencies=auth,
    )
    r.add_api_route(
        "/workstation/resume",
        _workstation_resume,
        methods=["GET"],
        dependencies=auth,
    )
    r.add_api_route(
        "/workstation/mode-composite",
        _mode_composite,
        methods=["GET"],
        dependencies=auth,
    )
    r.add_api_route(
        "/tmux/sessions",
        _tmux_sessions,
        methods=["GET"],
        dependencies=auth,
    )
    r.add_api_route(
        "/tmux/capture/{session_name}/{pane_id}",
        _tmux_capture,
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


# ── Cross-device node awareness ─────────────────────────────────────────────


def _read_mesh_snapshot() -> list[dict[str, Any]]:
    """Read the node mesh snapshot file for connected nodes."""
    import json
    import os
    path = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data", "runtime", "mesh_nodes.json",
    )
    if not os.path.exists(path):
        return []
    try:
        return json.loads(open(path, encoding="utf-8").read())
    except (json.JSONDecodeError, OSError):
        return []


def _read_vps_node() -> dict[str, Any]:
    """Build VPS node info from local system."""
    import os
    hostname = platform.node()
    return {
        "id": f"vps-{hostname}",
        "name": hostname,
        "os": platform.system().lower(),
        "os_version": platform.release(),
        "status": "connected",
        "role": "orchestrator",
        "environment": platform.system().lower(),
    }


async def _workstation_nodes(request: Request) -> dict[str, Any]:
    vps = _read_vps_node()
    mesh_nodes = _read_mesh_snapshot()

    all_nodes = [vps] + mesh_nodes
    return {
        "ok": True,
        "nodes": all_nodes,
        "count": len(all_nodes),
        "vps": vps,
        "remote_nodes": mesh_nodes,
    }


# ── Cross-device resume ─────────────────────────────────────────────────────


async def _workstation_resume(request: Request) -> dict[str, Any]:
    import json
    import os
    resume_path = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data", "runtime", "workstation", "resume_state.json",
    )

    resume_data: dict[str, Any] = {}
    if os.path.exists(resume_path):
        try:
            resume_data = json.loads(open(resume_path, encoding="utf-8").read())
        except (json.JSONDecodeError, OSError):
            resume_data = {}

    from substrate.workstation.mode_resolver import resolve_composite_mode
    mode = resolve_composite_mode()

    return {
        "ok": True,
        "resume_state": resume_data,
        "has_resume": bool(resume_data),
        "mode_composite": mode,
        "environment": platform.system().lower(),
    }


# ── Mode composite ───────────────────────────────────────────────────────────


async def _mode_composite(request: Request) -> dict[str, Any]:
    from substrate.workstation.mode_resolver import resolve_composite_mode
    mode = resolve_composite_mode()
    return {
        "ok": True,
        "mode_composite": mode,
    }


# ── Tmux visibility ─────────────────────────────────────────────────────────


async def _tmux_sessions(request: Request) -> dict[str, Any]:
    from adapters.tool_adapters.tmux import TmuxAdapter
    adapter = TmuxAdapter()
    result = adapter._execute_impl("list_sessions", {})
    if not result.get("success"):
        return {
            "ok": False,
            "error": result.get("stderr", "tmux not available"),
            "sessions": [],
        }

    sessions: list[dict[str, Any]] = []
    for line in result.get("stdout", "").strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(":")
        if len(parts) >= 3:
            sessions.append({
                "name": parts[0],
                "windows": int(parts[1]) if parts[1].isdigit() else 0,
                "attached": parts[2] == "1",
            })

    return {"ok": True, "sessions": sessions, "count": len(sessions)}


async def _tmux_capture(request: Request, session_name: str, pane_id: str) -> dict[str, Any]:
    from adapters.tool_adapters.tmux import TmuxAdapter
    adapter = TmuxAdapter()
    target = f"{session_name}:{pane_id}"
    result = adapter._execute_impl("capture_pane", {"target": target})
    if not result.get("success"):
        return {
            "ok": False,
            "error": result.get("stderr", "capture failed"),
            "target": target,
            "output": "",
        }

    return {
        "ok": True,
        "target": target,
        "output": result.get("stdout", ""),
    }
