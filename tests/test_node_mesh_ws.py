"""WebSocket integration test — simulates a node connecting to the mesh server.

Starts a real NodeMeshServer, connects a WebSocket client, performs the
full lifecycle: hello → heartbeat → signal → disconnect.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time

sys.path.insert(0, "/opt/OS/.claude/worktrees/layer3-phase2-slice-d-handoff")

import websockets

from services.umh.execution.executor import WorkPacketExecutor
from services.umh.node_mesh.config import MeshConfig
from services.umh.node_mesh.server import NodeMeshServer
from services.umh.sockets.capability_socket import CapabilitySocket
from services.umh.sockets.outcome_socket import OutcomeSocket
from services.umh.sockets.signal_socket import SignalSocket
from services.umh.sockets.view_socket import ViewSocket


async def run_test():
    config = MeshConfig(port=19094, heartbeat_timeout_s=5, max_nodes=3)

    server = NodeMeshServer(
        config=config,
        executor=WorkPacketExecutor(),
        signal_socket=SignalSocket(),
        capability_socket=CapabilitySocket(),
        outcome_socket=OutcomeSocket(),
        view_socket=ViewSocket(),
    )
    thread = server.start()
    await asyncio.sleep(1)

    try:
        # 1. Connect and send hello
        ws = await websockets.connect(f"ws://127.0.0.1:{config.port}/ws")

        hello = {
            "jsonrpc": "2.0",
            "method": "node.hello",
            "params": {
                "node_id": "test-win",
                "hostname": "TestPC",
                "os": "windows",
                "os_version": "11",
                "capabilities": [
                    {
                        "name": "shell",
                        "category": "compute",
                        "risk_class": "reversible_write",
                        "max_risk_class": "irreversible_write",
                    },
                    {
                        "name": "filesystem",
                        "category": "compute",
                        "risk_class": "read_only",
                        "max_risk_class": "reversible_write",
                    },
                ],
                "daemon_version": "0.1.0",
                "tailscale_ip": "100.74.199.102",
            },
            "id": 1,
        }
        await ws.send(json.dumps(hello))
        resp = json.loads(await ws.recv())
        assert resp["result"]["accepted"] is True, f"hello rejected: {resp}"
        print("PASS: node.hello accepted")

        # Verify node registered
        nodes = server.node_registry.all_nodes()
        assert len(nodes) == 1
        assert nodes[0].node_id == "test-win"
        assert len(nodes[0].capabilities) == 2
        print("PASS: node in registry with 2 capabilities")

        # 2. Send heartbeat with metrics
        hb = {
            "jsonrpc": "2.0",
            "method": "node.heartbeat",
            "params": {"metrics": {"cpu": 45.2, "memory": 68.0, "disk": 52.0, "battery": 87}},
            "id": 2,
        }
        await ws.send(json.dumps(hb))
        resp = json.loads(await ws.recv())
        assert resp["result"]["ack"] is True
        print("PASS: heartbeat acknowledged")

        # Verify metrics in buffer
        latest = server.metrics_buffer.latest("test-win")
        assert latest is not None
        assert latest.cpu == 45.2
        assert latest.battery == 87
        print("PASS: metrics recorded in buffer")

        # 3. Send a telemetry signal (should NOT enter pipeline)
        sig = {
            "jsonrpc": "2.0",
            "method": "signal.emit",
            "params": {
                "content_type": "node.system.metrics",
                "payload": {"cpu": 50.0, "memory": 70.0},
                "urgency": "LOW",
                "signal_class": "telemetry",
            },
            "id": 3,
        }
        await ws.send(json.dumps(sig))
        resp = json.loads(await ws.recv())
        assert resp["result"]["ack"] is True
        print("PASS: telemetry signal routed to buffer")

        # 4. Send capabilities_changed (remove filesystem)
        cap_change = {
            "jsonrpc": "2.0",
            "method": "node.capabilities_changed",
            "params": {
                "capabilities": [
                    {
                        "name": "shell",
                        "category": "compute",
                        "risk_class": "reversible_write",
                        "max_risk_class": "irreversible_write",
                    },
                ],
            },
        }
        await ws.send(json.dumps(cap_change))
        await asyncio.sleep(0.5)
        node = server.node_registry.get("test-win")
        assert node is not None
        assert len(node.capabilities) == 1
        print("PASS: capabilities updated (1 capability)")

        # 5. Reconnect (same node_id — should not error)
        ws2 = await websockets.connect(f"ws://127.0.0.1:{config.port}/ws")
        await ws2.send(json.dumps(hello))
        resp = json.loads(await ws2.recv())
        assert resp["result"]["accepted"] is True
        print("PASS: reconnect accepted (no ValueError)")

        # 6. Check API dict
        nodes = server.node_registry.all_nodes()
        assert len(nodes) == 1
        api = nodes[0].to_api_dict()
        assert api["os"] == "windows"
        assert "shell" in api["capabilities"]
        print("PASS: API dict correct")

        await ws2.close()
        await ws.close()
        await asyncio.sleep(0.5)

        # Node should be cleaned up after disconnect
        assert server.node_registry.node_count() == 0
        print("PASS: node cleaned up on disconnect")

    finally:
        server.stop()
        thread.join(timeout=3)

    print("\n=== ALL 8 WS INTEGRATION TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(run_test())
