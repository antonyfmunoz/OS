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

logger = logging.getLogger(__name__)

_UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_DATA_ROOT = os.path.join(_UMH_ROOT, "data", "umh")
_PRESENCE_LOG = os.path.join(_DATA_ROOT, "workstation_state", "presence_events.jsonl")

presence_router = APIRouter(prefix="/api/umh", tags=["presence"])
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

    _log_presence_event({
        "event": "activation",
        "activation_id": signal.activation_id,
        "source": source,
        "session_id": session.session_id,
        "continuity_state": continuity,
        "timestamp": signal.timestamp,
    })

    return {"ok": True, "session": session.to_dict()}


@presence_router.get("/presence/current")
async def _current(request: Request) -> dict[str, Any]:
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
    from substrate.workstation.jarvis_command import (
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

    else:
        result["response_text"] = f"Command not recognized. Try: status, resume, approvals, mode switch, or navigation."

    _log_presence_event({
        "event": "command",
        "command_id": result["command_id"],
        "intent": intent.value,
        "governance": gov.value,
        "source": source,
        "text": text,
        "timestamp": result["timestamp"],
    })

    return result


@presence_router.get("/presence/capabilities")
async def _capabilities(request: Request) -> dict[str, Any]:
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


def _check_tts_available() -> bool:
    """Check if Kokoro TTS on Beast is reachable."""
    try:
        import urllib.request
        kokoro_url = os.environ.get("KOKORO_TTS_URL", "http://100.74.199.102:8880")
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
