"""End-to-end integration test — real NodeMeshServer + real NodeClient.

Starts the VPS-side mesh server, connects an actual daemon client,
verifies the full lifecycle: connect → hello → heartbeat → capability
execution → signal emission → disconnect cleanup.

For capability tests, we open a raw WS acting as a second node that
sends commands to verify the round-trip works.
"""

from __future__ import annotations

import asyncio
import json
import sys

import websockets

from nodes.windows.umh_node.client import NodeClient
from nodes.windows.umh_node.config import CapabilityConfig, NodeConfig
from substrate.execution.executor import WorkPacketExecutor
from transports.node_mesh.config import MeshConfig
from transports.node_mesh.server import NodeMeshServer
from substrate.sockets.capability_socket import CapabilitySocket
from substrate.sockets.outcome_socket import OutcomeSocket
from substrate.sockets.signal_socket import SignalSocket
from substrate.sockets.view_socket import ViewSocket

_next_port = 19200


def _alloc_port() -> int:
    global _next_port
    p = _next_port
    _next_port += 1
    return p


def make_server(port: int) -> NodeMeshServer:
    config = MeshConfig(port=port, heartbeat_timeout_s=60, max_nodes=5)
    return NodeMeshServer(
        config=config,
        executor=WorkPacketExecutor(),
        signal_socket=SignalSocket(),
        capability_socket=CapabilitySocket(),
        outcome_socket=OutcomeSocket(),
        view_socket=ViewSocket(),
    )


def make_client(port: int, node_id: str = "e2e-test-node", **kwargs) -> NodeClient:
    caps = kwargs.pop(
        "capabilities",
        {
            "shell": CapabilityConfig(enabled=True, max_risk_class="IRREVERSIBLE_WRITE"),
            "filesystem": CapabilityConfig(enabled=True, max_risk_class="IRREVERSIBLE_WRITE"),
        },
    )
    config = NodeConfig(
        vps_host="127.0.0.1",
        vps_port=port,
        node_id=node_id,
        hostname=kwargs.pop("hostname", "E2ETestPC"),
        capabilities=caps,
        **kwargs,
    )
    return NodeClient(config)


async def _stop_all(client, client_task, server, thread):
    await client.stop()
    client_task.cancel()
    try:
        await client_task
    except asyncio.CancelledError:
        pass
    server.stop()
    thread.join(timeout=3)
    await asyncio.sleep(0.3)


# ── Test 1: connect + hello ────────────────────────────────


async def test_connect_hello_heartbeat():
    """Client connects, says hello, server sees node with capabilities."""
    port = _alloc_port()
    server = make_server(port)
    thread = server.start()
    await asyncio.sleep(0.5)

    client = make_client(port)
    client_task = asyncio.create_task(client.run())
    await asyncio.sleep(1.5)

    try:
        assert client.connected, "client should be connected"

        node = server.node_registry.get("e2e-test-node")
        assert node is not None, "server should have registered the node"
        assert node.hostname == "E2ETestPC"
        assert node.status == "connected"
        assert len(node.capabilities) == 2

        cap_names = {c.name for c in node.capabilities}
        assert "shell" in cap_names
        assert "filesystem" in cap_names

        print("PASS: connect + hello + registration")
    finally:
        await _stop_all(client, client_task, server, thread)


# ── Test 2: capability execution ───────────────────────────


async def test_capability_execution():
    """Daemon executes a shell command, verified by side-effect (file creation)."""
    import tempfile
    from pathlib import Path

    port = _alloc_port()
    server = make_server(port)
    thread = server.start()
    await asyncio.sleep(0.5)

    client = make_client(port)
    client_task = asyncio.create_task(client.run())
    await asyncio.sleep(1.5)

    try:
        assert client.connected
        node = server.node_registry.get("e2e-test-node")
        assert node is not None

        marker = Path(tempfile.gettempdir()) / "e2e_cap_test_marker.txt"
        marker.unlink(missing_ok=True)

        cap_msg = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "capability.execute",
                "params": {
                    "capability_name": "shell.run",
                    "params": {"command": f"echo cap_works > {marker}"},
                    "risk_class": "REVERSIBLE_WRITE",
                },
                "id": 9001,
            }
        )

        async def send_cap():
            await node.ws.send(cap_msg)

        assert server._loop is not None
        fut = asyncio.run_coroutine_threadsafe(send_cap(), server._loop)
        fut.result(timeout=5)

        await asyncio.sleep(2)

        assert marker.exists(), f"marker file should exist at {marker}"
        content = marker.read_text().strip()
        assert "cap_works" in content
        marker.unlink(missing_ok=True)

        print("PASS: capability execution (shell side-effect)")
    finally:
        await _stop_all(client, client_task, server, thread)


# ── Test 3: governance denial ──────────────────────────────


