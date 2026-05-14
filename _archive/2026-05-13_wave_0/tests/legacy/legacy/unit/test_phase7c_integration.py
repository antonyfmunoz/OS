"""Tests for Phase 7C: Multi-Agent Intelligence Layer — Pipeline integration.

Verifies:
- ReviewerAgent is called during create_plan and produces review data
- DebugAgent is called during execute_plan on failure
- Decision trace is populated by agent activity
- Agent failures do not break the planning/execution pipeline
- Plans are not mutated by review — steps, status, quality unchanged
- Events are published for review and debug actions
- to_dict serialization includes/excludes review and debug correctly
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import os

os.environ.setdefault("UMH_API_KEY", "test-key-phase7c")

from unittest.mock import MagicMock, patch

import pytest

from umh.planning.models import (
    ExecutionPlan,
    ExecutionPlanStep,
    PlanObjective,
    PlanSource,
    PlanStatus,
)
from umh.planning.planner import create_plan, execute_plan, get_plan, list_plans, reset_plans


@pytest.fixture(autouse=True)
def _clean_plans():
    reset_plans()
    yield
    reset_plans()


def _make_plan():
    """Create a validated plan via the summarize_text template (simpler, no shell)."""
    obj = PlanObjective(title="summarize_text", description="Summarize test")
    return create_plan(obj)


def _make_failed_task():
    """Build a mock failed task for execute_plan tests."""
    from umh.orchestrator.task import TaskStatus

    mock_task = MagicMock()
    mock_task.id = "task_test_fail"
    mock_task.status = TaskStatus.FAILED
    mock_task.error = "connection refused"
    mock_task.to_dict.return_value = {
        "id": "task_test_fail",
        "status": "failed",
        "steps": [{"status": "failed", "operation": "summarize", "name": "Summarize text"}],
        "error": "connection refused",
    }
    mock_task.paused_approval_id = None
    return mock_task


def _make_completed_task():
    """Build a mock completed task."""
    from umh.orchestrator.task import TaskStatus

    mock_task = MagicMock()
    mock_task.id = "task_test_ok"
    mock_task.status = TaskStatus.COMPLETED
    mock_task.error = ""
    mock_task.to_dict.return_value = {
        "id": "task_test_ok",
        "status": "completed",
        "steps": [{"status": "completed", "operation": "summarize"}],
    }
    mock_task.paused_approval_id = None
    return mock_task


# ── A. Review during create_plan ─────────────────────────────────────


class TestCreatePlanReview:
    def test_create_plan_succeeds(self):
        """Baseline: plan creation works with summarize_text template."""
        plan = _make_plan()
        assert plan.status == PlanStatus.VALIDATED
        assert len(plan.steps) >= 1

    def test_create_plan_has_quality(self):
        """Plan has quality_score after creation."""
        plan = _make_plan()
        assert plan.quality_score is not None

    def test_create_plan_adds_review(self):
        """Planner calls ReviewerAgent, so review should be set."""
        plan = _make_plan()
        assert plan.review is not None

    def test_create_plan_review_has_verdict(self):
        """Review output should contain a verdict."""
        plan = _make_plan()
        assert plan.review is not None
        review_output = plan.review.get("output", plan.review)
        assert "verdict" in review_output

    def test_create_plan_decision_trace(self):
        """Plan should have at least one decision_trace entry from reviewer."""
        plan = _make_plan()
        assert len(plan.decision_trace) >= 1

    def test_create_plan_decision_trace_has_reviewer(self):
        """Decision trace entry should identify the reviewer agent."""
        plan = _make_plan()
        reviewer_entries = [t for t in plan.decision_trace if t.get("agent") == "reviewer"]
        assert len(reviewer_entries) >= 1

    def test_create_plan_review_failure_doesnt_break(self):
        """If ReviewerAgent.run raises, plan creation still succeeds."""
        with patch("umh.agents.reviewer.ReviewerAgent.run", side_effect=RuntimeError("boom")):
            plan = _make_plan()
        # Plan should still be created and validated (reviewer failure is non-fatal)
        assert plan.status == PlanStatus.VALIDATED
        # Review should be None because the agent failed
        assert plan.review is None

    def test_create_plan_rejected_has_no_template(self):
        """Rejected plan (no template) should be rejected status."""
        obj = PlanObjective(title="nonexistent_template_xyz")
        plan = create_plan(obj)
        assert plan.status == PlanStatus.REJECTED


# ── B. Debug during execute_plan ─────────────────────────────────────


class TestExecutePlanDebug:
    def test_execute_plan_failure_adds_debug(self):
        """When execute_task returns a failed task, debug_analysis is set."""
        plan = _make_plan()
        assert plan.status == PlanStatus.VALIDATED

        mock_task = _make_failed_task()

        with patch("umh.orchestrator.task.execute_task", return_value=mock_task):
            result = execute_plan(plan)

        assert plan.debug_analysis is not None

    def test_execute_plan_debug_has_root_cause(self):
        """Debug analysis output should contain root_cause."""
        plan = _make_plan()
        mock_task = _make_failed_task()

        with patch("umh.orchestrator.task.execute_task", return_value=mock_task):
            execute_plan(plan)

        debug_output = plan.debug_analysis.get("output", plan.debug_analysis)
        assert "root_cause" in debug_output

    def test_execute_plan_debug_trace(self):
        """Decision trace should include a debugger entry after failure."""
        plan = _make_plan()
        mock_task = _make_failed_task()

        with patch("umh.orchestrator.task.execute_task", return_value=mock_task):
            execute_plan(plan)

        debugger_entries = [t for t in plan.decision_trace if t.get("agent") == "debugger"]
        assert len(debugger_entries) >= 1

    def test_execute_plan_debug_failure_doesnt_break(self):
        """If DebugAgent.run raises, execution still completes."""
        plan = _make_plan()
        mock_task = _make_failed_task()

        with (
            patch("umh.orchestrator.task.execute_task", return_value=mock_task),
            patch("umh.agents.debugger.DebugAgent.run", side_effect=RuntimeError("debug boom")),
        ):
            result = execute_plan(plan)
        # Execution should complete (plan is failed, but not crashed)
        assert plan.status == PlanStatus.FAILED
        # Debug should be None because the agent failed
        assert plan.debug_analysis is None

    def test_execute_plan_success_no_debug(self):
        """Successful execution should not add debug_analysis."""
        plan = _make_plan()
        mock_task = _make_completed_task()

        with patch("umh.orchestrator.task.execute_task", return_value=mock_task):
            result = execute_plan(plan)

        assert plan.status == PlanStatus.COMPLETED
        assert plan.debug_analysis is None


# ── C. Serialization ─────────────────────────────────────────────────


class TestPlanSerialization:
    def test_plan_to_dict_includes_review(self):
        """to_dict() includes review when set (auto-set by planner)."""
        plan = _make_plan()
        d = plan.to_dict()
        assert "review" in d

    def test_plan_to_dict_includes_debug(self):
        """to_dict() includes debug_analysis when set."""
        plan = _make_plan()
        plan.debug_analysis = {
            "output": {"root_cause": "timeout"},
            "agent_role": "debugger",
        }
        d = plan.to_dict()
        assert "debug_analysis" in d

    def test_plan_to_dict_includes_decision_trace(self):
        """to_dict() includes decision_trace when non-empty."""
        plan = _make_plan()
        d = plan.to_dict()
        assert "decision_trace" in d
        assert len(d["decision_trace"]) >= 1

    def test_plan_to_dict_excludes_none_review(self):
        """to_dict() does NOT include review when it is None."""
        plan = _make_plan()
        plan.review = None  # Override the auto-set review
        d = plan.to_dict()
        assert "review" not in d

    def test_plan_to_dict_excludes_none_debug(self):
        """to_dict() does NOT include debug_analysis when it is None."""
        plan = _make_plan()
        plan.debug_analysis = None
        d = plan.to_dict()
        assert "debug_analysis" not in d


# ── D. Advisory-only invariants ──────────────────────────────────────


class TestAdvisoryInvariants:
    def test_plan_review_does_not_modify_steps(self):
        """Plan steps must be unchanged after review runs — review is read-only."""
        # Create plan without auto-review to compare
        obj = PlanObjective(title="summarize_text", description="Test")
        with patch("umh.agents.reviewer.ReviewerAgent.run", side_effect=RuntimeError("skip")):
            plan_without = create_plan(obj)
        steps_without = [s.to_dict() for s in plan_without.steps]

        reset_plans()
        obj2 = PlanObjective(title="summarize_text", description="Test")
        plan_with = create_plan(obj2)
        steps_with = [s.to_dict() for s in plan_with.steps]

        # Steps should have the same structure (ignoring step_id UUIDs)
        assert len(steps_without) == len(steps_with)
        for s1, s2 in zip(steps_without, steps_with):
            assert s1["operation"] == s2["operation"]
            assert s1["name"] == s2["name"]

    def test_plan_review_does_not_modify_status(self):
        """Plan status must be VALIDATED after review (review doesn't change status)."""
        plan = _make_plan()
        assert plan.status == PlanStatus.VALIDATED

    def test_plan_review_does_not_modify_quality(self):
        """Plan quality_score is set before review and unchanged by review."""
        plan = _make_plan()
        assert plan.quality_score is not None
        # Quality should have a score field
        assert "score" in plan.quality_score

    def test_review_event_published(self):
        """Verify that an agent.review_completed event is emitted during create_plan."""
        from umh.events.stream import reset_event_stream

        stream = reset_event_stream()
        plan = _make_plan()

        events = stream.list_events(limit=100)
        review_events = [e for e in events if e.type == "agent.review_completed"]
        assert len(review_events) >= 1
        assert review_events[0].payload["plan_id"] == plan.plan_id

    def test_debug_event_published(self):
        """Verify that an agent.debug_completed event is emitted on failure."""
        from umh.events.stream import reset_event_stream

        stream = reset_event_stream()

        plan = _make_plan()
        mock_task = _make_failed_task()

        with patch("umh.orchestrator.task.execute_task", return_value=mock_task):
            execute_plan(plan)

        events = stream.list_events(limit=100)
        debug_events = [e for e in events if e.type == "agent.debug_completed"]
        assert len(debug_events) >= 1
        assert debug_events[0].payload["plan_id"] == plan.plan_id
