"""Registration ownership must survive node reconnect races."""

from __future__ import annotations

import asyncio
import json
import socket
from uuid import uuid4

import pytest

from substrate.execution.durable_remote_transport import (
    DurableRemoteStore,
)
from substrate.execution.durable_remote_transport import (
    make_request as _make_request,
)
from substrate.execution.executor import WorkPacketExecutor
from substrate.sockets.capability_socket import CapabilitySocket
from substrate.sockets.outcome_socket import OutcomeSocket
from substrate.sockets.signal_socket import SignalSocket
from substrate.sockets.view_socket import ViewSocket
from transports.node_mesh.config import MeshConfig, NodeTokenEntry
from transports.node_mesh.server import NodeMeshServer


def make_request(**kwargs):
    kwargs.setdefault("idempotency_key", f"test-idem-{uuid4().hex}")
    return _make_request(**kwargs)


@pytest.fixture(autouse=True)
def _isolate_snapshot_path(tmp_path, monkeypatch):
    import transports.node_mesh.registry as reg_mod

    monkeypatch.setattr(reg_mod, "_SNAPSHOT_PATH", tmp_path / "mesh_nodes.json")


class _FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, payload: str | bytes) -> None:
        assert isinstance(payload, str)
        self.sent.append(json.loads(payload))


def _free_port_pair() -> int:
    for _ in range(100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as first:
            first.bind(("127.0.0.1", 0))
            port = int(first.getsockname()[1])
        if port >= 65535:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as second:
            try:
                second.bind(("127.0.0.1", port + 1))
            except OSError:
                continue
        return port
    raise RuntimeError("could not allocate free adjacent mesh test ports")


def _server(tmp_path, *, port: int | None = None) -> NodeMeshServer:
    server = NodeMeshServer(
        config=MeshConfig(
            port=port or _free_port_pair(),
            heartbeat_timeout_s=2,
            max_nodes=4,
            node_tokens={"windows-desktop": NodeTokenEntry("windows-desktop", "tok")},
        ),
        executor=WorkPacketExecutor(),
        signal_socket=SignalSocket(),
        capability_socket=CapabilitySocket(),
        outcome_socket=OutcomeSocket(),
        view_socket=ViewSocket(),
    )
    server._durable_store = DurableRemoteStore(tmp_path / "durable_remote")
    return server


def _hello_params() -> dict:
    return {
        "node_id": "windows-desktop",
        "hostname": "DESKTOP-LVGUIQ9",
        "os": "windows",
        "capabilities": [],
        "peripherals": [],
    }


def test_stale_connection_cleanup_cannot_remove_new_registration(tmp_path):
    async def _run() -> None:
        s = _server(tmp_path)
        ws_a = _FakeWS()
        ws_b = _FakeWS()

        await s._handle_hello(ws_a, _hello_params(), 1, "tok", "conn-a")
        assert s._registry.get("windows-desktop").connection_id == "conn-a"

        await s._handle_hello(ws_b, _hello_params(), 2, "tok", "conn-b")
        assert s._registry.get("windows-desktop").connection_id == "conn-b"

        s._unregister_node("windows-desktop", connection_id="conn-a")
        current = s._registry.get("windows-desktop")
        assert current is not None
        assert current.connection_id == "conn-b"

        s._unregister_node("windows-desktop", connection_id="conn-b")
        assert s._registry.get("windows-desktop") is None

    asyncio.run(_run())


def test_stale_heartbeat_rejected_without_harming_current_registration(tmp_path):
    async def _run() -> None:
        s = _server(tmp_path)
        ws_a = _FakeWS()
        ws_b = _FakeWS()
        await s._handle_hello(ws_a, _hello_params(), 1, "tok", "conn-a")
        await s._handle_hello(ws_b, _hello_params(), 2, "tok", "conn-b")

        await s._handle_heartbeat(
            "windows-desktop", {"metrics": {"cpu": 99}}, 3, ws_a, "conn-a"
        )
        current = s._registry.get("windows-desktop")
        assert current is not None
        assert current.connection_id == "conn-b"
        assert current.latest_metrics == {}
        assert ws_a.sent[-1]["result"]["ack"] is False

        await s._handle_heartbeat(
            "windows-desktop", {"metrics": {"cpu": 7}}, 4, ws_b, "conn-b"
        )
        assert current.latest_metrics["cpu"] == 7
        assert ws_b.sent[-1]["result"]["ack"] is True

    asyncio.run(_run())


def test_stale_connection_cannot_receive_durable_delivery(tmp_path):
    async def _run() -> None:
        s = _server(tmp_path)

        ws_a = _FakeWS()
        ws_b = _FakeWS()
        await s._handle_hello(ws_a, _hello_params(), 1, "tok", "conn-a")
        await s._handle_hello(ws_b, _hello_params(), 2, "tok", "conn-b")
        req = make_request(
            correlation_id="registration-ownership",
            candidate_sha="sha",
            node_id="windows-desktop",
            operation_type="unit",
            capability="shell",
            params={"command": "hostname"},
            ttl_seconds=60,
        )
        s._durable_store.put_request(req)

        await s._pump_durable_requests("windows-desktop", ws_a, "conn-a")
        assert not any(msg.get("method") == "durable_command.request" for msg in ws_a.sent)

        await s._pump_durable_requests("windows-desktop", ws_b, "conn-b")
        delivered = [msg for msg in ws_b.sent if msg.get("method") == "durable_command.request"]
        assert len(delivered) == 1
        assert delivered[0]["params"]["request_id"] == req.request_id

    asyncio.run(_run())


def test_live_late_disconnect_cannot_unregister_replacement_connection(tmp_path):
    async def _run() -> None:
        import websockets

        s = _server(tmp_path)
        s.start()
        await asyncio.sleep(1.0)
        try:
            url = f"ws://127.0.0.1:{s._config.port}/ws"
            ws_a = await websockets.connect(url, additional_headers={"Authorization": "Bearer tok"})
            await ws_a.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "node.hello",
                        "params": _hello_params(),
                        "id": 1,
                    }
                )
            )
            await asyncio.wait_for(ws_a.recv(), timeout=5)
            conn_a = s._registry.get("windows-desktop").connection_id

            ws_b = await websockets.connect(url, additional_headers={"Authorization": "Bearer tok"})
            await ws_b.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "node.hello",
                        "params": _hello_params(),
                        "id": 2,
                    }
                )
            )
            await asyncio.wait_for(ws_b.recv(), timeout=5)
            conn_b = s._registry.get("windows-desktop").connection_id
            assert conn_b != conn_a

            await ws_a.close()
            await asyncio.sleep(0.5)
            current = s._registry.get("windows-desktop")
            assert current is not None
            assert current.connection_id == conn_b

            await ws_b.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "node.heartbeat",
                        "params": {"metrics": {"cpu": 3}},
                        "id": 3,
                    }
                )
            )
            ack = json.loads(await asyncio.wait_for(ws_b.recv(), timeout=5))
            assert ack["result"]["ack"] is True
            assert s._registry.get("windows-desktop").latest_metrics["cpu"] == 3
            await ws_b.close()
        finally:
            s.stop()

    asyncio.run(_run())
