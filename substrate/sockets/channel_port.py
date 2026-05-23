"""
Channel port — substrate-layer abstraction for the channel router.

The transport layer registers its concrete get_channel_router() at startup.
Substrate code calls the thin wrapper here, never importing from transports.
"""

from typing import Any, Callable, Optional

_router_fn: Optional[Callable] = None


def register_channel_router(fn: Callable) -> None:
    """Register the concrete channel-router factory (e.g. get_channel_router)."""
    global _router_fn
    _router_fn = fn


def get_channel_router() -> Any:
    """Return the channel router, or None if no transport is registered."""
    if _router_fn:
        return _router_fn()
    return None
