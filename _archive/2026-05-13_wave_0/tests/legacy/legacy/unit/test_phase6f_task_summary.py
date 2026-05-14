"""Tests for umh.orchestrator.summary — human-readable task summaries."""

import json
import sys
import os

sys.path.insert(0, "/opt/OS")
os.environ.setdefault("UMH_API_KEY", "test-key-phase6f")
os.environ["UMH_TASK_BACKEND"] = "memory"

import pytest

from umh.orchestrator.task import Task, TaskStep, TaskStatus, StepStatus, _save_task
from umh.orchestrator.summary import summarize_task, summarize_task_by_id


def _make_task(
    status: TaskStatus = TaskStatus.PENDING,
    steps: list[TaskStep] | None = None,
    **kwargs,
) -> Task:
    """Helper to build a Task with explicit state (no execution needed)."""
    if steps is None:
        steps = [
            TaskStep(operation="step_a"),
            TaskStep(operation="step_b"),
            TaskStep(operation="step_c"),
        ]
    task = Task(steps=steps, status=status, **kwargs)
    return task


class TestCompletedSummary:
    def test_counts(self):
        steps = [
            TaskStep(operation="a", status=StepStatus.COMPLETED),
            TaskStep(operation="b", status=StepStatus.COMPLETED),
        ]
        task = _make_task(TaskStatus.COMPLETED, steps=steps)
        summary = summarize_task(task)
        assert summary["completed_steps"] == 2
        assert summary["failed_steps"] == 0
        assert summary["total_steps"] == 2

    def test_final_summary_mentions_completed(self):
        steps = [
            TaskStep(operation="a", status=StepStatus.COMPLETED),
        ]
        task = _make_task(TaskStatus.COMPLETED, steps=steps)
        summary = summarize_task(task)
        assert "completed successfully" in summary["final_summary"]

    def test_next_action_no_action(self):
        steps = [TaskStep(operation="a", status=StepStatus.COMPLETED)]
        task = _make_task(TaskStatus.COMPLETED, steps=steps)
        summary = summarize_task(task)
        assert summary["next_action"] == "No action needed."


class TestFailedSummary:
    def test_error_in_errors_list(self):
        steps = [
            TaskStep(
                operation="a",
                status=StepStatus.COMPLETED,
            ),
            TaskStep(
                operation="b",
                status=StepStatus.FAILED,
                result={"error": "timeout exceeded"},
            ),
        ]
        task = _make_task(
            TaskStatus.FAILED,
            steps=steps,
            current_step_index=1,
            error="Step 1 (b) failed: timeout exceeded",
        )
        summary = summarize_task(task)
        assert len(summary["errors"]) > 0
        assert any("timeout exceeded" in e for e in summary["errors"])

    def test_final_summary_mentions_failed(self):
        steps = [
            TaskStep(operation="a", status=StepStatus.FAILED, result={"error": "boom"}),
        ]
        task = _make_task(TaskStatus.FAILED, steps=steps, error="boom")
        summary = summarize_task(task)
        assert "failed" in summary["final_summary"].lower()

    def test_next_action_mentions_retry(self):
        steps = [TaskStep(operation="a", status=StepStatus.FAILED, result={"error": "x"})]
        task = _make_task(TaskStatus.FAILED, steps=steps, error="x")
        summary = summarize_task(task)
        assert "retry" in summary["next_action"].lower()


class TestPausedSummary:
    def test_waiting_approval_true(self):
        steps = [
            TaskStep(operation="a", status=StepStatus.WAITING_APPROVAL),
        ]
        task = _make_task(
            TaskStatus.PAUSED,
            steps=steps,
            paused_step_index=0,
            paused_approval_id="appr_abc123",
            paused_reason="High risk operation",
        )
        summary = summarize_task(task)
        assert summary["waiting_approval"] is True

    def test_approval_id_set(self):
        steps = [TaskStep(operation="a", status=StepStatus.WAITING_APPROVAL)]
        task = _make_task(
            TaskStatus.PAUSED,
            steps=steps,
            paused_step_index=0,
            paused_approval_id="appr_abc123",
            paused_reason="risky",
        )
        summary = summarize_task(task)
        assert summary["approval_id"] == "appr_abc123"

    def test_next_action_mentions_approve(self):
        steps = [TaskStep(operation="a", status=StepStatus.WAITING_APPROVAL)]
        task = _make_task(
            TaskStatus.PAUSED,
            steps=steps,
            paused_step_index=0,
            paused_approval_id="appr_abc123",
        )
        summary = summarize_task(task)
        assert "approve" in summary["next_action"].lower()


