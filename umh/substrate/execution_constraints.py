"""
Execution Constraints — deterministic path and command boundary enforcement.

Pure evaluation module. No roles, no UI, no side effects.
Evaluates whether an action's target (path, command) falls within
approved execution boundaries.

Called by resolve_permission() inside discord_output_policy.py.
Never called directly by bridge or consumer code.

Design rules:
- Role-agnostic: no knowledge of builder/ea_product/unknown
- Pure functions: no I/O, no network, no state mutation
- Deterministic: same inputs always produce same outputs
- Fail-safe: ambiguous inputs bias toward ESCALATE or BLOCKED
"""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass
from enum import Enum
from typing import Any

from umh.substrate.discord_output_policy import (
    IntentType,
    PermissionIntent,
    RiskLevel,
    _DESTRUCTIVE_COMMAND_PATTERNS,
    _SAFE_COMMAND_PATTERNS,
)


# ─── Enums ────────────────────────────────────────────────────────────────


class ConstraintDecision(str, Enum):
    """Outcome of constraint evaluation."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    ESCALATE = "escalate"


class PathScope(str, Enum):
    """Classification of a target path relative to approved boundaries."""

    APPROVED_ROOT = "approved_root"
    TEMP_ROOT = "temp_root"
    OUTSIDE_ROOT = "outside_root"
    SYSTEM_PATH = "system_path"


class CommandClass(str, Enum):
    """Classification of a command's safety profile."""

    SAFE = "safe"
    DESTRUCTIVE = "destructive"
    UNKNOWN = "unknown"


class ConstraintType(str, Enum):
    """Category of constraint that produced the result."""

    PATH_BOUNDARY = "path_boundary"
    COMMAND_SAFETY = "command_safety"
    NETWORK_SCOPE = "network_scope"
    NO_TARGET = "no_target"
    NONE = "none"  # constraint evaluated, no issue found
    NOT_EVALUATED = "not_evaluated"  # intent type has no constraint logic


# ─── Result Model ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ConstraintResult:
    """Outcome of execution constraint evaluation.

    Returned to resolve_permission() for composition with tool policy.
    Never consumed directly by bridge or UI code.
    """

    result: ConstraintDecision
    constraint_type: ConstraintType
    reason: str


# ─── Approved Roots ───────────────────────────────────────────────────────

_APPROVED_ROOTS: tuple[str, ...] = ("/opt/OS",)
_APPROVED_TEMP_PREFIXES: tuple[str, ...] = ("/tmp/eos_",)

_SYSTEM_PATHS: frozenset[str] = frozenset(
    {
        "/",
        "/etc",
        "/root",
        "/usr",
        "/var",
        "/boot",
        "/sbin",
        "/bin",
        "/lib",
        "/proc",
        "/sys",
        "/dev",
    }
)


def get_approved_roots(session: Any = None) -> list[str]:
    """Return the current set of approved workspace roots.

    Always includes _APPROVED_ROOTS. Optionally appends
    session.active_workspace if present and non-empty.
    Never removes or overrides base roots.

    Args:
        session: Optional object with an active_workspace attribute.

    Returns:
        New list of approved root paths (caller may not mutate base set).
    """
    roots = list(_APPROVED_ROOTS)
    if session is not None:
        workspace = getattr(session, "active_workspace", None)
        if workspace and isinstance(workspace, str) and workspace.strip():
            normalized = os.path.realpath(os.path.abspath(workspace.strip()))
            if normalized not in roots:
                roots.append(normalized)
    return roots


# ─── Path Classification ─────────────────────────────────────────────────


def classify_path_scope(target_path: str, session: Any = None) -> PathScope:
    """Classify a target path relative to approved boundaries.

    All checks operate on normalized absolute paths (realpath + abspath)
    to prevent traversal attacks.

    Check order: system paths first, then approved roots, then temp roots.
    This ensures /etc/eos matches SYSTEM_PATH before any approved root.

    Args:
        target_path: Raw path to classify.
        session: Optional session for additional approved roots.

    Returns:
        PathScope classification.
    """
    normalized = os.path.realpath(os.path.abspath(target_path))

    # System paths — checked first (highest priority)
    for sys_path in _SYSTEM_PATHS:
        if sys_path == "/":
            # Root path: only match exact root, not everything
            if normalized == "/":
                return PathScope.SYSTEM_PATH
        elif normalized == sys_path or normalized.startswith(sys_path + os.sep):
            return PathScope.SYSTEM_PATH

    # Approved roots
    for root in get_approved_roots(session):
        norm_root = os.path.realpath(os.path.abspath(root))
        if normalized == norm_root or normalized.startswith(norm_root + os.sep):
            return PathScope.APPROVED_ROOT

    # Temp roots
    for prefix in _APPROVED_TEMP_PREFIXES:
        if normalized.startswith(prefix):
            return PathScope.TEMP_ROOT

    return PathScope.OUTSIDE_ROOT


