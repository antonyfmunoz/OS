from __future__ import annotations

import asyncio
import json
from collections import deque
from types import SimpleNamespace

import pytest

from nodes.windows.umh_node import client as client_mod
from nodes.windows.umh_node.client import (
    NodeClient,
    TransportGenerationTeardownFailed,
)
from nodes.windows.umh_node.config import NodeConfig
from substrate.execution import durable_remote_transport as durable_mod
from substrate.execution.durable_remote_transport import DurableRemoteStore, make_request


def _client(root) -> NodeClient:
    client = object.__new__(NodeClient)
    client._config = NodeConfig(
        vps_host="controller.test",
        node_id="windows-desktop",
        token="test-token",
    )
    client._connected = True
    client._ws = SimpleNamespace()
    client._msg_id = 0
    client._pending_rpc = {}
    client._pending_rpc_generations = {}
    client._durable_store = DurableRemoteStore(root)
    client._durable_processes = {}
    client._durable_execution_locks = {}
    client._durable_logical_executions = {}
    client._durable_request_gates = {}
    client._durable_request_trajectories = {}
    client._media_queue = deque(maxlen=4)
    client._media_event = asyncio.Event()
    client._media_drain_task = None
    client._adapters = {}
    client._ws_generation = 1
    client._active_ws_generation = 1
    client._ws_queue_generation = 1
    client._generation_tasks = {1: set()}
    client._generation_task_labels = {}
    client._generation_teardown_failed = False
    client._ws_transport_healthy = True
    return client


def _persist_terminal(client: NodeClient, *, suffix: str = "outbox") -> tuple[object, dict]:
    request = make_request(
        correlation_id=f"corr-{suffix}",
        candidate_sha="a" * 40,
        node_id="windows-desktop",
        operation_type="wave2_terminal_outbox",
        capability="shell",
        params={"command": "echo already-executed"},
        idempotency_key=f"terminal-outbox-{suffix}",
    )
    request = client._durable_store.put_request(request)
    client._durable_store.mark_claimed(
        request.request_id,
        claim_id=f"claim-{suffix}",
        process_tree={"root_pid": 1234},
    )
    client._durable_store.mark_running(
        request.request_id,
        claim_id=f"claim-{suffix}",
        process_tree={"root_pid": 1234},
    )
    client._durable_store.publish_result(
        request.request_id,
        claim_id=f"claim-{suffix}",
        state="SUCCEEDED",
        result={"success": True, "stdout": "already executed"},
        cleanup={"process_residue": [], "cleanup_verified": True},
    )
    result = client._durable_store.result_for(request.request_id)
    assert result is not None
    return request, result


def _receipt(delivery: dict) -> dict:
    return {
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
    }


def _install_receipting_send(client: NodeClient, sent: list[dict]) -> None:
    async def send(raw, *, traffic_class, generation=None):
        message = json.loads(raw)
        sent.append(message)
        delivery = client._durable_store.terminal_result_delivery_for(
            message["params"]["request_id"]
        )
        assert delivery is not None
        response = {"id": message["id"], "result": _receipt(delivery)}
        asyncio.get_running_loop().call_soon(
            lambda: client._handle_rpc_response(response, generation=generation)
        )
        return {
            "seq": len(sent),
            "traffic_class": traffic_class,
            "generation": generation,
            "queue_wait_ms": 0.0,
            "send_ms": 0.0,
        }

    client._send_ws = send


def test_reconnect_autonomously_replays_exact_terminal_result_without_execution(tmp_path) -> None:
    async def run() -> tuple[dict, list[dict], dict, int]:
        client = _client(tmp_path)
        request, result = _persist_terminal(client)
        sent: list[dict] = []
        execution_count = 0

        async def execute_again(*_args, **_kwargs) -> None:
            nonlocal execution_count
            execution_count += 1

        client._execute_accepted_durable_claim = execute_again
        _install_receipting_send(client, sent)

        replay = asyncio.create_task(client._terminal_result_replay_loop(1))
        for _ in range(100):
            delivery = client._durable_store.terminal_result_delivery_for(request.request_id)
            if delivery is not None and delivery["delivery_state"] == "ACKNOWLEDGED":
                break
            await asyncio.sleep(0.01)
        client._connected = False
        await replay
        delivery = client._durable_store.terminal_result_delivery_for(request.request_id)
        assert delivery is not None
        return delivery, sent, result, execution_count

    delivery, sent, result, execution_count = asyncio.run(run())
    assert delivery["delivery_state"] == "ACKNOWLEDGED"
    assert len(sent) == 1
    assert sent[0]["method"] == "durable_command.result"
    assert sent[0]["params"]["result_digest"] == result["result_digest"]
    assert execution_count == 0


