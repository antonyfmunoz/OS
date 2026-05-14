"""Tests for Phase 5C: Event Stream + State Sync.

Verifies:
- Event creation and publishing
- Events emitted on execution lifecycle
- Events emitted on approval lifecycle
- API returns events via GET /events
- SSE endpoint streams events
- Ordering preserved
- Thread safety
- Identity/metadata attached to events
"""

import sys
import os
import json
import threading
import time

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase5a")

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import get_identity_store, reset_identity_store
from umh.events.stream import (
    Event,
    EventStream,
    get_event_stream,
    publish,
    reset_event_stream,
)
from umh.execution.approval import ApprovalStatus, get_approval_store
from umh.execution.contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionRequest,
    ExecutionTarget,
)
from umh.execution.engine import execute

client = TestClient(app)


def _reset():
    get_approval_store().reset()
    get_identity_store().reset()
    reset_event_stream()


def _create_identity(
    name: str = "test-actor",
    scopes: list[str] | None = None,
) -> tuple:
    store = get_identity_store()
    identity, raw_key = store.create_identity(name, scopes or ["admin"])
    headers = {"X-API-Key": raw_key}
    return identity, raw_key, headers


def _make_request(operation: str = "test_op", issued_by: str = "") -> ExecutionRequest:
    return ExecutionRequest(
        execution_id=f"exec_test_{operation}",
        correlation_id="corr_test",
        causal_event_id="",
        session_id="",
        operation=operation,
        inputs={"prompt": "hello", "system_prompt": "", "max_tokens": 100},
        execution_class=ExecutionClass.LLM_CALL,
        constraints=ExecutionConstraints(timeout_s=10),
        target=ExecutionTarget(node_id="local", transport="test"),
        context=ExecutionContext(metadata={}),
        issued_at="2026-01-01T00:00:00+00:00",
        issued_by=issued_by,
        idempotency_key="",
    )


# ── A. Event Core ──────────────────────────────────────────────────


class TestEventCore:
    def test_event_dataclass(self):
        e = Event(
            id="evt_test1",
            type="test.event",
            timestamp="2026-01-01T00:00:00",
            payload={"key": "value"},
            actor_id="actor_1",
            execution_id="exec_1",
        )
        assert e.type == "test.event"
        assert e.payload == {"key": "value"}
        assert e.actor_id == "actor_1"

    def test_event_to_dict(self):
        e = Event(
            id="evt_test2",
            type="test.event",
            timestamp="2026-01-01T00:00:00",
            payload={"x": 1},
        )
        d = e.to_dict()
        assert d["id"] == "evt_test2"
        assert d["type"] == "test.event"
        assert d["payload"] == {"x": 1}
        assert "actor_id" in d
        assert "execution_id" in d
        assert "approval_id" in d

    def test_event_immutable(self):
        e = Event(
            id="evt_imm",
            type="test.frozen",
            timestamp="2026-01-01T00:00:00",
            payload={},
        )
        try:
            e.type = "modified"
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass

    def test_event_defaults(self):
        e = Event(id="evt_d", type="t", timestamp="ts", payload={})
        assert e.actor_id == ""
        assert e.execution_id == ""
        assert e.approval_id == ""


# ── B. EventStream ─────────────────────────────────────────────────


