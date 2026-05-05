"""Tests for UMH MVP golden paths — plan, execute, enqueue, summary, timeline.

All tests use the in-memory task backend and require no HTTP server.
"""

import sys
import os

sys.path.insert(0, "/opt/OS")
os.environ.setdefault("UMH_API_KEY", "test-key-phase6f")
os.environ["UMH_TASK_BACKEND"] = "memory"

import pytest

from umh.orchestrator.summary import summarize_task, summarize_task_by_id
from umh.orchestrator.task import (
    Task,
    TaskStatus,
    TaskStep,
    StepStatus,
    enqueue_task,
    execute_task,
    _save_task,
)
from umh.orchestrator.timeline import build_task_timeline
from umh.planning.models import ExecutionPlan, PlanObjective, PlanSource, PlanStatus
from umh.planning.planner import (
    create_plan,
    create_plan_from_raw,
    execute_plan,
    list_plans,
    reset_plans,
)


# ── Path 1: Plan Only ──────────────────────────────────────────────


class TestPlanOnlyPath:
    """Path 1: create_plan_from_raw succeeds for known intent."""

    def test_plan_from_raw_creates_plan(self):
        plan = create_plan_from_raw("check system health")
        assert plan is not None
        assert plan.plan_id.startswith("eplan_")

    def test_plan_status_validated(self):
        plan = create_plan_from_raw("check system health")
        assert plan.status == PlanStatus.VALIDATED

    def test_plan_has_steps(self):
        plan = create_plan_from_raw("check system health")
        assert len(plan.steps) > 0

    def test_plan_source_is_template(self):
        plan = create_plan_from_raw("check system health")
        assert plan.source == PlanSource.TEMPLATE

    def test_plan_quality_scored(self):
        plan = create_plan_from_raw("check system health")
        assert plan.quality_score is not None
        assert "verdict" in plan.quality_score
        assert "score" in plan.quality_score

    def test_plan_quality_passes(self):
        plan = create_plan_from_raw("check system health")
        assert plan.quality_score["verdict"] == "pass"

    def test_plan_explanation_attached(self):
        plan = create_plan_from_raw("check system health")
        assert plan.explanation is not None
        assert "objective_summary" in plan.explanation
        assert "assumptions" in plan.explanation

    def test_plan_to_dict_serializable(self):
        import json

        plan = create_plan_from_raw("check system health")
        d = plan.to_dict()
        serialized = json.dumps(d)
        assert isinstance(serialized, str)


# ── Path 2: Run Safe Workflow ──────────────────────────────────────


class TestRunSafePath:
    """Path 2: plan + execute succeeds for system health check."""

    def test_execute_returns_task(self):
        plan = create_plan_from_raw("check system health")
        task = execute_plan(plan)
        assert task is not None

    def test_task_completed(self):
        plan = create_plan_from_raw("check system health")
        task = execute_plan(plan)
        assert task.status == TaskStatus.COMPLETED

    def test_all_steps_completed(self):
        plan = create_plan_from_raw("check system health")
        task = execute_plan(plan)
        for step in task.steps:
            assert step.status == StepStatus.COMPLETED

    def test_task_has_id(self):
        plan = create_plan_from_raw("check system health")
        task = execute_plan(plan)
        assert task.id.startswith("task_")

    def test_plan_status_updated_after_execute(self):
        plan = create_plan_from_raw("check system health")
        execute_plan(plan)
        assert plan.status == PlanStatus.COMPLETED


# ── Path 3: Inspect File Path ─────────────────────────────────────


class TestInspectFilePath:
    """Path 3: inspect template creates a valid plan for file paths."""

    def test_file_inspect_plan_created(self):
        plan = create_plan_from_raw("inspect /opt/OS/README.md")
        assert plan is not None
        assert plan.status == PlanStatus.VALIDATED

    def test_file_inspect_has_file_read_step(self):
        plan = create_plan_from_raw("inspect /opt/OS/README.md")
        operations = [s.operation for s in plan.steps]
        assert "file_read" in operations

    def test_file_inspect_path_in_inputs(self):
        plan = create_plan_from_raw("inspect /opt/OS/README.md")
        file_read_steps = [s for s in plan.steps if s.operation == "file_read"]
        assert len(file_read_steps) > 0
        assert file_read_steps[0].inputs.get("path") == "/opt/OS/README.md"

    def test_file_inspect_source_template(self):
        plan = create_plan_from_raw("inspect /opt/OS/README.md")
        assert plan.source == PlanSource.TEMPLATE


# ── Path 4: Enqueue Path ─────────────────────────────────────────


class TestEnqueuePath:
    """Path 4: enqueue returns a pending task."""

    def test_enqueue_returns_task(self):
        steps = [
            TaskStep(
                operation="file_read",
                inputs_template={"path": "/opt/OS/README.md"},
                execution_class="side_effect",
            ),
        ]
        task = Task(steps=steps, issued_by="test")
        result = enqueue_task(task)
        assert result is not None

    def test_enqueue_status_pending(self):
        steps = [
            TaskStep(
                operation="file_read",
                inputs_template={"path": "/opt/OS/README.md"},
                execution_class="side_effect",
            ),
        ]
        task = Task(steps=steps, issued_by="test")
        result = enqueue_task(task)
        assert result.status == TaskStatus.PENDING

    def test_enqueue_preserves_steps(self):
        steps = [
            TaskStep(operation="file_read", execution_class="side_effect"),
            TaskStep(operation="summarize", execution_class="llm_call"),
        ]
        task = Task(steps=steps, issued_by="test")
        result = enqueue_task(task)
        assert len(result.steps) == 2

    def test_enqueue_sets_task_id(self):
        steps = [TaskStep(operation="file_read", execution_class="side_effect")]
        task = Task(steps=steps, issued_by="test")
        result = enqueue_task(task)
        assert result.id.startswith("task_")


