"""Phase 28 — UMH Node Role & Version Topology tests.

Tests: node topology types, node registry, version coherence,
workspace node links, routing hints, cockpit routes, type registration,
integration.

80 tests across 12 classes.
"""

from __future__ import annotations

import json
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/opt/OS")

from substrate.organism.umh_node_topology import (
    UMHNodeRecord,
    UMHNodeRole,
    UMHNodeStatus,
    UMHNodeTopology,
    UMHServiceActivation,
    UMHServiceRole,
    UMHVersionInfo,
    UMHVersionStatus,
)


class TestUMHNodeTypes(unittest.TestCase):
    """Test enum types and string conversion."""

    def test_node_role_values(self) -> None:
        assert UMHNodeRole.ORCHESTRATOR.value == "orchestrator"
        assert UMHNodeRole.CONTROL_PLANE.value == "control_plane"
        assert UMHNodeRole.WORKSTATION.value == "workstation"
        assert UMHNodeRole.BUILDER.value == "builder"

    def test_node_role_count(self) -> None:
        assert len(UMHNodeRole) == 7

    def test_node_status_values(self) -> None:
        assert UMHNodeStatus.ONLINE.value == "online"
        assert UMHNodeStatus.OFFLINE.value == "offline"
        assert UMHNodeStatus.DEGRADED.value == "degraded"
        assert UMHNodeStatus.UNKNOWN.value == "unknown"

    def test_node_status_count(self) -> None:
        assert len(UMHNodeStatus) == 4

    def test_service_role_values(self) -> None:
        assert UMHServiceRole.COCKPIT_API.value == "cockpit_api"
        assert UMHServiceRole.GOVERNANCE.value == "governance"
        assert UMHServiceRole.META_IDE.value == "meta_ide"
        assert UMHServiceRole.LOCAL_BUILDER.value == "local_builder"

    def test_service_role_count(self) -> None:
        assert len(UMHServiceRole) == 13

    def test_version_status_values(self) -> None:
        assert UMHVersionStatus.COHERENT.value == "coherent"
        assert UMHVersionStatus.DRIFTED.value == "drifted"
        assert UMHVersionStatus.UNKNOWN.value == "unknown"

    def test_version_status_count(self) -> None:
        assert len(UMHVersionStatus) == 3


class TestUMHVersionInfo(unittest.TestCase):
    """Test version info construction and serialization."""

    def test_construction(self) -> None:
        v = UMHVersionInfo(
            umh_version="1.0.0",
            git_commit="abc123",
            branch="main",
            schema_version="v1",
            migration_version="m1",
        )
        assert v.umh_version == "1.0.0"
        assert v.git_commit == "abc123"

    def test_to_dict(self) -> None:
        v = UMHVersionInfo(git_commit="abc123", branch="main")
        d = v.to_dict()
        assert d["git_commit"] == "abc123"
        assert d["branch"] == "main"

    def test_from_dict(self) -> None:
        d = {"git_commit": "abc123", "branch": "dev", "schema_version": "v2"}
        v = UMHVersionInfo.from_dict(d)
        assert v.git_commit == "abc123"
        assert v.branch == "dev"
        assert v.schema_version == "v2"

    def test_roundtrip(self) -> None:
        v = UMHVersionInfo(
            umh_version="2.0",
            git_commit="def456",
            branch="main",
            schema_version="v3",
            migration_version="m3",
            build_timestamp=1000.0,
        )
        rebuilt = UMHVersionInfo.from_dict(v.to_dict())
        assert rebuilt.git_commit == v.git_commit
        assert rebuilt.schema_version == v.schema_version
        assert rebuilt.build_timestamp == v.build_timestamp

    def test_matches_same(self) -> None:
        v1 = UMHVersionInfo(git_commit="abc", schema_version="v1", migration_version="m1")
        v2 = UMHVersionInfo(git_commit="abc", schema_version="v1", migration_version="m1")
        assert v1.matches(v2) is True

    def test_matches_different(self) -> None:
        v1 = UMHVersionInfo(git_commit="abc", schema_version="v1", migration_version="m1")
        v2 = UMHVersionInfo(git_commit="def", schema_version="v1", migration_version="m1")
        assert v1.matches(v2) is False


