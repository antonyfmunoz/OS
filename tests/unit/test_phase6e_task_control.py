"""Tests for Phase 6E Agent 1: Task Control API/CLI.

Covers:
- TestCancelTask: cancel pending, paused, completed rejected, failed rejected,
  steps SKIPPED, event emitted
- TestRetryTask: retry failed creates new task, retry non-failed rejected,
  new task is PENDING, original unchanged, context has retried_from
- TestCancelAPI: POST /tasks/{id}/cancel 200, 404, 409
- TestRetryAPI: POST /tasks/{id}/retry 200 with new task, 409 for non-failed
- TestTimelineAPI: GET /tasks/{id}/timeline returns events, 404 for missing
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase6e")
os.environ["UMH_TASK_BACKEND"] = "memory"

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import get_identity_store
from umh.events.stream import get_event_stream, reset_event_stream
from umh.execution.approval import get_approval_store
from umh.orchestrator.engine import reset_orchestrator
from umh.orchestrator.task import (
    Task,
    TaskStatus,
    TaskStep,
    StepStatus,
    cancel_task,
    enqueue_task,
    get_task,
    reset_tasks,
    retry_task,
)
from umh.orchestrator.task_store import (
    InMemoryTaskBackend,
    reset_task_store,
)
from umh.orchestrator.worker import reset_worker

client = TestClient(app)


def _reset():
    get_approval_store().reset()
    get_identity_store().reset()
    reset_event_stream()
    reset_orchestrator()
    reset_tasks()
    reset_task_store(backend=InMemoryTaskBackend())
    reset_worker()


def _create_identity(name="admin", scopes=None):
    store = get_identity_store()
    identity, raw_key = store.create_identity(name, scopes or ["admin"])
    return identity, raw_key, {"X-API-Key": raw_key}


# ── TestCancelTask ──────────────────────────────────────────────────


class TestCancelTask:
    def setup_method(self):
        _reset()

    def test_cancel_pending(self):
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        enqueue_task(task)
        assert task.status == TaskStatus.PENDING

        result = cancel_task(task.id)
        assert result is not None
        assert result.status == TaskStatus.CANCELLED

    def test_cancel_paused(self):
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        task.status = TaskStatus.PAUSED
        task.paused_step_index = 0
        task.paused_approval_id = "appr_123"
        from umh.orchestrator.task import _save_task

        _save_task(task)

        result = cancel_task(task.id)
        assert result is not None
        assert result.status == TaskStatus.CANCELLED

    def test_cancel_completed_rejected(self):
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        task.status = TaskStatus.COMPLETED
        from umh.orchestrator.task import _save_task

        _save_task(task)

        result = cancel_task(task.id)
        assert result is None

    def test_cancel_failed_rejected(self):
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        task.status = TaskStatus.FAILED
        task.error = "some error"
        from umh.orchestrator.task import _save_task

        _save_task(task)

        result = cancel_task(task.id)
        assert result is None

    def test_cancelled_task_has_skipped_steps(self):
        task = Task(
            steps=[
                TaskStep(operation="op1"),
                TaskStep(operation="op2"),
                TaskStep(operation="op3"),
            ],
            issued_by="test",
        )
        enqueue_task(task)

        result = cancel_task(task.id)
        assert result is not None
        for step in result.steps:
            assert step.status == StepStatus.SKIPPED

    def test_cancel_emits_event(self):
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        enqueue_task(task)

        stream = get_event_stream()
        before = stream.count()

        cancel_task(task.id)

        events = stream.list_events(limit=1000)
        cancel_events = [e for e in events if e.type == "task.cancelled"]
        assert len(cancel_events) == 1
        assert cancel_events[0].payload["task_id"] == task.id


# ── TestRetryTask ───────────────────────────────────────────────────


class TestRetryTask:
    def setup_method(self):
        _reset()

    def test_retry_failed_creates_new_task(self):
        task = Task(
            steps=[TaskStep(operation="op1"), TaskStep(operation="op2")],
            issued_by="test",
            context={"key": "value"},
        )
        task.status = TaskStatus.FAILED
        task.error = "step failed"
        from umh.orchestrator.task import _save_task

        _save_task(task)

        new_task = retry_task(task.id)
        assert new_task is not None
        assert new_task.id != task.id
        assert len(new_task.steps) == 2
        assert new_task.steps[0].operation == "op1"
        assert new_task.steps[1].operation == "op2"

    def test_retry_non_failed_rejected(self):
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        enqueue_task(task)
        assert task.status == TaskStatus.PENDING

        result = retry_task(task.id)
        assert result is None

    def test_retry_completed_rejected(self):
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        task.status = TaskStatus.COMPLETED
        from umh.orchestrator.task import _save_task

        _save_task(task)

        result = retry_task(task.id)
        assert result is None

    def test_new_task_is_pending(self):
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        task.status = TaskStatus.FAILED
        from umh.orchestrator.task import _save_task

        _save_task(task)

        new_task = retry_task(task.id)
        assert new_task is not None
        assert new_task.status == TaskStatus.PENDING

    def test_original_task_unchanged(self):
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        task.status = TaskStatus.FAILED
        task.error = "original error"
        from umh.orchestrator.task import _save_task

        _save_task(task)

        retry_task(task.id)

        original = get_task(task.id)
        assert original is not None
        assert original.status == TaskStatus.FAILED
        assert original.error == "original error"

    def test_context_has_retried_from(self):
        task = Task(
            steps=[TaskStep(operation="op1")],
            issued_by="test",
            context={"original": True},
        )
        task.status = TaskStatus.FAILED
        from umh.orchestrator.task import _save_task

        _save_task(task)

        new_task = retry_task(task.id)
        assert new_task is not None
        assert new_task.context["retried_from"] == task.id
        assert new_task.context["original"] is True

    def test_retry_emits_event(self):
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        task.status = TaskStatus.FAILED
        from umh.orchestrator.task import _save_task

        _save_task(task)

        retry_task(task.id)

        stream = get_event_stream()
        events = stream.list_events(limit=1000)
        retry_events = [e for e in events if e.type == "task.retried"]
        assert len(retry_events) == 1
        assert retry_events[0].payload["task_id"] == task.id

    def test_new_task_steps_are_fresh(self):
        task = Task(
            steps=[
                TaskStep(operation="op1"),
                TaskStep(operation="op2"),
            ],
            issued_by="test",
        )
        task.status = TaskStatus.FAILED
        task.steps[0].status = StepStatus.COMPLETED
        task.steps[1].status = StepStatus.FAILED
        from umh.orchestrator.task import _save_task

        _save_task(task)

        new_task = retry_task(task.id)
        assert new_task is not None
        for step in new_task.steps:
            assert step.status == StepStatus.PENDING


# ── TestCancelAPI ───────────────────────────────────────────────────


class TestCancelAPI:
    def setup_method(self):
        _reset()

    def test_cancel_returns_200(self):
        _, _, headers = _create_identity()
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        enqueue_task(task)

        resp = client.post(f"/tasks/{task.id}/cancel", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancelled"
        assert data["id"] == task.id

    def test_cancel_returns_404(self):
        _, _, headers = _create_identity()
        resp = client.post("/tasks/nonexistent_id/cancel", headers=headers)
        assert resp.status_code == 404

    def test_cancel_returns_409_for_completed(self):
        _, _, headers = _create_identity()
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        task.status = TaskStatus.COMPLETED
        from umh.orchestrator.task import _save_task

        _save_task(task)

        resp = client.post(f"/tasks/{task.id}/cancel", headers=headers)
        assert resp.status_code == 409

    def test_cancel_returns_409_for_failed(self):
        _, _, headers = _create_identity()
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        task.status = TaskStatus.FAILED
        from umh.orchestrator.task import _save_task

        _save_task(task)

        resp = client.post(f"/tasks/{task.id}/cancel", headers=headers)
        assert resp.status_code == 409


# ── TestRetryAPI ────────────────────────────────────────────────────


class TestRetryAPI:
    def setup_method(self):
        _reset()

    def test_retry_returns_200_with_new_task(self):
        _, _, headers = _create_identity()
        task = Task(
            steps=[TaskStep(operation="op1")],
            issued_by="test",
            context={"key": "val"},
        )
        task.status = TaskStatus.FAILED
        task.error = "boom"
        from umh.orchestrator.task import _save_task

        _save_task(task)

        resp = client.post(f"/tasks/{task.id}/retry", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] != task.id
        assert data["status"] == "pending"
        assert data["retried_from"] == task.id

    def test_retry_returns_409_for_non_failed(self):
        _, _, headers = _create_identity()
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        enqueue_task(task)

        resp = client.post(f"/tasks/{task.id}/retry", headers=headers)
        assert resp.status_code == 409

    def test_retry_returns_404_for_missing(self):
        _, _, headers = _create_identity()
        resp = client.post("/tasks/nonexistent_id/retry", headers=headers)
        assert resp.status_code == 404


# ── TestTimelineAPI ─────────────────────────────────────────────────


class TestTimelineAPI:
    def setup_method(self):
        _reset()

    def test_timeline_returns_events(self):
        _, _, headers = _create_identity()
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        enqueue_task(task)
        cancel_task(task.id)

        resp = client.get(f"/tasks/{task.id}/timeline", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # enqueued + cancelled
        types = [e["event_type"] for e in data]
        assert "task.enqueued" in types
        assert "task.cancelled" in types

    def test_timeline_returns_404_for_missing(self):
        _, _, headers = _create_identity()
        resp = client.get("/tasks/nonexistent_id/timeline", headers=headers)
        assert resp.status_code == 404

    def test_timeline_synthesizes_created_for_task_with_no_events(self):
        _, _, headers = _create_identity()
        task = Task(steps=[TaskStep(operation="op1")], issued_by="test")
        from umh.orchestrator.task import _save_task

        _save_task(task)

        resp = client.get(f"/tasks/{task.id}/timeline", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["event_type"] == "task.created"
