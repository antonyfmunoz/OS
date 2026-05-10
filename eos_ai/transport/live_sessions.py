"""
Live sessions — real-time continuous interaction layer for the substrate.

Purpose
-------
This module supports real-time continuous sessions with one or more agent
roles. A live session is a synchronous interaction container that can be
attached to a day session, tasks, and pipelines. It tracks the lifecycle
of voice calls, meetings, Discord voice channels, Google Meet sessions,
and local interactive sessions.

Design rules (mirror the rest of substrate)
-------------------------------------------
- Additive only. Hot path (gateway/cognitive_loop/model_router/agent_runtime/
  primitives) is never imported.
- Bounded. Sessions are an explicit lifecycle (CREATED → ACTIVE → PAUSED →
  WAITING_ON_OPERATOR → ENDED/FAILED). Max 200 stored; oldest terminal
  sessions pruned first.
- Deterministic. State transitions are explicit function calls.
- Observable. LiveSessionStore is dual-layer (in-mem + substrate.storage)
  exactly like TaskStore. Bounded retention. Thread-safe. Singleton.
- Best-effort. Runtime methods catch and log; never raise into callers
  (except ValueError for not-found, which is documented).
- Reversible. Removing this file leaves the substrate exactly as it was.
"""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional


# ─── Constants ────────────────────────────────────────────────────────────────

_STORAGE_KEY = "live_sessions"
_MAX_SESSIONS = 200


