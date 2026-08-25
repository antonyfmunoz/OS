"""Binary-frame heartbeat refresh — security boundary + eviction behavior.

THE DEFECT (Beast, 2026-08-05 00:41:30): a node streaming ONLY binary frames
(desktop/camera capture) sends no JSON heartbeat. The registry evicted it after
heartbeat_timeout_s while its WebSocket stayed ESTABLISHED. Because the socket
never dropped, the daemon never reconnected or re-registered, so mesh dispatch
refused a demonstrably live node with "node windows-desktop not connected".
The condition could not self-heal.

THE FIX: a binary frame that the normal handler ACCEPTS refreshes that node's
heartbeat in the authoritative registry.

These tests pin the SECURITY BOUNDARY, not just the happy path. Heartbeat may be
refreshed only for an authenticated, registered, correctly-bound node sending a
valid frame — and eviction of a genuinely idle node must still work.
"""

from __future__ import annotations

import asyncio
import json
import socket
import struct
import time

import pytest

from substrate.execution.durable_remote_transport import DurableRemoteStore, make_request
from substrate.execution.executor import WorkPacketExecutor
from substrate.sockets.capability_socket import CapabilitySocket
from substrate.sockets.outcome_socket import OutcomeSocket
from substrate.sockets.signal_socket import SignalSocket
from substrate.sockets.view_socket import ViewSocket
from transports.node_mesh.config import MeshConfig, NodeTokenEntry
from transports.node_mesh.integration.types import ConnectedNode
from transports.node_mesh.registry import NodeRegistry
from transports.node_mesh.server import NodeMeshServer


@pytest.fixture(autouse=True)
def _isolate_snapshot_path(tmp_path, monkeypatch):
    """Never let a test write the LIVE registry snapshot.

    `NodeRegistry._write_snapshot` targets a module-level absolute path
    (`data/runtime/mesh_nodes.json`) that the RUNNING mesh service also writes.
    The live-WebSocket tests construct a real `NodeMeshServer`, whose registry
    therefore wrote fixture nodes into production runtime state — observed
    2026-08-05, when a test node `n1` appeared in the deployed service's
    snapshot file. Redirect the path for every test in this module.
    """
    import transports.node_mesh.registry as reg_mod

    monkeypatch.setattr(reg_mod, "_SNAPSHOT_PATH", tmp_path / "mesh_nodes.json")


def _frame(meta: dict, jpeg: bytes = b"\xff\xd8\xff\xe0JPEGBODY") -> bytes:
    """Build a well-formed [4-byte meta_len][JSON meta][JPEG] frame."""
    mb = json.dumps(meta).encode()
    return struct.pack(">I", len(mb)) + mb + jpeg


def _free_port_pair() -> int:
    """Return a websocket port whose adjacent HTTP relay port is also free."""
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


def _server(**cfg) -> NodeMeshServer:
    config = MeshConfig(
        port=cfg.pop("port", _free_port_pair()),
        heartbeat_timeout_s=cfg.pop("heartbeat_timeout_s", 5),
        max_nodes=4,
        node_tokens={"n1": NodeTokenEntry(node_id="n1", token="tok-n1")},
    )
    return NodeMeshServer(
        config=config,
        executor=WorkPacketExecutor(),
        signal_socket=SignalSocket(),
        capability_socket=CapabilitySocket(),
        outcome_socket=OutcomeSocket(),
        view_socket=ViewSocket(),
    )


def _node(node_id: str = "n1") -> ConnectedNode:
    return ConnectedNode(
        node_id=node_id,
        hostname="H",
        os="windows",
        os_version="10",
        capabilities=[],
        daemon_version="1.0",
        tailscale_ip="127.0.0.1",
        ws=None,
        peripherals=[],
    )


# ── the accepted-frame contract ──────────────────────────────────────────────


def test_valid_frame_reports_accepted():
    """A well-formed frame returns True — the liveness signal the caller needs."""
    s = _server()
    assert s._handle_binary_frame("n1", _frame({"source": "desktop"})) is True


@pytest.mark.parametrize(
    "raw,why",
    [
        (struct.pack(">I", 70000) + b"x" * 20, "meta_len exceeds the 65536 cap"),
        (struct.pack(">I", 500) + b"x" * 10, "declared meta_len overruns the buffer"),
    ],
)
def test_malformed_frame_reports_rejected(raw, why):
    """Malformed frames MUST return False or garbage would sustain a node."""
    s = _server()
    assert s._handle_binary_frame("n1", raw) is False, why


def test_unparseable_meta_json_still_forwarded():
    """Bad JSON meta degrades to {} by design — forwarding stays permissive.

    Pins existing RELAY behavior. This is explicitly NOT a liveness assertion;
    see test_unparseable_meta_does_not_prove_liveness.
    """
    s = _server()
    body = b"not-json"
    raw = struct.pack(">I", len(body)) + body + b"JPEG"
    assert s._handle_binary_frame("n1", raw) is True


# ── liveness is STRICTER than forwarding (fail-open regression guard) ────────
#
# Found by adversarial review: reusing forwarding-tolerance as proof of life let
# b"\x00" * 7 forge an indefinite heartbeat. That inverts the bug this path
# fixes — instead of a live node marked dead (fail-safe), a DEAD node is marked
# alive (fail-open) and dispatch routes real work to it.


@pytest.mark.parametrize(
    "raw,why",
    [
        (b"\x00" * 7, "seven zero bytes: meta_len==0 clears both bounds checks"),
        (b"\x00\x00\x00\x00XXXX", "meta_len==0 with a payload"),
        (struct.pack(">I", 8) + b"not-json" + b"JPEG", "meta present but not JSON"),
        (struct.pack(">I", 2) + b"[]" + b"JPEG", "meta is JSON but not an object"),
        (struct.pack(">I", 2) + b"{}", "no payload after the meta block"),
        # A VALID JSON meta that exactly fills the frame, leaving zero payload
        # bytes. This is the case the `>=` bound catches and `>` does not: a
        # node emitting well-formed headers with no captured image at all.
        (struct.pack(">I", 7) + b'{"s":1}', "valid meta, zero-length payload"),
        (struct.pack(">I", 20) + b'{"source":"desktop"}', "real-looking meta, no image"),
        (b"\x00" * 4, "runt frame, shorter than the minimum"),
        (struct.pack(">I", 70000) + b"x" * 20, "meta_len exceeds the cap"),
        (struct.pack(">I", 500) + b"x" * 10, "meta_len overruns the buffer"),
    ],
)
def test_frames_that_must_not_prove_liveness(raw, why):
    assert NodeMeshServer._frame_proves_liveness(raw) is False, why


