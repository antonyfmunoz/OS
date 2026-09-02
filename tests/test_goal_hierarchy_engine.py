"""Goal Hierarchy Engine — Campaign 8.1 tests.

Tests tree traversal, path computation, validation, and structural queries
on the goal hierarchy via GoalHierarchyEngine.
"""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

# Repo root DERIVED from the active checkout — never a hardcoded worktree path.
from tests.repo_root import ensure_repo_on_path

ensure_repo_on_path()

from substrate.organism.strategic_gap_engine import (
    Goal,
    GoalRegistry,
    GoalStatus,
    GoalType,
)
from substrate.organism.goal_hierarchy_engine import (
    GoalHierarchyEngine,
    HierarchyValidation,
)


@pytest.fixture()
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture()
def registry(tmp_dir):
    return GoalRegistry(store_path=os.path.join(tmp_dir, "goals.jsonl"))


@pytest.fixture()
def hierarchy(registry):
    return GoalHierarchyEngine(goal_registry=registry)


def _add_chain(registry):
    """Create: Vision → Objective → Outcome → Initiative → Project."""
    vision = Goal(goal_id="v1", title="Empire Vision", goal_type=GoalType.VISION)
    obj = Goal(goal_id="o1", title="Revenue Objective", goal_type=GoalType.OBJECTIVE, parent_goal_id="v1")
    outcome = Goal(goal_id="oc1", title="First Revenue", goal_type=GoalType.OUTCOME, parent_goal_id="o1")
    initiative = Goal(goal_id="i1", title="Launch Arena", goal_type=GoalType.INITIATIVE, parent_goal_id="oc1")
    project = Goal(goal_id="p1", title="Build Arena", goal_type=GoalType.PROJECT, parent_goal_id="i1")
    for g in [vision, obj, outcome, initiative, project]:
        registry.add(g)
    return vision, obj, outcome, initiative, project


# ── No-registry edge cases ───────────────────────────────────────────


class TestHierarchyNoRegistry:
    def test_roots_empty(self):
        engine = GoalHierarchyEngine(goal_registry=None)
        assert engine.roots() == []

    def test_leaves_empty(self):
        engine = GoalHierarchyEngine(goal_registry=None)
        assert engine.leaves() == []

    def test_tree_empty(self):
        engine = GoalHierarchyEngine(goal_registry=None)
        assert engine.tree() == {"roots": []}

    def test_path_empty(self):
        engine = GoalHierarchyEngine(goal_registry=None)
        assert engine.path("anything") == []

    def test_ancestors_empty(self):
        engine = GoalHierarchyEngine(goal_registry=None)
        assert engine.ancestors("anything") == []

    def test_descendants_empty(self):
        engine = GoalHierarchyEngine(goal_registry=None)
        assert engine.descendants("anything") == []

    def test_depth_zero(self):
        engine = GoalHierarchyEngine(goal_registry=None)
        assert engine.depth("anything") == 0

    def test_summary_empty(self):
        engine = GoalHierarchyEngine(goal_registry=None)
        s = engine.summary()
        assert s["total_goals"] == 0
        assert s["valid"] is True


# ── Roots ────────────────────────────────────────────────────────────


class TestRoots:
    def test_single_root(self, registry, hierarchy):
        registry.add(Goal(goal_id="v1", title="Vision", goal_type=GoalType.VISION))
        roots = hierarchy.roots()
        assert len(roots) == 1
        assert roots[0].goal_id == "v1"

    def test_multiple_roots(self, registry, hierarchy):
        registry.add(Goal(goal_id="v1", title="Vision1"))
        registry.add(Goal(goal_id="v2", title="Vision2"))
        roots = hierarchy.roots()
        assert len(roots) == 2

    def test_excludes_children(self, registry, hierarchy):
        registry.add(Goal(goal_id="v1", title="Vision"))
        registry.add(Goal(goal_id="o1", title="Obj", parent_goal_id="v1"))
        roots = hierarchy.roots()
        assert len(roots) == 1
        assert roots[0].goal_id == "v1"


