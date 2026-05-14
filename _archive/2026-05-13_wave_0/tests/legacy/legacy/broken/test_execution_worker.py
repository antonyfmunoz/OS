"""Tests for ExecutionWorker — event-native adapter bridge."""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from runtime.substrate.event_scheduler import (
    ExecutionResult as SchedulerExecutionResult,
    SchedulerEvent,
)
from runtime.substrate.execution_contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTarget,
)
from runtime.substrate.execution_worker import ExecutionWorker
from runtime.substrate.runtime_state_store import RuntimeStateStore


# ---------------------------------------------------------------------------
# Mock adapter
# ---------------------------------------------------------------------------


class MockAdapter:
    """Test adapter that conforms to the ExecutionAdapter protocol."""

    def __init__(
        self,
        node_id: str = "test-node",
        capabilities: frozenset[str] = frozenset({"test_primitive"}),
    ) -> None:
        self._adapter_id = "mock_adapter"
        self._node_id = node_id
        self._capabilities = capabilities
        self.execute_fn = None  # set per test

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def capabilities(self) -> frozenset[str]:
        return self._capabilities

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if self.execute_fn:
            return self.execute_fn(request)
        return ExecutionResult(
            execution_id=request.execution_id,
            correlation_id=request.correlation_id,
            causal_event_id=request.causal_event_id,
            primitive_name=request.primitive_name,
            status=ExecutionStatus.SUCCEEDED,
            outputs={"key": "value"},
            node_id=self._node_id,
            idempotency_key=request.idempotency_key,
        )

    def health(self) -> dict:
        return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(
    primitive_name: str = "test_primitive",
    node_id: str = "test-node",
    timeout_s: int = 30,
    inputs: dict | None = None,
) -> ExecutionRequest:
    """Build a minimal ExecutionRequest for testing."""
    return ExecutionRequest(
        execution_id="exec_test_001",
        correlation_id="corr_test_001",
        causal_event_id="evt_test_001",
        session_name="test-session",
        run_id="run_test_001",
        primitive_name=primitive_name,
        inputs=inputs or {"action": "test"},
        execution_class=ExecutionClass.PURE,
        constraints=ExecutionConstraints(timeout_s=timeout_s),
        target=ExecutionTarget(node_id=node_id, transport="local"),
        issued_at="2026-04-16T00:00:00Z",
        issued_by="test_harness",
        idempotency_key="idem_test_001",
    )


def _make_event(request: ExecutionRequest | None = None) -> SchedulerEvent:
    """Build a SchedulerEvent wrapping a request payload."""
    if request is None:
        request = _make_request()
    return SchedulerEvent(
        event_type="execution_requested",
        session_name=request.session_name,
        source="test_harness",
        run_id=request.run_id,
        payload={"request": request.to_dict()},
        metadata={"execution_id": request.execution_id},
    )


def _setup() -> tuple[RuntimeStateStore, ExecutionWorker, MockAdapter]:
    """Create a store, worker, and registered mock adapter."""
    store = RuntimeStateStore()
    worker = ExecutionWorker(store)
    adapter = MockAdapter()
    worker.register_adapter(adapter)
    return store, worker, adapter


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_worker_emits_completed_on_success() -> None:
    """Adapter returns SUCCEEDED -> execution_completed event emitted."""
    store, worker, _adapter = _setup()
    event = _make_event()

    result = worker.handle_execution_requested(store, event)

    assert isinstance(result, SchedulerExecutionResult)
    assert len(result.emitted_events) == 1

    emitted = result.emitted_events[0]
    assert emitted.event_type == "execution_completed"
    assert emitted.source == "execution_worker"

    # Result payload is correct
    result_dict = emitted.payload["result"]
    assert result_dict["status"] == "succeeded"
    assert result_dict["execution_id"] == "exec_test_001"
    assert result_dict["outputs"] == {"key": "value"}
    assert result_dict["node_id"] == "test-node"


def test_worker_emits_failed_on_error() -> None:
    """Adapter raises Exception -> execution_failed event emitted."""
    store, worker, adapter = _setup()

    def _raise(_req: ExecutionRequest) -> ExecutionResult:
        raise RuntimeError("adapter exploded")

    adapter.execute_fn = _raise
    event = _make_event()

    result = worker.handle_execution_requested(store, event)

    assert len(result.emitted_events) == 1
    emitted = result.emitted_events[0]
    assert emitted.event_type == "execution_failed"

    assert "RuntimeError" in emitted.payload["failure_reason"]
    assert "adapter exploded" in emitted.payload["failure_reason"]


def test_worker_emits_timed_out() -> None:
    """Adapter sleeps beyond timeout -> execution_timed_out event."""
    store, worker, adapter = _setup()

    def _slow(_req: ExecutionRequest) -> ExecutionResult:
        time.sleep(3)
        return ExecutionResult(
            execution_id=_req.execution_id,
            correlation_id=_req.correlation_id,
            causal_event_id=_req.causal_event_id,
            primitive_name=_req.primitive_name,
            status=ExecutionStatus.SUCCEEDED,
            outputs={},
            node_id="test-node",
        )

    adapter.execute_fn = _slow

    # Use 1-second timeout
    request = _make_request(timeout_s=1)
    event = _make_event(request)

    result = worker.handle_execution_requested(store, event)

    assert len(result.emitted_events) == 1
    emitted = result.emitted_events[0]
    assert emitted.event_type == "execution_timed_out"
    assert emitted.payload["result"]["status"] == "timed_out"