def test_real_frame_proves_liveness():
    assert NodeMeshServer._frame_proves_liveness(_frame({"source": "desktop"})) is True


def test_unparseable_meta_does_not_prove_liveness():
    """The exact split: forwarded, but NOT proof of life."""
    s = _server()
    body = b"not-json"
    raw = struct.pack(">I", len(body)) + body + b"JPEG"
    assert s._handle_binary_frame("n1", raw) is True, "forwarding stays tolerant"
    assert NodeMeshServer._frame_proves_liveness(raw) is False, (
        "tolerant forwarding must never double as an unforgeable liveness proof"
    )


# ── requirement 4: malformed traffic does not refresh ────────────────────────


async def _live_malformed_does_not_sustain() -> dict:
    """Drive the REAL server path with malformed frames only.

    This must NOT re-implement the caller's `if accepted:` guard — a test that
    mirrors the server's logic cannot detect that logic being reordered (a
    refresh-before-validation mutant survives such a test).
    """
    import websockets

    s = _server(heartbeat_timeout_s=2)
    s.start()
    await asyncio.sleep(1.0)
    out: dict = {}
    try:
        ws = await websockets.connect(
            f"ws://127.0.0.1:{s._config.port}/ws",
            additional_headers={"Authorization": "Bearer tok-n1"},
        )
        await ws.send(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "node.hello",
                    "params": {
                        "node_id": "n1",
                        "hostname": "H",
                        "os": "windows",
                        "capabilities": [],
                        "peripherals": [],
                    },
                    "id": 1,
                }
            )
        )
        await asyncio.wait_for(ws.recv(), timeout=5)

        # Stream ONLY malformed frames well past the eviction window.
        bad = struct.pack(">I", 70000) + b"x" * 40
        deadline = time.monotonic() + 4.0
        while time.monotonic() < deadline:
            await ws.send(bad)
            await asyncio.sleep(0.3)

        out["stale_after_malformed"] = "n1" in s._registry.stale_nodes()
        await ws.close()
    finally:
        s.stop()
    return out


def test_live_malformed_frames_do_not_refresh_heartbeat():
    """Requirement 4, through the real path: garbage must not sustain a node."""
    r = asyncio.run(_live_malformed_does_not_sustain())
    assert r.get("stale_after_malformed") is True, (
        "malformed traffic refreshed the heartbeat — refresh must happen only "
        "AFTER the frame handler accepts the frame"
    )


async def _live_zero_bytes_do_not_sustain() -> dict:
    """The reviewer's Critical: b"\\x00" * 7 must NOT forge a heartbeat.

    Reproduces the demonstrated attack end-to-end over a real WebSocket: an
    authenticated, registered node streams only 7-zero-byte frames across three
    full eviction windows. It must go stale.
    """
    import websockets

    s = _server(heartbeat_timeout_s=2)
    s.start()
    await asyncio.sleep(1.0)
    out: dict = {}
    try:
        ws = await websockets.connect(
            f"ws://127.0.0.1:{s._config.port}/ws",
            additional_headers={"Authorization": "Bearer tok-n1"},
        )
        await ws.send(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "node.hello",
                    "params": {
                        "node_id": "n1",
                        "hostname": "H",
                        "os": "windows",
                        "capabilities": [],
                        "peripherals": [],
                    },
                    "id": 1,
                }
            )
        )
        await asyncio.wait_for(ws.recv(), timeout=5)
        out["registered"] = s._registry.get("n1") is not None

        deadline = time.monotonic() + 6.0  # 3x the eviction window
        while time.monotonic() < deadline:
            await ws.send(b"\x00" * 7)
            await asyncio.sleep(0.3)

        out["stale_after_zero_bytes"] = "n1" in s._registry.stale_nodes()
        await ws.close()
    finally:
        s.stop()
    return out


def test_live_zero_byte_frames_cannot_forge_a_heartbeat():
    """Critical regression guard: padding bytes must never advertise liveness."""
    r = asyncio.run(_live_zero_bytes_do_not_sustain())
    assert r.get("registered") is True
    assert r.get("stale_after_zero_bytes") is True, (
        "seven zero bytes forged an indefinite heartbeat — a node with a dead "
        "capture pipeline would be advertised as live and receive dispatched work"
    )


# ── requirement 6: cross-node isolation ──────────────────────────────────────


async def _live_cross_node_isolation() -> dict:
    """Two registered nodes; only ONE streams. The silent one must still evict.

    Driven through the real server so a "refresh every connected node" mutant
    is caught — asserting on the registry alone cannot see that.
    """
    import websockets

    config = MeshConfig(
        port=_free_port_pair(),
        heartbeat_timeout_s=2,
        max_nodes=4,
        node_tokens={
            "n1": NodeTokenEntry(node_id="n1", token="tok-n1"),
            "n2": NodeTokenEntry(node_id="n2", token="tok-n2"),
        },
    )
    s = NodeMeshServer(
        config=config,
        executor=WorkPacketExecutor(),
        signal_socket=SignalSocket(),
        capability_socket=CapabilitySocket(),
        outcome_socket=OutcomeSocket(),
        view_socket=ViewSocket(),
    )
    s.start()
    await asyncio.sleep(1.0)
    out: dict = {}

    async def _hello(node_id: str, token: str):
        ws = await websockets.connect(
            f"ws://127.0.0.1:{config.port}/ws",
            additional_headers={"Authorization": f"Bearer {token}"},
        )
        await ws.send(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "node.hello",
                    "params": {
                        "node_id": node_id,
                        "hostname": "H",
                        "os": "windows",
                        "capabilities": [],
                        "peripherals": [],
                    },
                    "id": 1,
                }
            )
        )
        await asyncio.wait_for(ws.recv(), timeout=5)
        return ws

    try:
        ws1 = await _hello("n1", "tok-n1")
        ws2 = await _hello("n2", "tok-n2")
        out["both_registered"] = (
            s._registry.get("n1") is not None and s._registry.get("n2") is not None
        )

        # ONLY n1 streams, for longer than the eviction window.
        deadline = time.monotonic() + 4.0
        while time.monotonic() < deadline:
            await ws1.send(_frame({"source": "desktop"}))
            await asyncio.sleep(0.3)

        stale = s._registry.stale_nodes()
        out["n1_fresh"] = "n1" not in stale
        out["n2_stale"] = "n2" in stale
        await ws1.close()
        await ws2.close()
    finally:
        s.stop()
    return out