# ── Leaves ───────────────────────────────────────────────────────────


class TestLeaves:
    def test_single_goal_is_leaf(self, registry, hierarchy):
        registry.add(Goal(goal_id="v1", title="Vision"))
        leaves = hierarchy.leaves()
        assert len(leaves) == 1

    def test_only_leaf_nodes(self, registry, hierarchy):
        _add_chain(registry)
        leaves = hierarchy.leaves()
        assert len(leaves) == 1
        assert leaves[0].goal_id == "p1"

    def test_multiple_leaves(self, registry, hierarchy):
        registry.add(Goal(goal_id="v1", title="Root"))
        registry.add(Goal(goal_id="c1", title="Child1", parent_goal_id="v1"))
        registry.add(Goal(goal_id="c2", title="Child2", parent_goal_id="v1"))
        leaves = hierarchy.leaves()
        assert len(leaves) == 2


# ── Path ─────────────────────────────────────────────────────────────


class TestPath:
    def test_root_path_is_itself(self, registry, hierarchy):
        registry.add(Goal(goal_id="v1", title="Vision"))
        path = hierarchy.path("v1")
        assert len(path) == 1
        assert path[0].goal_id == "v1"

    def test_full_chain_path(self, registry, hierarchy):
        _add_chain(registry)
        path = hierarchy.path("p1")
        assert len(path) == 5
        assert path[0].goal_id == "v1"
        assert path[-1].goal_id == "p1"

    def test_path_nonexistent(self, registry, hierarchy):
        assert hierarchy.path("nope") == []


# ── Ancestors ────────────────────────────────────────────────────────


class TestAncestors:
    def test_root_has_no_ancestors(self, registry, hierarchy):
        registry.add(Goal(goal_id="v1", title="Vision"))
        assert hierarchy.ancestors("v1") == []

    def test_leaf_ancestors(self, registry, hierarchy):
        _add_chain(registry)
        ancestors = hierarchy.ancestors("p1")
        assert len(ancestors) == 4
        assert ancestors[0].goal_id == "i1"
        assert ancestors[-1].goal_id == "v1"


# ── Descendants ──────────────────────────────────────────────────────


class TestDescendants:
    def test_leaf_has_no_descendants(self, registry, hierarchy):
        registry.add(Goal(goal_id="v1", title="Vision"))
        assert hierarchy.descendants("v1") == []

    def test_root_descendants(self, registry, hierarchy):
        _add_chain(registry)
        descs = hierarchy.descendants("v1")
        assert len(descs) == 4
        ids = [d.goal_id for d in descs]
        assert "o1" in ids
        assert "p1" in ids

    def test_mid_node_descendants(self, registry, hierarchy):
        _add_chain(registry)
        descs = hierarchy.descendants("o1")
        assert len(descs) == 3


# ── Depth ────────────────────────────────────────────────────────────


class TestDepth:
    def test_root_depth_zero(self, registry, hierarchy):
        registry.add(Goal(goal_id="v1", title="Vision"))
        assert hierarchy.depth("v1") == 0

    def test_leaf_depth(self, registry, hierarchy):
        _add_chain(registry)
        assert hierarchy.depth("p1") == 4

    def test_mid_depth(self, registry, hierarchy):
        _add_chain(registry)
        assert hierarchy.depth("oc1") == 2


# ── Tree ─────────────────────────────────────────────────────────────


class TestTree:
    def test_empty_tree(self, hierarchy):
        assert hierarchy.tree() == {"roots": []}

    def test_single_root_tree(self, registry, hierarchy):
        registry.add(Goal(goal_id="v1", title="Vision"))
        t = hierarchy.tree()
        assert len(t["roots"]) == 1
        assert t["roots"][0]["children"] == []

    def test_nested_tree(self, registry, hierarchy):
        _add_chain(registry)
        t = hierarchy.tree()
        assert len(t["roots"]) == 1
        vision_node = t["roots"][0]
        assert vision_node["goal_id"] == "v1"
        obj_node = vision_node["children"][0]
        assert obj_node["goal_id"] == "o1"

    def test_subtree(self, registry, hierarchy):
        _add_chain(registry)
        t = hierarchy.tree(root_id="o1")
        assert t["goal_id"] == "o1"
        assert len(t["children"]) == 1


