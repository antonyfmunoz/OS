"""Tests for Phase 8A: Persistent Goal System — GoalEngine evaluation.

Verifies:
- Goal evaluation creates tasks via planning pipeline
- Policy enforcement (pause, max tasks, failure handling)
- Event emission on evaluation
- Engine lifecycle (start/stop)
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import os

os.environ.setdefault("UMH_API_KEY", "test-key-phase8a")

from unittest.mock import MagicMock, patch

import pytest

from umh.goals.models import Goal, GoalPriority, GoalStatus
from umh.goals.store import get_goal_store, reset_goal_store
from umh.goals.goal_engine import GoalEngine, get_goal_engine, reset_goal_engine
from umh.events.stream import get_event_stream, reset_event_stream


@pytest.fixture(autouse=True)
def clean_state():
    reset_goal_store()
    reset_event_stream()
    reset_goal_engine()
    yield
    reset_goal_store()
    reset_event_stream()


def _mock_planning():
    """Build mock patches for planning pipeline functions."""
    from umh.planning.models import PlanStatus

    mock_plan = MagicMock()
    mock_plan.status = PlanStatus.VALIDATED
    mock_plan.plan_id = "eplan_goaltest"
    mock_plan.quality_score = {"verdict": "pass", "score": 1.0}
    mock_plan.objective = MagicMock()
    mock_plan.objective.dry_run = False

    mock_task = MagicMock()
    mock_task.id = "task_goaltest"
    mock_task.status = MagicMock(value="completed")

    mock_create = patch(
        "umh.planning.planner.create_plan_from_raw", return_value=mock_plan
    )
    mock_exec = patch(
        "umh.planning.planner.execute_plan", return_value=mock_task
    )
    return mock_create, mock_exec, mock_plan, mock_task


def _make_goal(**kwargs) -> Goal:
    """Create and store a goal with defaults."""
    defaults = {"name": "test-goal", "objective": "test objective"}
    defaults.update(kwargs)
    store = get_goal_store()
    goal = Goal(**defaults)
    store.create(goal)
    return goal


# ── A. Goal Evaluation Tests ──────────────────────────────────────────


class TestGoalEvaluation:
    def test_evaluate_goal_creates_task(self):
        """Evaluating an active goal produces tasks via planning pipeline."""
        goal = _make_goal()
        engine = GoalEngine()
        mock_create, mock_exec, _, _ = _mock_planning()

        with mock_create as mc, mock_exec as me:
            result = engine.evaluate_goal(goal)

        assert result["status"] == "evaluated"
        assert result["tasks_created"] >= 1
        mc.assert_called()
        me.assert_called()

    def test_evaluate_goal_skips_paused(self):
        """Paused goals return skipped status."""
        goal = _make_goal()
        store = get_goal_store()
        store.pause(goal.id)
        # Re-fetch after pause
        goal = store.get(goal.id)
        engine = GoalEngine()
        result = engine.evaluate_goal(goal)
        assert result["status"] == "skipped"

    def test_evaluate_goal_respects_max_tasks_per_cycle(self):
        """Engine creates at most max_tasks_per_cycle tasks."""
        from umh.goals.models import GoalPolicy

        goal = _make_goal()
        goal.policy = GoalPolicy(max_tasks_per_cycle=2)
        engine = GoalEngine()
        mock_create, mock_exec, _, _ = _mock_planning()

        with mock_create as mc, mock_exec:
            result = engine.evaluate_goal(goal)

        assert result["tasks_created"] <= 2
        assert mc.call_count <= 2

    def test_evaluate_goal_emits_events(self):
        """Goal evaluation publishes goal.evaluated events."""
        goal = _make_goal()
        engine = GoalEngine()
        mock_create, mock_exec, _, _ = _mock_planning()

        with mock_create, mock_exec:
            engine.evaluate_goal(goal)

        stream = get_event_stream()
        events = stream.list_events(limit=50)
        event_types = [e.type for e in events]
        assert "goal.evaluated" in event_types

    def test_evaluate_goal_updates_last_evaluated_at(self):
        """Evaluation sets last_evaluated_at on the goal."""
        goal = _make_goal()
        engine = GoalEngine()
        mock_create, mock_exec, _, _ = _mock_planning()
        assert goal.last_evaluated_at == ""

        with mock_create, mock_exec:
            engine.evaluate_goal(goal)

        updated = get_goal_store().get(goal.id)
        assert updated is not None
        assert updated.last_evaluated_at != ""

    def test_evaluate_now_nonexistent(self):
        """evaluate_now on non-existent goal returns error."""
        engine = GoalEngine()
        result = engine.evaluate_now("goal_does_not_exist")
        assert result["status"] == "error"
        assert "not found" in result.get("error", "")

    def test_evaluate_now_active_goal(self):
        """evaluate_now on an active goal triggers full evaluation."""
        goal = _make_goal()
        engine = GoalEngine()
        mock_create, mock_exec, _, _ = _mock_planning()

        with mock_create, mock_exec:
            result = engine.evaluate_now(goal.id)

        assert result["status"] == "evaluated"

    def test_evaluate_completed_goal(self):
        """Goal with progress >= 1.0 is auto-completed."""
        goal = _make_goal()
        goal.progress = 1.0
        engine = GoalEngine()
        result = engine.evaluate_goal(goal)
        assert result["status"] == "completed"

        updated = get_goal_store().get(goal.id)
        assert updated is not None
        assert updated.status == GoalStatus.COMPLETED

    def test_evaluate_goal_policy_denial(self):
        """Goal over max_active_tasks is denied by policy."""
        from umh.goals.models import GoalPolicy

        goal = _make_goal()
        goal.policy = GoalPolicy(max_active_tasks=0)
        goal.tasks_created = 1  # exceeds max_active_tasks=0

        engine = GoalEngine()
        result = engine.evaluate_goal(goal)
        assert result["status"] == "skipped"

    def test_evaluate_goal_auto_pause_on_failure(self):
        """When task creation fails and auto_pause_on_failure is True, goal fails."""
        goal = _make_goal()

        mock_create = patch(
            "umh.planning.planner.create_plan_from_raw",
            side_effect=RuntimeError("planning failed"),
        )
        mock_exec = patch(
            "umh.planning.planner.execute_plan",
            return_value=MagicMock(),
        )

        engine = GoalEngine()
        with mock_create, mock_exec:
            result = engine.evaluate_goal(goal)

        assert result["status"] == "failed"
        updated = get_goal_store().get(goal.id)
        assert updated is not None
        assert updated.status == GoalStatus.FAILED

    def test_evaluate_goal_tasks_created_count(self):
        """Result dict includes correct tasks_created count."""
        goal = _make_goal()
        engine = GoalEngine()
        mock_create, mock_exec, _, _ = _mock_planning()

        with mock_create, mock_exec:
            result = engine.evaluate_goal(goal)

        assert "tasks_created" in result
        assert isinstance(result["tasks_created"], int)
        assert result["tasks_created"] > 0

    def test_evaluate_goal_returns_dict(self):
        """evaluate_goal always returns a dict."""
        goal = _make_goal()
        engine = GoalEngine()
        mock_create, mock_exec, _, _ = _mock_planning()

        with mock_create, mock_exec:
            result = engine.evaluate_goal(goal)

        assert isinstance(result, dict)
        assert "status" in result
        assert "actions" in result

    def test_evaluate_goal_no_planning_bypass(self):
        """Engine always calls create_plan_from_raw, never bypasses planning."""
        goal = _make_goal()
        engine = GoalEngine()
        mock_create, mock_exec, _, _ = _mock_planning()

        with mock_create as mc, mock_exec:
            engine.evaluate_goal(goal)

        mc.assert_called()
        # Verify the first positional argument is the goal's objective
        call_args = mc.call_args
        assert call_args is not None
        assert goal.objective in str(call_args)


# ── B. Engine Lifecycle Tests ──────────────────────────────────────────


class TestGoalEngineLifecycle:
    def test_engine_start_stop(self):
        """Engine can start and stop without error."""
        engine = GoalEngine(poll_interval=0.1)
        engine.start()
        assert engine.is_running()
        engine.stop()
        assert not engine.is_running()

    def test_engine_is_running(self):
        """is_running reflects engine state accurately."""
        engine = GoalEngine(poll_interval=0.1)
        assert not engine.is_running()
        engine.start()
        assert engine.is_running()
        engine.stop()
        assert not engine.is_running()
