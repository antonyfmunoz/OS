"""
Day workflow coordination — open_day / close_day.

Coordination layer between the operator session spine (OperatorSessionStore)
and the existing ritual registry (RitualRegistry). No LLM calls. No tmux
logic. No Discord send logic. No operator_state / operator_transitions wiring.

Two public functions:
    open_day(*, workspace, node_preference, discord_channel_id) -> dict
    close_day(*, completed_today, unresolved, overnight_tasks,
               continuity_notes, resume_context, discord_channel_id) -> dict

Design rules (mirror substrate conventions):
- Best-effort ritual execution: ritual failures become warnings, not errors.
- Additive only — never imported on the hot path.
- Deterministic return shapes: callers can always key-access the dict safely.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Optional

from umh.substrate.operator_session import (
    OperatorDayMode,
    OperatorSession,
    OperatorSessionStore,
)
from umh.substrate.rituals import RitualKind, RitualRegistry, RitualState


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _log(msg: str) -> None:
    print(f"[substrate.day_workflows] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _start_ritual_best_effort(
    kind: RitualKind, inputs: dict
) -> tuple[Optional[str], Optional[str]]:
    """Start a ritual and return (ritual_id, warning).

    Returns (None, warning_str) on failure so callers can continue.
    """
    try:
        registry = RitualRegistry.default()
        ritual = registry.start(kind, inputs=inputs)
        return ritual.ritual_id, None
    except Exception as exc:  # noqa: BLE001
        msg = f"{kind.value} ritual start failed: {exc}"
        _log(msg)
        return None, msg


def _advance_ritual_best_effort(
    ritual_id: Optional[str],
    states: list[RitualState],
    outputs: Optional[dict] = None,
) -> Optional[str]:
    """Advance a ritual through a sequence of states; return warning string on failure."""
    if ritual_id is None:
        return None
    try:
        registry = RitualRegistry.default()
        for state in states[:-1]:
            registry.advance(ritual_id, state)
        # Last state — use complete() if it is COMPLETED, else advance()
        final = states[-1]
        if final == RitualState.COMPLETED:
            registry.complete(ritual_id, outputs=outputs or {})
        else:
            registry.advance(ritual_id, final)
        return None
    except Exception as exc:  # noqa: BLE001
        msg = f"ritual advance failed: {exc}"
        _log(msg)
        return msg


# ─── open_day ─────────────────────────────────────────────────────────────────


def open_day(
    *,
    workspace: Optional[str] = None,
    node_preference: Optional[str] = None,
    discord_channel_id: Optional[str] = None,
) -> dict:
    """Open the operator's day session.

    If the day is already open, returns an already_open response with no
    state mutation and no new ritual. Otherwise creates a new OperatorSession,
    inherits continuity from the prior session, starts an OPEN_DAY ritual
    (best-effort), and persists the new session.

    Args:
        workspace: Target workspace ("builder" | "product" | None → fallback).
        node_preference: Routing preference ("local" | "vps" | "auto" | None → fallback).
        discord_channel_id: Active Discord channel for observability (optional).

    Returns:
        dict with status, day_session_id, ritual_id, briefing, day_mode,
        active_workspace, opened_at. Includes ritual_warning if ritual failed.
    """
    store = OperatorSessionStore.default()
    current = store.get()

    # ── Guard: already open ──────────────────────────────────────────────────
    if current is not None and current.is_day_open:
        _log(f"day already open: {current.day_session_id}")
        return {
            "status": "already_open",
            "day_session_id": current.day_session_id,
            "ritual_id": current.ritual_open_id,
            "day_mode": current.day_mode.value,
            "active_workspace": current.active_workspace,
            "opened_at": current.opened_at,
        }

    # ── Start OPEN_DAY ritual (best-effort) ──────────────────────────────────
    ritual_id, ritual_warning = _start_ritual_best_effort(
        RitualKind.OPEN_DAY, inputs={"date": _today_str()}
    )
    advance_warning = _advance_ritual_best_effort(
        ritual_id,
        [RitualState.GATHERING, RitualState.BRIEFING, RitualState.COMPLETED],
    )
    if advance_warning and not ritual_warning:
        ritual_warning = advance_warning

    # ── Read continuity from prior session ───────────────────────────────────
    prior = current  # may be None or a closed session
    if prior is not None:
        where_we_left_off: Optional[str] = prior.continuity_notes_for_next_open
        unfinished_priorities: list = list(prior.unfinished_priorities)
        overnight_tasks: list = list(prior.overnight_tasks)
        resume_context: Optional[str] = prior.last_resume_context
        # Inherit workspace/node if caller did not supply
        prior_workspace = prior.active_workspace
        prior_node = prior.node_preference
    else:
        where_we_left_off = None
        unfinished_priorities = []
        overnight_tasks = []
        resume_context = None
        prior_workspace = "builder"
        prior_node = "auto"

    recommended_first_action: Optional[str] = (
        unfinished_priorities[0] if unfinished_priorities else None
    )

    # ── Resolve workspace and node_preference ─────────────────────────────────
    resolved_workspace = workspace or prior_workspace or "builder"
    resolved_node = node_preference or prior_node or "auto"

    # ── Determine day_mode (v1 heuristic) ────────────────────────────────────
    if resolved_node == "local":
        day_mode = OperatorDayMode.LOCAL_ACTIVE
    else:
        day_mode = OperatorDayMode.REMOTE_ACTIVE

    # ── Create new OperatorSession ───────────────────────────────────────────
    now = _utcnow()
    new_session = OperatorSession.new()
    new_session.is_day_open = True
    new_session.opened_at = now
    new_session.day_mode = day_mode
    new_session.active_workspace = resolved_workspace
    new_session.node_preference = resolved_node
    new_session.ritual_open_id = ritual_id
    # Inherit continuity fields into the new session
    new_session.unfinished_priorities = unfinished_priorities
    new_session.overnight_tasks = overnight_tasks
    new_session.continuity_notes_for_next_open = where_we_left_off
    new_session.last_resume_context = resume_context
    if discord_channel_id:
        new_session.last_active_discord_channel_id = discord_channel_id

    store.put(new_session)
    _log(f"day opened: {new_session.day_session_id} mode={day_mode.value}")

    # ── Best-effort: update station presence from open_day ──────────────────
    try:
        from umh.substrate.station_presence import (
            StationPresenceMode,
            set_presence_mode,
        )

        if resolved_node == "local":
            set_presence_mode(StationPresenceMode.LOCAL)
        else:
            set_presence_mode(StationPresenceMode.REMOTE)
    except Exception:  # noqa: BLE001
        pass

    # ── Task system summary (best-effort, v2-enhanced when available) ──────
    task_summary: dict = {}
    try:
        from umh.substrate.task_queue import get_enhanced_task_summary

        task_summary = get_enhanced_task_summary()
    except Exception:  # noqa: BLE001
        # v2 unavailable — fall back to v1 summary
        try:
            from umh.substrate.task_system import get_task_summary

            task_summary = get_task_summary()
        except Exception as exc:  # noqa: BLE001
            _log(f"task_summary failed: {exc}")

    # ── Pipeline summary (best-effort) ──────────────────────────────────────
    pipeline_summary: dict = {}
    try:
        from umh.substrate.pipeline_execution import get_pipeline_summary

        pipeline_summary = get_pipeline_summary()
    except Exception as exc:  # noqa: BLE001
        _log(f"pipeline_summary failed: {exc}")

    # ── Perception summary (v4, best-effort) ──────────────────────────────
    perception_summary: dict = {}
    try:
        from umh.substrate.auto_task_generation import get_perception_summary

        perception_summary = get_perception_summary()
    except Exception as exc:  # noqa: BLE001
        _log(f"perception_summary failed: {exc}")

    # ── Live session summary (v4, best-effort) ─────────────────────────────
    live_session_summary: dict = {}
    try:
        from umh.substrate.live_sessions import get_live_session_summary

        live_session_summary = get_live_session_summary()
    except Exception as exc:  # noqa: BLE001
        _log(f"live_session_summary failed: {exc}")

    # ── Station summary (v5, unified via station_presence) ──────────────────
    station_summary: dict = {}
    try:
        from umh.substrate.station_presence import get_station_summary

        station_summary = get_station_summary()
    except Exception as exc:  # noqa: BLE001
        _log(f"station_summary failed: {exc}")

    # ── Node health summary (v6, via node_controller) ─────────────────────
    node_health: dict = {}
    try:
        from umh.substrate.node_controller import get_node_health_summary

        node_health = get_node_health_summary()
    except Exception as exc:  # noqa: BLE001
        _log(f"node_health_summary failed: {exc}")

    # ── Apply default scene based on workspace (v6, best-effort) ──────────
    active_scene: Optional[str] = None
    try:
        from umh.substrate.scenes import get_scene

        default_scene = (
            "builder_mode" if resolved_workspace == "builder" else "operator_mode"
        )
        if resolved_node == "local":
            default_scene = "full_station"
        scene = get_scene(default_scene)
        if scene is not None:
            active_scene = scene.name
            new_session.active_scene = active_scene
            store.put(new_session)
    except Exception as exc:  # noqa: BLE001
        _log(f"scene application failed: {exc}")

    # ── Blocked operator items (v4, best-effort) ──────────────────────────
    blocked_operator_items: list = []
    try:
        from umh.substrate.task_queue import get_waiting_on_operator_tasks

        waiting_tasks = get_waiting_on_operator_tasks()
        for t in waiting_tasks[:5]:
            blocked_operator_items.append(
                {
                    "task_id": t.task_id,
                    "title": t.title,
                    "prompt": t.requires_input_prompt,
                }
            )
    except Exception as exc:  # noqa: BLE001
        _log(f"blocked_operator_items failed: {exc}")

    # ── Build response ───────────────────────────────────────────────────────
    response: dict = {
        "status": "ok",
        "day_session_id": new_session.day_session_id,
        "ritual_id": ritual_id,
        "briefing": {
            "where_we_left_off": where_we_left_off,
            "unfinished_priorities": unfinished_priorities,
            "overnight_tasks": overnight_tasks,
            "recommended_first_action": recommended_first_action,
            "resume_context": resume_context,
            "task_summary": task_summary,
            # Pipeline-level briefing (v3)
            "completed_overnight": pipeline_summary.get("completed_pipelines", 0),
            "active_pipelines": pipeline_summary.get("active_pipelines", 0),
            "failed_pipelines": pipeline_summary.get("failed_pipelines", 0),
            "waiting_on_operator": pipeline_summary.get("waiting_on_operator", 0),
            "top_priority_task_title": pipeline_summary.get("top_priority_task_title"),
            "top_blocked_prompt": pipeline_summary.get("top_blocked_prompt"),
        },
        "day_mode": day_mode.value,
        "active_workspace": resolved_workspace,
        "opened_at": now,
    }
    # v4/v5 extensions (additive, backward-compatible)
    if perception_summary:
        response["perception_summary"] = perception_summary
    if live_session_summary:
        response["live_session_summary"] = live_session_summary
    if station_summary:
        response["station_summary"] = station_summary
        # Backward compat alias
        response["local_station_summary"] = station_summary
    if blocked_operator_items:
        response["blocked_operator_items"] = blocked_operator_items
    # v6 extensions (node health + scene)
    if node_health:
        response["node_health"] = node_health
    if active_scene:
        response["active_scene"] = active_scene
    if ritual_warning:
        response["ritual_warning"] = ritual_warning
    return response


# ─── close_day ────────────────────────────────────────────────────────────────


def close_day(
    *,
    completed_today: Optional[list] = None,
    unresolved: Optional[list] = None,
    overnight_tasks: Optional[list] = None,
    continuity_notes: Optional[str] = None,
    resume_context: Optional[str] = None,
    discord_channel_id: Optional[str] = None,
) -> dict:
    """Close the operator's day session and write continuity for the next open.

    If no open session exists, returns {"status": "not_open"}. Otherwise
    starts a CLOSE_DAY ritual (best-effort), writes all continuity fields,
    sets is_day_open=False, and persists.

    Args:
        completed_today: Items finished during the day.
        unresolved: Items not finished — carried to next day's briefing.
        overnight_tasks: Tasks the system should handle autonomously overnight.
        continuity_notes: Freeform notes for the next open_day briefing.
        resume_context: Structured context string for the next session.
        discord_channel_id: Active Discord channel for observability (optional).

    Returns:
        dict with status, day_session_id, ritual_id, summary, closed_at.
        Includes ritual_warning if ritual failed.
    """
    store = OperatorSessionStore.default()
    current = store.get()

    # ── Guard: not open ───────────────────────────────────────────────────────
    if current is None or not current.is_day_open:
        _log("close_day called but no open session")
        return {"status": "not_open"}

    # ── Start CLOSE_DAY ritual (best-effort) ─────────────────────────────────
    ritual_id, ritual_warning = _start_ritual_best_effort(
        RitualKind.CLOSE_DAY, inputs={"date": _today_str()}
    )
    advance_warning = _advance_ritual_best_effort(
        ritual_id,
        [RitualState.GATHERING, RitualState.COMPLETED],
    )
    if advance_warning and not ritual_warning:
        ritual_warning = advance_warning

    # ── Build durable close recap string ─────────────────────────────────────
    lines = []
    if completed_today:
        lines.append("Completed: " + ", ".join(str(x) for x in completed_today))
    if unresolved:
        lines.append("Unresolved: " + ", ".join(str(x) for x in unresolved))
    if overnight_tasks:
        lines.append("Overnight: " + ", ".join(str(x) for x in overnight_tasks))
    if continuity_notes:
        lines.append(f"Notes: {continuity_notes}")
    recap = " | ".join(lines) if lines else "No entries."

    # ── Determine day_mode ───────────────────────────────────────────────────
    day_mode = (
        OperatorDayMode.OVERNIGHT if overnight_tasks else OperatorDayMode.INACTIVE
    )

    # ── Update current session ───────────────────────────────────────────────
    now = _utcnow()
    current.is_day_open = False
    current.closed_at = now
    current.day_mode = day_mode
    current.ritual_close_id = ritual_id
    current.unfinished_priorities = list(unresolved)
    current.overnight_tasks = list(overnight_tasks)
    current.continuity_notes_for_next_open = continuity_notes
    current.last_resume_context = resume_context
    current.last_briefing_summary = recap
    if discord_channel_id:
        current.last_active_discord_channel_id = discord_channel_id

    store.put(current)
    _log(f"day closed: {current.day_session_id} mode={day_mode.value}")

    # ── Best-effort: update station presence from close_day ─────────────────
    try:
        from umh.substrate.station_presence import (
            StationPresenceMode,
            set_presence_mode,
        )

        if day_mode == OperatorDayMode.OVERNIGHT:
            set_presence_mode(StationPresenceMode.OVERNIGHT)
        else:
            set_presence_mode(StationPresenceMode.AWAY)
    except Exception:  # noqa: BLE001
        pass

    # ── Apply close scene (v6, best-effort) ───────────────────────────────
    close_scene: Optional[str] = None
    try:
        from umh.substrate.scenes import get_scene as _get_scene

        scene_name = "overnight" if day_mode == OperatorDayMode.OVERNIGHT else "idle"
        scene = _get_scene(scene_name)
        if scene is not None:
            close_scene = scene.name
            current.active_scene = close_scene
            store.put(current)  # persist scene after assignment
    except Exception as exc:  # noqa: BLE001
        _log(f"close scene application failed: {exc}")

    # ── Node health for close summary (v6, best-effort) ───────────────────
    node_health_close: dict = {}
    try:
        from umh.substrate.node_controller import get_node_health_summary

        node_health_close = get_node_health_summary()
    except Exception as exc:  # noqa: BLE001
        _log(f"node_health_summary (close) failed: {exc}")

    # ── Prepare overnight queue (move READY → OVERNIGHT_QUEUED) ────────────
    overnight_queue_prep: Optional[dict] = None
    if day_mode == OperatorDayMode.OVERNIGHT:
        try:
            from umh.substrate.task_queue import prepare_overnight_queue

            overnight_queue_prep = prepare_overnight_queue()
        except Exception as exc:  # noqa: BLE001
            _log(f"overnight queue prep failed: {exc}")

    # ── Run overnight tasks if transitioning to OVERNIGHT mode ────────────────
    overnight_completed: list = []
    if day_mode == OperatorDayMode.OVERNIGHT:
        try:
            from umh.substrate.task_system import run_overnight_tasks

            executed = run_overnight_tasks()
            overnight_completed = [t.task_id for t in executed]
        except Exception as exc:  # noqa: BLE001
            _log(f"overnight task execution failed: {exc}")

    # ── Pipeline summary for close (best-effort) ────────────────────────────
    blocked_pipeline_count = 0
    try:
        from umh.substrate.pipeline_execution import get_pipeline_summary

        pipe_summary = get_pipeline_summary()
        blocked_pipeline_count = pipe_summary.get("waiting_on_operator", 0)
    except Exception:  # noqa: BLE001
        pass

    # ── Live session count for close (v4, best-effort) ────────────────────
    active_live_sessions = 0
    try:
        from umh.substrate.live_sessions import get_live_session_summary

        ls_summary = get_live_session_summary()
        active_live_sessions = ls_summary.get("total_active", 0)
    except Exception:  # noqa: BLE001
        pass

    # ── Local control mode for close (v4, best-effort) ─────────────────────
    local_control_mode = "passive"
    try:
        from umh.substrate.local_control import LocalControlStore

        local_control_mode = LocalControlStore.default().get_mode().value
    except Exception:  # noqa: BLE001
        pass

    # ── Station presence mode for close (v5, best-effort) ──────────────────
    station_presence_mode = "away"
    try:
        from umh.substrate.station_presence import get_station_presence

        sp = get_station_presence()
        station_presence_mode = sp.mode.value
    except Exception:  # noqa: BLE001
        pass

    # ── Build response ────────────────────────────────────────────────────────
    response: dict = {
        "status": "ok",
        "day_session_id": current.day_session_id,
        "ritual_id": ritual_id,
        "summary": {
            "completed_today": list(completed_today),
            "unresolved": list(unresolved),
            "overnight_tasks": list(overnight_tasks),
            "continuity_notes": continuity_notes,
            "day_mode": day_mode.value,
            "active_workspace": current.active_workspace,
            "node_preference": current.node_preference,
        },
        "closed_at": now,
        "overnight_queue_count": len(overnight_tasks) if overnight_tasks else 0,
        "blocked_count": blocked_pipeline_count,
        # v4 extensions (additive)
        "active_live_sessions": active_live_sessions,
        "local_control_mode": local_control_mode,
        # v5 extensions (additive)
        "station_presence_mode": station_presence_mode,
        "live_session_count": active_live_sessions,
    }
    if overnight_completed:
        response["overnight_tasks_executed"] = overnight_completed
    if overnight_queue_prep:
        response["overnight_queue_prep"] = overnight_queue_prep
    # v6 extensions (node health + scene)
    if node_health_close:
        response["node_health"] = node_health_close
    if close_scene:
        response["active_scene"] = close_scene
    if ritual_warning:
        response["ritual_warning"] = ritual_warning
    return response


# ─── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    "open_day",
    "close_day",
]
