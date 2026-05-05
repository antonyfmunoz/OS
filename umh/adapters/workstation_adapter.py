"""Workstation adapter — real local control implementation.

Manages local workstation state (apps, workspace, focus) in response
to lifecycle events. Config-driven — no hardcoded app paths.

This is a VPS-first implementation. Desktop features (OBS, VSCode
window focus) are config-gated and no-op when not available.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from umh.adapters.contracts import AdapterContext

logger = logging.getLogger(__name__)

_SUPPORTED_EVENTS = frozenset(
    {
        "open_day_started",
        "ritual_step_executed",
        "close_day_started",
        "ritual_completed",
    }
)

# ─── Workspace state persistence ──────────────────────────────────────

_WORKSPACE_STATE_DIR = Path("/opt/OS/umh/.substrate_sandbox")
_WORKSPACE_STATE_FILE = _WORKSPACE_STATE_DIR / "workspace_state.json"


def _load_workspace_state() -> dict[str, Any]:
    """Load persisted workspace state from disk."""
    try:
        if _WORKSPACE_STATE_FILE.exists():
            return json.loads(_WORKSPACE_STATE_FILE.read_text())
    except Exception:
        logger.exception("[WorkstationAdapter] Failed to load workspace state")
    return {}


def _save_workspace_state(state: dict[str, Any]) -> None:
    """Persist workspace state to disk."""
    try:
        _WORKSPACE_STATE_DIR.mkdir(parents=True, exist_ok=True)
        _WORKSPACE_STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))
    except Exception:
        logger.exception("[WorkstationAdapter] Failed to save workspace state")


# ─── Config-driven app launch ─────────────────────────────────────────

_DEFAULT_OPEN_COMMANDS: list[dict[str, str]] = [
    # VPS-appropriate defaults — no desktop apps
    # Override via WORKSTATION_OPEN_COMMANDS env var (JSON list)
]


def _get_open_commands() -> list[dict[str, str]]:
    """Load app launch commands from env or defaults."""
    raw = os.getenv("WORKSTATION_OPEN_COMMANDS", "")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "[WorkstationAdapter] Invalid WORKSTATION_OPEN_COMMANDS JSON"
            )
    return _DEFAULT_OPEN_COMMANDS


def _run_command(cmd: str, label: str) -> bool:
    """Execute a shell command safely. Returns True on success."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            logger.info("[WorkstationAdapter] %s: ok", label)
            return True
        else:
            logger.warning(
                "[WorkstationAdapter] %s: exit %d — %s",
                label,
                result.returncode,
                result.stderr.strip()[:200],
            )
            return False
    except subprocess.TimeoutExpired:
        logger.warning("[WorkstationAdapter] %s: timed out", label)
        return False
    except Exception:
        logger.exception("[WorkstationAdapter] %s: failed", label)
        return False


class WorkstationAdapter:
    """Manages local workstation lifecycle in response to session events.

    Config-driven — reads WORKSTATION_OPEN_COMMANDS from env.
    No-ops gracefully when commands are not configured (VPS mode).
    """

    def supports(self, event_type: str) -> bool:
        return event_type in _SUPPORTED_EVENTS

    def handle(self, event: Any, context: AdapterContext) -> None:
        """Dispatch to the appropriate workstation action. Never raises."""
        try:
            etype = event.event_type

            if etype == "open_day_started":
                self._open_workspace(event, context)
            elif etype == "ritual_step_executed":
                self._step_action(event, context)
            elif etype == "close_day_started":
                self._save_state(event, context)
            elif etype == "ritual_completed":
                self._finalize(event, context)

            logger.info(
                "[WorkstationAdapter] %s handled (correlation=%s)",
                etype,
                context.correlation_id,
            )
        except Exception:
            logger.exception(
                "[WorkstationAdapter] Failed on %s (correlation=%s)",
                event.event_type,
                context.correlation_id,
            )

    def _open_workspace(self, event: Any, context: AdapterContext) -> None:
        """Launch configured apps and restore workspace state."""
        # Restore previous state if exists
        prev_state = _load_workspace_state()
        if prev_state:
            logger.info(
                "[WorkstationAdapter] Restored workspace state: %d keys",
                len(prev_state),
            )

        # Launch configured apps
        commands = _get_open_commands()
        for cmd_entry in commands:
            cmd = cmd_entry.get("cmd", "")
            label = cmd_entry.get("label", cmd[:30])
            if cmd:
                _run_command(cmd, label)

        # Record session start
        _save_workspace_state(
            {
                "session_id": context.runtime_session_id,
                "started_at": context.state_snapshot.get("timestamp", ""),
                "correlation_id": context.correlation_id,
                "status": "active",
            }
        )

    def _step_action(self, event: Any, context: AdapterContext) -> None:
        """Optional per-step action (focus window, switch context)."""
        # No-op by default on VPS — desktop environments can override
        payload = event.payload if hasattr(event, "payload") else {}
        step_name = payload.get("step_name", "")
        logger.debug("[WorkstationAdapter] Step: %s (no-op on VPS)", step_name)

    def _save_state(self, event: Any, context: AdapterContext) -> None:
        """Persist current workspace state before close."""
        current = _load_workspace_state()
        current["status"] = "closing"
        current["close_started_at"] = context.state_snapshot.get("timestamp", "")
        _save_workspace_state(current)

    def _finalize(self, event: Any, context: AdapterContext) -> None:
        """Mark workspace as closed."""
        current = _load_workspace_state()
        current["status"] = "closed"
        _save_workspace_state(current)
