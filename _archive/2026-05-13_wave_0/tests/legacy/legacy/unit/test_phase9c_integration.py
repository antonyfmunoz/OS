"""Phase 9C — Integration and boundary tests."""

import ast
import os
import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.attention.controls import (
    ExecutionMode,
    RetryPolicy,
    SystemControls,
    compute_weight_modifiers,
    get_system_controls,
    reset_system_controls,
    set_system_controls,
    update_system_control,
)
from umh.attention.priority import PriorityEntry
from umh.attention.scorer import score_task, score_task_with_controls
from umh.goals.models import GoalPriority
from umh.orchestrator.task import StepStatus, Task, TaskStatus, TaskStep


@pytest.fixture(autouse=True)
def _reset():
    reset_system_controls()
    yield
    reset_system_controls()


# ── helpers ──────────────────────────────────────────────────────────────

ATTENTION_DIR = "/opt/OS/umh/attention"
ATTENTION_FILES = [
    os.path.join(ATTENTION_DIR, f) for f in os.listdir(ATTENTION_DIR) if f.endswith(".py")
]


def _get_imports(filepath: str) -> list[str]:
    with open(filepath) as f:
        tree = ast.parse(f.read())
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _make_task(
    steps: list[TaskStep] | None = None,
    status: TaskStatus = TaskStatus.PENDING,
    context: dict | None = None,
) -> Task:
    if steps is None:
        steps = [TaskStep(operation="test_op")]
    return Task(
        steps=steps,
        id="task_integ",
        status=status,
        context=context or {"goal_id": "goal_integ"},
    )


# ── TestBoundaryConstraints ─────────────────────────────────────────────


class TestBoundaryConstraints:
    """AST-verified import boundary checks for umh/attention/*.py."""

    def test_no_execution_imports(self):
        for fp in ATTENTION_FILES:
            for imp in _get_imports(fp):
                assert not imp.startswith("umh.execution"), f"{fp} imports {imp}"

    def test_no_adapter_imports(self):
        for fp in ATTENTION_FILES:
            for imp in _get_imports(fp):
                assert not imp.startswith("umh.adapters"), f"{fp} imports {imp}"

    def test_no_tool_imports(self):
        for fp in ATTENTION_FILES:
            for imp in _get_imports(fp):
                assert not imp.startswith("umh.tools"), f"{fp} imports {imp}"

    def test_no_planning_imports(self):
        for fp in ATTENTION_FILES:
            for imp in _get_imports(fp):
                assert not imp.startswith("umh.planning"), f"{fp} imports {imp}"

    def test_no_execute_calls(self):
        for fp in ATTENTION_FILES:
            with open(fp) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name) and func.id == "execute":
                        pytest.fail(f"{fp} calls execute()")

    def test_no_goal_engine_in_attention(self):
        for fp in ATTENTION_FILES:
            for imp in _get_imports(fp):
                assert imp != "umh.goals.goal_engine", f"{fp} imports umh.goals.goal_engine"


# ── TestDeterminism ─────────────────────────────────────────────────────


class TestDeterminism:
    def test_same_controls_same_score(self):
        task = _make_task()
        e1, i1 = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=100)
        e2, i2 = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=100)
        assert e1.priority_score == e2.priority_score
        assert i1.priority_adjustment == i2.priority_adjustment

    def test_controls_do_not_mutate_task(self):
        task = _make_task()
        original_status = task.status
        original_steps = len(task.steps)
        original_context = dict(task.context)
        score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)
        assert task.status == original_status
        assert len(task.steps) == original_steps
        assert task.context == original_context

    def test_weight_modifiers_are_pure(self):
        sc = SystemControls(execution_mode=ExecutionMode.AGGRESSIVE)
        m1 = compute_weight_modifiers(sc)
        m2 = compute_weight_modifiers(sc)
        assert m1 == m2


# ── TestModeTransitions ─────────────────────────────────────────────────


class TestModeTransitions:
    def test_aggressive_higher_than_balanced(self):
        task = _make_task()

        reset_system_controls()
        balanced, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)

        set_system_controls(SystemControls(execution_mode=ExecutionMode.AGGRESSIVE))
        aggressive, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)
        assert aggressive.priority_score > balanced.priority_score

    def test_conservative_lower_than_balanced(self):
        task = _make_task()

        reset_system_controls()
        balanced, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)

        set_system_controls(SystemControls(execution_mode=ExecutionMode.CONSERVATIVE))
        conservative, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)
        assert conservative.priority_score < balanced.priority_score

    def test_mode_switch_immediate(self):
        """Changing mode is reflected in the very next scoring call."""
        task = _make_task()

        set_system_controls(SystemControls(execution_mode=ExecutionMode.AGGRESSIVE))
        agg_entry, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)

        update_system_control("execution_mode", "conservative")
        con_entry, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)
        assert con_entry.priority_score < agg_entry.priority_score


# ── TestCostSensitivityEffect ──────────────────────────────────────────


class TestCostSensitivityEffect:
    def test_high_cost_sensitivity_lowers_score(self):
        """Higher cost_sensitivity increases cost penalty, lowering score."""
        task = _make_task()

        set_system_controls(SystemControls(cost_sensitivity=0.0))
        low_cost, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)

        set_system_controls(SystemControls(cost_sensitivity=1.0))
        high_cost, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)
        assert high_cost.priority_score < low_cost.priority_score

    def test_zero_cost_sensitivity_minimal_penalty(self):
        """cost_sensitivity=0.0 means cost adjustment term is zero."""
        task = _make_task()
        set_system_controls(SystemControls(cost_sensitivity=0.0))
        entry, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)
        # Base score with BALANCED mode (no modifiers) should match closely
        base = score_task(task, GoalPriority.HIGH, age_seconds=0)
        assert entry.priority_score == pytest.approx(base.priority_score, abs=0.01)


# ── TestFailureToleranceEffect ─────────────────────────────────────────


class TestFailureToleranceEffect:
    def test_high_tolerance_dampens_failure(self):
        """High failure_tolerance dampens failure pressure on tasks with
        failed steps — score changes vs low tolerance."""
        failed_steps = [
            TaskStep(operation="a", status=StepStatus.FAILED, retry_count=2),
            TaskStep(operation="b"),
        ]
        task = _make_task(steps=failed_steps)

        set_system_controls(SystemControls(failure_tolerance=0.0))
        low_tol, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)

        set_system_controls(SystemControls(failure_tolerance=1.0))
        high_tol, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)
        # High tolerance dampens failure pressure (subtracts from score)
        # so high_tol score < low_tol score (failure boost is reduced)
        assert high_tol.priority_score < low_tol.priority_score

    def test_low_tolerance_no_dampening(self):
        """failure_tolerance <= 0.5 means no failure dampening is applied.
        Scores at 0.0 and 0.5 should be equal for the same task."""
        failed_steps = [
            TaskStep(operation="a", status=StepStatus.FAILED, retry_count=1),
            TaskStep(operation="b"),
        ]
        task = _make_task(steps=failed_steps)

        set_system_controls(SystemControls(failure_tolerance=0.0))
        score_0, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)

        set_system_controls(SystemControls(failure_tolerance=0.5))
        score_half, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)
        assert score_0.priority_score == pytest.approx(score_half.priority_score, abs=0.001)