# ── Path 5: Summary Path ─────────────────────────────────────────


class TestSummaryPath:
    """Path 5: summarize_task returns a valid dict for various states."""

    def test_completed_summary(self):
        steps = [
            TaskStep(
                operation="shell_command",
                status=StepStatus.COMPLETED,
                result={"outputs": {"stdout": "ok"}},
            ),
        ]
        task = Task(steps=steps, status=TaskStatus.COMPLETED, issued_by="test")
        summary = summarize_task(task)
        assert isinstance(summary, dict)
        assert summary["status"] == "completed"
        assert summary["completed_steps"] == 1

    def test_failed_summary_has_errors(self):
        steps = [
            TaskStep(
                operation="bad_op",
                status=StepStatus.FAILED,
                result={"error": "unknown operation"},
            ),
        ]
        task = Task(
            steps=steps,
            status=TaskStatus.FAILED,
            error="Step 0 (bad_op) failed",
            issued_by="test",
        )
        summary = summarize_task(task)
        assert summary["status"] == "failed"
        assert len(summary["errors"]) > 0

    def test_pending_summary(self):
        steps = [TaskStep(operation="a")]
        task = Task(steps=steps, status=TaskStatus.PENDING, issued_by="test")
        summary = summarize_task(task)
        assert summary["status"] == "pending"
        assert "queued" in summary["final_summary"].lower()

    def test_summary_has_all_required_keys(self):
        steps = [TaskStep(operation="a", status=StepStatus.COMPLETED)]
        task = Task(steps=steps, status=TaskStatus.COMPLETED, issued_by="test")
        summary = summarize_task(task)
        required = [
            "task_id",
            "status",
            "objective",
            "current_step",
            "total_steps",
            "completed_steps",
            "failed_steps",
            "waiting_approval",
            "final_summary",
            "step_summaries",
            "errors",
            "next_action",
        ]
        for key in required:
            assert key in summary, f"Missing key: {key}"

    def test_summary_json_serializable(self):
        import json

        steps = [
            TaskStep(
                operation="a",
                status=StepStatus.COMPLETED,
                result={"outputs": {"response": "hello"}},
            ),
        ]
        task = Task(steps=steps, status=TaskStatus.COMPLETED, issued_by="test")
        summary = summarize_task(task)
        serialized = json.dumps(summary)
        assert isinstance(serialized, str)

    def test_summarize_by_id_found(self):
        steps = [TaskStep(operation="a", status=StepStatus.COMPLETED)]
        task = Task(steps=steps, status=TaskStatus.COMPLETED, issued_by="test")
        _save_task(task)
        result = summarize_task_by_id(task.id)
        assert result is not None
        assert result["task_id"] == task.id

    def test_summarize_by_id_missing(self):
        result = summarize_task_by_id("task_does_not_exist_999")
        assert result is None


# ── Timeline Path ─────────────────────────────────────────────────


class TestTimelinePath:
    """Timeline builds correct entries for executed tasks."""

    def test_timeline_for_executed_task(self):
        plan = create_plan_from_raw("check system health")
        task = execute_plan(plan)
        assert task is not None

        timeline = build_task_timeline(task.id)
        assert len(timeline) > 0

    def test_timeline_has_task_events(self):
        plan = create_plan_from_raw("check system health")
        task = execute_plan(plan)
        assert task is not None

        timeline = build_task_timeline(task.id)
        event_types = [e.event_type for e in timeline]
        # Should have at least task creation or start events
        assert any("task." in t for t in event_types)

    def test_timeline_entries_have_timestamps(self):
        plan = create_plan_from_raw("check system health")
        task = execute_plan(plan)
        assert task is not None

        timeline = build_task_timeline(task.id)
        for entry in timeline:
            assert entry.timestamp, f"Entry {entry.event_type} has no timestamp"

    def test_timeline_entries_serializable(self):
        import json

        plan = create_plan_from_raw("check system health")
        task = execute_plan(plan)
        assert task is not None

        timeline = build_task_timeline(task.id)
        for entry in timeline:
            d = entry.to_dict()
            serialized = json.dumps(d)
            assert isinstance(serialized, str)

    def test_timeline_empty_for_unknown_task(self):
        timeline = build_task_timeline("task_nonexistent_999")
        assert timeline == []


# ── Plan Rejection Path ───────────────────────────────────────────


class TestPlanRejectionPath:
    """Unknown intent produces a rejected plan with fail quality."""

    def test_unknown_intent_rejected(self):
        plan = create_plan_from_raw("do something completely invalid and weird")
        assert plan.status == PlanStatus.REJECTED

    def test_unknown_intent_quality_fail(self):
        plan = create_plan_from_raw("do something completely invalid and weird")
        assert plan.quality_score is not None
        assert plan.quality_score["verdict"] == "fail"

    def test_unknown_intent_has_validation_errors(self):
        plan = create_plan_from_raw("do something completely invalid and weird")
        assert len(plan.validation_errors) > 0

    def test_unknown_intent_no_steps(self):
        plan = create_plan_from_raw("do something completely invalid and weird")
        assert len(plan.steps) == 0
