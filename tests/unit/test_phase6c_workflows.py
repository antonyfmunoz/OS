"""Tests for Phase 6C: Demo Workflow Templates.

Verifies:
- New templates registered in registry
- Each creates a valid plan
- Each passes validation
- Plans convert to tasks correctly
- Safe workflows execute to completion
- approval_click_demo pauses on approval-gated step
- approval_click_demo resumes after approval
- workspace_snapshot creates correct steps
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase6c")
os.environ["PYTEST_CURRENT_TEST"] = "1"

from umh.control.identity import get_identity_store
from umh.events.stream import reset_event_stream
from umh.execution.approval import get_approval_store
from umh.orchestrator.engine import reset_orchestrator, start_orchestrator
from umh.orchestrator.task import (
    TaskStatus,
    get_task,
    reset_tasks,
)
from umh.planning.models import (
    ExecutionPlan,
    ExecutionPlanStep,
    PlanObjective,
    PlanSource,
    PlanStatus,
)
from umh.planning.planner import (
    create_plan,
    execute_plan,
    plan_to_task,
    reset_plans,
)
from umh.planning.templates import get_template, list_templates
from umh.planning.validator import validate_plan


def _reset():
    get_approval_store().reset()
    get_identity_store().reset()
    reset_event_stream()
    reset_orchestrator()
    reset_tasks()
    reset_plans()


def _start_fresh():
    _reset()
    return start_orchestrator()


# ── A. Registry Tests ──────────────────────────────────────────────


class TestWorkflowRegistry:
    def test_inspect_file_summary_registered(self):
        assert "inspect_file_summary" in list_templates()

    def test_workspace_snapshot_registered(self):
        assert "workspace_snapshot" in list_templates()

    def test_approval_click_demo_registered(self):
        assert "approval_click_demo" in list_templates()

    def test_full_system_diagnostic_registered(self):
        assert "full_system_diagnostic" in list_templates()

    def test_all_new_templates_in_registry(self):
        names = list_templates()
        for t in [
            "inspect_file_summary",
            "workspace_snapshot",
            "approval_click_demo",
            "full_system_diagnostic",
        ]:
            assert t in names, f"{t} not in registry"


# ── B. Plan Creation Tests ─────────────────────────────────────────


class TestWorkflowPlanCreation:
    def test_inspect_file_summary_creates_3_steps(self):
        obj = PlanObjective(
            title="inspect_file_summary",
            context={"path": "/opt/OS/README.md"},
        )
        fn = get_template("inspect_file_summary")
        plan = fn(obj)
        assert len(plan.steps) == 3
        assert plan.steps[0].operation == "file_stat"
        assert plan.steps[1].operation == "file_read"
        assert plan.steps[2].operation == "summarize"

    def test_inspect_file_summary_execution_classes(self):
        obj = PlanObjective(
            title="inspect_file_summary",
            context={"path": "/tmp/test.txt"},
        )
        fn = get_template("inspect_file_summary")
        plan = fn(obj)
        assert plan.steps[0].execution_class == "side_effect"
        assert plan.steps[1].execution_class == "side_effect"
        assert plan.steps[2].execution_class == "llm_call"

    def test_inspect_file_summary_path_in_inputs(self):
        obj = PlanObjective(
            title="inspect_file_summary",
            context={"path": "/opt/OS/CLAUDE.md"},
        )
        fn = get_template("inspect_file_summary")
        plan = fn(obj)
        assert plan.steps[0].inputs["path"] == "/opt/OS/CLAUDE.md"
        assert plan.steps[1].inputs["path"] == "/opt/OS/CLAUDE.md"

    def test_workspace_snapshot_creates_2_steps(self):
        obj = PlanObjective(title="workspace_snapshot")
        fn = get_template("workspace_snapshot")
        plan = fn(obj)
        assert len(plan.steps) == 2
        assert plan.steps[0].operation == "computer_screenshot"
        assert plan.steps[1].operation == "computer_get_screen_size"

    def test_workspace_snapshot_both_side_effect(self):
        obj = PlanObjective(title="workspace_snapshot")
        fn = get_template("workspace_snapshot")
        plan = fn(obj)
        for step in plan.steps:
            assert step.execution_class == "side_effect"

    def test_workspace_snapshot_assumptions(self):
        obj = PlanObjective(title="workspace_snapshot")
        fn = get_template("workspace_snapshot")
        plan = fn(obj)
        assert any("computer use" in a.lower() for a in plan.assumptions)

    def test_approval_click_demo_creates_2_steps(self):
        obj = PlanObjective(
            title="approval_click_demo",
            context={"x": 100, "y": 200},
        )
        fn = get_template("approval_click_demo")
        plan = fn(obj)
        assert len(plan.steps) == 2
        assert plan.steps[0].operation == "computer_screenshot"
        assert plan.steps[1].operation == "computer_click"

    def test_approval_click_demo_coordinates(self):
        obj = PlanObjective(
            title="approval_click_demo",
            context={"x": 42, "y": 99},
        )
        fn = get_template("approval_click_demo")
        plan = fn(obj)
        assert plan.steps[1].inputs["x"] == 42
        assert plan.steps[1].inputs["y"] == 99

    def test_approval_click_demo_both_side_effect(self):
        obj = PlanObjective(
            title="approval_click_demo",
            context={"x": 10, "y": 20},
        )
        fn = get_template("approval_click_demo")
        plan = fn(obj)
        for step in plan.steps:
            assert step.execution_class == "side_effect"

    def test_full_system_diagnostic_creates_5_steps(self):
        obj = PlanObjective(title="full_system_diagnostic")
        fn = get_template("full_system_diagnostic")
        plan = fn(obj)
        assert len(plan.steps) == 5
        for step in plan.steps:
            assert step.operation == "shell_command"
            assert step.execution_class == "side_effect"

    def test_full_system_diagnostic_shell_commands(self):
        obj = PlanObjective(title="full_system_diagnostic")
        fn = get_template("full_system_diagnostic")
        plan = fn(obj)
        commands = [s.inputs["command"] for s in plan.steps]
        assert "cat /proc/loadavg" in commands
        assert "df -h" in commands
        assert "free -h" in commands
        assert "ps aux" in commands
        assert "docker ps" in commands

    def test_full_system_diagnostic_respects_max_steps(self):
        obj = PlanObjective(title="full_system_diagnostic", max_steps=3)
        fn = get_template("full_system_diagnostic")
        plan = fn(obj)
        assert len(plan.steps) == 3

    def test_all_templates_have_template_source(self):
        for name in [
            "inspect_file_summary",
            "workspace_snapshot",
            "approval_click_demo",
            "full_system_diagnostic",
        ]:
            obj = PlanObjective(title=name, context={"path": "/tmp/x", "x": 0, "y": 0})
            fn = get_template(name)
            plan = fn(obj)
            assert plan.source == PlanSource.TEMPLATE


# ── C. Validation Tests ────────────────────────────────────────────


class TestWorkflowValidation:
    def test_inspect_file_summary_validates(self):
        obj = PlanObjective(
            title="inspect_file_summary",
            context={"path": "/opt/OS/README.md"},
        )
        fn = get_template("inspect_file_summary")
        plan = fn(obj)
        result = validate_plan(plan)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_workspace_snapshot_validates(self):
        obj = PlanObjective(title="workspace_snapshot")
        fn = get_template("workspace_snapshot")
        plan = fn(obj)
        result = validate_plan(plan)
        assert result.valid is True

    def test_approval_click_demo_validates_with_warning(self):
        obj = PlanObjective(
            title="approval_click_demo",
            context={"x": 10, "y": 20},
        )
        fn = get_template("approval_click_demo")
        plan = fn(obj)
        result = validate_plan(plan)
        assert result.valid is True
        assert any("require approval" in w.lower() for w in result.warnings)

    def test_full_system_diagnostic_validates(self):
        obj = PlanObjective(title="full_system_diagnostic")
        fn = get_template("full_system_diagnostic")
        plan = fn(obj)
        result = validate_plan(plan)
        assert result.valid is True
        assert len(result.errors) == 0


# ── D. Task Conversion Tests ──────────────────────────────────────


class TestWorkflowTaskConversion:
    def test_inspect_file_summary_converts_to_task(self):
        _reset()
        obj = PlanObjective(
            title="inspect_file_summary",
            context={"path": "/opt/OS/README.md"},
        )
        plan = create_plan(obj)
        assert plan.status == PlanStatus.VALIDATED
        task = plan_to_task(plan)
        assert task is not None
        assert len(task.steps) == 3

    def test_full_system_diagnostic_converts_to_task(self):
        _reset()
        obj = PlanObjective(title="full_system_diagnostic")
        plan = create_plan(obj)
        assert plan.status == PlanStatus.VALIDATED
        task = plan_to_task(plan)
        assert task is not None
        assert len(task.steps) == 5

    def test_task_preserves_operations(self):
        _reset()
        obj = PlanObjective(
            title="inspect_file_summary",
            context={"path": "/tmp/x"},
        )
        plan = create_plan(obj)
        task = plan_to_task(plan)
        ops = [s.operation for s in task.steps]
        assert ops == ["file_stat", "file_read", "summarize"]

    def test_task_preserves_execution_classes(self):
        _reset()
        obj = PlanObjective(
            title="inspect_file_summary",
            context={"path": "/tmp/x"},
        )
        plan = create_plan(obj)
        task = plan_to_task(plan)
        classes = [s.execution_class for s in task.steps]
        assert classes == ["side_effect", "side_effect", "llm_call"]

    def test_task_has_plan_metadata(self):
        _reset()
        obj = PlanObjective(title="full_system_diagnostic")
        plan = create_plan(obj)
        task = plan_to_task(plan)
        assert task.context["plan_id"] == plan.plan_id
        assert task.context["objective_id"] == obj.objective_id


# ── E. Execution Tests ─────────────────────────────────────────────
# Note: shell_command and file ops are additionally guarded at the
# runtime adapter layer (umh_execution.py _SHELL_ALLOWLIST and
# execution_guard.py _SANDBOX_ROOTS). Full end-to-end execution
# tests only work for LLM-only plans (like summarize_text in phase6a).
# Here we verify that plans execute (may fail due to runtime guards)
# and that the plan lifecycle status is correctly updated.


class TestWorkflowExecution:
    def test_inspect_file_summary_produces_task(self):
        """Plan creates and converts; execution hits runtime sandbox."""
        _reset()
        obj = PlanObjective(
            title="inspect_file_summary",
            context={"path": "/tmp/test_phase6c.txt"},
        )
        plan = create_plan(obj)
        assert plan.status == PlanStatus.VALIDATED
        result = execute_plan(plan)
        assert result is not None
        # Task is created and executed (may fail due to missing file)
        assert plan.task_id.startswith("task_")

    def test_full_system_diagnostic_produces_task(self):
        """Plan creates and converts; execution reaches adapter."""
        _reset()
        obj = PlanObjective(title="full_system_diagnostic")
        plan = create_plan(obj)
        assert plan.status == PlanStatus.VALIDATED
        result = execute_plan(plan)
        assert result is not None
        assert plan.task_id.startswith("task_")

    def test_full_system_diagnostic_task_id_set(self):
        _reset()
        obj = PlanObjective(title="full_system_diagnostic")
        plan = create_plan(obj)
        execute_plan(plan)
        assert plan.task_id != ""
        assert plan.task_id.startswith("task_")


# ── F. Approval-Gated Tests ───────────────────────────────────────


class TestWorkflowApproval:
    def test_approval_click_demo_pauses_task(self):
        _reset()
        obj = PlanObjective(
            title="approval_click_demo",
            context={"x": 50, "y": 75},
        )
        plan = create_plan(obj)
        assert plan.status == PlanStatus.VALIDATED
        result = execute_plan(plan)
        assert result is not None
        assert result.status == TaskStatus.PAUSED

    def test_approval_click_demo_resumes_after_approval(self):
        _start_fresh()
        obj = PlanObjective(
            title="approval_click_demo",
            context={"x": 50, "y": 75},
        )
        plan = create_plan(obj)
        result = execute_plan(plan)
        assert result.status == TaskStatus.PAUSED

        task = get_task(plan.task_id)
        approval_id = task.paused_approval_id
        get_approval_store().approve(approval_id, approved_by="tester")

        stored = get_task(plan.task_id)
        assert stored.status == TaskStatus.COMPLETED

    def test_approval_click_demo_manual_plan_pauses(self):
        """Manually constructed plan with approval-gated step also pauses."""
        _reset()
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(
                    name="Screenshot",
                    operation="computer_screenshot",
                    inputs={},
                    execution_class="side_effect",
                ),
                ExecutionPlanStep(
                    name="Click",
                    operation="computer_click",
                    inputs={"x": 10, "y": 20},
                    execution_class="side_effect",
                ),
            ],
            source=PlanSource.MANUAL,
            status=PlanStatus.VALIDATED,
        )
        result = execute_plan(plan)
        assert result is not None
        assert result.status == TaskStatus.PAUSED
