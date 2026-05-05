"""Phase 9A — Priority model and scoring tests."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.attention.priority import AttentionState, PriorityBreakdown, PriorityEntry
from umh.attention.scorer import (
    _score_cost,
    _score_failure_pressure,
    _score_importance,
    _score_recency,
    _score_dependency_value,
    apply_starvation_boost,
    score_task,
)
from umh.goals.models import Goal, GoalPriority
from umh.orchestrator.task import StepStatus, Task, TaskStatus, TaskStep


# ── helpers ──────────────────────────────────────────────────────────────


def _make_task(
    steps: list[TaskStep] | None = None,
    status: TaskStatus = TaskStatus.PENDING,
    context: dict | None = None,
) -> Task:
    if steps is None:
        steps = [TaskStep(operation="noop")]
    t = Task(steps=steps, status=status, context=context or {})
    return t


def _make_goal(priority: GoalPriority = GoalPriority.MEDIUM) -> Goal:
    return Goal(name="test", objective="test goal", priority=priority)


# ── TestPriorityBreakdown ────────────────────────────────────────────────


class TestPriorityBreakdown:
    def test_defaults(self):
        b = PriorityBreakdown()
        assert b.importance == 0.0
        assert b.recency == 0.0
        assert b.failure_pressure == 0.0
        assert b.dependency_value == 0.0
        assert b.cost_penalty == 0.0

    def test_to_dict(self):
        b = PriorityBreakdown(importance=0.12345, recency=0.6789)
        d = b.to_dict()
        assert isinstance(d, dict)
        assert d["importance"] == 0.123
        assert d["recency"] == 0.679
        assert "failure_pressure" in d
        assert "dependency_value" in d
        assert "cost_penalty" in d

    def test_custom_values(self):
        b = PriorityBreakdown(
            importance=1.0,
            recency=0.5,
            failure_pressure=0.3,
            dependency_value=0.75,
            cost_penalty=0.05,
        )
        assert b.importance == 1.0
        assert b.recency == 0.5
        assert b.failure_pressure == 0.3
        assert b.dependency_value == 0.75
        assert b.cost_penalty == 0.05


# ── TestPriorityEntry ────────────────────────────────────────────────────


class TestPriorityEntry:
    def test_defaults(self):
        e = PriorityEntry(task_id="t1")
        assert e.id.startswith("pri_")
        assert e.state == AttentionState.READY
        assert e.priority_score == 0.0
        assert e.starvation_boost == 0.0
        assert e.created_at != ""

    def test_to_dict(self):
        e = PriorityEntry(task_id="t1", goal_id="g1", priority_score=0.75)
        d = e.to_dict()
        assert d["task_id"] == "t1"
        assert d["goal_id"] == "g1"
        assert d["priority_score"] == 0.75
        assert d["state"] == "ready"
        assert "breakdown" in d
        assert "created_at" in d

    def test_unique_ids(self):
        e1 = PriorityEntry(task_id="t1")
        e2 = PriorityEntry(task_id="t2")
        assert e1.id != e2.id

    def test_custom_state(self):
        e = PriorityEntry(task_id="t1", state=AttentionState.BLOCKED)
        assert e.state == AttentionState.BLOCKED


# ── TestScoreImportance ──────────────────────────────────────────────────


class TestScoreImportance:
    def test_high_priority(self):
        assert _score_importance(GoalPriority.HIGH) == 1.0

    def test_medium_priority(self):
        assert _score_importance(GoalPriority.MEDIUM) == 0.6

    def test_low_priority(self):
        assert _score_importance(GoalPriority.LOW) == 0.3


# ── TestScoreRecency ─────────────────────────────────────────────────────


class TestScoreRecency:
    def test_fresh_task(self):
        assert _score_recency(0) == 1.0

    def test_half_hour(self):
        assert _score_recency(1800) == pytest.approx(0.5, abs=0.01)

    def test_old_task(self):
        assert _score_recency(3600) == pytest.approx(0.0, abs=0.01)


# ── TestScoreFailurePressure ─────────────────────────────────────────────


class TestScoreFailurePressure:
    def test_no_failures(self):
        task = _make_task(steps=[TaskStep(operation="a"), TaskStep(operation="b")])
        assert _score_failure_pressure(task) == 0.0

    def test_with_retries(self):
        steps = [
            TaskStep(operation="a", retry_count=2),
            TaskStep(operation="b", retry_count=1),
        ]
        task = _make_task(steps=steps)
        score = _score_failure_pressure(task)
        assert score > 0.0
        # 2*0.1 + 1*0.1 = 0.3
        assert score == pytest.approx(0.3, abs=0.01)

    def test_with_failed_step(self):
        steps = [
            TaskStep(operation="a", status=StepStatus.FAILED),
            TaskStep(operation="b"),
        ]
        task = _make_task(steps=steps)
        score = _score_failure_pressure(task)
        assert score >= 0.3


# ── TestScoreCost ────────────────────────────────────────────────────────


class TestScoreCost:
    def test_few_steps(self):
        task = _make_task(steps=[TaskStep(operation="a"), TaskStep(operation="b")])
        penalty = _score_cost(task)
        # 2/10 * 0.1 = 0.02
        assert penalty == pytest.approx(0.02, abs=0.001)

    def test_many_steps(self):
        steps = [TaskStep(operation=f"op{i}") for i in range(10)]
        task = _make_task(steps=steps)
        penalty = _score_cost(task)
        # 10/10 * 0.1 = 0.1  (capped at 1.0 ratio, then * 0.1)
        assert penalty == pytest.approx(0.1, abs=0.001)


# ── TestScoreTask ────────────────────────────────────────────────────────


class TestScoreTask:
    def test_score_with_goal(self):
        task = _make_task()
        entry = score_task(task, GoalPriority.HIGH, age_seconds=0)
        assert entry.priority_score >= 0.49
        assert entry.task_id == task.id
        assert entry.breakdown.importance == 1.0

    def test_score_without_goal(self):
        task = _make_task()
        entry = score_task(task, GoalPriority.LOW, age_seconds=0)
        assert entry.breakdown.importance == 0.3

    def test_score_deterministic(self):
        task = _make_task()
        e1 = score_task(task, GoalPriority.HIGH, age_seconds=100)
        e2 = score_task(task, GoalPriority.HIGH, age_seconds=100)
        assert e1.priority_score == e2.priority_score

    def test_score_components_sum(self):
        task = _make_task()
        entry = score_task(task, GoalPriority.MEDIUM, age_seconds=600)
        b = entry.breakdown
        expected = (
            b.importance * 0.30
            + b.recency * 0.20
            + b.failure_pressure * 0.20
            + b.dependency_value * 0.20
            - b.cost_penalty * 0.10
        )
        assert entry.priority_score == pytest.approx(expected, abs=0.001)


# ── TestStarvationBoost ──────────────────────────────────────────────────


class TestStarvationBoost:
    def test_no_boost_under_threshold(self):
        entry = PriorityEntry(task_id="t1", priority_score=0.5, state=AttentionState.READY)
        result = apply_starvation_boost(entry, current_age_seconds=300, threshold=600)
        assert result.starvation_boost == 0.0
        assert result.state == AttentionState.READY

    def test_boost_over_threshold(self):
        entry = PriorityEntry(task_id="t1", priority_score=0.5, state=AttentionState.READY)
        result = apply_starvation_boost(entry, current_age_seconds=900, threshold=600)
        assert result.starvation_boost > 0.0
        assert result.priority_score > 0.5

    def test_boost_capped(self):
        entry = PriorityEntry(task_id="t1", priority_score=0.5, state=AttentionState.READY)
        result = apply_starvation_boost(entry, current_age_seconds=99999, threshold=600)
        assert result.starvation_boost <= 0.3

    def test_starved_state(self):
        entry = PriorityEntry(task_id="t1", priority_score=0.5, state=AttentionState.READY)
        result = apply_starvation_boost(entry, current_age_seconds=900, threshold=600)
        assert result.state == AttentionState.STARVED
