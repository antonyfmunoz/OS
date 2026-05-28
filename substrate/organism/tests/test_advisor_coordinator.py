"""Tests for advisor → coordinator integration (Phase 2A)."""

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/anti-divergence-gate")

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
from substrate.organism.coordinator import OrganismCoordinator
from substrate.organism.advisor import Advisor


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


def _make_graph() -> RuntimeGraph:
    graph = RuntimeGraph()
    adapter = FakeAdapter()
    graph.register(
        "fake",
        RuntimeClass.AI_CLI,
        adapter.capabilities,
        cost=CostProfile(is_subscription=True),
        adapter=adapter,
    )
    graph.update_status("fake", AvailabilityStatus.AVAILABLE)
    return graph


class TestAdvisorCoordinatorIntegration:
    def test_execute_objective_creates_coordinator(self):
        graph = _make_graph()
        advisor = Advisor(graph=graph)
        assert advisor.coordinator is None

        result = advisor.execute_objective("test", "do something")
        assert advisor.coordinator is not None
        assert result["status"] == "completed"

    def test_execute_objective_with_coordinator(self):
        graph = _make_graph()
        coord = OrganismCoordinator(graph, state_dir=tempfile.mkdtemp())
        advisor = Advisor(graph=graph, coordinator=coord)

        result = advisor.execute_objective("build widget", "create a dashboard widget")
        assert result["status"] == "completed"
        assert result["completion_rate"] == 1.0
        assert result["objective_id"].startswith("obj-")

    def test_execute_objective_with_work_units(self):
        graph = _make_graph()
        advisor = Advisor(graph=graph)

        units = [
            {"title": "Research", "type": "research"},
            {"title": "Build", "type": "build", "blocked_by": ["Research"]},
        ]
        result = advisor.execute_objective("phased work", "two-step process", units)
        assert result["status"] == "completed"
        assert result["work_units"] == 2

    def test_execute_objective_no_graph(self):
        advisor = Advisor()
        result = advisor.execute_objective("test", "no graph")
        assert "error" in result

    def test_get_objective(self):
        graph = _make_graph()
        advisor = Advisor(graph=graph)
        result = advisor.execute_objective("test", "get me later")
        obj_id = result["objective_id"]

        obj = advisor.get_objective(obj_id)
        assert obj is not None
        assert obj["id"] == obj_id
        assert obj["status"] == "completed"

    def test_get_objective_not_found(self):
        graph = _make_graph()
        advisor = Advisor(graph=graph)
        advisor.execute_objective("test", "init coordinator")
        assert advisor.get_objective("nonexistent") is None

    def test_get_objective_no_coordinator(self):
        advisor = Advisor()
        assert advisor.get_objective("anything") is None

    def test_handle_signal_backward_compatible(self):
        advisor = Advisor()
        result = advisor.handle_signal("search for files")
        assert "delegated_to" in result
        assert result["delegated_to"] == "researcher"

    def test_handle_signal_builder(self):
        advisor = Advisor()
        result = advisor.handle_signal("create a new component")
        assert result["delegated_to"] == "builder"

    def test_organism_status_includes_coordinator(self):
        graph = _make_graph()
        advisor = Advisor(graph=graph)
        advisor.execute_objective("test", "for status check")

        status = advisor.organism_status()
        assert "coordinator" in status
        assert status["coordinator"] is not None
        assert status["coordinator"]["total_objectives"] == 1

    def test_organism_status_without_coordinator(self):
        advisor = Advisor()
        status = advisor.organism_status()
        assert status["coordinator"] is None

    def test_is_complex_heuristic(self):
        advisor = Advisor()
        assert not advisor._is_complex("find the bug")
        assert advisor._is_complex(
            "first research the problem.\nthen build the fix.\nfinally deploy it."
        )
        assert not advisor._is_complex("first do this")