class TestUMHServiceActivation(unittest.TestCase):
    """Test service activation construction and serialization."""

    def test_construction(self) -> None:
        s = UMHServiceActivation(
            service_id="umh-vps-governance",
            node_id="umh-vps",
            service_role="governance",
            active=True,
        )
        assert s.service_id == "umh-vps-governance"
        assert s.service_role == "governance"

    def test_to_dict(self) -> None:
        s = UMHServiceActivation(service_id="test", service_role="memory", active=True)
        d = s.to_dict()
        assert d["service_role"] == "memory"
        assert d["active"] is True

    def test_from_dict(self) -> None:
        d = {"service_id": "s1", "node_id": "n1", "service_role": "meta_ide", "active": False}
        s = UMHServiceActivation.from_dict(d)
        assert s.service_role == "meta_ide"
        assert s.active is False

    def test_roundtrip(self) -> None:
        s = UMHServiceActivation(
            service_id="s1",
            node_id="n1",
            service_role="event_spine",
            active=True,
            status="running",
            endpoint="http://localhost:8000",
            health="healthy",
            metadata={"port": 8000},
        )
        rebuilt = UMHServiceActivation.from_dict(s.to_dict())
        assert rebuilt.service_role == s.service_role
        assert rebuilt.metadata == {"port": 8000}


class TestUMHNodeModels(unittest.TestCase):
    """Test UMHNodeRecord and UMHNodeTopology construction and serialization."""

    def _make_node(self, node_id: str = "test-node", primary: bool = False) -> UMHNodeRecord:
        return UMHNodeRecord(
            node_id=node_id,
            device_id="vps",
            hostname="vps",
            purpose="test node",
            roles=["orchestrator"],
            status="online",
            version=UMHVersionInfo(git_commit="abc123"),
            active_services=[
                UMHServiceActivation(service_id=f"{node_id}-gov", service_role="governance")
            ],
            capability_ids=["api_runtime"],
            workspace_ids=["umh"],
            primary=primary,
        )

    def test_node_construction(self) -> None:
        n = self._make_node()
        assert n.node_id == "test-node"
        assert n.device_id == "vps"

    def test_node_to_dict(self) -> None:
        n = self._make_node()
        d = n.to_dict()
        assert d["node_id"] == "test-node"
        assert d["version"]["git_commit"] == "abc123"
        assert len(d["active_services"]) == 1

    def test_node_from_dict(self) -> None:
        n = self._make_node()
        rebuilt = UMHNodeRecord.from_dict(n.to_dict())
        assert rebuilt.node_id == "test-node"
        assert rebuilt.version.git_commit == "abc123"
        assert len(rebuilt.active_services) == 1

    def test_node_roundtrip(self) -> None:
        n = self._make_node(primary=True)
        rebuilt = UMHNodeRecord.from_dict(n.to_dict())
        assert rebuilt.primary is True
        assert rebuilt.roles == ["orchestrator"]

    def test_topology_construction(self) -> None:
        t = UMHNodeTopology(nodes=[self._make_node()])
        assert len(t.nodes) == 1
        assert t.organism_id == "umh"

    def test_topology_to_dict(self) -> None:
        t = UMHNodeTopology(nodes=[self._make_node()])
        d = t.to_dict()
        assert d["node_count"] == 1
        assert d["organism_id"] == "umh"

    def test_topology_from_dict(self) -> None:
        t = UMHNodeTopology(
            nodes=[self._make_node()],
            version_status="coherent",
            canonical_version=UMHVersionInfo(git_commit="abc123"),
        )
        rebuilt = UMHNodeTopology.from_dict(t.to_dict())
        assert len(rebuilt.nodes) == 1
        assert rebuilt.version_status == "coherent"
        assert rebuilt.canonical_version is not None
        assert rebuilt.canonical_version.git_commit == "abc123"

    def test_topology_no_canonical(self) -> None:
        t = UMHNodeTopology(nodes=[])
        d = t.to_dict()
        assert d["canonical_version"] is None


