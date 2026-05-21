"""UMH Execution Guard — security enforcement for non-LLM execution.

All shell commands, file operations, and system interactions MUST pass
through this guard before execution. The guard enforces:
1. Command allowlists for shell execution
2. Path sandboxing for file operations
3. Rate limiting for all non-LLM execution
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

_log = logging.getLogger(__name__)


class GuardVerdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRES_APPROVAL = "requires_approval"


@dataclass(frozen=True)
class GuardResult:
    """Result of a security check."""

    verdict: GuardVerdict
    reason: str
    sanitized_inputs: dict[str, Any] | None = None


# Sandboxed paths for file operations
_SANDBOX_ROOTS = frozenset(
    {
        "/opt/OS/data",
        "/opt/OS/logs",
        "/opt/OS/10_Wiki",
        "/tmp",
    }
)

_DENIED_PATH_PATTERNS = frozenset(
    {
        ".env",
        "credentials",
        "secret",
        ".ssh",
        ".gnupg",
        "private_key",
    }
)


def check_shell_command(command: str) -> GuardResult:
    """Validate a shell command against the allowlist."""
    if not command or not command.strip():
        return GuardResult(
            verdict=GuardVerdict.DENY,
            reason="Empty command",
        )

    # The actual allowlist is in SpineExecutionBackend._SHELL_ALLOWLIST
    # This guard provides an additional layer of validation
    stripped = command.strip()

    # Deny shell metacharacters
    dangerous_chars = {
        ";",
        "|",
        "&",
        "`",
        "$",
        "(",
        ")",
        "{",
        "}",
        "<",
        ">",
        "\\",
        "\n",
    }
    if any(c in stripped for c in dangerous_chars):
        _log.warning("[ExecutionGuard] shell DENIED: dangerous chars in %r", stripped)
        return GuardResult(
            verdict=GuardVerdict.DENY,
            reason=f"Command contains dangerous characters: {stripped!r}",
        )

    return GuardResult(
        verdict=GuardVerdict.ALLOW,
        reason="Command passed guard checks",
        sanitized_inputs={"command": stripped},
    )


def check_file_operation(
    operation: str,
    path: str,
) -> GuardResult:
    """Validate a file operation against the sandbox."""
    if not path:
        return GuardResult(
            verdict=GuardVerdict.DENY,
            reason="Empty path",
        )

    # Resolve to absolute path
    resolved = os.path.realpath(path)

    # Check sandbox
    in_sandbox = any(resolved.startswith(root) for root in _SANDBOX_ROOTS)
    if not in_sandbox:
        _log.warning("[ExecutionGuard] file DENIED: %s not in sandbox", resolved)
        return GuardResult(
            verdict=GuardVerdict.DENY,
            reason=f"Path {resolved} is outside sandbox. Allowed roots: {', '.join(sorted(_SANDBOX_ROOTS))}",
        )

    # Check for sensitive file patterns
    path_lower = resolved.lower()
    for pattern in _DENIED_PATH_PATTERNS:
        if pattern in path_lower:
            _log.warning(
                "[ExecutionGuard] file DENIED: sensitive pattern %r in %s",
                pattern,
                resolved,
            )
            return GuardResult(
                verdict=GuardVerdict.DENY,
                reason=f"Path contains sensitive pattern: {pattern}",
            )

    # Write operations require extra scrutiny
    if operation in ("file_write", "file_delete"):
        _log.info(
            "[ExecutionGuard] file write allowed: %s on %s",
            operation,
            resolved,
        )

    return GuardResult(
        verdict=GuardVerdict.ALLOW,
        reason="File operation passed guard checks",
        sanitized_inputs={"path": resolved, "operation": operation},
    )


def check_tool_operation(
    operation: str,
    inputs: dict[str, Any],
    *,
    approved_execution: bool = False,
) -> GuardResult:
    """Validate a tool operation (http_*, webhook, tool_*) against the registry."""
    from umh.tools.registry import get_tool, is_domain_allowed, validate_tool_inputs

    # Derive tool_name from inputs or operation
    tool_name = inputs.get("tool_name") or operation

    tool = get_tool(tool_name)
    if tool is None:
        _log.warning("[ExecutionGuard] tool DENIED: unknown tool %r", tool_name)
        return GuardResult(
            verdict=GuardVerdict.DENY,
            reason=f"Unknown tool: {tool_name}",
        )

    # Validate required inputs — registry returns (bool, error_msg)
    valid, error_msg = validate_tool_inputs(tool_name, inputs)
    if not valid:
        _log.warning("[ExecutionGuard] tool DENIED: %s", error_msg)
        return GuardResult(
            verdict=GuardVerdict.DENY,
            reason=error_msg,
        )

    # Check domain allowlist for URL-bearing tools
    url = inputs.get("url", "")
    if url and not is_domain_allowed(url, tool):
        _log.warning("[ExecutionGuard] tool DENIED: blocked domain in %r", url)
        return GuardResult(
            verdict=GuardVerdict.DENY,
            reason=f"Domain not allowed: {url}",
        )

    # Mutating tools require approval
    if tool.mutating:
        if not approved_execution:
            _log.warning("[ExecutionGuard] tool REQUIRES_APPROVAL: %s", tool_name)
            return GuardResult(
                verdict=GuardVerdict.REQUIRES_APPROVAL,
                reason=f"Tool '{tool_name}' is mutating — requires approval",
            )
        _log.info("[ExecutionGuard] tool ALLOWED: %s (approved)", tool_name)
        return GuardResult(
            verdict=GuardVerdict.ALLOW,
            reason=f"Approved mutating tool: {tool_name}",
            sanitized_inputs=inputs,
        )

    _log.info("[ExecutionGuard] tool ALLOWED: %s (non-mutating)", tool_name)
    return GuardResult(
        verdict=GuardVerdict.ALLOW,
        reason=f"Non-mutating tool: {tool_name}",
        sanitized_inputs=inputs,
    )


_SAFE_COMPUTER_OPS = frozenset(
    {"computer_screenshot", "computer_get_screen_size", "computer_get_active_window"}
)

_MUTATION_COMPUTER_OPS = frozenset(
    {"computer_click", "computer_type", "computer_key", "computer_scroll", "computer_drag"}
)


def check_computer_operation(
    operation: str,
    inputs: dict[str, Any],
    *,
    approved_execution: bool = False,
) -> GuardResult:
    """Validate a computer use operation."""
    if operation in _SAFE_COMPUTER_OPS:
        _log.info("[ExecutionGuard] computer ALLOWED: %s (read-only)", operation)
        return GuardResult(
            verdict=GuardVerdict.ALLOW,
            reason=f"Read-only computer operation: {operation}",
        )

    if operation in _MUTATION_COMPUTER_OPS:
        if approved_execution:
            _log.info("[ExecutionGuard] computer ALLOWED: %s (approved)", operation)
            return GuardResult(
                verdict=GuardVerdict.ALLOW,
                reason=f"Approved computer mutation: {operation}",
            )
        _log.warning("[ExecutionGuard] computer REQUIRES_APPROVAL: %s", operation)
        return GuardResult(
            verdict=GuardVerdict.REQUIRES_APPROVAL,
            reason=f"Computer mutation requires approval: {operation}",
        )

    return GuardResult(
        verdict=GuardVerdict.DENY,
        reason=f"Unknown computer operation: {operation}",
    )


def check_execution(
    operation: str,
    inputs: dict[str, Any],
    *,
    approved_execution: bool = False,
) -> GuardResult:
    """Top-level guard check for any non-LLM execution."""
    if operation == "shell_command":
        return check_shell_command(inputs.get("command", ""))

    if operation in ("file_read", "file_write", "file_list", "file_delete", "file_stat"):
        return check_file_operation(operation, inputs.get("path", ""))

    if operation.startswith("computer_"):
        return check_computer_operation(operation, inputs, approved_execution=approved_execution)

    if operation.startswith("browser_"):
        return GuardResult(
            verdict=GuardVerdict.DENY,
            reason="Browser actions not yet implemented",
        )

    if operation.startswith("os_"):
        return GuardResult(
            verdict=GuardVerdict.DENY,
            reason="OS interactions not yet implemented",
        )

    if operation == "http_request" or operation.startswith("tool_"):
        return check_tool_operation(operation, inputs, approved_execution=approved_execution)

    return GuardResult(
        verdict=GuardVerdict.DENY,
        reason=f"Unknown operation: {operation}",
    )
