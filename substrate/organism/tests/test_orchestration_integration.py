"""Integration tests for Phase 2 organism orchestration.

Tests the full wiring: Advisor ↔ RuntimeGraph ↔ RuntimeSupervisor
↔ OrganismCoordinator ↔ HomeostasisEngine ↔ OrganismObserver.

Each test verifies a specific integration point. No mocks of
organism subsystems — we use FakeAdapter for runtime execution only.
"""

from __future__ import annotations

import tempfile
import time
from typing import Any

import pytest

from substrate.organism.advisor import (
    Advisor,
    _infer_capability,
    _infer_risk_class,
    _CAPABILITY_TO_AGENT,
)
from substrate.organism.coordinator import OrganismCoordinator
from substrate.organism.daemon import OrganismDaemon
from substrate.organism.homeostasis import HomeostasisEngine
from substrate.organism.observability import OrganismObserver
from substrate.organism.runtime_graph import (
    AvailabilityStatus,
    CostProfile,
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
    RuntimeResult,
)
from substrate.organism.runtime_supervisor import RuntimeSupervisor
from substrate.organism.store import OrganismStore


class FakeAdapter:
    def __init__(self, rid: str = "fake", output: str = "done") -> None:
        self._rid = rid
        self._output = output
        self._available = True
        self._call_count = 0

    @property
    def runtime_id(self) -> str:
        return self._rid

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.AI_CLI

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset({
            RuntimeCapability.REASON,
            RuntimeCapability.CODE_WRITE,
            RuntimeCapability.CODE_REVIEW,
            RuntimeCapability.RESEARCH,
            RuntimeCapability.SHELL,
            RuntimeCapability.CODE_EXECUTE,
        })

    def check_available(self) -> bool:
        return self._available

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        self._call_count += 1
        if not self._available:
            return None
        return RuntimeResult(output=self._output, runtime_id=self._rid, latency_ms=10)


def _make_graph(adapter: FakeAdapter | None = None) -> RuntimeGraph:
    graph = RuntimeGraph()
    adapter = adapter or FakeAdapter()
    graph.register(
        adapter.runtime_id,
        adapter.runtime_class,
        adapter.capabilities,
        cost=CostProfile(is_subscription=True),
        adapter=adapter,
    )
    graph.update_status(adapter.runtime_id, AvailabilityStatus.AVAILABLE)
    return graph


def _make_full_daemon(tmp_path, adapter: FakeAdapter | None = None) -> OrganismDaemon:
    adapter = adapter or FakeAdapter()
    graph = _make_graph(adapter)
    return OrganismDaemon(
        store_dir=str(tmp_path / "organism"),
        graph=graph,
    )


# ─── Capability inference ────────────────────────────────────────


class TestCapabilityInference:
    def test_build_keywords(self):
        assert _infer_capability("create a dashboard") == RuntimeCapability.CODE_WRITE
        assert _infer_capability("fix the login bug") == RuntimeCapability.CODE_WRITE
        assert _infer_capability("implement user auth") == RuntimeCapability.CODE_WRITE

    def test_research_keywords(self):
        assert _infer_capability("search for patterns") == RuntimeCapability.RESEARCH
        assert _infer_capability("audit the codebase") == RuntimeCapability.RESEARCH
        assert _infer_capability("investigate the crash") == RuntimeCapability.RESEARCH

    def test_review_keywords(self):
        assert _infer_capability("review the PR") == RuntimeCapability.CODE_REVIEW
        assert _infer_capability("check the imports") == RuntimeCapability.CODE_REVIEW
        assert _infer_capability("inspect the output") == RuntimeCapability.CODE_REVIEW

    def test_shell_keywords(self):
        assert _infer_capability("run the tests") == RuntimeCapability.SHELL
        assert _infer_capability("deploy to production") == RuntimeCapability.SHELL
        assert _infer_capability("execute the migration") == RuntimeCapability.SHELL

    def test_reason_keywords(self):
        assert _infer_capability("think about the architecture") == RuntimeCapability.REASON
        assert _infer_capability("plan the migration") == RuntimeCapability.REASON

    def test_gpu_keywords(self):
        assert _infer_capability("train the model") == RuntimeCapability.GPU_COMPUTE
        assert _infer_capability("render the video") == RuntimeCapability.GPU_COMPUTE

    def test_browser_keywords(self):
        assert _infer_capability("browse the documentation") == RuntimeCapability.BROWSER
        assert _infer_capability("scrape the website") == RuntimeCapability.BROWSER

    def test_unknown_defaults_to_reason(self):
        assert _infer_capability("hello world") == RuntimeCapability.REASON

    def test_first_keyword_wins(self):
        assert _infer_capability("build and then review it") == RuntimeCapability.CODE_WRITE

    def test_risk_class_mapping(self):
        assert _infer_risk_class(RuntimeCapability.CODE_WRITE) == "REVERSIBLE_WRITE"
        assert _infer_risk_class(RuntimeCapability.RESEARCH) == "READ_ONLY"
        assert _infer_risk_class(RuntimeCapability.SHELL) == "REVERSIBLE_WRITE"
        assert _infer_risk_class(RuntimeCapability.REASON) == "READ_ONLY"

    def test_capability_to_agent_mapping(self):
        assert _CAPABILITY_TO_AGENT[RuntimeCapability.CODE_WRITE] == "builder"
        assert _CAPABILITY_TO_AGENT[RuntimeCapability.RESEARCH] == "researcher"
        assert _CAPABILITY_TO_AGENT[RuntimeCapability.CODE_REVIEW] == "researcher"