class TestUMHNodeRegistry(unittest.TestCase):
    """Test the UMH node registry."""

    def setUp(self) -> None:
        self.registry = self._create_registry()

    def _create_registry(self):  # type: ignore[no-untyped-def]
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        return UMHNodeRegistry()

    def test_seed_count(self) -> None:
        nodes = self.registry.list_nodes()
        assert len(nodes) == 2

    def test_get_vps(self) -> None:
        node = self.registry.get_node("umh-vps")
        assert node is not None
        assert node.device_id == "vps"

    def test_get_windows(self) -> None:
        node = self.registry.get_node("umh-windows")
        assert node is not None
        assert node.device_id == "beast"

    def test_nodes_for_device_vps(self) -> None:
        nodes = self.registry.nodes_for_device("vps")
        assert len(nodes) == 1
        assert nodes[0].node_id == "umh-vps"

    def test_nodes_for_device_beast(self) -> None:
        nodes = self.registry.nodes_for_device("beast")
        assert len(nodes) == 1
        assert nodes[0].node_id == "umh-windows"

    def test_nodes_for_role_orchestrator(self) -> None:
        nodes = self.registry.nodes_for_role("orchestrator")
        assert len(nodes) == 1
        assert nodes[0].node_id == "umh-vps"

    def test_nodes_for_role_workstation(self) -> None:
        nodes = self.registry.nodes_for_role("workstation")
        assert len(nodes) == 1
        assert nodes[0].node_id == "umh-windows"

    def test_nodes_for_service_governance(self) -> None:
        nodes = self.registry.nodes_for_service("governance")
        assert len(nodes) == 1
        assert nodes[0].node_id == "umh-vps"

    def test_nodes_for_service_meta_ide(self) -> None:
        nodes = self.registry.nodes_for_service("meta_ide")
        assert len(nodes) == 1
        assert nodes[0].node_id == "umh-windows"

    def test_primary_node(self) -> None:
        primary = self.registry.primary_node()
        assert primary is not None
        assert primary.node_id == "umh-vps"
        assert primary.primary is True


class TestSeedNodes(unittest.TestCase):
    """Verify seed node structure matches the organism model."""

    def setUp(self) -> None:
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        self.registry = UMHNodeRegistry()

    def test_vps_has_orchestrator_role(self) -> None:
        node = self.registry.get_node("umh-vps")
        assert node is not None
        assert "orchestrator" in node.roles
        assert "control_plane" in node.roles

    def test_windows_has_workstation_role(self) -> None:
        node = self.registry.get_node("umh-windows")
        assert node is not None
        assert "workstation" in node.roles
        assert "builder" in node.roles

    def test_both_have_observer_role(self) -> None:
        vps = self.registry.get_node("umh-vps")
        win = self.registry.get_node("umh-windows")
        assert vps is not None and "observer" in vps.roles
        assert win is not None and "observer" in win.roles

    def test_both_have_umh_workspace(self) -> None:
        vps = self.registry.get_node("umh-vps")
        win = self.registry.get_node("umh-windows")
        assert vps is not None and "umh" in vps.workspace_ids
        assert win is not None and "umh" in win.workspace_ids

    def test_vps_service_count(self) -> None:
        node = self.registry.get_node("umh-vps")
        assert node is not None
        assert len(node.active_services) == 6

    def test_windows_service_count(self) -> None:
        node = self.registry.get_node("umh-windows")
        assert node is not None
        assert len(node.active_services) == 6


