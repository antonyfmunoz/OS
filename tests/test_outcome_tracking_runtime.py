"""Tests for OutcomeTrackingRuntime — Campaign 8.2."""

import sys
import os
import time

# Repo root is DERIVED from the active checkout, never hardcoded. The previous
# module-scope `sys.path.insert(...)` + `os.environ.setdefault("UMH_ROOT", ...)`
# pinned a foreign campaign worktree at IMPORT time and never restored it, so it
# leaked into every module collected afterwards and hard-aborted whole shards.
from tests.repo_root import ensure_repo_on_path

ensure_repo_on_path()

import pytest
from substrate.organism.strategic_gap_engine import (
    Goal,
    GoalRegistry,
    GoalStatus,
    GoalType,
    SuccessCriterion,
)
from substrate.organism.goal_hierarchy_engine import GoalHierarchyEngine
from substrate.organism.outcome_tracking_runtime import (
    OutcomeProgress,
    OutcomeSnapshot,
    OutcomeTrackingRuntime,
)


@pytest.fixture
def tmp_store(tmp_path):
    return str(tmp_path / "goals.json")


@pytest.fixture
def registry(tmp_store):
    return GoalRegistry(store_path=tmp_store)


@pytest.fixture
def hierarchy(registry):
    return GoalHierarchyEngine(goal_registry=registry)


@pytest.fixture
def runtime(registry, hierarchy):
    return OutcomeTrackingRuntime(
        goal_registry=registry,
        goal_hierarchy=hierarchy,
    )


def _goal(
    goal_id: str = "g1",
    title: str = "Test Goal",
    goal_type: GoalType = GoalType.PROJECT,
    status: GoalStatus = GoalStatus.ACTIVE,
    parent: str = "",
    criteria: list[SuccessCriterion] | None = None,
) -> Goal:
    return Goal(
        goal_id=goal_id,
        title=title,
        goal_type=goal_type,
        status=status,
        parent_goal_id=parent,
        success_criteria=criteria or [],
    )


# ── OutcomeProgress dataclass ────────────────────────────────────────


class TestOutcomeProgress:
    def test_defaults(self):
        p = OutcomeProgress()
        assert p.goal_id == ""
        assert p.percent_complete == 0.0
        assert p.health == "unknown"

    def test_to_dict(self):
        p = OutcomeProgress(goal_id="g1", title="T", percent_complete=0.5)
        d = p.to_dict()
        assert d["goal_id"] == "g1"
        assert d["percent_complete"] == 0.5
        assert d["child_progress"] == []

    def test_to_dict_rounds(self):
        p = OutcomeProgress(percent_complete=0.33333333)
        assert p.to_dict()["percent_complete"] == 0.3333


# ── OutcomeSnapshot dataclass ────────────────────────────────────────


class TestOutcomeSnapshot:
    def test_defaults(self):
        s = OutcomeSnapshot()
        assert s.overall_health == "unknown"
        assert s.total_active == 0

    def test_to_dict(self):
        s = OutcomeSnapshot(total_active=5, overall_health="healthy")
        d = s.to_dict()
        assert d["total_active"] == 5
        assert d["overall_health"] == "healthy"


# ── Constructor ──────────────────────────────────────────────────────


class TestConstructor:
    def test_none_deps(self):
        rt = OutcomeTrackingRuntime()
        assert rt.completion("anything") == 0.0

    def test_none_registry_progress(self):
        rt = OutcomeTrackingRuntime()
        p = rt.progress("g1")
        assert p.goal_id == "g1"
        assert p.health == "unknown"

    def test_none_registry_snapshot(self):
        rt = OutcomeTrackingRuntime()
        s = rt.snapshot()
        assert s.goals == []
        assert s.overall_health == "unknown"

    def test_none_registry_goals_at_risk(self):
        rt = OutcomeTrackingRuntime()
        assert rt.goals_at_risk() == []


# ── completion() ─────────────────────────────────────────────────────


class TestCompletion:
    def test_no_criteria_returns_zero(self, registry, runtime):
        registry.add(_goal(goal_id="g1"))
        assert runtime.completion("g1") == 0.0

    def test_all_met_returns_one(self, registry, runtime):
        c1 = SuccessCriterion(description="a", met=True)
        c2 = SuccessCriterion(description="b", met=True)
        registry.add(_goal(goal_id="g1", criteria=[c1, c2]))
        assert runtime.completion("g1") == 1.0

    def test_half_met(self, registry, runtime):
        c1 = SuccessCriterion(description="a", met=True)
        c2 = SuccessCriterion(description="b", met=False)
        registry.add(_goal(goal_id="g1", criteria=[c1, c2]))
        assert runtime.completion("g1") == 0.5

    def test_missing_goal_returns_zero(self, runtime):
        assert runtime.completion("nonexistent") == 0.0


# ── health classification ────────────────────────────────────────────


class TestHealthClassification:
    def test_healthy_at_75(self, registry, runtime):
        criteria = [SuccessCriterion(description=f"c{i}", met=(i < 3)) for i in range(4)]
        registry.add(_goal(goal_id="g1", criteria=criteria))
        assert runtime.health("g1") == "healthy"

    def test_watch_at_50(self, registry, runtime):
        criteria = [SuccessCriterion(description=f"c{i}", met=(i < 2)) for i in range(4)]
        registry.add(_goal(goal_id="g1", criteria=criteria))
        assert runtime.health("g1") == "watch"

    def test_degraded_at_25(self, registry, runtime):
        criteria = [SuccessCriterion(description=f"c{i}", met=(i < 1)) for i in range(4)]
        registry.add(_goal(goal_id="g1", criteria=criteria))
        assert runtime.health("g1") == "degraded"

    def test_critical_at_zero(self, registry, runtime):
        criteria = [SuccessCriterion(description="c", met=False)]
        registry.add(_goal(goal_id="g1", criteria=criteria))
        assert runtime.health("g1") == "critical"

    def test_missing_goal_unknown(self, runtime):
        p = runtime.progress("nonexistent")
        assert p.health == "unknown"

    def test_blockers_override_to_critical(self, registry, runtime):
        criteria = [SuccessCriterion(description="c", met=True)]
        registry.add(_goal(goal_id="g1", criteria=criteria))
        p = OutcomeProgress(percent_complete=1.0, blocker_count=3)
        h = runtime._classify_health(p)
        assert h == "critical"

    def test_one_blocker_is_degraded(self, registry, runtime):
        p = OutcomeProgress(percent_complete=1.0, blocker_count=1)
        h = runtime._classify_health(p)
        assert h == "degraded"


