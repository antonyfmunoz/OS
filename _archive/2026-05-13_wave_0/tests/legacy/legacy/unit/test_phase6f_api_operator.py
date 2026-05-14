"""Tests for Phase 6F — API Operator Response Upgrade.

Covers POST /run, GET /tasks/{id}/summary, _build_next_actions helper,
and verifies existing endpoints remain unbroken.
"""

import sys
import os

sys.path.insert(0, "/opt/OS")
os.environ.setdefault("UMH_API_KEY", "test-key-phase6f")
os.environ["UMH_TASK_BACKEND"] = "memory"

import pytest
from fastapi.testclient import TestClient

from umh.control.api import app, _build_next_actions
from umh.orchestrator.task import (
    Task,
    TaskStep,
    TaskStatus,
    StepStatus,
    _save_task,
    reset_tasks,
)
from umh.planning.planner import reset_plans
from umh.planning.templates import _TEMPLATE_REGISTRY
from umh.planning.models import (
    ExecutionPlan,
    ExecutionPlanStep,
    PlanObjective,
    PlanSource,
    PlanStatus,
)

HEADERS = {"X-API-Key": "test-key-phase6f"}


@pytest.fixture(autouse=True)
def _clean_state():
    """Reset task and plan stores between tests."""
    reset_tasks()
    reset_plans()
    saved_templates = dict(_TEMPLATE_REGISTRY)
    yield
    reset_tasks()
    reset_plans()
    _TEMPLATE_REGISTRY.clear()
    _TEMPLATE_REGISTRY.update(saved_templates)


@pytest.fixture
def client():
    return TestClient(app)


def _register_echo_template():
    """Register a simple echo template that always validates.

    Uses 'summarize_text' key which is what reconstruct_objective
    produces for inputs containing 'summarize'.
    """

    def echo_template(objective: PlanObjective) -> ExecutionPlan:
        return ExecutionPlan(
            objective=objective,
            steps=[
                ExecutionPlanStep(
                    name="echo",
                    operation="classify_intent",
                    inputs={"prompt": objective.title},
                    execution_class="llm_call",
                    rationale="Echo the objective",
                )
            ],
            source=PlanSource.TEMPLATE,
            confidence=1.0,
        )

    _TEMPLATE_REGISTRY["summarize_text"] = echo_template


# ── TestRunEndpoint ────────────────────────────────────────────────


class TestRunEndpoint:
    def test_run_valid_objective_returns_plan_and_task(self, client):
        _register_echo_template()
        resp = client.post(
            "/run",
            json={"objective": "summarize the current state"},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Must have plan fields
        assert "plan_id" in data
        assert "executable" in data
        # Must have task fields from execution
        assert "task_status" in data
        assert "task_summary" in data
        assert "next_actions" in data
        assert isinstance(data["next_actions"], list)

    def test_run_dry_run_returns_plan_only(self, client):
        _register_echo_template()
        resp = client.post(
            "/run",
            json={"objective": "summarize the current state", "dry_run": True},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "plan_id" in data
        assert "executable" in data
        # No task_status when dry_run (plan returned, not executed)
        assert "task_status" not in data

    def test_run_invalid_objective_returns_quality_info(self, client):
        """When no template matches and no LLM, plan is rejected."""
        resp = client.post(
            "/run",
            json={"objective": "nonexistent_operation_xyz"},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["executable"] is False
        assert data["blocked_reason"] != ""
        # Should NOT have task_status (plan not executable)
        assert "task_status" not in data

    def test_run_requires_auth(self, client):
        resp = client.post("/run", json={"objective": "test"})
        assert resp.status_code == 401


# ── TestSummaryEndpoint ────────────────────────────────────────────


class TestSummaryEndpoint:
    def test_summary_for_completed_task(self, client):
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={"prompt": "hello"},
                    execution_class="llm_call",
                )
            ],
            issued_by="test",
        )
        task.status = TaskStatus.COMPLETED
        task.steps[0].status = StepStatus.COMPLETED
        task.steps[0].result = {
            "status": "succeeded",
            "outputs": {"response": "greeting"},
        }
        _save_task(task)

        resp = client.get(f"/tasks/{task.id}/summary", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task.id
        assert data["status"] == "completed"
        assert data["completed_steps"] == 1
        assert "final_summary" in data

    def test_summary_404_for_missing_task(self, client):
        resp = client.get("/tasks/task_nonexistent/summary", headers=HEADERS)
        assert resp.status_code == 404

    def test_summary_requires_auth(self, client):
        resp = client.get("/tasks/task_test/summary")
        assert resp.status_code == 401


# ── TestNextActions ────────────────────────────────────────────────


class TestNextActions:
    def test_paused_task_has_approve_deny_actions(self):
        task = Task(
            steps=[TaskStep(operation="test", execution_class="llm_call")],
            issued_by="test",
        )
        task.status = TaskStatus.PAUSED
        task.paused_approval_id = "apr_12345"
        actions = _build_next_actions(task)
        assert any("approve" in a.lower() for a in actions)
        assert any("deny" in a.lower() for a in actions)
        assert any("cancel" in a.lower() for a in actions)
        assert f"apr_12345" in " ".join(actions)

    def test_failed_task_has_retry_action(self):
        task = Task(
            steps=[TaskStep(operation="test", execution_class="llm_call")],
            issued_by="test",
        )
        task.status = TaskStatus.FAILED
        actions = _build_next_actions(task)
        assert any("retry" in a.lower() for a in actions)
        assert any("timeline" in a.lower() for a in actions)

    def test_completed_task_has_summary_timeline_actions(self):
        task = Task(
            steps=[TaskStep(operation="test", execution_class="llm_call")],
            issued_by="test",
        )
        task.status = TaskStatus.COMPLETED
        actions = _build_next_actions(task)
        assert any("summary" in a.lower() for a in actions)
        assert any("timeline" in a.lower() for a in actions)

    def test_pending_task_has_watch_cancel_actions(self):
        task = Task(
            steps=[TaskStep(operation="test", execution_class="llm_call")],
            issued_by="test",
        )
        task.status = TaskStatus.PENDING
        actions = _build_next_actions(task)
        assert any("watch" in a.lower() or "get" in a.lower() for a in actions)
        assert any("cancel" in a.lower() for a in actions)


# ── TestExistingEndpoints ──────────────────────────────────────────


class TestExistingEndpoints:
    def test_post_plans_still_works(self, client):
        _register_echo_template()
        resp = client.post(
            "/plans",
            json={"raw_input": "summarize the report"},
            headers=HEADERS,
        )
        assert resp.status_code in (200, 422)
        data = resp.json()
        assert "plan_id" in data

    def test_post_tasks_still_works(self, client):
        resp = client.post(
            "/tasks",
            json={
                "steps": [{"operation": "classify_intent", "inputs_template": {"prompt": "test"}}],
                "context": {},
            },
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    def test_metrics_unaffected(self, client):
        resp = client.get("/metrics", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data
        assert "plans" in data

    def test_execute_plan_has_next_actions(self, client):
        """POST /plans/{id}/execute now includes next_actions."""
        _register_echo_template()
        # Create a plan first
        plan_resp = client.post(
            "/plans",
            json={"raw_input": "summarize the report"},
            headers=HEADERS,
        )
        assert plan_resp.status_code == 200
        plan_id = plan_resp.json()["plan_id"]

        # Execute it
        exec_resp = client.post(f"/plans/{plan_id}/execute", headers=HEADERS)
        assert exec_resp.status_code == 200
        data = exec_resp.json()
        assert "next_actions" in data
        assert isinstance(data["next_actions"], list)

    def test_health_still_works(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
