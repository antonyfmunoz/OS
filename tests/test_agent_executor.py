"""Tests for AgentExecutor — Phase 17A.

Validates:
  - Risk classification
  - Path validation
  - Prompt assembly
  - Output parsing
  - Validation logic
  - Prepare gate checks
  - Execute lifecycle (mocked Claude Code CLI)
  - Monitor/cancel/cleanup
  - Proof generation
  - Telemetry emission
  - Runtime context builder
  - Route API structure
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.executors.agent_executor import (
    AgentExecutionProof,
    AgentExecutor,
    AgentTaskResult,
    SUPPORTED_OPERATIONS,
    _validate_working_dir,
    build_agent_runtime_context,
    classify_agent_task_risk,
    parse_agent_output,
)
from substrate.organism.executor_runtime import (
    ExecutorRequest,
    ExecutorResult,
    ExecutorType,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _make_request(
    task: str = "add a test file",
    operation: str = "run_task",
    executor_type: str = "agent",
    repo_path: str = "/opt/OS",
    request_id: str = "test-req-001",
    **extra_params: Any,
) -> ExecutorRequest:
    return ExecutorRequest(
        request_id=request_id,
        execution_plan_id=f"plan-{request_id}",
        executor_type=executor_type,
        metadata={
            "operation": operation,
            "params": {
                "task": task,
                "repo_path": repo_path,
                **extra_params,
            },
        },
        description=task[:200],
    )


def _make_executor(
    telemetry: Any | None = None,
    runtime: Any | None = None,
) -> AgentExecutor:
    return AgentExecutor(
        telemetry_emitter=telemetry,
        runtime=runtime,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Risk Classification
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_classify_low_risk():
    assert classify_agent_task_risk("add a test file") == "low"
    assert classify_agent_task_risk("refactor the auth module") == "low"


def test_classify_medium_risk():
    assert classify_agent_task_risk("delete the old migration file") == "medium"
    assert classify_agent_task_risk("remove unused imports") == "medium"
    assert classify_agent_task_risk("overwrite the config") == "medium"


def test_classify_high_risk():
    assert classify_agent_task_risk("git push to main") == "high"
    assert classify_agent_task_risk("run rm -rf /tmp/old") == "high"
    assert classify_agent_task_risk("flyctl deploy the cockpit") == "high"
    assert classify_agent_task_risk("use --force flag") == "high"
    assert classify_agent_task_risk("DROP TABLE users") == "high"
    assert classify_agent_task_risk("edit the .env file") == "high"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Path Validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_validate_approved_path():
    path, err = _validate_working_dir("/opt/OS")
    assert not err
    assert str(path) == "/opt/OS"


def test_validate_subdir_of_approved():
    path, err = _validate_working_dir("/opt/OS/substrate")
    assert not err


def test_validate_unapproved_path():
    _, err = _validate_working_dir("/etc/passwd")
    assert "outside approved roots" in err


def test_validate_nonexistent_path():
    _, err = _validate_working_dir("/opt/OS/nonexistent_xyz_dir")
    assert err


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Output Parsing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_parse_agent_output_structured():
    raw = """\
I added a test file.

AGENT_RESULT:
status: success
summary: Added test_foo.py with 3 tests
files_changed: tests/test_foo.py
commands_run: python3 -m pytest tests/test_foo.py
proof_notes: All 3 tests pass
remaining_blockers: none
"""
    result = parse_agent_output(raw, exit_code=0)
    assert result.status == "success"
    assert result.summary == "Added test_foo.py with 3 tests"
    assert result.files_changed == ["tests/test_foo.py"]
    assert result.commands_run == ["python3 -m pytest tests/test_foo.py"]
    assert result.proof_notes == "All 3 tests pass"
    assert result.remaining_blockers == "none"


def test_parse_agent_output_no_result_block():
    raw = "I made some changes but no structured output block."
    result = parse_agent_output(raw, exit_code=0)
    assert result.status == "success"
    assert raw in result.summary


def test_parse_agent_output_failure():
    raw = "Error: could not compile"
    result = parse_agent_output(raw, exit_code=1)
    assert result.status == "failed"
    assert result.exit_code == 1


def test_parse_agent_output_multiple_files():
    raw = """\
