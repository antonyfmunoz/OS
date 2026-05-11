"""Integration tests — Full lifecycle end-to-end for the execution fabric.

Wires up real EventScheduler, real RuntimeStateStore, and real handler
registrations. Only the adapter is mocked. Validates the architecture:

    lifecycle_event -> authority -> EXECUTION_REQUESTED -> worker
    -> EXECUTION_COMPLETED -> result_handler -> state + lifecycle events
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from runtime.substrate.runtime_state_store import RuntimeStateStore
from runtime.substrate.event_scheduler import EventScheduler, SchedulerEvent
from runtime.substrate.execution_contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTarget,
    _compute_idempotency_key,
)
from runtime.substrate.execution_authority import ExecutionAuthority
from runtime.substrate.execution_router import ExecutionRouter
from runtime.substrate.execution_worker import ExecutionWorker
from runtime.substrate.execution_result_handler import ExecutionResultHandler
from runtime.substrate.nodes import Node, NodeRegistry, NodeRole, NodeStatus, NodeType


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------


def make_test_harness(
    emission_map=None,
    adapter_execute_fn=None,
):
    """Wire up a complete execution fabric for testing."""
    # Store
    store = RuntimeStateStore()

    # Registry with test node
    registry = NodeRegistry(persist=False)
    registry.upsert(
        Node(
            node_id="vps-primary",
            node_type=NodeType.VPS,
            role=NodeRole.ORCHESTRATOR,
            capabilities=[
                "reasoning",
                "extract_response",
                "clean_output",
                "test_primitive",
            ],
            status=NodeStatus.ONLINE,
        )
    )

    # Router
    router = ExecutionRouter(registry=registry)

    # Authority
    authority = ExecutionAuthority(router)

    # Worker with mock adapter
    worker = ExecutionWorker(store)

    class TestAdapter:
        adapter_id = "test_adapter"

        @property
        def node_id(self):
            return "vps-primary"

        @property
        def capabilities(self):
            return frozenset({"extract_response", "clean_output", "test_primitive"})

        def execute(self, request):
            if adapter_execute_fn:
                return adapter_execute_fn(request)
            # Default: succeed with echo outputs
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                primitive_name=request.primitive_name,
                status=ExecutionStatus.SUCCEEDED,
                outputs={"result_key": f"executed_{request.primitive_name}"},
                node_id="vps-primary",
                idempotency_key=request.idempotency_key,
            )

        def health(self):
            return {"status": "healthy"}

    worker.register_adapter(TestAdapter())

    # Result handler
    result_handler = ExecutionResultHandler(
        primitive_emission_map=emission_map or {},
    )

    # Scheduler
    scheduler = EventScheduler(store)

    # Wire subscriptions
    scheduler.subscribe(
        "stability_reached",
        authority.make_handler(
            "extract_response",
            ExecutionClass.PURE,
            requires=["cleaned_output", "gate_verdict"],
            constraints=ExecutionConstraints(timeout_s=10, max_retries=2),
        ),
        name="authority:extract_response",
    )

    scheduler.subscribe(
        "execution_requested",
        worker.handle_execution_requested,
        name="worker",
    )
    scheduler.subscribe(
        "execution_retried",
        worker.handle_execution_requested,
        name="worker:retry",
    )

    for evt_type in [
        "execution_completed",
        "execution_failed",
        "execution_timed_out",
        "execution_rejected",
    ]:
        scheduler.subscribe(
            evt_type,
            result_handler.handle_result,
            name=f"result_handler:{evt_type}",
        )

    return store, scheduler, registry, authority, worker, result_handler


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_full_lifecycle_local():
    """End-to-end: stability_reached -> authority -> worker -> result_handler -> state."""
    store, scheduler, *_ = make_test_harness(
        emission_map={"extract_response": ["response_extracted"]},
    )

    # Pre-set required state
    store.set("cleaned_output", "some text")
    store.set("gate_verdict", "CONFIRMED")

    # Subscribe a no-op to response_extracted so we can detect it was emitted
    response_extracted_seen = []
    scheduler.subscribe(
        "response_extracted",
        lambda s, e: _noop_handler(response_extracted_seen, e),
        name="test:response_extracted",
    )

    # Emit the lifecycle trigger
    scheduler.emit(
        SchedulerEvent(
            event_type="stability_reached",
            session_name="test_session",
            source="test",
        )
    )

    result = scheduler.run()

    # Verify outputs written to state
    assert store.get("result_key") == "executed_extract_response"

    # Verify execution was tracked as completed
    completed = store.get("completed_executions", [])
    assert len(completed) == 1

    # Verify event chain processed: stability_reached, execution_requested,
    # execution_completed, response_extracted
    event_types_processed = [
        rr.event.event_type for rr in result.route_results if not rr.skipped_dedup
    ]
    assert "stability_reached" in event_types_processed
    assert "execution_requested" in event_types_processed
    assert "execution_completed" in event_types_processed
    assert "response_extracted" in event_types_processed

    # Verify the no-op handler for response_extracted was called
    assert len(response_extracted_seen) == 1


def test_full_lifecycle_with_retry():
    """Adapter fails first call, succeeds on second -> retry path exercises."""
    call_count = [0]

    def fail_then_succeed(request):
        call_count[0] += 1
        if call_count[0] == 1:
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                primitive_name=request.primitive_name,
                status=ExecutionStatus.FAILED,
                outputs={},
                error="transient_failure",
                node_id="vps-primary",
                idempotency_key=request.idempotency_key,
                retry_count=request.retry_count,
            )
        return ExecutionResult(
            execution_id=request.execution_id,
            correlation_id=request.correlation_id,
            causal_event_id=request.causal_event_id,
            primitive_name=request.primitive_name,
            status=ExecutionStatus.SUCCEEDED,
            outputs={"result_key": "retry_success"},
            node_id="vps-primary",
            idempotency_key=request.idempotency_key,
            retry_count=request.retry_count,
        )

    store, scheduler, *_ = make_test_harness(
        adapter_execute_fn=fail_then_succeed,
    )

    # Pre-set required state
    store.set("cleaned_output", "retry test text")
    store.set("gate_verdict", "CONFIRMED")

    # Emit the lifecycle trigger
    scheduler.emit(
        SchedulerEvent(
            event_type="stability_reached",
            session_name="test_session",
            source="test",
        )
    )

    result = scheduler.run()

    # Verify event chain: stability_reached -> execution_requested ->
    # execution_failed -> execution_retried -> execution_completed
    event_types_processed = [
        rr.event.event_type for rr in result.route_results if not rr.skipped_dedup
    ]
    assert "stability_reached" in event_types_processed
    assert "execution_requested" in event_types_processed
    assert "execution_failed" in event_types_processed
    assert "execution_retried" in event_types_processed
    assert "execution_completed" in event_types_processed

    # Verify adapter was called twice
    assert call_count[0] == 2

    # Verify final outputs written
    assert store.get("result_key") == "retry_success"

    # Verify execution tracked as completed
    completed = store.get("completed_executions", [])
    assert len(completed) >= 1


def test_full_lifecycle_side_effect_no_retry():
    """SIDE_EFFECT execution class with max_retries=0 -> no retry on failure."""
    store, scheduler, registry, authority, worker, result_handler = make_test_harness(
        adapter_execute_fn=lambda req: ExecutionResult(
            execution_id=req.execution_id,
            correlation_id=req.correlation_id,
            causal_event_id=req.causal_event_id,
            primitive_name=req.primitive_name,
            status=ExecutionStatus.FAILED,
            outputs={},
            error="permanent_error",
            node_id="vps-primary",
            idempotency_key=req.idempotency_key,
            retry_count=req.retry_count,
        ),
    )

    # Subscribe a side_effect handler for a different trigger event
    scheduler.subscribe(
        "side_effect_trigger",
        authority.make_handler(
            "test_primitive",
            ExecutionClass.SIDE_EFFECT,
            requires=["cleaned_output"],
            constraints=ExecutionConstraints(timeout_s=10, max_retries=0),
        ),
        name="authority:side_effect_test",
    )

    # Pre-set required state
    store.set("cleaned_output", "side effect input")

    # Emit the side effect trigger
    scheduler.emit(
        SchedulerEvent(
            event_type="side_effect_trigger",
            session_name="test_session",
            source="test",
        )
    )

    result = scheduler.run()

    # Verify event chain
    event_types_processed = [
        rr.event.event_type for rr in result.route_results if not rr.skipped_dedup
    ]
    assert "side_effect_trigger" in event_types_processed
    assert "execution_requested" in event_types_processed
    assert "execution_failed" in event_types_processed

    # No retry event should have been emitted
    assert "execution_retried" not in event_types_processed

    # In-flight record should show failed status
    keys = store.keys()
    in_flight_keys = [k for k in keys if k.startswith("in_flight_executions.")]
    assert len(in_flight_keys) >= 1
    in_flight_record = store.get(in_flight_keys[0])
    assert in_flight_record["status"] == "failed"


def test_idempotency_prevents_duplicate_execution():
    """Pre-set idempotency key -> second dispatch is skipped."""
    store, scheduler, *_ = make_test_harness()

    # Pre-set required state
    store.set("cleaned_output", "some text")
    store.set("gate_verdict", "CONFIRMED")

    # Compute the idempotency key that the authority would compute
    inputs = {"cleaned_output": "some text", "gate_verdict": "CONFIRMED"}
    idempotency_key = _compute_idempotency_key("extract_response", inputs)

    # Pre-set the dispatched key so the authority sees it as already dispatched
    store.set("dispatched_idempotency_keys", [idempotency_key])

    # Emit the lifecycle trigger
    scheduler.emit(
        SchedulerEvent(
            event_type="stability_reached",
            session_name="test_session",
            source="test",
        )
    )

    result = scheduler.run()

    # The authority handler was called but should have skipped dispatch
    event_types_processed = [
        rr.event.event_type for rr in result.route_results if not rr.skipped_dedup
    ]
    assert "stability_reached" in event_types_processed

    # No execution_requested event should have been emitted
    assert "execution_requested" not in event_types_processed

    # No completed executions
    completed = store.get("completed_executions")
    assert completed is None or len(completed) == 0


def test_multiple_runs_same_result():
    """Running the same lifecycle event twice produces no new state on second run."""
    store, scheduler, *_ = make_test_harness(
        emission_map={"extract_response": ["response_extracted"]},
    )

    # Pre-set required state
    store.set("cleaned_output", "deterministic input")
    store.set("gate_verdict", "CONFIRMED")

    # First run
    scheduler.emit(
        SchedulerEvent(
            event_type="stability_reached",
            session_name="test_session",
            source="test",
            event_id="evt_first_run",
        )
    )
    result1 = scheduler.run()
    state_after_first = store.snapshot()

    # Verify first run actually did work
    assert store.get("result_key") is not None
    completed_after_first = store.get("completed_executions", [])
    assert len(completed_after_first) == 1

    # Second run with a different event_id (same semantic trigger)
    scheduler.emit(
        SchedulerEvent(
            event_type="stability_reached",
            session_name="test_session",
            source="test",
            event_id="evt_second_run",
        )
    )
    result2 = scheduler.run()
    state_after_second = store.snapshot()

    # Idempotency should prevent the second execution from dispatching
    event_types_second = [
        rr.event.event_type for rr in result2.route_results if not rr.skipped_dedup
    ]
    assert "execution_requested" not in event_types_second

    # No new completed executions
    completed_after_second = store.get("completed_executions", [])
    assert len(completed_after_second) == len(completed_after_first)

    # result_key should be unchanged
    assert store.get("result_key") == state_after_first.get("result_key")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _noop_handler(collector: list, event: SchedulerEvent):
    """No-op handler that records the event it was called with."""
    from runtime.substrate.event_scheduler import (
        ExecutionResult as SchedulerExecutionResult,
    )

    collector.append(event)
    return SchedulerExecutionResult()
