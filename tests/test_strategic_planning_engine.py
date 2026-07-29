"""Tests for StrategicPlanningEngine — Campaign 8.3."""

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
from substrate.organism.outcome_tracking_runtime import OutcomeTrackingRuntime
from substrate.organism.strategic_planning_engine import (
    PlanningStatus,
    StrategicMilestone,
    StrategicPlan,
    StrategicPlanningEngine,
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
def outcomes(registry, hierarchy):
    return OutcomeTrackingRuntime(
        goal_registry=registry,
        goal_hierarchy=hierarchy,
    )


@pytest.fixture
def engine(registry, hierarchy, outcomes):
    return StrategicPlanningEngine(
        goal_registry=registry,
        goal_hierarchy=hierarchy,
        outcome_tracking=outcomes,
    )


def _goal(
    goal_id: str = "g1",
    title: str = "Test Goal",
    goal_type: GoalType = GoalType.PROJECT,
    status: GoalStatus = GoalStatus.ACTIVE,
    parent: str = "",
    criteria: list[SuccessCriterion] | None = None,
    deps: list[str] | None = None,
    target_date: str = "",
) -> Goal:
    return Goal(
        goal_id=goal_id,
        title=title,
        goal_type=goal_type,
        status=status,
        parent_goal_id=parent,
        success_criteria=criteria or [],
        dependencies=deps or [],
        target_date=target_date,
    )


# ── PlanningStatus enum ─────────────────────────────────────────────


class TestPlanningStatus:
    def test_values(self):
        assert PlanningStatus.ON_TRACK.value == "on_track"
        assert PlanningStatus.AT_RISK.value == "at_risk"
        assert PlanningStatus.BLOCKED.value == "blocked"
        assert PlanningStatus.NOT_STARTED.value == "not_started"

    def test_is_str_enum(self):
        assert isinstance(PlanningStatus.ON_TRACK, str)

    def test_from_value(self):
        assert PlanningStatus("blocked") == PlanningStatus.BLOCKED


# ── StrategicMilestone dataclass ─────────────────────────────────────


class TestStrategicMilestone:
    def test_defaults(self):
        m = StrategicMilestone()
        assert m.milestone_id.startswith("ms-")
        assert m.status == PlanningStatus.NOT_STARTED.value
        assert m.dependencies == []

    def test_to_dict(self):
        m = StrategicMilestone(
            milestone_id="ms-test",
            title="M1",
            goal_id="g1",
            percent_complete=0.5,
        )
        d = m.to_dict()
        assert d["milestone_id"] == "ms-test"
        assert d["title"] == "M1"
        assert d["percent_complete"] == 0.5

    def test_to_dict_rounds(self):
        m = StrategicMilestone(percent_complete=0.33333333)
        assert m.to_dict()["percent_complete"] == 0.3333


# ── StrategicPlan dataclass ──────────────────────────────────────────


class TestStrategicPlan:
    def test_defaults(self):
        p = StrategicPlan()
        assert p.plan_id.startswith("plan-")
        assert p.status == PlanningStatus.NOT_STARTED.value
        assert p.blockers == []
        assert p.milestones == []
        assert p.child_plans == []

    def test_to_dict(self):
        p = StrategicPlan(
            plan_id="plan-test",
            goal_id="g1",
            goal_title="T",
            status="on_track",
            blockers=["b1"],
        )
        d = p.to_dict()
        assert d["plan_id"] == "plan-test"
        assert d["goal_title"] == "T"
        assert d["blockers"] == ["b1"]

    def test_generated_at_set(self):
        before = time.time()
        p = StrategicPlan()
        assert p.generated_at >= before


# ── Constructor ──────────────────────────────────────────────────────


class TestConstructor:
    def test_none_deps(self):
        eng = StrategicPlanningEngine()
        plan = eng.generate_plan("any")
        assert plan.goal_id == "any"
        assert plan.goal_title == ""

    def test_none_registry_roadmap(self):
        eng = StrategicPlanningEngine()
        rm = eng.roadmap()
        assert rm["plans"] == []

    def test_none_registry_milestones(self):
        eng = StrategicPlanningEngine()
        assert eng.milestones("g1") == []


# ── _classify_status() ───────────────────────────────────────────────


class TestClassifyStatus:
    def test_blocked_when_blockers(self, engine):
        assert engine._classify_status(0.8, 2, True) == PlanningStatus.BLOCKED

    def test_not_started_no_work_zero_progress(self, engine):
        assert engine._classify_status(0.0, 0, False) == PlanningStatus.NOT_STARTED

    def test_at_risk_below_half(self, engine):
        assert engine._classify_status(0.3, 0, True) == PlanningStatus.AT_RISK

    def test_on_track_at_half(self, engine):
        assert engine._classify_status(0.5, 0, True) == PlanningStatus.ON_TRACK

    def test_on_track_above_half(self, engine):
        assert engine._classify_status(0.9, 0, True) == PlanningStatus.ON_TRACK

    def test_at_risk_at_zero_with_work(self, engine):
        assert engine._classify_status(0.0, 0, True) == PlanningStatus.AT_RISK


# ── generate_plan() ──────────────────────────────────────────────────


class TestGeneratePlan:
    def test_basic_plan(self, registry, engine):
        registry.add(_goal(goal_id="g1", title="Build Widget"))
        plan = engine.generate_plan("g1")
        assert plan.goal_id == "g1"
        assert plan.goal_title == "Build Widget"
        assert plan.goal_type == "project"

    def test_missing_goal(self, engine):
        plan = engine.generate_plan("nonexistent")
        assert plan.goal_id == "nonexistent"
        assert plan.goal_title == ""

    def test_plan_with_criteria(self, registry, engine):
        c1 = SuccessCriterion(description="a", met=True)
        c2 = SuccessCriterion(description="b", met=False)
        registry.add(_goal(goal_id="g1", criteria=[c1, c2]))
        plan = engine.generate_plan("g1")
        assert plan.current_state.get("percent_complete") == 0.5
        assert plan.current_state.get("criteria_met") == 1
        assert plan.current_state.get("criteria_total") == 2

    def test_desired_state(self, registry, engine):
        c1 = SuccessCriterion(description="ship", target_value="100%")
        registry.add(_goal(goal_id="g1", criteria=[c1], target_date="2026-12-31"))
        plan = engine.generate_plan("g1")
        assert plan.desired_state["percent_complete"] == 1.0
        assert plan.desired_state["target_date"] == "2026-12-31"

    def test_plan_with_children(self, registry, engine):
        registry.add(_goal(goal_id="parent", title="Parent"))
        registry.add(_goal(goal_id="child1", title="C1", parent="parent"))
        registry.add(_goal(goal_id="child2", title="C2", parent="parent"))
        plan = engine.generate_plan("parent")
        assert len(plan.child_plans) == 2
        child_ids = {cp["goal_id"] for cp in plan.child_plans}
        assert "child1" in child_ids
        assert "child2" in child_ids

    def test_plan_status_not_started(self, registry, engine):
        registry.add(_goal(goal_id="g1"))
        plan = engine.generate_plan("g1")
        assert plan.status == PlanningStatus.NOT_STARTED.value

    def test_plan_status_on_track(self, registry, engine):
        criteria = [SuccessCriterion(description=f"c{i}", met=(i < 3)) for i in range(4)]
        registry.add(_goal(goal_id="g1", criteria=criteria))
        plan = engine.generate_plan("g1")
        assert plan.status == PlanningStatus.ON_TRACK.value

    def test_plan_with_dependency_blocker(self, registry, engine):
        registry.add(_goal(goal_id="dep", title="Dependency", status=GoalStatus.ACTIVE))
        registry.add(_goal(goal_id="g1", title="Main", deps=["dep"]))
        plan = engine.generate_plan("g1")
        assert len(plan.blockers) > 0
        assert plan.status == PlanningStatus.BLOCKED.value

    def test_plan_no_blockers_when_dep_completed(self, registry, engine):
        registry.add(_goal(goal_id="dep", title="Dep", status=GoalStatus.COMPLETED))
        registry.add(_goal(goal_id="g1", title="Main", deps=["dep"]))
        plan = engine.generate_plan("g1")
        dep_blockers = [b for b in plan.blockers if "Depends on" in b]
        assert len(dep_blockers) == 0


# ── milestones() ─────────────────────────────────────────────────────


class TestMilestones:
    def test_no_children_no_milestones(self, registry, engine):
        registry.add(_goal(goal_id="g1"))
        ms = engine.milestones("g1")
        assert ms == []

    def test_children_become_milestones(self, registry, engine):
        registry.add(_goal(goal_id="parent"))
        registry.add(_goal(goal_id="c1", title="Child 1", parent="parent"))
        registry.add(_goal(goal_id="c2", title="Child 2", parent="parent"))
        ms = engine.milestones("parent")
        assert len(ms) == 2
        titles = {m.title for m in ms}
        assert "Child 1" in titles
        assert "Child 2" in titles

    def test_completed_child_on_track(self, registry, engine):
        registry.add(_goal(goal_id="parent"))
        criteria = [SuccessCriterion(description="done", met=True)]
        registry.add(_goal(goal_id="c1", parent="parent", criteria=criteria))
        ms = engine.milestones("parent")
        assert ms[0].status == PlanningStatus.ON_TRACK.value
        assert ms[0].percent_complete == 1.0

    def test_partial_child_at_risk(self, registry, engine):
        registry.add(_goal(goal_id="parent"))
        criteria = [
            SuccessCriterion(description="a", met=True),
            SuccessCriterion(description="b", met=False),
        ]
        registry.add(_goal(goal_id="c1", parent="parent", criteria=criteria))
        ms = engine.milestones("parent")
        assert ms[0].status == PlanningStatus.AT_RISK.value

    def test_zero_child_not_started(self, registry, engine):
        registry.add(_goal(goal_id="parent"))
        registry.add(_goal(goal_id="c1", parent="parent"))
        ms = engine.milestones("parent")
        assert ms[0].status == PlanningStatus.NOT_STARTED.value

    def test_milestone_has_dependencies(self, registry, engine):
        registry.add(_goal(goal_id="parent"))
        registry.add(_goal(goal_id="c1", parent="parent", deps=["dep1"]))
        ms = engine.milestones("parent")
        assert ms[0].dependencies == ["dep1"]


# ── status() ─────────────────────────────────────────────────────────


class TestStatus:
    def test_returns_planning_status(self, registry, engine):
        registry.add(_goal(goal_id="g1"))
        s = engine.status("g1")
        assert isinstance(s, PlanningStatus)

    def test_not_started(self, registry, engine):
        registry.add(_goal(goal_id="g1"))
        assert engine.status("g1") == PlanningStatus.NOT_STARTED

    def test_on_track(self, registry, engine):
        criteria = [SuccessCriterion(description=f"c{i}", met=True) for i in range(4)]
        registry.add(_goal(goal_id="g1", criteria=criteria))
        assert engine.status("g1") == PlanningStatus.ON_TRACK


# ── roadmap() ────────────────────────────────────────────────────────


class TestRoadmap:
    def test_empty_registry(self, engine):
        rm = engine.roadmap()
        assert rm["plans"] == []
        assert rm["total"] == 0

    def test_active_goals_included(self, registry, engine):
        registry.add(_goal(goal_id="g1"))
        registry.add(_goal(goal_id="g2"))
        rm = engine.roadmap()
        assert rm["total"] == 2
        assert len(rm["plans"]) == 2

    def test_paused_excluded(self, registry, engine):
        registry.add(_goal(goal_id="g1", status=GoalStatus.ACTIVE))
        registry.add(_goal(goal_id="g2", status=GoalStatus.PAUSED))
        rm = engine.roadmap()
        assert rm["total"] == 1

    def test_roadmap_counts(self, registry, engine):
        registry.add(_goal(goal_id="g1"))
        registry.add(_goal(goal_id="g2"))
        rm = engine.roadmap()
        total = rm["blocked"] + rm["at_risk"] + rm["on_track"] + rm["not_started"]
        assert total == rm["total"]

    def test_blocked_sorted_first(self, registry, engine):
        criteria_good = [SuccessCriterion(description=f"c{i}", met=True) for i in range(4)]
        registry.add(_goal(goal_id="good", criteria=criteria_good))
        registry.add(_goal(goal_id="dep", status=GoalStatus.ACTIVE))
        registry.add(_goal(goal_id="blocked", deps=["dep"]))
        rm = engine.roadmap()
        statuses = [p["status"] for p in rm["plans"]]
        blocked_idx = next(i for i, s in enumerate(statuses) if s == "blocked")
        on_track_indices = [i for i, s in enumerate(statuses) if s == "on_track"]
        for ot_idx in on_track_indices:
            assert blocked_idx < ot_idx

    def test_generated_at(self, registry, engine):
        registry.add(_goal(goal_id="g1"))
        rm = engine.roadmap()
        assert rm["generated_at"] > 0


# ── snapshot() ───────────────────────────────────────────────────────


class TestSnapshot:
    def test_snapshot_equals_roadmap(self, registry, engine):
        registry.add(_goal(goal_id="g1"))
        snap = engine.snapshot()
        rm = engine.roadmap()
        assert snap["total"] == rm["total"]
