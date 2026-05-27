"""Tests for RuntimeSupervisor — lifecycle management, crash detection, recovery."""

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/anti-divergence-gate")

import time
import tempfile
import pytest
from typing import Any

from substrate.organism.runtime_graph import (
    AvailabilityStatus,
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
    RuntimeResult,
)
from substrate.organism.runtime_supervisor import (
    RuntimeSupervisor,
    SupervisedHealth,
    _HEARTBEAT_TIMEOUT_S,
    _HEARTBEAT_DEGRADED_S,
    _MAX_CRASHES_IN_WINDOW,
    _MAX_DAILY_RESTARTS,
)


class FakeAdapter:
    def __init__(self, available: bool = True) -> None:
        self._available = available

    @property
    def runtime_id(self) -> str:
        return "fake"

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.AI_CLI

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset({RuntimeCapability.REASON})

    def check_available(self) -> bool:
        return self._available

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        return RuntimeResult(output="ok", runtime_id="fake")


def _make_supervisor() -> tuple[RuntimeSupervisor, RuntimeGraph]:
    graph = RuntimeGraph()
    adapter = FakeAdapter(available=True)
    graph.register(
        "test-rt",
        RuntimeClass.AI_CLI,
        frozenset({RuntimeCapability.REASON}),
        adapter=adapter,
    )
    supervisor = RuntimeSupervisor(graph, state_dir=tempfile.mkdtemp())
    return supervisor, graph


class TestSupervise:
    def test_supervise_available_runtime(self):
        supervisor, _ = _make_supervisor()
        sr = supervisor.supervise("test-rt")
        assert sr.health == SupervisedHealth.ALIVE
        assert sr.last_heartbeat > 0

    def test_supervise_unavailable_runtime(self):
        graph = RuntimeGraph()
        adapter = FakeAdapter(available=False)
        graph.register("down", RuntimeClass.AI_CLI, frozenset(), adapter=adapter)
        supervisor = RuntimeSupervisor(graph, state_dir=tempfile.mkdtemp())

        sr = supervisor.supervise("down")
        assert sr.health == SupervisedHealth.STOPPED

    def test_supervise_idempotent(self):
        supervisor, _ = _make_supervisor()
        sr1 = supervisor.supervise("test-rt")
        sr2 = supervisor.supervise("test-rt")
        assert sr1 is sr2


class TestHeartbeat:
    def test_heartbeat_keeps_alive(self):
        supervisor, _ = _make_supervisor()
        supervisor.supervise("test-rt")
        supervisor.heartbeat("test-rt")
        health = supervisor.check_health("test-rt")
        assert health == SupervisedHealth.ALIVE

    def test_stale_heartbeat_degrades(self):
        supervisor, _ = _make_supervisor()
        sr = supervisor.supervise("test-rt")
        sr.last_heartbeat = time.time() - _HEARTBEAT_DEGRADED_S - 1
        health = supervisor.check_health("test-rt")
        assert health == SupervisedHealth.DEGRADED

    def test_very_stale_heartbeat_dies(self):
        supervisor, _ = _make_supervisor()
        sr = supervisor.supervise("test-rt")
        sr.last_heartbeat = time.time() - _HEARTBEAT_TIMEOUT_S - 1
        health = supervisor.check_health("test-rt")
        assert health == SupervisedHealth.DEAD

    def test_heartbeat_recovers_dead(self):
        supervisor, graph = _make_supervisor()
        sr = supervisor.supervise("test-rt")
        sr.health = SupervisedHealth.DEAD
        supervisor.heartbeat("test-rt")
        assert sr.health == SupervisedHealth.ALIVE
        node = graph.get("test-rt")
        assert node is not None
        assert node.status == AvailabilityStatus.AVAILABLE


