"""Tests for eos_ai.substrate.execution_contract."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from eos_ai.substrate.execution_contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTarget,
    _compute_execution_hash,
    _compute_idempotency_key,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_request(**overrides) -> ExecutionRequest:
    defaults = dict(
        execution_id="exec_abc123",
        correlation_id="corr_001",
        causal_event_id="evt_001",
        session_name="test-session",
        run_id="run_001",
        primitive_name="send_message",
        inputs={"channel": "general", "text": "hello"},
        execution_class=ExecutionClass.SIDE_EFFECT,
        constraints=ExecutionConstraints(timeout_s=10, max_retries=1, sandbox=True),
        target=ExecutionTarget(
            node_id="vps-primary",
            transport="local",
            fallback_node_id="station-1",
            fallback_transport="ssh",
        ),
        issued_at="2026-04-16T00:00:00Z",
        issued_by="router",
        idempotency_key="key123",
        retry_count=0,
    )
    defaults.update(overrides)
    return ExecutionRequest(**defaults)


def _make_result(**overrides) -> ExecutionResult:
    defaults = dict(
        execution_id="exec_abc123",
        correlation_id="corr_001",
        causal_event_id="evt_001",
        primitive_name="send_message",
        status=ExecutionStatus.SUCCEEDED,
        outputs={"message_id": "msg_999"},
        side_effects=("discord:message_sent",),
        error=None,
        started_at="2026-04-16T00:00:00Z",
        completed_at="2026-04-16T00:00:01Z",
        node_id="vps-primary",
        idempotency_key="key123",
        execution_hash="hash456",
        retry_count=0,
    )
    defaults.update(overrides)
    return ExecutionResult(**defaults)


# ---------------------------------------------------------------------------
# Roundtrip tests
# ---------------------------------------------------------------------------


def test_execution_request_roundtrip():
    """to_dict/from_dict produces an equivalent ExecutionRequest."""
    original = _make_request()
    rebuilt = ExecutionRequest.from_dict(original.to_dict())
    assert rebuilt == original


def test_execution_result_roundtrip():
    """to_dict/from_dict produces an equivalent ExecutionResult."""
    original = _make_result()
    rebuilt = ExecutionResult.from_dict(original.to_dict())
    assert rebuilt == original


# ---------------------------------------------------------------------------
# Idempotency key tests
# ---------------------------------------------------------------------------


def test_idempotency_key_deterministic():
    """Same primitive + inputs must produce the same key every time."""
    key1 = _compute_idempotency_key("send_message", {"text": "hi"})
    key2 = _compute_idempotency_key("send_message", {"text": "hi"})
    assert key1 == key2
    assert len(key1) == 16


def test_idempotency_key_differs_on_input_change():
    """Different inputs must produce a different key."""
    key_a = _compute_idempotency_key("send_message", {"text": "hi"})
    key_b = _compute_idempotency_key("send_message", {"text": "bye"})
    assert key_a != key_b


# ---------------------------------------------------------------------------
# Execution hash tests
# ---------------------------------------------------------------------------


def test_execution_hash_deterministic():
    """Same id + status + outputs must produce the same hash every time."""
    h1 = _compute_execution_hash("exec_1", "succeeded", {"ok": True})
    h2 = _compute_execution_hash("exec_1", "succeeded", {"ok": True})
    assert h1 == h2
    assert len(h1) == 16


# ---------------------------------------------------------------------------
# Immutability tests
# ---------------------------------------------------------------------------


def test_frozen_dataclasses_immutable():
    """Cannot assign to fields on ExecutionRequest or ExecutionResult."""
    req = _make_request()
    with pytest.raises(AttributeError):
        req.execution_id = "changed"  # type: ignore[misc]

    res = _make_result()
    with pytest.raises(AttributeError):
        res.status = ExecutionStatus.FAILED  # type: ignore[misc]
