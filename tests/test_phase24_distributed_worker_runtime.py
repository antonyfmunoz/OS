"""Phase 24 — Distributed Worker Runtime test suite.

Tests worker registry, device capacity model, capability-first packet
routing, coordinator device constraints, worker lifecycle events,
distributed runtime facade, and capability-first routing chain.

66 tests across 8 test classes.
"""

from __future__ import annotations

import sys
import time
import threading
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/opt/OS")

from substrate.organism.worker_registry import (
    WorkerInstance,
    WorkerRegistry,
    WorkerStatus,
)
from substrate.organism.device_capacity import (
    DeviceCapacity,
    DeviceCapacityModel,
)
from substrate.organism.device_role_registry import (
    DeviceCapability,
    DeviceNodeProfile,
    DeviceRole,
)
from substrate.organism.packet_router import (
    PacketPlacement,
    PacketRouter,
)
from substrate.organism.worker_lifecycle import (
    WorkerEventType,
    WorkerLifecycleEmitter,
)
from substrate.organism.event_spine import EventDomain, EventSpine
from substrate.organism.distributed_runtime import DistributedRuntime


# ── Helpers ──────────────────────────────────────────────────────


def _make_profiles() -> list[DeviceNodeProfile]:
    return [
        DeviceNodeProfile(
            node_id="vps-001",
            device_name="VPS",
            role=DeviceRole.CONTROL_PLANE,
            os="linux",
            location="vps",
            trust_level="high",
            online_status="online",
            capabilities=[
                DeviceCapability.CODE_EXECUTION,
                DeviceCapability.CONTAINER_RUNTIME,
            ],
        ),
        DeviceNodeProfile(
            node_id="beast-001",
            device_name="Beast",
            role=DeviceRole.HEAVY_WORKSTATION,
            os="windows",
            location="local",
            trust_level="high",
            online_status="online",
            capabilities=[
                DeviceCapability.CODE_EXECUTION,
                DeviceCapability.GPU_AVAILABLE,
                DeviceCapability.DESKTOP_AUTOMATION,
                DeviceCapability.BROWSER_AUTOMATION,
                DeviceCapability.MEDIA_GENERATION,
            ],
        ),
    ]


def _make_spine() -> EventSpine:
    return EventSpine(max_events=1000)


class _FakePacket:
    def __init__(self, packet_id: str = "pkt-1", description: str = "", target_repo: str = ""):
        self.packet_id = packet_id
        self.description = description
        self.target_repo = target_repo
        self.action_type = ""


# ── TestWorkerRegistry ──────────────────────────────────────────


