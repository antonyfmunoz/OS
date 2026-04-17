"""Tests for ExecutionResultHandler — result validation, dedup, state mutation, lifecycle emission."""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.execution_contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTarget,
)
from eos_ai.substrate.execution_result_handler import ExecutionResultHandler
from eos_ai.substrate.event_scheduler import (
    ExecutionResult as SchedulerExecutionResult,
    SchedulerEvent,
)
from eos_ai.substrate.runtime_state_store import RuntimeStateStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_ORIGINAL_REQUEST = {
    "execution_id": "exec_123",
    "correlation_id": "corr_001",
    "causal_event_id": "sev_abc",
    "session_name": "test-session",
    "run_id": "run_001",
    "primitive_name": "extract_response",
    "inputs": {"raw": "hello"},
    "execution_class": "pure",
    "constraints": {"timeout_s": 30, "max_retries": 2, "sandbox": False},
    "target": {
        "node_id": "vps-primary",
        "transport": "local",
        "fallback_node_id": None,
        "fallback_transport": None,
    },
    "issued_at": "2026-04-16T00:00:00+00:00",
    "issued_by": "execution_authority",
    "idempotency_key": "abc123",
    "retry_count": 0,
}


def _make_in_flight(
    execution_id: str = "exec_123",
    primitive_name: str = "extract_response",
    execution_class: str = "pure",
    max_retries: int = 2,
    retry_count: int = 0,
    fallback_node_id: str | None = None,
    fallback_transport: str | None = None,
) -> dict:
    """Build a realistic in-flight execution record."""
    req = dict(_ORIGINAL_REQUEST)
    req["execution_id"] = execution_id
    req["primitive_name"] = primitive_name
    req["execution_class"] = execution_class
    return {
        "execution_id": execution_id,
        "primitive_name": primitive_name,
        "status": "dispatched",
        "execution_class": execution_class,
        "max_retries": max_retries,
        "retry_count": retry_count,
        "original_request": req,
        "fallback_node_id": fallback_node_id,
        "fallback_transport": fallback_transport,
    }


def _make_store(execution_id: str = "exec_123", **kwargs) -> RuntimeStateStore:
    """Build a store pre-populated with an in-flight record."""
    store = RuntimeStateStore()
    in_flight = _make_in_flight(execution_id=execution_id, **kwargs)
    store.set(f"in_flight_executions.{execution_id}", in_flight)
    return store


