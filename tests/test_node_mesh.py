"""Node mesh integration tests — verifies the full VPS-side stack.

Tests:
1. Socket unregister methods (prerequisite changes)
2. Registry re-registration (no ValueError on reconnect)
3. Executor unregister_adapter
4. MetricsBuffer ring behavior
5. NodeRegistry CRUD and heartbeat detection
6. NodeSignalEmitter protocol compliance
7. NodeCapabilityHandler descriptor building
8. NodeOutcomeReceiver protocol compliance
9. build_node_manifest produces valid IntegrationManifest
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(0, "/opt/OS/.claude/worktrees/layer3-phase2-slice-d-handoff")


def test_signal_socket_unregister():
    from substrate.sockets.signal_socket import SignalSocket
    from substrate.sockets.protocols import SignalDescriptor

    class FakeEmitter:
        @property
        def integration_id(self) -> str:
            return "test-emitter"

        def describe_signals(self):
            return [SignalDescriptor("test.signal", "test")]

    sock = SignalSocket()
    sock.register_emitter(FakeEmitter())
    assert "test-emitter" in sock.registered_integrations()

    sock.unregister_emitter("test-emitter")
    assert "test-emitter" not in sock.registered_integrations()

    # idempotent
    sock.unregister_emitter("test-emitter")
    print("PASS: signal_socket unregister")


def test_capability_socket_unregister():
    from substrate.sockets.capability_socket import CapabilitySocket
    from substrate.sockets.protocols import CapabilityDescriptor, CapabilityHealth
    from substrate.sockets.envelopes import CapabilityRequest, CapabilityResponse
    from substrate.governance.risk_classes import RiskClass
    from substrate.types import CapabilityCategory

    class FakeHandler:
        @property
        def integration_id(self) -> str:
            return "test-handler"

        def describe_capabilities(self):
            return [
                CapabilityDescriptor("test.cap", CapabilityCategory.COMPUTE, RiskClass.READ_ONLY)
            ]

        def handle_capability(self, req):
            return CapabilityResponse(request_id=req.request_id, success=True)

        def health(self):
            return CapabilityHealth("test-handler", "healthy")

    sock = CapabilitySocket()
    sock.register_handler(FakeHandler())
    assert "test-handler" in sock.capability_catalog()

    sock.unregister_handler("test-handler")
    assert "test-handler" not in sock.capability_catalog()

    sock.unregister_handler("test-handler")
    print("PASS: capability_socket unregister")


def test_outcome_socket_unregister():
    from substrate.sockets.outcome_socket import OutcomeSocket

    class FakeReceiver:
        @property
        def integration_id(self) -> str:
            return "test-receiver"

        def on_outcome(self, envelope):
            pass

        def accepts_outcomes(self):
            return []

    sock = OutcomeSocket()
    sock.register_receiver(FakeReceiver())
    assert "test-receiver" in sock.registered_receivers()

    sock.unregister_receiver("test-receiver")
    assert "test-receiver" not in sock.registered_receivers()

    sock.unregister_receiver("test-receiver")
    print("PASS: outcome_socket unregister")


def test_registry_reregistration():
    from substrate.sockets.capability_socket import CapabilitySocket
    from substrate.sockets.outcome_socket import OutcomeSocket
    from substrate.sockets.signal_socket import SignalSocket
    from substrate.sockets.view_socket import ViewSocket
    from substrate.sockets.registry import IntegrationManifest, IntegrationRegistry
    from substrate.sockets.protocols import (
        CapabilityDescriptor,
        CapabilityHealth,
        SignalDescriptor,
    )
    from substrate.sockets.envelopes import CapabilityResponse
    from substrate.governance.risk_classes import RiskClass
    from substrate.types import CapabilityCategory

    class FakeEmitter:
        @property
        def integration_id(self) -> str:
            return "test-reregister"

        def describe_signals(self):
            return [SignalDescriptor("test.signal", "test")]

    class FakeHandler:
        @property
        def integration_id(self) -> str:
            return "test-reregister"

        def describe_capabilities(self):
            return [
                CapabilityDescriptor("test.cap", CapabilityCategory.COMPUTE, RiskClass.READ_ONLY)
            ]

        def handle_capability(self, req):
            return CapabilityResponse(request_id=req.request_id, success=True)

        def health(self):
            return CapabilityHealth("test-reregister", "healthy")

    class FakeReceiver:
        @property
        def integration_id(self) -> str:
            return "test-reregister"

        def on_outcome(self, envelope):
            pass

        def accepts_outcomes(self):
            return []

    registry = IntegrationRegistry(
        SignalSocket(), CapabilitySocket(), OutcomeSocket(), ViewSocket()
    )

    manifest1 = IntegrationManifest(
        integration_id="test-reregister",
        signal_emitter=FakeEmitter(),
        capability_handler=FakeHandler(),
        outcome_receiver=FakeReceiver(),
    )
    adapter1 = registry.register(manifest1)
    assert adapter1 is not None

    # Re-register without ValueError
    manifest2 = IntegrationManifest(
        integration_id="test-reregister",
        signal_emitter=FakeEmitter(),
        capability_handler=FakeHandler(),
        outcome_receiver=FakeReceiver(),
    )
    adapter2 = registry.register(manifest2)
    assert adapter2 is not None
    assert "test-reregister" in registry.registered()

    # Unregister cleans up
    registry.unregister("test-reregister")
    assert "test-reregister" not in registry.registered()
    print("PASS: registry re-registration")


def test_executor_unregister():
    from substrate.execution.executor import WorkPacketExecutor

    class FakeAdapter:
        @property
        def name(self) -> str:
            return "test-adapter"

        def execute(self, op, params):
            return {}

        def classify_risk(self, op, params):
            from substrate.governance.risk_classes import RiskClass

            return RiskClass.READ_ONLY

    executor = WorkPacketExecutor()
    executor.register_adapter(FakeAdapter())
    assert "test-adapter" in executor.registered_adapters

    executor.unregister_adapter("test-adapter")
    assert "test-adapter" not in executor.registered_adapters

    executor.unregister_adapter("nonexistent")
    print("PASS: executor unregister_adapter")


def test_metrics_buffer():
    from transports.node_mesh.metrics_buffer import MetricsBuffer, MetricsSnapshot

    buf = MetricsBuffer(buffer_size=5)

    for i in range(10):
        buf.record(
            MetricsSnapshot(
                node_id="test-node",
                timestamp=f"2026-01-01T00:00:{i:02d}Z",
                cpu=float(i * 10),
            )
        )

    latest = buf.latest("test-node")
    assert latest is not None
    assert latest.cpu == 90.0

    history = buf.history("test-node")
    assert len(history) == 5  # ring buffer capped at 5

    buf.remove_node("test-node")
    assert buf.latest("test-node") is None
    print("PASS: metrics_buffer ring behavior")


def test_node_registry():
    from transports.node_mesh.registry import ConnectedNode, NodeCapability, NodeRegistry

    reg = NodeRegistry(heartbeat_timeout_s=1.0)

    node = ConnectedNode(
        node_id="test-node",
        hostname="TestPC",
        os="windows",
        os_version="11",
        capabilities=[NodeCapability("shell", "system", "REVERSIBLE_WRITE", "IRREVERSIBLE_WRITE")],
        daemon_version="0.1.0",
        tailscale_ip="100.0.0.1",
        ws=None,
    )
    reg.add(node)
    assert reg.node_count() == 1
    assert reg.get("test-node") is not None

    reg.update_heartbeat("test-node", {"cpu": 50})
    fetched = reg.get("test-node")
    assert fetched is not None
    assert fetched.latest_metrics.get("cpu") == 50

    api = fetched.to_api_dict()
    assert api["id"] == "test-node"
    assert api["os"] == "windows"
    assert "shell" in api["capabilities"]

    reg.remove("test-node")
    assert reg.node_count() == 0
    print("PASS: node_registry CRUD")


def test_node_registry_stale_detection():
    from transports.node_mesh.registry import ConnectedNode, NodeCapability, NodeRegistry

    reg = NodeRegistry(heartbeat_timeout_s=0.1)
    node = ConnectedNode(
        node_id="stale-node",
        hostname="X",
        os="linux",
        os_version="6",
        capabilities=[],
        daemon_version="0.1.0",
        tailscale_ip="",
        ws=None,
    )
    reg.add(node)
    time.sleep(0.2)

    stale = reg.stale_nodes()
    assert "stale-node" in stale
    reg.remove("stale-node")
    print("PASS: node_registry stale detection")


def test_node_signal_emitter():
    from substrate.integrations.node_mesh.signals import NodeSignalEmitter
    from substrate.sockets.protocols import SignalEmitter

    emitter = NodeSignalEmitter("test-node")
    assert isinstance(emitter, SignalEmitter)
    assert emitter.integration_id == "node-test-node"
    signals = emitter.describe_signals()
    assert len(signals) == 5
    types = {s.content_type for s in signals}
    assert "node.system.metrics" in types
    assert "node.connected" in types
    print("PASS: NodeSignalEmitter protocol compliance")


def test_node_capability_handler_descriptors():
    from substrate.integrations.node_mesh.handlers import NodeCapabilityHandler
    from transports.node_mesh.registry import ConnectedNode, NodeCapability
    from substrate.sockets.protocols import CapabilityHandler

    node = ConnectedNode(
        node_id="test-node",
        hostname="PC",
        os="windows",
        os_version="11",
        capabilities=[
            NodeCapability("shell", "compute", "reversible_write", "irreversible_write"),
            NodeCapability("filesystem", "compute", "read_only", "reversible_write"),
        ],
        daemon_version="0.1.0",
        tailscale_ip="",
        ws=None,
    )
    handler = NodeCapabilityHandler(node)
    assert isinstance(handler, CapabilityHandler)
    assert handler.integration_id == "node-test-node"
    caps = handler.describe_capabilities()
    assert len(caps) == 2
    names = {c.name for c in caps}
    assert "shell" in names
    assert "filesystem" in names
    print("PASS: NodeCapabilityHandler descriptors")


def test_node_outcome_receiver():
    from substrate.integrations.node_mesh.outcomes import NodeOutcomeReceiver
    from substrate.sockets.protocols import OutcomeReceiver

    receiver = NodeOutcomeReceiver("test-node", ws=None)
    assert isinstance(receiver, OutcomeReceiver)
    assert receiver.integration_id == "node-test-node"
    assert receiver.accepts_outcomes() == []
    print("PASS: NodeOutcomeReceiver protocol compliance")


def test_build_node_manifest():
    from substrate.integrations.node_mesh.manifest import build_node_manifest
    from transports.node_mesh.registry import ConnectedNode, NodeCapability
    from substrate.sockets.registry import IntegrationManifest

    node = ConnectedNode(
        node_id="win-pc",
        hostname="WinPC",
        os="windows",
        os_version="11",
        capabilities=[NodeCapability("shell", "compute", "reversible_write", "irreversible_write")],
        daemon_version="0.1.0",
        tailscale_ip="100.74.199.102",
        ws=None,
    )
    manifest = build_node_manifest(node)
    assert isinstance(manifest, IntegrationManifest)
    assert manifest.integration_id == "node-win-pc"
    assert manifest.signal_emitter is not None
    assert manifest.capability_handler is not None
    assert manifest.outcome_receiver is not None
    print("PASS: build_node_manifest")


if __name__ == "__main__":
    test_signal_socket_unregister()
    test_capability_socket_unregister()
    test_outcome_socket_unregister()
    test_registry_reregistration()
    test_executor_unregister()
    test_metrics_buffer()
    test_node_registry()
    test_node_registry_stale_detection()
    test_node_signal_emitter()
    test_node_capability_handler_descriptors()
    test_node_outcome_receiver()
    test_build_node_manifest()
    print("\n=== ALL 12 TESTS PASSED ===")