# ── Validate Hierarchy ──────────────────────────────────────────────


class TestValidateHierarchy:
    def test_valid_hierarchy(self, registry, hierarchy):
        _add_chain(registry)
        v = hierarchy.validate_hierarchy()
        assert v.valid is True
        assert v.orphans == []
        assert v.cycles == []
        assert v.missing_parents == []

    def test_missing_parent(self, registry, hierarchy):
        registry.add(Goal(goal_id="c1", title="Orphan Child", parent_goal_id="nonexistent"))
        v = hierarchy.validate_hierarchy()
        assert v.valid is False
        assert len(v.missing_parents) == 1
        assert v.missing_parents[0]["missing_parent_id"] == "nonexistent"

    def test_type_violation(self, registry, hierarchy):
        registry.add(Goal(goal_id="p1", title="Project", goal_type=GoalType.PROJECT))
        registry.add(Goal(goal_id="v1", title="Vision under Project", goal_type=GoalType.VISION, parent_goal_id="p1"))
        v = hierarchy.validate_hierarchy()
        assert len(v.type_violations) == 1
        assert v.type_violations[0]["goal_type"] == "vision"
        assert v.type_violations[0]["parent_type"] == "project"

    def test_empty_is_valid(self, hierarchy):
        v = hierarchy.validate_hierarchy()
        assert v.valid is True

    def test_validation_to_dict(self, registry, hierarchy):
        _add_chain(registry)
        v = hierarchy.validate_hierarchy()
        d = v.to_dict()
        assert d["valid"] is True
        assert d["orphan_count"] == 0
        assert d["cycle_count"] == 0


# ── Trace to Vision ─────────────────────────────────────────────────


class TestTraceToVision:
    def test_trace_full_chain(self, registry, hierarchy):
        _add_chain(registry)
        trace = hierarchy.trace_to_vision("p1")
        assert len(trace) == 5
        assert trace[0]["goal_type"] == "vision"
        assert trace[-1]["goal_type"] == "project"

    def test_trace_root_only(self, registry, hierarchy):
        registry.add(Goal(goal_id="v1", title="Vision", goal_type=GoalType.VISION))
        trace = hierarchy.trace_to_vision("v1")
        assert len(trace) == 1
        assert trace[0]["goal_type"] == "vision"

    def test_trace_nonexistent(self, hierarchy):
        assert hierarchy.trace_to_vision("nope") == []


# ── Subtree IDs ──────────────────────────────────────────────────────


class TestSubtreeIds:
    def test_leaf_subtree(self, registry, hierarchy):
        registry.add(Goal(goal_id="p1", title="Leaf"))
        ids = hierarchy.subtree_ids("p1")
        assert ids == ["p1"]

    def test_root_subtree(self, registry, hierarchy):
        _add_chain(registry)
        ids = hierarchy.subtree_ids("v1")
        assert len(ids) == 5
        assert "v1" in ids
        assert "p1" in ids


# ── Summary ──────────────────────────────────────────────────────────


class TestSummary:
    def test_summary_populated(self, registry, hierarchy):
        _add_chain(registry)
        s = hierarchy.summary()
        assert s["total_goals"] == 5
        assert s["root_count"] == 1
        assert s["leaf_count"] == 1
        assert s["max_depth"] == 4
        assert s["valid"] is True
        assert "vision" in s["by_type"]
        assert "project" in s["by_type"]

    def test_summary_empty(self, hierarchy):
        s = hierarchy.summary()
        assert s["total_goals"] == 0
        assert s["root_count"] == 0
