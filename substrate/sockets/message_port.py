"""
Message port — substrate-layer abstraction for conversation persistence.

Transports register their message sink at startup.
Substrate code calls the thin wrapper here, never importing from transports.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

_sink_fn: Optional[Callable] = None


def register_message_sink(fn: Callable) -> None:
    """Register the concrete message persistence function."""
    global _sink_fn
    _sink_fn = fn


def save_message(msg: Any) -> None:
    """Persist a message via the registered sink, or no-op if none registered."""
    if _sink_fn:
        _sink_fn(msg)


def get_message_sink() -> Optional[Callable]:
    """Return the registered sink, or None."""
    return _sink_fn
