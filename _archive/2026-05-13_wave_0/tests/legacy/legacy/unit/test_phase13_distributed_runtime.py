"""Phase 13 — Distributed Runtime + Remote Node Heartbeats + Resilient Routing.

Tests: heartbeat protocol, health state machine, remote execution abstraction,
failover routing, runtime loop integration, boundary checks, regression.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/opt/OS")

from umh.environments.telemetry import NodeTelemetry
from umh.nodes.failover import FailoverPolicy, FailoverRouter
from umh.nodes.health import NodeHealthManager, NodeHealthState
from umh.nodes.heartbeat import HeartbeatMonitor, HeartbeatStatus, NodeHeartbeat
from umh.nodes.registry import DeviceNode, DeviceType
from umh.nodes.remote import (
    MockRemoteNodeClient,
    RemoteExecutionRecord,
    RemoteExecutionStatus,
    RemoteNodeClient,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _past_iso(seconds: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


def _make_node(node_id: str, dtype: DeviceType = DeviceType.LOCAL) -> DeviceNode:
    return DeviceNode(node_id=node_id, device_type=dtype, hostname=f"{node_id}.local")


def _make_heartbeat(
    node_id: str,
    status: HeartbeatStatus = HeartbeatStatus.OK,
    timestamp: str | None = None,
    **telemetry_kw: float,
) -> NodeHeartbeat:
    return NodeHeartbeat(
        node_id=node_id,
        timestamp=timestamp or _now_iso(),
        status=status,
        telemetry=telemetry_kw,
    )


# ─── Heartbeat tests ──────────────────────────────────────────────────


class TestHeartbeatMonitor:
    def test_record_and_retrieve(self):
        mon = HeartbeatMonitor()
        hb = _make_heartbeat("n1")
        mon.record_heartbeat(hb)
        assert mon.get_last_heartbeat("n1") is hb

    def test_fresh_heartbeat_not_stale(self):
        mon = HeartbeatMonitor()
        mon.record_heartbeat(_make_heartbeat("n1"))
        assert not mon.is_stale("n1")

    def test_stale_heartbeat_detected(self):
        mon = HeartbeatMonitor(stale_threshold_s=30)
        hb = _make_heartbeat("n1", timestamp=_past_iso(60))
        mon.record_heartbeat(hb)
        assert mon.is_stale("n1")

    def test_missing_heartbeat_is_stale(self):
        mon = HeartbeatMonitor()
        assert mon.is_stale("nonexistent")

    def test_missing_heartbeat_status_unknown(self):
        mon = HeartbeatMonitor()
        assert mon.node_status("nonexistent") == HeartbeatStatus.UNKNOWN

    def test_deterministic_time_injection(self):
        mon = HeartbeatMonitor(stale_threshold_s=30)
        ts = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        hb = _make_heartbeat("n1", timestamp=ts.isoformat())
        mon.record_heartbeat(hb)
        check_at = ts + timedelta(seconds=10)
        assert not mon.is_stale("n1", now=check_at)
        check_at_stale = ts + timedelta(seconds=60)
        assert mon.is_stale("n1", now=check_at_stale)

    def test_stale_node_status_offline(self):
        mon = HeartbeatMonitor(stale_threshold_s=30)
        hb = _make_heartbeat("n1", timestamp=_past_iso(60))
        mon.record_heartbeat(hb)
        assert mon.node_status("n1") == HeartbeatStatus.OFFLINE

    def test_degraded_heartbeat_status(self):
        mon = HeartbeatMonitor()
        hb = _make_heartbeat("n1", status=HeartbeatStatus.DEGRADED)
        mon.record_heartbeat(hb)
        assert mon.node_status("n1") == HeartbeatStatus.DEGRADED

    def test_list_stale_nodes(self):
        mon = HeartbeatMonitor(stale_threshold_s=30)
        mon.record_heartbeat(_make_heartbeat("fresh"))
        mon.record_heartbeat(_make_heartbeat("stale", timestamp=_past_iso(60)))
        stale = mon.list_stale_nodes()
        assert "stale" in stale
        assert "fresh" not in stale

    def test_list_all_nodes(self):
        mon = HeartbeatMonitor()
        mon.record_heartbeat(_make_heartbeat("a"))
        mon.record_heartbeat(_make_heartbeat("b"))
        assert sorted(mon.list_all_nodes()) == ["a", "b"]


# ─── Health state machine tests ──────────────────────────────────────


class TestNodeHealthManager:
    def test_ok_heartbeat_becomes_healthy(self):
        mgr = NodeHealthManager()
        hb = _make_heartbeat("n1")
        state = mgr.update_from_heartbeat(hb)
        assert state == NodeHealthState.HEALTHY

    def test_degraded_heartbeat_becomes_degraded(self):
        mgr = NodeHealthManager()
        hb = _make_heartbeat("n1", status=HeartbeatStatus.DEGRADED)
        state = mgr.update_from_heartbeat(hb)
        assert state == NodeHealthState.DEGRADED

    def test_high_load_becomes_degraded(self):
        mgr = NodeHealthManager()
        hb = _make_heartbeat("n1", cpu_percent=95.0, memory_percent=90.0)
        state = mgr.update_from_heartbeat(hb)
        assert state == NodeHealthState.DEGRADED

    def test_offline_heartbeat_becomes_offline(self):
        mgr = NodeHealthManager()
        hb = _make_heartbeat("n1", status=HeartbeatStatus.OFFLINE)
        state = mgr.update_from_heartbeat(hb)
        assert state == NodeHealthState.OFFLINE

    def test_mark_failure_increments_count(self):
        mgr = NodeHealthManager()
        mgr.mark_failure("n1", "test failure")
        mgr.mark_failure("n1", "another failure")
        health = mgr.get_health("n1")
        assert health is not None
        assert health.failure_count == 2
        assert health.state == NodeHealthState.OFFLINE

    def test_recovery_from_offline(self):
        mgr = NodeHealthManager()
        mgr.mark_failure("n1", "went down")
        hb = _make_heartbeat("n1")
        state = mgr.update_from_heartbeat(hb)
        assert state == NodeHealthState.RECOVERING

    def test_full_recovery_cycle(self):
        mgr = NodeHealthManager()
        mgr.mark_failure("n1", "went down")
        mgr.update_from_heartbeat(_make_heartbeat("n1"))
        state = mgr.update_from_heartbeat(_make_heartbeat("n1"))
        assert state == NodeHealthState.HEALTHY

    def test_list_healthy(self):
        mgr = NodeHealthManager()
        mgr.update_from_heartbeat(_make_heartbeat("good"))
        mgr.mark_failure("bad", "down")
        healthy = mgr.list_healthy()
        assert len(healthy) == 1
        assert healthy[0].node_id == "good"

    def test_list_available_includes_degraded(self):
        mgr = NodeHealthManager()
        mgr.update_from_heartbeat(_make_heartbeat("good"))
        mgr.update_from_heartbeat(_make_heartbeat("slow", status=HeartbeatStatus.DEGRADED))
        mgr.mark_failure("dead", "offline")
        available = mgr.list_available()
        ids = {h.node_id for h in available}
        assert ids == {"good", "slow"}

    def test_mark_stale_transitions_to_offline(self):
        mgr = NodeHealthManager()
        mgr.update_from_heartbeat(_make_heartbeat("n1"))
        assert mgr.get_health("n1").state == NodeHealthState.HEALTHY
        mgr.mark_stale("n1")
        assert mgr.get_health("n1").state == NodeHealthState.OFFLINE


# ─── Remote execution tests ─────────────────────────────────────────


class TestRemoteExecution:
    def test_mock_implements_protocol(self):
        client = MockRemoteNodeClient()
        assert isinstance(client, RemoteNodeClient)

    def test_mock_ping_reachable(self):
        client = MockRemoteNodeClient(reachable=True)
        node = _make_node("n1")
        assert client.ping(node) is True

    def test_mock_submit_accepted(self):
        client = MockRemoteNodeClient()
        node = _make_node("n1")
        record = client.submit_execution(node, {"task_id": "t1"})
        assert record.status == RemoteExecutionStatus.ACCEPTED
        assert record.task_id == "t1"

    def test_mock_fetch_result(self):
        client = MockRemoteNodeClient()
        node = _make_node("n1")
        client.submit_execution(node, {"task_id": "t1"})
        client.complete_task("t1", {"output": "done"})
        result = client.fetch_result(node, "t1")
        assert result is not None
        assert result.status == RemoteExecutionStatus.SUCCEEDED
        assert result.result == {"output": "done"}

    def test_unreachable_node_returns_controlled_failure(self):
        client = MockRemoteNodeClient(reachable=False)
        node = _make_node("n1")
        record = client.submit_execution(node, {"task_id": "t1"})
        assert record.status == RemoteExecutionStatus.UNREACHABLE

    def test_cancel_works(self):
        client = MockRemoteNodeClient()
        node = _make_node("n1")
        client.submit_execution(node, {"task_id": "t1"})
        assert client.cancel(node, "t1") is True
        result = client.fetch_result(node, "t1")
        assert result.status == RemoteExecutionStatus.CANCELLED

    def test_cancel_unreachable_returns_false(self):
        client = MockRemoteNodeClient(reachable=False)
        node = _make_node("n1")
        assert client.cancel(node, "t1") is False

    def test_execution_record_serialization(self):
        record = RemoteExecutionRecord(
            task_id="t1",
            node_id="n1",
            status=RemoteExecutionStatus.SUCCEEDED,
            result={"output": "ok"},
        )
        d = record.to_dict()
        assert d["task_id"] == "t1"
        assert d["status"] == "succeeded"


# ─── Failover routing tests ─────────────────────────────────────────


class TestFailoverRouting:
    def test_healthy_local_preferred(self):
        health_mgr = NodeHealthManager()
        health_mgr.update_from_heartbeat(_make_heartbeat("local1"))
        health_mgr.update_from_heartbeat(_make_heartbeat("vps1"))

        router = FailoverRouter(health_manager=health_mgr)
        local = _make_node("local1", DeviceType.LOCAL)
        vps = _make_node("vps1", DeviceType.VPS)

        chosen = router.choose_initial_node([local, vps])
        assert chosen is not None
        assert chosen.node_id == "local1"

    def test_offline_local_falls_back_to_vps(self):
        health_mgr = NodeHealthManager()
        health_mgr.mark_failure("local1", "down")
        health_mgr.update_from_heartbeat(_make_heartbeat("vps1"))

        router = FailoverRouter(health_manager=health_mgr)
        local = _make_node("local1", DeviceType.LOCAL)
        vps = _make_node("vps1", DeviceType.VPS)

        chosen = router.choose_initial_node([local, vps])
        assert chosen is not None
        assert chosen.node_id == "vps1"

    def test_degraded_avoided_when_policy_says_so(self):
        health_mgr = NodeHealthManager()
        health_mgr.update_from_heartbeat(_make_heartbeat("n1", status=HeartbeatStatus.DEGRADED))
        health_mgr.update_from_heartbeat(_make_heartbeat("n2"))

        policy = FailoverPolicy(avoid_degraded_nodes=True)
        router = FailoverRouter(health_manager=health_mgr, policy=policy)
        n1 = _make_node("n1", DeviceType.LOCAL)
        n2 = _make_node("n2", DeviceType.LOCAL)

        chosen = router.choose_initial_node([n1, n2])
        assert chosen is not None
        assert chosen.node_id == "n2"

    def test_degraded_allowed_by_default(self):
        health_mgr = NodeHealthManager()
        health_mgr.update_from_heartbeat(_make_heartbeat("n1", status=HeartbeatStatus.DEGRADED))

        router = FailoverRouter(health_manager=health_mgr)
        n1 = _make_node("n1", DeviceType.LOCAL)
        chosen = router.choose_initial_node([n1])
        assert chosen is not None

    def test_deterministic_tiebreak(self):
        health_mgr = NodeHealthManager()
        health_mgr.update_from_heartbeat(_make_heartbeat("b"))
        health_mgr.update_from_heartbeat(_make_heartbeat("a"))

        router = FailoverRouter(health_manager=health_mgr)
        nodes = [_make_node("b", DeviceType.VPS), _make_node("a", DeviceType.VPS)]
        chosen = router.choose_initial_node(nodes, prefer_local=False)
        assert chosen is not None
        assert chosen.node_id == "a"

    def test_no_available_nodes_returns_none(self):
        health_mgr = NodeHealthManager()
        health_mgr.mark_failure("n1", "down")

        policy = FailoverPolicy(allow_vps_fallback=False, allow_local_fallback=False)
        router = FailoverRouter(health_manager=health_mgr, policy=policy)
        n1 = _make_node("n1", DeviceType.LOCAL)

        assert router.choose_initial_node([n1]) is None

    def test_fallback_excludes_failed_node(self):
        health_mgr = NodeHealthManager()
        health_mgr.update_from_heartbeat(_make_heartbeat("n1"))
        health_mgr.update_from_heartbeat(_make_heartbeat("n2"))

        router = FailoverRouter(health_manager=health_mgr)
        n1 = _make_node("n1", DeviceType.LOCAL)
        n2 = _make_node("n2", DeviceType.VPS)

        fallback = router.choose_fallback_node("n1", [n1, n2])
        assert fallback is not None
        assert fallback.node_id == "n2"

    def test_record_failure_and_success(self):
        router = FailoverRouter()
        router.record_failure("n1", "timeout")
        router.record_success("n1")
        stats = router.get_stats("n1")
        assert stats["failures"] == 1
        assert stats["successes"] == 1


# ─── Runtime loop integration tests ─────────────────────────────────


class TestRuntimeLoopNodeIntegration:
    def test_tick_does_not_crash_with_offline_node(self):
        from umh.runtime.loop import RuntimeLoop

        health_mgr = NodeHealthManager()
        hb_mon = HeartbeatMonitor(stale_threshold_s=30)
        hb_mon.record_heartbeat(_make_heartbeat("n1", timestamp=_past_iso(60)))

        loop = RuntimeLoop(
            heartbeat_monitor=hb_mon,
            health_manager=health_mgr,
        )
        loop.start()
        try:
            result = loop.tick()
            assert "error" not in result
        finally:
            loop.stop()

    def test_stale_node_marked_offline_during_tick(self):
        from umh.runtime.loop import RuntimeLoop

        health_mgr = NodeHealthManager()
        health_mgr.update_from_heartbeat(_make_heartbeat("n1"))

        hb_mon = HeartbeatMonitor(stale_threshold_s=30)
        hb_mon.record_heartbeat(_make_heartbeat("n1", timestamp=_past_iso(60)))

        loop = RuntimeLoop(
            heartbeat_monitor=hb_mon,
            health_manager=health_mgr,
        )
        loop.start()
        try:
            result = loop.tick()
            assert "node_updates" in result
            assert any(u["node_id"] == "n1" for u in result["node_updates"])
            health = health_mgr.get_health("n1")
            assert health.state == NodeHealthState.OFFLINE
        finally:
            loop.stop()

    def test_recovered_heartbeat_updates_state(self):
        health_mgr = NodeHealthManager()
        health_mgr.mark_failure("n1", "was down")
        hb = _make_heartbeat("n1")
        state = health_mgr.update_from_heartbeat(hb)
        assert state == NodeHealthState.RECOVERING

    def test_loop_without_health_works_as_before(self):
        from umh.runtime.loop import RuntimeLoop

        loop = RuntimeLoop()
        loop.start()
        try:
            result = loop.tick()
            assert "error" not in result
            assert "node_updates" not in result
        finally:
            loop.stop()

    def test_advisor_and_loop_cannot_execute(self):
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.loop import RuntimeLoop

        advisor = AdvisorRuntime()
        loop = RuntimeLoop(advisor=advisor)
        assert not hasattr(advisor, "execute")
        assert not hasattr(advisor, "run_task")
        assert not hasattr(loop, "execute")
        assert not hasattr(loop, "run_task")


# ─── Boundary tests ─────────────────────────────────────────────────


class TestBoundaryInvariants:
    def test_cells_do_not_import_nodes(self):
        import importlib
        import inspect

        mod = importlib.import_module("umh.cells.models")
        src = inspect.getsource(mod)
        assert "from umh.nodes" not in src
        assert "import umh.nodes" not in src

    def test_cells_do_not_import_environments(self):
        import importlib
        import inspect

        mod = importlib.import_module("umh.cells.models")
        src = inspect.getsource(mod)
        assert "from umh.environments" not in src
        assert "import umh.environments" not in src

    def test_nodes_do_not_import_cells(self):
        import importlib
        import inspect

        for name in [
            "umh.nodes.heartbeat",
            "umh.nodes.health",
            "umh.nodes.remote",
            "umh.nodes.failover",
        ]:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            assert "from umh.cells" not in src, f"{name} imports cells"
            assert "import umh.cells" not in src, f"{name} imports cells"

    def test_nodes_do_not_import_adapters(self):
        import importlib
        import inspect

        for name in [
            "umh.nodes.heartbeat",
            "umh.nodes.health",
            "umh.nodes.remote",
            "umh.nodes.failover",
        ]:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            assert "from umh.adapters" not in src, f"{name} imports adapters"
            assert "import umh.adapters" not in src, f"{name} imports adapters"

    def test_no_subprocess_in_nodes(self):
        import importlib
        import inspect

        for name in [
            "umh.nodes.heartbeat",
            "umh.nodes.health",
            "umh.nodes.remote",
            "umh.nodes.failover",
            "umh.nodes.registry",
            "umh.nodes.routing",
        ]:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            assert "import subprocess" not in src, f"{name} imports subprocess"
            assert "import docker" not in src, f"{name} imports docker"

    def test_no_shell_true_outside_environment(self):
        import importlib
        import inspect

        for name in [
            "umh.nodes.heartbeat",
            "umh.nodes.health",
            "umh.nodes.remote",
            "umh.nodes.failover",
            "umh.runtime.loop",
            "umh.runtime.advisor",
        ]:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            assert "shell=True" not in src, f"{name} contains shell=True"

    def test_runtime_loop_does_not_import_environments(self):
        import importlib
        import inspect

        mod = importlib.import_module("umh.runtime.loop")
        src = inspect.getsource(mod)
        assert "from umh.environments" not in src
        assert "import umh.environments" not in src

    def test_advisor_does_not_import_environments(self):
        import importlib
        import inspect

        mod = importlib.import_module("umh.runtime.advisor")
        src = inspect.getsource(mod)
        assert "from umh.environments" not in src
        assert "import umh.environments" not in src

    def test_nodes_do_not_import_runtime(self):
        import importlib
        import inspect

        for name in [
            "umh.nodes.heartbeat",
            "umh.nodes.health",
            "umh.nodes.remote",
            "umh.nodes.failover",
        ]:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            assert "from umh.runtime" not in src, f"{name} imports runtime"
            assert "import umh.runtime" not in src, f"{name} imports runtime"


# ─── Regression tests ────────────────────────────────────────────────


class TestPhase13Regression:
    def test_heartbeat_to_dict(self):
        hb = _make_heartbeat("n1", cpu_percent=50.0)
        d = hb.to_dict()
        assert d["node_id"] == "n1"
        assert d["status"] == "ok"

    def test_health_to_dict(self):
        from umh.nodes.health import NodeHealth

        h = NodeHealth(node_id="n1", state=NodeHealthState.HEALTHY)
        d = h.to_dict()
        assert d["state"] == "healthy"

    def test_failover_policy_to_dict(self):
        policy = FailoverPolicy(max_attempts=5)
        d = policy.to_dict()
        assert d["max_attempts"] == 5

    def test_remote_record_to_dict(self):
        record = RemoteExecutionRecord(
            task_id="t1", node_id="n1", status=RemoteExecutionStatus.ACCEPTED
        )
        d = record.to_dict()
        assert d["status"] == "accepted"

    def test_import_phase13_package(self):
        from umh.nodes import (
            FailoverPolicy,
            FailoverRouter,
            HeartbeatMonitor,
            MockRemoteNodeClient,
            NodeHealthManager,
            NodeHealthState,
        )

        assert FailoverRouter is not None
        assert HeartbeatMonitor is not None
        assert NodeHealthManager is not None
        assert MockRemoteNodeClient is not None
