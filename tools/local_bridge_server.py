"""
Local Bridge Server — runs on Antony's Windows machine (WSL2).

Receives Discord messages forwarded from the VPS and injects them into
a local Claude Code tmux session.

Architecture:
    VPS discord_bot.py → local_bridge_client.py → POST /message here
    → Writes to ~/eos_inbox/{session_name}.txt
    → Watcher loop reads inbox files and injects via tmux send-keys
    → Local CC session processes the message
    → Stop hook POSTs reply back to VPS webhook receiver

Endpoints:
    GET  /health  → {"status": "ok", "machine": "local"}
    POST /message → receives {text, session_name}, injects into local CC

Usage (on Windows WSL):
    python3 local_bridge_server.py
    # or with custom port:
    EOS_LOCAL_BRIDGE_PORT=8766 python3 local_bridge_server.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path

from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("local_bridge")

# ── Configuration ───────────────────────────────────────────────────────────

PORT = int(os.getenv("EOS_LOCAL_BRIDGE_PORT", "8766"))
INBOX_DIR = Path.home() / "eos_inbox"
TMUX_INJECT_TIMEOUT_S = 5.0

# ── Inbox ───────────────────────────────────────────────────────────────────

INBOX_DIR.mkdir(parents=True, exist_ok=True)


def _tmux_has_session(session_name: str) -> bool:
    """Check if a tmux session exists."""
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
            timeout=TMUX_INJECT_TIMEOUT_S,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _tmux_send(session_name: str, text: str) -> bool:
    """Inject text into a tmux session via send-keys."""
    try:
        # Flatten to single line (same as claude_session_bridge.py)
        text = " ".join(text.splitlines())

        # Send literal text
        result = subprocess.run(
            ["tmux", "send-keys", "-t", session_name, "-l", text],
            capture_output=True,
            timeout=TMUX_INJECT_TIMEOUT_S,
        )
        if result.returncode != 0:
            logger.error(
                "[Bridge] tmux send-keys text failed: %s",
                result.stderr.decode(),
            )
            return False

        # Brief pause for CC to register paste, then send Enter
        time.sleep(0.1)

        result = subprocess.run(
            ["tmux", "send-keys", "-t", session_name, "Enter"],
            capture_output=True,
            timeout=TMUX_INJECT_TIMEOUT_S,
        )
        if result.returncode != 0:
            logger.error(
                "[Bridge] tmux send-keys Enter failed: %s",
                result.stderr.decode(),
            )
            return False

        return True
    except subprocess.TimeoutExpired:
        logger.error("[Bridge] tmux send-keys timed out")
        return False
    except FileNotFoundError:
        logger.error("[Bridge] tmux not found — is it installed?")
        return False


def _inject_message(session_name: str, text: str) -> dict:
    """Inject a message into the local CC session.

    Strategy:
    1. If tmux session exists → inject directly via send-keys
    2. Otherwise → write to inbox file for manual pickup
    """
    if _tmux_has_session(session_name):
        if _tmux_send(session_name, text):
            logger.info(
                "[Bridge] Injected %d chars into tmux session '%s'",
                len(text),
                session_name,
            )
            return {"ok": True, "method": "tmux", "session": session_name}
        else:
            logger.warning(
                "[Bridge] tmux inject failed for '%s', writing to inbox",
                session_name,
            )

    # Fallback: write to inbox file
    inbox_file = INBOX_DIR / f"{session_name}.txt"
    try:
        with open(inbox_file, "a") as f:
            f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            f.write(text)
            f.write("\n\n")
        logger.info(
            "[Bridge] Wrote %d chars to inbox %s",
            len(text),
            inbox_file,
        )
        return {"ok": True, "method": "inbox", "path": str(inbox_file)}
    except OSError as exc:
        logger.error("[Bridge] Inbox write failed: %s", exc)
        return {"ok": False, "error": str(exc)}


# ── HTTP Handlers ───────────────────────────────────────────────────────────


async def handle_health(_request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response(
        {
            "status": "ok",
            "machine": "local",
            "timestamp": time.time(),
        }
    )


async def handle_message(request: web.Request) -> web.Response:
    """Receive a message from the VPS and inject into local CC session."""
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response(
            {"ok": False, "error": "invalid json"},
            status=400,
        )

    text = data.get("text", "").strip()
    session_name = data.get("session_name", "").strip()

    if not text:
        return web.json_response(
            {"ok": False, "error": "missing text"},
            status=400,
        )
    if not session_name:
        return web.json_response(
            {"ok": False, "error": "missing session_name"},
            status=400,
        )

    # Run injection in executor to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, lambda: _inject_message(session_name, text)
    )

    status_code = 200 if result.get("ok") else 500
    return web.json_response(result, status=status_code)


async def handle_status(_request: web.Request) -> web.Response:
    """Status endpoint showing active tmux sessions and inbox state."""
    sessions = []
    try:
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        if result.returncode == 0:
            sessions = [s.strip() for s in result.stdout.splitlines() if s.strip()]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    inbox_files = list(INBOX_DIR.glob("*.txt"))

    return web.json_response(
        {
            "machine": "local",
            "tmux_sessions": sessions,
            "inbox_files": [f.name for f in inbox_files],
            "inbox_dir": str(INBOX_DIR),
            "timestamp": time.time(),
        }
    )


# ── Server ──────────────────────────────────────────────────────────────────


def create_app() -> web.Application:
    """Create the aiohttp application."""
    app = web.Application()
    app.router.add_get("/health", handle_health)
    app.router.add_post("/message", handle_message)
    app.router.add_get("/status", handle_status)
    return app


if __name__ == "__main__":
    print(f"[LocalBridge] Starting server on 0.0.0.0:{PORT}")
    print(f"[LocalBridge] Inbox directory: {INBOX_DIR}")
    print(f"[LocalBridge] Health: http://0.0.0.0:{PORT}/health")
    print(f"[LocalBridge] Status: http://0.0.0.0:{PORT}/status")
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=PORT, print=None)
