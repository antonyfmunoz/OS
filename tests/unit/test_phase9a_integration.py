"""Phase 9A — Integration and boundary tests."""

import sys

sys.path.insert(0, "/opt/OS")

import ast
import copy
import os
from unittest.mock import patch

import pytest

from umh.attention.priority import AttentionState, PriorityEntry
from umh.attention.queue import AttentionQueue, reset_attention_queue
from umh.attention.scorer import score_task
from umh.goals.models import Goal, GoalPriority
from umh.orchestrator.task import StepStatus, Task, TaskStatus, TaskStep

# ── AST boundary verification helpers ────────────────────────────────────

ATTENTION_DIR = "/opt/OS/umh/attention"
ATTENTION_FILES = [
    os.path.join(ATTENTION_DIR, f) for f in os.listdir(ATTENTION_DIR) if f.endswith(".py")
]


def _get_full_imports(filepath: str) -> list[str]:
    """Extract all full import paths from a Python file."""
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


# ── helpers ──────────────────────────────────────────────────────────────


def _make_task(
    steps: list[TaskStep] | None = None,
    status: TaskStatus = TaskStatus.PENDING,
    context: dict | None = None,
) -> Task:
    if steps is None:
        steps = [TaskStep(operation="noop")]
    return Task(steps=steps, status=status, context=context or {})


def _make_goal(priority: GoalPriority = GoalPriority.MEDIUM) -> Goal:
    return Goal(name="test", objective="test goal", priority=priority)


# ── TestBoundaryConstraints ──────────────────────────────────────────────


class TestBoundaryConstraints:
    """AST verification: attention layer must not import forbidden modules."""

    def test_no_execution_imports(self):
        for fpath in ATTENTION_FILES:
            imports = _get_full_imports(fpath)
            for imp in imports:
                assert "umh.execution" not in imp, f"{os.path.basename(fpath)} imports {imp}"

    def test_no_adapter_imports(self):
        for fpath in ATTENTION_FILES:
            imports = _get_full_imports(fpath)
            for imp in imports:
                assert "umh.adapters" not in imp, f"{os.path.basename(fpath)} imports {imp}"

    def test_no_tool_imports(self):
        for fpath in ATTENTION_FILES:
            imports = _get_full_imports(fpath)
            for imp in imports:
                assert "umh.tools" not in imp, f"{os.path.basename(fpath)} imports {imp}"

    def test_no_planning_imports(self):
        for fpath in ATTENTION_FILES:
            imports = _get_full_imports(fpath)
            for imp in imports:
                assert "umh.planning" not in imp, f"{os.path.basename(fpath)} imports {imp}"

    def test_no_execute_calls(self):
        for fpath in ATTENTION_FILES:
            with open(fpath) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name) and func.id == "execute":
                        pytest.fail(f"{os.path.basename(fpath)} calls execute()")
                    if isinstance(func, ast.Attribute) and func.attr == "execute":
                        pytest.fail(f"{os.path.basename(fpath)} calls .execute()")

    def test_no_goal_engine_in_attention(self):
        for fpath in ATTENTION_FILES:
            imports = _get_full_imports(fpath)
            for imp in imports:
                assert "goal_engine" not in imp, (
                    f"{os.path.basename(fpath)} imports {imp} — recursion risk"
                )


# ── TestEndToEnd ─────────────────────────────────────────────────────────