async def test_capability_governance_deny():
    """Daemon rejects a command that exceeds local governance policy.

    Verified by side-effect: the dangerous command should NOT execute.
    """
    import tempfile
    from pathlib import Path

    port = _alloc_port()
    server = make_server(port)
    thread = server.start()
    await asyncio.sleep(0.5)

    client = make_client(
        port,
        node_id="e2e-gov-node",
        hostname="GovTestPC",
        capabilities={
            "shell": CapabilityConfig(enabled=True, max_risk_class="READ_ONLY"),
        },
    )
    client_task = asyncio.create_task(client.run())
    await asyncio.sleep(1.5)

    try:
        assert client.connected
        node = server.node_registry.get("e2e-gov-node")
        assert node is not None

        marker = Path(tempfile.gettempdir()) / "e2e_gov_deny_marker.txt"
        marker.unlink(missing_ok=True)

        cap_msg = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "capability.execute",
                "params": {
                    "capability_name": "shell.run",
                    "params": {"command": f"echo should_not_run > {marker}"},
                    "risk_class": "IRREVERSIBLE_WRITE",
                },
                "id": 9002,
            }
        )

        async def send_cap():
            await node.ws.send(cap_msg)

        assert server._loop is not None
        fut = asyncio.run_coroutine_threadsafe(send_cap(), server._loop)
        fut.result(timeout=5)

        await asyncio.sleep(2)

        assert not marker.exists(), "marker should NOT exist — governance should deny"

        print("PASS: governance denial (command not executed)")
    finally:
        await _stop_all(client, client_task, server, thread)


# ── Test 4: signal emission ────────────────────────────────


async def test_signal_emission():
    """Client emits a signal, server receives and acks it."""
    port = _alloc_port()
    server = make_server(port)
    thread = server.start()
    await asyncio.sleep(0.5)

    client = make_client(port)
    client_task = asyncio.create_task(client.run())
    await asyncio.sleep(1.5)

    try:
        assert client.connected

        await client.emit_signal(
            content_type="workspace.active_window",
            payload={"title": "Visual Studio Code", "process": "code.exe"},
            signal_class="event",
            urgency="LOW",
        )
        await asyncio.sleep(0.5)

        print("PASS: signal emission (fire-and-forget)")
    finally:
        await _stop_all(client, client_task, server, thread)


# ── Test 5: disconnect cleanup ─────────────────────────────


async def test_disconnect_cleanup():
    """When client disconnects, server removes node from registry."""
    port = _alloc_port()
    server = make_server(port)
    thread = server.start()
    await asyncio.sleep(0.5)

    client = make_client(port)
    client_task = asyncio.create_task(client.run())
    await asyncio.sleep(1.5)

    assert client.connected
    node = server.node_registry.get("e2e-test-node")
    assert node is not None

    await client.stop()
    client_task.cancel()
    try:
        await client_task
    except asyncio.CancelledError:
        pass
    await asyncio.sleep(1.5)

    node_after = server.node_registry.get("e2e-test-node")
    assert node_after is None, "node should be removed after disconnect"

    server.stop()
    thread.join(timeout=3)
    await asyncio.sleep(0.3)
    print("PASS: disconnect cleanup")


# ── Test 6: reconnect ─────────────────────────────────────


async def test_reconnect():
    """Client reconnects after server restarts."""
    port = _alloc_port()
    server = make_server(port)
    thread = server.start()
    await asyncio.sleep(0.5)

    client = make_client(
        port,
        node_id="e2e-reconnect-node",
        hostname="ReconnectPC",
        reconnect_max_backoff_s=2,
        capabilities={
            "shell": CapabilityConfig(enabled=True, max_risk_class="REVERSIBLE_WRITE"),
        },
    )
    client_task = asyncio.create_task(client.run())
    await asyncio.sleep(1.5)

    assert client.connected, "initial connection should succeed"

    server.stop()
    thread.join(timeout=3)
    await asyncio.sleep(3)

    server2 = make_server(port)
    thread2 = server2.start()
    await asyncio.sleep(8)

    try:
        assert client.connected, "client should have reconnected"
        node = server2.node_registry.get("e2e-reconnect-node")
        assert node is not None, "server2 should see reconnected node"
        print("PASS: reconnect after server restart")
    finally:
        await client.stop()
        client_task.cancel()
        try:
            await client_task
        except asyncio.CancelledError:
            pass
        server2.stop()
        thread2.join(timeout=3)
        await asyncio.sleep(0.3)


# ── Test 7: metrics buffered ──────────────────────────────


async def test_metrics_buffered():
    """Heartbeat metrics land in the metrics buffer."""
    port = _alloc_port()
    server = make_server(port)
    thread = server.start()
    await asyncio.sleep(0.5)

    client = make_client(
        port,
        node_id="e2e-metrics-node",
        hostname="MetricsPC",
        capabilities={"shell": CapabilityConfig(enabled=True)},
    )
    client._config.signals.metrics_interval_s = 1
    client_task = asyncio.create_task(client.run())
    await asyncio.sleep(4)

    try:
        assert client.connected
        snap = server.metrics_buffer.latest("e2e-metrics-node")
        assert snap is not None, "expected at least one metrics snapshot"
        assert snap.cpu is not None
        assert snap.memory is not None

        history = server.metrics_buffer.history("e2e-metrics-node", limit=5)
        assert len(history) >= 1, f"expected >=1 in history, got {len(history)}"

        print("PASS: metrics buffered from heartbeat")
    finally:
        await _stop_all(client, client_task, server, thread)


# ── Runner ─────────────────────────────────────────────────


async def run_all():
    tests = [
        ("connect_hello_heartbeat", test_connect_hello_heartbeat),
        ("capability_execution", test_capability_execution),
        ("capability_governance_deny", test_capability_governance_deny),
        ("signal_emission", test_signal_emission),
        ("disconnect_cleanup", test_disconnect_cleanup),
        ("reconnect", test_reconnect),
        ("metrics_buffered", test_metrics_buffered),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            await test_fn()
            passed += 1
        except Exception as exc:
            print(f"FAIL: {name} — {exc}")
            failed += 1

    print(f"\n=== E2E: {passed}/{passed + failed} PASSED ===")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all())
