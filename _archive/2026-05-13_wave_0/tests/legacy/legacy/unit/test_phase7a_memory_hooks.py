"""Tests for umh.memory.hooks — task completion memory recording."""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("UMH_ENV", "test")


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path):
    """Point memory store at a temp DB and reset between tests."""
    db_path = str(tmp_path / "test_hooks_memory.sqlite")
    os.environ["UMH_MEMORY_DB_PATH"] = db_path

    from umh.memory.persistent_store import reset_memory_store

    reset_memory_store()
    yield
    reset_memory_store()
    os.environ.pop("UMH_MEMORY_DB_PATH", None)


def _make_task(status, steps=None, error=""):
    """Create a Task with given status and steps."""
    from umh.orchestrator.task import Task, TaskStep, TaskStatus, StepStatus

    if steps is None:
        steps = [
            TaskStep(operation="shell_command", inputs_template={"command": "ls"}),
            TaskStep(operation="file_read", inputs_template={"path": "/tmp/test"}),
        ]

    task = Task(steps=steps)
    task.status = TaskStatus(status)

    if status == "failed":
        task.error = error or "something went wrong"
        # Mark the second step as failed by default
        if len(task.steps) >= 2:
            task.steps[0].status = StepStatus.COMPLETED
            task.steps[1].status = StepStatus.FAILED

    if status == "completed":
        for step in task.steps:
            step.status = StepStatus.COMPLETED

    return task


class TestRecordTaskCompletion:
    """record_task_completion tests."""

    def test_completed_task_returns_id(self):
        from umh.memory.hooks import record_task_completion

        task = _make_task("completed")
        result = record_task_completion(task)

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_failed_task_returns_id(self):
        from umh.memory.hooks import record_task_completion

        task = _make_task("failed", error="timeout exceeded")
        result = record_task_completion(task)

        assert result is not None
        assert isinstance(result, str)

    def test_pending_task_returns_none(self):
        from umh.memory.hooks import record_task_completion

        task = _make_task("pending")
        result = record_task_completion(task)

        assert result is None

    def test_running_task_returns_none(self):
        from umh.memory.hooks import record_task_completion

        task = _make_task("running")
        result = record_task_completion(task)

        assert result is None

    def test_includes_operations_in_tags(self):
        from umh.memory.hooks import record_task_completion
        from umh.memory.persistent_store import get_memory_store

        task = _make_task("completed")
        memory_id = record_task_completion(task)

        store = get_memory_store()
        memory = store.get_memory(memory_id)

        assert "shell_command" in memory.tags
        assert "file_read" in memory.tags

    def test_metadata_has_correct_fields(self):
        from umh.memory.hooks import record_task_completion
        from umh.memory.persistent_store import get_memory_store

        task = _make_task("completed")
        memory_id = record_task_completion(task)

        store = get_memory_store()
        memory = store.get_memory(memory_id)

        assert memory.metadata["task_id"] == task.id
        assert memory.metadata["status"] == "completed"
        assert memory.metadata["step_count"] == 2
        assert memory.metadata["created_at"] == task.created_at

    def test_content_format_completed(self):
        from umh.memory.hooks import record_task_completion
        from umh.memory.persistent_store import get_memory_store

        task = _make_task("completed")
        memory_id = record_task_completion(task)

        store = get_memory_store()
        memory = store.get_memory(memory_id)

        assert f"Task {task.id} completed" in memory.content
        assert "2 steps" in memory.content
        assert "shell_command" in memory.content
        assert "file_read" in memory.content

    def test_content_format_failed(self):
        from umh.memory.hooks import record_task_completion
        from umh.memory.persistent_store import get_memory_store

        task = _make_task("failed", error="disk full")
        memory_id = record_task_completion(task)

        store = get_memory_store()
        memory = store.get_memory(memory_id)

        assert f"Task {task.id} failed" in memory.content
        assert "disk full" in memory.content

    def test_completed_tags_include_status_and_auto(self):
        from umh.memory.hooks import record_task_completion
        from umh.memory.persistent_store import get_memory_store

        task = _make_task("completed")
        memory_id = record_task_completion(task)

        store = get_memory_store()
        memory = store.get_memory(memory_id)

        assert "completed" in memory.tags
        assert "auto-recorded" in memory.tags

    def test_failed_tags_include_status(self):
        from umh.memory.hooks import record_task_completion
        from umh.memory.persistent_store import get_memory_store

        task = _make_task("failed")
        memory_id = record_task_completion(task)

        store = get_memory_store()
        memory = store.get_memory(memory_id)

        assert "failed" in memory.tags
        assert "auto-recorded" in memory.tags


class TestRecordTaskSummary:
    """record_task_summary tests."""

    def test_saves_summary_memory(self):
        from umh.memory.hooks import record_task_summary
        from umh.memory.persistent_store import get_memory_store

        summary = {
            "status": "completed",
            "final_summary": "All 3 steps completed successfully.",
            "step_summaries": [
                {"step": 0, "operation": "classify_intent", "status": "completed"},
            ],
        }
        memory_id = record_task_summary("task_abc123", summary)

        assert memory_id is not None

        store = get_memory_store()
        memory = store.get_memory(memory_id)

        assert memory.type == "summary"
        assert memory.content == "All 3 steps completed successfully."
        assert memory.metadata["task_id"] == "task_abc123"
        assert memory.metadata["status"] == "completed"
        assert "summary" in memory.tags
        assert "task_abc123" in memory.tags

    def test_empty_summary(self):
        from umh.memory.hooks import record_task_summary
        from umh.memory.persistent_store import get_memory_store

        summary = {}
        memory_id = record_task_summary("task_empty", summary)

        assert memory_id is not None

        store = get_memory_store()
        memory = store.get_memory(memory_id)

        assert memory.content == ""
        assert memory.metadata["task_id"] == "task_empty"
        assert memory.metadata["status"] == ""
        assert memory.metadata["steps"] == []
