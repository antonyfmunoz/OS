"""Tests for Execution Telemetry — Phase 15B.

Validates:
  1. Event creation and serialization
  2. Sequence ordering and monotonicity
  3. Subscribe/get patterns
  4. Lifecycle emission from ExecutorRuntime
  5. Command-level events from WorkstationExecutor
  6. Failure and cancellation events
  7. Telemetry resilience (never blocks execution)
  8. Payload redaction
  9. Store eviction (bounded capacity)
  10. SSE formatting
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.organism.executors.execution_telemetry import (
    ExecutionTelemetryEmitter,
    ExecutionTelemetryEvent,
    InMemoryExecutionTelemetryStore,
    TelemetryEventType,
    get_telemetry_emitter,
    redact_telemetry_payload,
    reset_telemetry_emitter,
)


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_singleton():
    reset_telemetry_emitter()
    yield
    reset_telemetry_emitter()


@pytest.fixture
def store():
    return InMemoryExecutionTelemetryStore(max_events=100)


@pytest.fixture
def emitter(store):
    return ExecutionTelemetryEmitter(store=store)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. Event creation and serialization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEventCreation:
    def test_event_has_auto_id(self):
        event = ExecutionTelemetryEvent()
        assert event.event_id.startswith("extel-")
        assert len(event.event_id) == 18  # extel- + 12 hex

    def test_event_to_dict(self):
        event = ExecutionTelemetryEvent(
            execution_id="exec-1",
            event_type="execution_started",
            status="ok",
        )
        d = event.to_dict()
        assert d["execution_id"] == "exec-1"
        assert d["event_type"] == "execution_started"
        assert d["status"] == "ok"
        assert "event_id" in d
        assert "timestamp" in d

    def test_event_from_dict(self):
        original = ExecutionTelemetryEvent(
            execution_id="exec-2",
            event_type="command_started",
            payload={"cmd": "echo hi"},
        )
        d = original.to_dict()
        restored = ExecutionTelemetryEvent.from_dict(d)
        assert restored.execution_id == "exec-2"
        assert restored.event_type == "command_started"
        assert restored.payload == {"cmd": "echo hi"}

    def test_event_from_dict_ignores_unknown_keys(self):
        d = {"execution_id": "exec-3", "event_type": "test", "unknown_key": "ignore"}
        event = ExecutionTelemetryEvent.from_dict(d)
        assert event.execution_id == "exec-3"

    def test_all_14_event_types_defined(self):
        assert len(TelemetryEventType) == 14
        expected = {
            "execution_requested", "execution_validating", "execution_approved",
            "execution_preparing", "execution_started", "command_started",
            "stdout_chunk", "stderr_chunk", "command_completed",
            "proof_generated", "execution_cleaning_up", "execution_completed",
            "execution_failed", "execution_cancelled",
        }
        actual = {e.value for e in TelemetryEventType}
        assert actual == expected


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. Sequence ordering and monotonicity
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSequenceOrdering:
    def test_sequence_numbers_monotonic(self, store):
        events = []
        for i in range(10):
            e = ExecutionTelemetryEvent(
                execution_id="exec-1", event_type=f"event_{i}"
            )
            store.append(e)
            events.append(e)
        seqs = [e.sequence_number for e in events]
        assert seqs == sorted(seqs)
        assert len(set(seqs)) == 10  # all unique

    def test_sequence_survives_eviction(self):
        store = InMemoryExecutionTelemetryStore(max_events=5)
        for i in range(10):
            e = ExecutionTelemetryEvent(
                execution_id="exec-1", event_type=f"event_{i}"
            )
            store.append(e)
        assert store.count == 5
        assert store.sequence == 10

    def test_cross_execution_sequence(self, store):
        e1 = ExecutionTelemetryEvent(execution_id="exec-a", event_type="t1")
        e2 = ExecutionTelemetryEvent(execution_id="exec-b", event_type="t2")
        store.append(e1)
        store.append(e2)
        assert e2.sequence_number > e1.sequence_number


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. Subscribe/get patterns
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSubscribeGet:
    def test_subscribe_receives_events(self, emitter):
        received = []
        emitter.subscribe("exec-1", lambda e: received.append(e))
        emitter.emit("execution_started", execution_id="exec-1")
        assert len(received) == 1
        assert received[0].event_type == "execution_started"

    def test_subscribe_isolated_by_execution_id(self, emitter):
        received_a = []
        received_b = []
        emitter.subscribe("exec-a", lambda e: received_a.append(e))
        emitter.subscribe("exec-b", lambda e: received_b.append(e))
        emitter.emit("execution_started", execution_id="exec-a")
        assert len(received_a) == 1
        assert len(received_b) == 0

    def test_subscribe_all_receives_everything(self, emitter):
        received = []
        emitter.subscribe_all(lambda e: received.append(e))
        emitter.emit("t1", execution_id="exec-a")
        emitter.emit("t2", execution_id="exec-b")
        assert len(received) == 2

    def test_unsubscribe(self, emitter):
        received = []
        cb = lambda e: received.append(e)
        emitter.subscribe("exec-1", cb)
        emitter.emit("t1", execution_id="exec-1")
        emitter.unsubscribe("exec-1", cb)
        emitter.emit("t2", execution_id="exec-1")
        assert len(received) == 1

    def test_unsubscribe_all(self, emitter):
        received = []
        cb = lambda e: received.append(e)
        emitter.subscribe_all(cb)
        emitter.emit("t1", execution_id="exec-1")
        emitter.unsubscribe_all(cb)
        emitter.emit("t2", execution_id="exec-1")
        assert len(received) == 1

    def test_get_events_by_execution_id(self, emitter):
        emitter.emit("t1", execution_id="exec-1")
        emitter.emit("t2", execution_id="exec-2")
        emitter.emit("t3", execution_id="exec-1")
        events = emitter.get_events("exec-1")
        assert len(events) == 2
        assert all(e.execution_id == "exec-1" for e in events)

    def test_get_events_after_sequence(self, emitter):
        emitter.emit("t1", execution_id="exec-1")
        seq1 = emitter.store.sequence
        emitter.emit("t2", execution_id="exec-1")
        emitter.emit("t3", execution_id="exec-1")
        after = emitter.get_events_after("exec-1", seq1)
        assert len(after) == 2

    def test_get_latest(self, emitter):
        for i in range(20):
            emitter.emit(f"t{i}", execution_id=f"exec-{i % 3}")
        latest = emitter.get_latest(5)
        assert len(latest) == 5


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. Lifecycle emission from ExecutorRuntime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLifecycleEmission:
    def test_runtime_emits_lifecycle_events(self, tmp_path):
        from substrate.organism.executor_runtime import (
            ExecutorContract,
            ExecutorRequest,
            ExecutorRequestStatus,
            ExecutorResult,
            ExecutorRuntime,
        )

        class TestExecutor(ExecutorContract):
            @property
            def executor_type(self):
                return "test"
            def validate(self, request):
                return True, "ok"
            def prepare(self, request):
                return True, "ok"
            def execute(self, request):
                return ExecutorResult(
                    request_id=request.request_id,
                    executor_type="test",
                    success=True,
                    outcome="ok",
                )
            def monitor(self, request):
                return {"status": "done"}
            def cancel(self, request):
                return True
            def cleanup(self, request):
                return True

        emitter = ExecutionTelemetryEmitter()
        os.environ["UMH_ROOT"] = str(tmp_path)
        try:
            runtime = ExecutorRuntime(telemetry_emitter=emitter)
            runtime.register_executor("test", TestExecutor())

            req = ExecutorRequest(
                request_id="req-lifecycle",
                execution_plan_id="plan-1",
                executor_type="test",
                description="lifecycle test",
            )
            req.status = ExecutorRequestStatus.PENDING.value
            req.approval_state = "approved"
            runtime._request_store.save(req)

            result = runtime.run_lifecycle("req-lifecycle")
        finally:
            if os.environ.get("UMH_ROOT") == str(tmp_path):
                del os.environ["UMH_ROOT"]

        events = emitter.get_events("req-lifecycle")
        event_types = [e.event_type for e in events]

        assert "execution_requested" in event_types
        assert "execution_approved" in event_types
        assert "execution_started" in event_types
        assert "execution_completed" in event_types or "execution_failed" in event_types

    def test_runtime_telemetry_property(self, tmp_path):
        from substrate.organism.executor_runtime import ExecutorRuntime

        os.environ["UMH_ROOT"] = str(tmp_path)
        try:
            emitter = ExecutionTelemetryEmitter()
            runtime = ExecutorRuntime()
            assert runtime.telemetry is None
            runtime.telemetry = emitter
            assert runtime.telemetry is emitter
        finally:
            if os.environ.get("UMH_ROOT") == str(tmp_path):
                del os.environ["UMH_ROOT"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. Command-level events from WorkstationExecutor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCommandEvents:
    def test_workstation_emits_command_events(self):
        from substrate.organism.executor_runtime import (
            ExecutorRequest,
            ExecutorRequestStatus,
        )
        from substrate.organism.executors.workstation_executor import (
            WorkstationExecutor,
        )

        emitter = ExecutionTelemetryEmitter()
        executor = WorkstationExecutor(telemetry_emitter=emitter)

        req = ExecutorRequest(
            request_id="req-cmd",
            execution_plan_id="plan-1",
            executor_type="workstation",
            description="command test",
            metadata={
                "operation": "run_command",
                "params": {"command": "echo hello"},
            },
        )
        req.status = ExecutorRequestStatus.EXECUTING

        result = executor.execute(req)
        assert result is not None

        events = emitter.get_events("req-cmd")
        event_types = [e.event_type for e in events]

        assert "command_started" in event_types
        assert "command_completed" in event_types

    def test_stdout_chunk_emitted(self):
        from substrate.organism.executor_runtime import (
            ExecutorRequest,
            ExecutorRequestStatus,
        )
        from substrate.organism.executors.workstation_executor import (
            WorkstationExecutor,
        )

        emitter = ExecutionTelemetryEmitter()
        executor = WorkstationExecutor(telemetry_emitter=emitter)

        req = ExecutorRequest(
            request_id="req-stdout",
            execution_plan_id="plan-1",
            executor_type="workstation",
            description="stdout test",
            metadata={
                "operation": "run_command",
                "params": {"command": "echo output_text"},
            },
        )
        req.status = ExecutorRequestStatus.EXECUTING

        executor.execute(req)

        events = emitter.get_events("req-stdout")
        stdout_events = [e for e in events if e.event_type == "stdout_chunk"]
        assert len(stdout_events) >= 1
        payload = stdout_events[0].payload
        stdout_data = payload.get("data", "") or payload.get("stdout", "")
        assert "output_text" in str(stdout_data)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. Failure and cancellation events
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFailureAndCancel:
    def test_failed_execution_emits_failure_event(self, tmp_path):
        from substrate.organism.executor_runtime import (
            ExecutorContract,
            ExecutorRequest,
            ExecutorRequestStatus,
            ExecutorRuntime,
        )

        class FailingExecutor(ExecutorContract):
            @property
            def executor_type(self):
                return "fail"
            def validate(self, request):
                return True, "ok"
            def prepare(self, request):
                return True, "ok"
            def execute(self, request):
                raise RuntimeError("test explosion")
            def monitor(self, request):
                return {}
            def cancel(self, request):
                return True
            def cleanup(self, request):
                return True

        emitter = ExecutionTelemetryEmitter()
        os.environ["UMH_ROOT"] = str(tmp_path)
        try:
            runtime = ExecutorRuntime(telemetry_emitter=emitter)
            runtime.register_executor("fail", FailingExecutor())

            req = ExecutorRequest(
                request_id="req-fail",
                execution_plan_id="plan-1",
                executor_type="fail",
                description="fail test",
            )
            req.status = ExecutorRequestStatus.PENDING.value
            runtime._request_store.save(req)

            runtime.run_lifecycle("req-fail")
        finally:
            if os.environ.get("UMH_ROOT") == str(tmp_path):
                del os.environ["UMH_ROOT"]

        events = emitter.get_events("req-fail")
        event_types = [e.event_type for e in events]
        assert "execution_failed" in event_types

    def test_cancel_emits_cancel_event(self, tmp_path):
        from substrate.organism.executor_runtime import (
            ExecutorContract,
            ExecutorRequest,
            ExecutorRequestStatus,
            ExecutorRuntime,
        )

        emitter = ExecutionTelemetryEmitter()
        os.environ["UMH_ROOT"] = str(tmp_path)
        try:
            runtime = ExecutorRuntime(telemetry_emitter=emitter)

            req = ExecutorRequest(
                request_id="req-cancel",
                execution_plan_id="plan-1",
                executor_type="workstation",
                description="cancel test",
            )
            req.status = ExecutorRequestStatus.EXECUTING.value
            runtime._request_store.save(req)

            runtime.cancel_request("req-cancel")
        finally:
            if os.environ.get("UMH_ROOT") == str(tmp_path):
                del os.environ["UMH_ROOT"]

        events = emitter.get_events("req-cancel")
        event_types = [e.event_type for e in events]
        assert "execution_cancelled" in event_types


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. Telemetry resilience (never blocks execution)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestResilience:
    def test_emit_never_raises(self, emitter):
        broken_store = InMemoryExecutionTelemetryStore()
        broken_store.append = None  # type: ignore — break it

        emitter._store = broken_store
        result = emitter.emit("test_event", execution_id="exec-1")
        assert result is None  # didn't raise

    def test_subscriber_exception_doesnt_block_emit(self, emitter):
        def bad_subscriber(event):
            raise ValueError("subscriber error")

        emitter.subscribe("exec-1", bad_subscriber)
        event = emitter.emit("test_event", execution_id="exec-1")
        assert event is not None  # emitted despite subscriber error

    def test_thread_safety(self, store):
        errors = []

        def writer(n):
            try:
                for i in range(50):
                    e = ExecutionTelemetryEvent(
                        execution_id=f"exec-{n}", event_type=f"event_{i}"
                    )
                    store.append(e)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert store.sequence == 250


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 8. Payload redaction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRedaction:
    def test_redact_api_key(self):
        result = redact_telemetry_payload({"api_key": "sk-12345"})
        assert result["api_key"] == "[REDACTED]"

    def test_redact_token(self):
        result = redact_telemetry_payload({"auth_token": "abc123"})
        assert result["auth_token"] == "[REDACTED]"

    def test_redact_password(self):
        result = redact_telemetry_payload({"password": "hunter2"})
        assert result["password"] == "[REDACTED]"

    def test_redact_authorization(self):
        result = redact_telemetry_payload({"authorization": "Bearer xyz"})
        assert result["authorization"] == "[REDACTED]"

    def test_redact_nested(self):
        result = redact_telemetry_payload(
            {"config": {"api_key": "sk-123", "host": "localhost"}}
        )
        assert result["config"]["api_key"] == "[REDACTED]"
        assert result["config"]["host"] == "localhost"

    def test_redact_value_containing_secret(self):
        result = redact_telemetry_payload(
            {"output": "my_api_key_is_leaked"}
        )
        assert result["output"] == "[REDACTED]"

    def test_safe_payload_unchanged(self):
        payload = {"command": "echo hi", "exit_code": 0, "duration_ms": 123}
        result = redact_telemetry_payload(payload)
        assert result == payload

    def test_empty_payload(self):
        assert redact_telemetry_payload({}) == {}
        assert redact_telemetry_payload(None) is None  # type: ignore

    def test_store_redacts_on_append(self, store):
        event = ExecutionTelemetryEvent(
            execution_id="exec-1",
            event_type="test",
            payload={"api_key": "sk-secret-123", "safe": "value"},
        )
        store.append(event)
        assert event.payload["api_key"] == "[REDACTED]"
        assert event.payload["safe"] == "value"

    def test_redact_github_pat(self):
        result = redact_telemetry_payload(
            {"output": "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"}
        )
        assert result["output"] == "[REDACTED]"

    def test_redact_aws_key(self):
        result = redact_telemetry_payload(
            {"output": "AKIAIOSFODNN7EXAMPLE"}
        )
        assert result["output"] == "[REDACTED]"

    def test_redact_jwt(self):
        result = redact_telemetry_payload(
            {"output": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"}
        )
        assert result["output"] == "[REDACTED]"

    def test_redact_slack_token(self):
        result = redact_telemetry_payload(
            {"output": "xoxb-FAKE00000000-FAKE0000000TEST-FakeSlackTestVal"}
        )
        assert result["output"] == "[REDACTED]"

    def test_redact_url_with_userinfo(self):
        result = redact_telemetry_payload(
            {"output": "postgres://admin:s3cretP4ss@db.example.com:5432/mydb"}
        )
        assert result["output"] == "[REDACTED]"

    def test_redact_long_hex(self):
        result = redact_telemetry_payload(
            {"output": "a" * 40}  # 40-char hex
        )
        assert result["output"] == "[REDACTED]"

    def test_redact_list_values(self):
        result = redact_telemetry_payload(
            {"items": ["safe", "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij", "also safe"]}
        )
        assert result["items"][0] == "safe"
        assert result["items"][1] == "[REDACTED]"
        assert result["items"][2] == "also safe"

    def test_redact_openai_key(self):
        result = redact_telemetry_payload(
            {"output": "sk-proj-abcdefghijklmnopqrstuvwx"}
        )
        assert result["output"] == "[REDACTED]"

    def test_redact_anthropic_key(self):
        result = redact_telemetry_payload(
            {"output": "sk-ant-abcdefghijklmnopqrstuvwx"}
        )
        assert result["output"] == "[REDACTED]"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 9. Store eviction (bounded capacity)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEviction:
    def test_store_caps_at_max(self):
        store = InMemoryExecutionTelemetryStore(max_events=5)
        for i in range(10):
            store.append(
                ExecutionTelemetryEvent(execution_id="exec-1", event_type=f"t{i}")
            )
        assert store.count == 5
        events = store.get_latest(10)
        assert len(events) == 5
        assert events[0].event_type == "t5"  # oldest surviving

    def test_eviction_cleans_execution_index(self):
        store = InMemoryExecutionTelemetryStore(max_events=3)
        for i in range(5):
            store.append(
                ExecutionTelemetryEvent(execution_id="exec-1", event_type=f"t{i}")
            )
        exec_events = store.get_events("exec-1")
        assert len(exec_events) <= 3

    def test_clear_resets_everything(self, store):
        for i in range(5):
            store.append(
                ExecutionTelemetryEvent(execution_id="exec-1", event_type=f"t{i}")
            )
        assert store.count == 5
        store.clear()
        assert store.count == 0
        assert store.sequence == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 10. SSE formatting
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSSEFormat:
    def test_to_sse_format(self, store):
        event = ExecutionTelemetryEvent(
            execution_id="exec-1",
            event_type="execution_started",
            status="ok",
        )
        store.append(event)  # assigns sequence_number

        sse = event.to_sse()
        assert sse.startswith(f"id: {event.sequence_number}\n")
        assert "event: execution_started\n" in sse
        assert "data: {" in sse
        assert sse.endswith("\n\n")

    def test_sse_data_is_valid_json(self, store):
        event = ExecutionTelemetryEvent(
            execution_id="exec-1",
            event_type="command_completed",
            payload={"exit_code": 0, "duration_ms": 42},
        )
        store.append(event)

        sse = event.to_sse()
        data_line = [line for line in sse.strip().split("\n") if line.startswith("data:")][0]
        json_str = data_line[len("data: "):]
        parsed = json.loads(json_str)
        assert parsed["event_type"] == "command_completed"
        assert parsed["payload"]["exit_code"] == 0

    def test_sse_multi_event_parseable(self, store):
        events = []
        for i in range(3):
            e = ExecutionTelemetryEvent(
                execution_id="exec-1",
                event_type=f"event_{i}",
            )
            store.append(e)
            events.append(e)

        full_stream = "".join(e.to_sse() for e in events)
        blocks = [b for b in full_stream.split("\n\n") if b.strip()]
        assert len(blocks) == 3


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Singleton
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSingleton:
    def test_get_telemetry_emitter_returns_same_instance(self):
        a = get_telemetry_emitter()
        b = get_telemetry_emitter()
        assert a is b

    def test_reset_creates_new_instance(self):
        a = get_telemetry_emitter()
        reset_telemetry_emitter()
        b = get_telemetry_emitter()
        assert a is not b
