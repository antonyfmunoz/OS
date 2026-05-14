"""
Session control — lifecycle commands for Claude Code tmux sessions.

Purpose
-------
Provides /clear, /reset, and auto-clear functionality for persistent
Claude Code tmux sessions managed by claude_session_bridge.

Design rules
------------
- Composes on top of claude_session_bridge primitives. Never duplicates
  tmux plumbing.
- No background threads, no daemons. Auto-clear is triggered inside the
  request flow.
- No hot-path imports. This is a substrate leaf.
- All functions return JSON-safe dicts. Never raises.

Public API:
  - clear_session(target, session_name) -> dict
  - reset_session(target, session_name) -> dict
  - maybe_auto_clear(session_name, *, target) -> dict
  - get_message_count(session_name) -> int
  - reset_counters_for_tests() -> None
"""

from __future__ import annotations

import os
import sys
import threading
from typing import Any
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


LAYER_NAME = "session_control"
LAYER_VERSION = "v1"

_ENV_AUTO_CLEAR_MESSAGES = "EOS_SESSION_AUTO_CLEAR_MESSAGES"
_DEFAULT_AUTO_CLEAR = 25


def _log(msg: str) -> None:
    print(f"[substrate.session_control] {msg}", file=sys.stderr)


def _auto_clear_threshold() -> int:
    """Read auto-clear threshold from env. 0 = disabled."""
    raw = os.getenv(_ENV_AUTO_CLEAR_MESSAGES, "").strip()
    if not raw:
        return _DEFAULT_AUTO_CLEAR
    try:
        n = int(raw)
        return max(0, n)
    except ValueError:
        return _DEFAULT_AUTO_CLEAR


# ─── Per-session message counters ────────────────────────────────────────────
# Tracks how many messages have been sent to each session since last clear.
# In-memory only — resets on process restart. No persistence needed.

_counter_lock = threading.Lock()
_message_counts: dict[str, int] = {}


def _increment_count(session_name: str) -> int:
    """Increment and return the new count for a session."""
    with _counter_lock:
        _message_counts[session_name] = _message_counts.get(session_name, 0) + 1
        return _message_counts[session_name]


def _reset_count(session_name: str) -> None:
    """Reset the counter for a session (after clear/reset)."""
    with _counter_lock:
        _message_counts[session_name] = 0


def get_message_count(session_name: str) -> int:
    """Return current message count for a session."""
    with _counter_lock:
        return _message_counts.get(session_name, 0)


def reset_counters_for_tests() -> None:
    """Test helper — clear all counters."""
    with _counter_lock:
        _message_counts.clear()


# ─── Clear ───────────────────────────────────────────────────────────────────


def clear_session(target: str, session_name: str) -> dict[str, Any]:
    """Send /clear into a tmux Claude Code session.

    This sends the literal "/clear" command to the Claude CLI running in
    the tmux session, which clears its conversation context.
    """
    try:
        from runtime.transport.claude_session_bridge import send_message
    except Exception as e:  # noqa: BLE001
        _log(f"claude_session_bridge import failed: {e}")
        return {
            "ok": False,
            "reason": "import_failed",
            "detail": str(e),
            "layer": LAYER_NAME,
            "version": LAYER_VERSION,
        }

    result = send_message(target, session_name, "/clear")
    if result.get("ok"):
        _reset_count(session_name)
        _log(f"clear sent to {session_name}")
    else:
        _log(f"clear failed for {session_name}: {result.get('reason')}")

    return {
        "ok": result.get("ok", False),
        "action": "clear",
        "target": target,
        "session_name": session_name,
        "reason": result.get("reason"),
        "layer": LAYER_NAME,
        "version": LAYER_VERSION,
    }


# ─── Reset ───────────────────────────────────────────────────────────────────


def reset_session(
    target: str,
    session_name: str,
    *,
    working_dir: str | None = None,
) -> dict[str, Any]:
    """Kill and recreate a tmux Claude Code session.

    Steps:
    1. Kill the existing tmux session (if present)
    2. Re-run ensure_session to create a fresh one with Claude launched
    """
    try:
        from runtime.transport.claude_session_bridge import (
            _run_tmux,
            _tmux_has_session,
            ensure_session,
        )
    except Exception as e:  # noqa: BLE001
        _log(f"claude_session_bridge import failed: {e}")
        return {
            "ok": False,
            "reason": "import_failed",
            "detail": str(e),
            "layer": LAYER_NAME,
            "version": LAYER_VERSION,
        }

    killed = False
    if _tmux_has_session(session_name):
        kill_result = _run_tmux(["kill-session", "-t", session_name])
        killed = bool(kill_result.get("ok"))
        if not killed:
            _log(f"kill-session failed for {session_name}: {kill_result.get('stderr')}")
            return {
                "ok": False,
                "action": "reset",
                "target": target,
                "session_name": session_name,
                "reason": "kill_failed",
                "detail": kill_result.get("stderr", ""),
                "layer": LAYER_NAME,
                "version": LAYER_VERSION,
            }

    wd = working_dir or _ROOT
    ensure_result = ensure_session(
        target,
        session_name,
        working_dir=wd,
        launch_claude=True,
    )

    _reset_count(session_name)
    _log(f"reset completed for {session_name} (killed={killed})")

    return {
        "ok": ensure_result.get("ok", False),
        "action": "reset",
        "target": target,
        "session_name": session_name,
        "killed": killed,
        "created": ensure_result.get("created", False),
        "claude_launched": ensure_result.get("claude_launched", False),
        "reason": ensure_result.get("reason") or ensure_result.get("claude_reason"),
        "layer": LAYER_NAME,
        "version": LAYER_VERSION,
    }


# ─── Auto-clear ─────────────────────────────────────────────────────────────


def maybe_auto_clear(
    session_name: str,
    *,
    target: str = "vps",
) -> dict[str, Any]:
    """Increment the message counter and clear if threshold is reached.

    Called inside the request flow — no background threads. Returns a dict
    indicating whether a clear was triggered.
    """
    threshold = _auto_clear_threshold()
    if threshold <= 0:
        return {
            "auto_cleared": False,
            "reason": "disabled",
            "session_name": session_name,
            "layer": LAYER_NAME,
        }

    count = _increment_count(session_name)
    if count < threshold:
        return {
            "auto_cleared": False,
            "count": count,
            "threshold": threshold,
            "session_name": session_name,
            "layer": LAYER_NAME,
        }

    _log(
        f"auto-clear triggered for {session_name} (count={count}, threshold={threshold})"
    )
    result = clear_session(target, session_name)
    # Always reset the counter after an auto-clear attempt — even if the
    # tmux command failed. Otherwise the counter stays at threshold and
    # triggers on every subsequent message.
    _reset_count(session_name)
    return {
        "auto_cleared": True,
        "clear_result": result,
        "count_before_clear": count,
        "threshold": threshold,
        "session_name": session_name,
        "layer": LAYER_NAME,
    }


__all__ = [
    "LAYER_NAME",
    "LAYER_VERSION",
    "clear_session",
    "reset_session",
    "maybe_auto_clear",
    "get_message_count",
    "reset_counters_for_tests",
]
