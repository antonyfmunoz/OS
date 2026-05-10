"""Tests for execution adapters — LocalRuntimeAdapter and WorkstationAdapter."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from eos_ai.substrate.control_commands import ControlCommand
from eos_ai.substrate.execution_adapter import (
    AdapterHealth,
    LocalRuntimeAdapter,
    WorkstationAdapter,
)
from eos_ai.substrate.execution_contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTarget,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(
    primitive_name: str = "run_shell",
    inputs: dict | None = None,
    node_id: str = "vps-primary",
) -> ExecutionRequest:
    """Build a minimal ExecutionRequest for testing."""
    return ExecutionRequest(
        execution_id="exec_test_001",
        correlation_id="corr_test_001",
        causal_event_id="evt_test_001",
        session_name="test-session",
        run_id="run_test_001",
        primitive_name=primitive_name,
        inputs=inputs or {"cmd": "echo hello"},
        execution_class=ExecutionClass.SIDE_EFFECT,
        constraints=ExecutionConstraints(timeout_s=10),
        target=ExecutionTarget(node_id=node_id, transport="local"),
        issued_at="2026-04-16T00:00:00Z",
        issued_by="test_harness",
        idempotency_key="idem_test_001",
    )


# ---------------------------------------------------------------------------
# LocalRuntimeAdapter tests
# ---------------------------------------------------------------------------


def test_local_adapter_wraps_executor() -> None:
    """Mock local_executor.execute_command, verify it's called with correct ControlCommand."""
    adapter = LocalRuntimeAdapter()
    request = _make_request(primitive_name="run_shell", inputs={"cmd": "ls"})

    mock_result = {
        "ok": True,
        "command_id": "cmd_abc",
        "action": "run_shell",
        "node_id": "vps-primary",
        "executed_at": 1713225600.0,
        "exit_code": 0,
        "stdout": "file.txt",
        "stderr": "",
    }

    with patch(
        "eos_ai.substrate.local_executor.execute_command",
        return_value=mock_result,
    ) as mock_exec:
        result = adapter.execute(request)

        # Verify execute_command was called exactly once
        mock_exec.assert_called_once()

        # Verify the ControlCommand passed in
        call_args = mock_exec.call_args
        cmd: ControlCommand = call_args[0][0]
        assert isinstance(cmd, ControlCommand)
        assert cmd.action == "run_shell"
        assert cmd.payload == {"cmd": "ls"}
        assert cmd.issued_by == "test_harness"
        assert cmd.node_id == "vps-primary"
        assert cmd.target == "local"


def test_local_adapter_returns_execution_result() -> None:
    """Verify output has correct ExecutionResult fields."""
    adapter = LocalRuntimeAdapter()
    request = _make_request(
        primitive_name="write_file", inputs={"path": "test.txt", "content": "hi"}
    )

    mock_result = {
        "ok": True,
        "command_id": "cmd_xyz",
        "action": "write_file",
        "node_id": "vps-primary",
        "executed_at": 1713225600.0,
        "path": f"{_ROOT}/eos_ai/.substrate_sandbox/test.txt",
        "bytes_written": 2,
    }

    with patch(
        "eos_ai.substrate.local_executor.execute_command",
        return_value=mock_result,
    ):
        result = adapter.execute(request)

    assert isinstance(result, ExecutionResult)
    assert result.execution_id == "exec_test_001"
    assert result.correlation_id == "corr_test_001"
    assert result.causal_event_id == "evt_test_001"
    assert result.primitive_name == "write_file"
    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.node_id == "vps-primary"
    assert result.idempotency_key == "idem_test_001"
    assert result.retry_count == 0
    assert result.started_at is not None
    assert result.completed_at is not None
    assert result.outputs["ok"] is True


def test_local_adapter_rejects_unknown_primitive() -> None:
    """Request with primitive_name not in capabilities -> REJECTED."""
    adapter = LocalRuntimeAdapter()
    request = _make_request(primitive_name="launch_missile")

    result = adapter.execute(request)

    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.REJECTED
    assert "launch_missile" in (result.error or "")
    assert result.node_id == "vps-primary"


def test_local_adapter_returns_failed_on_executor_error() -> None:
    """Executor returning ok=False produces FAILED result."""
    adapter = LocalRuntimeAdapter()
    request = _make_request(primitive_name="run_shell", inputs={"cmd": "rm -rf /"})

    mock_result = {
        "ok": False,
        "command_id": "cmd_bad",
        "action": "run_shell",
        "node_id": "vps-primary",
        "executed_at": 1713225600.0,
        "reason": "shell_not_whitelisted:rm",
    }

    with patch(
        "eos_ai.substrate.local_executor.execute_command",
        return_value=mock_result,
    ):
        result = adapter.execute(request)

    assert result.status == ExecutionStatus.FAILED
    assert result.error == "shell_not_whitelisted:rm"


def test_local_adapter_returns_timed_out() -> None:
    """Executor returning reason=timeout produces TIMED_OUT result."""
    adapter = LocalRuntimeAdapter()
    request = _make_request(primitive_name="run_shell", inputs={"cmd": "echo slow"})

    mock_result = {
        "ok": False,
        "command_id": "cmd_timeout",
        "action": "run_shell",
        "node_id": "vps-primary",
        "executed_at": 1713225600.0,
        "reason": "timeout",
    }

    with patch(
        "eos_ai.substrate.local_executor.execute_command",
        return_value=mock_result,
    ):
        result = adapter.execute(request)

    assert result.status == ExecutionStatus.TIMED_OUT
    assert result.error == "timeout"


