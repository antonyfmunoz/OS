"""Tests for GoalAlignmentEngine — Campaign 8.4.

Validates alignment measurement between work and goals,
work→goal tracing (the C8 acceptance test), and orphan detection.
"""

import sys
import time

# Repo root DERIVED from the active checkout — never a hardcoded worktree path.
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
from substrate.organism.goal_alignment_engine import (
    AlignmentReport,
    GoalAlignmentEngine,
)


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def tmp_goals(tmp_path):
    """Create a GoalRegistry with a VISION→OBJECTIVE→OUTCOME→PROJECT hierarchy."""
    store = str(tmp_path / "goals.jsonl")
    registry = GoalRegistry(store_path=store)

    vision = Goal(
        goal_id="v-1",
        title="Build $10K/month revenue",
        goal_type=GoalType.VISION,
        status=GoalStatus.ACTIVE,
    )
    objective = Goal(
        goal_id="obj-1",
        title="Launch Initiate Arena",
        goal_type=GoalType.OBJECTIVE,
        status=GoalStatus.ACTIVE,
        parent_goal_id="v-1",
    )
    outcome = Goal(
        goal_id="out-1",
        title="First paying customer",
        goal_type=GoalType.OUTCOME,
        status=GoalStatus.ACTIVE,
        parent_goal_id="obj-1",
    )
    project = Goal(
        goal_id="proj-1",
        title="Outreach campaign",
        goal_type=GoalType.PROJECT,
        status=GoalStatus.ACTIVE,
        parent_goal_id="out-1",
    )

    registry.add(vision)
    registry.add(objective)
    registry.add(outcome)
    registry.add(project)
    return registry


@pytest.fixture
def hierarchy(tmp_goals):
    return GoalHierarchyEngine(goal_registry=tmp_goals)


class FakeRealityEntity:
    def __init__(self, entity_id, name, status="active", properties=None):
        self.entity_id = entity_id
        self.name = name
        self.status = type("S", (), {"value": status})()
        self.properties = properties or {}


class FakeRealityGraph:
    def __init__(self, packets=None):
        self._packets = packets or []

    def find_by_type(self, entity_type):
        return self._packets


class FakeRuntimeSnapshot:
    def __init__(self, active=None, blocked=None):
        self.active_work_packets = active or []
        self.blocked_work = blocked or []


class FakeRuntimeAwareness:
    def __init__(self, snapshot):
        self._snap = snapshot

    def snapshot(self):
        return self._snap


# ── AlignmentReport defaults ─────────────────────────────────────────


class TestAlignmentReportDefaults:
    def test_default_fields(self):
        r = AlignmentReport()
        assert r.total_work_count == 0
        assert r.linked_work_count == 0
        assert r.unlinked_work_count == 0
        assert r.alignment_score == 0.0
        assert r.goal_coverage == {}
        assert r.orphan_goals == []
        assert r.unlinked_items == []
        assert r.generated_at == 0.0

    def test_to_dict_round_trip(self):
        r = AlignmentReport(
            total_work_count=10,
            linked_work_count=7,
            unlinked_work_count=3,
            alignment_score=0.71234,
            generated_at=time.time(),
        )
        d = r.to_dict()
        assert d["alignment_score"] == 0.7123
        assert d["orphan_goal_count"] == 0

    def test_to_dict_orphan_count(self):
        r = AlignmentReport(orphan_goals=[{"goal_id": "g1", "title": "T"}])
        d = r.to_dict()
        assert d["orphan_goal_count"] == 1


# ── Constructor degradation ──────────────────────────────────────────


class TestConstructorDegradation:
    def test_all_none_alignment_score(self):
        engine = GoalAlignmentEngine()
        assert engine.alignment_score() == 1.0

    def test_all_none_unlinked_work(self):
        engine = GoalAlignmentEngine()
        assert engine.unlinked_work() == []

    def test_all_none_coverage(self):
        engine = GoalAlignmentEngine()
        assert engine.coverage() == {}

    def test_all_none_orphan_goals(self):
        engine = GoalAlignmentEngine()
        assert engine.orphan_goals() == []

    def test_all_none_report(self):
        engine = GoalAlignmentEngine()
        r = engine.report()
        assert r.total_work_count == 0
        assert r.alignment_score == 1.0

    def test_all_none_goal_for_work(self):
        engine = GoalAlignmentEngine()
        assert engine.goal_for_work("wp-1") == []