def test_live_frame_from_one_node_cannot_refresh_another():
    """Requirement 6, through the real path: refresh is bound to the sender."""
    r = asyncio.run(_live_cross_node_isolation())
    assert r.get("both_registered") is True, "both nodes must register"
    assert r.get("n1_fresh") is True, "the streaming node must stay fresh"
    assert r.get("n2_stale") is True, (
        "a SILENT node was refreshed by another node's frames — refresh must "
        "apply only to the node bound to the sending connection"
    )


def test_update_heartbeat_refuses_unknown_node():
    """The authoritative registry refuses unknown nodes — never silently true."""
    reg = NodeRegistry(heartbeat_timeout_s=5)
    assert reg.update_heartbeat("ghost") is False
    assert reg.node_count() == 0


def test_evicted_node_cannot_revive_itself_by_streaming():
    """Requirement 7: after removal, frames cannot resurrect a registration."""
    reg = NodeRegistry(heartbeat_timeout_s=5)
    reg.add(_node())
    reg.remove("n1")

    assert reg.update_heartbeat("n1") is False, "a removed node must not revive"
    assert reg.get("n1") is None
    assert reg.node_count() == 0


# ── requirement 3: idle nodes are still evicted ──────────────────────────────


def test_idle_node_is_still_evicted():
    reg = NodeRegistry(heartbeat_timeout_s=0.05)
    reg.add(_node())
    time.sleep(0.12)
    assert "n1" in reg.stale_nodes(), "eviction must not be weakened"


def test_refresh_extends_across_multiple_eviction_windows():
    """Requirement 1, at registry level: repeated refresh outlives N windows."""
    reg = NodeRegistry(heartbeat_timeout_s=0.05)
    reg.add(_node())
    for _ in range(6):  # 6 windows' worth of elapsed time
        time.sleep(0.04)
        assert reg.update_heartbeat("n1") is True
        assert "n1" not in reg.stale_nodes()

    time.sleep(0.12)  # stop refreshing
    assert "n1" in reg.stale_nodes(), "must evict once frames stop"


# ── requirements 1 + 5: live end-to-end over a real WebSocket ────────────────


async def _live_binary_only_survives() -> dict:
    """Real server, real WS. Node sends ONLY binary frames across >3 windows."""
    import websockets

    s = _server(heartbeat_timeout_s=2)
    s.start()
    await asyncio.sleep(1.0)
    out: dict = {}
    try:
        ws = await websockets.connect(
            f"ws://127.0.0.1:{s._config.port}/ws",
            additional_headers={"Authorization": "Bearer tok-n1"},
        )
        await ws.send(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "node.hello",
                    "params": {
                        "node_id": "n1",
                        "hostname": "H",
                        "os": "windows",
                        "capabilities": [],
                        "peripherals": [],
                    },
                    "id": 1,
                }
            )
        )
        await asyncio.wait_for(ws.recv(), timeout=5)
        out["registered"] = s._registry.get("n1") is not None

        # Stream ONLY binary frames for 3x the eviction window (6s).
        deadline = time.monotonic() + 6.0
        while time.monotonic() < deadline:
            await ws.send(_frame({"source": "desktop"}))
            await asyncio.sleep(0.4)

        out["survived_binary_only"] = s._registry.get("n1") is not None
        out["stale_after_streaming"] = "n1" in s._registry.stale_nodes()

        # Now go silent for longer than the window — eviction must still fire.
        await asyncio.sleep(3.0)
        out["stale_when_idle"] = "n1" in s._registry.stale_nodes()

        await ws.close()
        await asyncio.sleep(0.5)
        out["unregistered_on_close"] = s._registry.get("n1") is None
    finally:
        s.stop()
    return out


def test_live_node_streaming_binary_only_survives_three_windows():
    r = asyncio.run(_live_binary_only_survives())
    assert r.get("registered") is True, "hello must register"
    assert r.get("survived_binary_only") is True, (
        "THE DEFECT: binary-only streaming was evicted after ~1 window"
    )
    assert r.get("stale_after_streaming") is False, "frames must refresh heartbeat"
    assert r.get("stale_when_idle") is True, "requirement 3: idle must still evict"
    assert r.get("unregistered_on_close") is True, "requirement 8: cleanup intact"


async def _live_binary_liveness_pumps_durable_requests(tmp_path) -> dict:
    """A media-heavy node must not starve queued durable work until a text heartbeat."""
    import websockets

    s = _server(heartbeat_timeout_s=5)
    s._durable_store = DurableRemoteStore(tmp_path)
    s.start()
    await asyncio.sleep(1.0)
    out: dict = {}
    try:
        ws = await websockets.connect(
            f"ws://127.0.0.1:{s._config.port}/ws",
            additional_headers={"Authorization": "Bearer tok-n1"},
        )
        await ws.send(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "node.hello",
                    "params": {
                        "node_id": "n1",
                        "hostname": "H",
                        "os": "windows",
                        "capabilities": [],
                        "peripherals": [],
                    },
                    "id": 1,
                }
            )
        )
        await asyncio.wait_for(ws.recv(), timeout=5)
        req = make_request(
            correlation_id="binary-pump-test",
            candidate_sha="sha",
            node_id="n1",
            operation_type="unit",
            capability="shell",
            params={"command": "hostname"},
            ttl_seconds=60,
        )
        s._durable_store.put_request(req)

        await ws.send(_frame({"source": "desktop"}))
        delivered = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        out["method"] = delivered.get("method")
        out["request_id"] = delivered.get("params", {}).get("request_id")
        out["node_id"] = delivered.get("params", {}).get("node_id")
        await ws.send(_frame({"source": "desktop"}))
        try:
            duplicate = await asyncio.wait_for(ws.recv(), timeout=0.5)
            out["immediate_duplicate"] = duplicate
        except asyncio.TimeoutError:
            out["immediate_duplicate"] = None
        await ws.close()
    finally:
        s.stop()
    return out


