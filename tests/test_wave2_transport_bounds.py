from __future__ import annotations

import asyncio
import json
from collections import deque
from types import SimpleNamespace

import pytest

from nodes.windows.umh_node import client as client_mod
from nodes.windows.umh_node.client import (
    NodeClient,
    TransportQueueOverload,
    TransportSendDeadlineExceeded,
)
from nodes.windows.umh_node.config import NodeConfig
from substrate.execution.durable_remote_transport import DurableRemoteStore, make_request


class _AsyncHttpResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self.body = body
        self.content = self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def read(self, _limit: int) -> bytes:
        return self.body


class _NeverCompletingHttpResponse(_AsyncHttpResponse):
    async def read(self, _limit: int) -> bytes:
        await asyncio.Event().wait()
        raise AssertionError("unreachable")


class _AsyncHttpSession:
    def __init__(self, response=None, failure: BaseException | None = None, **kwargs) -> None:
        self.response = response
        self.failure = failure
        self.trace_configs = kwargs.get("trace_configs", [])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def post(self, *_args, **_kwargs):
        if self.failure is not None:
            raise self.failure

        session = self
        response = self.response

        class _RequestContext:
            async def __aenter__(self):
                for trace in session.trace_configs:
                    for callback in trace.on_request_headers_sent:
                        await callback(session, SimpleNamespace(), SimpleNamespace())
                return response

            async def __aexit__(self, *_exit_args):
                return False

        return _RequestContext()


def _client(tmp_path) -> NodeClient:
    client = object.__new__(NodeClient)
    client._config = NodeConfig(
        vps_host="controller.test",
        node_id="windows-desktop",
        token="test-token",
    )
    client._connected = True
    client._ws = None
    client._msg_id = 0
    client._pending_rpc = {}
    client._pending_rpc_generations = {}
    client._durable_store = DurableRemoteStore(tmp_path)
    client._durable_processes = {}
    client._durable_execution_locks = {}
    client._durable_request_gates = {}
    client._durable_request_trajectories = {}
    client._media_queue = deque(maxlen=4)
    client._media_event = asyncio.Event()
    client._adapters = {}
    client._ws_generation = 1
    client._active_ws_generation = 1
    client._ws_queue_generation = 1
    client._generation_tasks = {1: set()}
    client._generation_task_labels = {}
    client._generation_teardown_failed = False
    client._ws_transport_healthy = True
    return client


def _request():
    return make_request(
        correlation_id="corr-transport-bound",
        candidate_sha="a" * 40,
        node_id="windows-desktop",
        operation_type="wave2_transport_bound",
        capability="shell",
        params={"command": "echo bounded"},
        risk_class="reversible_write",
        idempotency_key="transport-bound-key",
    )


class _AbortableTransport:
    def __init__(self, release: asyncio.Event) -> None:
        self.release = release
        self.aborted = False

    def abort(self) -> None:
        self.aborted = True
        self.release.set()