def test_node_startup_discovers_pending_terminal_result(tmp_path) -> None:
    async def run() -> tuple[dict, list[dict]]:
        first = _client(tmp_path)
        request, _result = _persist_terminal(first, suffix="startup")

        restarted = _client(tmp_path)
        sent: list[dict] = []
        _install_receipting_send(restarted, sent)
        replay = asyncio.create_task(restarted._terminal_result_replay_loop(1))
        for _ in range(100):
            delivery = restarted._durable_store.terminal_result_delivery_for(
                request.request_id
            )
            if delivery is not None and delivery["delivery_state"] == "ACKNOWLEDGED":
                break
            await asyncio.sleep(0.01)
        restarted._connected = False
        await replay
        delivery = restarted._durable_store.terminal_result_delivery_for(request.request_id)
        assert delivery is not None
        return delivery, sent

    delivery, sent = asyncio.run(run())
    assert len(sent) == 1
    assert delivery["delivery_state"] == "ACKNOWLEDGED"


def test_lost_result_receipt_replays_same_identity_after_backoff(
    tmp_path,
    monkeypatch,
) -> None:
    clock = [1000.0]
    monkeypatch.setattr(durable_mod, "now_s", lambda: clock[0])
    client = _client(tmp_path)
    request, _result = _persist_terminal(client, suffix="lost-ack")
    sent: list[dict] = []

    async def no_receipt(raw, *, traffic_class, generation=None):
        sent.append(json.loads(raw))
        return {
            "seq": 1,
            "traffic_class": traffic_class,
            "generation": generation,
            "queue_wait_ms": 0.0,
            "send_ms": 0.0,
        }

    client._send_ws = no_receipt
    first = asyncio.run(
        client._send_durable_event(
            "durable_command.result",
            {"request_id": request.request_id},
            timeout_s=0.01,
        )
    )
    pending = client._durable_store.terminal_result_delivery_for(request.request_id)
    assert first["ok"] is False
    assert pending is not None and pending["delivery_state"] == "PENDING"
    assert client._durable_store.pending_terminal_result_deliveries(current_time=1000.5) == []

    clock[0] += 2.0
    _install_receipting_send(client, sent)
    async def replay() -> None:
        task = asyncio.create_task(client._terminal_result_replay_loop(1))
        for _ in range(100):
            delivery = client._durable_store.terminal_result_delivery_for(request.request_id)
            if delivery is not None and delivery["delivery_state"] == "ACKNOWLEDGED":
                break
            await asyncio.sleep(0.01)
        client._connected = False
        await task

    asyncio.run(replay())
    acknowledged = client._durable_store.terminal_result_delivery_for(request.request_id)
    assert acknowledged is not None and acknowledged["delivery_state"] == "ACKNOWLEDGED"
    assert sent[0]["params"]["result_id"] == sent[1]["params"]["result_id"]


def test_terminal_result_send_failure_preserves_pending_delivery(tmp_path) -> None:
    client = _client(tmp_path)
    request, result = _persist_terminal(client, suffix="send-failure")

    async def failed_send(*_args, **_kwargs):
        raise ConnectionError("connection generation closed")

    client._send_ws = failed_send
    response = asyncio.run(
        client._send_durable_event(
            "durable_command.result",
            {"request_id": request.request_id},
        )
    )

    delivery = client._durable_store.terminal_result_delivery_for(request.request_id)
    assert response["ok"] is False
    assert response["retryable"] is True
    assert delivery is not None
    assert delivery["delivery_state"] == "PENDING"
    assert delivery["last_error"] == "connection generation closed"
    assert client._durable_store.result_for(request.request_id) == result