# ── progress() ───────────────────────────────────────────────────────


class TestProgress:
    def test_single_goal(self, registry, runtime):
        c1 = SuccessCriterion(description="a", met=True)
        c2 = SuccessCriterion(description="b", met=False)
        registry.add(_goal(goal_id="g1", title="First Goal", criteria=[c1, c2]))
        p = runtime.progress("g1")
        assert p.goal_id == "g1"
        assert p.title == "First Goal"
        assert p.criteria_met == 1
        assert p.criteria_total == 2
        assert p.percent_complete == 0.5

    def test_missing_goal_returns_empty(self, runtime):
        p = runtime.progress("missing")
        assert p.goal_id == "missing"
        assert p.title == ""
        assert p.health == "unknown"

    def test_goal_type_included(self, registry, runtime):
        registry.add(_goal(goal_id="g1", goal_type=GoalType.VISION))
        p = runtime.progress("g1")
        assert p.goal_type == "vision"

    def test_child_progress_populated(self, registry, runtime):
        registry.add(_goal(goal_id="parent", title="Parent"))
        c1 = SuccessCriterion(description="done", met=True)
        registry.add(_goal(goal_id="child1", title="Child", parent="parent", criteria=[c1]))
        p = runtime.progress("parent")
        assert len(p.child_progress) == 1
        assert p.child_progress[0]["goal_id"] == "child1"
        assert p.child_progress[0]["percent_complete"] == 1.0

    def test_no_children_no_child_progress(self, registry, runtime):
        registry.add(_goal(goal_id="g1"))
        p = runtime.progress("g1")
        assert p.child_progress == []


# ── goals_at_risk() ──────────────────────────────────────────────────


class TestGoalsAtRisk:
    def test_healthy_goals_excluded(self, registry, runtime):
        criteria = [SuccessCriterion(description=f"c{i}", met=True) for i in range(4)]
        registry.add(_goal(goal_id="g1", criteria=criteria))
        assert runtime.goals_at_risk() == []

    def test_critical_goal_included(self, registry, runtime):
        criteria = [SuccessCriterion(description="c", met=False)]
        registry.add(_goal(goal_id="g1", criteria=criteria))
        at_risk = runtime.goals_at_risk()
        assert len(at_risk) == 1
        assert at_risk[0].goal_id == "g1"

    def test_watch_goal_included(self, registry, runtime):
        criteria = [SuccessCriterion(description=f"c{i}", met=(i < 2)) for i in range(4)]
        registry.add(_goal(goal_id="g1", criteria=criteria))
        at_risk = runtime.goals_at_risk()
        assert len(at_risk) == 1

    def test_paused_goals_excluded(self, registry, runtime):
        criteria = [SuccessCriterion(description="c", met=False)]
        registry.add(_goal(goal_id="g1", criteria=criteria, status=GoalStatus.PAUSED))
        assert runtime.goals_at_risk() == []


# ── snapshot() ───────────────────────────────────────────────────────


class TestSnapshot:
    def test_empty_registry(self, runtime):
        s = runtime.snapshot()
        assert s.goals == []
        assert s.total_active == 0
        assert s.total_completed == 0

    def test_active_goals_counted(self, registry, runtime):
        registry.add(_goal(goal_id="g1"))
        registry.add(_goal(goal_id="g2"))
        s = runtime.snapshot()
        assert s.total_active == 2

    def test_completed_goals_counted(self, registry, runtime):
        registry.add(_goal(goal_id="g1", status=GoalStatus.COMPLETED))
        registry.add(_goal(goal_id="g2", status=GoalStatus.ACTIVE))
        s = runtime.snapshot()
        assert s.total_active == 1
        assert s.total_completed == 1

    def test_overall_health_critical_if_any_critical(self, registry, runtime):
        criteria_bad = [SuccessCriterion(description="c", met=False)]
        criteria_good = [SuccessCriterion(description=f"c{i}", met=True) for i in range(4)]
        registry.add(_goal(goal_id="g1", criteria=criteria_bad))
        registry.add(_goal(goal_id="g2", criteria=criteria_good))
        s = runtime.snapshot()
        assert s.overall_health == "critical"

    def test_overall_health_healthy_if_all_healthy(self, registry, runtime):
        criteria = [SuccessCriterion(description=f"c{i}", met=True) for i in range(4)]
        registry.add(_goal(goal_id="g1", criteria=criteria))
        s = runtime.snapshot()
        assert s.overall_health == "healthy"

    def test_snapshot_has_generated_at(self, registry, runtime):
        registry.add(_goal(goal_id="g1"))
        s = runtime.snapshot()
        assert s.generated_at > 0

    def test_to_dict(self, registry, runtime):
        registry.add(_goal(goal_id="g1"))
        s = runtime.snapshot()
        d = s.to_dict()
        assert "goals" in d
        assert "overall_health" in d
        assert "generated_at" in d