class TestEventStream:
    def test_publish_and_list(self):
        stream = EventStream()
        e = Event(id="e1", type="t", timestamp="ts", payload={"a": 1})
        stream.publish(e)
        events = stream.list_events()
        assert len(events) == 1
        assert events[0].id == "e1"

    def test_list_with_limit(self):
        stream = EventStream()
        for i in range(10):
            stream.publish(Event(id=f"e{i}", type="t", timestamp="ts", payload={}))
        assert len(stream.list_events(limit=5)) == 5
        assert stream.list_events(limit=5)[0].id == "e5"

    def test_subscriber_called(self):
        stream = EventStream()
        received = []
        stream.subscribe(lambda e: received.append(e))
        e = Event(id="e_sub", type="t", timestamp="ts", payload={})
        stream.publish(e)
        assert len(received) == 1
        assert received[0].id == "e_sub"

    def test_unsubscribe(self):
        stream = EventStream()
        received = []
        cb = lambda e: received.append(e)
        stream.subscribe(cb)
        stream.publish(Event(id="e1", type="t", timestamp="ts", payload={}))
        stream.unsubscribe(cb)
        stream.publish(Event(id="e2", type="t", timestamp="ts", payload={}))
        assert len(received) == 1

    def test_subscriber_error_does_not_break_publish(self):
        stream = EventStream()
        good = []

        def bad_cb(e):
            raise RuntimeError("boom")

        stream.subscribe(bad_cb)
        stream.subscribe(lambda e: good.append(e))
        stream.publish(Event(id="e1", type="t", timestamp="ts", payload={}))
        assert len(good) == 1

    def test_max_events_bounded(self):
        stream = EventStream(max_events=5)
        for i in range(10):
            stream.publish(Event(id=f"e{i}", type="t", timestamp="ts", payload={}))
        assert stream.count() == 5
        assert stream.list_events()[0].id == "e5"

    def test_clear(self):
        stream = EventStream()
        stream.publish(Event(id="e1", type="t", timestamp="ts", payload={}))
        stream.subscribe(lambda e: None)
        stream.clear()
        assert stream.count() == 0
        assert stream.list_events() == []

    def test_ordering_preserved(self):
        stream = EventStream()
        for i in range(100):
            stream.publish(Event(id=f"e{i}", type="t", timestamp="ts", payload={}))
        events = stream.list_events(limit=100)
        for i, e in enumerate(events):
            assert e.id == f"e{i}"


# ── C. Thread Safety ───────────────────────────────────────────────


