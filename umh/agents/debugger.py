"""UMH Debug Agent — post-execution failure analysis with structured diagnostics.

Analyzes execution failures and produces diagnostic output: root cause,
failure category, suggested fix, retryability. Deterministic classification
with optional LLM-enhanced analysis via lightweight_execute.

READ-ONLY. ADVISORY. STATELESS. Never calls execute(). Never mutates state.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from umh.agents.base import AgentOutput, AgentRole, BaseAgent

_log = logging.getLogger(__name__)

# Error pattern → (failure_category, retryable, suggested_fix)
_ERROR_PATTERNS: list[tuple[list[str], str, bool, str]] = [
    (
        ["timeout", "timed out"],
        "timeout",
        True,
        "Increase timeout budget or check if the target service is overloaded",
    ),
    (
        ["permission", "denied", "403", "401"],
        "permission_denied",
        False,
        "Check API keys, tokens, or filesystem permissions",
    ),
    (
        ["not found", "404"],
        "input_error",
        False,
        "Verify the resource path/URL exists and is accessible",
    ),
    (
        ["500", "internal"],
        "external_failure",
        True,
        "External service error — retry after backoff or check service status",
    ),
    (
        ["validation", "invalid"],
        "validation_error",
        False,
        "Check input data against expected schema and constraints",
    ),
    (
        ["connection", "network"],
        "external_failure",
        True,
        "Network connectivity issue — check DNS, firewall, and service availability",
    ),
]

# Valid failure categories
_VALID_CATEGORIES = frozenset(
    {
        "input_error",
        "timeout",
        "permission_denied",
        "external_failure",
        "validation_error",
        "internal_error",
        "unknown",
    }
)


def _find_failed_step_index(task: dict) -> int:
    """Find the index of the first failed step in a task dict.

    Returns -1 if no failed step found.
    """
    steps = task.get("steps", [])
    for i, step in enumerate(steps):
        status = step.get("status", "")
        if status in ("failed", "error"):
            return i
    # If no explicit failed step, use current_step_index
    return task.get("current_step_index", -1)


def _classify_error(error: str) -> tuple[str, bool, str]:
    """Classify an error string into category, retryability, and suggested fix.

    Returns (failure_category, retryable, suggested_fix).
    """
    error_lower = error.lower()

    for patterns, category, retryable, fix in _ERROR_PATTERNS:
        for pattern in patterns:
            if pattern in error_lower:
                return category, retryable, fix

    return "unknown", False, "Inspect the full traceback and logs for additional context"


def _build_root_cause(error: str, category: str, failed_step_index: int, task: dict) -> str:
    """Build a one-line root cause assessment."""
    steps = task.get("steps", [])

    step_info = ""
    if 0 <= failed_step_index < len(steps):
        step = steps[failed_step_index]
        op = step.get("operation", "unknown")
        name = step.get("name", step.get("id", ""))
        step_info = f" at step {failed_step_index} ({op}"
        if name:
            step_info += f": {name}"
        step_info += ")"

    category_labels = {
        "timeout": "Operation timed out",
        "permission_denied": "Permission or authentication failure",
        "input_error": "Required resource not found",
        "external_failure": "External service failure",
        "validation_error": "Input validation failed",
        "internal_error": "Internal system error",
        "unknown": "Unclassified execution failure",
    }

    label = category_labels.get(category, "Execution failure")
    # Truncate raw error to keep root cause concise
    error_snippet = error[:120].replace("\n", " ").strip()
    if len(error) > 120:
        error_snippet += "..."

    return f"{label}{step_info}: {error_snippet}"


def _try_llm_analysis(
    error: str,
    task: dict,
    plan: dict,
    failed_step_index: int,
    deterministic_category: str,
) -> tuple[str, str, str, float, str]:
    """Attempt LLM-enhanced failure analysis.

    Returns (root_cause, category, suggested_fix, confidence, model_used).
    Returns empty strings/0.0 if LLM unavailable.
    """
    try:
        from umh.execution.engine import lightweight_execute
    except ImportError:
        return "", "", "", 0.0, ""

    steps = task.get("steps", [])
    failed_step = {}
    if 0 <= failed_step_index < len(steps):
        failed_step = steps[failed_step_index]

    prompt = (
        "You are a failure analysis expert for an AI execution system.\n"
        "Analyze this execution failure and provide root cause analysis.\n\n"
        f"Error: {error[:500]}\n\n"
        f"Failed step (index {failed_step_index}):\n"
        f"{json.dumps(failed_step, indent=2, default=str)}\n\n"
        f"Task status: {task.get('status', 'unknown')}\n"
        f"Deterministic classification: {deterministic_category}\n\n"
        "Respond with valid JSON only:\n"
        '{"root_cause": "one-line root cause", '
        '"failure_category": "one of: input_error, timeout, '
        "permission_denied, external_failure, validation_error, "
        'internal_error, unknown", '
        '"suggested_fix": "actionable fix suggestion"}'
    )

    try:
        result = lightweight_execute(
            "validation",
            prompt,
            system=("You are a deterministic failure analyst. Return only valid JSON."),
            max_tokens=256,
        )
        if result.status.value != "succeeded":
            return "", "", "", 0.0, ""

        response_text = result.outputs.get("response", "")
        if not response_text:
            return "", "", "", 0.0, ""

        parsed = json.loads(response_text)
        root_cause = parsed.get("root_cause", "")
        category = parsed.get("failure_category", "")
        fix = parsed.get("suggested_fix", "")
        model_used = result.model_used or ""

        # Validate category
        if category not in _VALID_CATEGORIES:
            category = ""

        if root_cause and isinstance(root_cause, str):
            return root_cause, category, fix, 0.85, model_used

        return "", "", "", 0.0, model_used

    except Exception as exc:
        _log.debug("LLM failure analysis failed (non-fatal): %s", exc)
        return "", "", "", 0.0, ""


class DebugAgent(BaseAgent):
    """Analyzes execution failures and produces diagnostic output.

    Deterministic error classification runs always. LLM enhancement
    is optional and gracefully degrades when unavailable.
    """

    @property
    def role(self) -> AgentRole:
        return AgentRole.DEBUGGER

    @property
    def description(self) -> str:
        return "Analyzes execution failures and produces root-cause diagnostics"

    def run(self, input_data: dict) -> AgentOutput:
        """Analyze a failure and return structured diagnostics.

        Args:
            input_data: Must contain 'task' (Task.to_dict()) and 'error' (str).
                        Optionally 'plan' (ExecutionPlan.to_dict()).

        Returns:
            AgentOutput with output containing root_cause, failed_step_index,
            failure_category, suggested_fix, retryable, and confidence.
        """
        task = input_data.get("task", {})
        error = input_data.get("error", "")
        plan = input_data.get("plan", {})

        # Deterministic analysis
        failed_step_index = _find_failed_step_index(task)
        category, retryable, suggested_fix = _classify_error(error)
        root_cause = _build_root_cause(error, category, failed_step_index, task)
        confidence = 0.6
        model_used = ""

        # Optional LLM enhancement
        llm_root, llm_cat, llm_fix, llm_conf, llm_model = _try_llm_analysis(
            error, task, plan, failed_step_index, category
        )

        if llm_root and llm_conf > confidence:
            root_cause = llm_root
            confidence = llm_conf
            model_used = llm_model
            if llm_cat and llm_cat in _VALID_CATEGORIES:
                category = llm_cat
                # Re-derive retryability from LLM category
                retryable = category in ("timeout", "external_failure")
            if llm_fix and isinstance(llm_fix, str):
                suggested_fix = llm_fix

        return AgentOutput(
            agent_role=self.role.value,
            agent_id="",
            output={
                "root_cause": root_cause,
                "failed_step_index": failed_step_index,
                "failure_category": category,
                "suggested_fix": suggested_fix,
                "retryable": retryable,
                "confidence": confidence,
            },
            confidence=confidence,
            model_used=model_used,
        )
