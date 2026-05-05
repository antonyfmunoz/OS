"""
umh.substrate.live_session — Transport-agnostic live interaction session
state model for persistent conversational sessions.

Pure bookkeeping for live sessions — no Discord, Meet, STT, TTS, or UI logic.
All state transitions expressed as SET/REMOVE mutations for replay safety.

Public API:
    LiveSession                 — frozen session record
    compute_live_session_id     — deterministic session ID
    build_live_session          — construct a new session
    load_live_session           — reconstruct from state
    list_active_live_sessions   — enumerate active session IDs
    list_recent_live_sessions   — enumerate recent session IDs (bounded)
    build_live_session_mutations — persistence mutations for new session
    end_live_session            — transition to ended
    interrupt_live_session      — transition to interrupted
    touch_live_session          — update last_active_at

Separation note:
    This module is harness-only. No Discord, Meet, STT, TTS, or UI code.
    It models a transport-agnostic live conversational session that can
    be backed by any future streaming transport.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_LOG_PREFIX = "[substrate.live_session]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# State key helpers
# ---------------------------------------------------------------------------
_SESSION_KEY_PREFIX = "live_session."
_ACTIVE_INDEX_PREFIX = "live_session_index.active."
_RECENT_INDEX_PREFIX = "live_session_index.recent."


def _session_key(session_id: str) -> str:
    return f"{_SESSION_KEY_PREFIX}{session_id}"


def _active_key(session_id: str) -> str:
    return f"{_ACTIVE_INDEX_PREFIX}{session_id}"


def _recent_key(session_id: str) -> str:
    return f"{_RECENT_INDEX_PREFIX}{session_id}"


# ---------------------------------------------------------------------------
# LiveSession — frozen session record
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LiveSession:
    """Immutable record of a transport-agnostic live interaction session.

    Fields:
        session_id:          deterministic session identifier
        runtime_session_id:  upstream runtime session reference
        mode:                session mode (e.g. voice, text, mixed)
        transport:           source transport (discord_voice, meet, local_mic)
        operator_id:         who initiated
        started_at:          ISO timestamp of creation
        last_active_at:      ISO timestamp of last activity
        ended_at:            ISO timestamp when session ended
        status:              active | interrupted | ended
        current_turn_id:     ID of the currently open turn (empty if none)
        turn_count:          total turns in this session
        interruption_count:  total interruptions in this session
        open_execution_count: executions dispatched but not yet resolved
        last_artifact_id:    most recent artifact produced
        correlation_id:      links session to upstream event chain
    """

    session_id: str
    runtime_session_id: str
    mode: str
    transport: str
    operator_id: str
    started_at: str
    last_active_at: str = ""
    ended_at: str = ""
    status: str = "active"
    current_turn_id: str = ""
    turn_count: int = 0
    interruption_count: int = 0
    open_execution_count: int = 0
    last_artifact_id: str = ""
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if not self.started_at:
            object.__setattr__(self, "started_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "correlation_id": self.correlation_id,
            "current_turn_id": self.current_turn_id,
            "ended_at": self.ended_at,
            "interruption_count": self.interruption_count,
            "last_active_at": self.last_active_at,
            "last_artifact_id": self.last_artifact_id,
            "mode": self.mode,
            "open_execution_count": self.open_execution_count,
            "operator_id": self.operator_id,
            "runtime_session_id": self.runtime_session_id,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "status": self.status,
            "transport": self.transport,
            "turn_count": self.turn_count,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> LiveSession:
        """Reconstruct from plain dict with backward-safe defaults."""
        return LiveSession(
            session_id=str(d.get("session_id", "")),
            runtime_session_id=str(d.get("runtime_session_id", "")),
            mode=str(d.get("mode", "")),
            transport=str(d.get("transport", "")),
            operator_id=str(d.get("operator_id", "")),
            started_at=str(d.get("started_at", "")),
            last_active_at=str(d.get("last_active_at", "")),
            ended_at=str(d.get("ended_at", "")),
            status=str(d.get("status", "active")),
            current_turn_id=str(d.get("current_turn_id", "")),
            turn_count=int(d.get("turn_count", 0)),
            interruption_count=int(d.get("interruption_count", 0)),
            open_execution_count=int(d.get("open_execution_count", 0)),
            last_artifact_id=str(d.get("last_artifact_id", "")),
            correlation_id=str(d.get("correlation_id", "")),
        )

    def _replace(self, **overrides: Any) -> LiveSession:
        """Return a copy with field overrides."""
        d = self.to_dict()
        d.update(overrides)
        return LiveSession.from_dict(d)


# ---------------------------------------------------------------------------
# Deterministic ID
# ---------------------------------------------------------------------------


def compute_live_session_id(
    runtime_session_id: str,
    transport: str,
    operator_id: str,
) -> str:
    """Deterministic session ID: same inputs → same ID.

    Uses SHA-256 of canonical JSON. Prefix: ``lse_``.
    """
    canonical = json.dumps(
        {
            "operator_id": operator_id,
            "runtime_session_id": runtime_session_id,
            "transport": transport,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"lse_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_live_session(
    *,
    runtime_session_id: str,
    mode: str,
    transport: str,
    operator_id: str,
    started_at: str = "",
    correlation_id: str = "",
    session_id: str | None = None,
) -> LiveSession:
    """Construct a new LiveSession with deterministic ID."""
    ts = started_at or _utcnow()
    sid = session_id or compute_live_session_id(
        runtime_session_id, transport, operator_id
    )
    return LiveSession(
        session_id=sid,
        runtime_session_id=runtime_session_id,
        mode=mode,
        transport=transport,
        operator_id=operator_id,
        started_at=ts,
        last_active_at=ts,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Load / list helpers
# ---------------------------------------------------------------------------


def load_live_session(
    state: dict[str, Any],
    session_id: str,
) -> LiveSession | None:
    """Reconstruct a LiveSession from state, or None if missing."""
    raw = state.get(_session_key(session_id))
    if not isinstance(raw, dict):
        return None
    return LiveSession.from_dict(raw)


def list_active_live_sessions(
    state: dict[str, Any],
) -> tuple[str, ...]:
    """Return sorted tuple of active live session IDs."""
    ids = sorted(
        k[len(_ACTIVE_INDEX_PREFIX) :]
        for k in state
        if k.startswith(_ACTIVE_INDEX_PREFIX)
    )
    return tuple(ids)


def list_recent_live_sessions(
    state: dict[str, Any],
    limit: int = 20,
) -> tuple[str, ...]:
    """Return most recent live session IDs (bounded).

    Sorts by started_at descending from the recent index entries.
    """
    entries: list[tuple[str, str]] = []
    for k, v in state.items():
        if not k.startswith(_RECENT_INDEX_PREFIX):
            continue
        if not isinstance(v, dict):
            continue
        sid = k[len(_RECENT_INDEX_PREFIX) :]
        started = str(v.get("started_at", v.get("ended_at", "")))
        entries.append((started, sid))
    entries.sort(reverse=True)
    return tuple(sid for _, sid in entries[:limit])


# ---------------------------------------------------------------------------
# Mutation builders — SET / REMOVE only
# ---------------------------------------------------------------------------


def build_live_session_mutations(
    session: LiveSession,
) -> list[dict[str, Any]]:
    """Build mutations to persist a new live session.

    Writes:
        1. Session record: live_session.{session_id}
        2. Active index:   live_session_index.active.{session_id}
        3. Recent index:   live_session_index.recent.{session_id}
    """
    return [
        {
            "op": "SET",
            "key": _session_key(session.session_id),
            "value": session.to_dict(),
        },
        {
            "op": "SET",
            "key": _active_key(session.session_id),
            "value": {
                "operator_id": session.operator_id,
                "started_at": session.started_at,
                "transport": session.transport,
                "mode": session.mode,
                "correlation_id": session.correlation_id,
            },
        },
        {
            "op": "SET",
            "key": _recent_key(session.session_id),
            "value": {
                "operator_id": session.operator_id,
                "started_at": session.started_at,
                "transport": session.transport,
                "status": session.status,
            },
        },
    ]


# ---------------------------------------------------------------------------
# State transitions — return (updated_session, mutations)
# ---------------------------------------------------------------------------


def end_live_session(
    session: LiveSession,
    ended_at: str,
) -> tuple[LiveSession, list[dict[str, Any]]]:
    """Transition session to ended.

    Returns (updated_session, mutations).
    Removes active index, preserves recent index.
    """
    updated = session._replace(
        status="ended",
        ended_at=ended_at,
        current_turn_id="",
    )
    mutations: list[dict[str, Any]] = [
        {
            "op": "SET",
            "key": _session_key(session.session_id),
            "value": updated.to_dict(),
        },
        {"op": "REMOVE", "key": _active_key(session.session_id)},
        {
            "op": "SET",
            "key": _recent_key(session.session_id),
            "value": {
                "operator_id": session.operator_id,
                "started_at": session.started_at,
                "ended_at": ended_at,
                "transport": session.transport,
                "status": "ended",
            },
        },
    ]
    return updated, mutations


def interrupt_live_session(
    session: LiveSession,
    at: str,
) -> tuple[LiveSession, list[dict[str, Any]]]:
    """Transition session to interrupted.

    Returns (updated_session, mutations).
    Session remains in active index since it may be resumed.
    """
    updated = session._replace(
        status="interrupted",
        last_active_at=at,
        interruption_count=session.interruption_count + 1,
    )
    mutations: list[dict[str, Any]] = [
        {
            "op": "SET",
            "key": _session_key(session.session_id),
            "value": updated.to_dict(),
        },
        {
            "op": "SET",
            "key": _active_key(session.session_id),
            "value": {
                "operator_id": session.operator_id,
                "started_at": session.started_at,
                "transport": session.transport,
                "mode": session.mode,
                "status": "interrupted",
                "last_active_at": at,
                "correlation_id": session.correlation_id,
            },
        },
        {
            "op": "SET",
            "key": _recent_key(session.session_id),
            "value": {
                "operator_id": session.operator_id,
                "started_at": session.started_at,
                "transport": session.transport,
                "status": "interrupted",
            },
        },
    ]
    return updated, mutations


def touch_live_session(
    session: LiveSession,
    at: str,
) -> tuple[LiveSession, list[dict[str, Any]]]:
    """Update last_active_at without changing status.

    Returns (updated_session, mutations).
    """
    updated = session._replace(last_active_at=at)
    mutations: list[dict[str, Any]] = [
        {
            "op": "SET",
            "key": _session_key(session.session_id),
            "value": updated.to_dict(),
        },
    ]
    return updated, mutations
