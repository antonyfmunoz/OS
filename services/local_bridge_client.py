"""
Local Bridge Client — forwards Discord messages to Antony's local machine.

When Antony is at his PC (Windows/WSL via Tailscale), Discord messages route
to a Claude Code session running locally instead of the VPS tmux sessions.

Architecture:
    Discord message arrives on VPS
    → forward_to_local() checks bridge health (GET /health, 2s timeout)
    → If healthy: POST /message with {text, session_name}
    → If unhealthy: returns False, caller falls back to VPS tmux

This module never raises. Every failure returns False for graceful degradation.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import requests

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
load_dotenv(_REPO_ROOT / "eos_ai" / ".env")

logger = logging.getLogger(__name__)

# ── Configuration ───────────────────────────────────────────────────────────

_BRIDGE_IP = os.getenv("EOS_LOCAL_BRIDGE_IP", "100.74.199.102")
_BRIDGE_PORT = int(os.getenv("EOS_LOCAL_BRIDGE_PORT", "8766"))
_BRIDGE_ENABLED = os.getenv("EOS_LOCAL_BRIDGE_ENABLED", "0").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

_HEALTH_TIMEOUT_S = 2.0
_SEND_TIMEOUT_S = 10.0

_BASE_URL = f"http://{_BRIDGE_IP}:{_BRIDGE_PORT}"


def is_bridge_enabled() -> bool:
    """Check if local bridge routing is enabled via env var."""
    return _BRIDGE_ENABLED


def check_health() -> bool:
    """Ping the local bridge health endpoint. Returns True if reachable."""
    if not _BRIDGE_ENABLED:
        return False
    try:
        resp = requests.get(
            f"{_BASE_URL}/health",
            timeout=_HEALTH_TIMEOUT_S,
        )
        return resp.status_code == 200
    except (requests.ConnectionError, requests.Timeout, OSError):
        return False
    except Exception:
        logger.debug("[LocalBridge] Unexpected health check error", exc_info=True)
        return False


def forward_to_local(text: str, session_name: str) -> bool:
    """Forward a message to the local bridge.

    Returns True if successfully forwarded, False otherwise.
    Caller should fall back to VPS tmux injection on False.
    """
    if not _BRIDGE_ENABLED:
        logger.debug("[LocalBridge] Disabled — skipping")
        return False

    if not text or not session_name:
        logger.warning("[LocalBridge] Empty text or session_name")
        return False

    # Health check first — fail fast if local machine unreachable
    if not check_health():
        logger.info("[LocalBridge] Health check failed — local unavailable")
        return False

    # Forward the message
    try:
        resp = requests.post(
            f"{_BASE_URL}/message",
            json={"text": text, "session_name": session_name},
            timeout=_SEND_TIMEOUT_S,
        )
        if resp.status_code == 200:
            logger.info(
                "[LocalBridge] Forwarded %d chars to %s on local machine",
                len(text),
                session_name,
            )
            return True
        else:
            logger.warning(
                "[LocalBridge] Forward failed — HTTP %d: %s",
                resp.status_code,
                resp.text[:200],
            )
            return False
    except (requests.ConnectionError, requests.Timeout, OSError) as exc:
        logger.info("[LocalBridge] Forward failed — %s", exc)
        return False
    except Exception:
        logger.warning("[LocalBridge] Unexpected forward error", exc_info=True)
        return False


def bridge_status() -> dict[str, Any]:
    """Return a status dict for diagnostics."""
    healthy = check_health() if _BRIDGE_ENABLED else False
    return {
        "enabled": _BRIDGE_ENABLED,
        "ip": _BRIDGE_IP,
        "port": _BRIDGE_PORT,
        "healthy": healthy,
        "base_url": _BASE_URL,
    }
