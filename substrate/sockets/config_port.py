"""
Config port — substrate-layer abstraction for runtime config access.

Any substrate code that needs config values calls these functions.
The config store registers itself at startup.

Usage:
    from substrate.sockets.config_port import get_config, set_config
    ai_name = get_config("ai_name")
    set_config("ai_name", "ARIA", layer="system")
"""

from __future__ import annotations

from typing import Any, Callable, Optional

_get_fn: Optional[Callable[..., Any]] = None
_set_fn: Optional[Callable[..., None]] = None
_get_all_fn: Optional[Callable[[], dict[str, Any]]] = None
_on_change_fn: Optional[Callable[..., Callable[[], None]]] = None


def register_config_store(
    get_fn: Callable[..., Any],
    set_fn: Callable[..., None],
    get_all_fn: Callable[[], dict[str, Any]],
    on_change_fn: Optional[Callable[..., Callable[[], None]]] = None,
) -> None:
    """Register the concrete config store functions."""
    global _get_fn, _set_fn, _get_all_fn, _on_change_fn
    _get_fn = get_fn
    _set_fn = set_fn
    _get_all_fn = get_all_fn
    _on_change_fn = on_change_fn


def get_config(key: str, default: Any = None) -> Any:
    """Get a resolved config value. Falls back to env var, then default."""
    if _get_fn:
        val = _get_fn(key, default)
        if val is not None:
            return val
    import os
    env = os.environ.get(key.upper())
    if env:
        return env
    return default


def set_config(key: str, value: Any, layer: str = "system") -> None:
    """Set a config value in the specified layer."""
    if _set_fn:
        _set_fn(key, value, layer=layer)


def get_all_config() -> dict[str, Any]:
    """Get the fully resolved config dict."""
    if _get_all_fn:
        return _get_all_fn()
    return {}


def on_config_change(
    listener: Callable[[str, Any, str], None],
) -> Optional[Callable[[], None]]:
    """Register a change listener. Returns unsubscribe, or None if no store."""
    if _on_change_fn:
        return _on_change_fn(listener)
    return None