def test_local_adapter_catches_exception() -> None:
    """If execute_command raises, adapter returns FAILED, never raises."""
    adapter = LocalRuntimeAdapter()
    request = _make_request()

    with patch(
        "eos_ai.substrate.local_executor.execute_command",
        side_effect=RuntimeError("boom"),
    ):
        result = adapter.execute(request)

    assert result.status == ExecutionStatus.FAILED
    assert "RuntimeError" in (result.error or "")
    assert "boom" in (result.error or "")


def test_local_adapter_health() -> None:
    """Health check returns healthy status."""
    adapter = LocalRuntimeAdapter()
    h = adapter.health()

    assert isinstance(h, AdapterHealth)
    assert h.node_id == "vps-primary"
    assert h.status == "healthy"
    assert h.capabilities_count == 3


# ---------------------------------------------------------------------------
# WorkstationAdapter tests
# ---------------------------------------------------------------------------


def test_workstation_adapter_calls_http() -> None:
    """Mock send_task_via_http, verify called with correct dict."""
    adapter = WorkstationAdapter(node_id="test-workstation")
    request = _make_request(
        primitive_name="speak_text",
        inputs={"text": "hello world"},
        node_id="test-workstation",
    )

    mock_response = {"status": "ok", "detail": "spoken", "data": {}}

    with patch(
        "eos_ai.substrate.node_transport.send_task_via_http",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_http:
        result = adapter.execute(request)

        mock_http.assert_called_once()
        call_kwargs = mock_http.call_args
        action_dict = call_kwargs[0][0]

        assert action_dict["kind"] == "speak_text"
        assert action_dict["payload"] == {"text": "hello world"}
        assert action_dict["execution_id"] == "exec_test_001"
        assert action_dict["issued_by"] == "test_harness"

        # Verify timeout passed through
        assert call_kwargs[1]["timeout_s"] == 10.0

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.node_id == "test-workstation"


def test_workstation_adapter_falls_back_on_http_failure() -> None:
    """Mock returns None -> FAILED result."""
    adapter = WorkstationAdapter()
    request = _make_request(
        primitive_name="speak_text",
        inputs={"text": "fail"},
    )

    with patch(
        "eos_ai.substrate.node_transport.send_task_via_http",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = adapter.execute(request)

    assert result.status == ExecutionStatus.FAILED
    assert "http_transport_failure" in (result.error or "")
    assert result.node_id == "antony-workstation"


def test_workstation_adapter_rejects_unknown_primitive() -> None:
    """Request with primitive not in capabilities -> REJECTED."""
    adapter = WorkstationAdapter()
    request = _make_request(primitive_name="run_shell")

    result = adapter.execute(request)

    assert result.status == ExecutionStatus.REJECTED
    assert "run_shell" in (result.error or "")


def test_workstation_adapter_catches_exception() -> None:
    """If send_task_via_http raises, adapter returns FAILED."""
    adapter = WorkstationAdapter()
    request = _make_request(
        primitive_name="open_url",
        inputs={"url": "https://example.com"},
    )

    with patch(
        "eos_ai.substrate.node_transport.send_task_via_http",
        new_callable=AsyncMock,
        side_effect=ConnectionError("refused"),
    ):
        result = adapter.execute(request)

    assert result.status == ExecutionStatus.FAILED
    assert "ConnectionError" in (result.error or "")


def test_workstation_adapter_error_response() -> None:
    """HTTP returns error status -> FAILED with detail."""
    adapter = WorkstationAdapter()
    request = _make_request(
        primitive_name="play_sound",
        inputs={"path": "/sounds/alert.wav"},
    )

    mock_response = {
        "status": "error",
        "detail": "file not found",
        "data": {},
    }

    with patch(
        "eos_ai.substrate.node_transport.send_task_via_http",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = adapter.execute(request)

    assert result.status == ExecutionStatus.FAILED
    assert result.error == "file not found"


def test_workstation_adapter_health_healthy() -> None:
    """Health check returns healthy when HTTP is reachable."""
    adapter = WorkstationAdapter()

    with patch(
        "eos_ai.substrate.node_transport.check_http_health",
        new_callable=AsyncMock,
        return_value=True,
    ):
        h = adapter.health()

    assert h.status == "healthy"
    assert h.capabilities_count == 6


def test_workstation_adapter_health_unhealthy() -> None:
    """Health check returns unhealthy when HTTP is unreachable."""
    adapter = WorkstationAdapter()

    with patch(
        "eos_ai.substrate.node_transport.check_http_health",
        new_callable=AsyncMock,
        return_value=False,
    ):
        h = adapter.health()

    assert h.status == "unhealthy"


# ---------------------------------------------------------------------------
# Design constraint: adapters must not reference RuntimeStateStore
# ---------------------------------------------------------------------------


def test_adapter_does_not_mutate_state() -> None:
    """Verify adapters have no reference to RuntimeStateStore.

    This is a design test: adapters are stateless workers and must never
    hold a reference to the state store. We inspect the source to confirm.
    """
    import inspect

    from eos_ai.substrate import execution_adapter

    source = inspect.getsource(execution_adapter)

    # The module must not import or reference RuntimeStateStore
    assert "RuntimeStateStore" not in source, (
        "execution_adapter.py must not reference RuntimeStateStore — "
        "adapters are stateless workers"
    )

    # Also verify no instance attributes referencing state
    local_adapter = LocalRuntimeAdapter()
    workstation_adapter = WorkstationAdapter()

    for attr_name in dir(local_adapter):
        if attr_name.startswith("_") and not attr_name.startswith("__"):
            val = getattr(local_adapter, attr_name)
            assert "state_store" not in str(type(val)).lower()

    for attr_name in dir(workstation_adapter):
        if attr_name.startswith("_") and not attr_name.startswith("__"):
            val = getattr(workstation_adapter, attr_name)
            assert "state_store" not in str(type(val)).lower()