def test_result_receipt_with_foreign_identity_enters_reconciliation(tmp_path) -> None:
    client = _client(tmp_path)
    request, _result = _persist_terminal(client, suffix="foreign-receipt")

    async def send(raw, *, traffic_class, generation=None):
        message = json.loads(raw)
        delivery = client._durable_store.terminal_result_delivery_for(request.request_id)
        assert delivery is not None
        receipt = _receipt(delivery)
        receipt["claim_id"] = "foreign-claim"
        response = {"id": message["id"], "result": receipt}
        asyncio.get_running_loop().call_soon(
            lambda: client._handle_rpc_response(response, generation=generation)
        )
        return {"traffic_class": traffic_class, "generation": generation}

    client._send_ws = send
    ack = asyncio.run(
        client._send_durable_event(
            "durable_command.result",
            {"request_id": request.request_id},
        )
    )
    delivery = client._durable_store.terminal_result_delivery_for(request.request_id)
    assert ack["ok"] is False
    assert delivery is not None
    assert delivery["delivery_state"] == "RECONCILIATION_REQUIRED"
    assert delivery["next_attempt_at"] == 0.0
    second = asyncio.run(
        client._send_durable_event(
            "durable_command.result",
            {"request_id": request.request_id},
        )
    )
    assert second["ok"] is False
    assert "governed reconciliation" in second["error"]