def test_worker_emits_rejected_no_adapter() -> None:
    """Request targets unknown node -> execution_rejected."""
    store = RuntimeStateStore()
    worker = ExecutionWorker(store)
    # No adapter registered

    request = _make_request(node_id="nonexistent-node")
    event = _make_event(request)

    result = worker.handle_execution_requested(store, event)

    assert len(result.emitted_events) == 1
    emitted = result.emitted_events[0]
    assert emitted.event_type == "execution_rejected"
    assert "no_adapter_for_node" in emitted.payload["failure_reason"]


def test_worker_emits_rejected_no_capability() -> None:
    """Adapter lacks the requested primitive -> execution_rejected."""
    store, worker, _adapter = _setup()

    # Request a primitive the adapter does not have
    request = _make_request(primitive_name="unknown_primitive")
    event = _make_event(request)

    result = worker.handle_execution_requested(store, event)

    assert len(result.emitted_events) == 1
    emitted = result.emitted_events[0]
    assert emitted.event_type == "execution_rejected"
    assert "capability_missing" in emitted.payload["failure_reason"]
    assert "unknown_primitive" in emitted.payload["failure_reason"]


def test_worker_mutations_always_empty() -> None:
    """Verify handler ALWAYS returns mutations=[]."""
    store, worker, _adapter = _setup()
    event = _make_event()

    result = worker.handle_execution_requested(store, event)

    assert result.mutations == []


def test_worker_mutations_empty_on_rejection() -> None:
    """Even on rejection, mutations must be empty."""
    store = RuntimeStateStore()
    worker = ExecutionWorker(store)

    request = _make_request(node_id="missing-node")
    event = _make_event(request)

    result = worker.handle_execution_requested(store, event)

    assert result.mutations == []


def test_worker_mutations_empty_on_error() -> None:
    """Even on adapter error, mutations must be empty."""
    store, worker, adapter = _setup()
    adapter.execute_fn = lambda _: (_ for _ in ()).throw(ValueError("boom"))
    event = _make_event()

    result = worker.handle_execution_requested(store, event)

    assert result.mutations == []


def test_worker_detects_state_write_violation() -> None:
    """Adapter mutates store during execute -> FAILED with state_write_violation."""
    store = RuntimeStateStore()
    # Do NOT enable write enforcement so the adapter CAN write
    # (the worker detects the violation via hash comparison)
    worker = ExecutionWorker(store)

    adapter = MockAdapter()

    def _sneaky_write(req: ExecutionRequest) -> ExecutionResult:
        # Directly mutate the store — this should be detected
        store.set("illegal_key", "illegal_value")
        return ExecutionResult(
            execution_id=req.execution_id,
            correlation_id=req.correlation_id,
            causal_event_id=req.causal_event_id,
            primitive_name=req.primitive_name,
            status=ExecutionStatus.SUCCEEDED,
            outputs={"looks": "fine"},
            node_id=adapter.node_id,
            idempotency_key=req.idempotency_key,
        )

    adapter.execute_fn = _sneaky_write
    worker.register_adapter(adapter)

    event = _make_event()
    result = worker.handle_execution_requested(store, event)

    assert len(result.emitted_events) == 1
    emitted = result.emitted_events[0]
    assert emitted.event_type == "execution_failed"
    assert "state_write_violation" in emitted.payload["failure_reason"]
    assert result.mutations == []


def test_worker_deserializes_request_from_payload() -> None:
    """Test that request.to_dict() in payload is correctly deserialized."""
    store, worker, _adapter = _setup()

    request = _make_request(
        primitive_name="test_primitive",
        inputs={"complex": {"nested": True}},
    )
    event = _make_event(request)

    result = worker.handle_execution_requested(store, event)

    # If deserialization works, execution succeeds
    assert len(result.emitted_events) == 1
    emitted = result.emitted_events[0]
    assert emitted.event_type == "execution_completed"

    # Verify the execution_id matches — proves deserialization worked
    assert emitted.metadata["execution_id"] == "exec_test_001"


def test_worker_handles_malformed_payload() -> None:
    """Malformed payload -> execution_rejected (deserialization failure)."""
    store, worker, _adapter = _setup()

    event = SchedulerEvent(
        event_type="execution_requested",
        session_name="test-session",
        source="test_harness",
        payload={"request": {"this": "is_incomplete"}},
    )

    result = worker.handle_execution_requested(store, event)

    assert len(result.emitted_events) == 1
    emitted = result.emitted_events[0]
    assert emitted.event_type == "execution_rejected"
    assert "deserialization_failed" in emitted.payload["failure_reason"]
    assert result.mutations == []


def test_worker_register_and_get_adapter() -> None:
    """Register and retrieve adapters by node_id."""
    store = RuntimeStateStore()
    worker = ExecutionWorker(store)

    assert worker.get_adapter("test-node") is None

    adapter = MockAdapter(node_id="test-node")
    worker.register_adapter(adapter)

    assert worker.get_adapter("test-node") is adapter
    assert worker.get_adapter("other-node") is None


def test_worker_handles_retried_event() -> None:
    """execution_retried events have the same payload shape and are handled."""
    store, worker, _adapter = _setup()

    request = _make_request()
    event = SchedulerEvent(
        event_type="execution_retried",
        session_name=request.session_name,
        source="result_handler",
        run_id=request.run_id,
        payload={
            "request": request.to_dict(),
            "original_execution_id": "exec_original",
            "retry_count": 1,
        },
        metadata={"execution_id": request.execution_id},
    )

    result = worker.handle_execution_requested(store, event)

    assert len(result.emitted_events) == 1
    emitted = result.emitted_events[0]
    assert emitted.event_type == "execution_completed"
    assert result.mutations == []
