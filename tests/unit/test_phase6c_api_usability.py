"""Tests for Phase 6C: API Response Usability Enrichments.

Verifies:
- POST /plans includes executable, blocked_reason, warnings
- POST /plans/{id}/execute includes plan_id, objective_summary, step_count,
  approval_required, approval_id
- GET /tasks/{id} includes step_statuses, current_step, pending_approval
- GET /metrics includes tasks, plans, approvals sections
- Quality warn plans surface warnings in responses
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase6c")
os.environ["PYTEST_CURRENT_TEST"] = "1"

from fastapi.testclient import TestClient

from umh.control.api import app
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
    get_plan,
    reset_plans,
)

client = TestClient(app)


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


def _create_identity(name="admin", scopes=None):
    store = get_identity_store()
    identity, raw_key = store.create_identity(name, scopes or ["admin"])
    return identity, raw_key, {"X-API-Key": raw_key}


# ── A. POST /plans enrichment tests ─────────────────────────────────


class TestPostPlansEnrichment:
    def test_post_plans_raw_input_includes_quality_explanation_executable(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            json={"raw_input": "check system health"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "quality" in data
        assert "explanation" in data
        assert "executable" in data
        assert data["executable"] is True

    def test_post_plans_invalid_returns_blocked_reason(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            json={"title": "nonexistent"},
            headers=headers,
        )
        assert resp.status_code == 422
        data = resp.json()
        assert "executable" in data
        assert data["executable"] is False
        assert "blocked_reason" in data
        assert data["blocked_reason"] != ""

    def test_post_plans_warn_includes_warnings(self):
        """Create a plan, manually set quality verdict to warn, then re-check via GET."""
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            json={"title": "summarize_text", "context": {"text": "hi"}},
            headers=headers,
        )
        assert resp.status_code == 200
        plan_id = resp.json()["plan_id"]

        # Manually set verdict to warn with reasons
        plan = get_plan(plan_id)
        plan.quality_score = {
            "verdict": "warn",
            "score": 0.55,
            "reasons": ["LLM-generated plan", "vague objective"],
            "dimensions": {},
        }

        # Execute the plan to get the warn-enriched response
        exec_resp = client.post(f"/plans/{plan_id}/execute", headers=headers)
        assert exec_resp.status_code == 200
        exec_data = exec_resp.json()
        assert "quality_warnings" in exec_data
        assert len(exec_data["quality_warnings"]) > 0


# ── B. POST /plans/{id}/execute enrichment tests ────────────────────


class TestExecutePlanEnrichment:
    def test_post_plans_execute_returns_task_summary(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            json={"title": "summarize_text", "context": {"text": "hello"}},
            headers=headers,
        )
        assert resp.status_code == 200
        plan_id = resp.json()["plan_id"]

        exec_resp = client.post(f"/plans/{plan_id}/execute", headers=headers)
        assert exec_resp.status_code == 200
        data = exec_resp.json()
        assert data["plan_id"] == plan_id
        assert "objective_summary" in data
        assert "summarize_text" in data["objective_summary"]
        assert "step_count" in data
        assert data["step_count"] >= 1

    def test_approval_gated_returns_approval_info(self):
        _start_fresh()
        _, _, headers = _create_identity()

        # Create plan with approval-gated step manually
        obj = PlanObjective(title="test_click")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(
                    name="click",
                    operation="computer_click",
                    inputs={"x": 10, "y": 20},
                    execution_class="side_effect",
                ),
            ],
            source=PlanSource.MANUAL,
            status=PlanStatus.VALIDATED,
        )
        # Save it so the API can find it
        from umh.planning.planner import _save_plan

        _save_plan(plan)

        exec_resp = client.post(
            f"/plans/{plan.plan_id}/execute",
            headers=headers,
        )
        assert exec_resp.status_code == 200
        data = exec_resp.json()
        assert data["approval_required"] is True
        assert data["approval_id"] != ""
        assert data["approval_id"].startswith("approval_")


# ── C. GET /tasks/{id} enrichment tests ─────────────────────────────


class TestGetTaskEnrichment:
    def test_get_task_includes_step_statuses(self):
        _reset()
        _, _, headers = _create_identity()

        # Create and execute a plan to get a task
        resp = client.post(
            "/plans",
            json={"title": "summarize_text", "context": {"text": "test step statuses"}},
            headers=headers,
        )
        plan_id = resp.json()["plan_id"]
        exec_resp = client.post(f"/plans/{plan_id}/execute", headers=headers)
        task_id = exec_resp.json()["id"]

        task_resp = client.get(f"/tasks/{task_id}", headers=headers)
        assert task_resp.status_code == 200
        data = task_resp.json()
        assert "step_statuses" in data
        assert isinstance(data["step_statuses"], list)
        assert len(data["step_statuses"]) >= 1
        assert "current_step" in data
        assert isinstance(data["current_step"], int)

    def test_get_task_pending_approval(self):
        _start_fresh()
        _, _, headers = _create_identity()

        # Create plan with approval-gated step
        obj = PlanObjective(title="test_approval_task")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(
                    name="click",
                    operation="computer_click",
                    inputs={"x": 10, "y": 20},
                    execution_class="side_effect",
                ),
            ],
            source=PlanSource.MANUAL,
            status=PlanStatus.VALIDATED,
        )
        from umh.planning.planner import _save_plan

        _save_plan(plan)

        exec_resp = client.post(
            f"/plans/{plan.plan_id}/execute",
            headers=headers,
        )
        assert exec_resp.status_code == 200
        task_id = exec_resp.json()["id"]

        task_resp = client.get(f"/tasks/{task_id}", headers=headers)
        assert task_resp.status_code == 200
        data = task_resp.json()
        assert "pending_approval" in data
        assert data["pending_approval"] is not None
        assert data["pending_approval"].startswith("approval_")


# ── D. GET /metrics enrichment tests ────────────────────────────────


class TestMetricsEnrichment:
    def test_metrics_includes_mvp_sections(self):
        _reset()
        _, _, headers = _create_identity()

        # Create at least one plan/task so metrics are non-empty
        client.post(
            "/plans",
            json={"title": "summarize_text", "context": {"text": "metrics test"}},
            headers=headers,
        )

        resp = client.get("/metrics", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data
        assert "plans" in data
        assert "approvals" in data
        assert "pending_count" in data["approvals"]
        assert "approvals_consumed" in data["approvals"]
        assert "approvals_denied" in data["approvals"]
