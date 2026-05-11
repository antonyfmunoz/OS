"""Tests for ExecutionAuthority — non-blocking control-plane dispatch."""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/opt/OS")

from runtime.substrate.execution_authority import ExecutionAuthority
from runtime.substrate.execution_contract import (
    ExecutionClass,
    ExecutionConstraints,
    _compute_idempotency_key,
)
from runtime.substrate.event_scheduler import (
    ExecutionResult as SchedulerExecutionResult,
    SchedulerEvent,
)
from runtime.substrate.execution_router import ExecutionRouter
from runtime.substrate.nodes import (
    Node,
    NodeRegistry,
    NodeRole,
    NodeStatus,
    NodeType,
)
from runtime.substrate.runtime_state_store import RuntimeStateStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_registry() -> NodeRegistry:
    """Build a test registry with a single vps-primary node."""
    reg = NodeRegistry(persist=False)
    reg.upsert(
        Node(
            node_id="vps-primary",
            node_type=NodeType.VPS,
            role=NodeRole.ORCHESTRATOR,
            capabilities=["reasoning", "run_shell", "run_python"],
            status=NodeStatus.ONLINE,
        )
    )
    return reg


def _make_router() -> ExecutionRouter:
    return ExecutionRouter(_make_registry())


def _make_authority() -> ExecutionAuthority:
    return ExecutionAuthority(router=_make_router())


def _make_event(session_name: str = "test-session") -> SchedulerEvent:
    return SchedulerEvent(
        event_type="stability_reached",
        session_name=session_name,
        source="test",
        run_id="run-001",
        payload={"correlation_id": "corr-abc"},
    )


@pytest.fixture()
def authority() -> ExecutionAuthority:
    return _make_authority()


@pytest.fixture()
def store() -> RuntimeStateStore:
    return RuntimeStateStore()


@pytest.fixture()
def event() -> SchedulerEvent:
    return _make_event()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_authority_emits_execution_requested(
    authority: ExecutionAuthority,
    store: RuntimeStateStore,
    event: SchedulerEvent,
) -> None:
    """Handler emits exactly one event with event_type='execution_requested'."""
    handler = authority.make_handler(
        primitive_name="send_message",
        execution_class=ExecutionClass.TRANSPORT,
        requires=["channel_id"],
    )
    result = handler(store, event)

    assert len(result.emitted_events) == 1
    emitted = result.emitted_events[0]
    assert emitted.event_type == "execution_requested"
    assert emitted.source == "execution_authority"
    assert "request" in emitted.payload


def test_authority_records_in_flight(
    authority: ExecutionAuthority,
    store: RuntimeStateStore,
    event: SchedulerEvent,
) -> None:
    """Handler returns SET mutation for 'in_flight_executions.{exec_id}'."""
    handler = authority.make_handler(
        primitive_name="send_message",
        execution_class=ExecutionClass.TRANSPORT,
        requires=[],
    )
    result = handler(store, event)

    execution_id = result.metadata["execution_id"]
    set_mutations = [
        m
        for m in result.mutations
        if m["op"] == "SET" and m["key"] == f"in_flight_executions.{execution_id}"
    ]
    assert len(set_mutations) == 1

    record = set_mutations[0]["value"]
    assert record["execution_id"] == execution_id
    assert record["primitive_name"] == "send_message"
    assert record["status"] == "dispatched"
    assert record["target_node_id"] == "vps-primary"


def test_authority_records_dispatched_key(
    authority: ExecutionAuthority,
    store: RuntimeStateStore,
    event: SchedulerEvent,
) -> None:
    """Handler returns APPEND_UNIQUE for 'dispatched_idempotency_keys'."""
    handler = authority.make_handler(
        primitive_name="send_message",
        execution_class=ExecutionClass.TRANSPORT,
        requires=[],
    )
    result = handler(store, event)

    append_mutations = [
        m
        for m in result.mutations
        if m["op"] == "APPEND_UNIQUE" and m["key"] == "dispatched_idempotency_keys"
    ]
    assert len(append_mutations) == 1
    # Value should be the idempotency key string
    assert isinstance(append_mutations[0]["value"], str)
    assert len(append_mutations[0]["value"]) == 16  # SHA-256 prefix


def test_authority_skips_duplicate_idempotency(
    authority: ExecutionAuthority,
    event: SchedulerEvent,
) -> None:
    """Pre-set dispatched_idempotency_keys in store, same key -> handler returns empty (skipped)."""
    store = RuntimeStateStore()

    # Pre-compute the idempotency key for empty inputs
    expected_key = _compute_idempotency_key("send_message", {})
    store.set("dispatched_idempotency_keys", [expected_key])

    handler = authority.make_handler(
        primitive_name="send_message",
        execution_class=ExecutionClass.TRANSPORT,
        requires=[],
    )
    result = handler(store, event)

    assert result.mutations == []
    assert result.emitted_events == []
    assert result.metadata.get("skipped") is True


def test_authority_does_not_block(
    authority: ExecutionAuthority,
    store: RuntimeStateStore,
    event: SchedulerEvent,
) -> None:
    """Handler returns immediately with no adapter.execute() call.

    The handler has no adapter reference at all — it only produces
    mutations and events.
    """
    handler = authority.make_handler(
        primitive_name="send_message",
        execution_class=ExecutionClass.PURE,
        requires=[],
    )
    # Handler returns a SchedulerExecutionResult (synchronous, non-blocking)
    result = handler(store, event)

    assert isinstance(result, SchedulerExecutionResult)
    # No adapter attribute on the authority
    assert not hasattr(authority, "_adapter")
    assert not hasattr(authority, "adapter")


def test_authority_reads_inputs_from_store(
    authority: ExecutionAuthority,
    event: SchedulerEvent,
) -> None:
    """Pre-set state keys, verify they appear in the request payload."""
    store = RuntimeStateStore()
    store.set("channel_id", "discord-123")
    store.set("message_body", "hello world")

    handler = authority.make_handler(
        primitive_name="send_message",
        execution_class=ExecutionClass.TRANSPORT,
        requires=["channel_id", "message_body"],
    )
    result = handler(store, event)

    # Extract the request from the emitted event payload
    emitted = result.emitted_events[0]
    request_dict = emitted.payload["request"]

    assert request_dict["inputs"]["channel_id"] == "discord-123"
    assert request_dict["inputs"]["message_body"] == "hello world"
    assert request_dict["primitive_name"] == "send_message"

    # Also verify in the in-flight record
    set_mutation = [m for m in result.mutations if m["op"] == "SET"][0]
    original_request = set_mutation["value"]["original_request"]
    assert original_request["inputs"]["channel_id"] == "discord-123"
    assert original_request["inputs"]["message_body"] == "hello world"
