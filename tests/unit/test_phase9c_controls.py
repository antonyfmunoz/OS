"""Phase 9C — System controls and scoring integration tests."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.attention.controls import (
    ControlInfluence,
    ExecutionMode,
    RetryPolicy,
    SystemControls,
    compute_control_influence,
    compute_weight_modifiers,
    get_max_retries,
    get_refinement_bias,
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


def _make_task(
    steps: list[TaskStep] | None = None,
    status: TaskStatus = TaskStatus.PENDING,
    context: dict | None = None,
) -> Task:
    if steps is None:
        steps = [TaskStep(operation="test_op")]
    return Task(
        steps=steps,
        id="task_test",
        status=status,
        context=context or {"goal_id": "goal_test"},
    )


# ── TestSystemControls ──────────────────────────────────────────────────


class TestSystemControls:
    def test_defaults(self):
        sc = SystemControls()
        assert sc.execution_mode == ExecutionMode.BALANCED
        assert sc.max_concurrent_tasks == 5
        assert sc.retry_policy == RetryPolicy.NORMAL
        assert sc.cost_sensitivity == 0.5
        assert sc.failure_tolerance == 0.5
        assert sc.exploration_factor == 0.3

    def test_to_dict(self):
        sc = SystemControls()
        d = sc.to_dict()
        assert isinstance(d, dict)
        assert d["execution_mode"] == "balanced"
        assert d["max_concurrent_tasks"] == 5
        assert d["retry_policy"] == "normal"
        assert d["cost_sensitivity"] == 0.5
        assert d["failure_tolerance"] == 0.5
        assert d["exploration_factor"] == 0.3
        assert "updated_at" in d

    def test_custom_values(self):
        sc = SystemControls(
            execution_mode=ExecutionMode.AGGRESSIVE,
            max_concurrent_tasks=10,
            retry_policy=RetryPolicy.LENIENT,
            cost_sensitivity=0.9,
            failure_tolerance=0.1,
            exploration_factor=0.5,
        )
        assert sc.execution_mode == ExecutionMode.AGGRESSIVE
        assert sc.max_concurrent_tasks == 10
        assert sc.retry_policy == RetryPolicy.LENIENT
        assert sc.cost_sensitivity == 0.9
        assert sc.failure_tolerance == 0.1
        assert sc.exploration_factor == 0.5

    def test_updated_at_auto(self):
        sc = SystemControls()
        assert sc.updated_at != ""
        assert len(sc.updated_at) > 10  # ISO timestamp

    def test_enum_values(self):
        assert ExecutionMode.BALANCED.value == "balanced"
        assert ExecutionMode.AGGRESSIVE.value == "aggressive"
        assert ExecutionMode.CONSERVATIVE.value == "conservative"
        assert RetryPolicy.STRICT.value == "strict"
        assert RetryPolicy.NORMAL.value == "normal"
        assert RetryPolicy.LENIENT.value == "lenient"

    def test_clamping_via_update(self):
        """update_system_control clamps float fields to [0.0, 1.0]."""
        update_system_control("cost_sensitivity", 1.5)
        sc = get_system_controls()
        assert sc.cost_sensitivity == 1.0

        update_system_control("failure_tolerance", -0.5)
        sc = get_system_controls()
        assert sc.failure_tolerance == 0.0

        update_system_control("exploration_factor", 2.0)
        sc = get_system_controls()
        assert sc.exploration_factor == 1.0


# ── TestControlInfluence ────────────────────────────────────────────────


class TestControlInfluence:
    def test_to_dict(self):
        ci = ControlInfluence(
            mode="aggressive",
            priority_adjustment=0.15,
            retry_policy="lenient",
            cost_modifier=0.7,
            failure_modifier=1.2,
        )
        d = ci.to_dict()
        assert d["mode"] == "aggressive"
        assert d["priority_adjustment"] == 0.15
        assert d["retry_policy"] == "lenient"
        assert d["cost_modifier"] == 0.7
        assert d["failure_modifier"] == 1.2

    def test_defaults(self):
        ci = ControlInfluence()
        assert ci.mode == "balanced"
        assert ci.priority_adjustment == 0.0
        assert ci.retry_policy == "normal"
        assert ci.cost_modifier == 0.0
        assert ci.failure_modifier == 0.0


# ── TestWeightModifiers ─────────────────────────────────────────────────


class TestWeightModifiers:
    def test_balanced_no_change(self):
        """BALANCED mode: all modifiers are 1.0."""
        sc = SystemControls()
        mods = compute_weight_modifiers(sc)
        assert mods["importance_mod"] == 1.0
        assert mods["recency_mod"] == 1.0
        assert mods["failure_mod"] == 1.0
        assert mods["dependency_mod"] == 1.0
        assert mods["cost_mod"] == 1.0

    def test_aggressive_boosts(self):
        """AGGRESSIVE mode boosts importance, reduces cost penalty."""
        sc = SystemControls(execution_mode=ExecutionMode.AGGRESSIVE)
        mods = compute_weight_modifiers(sc)
        assert mods["importance_mod"] > 1.0
        assert mods["cost_mod"] < 1.0

    def test_conservative_penalizes(self):
        """CONSERVATIVE mode boosts failure pressure and cost penalty."""
        sc = SystemControls(execution_mode=ExecutionMode.CONSERVATIVE)
        mods = compute_weight_modifiers(sc)
        assert mods["failure_mod"] > 1.0
        assert mods["cost_mod"] > 1.0


# ── TestMaxRetries ──────────────────────────────────────────────────────


class TestMaxRetries:
    def test_strict(self):
        sc = SystemControls(retry_policy=RetryPolicy.STRICT)
        assert get_max_retries(sc) == 1

    def test_normal(self):
        sc = SystemControls(retry_policy=RetryPolicy.NORMAL)
        assert get_max_retries(sc) == 3

    def test_lenient(self):
        sc = SystemControls(retry_policy=RetryPolicy.LENIENT)
        assert get_max_retries(sc) == 5


# ── TestRefinementBias ──────────────────────────────────────────────────


class TestRefinementBias:
    def test_balanced(self):
        sc = SystemControls(execution_mode=ExecutionMode.BALANCED)
        assert get_refinement_bias(sc) == "neutral"

    def test_aggressive(self):
        sc = SystemControls(execution_mode=ExecutionMode.AGGRESSIVE)
        assert get_refinement_bias(sc) == "complex"

    def test_conservative(self):
        sc = SystemControls(execution_mode=ExecutionMode.CONSERVATIVE)
        assert get_refinement_bias(sc) == "simple"


# ── TestSingleton ───────────────────────────────────────────────────────


class TestSingleton:
    def test_get_returns_defaults(self):
        sc = get_system_controls()
        assert sc.execution_mode == ExecutionMode.BALANCED
        assert sc.max_concurrent_tasks == 5

    def test_set_replaces(self):
        new = SystemControls(
            execution_mode=ExecutionMode.CONSERVATIVE,
            max_concurrent_tasks=2,
        )
        set_system_controls(new)
        current = get_system_controls()
        assert current.execution_mode == ExecutionMode.CONSERVATIVE
        assert current.max_concurrent_tasks == 2

    def test_update_single_key(self):
        update_system_control("execution_mode", "aggressive")
        sc = get_system_controls()
        assert sc.execution_mode == ExecutionMode.AGGRESSIVE
        # Other fields unchanged
        assert sc.max_concurrent_tasks == 5
        assert sc.retry_policy == RetryPolicy.NORMAL

    def test_update_unknown_key(self):
        with pytest.raises(ValueError):
            update_system_control("nonexistent_key", "value")


# ── TestScoreWithControls ──────────────────────────────────────────────


class TestScoreWithControls:
    def test_balanced_matches_base(self):
        """With default BALANCED controls, controlled score ~= base score."""
        task = _make_task()
        base_entry = score_task(task, GoalPriority.HIGH, age_seconds=0)
        adjusted_entry, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)
        assert adjusted_entry.priority_score == pytest.approx(base_entry.priority_score, abs=0.05)

    def test_aggressive_boosts_score(self):
        """AGGRESSIVE mode produces higher score than BALANCED."""
        task = _make_task()

        reset_system_controls()
        balanced_entry, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)

        set_system_controls(SystemControls(execution_mode=ExecutionMode.AGGRESSIVE))
        aggressive_entry, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)
        assert aggressive_entry.priority_score > balanced_entry.priority_score

    def test_conservative_lowers_score(self):
        """CONSERVATIVE mode produces lower score than BALANCED."""
        task = _make_task()

        reset_system_controls()
        balanced_entry, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)

        set_system_controls(SystemControls(execution_mode=ExecutionMode.CONSERVATIVE))
        conservative_entry, _ = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)
        assert conservative_entry.priority_score < balanced_entry.priority_score

    def test_returns_control_influence(self):
        """Non-BALANCED mode returns ControlInfluence with non-zero adjustment."""
        task = _make_task()
        set_system_controls(SystemControls(execution_mode=ExecutionMode.AGGRESSIVE))
        _, influence = score_task_with_controls(task, GoalPriority.HIGH, age_seconds=0)
        assert isinstance(influence, ControlInfluence)
        assert influence.mode == "aggressive"
        assert influence.priority_adjustment != 0.0