class TestVersionCoherence(unittest.TestCase):
    """Test version coherence detection."""

    def _make_registry_with_versions(self, vps_commit: str, win_commit: str):  # type: ignore[no-untyped-def]
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        reg = UMHNodeRegistry(seed=False)
        reg.register_node(
            UMHNodeRecord(
                node_id="umh-vps",
                device_id="vps",
                roles=["orchestrator"],
                status="online",
                version=UMHVersionInfo(
                    git_commit=vps_commit, schema_version="v1", migration_version="m1"
                ),
                primary=True,
            )
        )
        reg.register_node(
            UMHNodeRecord(
                node_id="umh-windows",
                device_id="beast",
                roles=["workstation"],
                status="online",
                version=UMHVersionInfo(
                    git_commit=win_commit, schema_version="v1", migration_version="m1"
                ),
                primary=False,
            )
        )
        return reg

    def test_coherent_same_commits(self) -> None:
        from substrate.organism.umh_version_coherence import UMHVersionCoherenceEngine

        reg = self._make_registry_with_versions("abc123", "abc123")
        engine = UMHVersionCoherenceEngine(registry=reg)
        assert engine.overall_status() == UMHVersionStatus.COHERENT

    def test_drifted_different_commits(self) -> None:
        from substrate.organism.umh_version_coherence import UMHVersionCoherenceEngine

        reg = self._make_registry_with_versions("abc123", "def456")
        engine = UMHVersionCoherenceEngine(registry=reg)
        assert engine.overall_status() == UMHVersionStatus.DRIFTED

    def test_unknown_no_commits(self) -> None:
        from substrate.organism.umh_node_registry import UMHNodeRegistry
        from substrate.organism.umh_version_coherence import UMHVersionCoherenceEngine

        reg = UMHNodeRegistry(seed=False)
        engine = UMHVersionCoherenceEngine(registry=reg)
        assert engine.overall_status() == UMHVersionStatus.UNKNOWN

    def test_canonical_version_from_primary(self) -> None:
        from substrate.organism.umh_version_coherence import UMHVersionCoherenceEngine

        reg = self._make_registry_with_versions("abc123", "abc123")
        engine = UMHVersionCoherenceEngine(registry=reg)
        cv = engine.canonical_version()
        assert cv is not None
        assert cv.git_commit == "abc123"

    def test_drift_report_structure(self) -> None:
        from substrate.organism.umh_version_coherence import UMHVersionCoherenceEngine

        reg = self._make_registry_with_versions("abc123", "def456")
        engine = UMHVersionCoherenceEngine(registry=reg)
        report = engine.drift_report()
        assert report["overall_status"] == "drifted"
        assert report["node_count"] == 2
        assert len(report["nodes"]) == 2

    def test_node_version_status_matches(self) -> None:
        from substrate.organism.umh_version_coherence import UMHVersionCoherenceEngine

        reg = self._make_registry_with_versions("abc123", "abc123")
        engine = UMHVersionCoherenceEngine(registry=reg)
        status = engine.node_version_status("umh-vps")
        assert status["matches_canonical"] is True

    def test_node_version_status_drifted(self) -> None:
        from substrate.organism.umh_version_coherence import UMHVersionCoherenceEngine

        reg = self._make_registry_with_versions("abc123", "def456")
        engine = UMHVersionCoherenceEngine(registry=reg)
        status = engine.node_version_status("umh-windows")
        assert status["matches_canonical"] is False
        assert "git_commit" in status["drift_fields"]

    def test_node_version_status_not_found(self) -> None:
        from substrate.organism.umh_version_coherence import UMHVersionCoherenceEngine

        reg = self._make_registry_with_versions("abc123", "abc123")
        engine = UMHVersionCoherenceEngine(registry=reg)
        status = engine.node_version_status("nonexistent")
        assert status["found"] is False