def _make_result_event(
    execution_id: str = "exec_123",
    status: str = "succeeded",
    primitive_name: str = "extract_response",
    outputs: dict | None = None,
    error: str | None = None,
    event_type: str = "execution_completed",
) -> SchedulerEvent:
    """Build a SchedulerEvent wrapping an ExecutionResult."""
    result = ExecutionResult(
        execution_id=execution_id,
        correlation_id="corr_001",
        causal_event_id="sev_abc",
        primitive_name=primitive_name,
        status=ExecutionStatus(status),
        outputs=outputs or {},
        error=error,
        started_at="2026-04-16T00:00:01+00:00",
        completed_at="2026-04-16T00:00:02+00:00",
        node_id="vps-primary",
    )
    return SchedulerEvent(
        event_type=event_type,
        session_name="test-session",
        source="execution_worker",
        run_id="run_001",
        payload={"result": result.to_dict()},
        metadata={"execution_id": execution_id},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSucceeded:
    """SUCCEEDED result handling."""

    def test_succeeded_writes_outputs(self) -> None:
        """SUCCEEDED result with outputs → SET mutation for each output key."""
        store = _make_store()
        handler = ExecutionResultHandler()
        event = _make_result_event(outputs={"raw_response": "hello"})

        result = handler.handle_result(store, event)

        set_mutations = [
            m
            for m in result.mutations
            if m["op"] == "SET" and m["key"] == "raw_response"
        ]
        assert len(set_mutations) == 1
        assert set_mutations[0]["value"] == "hello"

    def test_succeeded_marks_complete(self) -> None:
        """SUCCEEDED → execution_id appears in APPEND_UNIQUE for completed_executions."""
        store = _make_store()
        handler = ExecutionResultHandler()
        event = _make_result_event(outputs={"raw_response": "hello"})

        result = handler.handle_result(store, event)

        append_mutations = [
            m
            for m in result.mutations
            if m["op"] == "APPEND_UNIQUE" and m["key"] == "completed_executions"
        ]
        assert len(append_mutations) == 1
        assert append_mutations[0]["value"] == "exec_123"

    def test_succeeded_emits_lifecycle_events(self) -> None:
        """Configured emissions for primitive → lifecycle event emitted on success."""
        store = _make_store()
        handler = ExecutionResultHandler(
            primitive_emission_map={"extract_response": ["response_extracted"]},
        )
        event = _make_result_event(outputs={"raw_response": "hello"})

        result = handler.handle_result(store, event)

        assert len(result.emitted_events) == 1
        emitted = result.emitted_events[0]
        assert emitted.event_type == "response_extracted"
        assert emitted.source == "result_handler"
        assert emitted.payload["execution_id"] == "exec_123"
        assert emitted.payload["outputs"]["raw_response"] == "hello"

    def test_succeeded_emits_conditional_event(self) -> None:
        """Conditional emission fires when condition matches outputs."""
        store = _make_store()
        handler = ExecutionResultHandler(
            primitive_conditional_map={
                "extract_response": {"gate_verdict==CONFIRMED": "gate_confirmed"},
            },
        )
        event = _make_result_event(outputs={"gate_verdict": "CONFIRMED"})

        result = handler.handle_result(store, event)

        assert len(result.emitted_events) == 1
        assert result.emitted_events[0].event_type == "gate_confirmed"

    def test_succeeded_conditional_no_match(self) -> None:
        """Conditional emission does NOT fire when condition does not match."""
        store = _make_store()
        handler = ExecutionResultHandler(
            primitive_conditional_map={
                "extract_response": {"gate_verdict==CONFIRMED": "gate_confirmed"},
            },
        )
        event = _make_result_event(outputs={"gate_verdict": "DENIED"})

        result = handler.handle_result(store, event)

        assert len(result.emitted_events) == 0


class TestDuplicate:
    """Idempotency dedup."""

    def test_duplicate_completion_dropped(self) -> None:
        """Pre-set completed_executions with execution_id → handler returns skipped."""
        store = _make_store()
        # Pre-populate completed set
        store.set("completed_executions", ["exec_123"])
        handler = ExecutionResultHandler()
        event = _make_result_event(outputs={"raw_response": "hello"})

        result = handler.handle_result(store, event)

        assert result.metadata["skipped"] is True
        assert result.metadata["reason"] == "duplicate_execution_id"
        assert len(result.mutations) == 0
        assert len(result.emitted_events) == 0


class TestNoInFlight:
    """Missing in-flight record."""

    def test_no_in_flight_record_dropped(self) -> None:
        """Result for unknown execution_id → dropped silently."""
        store = RuntimeStateStore()  # empty store — no in-flight records
        handler = ExecutionResultHandler()
        event = _make_result_event(
            execution_id="exec_unknown",
            outputs={"raw_response": "hello"},
        )

        result = handler.handle_result(store, event)

        assert result.metadata["skipped"] is True
        assert result.metadata["reason"] == "no_in_flight_record"
        assert len(result.mutations) == 0


class TestFailed:
    """FAILED result handling with retry logic."""

    def test_failed_pure_retries(self) -> None:
        """FAILED + execution_class=pure + retry_count=0 + max_retries=2 → emits execution_retried."""
        store = _make_store(execution_class="pure", max_retries=2, retry_count=0)
        handler = ExecutionResultHandler()
        event = _make_result_event(
            status="failed",
            error="something broke",
            event_type="execution_failed",
        )

        result = handler.handle_result(store, event)

        assert result.metadata["status"] == "retrying"
        assert result.metadata["retry_count"] == 1
        assert len(result.emitted_events) == 1
        assert result.emitted_events[0].event_type == "execution_retried"
        # Should NOT be in completed_executions
        completed_mutations = [
            m
            for m in result.mutations
            if m["op"] == "APPEND_UNIQUE" and m["key"] == "completed_executions"
        ]
        assert len(completed_mutations) == 0

    def test_failed_side_effect_no_retry(self) -> None:
        """FAILED + execution_class=side_effect → no retry, permanent failure."""
        store = _make_store(execution_class="side_effect", max_retries=2, retry_count=0)
        handler = ExecutionResultHandler()
        event = _make_result_event(
            status="failed",
            error="side effect failed",
            event_type="execution_failed",
        )

        result = handler.handle_result(store, event)

        assert result.metadata["status"] == "permanent_failure"
        assert len(result.emitted_events) == 0
        # Should be marked in completed_executions
        completed_mutations = [
            m
            for m in result.mutations
            if m["op"] == "APPEND_UNIQUE" and m["key"] == "completed_executions"
        ]
        assert len(completed_mutations) == 1

    def test_failed_transport_retries(self) -> None:
        """FAILED + execution_class=transport + retries left → emits execution_retried."""
        store = _make_store(execution_class="transport", max_retries=3, retry_count=1)
        handler = ExecutionResultHandler()
        event = _make_result_event(
            status="failed",
            error="transport error",
            event_type="execution_failed",
        )

        result = handler.handle_result(store, event)

        assert result.metadata["status"] == "retrying"
        assert result.metadata["retry_count"] == 2
        assert len(result.emitted_events) == 1
        assert result.emitted_events[0].event_type == "execution_retried"

    def test_failed_retries_exhausted(self) -> None:
        """FAILED + retry_count >= max_retries → permanent failure."""
        store = _make_store(execution_class="pure", max_retries=2, retry_count=2)
        handler = ExecutionResultHandler()
        event = _make_result_event(
            status="failed",
            error="still broken",
            event_type="execution_failed",
        )

        result = handler.handle_result(store, event)

        assert result.metadata["status"] == "permanent_failure"
        assert len(result.emitted_events) == 0


class TestTimedOut:
    """TIMED_OUT result handling."""

    def test_timed_out_treated_as_failed(self) -> None:
        """TIMED_OUT result → same path as FAILED (retry if allowed)."""
        store = _make_store(execution_class="pure", max_retries=2, retry_count=0)
        handler = ExecutionResultHandler()
        event = _make_result_event(
            status="timed_out",
            error="timeout",
            event_type="execution_timed_out",
        )

        result = handler.handle_result(store, event)

        # Should retry since pure with retries remaining
        assert result.metadata["status"] == "retrying"
        assert len(result.emitted_events) == 1
        assert result.emitted_events[0].event_type == "execution_retried"


class TestRejected:
    """REJECTED result handling."""

    def test_rejected_fallback_reroute(self) -> None:
        """REJECTED + fallback_node_id set → emits execution_retried targeting fallback."""
        store = _make_store(
            fallback_node_id="vps-secondary",
            fallback_transport="ssh",
        )
        handler = ExecutionResultHandler()
        event = _make_result_event(
            status="rejected",
            error="node busy",
            event_type="execution_rejected",
        )

        result = handler.handle_result(store, event)

        assert result.metadata["status"] == "fallback_reroute"
        assert result.metadata["fallback_node_id"] == "vps-secondary"
        assert len(result.emitted_events) == 1
        retry_event = result.emitted_events[0]
        assert retry_event.event_type == "execution_retried"
        # The retried request should target the fallback node
        retried_request = retry_event.payload["request"]
        assert retried_request["target"]["node_id"] == "vps-secondary"

    def test_rejected_no_fallback_permanent_fail(self) -> None:
        """REJECTED + no fallback → permanent failure."""
        store = _make_store(
            execution_class="side_effect",  # side effect so no retry either
            fallback_node_id=None,
        )
        handler = ExecutionResultHandler()
        event = _make_result_event(
            status="rejected",
            error="no capacity",
            event_type="execution_rejected",
        )

        result = handler.handle_result(store, event)

        assert result.metadata["status"] == "permanent_failure"
        assert len(result.emitted_events) == 0
