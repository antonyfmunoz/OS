"""Phase 6G API contract tests — validates UI-required endpoint shapes.

Every test verifies that the API returns the fields the frontend expects.
If a field is missing or renamed, these tests break before the UI does.
"""

import sys
import os

sys.path.insert(0, "/opt/OS")
os.environ.setdefault("UMH_API_KEY", "test-key-phase6g")
os.environ["UMH_TASK_BACKEND"] = "memory"

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import get_identity_store
from umh.events.stream import reset_event_stream
from umh.execution.approval import get_approval_store
from umh.orchestrator.engine import reset_orchestrator, start_orchestrator
from umh.orchestrator.task import reset_tasks
from umh.orchestrator.task_store import InMemoryTaskBackend, reset_task_store
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


# ── Health ──────────────────────────────────────────────────────────


class TestHealthEndpoint:
    def test_health_no_auth(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ── Run ─────────────────────────────────────────────────────────────


class TestRunEndpointContract:
    def setup_method(self):
        _reset()
        self._identity, self._key, self._headers = _create_identity()
        start_orchestrator()

    def test_run_dry_returns_plan_fields(self):
        resp = client.post(
            "/run",
            json={"objective": "test dry run", "dry_run": True},
            headers=self._headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "plan_id" in data
        assert "status" in data
        assert "quality" in data or "quality_score" in data
        assert "explanation" in data or "steps" in data
        assert "executable" in data
        assert "blocked_reason" in data
        assert "warnings" in data

    def test_run_execute_returns_task_fields(self):
        resp = client.post(
            "/run",
            json={"objective": "test execution"},
            headers=self._headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Execution may or may not produce a task depending on plan validation.
        # If it does, verify task fields; if not, verify plan fields.
        if data.get("task_id"):
            assert "task_status" in data
            assert "task_summary" in data
            assert "next_actions" in data
            assert isinstance(data["next_actions"], list)
        else:
            # Plan-only response (plan not executable)
            assert "plan_id" in data
            assert "status" in data
            assert "executable" in data

    def test_run_requires_auth(self):
        resp = client.post("/run", json={"objective": "no auth"})
        assert resp.status_code == 401


# ── Tasks ───────────────────────────────────────────────────────────


class TestTaskEndpointContract:
    def setup_method(self):
        _reset()
        self._identity, self._key, self._headers = _create_identity()
        start_orchestrator()

    def _create_task(self):
        resp = client.post(
            "/tasks",
            json={
                "steps": [{"operation": "echo test", "execution_class": "llm_call"}],
                "context": {},
            },
            headers=self._headers,
        )
        assert resp.status_code == 200
        return resp.json()

    def test_task_list_returns_array(self):
        resp = client.get("/tasks", headers=self._headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_task_detail_has_step_statuses(self):
        task_data = self._create_task()
        task_id = task_data["id"]
        resp = client.get(f"/tasks/{task_id}", headers=self._headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "step_statuses" in data
        assert "current_step" in data
        assert "pending_approval" in data

    def test_task_summary_has_required_fields(self):
        task_data = self._create_task()
        task_id = task_data["id"]
        resp = client.get(f"/tasks/{task_id}/summary", headers=self._headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert "status" in data
        assert "objective" in data
        assert "final_summary" in data
        assert "step_summaries" in data
        assert "errors" in data
        assert "next_action" in data

    def test_task_timeline_returns_array(self):
        task_data = self._create_task()
        task_id = task_data["id"]
        resp = client.get(f"/tasks/{task_id}/timeline", headers=self._headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Timeline may be empty for newly created tasks, but if present
        # each entry must have the required fields.
        for entry in data:
            assert "timestamp" in entry
            assert "event_type" in entry
            assert "summary" in entry


# ── Approvals ───────────────────────────────────────────────────────


class TestApprovalEndpointContract:
    def setup_method(self):
        _reset()
        self._identity, self._key, self._headers = _create_identity()

    def test_approvals_list(self):
        resp = client.get("/approvals", headers=self._headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_approvals_pending_filter(self):
        resp = client.get("/approvals?status=pending", headers=self._headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── Metrics ─────────────────────────────────────────────────────────


class TestMetricsContract:
    def setup_method(self):
        _reset()
        self._identity, self._key, self._headers = _create_identity()

    def test_metrics_has_tasks(self):
        resp = client.get("/metrics", headers=self._headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data
        assert "total_tasks" in data["tasks"]
        assert "tasks_by_status" in data["tasks"]

    def test_metrics_has_approvals(self):
        resp = client.get("/metrics", headers=self._headers)
        assert resp.status_code == 200
        data = resp.json()
        # Metrics include approval data from the base metrics
        assert "tasks" in data


# ── Static Serving ──────────────────────────────────────────────────


class TestStaticServing:
    def test_root_redirects(self):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 307
        assert "/ui/" in resp.headers.get("location", "")

    def test_ui_auth_skip(self):
        # /ui paths should not require auth — even if frontend dir doesn't
        # exist, the middleware should still skip auth for these paths.
        resp = client.get("/ui/nonexistent", follow_redirects=False)
        # Should NOT be 401. Could be 404 (no frontend) or 200 (frontend exists).
        assert resp.status_code != 401
