"""Shell adapter — governed command execution with destructive-command blocking."""

from __future__ import annotations

import re
import subprocess
from typing import Any

from services.umh.adapters.base import BaseAdapter
from services.umh.governance.risk_classes import RiskClass

_DESTRUCTIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f", re.IGNORECASE),
    re.compile(r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bdd\s+if=", re.IGNORECASE),
    re.compile(r"\b(cat|strings|xxd)\s+/dev/(sd|nvme|hd)", re.IGNORECASE),
    re.compile(r"\bshred\b"),
    re.compile(r"\bwipe\b"),
    # credential / secret dumping
    re.compile(r"\bcat\s+.*(/\.ssh/|/\.gnupg/|/\.aws/|credentials|\.env\b)", re.IGNORECASE),
    re.compile(r"\bprintenv\b"),
    re.compile(r"\benv\s*$"),
    # package management destructive
    re.compile(r"\b(apt|apt-get|yum|dnf|pip|npm)\s+(remove|uninstall|purge)\b", re.IGNORECASE),
    re.compile(r"\bpip\s+uninstall\b", re.IGNORECASE),
    re.compile(r"\bnpm\s+uninstall\b", re.IGNORECASE),
    # firewall / security
    re.compile(r"\b(iptables|ufw|firewalld|nftables)\b", re.IGNORECASE),
    re.compile(r"\bpasswd\b"),
    re.compile(r"\busermod\b"),
    re.compile(r"\buserdel\b"),
    re.compile(r"\bgroupdel\b"),
    # daemon management
    re.compile(r"\bsystemctl\s+(stop|disable|mask|kill)\b", re.IGNORECASE),
    re.compile(r"\bservice\s+\S+\s+stop\b", re.IGNORECASE),
    re.compile(r"\bkillall\b"),
    re.compile(r"\bpkill\s+-9\b"),
    # destructive git (handled by git adapter, but block here too)
    re.compile(r"\bgit\s+push\s+--force\b", re.IGNORECASE),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
    re.compile(r"\bgit\s+clean\s+-[a-zA-Z]*f", re.IGNORECASE),
    # network exfiltration
    re.compile(r"\bcurl\s+.*--upload-file\b", re.IGNORECASE),
    re.compile(r"\bwget\s+.*--post-data\b", re.IGNORECASE),
    re.compile(r"\bnc\s+-[a-zA-Z]*l", re.IGNORECASE),
    # shutdown / reboot
    re.compile(r"\b(shutdown|reboot|halt|poweroff|init\s+[06])\b", re.IGNORECASE),
)

_READ_ONLY_PREFIXES: tuple[str, ...] = (
    "ls", "cat", "head", "tail", "wc", "file", "stat", "du", "df",
    "find", "grep", "awk", "sed", "sort", "uniq", "cut", "tr",
    "date", "uptime", "whoami", "hostname", "uname", "id",
    "ps", "top", "htop", "free", "vmstat", "iostat",
    "python3 -c", "python3 -m py_compile",
    "ruff", "black", "mypy", "flake8", "pylint",
    "docker ps", "docker logs", "docker inspect",
)

_MAX_OUTPUT_BYTES = 500_000
_DEFAULT_TIMEOUT = 30


class ShellAdapter(BaseAdapter):
    """Shell command execution with deny-pattern enforcement."""

    _DENIED_PATTERNS = _DESTRUCTIVE_PATTERNS

    def __init__(self, timeout: int = _DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "shell"

    def classify_risk(self, operation: str, params: dict[str, Any]) -> RiskClass:
        command = params.get("command", operation)
        stripped = command.strip()

        for prefix in _READ_ONLY_PREFIXES:
            if stripped.startswith(prefix):
                return RiskClass.READ_ONLY

        if any(p.search(command) for p in _DESTRUCTIVE_PATTERNS):
            return RiskClass.IRREVERSIBLE_WRITE

        if any(kw in command for kw in ("curl", "wget", "http", "ssh", "scp")):
            return RiskClass.EXTERNAL_COMMUNICATION

        return RiskClass.REVERSIBLE_WRITE

    def _execute_impl(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        command = params.get("command", operation)
        timeout = params.get("timeout", self._timeout)
        cwd = params.get("cwd")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            stdout = result.stdout[:_MAX_OUTPUT_BYTES] if result.stdout else ""
            stderr = result.stderr[:_MAX_OUTPUT_BYTES] if result.stderr else ""

            return {
                "command": command,
                "returncode": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "success": result.returncode == 0,
            }

        except subprocess.TimeoutExpired:
            raise TimeoutError(f"command timed out after {timeout}s: {command}")
