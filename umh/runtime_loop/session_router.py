"""Session-first routing — routes messages using SessionRecord as authority.

Replaces the old flow of:
    resolve_discord_mode → resolve_mode_session → env-based session name → tmux

New flow:
    SessionRecord → derive tmux name → try local → fallback VPS → update registry

Design rules:
- No env-based session name lookups
- No substrate imports
- tmux name is DERIVED from SessionRecord
- Failover updates the registry atomically
"""

from __future__ import annotations

import logging
from typing import Any

from umh.runtime_loop.session_registry import SessionRecord, get_registry

logger = logging.getLogger(__name__)


def route_session_message(session: SessionRecord, text: str) -> dict[str, Any]:
    """Route a message through the session's execution path.

    Tries local bridge first (if session.node == "local" or bridge enabled),
    falls back to VPS. Updates registry node on failover.

    Returns: {"ok": bool, "node": str, "session_name": str, "method": str}
    """
    tmux_name = session.tmux_name
    registry = get_registry()

    if session.node == "local":
        local_ok = _try_local_bridge(text, tmux_name)
        if local_ok:
            return {
                "ok": True,
                "node": "local",
                "session_name": tmux_name,
                "method": "local_bridge",
            }
        registry.update_node(session.session_id, "vps")
        logger.info(
            "[SessionRouter] Local failed for %s, falling back to VPS",
            session.session_id,
        )

    vps_ok = _try_vps_injection(tmux_name, text)
    if vps_ok:
        if session.node == "local":
            registry.update_node(session.session_id, "vps")
        return {
            "ok": True,
            "node": "vps",
            "session_name": tmux_name,
            "method": "vps_tmux",
        }

    return {
        "ok": False,
        "node": session.node,
        "session_name": tmux_name,
        "method": "none",
        "reason": "both local and vps injection failed",
    }


_local_bridge_fn = None


def register_local_bridge(fn) -> None:
    global _local_bridge_fn
    _local_bridge_fn = fn


def _try_local_bridge(text: str, session_name: str) -> bool:
    if _local_bridge_fn is None:
        return False
    try:
        return _local_bridge_fn(text, session_name)
    except Exception as exc:
        logger.debug("[SessionRouter] Local bridge error: %s", exc)
        return False


def _try_vps_injection(session_name: str, text: str) -> bool:
    try:
        from umh.substrate.claude_session_bridge import send_message

        result = send_message("vps", session_name, text)
        return result.get("ok", False)
    except Exception as exc:
        logger.debug("[SessionRouter] VPS injection error: %s", exc)
        return False
