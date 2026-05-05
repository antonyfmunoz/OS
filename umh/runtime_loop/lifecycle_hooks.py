"""Lifecycle hooks — extension points for session state transitions.

Hook functions are called when a session transitions between states:
  OPEN → on_open     (new session created)
  ACTIVE → on_active (session re-activated from idle)
  IDLE → on_idle     (session went idle)
  CLOSED → on_close  (session terminated)

All hooks are no-ops by default. Replace them to inject behavior.
Hook failures are logged and swallowed — they never break lifecycle.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from umh.runtime_loop.session_registry import SessionRecord

logger = logging.getLogger(__name__)

HookFn = Callable[["SessionRecord"], None]


def _noop(session: "SessionRecord") -> None:
    pass


_hooks: dict[str, HookFn] = {
    "on_open": _noop,
    "on_active": _noop,
    "on_idle": _noop,
    "on_close": _noop,
}


def register_hook(name: str, fn: HookFn) -> None:
    """Register a lifecycle hook by name.

    Raises KeyError if name is not a valid hook point.
    """
    if name not in _hooks:
        raise KeyError(f"Unknown hook: {name!r}. Valid: {sorted(_hooks)}")
    _hooks[name] = fn


def fire_hook(name: str, session: "SessionRecord") -> None:
    """Fire a lifecycle hook. Failures are logged, never raised."""
    fn = _hooks.get(name)
    if fn is None or fn is _noop:
        return
    try:
        fn(session)
    except Exception as exc:
        logger.warning(
            "lifecycle hook %s failed for session %s: %s",
            name,
            session.session_id,
            exc,
        )
        print(
            f"[lifecycle_hooks] {name} failed: {exc}",
            file=sys.stderr,
        )


def on_open(session: "SessionRecord") -> None:
    """Called when a new session is created."""
    fire_hook("on_open", session)


def on_active(session: "SessionRecord") -> None:
    """Called when a session re-activates from idle."""
    fire_hook("on_active", session)


def on_idle(session: "SessionRecord") -> None:
    """Called when a session transitions to idle."""
    fire_hook("on_idle", session)


def on_close(session: "SessionRecord") -> None:
    """Called when a session is closed."""
    fire_hook("on_close", session)


def reset_hooks() -> None:
    """Reset all hooks to no-op. Useful for testing."""
    for key in _hooks:
        _hooks[key] = _noop
