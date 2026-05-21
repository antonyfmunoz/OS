"""
Runtime session — operator-facing runtime continuity primitives.

Tracks lightweight session state for operator continuity across interactions.
This is NOT the deep orchestration state (that lives in OperatorSession / event spine).
This is the operator-facing runtime view: "when did this session start, what mode
is it in, how many tasks are open, when was the last summary sent?"

Design rules (substrate conventions):
- Additive only. No hot-path imports.
- SET-only style updates (no list mutations, no scans).
- Deterministic keys.
- Backward-compatible: if no session exists, system still works.
- Thread-safe via lock.
- Best-effort persistence.
"""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from umh.substrate.runtime_mode import RuntimeMode, resolve_mode

_LOG_PREFIX = "[substrate.runtime_session]"
_STORAGE_KEY = "runtime_session"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_id() -> str:
    return f"rs_{uuid.uuid4().hex[:12]}"


# ─── Dataclass ──────────────────────────────────────────────────────────────


@dataclass
class RuntimeSessionState:
    """Operator-facing runtime session record.

    One active at a time. Lightweight — not the full orchestration session.
    """

    session_id: str
    started_at: str
    last_active_at: str
    active_mode: RuntimeMode = RuntimeMode.ACTIVE
    active_operator_transport: str = "discord"
    open_task_count: int = 0
    last_summary_at: Optional[str] = None
    ended_at: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """True if session has not been ended."""
        return self.ended_at is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "last_active_at": self.last_active_at,
            "active_mode": self.active_mode.value,
            "active_operator_transport": self.active_operator_transport,
            "open_task_count": self.open_task_count,
            "last_summary_at": self.last_summary_at,
            "ended_at": self.ended_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RuntimeSessionState:
        return cls(
            session_id=str(d.get("session_id") or _session_id()),
            started_at=str(d.get("started_at") or _utcnow()),
            last_active_at=str(d.get("last_active_at") or _utcnow()),
            active_mode=resolve_mode(d.get("active_mode")),
            active_operator_transport=str(
                d.get("active_operator_transport", "discord")
            ),
            open_task_count=int(d.get("open_task_count", 0)),
            last_summary_at=d.get("last_summary_at"),
            ended_at=d.get("ended_at"),
            metadata=dict(d.get("metadata") or {}),
        )


# ─── Public API (pure functions that return new/updated state) ──────────────


def start_runtime_session(
    *,
    mode: RuntimeMode = RuntimeMode.ACTIVE,
    transport: str = "discord",
) -> RuntimeSessionState:
    """Create a new runtime session."""
    now = _utcnow()
    session = RuntimeSessionState(
        session_id=_session_id(),
        started_at=now,
        last_active_at=now,
        active_mode=mode,
        active_operator_transport=transport,
    )
    _log(f"started: id={session.session_id} mode={mode.value} transport={transport}")
    return session


def touch_runtime_session(
    session: RuntimeSessionState,
    *,
    open_task_count: int | None = None,
) -> RuntimeSessionState:
    """Update last_active_at and optionally open_task_count.

    Returns the same object (mutated in place for simplicity; caller holds lock).
    """
    session.last_active_at = _utcnow()
    if open_task_count is not None:
        session.open_task_count = open_task_count
    return session


def end_runtime_session(session: RuntimeSessionState) -> RuntimeSessionState:
    """Mark a session as ended."""
    session.ended_at = _utcnow()
    session.last_active_at = session.ended_at
    _log(f"ended: id={session.session_id}")
    return session


def record_summary_sent(session: RuntimeSessionState) -> RuntimeSessionState:
    """Record that a summary was sent to the operator."""
    session.last_summary_at = _utcnow()
    session.last_active_at = session.last_summary_at
    return session


# ─── Store (singleton, thread-safe) ─────────────────────────────────────────


class RuntimeSessionStore:
    """Thread-safe store for one RuntimeSessionState.

    Holds at most one active session. Best-effort persistence via
    substrate storage.
    """

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._session: Optional[RuntimeSessionState] = None
        self._loaded = False
        if autoload:
            self._load()

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from umh.substrate.storage import get_storage

                raw = get_storage().get(_STORAGE_KEY, default=None)
            except Exception as e:  # noqa: BLE001
                _log(f"load failed ({e}); starting empty")
                raw = None
            if isinstance(raw, dict):
                try:
                    self._session = RuntimeSessionState.from_dict(raw)
                except Exception as e:  # noqa: BLE001
                    _log(f"deserialize failed ({e}); starting empty")
                    self._session = None
            self._loaded = True

    def _flush(self) -> None:
        try:
            from umh.substrate.storage import get_storage

            payload = self._session.to_dict() if self._session is not None else None
            get_storage().put(_STORAGE_KEY, payload)
        except Exception as e:  # noqa: BLE001
            _log(f"flush failed: {e}")

    def get(self) -> Optional[RuntimeSessionState]:
        """Return the current session, or None if none exists."""
        with self._lock:
            return self._session

    def put(self, session: RuntimeSessionState) -> None:
        """Persist a session. Replaces any existing session."""
        with self._lock:
            self._session = session
            self._flush()

    def start(
        self,
        *,
        mode: RuntimeMode = RuntimeMode.ACTIVE,
        transport: str = "discord",
    ) -> RuntimeSessionState:
        """Create and persist a new runtime session."""
        session = start_runtime_session(mode=mode, transport=transport)
        self.put(session)
        return session

    def touch(
        self, *, open_task_count: int | None = None
    ) -> Optional[RuntimeSessionState]:
        """Touch the current session. Returns None if no session exists."""
        with self._lock:
            if self._session is None:
                return None
            touch_runtime_session(self._session, open_task_count=open_task_count)
            self._flush()
            return self._session

    def end(self) -> Optional[RuntimeSessionState]:
        """End the current session. Returns None if no session exists."""
        with self._lock:
            if self._session is None:
                return None
            end_runtime_session(self._session)
            self._flush()
            return self._session

    # ── singleton ───────────────────────────────────────────────────────────

    _default: Optional["RuntimeSessionStore"] = None
    _default_lock = threading.Lock()

    @classmethod
    def default(cls) -> "RuntimeSessionStore":
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default

    @classmethod
    def reset_for_tests(cls) -> None:
        with cls._default_lock:
            cls._default = None


__all__ = [
    "RuntimeSessionState",
    "RuntimeSessionStore",
    "start_runtime_session",
    "touch_runtime_session",
    "end_runtime_session",
    "record_summary_sent",
]
