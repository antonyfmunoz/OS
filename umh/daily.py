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
    profiles = " + ".join(p.value for p in mode_state.profiles)

    lines = [
        "",
        "╔══════════════════════════════════════════╗",
        f"║  UMH Workstation — {persona_name:<22s}║",
        "╠══════════════════════════════════════════╣",
        f"║  Mode:    {profiles:<13s} Session: {session_id[:8]:<4s} ║",
        f"║  Voice:   {voice_str:<31s}║",
        f"║  Webcam:  {webcam_str:<31s}║",
    ]

    if trace_count or error_count:
        lines.append(
            f"║  Status:  {trace_count} traces, {error_count} errors{' ' * (20 - len(str(trace_count)) - len(str(error_count)))}║"
        )
    if pending_count:
        lines.append(
            f"║  Pending: {pending_count} approval{'s' if pending_count != 1 else ''}{' ' * (20 - len(str(pending_count)))}║"
        )
    if next_action:
        na = next_action[:28]
        lines.append(f"║  Next:    {na:<31s}║")

    lines.append("╚══════════════════════════════════════════╝")
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

    trace_count = 0
    error_count = 0
    pending_count = 0
    if snapshot and hasattr(snapshot, "session"):
        trace_count = getattr(snapshot.session, "trace_count", 0)
        error_count = getattr(snapshot.session, "error_count", 0)
        pending_count = len(getattr(snapshot.session, "pending_approvals", []))

    greeting = f"{persona_name} online."
    if resume_summary and resume_summary != "No previous session":
        greeting += f" {resume_summary}."
    if next_action:
        greeting += f" {next_action}."

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
