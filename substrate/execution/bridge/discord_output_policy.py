"""Display-name policy for Discord watcher output."""

from __future__ import annotations

_STRIP_PREFIXES = ("cc_", "session_", "watcher_", "bridge_")


def get_display_name(name: str) -> str:
    """Return a human-readable display name from a watcher key."""
    result = name
    for prefix in _STRIP_PREFIXES:
        if result.lower().startswith(prefix):
            result = result[len(prefix):]
            break
    return result.replace("_", " ").strip().title() or name