class TestWorkerRegistry(unittest.TestCase):
    """12 tests for worker registration, status, heartbeat, querying."""

    def setUp(self):
        self.spine = _make_spine()
        self.reg = WorkerRegistry(event_spine=self.spine)

    def test_register_worker(self):
        w = self.reg.register("wkr-001", "vps-001", "rt-1", capabilities=["code_write"])
        self.assertEqual(w.worker_id, "wkr-001")
        self.assertEqual(w.device_id, "vps-001")
        self.assertEqual(w.status, WorkerStatus.SPAWNING)
        self.assertEqual(w.capabilities, ["code_write"])

    def test_register_duplicate_overwrites(self):
        self.reg.register("wkr-001", "vps-001", "rt-1", capabilities=["code_write"])
        w2 = self.reg.register("wkr-001", "vps-001", "rt-1", capabilities=["gpu_compute"])
        self.assertEqual(w2.capabilities, ["gpu_compute"])
        self.assertEqual(len(self.reg.active_workers()), 1)

    def test_unregister_worker(self):
        self.reg.register("wkr-001", "vps-001", "rt-1")
        removed = self.reg.unregister("wkr-001")
        self.assertIsNotNone(removed)
        self.assertIsNone(self.reg.get("wkr-001"))

    def test_unregister_nonexistent_returns_none(self):
        self.assertIsNone(self.reg.unregister("nonexist"))

    def test_update_status(self):
        self.reg.register("wkr-001", "vps-001", "rt-1")
        ok = self.reg.update_status("wkr-001", WorkerStatus.IDLE)
        self.assertTrue(ok)
        self.assertEqual(self.reg.get("wkr-001").status, WorkerStatus.IDLE)

    def test_update_status_with_task(self):
        self.reg.register("wkr-001", "vps-001", "rt-1")
        self.reg.update_status("wkr-001", WorkerStatus.WORKING, current_task_id="task-42")
        w = self.reg.get("wkr-001")
        self.assertEqual(w.current_task_id, "task-42")

    def test_heartbeat(self):
        self.reg.register("wkr-001", "vps-001", "rt-1")
        before = self.reg.get("wkr-001").last_heartbeat
        time.sleep(0.01)
        ok = self.reg.heartbeat("wkr-001")
        self.assertTrue(ok)
        self.assertGreater(self.reg.get("wkr-001").last_heartbeat, before)

    def test_heartbeat_nonexistent_returns_false(self):
        self.assertFalse(self.reg.heartbeat("nonexist"))

    def test_workers_on_device(self):
        self.reg.register("wkr-001", "vps-001", "rt-1")
        self.reg.register("wkr-002", "vps-001", "rt-1")
        self.reg.register("wkr-003", "beast-001", "rt-2")
        ws = self.reg.workers_on_device("vps-001")
        self.assertEqual(len(ws), 2)

    def test_active_workers_excludes_terminated(self):
        self.reg.register("wkr-001", "vps-001", "rt-1")
        self.reg.register("wkr-002", "vps-001", "rt-1")
        self.reg.update_status("wkr-002", WorkerStatus.TERMINATED)
        active = self.reg.active_workers()
        self.assertEqual(len(active), 1)

    def test_workers_with_capability(self):
        self.reg.register("wkr-001", "vps-001", "rt-1", capabilities=["code_write", "code_review"])
        self.reg.register("wkr-002", "beast-001", "rt-2", capabilities=["gpu_compute"])
        self.reg.register("wkr-003", "vps-001", "rt-1", capabilities=["code_write"])
        cw = self.reg.workers_with_capability("code_write")
        self.assertEqual(len(cw), 2)
        gpu = self.reg.workers_with_capability("gpu_compute")
        self.assertEqual(len(gpu), 1)

    def test_stale_workers(self):
        self.reg.register("wkr-001", "vps-001", "rt-1")
        w = self.reg.get("wkr-001")
        w.last_heartbeat = time.time() - 200
        stale = self.reg.stale_workers(timeout_s=120)
        self.assertIn("wkr-001", stale)


# ── TestDeviceCapacityModel ─────────────────────────────────────


class TestDeviceCapacityModel(unittest.TestCase):
    """10 tests for capacity computation, saturation, best device."""

    def setUp(self):
        self.spine = _make_spine()
        self.reg = WorkerRegistry(event_spine=self.spine)
        self.profiles = _make_profiles()
        self.cap = DeviceCapacityModel(self.reg, self.profiles)

    def test_capacity_for_known_device(self):
        c = self.cap.capacity_for("vps-001")
        self.assertEqual(c.device_id, "vps-001")
        self.assertEqual(c.max_workers, 4)  # CONTROL_PLANE
        self.assertTrue(c.accepting_work)

    def test_capacity_for_heavy_workstation(self):
        c = self.cap.capacity_for("beast-001")
        self.assertEqual(c.max_workers, 8)  # HEAVY_WORKSTATION

    def test_capacity_unknown_device(self):
        c = self.cap.capacity_for("unknown-device")
        self.assertEqual(c.max_workers, 1)  # UNKNOWN default

    def test_utilization_zero_when_empty(self):
        c = self.cap.capacity_for("vps-001")
        self.assertEqual(c.utilization, 0.0)
        self.assertEqual(c.active_workers, 0)

    def test_utilization_increases_with_workers(self):
        self.reg.register("wkr-001", "vps-001", "rt-1")
        self.reg.register("wkr-002", "vps-001", "rt-1")
        c = self.cap.capacity_for("vps-001")
        self.assertEqual(c.active_workers, 2)
        self.assertAlmostEqual(c.utilization, 0.5)

    def test_saturated_when_full(self):
        for i in range(4):
            self.reg.register(f"wkr-{i}", "vps-001", "rt-1")
        self.assertTrue(self.cap.is_saturated("vps-001"))

    def test_not_saturated_with_headroom(self):
        self.reg.register("wkr-001", "vps-001", "rt-1")
        self.assertFalse(self.cap.is_saturated("vps-001"))

    def test_best_device_for_work(self):
        self.reg.register("wkr-001", "vps-001", "rt-1")
        best = self.cap.best_device_for_work(["vps-001", "beast-001"])
        self.assertEqual(best, "beast-001")  # beast has 8 headroom vs vps 3

    def test_all_capacities(self):
        caps = self.cap.all_capacities()
        self.assertEqual(len(caps), 2)

    def test_to_dict(self):
        d = self.cap.to_dict()
        self.assertIn("devices", d)
        self.assertIn("total_headroom", d)
        self.assertIn("saturated_count", d)