AGENT_RESULT:
status: success
summary: Updated two files
files_changed: a.py, b.py, c.py
commands_run: python3 -m py_compile a.py, python3 -m py_compile b.py
proof_notes: All compile clean
remaining_blockers: none
"""
    result = parse_agent_output(raw, exit_code=0)
    assert len(result.files_changed) == 3
    assert len(result.commands_run) == 2


def test_agent_task_result_to_dict():
    r = AgentTaskResult(
        status="success",
        summary="done",
        files_changed=["a.py"],
        commands_run=["pytest"],
        proof_notes="ok",
        remaining_blockers="none",
        exit_code=0,
    )
    d = r.to_dict()
    assert d["status"] == "success"
    assert d["exit_code"] == 0
    assert "raw_output" not in d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime Context Builder
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_build_context_with_snapshot():
    snapshot = {
        "summary": {
            "worktree_count": 2,
            "process_count": 5,
            "container_count": 3,
            "execution_count": 1,
        },
        "repositories": [
            {
                "current_branch": "main",
                "dirty": True,
                "untracked_count": 2,
            }
        ],
        "worktrees": [
            {"branch": "feature-1", "path": "/opt/OS/.claude/worktrees/feature-1"},
        ],
        "containers": [
            {"name": "os-discord", "status": "Up 2h"},
        ],
    }
    req = _make_request()
    ctx = build_agent_runtime_context(snapshot, req)
    assert "UMH RUNTIME CONTEXT" in ctx
    assert "Worktrees: 2" in ctx
    assert "Dirty: True" in ctx
    assert "feature-1" in ctx
    assert "os-discord" in ctx


def test_build_context_no_snapshot():
    req = _make_request()
    ctx = build_agent_runtime_context(None, req)
    assert "unavailable" in ctx


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_validate_success():
    ex = _make_executor()
    req = _make_request()
    ok, msg = ex.validate(req)
    assert ok
    assert "run_task" in msg


def test_validate_no_plan_id():
    ex = _make_executor()
    req = _make_request()
    req.execution_plan_id = ""
    ok, msg = ex.validate(req)
    assert not ok
    assert "execution_plan_id" in msg


def test_validate_wrong_executor_type():
    ex = _make_executor()
    req = _make_request(executor_type="workstation")
    ok, msg = ex.validate(req)
    assert not ok
    assert "Wrong executor type" in msg


def test_validate_no_operation():
    ex = _make_executor()
    req = _make_request()
    req.metadata["operation"] = ""
    ok, msg = ex.validate(req)
    assert not ok
    assert "No operation" in msg


def test_validate_unsupported_operation():
    ex = _make_executor()
    req = _make_request(operation="hack_something")
    ok, msg = ex.validate(req)
    assert not ok
    assert "Unsupported" in msg


def test_validate_stub_operation():
    ex = _make_executor()
    req = _make_request(operation="continue_task")
    ok, msg = ex.validate(req)
    assert not ok
    assert "stub" in msg


def test_validate_empty_task():
    ex = _make_executor()
    req = _make_request(task="")
    ok, msg = ex.validate(req)
    assert not ok
    assert "Empty task" in msg


def test_validate_task_too_long():
    ex = _make_executor()
    req = _make_request(task="x" * 20000)
    ok, msg = ex.validate(req)
    assert not ok
    assert "too long" in msg


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Prepare
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@patch(
    "substrate.organism.executors.agent_executor.cpu_gate_check",
    return_value=MagicMock(allowed=True, reason="ok"),
)
def test_prepare_success(mock_gate: MagicMock) -> None:
    ex = _make_executor()
    req = _make_request(repo_path="/opt/OS")
    ok, msg = ex.prepare(req)
    assert ok
    assert "/opt/OS" in msg


@patch(
    "substrate.organism.executors.agent_executor.cpu_gate_check",
    return_value=MagicMock(allowed=False, reason="CPU load too high"),
)
def test_prepare_cpu_gate_blocked(mock_gate: MagicMock) -> None:
    ex = _make_executor()
    req = _make_request()
    ok, msg = ex.prepare(req)
    assert not ok
    assert "CPU gate" in msg


@patch(
    "substrate.organism.executors.agent_executor.cpu_gate_check",
    return_value=MagicMock(allowed=True, reason="ok"),
)
def test_prepare_bad_path(mock_gate: MagicMock) -> None:
    ex = _make_executor()
    req = _make_request(repo_path="/etc/passwd")
    ok, msg = ex.prepare(req)
    assert not ok
    assert "invalid" in msg.lower() or "outside" in msg.lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Execute (mocked CLI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class FakeProcess:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


@patch(
    "substrate.organism.executors.agent_executor.cpu_gate_check",
    return_value=MagicMock(allowed=True, reason="ok"),
)
@patch("substrate.organism.executors.agent_executor.gated_subprocess_run")
def test_execute_success(mock_run: MagicMock, mock_gate: MagicMock) -> None:
    mock_run.return_value = FakeProcess(
        returncode=0,
        stdout="""\
I added the test file.

