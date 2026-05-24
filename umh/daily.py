"""Daily boot sequence — clap, greeting, status, mode boot."""

from __future__ import annotations

import logging
import os
import sys
import uuid

from umh.audio import play_boot_clap
from umh.modes import ModeState, ProfileMode
from umh.profile import ProfileManager
from umh.voice import VoiceOutput

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


def _get_persona_name() -> str:
    try:
        from substrate.foundation.persona import Persona

        p = Persona.from_env()
        return p.display_name
    except (ImportError, Exception):
        return os.environ.get("UMH_PERSONA_NAME", "UMH")


def _get_approval_count() -> int:
    try:
        from umh.approvals import pending_count

        return pending_count()
    except Exception:
        return 0


def _get_operator_mode(node_id: str = "workstation_local") -> str:
    try:
        from substrate.execution.bridge.operator_state import get_operator_state_store

        store = get_operator_state_store()
        state = store.get_or_create(node_id)
        return state.mode.value
    except Exception:
        return "unknown"


def _get_continuity_summary() -> str:
    try:
        from umh.continuity import SessionContinuity

        c = SessionContinuity()
        return c.get_resume_summary()
    except Exception:
        return ""


def _log_boot_health() -> None:
    try:
        from umh.health import run_health_check

        results = run_health_check()
        down = [r for r in results if r.status == "DOWN"]
        if down:
            names = ", ".join(r.name for r in down)
            logger.info("Boot health: %d/%d subsystems DOWN: %s", len(down), len(results), names)
    except Exception:
        pass


def _get_recent_trigger_count() -> int:
    try:
        from umh.triggers import get_trigger_history

        return len(get_trigger_history())
    except Exception:
        return 0


def _format_status(
    persona_name: str,
    mode_state: ModeState,
    session_id: str,
    text_only: bool,
    trace_count: int = 0,
    error_count: int = 0,
    pending_count: int = 0,
    resume_summary: str = "",
    next_action: str = "",
    perception_snapshot: dict | None = None,
) -> str:
    voice_str = "text-only" if text_only else "ambient (persona)"

    webcam_snap = (perception_snapshot or {}).get("webcam", {})
    if webcam_snap.get("running"):
        webcam_str = "active (present)" if webcam_snap.get("face_detected") else "active (no face)"
    else:
        webcam_str = "disabled"
    try:
        from umh.mesh import get_node_count

        mesh_nodes = get_node_count()
        mesh_str = (
            f"{mesh_nodes} node{'s' if mesh_nodes != 1 else ''} online"
            if mesh_nodes
            else "standalone"
        )
    except Exception:
        mesh_str = "standalone"

    profiles = " + ".join(p.value for p in mode_state.profiles)
    operator_str = _get_operator_mode()
    live_approvals = _get_approval_count()
    trigger_count = _get_recent_trigger_count()

    w = 44
    lines = [
        "",
        "╔" + "═" * w + "╗",
        f"║  UMH Workstation — {persona_name:<{w - 21}s}║",
        "╠" + "═" * w + "╝",
        f"  Mode:      {profiles}",
        f"  Session:   {session_id[:8]}",
        f"  Voice:     {voice_str}",
        f"  Webcam:    {webcam_str}",
        f"  Mesh:      {mesh_str}",
        f"  Operator:  {operator_str}",
    ]

    if trace_count or error_count:
        lines.append(f"  Status:    {trace_count} traces, {error_count} errors")
    if live_approvals > 0:
        lines.append(f"  Approvals: {live_approvals} pending")
    elif pending_count > 0:
        lines.append(f"  Approvals: {pending_count} pending")
    if trigger_count > 0:
        lines.append(f"  Triggers:  {trigger_count} recent")
    if next_action:
        lines.append(f"  Next:      {next_action[:40]}")

    lines.append("")
    return "\n".join(lines)


def run_daily_boot(text_only: bool = False) -> tuple[ModeState, str]:
    persona_name = _get_persona_name()
    session_id = uuid.uuid4().hex[:8]
    voice = VoiceOutput(text_only=text_only)
    pm = ProfileManager()

    play_boot_clap()

    snapshot = pm.load_snapshot()
    resume_summary = pm.resume_summary
    next_actions = pm.next_actions
    next_action = next_actions[0] if next_actions else ""

    continuity_summary = _get_continuity_summary()
    if continuity_summary and continuity_summary != "No previous session to resume.":
        resume_summary = continuity_summary

    trace_count = 0
    error_count = 0
    pending_count = 0
    if snapshot and hasattr(snapshot, "session"):
        trace_count = getattr(snapshot.session, "trace_count", 0)
        error_count = getattr(snapshot.session, "error_count", 0)
        pending_count = len(getattr(snapshot.session, "pending_approvals", []))

    live_approvals = _get_approval_count()

    greeting = f"{persona_name} online."
    if resume_summary and resume_summary != "No previous session":
        greeting += f" {resume_summary}."
    if trace_count or error_count:
        greeting += f" {trace_count} traces, {error_count} errors."
    if live_approvals > 0:
        greeting += f" {live_approvals} pending approval{'s' if live_approvals != 1 else ''}."
    if next_action:
        greeting += f" {next_action}."

    _log_boot_health()

    voice.speak_and_print(greeting)

    mode_state = ModeState()
    default_mode = pm.preferences.default_profile
    for pm_enum in ProfileMode:
        if pm_enum.value == default_mode:
            mode_state.set_profile(pm_enum)
            break

    status = _format_status(
        persona_name=persona_name,
        mode_state=mode_state,
        session_id=session_id,
        text_only=text_only,
        trace_count=trace_count,
        error_count=error_count,
        pending_count=pending_count,
        resume_summary=resume_summary,
        next_action=next_action,
    )
    print(status)

    return mode_state, session_id


def show_status() -> int:
    persona_name = _get_persona_name()
    pm = ProfileManager()
    snapshot = pm.load_snapshot()
    mode_state = ModeState()

    trace_count = 0
    error_count = 0
    pending_count = 0
    if snapshot and hasattr(snapshot, "session"):
        trace_count = getattr(snapshot.session, "trace_count", 0)
        error_count = getattr(snapshot.session, "error_count", 0)
        pending_count = len(getattr(snapshot.session, "pending_approvals", []))

    status = _format_status(
        persona_name=persona_name,
        mode_state=mode_state,
        session_id="(none)",
        text_only=True,
        trace_count=trace_count,
        error_count=error_count,
        pending_count=pending_count,
        resume_summary=pm.resume_summary,
        next_action=pm.next_actions[0] if pm.next_actions else "",
    )
    print(status)
    return 0