def test_live_binary_liveness_pumps_durable_requests(tmp_path):
    r = asyncio.run(_live_binary_liveness_pumps_durable_requests(tmp_path))
    assert r.get("method") == "durable_command.request"
    assert r.get("node_id") == "n1"
    assert r.get("request_id")
    assert r.get("immediate_duplicate") is None


class _CaptureWs:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send(self, payload: str) -> None:
        self.sent.append(payload)


def _durable_request(request_id: str, correlation_id: str):
    req = make_request(
        correlation_id=correlation_id,
        candidate_sha="sha",
        node_id="n1",
        operation_type="unit",
        capability="shell",
        params={"command": "hostname", "budgets": {"claim_acquisition_timeout_s": 30}},
        ttl_seconds=60,
    )
    req.request_id = request_id
    req.idempotency_key = request_id
    return req


async def _pump_suppression_preserves_distinct_delivery(tmp_path) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req1 = _durable_request("drc-aaa", "redelivery-one")
    req2 = _durable_request("drc-bbb", "redelivery-two")
    s._durable_store.put_request(req1)
    s._durable_store.put_request(req2)
    ws = _CaptureWs()

    await s._pump_durable_requests("n1", ws)  # sends req1
    delivered_req1 = s._durable_store.get_request(req1.request_id)
    assert delivered_req1 is not None
    delivered_req1.delivered_at = 0.0
    s._durable_store.update_request(delivered_req1)

    await s._pump_durable_requests("n1", ws)  # suppresses req1, sends req2

    sent_ids = [
        json.loads(payload)["params"]["request_id"]
        for payload in ws.sent
        if json.loads(payload).get("method") == "durable_command.request"
    ]
    stored_req1 = s._durable_store.get_request(req1.request_id)
    stored_req2 = s._durable_store.get_request(req2.request_id)
    assert stored_req1 is not None
    assert stored_req2 is not None
    return {
        "sent_ids": sent_ids,
        "req1_delivery_attempts": stored_req1.delivery_attempts,
        "req2_delivery_attempts": stored_req2.delivery_attempts,
        "req1_transport_events": stored_req1.diagnostics.get("transport_control", {}).get(
            "events", []
        ),
    }


def test_durable_pump_suppresses_same_request_without_serializing_distinct_requests(tmp_path):
    result = asyncio.run(_pump_suppression_preserves_distinct_delivery(tmp_path))
    assert result["sent_ids"] == ["drc-aaa", "drc-bbb"]
    assert result["req1_delivery_attempts"] == 1
    assert result["req2_delivery_attempts"] == 1
    assert any(event["event"] == "delivery_suppressed" for event in result["req1_transport_events"])


async def _pump_suppression_expires_boundedly(tmp_path) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = _durable_request("drc-aaa", "redelivery-expiry")
    s._durable_store.put_request(req)
    ws = _CaptureWs()

    await s._pump_durable_requests("n1", ws)
    s._durable_delivery_inflight[req.request_id]["suppress_until"] = 0.0
    delivered_req = s._durable_store.get_request(req.request_id)
    assert delivered_req is not None
    delivered_req.delivered_at = 0.0
    s._durable_store.update_request(delivered_req)
    await s._pump_durable_requests("n1", ws)

    stored = s._durable_store.get_request(req.request_id)
    assert stored is not None
    return {
        "delivery_attempts": stored.delivery_attempts,
        "sent_count": len(ws.sent),
        "inflight": req.request_id in s._durable_delivery_inflight,
    }


def test_durable_delivery_suppression_expires_without_permanent_starvation(tmp_path):
    result = asyncio.run(_pump_suppression_expires_boundedly(tmp_path))
    assert result["delivery_attempts"] == 2
    assert result["sent_count"] == 2
    assert result["inflight"] is True


async def _durable_claim_progress_clears_inflight_and_records_timing(tmp_path) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = _durable_request("drc-aaa", "claim-progress")
    s._durable_store.put_request(req)
    ws = _CaptureWs()
    await s._pump_durable_requests("n1", ws)

    await s._handle_durable_claimed(
        "n1",
        {
            "request_id": req.request_id,
            "claim_id": "claim-1",
            "state": "CLAIMED",
            "process_tree": {"node_pid": 123, "claimed_at": 10.0},
        },
        99,
        ws,  # type: ignore[arg-type]
    )
    stored = s._durable_store.get_request(req.request_id)
    assert stored is not None
    events = stored.diagnostics.get("transport_control", {}).get("events", [])
    return {
        "accepted": json.loads(ws.sent[-1])["result"]["accepted"],
        "inflight_present": req.request_id in s._durable_delivery_inflight,
        "events": [event["event"] for event in events],
    }


def test_durable_claim_progress_clears_transport_inflight_with_positive_evidence(tmp_path):
    result = asyncio.run(_durable_claim_progress_clears_inflight_and_records_timing(tmp_path))
    assert result["accepted"] is True
    assert result["inflight_present"] is False
    assert "durable_control_frame_received" in result["events"]
    assert "canonical_write_started" in result["events"]
    assert "canonical_write_completed" in result["events"]
    assert "ack_sent" in result["events"]