# ── TestPacketRouter ────────────────────────────────────────────


class TestPacketRouter(unittest.TestCase):
    """14 tests for capability-first routing chain."""

    def setUp(self):
        self.spine = _make_spine()
        self.reg = WorkerRegistry(event_spine=self.spine)
        self.profiles = _make_profiles()
        self.cap = DeviceCapacityModel(self.reg, self.profiles)
        self.router = PacketRouter(self.reg, self.cap, event_spine=self.spine)
        self.router._profiles = {p.node_id: p for p in self.profiles}

    def test_infer_capability_react(self):
        cap = self.router._infer_capability("build react frontend")
        self.assertEqual(cap, "react_build")

    def test_infer_capability_gpu(self):
        cap = self.router._infer_capability("GPU cuda model training")
        self.assertEqual(cap, "gpu_compute")

    def test_infer_capability_deploy(self):
        cap = self.router._infer_capability("deploy to production")
        self.assertEqual(cap, "deployment")

    def test_infer_capability_default(self):
        cap = self.router._infer_capability("zzz no match zzz")
        self.assertEqual(cap, "code_write")

    def test_route_basic_packet(self):
        pkt = _FakePacket(description="implement new feature")
        placement = self.router.route(pkt)
        self.assertIsInstance(placement, PacketPlacement)
        self.assertEqual(placement.packet_id, "pkt-1")
        self.assertEqual(placement.required_capability, "code_write")

    def test_routing_chain_has_five_steps(self):
        pkt = _FakePacket(description="implement new feature")
        placement = self.router.route(pkt)
        self.assertEqual(len(placement.routing_chain), 5)
        self.assertTrue(placement.routing_chain[0].startswith("capability:"))
        self.assertTrue(placement.routing_chain[1].startswith("worker:"))
        self.assertTrue(placement.routing_chain[2].startswith("device:"))
        self.assertTrue(placement.routing_chain[3].startswith("workspace:"))
        self.assertTrue(placement.routing_chain[4].startswith("runtime:"))

    def test_worker_selection_by_capability(self):
        self.reg.register("wkr-001", "vps-001", "rt-1", capabilities=["code_write"])
        self.reg.update_status("wkr-001", WorkerStatus.IDLE)
        pkt = _FakePacket(description="implement feature")
        placement = self.router.route(pkt)
        self.assertEqual(placement.matched_worker_id, "wkr-001")

    def test_device_derived_from_worker(self):
        self.reg.register("wkr-001", "beast-001", "rt-2", capabilities=["code_write"])
        self.reg.update_status("wkr-001", WorkerStatus.IDLE)
        pkt = _FakePacket(description="implement feature")
        placement = self.router.route(pkt)
        self.assertEqual(placement.device_id, "beast-001")

    def test_gpu_routes_to_beast(self):
        pkt = _FakePacket(description="GPU cuda model training")
        placement = self.router.route(pkt)
        self.assertEqual(placement.required_capability, "gpu_compute")
        self.assertEqual(placement.device_id, "beast-001")

    def test_workspace_resolution_linux(self):
        pkt = _FakePacket(description="implement feature", target_repo="OS")
        placement = self.router.route(pkt)
        if placement.device_id == "vps-001":
            self.assertEqual(placement.workspace_path, "/opt/OS")

    def test_workspace_resolution_windows(self):
        self.reg.register("wkr-001", "beast-001", "rt-2", capabilities=["code_write"])
        self.reg.update_status("wkr-001", WorkerStatus.IDLE)
        pkt = _FakePacket(description="implement feature", target_repo="CreatorOS")
        placement = self.router.route(pkt)
        self.assertEqual(placement.workspace_path, "C:\\Projects\\CreatorOS")

    def test_no_eligible_worker_falls_to_device(self):
        pkt = _FakePacket(description="implement feature")
        placement = self.router.route(pkt)
        self.assertEqual(placement.matched_worker_id, "")
        self.assertNotEqual(placement.device_id, "")

    def test_batch_routing(self):
        pkts = [_FakePacket(f"pkt-{i}", "implement feature") for i in range(3)]
        placements = self.router.route_batch(pkts)
        self.assertEqual(len(placements), 3)

    def test_remote_dispatch_flag(self):
        pkt = _FakePacket(description="implement feature")
        placement = self.router.route(pkt)
        if placement.device_id == "beast-001":
            self.assertTrue(placement.requires_remote_dispatch)
        elif placement.device_id == "vps-001":
            self.assertFalse(placement.requires_remote_dispatch)