class TestThreadSafety:
    def test_concurrent_publish(self):
        stream = EventStream()
        barrier = threading.Barrier(4)

        def writer(prefix):
            barrier.wait()
            for i in range(50):
                stream.publish(Event(id=f"{prefix}_{i}", type="t", timestamp="ts", payload={}))

        threads = [threading.Thread(target=writer, args=(f"w{t}",)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert stream.count() == 200

    def test_concurrent_subscribe_publish(self):
        stream = EventStream()
        received = []
        lock = threading.Lock()

        def cb(e):
            with lock:
                received.append(e)

        stream.subscribe(cb)
        barrier = threading.Barrier(2)

        def writer():
            barrier.wait()
            for i in range(50):
                stream.publish(Event(id=f"e{i}", type="t", timestamp="ts", payload={}))

        t1 = threading.Thread(target=writer)
        t2 = threading.Thread(target=writer)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert len(received) == 100

    def test_wait_for_event(self):
        stream = EventStream()
        result = [None]

        def publisher():
            time.sleep(0.1)
            stream.publish(Event(id="waited", type="t", timestamp="ts", payload={}))

        t = threading.Thread(target=publisher)
        t.start()
        result[0] = stream.wait_for_event(timeout=2.0)
        t.join()
        assert result[0] is not None
        assert result[0].id == "waited"

    def test_wait_for_event_timeout(self):
        stream = EventStream()
        result = stream.wait_for_event(timeout=0.1)
        assert result is None


# ── D. Module-level publish() ──────────────────────────────────────


class TestModulePublish:
    def test_publish_creates_event(self):
        _reset()
        event = publish("test.event", payload={"x": 1}, actor_id="a1")
        assert event.type == "test.event"
        assert event.actor_id == "a1"
        assert event.id.startswith("evt_")

    def test_publish_adds_to_stream(self):
        _reset()
        publish("test.1", payload={})
        publish("test.2", payload={})
        events = get_event_stream().list_events()
        assert len(events) == 2

    def test_publish_with_all_metadata(self):
        _reset()
        event = publish(
            "test.full",
            payload={"data": True},
            actor_id="actor_x",
            execution_id="exec_y",
            approval_id="appr_z",
        )
        assert event.execution_id == "exec_y"
        assert event.approval_id == "appr_z"


# ── E. Execution Events ───────────────────────────────────────────


class TestExecutionEvents:
    def test_execution_emits_started_and_completed(self):
        _reset()
        req = _make_request("classify_intent", issued_by="actor_test")
        execute(req)
        events = get_event_stream().list_events()
        types = [e.type for e in events]
        assert "execution.started" in types
        assert "execution.completed" in types

    def test_execution_started_has_metadata(self):
        _reset()
        req = _make_request("test_meta", issued_by="actor_meta")
        execute(req)
        started = [e for e in get_event_stream().list_events() if e.type == "execution.started"]
        assert len(started) >= 1
        e = started[0]
        assert e.actor_id == "actor_meta"
        assert e.execution_id == req.execution_id
        assert e.payload["operation"] == "test_meta"

    def test_execution_completed_has_status(self):
        _reset()
        req = _make_request("test_status")
        execute(req)
        completed = [e for e in get_event_stream().list_events() if e.type == "execution.completed"]
        assert len(completed) >= 1
        assert "status" in completed[0].payload

    def test_execution_ordering(self):
        _reset()
        req = _make_request("test_order")
        execute(req)
        events = get_event_stream().list_events()
        exec_events = [e for e in events if e.type.startswith("execution.")]
        assert exec_events[0].type == "execution.started"
        assert exec_events[1].type == "execution.completed"


# ── F. Approval Events ────────────────────────────────────────────


class TestApprovalEvents:
    def test_approval_created_event(self):
        _reset()
        store = get_approval_store()
        store.create_approval(
            execution_id="exec_1",
            operation="shell_exec",
            capability_type="shell_command",
            requested_by="actor_req",
        )
        events = get_event_stream().list_events()
        created = [e for e in events if e.type == "approval.created"]
        assert len(created) == 1
        assert created[0].actor_id == "actor_req"
        assert created[0].execution_id == "exec_1"
        assert created[0].payload["operation"] == "shell_exec"

    def test_approval_approved_event(self):
        _reset()
        store = get_approval_store()
        req = store.create_approval(
            execution_id="exec_2",
            operation="shell_exec",
            capability_type="shell_command",
        )
        store.approve(req.id, approved_by="operator_1")
        events = get_event_stream().list_events()
        approved = [e for e in events if e.type == "approval.approved"]
        assert len(approved) == 1
        assert approved[0].actor_id == "operator_1"
        assert approved[0].approval_id == req.id

    def test_approval_denied_event(self):
        _reset()
        store = get_approval_store()
        req = store.create_approval(
            execution_id="exec_3",
            operation="shell_exec",
            capability_type="shell_command",
        )
        store.deny(req.id)
        events = get_event_stream().list_events()
        denied = [e for e in events if e.type == "approval.denied"]
        assert len(denied) == 1
        assert denied[0].approval_id == req.id

    def test_approval_consumed_event(self):
        _reset()
        store = get_approval_store()
        req = store.create_approval(
            execution_id="exec_4",
            operation="shell_exec",
            capability_type="shell_command",
        )
        store.approve(req.id)
        store.consume(req.id)
        events = get_event_stream().list_events()
        consumed = [e for e in events if e.type == "approval.consumed"]
        assert len(consumed) == 1
        assert consumed[0].approval_id == req.id

    def test_full_approval_lifecycle_events(self):
        _reset()
        store = get_approval_store()
        req = store.create_approval(
            execution_id="exec_lifecycle",
            operation="shell_exec",
            capability_type="shell_command",
            requested_by="agent_1",
        )
        store.approve(req.id, approved_by="operator_1")
        store.consume(req.id)
        events = get_event_stream().list_events()
        types = [e.type for e in events]
        assert types == ["approval.created", "approval.approved", "approval.consumed"]

    def test_approval_event_has_approval_id(self):
        _reset()
        store = get_approval_store()
        req = store.create_approval(
            execution_id="exec_5",
            operation="test_op",
            capability_type="shell_command",
        )
        events = get_event_stream().list_events()
        assert events[0].approval_id == req.id


# ── G. API GET /events ────────────────────────────────────────────


class TestEventsAPI:
    def test_events_endpoint_requires_auth(self):
        _reset()
        resp = client.get("/events")
        assert resp.status_code == 401

    def test_events_endpoint_requires_scope(self):
        _reset()
        _, _, headers = _create_identity("agent", ["execute"])
        resp = client.get("/events", headers=headers)
        assert resp.status_code == 403

    def test_events_endpoint_returns_events(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        publish("test.api", payload={"x": 1})
        resp = client.get("/events", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[-1]["type"] == "test.api"

    def test_events_endpoint_limit(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        for i in range(10):
            publish(f"test.{i}", payload={})
        resp = client.get("/events?limit=3", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    def test_events_endpoint_with_metrics_scope(self):
        _reset()
        _, _, headers = _create_identity("viewer", ["metrics:read"])
        publish("test.viewer", payload={})
        resp = client.get("/events", headers=headers)
        assert resp.status_code == 200

    def test_events_contain_full_metadata(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        publish(
            "test.meta",
            payload={"key": "val"},
            actor_id="a1",
            execution_id="e1",
            approval_id="ap1",
        )
        resp = client.get("/events", headers=headers)
        data = resp.json()
        event = data[-1]
        assert event["actor_id"] == "a1"
        assert event["execution_id"] == "e1"
        assert event["approval_id"] == "ap1"
        assert event["payload"] == {"key": "val"}


# ── H. SSE Endpoint ───────────────────────────────────────────────


class TestSSEEndpoint:
    """SSE endpoint tests.

    httpx TestClient buffers streaming responses, so we test auth/scope
    via the client and test streaming behavior via the subscriber mechanism
    directly — which is what the SSE generator uses internally.
    """

    def test_sse_requires_auth(self):
        _reset()
        resp = client.get("/events/stream")
        assert resp.status_code == 401

    def test_sse_requires_scope(self):
        _reset()
        _, _, headers = _create_identity("agent", ["execute"])
        resp = client.get("/events/stream", headers=headers)
        assert resp.status_code == 403

    def test_sse_subscriber_receives_events(self):
        """Verify the subscriber mechanism that SSE uses internally."""
        _reset()
        stream = get_event_stream()
        received = []

        def on_event(event):
            received.append(event)

        stream.subscribe(on_event)
        publish("test.sse", payload={"streamed": True})
        assert len(received) == 1
        assert received[0].type == "test.sse"
        assert received[0].payload["streamed"] is True
        stream.unsubscribe(on_event)

    def test_sse_subscriber_receives_execution_events(self):
        _reset()
        stream = get_event_stream()
        received = []

        def on_event(event):
            received.append(event)

        stream.subscribe(on_event)
        req = _make_request("sse_exec", issued_by="sse_actor")
        execute(req)
        stream.unsubscribe(on_event)
        types = [e.type for e in received]
        assert "execution.started" in types
        assert "execution.completed" in types

    def test_sse_subscriber_receives_approval_events(self):
        _reset()
        stream = get_event_stream()
        received = []

        def on_event(event):
            received.append(event)

        stream.subscribe(on_event)
        store = get_approval_store()
        store.create_approval(
            execution_id="exec_sse",
            operation="shell_exec",
            capability_type="shell_command",
        )
        stream.unsubscribe(on_event)
        assert len(received) == 1
        assert received[0].type == "approval.created"

    def test_sse_event_serializes_as_json(self):
        """Verify events serialize to the format SSE would send."""
        _reset()
        event = publish("test.json", payload={"key": "value"}, actor_id="a1")
        serialized = json.dumps(event.to_dict())
        parsed = json.loads(serialized)
        assert parsed["type"] == "test.json"
        assert parsed["actor_id"] == "a1"
        sse_line = f"data: {serialized}\n\n"
        assert sse_line.startswith("data: ")
        assert sse_line.endswith("\n\n")


# ── I. Global Singleton ───────────────────────────────────────────


class TestGlobalSingleton:
    def test_get_event_stream_returns_same_instance(self):
        from umh.events.stream import get_event_stream

        s1 = get_event_stream()
        s2 = get_event_stream()
        assert s1 is s2

    def test_reset_event_stream_creates_new(self):
        from umh.events.stream import get_event_stream, reset_event_stream

        s1 = get_event_stream()
        s2 = reset_event_stream()
        assert s1 is not s2


# ── J. Integration: Execution + Events via API ────────────────────


class TestIntegrationExecuteEvents:
    def test_execute_via_api_produces_events(self):
        _reset()
        _, _, headers = _create_identity("executor", ["admin"])
        client.post(
            "/execute",
            json={
                "operation": "test_via_api",
                "inputs": {"prompt": "hi", "system_prompt": "", "max_tokens": 100},
                "execution_class": "llm_call",
            },
            headers=headers,
        )
        resp = client.get("/events", headers=headers)
        data = resp.json()
        types = [e["type"] for e in data]
        assert "execution.started" in types
        assert "execution.completed" in types

    def test_approval_via_api_produces_events(self):
        _reset()
        _, _, admin_headers = _create_identity("admin", ["admin"])
        store = get_approval_store()
        req = store.create_approval(
            execution_id="exec_api_appr",
            operation="shell_exec",
            capability_type="shell_command",
        )
        client.post(f"/approvals/{req.id}/approve", headers=admin_headers)
        resp = client.get("/events", headers=admin_headers)
        data = resp.json()
        types = [e["type"] for e in data]
        assert "approval.created" in types
        assert "approval.approved" in types
