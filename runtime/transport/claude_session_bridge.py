"""
Claude Code Session Bridge v1 — persistent tmux-backed Claude Code sessions.

This module provides an explicit, bounded bridge into persistent Claude Code
CLI sessions running inside tmux. It is designed as a *responder backend*
that later surfaces (Discord text, meeting intelligence, operator interface)
can route conversational turns through — WITHOUT introducing a second
cognition pipeline alongside gateway/cognitive_loop/model_router.

Design invariants:
  - No hot-path imports (gateway, cognitive_loop, model_router, agent_runtime,
    primitives). This module is a substrate leaf.
  - No background threads, no daemons, no auto-spawn loops.
  - All tmux interaction is explicit and observable via subprocess.run.
  - Safe degradation when tmux or claude CLI are unavailable — every
    entry point returns a JSON-safe status dict and never raises.
  - Supports dual targets ("vps" | "local") so the same code runs on both
    the VPS and the local machine against their own tmux server. No
    networking: cross-machine routing is handled by Control Layer v2.

Public API (all return JSON-safe dicts):
  - detect_tmux_available() -> dict
  - detect_claude_cli_available() -> dict
  - default_session_target() -> str ("vps" | "local")
  - make_session_name(kind, *parts) -> str
  - list_sessions(target=None) -> dict
  - session_status(target, session_name) -> dict
  - ensure_session(target, session_name, *, working_dir=None,
                   launch_claude=True) -> dict
  - send_message(target, session_name, text) -> dict
  - capture_output(target, session_name, *, tail_lines=200) -> dict
  - ask_session(target, session_name, text, *, ensure=True,
                poll_interval_s=None, max_polls=None,
                settle_lines=200) -> dict
                (defaults: poll_interval_s=1.0, max_polls=40;
                 overridable via EOS_SESSION_POLL_INTERVAL,
                 EOS_SESSION_MAX_POLLS env vars)

All functions accept target in {"vps", "local"}. Because this pass does not
do networking, the target is metadata: both values talk to the *local tmux
server* of whichever machine is running the bridge. The field exists so
callers on either node use the same API surface and so downstream routing
can distinguish which brain they were talking to.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


LAYER_NAME = "claude_session_bridge"
LAYER_VERSION = "v1"

VALID_TARGETS = ("vps", "local")

# Bounds (explicit, observable, safe):
_TMUX_CMD_TIMEOUT_S = 5.0
_MAX_TAIL_LINES = 2000
_DEFAULT_TAIL_LINES = 200
_MAX_MESSAGE_CHARS = 8000
_MAX_POLLS = 60
_MIN_POLL_INTERVAL_S = 0.1
_MAX_POLL_INTERVAL_S = 5.0

# ─── Session → persona soul-doc mapping ──────────────────────────────────────
# When claude is launched inside a session, an optional soul-doc path can be
# appended to the default system prompt via --append-system-prompt. This is
# how dex_product_main gets EA persona instead of the developer CLAUDE.md.
#
# Builder sessions (dex_builder_main) deliberately have NO entry here — they
# run bare `claude` and pick up /opt/OS/CLAUDE.md as the full developer
# context. That is the correct behavior for the developer lane.
#
# Per-channel session names (dex_product_main_<channel_id>) are handled by
# _resolve_soul_doc() via prefix match, so the EOS_DISCORD_MODE_PER_CHANNEL
# feature keeps working.
#
# Override at runtime with the env var:
#   EOS_SESSION_SOUL_DOC__<session_name> = /absolute/path/to/doc.md
_SESSION_SOUL_DOCS: dict[str, str] = {
    "dex_product_main": f"{_ROOT}/agents/executive_assistant.md",
}

_SOUL_DOC_ENV_PREFIX = "EOS_SESSION_SOUL_DOC__"

# Session name sanitation: tmux session names must not contain ":" or ".".
_SESSION_NAME_FORBIDDEN = set(":.\n\r\t ")

# Per-session serialization locks — prevents race conditions when multiple
# callers (e.g. voice path + text path) route to the same tmux session
# concurrently.  Without this, one caller can pick up another's response
# from the shared tmux pane output.
_SESSION_LOCKS: dict[str, threading.Lock] = {}
_SESSION_LOCKS_GUARD = threading.Lock()


def _get_session_lock(session_name: str) -> threading.Lock:
    """Return (or create) a per-session threading.Lock."""
    with _SESSION_LOCKS_GUARD:
        if session_name not in _SESSION_LOCKS:
            _SESSION_LOCKS[session_name] = threading.Lock()
        return _SESSION_LOCKS[session_name]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ClaudeSessionTarget:
    target: str  # "vps" | "local"
    session_name: str
    node_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClaudeSessionInfo:
    target: str
    session_name: str
    status: str  # "missing" | "running" | "degraded"
    last_seen_ts: float | None = None
    detail: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------


def detect_tmux_available() -> dict[str, Any]:
    """Check whether tmux is installed and reachable."""
    path = shutil.which("tmux")
    if not path:
        return {"available": False, "path": None, "version": None}
    try:
        proc = subprocess.run(
            [path, "-V"],
            capture_output=True,
            text=True,
            timeout=_TMUX_CMD_TIMEOUT_S,
        )
        version = (proc.stdout or proc.stderr or "").strip() or "unknown"
        return {"available": proc.returncode == 0, "path": path, "version": version}
    except Exception as exc:  # noqa: BLE001 - boundary: safe degrade
        return {"available": False, "path": path, "version": None, "error": str(exc)}


def detect_claude_cli_available() -> dict[str, Any]:
    """Check whether the Claude Code CLI is on PATH."""
    # The CLI binary is typically `claude`.
    path = shutil.which("claude")
    if not path:
        return {"available": False, "path": None, "binary": "claude"}
    return {"available": True, "path": path, "binary": "claude"}


def default_session_target() -> str:
    """Pick a default target based on EOS_NODE_ROLE / hostname.

    Convention:
      - EOS_NODE_ROLE=vps   -> "vps"
      - EOS_NODE_ROLE=local -> "local"
      - otherwise: hostname containing "vps" -> "vps", else "local".
    """
    role = (os.getenv("EOS_NODE_ROLE") or "").strip().lower()
    if role in VALID_TARGETS:
        return role
    host = (socket.gethostname() or "").lower()
    if "vps" in host:
        return "vps"
    return "local"


def _current_node_id() -> str:
    return (
        os.getenv("EOS_NODE_ID")
        or os.getenv("HOSTNAME")
        or socket.gethostname()
        or "unknown"
    )


# ---------------------------------------------------------------------------
# Naming helpers
# ---------------------------------------------------------------------------


def _sanitize_session_name(name: str) -> str:
    out = []
    for ch in (name or "").strip():
        if ch in _SESSION_NAME_FORBIDDEN:
            out.append("_")
        else:
            out.append(ch)
    cleaned = "".join(out).strip("_")
    return cleaned or "dex_unnamed"


def make_session_name(kind: str, *parts: str) -> str:
    """Build a stable, tmux-safe session name.

    Examples:
      make_session_name("main")                  -> "dex_main"
      make_session_name("discord", "123", "456") -> "dex_discord_123_456"
      make_session_name("local", "main")         -> "dex_local_main"
    """
    pieces = [str(kind)] + [str(p) for p in parts if p is not None and str(p) != ""]
    raw = "dex_" + "_".join(pieces)
    return _sanitize_session_name(raw)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_target(target: str) -> tuple[bool, str]:
    if target not in VALID_TARGETS:
        return False, f"invalid_target:{target!r}"
    return True, ""


def _validate_session_name(session_name: str) -> tuple[bool, str]:
    if not isinstance(session_name, str) or not session_name.strip():
        return False, "session_name_empty"
    if session_name != _sanitize_session_name(session_name):
        return False, "session_name_unsafe"
    if len(session_name) > 120:
        return False, "session_name_too_long"
    return True, ""


def _err(target: str, session_name: str, reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "ok": False,
        "target": target,
        "session_name": session_name,
        "reason": reason,
        "layer": LAYER_NAME,
        "version": LAYER_VERSION,
    }
    if extra:
        out["extra"] = extra
    return out


# ---------------------------------------------------------------------------
# Low-level tmux plumbing (bounded, explicit)
# ---------------------------------------------------------------------------


def _resolve_soul_doc(session_name: str) -> str | None:
    """Resolve the soul-doc path for a session, if any.

    Lookup order:
      1. Env override EOS_SESSION_SOUL_DOC__<session_name> (exact match)
      2. Exact match in _SESSION_SOUL_DOCS
      3. Prefix match against _SESSION_SOUL_DOCS keys (handles per-channel
         suffixes like dex_product_main_1234567890)

    Returns an absolute path that is verified to exist, or None.
    Never raises.
    """
    # 1. Env override
    env_key = f"{_SOUL_DOC_ENV_PREFIX}{session_name}"
    env_val = (os.getenv(env_key) or "").strip()
    if env_val:
        if os.path.isfile(env_val):
            return env_val
        return None

    # 2. Exact match
    if session_name in _SESSION_SOUL_DOCS:
        path = _SESSION_SOUL_DOCS[session_name]
        return path if os.path.isfile(path) else None

    # 3. Prefix match (per-channel variants: dex_product_main_<channel_id>)
    for base_name, path in _SESSION_SOUL_DOCS.items():
        if session_name.startswith(base_name + "_"):
            return path if os.path.isfile(path) else None

    return None


def _build_claude_launch_cmd(session_name: str) -> tuple[str, str | None]:
    """Build the shell command string to launch claude in a session pane.

    Returns (command_string, soul_doc_path_used_or_None).

    The command is a single shell line that will be typed into the tmux
    pane's shell via `send-keys`. If a soul doc is resolved, it is appended
    via --append-system-prompt using command substitution so the shell does
    the file reading — this avoids any Python-side escaping of arbitrary
    markdown content.
    """
    soul_doc = _resolve_soul_doc(session_name)
    if not soul_doc:
        return "claude", None

    # Single-quote the path so paths with spaces / special chars are safe.
    # command substitution $(cat '...') streams the file contents into the
    # flag value; the outer double quotes keep it as a single argv token
    # from claude's perspective.
    quoted_path = soul_doc.replace("'", "'\\''")
    cmd = f"claude --append-system-prompt \"$(cat '{quoted_path}')\""
    return cmd, soul_doc


def _run_tmux(args: list[str]) -> dict[str, Any]:
    """Run a tmux command with bounds. Never raises."""
    path = shutil.which("tmux")
    if not path:
        return {"ok": False, "reason": "tmux_not_available", "stdout": "", "stderr": ""}
    try:
        proc = subprocess.run(
            [path, *args],
            capture_output=True,
            text=True,
            timeout=_TMUX_CMD_TIMEOUT_S,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[:16000],
            "stderr": (proc.stderr or "")[:4000],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "tmux_timeout", "stdout": "", "stderr": ""}
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "reason": "tmux_exception",
            "error": str(exc),
            "stdout": "",
            "stderr": "",
        }


def _tmux_has_session(session_name: str) -> bool:
    res = _run_tmux(["has-session", "-t", session_name])
    return bool(res.get("ok"))


def _tmux_list_sessions() -> list[dict[str, Any]]:
    res = _run_tmux(
        [
            "list-sessions",
            "-F",
            "#{session_name}|#{session_created}|#{session_attached}",
        ]
    )
    if not res.get("ok"):
        return []
    sessions: list[dict[str, Any]] = []
    for line in (res.get("stdout") or "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        name = parts[0] if parts else line
        created = parts[1] if len(parts) > 1 else ""
        attached = parts[2] if len(parts) > 2 else ""
        try:
            created_ts = float(created) if created else None
        except ValueError:
            created_ts = None
        sessions.append(
            {
                "session_name": name,
                "created_ts": created_ts,
                "attached": attached == "1",
            }
        )
    return sessions


# ---------------------------------------------------------------------------
# Public: listing & status
# ---------------------------------------------------------------------------


def list_sessions(target: str | None = None) -> dict[str, Any]:
    """List tmux sessions visible on this machine.

    If target is provided, the payload will include it as metadata and filter
    to sessions whose names start with the dex_ prefix. All sessions are
    still reported under "all_sessions" for observability.
    """
    tmux_env = detect_tmux_available()
    if not tmux_env.get("available"):
        return {
            "ok": True,  # degrade safely
            "target": target,
            "available": False,
            "reason": "tmux_not_available",
            "sessions": [],
            "all_sessions": [],
            "layer": LAYER_NAME,
            "version": LAYER_VERSION,
        }
    all_sessions = _tmux_list_sessions()
    dex_sessions = [s for s in all_sessions if s["session_name"].startswith("dex_")]
    return {
        "ok": True,
        "target": target or default_session_target(),
        "available": True,
        "sessions": dex_sessions,
        "all_sessions": all_sessions,
        "node_id": _current_node_id(),
        "layer": LAYER_NAME,
        "version": LAYER_VERSION,
    }


def session_status(target: str, session_name: str) -> dict[str, Any]:
    ok, reason = _validate_target(target)
    if not ok:
        return _err(target, session_name, reason)
    ok, reason = _validate_session_name(session_name)
    if not ok:
        return _err(target, session_name, reason)

    tmux_env = detect_tmux_available()
    if not tmux_env.get("available"):
        info = ClaudeSessionInfo(
            target=target,
            session_name=session_name,
            status="degraded",
            last_seen_ts=None,
            detail="tmux_not_available",
        )
        return {
            "ok": True,
            **info.to_dict(),
            "layer": LAYER_NAME,
            "version": LAYER_VERSION,
        }

    exists = _tmux_has_session(session_name)
    if not exists:
        info = ClaudeSessionInfo(
            target=target,
            session_name=session_name,
            status="missing",
            last_seen_ts=None,
        )
        return {
            "ok": True,
            **info.to_dict(),
            "layer": LAYER_NAME,
            "version": LAYER_VERSION,
        }

    # Pull creation ts if available
    created_ts: float | None = None
    for s in _tmux_list_sessions():
        if s["session_name"] == session_name:
            created_ts = s.get("created_ts")
            break
    info = ClaudeSessionInfo(
        target=target,
        session_name=session_name,
        status="running",
        last_seen_ts=created_ts,
    )
    return {"ok": True, **info.to_dict(), "layer": LAYER_NAME, "version": LAYER_VERSION}


# ---------------------------------------------------------------------------
# Public: ensure / send / capture / ask
# ---------------------------------------------------------------------------


def ensure_session(
    target: str,
    session_name: str,
    *,
    working_dir: str | None = None,
    launch_claude: bool = True,
) -> dict[str, Any]:
    """Ensure a tmux session exists; optionally launch Claude Code inside it.

    If the session already exists, this is a no-op and reports created=False.
    If tmux is unavailable, degrades safely with ok=True + status=degraded.
    If launch_claude is True and the claude CLI is not on PATH, the session
    is still created (empty shell) and the response reports that Claude was
    not launched with reason=claude_cli_not_available.
    """
    ok, reason = _validate_target(target)
    if not ok:
        return _err(target, session_name, reason)
    ok, reason = _validate_session_name(session_name)
    if not ok:
        return _err(target, session_name, reason)

    tmux_env = detect_tmux_available()
    if not tmux_env.get("available"):
        return {
            "ok": True,
            "target": target,
            "session_name": session_name,
            "status": "degraded",
            "created": False,
            "claude_launched": False,
            "reason": "tmux_not_available",
            "layer": LAYER_NAME,
            "version": LAYER_VERSION,
        }

    if working_dir and not os.path.isdir(working_dir):
        return _err(
            target, session_name, "working_dir_not_found", working_dir=working_dir
        )

    already = _tmux_has_session(session_name)
    created = False
    if not already:
        cmd: list[str] = ["new-session", "-d", "-s", session_name]
        if working_dir:
            cmd.extend(["-c", working_dir])
        res = _run_tmux(cmd)
        if not res.get("ok"):
            return _err(
                target,
                session_name,
                "tmux_new_session_failed",
                stderr=res.get("stderr"),
                returncode=res.get("returncode"),
            )
        created = True

    claude_launched = False
    claude_reason = ""
    soul_doc_used: str | None = None
    if launch_claude and created:
        cli = detect_claude_cli_available()
        if cli.get("available"):
            # Build the launch command. For sessions with a persona mapping
            # (e.g. dex_product_main → executive_assistant.md) this appends
            # the soul doc via --append-system-prompt. Builder sessions get
            # a bare `claude` and pick up /opt/OS/CLAUDE.md as usual.
            launch_cmd, soul_doc_used = _build_claude_launch_cmd(session_name)
            res = _run_tmux(["send-keys", "-t", session_name, launch_cmd, "Enter"])
            if res.get("ok"):
                claude_launched = True
                # brief settle so the CLI has a moment to initialize
                time.sleep(0.3)
            else:
                claude_reason = f"send_keys_failed:{res.get('stderr', '')[:200]}"
        else:
            claude_reason = "claude_cli_not_available"

    return {
        "ok": True,
        "target": target,
        "session_name": session_name,
        "status": "running",
        "created": created,
        "already_existed": already,
        "claude_launched": claude_launched,
        "claude_reason": claude_reason,
        "working_dir": working_dir,
        "soul_doc": soul_doc_used,
        "node_id": _current_node_id(),
        "layer": LAYER_NAME,
        "version": LAYER_VERSION,
    }


def send_message(target: str, session_name: str, text: str) -> dict[str, Any]:
    """Inject text into a tmux session's active pane (followed by Enter)."""
    ok, reason = _validate_target(target)
    if not ok:
        return _err(target, session_name, reason)
    ok, reason = _validate_session_name(session_name)
    if not ok:
        return _err(target, session_name, reason)
    if not isinstance(text, str):
        return _err(target, session_name, "text_not_string")
    if not text:
        return _err(target, session_name, "text_empty")
    if len(text) > _MAX_MESSAGE_CHARS:
        return _err(
            target,
            session_name,
            "text_too_long",
            max_chars=_MAX_MESSAGE_CHARS,
            got=len(text),
        )

    tmux_env = detect_tmux_available()
    if not tmux_env.get("available"):
        return {
            "ok": False,
            "target": target,
            "session_name": session_name,
            "reason": "tmux_not_available",
            "degraded": True,
            "layer": LAYER_NAME,
            "version": LAYER_VERSION,
        }

    if not _tmux_has_session(session_name):
        return _err(target, session_name, "session_missing")

    # Flatten to a single line — newlines cause tmux to show
    # "[Pasted text #N +X lines]" instead of clean injection.
    text = " ".join(text.splitlines())

    # Send literal text (-l), pause 100ms for CC to register the paste,
    # then send Enter as a separate keypress.  Without this delay the
    # second message in a rapid sequence can sit unsubmitted because
    # Enter arrives before CC has ingested the pasted text.
    res_text = _run_tmux(["send-keys", "-t", session_name, "-l", text])
    if not res_text.get("ok"):
        return _err(
            target,
            session_name,
            "send_keys_text_failed",
            stderr=res_text.get("stderr"),
        )
    time.sleep(0.1)  # let CC register pasted text before Enter
    res_enter = _run_tmux(["send-keys", "-t", session_name, "Enter"])
    if not res_enter.get("ok"):
        return _err(
            target,
            session_name,
            "send_keys_enter_failed",
            stderr=res_enter.get("stderr"),
        )
    return {
        "ok": True,
        "target": target,
        "session_name": session_name,
        "chars_sent": len(text),
        "sent_at": time.time(),
        "layer": LAYER_NAME,
        "version": LAYER_VERSION,
    }