def test_node_shutdown_marks_unresolved_logical_execution_for_reconciliation(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(client_mod, "_LOGICAL_EXECUTION_TEARDOWN_S", 0.01)

    async def run() -> tuple[str, bool, bool]:
        client = _client(tmp_path)
        request = make_request(
            correlation_id="corr-shutdown-unresolved",
            candidate_sha="a" * 40,
            node_id="windows-desktop",
            operation_type="shutdown_unresolved",
            capability="terminal.execute",
            params={},
            idempotency_key="shutdown-unresolved",
        )
        request = client._durable_store.put_request(request)
        client._durable_store.mark_claimed(request.request_id, claim_id="claim-shutdown")
        client._durable_store.mark_running(request.request_id, claim_id="claim-shutdown")

        async def blocked_observer() -> None:
            await asyncio.Event().wait()

        task = asyncio.create_task(blocked_observer())
        client._durable_logical_executions[request.request_id] = {
            "identity": client._durable_request_identity(request),
            "state": "STARTED",
            "task": task,
            "operation_future": None,
        }
        await client._quiesce_logical_executions()
        current = client._durable_store.get_request(request.request_id)
        assert current is not None
        return current.lifecycle_state, task.done(), client._durable_store.result_for(
            request.request_id
        ) is None

    assert asyncio.run(run()) == ("RECONCILIATION_REQUIRED", True, True)


def test_logical_execution_callback_persists_unresolved_outcome(tmp_path) -> None:
    async def run() -> tuple[str, bool]:
        client = _client(tmp_path)
        request = make_request(
            correlation_id="corr-observer-unresolved",
            candidate_sha="a" * 40,
            node_id="windows-desktop",
            operation_type="observer_unresolved",
            capability="terminal.execute",
            params={},
            idempotency_key="observer-unresolved",
        )
        request = client._durable_store.put_request(request)
        client._durable_store.mark_claimed(request.request_id, claim_id="claim-observer")
        client._durable_store.mark_running(request.request_id, claim_id="claim-observer")

        async def interrupted_handler(_msg) -> None:
            entry = client._durable_logical_executions[request.request_id]
            entry["state"] = "STARTED"
            raise RuntimeError("synthetic observer loss")

        client._handle_durable_command = interrupted_handler
        client._schedule_logical_durable_command(
            {"method": "durable_command.request", "params": request.to_dict()}
        )
        task = client._durable_logical_executions[request.request_id]["task"]
        await task
        await asyncio.sleep(0)

        current = client._durable_store.get_request(request.request_id)
        assert current is not None
        return (
            current.lifecycle_state,
            client._durable_store.result_for(request.request_id) is None,
        )

    assert asyncio.run(run()) == ("RECONCILIATION_REQUIRED", True)


def test_old_generation_handler_cannot_enqueue_on_replacement_socket(tmp_path) -> None:
    client = _client(tmp_path)
    client._ws_generation = 2
    client._active_ws_generation = 2
    client._ws_queue_generation = 2
    token = client_mod._connection_generation_context.set(1)
    try:
        with pytest.raises(ConnectionError, match="not connected"):
            asyncio.run(client._send_ws("stale", traffic_class="AUTHORITY_CONTROL"))
    finally:
        client_mod._connection_generation_context.reset(token)
    assert all(not queue for queue in client._ws_send_queues.values())


def test_generation_teardown_cancels_awaits_and_clears_pending_rpc(tmp_path) -> None:
    async def run() -> tuple[int, int, bool, bool]:
        client = _client(tmp_path)
        wait_forever = asyncio.Event()
        tasks = [
            client._create_generation_task(
                wait_forever.wait(),
                generation=1,
                label=label,
            )
            for label in (
                "reader",
                "writer",
                "capability-handler",
                "durable-handler",
                "readback",
            )
        ]
        future = asyncio.get_running_loop().create_future()
        client._pending_rpc[7] = future
        client._pending_rpc_generations[7] = 1
        await client._teardown_connection_generation(1, client._ws)
        return (
            len(client._generation_tasks),
            len(client._pending_rpc),
            all(task.done() for task in tasks),
            bool((await asyncio.wait_for(future, timeout=0.5))["retryable"]),
        )

    assert asyncio.run(run()) == (0, 0, True, True)


def test_logical_durable_execution_survives_connection_generation_teardown(tmp_path) -> None:
    async def run() -> tuple[int, int, bool, bool]:
        client = _client(tmp_path)
        capability_entered = asyncio.Event()
        durable_entered = asyncio.Event()

        async def blocked_capability(_msg) -> None:
            capability_entered.set()
            await asyncio.Event().wait()

        async def blocked_durable(_msg) -> None:
            durable_entered.set()
            await asyncio.Event().wait()

        request = make_request(
            correlation_id="corr-logical-owner",
            candidate_sha="a" * 40,
            node_id="windows-desktop",
            operation_type="logical_execution_owner",
            capability="terminal.read",
            params={},
            idempotency_key="logical-execution-owner",
        )
        client._safe_handle_capability = blocked_capability
        client._safe_handle_durable_command = blocked_durable
        await client._handle_message(
            json.dumps({"method": "capability.execute"}), generation=1
        )
        await client._handle_message(
            json.dumps(
                {
                    "method": "durable_command.request",
                    "params": request.to_dict(),
                }
            ),
            generation=1,
        )
        await capability_entered.wait()
        await durable_entered.wait()
        generation_tasks = tuple(client._generation_tasks[1])
        logical_task = client._durable_logical_executions[request.request_id]["task"]
        assert len(generation_tasks) == 1
        assert logical_task not in generation_tasks
        await client._teardown_connection_generation(1, client._ws)
        logical_survived = not logical_task.done()
        logical_task.cancel()
        await asyncio.gather(logical_task, return_exceptions=True)
        return (
            len(client._generation_tasks),
            len(client._pending_rpc),
            all(task.done() for task in generation_tasks),
            logical_survived,
        )

    assert asyncio.run(run()) == (0, 0, True, True)


def test_generation_teardown_awaits_blocked_real_writer(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(client_mod, "_WS_SEND_DEADLINE_S", 30.0)

    class _Ws:
        async def send(self, _payload) -> None:
            await asyncio.Event().wait()

    async def run() -> tuple[bool, int]:
        client = _client(tmp_path)
        ws = _Ws()
        client._ws = ws
        send = asyncio.create_task(
            client._send_ws(
                "blocked",
                traffic_class="AUTHORITY_CONTROL",
                generation=1,
            )
        )
        for _ in range(100):
            if any(
                client._generation_task_labels.get(task) == "websocket-send"
                for task in client._generation_tasks[1]
            ):
                break
            await asyncio.sleep(0.01)
        await client._teardown_connection_generation(1, ws)
        result = await asyncio.wait_for(
            asyncio.gather(send, return_exceptions=True),
            timeout=0.5,
        )
        return isinstance(result[0], BaseException), len(client._generation_tasks)

    assert asyncio.run(run()) == (True, 0)


def test_stubborn_generation_task_blocks_replacement_authority(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(client_mod, "_CONNECTION_GENERATION_TEARDOWN_S", 0.02)

    async def run() -> tuple[bool, bool]:
        client = _client(tmp_path)
        release = asyncio.Event()

        async def stubborn() -> None:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                await release.wait()

        task = client._create_generation_task(
            stubborn(),
            generation=1,
            label="stubborn-handler",
        )
        await asyncio.sleep(0)
        try:
            with pytest.raises(
                TransportGenerationTeardownFailed,
                match="TRANSPORT_GENERATION_TEARDOWN_FAILED",
            ):
                await client._teardown_connection_generation(1, client._ws)
            with pytest.raises(TransportGenerationTeardownFailed):
                client._activate_connection_generation(SimpleNamespace())
        finally:
            release.set()
            await task
        return client._generation_teardown_failed, client._active_ws_generation is None

    assert asyncio.run(run()) == (True, True)


def test_connection_churn_leaves_no_tasks_futures_or_generation_queues(tmp_path) -> None:
    class _Ws:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, payload) -> None:
            self.sent.append(payload)

    async def run() -> tuple[int, int, int, bool]:
        client = _client(tmp_path)
        client._ensure_ws_writer_state()
        old_queues = dict(client._ws_send_queues)
        await client._teardown_connection_generation(1, client._ws)
        fresh_queue_ownership = True
        for _ in range(12):
            ws = _Ws()
            generation = client._activate_connection_generation(ws)
            fresh_queue_ownership = fresh_queue_ownership and all(
                client._ws_send_queues[name] is not old_queues[name]
                for name in client._ws_send_queues
            )
            old_queues = dict(client._ws_send_queues)
            client._connected = True
            await client._send_ws(
                "control",
                traffic_class="REQUIRED_CONTROL",
                generation=generation,
            )
            future = asyncio.get_running_loop().create_future()
            client._pending_rpc[generation] = future
            client._pending_rpc_generations[generation] = generation
            await client._teardown_connection_generation(generation, ws)
            assert (await asyncio.wait_for(future, timeout=0.5))["retryable"] is True
        return (
            len(client._generation_tasks),
            len(client._pending_rpc),
            sum(len(queue) for queue in client._ws_send_queues.values()),
            fresh_queue_ownership,
        )

    assert asyncio.run(run()) == (0, 0, 0, True)


def test_result_replay_and_stale_handler_are_isolated_across_generation(tmp_path) -> None:
    async def run() -> tuple[str, bool, int]:
        client = _client(tmp_path)
        request, _result = _persist_terminal(client, suffix="generation-race")
        await client._teardown_connection_generation(1, client._ws)

        class _Ws:
            async def send(self, raw) -> None:
                message = json.loads(raw)
                delivery = client._durable_store.terminal_result_delivery_for(
                    request.request_id
                )
                assert delivery is not None
                response = {"id": message["id"], "result": _receipt(delivery)}
                await client._handle_message(
                    json.dumps(response),
                    generation=generation,
                )

        ws = _Ws()
        generation = client._activate_connection_generation(ws)
        client._connected = True
        stale_rejected = False
        token = client_mod._connection_generation_context.set(generation - 1)
        try:
            with pytest.raises(ConnectionError):
                await client._send_ws(
                    "stale-handler-frame",
                    traffic_class="AUTHORITY_CONTROL",
                )
            stale_rejected = True
        finally:
            client_mod._connection_generation_context.reset(token)

        attempted = await client._replay_due_terminal_results(generation)
        delivery = client._durable_store.terminal_result_delivery_for(request.request_id)
        assert delivery is not None
        await client._teardown_connection_generation(generation, ws)
        return delivery["delivery_state"], stale_rejected, attempted

    assert asyncio.run(run()) == ("ACKNOWLEDGED", True, 1)
