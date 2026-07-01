"""Cockpit operator loop session routes — Phases 9-12.

Phase 9: Command Runtime
Phase 10: Workstation Runtime
Phase 11: Profile Runtime
Phase 12: Session Runtime

Split from cockpit_operator_loop_routes.py for the 3,000-line limit.
Mounted under /api/umh/ via include_router in cockpit.py.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

operator_loop_session_router: APIRouter = APIRouter()

_configured: bool = False

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


def _audit_log(event_type: str, data: dict[str, Any]) -> None:
    """Append to JSONL audit trail."""
    audit_path = os.path.join(_REPO_ROOT, "data", "umh", "audit", "operator_loop_audit.jsonl")
    os.makedirs(os.path.dirname(audit_path), exist_ok=True)
    entry = {
        "id": str(uuid4()),
        "event_type": event_type,
        "timestamp": time.time(),
        "data": data,
    }
    try:
        with open(audit_path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        logger.debug("audit log write failed: %s", e)


def configure(require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    operator_loop_session_router.include_router(
        _build_router(require_operator_dep), tags=["operator-loop-session"]
    )


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    # ── Phase 9: Command Runtime routes ─────────────────────────
    r.add_api_route("/command/status", _command_status, methods=["GET"], dependencies=auth)
    r.add_api_route("/command/submit", _command_submit, methods=["POST"], dependencies=auth)
    r.add_api_route("/command/classify", _command_classify, methods=["POST"], dependencies=auth)
    r.add_api_route("/command/history", _command_history, methods=["GET"], dependencies=auth)
    r.add_api_route("/command/pending", _command_pending, methods=["GET"], dependencies=auth)
    r.add_api_route("/command/timeline", _command_timeline, methods=["GET"], dependencies=auth)
    r.add_api_route(
        "/command/{command_id}/approve", _command_approve, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/command/{command_id}/reject", _command_reject, methods=["POST"], dependencies=auth
    )

    # ── Phase 10: Workstation Runtime routes ──────────────────────
    r.add_api_route(
        "/workstation/prepare", _workstation_prepare, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/workstation/restore", _workstation_restore, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/workstation/templates", _workstation_templates, methods=["GET"], dependencies=auth
    )
    r.add_api_route(
        "/workstation/snapshots", _workstation_snapshots, methods=["GET"], dependencies=auth
    )
    r.add_api_route(
        "/workstation/snapshots/take",
        _workstation_take_snapshot,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/workstation/recommendations",
        _workstation_recommendations,
        methods=["GET"],
        dependencies=auth,
    )
    r.add_api_route("/workstation/state", _workstation_state, methods=["GET"], dependencies=auth)

    # ── Phase 11: Profile Runtime routes ─────────────────────────
    r.add_api_route("/profile/state", _profile_state, methods=["GET"], dependencies=auth)
    r.add_api_route("/profile/profiles", _profile_profiles, methods=["GET"], dependencies=auth)
    r.add_api_route(
        "/profile/system-modes", _profile_system_modes, methods=["GET"], dependencies=auth
    )
    r.add_api_route(
        "/profile/activate-profile", _profile_activate_profile, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/profile/deactivate-profile",
        _profile_deactivate_profile,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/profile/activate-system-mode",
        _profile_activate_system_mode,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/profile/deactivate-system-mode",
        _profile_deactivate_system_mode,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/profile/activation-plan", _profile_activation_plan, methods=["GET"], dependencies=auth
    )
    r.add_api_route("/profile/conflicts", _profile_conflicts, methods=["GET"], dependencies=auth)
    r.add_api_route("/profile/timeline", _profile_timeline, methods=["GET"], dependencies=auth)
    r.add_api_route("/profile/context", _profile_context, methods=["GET"], dependencies=auth)

    # ── Phase 12: Session Runtime routes ─────────────────────────
    r.add_api_route("/session/state", _session_state, methods=["GET"], dependencies=auth)
    r.add_api_route("/session/list", _session_list, methods=["GET"], dependencies=auth)
    r.add_api_route("/session/active", _session_active, methods=["GET"], dependencies=auth)
    r.add_api_route("/session/start", _session_start, methods=["POST"], dependencies=auth)
    r.add_api_route(
        "/session/suspend", _session_suspend, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/session/resume", _session_resume, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/session/disconnect", _session_disconnect, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/session/restore", _session_restore, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/session/promote", _session_promote, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/session/handoff", _session_handoff, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/session/handoff/complete",
        _session_handoff_complete,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/session/history", _session_history, methods=["GET"], dependencies=auth
    )
    r.add_api_route(
        "/session/timeline", _session_timeline, methods=["GET"], dependencies=auth
    )

    return r


# ── Phase 9: Command Runtime handlers ────────────────────────────────────


def _get_command_runtime():
    from substrate.organism.command_runtime import get_command_runtime

    return get_command_runtime()


def _command_status(request: Request) -> dict:
    try:
        rt = _get_command_runtime()
        return {"success": True, **rt.get_status()}
    except Exception as exc:
        logger.error("command status failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _command_submit(request: Request) -> dict:
    body = await request.json()
    raw_input = body.get("raw_input", body.get("command", ""))
    if not raw_input:
        return {"success": False, "error": "raw_input required"}

    cmd_data = {}

    def _do_submit():
        rt = _get_command_runtime()
        cmd = rt.submit(
            raw_input=raw_input, source=body.get("source", "cockpit"),
            operator_id=body.get("operator_id", ""), session_id=body.get("session_id", ""),
            profile_mode=body.get("profile_mode", ""),
        )
        _audit_log("command_submit", {"command_id": cmd.command_id, "action": cmd.action_type})
        cmd_data["command"] = cmd.to_dict()
        return f"command {cmd.command_id} submitted", True

    resp = governed_mutation(
        mutation_name="command_submit",
        intent=f"submit command: {raw_input[:80]}",
        execute_fn=_do_submit,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(cmd_data)
    return result


async def _command_classify(request: Request) -> dict:
    try:
        body = await request.json()
        raw_input = body.get("raw_input", body.get("command", ""))
        if not raw_input:
            return {"success": False, "error": "raw_input required"}

        from substrate.organism.command_runtime import CommandClassifier

        classifier = CommandClassifier()
        action_type, confidence = classifier.classify(raw_input)
        return {
            "success": True,
            "action_type": action_type.value,
            "confidence": confidence,
            "raw_input": raw_input,
        }
    except Exception as exc:
        logger.error("command classify failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _command_history(request: Request) -> dict:
    try:
        rt = _get_command_runtime()
        limit = int(request.query_params.get("limit", "50"))
        return {"success": True, "commands": rt.get_history(limit=limit)}
    except Exception as exc:
        logger.error("command history failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _command_pending(request: Request) -> dict:
    try:
        rt = _get_command_runtime()
        return {"success": True, "pending": rt.get_pending()}
    except Exception as exc:
        logger.error("command pending failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _command_timeline(request: Request) -> dict:
    try:
        rt = _get_command_runtime()
        since = float(request.query_params.get("since", "0"))
        command_id = request.query_params.get("command_id", "")
        event_type = request.query_params.get("type", "")
        limit = int(request.query_params.get("limit", "100"))
        events = rt.get_timeline(
            since=since,
            command_id=command_id,
            event_type=event_type,
            limit=limit,
        )
        return {"success": True, "events": events}
    except Exception as exc:
        logger.error("command timeline failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _command_approve(request: Request) -> dict:
    command_id = request.path_params.get("command_id", "")
    if not command_id:
        return {"success": False, "error": "command_id required"}

    approve_data = {}

    def _do_approve():
        rt = _get_command_runtime()
        r = rt.approve_command(command_id)
        _audit_log("command_approve", {"command_id": command_id})
        approve_data.update(r)
        return f"command {command_id} approved", True

    resp = governed_mutation(
        mutation_name="approval_decide",
        intent=f"approve command {command_id}",
        execute_fn=_do_approve,
        source="cockpit",
        metadata={"command_id": command_id},
    )
    result = resp.to_http_dict()
    result.update(approve_data)
    return result


async def _command_reject(request: Request) -> dict:
    command_id = request.path_params.get("command_id", "")
    if not command_id:
        return {"success": False, "error": "command_id required"}
    body = await request.json()
    reason = body.get("reason", "")
    reject_data = {}

    def _do_reject():
        rt = _get_command_runtime()
        r = rt.reject_command(command_id, reason=reason)
        _audit_log("command_reject", {"command_id": command_id, "reason": reason})
        reject_data.update(r)
        return f"command {command_id} rejected", True

    resp = governed_mutation(
        mutation_name="approval_decide",
        intent=f"reject command {command_id}",
        execute_fn=_do_reject,
        source="cockpit",
        metadata={"command_id": command_id},
    )
    result = resp.to_http_dict()
    result.update(reject_data)
    return result


# ── Phase 10: Workstation Runtime handlers ────────────────────────────────


def _get_workstation_runtime():
    from substrate.organism.workstation_runtime import get_workstation_runtime

    return get_workstation_runtime()


async def _workstation_prepare(request: Request) -> dict:
    body = await request.json()
    intent = body.get("intent", "")
    if not intent:
        return {"success": False, "error": "intent required"}

    plan_data = {}

    def _do_prepare():
        rt = _get_workstation_runtime()
        plan = rt.prepare_workspace(
            intent=intent, profile_mode=body.get("profile_mode", ""),
            session_id=body.get("session_id", ""), operator_id=body.get("operator_id", ""),
        )
        _audit_log("workstation_prepare", {"intent": intent, "mode": plan.mode})
        plan_data["plan"] = plan.to_dict()
        return f"workspace prepared: {plan.mode}", True

    resp = governed_mutation(
        mutation_name="workstation_mutate",
        intent=f"prepare workspace: {intent[:80]}",
        execute_fn=_do_prepare,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(plan_data)
    return result


async def _workstation_restore(request: Request) -> dict:
    body = await request.json()
    snapshot_id = body.get("snapshot_id", "")
    plan_data = {}

    def _do_restore():
        rt = _get_workstation_runtime()
        plan = rt.restore_workspace(snapshot_id=snapshot_id)
        _audit_log("workstation_restore", {"snapshot_id": snapshot_id})
        plan_data["plan"] = plan.to_dict()
        return f"workspace restored from {snapshot_id}", True

    resp = governed_mutation(
        mutation_name="workstation_mutate",
        intent=f"restore workspace from {snapshot_id}",
        execute_fn=_do_restore,
        source="cockpit",
        metadata={"snapshot_id": snapshot_id},
    )
    result = resp.to_http_dict()
    result.update(plan_data)
    return result


def _workstation_templates(request: Request) -> dict:
    try:
        rt = _get_workstation_runtime()
        return {"success": True, "templates": rt.get_templates()}
    except Exception as exc:
        logger.error("workstation templates failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _workstation_snapshots(request: Request) -> dict:
    try:
        limit = int(request.query_params.get("limit", "20"))
        rt = _get_workstation_runtime()
        return {"success": True, "snapshots": rt.get_snapshots(limit=limit)}
    except Exception as exc:
        logger.error("workstation snapshots failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _workstation_take_snapshot(request: Request) -> dict:
    body = await request.json()
    trigger = body.get("trigger", "manual")
    notes = body.get("operator_notes", "")
    snap_data = {}

    def _do_snapshot():
        rt = _get_workstation_runtime()
        snap = rt.take_snapshot(trigger=trigger, operator_notes=notes)
        _audit_log("workstation_snapshot", {"snapshot_id": snap.snapshot_id})
        snap_data["snapshot"] = snap.to_dict()
        return f"snapshot {snap.snapshot_id} taken", True

    resp = governed_mutation(
        mutation_name="workstation_mutate",
        intent="take workstation snapshot",
        execute_fn=_do_snapshot,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(snap_data)
    return result


def _workstation_recommendations(request: Request) -> dict:
    try:
        rt = _get_workstation_runtime()
        return {"success": True, "recommendations": rt.get_recommendations()}
    except Exception as exc:
        logger.error("workstation recommendations failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _workstation_state(request: Request) -> dict:
    try:
        rt = _get_workstation_runtime()
        return {"success": True, "state": rt.get_state()}
    except Exception as exc:
        logger.error("workstation state failed: %s", exc)
        return {"success": False, "error": str(exc)}


# ── Phase 11: Profile Runtime handlers ───────────────────────────


def _get_profile_runtime():
    from substrate.organism.profile_runtime import get_profile_runtime

    return get_profile_runtime()


def _profile_state(request: Request) -> dict:
    try:
        rt = _get_profile_runtime()
        return {"success": True, "state": rt.get_state()}
    except Exception as exc:
        logger.error("profile state failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _profile_profiles(request: Request) -> dict:
    try:
        rt = _get_profile_runtime()
        return {"success": True, "profiles": rt.get_profiles()}
    except Exception as exc:
        logger.error("profile profiles failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _profile_system_modes(request: Request) -> dict:
    try:
        rt = _get_profile_runtime()
        return {"success": True, "system_modes": rt.get_system_modes()}
    except Exception as exc:
        logger.error("profile system modes failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _profile_activate_profile(request: Request) -> dict:
    body = await request.json()
    profile_mode = body.get("profile_mode", "")
    source = body.get("source", "cockpit")
    manual_override = body.get("manual_override", False)
    if not profile_mode:
        return {"success": False, "error": "profile_mode is required"}

    activate_data = {}

    def _do_activate():
        rt = _get_profile_runtime()
        r = rt.activate_profile(profile_mode, source=source, manual_override=manual_override)
        _audit_log("profile_activated", {"profile": profile_mode, "source": source})
        activate_data.update(r)
        return f"profile {profile_mode} activated", r.get("success", True)

    resp = governed_mutation(
        mutation_name="profile_mutate",
        intent=f"activate profile {profile_mode}",
        execute_fn=_do_activate,
        source="cockpit",
        metadata={"profile_mode": profile_mode},
    )
    result = resp.to_http_dict()
    result.update(activate_data)
    return result


def _profile_deactivate_profile(request: Request) -> dict:
    deactivate_data = {}

    def _do_deactivate():
        rt = _get_profile_runtime()
        r = rt.deactivate_profile()
        _audit_log("profile_deactivated", {})
        deactivate_data.update(r)
        return "profile deactivated", r.get("success", True)

    resp = governed_mutation(
        mutation_name="profile_mutate",
        intent="deactivate profile",
        execute_fn=_do_deactivate,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(deactivate_data)
    return result


async def _profile_activate_system_mode(request: Request) -> dict:
    body = await request.json()
    mode_name = body.get("mode_name", "")
    source = body.get("source", "cockpit")
    if not mode_name:
        return {"success": False, "error": "mode_name is required"}

    mode_data = {}

    def _do_activate():
        rt = _get_profile_runtime()
        r = rt.activate_system_mode(mode_name, source=source)
        _audit_log("system_mode_activated", {"mode": mode_name, "source": source})
        mode_data.update(r)
        return f"system mode {mode_name} activated", r.get("success", True)

    resp = governed_mutation(
        mutation_name="profile_mutate",
        intent=f"activate system mode {mode_name}",
        execute_fn=_do_activate,
        source="cockpit",
        metadata={"mode_name": mode_name},
    )
    result = resp.to_http_dict()
    result.update(mode_data)
    return result


async def _profile_deactivate_system_mode(request: Request) -> dict:
    body = await request.json()
    mode_name = body.get("mode_name", "")
    if not mode_name:
        return {"success": False, "error": "mode_name is required"}

    mode_data = {}

    def _do_deactivate():
        rt = _get_profile_runtime()
        r = rt.deactivate_system_mode(mode_name)
        _audit_log("system_mode_deactivated", {"mode": mode_name})
        mode_data.update(r)
        return f"system mode {mode_name} deactivated", r.get("success", True)

    resp = governed_mutation(
        mutation_name="profile_mutate",
        intent=f"deactivate system mode {mode_name}",
        execute_fn=_do_deactivate,
        source="cockpit",
        metadata={"mode_name": mode_name},
    )
    result = resp.to_http_dict()
    result.update(mode_data)
    return result


def _profile_activation_plan(request: Request) -> dict:
    try:
        rt = _get_profile_runtime()
        plan = rt.get_activation_plan()
        return {"success": True, "plan": plan}
    except Exception as exc:
        logger.error("profile activation plan failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _profile_conflicts(request: Request) -> dict:
    try:
        rt = _get_profile_runtime()
        conflicts = rt.detect_conflicts()
        return {"success": True, "conflicts": [c.to_dict() for c in conflicts]}
    except Exception as exc:
        logger.error("profile conflicts failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _profile_timeline(request: Request) -> dict:
    try:
        rt = _get_profile_runtime()
        limit = int(request.query_params.get("limit", "50"))
        events = rt.get_timeline(limit)
        return {"success": True, "events": events}
    except Exception as exc:
        logger.error("profile timeline failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _profile_context(request: Request) -> dict:
    try:
        rt = _get_profile_runtime()
        ctx = rt.get_context()
        return {"success": True, "context": ctx.to_dict()}
    except Exception as exc:
        logger.error("profile context failed: %s", exc)
        return {"success": False, "error": str(exc)}


# ── Phase 12: Session Runtime handlers ────────────────────────────────────


def _get_session_runtime():
    from substrate.organism.session_runtime import get_session_runtime

    return get_session_runtime()


def _session_state(request: Request) -> dict:
    try:
        rt = _get_session_runtime()
        return {"success": True, **rt.get_state()}
    except Exception as exc:
        logger.error("session state failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _session_list(request: Request) -> dict:
    try:
        rt = _get_session_runtime()
        sessions = rt.list_sessions()
        return {"success": True, "sessions": [s.to_dict() for s in sessions]}
    except Exception as exc:
        logger.error("session list failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _session_active(request: Request) -> dict:
    try:
        rt = _get_session_runtime()
        active = rt.list_active_sessions()
        return {"success": True, "sessions": [s.to_dict() for s in active]}
    except Exception as exc:
        logger.error("session active failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _session_start(request: Request) -> dict:
    body = await request.json()
    session_data = {}

    def _do_start():
        rt = _get_session_runtime()
        session = rt.start_session(
            session_type=body.get("session_type", "desktop"), host_id=body.get("host_id", ""),
            device_id=body.get("device_id", ""), profile_id=body.get("profile_id", ""),
            workstation_mode=body.get("workstation_mode", ""),
            authority=body.get("authority", "secondary"), metadata=body.get("metadata"),
        )
        _audit_log("session_started", {"session_id": session.session_id})
        session_data["session"] = session.to_dict()
        return f"session {session.session_id} started", True

    resp = governed_mutation(
        mutation_name="session_mutate",
        intent="start session",
        execute_fn=_do_start,
        source="cockpit",
    )
    result = resp.to_http_dict()
    result.update(session_data)
    return result


async def _session_suspend(request: Request) -> dict:
    body = await request.json()
    session_id = body.get("session_id", "")
    if not session_id:
        return {"success": False, "error": "session_id is required"}

    def _do_suspend():
        rt = _get_session_runtime()
        ok = rt.suspend_session(session_id)
        _audit_log("session_suspended", {"session_id": session_id})
        return f"session {session_id} suspended", ok

    resp = governed_mutation(
        mutation_name="session_mutate",
        intent=f"suspend session {session_id}",
        execute_fn=_do_suspend,
        source="cockpit",
        metadata={"session_id": session_id},
    )
    return resp.to_http_dict()


async def _session_resume(request: Request) -> dict:
    body = await request.json()
    session_id = body.get("session_id", "")
    if not session_id:
        return {"success": False, "error": "session_id is required"}

    def _do_resume():
        rt = _get_session_runtime()
        ok = rt.resume_session(session_id)
        _audit_log("session_resumed", {"session_id": session_id})
        return f"session {session_id} resumed", ok

    resp = governed_mutation(
        mutation_name="session_mutate",
        intent=f"resume session {session_id}",
        execute_fn=_do_resume,
        source="cockpit",
        metadata={"session_id": session_id},
    )
    return resp.to_http_dict()


async def _session_disconnect(request: Request) -> dict:
    body = await request.json()
    session_id = body.get("session_id", "")
    if not session_id:
        return {"success": False, "error": "session_id is required"}

    def _do_disconnect():
        rt = _get_session_runtime()
        ok = rt.disconnect_session(session_id)
        _audit_log("session_disconnected", {"session_id": session_id})
        return f"session {session_id} disconnected", ok

    resp = governed_mutation(
        mutation_name="session_mutate",
        intent=f"disconnect session {session_id}",
        execute_fn=_do_disconnect,
        source="cockpit",
        metadata={"session_id": session_id},
    )
    return resp.to_http_dict()


async def _session_restore(request: Request) -> dict:
    body = await request.json()
    session_id = body.get("session_id", "")
    if not session_id:
        return {"success": False, "error": "session_id is required"}

    def _do_restore():
        rt = _get_session_runtime()
        ok = rt.restore_session(session_id)
        _audit_log("session_restored", {"session_id": session_id})
        return f"session {session_id} restored", ok

    resp = governed_mutation(
        mutation_name="session_mutate",
        intent=f"restore session {session_id}",
        execute_fn=_do_restore,
        source="cockpit",
        metadata={"session_id": session_id},
    )
    return resp.to_http_dict()


async def _session_promote(request: Request) -> dict:
    body = await request.json()
    session_id = body.get("session_id", "")
    if not session_id:
        return {"success": False, "error": "session_id is required"}

    promote_data = {}

    def _do_promote():
        rt = _get_session_runtime()
        ok, demoted = rt.promote_to_primary(session_id)
        _audit_log("session_promoted", {"session_id": session_id, "demoted": demoted})
        promote_data["demoted_session_id"] = demoted
        return f"session {session_id} promoted", ok

    resp = governed_mutation(
        mutation_name="session_mutate",
        intent=f"promote session {session_id} to primary",
        execute_fn=_do_promote,
        source="cockpit",
        metadata={"session_id": session_id},
    )
    result = resp.to_http_dict()
    result.update(promote_data)
    return result


async def _session_handoff(request: Request) -> dict:
    body = await request.json()
    source = body.get("source_session_id", "")
    target = body.get("target_session_id", "")
    if not source or not target:
        return {"success": False, "error": "source_session_id and target_session_id required"}

    handoff_data = {}

    def _do_handoff():
        rt = _get_session_runtime()
        handoff = rt.initiate_handoff(source, target)
        if handoff:
            _audit_log("session_handoff_initiated", {"handoff_id": handoff.handoff_id})
            handoff_data["handoff"] = handoff.to_dict()
            return f"handoff {handoff.handoff_id} initiated", True
        return "handoff failed", False

    resp = governed_mutation(
        mutation_name="session_mutate",
        intent=f"handoff session {source} to {target}",
        execute_fn=_do_handoff,
        source="cockpit",
        metadata={"source": source, "target": target},
    )
    result = resp.to_http_dict()
    result.update(handoff_data)
    return result


async def _session_handoff_complete(request: Request) -> dict:
    body = await request.json()
    handoff_id = body.get("handoff_id", "")
    if not handoff_id:
        return {"success": False, "error": "handoff_id is required"}

    def _do_complete():
        rt = _get_session_runtime()
        ok = rt.complete_handoff(handoff_id)
        _audit_log("session_handoff_completed", {"handoff_id": handoff_id})
        return f"handoff {handoff_id} completed", ok

    resp = governed_mutation(
        mutation_name="session_mutate",
        intent=f"complete handoff {handoff_id}",
        execute_fn=_do_complete,
        source="cockpit",
        metadata={"handoff_id": handoff_id},
    )
    return resp.to_http_dict()


def _session_history(request: Request) -> dict:
    try:
        rt = _get_session_runtime()
        handoffs = rt.get_recent_handoffs(limit=20)
        return {"success": True, "handoffs": [h.to_dict() for h in handoffs]}
    except Exception as exc:
        logger.error("session history failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _session_timeline(request: Request) -> dict:
    try:
        rt = _get_session_runtime()
        limit = int(request.query_params.get("limit", "50"))
        events = rt.get_timeline(limit)
        return {"success": True, "events": [e.to_dict() for e in events]}
    except Exception as exc:
        logger.error("session timeline failed: %s", exc)
        return {"success": False, "error": str(exc)}
