"""
SessionStore — persistent in-process session registry.

Ensures that the same session_id always returns the same SessionRuntime
instance, so messages accumulate across turns and compaction can trigger.

Thread-safe. No external storage — sessions live in process memory.
"""

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.runtime_engine.session_runtime import SessionRuntime

_lock = threading.Lock()
_SESSIONS: dict[str, "SessionRuntime"] = {}


def get_session(session_id: str, ctx: object) -> "SessionRuntime":
    """Return existing SessionRuntime for session_id, or create one.

    The ctx argument is only used when creating a new session — existing
    sessions retain whatever ctx they were created with.
    """
    with _lock:
        session = _SESSIONS.get(session_id)
        if session is not None:
            return session

        from umh.runtime_engine.session_runtime import SessionRuntime

        session = SessionRuntime(ctx, session_id=session_id)
        _SESSIONS[session_id] = session
        return session


def clear_session(session_id: str) -> bool:
    """Remove a session from the store. Returns True if it existed."""
    with _lock:
        return _SESSIONS.pop(session_id, None) is not None


def clear_all_sessions() -> int:
    """Remove all sessions. Returns count cleared."""
    with _lock:
        count = len(_SESSIONS)
        _SESSIONS.clear()
        return count


def active_session_count() -> int:
    """Return the number of active sessions."""
    with _lock:
        return len(_SESSIONS)