class TestCrashDetection:
    def test_record_crash(self):
        supervisor, graph = _make_supervisor()
        supervisor.supervise("test-rt")
        supervisor.record_crash("test-rt", "segfault")

        sr = supervisor._supervised["test-rt"]
        assert sr.health == SupervisedHealth.DEAD
        assert len(sr.crashes) == 1
        assert sr.generation == 1

        node = graph.get("test-rt")
        assert node is not None
        assert node.status == AvailabilityStatus.UNAVAILABLE

    def test_crash_loop_detection(self):
        supervisor, _ = _make_supervisor()
        supervisor.supervise("test-rt")

        for i in range(_MAX_CRASHES_IN_WINDOW):
            supervisor.record_crash("test-rt", f"crash {i}")
            if i < _MAX_CRASHES_IN_WINDOW - 1:
                supervisor.mark_restarting("test-rt")

        should, reason = supervisor.should_restart("test-rt")
        assert not should
        assert "crash_loop_detected" in reason

    def test_daily_budget_exhaustion(self):
        supervisor, _ = _make_supervisor()
        sr = supervisor.supervise("test-rt")
        sr.health = SupervisedHealth.DEAD
        sr.daily_restart_count = _MAX_DAILY_RESTARTS
        sr.daily_reset_at = time.time()

        should, reason = supervisor.should_restart("test-rt")
        assert not should
        assert "daily_budget_exhausted" in reason


class TestRecovery:
    def test_should_restart_dead(self):
        supervisor, _ = _make_supervisor()
        sr = supervisor.supervise("test-rt")
        sr.health = SupervisedHealth.DEAD
        should, reason = supervisor.should_restart("test-rt")
        assert should
        assert "restart_allowed" in reason

    def test_should_not_restart_alive(self):
        supervisor, _ = _make_supervisor()
        supervisor.supervise("test-rt")
        should, reason = supervisor.should_restart("test-rt")
        assert not should
        assert "alive" in reason

    def test_mark_restarting(self):
        supervisor, graph = _make_supervisor()
        sr = supervisor.supervise("test-rt")
        sr.health = SupervisedHealth.DEAD
        supervisor.mark_restarting("test-rt")

        assert sr.health == SupervisedHealth.RECOVERING
        assert sr.restart_count == 1
        assert sr.daily_restart_count == 1

        node = graph.get("test-rt")
        assert node is not None
        assert node.status == AvailabilityStatus.STARTING

    def test_backoff_increases(self):
        supervisor, _ = _make_supervisor()
        sr = supervisor.supervise("test-rt")
        sr.restart_count = 0
        b0 = sr.backoff_seconds
        sr.restart_count = 3
        b3 = sr.backoff_seconds
        assert b3 > b0

    def test_backoff_capped(self):
        supervisor, _ = _make_supervisor()
        sr = supervisor.supervise("test-rt")
        sr.restart_count = 100
        assert sr.backoff_seconds <= 300.0

    def test_backoff_blocks_restart(self):
        supervisor, _ = _make_supervisor()
        sr = supervisor.supervise("test-rt")
        sr.health = SupervisedHealth.DEAD
        sr.last_restart_at = time.time()
        sr.restart_count = 1

        should, reason = supervisor.should_restart("test-rt")
        assert not should
        assert "backoff_active" in reason

    def test_get_recovery_plan(self):
        supervisor, _ = _make_supervisor()
        sr = supervisor.supervise("test-rt")
        sr.health = SupervisedHealth.DEAD
        plan = supervisor.get_recovery_plan()
        assert len(plan) == 1
        assert plan[0]["runtime_id"] == "test-rt"
        assert plan[0]["should_restart"]


class TestCheckAll:
    def test_check_all(self):
        supervisor, _ = _make_supervisor()
        supervisor.supervise("test-rt")
        results = supervisor.check_all()
        assert "test-rt" in results
        assert results["test-rt"] == SupervisedHealth.ALIVE


class TestPersistence:
    def test_persist_state(self):
        supervisor, _ = _make_supervisor()
        supervisor.supervise("test-rt")
        supervisor.persist_state()
        state_path = supervisor._state_dir / "supervisor_state.json"
        assert state_path.exists()

    def test_to_dict(self):
        supervisor, _ = _make_supervisor()
        supervisor.supervise("test-rt")
        d = supervisor.to_dict()
        assert d["supervised_count"] == 1
        assert d["alive"] == 1
        assert "test-rt" in d["runtimes"]