# ── TestCoordinatorConstraints ──────────────────────────────────


class TestCoordinatorConstraints(unittest.TestCase):
    """8 tests for coordinator device constraint filtering."""

    def setUp(self):
        self.profiles = _make_profiles()

    def test_import_coordinator(self):
        from substrate.organism.coordinator import OrganismCoordinator

        self.assertIsNotNone(OrganismCoordinator)

    def test_coordinator_accepts_capacity_model(self):
        from substrate.organism.coordinator import OrganismCoordinator

        spine = _make_spine()
        reg = WorkerRegistry(event_spine=spine)
        cap = DeviceCapacityModel(reg, self.profiles)
        coord = OrganismCoordinator(graph=MagicMock(), capacity_model=cap)
        self.assertIsNotNone(coord._capacity_model)

    def test_coordinator_backward_compat_no_capacity(self):
        from substrate.organism.coordinator import OrganismCoordinator

        coord = OrganismCoordinator(graph=MagicMock())
        self.assertIsNone(coord._capacity_model)

    def test_apply_device_constraints_exists(self):
        from substrate.organism.coordinator import OrganismCoordinator

        coord = OrganismCoordinator(graph=MagicMock())
        self.assertTrue(hasattr(coord, "_apply_device_constraints"))

    def test_apply_device_constraints_filters_blocked(self):
        from substrate.organism.coordinator import OrganismCoordinator

        profile_a = DeviceNodeProfile(
            node_id="node-a",
            device_name="Node A",
            role=DeviceRole.CONTROL_PLANE,
            os="linux",
            location="vps",
            trust_level="high",
            online_status="online",
            blocked_workloads=["gpu_compute"],
        )
        profile_b = DeviceNodeProfile(
            node_id="node-b",
            device_name="Node B",
            role=DeviceRole.HEAVY_WORKSTATION,
            os="windows",
            location="local",
            trust_level="high",
            online_status="online",
        )

        coord = OrganismCoordinator(graph=MagicMock())
        wu = MagicMock()
        wu.metadata = {"workload_type": "gpu_compute"}

        cand_a = MagicMock()
        cand_a.metadata = {"device_id": "node-a"}
        cand_b = MagicMock()
        cand_b.metadata = {"device_id": "node-b"}

        profiles = [profile_a, profile_b]
        with patch("substrate.organism.device_role_registry.load_registry", return_value=profiles):
            with patch("substrate.organism.device_role_registry.seed_known_nodes", return_value=profiles):
                result = coord._apply_device_constraints(wu, [cand_a, cand_b])
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0].metadata["device_id"], "node-b")

    def test_apply_device_constraints_passes_unblocked(self):
        from substrate.organism.coordinator import OrganismCoordinator

        profile = DeviceNodeProfile(
            node_id="node-a",
            device_name="Node A",
            role=DeviceRole.CONTROL_PLANE,
            os="linux",
            location="vps",
            trust_level="high",
            online_status="online",
        )

        coord = OrganismCoordinator(graph=MagicMock())
        wu = MagicMock()
        wu.metadata = {"workload_type": "code_write"}

        candidate = MagicMock()
        candidate.metadata = {"device_id": "node-a"}

        with patch("substrate.organism.device_role_registry.load_registry", return_value=[profile]):
            with patch("substrate.organism.device_role_registry.seed_known_nodes", return_value=[profile]):
                result = coord._apply_device_constraints(wu, [candidate])
                self.assertEqual(len(result), 1)

    def test_apply_device_constraints_saturated_filtered(self):
        from substrate.organism.coordinator import OrganismCoordinator

        spine = _make_spine()
        reg = WorkerRegistry(event_spine=spine)
        cap = DeviceCapacityModel(reg, self.profiles)
        for i in range(4):
            reg.register(f"wkr-{i}", "vps-001", "rt-1")

        coord = OrganismCoordinator(graph=MagicMock(), capacity_model=cap)
        wu = MagicMock()
        wu.metadata = {}

        cand_vps = MagicMock()
        cand_vps.metadata = {"device_id": "vps-001"}
        cand_beast = MagicMock()
        cand_beast.metadata = {"device_id": "beast-001"}

        with patch("substrate.organism.device_role_registry.load_registry", return_value=self.profiles):
            with patch(
                "substrate.organism.device_role_registry.seed_known_nodes",
                return_value=self.profiles,
            ):
                result = coord._apply_device_constraints(wu, [cand_vps, cand_beast])
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0].metadata["device_id"], "beast-001")

    def test_constraints_fall_back_when_all_filtered(self):
        from substrate.organism.coordinator import OrganismCoordinator

        profile = DeviceNodeProfile(
            node_id="node-a",
            device_name="Node A",
            role=DeviceRole.CONTROL_PLANE,
            os="linux",
            location="vps",
            trust_level="high",
            online_status="online",
            blocked_workloads=["code_write"],
        )

        coord = OrganismCoordinator(graph=MagicMock())
        wu = MagicMock()
        wu.metadata = {"workload_type": "code_write"}

        candidate = MagicMock()
        candidate.metadata = {"device_id": "node-a"}

        with patch("substrate.organism.device_role_registry.load_registry", return_value=[profile]):
            with patch("substrate.organism.device_role_registry.seed_known_nodes", return_value=[profile]):
                result = coord._apply_device_constraints(wu, [candidate])
                self.assertEqual(len(result), 1)