def _log(msg: str) -> None:
    print(f"[substrate.live_sessions] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"lsess_{uuid.uuid4().hex[:12]}"


# ─── Enums ────────────────────────────────────────────────────────────────────


class LiveSessionState(str, Enum):
    """Bounded lifecycle of a live session.

    CREATED              — allocated but not yet active
    ACTIVE               — live interaction in progress
    PAUSED               — temporarily suspended (break, context switch)
    WAITING_ON_OPERATOR  — session needs operator input to proceed
    ENDED                — explicitly closed; terminal
    FAILED               — error during session; terminal
    """

    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    WAITING_ON_OPERATOR = "waiting_on_operator"
    ENDED = "ended"
    FAILED = "failed"


class LiveSessionType(str, Enum):
    """Transport or context for the live session."""

    VOICE = "voice"
    MEETING = "meeting"
    DISCORD_VOICE = "discord_voice"
    GOOGLE_MEET = "google_meet"
    LOCAL = "local"


# ─── Dataclass ────────────────────────────────────────────────────────────────


@dataclass
class LiveSession:
    """A bounded real-time interaction container.

    Tracks one continuous session with agent roles, attached resources,
    and lifecycle state. Persisted via LiveSessionStore.
    """

    live_session_id: str
    title: str
    session_type: LiveSessionType
    state: LiveSessionState = LiveSessionState.CREATED
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)
    primary_agent_role: str = "general"
    participant_agent_roles: list[str] = field(default_factory=list)
    attached_day_session_id: Optional[str] = None
    attached_task_ids: list[str] = field(default_factory=list)
    attached_pipeline_ids: list[str] = field(default_factory=list)
    summary: Optional[str] = None
    last_event: Optional[str] = None

    # — factory ──────────────────────────────────────────────────────────────

    @classmethod
    def new(
        cls,
        title: str,
        session_type: LiveSessionType,
        *,
        primary_agent_role: str = "general",
        participant_agent_roles: Optional[list[str]] = None,
        attached_day_session_id: Optional[str] = None,
    ) -> "LiveSession":
        """Create a new LiveSession with generated ID and current timestamps."""
        now = _utcnow()
        return cls(
            live_session_id=_new_id(),
            title=title,
            session_type=session_type,
            state=LiveSessionState.CREATED,
            created_at=now,
            updated_at=now,
            primary_agent_role=primary_agent_role,
            participant_agent_roles=list(participant_agent_roles or []),
            attached_day_session_id=attached_day_session_id,
        )

    # — helpers ──────────────────────────────────────────────────────────────

    def is_terminal(self) -> bool:
        """Return True if session is in a terminal state (ENDED or FAILED)."""
        return self.state in (LiveSessionState.ENDED, LiveSessionState.FAILED)

    # — serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Return a JSON-safe dict. Enums serialized as their .value."""
        return {
            "live_session_id": self.live_session_id,
            "title": self.title,
            "session_type": self.session_type.value,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "primary_agent_role": self.primary_agent_role,
            "participant_agent_roles": list(self.participant_agent_roles),
            "attached_day_session_id": self.attached_day_session_id,
            "attached_task_ids": list(self.attached_task_ids),
            "attached_pipeline_ids": list(self.attached_pipeline_ids),
            "summary": self.summary,
            "last_event": self.last_event,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LiveSession":
        """Deserialize from a dict, reconstructing enums and guarding list fields."""
        try:
            state = LiveSessionState(d.get("state", "created"))
        except Exception:
            state = LiveSessionState.CREATED

        try:
            session_type = LiveSessionType(d.get("session_type", "local"))
        except Exception:
            session_type = LiveSessionType.LOCAL

        raw_participants = d.get("participant_agent_roles")
        participant_agent_roles: list[str] = (
            list(raw_participants) if isinstance(raw_participants, list) else []
        )

        raw_task_ids = d.get("attached_task_ids")
        attached_task_ids: list[str] = (
            list(raw_task_ids) if isinstance(raw_task_ids, list) else []
        )

        raw_pipeline_ids = d.get("attached_pipeline_ids")
        attached_pipeline_ids: list[str] = (
            list(raw_pipeline_ids) if isinstance(raw_pipeline_ids, list) else []
        )

        return cls(
            live_session_id=str(d.get("live_session_id") or _new_id()),
            title=str(d.get("title", "")),
            session_type=session_type,
            state=state,
            created_at=str(d.get("created_at") or _utcnow()),
            updated_at=str(d.get("updated_at") or _utcnow()),
            primary_agent_role=str(d.get("primary_agent_role", "general")),
            participant_agent_roles=participant_agent_roles,
            attached_day_session_id=d.get("attached_day_session_id"),
            attached_task_ids=attached_task_ids,
            attached_pipeline_ids=attached_pipeline_ids,
            summary=d.get("summary"),
            last_event=d.get("last_event"),
        )


# ─── Store ────────────────────────────────────────────────────────────────────


class LiveSessionStore:
    """Durable, bounded, thread-safe store for LiveSession records.

    Dual-layer: in-memory dict + substrate.storage (Neon-backed, JSON fallback).
    Best-effort persistence — flush failures log and the in-memory state
    remains correct.

    Keyed by live_session_id. Bounded — prunes oldest terminal sessions
    when count exceeds _MAX_SESSIONS.
    """

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, LiveSession] = {}
        self._loaded = False
        if autoload:
            self._load()

    # — persistence ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from eos_ai.substrate.storage import get_storage

                raw = get_storage().get(_STORAGE_KEY, default=None)
            except Exception as e:  # noqa: BLE001
                _log(f"load failed ({e}); starting empty")
                raw = None
            if isinstance(raw, dict):
                for key, val in raw.items():
                    if isinstance(val, dict):
                        try:
                            self._sessions[key] = LiveSession.from_dict(val)
                        except Exception as e:  # noqa: BLE001
                            _log(f"skip bad session {key}: {e}")
            self._loaded = True

    def _flush(self) -> None:
        """Persist in-memory state to substrate storage. Caller holds lock."""
        try:
            from eos_ai.substrate.storage import get_storage

            payload = {sid: s.to_dict() for sid, s in self._sessions.items()}
            get_storage().put(_STORAGE_KEY, payload)
        except Exception as e:  # noqa: BLE001
            _log(f"flush failed: {e}")

    def _prune_if_needed(self) -> None:
        """Remove oldest ENDED/FAILED sessions if store exceeds _MAX_SESSIONS.

        Caller holds lock.
        """
        if len(self._sessions) <= _MAX_SESSIONS:
            return
        # Collect terminal sessions sorted by created_at ascending (oldest first)
        terminal = [
            s
            for s in self._sessions.values()
            if s.state in (LiveSessionState.ENDED, LiveSessionState.FAILED)
        ]
        terminal.sort(key=lambda s: s.created_at)
        to_remove = len(self._sessions) - _MAX_SESSIONS
        for session in terminal[:to_remove]:
            self._sessions.pop(session.live_session_id, None)

    # — public api ───────────────────────────────────────────────────────────

    def get(self, live_session_id: str) -> Optional[LiveSession]:
        """Return a session by ID, or None."""
        with self._lock:
            return self._sessions.get(live_session_id)

    def put(self, session: LiveSession) -> None:
        """Insert or update a session. Prunes if needed, then flushes to storage."""
        with self._lock:
            session.updated_at = _utcnow()
            self._sessions[session.live_session_id] = session
            self._prune_if_needed()
            self._flush()

    def all(self) -> list[LiveSession]:
        """Return all sessions, sorted by created_at descending (newest first)."""
        with self._lock:
            sessions = list(self._sessions.values())
            sessions.sort(key=lambda s: s.created_at, reverse=True)
            return sessions

    def active(self) -> list[LiveSession]:
        """Return non-terminal sessions (CREATED, ACTIVE, PAUSED, WAITING_ON_OPERATOR)."""
        with self._lock:
            return [s for s in self._sessions.values() if not s.is_terminal()]

    def by_state(self, state: LiveSessionState) -> list[LiveSession]:
        """Return sessions matching the given state."""
        with self._lock:
            return [s for s in self._sessions.values() if s.state == state]

    def by_day_session(self, day_session_id: str) -> list[LiveSession]:
        """Return sessions attached to a specific day session."""
        with self._lock:
            return [
                s
                for s in self._sessions.values()
                if s.attached_day_session_id == day_session_id
            ]

    # — singleton ────────────────────────────────────────────────────────────

    _default: Optional["LiveSessionStore"] = None
    _default_lock = threading.Lock()

    @classmethod
    def default(cls) -> "LiveSessionStore":
        """Return the process-level singleton, creating it on first call."""
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        """Tear down the singleton so the next call to default() creates a fresh instance."""
        with cls._default_lock:
            cls._default = None


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _get_current_day_session_id() -> Optional[str]:
    """Best-effort: pull the current day session ID from OperatorSession.

    Returns None if no day session is open or import fails. Never raises.
    """
    try:
        from eos_ai.substrate.operator_session import OperatorSessionStore

        session = OperatorSessionStore.default().get()
        if session is not None and session.is_day_open:
            return session.day_session_id
    except Exception:  # noqa: BLE001
        pass
    return None