async def _heartbeat_does_not_await_slow_durable_pump() -> dict:
    s = _server()
    s._registry.add(_node())
    ws = _CaptureWs()
    pump_started = asyncio.Event()
    release_pump = asyncio.Event()

    async def slow_pump(node_id: str, ws_arg, connection_id: str = "") -> None:
        pump_started.set()
        await release_pump.wait()

    s._pump_durable_requests = slow_pump  # type: ignore[method-assign]
    start = time.monotonic()
    await s._handle_heartbeat("n1", {"metrics": {}}, 7, ws)  # type: ignore[arg-type]
    elapsed = time.monotonic() - start
    await asyncio.sleep(0)
    pump_was_scheduled = pump_started.is_set()
    release_pump.set()
    await asyncio.sleep(0)
    return {
        "elapsed": elapsed,
        "pump_was_scheduled": pump_was_scheduled,
        "heartbeat_ack": json.loads(ws.sent[0])["result"]["ack"],
    }


def test_heartbeat_receive_path_schedules_pump_without_waiting_for_it():
    result = asyncio.run(_heartbeat_does_not_await_slow_durable_pump())
    assert result["heartbeat_ack"] is True
    assert result["elapsed"] < 0.5
    assert result["pump_was_scheduled"] is True


async def _durable_claim_handler_progresses_while_pump_is_busy(tmp_path) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = _durable_request("drc-aaa", "claim-under-pump-pressure")
    s._durable_store.put_request(req)
    ws = _CaptureWs()
    pump_started = asyncio.Event()
    release_pump = asyncio.Event()

    async def slow_pump(node_id: str, ws_arg, connection_id: str = "") -> None:
        pump_started.set()
        await release_pump.wait()

    s._pump_durable_requests = slow_pump  # type: ignore[method-assign]
    s._schedule_durable_pump("n1", ws, "", reason="test_pressure")
    await asyncio.wait_for(pump_started.wait(), timeout=1)

    start = time.monotonic()
    await s._handle_durable_claimed(
        "n1",
        {
            "request_id": req.request_id,
            "claim_id": "claim-1",
            "state": "CLAIMED",
            "process_tree": {"node_pid": 123, "claimed_at": 10.0},
        },
        88,
        ws,  # type: ignore[arg-type]
    )
    elapsed = time.monotonic() - start
    release_pump.set()
    await asyncio.sleep(0)

    stored = s._durable_store.get_request(req.request_id)
    assert stored is not None
    return {
        "elapsed": elapsed,
        "state": stored.lifecycle_state,
        "claim_id": stored.claim_id,
        "accepted": json.loads(ws.sent[-1])["result"]["accepted"],
    }


def test_inbound_durable_claim_progresses_while_outbound_pump_is_busy(tmp_path):
    result = asyncio.run(_durable_claim_handler_progresses_while_pump_is_busy(tmp_path))
    assert result["elapsed"] < 0.5
    assert result["state"] == "CLAIMED"
    assert result["claim_id"] == "claim-1"
    assert result["accepted"] is True


async def _claim_conflict_ack_reports_rejection(tmp_path) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="claim-conflict-test",
        candidate_sha="sha",
        node_id="n1",
        operation_type="unit",
        capability="shell",
        params={"command": "hostname"},
        ttl_seconds=60,
    )
    s._durable_store.put_request(req)
    s._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    ws = _CaptureWs()
    await s._handle_durable_claimed(
        "n1",
        {"request_id": req.request_id, "claim_id": "claim-2", "state": "CLAIMED"},
        99,
        ws,  # type: ignore[arg-type]
    )
    return json.loads(ws.sent[0])["result"]


def test_claim_conflict_ack_reports_rejection(tmp_path):
    result = asyncio.run(_claim_conflict_ack_reports_rejection(tmp_path))
    assert result["ok"] is False
    assert "RECONCILIATION_REQUIRED" in result["error"]


async def _claim_ack_reports_canonical_identity(tmp_path) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="claim-ack-test",
        candidate_sha="sha",
        node_id="n1",
        operation_type="unit",
        capability="shell",
        params={"command": "hostname"},
        ttl_seconds=60,
    )
    s._durable_store.put_request(req)

    ws = _CaptureWs()
    await s._handle_durable_claimed(
        "n1",
        {"request_id": req.request_id, "claim_id": "claim-1", "state": "CLAIMED"},
        99,
        ws,  # type: ignore[arg-type]
    )
    return json.loads(ws.sent[0])["result"]


def test_claim_ack_reports_canonical_identity(tmp_path):
    result = asyncio.run(_claim_ack_reports_canonical_identity(tmp_path))

    assert result["ok"] is True
    assert result["accepted"] is True
    assert result["correlation_id"] == "claim-ack-test"
    assert result["candidate_sha"] == "sha"
    assert result["node_id"] == "n1"
    assert result["claim_id"] == "claim-1"
    assert result["lifecycle_state"] == "CLAIMED"
    assert result["authority_source"] == "vps_canonical_durable_store"


async def _claim_state_reports_exact_accepted_claim(tmp_path) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="claim-state-test",
        candidate_sha="sha",
        node_id="n1",
        operation_type="unit",
        capability="shell",
        params={"command": "hostname"},
        ttl_seconds=60,
    )
    s._durable_store.put_request(req)
    claimed = s._durable_store.mark_claimed(
        req.request_id,
        claim_id="claim-1",
        process_tree={"node_pid": 123, "claimed_at": 10.0},
    )

    class Ws:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, payload: str) -> None:
            self.sent.append(payload)

    ws = Ws()
    await s._handle_durable_claim_state(
        "n1",
        {
            "request_id": req.request_id,
            "correlation_id": req.correlation_id,
            "candidate_sha": req.candidate_sha,
            "claim_id": claimed.claim_id,
        },
        98,
        ws,  # type: ignore[arg-type]
    )
    return json.loads(ws.sent[0])["result"]


def test_claim_state_reports_exact_accepted_claim(tmp_path):
    result = asyncio.run(_claim_state_reports_exact_accepted_claim(tmp_path))
    assert result["ok"] is True
    assert result["accepted"] is True
    assert result["claim_id"] == "claim-1"
    assert result["candidate_sha"] == "sha"
    assert result["correlation_id"] == "claim-state-test"
    assert result["lifecycle_state"] == "CLAIMED"
    assert result["process_tree"]["node_pid"] == 123
    assert result["authority_source"] == "vps_canonical_durable_store"