# ─── Command Classification ──────────────────────────────────────────────


def classify_command(command: str) -> CommandClass:
    """Classify a command's safety profile.

    Reuses _DESTRUCTIVE_COMMAND_PATTERNS and _SAFE_COMMAND_PATTERNS
    from discord_output_policy. No new pattern sets.

    Check order: destructive first (fail-safe bias), then safe.

    Args:
        command: Raw command string.

    Returns:
        CommandClass classification.
    """
    cmd = command.strip()
    if not cmd:
        return CommandClass.UNKNOWN

    for pat in _DESTRUCTIVE_COMMAND_PATTERNS:
        if pat.search(cmd):
            return CommandClass.DESTRUCTIVE

    for pat in _SAFE_COMMAND_PATTERNS:
        if pat.search(cmd):
            return CommandClass.SAFE

    return CommandClass.UNKNOWN


# ─── Command Path Extraction ─────────────────────────────────────────────

# Pattern for absolute paths in command arguments.
_ABS_PATH_RE = re.compile(r"(?:^|\s)(/[^\s;|&]+)")


def _extract_command_target_path(command: str) -> str:
    """Extract a single deterministic target path from a command.

    Strict extraction rules:
    - Split on |, examine only the first segment
    - Find arguments that start with / (absolute paths)
    - If exactly one absolute path found, return it
    - If zero or multiple found, return "" (fail safe)
    - Never guess, never partially parse

    Args:
        command: Raw command string.

    Returns:
        Absolute path string, or "" if extraction fails.
    """
    cmd = command.strip()
    if not cmd:
        return ""

    # Split on pipe, take first segment only
    first_segment = cmd.split("|")[0].strip()
    if not first_segment:
        return ""

    # Find all absolute paths in the first segment
    matches = _ABS_PATH_RE.findall(first_segment)

    # Exactly one path → return it; otherwise fail safe
    if len(matches) == 1:
        return matches[0]
    return ""


# ─── Command Decision Matrix ─────────────────────────────────────────────

# (CommandClass, PathScope) → ConstraintDecision
_COMMAND_MATRIX: dict[tuple[CommandClass, PathScope], ConstraintDecision] = {
    # SAFE commands
    (CommandClass.SAFE, PathScope.APPROVED_ROOT): ConstraintDecision.ALLOWED,
    (CommandClass.SAFE, PathScope.TEMP_ROOT): ConstraintDecision.ALLOWED,
    (CommandClass.SAFE, PathScope.OUTSIDE_ROOT): ConstraintDecision.ESCALATE,
    (CommandClass.SAFE, PathScope.SYSTEM_PATH): ConstraintDecision.BLOCKED,
    # DESTRUCTIVE commands
    (CommandClass.DESTRUCTIVE, PathScope.APPROVED_ROOT): ConstraintDecision.ESCALATE,
    (CommandClass.DESTRUCTIVE, PathScope.TEMP_ROOT): ConstraintDecision.ESCALATE,
    (CommandClass.DESTRUCTIVE, PathScope.OUTSIDE_ROOT): ConstraintDecision.BLOCKED,
    (CommandClass.DESTRUCTIVE, PathScope.SYSTEM_PATH): ConstraintDecision.BLOCKED,
    # UNKNOWN commands
    (CommandClass.UNKNOWN, PathScope.APPROVED_ROOT): ConstraintDecision.ESCALATE,
    (CommandClass.UNKNOWN, PathScope.TEMP_ROOT): ConstraintDecision.ESCALATE,
    (CommandClass.UNKNOWN, PathScope.OUTSIDE_ROOT): ConstraintDecision.BLOCKED,
    (CommandClass.UNKNOWN, PathScope.SYSTEM_PATH): ConstraintDecision.BLOCKED,
}


# ─── File Path Decision Logic ────────────────────────────────────────────


def _evaluate_file_constraint(
    intent_type: IntentType,
    path_scope: PathScope,
) -> ConstraintResult:
    """Evaluate file read/write constraints based on path scope.

    Reads are more permissive than writes:
    - APPROVED_ROOT / TEMP_ROOT → ALLOWED for both
    - OUTSIDE_ROOT → ESCALATE for reads, BLOCKED for writes
    - SYSTEM_PATH → BLOCKED for both
    """
    if path_scope in (PathScope.APPROVED_ROOT, PathScope.TEMP_ROOT):
        return ConstraintResult(
            result=ConstraintDecision.ALLOWED,
            constraint_type=ConstraintType.NONE,
            reason="",
        )

    if path_scope == PathScope.OUTSIDE_ROOT:
        if intent_type == IntentType.FILE_READ:
            return ConstraintResult(
                result=ConstraintDecision.ESCALATE,
                constraint_type=ConstraintType.PATH_BOUNDARY,
                reason="read target outside approved workspace root",
            )
        # FILE_WRITE
        return ConstraintResult(
            result=ConstraintDecision.BLOCKED,
            constraint_type=ConstraintType.PATH_BOUNDARY,
            reason="write target outside approved workspace root",
        )

    # SYSTEM_PATH
    action = "read" if intent_type == IntentType.FILE_READ else "write"
    return ConstraintResult(
        result=ConstraintDecision.BLOCKED,
        constraint_type=ConstraintType.PATH_BOUNDARY,
        reason=f"{action} target in protected system path",
    )