def _get_and_validate(live_session_id: str) -> LiveSession:
    """Fetch a session by ID or raise ValueError."""
    session = LiveSessionStore.default().get(live_session_id)
    if session is None:
        raise ValueError(f"live session {live_session_id!r} not found")
    return session


# ─── Lifecycle functions ──────────────────────────────────────────────────────


def create_live_session(
    title: str,
    session_type: LiveSessionType,
    *,
    primary_agent_role: str = "general",
    participant_agent_roles: Optional[list[str]] = None,
    day_session_id: Optional[str] = None,
) -> LiveSession:
    """Create and persist a new live session.

    If day_session_id is not provided, attempts to auto-attach from the
    current OperatorSession.
    """
    resolved_day_session_id = day_session_id or _get_current_day_session_id()

    session = LiveSession.new(
        title=title,
        session_type=session_type,
        primary_agent_role=primary_agent_role,
        participant_agent_roles=participant_agent_roles,
        attached_day_session_id=resolved_day_session_id,
    )

    LiveSessionStore.default().put(session)
    _log(f"created live session {session.live_session_id} ({title!r})")
    return session


def start_live_session(live_session_id: str) -> LiveSession:
    """Transition session CREATED -> ACTIVE.

    Raises ValueError if session not found.
    Logs warning if not in CREATED state (but still transitions for recovery).
    """
    session = _get_and_validate(live_session_id)

    if session.state != LiveSessionState.CREATED:
        _log(
            f"start_live_session: session {live_session_id} in state "
            f"{session.state.value}, not CREATED — transitioning anyway for recovery"
        )

    session.state = LiveSessionState.ACTIVE
    session.last_event = "started"
    LiveSessionStore.default().put(session)
    _log(f"started live session {live_session_id}")
    return session


def pause_live_session(live_session_id: str) -> LiveSession:
    """Transition session ACTIVE -> PAUSED.

    Raises ValueError if session not found.
    """
    session = _get_and_validate(live_session_id)

    if session.state != LiveSessionState.ACTIVE:
        _log(
            f"pause_live_session: session {live_session_id} in state "
            f"{session.state.value}, not ACTIVE — transitioning anyway"
        )

    session.state = LiveSessionState.PAUSED
    session.last_event = "paused"
    LiveSessionStore.default().put(session)
    _log(f"paused live session {live_session_id}")
    return session


def resume_live_session(live_session_id: str) -> LiveSession:
    """Transition session PAUSED -> ACTIVE.

    Raises ValueError if session not found.
    """
    session = _get_and_validate(live_session_id)

    if session.state != LiveSessionState.PAUSED:
        _log(
            f"resume_live_session: session {live_session_id} in state "
            f"{session.state.value}, not PAUSED — transitioning anyway"
        )

    session.state = LiveSessionState.ACTIVE
    session.last_event = "resumed"
    LiveSessionStore.default().put(session)
    _log(f"resumed live session {live_session_id}")
    return session


def end_live_session(
    live_session_id: str,
    *,
    summary: Optional[str] = None,
) -> LiveSession:
    """Transition session to ENDED. Sets summary if provided.

    Raises ValueError if session not found.
    """
    session = _get_and_validate(live_session_id)

    session.state = LiveSessionState.ENDED
    session.last_event = "ended"
    if summary is not None:
        session.summary = summary
    LiveSessionStore.default().put(session)
    _log(f"ended live session {live_session_id}")
    return session