def capture_output(
    target: str,
    session_name: str,
    *,
    tail_lines: int = _DEFAULT_TAIL_LINES,
) -> dict[str, Any]:
    """Capture bounded pane output from a tmux session."""
    ok, reason = _validate_target(target)
    if not ok:
        return _err(target, session_name, reason)
    ok, reason = _validate_session_name(session_name)
    if not ok:
        return _err(target, session_name, reason)

    try:
        n = int(tail_lines)
    except (TypeError, ValueError):
        return _err(target, session_name, "tail_lines_invalid")
    if n <= 0:
        return _err(target, session_name, "tail_lines_nonpositive")
    if n > _MAX_TAIL_LINES:
        n = _MAX_TAIL_LINES

    tmux_env = detect_tmux_available()
    if not tmux_env.get("available"):
        return {
            "ok": False,
            "target": target,
            "session_name": session_name,
            "reason": "tmux_not_available",
            "degraded": True,
            "layer": LAYER_NAME,
            "version": LAYER_VERSION,
        }

    if not _tmux_has_session(session_name):
        return _err(target, session_name, "session_missing")

    # -p print to stdout, -S -N start offset N lines back, -J join wrapped
    res = _run_tmux(["capture-pane", "-t", session_name, "-p", "-J", "-S", f"-{n}"])
    if not res.get("ok"):
        return _err(
            target, session_name, "capture_pane_failed", stderr=res.get("stderr")
        )
    output = res.get("stdout") or ""
    lines = output.splitlines()
    return {
        "ok": True,
        "target": target,
        "session_name": session_name,
        "tail_lines": n,
        "line_count": len(lines),
        "output": output,
        "captured_at": time.time(),
        "layer": LAYER_NAME,
        "version": LAYER_VERSION,
    }


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\].*?\x07|\x1b\[[\d;]*m")
_RESPONSE_MARKER = "●"
_PROMPT_MARKER = "❯"
# Lines made entirely of box-drawing / decoration chars (no alphanumeric content)
_DECORATION_LINE_RE = re.compile(r"^[\s─━═╌╍┄┅┈┉\-–—_.·•·,]+$")
# CC boot banner pattern — e.g. "▐▛███▜▌ Claude Code v2.1.97 ▝▜█████▛▘ Opus 4.6"
_CC_BANNER_RE = re.compile(r"[▐▛▜▌▝▘█]+.*Claude Code")
# CC footer metadata lines — cost, tokens, timing, spend summaries, provider badge
_CC_FOOTER_RE = re.compile(
    r"^\s*("
    r"\$\d"  # cost lines: "$0.0264"
    r"|[\d,]+\s*tokens"  # token counts: "8,349 tokens"
    r"|⏱"  # timing: "⏱ 47.3s"
    r"|⚙"  # gear: settings/config line
    r"|🪙"  # token coin
    r"|📊"  # chart: stats line
    r"|💰"  # money bag: cost line
    r"|Today\s+\$"  # daily spend: "Today $1.23"
    r"|Month\s+\$"  # monthly spend: "Month $45.67"
    r"|All-time\s+\$"  # all-time spend: "All-time $123.45"
    r"|>\s*\$\d"  # "> $0.03" cost prefix
    r"|\d+\.\d+s\b"  # bare timing: "47.3s"
    r"|provider:"  # "provider: claude"
    r"|model:"  # "model: opus"
    r"|claude-\w"  # model badge: "claude-opus-4-6"
    r"|gemini-\w"  # model badge: "gemini-2.5-flash"
    r"|Context:"  # "Context: 8k tokens"
    r")",
    re.IGNORECASE,
)


def _scrub_cli_chrome(text: str) -> str:
    """Extract Claude Code reply content from captured tmux output.

    Strategy: boundary extraction, not pattern exclusion.

    Claude Code's output has a reliable structure:
      - The actual reply begins after the last ``●`` marker.
      - The reply ends before the next ``❯`` prompt (if present).
      - Everything outside those boundaries is tooling chrome.

    Processing order:
      1. Strip ANSI escape sequences.
      2. Find last ``●`` — extract from there to end (or next ``❯``).
      3. Strip the ``●`` prefix character itself.
      4. Strip trailing tmux whitespace padding per line.
      5. Strip leading/trailing blank lines.

    If no ``●`` is found the text is returned with only ANSI and
    whitespace cleanup — this handles pre-marker edge cases where
    the capture didn't include the full response frame.

    Pure function, no side-effects.
    """
    # 1. Strip ANSI escapes
    text = _ANSI_RE.sub("", text)

    lines = text.splitlines()

    # 2. Find last ● response marker
    last_marker_idx: int | None = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith(_RESPONSE_MARKER):
            last_marker_idx = i

    if last_marker_idx is not None:
        # Extract: marker line (strip ● prefix) + everything after
        marker_line = lines[last_marker_idx].lstrip()
        marker_line = marker_line[len(_RESPONSE_MARKER) :].lstrip()
        lines = [marker_line] + lines[last_marker_idx + 1 :]

    # 3. Truncate at first ❯ prompt (end boundary)
    truncated: list[str] = []
    for line in lines:
        if line.lstrip().startswith(_PROMPT_MARKER):
            break
        truncated.append(line)
    lines = truncated

    # 4. Drop decoration-only lines (box-drawing separators from CC rendering)
    #    Also drop CC boot banner lines and footer metadata (cost, tokens, etc.)
    lines = [
        line
        for line in lines
        if not _DECORATION_LINE_RE.match(line)
        and not _CC_BANNER_RE.search(line)
        and not _CC_FOOTER_RE.match(line)
    ]

    # 5. Strip tmux trailing whitespace padding per line
    lines = [line.rstrip() for line in lines]

    return "\n".join(lines).strip()


def _extract_new_reply(before: str, after: str) -> str:
    """Extract the latest reply from a tmux pane capture.

    Strategy: watermark suffix-diff + boundary extraction.

    The tmux capture is a sliding window (last N lines), so ``after``
    is NOT simply ``before + new_stuff`` — old lines scroll out as new
    ones appear.  To find genuinely new content we locate the longest
    trailing portion of ``before`` that still appears at the *start* of
    ``after`` (the overlap), then treat everything past that overlap as
    new.  Within the new slice, ``_scrub_cli_chrome`` performs ``●``/
    ``❯`` boundary extraction as normal.

    This prevents stale ``●`` content from prior CC tasks (still
    visible in the pane scrollback) from being returned as the reply
    to a new message.

    Returns empty string if no new content exists past the watermark,
    which triggers fallback provider in the router.
    """
    if after == before:
        return ""

    # Fast path: after is strictly longer and starts with before (no scroll)
    if after.startswith(before):
        new_content = after[len(before) :]
        return _scrub_cli_chrome(new_content) if new_content.strip() else ""

    # Sliding-window path: find the overlap between the tail of
    # ``before`` and the head of ``after``.  We compare line-by-line
    # from the end of ``before`` to find the longest suffix of
    # ``before`` lines that matches a prefix of ``after`` lines.
    before_lines = before.splitlines()
    after_lines = after.splitlines()

    # Search for the longest suffix of before_lines that is a prefix
    # of after_lines. Start from the full before_lines and shrink.
    overlap_len = 0
    for start in range(len(before_lines)):
        suffix = before_lines[start:]
        slen = len(suffix)
        if slen <= len(after_lines) and after_lines[:slen] == suffix:
            overlap_len = slen
            break

    if overlap_len > 0 and overlap_len < len(after_lines):
        new_lines = after_lines[overlap_len:]
        new_content = "\n".join(new_lines)
        return _scrub_cli_chrome(new_content) if new_content.strip() else ""

    # No overlap found — content changed entirely (large output burst).
    # Fall back to full scrub of after, but only if after is actually
    # different from before (already checked above).
    return _scrub_cli_chrome(after)


def _raw_new_region(before_lines: list[str], after_text: str) -> str:
    """Return the raw (unscrubbed) new content in *after_text* that was not
    present in *before_lines*.

    Uses the same line-based suffix-overlap algorithm as
    ``_extract_new_reply`` but returns the raw text (no scrubbing) so
    callers can inspect it for structural markers like ``●``.
    """
    after_lines = after_text.splitlines()

    # Fast path: after starts with all of before (no scroll).
    if (
        len(after_lines) >= len(before_lines)
        and after_lines[: len(before_lines)] == before_lines
    ):
        new = after_lines[len(before_lines) :]
        return "\n".join(new)

    # Sliding-window: find longest suffix of before_lines that matches
    # a prefix of after_lines.
    overlap_len = 0
    for start in range(len(before_lines)):
        suffix = before_lines[start:]
        slen = len(suffix)
        if slen <= len(after_lines) and after_lines[:slen] == suffix:
            overlap_len = slen
            break

    if overlap_len > 0 and overlap_len < len(after_lines):
        new = after_lines[overlap_len:]
        return "\n".join(new)

    # No overlap — everything in after is new (large burst).
    if after_text != "\n".join(before_lines):
        return after_text
    return ""


def ask_session(
    target: str,
    session_name: str,
    text: str,
    *,
    ensure: bool = True,
    working_dir: str | None = None,
    poll_interval_s: float | None = None,
    max_polls: int | None = None,
    settle_lines: int = _DEFAULT_TAIL_LINES,
) -> dict[str, Any]:
    """Ensure → capture-before → send → bounded-poll → capture-after → diff.

    Returns a structured dict with best-effort extracted reply text. Never
    raises. Degrades safely if tmux/claude CLI are missing.

    If a SessionWatcher is running for this session, delegates to the
    watcher-aware path (faster, state-aware). Falls back to polling
    if no watcher is active.
    """
    # ── Watcher-aware fast path ──────────────────────────────────────────
    try:
        from eos_ai.transport.session_watcher import get_watcher

        watcher = get_watcher(session_name)
        if watcher:
            if ensure:
                ensure_res = ensure_session(
                    target,
                    session_name,
                    working_dir=working_dir,
                    launch_claude=True,
                )
                if not ensure_res.get("ok"):
                    return {
                        "ok": False,
                        "stage": "ensure",
                        "ensure": ensure_res,
                        "layer": LAYER_NAME,
                        "version": LAYER_VERSION,
                    }

            # Resolve timeout from poll params
            _interval = poll_interval_s or 1.0
            _polls = max_polls or 40
            timeout = _interval * _polls

            # Send message, then let wait_for_reply handle its own
            # state clearing under the watcher lock (avoids race where
            # the daemon thread sets the event between our clear and
            # wait_for_reply's clear, losing the reply).
            send_res = send_message(target, session_name, text)
            if not send_res.get("ok"):
                return {
                    "ok": False,
                    "stage": "send",
                    "send": send_res,
                    "layer": LAYER_NAME,
                    "version": LAYER_VERSION,
                }

            raw_reply = watcher.wait_for_reply(timeout=timeout)
            # Watcher returns raw tmux text — scrub CC chrome/footer
            reply = _scrub_cli_chrome(raw_reply).strip("\n") if raw_reply else ""
            return {
                "ok": True,
                "target": target,
                "session_name": session_name,
                "sent_chars": len(text),
                "polls_done": 0,
                "poll_interval_s": 0,
                "max_polls": 0,
                "reply_text": reply,
                "reply_chars": len(reply),
                "before_chars": 0,
                "after_chars": 0,
                "ensure": None,
                "watcher": True,
                "layer": LAYER_NAME,
                "version": LAYER_VERSION,
            }
    except ImportError:
        pass  # session_watcher not available — use polling fallback
    except Exception as e:
        print(f"[ask_session] Watcher path failed, falling back to polling: {e}")

    # ── Polling fallback (original behavior) ─────────────────────────────
    # Resolve defaults: caller arg → env var → hardcoded default
    _default_interval = 1.0
    _default_polls = 40
    if poll_interval_s is None:
        _env_interval = os.getenv("EOS_SESSION_POLL_INTERVAL")
        if _env_interval:
            try:
                _default_interval = float(_env_interval)
            except (TypeError, ValueError):
                pass
        poll_interval_s = _default_interval
    if max_polls is None:
        _env_polls = os.getenv("EOS_SESSION_MAX_POLLS")
        if _env_polls:
            try:
                _default_polls = int(_env_polls)
            except (TypeError, ValueError):
                pass
        max_polls = _default_polls

    # Clamp polling bounds
    try:
        interval = float(poll_interval_s)
    except (TypeError, ValueError):
        interval = 1.0
    interval = max(_MIN_POLL_INTERVAL_S, min(_MAX_POLL_INTERVAL_S, interval))
    try:
        polls = int(max_polls)
    except (TypeError, ValueError):
        polls = 40
    polls = max(1, min(_MAX_POLLS, polls))

    # Serialize access to the same tmux session so concurrent callers
    # (e.g. substrate voice mirror + gateway text path) cannot interleave
    # capture/send/poll and pick up each other's responses.
    lock = _get_session_lock(session_name)
    lock.acquire()
    try:
        if ensure:
            ensure_res = ensure_session(
                target,
                session_name,
                working_dir=working_dir,
                launch_claude=True,
            )
            if not ensure_res.get("ok"):
                return {
                    "ok": False,
                    "stage": "ensure",
                    "ensure": ensure_res,
                    "layer": LAYER_NAME,
                    "version": LAYER_VERSION,
                }
        else:
            ensure_res = None

        before = capture_output(target, session_name, tail_lines=settle_lines)
        if not before.get("ok"):
            return {
                "ok": False,
                "stage": "capture_before",
                "before": before,
                "ensure": ensure_res,
                "layer": LAYER_NAME,
                "version": LAYER_VERSION,
            }
        before_output = before.get("output", "")

        send_res = send_message(target, session_name, text)
        if not send_res.get("ok"):
            return {
                "ok": False,
                "stage": "send",
                "send": send_res,
                "ensure": ensure_res,
                "layer": LAYER_NAME,
                "version": LAYER_VERSION,
            }

        # Bounded poll for reply — watermark strategy.
        #
        # The tmux pane is a sliding window: old lines scroll out as
        # new ones appear.  A raw character offset watermark fails
        # because before and after captures can have completely
        # different starting lines.
        #
        # Instead we use line-based overlap detection (same algorithm
        # as _extract_new_reply) to find the genuinely NEW lines each
        # poll, then check for a ● response marker in that raw
        # (unscrubbed) region.  Only when a new ● is found AND output
        # is stable for 2 polls do we extract.
        before_lines = before_output.splitlines()
        after_output = before_output
        polls_done = 0
        stable_count = 0
        last_len = len(before_output)
        found_new_marker = False
        for _ in range(polls):
            time.sleep(interval)
            polls_done += 1
            cap = capture_output(target, session_name, tail_lines=settle_lines)
            if not cap.get("ok"):
                break
            after_output = cap.get("output", "")

            # Find genuinely new lines via overlap detection.
            new_raw = _raw_new_region(before_lines, after_output)
            has_marker = _RESPONSE_MARKER in new_raw

            if len(after_output) == last_len:
                stable_count += 1
                if has_marker:
                    found_new_marker = True
                if stable_count >= 2 and found_new_marker:
                    break
            else:
                stable_count = 0
                last_len = len(after_output)
                if has_marker:
                    found_new_marker = True

        if not found_new_marker:
            # No new ● appeared after the watermark — CC never
            # responded to this message.  Return empty to trigger
            # fallback provider in the router.
            reply = ""
        else:
            # Extract from the new region only and scrub.
            new_raw = _raw_new_region(before_lines, after_output)
            reply = _scrub_cli_chrome(new_raw).strip("\n") if new_raw.strip() else ""

        return {
            "ok": True,
            "target": target,
            "session_name": session_name,
            "sent_chars": len(text),
            "polls_done": polls_done,
            "poll_interval_s": interval,
            "max_polls": polls,
            "reply_text": reply,
            "reply_chars": len(reply),
            "before_chars": len(before_output),
            "after_chars": len(after_output),
            "ensure": ensure_res,
            "layer": LAYER_NAME,
            "version": LAYER_VERSION,
        }
    finally:
        lock.release()


__all__ = [
    "LAYER_NAME",
    "LAYER_VERSION",
    "VALID_TARGETS",
    "ClaudeSessionTarget",
    "ClaudeSessionInfo",
    "detect_tmux_available",
    "detect_claude_cli_available",
    "default_session_target",
    "make_session_name",
    "list_sessions",
    "session_status",
    "ensure_session",
    "send_message",
    "capture_output",
    "ask_session",
]