def test_canonical_claim_state_http_auth_binds_node_token_to_node_id(tmp_path):
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="claim-state-http",
        candidate_sha="sha",
        node_id="n1",
        operation_type="unit",
        capability="shell",
        params={"command": "hostname"},
        ttl_seconds=60,
    )
    s._durable_store.put_request(req)
    claimed = s._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    assert s._http_authenticated_node_id("Bearer tok-n1") == "n1"
    response = s._canonical_durable_claim_state(
        "n1",
        {
            "request_id": req.request_id,
            "correlation_id": req.correlation_id,
            "candidate_sha": req.candidate_sha,
            "node_id": "n1",
            "claim_id": claimed.claim_id,
            "state": "CLAIMED",
        },
    )

    assert response["ok"] is True
    assert response["accepted"] is True
    assert response["authority_source"] == "vps_canonical_durable_store"


async def _canonical_claim_state_http_relay_reads_store(tmp_path, monkeypatch) -> dict:
    monkeypatch.setenv("UMH_MESH_RELAY_BIND", "127.0.0.1")
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="claim-state-http-relay",
        candidate_sha="sha",
        node_id="n1",
        operation_type="unit",
        capability="shell",
        params={"command": "hostname"},
        ttl_seconds=60,
    )
    s._durable_store.put_request(req)
    claimed = s._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    s.start()
    try:
        last_exc: Exception | None = None
        for _ in range(50):
            try:
                reader, writer = await asyncio.open_connection(
                    "127.0.0.1", s._config.port + 1
                )
                break
            except OSError as exc:
                last_exc = exc
                await asyncio.sleep(0.05)
        else:
            raise AssertionError(f"HTTP relay did not start: {last_exc}")

        body = json.dumps(
            {
                "request_id": req.request_id,
                "correlation_id": req.correlation_id,
                "candidate_sha": req.candidate_sha,
                "node_id": req.node_id,
                "claim_id": claimed.claim_id,
                "state": "CLAIMED",
            },
            separators=(",", ":"),
        ).encode("utf-8")
        writer.write(
            b"POST /durable-claim-state HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Authorization: Bearer tok-n1\r\n"
            b"Content-Type: application/json\r\n"
            + f"Content-Length: {len(body)}\r\n".encode("ascii")
            + b"Connection: close\r\n\r\n"
            + body
        )
        await writer.drain()
        raw = await reader.read()
        writer.close()
        await writer.wait_closed()
    finally:
        s.stop()

    _, _, response_body = raw.partition(b"\r\n\r\n")
    return json.loads(response_body.decode("utf-8"))


def test_canonical_claim_state_http_relay_reads_store(tmp_path, monkeypatch):
    response = asyncio.run(_canonical_claim_state_http_relay_reads_store(tmp_path, monkeypatch))

    assert response["ok"] is True
    assert response["accepted"] is True
    assert response["request_id"]
    assert response["node_id"] == "n1"
    assert response["authority_source"] == "vps_canonical_durable_store"


async def _claim_state_reports_exact_running_claim(tmp_path) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="claim-state-running-test",
        candidate_sha="sha",
        node_id="n1",
        operation_type="unit",
        capability="shell",
        params={"command": "hostname"},
        ttl_seconds=60,
    )
    s._durable_store.put_request(req)
    s._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    running = s._durable_store.mark_running(
        req.request_id,
        claim_id="claim-1",
        process_tree={"node_pid": 123, "root_pid": 456, "running_at": 11.0},
    )

    class Ws:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, payload: str) -> None:
            self.sent.append(payload)

    ws = Ws()
    await s._handle_durable_claim_state(
        "n1",
        {
            "request_id": req.request_id,
            "correlation_id": req.correlation_id,
            "candidate_sha": req.candidate_sha,
            "claim_id": running.claim_id,
            "state": "RUNNING",
        },
        102,
        ws,  # type: ignore[arg-type]
    )
    return json.loads(ws.sent[0])["result"]


def test_claim_state_reports_exact_running_claim(tmp_path):
    result = asyncio.run(_claim_state_reports_exact_running_claim(tmp_path))
    assert result["ok"] is True
    assert result["accepted"] is True
    assert result["claim_id"] == "claim-1"
    assert result["lifecycle_state"] == "RUNNING"
    assert result["process_tree"]["root_pid"] == 456


async def _claim_state_claimed_proof_accepts_same_claim_running(tmp_path) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="claim-state-running-proof-test",
        candidate_sha="sha",
        node_id="n1",
        operation_type="unit",
        capability="shell",
        params={"command": "hostname"},
        ttl_seconds=60,
    )
    s._durable_store.put_request(req)
    s._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    s._durable_store.mark_running(
        req.request_id,
        claim_id="claim-1",
        process_tree={"node_pid": 123, "root_pid": 456, "running_at": 11.0},
    )

    class Ws:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, payload: str) -> None:
            self.sent.append(payload)

    ws = Ws()
    await s._handle_durable_claim_state(
        "n1",
        {
            "request_id": req.request_id,
            "correlation_id": req.correlation_id,
            "candidate_sha": req.candidate_sha,
            "claim_id": "claim-1",
            "state": "CLAIMED",
        },
        103,
        ws,  # type: ignore[arg-type]
    )
    return json.loads(ws.sent[0])["result"]


def test_claim_state_claimed_proof_accepts_same_claim_running(tmp_path):
    result = asyncio.run(_claim_state_claimed_proof_accepts_same_claim_running(tmp_path))
    assert result["ok"] is True
    assert result["accepted"] is True
    assert result["claim_id"] == "claim-1"
    assert result["lifecycle_state"] == "RUNNING"
    assert result["process_tree"]["root_pid"] == 456


async def _claimed_ack_accepts_running_without_regression(tmp_path) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="claimed-ack-running-proof-test",
        candidate_sha="sha",
        node_id="n1",
        operation_type="unit",
        capability="shell",
        params={"command": "hostname"},
        ttl_seconds=60,
    )
    s._durable_store.put_request(req)
    s._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    s._durable_store.mark_running(
        req.request_id,
        claim_id="claim-1",
        process_tree={"node_pid": 123, "root_pid": 456, "running_at": 11.0},
    )

    class Ws:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, payload: str) -> None:
            self.sent.append(payload)

    ws = Ws()
    await s._handle_durable_claimed(
        "n1",
        {
            "request_id": req.request_id,
            "claim_id": "claim-1",
            "state": "CLAIMED",
            "process_tree": {"node_pid": 123, "claimed_at": 12.0},
        },
        104,
        ws,  # type: ignore[arg-type]
    )
    return json.loads(ws.sent[0])["result"]