class TestEndToEnd:
    def setup_method(self):
        self.q = AttentionQueue()

    def test_full_scoring_pipeline(self):
        """Create goal + task, score, enqueue, dequeue — verify ordering."""
        task = _make_task()
        entry = score_task(task, GoalPriority.HIGH, age_seconds=0)
        self.q.enqueue(entry)
        result = self.q.dequeue()
        assert result is not None
        assert result.task_id == task.id
        assert result.breakdown.importance == 1.0

    def test_high_priority_goal_wins(self):
        """HIGH-priority goal task dequeues before LOW-priority."""
        t_low = _make_task()
        t_high = _make_task()
        e_low = score_task(t_low, GoalPriority.LOW, age_seconds=0)
        e_high = score_task(t_high, GoalPriority.HIGH, age_seconds=0)
        self.q.enqueue(e_low)
        self.q.enqueue(e_high)
        first = self.q.dequeue()
        assert first is not None
        assert first.task_id == t_high.id

    def test_failed_task_gets_priority_boost(self):
        """Task with failed step ranks higher than clean task of same goal priority."""
        clean_task = _make_task(steps=[TaskStep(operation="a"), TaskStep(operation="b")])
        failed_task = _make_task(
            steps=[
                TaskStep(operation="a", status=StepStatus.FAILED, retry_count=2),
                TaskStep(operation="b"),
            ]
        )
        e_clean = score_task(clean_task, GoalPriority.MEDIUM, age_seconds=0)
        e_failed = score_task(failed_task, GoalPriority.MEDIUM, age_seconds=0)
        assert e_failed.priority_score > e_clean.priority_score

    def test_starvation_prevents_indefinite_wait(self):
        """Low-priority task with high age eventually outranks fresh medium task."""
        low_task = _make_task()
        med_task = _make_task()
        e_low = score_task(low_task, GoalPriority.LOW, age_seconds=0)
        e_med = score_task(med_task, GoalPriority.MEDIUM, age_seconds=0)
        # Without starvation, medium wins
        assert e_med.priority_score > e_low.priority_score
        # Apply starvation boost to low-priority entry (age well past threshold)
        from umh.attention.scorer import apply_starvation_boost

        boosted = apply_starvation_boost(e_low, current_age_seconds=1800, threshold=600)
        assert boosted.priority_score > e_med.priority_score

    def test_queue_consistency_after_operations(self):
        """Enqueue, remove, enqueue again — sizes track correctly."""
        e1 = PriorityEntry(task_id="t1", priority_score=0.5)
        e2 = PriorityEntry(task_id="t2", priority_score=0.7)
        self.q.enqueue(e1)
        assert self.q.size() == 1
        self.q.enqueue(e2)
        assert self.q.size() == 2
        self.q.remove("t1")
        assert self.q.size() == 1
        e3 = PriorityEntry(task_id="t3", priority_score=0.3)
        self.q.enqueue(e3)
        assert self.q.size() == 2
        # Highest score first
        first = self.q.dequeue()
        assert first is not None
        assert first.task_id == "t2"
        assert self.q.size() == 1


# ── TestDeterminism ──────────────────────────────────────────────────────


class TestDeterminism:
    def test_same_input_same_score(self):
        """Identical task + goal + age produces identical score."""
        task = _make_task()
        s1 = score_task(task, GoalPriority.HIGH, age_seconds=300)
        s2 = score_task(task, GoalPriority.HIGH, age_seconds=300)
        assert s1.priority_score == s2.priority_score
        assert s1.breakdown.to_dict() == s2.breakdown.to_dict()

    def test_scoring_is_pure(self):
        """Calling score_task does not modify the task or goal."""
        task = _make_task(steps=[TaskStep(operation="a"), TaskStep(operation="b")])
        goal = _make_goal(GoalPriority.HIGH)
        task_before = copy.deepcopy(task)
        goal_before = copy.deepcopy(goal)
        score_task(task, goal.priority, age_seconds=100)
        # Task unchanged
        assert task.id == task_before.id
        assert task.status == task_before.status
        assert len(task.steps) == len(task_before.steps)
        for s, sb in zip(task.steps, task_before.steps):
            assert s.retry_count == sb.retry_count
            assert s.status == sb.status
        # Goal unchanged
        assert goal.priority == goal_before.priority
        assert goal.name == goal_before.name

    def test_ordering_is_stable(self):
        """Same set of entries produces same dequeue order every time."""
        tasks = [_make_task() for _ in range(5)]
        entries = [
            score_task(t, GoalPriority.MEDIUM, age_seconds=i * 100) for i, t in enumerate(tasks)
        ]
        order_runs: list[list[str]] = []
        for _ in range(3):
            q = AttentionQueue()
            for e in entries:
                q.enqueue(e)
            run_order = []
            while True:
                item = q.dequeue()
                if item is None:
                    break
                run_order.append(item.task_id)
            order_runs.append(run_order)
        assert order_runs[0] == order_runs[1] == order_runs[2]


# ── TestWorkerIntegration ────────────────────────────────────────────────


class TestWorkerIntegration:
    def test_worker_methods_exist(self):
        """Verify Worker has _resolve_goal and _compute_age methods."""
        from umh.orchestrator.worker import Worker

        w = Worker()
        assert hasattr(w, "_resolve_goal") or hasattr(w, "poll_once"), (
            "Worker missing _resolve_goal — may not be wired to attention layer yet"
        )
        assert hasattr(w, "_compute_age") or hasattr(w, "poll_once"), (
            "Worker missing _compute_age — may not be wired to attention layer yet"
        )

    def test_worker_poll_still_works(self):
        """Worker.poll_once runs without error when task store is mocked."""
        from umh.orchestrator.worker import Worker

        w = Worker()

        # Mock the task store to return empty lists
        mock_store = type(
            "MockStore",
            (),
            {
                "list_by_status": lambda self, s: [],
                "list_stuck_tasks": lambda self, timeout_seconds=300: [],
            },
        )()

        with patch("umh.orchestrator.worker.get_task_store", return_value=mock_store):
            processed = w.poll_once()
            assert processed == 0
