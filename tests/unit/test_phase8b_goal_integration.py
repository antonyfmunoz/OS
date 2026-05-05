"""Phase 8B — Goal engine + strategy integration tests."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

from umh.goals.models import Goal, GoalPolicy, GoalStatus
from umh.goals.store import reset_goal_store, get_goal_store
from umh.goals.goal_engine import GoalEngine, reset_goal_engine
from umh.strategy.decomposer import reset_strategy_cache, cache_strategy, get_cached_strategy
from umh.strategy.models import Strategy, StrategyStep, StepStatus, StepType
from umh.events.stream import reset_event_stream, get_event_stream


@dataclass
class MockPlan:
    plan_id: str = "plan_test"
    status: object = None

    def __post_init__(self):
        if self.status is None:
            from umh.planning.models import PlanStatus

            self.status = PlanStatus.VALIDATED


@dataclass
class MockTask:
    id: str = "task_test"


class TestGoalEngineStrategyIntegration:
    def setup_method(self):
        reset_goal_store()
        reset_strategy_cache()
        reset_event_stream()
        self.engine = GoalEngine()
        self.store = get_goal_store()

    def _make_goal(self, objective="build a test system", **kwargs):
        goal = Goal(name="test", objective=objective, **kwargs)
        return self.store.create(goal)

    @patch("umh.planning.planner.execute_plan")
    @patch("umh.planning.planner.create_plan_from_raw")
    def test_evaluate_creates_strategy(self, mock_plan, mock_exec):
        mock_plan.return_value = MockPlan()
        mock_exec.return_value = MockTask()
        goal = self._make_goal()
        result = self.engine.evaluate_goal(goal)
        assert result["status"] == "evaluated"
        assert "strategy_progress" in result
        cached = get_cached_strategy(goal.id)
        assert cached is not None

    @patch("umh.planning.planner.execute_plan")
    @patch("umh.planning.planner.create_plan_from_raw")
    def test_evaluate_reuses_cached_strategy(self, mock_plan, mock_exec):
        mock_plan.return_value = MockPlan()
        mock_exec.return_value = MockTask()
        goal = self._make_goal()
        self.engine.evaluate_goal(goal)
        cached1 = get_cached_strategy(goal.id)
        self.engine.evaluate_goal(goal)
        cached2 = get_cached_strategy(goal.id)
        assert cached1.id == cached2.id

    @patch("umh.planning.planner.execute_plan")
    @patch("umh.planning.planner.create_plan_from_raw")
    def test_evaluate_uses_ready_steps(self, mock_plan, mock_exec):
        mock_plan.return_value = MockPlan()
        mock_exec.return_value = MockTask()
        goal = self._make_goal()
        result = self.engine.evaluate_goal(goal)
        assert result["tasks_created"] >= 1
        assert len(result["actions"]) >= 1
        for action in result["actions"]:
            assert "step_id" in action

    @patch("umh.planning.planner.execute_plan")
    @patch("umh.planning.planner.create_plan_from_raw")
    def test_max_tasks_per_cycle_respected(self, mock_plan, mock_exec):
        mock_plan.return_value = MockPlan()
        mock_exec.return_value = MockTask()
        goal = self._make_goal(policy=GoalPolicy(max_tasks_per_cycle=1))
        result = self.engine.evaluate_goal(goal)
        assert result["tasks_created"] <= 1

    @patch("umh.planning.planner.execute_plan")
    @patch("umh.planning.planner.create_plan_from_raw")
    def test_step_gets_task_id(self, mock_plan, mock_exec):
        mock_plan.return_value = MockPlan()
        mock_exec.return_value = MockTask(id="task_xyz")
        goal = self._make_goal()
        self.engine.evaluate_goal(goal)
        cached = get_cached_strategy(goal.id)
        has_task = any("task_xyz" in step.task_ids for step in cached.steps if step.task_ids)
        assert has_task

    @patch("umh.planning.planner.execute_plan")
    @patch("umh.planning.planner.create_plan_from_raw")
    def test_strategy_applied_event(self, mock_plan, mock_exec):
        mock_plan.return_value = MockPlan()
        mock_exec.return_value = MockTask()
        goal = self._make_goal()
        self.engine.evaluate_goal(goal)
        events = get_event_stream().list_events()
        types = [e.type for e in events]
        assert "strategy.applied" in types

    def test_evaluate_skips_inactive_goal(self):
        goal = self._make_goal()
        self.store.pause(goal.id)
        goal = self.store.get(goal.id)
        result = self.engine.evaluate_goal(goal)
        assert result["status"] == "skipped"

    @patch("umh.planning.planner.execute_plan")
    @patch("umh.planning.planner.create_plan_from_raw")
    def test_evaluate_completes_when_all_done(self, mock_plan, mock_exec):
        goal = self._make_goal()
        goal.progress = 1.0
        result = self.engine.evaluate_goal(goal)
        assert result["status"] == "completed"

    @patch("umh.strategy.decomposer.decompose_goal", side_effect=ValueError("decomp failed"))
    def test_decomposition_failure_returns_error(self, mock_decomp):
        goal = self._make_goal(objective="unique xyz no template match 12345")
        result = self.engine.evaluate_goal(goal)
        assert result["status"] == "error"
        assert "decomp failed" in result.get("error", "")

    @patch("umh.planning.planner.execute_plan")
    @patch("umh.planning.planner.create_plan_from_raw")
    def test_evaluate_waiting_when_no_ready_steps(self, mock_plan, mock_exec):
        goal = self._make_goal()
        # Pre-cache a strategy with all steps having unsatisfied deps
        steps = [
            StrategyStep(description="a", id="s1", dependencies=["s2"]),
            StrategyStep(description="b", id="s2", dependencies=["s1"]),
        ]
        strat = Strategy(goal_id=goal.id, objective=goal.objective, steps=steps)
        cache_strategy(strat)
        result = self.engine.evaluate_goal(goal)
        assert result["status"] == "waiting"

    @patch("umh.planning.planner.execute_plan", side_effect=RuntimeError("exec failed"))
    @patch("umh.planning.planner.create_plan_from_raw")
    def test_task_failure_with_auto_pause(self, mock_plan, mock_exec):
        mock_plan.return_value = MockPlan()
        goal = self._make_goal(policy=GoalPolicy(auto_pause_on_failure=True))
        result = self.engine.evaluate_goal(goal)
        assert result["status"] == "failed"
        updated = self.store.get(goal.id)
        assert updated.status == GoalStatus.FAILED

    @patch("umh.planning.planner.execute_plan")
    @patch("umh.planning.planner.create_plan_from_raw")
    def test_strategy_progress_updates_goal(self, mock_plan, mock_exec):
        mock_plan.return_value = MockPlan()
        mock_exec.return_value = MockTask()
        goal = self._make_goal()
        self.engine.evaluate_goal(goal)
        updated = self.store.get(goal.id)
        assert updated.tasks_created > 0

    def test_evaluate_now_not_found(self):
        result = self.engine.evaluate_now("nonexistent_goal")
        assert result["status"] == "error"

    @patch("umh.planning.planner.execute_plan")
    @patch("umh.planning.planner.create_plan_from_raw")
    def test_evaluate_now_success(self, mock_plan, mock_exec):
        mock_plan.return_value = MockPlan()
        mock_exec.return_value = MockTask()
        goal = self._make_goal()
        result = self.engine.evaluate_now(goal.id)
        assert result["status"] == "evaluated"