# ── TestWorkerLifecycle ─────────────────────────────────────────


class TestWorkerLifecycle(unittest.TestCase):
    """6 tests for worker lifecycle event emission."""

    def setUp(self):
        self.spine = _make_spine()
        self.emitter = WorkerLifecycleEmitter(self.spine)
        self.worker = WorkerInstance(
            worker_id="wkr-test",
            device_id="vps-001",
            runtime_id="rt-1",
        )

    def test_on_spawn_emits(self):
        self.emitter.on_spawn(self.worker)
        events = self.spine.replay(domains={EventDomain.WORKER})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, WorkerEventType.SPAWNED.value)

    def test_on_ready_emits(self):
        self.emitter.on_ready(self.worker)
        events = self.spine.replay(domains={EventDomain.WORKER})
        self.assertEqual(events[0].event_type, WorkerEventType.READY.value)

    def test_on_assigned_emits(self):
        self.emitter.on_assigned(self.worker, "task-42")
        events = self.spine.replay(domains={EventDomain.WORKER})
        self.assertEqual(events[0].data["task_id"], "task-42")

    def test_on_failed_emits(self):
        self.emitter.on_failed(self.worker, "out of memory")
        events = self.spine.replay(domains={EventDomain.WORKER})
        self.assertEqual(events[0].data["error"], "out of memory")

    def test_on_terminated_emits(self):
        self.emitter.on_terminated(self.worker, "shutdown")
        events = self.spine.replay(domains={EventDomain.WORKER})
        self.assertEqual(events[0].data["reason"], "shutdown")

    def test_on_heartbeat_lost_emits(self):
        self.emitter.on_heartbeat_lost("wkr-test", "vps-001")
        events = self.spine.replay(domains={EventDomain.WORKER})
        self.assertEqual(events[0].event_type, WorkerEventType.HEARTBEAT_LOST.value)


# ── TestDistributedRuntime ──────────────────────────────────────