# ─── Advisor + RuntimeGraph integration ──────────────────────────


class TestAdvisorGraphIntegration:
    def test_signal_routes_through_graph(self, tmp_path):
        adapter = FakeAdapter(output="graph result")
        graph = _make_graph(adapter)
        advisor = Advisor(
            store=OrganismStore(store_dir=tmp_path / "store"),
            graph=graph,
        )

        result = advisor.handle_signal("search for TODO comments")
        assert result["execution"] == "runtime_direct"
        assert result["runtime_id"] == "fake"
        assert "graph result" in result["output"]

    def test_signal_falls_back_to_agent_without_graph(self, tmp_path):
        advisor = Advisor(store=OrganismStore(store_dir=tmp_path / "store"))
        result = advisor.handle_signal("search for TODO comments")
        assert result["execution"] == "agent_dispatch"
        assert "delegated_to" in result

    def test_signal_falls_back_on_graph_failure(self, tmp_path):
        adapter = FakeAdapter()
        adapter._available = False
        graph = _make_graph(adapter)
        graph.update_status("fake", AvailabilityStatus.UNAVAILABLE)

        advisor = Advisor(
            store=OrganismStore(store_dir=tmp_path / "store"),
            graph=graph,
        )

        result = advisor.handle_signal("search for files")
        assert result["execution"] == "agent_dispatch"

    def test_signal_includes_capability(self, tmp_path):
        adapter = FakeAdapter()
        graph = _make_graph(adapter)
        advisor = Advisor(
            store=OrganismStore(store_dir=tmp_path / "store"),
            graph=graph,
        )

        result = advisor.handle_signal("build a dashboard")
        assert result["capability"] == "code_write"


# ─── Advisor + RuntimeSupervisor integration ─────────────────────


class TestAdvisorSupervisorIntegration:
    def test_supervisor_gets_heartbeat_on_success(self, tmp_path):
        adapter = FakeAdapter()
        graph = _make_graph(adapter)
        supervisor = RuntimeSupervisor(
            graph, state_dir=str(tmp_path / "supervisor")
        )
        supervisor.supervise("fake")

        advisor = Advisor(
            store=OrganismStore(store_dir=tmp_path / "store"),
            graph=graph,
            supervisor=supervisor,
        )

        advisor.handle_signal("search for files")
        sr = supervisor._supervised.get("fake")
        assert sr is not None
        assert sr.last_heartbeat > 0

    def test_health_check_in_autonomous_tick(self, tmp_path):
        adapter = FakeAdapter()
        graph = _make_graph(adapter)
        supervisor = RuntimeSupervisor(
            graph, state_dir=str(tmp_path / "supervisor")
        )
        supervisor.supervise("fake")

        advisor = Advisor(
            store=OrganismStore(store_dir=tmp_path / "store"),
            graph=graph,
            supervisor=supervisor,
        )

        result = advisor.autonomous_tick()
        assert result["tick"] == 1
        assert "system_mode" in result