class TestCancelledSummary:
    def test_counts(self):
        steps = [
            TaskStep(operation="a", status=StepStatus.COMPLETED),
            TaskStep(operation="b", status=StepStatus.SKIPPED),
        ]
        task = _make_task(TaskStatus.CANCELLED, steps=steps)
        summary = summarize_task(task)
        assert summary["completed_steps"] == 1
        assert summary["total_steps"] == 2

    def test_next_action_no_action(self):
        steps = [TaskStep(operation="a", status=StepStatus.SKIPPED)]
        task = _make_task(TaskStatus.CANCELLED, steps=steps)
        summary = summarize_task(task)
        assert summary["next_action"] == "No action needed."


class TestRunningSummary:
    def test_partial_progress(self):
        steps = [
            TaskStep(operation="a", status=StepStatus.COMPLETED),
            TaskStep(operation="b", status=StepStatus.RUNNING),
            TaskStep(operation="c", status=StepStatus.PENDING),
        ]
        task = _make_task(TaskStatus.RUNNING, steps=steps, current_step_index=1)
        summary = summarize_task(task)
        assert summary["completed_steps"] == 1
        assert summary["total_steps"] == 3
        assert "running" in summary["final_summary"].lower()


class TestPendingSummary:
    def test_queued(self):
        task = _make_task(TaskStatus.PENDING)
        summary = summarize_task(task)
        assert "queued" in summary["final_summary"].lower()


class TestStepSummaries:
    def test_includes_operation_and_status(self):
        steps = [
            TaskStep(operation="classify", status=StepStatus.COMPLETED),
            TaskStep(operation="respond", status=StepStatus.PENDING),
        ]
        task = _make_task(TaskStatus.RUNNING, steps=steps)
        summary = summarize_task(task, include_steps=True)
        assert len(summary["step_summaries"]) == 2
        assert summary["step_summaries"][0]["operation"] == "classify"
        assert summary["step_summaries"][0]["status"] == "completed"
        assert summary["step_summaries"][1]["operation"] == "respond"
        assert summary["step_summaries"][1]["status"] == "pending"

    def test_output_truncated(self):
        long_response = "x" * 500
        steps = [
            TaskStep(
                operation="gen",
                status=StepStatus.COMPLETED,
                result={"outputs": {"response": long_response}},
            ),
        ]
        task = _make_task(TaskStatus.COMPLETED, steps=steps)
        summary = summarize_task(task)
        assert len(summary["step_summaries"][0]["output"]) <= 200

    def test_include_steps_false(self):
        steps = [TaskStep(operation="a", status=StepStatus.COMPLETED)]
        task = _make_task(TaskStatus.COMPLETED, steps=steps)
        summary = summarize_task(task, include_steps=False)
        assert summary["step_summaries"] == []


class TestMissingTimeline:
    def test_none_timeline_works(self):
        steps = [TaskStep(operation="a", status=StepStatus.COMPLETED)]
        task = _make_task(TaskStatus.COMPLETED, steps=steps)
        # Should not raise
        summary = summarize_task(task, timeline=None)
        assert summary["task_id"] == task.id


class TestSummarizeById:
    def test_found(self):
        steps = [TaskStep(operation="a", status=StepStatus.COMPLETED)]
        task = _make_task(TaskStatus.COMPLETED, steps=steps)
        _save_task(task)
        result = summarize_task_by_id(task.id)
        assert result is not None
        assert result["task_id"] == task.id

    def test_missing_returns_none(self):
        result = summarize_task_by_id("task_nonexistent_999")
        assert result is None


class TestSerializable:
    def test_json_serializable(self):
        steps = [
            TaskStep(
                operation="a",
                status=StepStatus.COMPLETED,
                result={"outputs": {"response": "hello"}},
            ),
            TaskStep(
                operation="b",
                status=StepStatus.FAILED,
                result={"error": "kaboom", "outputs": {}},
            ),
        ]
        task = _make_task(
            TaskStatus.FAILED,
            steps=steps,
            current_step_index=1,
            error="Step 1 (b) failed",
        )
        summary = summarize_task(task)
        # Must not raise
        serialized = json.dumps(summary)
        assert isinstance(serialized, str)
        parsed = json.loads(serialized)
        assert parsed["task_id"] == task.id
