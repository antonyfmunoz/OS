"""Phase 76 CLI adapter — safe subprocess execution.

Executes approved CLI commands through subprocess with:
  - No shell=True
  - Timeout enforcement
  - stdout/stderr capture
  - Safe command allowlist
  - Dangerous command blocklist

All execution goes through the governed path — this adapter
never decides whether to execute.  It only executes what
governance has already approved.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from typing import Any

from umh.adapters.mvp_contract import (
    AdapterRequest,
    AdapterResult,
    AdapterStatus,
    MVPAdapter,
)

_SAFE_COMMANDS = frozenset(
    {
        "pwd",
        "ls",
        "echo",
        "cat",
        "head",
        "tail",
        "wc",
        "date",
        "whoami",
        "hostname",
        "uname",
        "python3",
        "pip3",
        "git",
        "find",
        "grep",
        "which",
        "df",
        "du",
        "free",
        "uptime",
        "env",
        "printenv",
    }
)

_DANGEROUS_PATTERNS = frozenset(
    {
        "rm -rf /",
        "rm -rf /*",
        "sudo",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "mkfs",
        "dd if=",
        ":(){ :|:",
        "> /dev/sd",
        "chmod -R 777 /",
        "chown -R",
    }
)

_DANGEROUS_PIPES = frozenset(
    {
        "curl|bash",
        "curl|sh",
        "wget|bash",
        "wget|sh",
    }
)


def _is_dangerous(command: str) -> str | None:
    """Return reason if command is dangerous, else None."""
    lower = command.lower().strip()
    for pattern in _DANGEROUS_PATTERNS:
        if pattern in lower:
            return f"Blocked dangerous pattern: {pattern}"
    normalized = lower.replace(" ", "")
    for pipe in _DANGEROUS_PIPES:
        if pipe in normalized:
            return f"Blocked dangerous pipe pattern: {pipe}"
    return None


def _is_safe_command(args: list[str]) -> bool:
    """Check if the base command is in the safe allowlist."""
    if not args:
        return False
    base = args[0].split("/")[-1]
    return base in _SAFE_COMMANDS


class CLIAdapter:
    """Executes CLI commands via subprocess (no shell=True)."""

    @property
    def name(self) -> str:
        return "cli"

    @property
    def supported_capabilities(self) -> frozenset[str]:
        return frozenset({"cli.command"})

    @property
    def supported_environments(self) -> frozenset[str]:
        return frozenset({"local", "vps", "sandbox"})

    def validate(self, request: AdapterRequest) -> AdapterResult | None:
        command = request.inputs.get("command", "")
        if not command or not command.strip():
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.VALIDATION_FAILED,
                error="Empty command",
            )

        danger = _is_dangerous(command)
        if danger:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.DENIED,
                error=danger,
            )

        try:
            args = shlex.split(command)
        except ValueError as e:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.VALIDATION_FAILED,
                error=f"Cannot parse command: {e}",
            )

        if not args:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.VALIDATION_FAILED,
                error="Empty command after parsing",
            )

        if shutil.which(args[0]) is None:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.VALIDATION_FAILED,
                error=f"Command not found: {args[0]}",
            )

        return None

    def execute(self, request: AdapterRequest) -> AdapterResult:
        command = request.inputs.get("command", "")
        timeout_s = request.constraints.get("timeout_s", 30)

        try:
            args = shlex.split(command)
        except ValueError as e:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.FAILURE,
                error=f"Parse error: {e}",
            )

        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                cwd=request.inputs.get("cwd", None),
            )
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.SUCCESS if proc.returncode == 0 else AdapterStatus.FAILURE,
                output={
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout[:10000],
                    "stderr": proc.stderr[:5000],
                },
                error=proc.stderr[:500] if proc.returncode != 0 else None,
                metadata={"command": command, "timeout_s": timeout_s},
            )
        except subprocess.TimeoutExpired:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.TIMEOUT,
                error=f"Command timed out after {timeout_s}s",
                metadata={"command": command},
            )
        except Exception as e:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.FAILURE,
                error=str(e),
                metadata={"command": command},
            )


def is_safe_command(command: str) -> bool:
    """Check if a command string uses only safe-listed base commands."""
    try:
        args = shlex.split(command)
    except ValueError:
        return False
    return _is_safe_command(args)
