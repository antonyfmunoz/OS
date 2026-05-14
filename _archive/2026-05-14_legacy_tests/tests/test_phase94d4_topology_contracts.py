"""Tests for Phase 94D.4 topology contracts."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import pytest

from runtime.substrate.topology_contracts import (
    InterfaceProfile,
    InterfaceRole,
    NodeProfile,
    NodeRole,
    NodeType,
    TopologyProfile,
    TransportProfile,
    TransportType,
    build_founder_current_topology,
    build_single_local_topology,
)


class TestNodeProfile:
    def test_has_role(self):
        node = NodeProfile(
            node_id="n1",
            node_type=NodeType.CLOUD_VPS,
            roles=[NodeRole.ORCHESTRATOR, NodeRole.CONTROL_PLANE],
            capabilities=["llm_inference"],
        )
        assert node.has_role(NodeRole.ORCHESTRATOR)
        assert not node.has_role(NodeRole.WORKER)

    def test_has_capability(self):
        node = NodeProfile(
            node_id="n1",
            node_type=NodeType.LOCAL_WORKSTATION,
            roles=[NodeRole.WORKER],
            capabilities=["gui_computer_use", "browser_session"],
        )
        assert node.has_capability("gui_computer_use")
        assert not node.has_capability("docker")

    def test_to_dict_and_from_dict_roundtrip(self):
        node = NodeProfile(
            node_id="test_node",
            node_type=NodeType.GPU_NODE,
            roles=[NodeRole.INFERENCE_NODE],
            capabilities=["gpu_compute", "llm_inference"],
            hostname="gpu-srv",
            os="linux",
            ip="10.0.0.5",
            online=True,
        )
        d = node.to_dict()
        restored = NodeProfile.from_dict(d)
        assert restored.node_id == "test_node"
        assert restored.node_type == NodeType.GPU_NODE
        assert NodeRole.INFERENCE_NODE in restored.roles
        assert "gpu_compute" in restored.capabilities


class TestTopologyProfile:
    def test_get_node(self):
        topo = build_founder_current_topology()
        assert topo.get_node("vps_orchestrator") is not None
        assert topo.get_node("nonexistent") is None

    def test_nodes_with_role(self):
        topo = build_founder_current_topology()
        orchestrators = topo.nodes_with_role(NodeRole.ORCHESTRATOR)
        assert len(orchestrators) == 1
        assert orchestrators[0].node_id == "vps_orchestrator"

    def test_nodes_with_capability(self):
        topo = build_founder_current_topology()
        gui_nodes = topo.nodes_with_capability("gui_computer_use")
        assert len(gui_nodes) == 1
        assert gui_nodes[0].node_id == "local_pc_worker"

    def test_to_dict_and_from_dict_roundtrip(self):
        topo = build_founder_current_topology()
        d = topo.to_dict()
        restored = TopologyProfile.from_dict(d)
        assert restored.topology_id == "founder_current"
        assert restored.owner_id == "antonyfm"
        assert len(restored.nodes) == 2

    def test_no_hardcoded_vps_assumption(self):
        topo = build_single_local_topology("alice")
        assert topo.owner_id == "alice"
        assert len(topo.nodes) == 1
        node = topo.nodes[0]
        assert node.has_role(NodeRole.ORCHESTRATOR)
        assert node.has_role(NodeRole.WORKER)
        assert node.has_capability("gui_computer_use")


class TestFounderTopology:
    def test_vps_has_correct_roles(self):
        topo = build_founder_current_topology()
        vps = topo.get_node("vps_orchestrator")
        assert vps is not None
        assert vps.has_role(NodeRole.ORCHESTRATOR)
        assert vps.has_role(NodeRole.CONTROL_PLANE)
        assert not vps.has_role(NodeRole.COMPUTER_USE_WORKER)

    def test_local_pc_has_correct_roles(self):
        topo = build_founder_current_topology()
        pc = topo.get_node("local_pc_worker")
        assert pc is not None
        assert pc.has_role(NodeRole.WORKER)
        assert pc.has_role(NodeRole.COMPUTER_USE_WORKER)
        assert not pc.has_role(NodeRole.ORCHESTRATOR)

    def test_gui_computer_use_only_on_local(self):
        topo = build_founder_current_topology()
        vps = topo.get_node("vps_orchestrator")
        pc = topo.get_node("local_pc_worker")
        assert not vps.has_capability("gui_computer_use")
        assert pc.has_capability("gui_computer_use")


class TestTransportProfile:
    def test_serialization(self):
        tp = TransportProfile(
            transport_type=TransportType.SSH,
            from_node="vps",
            to_node="local",
            endpoint="100.74.199.102",
            port=22,
            authenticated=True,
        )
        d = tp.to_dict()
        assert d["transport_type"] == "ssh"
        assert d["port"] == 22


class TestInterfaceProfile:
    def test_serialization(self):
        ip = InterfaceProfile(
            interface_id="cli_vps",
            interface_type="terminal",
            role=InterfaceRole.PRIMARY_COMMAND,
            node_id="vps_orchestrator",
            approval_capable=True,
            connected=True,
        )
        d = ip.to_dict()
        assert d["role"] == "primary_command"
        assert d["approval_capable"] is True