# ─── Core Evaluator ──────────────────────────────────────────────────────


def evaluate_execution_constraints(
    intent: PermissionIntent,
    risk_level: RiskLevel,
    target_path: str = "",
) -> ConstraintResult:
    """Evaluate execution constraints for a permission request.

    Pure function. No roles, no UI, no side effects.
    Called by resolve_permission() only — never by bridge code.

    Args:
        intent: Structured permission intent.
        risk_level: Risk classification from classify_risk().
        target_path: Explicit target path override (usually intent.target).

    Returns:
        ConstraintResult with decision, type, and reason.
    """
    # ── Intent-type routing ──────────────────────────────────────────

    # BROWSER_NAVIGATION: local browser open — no constraint needed
    if intent.type == IntentType.BROWSER_NAVIGATION:
        return ConstraintResult(
            result=ConstraintDecision.ALLOWED,
            constraint_type=ConstraintType.NONE,
            reason="",
        )

    # NETWORK_CALL: observable escalation (tool policy already handles blocking)
    if intent.type == IntentType.NETWORK_CALL:
        return ConstraintResult(
            result=ConstraintDecision.ESCALATE,
            constraint_type=ConstraintType.NETWORK_SCOPE,
            reason="network call requires escalation for observability",
        )

    # PROCESS_EXEC / UNKNOWN: no meaningful constraint logic
    if intent.type in (IntentType.PROCESS_EXEC, IntentType.UNKNOWN):
        return ConstraintResult(
            result=ConstraintDecision.ESCALATE,
            constraint_type=ConstraintType.NOT_EVALUATED,
            reason="intent type has no path/command constraint logic",
        )

    # ── FILE_READ / FILE_WRITE ───────────────────────────────────────

    if intent.type in (IntentType.FILE_READ, IntentType.FILE_WRITE):
        effective_path = target_path or intent.target
        if not effective_path or not effective_path.strip():
            return ConstraintResult(
                result=ConstraintDecision.ESCALATE,
                constraint_type=ConstraintType.NO_TARGET,
                reason="no target path could be determined for file operation",
            )

        path_scope = classify_path_scope(effective_path)
        return _evaluate_file_constraint(intent.type, path_scope)

    # ── COMMAND ──────────────────────────────────────────────────────

    if intent.type == IntentType.COMMAND:
        cmd_class = classify_command(intent.command)
        extracted_path = _extract_command_target_path(intent.command)

        if not extracted_path:
            # No deterministic path → escalate (fail safe)
            return ConstraintResult(
                result=ConstraintDecision.ESCALATE,
                constraint_type=ConstraintType.NO_TARGET,
                reason="no target path could be extracted from command",
            )

        path_scope = classify_path_scope(extracted_path)
        decision = _COMMAND_MATRIX.get(
            (cmd_class, path_scope), ConstraintDecision.ESCALATE
        )

        if decision == ConstraintDecision.ALLOWED:
            return ConstraintResult(
                result=decision,
                constraint_type=ConstraintType.NONE,
                reason="",
            )
        elif decision == ConstraintDecision.BLOCKED:
            return ConstraintResult(
                result=decision,
                constraint_type=ConstraintType.COMMAND_SAFETY,
                reason=(
                    f"{cmd_class.value} command targeting "
                    f"{path_scope.value} path: {extracted_path}"
                ),
            )
        else:
            # ESCALATE
            return ConstraintResult(
                result=decision,
                constraint_type=ConstraintType.COMMAND_SAFETY,
                reason=(
                    f"{cmd_class.value} command targeting "
                    f"{path_scope.value} path: {extracted_path}"
                ),
            )

    # Fallback: should not reach here, but fail safe
    return ConstraintResult(
        result=ConstraintDecision.ESCALATE,
        constraint_type=ConstraintType.NOT_EVALUATED,
        reason="unhandled intent type",
    )


# ─── Exports ──────────────────────────────────────────────────────────────

__all__ = [
    "ConstraintDecision",
    "PathScope",
    "CommandClass",
    "ConstraintType",
    "ConstraintResult",
    "get_approved_roots",
    "classify_path_scope",
    "classify_command",
    "evaluate_execution_constraints",
]
