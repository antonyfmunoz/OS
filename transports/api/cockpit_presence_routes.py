"""Cockpit presence routes — activation, session, command, capabilities.

Phase 14.11D. Provides the API surface for Jarvis presence activation
and natural language command routing. All routes are read-safe or
governance-gated for executable commands.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

_UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_DATA_ROOT = os.path.join(_UMH_ROOT, "data", "umh")
_PRESENCE_LOG = os.path.join(_DATA_ROOT, "workstation_state", "presence_events.jsonl")

presence_router = APIRouter(tags=["presence"])
_require_operator: Callable | None = None


def configure(require_operator_dep: Callable) -> None:
    global _require_operator
    _require_operator = require_operator_dep


def _get_dep():
    if _require_operator:
        return Depends(_require_operator)
    return None


def _detect_env() -> str:
    import platform
    system = platform.system().lower()
    if os.path.exists("/.dockerenv"):
        return "container"
    if system == "linux":
        return "vps"
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    return "unknown"


def _load_continuity_state() -> dict[str, Any]:
    checkpoint_path = os.path.join(_DATA_ROOT, "workstation_state", "latest_checkpoint.json")
    if os.path.exists(checkpoint_path):
        try:
            with open(checkpoint_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"continuity_state": "active", "lifecycle_mode": "default"}


def _load_resume_summary() -> dict[str, Any]:
    snapshot_path = os.path.join(_DATA_ROOT, "workstation_state", "current_snapshot.json")
    if os.path.exists(snapshot_path):
        try:
            with open(snapshot_path) as f:
                data = json.load(f)
            return data.get("resume", {})
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _load_pending_approvals() -> list[dict[str, Any]]:
    approval_path = os.path.join(_DATA_ROOT, "organism", "execution_journal.jsonl")
    approvals: list[dict[str, Any]] = []
    if os.path.exists(approval_path):
        try:
            with open(approval_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("status") in ("pending_approval", "needs_approval"):
                            approvals.append({
                                "id": entry.get("id", ""),
                                "description": entry.get("description", entry.get("input_signal_preview", "")),
                                "status": entry.get("status", ""),
                                "risk_class": entry.get("risk_class", ""),
                            })
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
    return approvals[-10:]


def _log_presence_event(event: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_PRESENCE_LOG), exist_ok=True)
    try:
        with open(_PRESENCE_LOG, "a") as f:
            f.write(json.dumps(event, separators=(",", ":")) + "\n")
    except OSError:
        logger.debug("Failed to write presence event")


@presence_router.post("/presence/activate")
async def _activate(request: Request) -> dict[str, Any]:
    from substrate.workstation.activation import (
        ActivationSignal,
        ActivationSource,
        PresenceSession,
        get_activation_capabilities,
    )
    from substrate.workstation.state import WorkstationProfile

    body: dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        pass

    source = body.get("source", ActivationSource.MANUAL_COCKPIT_OPEN.value)
    raw_payload = body.get("raw_payload", "")

    profile = WorkstationProfile.detect(
        user_id=body.get("user_id", ""),
        session_id=body.get("session_id", ""),
    )

    checkpoint = _load_continuity_state()
    continuity = checkpoint.get("continuity_state", checkpoint.get("new_continuity_state", "active"))
    lifecycle = checkpoint.get("lifecycle_mode", "default")
    profile_modes = checkpoint.get("active_profile_modes", [])

    resume = _load_resume_summary()
    approvals = _load_pending_approvals()
    caps = get_activation_capabilities()

    signal = ActivationSignal(
        source=source,
        user_id=profile.user_id,
        session_id=profile.session_id,
        lifecycle_mode=lifecycle,
        profile_mode=",".join(profile_modes) if isinstance(profile_modes, list) else str(profile_modes),
        continuity_state=continuity,
        raw_payload=raw_payload,
    )

    session = PresenceSession(
        activation=signal,
        profile=profile.to_dict(),
        continuity_state=continuity,
        lifecycle_mode=lifecycle,
        profile_modes=profile_modes if isinstance(profile_modes, list) else [],
        pending_approvals=approvals,
        resume_summary=resume.get("resume_summary", ""),
        next_actions=resume.get("next_suggested_actions", []),
        active_node=signal.node,
        active_environment=_detect_env(),
        capabilities=[c.to_dict() for c in caps],
    )

    session_dict = session.to_dict()

    def _do_activate():
        _log_presence_event({
            "event": "activation",
            "activation_id": signal.activation_id,
            "source": source,
            "session_id": session.session_id,
            "continuity_state": continuity,
            "timestamp": signal.timestamp,
        })
        return f"presence activated: {session.session_id}", True

    resp = governed_mutation(
        mutation_name="presence_update",
        intent=f"activate presence session from {source}",
        execute_fn=_do_activate,
        source="cockpit",
        metadata={"session_id": session.session_id, "source": source},
    )
    result = resp.to_http_dict()
    result["session"] = session_dict
    return result


@presence_router.get("/presence/current")
def _current(request: Request) -> dict[str, Any]:
    from substrate.workstation.activation import get_activation_capabilities
    from substrate.workstation.state import WorkstationProfile

    profile = WorkstationProfile.detect()
    checkpoint = _load_continuity_state()
    continuity = checkpoint.get("continuity_state", checkpoint.get("new_continuity_state", "active"))
    lifecycle = checkpoint.get("lifecycle_mode", "default")
    profile_modes = checkpoint.get("active_profile_modes", [])
    resume = _load_resume_summary()
    approvals = _load_pending_approvals()
    caps = get_activation_capabilities()

    return {
        "ok": True,
        "profile": profile.to_dict(),
        "continuity_state": continuity,
        "lifecycle_mode": lifecycle,
        "profile_modes": profile_modes if isinstance(profile_modes, list) else [],
        "pending_approvals": approvals,
        "resume_summary": resume.get("resume_summary", ""),
        "next_actions": resume.get("next_suggested_actions", []),
        "active_node": os.uname().nodename,
        "active_environment": _detect_env(),
        "capabilities": [c.to_dict() for c in caps],
        "source_env": _detect_env(),
    }


@presence_router.post("/presence/command")
async def _command(request: Request) -> dict[str, Any]:
    from substrate.workstation.command_router import (
        CommandIntent,
        GovernanceRequirement,
        classify_intent,
        governance_requirement,
        resolve_mode_target,
        resolve_navigation_target,
    )

    body: dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        return {"ok": False, "error": "Invalid request body"}

    text = body.get("text", "").strip()
    source = body.get("source", "typed_command")
    if not text:
        return {"ok": False, "error": "Empty command text"}

    intent = classify_intent(text)
    gov = governance_requirement(intent)

    result: dict[str, Any] = {
        "ok": True,
        "command_id": f"jcmd_{uuid.uuid4().hex[:12]}",
        "intent": intent.value,
        "raw_text": text,
        "governance": gov.value,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if intent == CommandIntent.STATUS_QUERY:
        checkpoint = _load_continuity_state()
        resume = _load_resume_summary()
        result["response_text"] = _build_status_response(checkpoint, resume)
        result["data"] = {"checkpoint": checkpoint, "resume": resume}

    elif intent == CommandIntent.RESUME_QUERY:
        resume = _load_resume_summary()
        checkpoint = _load_continuity_state()
        approvals = _load_pending_approvals()
        result["response_text"] = _build_resume_response(resume, approvals)
        result["data"] = {"resume": resume, "approvals": approvals, "checkpoint": checkpoint}

    elif intent == CommandIntent.APPROVAL_QUERY:
        approvals = _load_pending_approvals()
        result["response_text"] = _build_approval_response(approvals)
        result["data"] = {"approvals": approvals}
        result["panel_target"] = "approvals"

    elif intent == CommandIntent.MODE_SWITCH:
        target = resolve_mode_target(text)
        result["mode_target"] = target
        result["response_text"] = f"Mode target: {target}" if target else "Could not determine target mode."

    elif intent == CommandIntent.COCKPIT_NAVIGATION:
        panel = resolve_navigation_target(text)
        result["panel_target"] = panel
        result["response_text"] = f"Navigating to {panel}." if panel else "Panel not found."

    elif intent == CommandIntent.WORK_PACKET_DRAFT:
        result["response_text"] = "Work packet draft requires governance approval."
        result["governance"] = GovernanceRequirement.REQUIRES_GOVERNANCE.value
        result["data"] = {"draft_text": text, "status": "pending_governance"}
        result["panel_target"] = "commandcenter"

    elif intent == CommandIntent.AGENT_QUERY:
        agents_data = _load_agent_summary()
        result["response_text"] = _build_agent_response(agents_data)
        result["data"] = agents_data
        result["panel_target"] = "agents"

    elif intent == CommandIntent.BLOCKED_QUERY:
        blocked_data = _load_blocked_summary()
        result["response_text"] = _build_blocked_response(blocked_data)
        result["data"] = blocked_data

    elif intent == CommandIntent.PACKET_CONTROL:
        from substrate.workstation.command_router import resolve_packet_control_action
        action = resolve_packet_control_action(text)
        result["response_text"] = f"Packet {action} requires governance approval."
        result["governance"] = GovernanceRequirement.REQUIRES_GOVERNANCE.value
        result["data"] = {"action": action, "raw_text": text, "status": "pending_governance"}

    elif intent == CommandIntent.COMMAND_CENTER_QUERY:
        summary_data = _load_command_center_summary()
        result["response_text"] = _build_command_center_response(summary_data)
        result["data"] = summary_data
        result["panel_target"] = "commandcenter"

    else:
        result["response_text"] = "Command not recognized. Try: status, agents, blocked, approvals, mode switch, or navigation."

    def _do_command():
        _log_presence_event({
            "event": "command",
            "command_id": result["command_id"],
            "intent": intent.value,
            "governance": gov.value,
            "source": source,
            "text": text,
            "timestamp": result["timestamp"],
        })
        return f"command processed: {intent.value}", True

    gm_resp = governed_mutation(
        mutation_name="presence_update",
        intent=f"presence command: {intent.value}",
        execute_fn=_do_command,
        source="cockpit",
        metadata={"command_id": result["command_id"], "intent": intent.value},
    )
    if not gm_resp.success:
        return {"ok": False, "error": gm_resp.output}
    return result


@presence_router.get("/presence/capabilities")
def _capabilities(request: Request) -> dict[str, Any]:
    from substrate.workstation.activation import get_activation_capabilities

    caps = get_activation_capabilities()
    available = [c for c in caps if c.status == "available"]
    degraded = [c for c in caps if c.status == "degraded"]
    unavailable = [c for c in caps if c.status in ("unavailable", "not_implemented")]

    return {
        "ok": True,
        "capabilities": [c.to_dict() for c in caps],
        "summary": {
            "available": len(available),
            "degraded": len(degraded),
            "unavailable": len(unavailable),
            "total": len(caps),
        },
        "stt_available": any(
            c.source == "push_to_talk_voice" and c.status in ("available", "degraded")
            for c in caps
        ),
        "tts_available": _check_tts_available(),
        "source_env": _detect_env(),
    }


@presence_router.get("/voice/health")
def _voice_health() -> dict[str, Any]:
    """Voice subsystem health — STT/TTS provider status."""
    stt_provider = os.environ.get("UMH_STT_PROVIDER", "browser_native")
    tts_provider = os.environ.get("UMH_TTS_PROVIDER", "kokoro")
    tts_host = os.environ.get("KOKORO_TTS_HOST", "")
    kokoro_url = os.environ.get("KOKORO_TTS_URL", "")
    ws_port = os.environ.get("UMH_VOICE_WS_PORT", "8096")

    tts_reachable = _check_tts_available()

    stt_status = "available" if stt_provider == "browser_native" else "configured"
    tts_status = "available" if tts_reachable else "unreachable"

    voice_ws_reachable = _check_voice_ws_reachable(int(ws_port))

    return {
        "ok": voice_ws_reachable,
        "voice_server": "reachable" if voice_ws_reachable else "unreachable",
        "local_ws": f"ws://127.0.0.1:{ws_port}/voice",
        "public_ws": "/api/umh/voice/ws",
        "deployed_browser_supported": True,
        "tap_to_toggle_supported": True,
        "tts_cancel_supported": True,
        "stt": {
            "provider": stt_provider,
            "status": stt_status,
        },
        "tts": {
            "provider": tts_provider,
            "status": tts_status,
            "host": tts_host or kokoro_url,
            "reachable": tts_reachable,
        },
        "note": "Browser mic availability is client-side only — server cannot verify",
        "source_env": _detect_env(),
    }


def _check_voice_ws_reachable(port: int) -> bool:
    """Check if the voice WebSocket server is listening."""
    import socket
    upstream = os.environ.get("VOICE_WS_UPSTREAM", "")
    if "host.docker.internal" in upstream:
        host = "host.docker.internal"
    else:
        host = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def _check_tts_available() -> bool:
    """Check if Kokoro TTS on Beast is reachable."""
    try:
        import urllib.request
        kokoro_url = os.environ.get("KOKORO_TTS_URL", "")
        req = urllib.request.Request(f"{kokoro_url}/health", method="GET")
        req.add_header("Connection", "close")
        urllib.request.urlopen(req, timeout=2)
        return True
    except Exception:
        return False


def _build_status_response(checkpoint: dict[str, Any], resume: dict[str, Any]) -> str:
    parts: list[str] = []
    state = checkpoint.get("continuity_state", checkpoint.get("new_continuity_state", "active"))
    parts.append(f"Continuity: {state}.")
    mode = checkpoint.get("lifecycle_mode", "default")
    if mode and mode != "default":
        parts.append(f"Lifecycle: {mode}.")
    summary = resume.get("resume_summary", "")
    if summary:
        parts.append(summary)
    return " ".join(parts) if parts else "System is active. No recent activity."


def _build_resume_response(resume: dict[str, Any], approvals: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    summary = resume.get("resume_summary", "")
    if summary:
        parts.append(summary)
    else:
        parts.append("No activity since last session.")

    actions = resume.get("next_suggested_actions", [])
    if actions:
        parts.append(f"Suggested: {'; '.join(actions)}.")

    if approvals:
        parts.append(f"{len(approvals)} item(s) pending approval.")

    return " ".join(parts)


def _build_approval_response(approvals: list[dict[str, Any]]) -> str:
    if not approvals:
        return "No pending approvals."
    descriptions = [a.get("description", a.get("id", "unknown")) for a in approvals[:5]]
    return f"{len(approvals)} pending: {'; '.join(descriptions)}."


def _load_agent_summary() -> dict[str, Any]:
    """Load workcell heartbeats as agent summary."""
    workcell_dir = os.path.join(_DATA_ROOT, "organism", "workcells")
    agents: list[dict[str, Any]] = []
    if os.path.isdir(workcell_dir):
        for entry in sorted(os.listdir(workcell_dir)):
            hb_path = os.path.join(workcell_dir, entry, "heartbeat.json")
            if os.path.exists(hb_path):
                try:
                    with open(hb_path) as f:
                        data = json.load(f)
                    agents.append({
                        "agent_id": data.get("workcell_id", entry),
                        "role": data.get("role", "unknown"),
                        "status": data.get("status", "unknown"),
                        "messages": data.get("messages_processed", 0),
                        "inbox": data.get("inbox_depth", 0),
                    })
                except (json.JSONDecodeError, OSError):
                    agents.append({"agent_id": entry, "role": "unknown", "status": "unavailable"})
    return {
        "agents": agents,
        "total": len(agents),
        "active": sum(1 for a in agents if a["status"] == "active"),
        "idle": sum(1 for a in agents if a["status"] == "idle"),
    }


def _build_agent_response(data: dict[str, Any]) -> str:
    agents = data.get("agents", [])
    if not agents:
        return "No agents registered."
    lines = [f"{len(agents)} agents: {data.get('active', 0)} active, {data.get('idle', 0)} idle."]
    for a in agents[:5]:
        lines.append(f"  {a['role']}: {a['status']}")
    return " ".join(lines)


def _load_blocked_summary() -> dict[str, Any]:
    """Load blocked work packets."""
    wp_path = os.path.join(_DATA_ROOT, "universal_work", "work_packets.jsonl")
    blocked: list[dict[str, Any]] = []
    if os.path.exists(wp_path):
        try:
            with open(wp_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        pkt = json.loads(line)
                        if pkt.get("status") == "blocked" or pkt.get("blockers"):
                            blocked.append({
                                "id": pkt.get("packet_id", ""),
                                "title": pkt.get("title", ""),
                                "blockers": pkt.get("blockers", []),
                                "status": pkt.get("status", ""),
                            })
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
    return {"blocked": blocked, "count": len(blocked)}


def _build_blocked_response(data: dict[str, Any]) -> str:
    blocked = data.get("blocked", [])
    if not blocked:
        return "Nothing is blocked."
    lines = [f"{len(blocked)} blocked item(s):"]
    for b in blocked[:5]:
        blockers = ", ".join(b.get("blockers", [])) or "unknown blocker"
        lines.append(f"  {b.get('title', b.get('id', 'unknown'))}: {blockers}")
    return " ".join(lines)


def _load_command_center_summary() -> dict[str, Any]:
    """Load full command center summary."""
    agents = _load_agent_summary()
    blocked = _load_blocked_summary()
    approvals = _load_pending_approvals()
    checkpoint = _load_continuity_state()
    resume = _load_resume_summary()
    return {
        "agents": agents,
        "blocked": blocked,
        "approvals": approvals,
        "continuity_state": checkpoint.get("continuity_state", "active"),
        "lifecycle_mode": checkpoint.get("lifecycle_mode", "default"),
        "resume_summary": resume.get("resume_summary", ""),
        "next_actions": resume.get("next_suggested_actions", []),
    }


def _build_command_center_response(data: dict[str, Any]) -> str:
    parts: list[str] = []
    agents = data.get("agents", {})
    parts.append(f"Agents: {agents.get('active', 0)} active, {agents.get('idle', 0)} idle of {agents.get('total', 0)}.")
    blocked = data.get("blocked", {})
    if blocked.get("count", 0):
        parts.append(f"Blocked: {blocked['count']} item(s).")
    else:
        parts.append("Nothing blocked.")
    approvals = data.get("approvals", [])
    if approvals:
        parts.append(f"Approvals: {len(approvals)} pending.")
    else:
        parts.append("No pending approvals.")
    state = data.get("continuity_state", "active")
    parts.append(f"Continuity: {state}.")
    summary = data.get("resume_summary", "")
    if summary:
        parts.append(summary)
    return " ".join(parts)