AGENT_RESULT:
status: success
summary: Added test_foo.py
files_changed: tests/test_foo.py
commands_run: pytest
proof_notes: Tests pass
remaining_blockers: none
""",
    )

    tel = MagicMock()
    ex = _make_executor(telemetry=tel)
    req = _make_request()
    ex.prepare(req)

    result = ex.execute(req)

    assert isinstance(result, ExecutorResult)
    assert result.success
    assert "test_foo.py" in result.outcome
    assert result.metadata.get("proof")
    assert result.metadata["proof"]["status"] == "success"

    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "claude"
    assert cmd[1] == "--print"

    assert tel.emit.called


@patch(
    "substrate.organism.executors.agent_executor.cpu_gate_check",
    return_value=MagicMock(allowed=True, reason="ok"),
)
@patch("substrate.organism.executors.agent_executor.gated_subprocess_run")
def test_execute_cli_failure(mock_run: MagicMock, mock_gate: MagicMock) -> None:
    mock_run.return_value = FakeProcess(returncode=1, stdout="Error: compile failed")

    ex = _make_executor()
    req = _make_request()
    ex.prepare(req)

    result = ex.execute(req)
    assert not result.success
    assert len(result.errors) > 0


@patch(
    "substrate.organism.executors.agent_executor.cpu_gate_check",
    return_value=MagicMock(allowed=True, reason="ok"),
)
@patch("substrate.organism.executors.agent_executor.gated_subprocess_run")
def test_execute_cpu_gate_blocks(mock_run: MagicMock, mock_gate: MagicMock) -> None:
    mock_run.return_value = None  # CPU gate returns None

    ex = _make_executor()
    req = _make_request()
    ex.prepare(req)

    result = ex.execute(req)
    assert not result.success
    assert "CPU gate" in result.outcome


@patch(
    "substrate.organism.executors.agent_executor.cpu_gate_check",
    return_value=MagicMock(allowed=True, reason="ok"),
)
@patch("substrate.organism.executors.agent_executor.gated_subprocess_run")
def test_execute_cancelled_before_start(mock_run: MagicMock, mock_gate: MagicMock) -> None:
    ex = _make_executor()
    req = _make_request()
    ex.prepare(req)
    ex._cancelled.add(req.request_id)

    result = ex.execute(req)
    assert not result.success
    assert "Cancelled" in result.outcome
    mock_run.assert_not_called()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Monitor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_monitor_unknown():
    ex = _make_executor()
    req = _make_request()
    status = ex.monitor(req)
    assert status["status"] == "unknown"
    assert status["agent_backend"] == "claude_code"


@patch(
    "substrate.organism.executors.agent_executor.cpu_gate_check",
    return_value=MagicMock(allowed=True, reason="ok"),
)
def test_monitor_after_prepare(mock_gate: MagicMock) -> None:
    ex = _make_executor()
    req = _make_request()
    ex.prepare(req)
    status = ex.monitor(req)
    assert status["status"] == "prepared"
    assert status["working_dir"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cancel
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@patch(
    "substrate.organism.executors.agent_executor.cpu_gate_check",
    return_value=MagicMock(allowed=True, reason="ok"),
)
def test_cancel(mock_gate: MagicMock) -> None:
    ex = _make_executor()
    req = _make_request()
    ex.prepare(req)
    ok = ex.cancel(req)
    assert ok
    assert req.request_id in ex._cancelled
    status = ex.monitor(req)
    assert status["status"] == "cancelled"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cleanup
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@patch(
    "substrate.organism.executors.agent_executor.cpu_gate_check",
    return_value=MagicMock(allowed=True, reason="ok"),
)
def test_cleanup(mock_gate: MagicMock) -> None:
    ex = _make_executor()
    req = _make_request()
    ex.prepare(req)
    ex.cancel(req)

    ok = ex.cleanup(req)
    assert ok
    assert req.request_id not in ex._active_requests
    assert req.request_id not in ex._cancelled


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Proof
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_proof_to_dict():
    proof = AgentExecutionProof(
        execution_id="ex-1",
        task="test task",
        runtime_snapshot_id="snap-1",
        agent_summary="done",
        commands_run=["pytest"],
        files_changed=["a.py"],
        exit_code=0,
        start_time=1000.0,
        end_time=1005.0,
        duration_ms=5000.0,
        status="success",
    )
    d = proof.to_dict()
    assert d["proof_id"].startswith("agprf-")
    assert d["execution_id"] == "ex-1"
    assert d["exit_code"] == 0
    assert d["duration_ms"] == 5000.0
    assert d["agent_backend"] == "claude_code"


def test_proof_task_truncation():
    proof = AgentExecutionProof(task="x" * 1000)
    d = proof.to_dict()
    assert len(d["task"]) <= 500


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Telemetry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_telemetry_never_raises():
    tel = MagicMock()
    tel.emit.side_effect = Exception("boom")
    ex = _make_executor(telemetry=tel)
    req = _make_request()
    ex._tel("test_event", req, data="test")


def test_telemetry_not_called_without_emitter():
    ex = _make_executor(telemetry=None)
    req = _make_request()
    ex._tel("test_event", req, data="test")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Executor Type Property
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_executor_type_property():
    ex = _make_executor()
    assert ex.executor_type == ExecutorType.AGENT.value
    assert ex.executor_type == "agent"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Route Imports
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_route_module_imports():
    from transports.api.agent_routes import (
        agent_cancel,
        agent_execution_detail,
        agent_executions,
        agent_run,
    )
    assert callable(agent_run)
    assert callable(agent_executions)
    assert callable(agent_execution_detail)
    assert callable(agent_cancel)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_supported_operations():
    assert "run_task" in SUPPORTED_OPERATIONS
    assert "continue_task" not in SUPPORTED_OPERATIONS
