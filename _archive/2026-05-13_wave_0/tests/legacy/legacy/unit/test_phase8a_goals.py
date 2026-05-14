"""Tests for Phase 8A: Persistent Goal System — core models and store.

Verifies:
- Goal, GoalPolicy, GoalPriority, GoalStatus data structures
- GoalStore CRUD operations
- Thread safety of store operations
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import os

os.environ.setdefault("UMH_API_KEY", "test-key-phase8a")

import threading

import pytest

from umh.goals.models import Goal, GoalPolicy, GoalPriority, GoalStatus
from umh.goals.store import get_goal_store, reset_goal_store
from umh.events.stream import reset_event_stream


@pytest.fixture(autouse=True)
def clean_state():
    reset_goal_store()
    reset_event_stream()
    yield
    reset_goal_store()


# ── A. Goal Model Tests ───────────────────────────────────────────────


class TestGoalModel:
    def test_create_goal(self):
        """Goal auto-generates id with 'goal_' prefix and sets created_at."""
        goal = Goal(name="test", objective="do stuff")
        assert goal.id.startswith("goal_")
        assert goal.created_at != ""
        assert goal.status == GoalStatus.ACTIVE

    def test_goal_default_status(self):
        """New goals default to ACTIVE status."""
        goal = Goal(name="test", objective="do stuff")
        assert goal.status == GoalStatus.ACTIVE

    def test_goal_to_dict(self):
        """to_dict round-trips all fields correctly."""
        goal = Goal(
            name="revenue",
            objective="hit $10k/month",
            priority=GoalPriority.HIGH,
            success_criteria=["close sale"],
            constraints={"budget": 500},
            metadata={"source": "test"},
            created_by="afm",
        )
        d = goal.to_dict()
        assert d["name"] == "revenue"
        assert d["objective"] == "hit $10k/month"
        assert d["status"] == "active"
        assert d["priority"] == "high"
        assert d["success_criteria"] == ["close sale"]
        assert d["constraints"] == {"budget": 500}
        assert d["metadata"] == {"source": "test"}
        assert d["created_by"] == "afm"
        assert d["id"].startswith("goal_")
        assert d["created_at"] != ""
        assert d["updated_at"] != ""
        assert d["progress"] == 0.0
        assert d["tasks_created"] == 0
        assert d["tasks_completed"] == 0
        assert "policy" in d

    def test_goal_status_values(self):
        """All 4 GoalStatus enum values exist."""
        assert GoalStatus.ACTIVE.value == "active"
        assert GoalStatus.PAUSED.value == "paused"
        assert GoalStatus.COMPLETED.value == "completed"
        assert GoalStatus.FAILED.value == "failed"
        assert len(GoalStatus) == 4

    def test_goal_priority_values(self):
        """All 3 GoalPriority enum values exist."""
        assert GoalPriority.LOW.value == "low"
        assert GoalPriority.MEDIUM.value == "medium"
        assert GoalPriority.HIGH.value == "high"
        assert len(GoalPriority) == 3

    def test_goal_custom_priority(self):
        """Goal accepts custom priority."""
        goal = Goal(name="urgent", objective="ship now", priority=GoalPriority.HIGH)
        assert goal.priority == GoalPriority.HIGH

    def test_goal_with_success_criteria(self):
        """Goal stores success_criteria list."""
        criteria = ["revenue > 10k", "churn < 5%"]
        goal = Goal(name="growth", objective="grow", success_criteria=criteria)
        assert goal.success_criteria == criteria

    def test_goal_with_constraints(self):
        """Goal stores constraints dict."""
        constraints = {"max_cost": 1000, "no_cold_email": True}
        goal = Goal(name="outreach", objective="reach out", constraints=constraints)
        assert goal.constraints == constraints

    def test_goal_with_metadata(self):
        """Goal stores arbitrary metadata."""
        meta = {"campaign": "q2-2026", "channel": "linkedin"}
        goal = Goal(name="campaign", objective="launch", metadata=meta)
        assert goal.metadata == meta

    def test_goal_created_by_field(self):
        """Goal tracks who created it."""
        goal = Goal(name="test", objective="test", created_by="api:user123")
        assert goal.created_by == "api:user123"


# ── B. GoalPolicy Tests ──────────────────────────────────────────────


class TestGoalPolicy:
    def test_policy_defaults(self):
        """GoalPolicy has correct default values."""
        policy = GoalPolicy()
        assert policy.max_tasks_per_cycle == 3
        assert policy.require_approval is True
        assert policy.allow_side_effects is False
        assert policy.evaluation_interval_sec == 300
        assert policy.max_active_tasks == 5
        assert policy.auto_pause_on_failure is True
        assert policy.cost_limit_usd == 0.0

    def test_policy_to_dict(self):
        """GoalPolicy serializes to dict correctly."""
        policy = GoalPolicy(max_tasks_per_cycle=5, require_approval=False)
        d = policy.to_dict()
        assert d["max_tasks_per_cycle"] == 5
        assert d["require_approval"] is False
        assert d["allow_side_effects"] is False
        assert d["evaluation_interval_sec"] == 300
        assert d["max_active_tasks"] == 5
        assert d["auto_pause_on_failure"] is True
        assert d["cost_limit_usd"] == 0.0


# ── C. GoalStore Tests ────────────────────────────────────────────────


class TestGoalStore:
    def test_store_create_and_get(self):
        """Store creates and retrieves a goal by ID."""
        store = get_goal_store()
        goal = Goal(name="test", objective="test goal")
        stored = store.create(goal)
        assert stored.id == goal.id

        retrieved = store.get(goal.id)
        assert retrieved is not None
        assert retrieved.name == "test"

    def test_store_list_all(self):
        """Store lists all goals regardless of status."""
        store = get_goal_store()
        g1 = Goal(name="a", objective="a")
        g2 = Goal(name="b", objective="b")
        store.create(g1)
        store.create(g2)
        store.pause(g2.id)

        all_goals = store.list_all()
        assert len(all_goals) == 2

    def test_store_list_active(self):
        """Store lists only ACTIVE goals."""
        store = get_goal_store()
        g1 = Goal(name="active", objective="a")
        g2 = Goal(name="paused", objective="b")
        store.create(g1)
        store.create(g2)
        store.pause(g2.id)

        active = store.list_active()
        assert len(active) == 1
        assert active[0].name == "active"

    def test_store_pause(self):
        """Store pauses a goal — sets PAUSED status."""
        store = get_goal_store()
        goal = Goal(name="test", objective="test")
        store.create(goal)
        result = store.pause(goal.id)
        assert result is not None
        assert result.status == GoalStatus.PAUSED

    def test_store_resume(self):
        """Store resumes a paused goal — sets ACTIVE status."""
        store = get_goal_store()
        goal = Goal(name="test", objective="test")
        store.create(goal)
        store.pause(goal.id)
        result = store.resume(goal.id)
        assert result is not None
        assert result.status == GoalStatus.ACTIVE

    def test_store_delete(self):
        """Store deletes a goal and returns True."""
        store = get_goal_store()
        goal = Goal(name="test", objective="test")
        store.create(goal)
        assert store.delete(goal.id) is True
        assert store.get(goal.id) is None

    def test_store_delete_nonexistent(self):
        """Deleting a non-existent goal returns False."""
        store = get_goal_store()
        assert store.delete("goal_does_not_exist") is False

    def test_store_complete(self):
        """Store completes a goal — sets COMPLETED, progress=1.0."""
        store = get_goal_store()
        goal = Goal(name="test", objective="test")
        store.create(goal)
        result = store.complete(goal.id)
        assert result is not None
        assert result.status == GoalStatus.COMPLETED
        assert result.progress == 1.0

    def test_store_fail(self):
        """Store fails a goal — sets FAILED status."""
        store = get_goal_store()
        goal = Goal(name="test", objective="test")
        store.create(goal)
        result = store.fail(goal.id)
        assert result is not None
        assert result.status == GoalStatus.FAILED

    def test_store_update_progress(self):
        """Store updates progress tracking counters."""
        store = get_goal_store()
        goal = Goal(name="test", objective="test")
        store.create(goal)
        store.update_progress(goal.id, progress=0.5, tasks_created=3, tasks_completed=1)
        updated = store.get(goal.id)
        assert updated is not None
        assert updated.progress == 0.5
        assert updated.tasks_created == 3
        assert updated.tasks_completed == 1

    def test_store_update_evaluation(self):
        """Store records evaluation timestamp."""
        store = get_goal_store()
        goal = Goal(name="test", objective="test")
        store.create(goal)
        assert goal.last_evaluated_at == ""

        store.update_evaluation(goal.id)
        updated = store.get(goal.id)
        assert updated is not None
        assert updated.last_evaluated_at != ""

    def test_store_get_nonexistent(self):
        """Getting a non-existent goal returns None."""
        store = get_goal_store()
        assert store.get("goal_nonexistent_xyz") is None

    def test_store_thread_safety(self):
        """Store handles concurrent creates from multiple threads."""
        store = get_goal_store()
        created_ids: list[str] = []
        errors: list[str] = []
        lock = threading.Lock()

        def create_goal(i: int):
            try:
                goal = Goal(name=f"thread-{i}", objective=f"objective-{i}")
                store.create(goal)
                with lock:
                    created_ids.append(goal.id)
            except Exception as exc:
                with lock:
                    errors.append(str(exc))

        threads = [threading.Thread(target=create_goal, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(created_ids) == 20
        assert len(store.list_all()) == 20
        # All IDs should be unique
        assert len(set(created_ids)) == 20
