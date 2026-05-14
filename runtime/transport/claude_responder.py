"""
Claude Responder v1 — thin adapter that turns a text prompt into a reply by
routing it through a persistent Claude Code tmux session via
`runtime.transport.claude_session_bridge`.

Purpose
-------
Provides a single, simple entry point that Discord (and later meeting /
operator) surfaces can call to get a conversational reply WITHOUT using any
provider API, token budget, or second cognition pipeline.

    respond_via_claude_session(text, target="vps", session_name="dex_main")
        -> {"ok": bool, "reply": str, "source": "claude_session",
            "session": str, ...}

Design invariants
-----------------
- No hot-path imports (gateway, cognitive_loop, model_router, agent_runtime,
  primitives).
- No provider SDK usage. No network calls.
- No background threads, no auto-spawn loops.
- Safe degradation: if tmux is missing, claude CLI is missing, or the
  session is unreachable, returns ok=False with a structured reason and
  an empty reply — callers then fall back to their existing path.
- This module is additive and bounded. It creates no second pipeline; it
  is a responder backend that plugs behind an existing transport.
"""

from __future__ import annotations

import os
from typing import Any

from runtime.transport import claude_session_bridge as csb

_DEFAULT_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

LAYER_NAME = "claude_responder"
LAYER_VERSION = "v1"

DEFAULT_SESSION_NAME = "dex_main"
DEFAULT_TARGET = "vps"

# Session mapping bounds
_DISCORD_CHANNEL_SESSION_PREFIX = "dex_discord_"


def session_name_for_discord_channel(channel_id: Any) -> str:
    """Stable per-channel session name, or the default if no channel id."""
    if channel_id is None or str(channel_id).strip() == "":
        return DEFAULT_SESSION_NAME
    return csb.make_session_name("discord", str(channel_id))


def _empty(
    *,
    target: str,
    session_name: str,
    reason: str,
    detail: str = "",
) -> dict[str, Any]:
    return {
        "ok": False,
        "reply": "",
        "source": "claude_session",
        "session": session_name,
        "target": target,
        "reason": reason,
        "detail": detail,
        "layer": LAYER_NAME,
        "version": LAYER_VERSION,
    }


def respond_via_claude_session(
    text: str,
    *,
    target: str = DEFAULT_TARGET,
    session_name: str = DEFAULT_SESSION_NAME,
    working_dir: str | None = _DEFAULT_ROOT,
    poll_interval_s: float | None = None,
    max_polls: int | None = None,
) -> dict[str, Any]:
    """Route `text` into a persistent Claude Code tmux session and return reply.

    Flow:
      1. Validate input; empty text → ok=False (empty_text).
      2. Check tmux + claude CLI availability; degrade safely if missing.
      3. csb.ask_session(target, session_name, text) — ensures the session,
         sends the text, and performs bounded polling to capture the reply.
      4. Return a structured dict with the extracted reply text.

    Never raises.
    """
    if not isinstance(text, str) or not text.strip():
        return _empty(
            target=target,
            session_name=session_name,
            reason="empty_text",
        )

    if target not in csb.VALID_TARGETS:
        return _empty(
            target=target,
            session_name=session_name,
            reason="invalid_target",
            detail=str(target),
        )

    tmux_env = csb.detect_tmux_available()
    if not tmux_env.get("available"):
        return _empty(
            target=target,
            session_name=session_name,
            reason="tmux_not_available",
            detail=str(tmux_env.get("error") or ""),
        )

    cli_env = csb.detect_claude_cli_available()
    if not cli_env.get("available"):
        return _empty(
            target=target,
            session_name=session_name,
            reason="claude_cli_not_available",
        )

    try:
        ask = csb.ask_session(
            target,
            session_name,
            text.strip(),
            ensure=True,
            working_dir=working_dir,
            poll_interval_s=poll_interval_s,
            max_polls=max_polls,
        )
    except Exception as exc:  # noqa: BLE001 — boundary: never raise
        return _empty(
            target=target,
            session_name=session_name,
            reason="ask_exception",
            detail=str(exc),
        )

    if not ask.get("ok"):
        return {
            "ok": False,
            "reply": "",
            "source": "claude_session",
            "session": session_name,
            "target": target,
            "reason": ask.get("stage") or "ask_failed",
            "detail": ask.get("reason") or "",
            "ask": ask,
            "layer": LAYER_NAME,
            "version": LAYER_VERSION,
        }

    reply = (ask.get("reply_text") or "").strip()
    return {
        "ok": bool(reply),
        "reply": reply,
        "source": "claude_session",
        "session": session_name,
        "target": target,
        "reason": "ok" if reply else "empty_reply",
        "polls_done": ask.get("polls_done"),
        "reply_chars": ask.get("reply_chars"),
        "layer": LAYER_NAME,
        "version": LAYER_VERSION,
    }


__all__ = [
    "LAYER_NAME",
    "LAYER_VERSION",
    "DEFAULT_SESSION_NAME",
    "DEFAULT_TARGET",
    "respond_via_claude_session",
    "session_name_for_discord_channel",
]
