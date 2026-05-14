"""Phase 7B — Tool-aware plan template tests.

Verifies that fetch_data and send_webhook templates produce valid plans
with correct structure, and that existing templates still work (regression).
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from unittest.mock import MagicMock, patch

import pytest

from umh.planning.models import (
    ExecutionPlan,
    ExecutionPlanStep,
    PlanObjective,
    PlanSource,
    PlanStatus,
)
from umh.planning.templates import get_template, list_templates
from umh.planning.validator import validate_plan


# ── helpers ───────────────────────────────────────────────────────────


def _objective(title: str, **ctx) -> PlanObjective:
    return PlanObjective(
        title=title,
        description=f"Test objective: {title}",
        context=ctx,
    )


# ── 1. fetch_data matches ────────────────────────────────────────────


def test_fetch_data_template_registered():
    """fetch_data template is registered and retrievable."""
    fn = get_template("fetch_data")
    assert fn is not None, "fetch_data template not registered"


def test_fetch_data_produces_valid_plan():
    """fetch_data template returns an ExecutionPlan."""
    fn = get_template("fetch_data")
    plan = fn(_objective("fetch_data", url="https://example.com/api"))
    assert isinstance(plan, ExecutionPlan)
    assert len(plan.steps) == 1


def test_fetch_data_step_uses_http_request_operation():
    """fetch_data step operation is http_request."""
    fn = get_template("fetch_data")
    plan = fn(_objective("fetch_data", url="https://example.com/api"))
    assert plan.steps[0].operation == "http_request"


def test_fetch_data_step_has_side_effect_class():
    """fetch_data step execution_class is side_effect."""
    fn = get_template("fetch_data")
    plan = fn(_objective("fetch_data", url="https://example.com/api"))
    assert plan.steps[0].execution_class == "side_effect"


def test_fetch_data_step_inputs_structure():
    """fetch_data step inputs contain tool_name, method, url."""
    fn = get_template("fetch_data")
    plan = fn(_objective("fetch_data", url="https://example.com/api"))
    inputs = plan.steps[0].inputs
    assert inputs["tool_name"] == "http_get"
    assert inputs["method"] == "GET"
    assert inputs["url"] == "https://example.com/api"


# ── 5. send_webhook matches ──────────────────────────────────────────


def test_send_webhook_template_registered():
    """send_webhook template is registered and retrievable."""
    fn = get_template("send_webhook")
    assert fn is not None, "send_webhook template not registered"


def test_send_webhook_produces_valid_plan():
    """send_webhook template returns an ExecutionPlan."""
    fn = get_template("send_webhook")
    plan = fn(
        _objective(
            "send_webhook",
            url="https://hooks.example.com/notify",
            body='{"event": "test"}',
        )
    )
    assert isinstance(plan, ExecutionPlan)
    assert len(plan.steps) == 1


def test_send_webhook_step_is_mutating():
    """send_webhook step uses the webhook tool_name (which is mutating)."""
    fn = get_template("send_webhook")
    plan = fn(
        _objective(
            "send_webhook",
            url="https://hooks.example.com/notify",
            body='{"event": "test"}',
        )
    )
    inputs = plan.steps[0].inputs
    assert inputs["tool_name"] == "webhook"
    assert inputs["method"] == "POST"


# ── 8. Templates return plans not execution ──────────────────────────


def test_fetch_data_returns_plan_not_result():
    """fetch_data returns ExecutionPlan, not ExecutionResult."""
    from umh.execution.contract import ExecutionResult

    fn = get_template("fetch_data")
    plan = fn(_objective("fetch_data", url="https://example.com/api"))
    assert isinstance(plan, ExecutionPlan)
    assert not isinstance(plan, ExecutionResult)


def test_send_webhook_returns_plan_not_result():
    """send_webhook returns ExecutionPlan, not ExecutionResult."""
    from umh.execution.contract import ExecutionResult

    fn = get_template("send_webhook")
    plan = fn(
        _objective(
            "send_webhook",
            url="https://hooks.example.com/notify",
            body="{}",
        )
    )
    assert isinstance(plan, ExecutionPlan)
    assert not isinstance(plan, ExecutionResult)


# ── 9. Validator accepts fetch_data plan ─────────────────────────────


def test_fetch_data_plan_passes_validator():
    """fetch_data plan passes the plan validator."""
    fn = get_template("fetch_data")
    plan = fn(_objective("fetch_data", url="https://example.com/api"))
    result = validate_plan(plan)
    assert result.valid, f"Validation failed: {result.errors}"


# ── 10. Validator accepts send_webhook plan ──────────────────────────


def test_send_webhook_plan_passes_validator():
    """send_webhook plan passes the plan validator."""
    fn = get_template("send_webhook")
    plan = fn(
        _objective(
            "send_webhook",
            url="https://hooks.example.com/notify",
            body="{}",
        )
    )
    result = validate_plan(plan)
    assert result.valid, f"Validation failed: {result.errors}"


# ── 11. Template plan can be passed to execute_plan (mock) ───────────


def test_fetch_data_plan_converts_to_task():
    """fetch_data plan converts to Task via plan_to_task."""
    from umh.planning.planner import plan_to_task

    fn = get_template("fetch_data")
    plan = fn(_objective("fetch_data", url="https://example.com/api"))
    plan.status = PlanStatus.VALIDATED
    task = plan_to_task(plan)
    assert task is not None
    assert len(task.steps) == 1
    assert task.steps[0].operation == "http_request"


def test_send_webhook_plan_converts_to_task():
    """send_webhook plan converts to Task via plan_to_task."""
    from umh.planning.planner import plan_to_task

    fn = get_template("send_webhook")
    plan = fn(
        _objective(
            "send_webhook",
            url="https://hooks.example.com/notify",
            body="{}",
        )
    )
    plan.status = PlanStatus.VALIDATED
    task = plan_to_task(plan)
    assert task is not None
    assert len(task.steps) == 1
    assert task.steps[0].operation == "http_request"
    assert task.steps[0].inputs_template["tool_name"] == "webhook"


# ── 12. Existing templates still work (regression) ───────────────────


@pytest.mark.parametrize(
    "template_name",
    [
        "inspect_system_status",
        "inspect_file",
        "list_directory",
        "summarize_text",
        "shell_health_check",
        "computer_screenshot_review",
        "inspect_file_summary",
        "workspace_snapshot",
        "approval_click_demo",
        "full_system_diagnostic",
    ],
)
def test_existing_templates_still_registered(template_name: str):
    """Existing templates are still registered after adding new ones."""
    fn = get_template(template_name)
    assert fn is not None, f"Template '{template_name}' not found"


def test_existing_template_produces_plan():
    """inspect_system_status still produces a valid plan."""
    fn = get_template("inspect_system_status")
    plan = fn(_objective("inspect_system_status"))
    assert isinstance(plan, ExecutionPlan)
    assert plan.source == PlanSource.TEMPLATE
    result = validate_plan(plan)
    assert result.valid, f"Validation failed: {result.errors}"


def test_new_templates_in_list():
    """New templates appear in list_templates()."""
    names = list_templates()
    assert "fetch_data" in names
    assert "send_webhook" in names
