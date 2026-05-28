"""Tests for ObjectivePhysics engine."""
from __future__ import annotations

import sys

import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from substrate.organism.objective_physics import (
    ObjectivePhysics,
    ObjectiveState,
)


def test_register_objective():
    op = ObjectivePhysics()
    node = op.register_objective("obj-1", name="Test Objective")
    assert node.objective_id == "obj-1"


def test_dependency_linking():
    op = ObjectivePhysics()
    op.register_objective("parent", name="Parent")
    op.register_objective("child", name="Child", depends_on=["parent"])
    parent = op._nodes["parent"]
    assert "child" in parent.enables


def test_blocking_nodes():
    op = ObjectivePhysics()
    op.register_objective("root", name="Root")
    op.register_objective("a", depends_on=["root"])
    op.register_objective("b", depends_on=["root"])
    blockers = op.blocking_nodes()
    assert len(blockers) == 1
    assert blockers[0].objective_id == "root"


def test_update_state():
    op = ObjectivePhysics()
    op.register_objective("obj-1")
    op.update_state("obj-1", ObjectiveState.EXECUTING)
    assert op._nodes["obj-1"].state == ObjectiveState.EXECUTING
    assert op._nodes["obj-1"].started_at > 0


def test_execution_gravity():
    op = ObjectivePhysics()
    op.register_objective("root", leverage_weight=5.0, resource_cost=10.0)
    op.register_objective("a", depends_on=["root"], resource_cost=5.0)
    op.register_objective("b", depends_on=["root"], resource_cost=3.0)
    gravity = op.execution_gravity()
    assert gravity[0]["objective_id"] == "root"
    assert gravity[0]["transitive_downstream"] == 2


def test_critical_paths():
    op = ObjectivePhysics()
    op.register_objective("root", estimated_seconds=10, leverage_weight=3)
    op.register_objective("mid", depends_on=["root"], estimated_seconds=20, leverage_weight=2)
    op.register_objective("leaf", depends_on=["mid"], estimated_seconds=5, leverage_weight=1)
    paths = op.critical_paths()
    assert len(paths) >= 1
    assert len(paths[0].path) == 3


def test_leverage_propagation():
    op = ObjectivePhysics()
    op.register_objective("root", leverage_weight=5)
    op.register_objective("a", depends_on=["root"], leverage_weight=3)
    op.register_objective("b", depends_on=["a"], leverage_weight=2)
    prop = op.leverage_propagation("root")
    assert prop.propagation_depth == 2
    assert prop.compound_leverage == 5.0


def test_what_matters_most():
    op = ObjectivePhysics()
    op.register_objective("critical", leverage_weight=10.0)
    op.register_objective("minor", leverage_weight=1.0)
    op.register_objective("dep", depends_on=["critical"], leverage_weight=5.0)
    result = op.what_matters_most(2)
    assert result[0]["objective_id"] == "critical"


def test_what_blocks_everything():
    op = ObjectivePhysics()
    op.register_objective("blocker")
    op.register_objective("a", depends_on=["blocker"])
    op.register_objective("b", depends_on=["blocker"])
    op.update_state("a", ObjectiveState.BLOCKED)
    blockers = op.what_blocks_everything()
    assert len(blockers) == 1
    assert blockers[0]["currently_blocking"] == 1


def test_physics_tick():
    op = ObjectivePhysics()
    op.register_objective("root")
    op.register_objective("child", depends_on=["root"])
    result = op.physics_tick()
    assert result["total_objectives"] == 2
    assert "critical_paths" in result


def test_to_dict():
    op = ObjectivePhysics()
    op.register_objective("a", name="Alpha")
    d = op.to_dict()
    assert d["total_objectives"] == 1
    assert "by_state" in d


def test_cycle_prevention():
    op = ObjectivePhysics()
    op.register_objective("a")
    op.register_objective("b", depends_on=["a"])
    # Manually create cycle
    op._nodes["a"].depends_on.append("b")
    op._nodes["b"].enables.append("a")
    # Should not hang
    paths = op.critical_paths()
    assert isinstance(paths, list)


if __name__ == "__main__":
    test_register_objective()
    test_dependency_linking()
    test_blocking_nodes()
    test_update_state()
    test_execution_gravity()
    test_critical_paths()
    test_leverage_propagation()
    test_what_matters_most()
    test_what_blocks_everything()
    test_physics_tick()
    test_to_dict()
    test_cycle_prevention()
    print("ALL OBJECTIVE PHYSICS TESTS PASSED")