# ─── Advisor + HomeostasisEngine integration ─────────────────────


class TestAdvisorHomeostasisIntegration:
    def test_homeostasis_records_executions(self, tmp_path):
        homeostasis = HomeostasisEngine()
        advisor = Advisor(
            store=OrganismStore(store_dir=tmp_path / "store"),
            homeostasis=homeostasis,
        )

        advisor.handle_signal("search for patterns")
        report = homeostasis.check()
        assert report.mode.value in {"healthy", "degraded", "protective", "critical"}

    def test_homeostasis_in_status(self, tmp_path):
        advisor = Advisor(store=OrganismStore(store_dir=tmp_path / "store"))
        status = advisor.organism_status()
        assert "homeostasis" in status
        assert "mode" in status["homeostasis"]


# ─── Autonomous tick ─────────────────────────────────────────────


class TestAutonomousTick:
    def test_tick_returns_report(self, tmp_path):
        advisor = Advisor(store=OrganismStore(store_dir=tmp_path / "store"))
        result = advisor.autonomous_tick()
        assert "tick" in result
        assert result["tick"] == 1
        assert "actions" in result
        assert "system_mode" in result
        assert "elapsed_ms" in result

    def test_tick_increments(self, tmp_path):
        advisor = Advisor(store=OrganismStore(store_dir=tmp_path / "store"))
        advisor.autonomous_tick()
        advisor.autonomous_tick()
        result = advisor.autonomous_tick()
        assert result["tick"] == 3

    def test_tick_drains_signal_queue(self, tmp_path):
        adapter = FakeAdapter()
        graph = _make_graph(adapter)
        advisor = Advisor(
            store=OrganismStore(store_dir=tmp_path / "store"),
            graph=graph,
        )

        advisor.queue_signal("search for files", priority=3)
        advisor.queue_signal("build a widget", priority=1)

        result = advisor.autonomous_tick()
        drained = [a for a in result["actions"] if a.get("type") == "signals_drained"]
        assert len(drained) == 1
        assert drained[0]["count"] == 2

    def test_tick_executes_ready_objectives(self, tmp_path):
        adapter = FakeAdapter()
        graph = _make_graph(adapter)
        coordinator = OrganismCoordinator(graph, state_dir=str(tmp_path / "coord"))
        advisor = Advisor(
            store=OrganismStore(store_dir=tmp_path / "store"),
            graph=graph,
            coordinator=coordinator,
        )

        coordinator.decompose("test", "do something")
        coordinator.assign_runtimes(coordinator.list_objectives()[0]["id"])

        result = advisor.autonomous_tick()
        executed = [a for a in result["actions"] if a.get("type") == "work_units_executed"]
        assert len(executed) == 1


# ─── Signal queue ────────────────────────────────────────────────


class TestSignalQueue:
    def test_queue_returns_id(self, tmp_path):
        advisor = Advisor(store=OrganismStore(store_dir=tmp_path / "store"))
        sig_id = advisor.queue_signal("test signal")
        assert sig_id.startswith("sig-")

    def test_queue_priority_ordering(self, tmp_path):
        advisor = Advisor(store=OrganismStore(store_dir=tmp_path / "store"))
        advisor.queue_signal("low priority", priority=9)
        advisor.queue_signal("high priority", priority=1)
        advisor.queue_signal("medium priority", priority=5)

        assert advisor._signal_queue[0]["priority"] == 1
        assert advisor._signal_queue[-1]["priority"] == 9


# ─── Resource topology ───────────────────────────────────────────


