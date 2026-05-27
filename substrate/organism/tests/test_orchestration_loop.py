"""Tests for orchestration_loop — PersistentLoop stages wired to organism daemon."""

import tempfile
from typing import Any

import pytest

from substrate.organism.daemon import OrganismDaemon
from substrate.organism.homeostasis import HomeostasisEngine
from substrate.organism.orchestration_loop import (
    _stage_delegation_check,
    _stage_health_check,
    _stage_homeostasis,
    _stage_objective_advance,
    _stage_organism_tick,
    _stage_recovery,
    _stage_state_persist,
    create_full_orchestration_loop,
    create_orchestration_loop,
    register_organism_stages,
)
from substrate.organism.runtime_graph import (
    AvailabilityStatus,
    CostProfile,
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
    RuntimeResult,
)
from substrate.organism.runtime_supervisor import RuntimeSupervisor
from substrate.execution.loop.persistent_loop import (
    CycleReport,
    PersistentLoop,
    LoopDefinition,
    STAGE_REGISTRY,
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
        return frozenset({RuntimeCapability.REASON, RuntimeCapability.CODE_WRITE, RuntimeCapability.SHELL})

    def check_available(self) -> bool:
        return True

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        return RuntimeResult(output=self._output, runtime_id=self._rid, latency_ms=5)


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


def _make_report() -> CycleReport:
    return CycleReport(loop_name="test", cycle_num=1, started_at="now", finished_at="")


class TestStageRegistration:
    def test_register_stages(self, tmp_path):
        graph = _make_graph()
        daemon = OrganismDaemon(store_dir=str(tmp_path / "org"), graph=graph)
        daemon.start()
        register_organism_stages(daemon)

        assert "organism_tick" in STAGE_REGISTRY
        assert "health_check" in STAGE_REGISTRY
        assert "homeostasis_check" in STAGE_REGISTRY
        assert "recovery_sweep" in STAGE_REGISTRY
        assert "delegation_check" in STAGE_REGISTRY
        assert "objective_advance" in STAGE_REGISTRY
        assert "state_persist" in STAGE_REGISTRY


class TestOrganismTickStage:
    def test_tick_stage_runs(self, tmp_path):
        graph = _make_graph()
        daemon = OrganismDaemon(store_dir=str(tmp_path / "org"), graph=graph)
        daemon.start()
        register_organism_stages(daemon)

        report = _make_report()
        loop = PersistentLoop(LoopDefinition(name="t", domain="test"))
        _stage_organism_tick(loop, report)

        assert len(report.details) == 1
        assert report.details[0]["stage"] == "organism_tick"
        assert "tick" in report.details[0]

    def test_tick_stage_no_daemon(self, tmp_path):
        import substrate.organism.orchestration_loop as ol
        old_ref = ol._daemon_ref
        ol._daemon_ref = None

        report = _make_report()
        loop = PersistentLoop(LoopDefinition(name="t", domain="test"))
        _stage_organism_tick(loop, report)
        assert report.errors == 1

        ol._daemon_ref = old_ref


class TestHealthCheckStage:
    def test_health_check_with_supervisor(self, tmp_path):
        graph = _make_graph()
        daemon = OrganismDaemon(store_dir=str(tmp_path / "org"), graph=graph)
        daemon.start()
        register_organism_stages(daemon)

        report = _make_report()
        loop = PersistentLoop(LoopDefinition(name="t", domain="test"))
        _stage_health_check(loop, report)


class TestHomeostasisStage:
    def test_homeostasis_stage(self, tmp_path):
        graph = _make_graph()
        daemon = OrganismDaemon(store_dir=str(tmp_path / "org"), graph=graph)
        daemon.start()
        register_organism_stages(daemon)

        daemon.homeostasis.record_execution(False, "test error")
        daemon.homeostasis.record_execution(False, "test error")
        daemon.homeostasis.record_execution(False, "test error")
        daemon.homeostasis.record_execution(False, "test error")

        report = _make_report()
        loop = PersistentLoop(LoopDefinition(name="t", domain="test"))
        _stage_homeostasis(loop, report)


class TestStatePersistStage:
    def test_state_persist(self, tmp_path):
        graph = _make_graph()
        daemon = OrganismDaemon(store_dir=str(tmp_path / "org"), graph=graph)
        daemon.start()
        register_organism_stages(daemon)

        report = _make_report()
        loop = PersistentLoop(LoopDefinition(name="t", domain="test"))
        _stage_state_persist(loop, report)

        assert len(report.details) == 1
        assert report.details[0]["persisted"] is True


class TestLoopCreation:
    def test_create_default_loop(self):
        loop = create_orchestration_loop(interval_seconds=30)
        assert loop.name == "organism_orchestration"
        assert loop.domain == "organism"
        assert loop.interval_seconds == 30
        assert "organism_tick" in loop.definition.stages
        assert "state_persist" in loop.definition.stages

    def test_create_full_loop(self):
        loop = create_full_orchestration_loop(interval_seconds=60)
        assert loop.name == "organism_full_orchestration"
        assert len(loop.definition.stages) == 6
        assert "health_check" in loop.definition.stages
        assert "recovery_sweep" in loop.definition.stages

    def test_create_loop_with_custom_stages(self):
        loop = create_orchestration_loop(
            interval_seconds=10,
            stages=["health_check", "state_persist"],
        )
        assert loop.definition.stages == ["health_check", "state_persist"]

    def test_loop_run_once(self, tmp_path):
        graph = _make_graph()
        daemon = OrganismDaemon(store_dir=str(tmp_path / "org"), graph=graph)
        daemon.start()
        register_organism_stages(daemon)

        loop = create_orchestration_loop(interval_seconds=10)
        report = loop.run_once()
        assert report.loop_name == "organism_orchestration"
        assert report.cycle_num == 1
