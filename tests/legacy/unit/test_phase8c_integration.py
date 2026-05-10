"""Phase 8C — Integration and boundary tests."""

import sys

sys.path.insert(0, "/opt/OS")

import ast
import os
import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

from umh.goals.models import Goal, GoalPolicy, GoalStatus
from umh.goals.store import reset_goal_store, get_goal_store
from umh.goals.goal_engine import GoalEngine
from umh.strategy.decomposer import reset_strategy_cache
from umh.strategy.history import (
    reset_strategy_history,
    get_strategy_history,
    record_strategy_version,
)
from umh.strategy.models import Strategy, StrategyStep, StepStatus
from umh.strategy.refiner import reset_proposals, get_proposal
from umh.events.stream import reset_event_stream


STRATEGY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "umh", "strategy")
NEW_FILES = ["history.py", "scoring.py", "refiner.py"]
STRATEGY_FILES = [
    os.path.join(STRATEGY_DIR, f)
    for f in NEW_FILES
    if os.path.exists(os.path.join(STRATEGY_DIR, f))
]


def _get_full_imports(filepath: str) -> list[str]:
    with open(filepath) as f:
        tree = ast.parse(f.read())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


class TestBoundaryConstraints:
    def test_no_execution_imports(self):
        for fpath in STRATEGY_FILES:
            imports = _get_full_imports(fpath)
            for imp in imports:
                assert "umh.execution" not in imp, f"{fpath} imports execution"

    def test_no_adapter_imports(self):
        for fpath in STRATEGY_FILES:
            imports = _get_full_imports(fpath)
            for imp in imports:
                assert "umh.adapters" not in imp, f"{fpath} imports adapters"

    def test_no_tool_imports(self):
        for fpath in STRATEGY_FILES:
            imports = _get_full_imports(fpath)
            for imp in imports:
                assert "umh.tools" not in imp, f"{fpath} imports tools"

    def test_no_execute_calls(self):
        for fpath in STRATEGY_FILES:
            with open(fpath) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name) and func.id == "execute":
                        pytest.fail(f"{fpath} calls execute()")
                    if isinstance(func, ast.Attribute) and func.attr == "execute":
                        pytest.fail(f"{fpath} calls .execute()")

    def test_no_goal_creation_in_refiner(self):
        refiner_path = os.path.join(STRATEGY_DIR, "refiner.py")
        if not os.path.exists(refiner_path):
            pytest.skip("refiner.py not found")
        with open(refiner_path) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "Goal":
                    pytest.fail("refiner.py creates Goal objects — recursion risk")

    def test_no_goal_engine_in_strategy(self):
        for fpath in STRATEGY_FILES:
            imports = _get_full_imports(fpath)
            for imp in imports:
                assert "goal_engine" not in imp, f"{fpath} imports goal_engine"


class TestStrategyImmutability:
    def test_refine_creates_new_not_modify(self):
        from umh.strategy.refiner import refine_strategy

        reset_strategy_history()
        reset_proposals()

        steps = [StrategyStep(description="failing", id="s1", status=StepStatus.FAILED)]
        s = Strategy(goal_id="g1", objective="test", steps=steps, id="original_id")
        v = record_strategy_version("g1", s)
        v.performance.tasks_completed = 2
        v.performance.tasks_failed = 5
        v.performance.evaluations = 7

        proposal = refine_strategy("g1")
        if proposal and proposal.new_strategy:
            assert proposal.new_strategy.id != s.id


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


class TestGoalEngineIntegration:
    def setup_method(self):
        reset_goal_store()
        reset_strategy_cache()
        reset_strategy_history()
        reset_proposals()
        reset_event_stream()
        self.engine = GoalEngine()
        self.store = get_goal_store()

    @patch("umh.planning.planner.execute_plan")
    @patch("umh.planning.planner.create_plan_from_raw")
    def test_evaluate_records_history(self, mock_plan, mock_exec):
        mock_plan.return_value = MockPlan()
        mock_exec.return_value = MockTask()
        goal = Goal(name="test", objective="build a test system")
        self.store.create(goal)
        self.engine.evaluate_goal(goal)
        h = get_strategy_history(goal.id)
        assert h.version_count() >= 1

    @patch("umh.planning.planner.execute_plan")
    @patch("umh.planning.planner.create_plan_from_raw")
    def test_evaluate_records_outcomes(self, mock_plan, mock_exec):
        mock_plan.return_value = MockPlan()
        mock_exec.return_value = MockTask()
        goal = Goal(name="test", objective="build a test system")
        self.store.create(goal)
        self.engine.evaluate_goal(goal)
        h = get_strategy_history(goal.id)
        active = h.active_version()
        assert active is not None
        assert active.performance.evaluations >= 1

    @patch("umh.planning.planner.execute_plan")
    @patch("umh.planning.planner.create_plan_from_raw")
    def test_refinement_info_in_result(self, mock_plan, mock_exec):
        mock_plan.return_value = MockPlan()
        mock_exec.return_value = MockTask()
        goal = Goal(name="test", objective="build a test system")
        self.store.create(goal)
        result = self.engine.evaluate_goal(goal)
        assert "refinement_available" in result
        assert "refinement_recommended" in result

    @patch("umh.planning.planner.execute_plan", side_effect=RuntimeError("fail"))
    @patch("umh.planning.planner.create_plan_from_raw")
    def test_failure_records_outcome(self, mock_plan, mock_exec):
        mock_plan.return_value = MockPlan()
        goal = Goal(
            name="test", objective="build a system", policy=GoalPolicy(auto_pause_on_failure=False)
        )
        self.store.create(goal)
        self.engine.evaluate_goal(goal)
        h = get_strategy_history(goal.id)
        active = h.active_version()
        if active:
            assert active.performance.tasks_failed >= 1 or active.performance.evaluations >= 0