def test_claimed_ack_accepts_running_without_regression(tmp_path):
    result = asyncio.run(_claimed_ack_accepts_running_without_regression(tmp_path))
    assert result["ok"] is True
    assert result["accepted"] is True
    assert result["claim_id"] == "claim-1"
    assert result["lifecycle_state"] == "RUNNING"
    assert result["process_tree"]["root_pid"] == 456


async def _claim_state_rejects_wrong_lifecycle_state(tmp_path, requested_state: str) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="claim-state-lifecycle-test",
        candidate_sha="sha",
        node_id="n1",
        operation_type="unit",
        capability="shell",
        params={"command": "hostname"},
        ttl_seconds=60,
    )
    s._durable_store.put_request(req)
    s._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    class Ws:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, payload: str) -> None:
            self.sent.append(payload)

    ws = Ws()
    await s._handle_durable_claim_state(
        "n1",
        {
            "request_id": req.request_id,
            "correlation_id": req.correlation_id,
            "candidate_sha": req.candidate_sha,
            "claim_id": "claim-1",
            "state": requested_state,
        },
        103,
        ws,  # type: ignore[arg-type]
    )
    return json.loads(ws.sent[0])["result"]


def test_claim_state_rejects_running_when_store_is_only_claimed(tmp_path):
    result = asyncio.run(_claim_state_rejects_wrong_lifecycle_state(tmp_path, "RUNNING"))
    assert result["ok"] is False
    assert result["accepted"] is False
    assert "lifecycle_state" in result["error"]


def test_claim_state_rejects_unsupported_state(tmp_path):
    result = asyncio.run(_claim_state_rejects_wrong_lifecycle_state(tmp_path, "BOGUS"))
    assert result["ok"] is False
    assert result["accepted"] is False
    mismatch_fields = result["error"].removeprefix("claim mismatch: ").split(",")
    assert "state" in mismatch_fields


async def _claim_state_rejects_foreign_correlation(tmp_path) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="claim-state-correlation-test",
        candidate_sha="sha",
        node_id="n1",
        operation_type="unit",
        capability="shell",
        params={"command": "hostname"},
        ttl_seconds=60,
    )
    s._durable_store.put_request(req)
    s._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    class Ws:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, payload: str) -> None:
            self.sent.append(payload)

    ws = Ws()
    await s._handle_durable_claim_state(
        "n1",
        {
            "request_id": req.request_id,
            "correlation_id": "foreign-correlation",
            "candidate_sha": req.candidate_sha,
            "claim_id": "claim-1",
        },
        104,
        ws,  # type: ignore[arg-type]
    )
    return json.loads(ws.sent[0])["result"]


def test_claim_state_rejects_foreign_correlation(tmp_path):
    result = asyncio.run(_claim_state_rejects_foreign_correlation(tmp_path))
    assert result["ok"] is False
    assert result["accepted"] is False
    mismatch_fields = result["error"].removeprefix("claim mismatch: ").split(",")
    assert mismatch_fields == ["correlation_id"]


async def _claim_state_rejects_foreign_claim(tmp_path) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="claim-state-foreign-test",
        candidate_sha="sha",
        node_id="n1",
        operation_type="unit",
        capability="shell",
        params={"command": "hostname"},
        ttl_seconds=60,
    )
    s._durable_store.put_request(req)
    s._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    class Ws:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, payload: str) -> None:
            self.sent.append(payload)

    ws = Ws()
    await s._handle_durable_claim_state(
        "n1",
        {
            "request_id": req.request_id,
            "correlation_id": req.correlation_id,
            "candidate_sha": req.candidate_sha,
            "claim_id": "claim-2",
        },
        99,
        ws,  # type: ignore[arg-type]
    )
    return json.loads(ws.sent[0])["result"]


def test_claim_state_rejects_foreign_claim(tmp_path):
    result = asyncio.run(_claim_state_rejects_foreign_claim(tmp_path))
    assert result["ok"] is False
    assert result["accepted"] is False
    assert result["claim_id"] == "claim-1"
    assert "claim mismatch" in result["error"]


async def _claim_state_requires_complete_identity(tmp_path) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="claim-state-required-test",
        candidate_sha="sha",
        node_id="n1",
        operation_type="unit",
        capability="shell",
        params={"command": "hostname"},
        ttl_seconds=60,
    )
    s._durable_store.put_request(req)
    s._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    class Ws:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, payload: str) -> None:
            self.sent.append(payload)

    ws = Ws()
    await s._handle_durable_claim_state(
        "n1",
        {"request_id": req.request_id, "correlation_id": req.correlation_id},
        100,
        ws,  # type: ignore[arg-type]
    )
    return json.loads(ws.sent[0])["result"]


def test_claim_state_requires_complete_identity(tmp_path):
    result = asyncio.run(_claim_state_requires_complete_identity(tmp_path))
    assert result["ok"] is False
    assert result["accepted"] is False
    assert "candidate_sha" in result["error"]
    assert "claim_id" in result["error"]


async def _claim_state_foreign_node_does_not_echo_request(tmp_path) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="claim-state-node-test",
        candidate_sha="sha",
        node_id="n1",
        operation_type="unit",
        capability="shell",
        params={"command": "secret-ish command"},
        authority_id="authority-hidden",
        ttl_seconds=60,
    )
    s._durable_store.put_request(req)
    s._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    class Ws:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, payload: str) -> None:
            self.sent.append(payload)

    ws = Ws()
    await s._handle_durable_claim_state(
        "foreign-node",
        {
            "request_id": req.request_id,
            "correlation_id": req.correlation_id,
            "candidate_sha": req.candidate_sha,
            "claim_id": req.claim_id,
        },
        101,
        ws,  # type: ignore[arg-type]
    )
    return json.loads(ws.sent[0])["result"]