def fail_live_session(
    live_session_id: str,
    *,
    error: Optional[str] = None,
) -> LiveSession:
    """Transition session to FAILED. Sets last_event with error info.

    Raises ValueError if session not found.
    """
    session = _get_and_validate(live_session_id)

    session.state = LiveSessionState.FAILED
    session.last_event = f"failed: {error}" if error else "failed"
    LiveSessionStore.default().put(session)
    _log(f"failed live session {live_session_id}: {error}")
    return session


# ─── Attachment functions ─────────────────────────────────────────────────────


def attach_task_to_live_session(live_session_id: str, task_id: str) -> LiveSession:
    """Attach a task to a live session. Deduplicates.

    Raises ValueError if session not found.
    """
    session = _get_and_validate(live_session_id)

    if task_id not in session.attached_task_ids:
        session.attached_task_ids.append(task_id)
        session.last_event = f"attached task {task_id}"
        LiveSessionStore.default().put(session)
        _log(f"attached task {task_id} to live session {live_session_id}")
    return session


def attach_pipeline_to_live_session(
    live_session_id: str, pipeline_id: str
) -> LiveSession:
    """Attach a pipeline to a live session. Deduplicates.

    Raises ValueError if session not found.
    """
    session = _get_and_validate(live_session_id)

    if pipeline_id not in session.attached_pipeline_ids:
        session.attached_pipeline_ids.append(pipeline_id)
        session.last_event = f"attached pipeline {pipeline_id}"
        LiveSessionStore.default().put(session)
        _log(f"attached pipeline {pipeline_id} to live session {live_session_id}")
    return session


def detach_task_from_live_session(live_session_id: str, task_id: str) -> LiveSession:
    """Detach a task from a live session.

    Raises ValueError if session not found.
    No error if task_id not attached (idempotent).
    """
    session = _get_and_validate(live_session_id)

    if task_id in session.attached_task_ids:
        session.attached_task_ids.remove(task_id)
        session.last_event = f"detached task {task_id}"
        LiveSessionStore.default().put(session)
        _log(f"detached task {task_id} from live session {live_session_id}")
    return session


def detach_pipeline_from_live_session(
    live_session_id: str, pipeline_id: str
) -> LiveSession:
    """Detach a pipeline from a live session.

    Raises ValueError if session not found.
    No error if pipeline_id not attached (idempotent).
    """
    session = _get_and_validate(live_session_id)

    if pipeline_id in session.attached_pipeline_ids:
        session.attached_pipeline_ids.remove(pipeline_id)
        session.last_event = f"detached pipeline {pipeline_id}"
        LiveSessionStore.default().put(session)
        _log(f"detached pipeline {pipeline_id} from live session {live_session_id}")
    return session


# ─── Summary helper ───────────────────────────────────────────────────────────


def get_live_session_summary() -> dict:
    """Get summary suitable for open_day/close_day integration.

    Returns:
        {
            "active_live_sessions": int,
            "paused_live_sessions": int,
            "waiting_live_sessions": int,
            "total_active": int,  # non-terminal
            "recent_ended": int,  # ended in last 24h
        }
    """
    store = LiveSessionStore.default()
    all_sessions = store.all()

    active_count = 0
    paused_count = 0
    waiting_count = 0
    total_non_terminal = 0
    recent_ended = 0

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    for s in all_sessions:
        if not s.is_terminal():
            total_non_terminal += 1
        if s.state == LiveSessionState.ACTIVE:
            active_count += 1
        elif s.state == LiveSessionState.PAUSED:
            paused_count += 1
        elif s.state == LiveSessionState.WAITING_ON_OPERATOR:
            waiting_count += 1
        elif s.state == LiveSessionState.ENDED and s.updated_at >= cutoff:
            recent_ended += 1

    return {
        "active_live_sessions": active_count,
        "paused_live_sessions": paused_count,
        "waiting_live_sessions": waiting_count,
        "total_active": total_non_terminal,
        "recent_ended": recent_ended,
    }


# ─── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    "LiveSessionState",
    "LiveSessionType",
    "LiveSession",
    "LiveSessionStore",
    "create_live_session",
    "start_live_session",
    "pause_live_session",
    "resume_live_session",
    "end_live_session",
    "fail_live_session",
    "attach_task_to_live_session",
    "attach_pipeline_to_live_session",
    "detach_task_from_live_session",
    "detach_pipeline_from_live_session",
    "get_live_session_summary",
]
