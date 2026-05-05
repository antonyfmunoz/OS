"""Tests for Phase 7C: Multi-Agent Intelligence Layer — API + CLI.

Verifies:
- API plan responses include review/debug data when present
- API metrics includes agent counts
- CLI review command shows verdict and structured output
- CLI plan command shows review line when present
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase7c")

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from umh.control.api import app
from umh.planning.models import (
    ExecutionPlan,
    ExecutionPlanStep,
    PlanObjective,
    PlanSource,
    PlanStatus,
)
from umh.planning.planner import create_plan, get_plan, reset_plans

client = TestClient(app)
HEADERS = {"X-API-Key": "test-key-phase7c"}


@pytest.fixture(autouse=True)
def _clean_plans():
    reset_plans()
    yield
    reset_plans()


def _create_reviewed_plan():
    """Create a plan via template — planner auto-attaches review."""
    obj = PlanObjective(title="summarize_text", description="Summarize test")
    plan = create_plan(obj)
    return plan


# ── A. API plan responses ────────────────────────────────────────────


class TestAPIReview:
    def test_plan_response_includes_review(self):
        """POST /plans with a valid template should return plan data with review."""
        resp = client.post(
            "/plans",
            headers=HEADERS,
            json={"title": "summarize_text", "description": "Summarize test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "plan_id" in data
        assert "status" in data
        # Review should be in the enriched response
        assert "review" in data

    def test_plan_response_review_has_verdict(self):
        """Review in API response contains verdict."""
        resp = client.post(
            "/plans",
            headers=HEADERS,
            json={"title": "summarize_text", "description": "Summarize test"},
        )
        data = resp.json()
        review = data.get("review", {})
        review_output = review.get("output", review)
        assert "verdict" in review_output

    def test_plan_list_includes_review_status(self):
        """GET /plans — plans with reviews have review in their to_dict output."""
        _create_reviewed_plan()
        resp = client.get("/plans", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        # Plans returned via list_plans use to_dict which includes review
        plan_data = data[0]
        assert "review" in plan_data

    def test_plan_detail_includes_review(self):
        """GET /plans/{id} includes review (via to_dict)."""
        plan = _create_reviewed_plan()
        resp = client.get(f"/plans/{plan.plan_id}", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "review" in data

    def test_plan_execute_includes_review(self):
        """POST /plans/{id}/execute response includes review when present."""
        plan = _create_reviewed_plan()

        from umh.orchestrator.task import TaskStatus

        mock_task = MagicMock()
        mock_task.id = "task_api_exec"
        mock_task.status = TaskStatus.COMPLETED
        mock_task.paused_approval_id = None
        mock_task.to_dict.return_value = {
            "id": "task_api_exec",
            "status": "completed",
            "steps": [],
        }

        with patch("umh.orchestrator.task.execute_task", return_value=mock_task):
            resp = client.post(
                f"/plans/{plan.plan_id}/execute",
                headers=HEADERS,
            )

        assert resp.status_code == 200
        data = resp.json()
        # The execute endpoint enriches response with review
        assert "review" in data

    def test_metrics_includes_agents(self):
        """GET /metrics includes agents section."""
        resp = client.get("/metrics", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data

    def test_metrics_agents_plans_reviewed(self):
        """agents.plans_reviewed is an integer."""
        resp = client.get("/metrics", headers=HEADERS)
        data = resp.json()
        assert isinstance(data["agents"]["plans_reviewed"], int)

    def test_metrics_agents_counts_reviewed_plans(self):
        """After creating a plan, plans_reviewed should increment."""
        _create_reviewed_plan()
        resp = client.get("/metrics", headers=HEADERS)
        data = resp.json()
        assert data["agents"]["plans_reviewed"] >= 1

    def test_task_detail_includes_review(self):
        """GET /tasks/{id} includes review from the associated plan."""
        plan = _create_reviewed_plan()

        from umh.orchestrator.task import Task, TaskStep, _save_task

        task = Task(
            steps=[
                TaskStep(
                    operation="summarize",
                    inputs_template={"prompt": "test"},
                )
            ],
            context={"plan_id": plan.plan_id},
            issued_by="test",
        )
        _save_task(task)

        resp = client.get(f"/tasks/{task.id}", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        # The task endpoint looks up the plan and attaches review
        assert "review" in data

    def test_task_detail_no_review_when_no_plan(self):
        """Task without plan_id context should not have review."""
        from umh.orchestrator.task import Task, TaskStep, _save_task

        task = Task(
            steps=[TaskStep(operation="summarize", inputs_template={"prompt": "x"})],
            context={},
            issued_by="test",
        )
        _save_task(task)

        resp = client.get(f"/tasks/{task.id}", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "review" not in data


# ── B. CLI review command ────────────────────────────────────────────


class TestCLIReview:
    def test_cmd_review_shows_verdict(self, capsys):
        """cmd_review with a valid plan that has review data shows verdict."""
        from umh.control.cli import cmd_review

        plan = _create_reviewed_plan()

        args = MagicMock()
        args.plan_id = plan.plan_id
        args.json = False
        result = cmd_review(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Verdict:" in captured.out

    def test_cmd_review_json_output(self, capsys):
        """cmd_review --json outputs valid JSON with review data."""
        from umh.control.cli import cmd_review

        plan = _create_reviewed_plan()

        args = MagicMock()
        args.plan_id = plan.plan_id
        args.json = True
        result = cmd_review(args)
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, dict)
        assert "review" in data

    def test_cmd_review_missing_plan(self, capsys):
        """cmd_review returns 1 for a nonexistent plan."""
        from umh.control.cli import cmd_review

        args = MagicMock()
        args.plan_id = "eplan_nonexistent"
        args.json = False
        result = cmd_review(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()

    def test_cmd_plan_shows_review(self, capsys):
        """cmd_plan output shows review line when review is present."""
        from umh.control.cli import cmd_plan

        plan = _create_reviewed_plan()

        with patch("umh.planning.planner.create_plan_from_raw", return_value=plan):
            args = MagicMock()
            args.objective = "summarize text"
            args.json = False
            result = cmd_plan(args)

        assert result == 0
        captured = capsys.readouterr()
        # The cmd_plan function shows "Review:" line when review is set
        assert "Review:" in captured.out
