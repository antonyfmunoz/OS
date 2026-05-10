"""
execution.py — Restricted execution contexts for agent workloads.

Goal
----
When an agent runs code or commands, the security layer should be able
to say "run this with *at most* these resources, only within this path
scope, and no longer than this many seconds." This module provides that.

Two concerns:

1. **Filesystem scoping** — a context declares a list of path prefixes
   the running code is allowed to read/write. Any access outside the
   scope raises. This is a *cooperative* guard: tools that honor the
   context (action_system, file I/O helpers) ask the context before
   touching a path. It is not a kernel-level jail.

2. **Command execution sandbox** — for `run_command` / `run_script`,
   this module provides `RestrictedExecutor.run()` which:
     - hard-timeouts via subprocess.TimeoutExpired
     - restricts cwd to the allowed scope
     - strips the environment to a minimal allow-list
     - blocks shell metacharacters unless explicit `shell=True`
     - captures stdout + stderr bounded by max_output_bytes

Why not containers
------------------
Containers are the right answer long-term. For single-tenant founder-phase
OS, process-level restrictions + path scoping + timeouts cover the
realistic threat (runaway agent, infinite loop, accidental rm -rf in the
wrong dir) without adding Docker-in-Docker complexity. Swap this module
for a container-backed one later without changing the SecurityContext
API.

Usage
-----
    from core.security.execution import ExecutionContext, RestrictedExecutor

    ctx = ExecutionContext(
        allowed_paths=["/opt/OS/data/sandboxes/sbx-1"],
        denied_paths=["/opt/OS/eos_ai", "/opt/OS/core"],
        timeout_seconds=30,
        max_output_bytes=1_000_000,
    )

    # Filesystem guard
    ctx.check_path("/opt/OS/data/sandboxes/sbx-1/foo.py", mode="w")  # ok
    ctx.check_path("/opt/OS/eos_ai/memory.py", mode="w")             # raises

    # Command sandbox
    exe = RestrictedExecutor(ctx)
    result = exe.run(["python3", "script.py"], cwd="/opt/OS/data/sandboxes/sbx-1")
"""

from __future__ import annotations

import os
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Literal, Sequence

PathMode = Literal["r", "w", "x"]

# Minimal env the restricted executor hands to subprocesses.
_MINIMAL_ENV_ALLOW = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TERM",
    "PYTHONPATH",
)

# Characters we refuse to pass through without explicit shell=True.
_SHELL_META = set("|&;<>()$`\\\"'*?[]{}!#~")

DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_OUTPUT_BYTES = 1_000_000


class ExecutionDenied(PermissionError):
    """Raised when a restricted context refuses an action."""


@dataclass
class ExecutionContext:
    """Declarative set of restrictions for a run of code.

    Fields
    ------
    name               — human label ("agent:executor@sandbox-1")
    allowed_paths      — prefixes the context allows. If empty, ALL paths
                         are allowed (subject to denied_paths). An empty
                         allow-list is only sensible for a trusted run.
    denied_paths       — explicit deny prefixes — always win over allow.
    timeout_seconds    — hard wall-clock ceiling on any single command.
    max_output_bytes   — output captured from a command is truncated at
                         this size.
    allow_shell        — if False, shell metacharacters in command args
                         raise ExecutionDenied.
    allow_network      — informational flag; enforcement requires an
                         outer layer (container / firewall). Logged so
                         auditors can see the declared intent.
    env_allow_list     — env vars forwarded to subprocesses.
    """

    name: str = "default"
    allowed_paths: list[str] = field(default_factory=list)
    denied_paths: list[str] = field(default_factory=list)
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES
    allow_shell: bool = False
    allow_network: bool = True
    env_allow_list: tuple[str, ...] = _MINIMAL_ENV_ALLOW

    # ── Path guard ────────────────────────────────────────────────────

    def check_path(self, path: str | Path, *, mode: PathMode = "r") -> Path:
        """Raise ExecutionDenied if `path` is not allowed for `mode`.

        Returns the resolved absolute Path on success.
        """
        p = Path(path).resolve()
        p_str = str(p)

        for deny in self.denied_paths:
            if self._matches(p_str, deny):
                raise ExecutionDenied(
                    f"ctx {self.name}: {mode} on {p_str} denied by {deny}"
                )

        if self.allowed_paths:
            if not any(self._matches(p_str, allow) for allow in self.allowed_paths):
                raise ExecutionDenied(
                    f"ctx {self.name}: {mode} on {p_str} outside allowed_paths"
                )
        return p

    def may_path(self, path: str | Path, *, mode: PathMode = "r") -> bool:
        """Non-raising version of check_path."""
        try:
            self.check_path(path, mode=mode)
            return True
        except ExecutionDenied:
            return False

    @staticmethod
    def _matches(path_str: str, prefix: str) -> bool:
        pfx = str(Path(prefix).resolve())
        return path_str == pfx or path_str.startswith(pfx + os.sep)

    # ── Command pre-check ─────────────────────────────────────────────

    def check_command(
        self,
        command: Sequence[str] | str,
        *,
        shell: bool = False,
    ) -> None:
        """Refuse shell metacharacters unless shell=True AND allow_shell=True."""
        if shell:
            if not self.allow_shell:
                raise ExecutionDenied(
                    f"ctx {self.name}: shell=True not permitted (allow_shell=False)"
                )
            return
        tokens = [command] if isinstance(command, str) else list(command)
        for tok in tokens:
            if any(ch in _SHELL_META for ch in tok):
                raise ExecutionDenied(
                    f"ctx {self.name}: shell metachar in argument {tok!r} "
                    f"without shell=True"
                )

    # ── Env minimization ──────────────────────────────────────────────

    def scrubbed_env(self, extra: dict | None = None) -> dict:
        """Return a minimized env dict to hand to subprocess."""
        base: dict = {}
        for k in self.env_allow_list:
            if k in os.environ:
                base[k] = os.environ[k]
        if extra:
            base.update(extra)
        return base

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "allowed_paths": list(self.allowed_paths),
            "denied_paths": list(self.denied_paths),
            "timeout_seconds": self.timeout_seconds,
            "max_output_bytes": self.max_output_bytes,
            "allow_shell": self.allow_shell,
            "allow_network": self.allow_network,
            "env_allow_list": list(self.env_allow_list),
        }


