"""UMH Plan Validator — validates execution plans before task conversion.

Enforces operation allowlist, execution class validity, step count limits,
input structure, dependency integrity, and capability constraints.
"""

from __future__ import annotations

from umh.execution.contract import ExecutionClass
from umh.planning.models import (
    ExecutionPlan,
    PlanValidationResult,
)

_MAX_STEPS = 10

_KNOWN_OPERATIONS = frozenset(
    {
        "classify_intent",
        "extract_entities",
        "summarize",
        "short_response",
        "validation",
        "shell_command",
        "file_read",
        "file_write",
        "file_list",
        "file_delete",
        "file_stat",
        "computer_click",
        "computer_type",
        "computer_key",
        "computer_scroll",
        "computer_drag",
        "computer_screenshot",
        "computer_get_screen_size",
        "computer_get_active_window",
        "http_request",
    }
)

_VALID_EXECUTION_CLASSES = frozenset(e.value for e in ExecutionClass)

_SHELL_ALLOWLIST = frozenset(
    {
        "uptime",
        "df -h",
        "free -h",
        "ps aux",
        "whoami",
        "hostname",
        "uname -a",
        "date",
        "ls",
        "ls -la",
        "cat /proc/loadavg",
        "docker ps",
    }
)

_APPROVAL_GATED_OPS = frozenset(
    {
        "computer_click",
        "computer_type",
        "computer_key",
        "computer_scroll",
        "computer_drag",
    }
)

_UNSUPPORTED_OPS = frozenset(
    {
        "browser_navigate",
        "browser_click",
        "browser_type",
        "os_reboot",
        "os_shutdown",
        "os_install",
    }
)


def validate_plan(plan: ExecutionPlan) -> PlanValidationResult:
    """Validate a plan for safety and correctness before execution."""
    errors: list[str] = []
    warnings: list[str] = []

    if not plan.steps:
        errors.append("Plan has no steps")
        return PlanValidationResult(valid=False, errors=errors, warnings=warnings)

    if len(plan.steps) > min(plan.objective.max_steps, _MAX_STEPS):
        errors.append(
            f"Plan has {len(plan.steps)} steps, max is {min(plan.objective.max_steps, _MAX_STEPS)}"
        )

    step_ids = set()
    for i, step in enumerate(plan.steps):
        if not step.step_id:
            errors.append(f"Step {i}: missing step_id")
            continue

        if step.step_id in step_ids:
            errors.append(f"Step {i}: duplicate step_id '{step.step_id}'")
        step_ids.add(step.step_id)

        if not step.operation:
            errors.append(f"Step {i} ({step.step_id}): empty operation")
            continue

        if step.operation in _UNSUPPORTED_OPS:
            errors.append(f"Step {i} ({step.step_id}): unsupported operation '{step.operation}'")
            continue

        if step.operation not in _KNOWN_OPERATIONS:
            errors.append(f"Step {i} ({step.step_id}): unknown operation '{step.operation}'")
            continue

        if step.execution_class not in _VALID_EXECUTION_CLASSES:
            errors.append(
                f"Step {i} ({step.step_id}): invalid execution_class '{step.execution_class}'"
            )

        if not isinstance(step.inputs, dict):
            errors.append(f"Step {i} ({step.step_id}): inputs must be a dict")

        if step.operation == "shell_command":
            cmd = step.inputs.get("command", "")
            if cmd not in _SHELL_ALLOWLIST:
                errors.append(f"Step {i} ({step.step_id}): shell command '{cmd}' not in allowlist")

        if (
            plan.objective.allowed_capabilities
            and step.operation not in plan.objective.allowed_capabilities
        ):
            errors.append(
                f"Step {i} ({step.step_id}): operation '{step.operation}' "
                f"not in allowed_capabilities"
            )

        for dep_id in step.depends_on:
            if dep_id not in step_ids:
                errors.append(
                    f"Step {i} ({step.step_id}): depends_on '{dep_id}' "
                    f"references unknown or later step"
                )

        if step.operation in _APPROVAL_GATED_OPS:
            if step.execution_class != "side_effect":
                errors.append(
                    f"Step {i} ({step.step_id}): approval-gated operation "
                    f"'{step.operation}' must use execution_class 'side_effect'"
                )
            warnings.append(f"Step {i} ({step.step_id}): '{step.operation}' will require approval")

    return PlanValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