def test_blocked_maximum_media_send_invalidates_transport_and_preserves_authority(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(client_mod, "_WS_SEND_DEADLINE_S", 0.02)
    release = asyncio.Event()
    bulk_started = asyncio.Event()

    class _Ws:
        def __init__(self) -> None:
            self.transport = _AbortableTransport(release)

        async def send(self, _payload) -> None:
            if isinstance(_payload, bytes):
                bulk_started.set()
            await release.wait()

    async def run() -> tuple[object, object, bool, bool]:
        client = _client(tmp_path)
        client._ws = _Ws()
        bulk = asyncio.create_task(
            client._send_ws(
                b"x" * client_mod._BULK_MEDIA_MAX_FRAME_BYTES,
                traffic_class="BULK_MEDIA",
            )
        )
        await asyncio.wait_for(bulk_started.wait(), timeout=0.5)
        authority = asyncio.create_task(
            client._send_durable_event(
                "durable_command.claimed",
                {"request_id": "req-bound", "claim_id": "claim-bound", "state": "CLAIMED"},
                expect_ack=True,
                timeout_s=0.1,
            )
        )
        bulk_result, authority_result = await asyncio.gather(
            bulk,
            authority,
            return_exceptions=True,
        )
        await client._stop_ws_writer()
        return (
            bulk_result,
            authority_result,
            client._ws.transport.aborted,
            client._connected,
        )

    bulk_result, authority_result, aborted, connected = asyncio.run(run())
    assert isinstance(bulk_result, TransportSendDeadlineExceeded)
    assert authority_result["ok"] is False
    assert "deadline" in authority_result["error"]
    assert aborted is True
    assert connected is False


def test_authority_queue_capacity_overflow_is_visible_and_fails_transport(tmp_path) -> None:
    release = asyncio.Event()

    class _Ws:
        def __init__(self) -> None:
            self.transport = _AbortableTransport(release)

        async def send(self, _payload) -> None:
            await release.wait()

    async def run() -> tuple[dict[str, object], list[object], bool]:
        client = _client(tmp_path)
        client._ws = _Ws()
        client._ensure_ws_writer_state()
        queued = []
        for index in range(client_mod._WS_SEND_QUEUE_CAPACITY["AUTHORITY_CONTROL"]):
            future = asyncio.get_running_loop().create_future()
            client._queue_ws_send(
                json.dumps({"method": "authority", "index": index}),
                traffic_class="AUTHORITY_CONTROL",
                future=future,
            )
            queued.append(future)
        result = await client._send_durable_event(
            "durable_command.claimed",
            {"request_id": "req-overload", "claim_id": "claim-overload", "state": "CLAIMED"},
            expect_ack=True,
        )
        queued_results = await asyncio.gather(*queued, return_exceptions=True)
        await client._stop_ws_writer()
        return result or {}, queued_results, client._ws.transport.aborted

    result, queued_results, aborted = asyncio.run(run())
    assert result["ok"] is False
    assert "AUTHORITY_CONTROL_OVERLOAD" in result["error"]
    assert all(isinstance(item, TransportQueueOverload) for item in queued_results)
    assert aborted is True


@pytest.mark.parametrize(
    "traffic_class",
    ["AUTHORITY_CONTROL", "REQUIRED_CONTROL", "ORDINARY", "BULK_MEDIA"],
)
def test_each_transport_class_has_independent_finite_capacity(tmp_path, traffic_class) -> None:
    async def run() -> tuple[int, int]:
        client = _client(tmp_path)
        client._ensure_ws_writer_state()
        payload = b"frame" if traffic_class == "BULK_MEDIA" else "control"
        futures = []
        for _ in range(client_mod._WS_SEND_QUEUE_CAPACITY[traffic_class]):
            future = asyncio.get_running_loop().create_future()
            client._queue_ws_send(
                payload,
                traffic_class=traffic_class,
                future=future,
            )
            futures.append(future)
        with pytest.raises(TransportQueueOverload):
            client._queue_ws_send(
                payload,
                traffic_class=traffic_class,
                future=asyncio.get_running_loop().create_future(),
            )
        depth = len(client._ws_send_queues[traffic_class])
        other_depth = sum(
            len(queue)
            for name, queue in client._ws_send_queues.items()
            if name != traffic_class
        )
        client._fail_queued_ws_sends(ConnectionError("test cleanup"))
        await asyncio.gather(*futures, return_exceptions=True)
        return depth, other_depth

    depth, other_depth = asyncio.run(run())
    assert depth == client_mod._WS_SEND_QUEUE_CAPACITY[traffic_class]
    assert other_depth == 0


def test_last_valid_authority_frame_is_serviced_fifo_within_envelope(tmp_path) -> None:
    sent: list[int] = []

    class _Ws:
        async def send(self, payload: str) -> None:
            sent.append(int(json.loads(payload)["index"]))

    async def run() -> list[dict[str, object]]:
        client = _client(tmp_path)
        client._ws = _Ws()
        client._ensure_ws_writer_state()
        futures = []
        for index in range(client_mod._WS_SEND_QUEUE_CAPACITY["AUTHORITY_CONTROL"]):
            future = asyncio.get_running_loop().create_future()
            client._queue_ws_send(
                json.dumps({"index": index}),
                traffic_class="AUTHORITY_CONTROL",
                future=future,
            )
            futures.append(future)
        client._ensure_ws_writer_task()
        evidence = await asyncio.gather(*futures)
        await client._stop_ws_writer()
        return evidence

    evidence = asyncio.run(run())
    assert sent == list(range(client_mod._WS_SEND_QUEUE_CAPACITY["AUTHORITY_CONTROL"]))
    assert evidence[-1]["queue_wait_ms"] < client_mod._AUTHORITY_QUEUE_MAX_WAIT_S * 1000


def test_last_valid_authority_frame_accounts_for_lower_class_fairness_turn(tmp_path) -> None:
    sent: list[str] = []

    class _Ws:
        async def send(self, payload: str) -> None:
            parsed = json.loads(payload)
            sent.append(str(parsed.get("class", parsed.get("index"))))

    async def run() -> None:
        client = _client(tmp_path)
        client._ws = _Ws()
        client._ensure_ws_writer_state()
        client._authority_send_burst = client_mod._AUTHORITY_SEND_BURST_LIMIT
        futures = []
        lower = asyncio.get_running_loop().create_future()
        client._queue_ws_send(
            json.dumps({"class": "lower"}),
            traffic_class="ORDINARY",
            future=lower,
        )
        for index in range(client_mod._WS_SEND_QUEUE_CAPACITY["AUTHORITY_CONTROL"]):
            future = asyncio.get_running_loop().create_future()
            client._queue_ws_send(
                json.dumps({"index": index}),
                traffic_class="AUTHORITY_CONTROL",
                future=future,
            )
            futures.append(future)
        client._ensure_ws_writer_task()
        await asyncio.gather(lower, *futures)
        await client._stop_ws_writer()

    asyncio.run(run())
    assert sent == ["lower", *map(str, range(client_mod._WS_SEND_QUEUE_CAPACITY["AUTHORITY_CONTROL"]))]


def test_authority_service_envelope_fits_claim_acquisition_deadline() -> None:
    assert client_mod._AUTHORITY_LOWER_CLASS_INTERLEAVES_MAX == 1
    assert client_mod._AUTHORITY_SERVICE_START_BOUND_S == 18.25
    assert client_mod._AUTHORITY_SERVICE_COMPLETE_BOUND_S == 20.25
    assert client_mod._CLAIM_AUTHORITY_ENVELOPE_S == 28.25
    assert (
        client_mod._CLAIM_AUTHORITY_ENVELOPE_S
        < client_mod._DURABLE_CLAIM_ACQUIRE_TIMEOUT_S
    )


def test_required_overload_resets_transport_while_bulk_overload_is_isolated(tmp_path) -> None:
    async def run_required() -> tuple[bool, list[object]]:
        client = _client(tmp_path)
        release = asyncio.Event()
        client._ws = SimpleNamespace(transport=_AbortableTransport(release))
        client._ws.send = lambda _payload: release.wait()
        queued = []
        for _ in range(client_mod._WS_SEND_QUEUE_CAPACITY["REQUIRED_CONTROL"]):
            future = asyncio.get_running_loop().create_future()
            client._queue_ws_send(
                "required",
                traffic_class="REQUIRED_CONTROL",
                future=future,
            )
            queued.append(future)
        with pytest.raises(TransportQueueOverload):
            await client._send_ws("overflow", traffic_class="REQUIRED_CONTROL")
        results = await asyncio.gather(*queued, return_exceptions=True)
        await client._stop_ws_writer()
        return client._ws_transport_healthy, results

    async def run_bulk() -> tuple[bool, int]:
        client = _client(tmp_path)
        client._ws = SimpleNamespace()
        queued = []
        for _ in range(client_mod._WS_SEND_QUEUE_CAPACITY["BULK_MEDIA"]):
            future = asyncio.get_running_loop().create_future()
            client._queue_ws_send(
                b"bulk",
                traffic_class="BULK_MEDIA",
                future=future,
            )
            queued.append(future)
        with pytest.raises(TransportQueueOverload):
            await client._send_ws(b"overflow", traffic_class="BULK_MEDIA")
        depth = len(client._ws_send_queues["BULK_MEDIA"])
        client._fail_queued_ws_sends(ConnectionError("test cleanup"))
        await asyncio.gather(*queued, return_exceptions=True)
        return client._ws_transport_healthy, depth

    required_healthy, required_results = asyncio.run(run_required())
    bulk_healthy, bulk_depth = asyncio.run(run_bulk())
    assert required_healthy is False
    assert all(isinstance(item, TransportQueueOverload) for item in required_results)
    assert bulk_healthy is True
    assert bulk_depth == client_mod._WS_SEND_QUEUE_CAPACITY["BULK_MEDIA"]


def test_terminal_result_is_retained_when_authority_queue_overloads(tmp_path) -> None:
    async def run() -> tuple[dict[str, object], list[object], list[str]]:
        client = _client(tmp_path)
        release = asyncio.Event()
        client._ws = SimpleNamespace(transport=_AbortableTransport(release))
        client._ws.send = lambda _payload: release.wait()
        req = client._durable_store.put_request(_request())
        client._durable_store.mark_claimed(req.request_id, claim_id="claim-result")
        client._durable_store.publish_result(
            req.request_id,
            claim_id="claim-result",
            state="SUCCEEDED",
            result={"success": True},
            cleanup={"process_residue": []},
        )
        client._ensure_ws_writer_state()
        queued = []
        for index in range(client_mod._WS_SEND_QUEUE_CAPACITY["AUTHORITY_CONTROL"]):
            future = asyncio.get_running_loop().create_future()
            client._queue_ws_send(
                json.dumps({"index": index}),
                traffic_class="AUTHORITY_CONTROL",
                future=future,
            )
            queued.append(future)
        result = await client._send_durable_event(
            "durable_command.result",
            {
                "request_id": req.request_id,
                "claim_id": "claim-result",
                "state": "SUCCEEDED",
                "result": {"success": True},
                "cleanup": {"process_residue": []},
            },
        )
        queued_results = await asyncio.gather(*queued, return_exceptions=True)
        await client._stop_ws_writer()
        replayed: list[str] = []

        class _RecoveredWs:
            async def send(self, raw: str) -> None:
                replayed.append(str(json.loads(raw)["method"]))

        client._ws_generation += 1
        client._ws = _RecoveredWs()
        client._connected = True
        client._ws_transport_healthy = True
        stored = client._durable_store.result_for(req.request_id) or {}
        await client._send_durable_event(
            "durable_command.result",
            {
                "request_id": req.request_id,
                "claim_id": stored["claim_id"],
                "state": stored["state"],
                "result": stored["result"],
                "cleanup": stored["cleanup"],
                "idempotent_replay": True,
            },
        )
        await client._stop_ws_writer()
        return stored, [result, *queued_results], replayed

    stored, results, replayed = asyncio.run(run())
    assert stored["state"] == "SUCCEEDED"
    assert stored["result"]["success"] is True
    assert results[0]["ok"] is False
    assert all(isinstance(item, TransportQueueOverload) for item in results[1:])
    assert replayed == ["durable_command.result"]


def test_continuous_media_production_cannot_starve_authority(tmp_path) -> None:
    class _Ws:
        def __init__(self, client: NodeClient) -> None:
            self.client = client
            self.bulk_sent = 0
            self.authority_sent = False

        async def send(self, payload) -> None:
            if isinstance(payload, bytes):
                self.bulk_sent += 1
                if not self.authority_sent:
                    future = asyncio.get_running_loop().create_future()
                    self.client._queue_ws_send(
                        b"replacement-frame",
                        traffic_class="BULK_MEDIA",
                        future=future,
                    )
                await asyncio.sleep(0)
                return
            message = json.loads(payload)
            self.authority_sent = True
            await self.client._handle_message(
                json.dumps({"jsonrpc": "2.0", "result": {"ok": True}, "id": message["id"]})
            )

    async def run() -> tuple[dict[str, object], int]:
        client = _client(tmp_path)
        client._ws = _Ws(client)
        first_bulk = asyncio.create_task(
            client._send_ws(b"first-frame", traffic_class="BULK_MEDIA")
        )
        while client._ws.bulk_sent < 1:
            await asyncio.sleep(0)
        ack = await asyncio.wait_for(
            client._send_durable_event(
                "durable_command.claimed",
                {"request_id": "req-live", "claim_id": "claim-live", "state": "CLAIMED"},
                expect_ack=True,
                timeout_s=1.0,
            ),
            timeout=2.0,
        )
        await asyncio.wait_for(first_bulk, timeout=1.0)
        drain_deadline = asyncio.get_running_loop().time() + 1.0
        while any(client._ws_send_queues.values()) and asyncio.get_running_loop().time() < drain_deadline:
            await asyncio.sleep(0)
        assert not any(client._ws_send_queues.values())
        await client._stop_ws_writer()
        return ack or {}, client._ws.bulk_sent

    ack, bulk_sent = asyncio.run(run())
    assert ack["ok"] is True
    assert bulk_sent >= 2


def test_cancellation_uses_authority_service_during_bulk_pressure(tmp_path) -> None:
    sent: list[str] = []

    class _Ws:
        async def send(self, payload) -> None:
            if isinstance(payload, bytes):
                sent.append("bulk")
                await asyncio.sleep(0)
                return
            sent.append(str(json.loads(payload)["method"]))

    async def run() -> None:
        client = _client(tmp_path)
        client._ws = _Ws()
        client._ensure_ws_writer_state()
        bulk_futures = []
        for _ in range(client_mod._WS_SEND_QUEUE_CAPACITY["BULK_MEDIA"]):
            future = asyncio.get_running_loop().create_future()
            client._queue_ws_send(
                b"frame",
                traffic_class="BULK_MEDIA",
                future=future,
            )
            bulk_futures.append(future)
        await client._send_durable_event(
            "durable_command.cancelled",
            {
                "request_id": "req-cancel",
                "claim_id": "claim-cancel",
                "state": "CANCELLED",
                "cleanup": {"process_residue": []},
            },
        )
        await asyncio.gather(*bulk_futures)
        await client._stop_ws_writer()

    asyncio.run(run())
    assert sent[0] == "durable_command.cancelled"
    assert sent.count("bulk") == client_mod._WS_SEND_QUEUE_CAPACITY["BULK_MEDIA"]


@pytest.mark.parametrize(
    "method",
    [
        "durable_command.claimed",
        "durable_command.result",
        "durable_command.cancelled",
    ],
)
def test_durable_lifecycle_frames_are_explicit_authority_control(
    tmp_path, method
) -> None:
    async def run() -> str:
        client = _client(tmp_path)
        observed_class = ""

        async def send(raw_payload, *, traffic_class, generation=None):
            nonlocal observed_class
            observed_class = traffic_class
            message = json.loads(raw_payload)
            if method == "durable_command.result":
                delivery = client._durable_store.terminal_result_delivery_for(
                    message["params"]["request_id"]
                )
                assert delivery is not None
                response = {
                        "id": message["id"],
                        "result": {
                            "ok": True,
                            **{
                                key: delivery[key]
                                for key in (
                                    "request_id",
                                    "correlation_id",
                                    "candidate_sha",
                                    "node_id",
                                    "claim_id",
                                    "state",
                                    "result_digest",
                                    "result_id",
                                )
                            },
                        },
                    }
                asyncio.get_running_loop().call_soon(
                    lambda: client._handle_rpc_response(
                        response,
                        generation=generation,
                    )
                )
            return {
                "seq": 1,
                "traffic_class": traffic_class,
                "generation": client._ws_generation,
                "queue_wait_ms": 0.0,
                "send_ms": 0.0,
            }

        client._ws = SimpleNamespace()
        client._send_ws = send
        payload = {
            "request_id": "req-classification",
            "claim_id": "claim-classification",
            "state": "CLAIMED",
        }
        if method == "durable_command.result":
            req = _request()
            client._durable_store.put_request(req)
            client._durable_store.mark_claimed(
                req.request_id,
                claim_id="claim-classification",
                process_tree={"root_pid": 0},
            )
            client._durable_store.publish_result(
                req.request_id,
                claim_id="claim-classification",
                state="FAILED",
                result={"success": False, "error": "classification"},
                cleanup={"process_residue": []},
            )
            payload = {
                "request_id": req.request_id,
                "claim_id": "claim-classification",
                "state": "FAILED",
            }
        await client._send_durable_event(
            method,
            payload,
        )
        return observed_class

    assert asyncio.run(run()) == "AUTHORITY_CONTROL"


def test_http_readback_records_bound_identity_and_success_stages(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)
    req = client._durable_store.put_request(_request())

    response = _AsyncHttpResponse(
        200,
        json.dumps({"ok": True, "accepted": True}).encode(),
    )
    monkeypatch.setattr(
        client_mod.aiohttp,
        "ClientSession",
        lambda **kwargs: _AsyncHttpSession(response=response, **kwargs),
    )
    payload = {
        "request_id": req.request_id,
        "claim_id": "claim-http",
        "correlation_id": req.correlation_id,
        "candidate_sha": req.candidate_sha,
        "node_id": req.node_id,
    }
    result = asyncio.run(client._read_canonical_durable_claim_state(payload, timeout_s=0.5))
    current = client._durable_store.get_request(req.request_id)
    events = current.diagnostics["transport_control"]["events"]
    names = [event["event"] for event in events]
    assert result["ok"] is True
    assert names[-6:] == [
        "NODE_CLAIM_READBACK_START",
        "NODE_CLAIM_READBACK_CONNECT_START",
        "NODE_CLAIM_READBACK_REQUEST_SENT",
        "NODE_CLAIM_READBACK_HTTP_STATUS",
        "NODE_CLAIM_READBACK_RESPONSE_RECEIVED",
        "NODE_CLAIM_READBACK_END",
    ]
    for event in events[-6:]:
        assert event["request_id"] == req.request_id
        assert event["claim_id"] == "claim-http"
        assert event["correlation_id"] == req.correlation_id
        assert event["candidate_sha"] == req.candidate_sha
        assert event["node_id"] == req.node_id
        assert event["readback_id"]


@pytest.mark.parametrize(
    ("failure", "expected_stage"),
    [
        (TimeoutError("slow"), "NODE_CLAIM_READBACK_TIMEOUT"),
        (
            client_mod.aiohttp.ClientConnectionError("offline"),
            "NODE_CLAIM_READBACK_TRANSPORT_ERROR",
        ),
    ],
)
def test_http_readback_failures_are_causally_distinguishable(
    tmp_path, monkeypatch, failure, expected_stage
) -> None:
    client = _client(tmp_path)
    req = client._durable_store.put_request(_request())

    monkeypatch.setattr(
        client_mod.aiohttp,
        "ClientSession",
        lambda **kwargs: _AsyncHttpSession(failure=failure, **kwargs),
    )
    result = asyncio.run(
        client._read_canonical_durable_claim_state(
            {
                "request_id": req.request_id,
                "claim_id": "claim-http",
                "correlation_id": req.correlation_id,
                "candidate_sha": req.candidate_sha,
                "node_id": req.node_id,
            },
            timeout_s=0.5,
        )
    )
    current = client._durable_store.get_request(req.request_id)
    names = [
        event["event"]
        for event in current.diagnostics["transport_control"]["events"]
    ]
    assert result["ok"] is False
    assert expected_stage in names


def test_http_readback_never_completing_response_has_finite_outer_bound(
    tmp_path, monkeypatch
) -> None:
    client = _client(tmp_path)
    req = client._durable_store.put_request(_request())
    monkeypatch.setattr(
        client_mod.aiohttp,
        "ClientSession",
        lambda **kwargs: _AsyncHttpSession(
            response=_NeverCompletingHttpResponse(200, b""),
            **kwargs,
        ),
    )

    async def run():
        return await asyncio.wait_for(
            client._read_canonical_durable_claim_state(
                {
                    "request_id": req.request_id,
                    "claim_id": "claim-http",
                    "correlation_id": req.correlation_id,
                    "candidate_sha": req.candidate_sha,
                    "node_id": req.node_id,
                },
                timeout_s=0.02,
            ),
            timeout=0.2,
        )

    result = asyncio.run(run())
    current = client._durable_store.get_request(req.request_id)
    names = [
        event["event"]
        for event in current.diagnostics["transport_control"]["events"]
    ]
    assert result["ok"] is False
    assert "NODE_CLAIM_READBACK_TIMEOUT" in names


def test_http_readback_non_2xx_and_invalid_json_are_distinct(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)
    req = client._durable_store.put_request(_request())
    payload = {
        "request_id": req.request_id,
        "claim_id": "claim-http",
        "correlation_id": req.correlation_id,
        "candidate_sha": req.candidate_sha,
        "node_id": req.node_id,
    }

    response = _AsyncHttpResponse(503, b"unavailable")
    monkeypatch.setattr(
        client_mod.aiohttp,
        "ClientSession",
        lambda **kwargs: _AsyncHttpSession(response=response, **kwargs),
    )
    failed = asyncio.run(client._read_canonical_durable_claim_state(payload, timeout_s=0.5))
    assert failed["ok"] is False
    assert failed["retryable"] is True

    invalid_response = _AsyncHttpResponse(200, b"not-json")
    monkeypatch.setattr(
        client_mod.aiohttp,
        "ClientSession",
        lambda **kwargs: _AsyncHttpSession(response=invalid_response, **kwargs),
    )
    invalid = asyncio.run(client._read_canonical_durable_claim_state(payload, timeout_s=0.5))
    current = client._durable_store.get_request(req.request_id)
    names = [
        event["event"]
        for event in current.diagnostics["transport_control"]["events"]
    ]
    assert invalid["ok"] is False
    assert "NODE_CLAIM_READBACK_HTTP_STATUS" in names
    assert "NODE_CLAIM_READBACK_VALIDATION_ERROR" in names


def test_http_readback_exact_claim_binding_records_validation(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)
    req = client._durable_store.put_request(_request())

    async def readback(_payload, **_kwargs):
        return {
            "ok": True,
            "accepted": True,
            "request_id": req.request_id,
            "correlation_id": req.correlation_id,
            "candidate_sha": req.candidate_sha,
            "node_id": req.node_id,
            "claim_id": "claim-exact",
            "lifecycle_state": "CLAIMED",
            "authority_source": "vps_canonical_durable_store",
            "_readback_id": "readback-exact",
        }

    monkeypatch.setattr(client, "_read_canonical_durable_claim_state", readback)
    result = asyncio.run(
        client._reconcile_durable_claim_state(
            req,
            claim_id="claim-exact",
            expected_state="CLAIMED",
            timeout_s=0.5,
        )
    )
    current = client._durable_store.get_request(req.request_id)
    events = current.diagnostics["transport_control"]["events"]
    assert result["ok"] is True
    assert events[-1]["event"] == "NODE_CLAIM_READBACK_RESPONSE_VALIDATED"
    assert events[-1]["readback_id"] == "readback-exact"


def test_http_readback_foreign_identity_fails_exact_canonical_binding(tmp_path) -> None:
    client = _client(tmp_path)
    req = client._durable_store.put_request(_request())
    result = client._validate_durable_claim_authority(
        {
            "ok": True,
            "accepted": True,
            "request_id": req.request_id,
            "correlation_id": req.correlation_id,
            "candidate_sha": req.candidate_sha,
            "node_id": req.node_id,
            "claim_id": "foreign-claim",
            "lifecycle_state": "CLAIMED",
            "authority_source": "vps_canonical_durable_store",
        },
        req,
        claim_id="claim-exact",
        expected_state="CLAIMED",
        label="claim readback",
    )
    assert result["ok"] is False
    assert result["accepted"] is False
    assert "claim_id" in result["error"]


def test_stale_rpc_response_cannot_satisfy_new_transport_generation(tmp_path) -> None:
    async def run() -> tuple[bool, bool]:
        client = _client(tmp_path)
        future = asyncio.get_running_loop().create_future()
        client._pending_rpc[7] = future
        client._pending_rpc_generations[7] = 1
        client._ws_generation = 2
        client._active_ws_generation = 2
        client._handle_rpc_response({"id": 7, "result": {"ok": True}})
        stale_rejected = not future.done()
        client._pending_rpc_generations[7] = 2
        client._handle_rpc_response({"id": 7, "result": {"ok": True}})
        return stale_rejected, bool((await future)["ok"])

    assert asyncio.run(run()) == (True, True)


def test_historical_starvation_shape_uses_http_readback_under_continuous_bulk(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(client_mod, "_CONTROL_TIMEOUT_S", 0.02)
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_ACQUIRE_TIMEOUT_S", 0.25)

    class _Ws:
        def __init__(self) -> None:
            self.bulk_sends = 0
            self.claim_sends = 0

        async def send(self, payload) -> None:
            if isinstance(payload, bytes):
                self.bulk_sends += 1
                await asyncio.sleep(0.001)
                return
            if json.loads(payload).get("method") == "durable_command.claimed":
                self.claim_sends += 1
                # Model the observed lost acknowledgement after canonical claim persistence.
                return

    async def run() -> tuple[dict[str, object], int, int, int]:
        client = _client(tmp_path)
        client._ws = _Ws()
        req = client._durable_store.put_request(_request())
        readbacks = 0
        keep_producing = True

        async def readback(_payload, **_kwargs):
            nonlocal readbacks
            readbacks += 1
            return {
                "ok": True,
                "accepted": True,
                "request_id": req.request_id,
                "correlation_id": req.correlation_id,
                "candidate_sha": req.candidate_sha,
                "node_id": req.node_id,
                "claim_id": "claim-combined",
                "lifecycle_state": "CLAIMED",
                "authority_source": "vps_canonical_durable_store",
                "_readback_id": "combined-readback",
            }

        client._read_canonical_durable_claim_state = readback

        async def produce_bulk() -> None:
            while keep_producing:
                await client._send_ws(b"media", traffic_class="BULK_MEDIA")

        producer = asyncio.create_task(produce_bulk())
        while client._ws.bulk_sends == 0:
            await asyncio.sleep(0)
        lower_futures = []
        for index in range(4):
            future = asyncio.get_running_loop().create_future()
            client._queue_ws_send(
                json.dumps({"reconciliation": index}),
                traffic_class="ORDINARY",
                future=future,
            )
            lower_futures.append(future)
        result = await client._acquire_durable_claim(
            req,
            claim_id="claim-combined",
            process_tree={},
        )
        keep_producing = False
        await producer
        await asyncio.gather(*lower_futures)
        await client._stop_ws_writer()
        return result, client._ws.claim_sends, client._ws.bulk_sends, readbacks

    result, claim_sends, bulk_sends, readbacks = asyncio.run(run())
    assert result["ok"] is True
    assert result["reconciled"] is True
    assert claim_sends == 1
    assert bulk_sends >= 2
    assert readbacks == 1


def test_authority_overload_cannot_satisfy_claim_acquisition(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_ACQUIRE_TIMEOUT_S", 0.1)

    async def run() -> dict[str, object]:
        client = _client(tmp_path)
        release = asyncio.Event()
        client._ws = SimpleNamespace(transport=_AbortableTransport(release))
        client._ws.send = lambda _payload: release.wait()
        req = client._durable_store.put_request(_request())
        client._ensure_ws_writer_state()
        queued = []
        for index in range(client_mod._WS_SEND_QUEUE_CAPACITY["AUTHORITY_CONTROL"]):
            future = asyncio.get_running_loop().create_future()
            client._queue_ws_send(
                json.dumps({"index": index}),
                traffic_class="AUTHORITY_CONTROL",
                future=future,
            )
            queued.append(future)

        async def unavailable(_payload, **_kwargs):
            return {
                "ok": False,
                "error": "canonical readback unavailable",
                "retryable": False,
            }

        client._read_canonical_durable_claim_state = unavailable
        result = await client._acquire_durable_claim(
            req,
            claim_id="claim-overload-acquire",
            process_tree={},
        )
        await asyncio.gather(*queued, return_exceptions=True)
        await client._stop_ws_writer()
        return result

    result = asyncio.run(run())
    assert result["ok"] is False
    assert "readback unavailable" in result["error"]
