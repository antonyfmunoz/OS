"""
Execution Control — deterministic command shaping and enforcement.

Sits BETWEEN the permission decision (resolve_permission) and actual
dispatch/execution. Does NOT change allow/deny decisions — only shapes
HOW allowed actions execute.

Design rules:
- Cannot turn DENY into anything else
- Can tighten behavior (rewrite commands, add timeouts)
- Cannot widen authority
- Pure functions: no I/O, no network, no state mutation
- Deterministic: same inputs always produce same outputs
- Observable: every control action is traceable

Called after resolve_permission() returns ALLOW or ESCALATE.
Never called for DENY results.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from enum import Enum
from typing import Any

from umh.substrate.discord_output_policy import (
    FinalResolution,
    IntentType,
    PermissionIntent,
    RiskLevel,
)
from umh.substrate.execution_constraints import (
    CommandClass,
    classify_command,
)


# ─── Enums ────────────────────────────────────────────────────────────────


class ControlType(str, Enum):
    """Category of execution control applied."""

    NONE = "none"  # no control needed
    COMMAND_NORMALIZATION = "command_normalization"
    TIMEOUT_APPLIED = "timeout_applied"
    SHELL_SAFETY = "shell_safety"
    DESTRUCTIVE_BOUND = "destructive_bound"
    COMBINED = "combined"  # multiple controls applied


# ─── Result Model ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ExecutionControlResult:
    """Outcome of execution control evaluation.

    Returned to the caller that sits between resolve_permission()
    and actual dispatch. Every field is observable for tracing.

    Attributes:
        allowed: Whether execution should proceed (always True if called
                 correctly — DENY never reaches this layer).
        rewritten_command: Normalized/safe form of the command, or None
                          if no rewrite was needed.
        control_type: Category of control applied.
        control_reason: Human-readable explanation of what was done.
        timeout_seconds: Execution timeout to enforce, or None if
                         no timeout applies (non-command intents).
        controls_applied: List of individual control actions taken,
                          for detailed tracing when multiple apply.
    """

    allowed: bool
    rewritten_command: str | None
    control_type: ControlType
    control_reason: str
    timeout_seconds: int | None
    controls_applied: tuple[str, ...] = ()


# ─── Timeout Defaults ─────────────────────────────────────────────────────

# Timeouts by (intent_type, risk_level). Conservative defaults.
# Values in seconds.
_TIMEOUT_TABLE: dict[tuple[IntentType, RiskLevel], int] = {
    # Commands
    (IntentType.COMMAND, RiskLevel.LOW): 30,
    (IntentType.COMMAND, RiskLevel.MEDIUM): 120,
    (IntentType.COMMAND, RiskLevel.HIGH): 300,
    # File reads — fast
    (IntentType.FILE_READ, RiskLevel.LOW): 15,
    (IntentType.FILE_READ, RiskLevel.MEDIUM): 30,
    (IntentType.FILE_READ, RiskLevel.HIGH): 60,
    # File writes — slightly longer
    (IntentType.FILE_WRITE, RiskLevel.LOW): 30,
    (IntentType.FILE_WRITE, RiskLevel.MEDIUM): 60,
    (IntentType.FILE_WRITE, RiskLevel.HIGH): 120,
    # Network calls — generous but bounded
    (IntentType.NETWORK_CALL, RiskLevel.LOW): 60,
    (IntentType.NETWORK_CALL, RiskLevel.MEDIUM): 120,
    (IntentType.NETWORK_CALL, RiskLevel.HIGH): 300,
    # Process exec — build/script timeouts
    (IntentType.PROCESS_EXEC, RiskLevel.LOW): 120,
    (IntentType.PROCESS_EXEC, RiskLevel.MEDIUM): 300,
    (IntentType.PROCESS_EXEC, RiskLevel.HIGH): 600,
}

_DEFAULT_TIMEOUT: int = 120  # fallback for unknown combinations


def _resolve_timeout(intent_type: IntentType, risk_level: RiskLevel) -> int:
    """Look up the timeout for an intent/risk combination."""
    return _TIMEOUT_TABLE.get((intent_type, risk_level), _DEFAULT_TIMEOUT)


# ─── Shell Safety Patterns ────────────────────────────────────────────────

# Dangerous shell chaining operators that allow arbitrary command injection.
# We detect and flag these — they indicate the command is compound and
# should be treated with higher scrutiny.
_SHELL_CHAIN_RE = re.compile(
    r"(?:"
    r"(?<![|&])[;]"  # semicolons (not inside quotes — approximated)
    r"|(?<![|])\|(?![|])"  # single pipe (not ||)
    r"|&&"  # logical AND chaining
    r"|\|\|"  # logical OR chaining
    r"|\$\("  # command substitution
    r"|`[^`]+`"  # backtick substitution
    r")"
)

# Patterns for obviously dangerous suffixes/arguments.
_DANGEROUS_SUFFIX_RE = re.compile(
    r"(?:"
    r">\s*/dev/sd"  # redirect to raw device
    r"|>\s*/dev/null\s*2>&1\s*&"  # background + suppress all output
    r"|--no-preserve-root"  # bypass rm safety
    r"|\beval\s+"  # eval injection
    r"|\bexec\s+"  # exec replacement
    r")"
)

# Excessive whitespace normalization.
_MULTI_SPACE_RE = re.compile(r"[ \t]+")


# ─── Normalization ────────────────────────────────────────────────────────


def _normalize_whitespace(command: str) -> str:
    """Collapse multiple spaces/tabs to single space, strip edges."""
    return _MULTI_SPACE_RE.sub(" ", command.strip())


def _detect_shell_chains(command: str) -> list[str]:
    """Detect dangerous shell chaining in a command.

    Returns list of concerns found. Empty list = clean.
    Does NOT attempt to parse shell grammar — just flags patterns.
    """
    concerns: list[str] = []
    if ";" in command:
        concerns.append("semicolon_chaining")
    if "&&" in command:
        concerns.append("and_chaining")
    if "||" in command:
        concerns.append("or_chaining")
    if "$(" in command:
        concerns.append("command_substitution")
    if "`" in command and command.count("`") >= 2:
        concerns.append("backtick_substitution")
    return concerns


def _detect_dangerous_suffixes(command: str) -> list[str]:
    """Detect obviously dangerous command suffixes/arguments."""
    concerns: list[str] = []
    if _DANGEROUS_SUFFIX_RE.search(command):
        if "--no-preserve-root" in command:
            concerns.append("no_preserve_root")
        if re.search(r"\beval\s+", command):
            concerns.append("eval_injection")
        if re.search(r"\bexec\s+", command):
            concerns.append("exec_replacement")
        if re.search(r">\s*/dev/sd", command):
            concerns.append("raw_device_redirect")
    return concerns


# ─── Core Logic ───────────────────────────────────────────────────────────


def apply_execution_controls(
    role: str,
    intent: PermissionIntent,
    risk_level: RiskLevel,
    final_resolution: FinalResolution,
) -> ExecutionControlResult:
    """Apply execution controls to a permitted action.

    Called AFTER resolve_permission() returns ALLOW or ESCALATE.
    Never called for DENY results.

    This function:
    1. Rejects DENY (defensive — caller should not pass these)
    2. Assigns timeouts based on intent type and risk level
    3. For COMMAND intents: normalizes, detects shell safety issues,
       bounds destructive commands
    4. Returns a fully traceable ExecutionControlResult

    Args:
        role: Session role (builder, ea_product, unknown).
        intent: Structured permission intent from extract_intent().
        risk_level: Risk classification from classify_risk().
        final_resolution: Output of resolve_permission() — ALLOW or ESCALATE.

    Returns:
        ExecutionControlResult with all control decisions.
    """
    # ── Guard: DENY must never reach this layer ─────────────────────
    if final_resolution == FinalResolution.DENY:
        return ExecutionControlResult(
            allowed=False,
            rewritten_command=None,
            control_type=ControlType.NONE,
            control_reason="DENY resolution passed to execution control — rejected",
            timeout_seconds=None,
        )

    # ── Non-command intents: timeout only ───────────────────────────
    if intent.type != IntentType.COMMAND:
        timeout = _resolve_timeout(intent.type, risk_level)
        return ExecutionControlResult(
            allowed=True,
            rewritten_command=None,
            control_type=ControlType.TIMEOUT_APPLIED,
            control_reason=f"timeout {timeout}s for {intent.type.value}/{risk_level.value}",
            timeout_seconds=timeout,
            controls_applied=("timeout",),
        )

    # ── Command intents: full control pipeline ──────────────────────
    command = intent.command
    if not command or not command.strip():
        timeout = _resolve_timeout(IntentType.COMMAND, risk_level)
        return ExecutionControlResult(
            allowed=True,
            rewritten_command=None,
            control_type=ControlType.TIMEOUT_APPLIED,
            control_reason="empty command — timeout only",
            timeout_seconds=timeout,
            controls_applied=("timeout",),
        )

    controls: list[str] = []
    reasons: list[str] = []
    rewritten: str | None = None

    # Step 1: Normalize whitespace
    normalized = _normalize_whitespace(command)
    if normalized != command:
        rewritten = normalized
        controls.append("whitespace_normalized")
        reasons.append("whitespace normalized")

    working_cmd = rewritten if rewritten else command

    # Step 2: Detect shell chaining concerns
    chain_concerns = _detect_shell_chains(working_cmd)
    if chain_concerns:
        controls.append("shell_chain_detected")
        reasons.append(f"shell chaining detected: {', '.join(chain_concerns)}")

    # Step 3: Detect dangerous suffixes
    suffix_concerns = _detect_dangerous_suffixes(working_cmd)
    if suffix_concerns:
        controls.append("dangerous_suffix_detected")
        reasons.append(f"dangerous patterns: {', '.join(suffix_concerns)}")

    # Step 4: Destructive command bounding
    cmd_class = classify_command(working_cmd)
    if cmd_class == CommandClass.DESTRUCTIVE:
        controls.append("destructive_bounded")
        reasons.append("destructive command — execution bounded")

    # Step 5: Assign timeout
    timeout = _resolve_timeout(IntentType.COMMAND, risk_level)
    # Destructive commands get shorter timeout (fail fast)
    if cmd_class == CommandClass.DESTRUCTIVE:
        timeout = min(timeout, 60)
        controls.append("timeout_capped_destructive")
    controls.append("timeout")

    # ── Determine control type ──────────────────────────────────────
    if len(controls) <= 1:
        # Only timeout
        control_type = ControlType.TIMEOUT_APPLIED
    elif suffix_concerns or chain_concerns:
        if rewritten:
            control_type = ControlType.COMBINED
        else:
            control_type = ControlType.SHELL_SAFETY
    elif rewritten:
        control_type = ControlType.COMMAND_NORMALIZATION
    elif cmd_class == CommandClass.DESTRUCTIVE:
        control_type = ControlType.DESTRUCTIVE_BOUND
    else:
        control_type = (
            ControlType.COMBINED if len(controls) > 2 else ControlType.TIMEOUT_APPLIED
        )

    reason_str = "; ".join(reasons) if reasons else f"timeout {timeout}s"

    return ExecutionControlResult(
        allowed=True,
        rewritten_command=rewritten,
        control_type=control_type,
        control_reason=reason_str,
        timeout_seconds=timeout,
        controls_applied=tuple(controls),
    )


# ─── Exports ──────────────────────────────────────────────────────────────

__all__ = [
    "ControlType",
    "ExecutionControlResult",
    "apply_execution_controls",
]
