"""Tests for OrganismCoordinator — task decomposition, assignment, execution."""

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/anti-divergence-gate")

import pytest
import tempfile
from typing import Any

from substrate.organism.runtime_graph import (
    AvailabilityStatus,
    CostProfile,
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
    RuntimeResult,
)
from substrate.organism.coordinator import (
    ObjectiveStatus,
    OrganismCoordinator,
    WorkUnit,
    WorkUnitStatus,
    WorkUnitType,
)


class FakeAdapter:
    def __init__(self, rid: str = "fake", output: str = "done") -> None:
        self._rid = rid
        self._output = output

    @property
    def runtime_id(self) -> str:
        return self._rid

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.AI_CLI

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset(
            {
                RuntimeCapability.REASON,
                RuntimeCapability.CODE_WRITE,
                RuntimeCapability.CODE_REVIEW,
                RuntimeCapability.RESEARCH,
                RuntimeCapability.SHELL,
            }
        )

    def check_available(self) -> bool:
        return True

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        return RuntimeResult(output=self._output, runtime_id=self._rid, latency_ms=10)


def _make_coordinator(output: str = "done") -> OrganismCoordinator:
    graph = RuntimeGraph()
    adapter = FakeAdapter(output=output)
    graph.register(
        "fake",
        RuntimeClass.AI_CLI,
        adapter.capabilities,
        cost=CostProfile(is_subscription=True),
        adapter=adapter,
    )
    graph.update_status("fake", AvailabilityStatus.AVAILABLE)

    with tempfile.TemporaryDirectory() as td:
        coord = OrganismCoordinator(graph, state_dir=td)
        coord._state_dir = coord._state_dir  # keep the tmpdir alive
    return OrganismCoordinator(graph, state_dir=tempfile.mkdtemp())


class TestWorkUnit:
    def test_defaults(self):
        wu = WorkUnit(title="test")
        assert wu.id.startswith("wu-")
        assert wu.status == WorkUnitStatus.PENDING
        assert wu.is_ready
        assert not wu.is_terminal

    def test_blocked(self):
        wu = WorkUnit(title="test", blocked_by=["other"])
        assert not wu.is_ready

    def test_terminal_states(self):
        for status in [WorkUnitStatus.COMPLETED, WorkUnitStatus.FAILED, WorkUnitStatus.CANCELLED]:
            wu = WorkUnit(title="test", status=status)
            assert wu.is_terminal

    def test_to_dict(self):
        wu = WorkUnit(title="test task", unit_type=WorkUnitType.BUILD)
        d = wu.to_dict()
        assert d["title"] == "test task"
        assert d["unit_type"] == "build"


class TestDecomposition:
    def test_single_work_unit(self):
        coord = _make_coordinator()
        obj = coord.decompose("fix the bug", "Fix the auth bug in login.py")
        assert len(obj.work_units) == 1
        assert obj.work_units[0].title == "fix the bug"
        assert obj.status == ObjectiveStatus.EXECUTING

    def test_multi_work_unit(self):
        coord = _make_coordinator()
        obj = coord.decompose(
            "Build feature",
            "New auth system",
            work_units=[
                {"title": "Research auth patterns", "type": "research"},
                {"title": "Implement auth module", "type": "build", "blocked_by": []},
                {"title": "Review auth code", "type": "review"},
            ],
        )
        assert len(obj.work_units) == 3
        assert obj.work_units[0].unit_type == WorkUnitType.RESEARCH
        assert obj.work_units[1].unit_type == WorkUnitType.BUILD

    def test_dependency_resolution(self):
        coord = _make_coordinator()
        obj = coord.decompose(
            "Pipeline",
            "Sequential work",
            work_units=[
                {"title": "Step A"},
                {"title": "Step B", "blocked_by": ["Step A"]},
            ],
        )
        step_b = obj.work_units[1]
        assert step_b.status == WorkUnitStatus.BLOCKED
        step_a = obj.work_units[0]
        assert step_b.blocked_by == [step_a.id]
        assert step_b.id in step_a.blocks

    def test_keyword_inference(self):
        coord = _make_coordinator()
        obj = coord.decompose("research the codebase", "Find patterns")
        assert obj.work_units[0].unit_type == WorkUnitType.RESEARCH

        obj2 = coord.decompose("build the API", "Create endpoints")
        assert obj2.work_units[0].unit_type == WorkUnitType.BUILD


class TestRuntimeAssignment:
    def test_assign_runtimes(self):
        coord = _make_coordinator()
        obj = coord.decompose("test task", "do something")
        assignments = coord.assign_runtimes(obj.id)
        assert len(assignments) == 1
        assert "fake" in assignments.values()

    def test_assign_nonexistent_objective(self):
        coord = _make_coordinator()
        assignments = coord.assign_runtimes("nonexistent")
        assert assignments == {}


class TestExecution:
    def test_execute_single(self):
        coord = _make_coordinator(output="task completed")
        obj = coord.decompose("analyze code", "Look at the codebase")
        coord.assign_runtimes(obj.id)

        results = coord.execute_ready(obj.id)
        assert len(results) == 1
        assert results[0]["status"] == "completed"

        obj = coord.get_objective(obj.id)
        assert obj is not None
        assert obj.status == ObjectiveStatus.COMPLETED

    def test_execute_objective_full_lifecycle(self):
        coord = _make_coordinator(output="result")
        result = coord.execute_objective(
            "Full pipeline",
            "Test full lifecycle",
            work_units=[
                {"title": "Research", "type": "research"},
                {"title": "Build", "type": "build"},
            ],
        )
        assert result["status"] in {"completed", "partial"}
        assert result["completion_rate"] > 0

    def test_dependency_ordering(self):
        coord = _make_coordinator(output="ok")
        obj = coord.decompose(
            "Sequential",
            "A then B",
            work_units=[
                {"title": "Step A"},
                {"title": "Step B", "blocked_by": ["Step A"]},
            ],
        )
        coord.assign_runtimes(obj.id)

        assert obj.work_units[1].status == WorkUnitStatus.BLOCKED

        results_1 = coord.execute_ready(obj.id)
        assert len(results_1) == 1
        assert obj.work_units[0].status == WorkUnitStatus.COMPLETED
        assert obj.work_units[1].status == WorkUnitStatus.PENDING

        results_2 = coord.execute_ready(obj.id)
        assert len(results_2) == 1
        assert obj.work_units[1].status == WorkUnitStatus.COMPLETED

    def test_execute_empty_graph(self):
        graph = RuntimeGraph()
        coord = OrganismCoordinator(graph, state_dir=tempfile.mkdtemp())
        result = coord.execute_objective("test", "no runtimes available")
        assert result["status"] in {"failed", "partial"}

    def test_generation_increments(self):
        coord = _make_coordinator()
        assert coord.generation == 0
        coord.decompose("a", "a")
        assert coord.generation == 1
        coord.decompose("b", "b")
        assert coord.generation == 2


class TestStatus:
    def test_list_objectives(self):
        coord = _make_coordinator()
        coord.decompose("obj1", "first")
        coord.decompose("obj2", "second")
        objs = coord.list_objectives()
        assert len(objs) == 2

    def test_status(self):
        coord = _make_coordinator()
        s = coord.status()
        assert "total_objectives" in s
        assert "graph" in s