class TestWorkspaceNodeLinks(unittest.TestCase):
    """Test workspace-node linking from Phase 27 enrichment."""

    def setUp(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry

        self.registry = WorkspaceRegistry()

    def test_umh_has_both_devices(self) -> None:
        ws = self.registry.get("umh")
        assert ws is not None
        assert "vps" in ws.device_ids
        assert "beast" in ws.device_ids

    def test_umh_primary_node_is_vps(self) -> None:
        ws = self.registry.get("umh")
        assert ws is not None
        assert ws.primary_umh_node_id == "umh-vps"

    def test_umh_supporting_includes_windows(self) -> None:
        ws = self.registry.get("umh")
        assert ws is not None
        assert "umh-windows" in ws.supporting_umh_node_ids

    def test_creatoros_primary_is_windows(self) -> None:
        ws = self.registry.get("creatoros")
        assert ws is not None
        assert ws.primary_umh_node_id == "umh-windows"

    def test_creatoros_supporting_is_vps(self) -> None:
        ws = self.registry.get("creatoros")
        assert ws is not None
        assert "umh-vps" in ws.supporting_umh_node_ids

    def test_workspace_definition_serialization(self) -> None:
        ws = self.registry.get("umh")
        assert ws is not None
        d = ws.to_dict()
        assert d["primary_umh_node_id"] == "umh-vps"
        assert "umh-windows" in d["supporting_umh_node_ids"]
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceDefinition

        rebuilt = WorkspaceDefinition.from_dict(d)
        assert rebuilt.primary_umh_node_id == "umh-vps"


class TestRoutingHints(unittest.TestCase):
    """Test routing hint fields on PacketPlacement."""

    def test_placement_has_node_fields(self) -> None:
        from substrate.organism.packet_router import PacketPlacement

        p = PacketPlacement()
        assert hasattr(p, "preferred_node_id")
        assert hasattr(p, "node_role_match")
        assert hasattr(p, "version_coherent")

    def test_placement_defaults(self) -> None:
        from substrate.organism.packet_router import PacketPlacement

        p = PacketPlacement()
        assert p.preferred_node_id == ""
        assert p.node_role_match == ""
        assert p.version_coherent is True

    def test_placement_serializes_node_fields(self) -> None:
        from substrate.organism.packet_router import PacketPlacement

        p = PacketPlacement(
            preferred_node_id="umh-vps",
            node_role_match="umh-vps",
            version_coherent=True,
        )
        d = p.to_dict()
        assert d["preferred_node_id"] == "umh-vps"
        assert d["node_role_match"] == "umh-vps"
        assert d["version_coherent"] is True

    def test_routing_does_not_override_capability(self) -> None:
        """Capability-first routing is unchanged by node hints."""
        from substrate.organism.packet_router import PacketRouter
        from substrate.organism.worker_registry import WorkerRegistry
        from substrate.organism.device_capacity import DeviceCapacityModel

        wr = WorkerRegistry()
        profiles = []
        try:
            from substrate.organism.device_role_registry import load_registry, seed_known_nodes

            profiles = load_registry() or seed_known_nodes()
        except Exception:
            pass
        cm = DeviceCapacityModel(wr, profiles)
        router = PacketRouter(wr, cm)

        packet = MagicMock()
        packet.packet_id = "test"
        packet.description = "run some code"
        packet.target_repo = ""
        packet.workspace_id = "umh"
        packet.required_service_role = ""

        placement = router.route(packet)
        assert placement.required_capability == "code_execution"

    def test_routing_adds_node_hint_to_chain(self) -> None:
        from substrate.organism.packet_router import PacketRouter
        from substrate.organism.worker_registry import WorkerRegistry
        from substrate.organism.device_capacity import DeviceCapacityModel

        wr = WorkerRegistry()
        profiles = []
        try:
            from substrate.organism.device_role_registry import load_registry, seed_known_nodes

            profiles = load_registry() or seed_known_nodes()
        except Exception:
            pass
        cm = DeviceCapacityModel(wr, profiles)
        router = PacketRouter(wr, cm)

        packet = MagicMock()
        packet.packet_id = "test"
        packet.description = "build something"
        packet.target_repo = ""
        packet.workspace_id = "umh"
        packet.required_service_role = ""

        placement = router.route(packet)
        has_node_hint = any("node_hint:" in step for step in placement.routing_chain)
        assert has_node_hint is True

    def test_routing_without_workspace_has_no_hint(self) -> None:
        from substrate.organism.packet_router import PacketRouter
        from substrate.organism.worker_registry import WorkerRegistry
        from substrate.organism.device_capacity import DeviceCapacityModel

        wr = WorkerRegistry()
        profiles = []
        try:
            from substrate.organism.device_role_registry import load_registry, seed_known_nodes

            profiles = load_registry() or seed_known_nodes()
        except Exception:
            pass
        cm = DeviceCapacityModel(wr, profiles)
        router = PacketRouter(wr, cm)

        packet = MagicMock()
        packet.packet_id = "test"
        packet.description = "write docs"
        packet.target_repo = ""
        packet.workspace_id = ""
        packet.required_service_role = ""

        placement = router.route(packet)
        has_node_hint = any("node_hint:" in step for step in placement.routing_chain)
        assert has_node_hint is False


class TestCockpitRoutes(unittest.TestCase):
    """Test cockpit route module structure."""

    def test_import(self) -> None:
        from transports.api import cockpit_umh_node_routes

        assert cockpit_umh_node_routes is not None

    def test_configure_callable(self) -> None:
        from transports.api import cockpit_umh_node_routes

        assert callable(cockpit_umh_node_routes.configure)

    def test_router_exists(self) -> None:
        from transports.api import cockpit_umh_node_routes

        assert cockpit_umh_node_routes.umh_node_router is not None

    def test_singleton_configure(self) -> None:
        from transports.api import cockpit_umh_node_routes

        dep = MagicMock()
        cockpit_umh_node_routes._configured = False
        cockpit_umh_node_routes.configure(require_operator_dep=dep)
        assert cockpit_umh_node_routes._configured is True


class TestTypeRegistration(unittest.TestCase):
    """Test canonical type registration for Phase 28."""

    def test_types_in_registry(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        phase28_types = [
            "UMHNodeRole",
            "UMHNodeStatus",
            "UMHServiceRole",
            "UMHVersionStatus",
            "UMHVersionInfo",
            "UMHServiceActivation",
            "UMHNodeRecord",
            "UMHNodeTopology",
            "UMHNodeRegistry",
            "UMHVersionCoherenceEngine",
        ]
        for t in phase28_types:
            assert t in CANONICAL_TYPES, f"{t} not in CANONICAL_TYPES"

    def test_no_collision_with_existing(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        umh_types = [k for k in CANONICAL_TYPES if k.startswith("UMH")]
        assert len(umh_types) == 10

    def test_canonical_lookup(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        assert CANONICAL_TYPES["UMHNodeRole"] == ["substrate.organism.umh_node_topology"]
        assert CANONICAL_TYPES["UMHNodeRegistry"] == ["substrate.organism.umh_node_registry"]
        assert CANONICAL_TYPES["UMHVersionCoherenceEngine"] == [
            "substrate.organism.umh_version_coherence"
        ]

    def test_import_from_canonical_location(self) -> None:
        from substrate.organism.umh_node_topology import UMHNodeRole as NR1
        from substrate.organism.umh_node_registry import UMHNodeRegistry as NR2
        from substrate.organism.umh_version_coherence import UMHVersionCoherenceEngine as VCE

        assert NR1 is not None
        assert NR2 is not None
        assert VCE is not None


class TestIntegration(unittest.TestCase):
    """End-to-end integration tests."""

    def test_full_topology_chain(self) -> None:
        from substrate.organism.umh_node_registry import UMHNodeRegistry
        from substrate.organism.umh_version_coherence import UMHVersionCoherenceEngine

        reg = UMHNodeRegistry()
        engine = UMHVersionCoherenceEngine(registry=reg)
        report = engine.drift_report()
        assert report["node_count"] == 2
        assert report["overall_status"] in ("coherent", "drifted", "unknown")

    def test_node_registry_composes_with_workspace(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        ws_reg = WorkspaceRegistry()
        node_reg = UMHNodeRegistry()

        umh_ws = ws_reg.get("umh")
        assert umh_ws is not None
        primary = node_reg.get_node(umh_ws.primary_umh_node_id)
        assert primary is not None
        assert primary.node_id == "umh-vps"

    def test_windows_node_serves_product_workspaces(self) -> None:
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        reg = UMHNodeRegistry()
        win = reg.get_node("umh-windows")
        assert win is not None
        assert "creatoros" in win.workspace_ids
        assert "entrepreneuros" in win.workspace_ids
        assert "lyfeos" in win.workspace_ids

    def test_vps_and_windows_same_organism(self) -> None:
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        reg = UMHNodeRegistry()
        topology = reg.topology()
        assert topology.organism_id == "umh"
        assert len(topology.nodes) == 2

    def test_governance_resolves_to_vps(self) -> None:
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        reg = UMHNodeRegistry()
        nodes = reg.nodes_for_service("governance")
        assert len(nodes) == 1
        assert nodes[0].device_id == "vps"

    def test_meta_ide_resolves_to_windows(self) -> None:
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        reg = UMHNodeRegistry()
        nodes = reg.nodes_for_service("meta_ide")
        assert len(nodes) == 1
        assert nodes[0].device_id == "beast"

    def test_distributed_runtime_node_topology(self) -> None:
        from substrate.organism.distributed_runtime import DistributedRuntime

        dr = DistributedRuntime()
        nt = dr.node_topology()
        assert "nodes" in nt
        assert nt["node_count"] == 2

    def test_workspace_topology_engine_workspace_nodes(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        result = engine.workspace_nodes("umh")
        assert result is not None
        assert result["primary_umh_node_id"] == "umh-vps"
        assert result["primary_node"] is not None
        assert result["primary_node"]["node_id"] == "umh-vps"
        assert len(result["supporting_nodes"]) == 1


if __name__ == "__main__":
    unittest.main()
