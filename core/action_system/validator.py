"""Validation + approval rules for Actions.

Kept deliberately simple. Two concerns:
    1. Is the action well-formed and safe to consider? (validate_action)
    2. Should we run it right now?                     (approve_action)
"""

from __future__ import annotations

from typing import Any

from .actions import Action, ALLOWED_ACTION_TYPES

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

    if action.risk_level not in ("low", "medium", "high"):
        errors.append(f"invalid risk_level {action.risk_level!r}")

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

    if action.risk_level == "low":
        result = {"approved": True, "reason": "auto-approved (low risk)"}
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
