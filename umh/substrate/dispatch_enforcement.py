"""
Dispatch Enforcement — physical enforcement of execution control decisions.

Sits BETWEEN the advisory output of resolve_permission() / ExecutionControlResult
and the actual execution boundary (subprocess, HTTP, LLM call, etc.).

This module does NOT make policy decisions. It enforces them:
- Denied actions are blocked before execution (never reach subprocess/network)
- Rewritten commands replace raw commands at the execution boundary
- Timeouts are physically enforced via threading deadline
- Every execution produces a structured ExecutionResult for tracing

Design rules:
- No policy logic — only enforcement
- No new execution capability — wraps existing boundaries
- Structured results — every path produces an ExecutionResult
- Centralized timeout — single implementation, not scattered per-boundary
- Never raises — returns structured failure instead

Called by execution boundaries (local_executor, station_daemon, pipeline).
Never called by policy/control code.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from umh.substrate.discord_output_policy import (
    FinalResolution,
    PermissionDecision,
)
from umh.substrate.execution_control import ExecutionControlResult


# ─── Constants ───────────────────────────────────────────────────────────────

_LOG_PREFIX = "[dispatch_enforcement]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ─── Enums ───────────────────────────────────────────────────────────────────


class ExecutionStatus(str, Enum):
    """Outcome of an enforced execution."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DENIED = "denied"
    TIMED_OUT = "timed_out"