class TestDistributedRuntime(unittest.TestCase):
    """8 tests for the facade composing all subsystems."""

    def setUp(self):
        self.spine = _make_spine()
        self.profiles = _make_profiles()
        self.rt = DistributedRuntime(
            event_spine=self.spine,
            device_profiles=self.profiles,
        )

    def test_overview_structure(self):
        ov = self.rt.overview()
        self.assertIn("devices", ov)
        self.assertIn("workers", ov)
        self.assertIn("capacity", ov)
        self.assertIn("topology", ov)

    def test_register_and_query_worker(self):
        w = self.rt.register_worker("wkr-001", "vps-001", "rt-1", capabilities=["code_write"])
        self.assertEqual(w.worker_id, "wkr-001")
        ws = self.rt.workers()
        self.assertEqual(len(ws), 1)

    def test_unregister_worker(self):
        self.rt.register_worker("wkr-001", "vps-001", "rt-1")
        ok = self.rt.unregister_worker("wkr-001")
        self.assertTrue(ok)
        self.assertFalse(self.rt.unregister_worker("wkr-001"))

    def test_heartbeat(self):
        self.rt.register_worker("wkr-001", "vps-001", "rt-1")
        ok = self.rt.worker_heartbeat("wkr-001")
        self.assertTrue(ok)
        self.assertFalse(self.rt.worker_heartbeat("nonexist"))

    def test_route_packet(self):
        pkt = _FakePacket(description="implement feature")
        placement = self.rt.route_packet(pkt)
        self.assertIsInstance(placement, PacketPlacement)
        self.assertEqual(len(placement.routing_chain), 5)

    def test_assignments_track_placements(self):
        self.rt.route_packet(_FakePacket(description="implement feature"))
        self.rt.route_packet(_FakePacket(description="deploy to prod"))
        assignments = self.rt.assignments()
        self.assertEqual(len(assignments), 2)

    def test_capabilities_matrix(self):
        matrix = self.rt.capabilities_matrix()
        self.assertIn("capabilities", matrix)
        self.assertIn("devices", matrix)
        self.assertIn("matrix", matrix)
        self.assertEqual(len(matrix["devices"]), 2)

    def test_topology_shows_capabilities(self):
        self.rt.register_worker("wkr-001", "vps-001", "rt-1", capabilities=["code_write"])
        topo = self.rt.topology()
        self.assertIn("capabilities", topo)
        self.assertIn("code_write", topo["capabilities"])
        self.assertEqual(len(topo["capabilities"]["code_write"]), 1)


# ── TestCockpitRoutes ───────────────────────────────────────────


class TestCockpitRoutes(unittest.TestCase):
    """4 tests for route module structure and configuration."""

    def test_import_routes(self):
        from transports.api.cockpit_distributed_runtime_routes import (
            distributed_runtime_router,
            configure,
        )

        self.assertIsNotNone(distributed_runtime_router)
        self.assertIsNotNone(configure)

    def test_configure_sets_flag(self):
        import transports.api.cockpit_distributed_runtime_routes as mod

        mod.configure(require_operator_dep=lambda: "test-user")
        self.assertTrue(mod._configured)

    def test_get_runtime_creates_instance(self):
        from transports.api.cockpit_distributed_runtime_routes import _get_runtime

        rt = _get_runtime()
        self.assertIsNotNone(rt)

    def test_router_has_expected_routes(self):
        import transports.api.cockpit_distributed_runtime_routes as mod

        mod.configure(require_operator_dep=lambda: "test-user")
        routes = [r.path for r in mod.distributed_runtime_router.routes]
        self.assertIn("/organism/distributed-runtime", routes)
        self.assertIn("/organism/distributed-runtime/devices", routes)
        self.assertIn("/organism/distributed-runtime/workers", routes)
        self.assertIn("/organism/distributed-runtime/capacity", routes)
        self.assertIn("/organism/distributed-runtime/assignments", routes)
        self.assertIn("/organism/distributed-runtime/capabilities", routes)


# ── TestCapabilityFirstRouting ──────────────────────────────────


