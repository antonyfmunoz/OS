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

from eos_ai.substrate.operator_session import (
    OperatorDayMode,
    OperatorSession,
    OperatorSessionStore,
)
from eos_ai.substrate.rituals import RitualKind, RitualRegistry, RitualState


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
    workspace: Optional[str],
    node_preference: Optional[str],
    discord_channel_id: Optional[str],
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
        },
        "day_mode": day_mode.value,
        "active_workspace": resolved_workspace,
        "opened_at": now,
    }
    if ritual_warning:
        response["ritual_warning"] = ritual_warning
    return response


# ─── close_day ────────────────────────────────────────────────────────────────


def close_day(
    *,
    completed_today: list,
    unresolved: list,
    overnight_tasks: list,
    continuity_notes: Optional[str],
    resume_context: Optional[str],
    discord_channel_id: Optional[str],
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
    }
    if ritual_warning:
        response["ritual_warning"] = ritual_warning
    return response


# ─── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    "open_day",
    "close_day",
]
