"""Cockpit workstation control routes — execution pause/resume/stop with environment awareness.

Mounted under /api/umh/ via include_router in cockpit.py.
Replaces execution_pause/execution_resume/execution_stop stubs from cockpit.py.

Phase 14.11A. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import platform
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request

from transports.api.governed import governed_mutation

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
        "/workstation/execution/pause", _execution_pause, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/workstation/execution/resume", _execution_resume, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/workstation/execution/stop", _execution_stop, methods=["POST"], dependencies=auth
    )
    r.add_api_route("/workstation/execution/status", _execution_status, methods=["GET"])
    r.add_api_route("/workstation/nodes", _workstation_nodes, methods=["GET"])
    r.add_api_route("/workstation/resume", _workstation_resume, methods=["GET"])
    r.add_api_route("/workstation/mode-composite", _mode_composite, methods=["GET"])
    r.add_api_route("/tmux/sessions", _tmux_sessions, methods=["GET"])
    r.add_api_route("/tmux/create", _tmux_create, methods=["POST"], dependencies=auth)
    r.add_api_route("/tmux/shells", _tmux_shells, methods=["GET"])
    r.add_api_route("/tmux/capture/{session_name}/{pane_id}", _tmux_capture, methods=["GET"])
    r.add_api_route(
        "/terminal/remote/create", _remote_terminal_create, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/terminal/remote/sessions", _remote_terminal_sessions, methods=["GET"], dependencies=auth
    )
    r.add_api_route(
        "/terminal/remote/shells", _remote_terminal_shells, methods=["GET"], dependencies=auth
    )
    r.add_api_route(
        "/terminal/remote/capture/{session_name}",
        _remote_terminal_capture,
        methods=["GET"],
        dependencies=auth,
    )
    r.add_api_route(
        "/terminal/remote/send", _remote_terminal_send, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/terminal/remote/send-key", _remote_terminal_send_key, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/terminal/remote/destroy", _remote_terminal_destroy, methods=["POST"], dependencies=auth
    )
    r.add_api_route("/workstation/continuity", _continuity_state, methods=["GET"])
    r.add_api_route(
        "/workstation/continuity/transition",
        _continuity_transition,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route("/workstation/checkpoint", _latest_checkpoint, methods=["GET"])
    r.add_api_route("/workstation/return-brief", _return_brief, methods=["GET"])
    r.add_api_route(
        "/workstation/return-brief/generate",
        _generate_return_brief,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route("/workstation/mode-switch", _mode_switch, methods=["POST"], dependencies=auth)
    r.add_api_route(
        "/workstation/profile-modes", _set_profile_modes, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/workstation/overnight/queue", _overnight_queue_work, methods=["POST"], dependencies=auth
    )
    r.add_api_route("/workstation/overnight/status", _overnight_status, methods=["GET"])
    r.add_api_route(
        "/workstation/overnight/approve", _overnight_approve, methods=["POST"], dependencies=auth
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
        return (
            mgr,
            None,
            {"ok": False, "error": f"no adapter for runtime_type={session.runtime_type}"},
        )

    return mgr, adapter, None


async def _execution_pause(request: Request) -> dict[str, Any]:
    body = await request.json()
    packet_id = body.get("packet_id", "")
    session_id = body.get("session_id", "")
    reason = body.get("reason", "operator requested pause")

    if not packet_id and not session_id:
        return {"ok": False, "error": "packet_id or session_id is required"}

    def _do_pause():
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
                return str(result), False

            pause_result = adapter.pause(session_id, reason=reason)
            result["runtime_pause"] = pause_result
            result["ok"] = pause_result.get("paused", False)
            result["supported"] = pause_result.get("supported", False)
        else:
            result["supported"] = False
            result["runtime_pause"] = {
                "paused": False,
                "reason": "no session_id — packet-only pause",
            }

        if packet_id:
            from substrate.organism.work_packet import PacketLifecycleStatus
            from substrate.organism.work_packet_engine import WorkPacketEngine

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

        return "paused", result.get("ok", False)

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"pause execution: packet={packet_id} session={session_id}",
        execute_fn=_do_pause,
        source="cockpit",
    )
    return resp.to_http_dict()


async def _execution_resume(request: Request) -> dict[str, Any]:
    body = await request.json()
    packet_id = body.get("packet_id", "")
    session_id = body.get("session_id", "")
    reason = body.get("reason", "operator requested resume")

    if not packet_id and not session_id:
        return {"ok": False, "error": "packet_id or session_id is required"}

    def _do_resume():
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
                return str(result), False

            resume_result = adapter.resume(session_id, reason=reason)
            result["runtime_resume"] = resume_result
            result["ok"] = resume_result.get("resumed", False)
            result["supported"] = resume_result.get("supported", False)
        else:
            result["supported"] = False
            result["runtime_resume"] = {
                "resumed": False,
                "reason": "no session_id — packet-only resume",
            }

        if packet_id:
            from substrate.organism.work_packet import PacketLifecycleStatus
            from substrate.organism.work_packet_engine import WorkPacketEngine

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

        return "resumed", result.get("ok", False)

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"resume execution: packet={packet_id} session={session_id}",
        execute_fn=_do_resume,
        source="cockpit",
    )
    return resp.to_http_dict()


async def _execution_stop(request: Request) -> dict[str, Any]:
    body = await request.json()
    packet_id = body.get("packet_id", "")
    session_id = body.get("session_id", "")
    reason = body.get("reason", "operator requested stop")

    if not packet_id and not session_id:
        return {"ok": False, "error": "packet_id or session_id is required"}

    def _do_stop():
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
                return str(result), False

            stop_result = adapter.stop(session_id, reason=reason)
            result["runtime_stop"] = stop_result
            result["ok"] = stop_result.get("stopped", False)
        else:
            result["runtime_stop"] = {
                "stopped": False,
                "reason": "no session_id — packet-only stop",
            }

        if packet_id:
            from substrate.organism.work_packet import PacketLifecycleStatus
            from substrate.organism.work_packet_engine import WorkPacketEngine

            wpe = WorkPacketEngine()
            ok = wpe.update_packet_status(packet_id, PacketLifecycleStatus.BLOCKED, reason)
            result["packet_status_updated"] = ok
            result["ok"] = result.get("ok", False) or ok

        return "stopped", result.get("ok", False)

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"stop execution: packet={packet_id} session={session_id}",
        execute_fn=_do_stop,
        source="cockpit",
    )
    return resp.to_http_dict()


def _execution_status(request: Request) -> dict[str, Any]:
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


# ── Remote terminal dispatch (mesh relay) ──────────────────────────────────

# Read-only terminal operations do not actuate the remote node and need no
# governance verdict. Every other operation is write-class: it spawns, writes
# to, keys, or destroys a remote session and MUST flow through a governed
# mutation carrying a verifiable verdict token.
_READ_ONLY_TERMINAL_OPS = frozenset({"list", "shells", "capture"})

# Map a terminal operation to the canonical governed mutation spec that
# authorizes it. `send`/`send_key` write into a live session (tmux_send);
# `create`/`destroy` actuate a remote process (remote_node_exec).
_TERMINAL_OP_MUTATION = {
    "create": "remote_node_exec",
    "destroy": "remote_node_exec",
    "send": "tmux_send",
    "send_key": "tmux_send",
}


async def _post_to_relay(payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    """POST a dispatch payload to the mesh relay with the relay bearer secret."""
    import aiohttp

    relay_host = os.environ.get("UMH_MESH_RELAY_HOST", "localhost")
    relay_url = f"http://{relay_host}:8095/dispatch"
    relay_secret = os.environ.get("UMH_MESH_RELAY_SECRET", "").strip()
    req_headers: dict[str, str] = {}
    if relay_secret:
        req_headers["Authorization"] = f"Bearer {relay_secret}"

    async with aiohttp.ClientSession() as session:
        async with session.post(
            relay_url,
            json=payload,
            headers=req_headers,
            timeout=aiohttp.ClientTimeout(total=timeout + 5),
        ) as resp:
            return await resp.json()


async def _remote_terminal_dispatch(
    node_id: str, operation: str, params: dict[str, Any], timeout: int = 15
) -> dict[str, Any]:
    """Dispatch a terminal operation to a remote mesh node.

    Read-only operations dispatch directly (no actuation). Write-class
    operations (create/send/send_key/destroy) route through a governed mutation
    that mints a signed verdict token bound to this node + capability; the token
    travels in the dispatch payload so the relay and the node can both validate
    it. The governed mutation also produces the trace event for the actuation.
    """
    capability = f"terminal.{operation}"

    # Read-only path: no verdict, no governance actuation record required.
    if operation in _READ_ONLY_TERMINAL_OPS:
        from uuid import uuid4

        from substrate.execution.mesh_verdict import READ_ONLY_EFFECT, canonical_payload_digest

        request_id = f"sync-{uuid4().hex}"
        payload_params = dict(params)
        payload = {
            "request_id": request_id,
            "correlation_id": f"cockpit-terminal:{operation}:{request_id}",
            "candidate_sha": os.environ.get("UMH_SOURCE_SHA", "").strip(),
            "effect_class": READ_ONLY_EFFECT,
            "idempotency_key": request_id,
            "payload_digest": canonical_payload_digest(payload_params),
            "node_id": node_id,
            "capability": capability,
            "params": payload_params,
            "risk_class": "read_only",
            "timeout": timeout,
        }
        try:
            result = await _post_to_relay(payload, timeout)
        except Exception as exc:
            logger.error("remote terminal dispatch failed: %s", exc)
            return {"ok": False, "error": f"Node unreachable: {exc}"}
        if not result.get("ok"):
            return {"ok": False, "error": result.get("error", "dispatch failed")}
        return {"ok": True, **result.get("result_data", {})}

    # Write-class path: fail closed; consequential remote actuation must enter
    # DurableRemote explicitly.
    return await _governed_remote_dispatch(node_id, operation, capability, params, timeout)


async def _governed_remote_dispatch(
    node_id: str,
    operation: str,
    capability: str,
    params: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    """Reject write-class remote actuation on the synchronous mesh path."""
    return {
        "ok": False,
        "status": "durable_remote_required",
        "error": "remote consequential operations must use DurableRemote, not sync mesh",
        "node_id": node_id,
        "operation": operation,
        "capability": capability,
    }


async def _remote_terminal_create(request: Request) -> dict[str, Any]:
    body = await request.json()
    node_id = body.get("node_id", "windows-desktop")
    name = body.get("name")
    shell = body.get("shell", "powershell")
    params: dict[str, Any] = {"shell": shell}
    if name:
        params["name"] = name
    return await _remote_terminal_dispatch(node_id, "create", params)


async def _remote_terminal_sessions(request: Request) -> dict[str, Any]:
    node_id = request.query_params.get("node_id", "windows-desktop")
    return await _remote_terminal_dispatch(node_id, "list", {})


async def _remote_terminal_shells(request: Request) -> dict[str, Any]:
    node_id = request.query_params.get("node_id", "windows-desktop")
    return await _remote_terminal_dispatch(node_id, "shells", {})


async def _remote_terminal_capture(request: Request, session_name: str) -> dict[str, Any]:
    node_id = request.query_params.get("node_id", "windows-desktop")
    lines = int(request.query_params.get("lines", "100"))
    return await _remote_terminal_dispatch(
        node_id, "capture", {"name": session_name, "lines": lines}
    )


async def _remote_terminal_send(request: Request) -> dict[str, Any]:
    body = await request.json()
    node_id = body.get("node_id", "windows-desktop")
    session_name = body.get("session_name", "")
    text = body.get("text", "")
    if not session_name or not text:
        return {"ok": False, "error": "session_name and text required"}
    return await _remote_terminal_dispatch(node_id, "send", {"name": session_name, "text": text})


async def _remote_terminal_send_key(request: Request) -> dict[str, Any]:
    body = await request.json()
    node_id = body.get("node_id", "windows-desktop")
    session_name = body.get("session_name", "")
    key = body.get("key", "")
    if not session_name or not key:
        return {"ok": False, "error": "session_name and key required"}
    return await _remote_terminal_dispatch(node_id, "send_key", {"name": session_name, "key": key})


async def _remote_terminal_destroy(request: Request) -> dict[str, Any]:
    body = await request.json()
    node_id = body.get("node_id", "windows-desktop")
    session_name = body.get("session_name", "")
    if not session_name:
        return {"ok": False, "error": "session_name required"}
    return await _remote_terminal_dispatch(node_id, "destroy", {"name": session_name})


# ── Cross-device node awareness ─────────────────────────────────────────────


def _read_mesh_snapshot() -> list[dict[str, Any]]:
    """Read the node mesh snapshot file for connected nodes."""
    import json
    import os

    path = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data",
        "runtime",
        "mesh_nodes.json",
    )
    if not os.path.exists(path):
        return []
    try:
        return json.loads(open(path, encoding="utf-8").read())
    except (json.JSONDecodeError, OSError):
        return []


def _read_vps_node() -> dict[str, Any]:
    """Build VPS node info from local system."""

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


def _workstation_nodes(request: Request) -> dict[str, Any]:
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


def _workstation_resume(request: Request) -> dict[str, Any]:
    import json
    import os

    resume_path = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data",
        "runtime",
        "workstation",
        "resume_state.json",
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


def _mode_composite(request: Request) -> dict[str, Any]:
    from substrate.workstation.mode_resolver import resolve_composite_mode

    mode = resolve_composite_mode()
    return {
        "ok": True,
        "mode_composite": mode,
    }


# ── Tmux visibility ─────────────────────────────────────────────────────────


def _tmux_sessions(request: Request) -> dict[str, Any]:
    # NEVER-500 read surface: adapter construction/execution raises when tmux
    # is absent from the runtime (the Wave-1 candidate container 500'd on
    # every poll — field run 20260722T181248Z network evidence). A status
    # read degrades to an empty, explicit "unavailable" — it never raises.
    try:
        from adapters.tool_adapters.tmux import TmuxAdapter

        adapter = TmuxAdapter()
        result = adapter._execute_impl("list_sessions", {})
    except Exception as exc:  # noqa: BLE001 — read surface fails soft
        logger.debug("tmux sessions read unavailable: %s", exc)
        return {"ok": False, "error": str(exc)[:200], "sessions": []}
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
            sessions.append(
                {
                    "name": parts[0],
                    "windows": int(parts[1]) if parts[1].isdigit() else 0,
                    "attached": parts[2] == "1",
                }
            )

    return {"ok": True, "sessions": sessions, "count": len(sessions)}


async def _tmux_create(request: Request) -> dict[str, Any]:
    body = await request.json()
    name = body.get("name", "")
    shell = body.get("shell", "bash")
    if not name:
        return {"ok": False, "error": "name required"}

    def _do_create():
        from adapters.tool_adapters.tmux import TmuxAdapter

        adapter = TmuxAdapter()
        result = adapter._execute_impl("new_session", {"name": name, "shell": shell})
        if not result.get("success"):
            return result.get("stderr", "failed to create session"), False
        return f"created tmux session {name}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"create tmux session: {name} (shell={shell})",
        execute_fn=_do_create,
        source="cockpit",
    )
    return resp.to_http_dict()


def _tmux_shells(request: Request) -> dict[str, Any]:
    """Full terminal capability report for the VPS node."""
    import shutil

    shells = []
    for shell_id, label, check in [
        ("bash", "Bash", lambda: shutil.which("bash") is not None),
        ("zsh", "Zsh", lambda: shutil.which("zsh") is not None),
        ("sh", "sh", lambda: shutil.which("sh") is not None),
        ("python", "Python REPL", lambda: shutil.which("python3") is not None),
    ]:
        try:
            if check():
                shells.append({"id": shell_id, "label": label, "os": "linux"})
        except Exception:
            pass

    multiplexers = []
    for mux_id, label, check in [
        ("tmux", "tmux", lambda: shutil.which("tmux") is not None),
        ("screen", "GNU Screen", lambda: shutil.which("screen") is not None),
    ]:
        try:
            if check():
                multiplexers.append({"id": mux_id, "label": label, "via": "native"})
        except Exception:
            pass

    return {
        "ok": True,
        "shells": shells,
        "multiplexers": multiplexers,
        "platform": "linux",
    }


def _tmux_capture(request: Request, session_name: str, pane_id: str) -> dict[str, Any]:
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


# ── Continuity state ──────────────────────────────────────────────────────


_continuity_machine = None


def _get_continuity_machine():
    global _continuity_machine
    if _continuity_machine is None:
        import json
        import os

        from substrate.workstation.continuity import ContinuityStateMachine

        path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data",
            "umh",
            "workstation_state",
            "continuity.json",
        )
        if os.path.exists(path):
            try:
                data = json.loads(open(path, encoding="utf-8").read())
                _continuity_machine = ContinuityStateMachine.from_dict(data)
            except (json.JSONDecodeError, ValueError):
                _continuity_machine = ContinuityStateMachine()
        else:
            _continuity_machine = ContinuityStateMachine()
    return _continuity_machine


def _persist_continuity():
    import json
    import os

    machine = _get_continuity_machine()
    path = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data",
        "umh",
        "workstation_state",
        "continuity.json",
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(machine.to_dict(), f, indent=2, default=str)


def _continuity_state(request: Request) -> dict[str, Any]:
    machine = _get_continuity_machine()
    return {
        "ok": True,
        "current_state": machine.current_state.value,
        "valid_transitions": [s.value for s in machine.valid_transitions()],
        "last_transition": machine.last_transition().to_dict()
        if machine.last_transition()
        else None,
    }


async def _continuity_transition(request: Request) -> dict[str, Any]:
    body = await request.json()
    target_str = body.get("target_state", "")
    reason = body.get("reason", "")

    from substrate.workstation.continuity import ContinuityState

    try:
        target = ContinuityState(target_str)
    except ValueError:
        valid = [s.value for s in ContinuityState]
        return {"ok": False, "error": f"Invalid state: {target_str}. Valid: {valid}"}

    machine = _get_continuity_machine()

    if not machine.can_transition(target):
        return {
            "ok": False,
            "error": f"Cannot transition from {machine.current_state.value} to {target_str}",
            "valid_transitions": [s.value for s in machine.valid_transitions()],
        }

    def _do_transition():
        prev = machine.current_state.value
        machine.transition(
            target,
            reason=reason,
            active_node=body.get("active_node", platform.node()),
            active_environment=body.get("active_environment", platform.system().lower()),
            active_work_packet_id=body.get("active_work_packet_id", ""),
            active_session_id=body.get("active_session_id", ""),
            pending_approvals_count=body.get("pending_approvals_count", 0),
            safe_work_constraints=body.get("safe_work_constraints", {}),
        )
        _persist_continuity()

        from substrate.workstation.checkpoint import CheckpointManager
        from substrate.workstation.mode_resolver import resolve_composite_mode

        mode = resolve_composite_mode(continuity_state=target_str)
        mgr = CheckpointManager()
        mgr.create_checkpoint(
            previous_state=prev,
            new_state=target_str,
            lifecycle_mode=mode.get("lifecycle_mode", ""),
            active_profile_modes=mode.get("active_profile_modes", []),
            risk_ceiling=mode.get("risk_ceiling", ""),
            active_node=body.get("active_node", platform.node()),
            active_environment=body.get("active_environment", platform.system().lower()),
            transition_reason=reason,
        )
        return f"transitioned {prev} → {target_str}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"continuity transition to {target_str}: {reason[:100]}",
        execute_fn=_do_transition,
        source="cockpit",
    )
    return resp.to_http_dict()


# ── Checkpoint ─────────────────────────────────────────────────────────────


def _latest_checkpoint(request: Request) -> dict[str, Any]:
    from substrate.workstation.checkpoint import CheckpointManager

    mgr = CheckpointManager()
    cp = mgr.latest()
    if not cp:
        return {"ok": True, "checkpoint": None, "has_checkpoint": False}
    return {"ok": True, "checkpoint": cp.to_dict(), "has_checkpoint": True}


# ── Return brief ───────────────────────────────────────────────────────────


def _return_brief(request: Request) -> dict[str, Any]:
    from substrate.workstation.resume_brief import ReturnBriefGenerator

    gen = ReturnBriefGenerator()
    brief = gen.latest()
    if not brief:
        return {"ok": True, "brief": None, "has_brief": False}
    return {"ok": True, "brief": brief.to_dict(), "has_brief": True}


async def _generate_return_brief(request: Request) -> dict[str, Any]:
    body = await request.json()

    def _do_generate():
        from substrate.workstation.mode_resolver import resolve_composite_mode
        from substrate.workstation.resume_brief import ReturnBriefGenerator

        mode = resolve_composite_mode()
        gen = ReturnBriefGenerator()
        gen.generate(
            departure_state=body.get("departure_state", ""),
            current_state=body.get("current_state", mode.get("continuity_state", "active")),
            lifecycle_mode=mode.get("lifecycle_mode", "day_cycle"),
            active_profile_modes=mode.get("active_profile_modes", ["developer"]),
            active_node=body.get("active_node", platform.node()),
            active_environment=platform.system().lower(),
        )
        return "return brief generated", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent="generate return brief",
        execute_fn=_do_generate,
        source="cockpit",
    )
    return resp.to_http_dict()


# ── Mode switching ─────────────────────────────────────────────────────────


async def _mode_switch(request: Request) -> dict[str, Any]:
    body = await request.json()
    text = body.get("command", "")
    if not text:
        return {"ok": False, "error": "No command text provided"}

    from substrate.workstation.mode_commands import parse_mode_command

    result = parse_mode_command(text)

    if not result.recognized:
        return {
            "ok": False,
            "error": "Command not recognized as a mode switch",
            "raw_input": text,
        }

    def _do_mode_switch():
        if result.command_type == "continuity":
            from substrate.workstation.continuity import ContinuityState

            try:
                target = ContinuityState(result.target_value)
            except ValueError:
                return f"Invalid continuity state: {result.target_value}", False

            machine = _get_continuity_machine()
            if not machine.can_transition(target):
                return (
                    f"Cannot transition to {result.target_value} from {machine.current_state.value}",
                    False,
                )

            prev = machine.current_state.value
            machine.transition(target, reason=f"mode command: {text}")
            _persist_continuity()

            from substrate.workstation.checkpoint import CheckpointManager
            from substrate.workstation.mode_resolver import resolve_composite_mode

            mode = resolve_composite_mode(continuity_state=result.target_value)
            mgr = CheckpointManager()
            mgr.create_checkpoint(
                previous_state=prev,
                new_state=result.target_value,
                lifecycle_mode=mode.get("lifecycle_mode", ""),
                transition_reason=f"mode command: {text}",
            )
            return f"mode switch: {prev} → {result.target_value}", True

        return f"mode command applied: {result.command_type}={result.target_value}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"mode switch: {text[:100]}",
        execute_fn=_do_mode_switch,
        source="cockpit",
    )
    return resp.to_http_dict()


async def _set_profile_modes(request: Request) -> dict[str, Any]:
    body = await request.json()
    modes = body.get("modes", [])
    if not modes:
        return {"ok": False, "error": "No modes provided"}

    from substrate.workstation.profile_modes import ProfileMode

    valid_values = {m.value for m in ProfileMode}
    invalid = [m for m in modes if m not in valid_values]
    if invalid:
        return {
            "ok": False,
            "error": f"Invalid profile modes: {invalid}",
            "valid": sorted(valid_values),
        }

    def _do_set_modes():
        import json as _json

        path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data",
            "umh",
            "workstation_state",
            "profile_modes.json",
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            _json.dump(
                {"active_modes": modes, "updated_at": datetime.now(timezone.utc).isoformat()},
                f,
                indent=2,
            )
        return f"profile modes set: {modes}", True

    resp = governed_mutation(
        mutation_name="settings_update",
        intent=f"set profile modes: {modes}",
        execute_fn=_do_set_modes,
        source="cockpit",
    )
    return resp.to_http_dict()


# ── Overnight queue ────────────────────────────────────────────────────────


async def _overnight_queue_work(request: Request) -> dict[str, Any]:
    body = await request.json()

    def _do_queue():
        from substrate.workstation.overnight_queue import OvernightQueue

        queue = OvernightQueue()
        queue.queue_work(
            work_packet_id=body.get("work_packet_id", ""),
            title=body.get("title", ""),
            risk_level=body.get("risk_level", "LOW"),
            reason=body.get("reason", ""),
        )
        return f"queued overnight work: {body.get('title', '')}", True

    resp = governed_mutation(
        mutation_name="work_packet_create",
        intent=f"queue overnight work: {body.get('title', '')[:100]}",
        execute_fn=_do_queue,
        source="cockpit",
    )
    return resp.to_http_dict()


def _overnight_status(request: Request) -> dict[str, Any]:
    from substrate.workstation.overnight_queue import OvernightQueue

    queue = OvernightQueue()
    return {"ok": True, "summary": queue.morning_summary()}


async def _overnight_approve(request: Request) -> dict[str, Any]:
    body = await request.json()
    item_id = body.get("item_id", "")
    if not item_id:
        return {"ok": False, "error": "No item_id provided"}

    def _do_approve():
        from substrate.workstation.overnight_queue import OvernightQueue

        queue = OvernightQueue()
        item = queue.approve(item_id)
        if not item:
            return f"Item {item_id} not found", False
        return f"approved overnight item {item_id}", True

    resp = governed_mutation(
        mutation_name="approval_decide",
        intent=f"approve overnight work item {item_id}",
        execute_fn=_do_approve,
        source="cockpit",
    )
    return resp.to_http_dict()
