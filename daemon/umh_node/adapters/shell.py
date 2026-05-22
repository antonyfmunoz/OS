"""Shell adapter — executes commands on the local machine."""

from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any

logger = logging.getLogger(__name__)


class ShellAdapter:
    """Executes shell and PowerShell commands locally."""

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        command = params.get("command", "")
        timeout = params.get("timeout", 30)
        cwd = params.get("cwd")

        if not command:
            return {"success": False, "error": "no command provided"}

        if operation == "shell.powershell" and sys.platform == "win32":
            args = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
        elif operation == "shell.query":
            args = self._build_args(command)
            timeout = min(timeout, 10)
        else:
            args = self._build_args(command)

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                shell=(sys.platform != "win32"),
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[-10000:],
                "stderr": result.stderr[-5000:],
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"command timed out after {timeout}s"}
        except Exception as exc:
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    def _build_args(self, command: str) -> list[str] | str:
        if sys.platform == "win32":
            return ["cmd", "/c", command]
        return command
