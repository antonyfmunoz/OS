"""Tests for Phase 5F: /metrics task visibility extension.

Verifies:
- /metrics includes a 'tasks' key with task counts
- tasks_by_status reflects completed, failed, running, pending states
- total_tasks increments after task execution
- recent_tasks returns up to 5 summaries (id, status, step_count, created_at)
- Failed tasks are counted in tasks_by_status['failed']
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase5f-metrics")

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import get_identity_store
from umh.events.stream import reset_event_stream
from umh.execution.approval import get_approval_store
from umh.orchestrator.engine import reset_orchestrator
from umh.orchestrator.task import reset_tasks

client = TestClient(app)


def _reset():
    get_approval_store().reset()
    get_identity_store().reset()
    reset_event_stream()
    reset_orchestrator()
    reset_tasks()


def _create_identity(name="admin", scopes=None):
    store = get_identity_store()
    identity, raw_key = store.create_identity(name, scopes or ["admin"])
    return identity, raw_key, {"X-API-Key": raw_key}


def _metrics_headers():
    """Return headers for an identity with metrics:read scope."""
    _, _, headers = _create_identity("metrics_reader", ["metrics:read"])
    return headers


def _exec_headers():
    """Return headers for an identity with execute scope."""
    _, _, headers = _create_identity("executor", ["admin"])
    return headers


def _run_task(headers, operation="classify_intent", execution_class="llm_call", inputs=None):
    """POST /tasks with a single step and return the response."""
    if inputs is None:
        inputs = {"prompt": "hi", "system_prompt": "", "max_tokens": 100}
    return client.post(
        "/tasks",
        json={
            "steps": [
                {
                    "operation": operation,
                    "inputs_template": inputs,
                    "execution_class": execution_class,
                }
            ]
        },
        headers=headers,
    )


# ── A. Metrics endpoint includes task block ──────────────────────────


class TestMetricsIncludesTaskBlock:
    def test_metrics_has_tasks_key(self):
        _reset()
        headers = _metrics_headers()
        resp = client.get("/metrics", headers=headers)
        assert resp.status_code == 200
        assert "tasks" in resp.json()

    def test_tasks_block_has_required_keys(self):
        _reset()
        headers = _metrics_headers()
        resp = client.get("/metrics", headers=headers)
        tasks = resp.json()["tasks"]
        assert "total_tasks" in tasks
        assert "tasks_by_status" in tasks
        assert "recent_tasks" in tasks

    def test_tasks_by_status_has_all_statuses(self):
        _reset()
        headers = _metrics_headers()
        resp = client.get("/metrics", headers=headers)
        by_status = resp.json()["tasks"]["tasks_by_status"]
        for status in ("pending", "running", "completed", "failed"):
            assert status in by_status, f"Missing status key: {status}"

    def test_metrics_requires_metrics_read_scope(self):
        _reset()
        _, _, no_scope_headers = _create_identity("nobody", ["execute"])
        resp = client.get("/metrics", headers=no_scope_headers)
        assert resp.status_code == 403

    def test_metrics_requires_auth(self):
        _reset()
        resp = client.get("/metrics")
        assert resp.status_code == 401


# ── B. Task counts update after execution ───────────────────────────


class TestTaskCountsAfterExecution:
    def test_total_tasks_zero_initially(self):
        _reset()
        headers = _metrics_headers()
        resp = client.get("/metrics", headers=headers)
        assert resp.json()["tasks"]["total_tasks"] == 0

    def test_total_tasks_increments_after_one_task(self):
        _reset()
        exec_hdrs = _exec_headers()
        metrics_hdrs = _metrics_headers()

        _run_task(exec_hdrs)

        resp = client.get("/metrics", headers=metrics_hdrs)
        assert resp.json()["tasks"]["total_tasks"] == 1

    def test_total_tasks_increments_after_multiple_tasks(self):
        _reset()
        exec_hdrs = _exec_headers()
        metrics_hdrs = _metrics_headers()

        for _ in range(3):
            _run_task(exec_hdrs)

        resp = client.get("/metrics", headers=metrics_hdrs)
        assert resp.json()["tasks"]["total_tasks"] == 3

    def test_completed_count_updates(self):
        _reset()
        exec_hdrs = _exec_headers()
        metrics_hdrs = _metrics_headers()

        _run_task(exec_hdrs)

        resp = client.get("/metrics", headers=metrics_hdrs)
        by_status = resp.json()["tasks"]["tasks_by_status"]
        assert by_status["completed"] == 1

    def test_completed_count_accumulates(self):
        _reset()
        exec_hdrs = _exec_headers()
        metrics_hdrs = _metrics_headers()

        for _ in range(4):
            _run_task(exec_hdrs)

        resp = client.get("/metrics", headers=metrics_hdrs)
        by_status = resp.json()["tasks"]["tasks_by_status"]
        assert by_status["completed"] == 4


# ── C. Failed tasks are counted correctly ───────────────────────────


class TestFailedTaskCounting:
    def test_failed_task_counted_in_failed_bucket(self):
        _reset()
        exec_hdrs = _exec_headers()
        metrics_hdrs = _metrics_headers()

        _run_task(
            exec_hdrs, operation="bad_op_that_fails", execution_class="side_effect", inputs={}
        )

        resp = client.get("/metrics", headers=metrics_hdrs)
        by_status = resp.json()["tasks"]["tasks_by_status"]
        assert by_status["failed"] == 1

    def test_failed_task_not_in_completed_bucket(self):
        _reset()
        exec_hdrs = _exec_headers()
        metrics_hdrs = _metrics_headers()

        _run_task(exec_hdrs, operation="bad_op", execution_class="side_effect", inputs={})

        resp = client.get("/metrics", headers=metrics_hdrs)
        by_status = resp.json()["tasks"]["tasks_by_status"]
        assert by_status["completed"] == 0

    def test_mixed_completed_and_failed_counts(self):
        _reset()
        exec_hdrs = _exec_headers()
        metrics_hdrs = _metrics_headers()

        # 2 successful
        _run_task(exec_hdrs)
        _run_task(exec_hdrs)

        # 1 failed
        _run_task(exec_hdrs, operation="bad_op", execution_class="side_effect", inputs={})

        resp = client.get("/metrics", headers=metrics_hdrs)
        by_status = resp.json()["tasks"]["tasks_by_status"]
        assert by_status["completed"] == 2
        assert by_status["failed"] == 1
        assert resp.json()["tasks"]["total_tasks"] == 3

    def test_multiple_failed_tasks_accumulate(self):
        _reset()
        exec_hdrs = _exec_headers()
        metrics_hdrs = _metrics_headers()

        for _ in range(3):
            _run_task(exec_hdrs, operation="bad_op", execution_class="side_effect", inputs={})

        resp = client.get("/metrics", headers=metrics_hdrs)
        by_status = resp.json()["tasks"]["tasks_by_status"]
        assert by_status["failed"] == 3


# ── D. recent_tasks summaries ────────────────────────────────────────


class TestRecentTasks:
    def test_recent_tasks_empty_initially(self):
        _reset()
        headers = _metrics_headers()
        resp = client.get("/metrics", headers=headers)
        assert resp.json()["tasks"]["recent_tasks"] == []

    def test_recent_tasks_includes_one_task_summary(self):
        _reset()
        exec_hdrs = _exec_headers()
        metrics_hdrs = _metrics_headers()

        task_resp = _run_task(exec_hdrs)
        task_id = task_resp.json()["id"]

        resp = client.get("/metrics", headers=metrics_hdrs)
        recent = resp.json()["tasks"]["recent_tasks"]
        assert len(recent) == 1
        assert recent[0]["id"] == task_id

    def test_recent_task_summary_has_required_fields(self):
        _reset()
        exec_hdrs = _exec_headers()
        metrics_hdrs = _metrics_headers()

        _run_task(exec_hdrs)

        resp = client.get("/metrics", headers=metrics_hdrs)
        summary = resp.json()["tasks"]["recent_tasks"][0]
        assert "id" in summary
        assert "status" in summary
        assert "step_count" in summary
        assert "created_at" in summary

    def test_recent_tasks_capped_at_five(self):
        _reset()
        exec_hdrs = _exec_headers()
        metrics_hdrs = _metrics_headers()

        for _ in range(8):
            _run_task(exec_hdrs)

        resp = client.get("/metrics", headers=metrics_hdrs)
        recent = resp.json()["tasks"]["recent_tasks"]
        assert len(recent) == 5

    def test_recent_tasks_includes_step_count(self):
        _reset()
        exec_hdrs = _exec_headers()
        metrics_hdrs = _metrics_headers()

        # 2-step task
        client.post(
            "/tasks",
            json={
                "steps": [
                    {
                        "operation": "classify_intent",
                        "inputs_template": {"prompt": "hi", "system_prompt": "", "max_tokens": 100},
                        "output_key": "s1",
                    },
                    {
                        "operation": "summarize",
                        "inputs_template": {
                            "prompt": "sum",
                            "system_prompt": "",
                            "max_tokens": 100,
                        },
                        "output_key": "s2",
                    },
                ]
            },
            headers=exec_hdrs,
        )

        resp = client.get("/metrics", headers=metrics_hdrs)
        recent = resp.json()["tasks"]["recent_tasks"]
        assert recent[0]["step_count"] == 2

    def test_recent_tasks_status_reflects_actual_status(self):
        _reset()
        exec_hdrs = _exec_headers()
        metrics_hdrs = _metrics_headers()

        _run_task(exec_hdrs, operation="bad_op", execution_class="side_effect", inputs={})

        resp = client.get("/metrics", headers=metrics_hdrs)
        recent = resp.json()["tasks"]["recent_tasks"]
        assert recent[0]["status"] == "failed"

    def test_recent_tasks_completed_status(self):
        _reset()
        exec_hdrs = _exec_headers()
        metrics_hdrs = _metrics_headers()

        _run_task(exec_hdrs)

        resp = client.get("/metrics", headers=metrics_hdrs)
        recent = resp.json()["tasks"]["recent_tasks"]
        assert recent[0]["status"] == "completed"