def test_claim_state_foreign_node_does_not_echo_request(tmp_path):
    result = asyncio.run(_claim_state_foreign_node_does_not_echo_request(tmp_path))
    assert result["ok"] is False
    assert result["accepted"] is False
    assert result["error"] == "request not found for node"
    assert result["claim_id"] == ""
    assert result["correlation_id"] == ""
    assert result["candidate_sha"] == ""
    assert "params" not in result
    assert "authority_id" not in result


async def _duplicate_terminal_result_ack_reports_rejection(tmp_path) -> dict:
    s = _server()
    s._durable_store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="result-conflict-test",
        candidate_sha="sha",
        node_id="n1",
        operation_type="unit",
        capability="shell",
        params={"command": "hostname"},
        ttl_seconds=60,
    )
    s._durable_store.put_request(req)
    s._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    s._durable_store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="SUCCEEDED",
        result={"success": True, "stdout": "first"},
    )

    class Ws:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, payload: str) -> None:
            self.sent.append(payload)

    ws = Ws()
    await s._handle_durable_result(
        "n1",
        {
            "request_id": req.request_id,
            "claim_id": "foreign",
            "state": "SUCCEEDED",
            "result": {"success": True, "stdout": "foreign"},
        },
        100,
        ws,  # type: ignore[arg-type]
    )
    return json.loads(ws.sent[0])["result"]


def test_duplicate_terminal_result_ack_reports_rejection(tmp_path):
    result = asyncio.run(_duplicate_terminal_result_ack_reports_rejection(tmp_path))
    assert result["ok"] is False
    assert "SUCCEEDED" in result["error"]


async def _unauthenticated_binary_rejected() -> dict:
    """Requirement 5: binary before/without auth never reaches the registry."""
    import websockets

    s = _server(heartbeat_timeout_s=5)
    s.start()
    await asyncio.sleep(1.0)
    out: dict = {}
    try:
        # Wrong token — the server must close before any frame is processed.
        try:
            ws = await websockets.connect(
                f"ws://127.0.0.1:{s._config.port}/ws",
                additional_headers={"Authorization": "Bearer WRONG"},
            )
            await ws.send(_frame({"source": "desktop"}))
            await asyncio.sleep(0.5)
            out["closed"] = ws.close_code is not None or True
            await ws.close()
        except Exception:
            out["closed"] = True

        out["registry_empty"] = s._registry.node_count() == 0

        # Authenticated but pre-hello: node_id is unbound, so `if node_id`
        # short-circuits and no heartbeat can be attributed.
        ws2 = await websockets.connect(
            f"ws://{'127.0.0.1'}:{s._config.port}/ws",
            additional_headers={"Authorization": "Bearer tok-n1"},
        )
        await ws2.send(_frame({"source": "desktop"}))
        await asyncio.sleep(0.5)
        out["no_registration_without_hello"] = s._registry.node_count() == 0
        await ws2.close()
    finally:
        s.stop()
    return out


def test_unauthenticated_and_prehello_binary_never_registers():
    r = asyncio.run(_unauthenticated_binary_rejected())
    assert r.get("registry_empty") is True, "failed auth must not register a node"
    assert r.get("no_registration_without_hello") is True, (
        "binary before node.hello must not create or refresh a registration"
    )


# ── requirement 2: JSON heartbeat path unchanged ─────────────────────────────


def test_snapshot_write_is_atomic_under_concurrent_reads(tmp_path, monkeypatch):
    """Readers must never observe a truncated snapshot.

    `write_text` truncates in place. Binary-frame refreshes raised the write
    rate ~500x, and 10+ consumers read this file, so a partial read would
    surface as a JSONDecodeError in production.
    """
    import threading

    import transports.node_mesh.registry as reg_mod

    snap = tmp_path / "mesh_nodes.json"
    monkeypatch.setattr(reg_mod, "_SNAPSHOT_PATH", snap)

    reg = NodeRegistry(heartbeat_timeout_s=90)
    for i in range(12):  # enough nodes that a partial write would be visible
        reg.add(_node(f"n{i}"))

    errors: list[str] = []
    stop = threading.Event()

    def writer():
        while not stop.is_set():
            reg.update_heartbeat("n0")

    def reader():
        while not stop.is_set():
            try:
                text = snap.read_text(encoding="utf-8")
            except FileNotFoundError:
                continue
            if not text:
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f"truncated read: {exc}")
                return
            if not isinstance(parsed, list):
                errors.append(f"unexpected shape: {type(parsed)}")
                return

    threads = [
        threading.Thread(target=writer),
        *(threading.Thread(target=reader) for _ in range(3)),
    ]
    for t in threads:
        t.start()
    time.sleep(1.5)
    stop.set()
    for t in threads:
        t.join(timeout=5)

    assert not errors, f"snapshot was read in a torn state: {errors[:3]}"
    assert not list(tmp_path.glob("*.tmp")), "temp file leaked"


def test_json_heartbeat_still_refreshes():
    reg = NodeRegistry(heartbeat_timeout_s=0.05)
    reg.add(_node())
    time.sleep(0.04)
    assert reg.update_heartbeat("n1", {"cpu": 10}) is True
    assert "n1" not in reg.stale_nodes()


def test_json_heartbeat_metrics_preserved():
    """Requirement 2: the JSON heartbeat path still records metrics unchanged."""
    reg = NodeRegistry(heartbeat_timeout_s=5)
    reg.add(_node())
    reg.update_heartbeat("n1", {"cpu_percent": 42})
    node = reg.get("n1")
    assert node is not None
    assert node.latest_metrics.get("cpu_percent") == 42


def test_binary_refresh_does_not_clobber_metrics():
    """A binary refresh passes no metrics — it must not erase existing ones."""
    reg = NodeRegistry(heartbeat_timeout_s=5)
    reg.add(_node())
    reg.update_heartbeat("n1", {"cpu_percent": 42})
    reg.update_heartbeat("n1")  # the binary-frame refresh shape
    node = reg.get("n1")
    assert node is not None
    assert node.latest_metrics.get("cpu_percent") == 42, (
        "binary refresh must update liveness only, never clear reported metrics"
    )
