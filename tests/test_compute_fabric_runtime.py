"""Tests for W1 — Unified Compute Fabric Runtime.

Covers: node aggregation, health computation, routing decisions,
registration, heartbeat, active execution tracking, capacity math.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.compute_fabric_runtime import (
    ComputeFabricRuntime,
    ComputeNode,
    ComputeNodeHealth,
    ComputeNodeType,
    RoutingDecision,
    _compute_health,
    _infer_node_type,
    _HEARTBEAT_DEGRADED_SECONDS,
    _HEARTBEAT_HEALTHY_SECONDS,
)
from substrate.organism.device_role_registry import (
    DeviceCapability,
    DeviceNodeProfile,
    DeviceRole,
)
from substrate.organism.worker_registry import WorkerInstance, WorkerRegistry, WorkerStatus
from substrate.organism.device_capacity import DeviceCapacityModel


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _make_vps_profile() -> DeviceNodeProfile:
    return DeviceNodeProfile(
        node_id="dn-vps-001",
        device_name="VPS Control Plane",
        role=DeviceRole.CONTROL_PLANE,
        os="linux",
        location="vps",
        trust_level="full",
        online_status="online",
        capabilities=[
            DeviceCapability.CPU_LIGHT,
            DeviceCapability.CODE_EXECUTION,
            DeviceCapability.FILE_ACCESS,
            DeviceCapability.NETWORK_ACCESS,
            DeviceCapability.CANONICAL_STATE,
        ],
    )


def _make_beast_profile() -> DeviceNodeProfile:
    return DeviceNodeProfile(
        node_id="dn-beast-001",
        device_name="Windows Beast",
        role=DeviceRole.HEAVY_WORKSTATION,
        os="windows",
        location="home",
        trust_level="full",
        online_status="online",
        capabilities=[
            DeviceCapability.CPU_HEAVY,
            DeviceCapability.GPU_AVAILABLE,
            DeviceCapability.BROWSER_AUTOMATION,
            DeviceCapability.CODE_EXECUTION,
            DeviceCapability.MEDIA_GENERATION,
            DeviceCapability.LOCAL_MODELS,
        ],
    )


def _make_offline_profile() -> DeviceNodeProfile:
    return DeviceNodeProfile(
        node_id="dn-offline-001",
        device_name="Offline Node",
        role=DeviceRole.HEAVY_WORKSTATION,
        os="windows",
        location="home",
        trust_level="full",
        online_status="offline",
        capabilities=[DeviceCapability.GPU_AVAILABLE],
    )


class MockDistributedRuntime:
    """Minimal mock of DistributedRuntime for testing ComputeFabricRuntime."""

    def __init__(
        self,
        profiles: list[DeviceNodeProfile] | None = None,
        worker_registry: WorkerRegistry | None = None,
    ) -> None:
        profs = profiles or [_make_vps_profile(), _make_beast_profile()]
        self._profiles = {p.node_id: p for p in profs}
        self._worker_registry = worker_registry or WorkerRegistry()
        self._capacity_model = DeviceCapacityModel(
            self._worker_registry, profs
        )


def _make_fabric(
    profiles: list[DeviceNodeProfile] | None = None,
    worker_registry: WorkerRegistry | None = None,
) -> ComputeFabricRuntime:
    dr = MockDistributedRuntime(profiles=profiles, worker_registry=worker_registry)
    return ComputeFabricRuntime(dr)


# ── Node Type Inference Tests ────────────────────────────────────────────────


class TestNodeTypeInference:
    def test_control_plane_maps_to_vps(self) -> None:
        assert _infer_node_type("control_plane", "linux", "vps") == ComputeNodeType.VPS

    def test_heavy_workstation_maps_to_windows(self) -> None:
        assert _infer_node_type("heavy_workstation", "windows", "home") == ComputeNodeType.WINDOWS

    def test_cockpit_ui_maps_to_container(self) -> None:
        assert _infer_node_type("cockpit_ui", "linux", "cloud") == ComputeNodeType.CONTAINER

    def test_windows_os_maps_to_windows(self) -> None:
        assert _infer_node_type("unknown", "windows", "home") == ComputeNodeType.WINDOWS

    def test_linux_os_maps_to_vps(self) -> None:
        assert _infer_node_type("unknown", "linux", "vps") == ComputeNodeType.VPS

    def test_cloud_location_maps_to_container(self) -> None:
        assert _infer_node_type("unknown", "other", "cloud") == ComputeNodeType.CONTAINER

    def test_unknown_defaults_to_vps(self) -> None:
        assert _infer_node_type("unknown", "other", "other") == ComputeNodeType.VPS


# ── Health Computation Tests ─────────────────────────────────────────────────


class TestHealthComputation:
    def test_offline_is_unreachable(self) -> None:
        assert _compute_health(time.time(), "offline", time.time()) == ComputeNodeHealth.UNREACHABLE

    def test_no_heartbeat_online_is_healthy(self) -> None:
        assert _compute_health(0, "online", time.time()) == ComputeNodeHealth.HEALTHY

    def test_no_heartbeat_unknown_is_unknown(self) -> None:
        assert _compute_health(0, "unknown", time.time()) == ComputeNodeHealth.UNKNOWN

    def test_fresh_heartbeat_is_healthy(self) -> None:
        now = time.time()
        assert _compute_health(now - 10, "online", now) == ComputeNodeHealth.HEALTHY

    def test_stale_heartbeat_is_degraded(self) -> None:
        now = time.time()
        hb = now - (_HEARTBEAT_HEALTHY_SECONDS + 10)
        assert _compute_health(hb, "online", now) == ComputeNodeHealth.DEGRADED

    def test_very_stale_heartbeat_is_unreachable(self) -> None:
        now = time.time()
        hb = now - (_HEARTBEAT_DEGRADED_SECONDS + 10)
        assert _compute_health(hb, "online", now) == ComputeNodeHealth.UNREACHABLE

    def test_heartbeat_boundary_healthy(self) -> None:
        now = time.time()
        hb = now - _HEARTBEAT_HEALTHY_SECONDS
        assert _compute_health(hb, "online", now) == ComputeNodeHealth.HEALTHY

    def test_heartbeat_boundary_degraded(self) -> None:
        now = time.time()
        hb = now - _HEARTBEAT_DEGRADED_SECONDS
        assert _compute_health(hb, "online", now) == ComputeNodeHealth.DEGRADED


# ── Node Aggregation Tests ───────────────────────────────────────────────────


class TestNodeAggregation:
    def test_nodes_returns_all_profiles(self) -> None:
        fabric = _make_fabric()
        nodes = fabric.nodes()
        assert len(nodes) == 2
        ids = {n.node_id for n in nodes}
        assert "dn-vps-001" in ids
        assert "dn-beast-001" in ids

    def test_node_types_inferred_correctly(self) -> None:
        fabric = _make_fabric()
        nodes = {n.node_id: n for n in fabric.nodes()}
        assert nodes["dn-vps-001"].node_type == ComputeNodeType.VPS
        assert nodes["dn-beast-001"].node_type == ComputeNodeType.WINDOWS

    def test_node_capabilities_populated(self) -> None:
        fabric = _make_fabric()
        nodes = {n.node_id: n for n in fabric.nodes()}
        assert "code_execution" in nodes["dn-vps-001"].capabilities
        assert "gpu_available" in nodes["dn-beast-001"].capabilities

    def test_node_display_name_from_profile(self) -> None:
        fabric = _make_fabric()
        nodes = {n.node_id: n for n in fabric.nodes()}
        assert nodes["dn-vps-001"].display_name == "VPS Control Plane"
        assert nodes["dn-beast-001"].display_name == "Windows Beast"

    def test_offline_node_unreachable(self) -> None:
        fabric = _make_fabric(profiles=[_make_vps_profile(), _make_offline_profile()])
        nodes = {n.node_id: n for n in fabric.nodes()}
        assert nodes["dn-offline-001"].health == ComputeNodeHealth.UNREACHABLE

    def test_to_dict_has_all_fields(self) -> None:
        fabric = _make_fabric()
        nodes = fabric.nodes()
        d = nodes[0].to_dict()
        expected_keys = {
            "node_id", "node_type", "health", "display_name", "capabilities",
            "active_workers", "max_workers", "active_executions",
            "last_heartbeat", "utilization", "metadata",
        }
        assert expected_keys.issubset(d.keys())


# ── Worker Tracking Tests ────────────────────────────────────────────────────


class TestWorkerTracking:
    def test_active_workers_count(self) -> None:
        wr = WorkerRegistry()
        wr.register("w1", "dn-vps-001", "rt-1", capabilities=["code_execution"])
        wr.register("w2", "dn-vps-001", "rt-1", capabilities=["code_execution"])
        fabric = _make_fabric(worker_registry=wr)
        nodes = {n.node_id: n for n in fabric.nodes()}
        assert nodes["dn-vps-001"].active_workers == 2
        assert nodes["dn-beast-001"].active_workers == 0

    def test_active_executions_tracked(self) -> None:
        wr = WorkerRegistry()
        w = wr.register("w1", "dn-vps-001", "rt-1")
        wr.update_status("w1", WorkerStatus.WORKING)
        w.current_task_id = "task-abc"
        fabric = _make_fabric(worker_registry=wr)
        nodes = {n.node_id: n for n in fabric.nodes()}
        assert "task-abc" in nodes["dn-vps-001"].active_executions


# ── Health Summary Tests ─────────────────────────────────────────────────────


class TestHealthSummary:
    def test_all_online_is_healthy(self) -> None:
        fabric = _make_fabric()
        h = fabric.health()
        assert h["fabric_status"] == "healthy"
        assert h["total_nodes"] == 2

    def test_one_offline_is_degraded(self) -> None:
        fabric = _make_fabric(profiles=[_make_vps_profile(), _make_offline_profile()])
        h = fabric.health()
        assert h["fabric_status"] == "degraded"
        assert h["by_health"]["unreachable"] == 1

    def test_all_offline_is_critical(self) -> None:
        off1 = _make_offline_profile()
        off2 = DeviceNodeProfile(
            node_id="dn-off-2", device_name="Off 2",
            role=DeviceRole.CONTROL_PLANE, os="linux",
            location="vps", trust_level="full",
            online_status="offline", capabilities=[],
        )
        fabric = _make_fabric(profiles=[off1, off2])
        h = fabric.health()
        assert h["fabric_status"] == "critical"

    def test_total_workers_counted(self) -> None:
        wr = WorkerRegistry()
        wr.register("w1", "dn-vps-001", "rt-1")
        wr.register("w2", "dn-beast-001", "rt-2")
        fabric = _make_fabric(worker_registry=wr)
        h = fabric.health()
        assert h["total_workers"] == 2

    def test_total_capacity_summed(self) -> None:
        fabric = _make_fabric()
        h = fabric.health()
        assert h["total_capacity"] == 12  # control_plane=4, heavy_workstation=8


# ── Capacity Tests ───────────────────────────────────────────────────────────


class TestCapacity:
    def test_per_node_capacity_returned(self) -> None:
        fabric = _make_fabric()
        cap = fabric.capacity()
        assert len(cap["nodes"]) == 2

    def test_utilization_zero_when_no_workers(self) -> None:
        fabric = _make_fabric()
        cap = fabric.capacity()
        for nc in cap["nodes"]:
            assert nc["utilization"] == 0.0

    def test_utilization_increases_with_workers(self) -> None:
        wr = WorkerRegistry()
        wr.register("w1", "dn-vps-001", "rt-1")
        wr.register("w2", "dn-vps-001", "rt-2")
        fabric = _make_fabric(worker_registry=wr)
        cap = fabric.capacity()
        vps = [nc for nc in cap["nodes"] if nc["node_id"] == "dn-vps-001"][0]
        assert vps["utilization"] == 0.5  # 2/4

    def test_accepting_work_flag(self) -> None:
        fabric = _make_fabric()
        cap = fabric.capacity()
        for nc in cap["nodes"]:
            if nc["max_workers"] > 0:
                assert nc["accepting_work"] is True


# ── Active Executions Tests ──────────────────────────────────────────────────


class TestActiveExecutions:
    def test_empty_when_no_tasks(self) -> None:
        fabric = _make_fabric()
        execs = fabric.active_executions()
        assert execs == []

    def test_returns_active_tasks(self) -> None:
        wr = WorkerRegistry()
        w = wr.register("w1", "dn-vps-001", "rt-1")
        w.current_task_id = "task-xyz"
        fabric = _make_fabric(worker_registry=wr)
        execs = fabric.active_executions()
        assert len(execs) == 1
        assert execs[0]["task_id"] == "task-xyz"
        assert execs[0]["node_id"] == "dn-vps-001"
        assert execs[0]["node_type"] == "vps"

    def test_multiple_tasks_across_nodes(self) -> None:
        wr = WorkerRegistry()
        w1 = wr.register("w1", "dn-vps-001", "rt-1")
        w1.current_task_id = "task-a"
        w2 = wr.register("w2", "dn-beast-001", "rt-2")
        w2.current_task_id = "task-b"
        fabric = _make_fabric(worker_registry=wr)
        execs = fabric.active_executions()
        assert len(execs) == 2
        task_ids = {e["task_id"] for e in execs}
        assert task_ids == {"task-a", "task-b"}


# ── Routing Decision Tests ───────────────────────────────────────────────────


class TestRouting:
    def test_routes_to_node_with_capability(self) -> None:
        fabric = _make_fabric()
        decision = fabric.route(capability_needs=["gpu_available"])
        assert decision.target_node_id == "dn-beast-001"
        assert decision.target_node_type == "windows"
        assert "gpu_available" in decision.capability_match
        assert decision.confidence > 0

    def test_routes_code_execution_to_best_match(self) -> None:
        fabric = _make_fabric()
        decision = fabric.route(capability_needs=["code_execution"])
        assert decision.target_node_id in ("dn-vps-001", "dn-beast-001")
        assert "code_execution" in decision.capability_match

    def test_routes_multiple_capabilities(self) -> None:
        fabric = _make_fabric()
        decision = fabric.route(capability_needs=["gpu_available", "code_execution"])
        assert decision.target_node_id == "dn-beast-001"
        assert len(decision.capability_match) == 2

    def test_no_match_returns_empty(self) -> None:
        fabric = _make_fabric()
        decision = fabric.route(capability_needs=["quantum_computing"])
        assert decision.target_node_id == ""
        assert decision.confidence == 0.0
        assert "No healthy node" in decision.reason

    def test_reason_is_human_readable(self) -> None:
        fabric = _make_fabric()
        decision = fabric.route(capability_needs=["code_execution"])
        assert "Selected" in decision.reason
        assert "healthy" in decision.reason
        assert "code_execution" in decision.reason

    def test_alternatives_excludes_selected(self) -> None:
        fabric = _make_fabric()
        decision = fabric.route(capability_needs=["code_execution"])
        assert decision.target_node_id not in decision.alternatives

    def test_skips_offline_nodes(self) -> None:
        fabric = _make_fabric(profiles=[_make_vps_profile(), _make_offline_profile()])
        decision = fabric.route(capability_needs=["gpu_available"])
        assert decision.target_node_id == ""  # only offline node has gpu

    def test_skips_saturated_nodes(self) -> None:
        wr = WorkerRegistry()
        for i in range(4):
            wr.register(f"w{i}", "dn-vps-001", f"rt-{i}")
        fabric = _make_fabric(worker_registry=wr)
        decision = fabric.route(capability_needs=["code_execution"])
        assert decision.target_node_id == "dn-beast-001"

    def test_to_dict_has_all_fields(self) -> None:
        fabric = _make_fabric()
        decision = fabric.route(capability_needs=["code_execution"])
        d = decision.to_dict()
        expected = {"target_node_id", "target_node_type", "reason",
                    "capability_match", "alternatives", "confidence"}
        assert expected.issubset(d.keys())

    def test_acceptance_response_shape(self) -> None:
        """Verify the acceptance test response shape matches the spec."""
        fabric = _make_fabric()
        decision = fabric.route(
            capability_needs=["code_execution"],
            risk_level="low",
        )
        d = decision.to_dict()
        assert isinstance(d["target_node_id"], str) and d["target_node_id"]
        assert isinstance(d["target_node_type"], str) and d["target_node_type"]
        assert isinstance(d["reason"], str) and len(d["reason"]) > 20
        assert isinstance(d["capability_match"], list) and len(d["capability_match"]) > 0
        assert isinstance(d["alternatives"], list)
        assert isinstance(d["confidence"], float) and d["confidence"] > 0


# ── Registration Tests ───────────────────────────────────────────────────────


class TestRegistration:
    def test_register_new_node(self) -> None:
        fabric = _make_fabric()
        node = fabric.register_node(
            node_id="agent-session-001",
            node_type="agent_session",
            capabilities=["code_execution"],
            display_name="Claude Agent #1",
        )
        assert node.node_id == "agent-session-001"
        assert node.node_type == ComputeNodeType.AGENT_SESSION
        assert node.health == ComputeNodeHealth.HEALTHY

    def test_registered_node_appears_in_nodes(self) -> None:
        fabric = _make_fabric()
        fabric.register_node("agent-001", "agent_session", ["code_execution"])
        nodes = fabric.nodes()
        ids = {n.node_id for n in nodes}
        assert "agent-001" in ids

    def test_registered_node_participates_in_routing(self) -> None:
        fabric = _make_fabric(profiles=[_make_vps_profile()])
        fabric.register_node("gpu-node", "model_runtime", ["gpu_available"])
        decision = fabric.route(capability_needs=["gpu_available"])
        assert decision.target_node_id == "gpu-node"

    def test_invalid_node_type_defaults_to_container(self) -> None:
        fabric = _make_fabric()
        node = fabric.register_node("x", "invalid_type", [])
        assert node.node_type == ComputeNodeType.CONTAINER


# ── Heartbeat Tests ──────────────────────────────────────────────────────────


class TestHeartbeat:
    def test_heartbeat_updates_extra_node(self) -> None:
        fabric = _make_fabric()
        fabric.register_node("agent-001", "agent_session", ["code_execution"])
        old_hb = fabric._extra_nodes["agent-001"].last_heartbeat
        time.sleep(0.01)
        assert fabric.heartbeat("agent-001") is True
        assert fabric._extra_nodes["agent-001"].last_heartbeat > old_hb

    def test_heartbeat_unknown_node_returns_false(self) -> None:
        fabric = _make_fabric()
        assert fabric.heartbeat("nonexistent") is False

    def test_heartbeat_delegates_to_worker_registry(self) -> None:
        wr = WorkerRegistry()
        wr.register("w1", "dn-vps-001", "rt-1")
        fabric = _make_fabric(worker_registry=wr)
        assert fabric.heartbeat("w1") is True


# ── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_profiles(self) -> None:
        """When no profiles passed, DeviceCapacityModel seeds defaults.
        Fabric still works — it just reflects the seed nodes."""
        dr = MockDistributedRuntime.__new__(MockDistributedRuntime)
        dr._profiles = {}
        dr._worker_registry = WorkerRegistry()
        dr._capacity_model = DeviceCapacityModel(dr._worker_registry, [])
        fabric = ComputeFabricRuntime(dr)
        assert fabric.nodes() == []
        assert fabric.health()["total_nodes"] == 0

    def test_empty_capability_needs_no_crash(self) -> None:
        fabric = _make_fabric()
        decision = fabric.route(capability_needs=[])
        assert decision.target_node_id == ""

    def test_single_node_fabric(self) -> None:
        fabric = _make_fabric(profiles=[_make_vps_profile()])
        nodes = fabric.nodes()
        assert len(nodes) == 1
        h = fabric.health()
        assert h["fabric_status"] == "healthy"