class TestResourceTopology:
    def test_topology_without_graph(self, tmp_path):
        advisor = Advisor(store=OrganismStore(store_dir=tmp_path / "store"))
        topo = advisor.resource_topology()
        assert topo["federation"]["total_runtimes"] == 0

    def test_topology_with_graph(self, tmp_path):
        adapter = FakeAdapter()
        graph = _make_graph(adapter)
        advisor = Advisor(
            store=OrganismStore(store_dir=tmp_path / "store"),
            graph=graph,
        )

        topo = advisor.resource_topology()
        assert topo["federation"]["total_runtimes"] == 1
        assert topo["federation"]["available"] == 1
        assert "fake" in topo["runtimes"]
        assert len(topo["capabilities_coverage"]) > 0

    def test_topology_with_supervisor(self, tmp_path):
        adapter = FakeAdapter()
        graph = _make_graph(adapter)
        supervisor = RuntimeSupervisor(
            graph, state_dir=str(tmp_path / "supervisor")
        )
        supervisor.supervise("fake")

        advisor = Advisor(
            store=OrganismStore(store_dir=tmp_path / "store"),
            graph=graph,
            supervisor=supervisor,
        )

        topo = advisor.resource_topology()
        assert topo["runtimes"]["fake"]["supervised"] is True


# ─── OrganismDaemon integration ──────────────────────────────────


class TestOrganismDaemonIntegration:
    def test_daemon_creates_all_subsystems(self, tmp_path):
        daemon = _make_full_daemon(tmp_path)
        assert daemon.graph is not None
        assert daemon.supervisor is not None
        assert daemon.homeostasis is not None
        assert daemon.advisor is not None

    def test_daemon_start_supervises_runtimes(self, tmp_path):
        daemon = _make_full_daemon(tmp_path)
        daemon.start()

        assert daemon.supervisor is not None
        sup_dict = daemon.supervisor.to_dict()
        assert sup_dict["supervised_count"] == 1

    def test_daemon_tick_produces_report(self, tmp_path):
        daemon = _make_full_daemon(tmp_path)
        daemon.start()
        result = daemon.tick()
        assert "cycle" in result
        assert "stages_executed" in result
        assert result["stages_executed"] >= 5
        assert result["cycle"] == 1

    def test_daemon_tick_increments(self, tmp_path):
        daemon = _make_full_daemon(tmp_path)
        daemon.start()
        daemon.tick()
        daemon.tick()
        assert daemon._tick_count == 2

    def test_daemon_stop_persists_state(self, tmp_path):
        daemon = _make_full_daemon(tmp_path)
        daemon.start()
        daemon.tick()
        daemon.stop()

        state_file = tmp_path / "organism" / "daemon_state.json"
        assert state_file.exists()

    def test_daemon_status_includes_subsystems(self, tmp_path):
        daemon = _make_full_daemon(tmp_path)
        daemon.start()

        status = daemon.status()
        assert status["running"] is True
        assert status["graph_available"] is True
        assert status["supervisor_available"] is True
        assert "tick_engine" in status
        assert "event_spine" in status
        assert "governor" in status
        assert "homeostasis" in status


# ─── OrganismObserver integration ────────────────────────────────


class TestObserverIntegration:
    def test_observer_snapshot_with_all_subsystems(self, tmp_path):
        adapter = FakeAdapter()
        graph = _make_graph(adapter)
        supervisor = RuntimeSupervisor(
            graph, state_dir=str(tmp_path / "supervisor")
        )
        supervisor.supervise("fake")
        coordinator = OrganismCoordinator(graph, state_dir=str(tmp_path / "coord"))
        homeostasis = HomeostasisEngine()

        observer = OrganismObserver(
            coordinator=coordinator,
            graph=graph,
            supervisor=supervisor,
            homeostasis=homeostasis,
        )

        snap = observer.snapshot()
        snap_dict = snap.to_dict()

        assert snap_dict["runtimes"]["total"] == 1
        assert "objectives" in snap_dict
        assert "supervision" in snap_dict
        assert "runtime_rankings" in snap_dict

    def test_observer_detects_no_runtimes_bottleneck(self, tmp_path):
        graph = RuntimeGraph()
        graph.register(
            "dead",
            RuntimeClass.AI_CLI,
            frozenset({RuntimeCapability.REASON}),
        )
        graph.update_status("dead", AvailabilityStatus.UNAVAILABLE)

        observer = OrganismObserver(graph=graph)
        snap = observer.snapshot()

        bottleneck_subs = [b.subsystem for b in snap.bottlenecks]
        assert "runtime_graph" in bottleneck_subs
