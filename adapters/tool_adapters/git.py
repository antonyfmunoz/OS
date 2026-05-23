"""Git adapter — governed git operations. Read-only by default."""

from __future__ import annotations

import re
import subprocess
from typing import Any

from adapters.tool_adapters.base import BaseAdapter
from substrate.governance.risk_classes import RiskClass

_READ_OPS = frozenset(
    {"status", "diff", "log", "branch", "show", "blame", "shortlog", "tag_list", "remote_list"}
)
_WRITE_OPS = frozenset(
    {
        "commit",
        "push",
        "merge",
        "rebase",
        "reset",
        "checkout",
        "stash",
        "tag_create",
        "branch_create",
    }
)

_DEFAULT_TIMEOUT = 30


class GitAdapter(BaseAdapter):
    """Git operations with destructive-command blocking.

    status, diff, log, branch, show, blame — always allowed.
    commit, push — denied unless explicitly assigned.
    force-push, reset --hard, clean -f — permanently denied.
    """

    _DENIED_OPERATIONS: frozenset[str] = frozenset(
        {
            "push",
            "commit",
            "merge",
            "rebase",
            "reset",
            "checkout",
            "stash",
            "tag_create",
            "branch_create",
        }
    )

    _DENIED_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(r"--force\b"),
        re.compile(r"--hard\b"),
        re.compile(r"\bclean\s+-[a-zA-Z]*f"),
        re.compile(r"\breset\s+--hard\b"),
    )

    def __init__(self, repo_path: str = "/opt/OS", timeout: int = _DEFAULT_TIMEOUT) -> None:
        self._repo_path = repo_path
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "git"

    def classify_risk(self, operation: str, params: dict[str, Any]) -> RiskClass:
        if operation in _READ_OPS:
            return RiskClass.READ_ONLY
        if operation in _WRITE_OPS:
            return RiskClass.REVERSIBLE_WRITE
        return RiskClass.IRREVERSIBLE_WRITE

    def _execute_impl(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        if operation == "status":
            return self._run_git(["git", "status", "--porcelain"])
        if operation == "diff":
            args = ["git", "diff"]
            if params.get("staged"):
                args.append("--cached")
            if params.get("target"):
                args.append(params["target"])
            return self._run_git(args)
        if operation == "log":
            count = params.get("count", 10)
            fmt = params.get("format", "--oneline")
            return self._run_git(["git", "log", fmt, f"-{count}"])
        if operation == "branch":
            args = ["git", "branch"]
            if params.get("all"):
                args.append("-a")
            return self._run_git(args)
        if operation == "show":
            ref = params.get("ref", "HEAD")
            return self._run_git(["git", "show", "--stat", ref])
        if operation == "blame":
            path = params.get("path", "")
            if not path:
                raise ValueError("blame requires a path")
            return self._run_git(["git", "blame", "--line-porcelain", path])
        if operation == "shortlog":
            return self._run_git(["git", "shortlog", "-sn", "--all"])
        if operation == "tag_list":
            return self._run_git(["git", "tag", "-l"])
        if operation == "remote_list":
            return self._run_git(["git", "remote", "-v"])
        raise ValueError(f"unknown git operation: {operation}")

    def _run_git(self, args: list[str]) -> dict[str, Any]:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=self._timeout,
            cwd=self._repo_path,
        )
        return {
            "command": " ".join(args),
            "returncode": result.returncode,
            "stdout": result.stdout[:200_000],
            "stderr": result.stderr[:50_000],
            "success": result.returncode == 0,
        }