# ── alignment_score ──────────────────────────────────────────────────


class TestAlignmentScore:
    def test_no_work_returns_1(self, tmp_goals, hierarchy):
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
        )
        assert engine.alignment_score() == 1.0

    def test_all_linked_returns_1(self, tmp_goals, hierarchy):
        graph = FakeRealityGraph([
            FakeRealityEntity("wp-1", "Work 1", properties={"goal_id": "proj-1"}),
            FakeRealityEntity("wp-2", "Work 2", properties={"goal_id": "out-1"}),
        ])
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            reality_graph=graph,
        )
        assert engine.alignment_score() == 1.0

    def test_half_linked(self, tmp_goals, hierarchy):
        graph = FakeRealityGraph([
            FakeRealityEntity("wp-1", "Work 1", properties={"goal_id": "proj-1"}),
            FakeRealityEntity("wp-2", "Work 2", properties={}),
        ])
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            reality_graph=graph,
        )
        assert engine.alignment_score() == 0.5

    def test_none_linked(self, tmp_goals, hierarchy):
        graph = FakeRealityGraph([
            FakeRealityEntity("wp-1", "Work 1", properties={}),
            FakeRealityEntity("wp-2", "Work 2", properties={}),
        ])
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            reality_graph=graph,
        )
        assert engine.alignment_score() == 0.0

    def test_goal_refs_counts_as_linked(self, tmp_goals, hierarchy):
        graph = FakeRealityGraph([
            FakeRealityEntity("wp-1", "Work 1", properties={"goal_refs": ["proj-1"]}),
        ])
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            reality_graph=graph,
        )
        assert engine.alignment_score() == 1.0


# ── unlinked_work ────────────────────────────────────────────────────


class TestUnlinkedWork:
    def test_returns_unlinked_only(self, tmp_goals, hierarchy):
        graph = FakeRealityGraph([
            FakeRealityEntity("wp-1", "Linked", properties={"goal_id": "proj-1"}),
            FakeRealityEntity("wp-2", "Unlinked", properties={}),
        ])
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            reality_graph=graph,
        )
        unlinked = engine.unlinked_work()
        assert len(unlinked) == 1
        assert unlinked[0]["work_id"] == "wp-2"

    def test_empty_when_all_linked(self, tmp_goals, hierarchy):
        graph = FakeRealityGraph([
            FakeRealityEntity("wp-1", "Linked", properties={"goal_id": "proj-1"}),
        ])
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            reality_graph=graph,
        )
        assert engine.unlinked_work() == []


# ── goal_for_work — THE acceptance test ──────────────────────────────


class TestGoalForWork:
    def test_traces_work_to_vision(self, tmp_goals, hierarchy):
        """Campaign 8 acceptance test:
        Work Packet → Project → Initiative → Outcome → Objective → Vision
        """
        graph = FakeRealityGraph([
            FakeRealityEntity("wp-1", "Outreach email", properties={"goal_id": "proj-1"}),
        ])
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            reality_graph=graph,
        )
        chain = engine.goal_for_work("wp-1")
        assert len(chain) >= 4
        assert chain[0]["goal_type"] == "vision"
        assert chain[-1]["goal_type"] == "project"
        assert chain[0]["goal_id"] == "v-1"
        assert chain[-1]["goal_id"] == "proj-1"

    def test_work_not_found(self, tmp_goals, hierarchy):
        graph = FakeRealityGraph([])
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            reality_graph=graph,
        )
        assert engine.goal_for_work("nonexistent") == []

    def test_work_with_no_goal_id(self, tmp_goals, hierarchy):
        graph = FakeRealityGraph([
            FakeRealityEntity("wp-1", "No Goal", properties={}),
        ])
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            reality_graph=graph,
        )
        assert engine.goal_for_work("wp-1") == []

    def test_work_via_goal_refs(self, tmp_goals, hierarchy):
        graph = FakeRealityGraph([
            FakeRealityEntity("wp-1", "Via Refs", properties={"goal_refs": ["proj-1"]}),
        ])
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            reality_graph=graph,
        )
        chain = engine.goal_for_work("wp-1")
        assert len(chain) >= 1
        assert any(c["goal_id"] == "proj-1" for c in chain)

    def test_fallback_to_registry_without_hierarchy(self, tmp_goals):
        graph = FakeRealityGraph([
            FakeRealityEntity("wp-1", "Work", properties={"goal_id": "proj-1"}),
        ])
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            reality_graph=graph,
        )
        chain = engine.goal_for_work("wp-1")
        assert len(chain) == 1
        assert chain[0]["goal_id"] == "proj-1"