class TestCapabilityFirstRouting(unittest.TestCase):
    """4 tests verifying capability-first (not device-first) routing."""

    def setUp(self):
        self.spine = _make_spine()
        self.reg = WorkerRegistry(event_spine=self.spine)
        self.profiles = _make_profiles()
        self.cap = DeviceCapacityModel(self.reg, self.profiles)
        self.router = PacketRouter(self.reg, self.cap, event_spine=self.spine)
        self.router._profiles = {p.node_id: p for p in self.profiles}

    def test_capability_is_primary_not_device(self):
        pkt = _FakePacket(description="GPU cuda training")
        placement = self.router.route(pkt)
        self.assertEqual(placement.required_capability, "gpu_compute")
        self.assertTrue(placement.routing_chain[0].startswith("capability:gpu_compute"))

    def test_device_derived_from_capability(self):
        pkt = _FakePacket(description="GPU cuda training")
        placement = self.router.route(pkt)
        self.assertEqual(placement.device_id, "beast-001")
        self.assertIn("device:beast-001", placement.routing_chain)

    def test_multiple_devices_same_capability(self):
        extra_profile = DeviceNodeProfile(
            node_id="cloud-001",
            device_name="Cloud Runner",
            role=DeviceRole.EXTERNAL_SERVICE,
            os="linux",
            location="cloud",
            trust_level="medium",
            online_status="online",
            capabilities=[DeviceCapability.CODE_EXECUTION],
        )
        profiles = self.profiles + [extra_profile]
        cap = DeviceCapacityModel(self.reg, profiles)
        router = PacketRouter(self.reg, cap, event_spine=self.spine)
        router._profiles = {p.node_id: p for p in profiles}

        self.reg.register("wkr-001", "vps-001", "rt-1", capabilities=["code_write"])
        self.reg.update_status("wkr-001", WorkerStatus.IDLE)
        self.reg.register("wkr-002", "cloud-001", "rt-3", capabilities=["code_write"])
        self.reg.update_status("wkr-002", WorkerStatus.IDLE)

        pkt = _FakePacket(description="implement feature")
        placement = router.route(pkt)
        self.assertEqual(placement.required_capability, "code_write")
        self.assertIn(placement.matched_worker_id, ["wkr-001", "wkr-002"])

    def test_routing_chain_audit_trail_complete(self):
        pkt = _FakePacket(description="implement feature", target_repo="OS")
        placement = self.router.route(pkt)
        chain = placement.routing_chain
        self.assertEqual(len(chain), 5)
        prefixes = [s.split(":")[0] for s in chain]
        self.assertEqual(prefixes, ["capability", "worker", "device", "workspace", "runtime"])


# ── TestThreadSafety ────────────────────────────────────────────


class TestThreadSafety(unittest.TestCase):
    """4 tests for concurrent access safety."""

    def test_concurrent_register(self):
        reg = WorkerRegistry()
        errors = []

        def register(i: int):
            try:
                reg.register(f"wkr-{i}", "vps-001", "rt-1")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(reg.active_workers()), 20)

    def test_concurrent_heartbeat(self):
        reg = WorkerRegistry()
        reg.register("wkr-001", "vps-001", "rt-1")
        errors = []

        def hb(_: int):
            try:
                reg.heartbeat("wkr-001")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=hb, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(errors), 0)

    def test_concurrent_status_update(self):
        reg = WorkerRegistry()
        reg.register("wkr-001", "vps-001", "rt-1")

        def update(i: int):
            status = WorkerStatus.IDLE if i % 2 == 0 else WorkerStatus.WORKING
            reg.update_status("wkr-001", status)

        threads = [threading.Thread(target=update, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        w = reg.get("wkr-001")
        self.assertIn(w.status, [WorkerStatus.IDLE, WorkerStatus.WORKING])

    def test_concurrent_register_unregister(self):
        reg = WorkerRegistry()
        for i in range(10):
            reg.register(f"wkr-{i}", "vps-001", "rt-1")

        def unreg(i: int):
            reg.unregister(f"wkr-{i}")

        threads = [threading.Thread(target=unreg, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(reg.active_workers()), 0)


# ── Type Registration ───────────────────────────────────────────


class TestTypeRegistration(unittest.TestCase):
    """2 tests for canonical type registration."""

    def test_types_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        for name in [
            "WorkerStatus",
            "WorkerInstance",
            "DeviceCapacity",
            "PacketPlacement",
            "WorkerEventType",
        ]:
            self.assertIn(name, CANONICAL_TYPES, f"{name} not in CANONICAL_TYPES")

    def test_reality_mutation_source(self):
        from substrate.reality_model.reality_mutation import MutationSource

        self.assertIn("WORKER_RUNTIME", MutationSource.__members__)


if __name__ == "__main__":
    unittest.main()
