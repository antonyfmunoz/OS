"""UMH Plan Templates — deterministic plan generation for common operations.

Each template function produces a known-safe ExecutionPlan from a
PlanObjective. Templates are the primary plan source in v1; LLM-assisted
planning is optional and treats LLM output as untrusted.
"""

from __future__ import annotations

from umh.planning.models import (
    ExecutionPlan,
    ExecutionPlanStep,
    PlanObjective,
    PlanSource,
)

_TEMPLATE_REGISTRY: dict[str, callable] = {}


def template(name: str):
    """Decorator to register a plan template."""

    def decorator(fn):
        _TEMPLATE_REGISTRY[name] = fn
        return fn

    return decorator


def get_template(name: str):
    return _TEMPLATE_REGISTRY.get(name)


def list_templates() -> list[str]:
    return sorted(_TEMPLATE_REGISTRY.keys())


@template("inspect_system_status")
def plan_inspect_system_status(objective: PlanObjective) -> ExecutionPlan:
    steps = [
        ExecutionPlanStep(
            name="Check uptime",
            operation="shell_command",
            inputs={"command": "uptime"},
            execution_class="side_effect",
            rationale="Get system uptime and load averages",
        ),
        ExecutionPlanStep(
            name="Check disk usage",
            operation="shell_command",
            inputs={"command": "df -h"},
            execution_class="side_effect",
            rationale="Report disk space usage",
        ),
        ExecutionPlanStep(
            name="Check memory",
            operation="shell_command",
            inputs={"command": "free -h"},
            execution_class="side_effect",
            rationale="Report memory usage",
        ),
        ExecutionPlanStep(
            name="Check docker containers",
            operation="shell_command",
            inputs={"command": "docker ps"},
            execution_class="side_effect",
            rationale="List running containers",
        ),
    ]
    max_allowed = min(objective.max_steps, len(steps))
    return ExecutionPlan(
        objective=objective,
        steps=steps[:max_allowed],
        source=PlanSource.TEMPLATE,
        confidence=1.0,
        assumptions=["System has docker installed", "Shell commands are available"],
    )


@template("inspect_file")
def plan_inspect_file(objective: PlanObjective) -> ExecutionPlan:
    path = objective.context.get("path", "")
    return ExecutionPlan(
        objective=objective,
        steps=[
            ExecutionPlanStep(
                name=f"Read file: {path}",
                operation="file_read",
                inputs={"path": path},
                execution_class="side_effect",
                rationale=f"Read contents of {path}",
            ),
        ],
        source=PlanSource.TEMPLATE,
        confidence=1.0,
        assumptions=[f"File exists at {path}"],
    )


@template("list_directory")
def plan_list_directory(objective: PlanObjective) -> ExecutionPlan:
    path = objective.context.get("path", "/opt/OS")
    return ExecutionPlan(
        objective=objective,
        steps=[
            ExecutionPlanStep(
                name=f"List directory: {path}",
                operation="file_list",
                inputs={"path": path},
                execution_class="side_effect",
                rationale=f"List files in {path}",
            ),
        ],
        source=PlanSource.TEMPLATE,
        confidence=1.0,
        assumptions=[f"Directory exists at {path}"],
    )


@template("summarize_text")
def plan_summarize_text(objective: PlanObjective) -> ExecutionPlan:
    text = objective.context.get("text", objective.description)
    return ExecutionPlan(
        objective=objective,
        steps=[
            ExecutionPlanStep(
                name="Summarize text",
                operation="summarize",
                inputs={
                    "prompt": f"Summarize the following: {text}",
                    "system_prompt": "You are a concise summarizer.",
                    "max_tokens": 256,
                },
                execution_class="llm_call",
                rationale="Use LLM to produce a summary",
            ),
        ],
        source=PlanSource.TEMPLATE,
        confidence=1.0,
    )


@template("shell_health_check")
def plan_shell_health_check(objective: PlanObjective) -> ExecutionPlan:
    steps = [
        ExecutionPlanStep(
            name="System load",
            operation="shell_command",
            inputs={"command": "cat /proc/loadavg"},
            execution_class="side_effect",
            rationale="Check CPU load average",
        ),
        ExecutionPlanStep(
            name="Disk usage",
            operation="shell_command",
            inputs={"command": "df -h"},
            execution_class="side_effect",
            rationale="Check disk space",
        ),
        ExecutionPlanStep(
            name="Memory usage",
            operation="shell_command",
            inputs={"command": "free -h"},
            execution_class="side_effect",
            rationale="Check RAM",
        ),
    ]
    max_allowed = min(objective.max_steps, len(steps))
    return ExecutionPlan(
        objective=objective,
        steps=steps[:max_allowed],
        source=PlanSource.TEMPLATE,
        confidence=1.0,
    )


@template("computer_screenshot_review")
def plan_computer_screenshot_review(objective: PlanObjective) -> ExecutionPlan:
    return ExecutionPlan(
        objective=objective,
        steps=[
            ExecutionPlanStep(
                name="Take screenshot",
                operation="computer_screenshot",
                inputs={},
                execution_class="side_effect",
                rationale="Capture current screen state",
            ),
            ExecutionPlanStep(
                name="Summarize screenshot",
                operation="summarize",
                inputs={
                    "prompt": "Describe what you see on screen.",
                    "system_prompt": "You are describing a screenshot.",
                    "max_tokens": 512,
                },
                execution_class="llm_call",
                rationale="Use LLM to interpret screenshot contents",
            ),
        ],
        source=PlanSource.TEMPLATE,
        confidence=0.9,
        assumptions=["Computer use adapter is available"],
    )