# ── coverage ─────────────────────────────────────────────────────────


class TestCoverage:
    def test_counts_per_goal(self, tmp_goals, hierarchy):
        graph = FakeRealityGraph([
            FakeRealityEntity("wp-1", "W1", properties={"goal_id": "proj-1"}),
            FakeRealityEntity("wp-2", "W2", properties={"goal_id": "proj-1"}),
            FakeRealityEntity("wp-3", "W3", properties={"goal_id": "out-1"}),
        ])
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            reality_graph=graph,
        )
        cov = engine.coverage()
        assert cov["proj-1"] == 2
        assert cov["out-1"] == 1

    def test_empty_coverage(self, tmp_goals, hierarchy):
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
        )
        assert engine.coverage() == {}

    def test_goal_refs_counted(self, tmp_goals, hierarchy):
        graph = FakeRealityGraph([
            FakeRealityEntity("wp-1", "W1", properties={"goal_refs": ["proj-1", "out-1"]}),
        ])
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            reality_graph=graph,
        )
        cov = engine.coverage()
        assert cov.get("proj-1", 0) >= 1
        assert cov.get("out-1", 0) >= 1


# ── orphan_goals ─────────────────────────────────────────────────────


class TestOrphanGoals:
    def test_all_goals_orphan_with_no_work(self, tmp_goals, hierarchy):
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
        )
        orphans = engine.orphan_goals()
        assert len(orphans) == 4

    def test_covered_goal_not_orphan(self, tmp_goals, hierarchy):
        graph = FakeRealityGraph([
            FakeRealityEntity("wp-1", "W1", properties={"goal_id": "proj-1"}),
        ])
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            reality_graph=graph,
        )
        orphans = engine.orphan_goals()
        orphan_ids = {g.goal_id for g in orphans}
        assert "proj-1" not in orphan_ids

    def test_no_registry_returns_empty(self):
        engine = GoalAlignmentEngine()
        assert engine.orphan_goals() == []


# ── report ───────────────────────────────────────────────────────────


class TestReport:
    def test_report_structure(self, tmp_goals, hierarchy):
        graph = FakeRealityGraph([
            FakeRealityEntity("wp-1", "Linked", properties={"goal_id": "proj-1"}),
            FakeRealityEntity("wp-2", "Unlinked", properties={}),
        ])
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            reality_graph=graph,
        )
        r = engine.report()
        assert r.total_work_count == 2
        assert r.linked_work_count == 1
        assert r.unlinked_work_count == 1
        assert r.alignment_score == 0.5
        assert r.generated_at > 0

    def test_report_to_dict(self, tmp_goals, hierarchy):
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
        )
        d = engine.report().to_dict()
        assert "alignment_score" in d
        assert "orphan_goal_count" in d
        assert "generated_at" in d

    def test_report_no_work_score_1(self, tmp_goals, hierarchy):
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
        )
        r = engine.report()
        assert r.alignment_score == 1.0

    def test_report_orphans_populated(self, tmp_goals, hierarchy):
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
        )
        r = engine.report()
        assert len(r.orphan_goals) == 4


# ── Runtime awareness integration ────────────────────────────────────


class TestRuntimeAwarenessIntegration:
    def test_work_from_runtime_snapshot(self, tmp_goals, hierarchy):
        snap = FakeRuntimeSnapshot(active=[
            {"packet_id": "wp-r1", "title": "Runtime work", "goal_id": "proj-1", "status": "active"},
        ])
        runtime = FakeRuntimeAwareness(snap)
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            runtime_awareness=runtime,
        )
        assert engine.alignment_score() == 1.0

    def test_dedup_across_sources(self, tmp_goals, hierarchy):
        graph = FakeRealityGraph([
            FakeRealityEntity("wp-1", "Work 1", properties={"goal_id": "proj-1"}),
        ])
        snap = FakeRuntimeSnapshot(active=[
            {"packet_id": "wp-1", "title": "Work 1 dup", "goal_id": "proj-1"},
        ])
        runtime = FakeRuntimeAwareness(snap)
        engine = GoalAlignmentEngine(
            goal_registry=tmp_goals,
            goal_hierarchy=hierarchy,
            reality_graph=graph,
            runtime_awareness=runtime,
        )
        r = engine.report()
        assert r.total_work_count == 1
