"""Tmux adapter — governed session inspection. No killing by default."""

from __future__ import annotations

import re
import subprocess
from typing import Any

from services.umh.adapters.base import BaseAdapter
from services.umh.governance.risk_classes import RiskClass

_DEFAULT_TIMEOUT = 10


class TmuxAdapter(BaseAdapter):
    """Tmux session inspection with kill protection.

    list_sessions, inspect — always allowed.
    kill — denied unless explicitly assigned.
    send_keys — denied by default (could trigger arbitrary commands).
    """

    _DENIED_OPERATIONS: frozenset[str] = frozenset({
        "kill_session", "kill_server", "kill_window", "kill_pane",
        "send_keys", "send_prefix",
    })

    def __init__(self, timeout: int = _DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "tmux"

    def classify_risk(self, operation: str, params: dict[str, Any]) -> RiskClass:
        if operation in ("list_sessions", "list_windows", "inspect", "capture_pane"):
            return RiskClass.READ_ONLY
        if operation in ("kill_session", "kill_server", "kill_window", "kill_pane"):
            return RiskClass.IRREVERSIBLE_WRITE
        if operation == "send_keys":
            return RiskClass.SECURITY_SENSITIVE
        return RiskClass.REVERSIBLE_WRITE

    def _execute_impl(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        if operation == "list_sessions":
            return self._run_tmux(["tmux", "list-sessions", "-F",
                                   "#{session_name}:#{session_windows}:#{session_attached}"])
        if operation == "list_windows":
            session = params.get("session", "")
            if not session:
                raise ValueError("list_windows requires a session name")
            return self._run_tmux(["tmux", "list-windows", "-t", session, "-F",
                                   "#{window_index}:#{window_name}:#{window_active}"])
        if operation == "inspect":
            session = params.get("session", "")
            return self._inspect_session(session)
        if operation == "capture_pane":
            target = params.get("target", "")
            if not target:
                raise ValueError("capture_pane requires a target (session:window.pane)")
            return self._run_tmux(["tmux", "capture-pane", "-t", target, "-p"])
        raise ValueError(f"unknown tmux operation: {operation}")

    def _inspect_session(self, session: str) -> dict[str, Any]:
        if not session:
            return self._run_tmux(["tmux", "info"])
        info = self._run_tmux(["tmux", "display-message", "-t", session, "-p",
                                "name=#{session_name} windows=#{session_windows} "
                                "attached=#{session_attached} created=#{session_created}"])
        windows = self._run_tmux(["tmux", "list-windows", "-t", session, "-F",
                                   "#{window_index}:#{window_name}:#{window_active}"])
        return {
            "session": session,
            "info": info.get("stdout", ""),
            "windows": windows.get("stdout", ""),
            "success": info.get("success", False),
        }

    def _run_tmux(self, args: list[str]) -> dict[str, Any]:
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            return {
                "command": " ".join(args),
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "success": result.returncode == 0,
            }
        except FileNotFoundError:
            return {
                "command": " ".join(args),
                "returncode": -1,
                "stdout": "",
                "stderr": "tmux not found",
                "success": False,
            }
