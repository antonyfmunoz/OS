"""Validation + approval rules for Actions.

Kept deliberately simple. Two concerns:
    1. Is the action well-formed and safe to consider? (validate_action)
    2. Should we run it right now?                     (approve_action)
"""

from __future__ import annotations

from typing import Any

from .actions import Action, ALLOWED_ACTION_TYPES
from .policy import (
    blocks_auto_execute,
    normalize_risk,
    requires_explicit_approval,
)

# Paths we will never touch regardless of caller.
FORBIDDEN_PATH_PREFIXES: tuple[str, ...] = (
    "/etc",
    "/boot",
    "/sys",
    "/proc",
    "/dev",
    "/root/.ssh",
)

# Substrings that indicate a destructive shell command.
DANGEROUS_SHELL_TOKENS: tuple[str, ...] = (
    "rm -rf /",
    "mkfs",
    ":(){:|:&};:",
    "dd if=",
    "> /dev/sda",
    "shutdown",
    "reboot",
)


def _check_path_safety(path: str) -> str | None:
    if not path:
        return "path is empty"
    for prefix in FORBIDDEN_PATH_PREFIXES:
        if path.startswith(prefix):
            return f"path {path!r} is under forbidden prefix {prefix!r}"
    return None


def _check_shell_safety(command: str) -> str | None:
    if not command:
        return "command is empty"
    for token in DANGEROUS_SHELL_TOKENS:
        if token in command:
            return f"command contains dangerous token {token!r}"
    return None


def validate_action(action: Action) -> dict[str, Any]:
    """Return a dict describing validation outcome and mutate action.validation.

    The Control Plane decides what to do with a failed validation; this
    function only reports.
    """
    errors: list[str] = []

    if not action.type:
        errors.append("missing action.type")
    elif action.type not in ALLOWED_ACTION_TYPES:
        errors.append(
            f"action.type {action.type!r} not in allowed set {ALLOWED_ACTION_TYPES}"
        )

    if not action.description:
        errors.append("missing action.description")

    # Normalise through the policy bridge. Accepts lowercase CP vocab
    # (low/medium/high/critical) as well as uppercase authority-engine
    # vocab (LOW/MEDIUM/HIGH/CRITICAL) and rewrites to canonical form.
    normalized = normalize_risk(action.risk_level)
    if action.risk_level not in ("low", "medium", "high", "critical"):
        # Only flag if normalisation had nothing plausible to work with.
        if not isinstance(
            action.risk_level, str
        ) or action.risk_level.strip().lower() not in (
            "low",
            "medium",
            "high",
            "critical",
        ):
            errors.append(f"invalid risk_level {action.risk_level!r}")
    action.risk_level = normalized

    # Type-specific safety checks.
    if action.type == "write_file":
        path = action.inputs.get("path", "")
        err = _check_path_safety(path)
        if err:
            errors.append(err)
        if "content" not in action.inputs:
            errors.append("write_file requires inputs.content")

    elif action.type == "shell_command":
        err = _check_shell_safety(action.inputs.get("command", ""))
        if err:
            errors.append(err)

    elif action.type == "run_script":
        path = action.inputs.get("path", "")
        if not path:
            errors.append("run_script requires inputs.path")
        elif not path.endswith(".py") and not path.endswith(".sh"):
            errors.append(f"run_script path {path!r} must be .py or .sh")

    elif action.type == "call_api":
        if not action.inputs.get("url"):
            errors.append("call_api requires inputs.url")

    ok = not errors
    result = {"ok": ok, "errors": errors}
    action.validation = result
    action.status = "validated" if ok else "rejected"
    return result


def approve_action(
    action: Action,
    *,
    explicit_approval: bool = False,
) -> dict[str, Any]:
    """Approve or defer an action based on its risk_level.

    v1 policy:
      - low         → auto-approve
      - medium/high → require explicit_approval=True

    Non-approved medium/high actions are left in `validated` state so
    an orchestrator (or human) can revisit them later.
    """
    if action.validation.get("ok") is not True:
        result = {"approved": False, "reason": "validation failed"}
        action.approval = result
        return result

    # Critical is a hard block: policy bridge says it must never
    # auto-execute regardless of explicit_approval=True. Callers that
    # truly need to run a critical action must downgrade it in a code
    # review + commit, not at the call site.
    if blocks_auto_execute(action.risk_level):
        result = {
            "approved": False,
            "reason": (
                f"{action.risk_level}-risk action is blocked from auto-execute; "
                "must be downgraded or routed through the business approval queue"
            ),
        }
        action.approval = result
        # Stays in `validated` so it shows up in the deferred queue for
        # operator visibility — but `run_action` will not execute it
        # even with explicit_approval=True.
        return result

    if not requires_explicit_approval(action.risk_level):
        result = {
            "approved": True,
            "reason": f"auto-approved ({action.risk_level} risk)",
        }
        action.approval = result
        action.status = "approved"
        return result

    if explicit_approval:
        result = {
            "approved": True,
            "reason": f"explicit approval for {action.risk_level}-risk action",
        }
        action.approval = result
        action.status = "approved"
        return result

    result = {
        "approved": False,
        "reason": f"{action.risk_level}-risk action requires explicit_approval=True",
    }
    action.approval = result
    # status stays "validated" — it's not rejected, just not yet approved.
    return result