@template("inspect_file_summary")
def plan_inspect_file_summary(objective: PlanObjective) -> ExecutionPlan:
    path = objective.context.get("path", "")
    return ExecutionPlan(
        objective=objective,
        steps=[
            ExecutionPlanStep(
                name=f"Stat file: {path}",
                operation="file_stat",
                inputs={"path": path},
                execution_class="side_effect",
                rationale=f"Get metadata for {path}",
            ),
            ExecutionPlanStep(
                name=f"Read file: {path}",
                operation="file_read",
                inputs={"path": path},
                execution_class="side_effect",
                rationale=f"Read contents of {path}",
            ),
            ExecutionPlanStep(
                name="Summarize file contents",
                operation="summarize",
                inputs={
                    "prompt": f"Summarize the contents of {path}.",
                    "system_prompt": "You are a concise file summarizer.",
                    "max_tokens": 512,
                },
                execution_class="llm_call",
                rationale="Use LLM to produce a summary of the file",
            ),
        ],
        source=PlanSource.TEMPLATE,
        confidence=1.0,
        assumptions=[f"File exists at {path}"],
    )


@template("workspace_snapshot")
def plan_workspace_snapshot(objective: PlanObjective) -> ExecutionPlan:
    return ExecutionPlan(
        objective=objective,
        steps=[
            ExecutionPlanStep(
                name="Take screenshot",
                operation="computer_screenshot",
                inputs={},
                execution_class="side_effect",
                rationale="Capture current workspace state",
            ),
            ExecutionPlanStep(
                name="Get screen dimensions",
                operation="computer_get_screen_size",
                inputs={},
                execution_class="side_effect",
                rationale="Get current screen resolution",
            ),
        ],
        source=PlanSource.TEMPLATE,
        confidence=1.0,
        assumptions=["Computer use adapter is available"],
    )


@template("fetch_data")
def plan_fetch_data(objective: PlanObjective) -> ExecutionPlan:
    url = objective.context.get("url", "")
    return ExecutionPlan(
        objective=objective,
        steps=[
            ExecutionPlanStep(
                name=f"HTTP GET {url}" if url else "HTTP GET request",
                operation="http_request",
                inputs={"tool_name": "http_get", "method": "GET", "url": url},
                execution_class="side_effect",
                rationale=f"Fetch data from {url}" if url else "Fetch data via HTTP GET",
            ),
        ],
        source=PlanSource.TEMPLATE,
        confidence=1.0,
        assumptions=["URL is reachable", "Target domain is not blocked"],
    )


@template("send_webhook")
def plan_send_webhook(objective: PlanObjective) -> ExecutionPlan:
    url = objective.context.get("url", "")
    body = objective.context.get("body", "")
    return ExecutionPlan(
        objective=objective,
        steps=[
            ExecutionPlanStep(
                name=f"Webhook POST {url}" if url else "Send webhook notification",
                operation="http_request",
                inputs={
                    "tool_name": "webhook",
                    "method": "POST",
                    "url": url,
                    "body": body,
                },
                execution_class="side_effect",
                rationale=f"Send webhook to {url}" if url else "Send webhook notification",
            ),
        ],
        source=PlanSource.TEMPLATE,
        confidence=1.0,
        assumptions=["Webhook endpoint is reachable", "Target domain is not blocked"],
    )


@template("approval_click_demo")
def plan_approval_click_demo(objective: PlanObjective) -> ExecutionPlan:
    x = objective.context.get("x", 0)
    y = objective.context.get("y", 0)
    return ExecutionPlan(
        objective=objective,
        steps=[
            ExecutionPlanStep(
                name="Take screenshot",
                operation="computer_screenshot",
                inputs={},
                execution_class="side_effect",
                rationale="Capture screen before click",
            ),
            ExecutionPlanStep(
                name=f"Click at ({x}, {y})",
                operation="computer_click",
                inputs={"x": x, "y": y},
                execution_class="side_effect",
                rationale="Click at specified coordinates (approval-gated)",
            ),
        ],
        source=PlanSource.TEMPLATE,
        confidence=0.9,
        assumptions=[
            "Computer use adapter is available",
            "Approval required for click operation",
        ],
    )


@template("full_system_diagnostic")
def plan_full_system_diagnostic(objective: PlanObjective) -> ExecutionPlan:
    steps = [
        ExecutionPlanStep(
            name="CPU load average",
            operation="shell_command",
            inputs={"command": "cat /proc/loadavg"},
            execution_class="side_effect",
            rationale="Check CPU load average",
        ),
        ExecutionPlanStep(
            name="Disk usage",
            operation="shell_command",
            inputs={"command": "df -h"},
            execution_class="side_effect",
            rationale="Report disk space usage",
        ),
        ExecutionPlanStep(
            name="Memory usage",
            operation="shell_command",
            inputs={"command": "free -h"},
            execution_class="side_effect",
            rationale="Report memory usage",
        ),
        ExecutionPlanStep(
            name="Process list",
            operation="shell_command",
            inputs={"command": "ps aux"},
            execution_class="side_effect",
            rationale="List running processes",
        ),
        ExecutionPlanStep(
            name="Docker containers",
            operation="shell_command",
            inputs={"command": "docker ps"},
            execution_class="side_effect",
            rationale="List running Docker containers",
        ),
    ]
    max_allowed = min(objective.max_steps, len(steps))
    return ExecutionPlan(
        objective=objective,
        steps=steps[:max_allowed],
        source=PlanSource.TEMPLATE,
        confidence=1.0,
        assumptions=["System has docker installed", "Shell commands are available"],
    )