# ─── Executor ───────────────────────────────────────────────────────────────


@dataclass
class ExecutionResult:
    command: Sequence[str] | str
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    truncated: bool = False


class RestrictedExecutor:
    """Runs commands under an ExecutionContext.

    The executor is intentionally thin — it's just `subprocess.run` with
    the context's guards applied before and after. No process namespace
    magic. That belongs in a container layer.
    """

    def __init__(self, ctx: ExecutionContext) -> None:
        self.ctx = ctx

    def run(
        self,
        command: Sequence[str] | str,
        *,
        cwd: str | Path | None = None,
        shell: bool = False,
        extra_env: dict | None = None,
        stdin: str | None = None,
    ) -> ExecutionResult:
        self.ctx.check_command(command, shell=shell)
        if cwd is not None:
            self.ctx.check_path(cwd, mode="x")

        env = self.ctx.scrubbed_env(extra_env)
        start = time.monotonic()
        timed_out = False
        try:
            proc = subprocess.run(
                command,
                shell=shell,
                cwd=str(cwd) if cwd else None,
                env=env,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=self.ctx.timeout_seconds,
                check=False,
            )
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            returncode = proc.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = (
                (exc.stdout or b"").decode("utf-8", errors="replace")
                if isinstance(exc.stdout, bytes)
                else (exc.stdout or "")
            )
            stderr = (
                (exc.stderr or b"").decode("utf-8", errors="replace")
                if isinstance(exc.stderr, bytes)
                else (exc.stderr or "")
            )
            stderr = (stderr or "") + f"\n[timeout after {self.ctx.timeout_seconds}s]"
            returncode = -1
        duration = round(time.monotonic() - start, 3)

        truncated = False
        if len(stdout.encode("utf-8")) > self.ctx.max_output_bytes:
            stdout = stdout[: self.ctx.max_output_bytes] + "\n[...truncated]"
            truncated = True
        if len(stderr.encode("utf-8")) > self.ctx.max_output_bytes:
            stderr = stderr[: self.ctx.max_output_bytes] + "\n[...truncated]"
            truncated = True

        return ExecutionResult(
            command=command,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            timed_out=timed_out,
            truncated=truncated,
        )


# ─── Context manager helper ─────────────────────────────────────────────────


@contextmanager
def restricted_context(
    *,
    name: str = "scoped",
    allowed_paths: Sequence[str] = (),
    denied_paths: Sequence[str] = (),
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    allow_shell: bool = False,
) -> Iterator[ExecutionContext]:
    """Syntactic sugar for one-shot restricted execution.

    Usage:
        with restricted_context(allowed_paths=["/tmp/scope"]) as ctx:
            RestrictedExecutor(ctx).run(["ls", "/tmp/scope"])
    """
    ctx = ExecutionContext(
        name=name,
        allowed_paths=list(allowed_paths),
        denied_paths=list(denied_paths),
        timeout_seconds=timeout_seconds,
        allow_shell=allow_shell,
    )
    yield ctx


__all__ = [
    "ExecutionContext",
    "ExecutionDenied",
    "ExecutionResult",
    "RestrictedExecutor",
    "restricted_context",
    "DEFAULT_TIMEOUT_SECONDS",
    "DEFAULT_MAX_OUTPUT_BYTES",
]