# ─── Result Model ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ExecutionResult:
    """Structured outcome of dispatch enforcement.

    Every execution boundary produces one of these. Easy to log,
    easy to feed into event-spine integration later.

    Attributes:
        status: Outcome category.
        executed_command: The command that was actually run (may be rewritten).
        original_command: The raw command before any rewriting.
        timeout_seconds: Timeout that was enforced, or None.
        exit_code: Process exit code if applicable, or None.
        stdout: Truncated stdout if applicable.
        stderr: Truncated stderr if applicable.
        control_reason: Why the action was denied/tightened, from upstream.
        boundary: Name of the execution boundary that produced this result.
        elapsed_seconds: Wall-clock time for execution.
        detail: Additional structured data from the execution.
        return_value: Raw return value from enforced_call callables.
            Preserved intact for callers. Not included in to_dict()
            to keep logs bounded — use detail for loggable summaries.
    """

    status: ExecutionStatus
    executed_command: str | None = None
    original_command: str | None = None
    timeout_seconds: int | None = None
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    control_reason: str | None = None
    boundary: str = ""
    elapsed_seconds: float = 0.0
    detail: dict[str, Any] = field(default_factory=dict)
    return_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a flat dict for logging and event-spine.

        Note: return_value is intentionally excluded — it may be an
        arbitrarily large structured object. Use detail for loggable data.
        """
        return {
            "status": self.status.value,
            "executed_command": self.executed_command,
            "original_command": self.original_command,
            "timeout_seconds": self.timeout_seconds,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "control_reason": self.control_reason,
            "boundary": self.boundary,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "detail": self.detail,
        }


# ─── Truncation ──────────────────────────────────────────────────────────────

_MAX_OUTPUT_CHARS = 4_000


def _truncate(s: str | None) -> str | None:
    """Truncate output to bounded size for logging."""
    if s is None:
        return None
    if len(s) <= _MAX_OUTPUT_CHARS:
        return s
    return s[:_MAX_OUTPUT_CHARS] + "…[truncated]"


# ─── Core: Deny Check ───────────────────────────────────────────────────────


def check_denied(decision: PermissionDecision) -> ExecutionResult | None:
    """Check if a PermissionDecision is denied. Returns ExecutionResult if so.

    Call this FIRST at every execution boundary. If it returns non-None,
    short-circuit immediately — do not execute.

    Args:
        decision: The PermissionDecision from resolve_permission().

    Returns:
        ExecutionResult with status=DENIED if the action is denied, else None.
    """
    if decision.final_resolution == FinalResolution.DENY:
        reason = decision.constraint_reason or "denied by policy"
        _log(f"DENIED: {reason}")
        return ExecutionResult(
            status=ExecutionStatus.DENIED,
            control_reason=reason,
        )
    return None


# ─── Core: Resolve Effective Command ────────────────────────────────────────


def resolve_command(
    raw_command: str,
    decision: PermissionDecision,
) -> str:
    """Resolve the effective command to execute.

    If execution control produced a rewritten_command, return that.
    Otherwise return the raw command unchanged.

    The raw command is NEVER executed when a rewrite exists.

    Args:
        raw_command: The original command string.
        decision: The PermissionDecision containing rewrite info.

    Returns:
        The command string that should actually be executed.
    """
    if decision.rewritten_command is not None:
        _log(f"REWRITE: '{raw_command}' → '{decision.rewritten_command}'")
        return decision.rewritten_command
    return raw_command


# ─── Core: Enforced Subprocess Execution ────────────────────────────────────


def enforced_subprocess(
    argv: list[str],
    *,
    decision: PermissionDecision,
    raw_command: str = "",
    boundary: str = "subprocess",
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> ExecutionResult:
    """Execute a subprocess with full dispatch enforcement.

    This is the primary enforcement function for shell/process boundaries.
    It:
    1. Blocks denied actions immediately
    2. Enforces timeout_seconds from the control layer
    3. Returns structured ExecutionResult for every outcome

    Note: command rewriting is handled BEFORE calling this function.
    The caller is responsible for calling resolve_command() to get the
    effective command and building argv from it. This function does not
    rewrite — it enforces timeout and captures results.

    Args:
        argv: Process argument vector (shell=False always).
        decision: The PermissionDecision from resolve_permission().
        raw_command: Original command string for audit trail.
        boundary: Name of the calling execution boundary.
        cwd: Working directory for the subprocess.
        env: Environment variables for the subprocess.

    Returns:
        ExecutionResult with full trace.
    """
    # Step 1: Deny check
    denied = check_denied(decision)
    if denied is not None:
        return ExecutionResult(
            status=ExecutionStatus.DENIED,
            original_command=raw_command or " ".join(argv),
            control_reason=denied.control_reason,
            boundary=boundary,
        )

    # Step 2: Resolve timeout
    timeout = decision.timeout_seconds
    executed_cmd = " ".join(argv)

    _log(f"EXECUTE: boundary={boundary} cmd='{executed_cmd}' timeout={timeout}s")

    # Step 3: Execute with enforced timeout
    start = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            shell=False,
            check=False,
            env=env,
        )
        elapsed = time.monotonic() - start

        status = (
            ExecutionStatus.SUCCEEDED
            if proc.returncode == 0
            else ExecutionStatus.FAILED
        )

        result = ExecutionResult(
            status=status,
            executed_command=executed_cmd,
            original_command=raw_command if raw_command != executed_cmd else None,
            timeout_seconds=timeout,
            exit_code=proc.returncode,
            stdout=_truncate(proc.stdout or ""),
            stderr=_truncate(proc.stderr or ""),
            boundary=boundary,
            elapsed_seconds=elapsed,
        )

        _log(
            f"RESULT: boundary={boundary} status={status.value} "
            f"exit_code={proc.returncode} elapsed={elapsed:.3f}s"
        )
        return result

    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        _log(f"TIMEOUT: boundary={boundary} cmd='{executed_cmd}' after {timeout}s")
        return ExecutionResult(
            status=ExecutionStatus.TIMED_OUT,
            executed_command=executed_cmd,
            original_command=raw_command if raw_command != executed_cmd else None,
            timeout_seconds=timeout,
            control_reason=f"timed out after {timeout}s",
            boundary=boundary,
            elapsed_seconds=elapsed,
        )

    except Exception as exc:
        elapsed = time.monotonic() - start
        _log(f"ERROR: boundary={boundary} {type(exc).__name__}: {exc}")
        return ExecutionResult(
            status=ExecutionStatus.FAILED,
            executed_command=executed_cmd,
            original_command=raw_command if raw_command != executed_cmd else None,
            timeout_seconds=timeout,
            control_reason=f"{type(exc).__name__}: {exc}",
            boundary=boundary,
            elapsed_seconds=elapsed,
        )


# ─── Core: Enforced Callable Execution ──────────────────────────────────────


def enforced_call(
    fn: Callable[[], Any],
    *,
    decision: PermissionDecision,
    boundary: str = "callable",
    description: str = "",
) -> ExecutionResult:
    """Execute an arbitrary callable with dispatch enforcement.

    For non-subprocess boundaries (HTTP fetch, LLM call, webbrowser.open).
    Enforces deny-check and timeout via threading deadline.

    Args:
        fn: Zero-arg callable to execute.
        decision: The PermissionDecision from resolve_permission().
        boundary: Name of the calling execution boundary.
        description: Human-readable description of what fn does.

    Returns:
        ExecutionResult with full trace.
    """
    # Step 1: Deny check
    denied = check_denied(decision)
    if denied is not None:
        return ExecutionResult(
            status=ExecutionStatus.DENIED,
            control_reason=denied.control_reason,
            boundary=boundary,
            detail={"description": description} if description else {},
        )

    timeout = decision.timeout_seconds

    _log(f"CALL: boundary={boundary} desc='{description}' timeout={timeout}s")

    # Step 2: Execute with timeout via thread
    result_container: dict[str, Any] = {}
    error_container: dict[str, Any] = {}

    def _worker() -> None:
        try:
            result_container["value"] = fn()
        except Exception as exc:
            error_container["exc"] = exc

    start = time.monotonic()

    if timeout is None:
        # No timeout — run directly
        _worker()
        elapsed = time.monotonic() - start
    else:
        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        elapsed = time.monotonic() - start

        if thread.is_alive():
            _log(f"TIMEOUT: boundary={boundary} desc='{description}' after {timeout}s")
            return ExecutionResult(
                status=ExecutionStatus.TIMED_OUT,
                timeout_seconds=timeout,
                control_reason=f"timed out after {timeout}s",
                boundary=boundary,
                elapsed_seconds=elapsed,
                detail={"description": description} if description else {},
            )

    # Step 3: Process outcome
    if "exc" in error_container:
        exc = error_container["exc"]
        _log(f"ERROR: boundary={boundary} {type(exc).__name__}: {exc}")
        return ExecutionResult(
            status=ExecutionStatus.FAILED,
            timeout_seconds=timeout,
            control_reason=f"{type(exc).__name__}: {exc}",
            boundary=boundary,
            elapsed_seconds=elapsed,
            detail={"description": description} if description else {},
        )

    raw_value = result_container.get("value")

    # Build bounded detail for logging — never dump raw_value into logs
    log_detail: dict[str, Any] = {}
    if description:
        log_detail["description"] = description
    # Summarize the return type/size for observability without dumping content
    if raw_value is not None:
        summary = str(raw_value)
        log_detail["return_summary"] = (
            summary[:200] + "…" if len(summary) > 200 else summary
        )

    _log(f"RESULT: boundary={boundary} status=succeeded elapsed={elapsed:.3f}s")
    return ExecutionResult(
        status=ExecutionStatus.SUCCEEDED,
        timeout_seconds=timeout,
        boundary=boundary,
        elapsed_seconds=elapsed,
        detail=log_detail,
        return_value=raw_value,
    )


# ─── Structured Logging Helper ───────────────────────────────────────────────


def log_enforcement_trace(
    result: ExecutionResult,
    *,
    role: str = "",
) -> dict[str, Any]:
    """Produce a structured log entry for dispatch enforcement.

    Returns a dict suitable for structured logging / event-spine.
    Does NOT perform I/O — caller decides where to send it.

    Args:
        result: The ExecutionResult from enforced execution.
        role: Session role that triggered the execution.

    Returns:
        Structured trace dict.
    """
    trace = {
        "layer": "dispatch_enforcement",
        "boundary": result.boundary,
        "role": role,
        "original_command": result.original_command,
        "executed_command": result.executed_command,
        "timeout_seconds": result.timeout_seconds,
        "status": result.status.value,
        "exit_code": result.exit_code,
        "control_reason": result.control_reason,
        "elapsed_seconds": round(result.elapsed_seconds, 3),
    }
    return {k: v for k, v in trace.items() if v is not None}


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "ExecutionStatus",
    "ExecutionResult",
    "check_denied",
    "resolve_command",
    "enforced_subprocess",
    "enforced_call",
    "log_enforcement_trace",
]
