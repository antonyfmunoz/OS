"""Lifecycle behaviors — real actions attached to session hooks.

First layer: lightweight artifacts logged to stderr and workstation_log.
Second layer: continuity artifacts — on_close persists, on_open resumes.
Third layer: resume decisions — continuity drives session strategy.
No database writes. No external APIs. Fast and non-blocking.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from umh.runtime_loop.session_registry import SessionRecord

logger = logging.getLogger(__name__)


def _surface_count(session_id: str) -> int:
    try:
        from umh.runtime_loop.surface_registry import get_surface_registry
        return len(get_surface_registry().get_surfaces(session_id))
    except Exception:
        return 0


_resume_contexts: dict[str, dict[str, Any]] = {}


def _stash_resume_context(
    session_id: str, prev: dict[str, Any], decision: dict[str, Any]
) -> None:
    _resume_contexts[session_id] = {
        "previous_session": prev,
        "resume_decision": decision,
    }


def get_resume_context(session_id: str) -> dict[str, Any] | None:
    """Retrieve stashed resume context for a session. Used by context builders."""
    return _resume_contexts.get(session_id)


def _save_continuity(channel_id: str, artifact: dict[str, Any]) -> None:
    try:
        from umh.runtime_loop.continuity_store import get_continuity_store
        get_continuity_store().save(channel_id, artifact)
    except Exception:
        pass


def _load_continuity(channel_id: str) -> dict[str, Any] | None:
    try:
        from umh.runtime_loop.continuity_store import get_continuity_store
        return get_continuity_store().load(channel_id)
    except Exception:
        return None


RESUME_THRESHOLD_S = 300.0


def _make_resume_decision(prev: dict[str, Any], now: float) -> dict[str, Any]:
    """Determine resume vs fresh strategy based on idle gap."""
    ended_at = prev.get("ended_at", 0.0)
    idle_gap = round(now - ended_at, 1) if ended_at else 0.0
    prev_duration = prev.get("duration_s", 0.0)
    last_mode = prev.get("mode", "unknown")

    if idle_gap < RESUME_THRESHOLD_S:
        strategy = "resume"
        reason = f"idle gap {idle_gap:.0f}s < {RESUME_THRESHOLD_S:.0f}s threshold"
    else:
        strategy = "fresh"
        reason = f"idle gap {idle_gap:.0f}s >= {RESUME_THRESHOLD_S:.0f}s threshold"

    return {
        "strategy": strategy,
        "reason": reason,
        "prev_duration_s": prev_duration,
        "idle_gap_s": idle_gap,
        "last_mode": last_mode,
        "previous_session_id": prev.get("session_id", ""),
    }


def _log_event(event: str, payload: dict[str, Any]) -> None:
    try:
        from umh.substrate.workstation_log import log_event
        log_event(event, payload, to_stderr=False)
    except Exception:
        pass
    print(f"[lifecycle] {event}: {payload}", file=sys.stderr)


def on_open(session: "SessionRecord") -> None:
    """Build session-start artifact, evaluate resume decision, and log."""
    now = time.time()
    artifact: dict[str, Any] = {
        "session_id": session.session_id,
        "mode": session.mode,
        "node": session.node,
        "transport": session.transport,
        "started_at": session.created_ts,
    }

    prev = _load_continuity(session.channel_id)
    if prev:
        decision = _make_resume_decision(prev, now)
        artifact["previous_session"] = prev
        artifact["resume_decision"] = decision
        _log_event("resume_decision", {
            "session_id": session.session_id,
            "channel_id": session.channel_id,
            **decision,
        })
        _stash_resume_context(session.session_id, prev, decision)

    _log_event("session_opened", artifact)
    logger.info("session_opened: %s mode=%s node=%s", session.session_id, session.mode, session.node)


def on_close(session: "SessionRecord") -> None:
    """Build session-closed artifact, persist for continuity, and log."""
    now = time.time()
    opened = session.last_opened_ts or session.created_ts
    artifact = {
        "session_id": session.session_id,
        "mode": session.mode,
        "node": session.node,
        "duration_s": round(now - opened, 1),
        "last_activity_ts": session.last_activity_ts,
        "surface_count": _surface_count(session.session_id),
        "ended_at": now,
    }
    _save_continuity(session.channel_id, artifact)
    _log_event("session_closed", artifact)
    logger.info(
        "session_closed: %s duration=%.1fs surfaces=%d",
        session.session_id,
        artifact["duration_s"],
        artifact["surface_count"],
    )


def install() -> None:
    """Register behaviors with lifecycle hooks. Idempotent."""
    from umh.runtime_loop.lifecycle_hooks import register_hook
    register_hook("on_open", on_open)
    register_hook("on_close", on_close)
