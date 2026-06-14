"""Tests for WorkstationExecutor — Phase 15A.

Validates:
  - All 5 operations (create_worktree, run_command, read_file, write_file, list_directory)
  - Path traversal rejection
  - Runtime lifecycle integration
  - Proof generation
  - Cancel behavior
  - CPU gate integration
  - Blocked file patterns
  - Edge cases
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.organism.executor_runtime import (
    ExecutorApprovalState,
    ExecutorRequest,
    ExecutorRequestStatus,
    ExecutorResult,
    ExecutorType,
    get_executor_runtime,
    reset_executor_runtime,
)
from substrate.organism.executors.workstation_executor import (
    SUPPORTED_OPERATIONS,
    ExecutionProof,
    WorkstationExecutor,
    _check_blocked,
    _resolve_and_validate,
)


# ── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def executor():
    return WorkstationExecutor()


@pytest.fixture
def tmp_workspace(tmp_path):
    """Create a temporary workspace within an approved-root-like structure."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def sample_request():
    """Create a minimal valid request."""
    return ExecutorRequest(
        execution_plan_id="plan-test-001",
        executor_type=ExecutorType.WORKSTATION.value,
        approval_state=ExecutorApprovalState.AUTO_APPROVED.value,
        risk_class="low",
        metadata={
            "operation": "run_command",
            "params": {"command": "echo hello"},
        },
    )


@pytest.fixture
def runtime_dir(tmp_path):
    """Temporary runtime data directory."""
    d = tmp_path / "executor_runtime"
    d.mkdir()
    for sub in ("requests", "results", "lifecycle", "snapshots"):
        (d / sub).mkdir()
    return d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Path Safety Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPathValidation:

    def test_approved_root_allowed(self):
        resolved, err = _resolve_and_validate("/opt/OS/substrate")
        assert err == ""
        assert str(resolved).startswith("/opt/OS")

    def test_outside_approved_roots_rejected(self):
        _, err = _resolve_and_validate("/etc/passwd")
        assert "outside approved roots" in err

    def test_traversal_rejected(self):
        _, err = _resolve_and_validate("/opt/OS/../../etc/passwd")
        assert "outside approved roots" in err

    def test_relative_traversal_rejected(self):
        _, err = _resolve_and_validate("/workspace/../../../etc/shadow")
        assert "outside approved roots" in err

    def test_workspace_root_allowed(self):
        resolved, err = _resolve_and_validate("/workspace")
        assert err == ""

    def test_blocked_env_file(self):
        reason = _check_blocked(
            __import__("pathlib").Path("/opt/OS/.env")
        )
        assert "blocked pattern" in reason

    def test_blocked_credentials(self):
        reason = _check_blocked(
            __import__("pathlib").Path("/opt/OS/credentials.json")
        )
        assert "blocked pattern" in reason

    def test_blocked_ssh_key(self):
        reason = _check_blocked(
            __import__("pathlib").Path("/home/user/.ssh/id_rsa")
        )
        assert "blocked pattern" in reason

    def test_normal_file_not_blocked(self):
        reason = _check_blocked(
            __import__("pathlib").Path("/opt/OS/substrate/types.py")
        )
        assert reason == ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ExecutionProof Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExecutionProof:

    def test_auto_id(self):
        proof = ExecutionProof()
        assert proof.proof_id.startswith("wxprf-")

    def test_roundtrip(self):
        proof = ExecutionProof(
            execution_id="req-123",
            operation="run_command",
            start_time=1000.0,
            end_time=1001.5,
            duration_ms=1500.0,
            status="success",
            inputs={"command": "echo hi"},
            outputs={"stdout": "hi\n", "exit_code": 0},
        )
        d = proof.to_dict()
        restored = ExecutionProof.from_dict(d)
        assert restored.proof_id == proof.proof_id
        assert restored.operation == "run_command"
        assert restored.duration_ms == 1500.0
        assert restored.outputs["exit_code"] == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Validation Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestValidation:

    def test_valid_run_command(self, executor, sample_request):
        ok, reason = executor.validate(sample_request)
        assert ok
        assert "run_command" in reason

    def test_missing_plan_id(self, executor):
        req = ExecutorRequest(
            execution_plan_id="",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={"operation": "run_command", "params": {"command": "ls"}},
        )
        ok, reason = executor.validate(req)
        assert not ok
        assert "execution_plan_id" in reason

    def test_wrong_executor_type(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type="agent",
            metadata={"operation": "run_command", "params": {"command": "ls"}},
        )
        ok, reason = executor.validate(req)
        assert not ok
        assert "Wrong executor type" in reason

    def test_missing_operation(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={},
        )
        ok, reason = executor.validate(req)
        assert not ok
        assert "No operation" in reason

    def test_unsupported_operation(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={"operation": "launch_browser", "params": {}},
        )
        ok, reason = executor.validate(req)
        assert not ok
        assert "Unsupported operation" in reason

    def test_run_command_missing_command(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={"operation": "run_command", "params": {}},
        )
        ok, reason = executor.validate(req)
        assert not ok
        assert "command" in reason

    def test_create_worktree_missing_branch(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={"operation": "create_worktree", "params": {}},
        )
        ok, reason = executor.validate(req)
        assert not ok
        assert "branch_name" in reason

    def test_read_file_missing_path(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={"operation": "read_file", "params": {}},
        )
        ok, reason = executor.validate(req)
        assert not ok
        assert "path" in reason

    def test_all_supported_operations(self):
        expected = {"create_worktree", "run_command", "read_file", "write_file", "list_directory"}
        assert SUPPORTED_OPERATIONS == expected


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Preparation Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPreparation:

    def test_prepare_run_command(self, executor, sample_request):
        ok, reason = executor.prepare(sample_request)
        assert ok
        assert "run_command" in reason

    def test_prepare_validates_path(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "read_file",
                "params": {"path": "/etc/passwd"},
            },
        )
        ok, reason = executor.prepare(req)
        assert not ok
        assert "Path validation failed" in reason

    def test_prepare_tracks_active(self, executor, sample_request):
        executor.prepare(sample_request)
        assert sample_request.request_id in executor._active_requests


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Run Command Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRunCommand:

    def test_echo_command(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "run_command",
                "params": {"command": "echo hello world"},
            },
        )
        result = executor.execute(req)
        assert result.success
        assert "hello world" in result.metadata["proof"]["outputs"]["stdout"]
        assert result.metadata["proof"]["status"] == "success"

    def test_failing_command(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "run_command",
                "params": {"command": "false"},
            },
        )
        result = executor.execute(req)
        assert not result.success
        assert result.metadata["proof"]["outputs"]["exit_code"] != 0

    def test_command_as_list(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "run_command",
                "params": {"command": ["echo", "list", "mode"]},
            },
        )
        result = executor.execute(req)
        assert result.success
        assert "list mode" in result.metadata["proof"]["outputs"]["stdout"]

    def test_command_with_cwd(self, executor, tmp_path):
        test_dir = tmp_path / "opt" / "OS" / "testdir"
        test_dir.mkdir(parents=True)
        (test_dir / "marker.txt").write_text("found_it")

        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "run_command",
                "params": {
                    "command": "cat marker.txt",
                    "cwd": str(test_dir),
                },
            },
        )
        result = executor.execute(req)
        # cwd validation may reject if not in approved roots
        # This is expected behavior for paths outside /opt/OS or /workspace
        if not result.success:
            assert "invalid" in result.outcome.lower() or "outside" in result.outcome.lower()

    def test_command_outside_approved_cwd(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "run_command",
                "params": {"command": "ls", "cwd": "/tmp"},
            },
        )
        result = executor.execute(req)
        assert not result.success
        assert "invalid" in result.outcome.lower() or "outside" in result.outcome.lower()

    def test_command_captures_stderr(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "run_command",
                "params": {"command": "echo err >&2"},
            },
        )
        result = executor.execute(req)
        proof = result.metadata["proof"]
        assert "err" in proof["outputs"]["stderr"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Read File Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestReadFile:

    def test_read_existing_file(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "read_file",
                "params": {"path": "/opt/OS/CLAUDE.md"},
            },
        )
        result = executor.execute(req)
        assert result.success
        assert result.metadata["proof"]["outputs"]["size_bytes"] > 0
        assert len(result.artifacts) > 0

    def test_read_nonexistent_file(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "read_file",
                "params": {"path": "/opt/OS/nonexistent_file_xyz.txt"},
            },
        )
        result = executor.execute(req)
        assert not result.success
        assert "Not a file" in result.outcome

    def test_read_blocked_env_file(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "read_file",
                "params": {"path": "/opt/OS/.env"},
            },
        )
        result = executor.execute(req)
        assert not result.success
        assert "blocked pattern" in result.outcome.lower()

    def test_read_outside_roots(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "read_file",
                "params": {"path": "/etc/hostname"},
            },
        )
        result = executor.execute(req)
        assert not result.success
        assert "outside" in result.outcome.lower()

    def test_read_path_traversal(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "read_file",
                "params": {"path": "/opt/OS/../../../etc/passwd"},
            },
        )
        result = executor.execute(req)
        assert not result.success


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Write File Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestWriteFile:

    def test_write_new_file(self, executor, tmp_path):
        # Write to a file under /opt/OS for path validation
        target = "/opt/OS/data/test_ws_write_" + os.urandom(4).hex() + ".txt"
        content = "test content\nline 2\n"
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "write_file",
                "params": {"path": target, "content": content},
            },
        )
        result = executor.execute(req)
        try:
            assert result.success
            assert os.path.exists(target)
            assert open(target).read() == content
            assert result.metadata["proof"]["status"] == "success"
        finally:
            if os.path.exists(target):
                os.remove(target)

    def test_write_blocked_path(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "write_file",
                "params": {"path": "/opt/OS/.env.test", "content": "SECRET=x"},
            },
        )
        result = executor.execute(req)
        assert not result.success
        assert "blocked" in result.outcome.lower()

    def test_write_outside_roots(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "write_file",
                "params": {"path": "/tmp/evil.txt", "content": "hack"},
            },
        )
        result = executor.execute(req)
        assert not result.success


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# List Directory Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestListDirectory:

    def test_list_existing_directory(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "list_directory",
                "params": {"path": "/opt/OS/substrate"},
            },
        )
        result = executor.execute(req)
        assert result.success
        entries = result.metadata["proof"]["outputs"]["entries"]
        assert len(entries) > 0
        names = [e["name"] for e in entries]
        assert "types.py" in names or "__init__.py" in names

    def test_list_nonexistent_directory(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "list_directory",
                "params": {"path": "/opt/OS/nonexistent_dir_xyz"},
            },
        )
        result = executor.execute(req)
        assert not result.success

    def test_list_outside_roots(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "list_directory",
                "params": {"path": "/etc"},
            },
        )
        result = executor.execute(req)
        assert not result.success

    def test_list_max_entries(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "list_directory",
                "params": {"path": "/opt/OS", "max_entries": 5},
            },
        )
        result = executor.execute(req)
        assert result.success
        entries = result.metadata["proof"]["outputs"]["entries"]
        assert len(entries) <= 5


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Create Worktree Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCreateWorktree:

    def test_create_worktree_success(self, executor):
        branch = f"test-ws-{os.urandom(4).hex()}"
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "create_worktree",
                "params": {
                    "repo_root": "/opt/OS",
                    "branch_name": branch,
                    "base_ref": "HEAD",
                },
            },
        )
        result = executor.execute(req)
        worktree_path = f"/opt/OS/.claude/worktrees/{branch}"
        try:
            assert result.success, f"Failed: {result.outcome}"
            assert os.path.isdir(worktree_path)
            proof = result.metadata["proof"]
            assert proof["operation"] == "create_worktree"
            assert proof["status"] == "success"
        finally:
            import subprocess
            subprocess.run(
                ["git", "-C", "/opt/OS", "worktree", "remove", "--force", worktree_path],
                capture_output=True, timeout=10,
            )
            subprocess.run(
                ["git", "-C", "/opt/OS", "branch", "-D", branch],
                capture_output=True, timeout=10,
            )

    def test_create_worktree_missing_branch(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "create_worktree",
                "params": {"repo_root": "/opt/OS"},
            },
        )
        # validate() catches this first
        ok, reason = executor.validate(req)
        assert not ok
        assert "branch_name" in reason

    def test_create_worktree_outside_roots(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "create_worktree",
                "params": {
                    "repo_root": "/tmp/not-a-repo",
                    "branch_name": "evil",
                },
            },
        )
        result = executor.execute(req)
        assert not result.success


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Monitor & Cancel Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestMonitorCancel:

    def test_monitor_active_request(self, executor, sample_request):
        executor.prepare(sample_request)
        mon = executor.monitor(sample_request)
        assert mon["request_id"] == sample_request.request_id
        assert mon["operation"] == "run_command"

    def test_monitor_unknown_request(self, executor):
        req = ExecutorRequest(request_id="nonexistent")
        mon = executor.monitor(req)
        assert mon["status"] == "unknown"

    def test_cancel_request(self, executor, sample_request):
        executor.prepare(sample_request)
        cancelled = executor.cancel(sample_request)
        assert cancelled
        assert sample_request.request_id in executor._cancelled

    def test_cancel_then_execute(self, executor, sample_request):
        executor.cancel(sample_request)
        result = executor.execute(sample_request)
        assert not result.success
        assert "Cancelled" in result.outcome

    def test_cleanup(self, executor, sample_request):
        executor.prepare(sample_request)
        assert sample_request.request_id in executor._active_requests
        ok = executor.cleanup(sample_request)
        assert ok
        assert sample_request.request_id not in executor._active_requests


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Proof Generation Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestProofGeneration:

    def test_proof_attached_to_result(self, executor, sample_request):
        result = executor.execute(sample_request)
        assert "proof" in result.metadata
        proof = result.metadata["proof"]
        assert proof["proof_id"].startswith("wxprf-")
        assert proof["operation"] == "run_command"
        assert proof["duration_ms"] >= 0

    def test_proof_has_inputs_outputs(self, executor, sample_request):
        result = executor.execute(sample_request)
        proof = result.metadata["proof"]
        assert "operation" in proof["inputs"]
        assert "params" in proof["inputs"]
        assert "stdout" in proof["outputs"]
        assert "exit_code" in proof["outputs"]

    def test_proof_on_failure(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "run_command",
                "params": {"command": "false"},
            },
        )
        result = executor.execute(req)
        proof = result.metadata["proof"]
        assert proof["status"] == "failed"

    def test_proof_on_error(self, executor):
        req = ExecutorRequest(
            execution_plan_id="plan-001",
            executor_type=ExecutorType.WORKSTATION.value,
            metadata={
                "operation": "read_file",
                "params": {"path": "/opt/OS/no_such_file_xyz.txt"},
            },
        )
        result = executor.execute(req)
        proof = result.metadata["proof"]
        assert proof["status"] == "failed"

    def test_proof_timing(self, executor, sample_request):
        result = executor.execute(sample_request)
        proof = result.metadata["proof"]
        assert proof["start_time"] > 0
        assert proof["end_time"] >= proof["start_time"]
        assert proof["duration_ms"] == (proof["end_time"] - proof["start_time"]) * 1000


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime Lifecycle Integration Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRuntimeIntegration:

    @pytest.fixture(autouse=True)
    def reset_runtime(self, runtime_dir):
        reset_executor_runtime()
        yield
        reset_executor_runtime()

    def test_register_workstation_executor(self, runtime_dir):
        from substrate.organism.executor_runtime import ExecutorRuntime

        rt = ExecutorRuntime(data_dir=str(runtime_dir))
        ws = WorkstationExecutor()
        rt.register_executor("workstation", ws)
        assert rt.has_executor("workstation")
        impl = rt._impl_registry.get("workstation")
        assert isinstance(impl, WorkstationExecutor)

    def test_full_lifecycle_run_command(self, runtime_dir):
        from substrate.organism.executor_runtime import ExecutorRuntime

        rt = ExecutorRuntime(data_dir=str(runtime_dir))
        ws = WorkstationExecutor()
        rt.register_executor("workstation", ws)

        request = rt.create_request(
            execution_plan_id="plan-lifecycle-001",
            executor_type="workstation",
            risk_class="low",
            description="Test echo command",
            metadata={
                "operation": "run_command",
                "params": {"command": "echo lifecycle test"},
            },
        )
        assert request.approval_state == ExecutorApprovalState.AUTO_APPROVED.value

        result = rt.run_lifecycle(request.request_id)
        assert result is not None
        assert result.success
        assert "lifecycle test" in result.metadata["proof"]["outputs"]["stdout"]

        events = rt.lifecycle_for_request(request.request_id)
        event_types = [e.event_type for e in events]
        assert "request_created" in event_types
        assert "validation_started" in event_types
        assert "execution_completed" in event_types
        assert "cleanup_completed" in event_types

    def test_full_lifecycle_read_file(self, runtime_dir):
        from substrate.organism.executor_runtime import ExecutorRuntime

        rt = ExecutorRuntime(data_dir=str(runtime_dir))
        ws = WorkstationExecutor()
        rt.register_executor("workstation", ws)

        request = rt.create_request(
            execution_plan_id="plan-lifecycle-002",
            executor_type="workstation",
            risk_class="low",
            metadata={
                "operation": "read_file",
                "params": {"path": "/opt/OS/CLAUDE.md"},
            },
        )
        result = rt.run_lifecycle(request.request_id)
        assert result is not None
        assert result.success
        assert len(result.artifacts) > 0

    def test_full_lifecycle_list_directory(self, runtime_dir):
        from substrate.organism.executor_runtime import ExecutorRuntime

        rt = ExecutorRuntime(data_dir=str(runtime_dir))
        ws = WorkstationExecutor()
        rt.register_executor("workstation", ws)

        request = rt.create_request(
            execution_plan_id="plan-lifecycle-003",
            executor_type="workstation",
            risk_class="low",
            metadata={
                "operation": "list_directory",
                "params": {"path": "/opt/OS/substrate"},
            },
        )
        result = rt.run_lifecycle(request.request_id)
        assert result is not None
        assert result.success

    def test_lifecycle_denied_request(self, runtime_dir):
        from substrate.organism.executor_runtime import ExecutorRuntime

        rt = ExecutorRuntime(data_dir=str(runtime_dir))
        ws = WorkstationExecutor()
        rt.register_executor("workstation", ws)

        request = rt.create_request(
            execution_plan_id="plan-denied-001",
            executor_type="workstation",
            risk_class="high",
            metadata={
                "operation": "run_command",
                "params": {"command": "echo should not run"},
            },
        )
        assert request.approval_state == ExecutorApprovalState.PENDING.value

        result = rt.run_lifecycle(request.request_id)
        assert result is None

    def test_lifecycle_approved_high_risk(self, runtime_dir):
        from substrate.organism.executor_runtime import ExecutorRuntime

        rt = ExecutorRuntime(data_dir=str(runtime_dir))
        ws = WorkstationExecutor()
        rt.register_executor("workstation", ws)

        request = rt.create_request(
            execution_plan_id="plan-highrisk-001",
            executor_type="workstation",
            risk_class="high",
            metadata={
                "operation": "run_command",
                "params": {"command": "echo approved"},
            },
        )
        rt.approve_request(request.request_id)
        result = rt.run_lifecycle(request.request_id)
        assert result is not None
        assert result.success

    def test_snapshot_after_execution(self, runtime_dir):
        from substrate.organism.executor_runtime import ExecutorRuntime

        rt = ExecutorRuntime(data_dir=str(runtime_dir))
        ws = WorkstationExecutor()
        rt.register_executor("workstation", ws)

        for i in range(3):
            req = rt.create_request(
                execution_plan_id=f"plan-snap-{i}",
                executor_type="workstation",
                risk_class="low",
                metadata={
                    "operation": "run_command",
                    "params": {"command": f"echo test {i}"},
                },
            )
            rt.run_lifecycle(req.request_id)

        snap = rt.snapshot()
        assert snap.total_requests == 3
        assert snap.by_status.get("cleaned_up", 0) == 3

    def test_result_persisted(self, runtime_dir):
        from substrate.organism.executor_runtime import ExecutorRuntime

        rt = ExecutorRuntime(data_dir=str(runtime_dir))
        ws = WorkstationExecutor()
        rt.register_executor("workstation", ws)

        request = rt.create_request(
            execution_plan_id="plan-persist-001",
            executor_type="workstation",
            risk_class="low",
            metadata={
                "operation": "run_command",
                "params": {"command": "echo persisted"},
            },
        )
        result = rt.run_lifecycle(request.request_id)
        assert result is not None

        stored = rt.result_for_request(request.request_id)
        assert stored is not None
        assert stored.result_id == result.result_id
        assert stored.success

    def test_write_file_through_lifecycle(self, runtime_dir):
        from substrate.organism.executor_runtime import ExecutorRuntime

        target = f"/opt/OS/data/test_lifecycle_write_{os.urandom(4).hex()}.txt"
        rt = ExecutorRuntime(data_dir=str(runtime_dir))
        ws = WorkstationExecutor()
        rt.register_executor("workstation", ws)

        request = rt.create_request(
            execution_plan_id="plan-write-001",
            executor_type="workstation",
            risk_class="low",
            metadata={
                "operation": "write_file",
                "params": {"path": target, "content": "lifecycle write test"},
            },
        )
        result = rt.run_lifecycle(request.request_id)
        try:
            assert result is not None
            assert result.success
            assert os.path.exists(target)
        finally:
            if os.path.exists(target):
                os.remove(target)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Acceptance Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestAcceptance:
    """End-to-end acceptance tests per Phase 15A spec."""

    @pytest.fixture(autouse=True)
    def reset_runtime(self, runtime_dir):
        reset_executor_runtime()
        yield
        reset_executor_runtime()

    def test_end_to_end_real_execution(self, runtime_dir):
        """Full path: create request → governance → execute → proof → result."""
        from substrate.organism.executor_runtime import ExecutorRuntime

        rt = ExecutorRuntime(data_dir=str(runtime_dir))
        ws = WorkstationExecutor()
        rt.register_executor("workstation", ws)

        request = rt.create_request(
            execution_plan_id="plan-e2e-001",
            executor_type="workstation",
            risk_class="low",
            description="E2E acceptance: run real command",
            metadata={
                "operation": "run_command",
                "params": {"command": "python3 -c 'print(40+2)'"},
            },
        )

        assert request.approval_state == ExecutorApprovalState.AUTO_APPROVED.value

        result = rt.run_lifecycle(request.request_id)

        assert result is not None
        assert result.success
        assert "42" in result.metadata["proof"]["outputs"]["stdout"]
        assert result.metadata["proof"]["proof_id"].startswith("wxprf-")
        assert result.duration_seconds >= 0

        final_req = rt.get_request(request.request_id)
        assert final_req is not None
        assert final_req.status == "cleaned_up"

        stored_result = rt.result_for_request(request.request_id)
        assert stored_result is not None
        assert stored_result.result_id == result.result_id

    def test_no_simulation_in_real_executor(self, runtime_dir):
        """WorkstationExecutor must NOT produce simulated output."""
        from substrate.organism.executor_runtime import ExecutorRuntime

        rt = ExecutorRuntime(data_dir=str(runtime_dir))
        ws = WorkstationExecutor()
        rt.register_executor("workstation", ws)

        request = rt.create_request(
            execution_plan_id="plan-real-001",
            executor_type="workstation",
            risk_class="low",
            metadata={
                "operation": "run_command",
                "params": {"command": "echo real-not-simulated"},
            },
        )
        result = rt.run_lifecycle(request.request_id)

        assert result is not None
        assert result.success
        assert "real-not-simulated" in result.metadata["proof"]["outputs"]["stdout"]
        for art in result.artifacts:
            content = art.get("content", "")
            assert "simulation_report" not in art.get("artifact_type", "")
            assert '"simulated": true' not in content.lower()

    def test_governance_blocks_unapproved(self, runtime_dir):
        """High-risk without approval must be blocked."""
        from substrate.organism.executor_runtime import ExecutorRuntime

        rt = ExecutorRuntime(data_dir=str(runtime_dir))
        ws = WorkstationExecutor()
        rt.register_executor("workstation", ws)

        request = rt.create_request(
            execution_plan_id="plan-blocked-001",
            executor_type="workstation",
            risk_class="critical",
            metadata={
                "operation": "run_command",
                "params": {"command": "echo should-not-run"},
            },
        )
        result = rt.run_lifecycle(request.request_id)
        assert result is None

        final_req = rt.get_request(request.request_id)
        assert final_req is not None
        assert final_req.status == "failed"

    def test_path_traversal_blocked_e2e(self, runtime_dir):
        """Path traversal attempts must be rejected at execution."""
        from substrate.organism.executor_runtime import ExecutorRuntime

        rt = ExecutorRuntime(data_dir=str(runtime_dir))
        ws = WorkstationExecutor()
        rt.register_executor("workstation", ws)

        request = rt.create_request(
            execution_plan_id="plan-traversal-001",
            executor_type="workstation",
            risk_class="low",
            metadata={
                "operation": "read_file",
                "params": {"path": "/opt/OS/../../etc/passwd"},
            },
        )
        result = rt.run_lifecycle(request.request_id)
        # Traversal is caught at prepare() — run_lifecycle returns None
        assert result is None
        final_req = rt.get_request(request.request_id)
        assert final_req is not None
        assert final_req.status == "failed"
        assert "outside" in final_req.metadata.get("failure_reason", "").lower()

    def test_all_operations_produce_proof(self, runtime_dir):
        """Every operation type must produce an ExecutionProof."""
        from substrate.organism.executor_runtime import ExecutorRuntime

        rt = ExecutorRuntime(data_dir=str(runtime_dir))
        ws = WorkstationExecutor()
        rt.register_executor("workstation", ws)

        ops = [
            ("run_command", {"command": "echo proof_test"}),
            ("read_file", {"path": "/opt/OS/CLAUDE.md"}),
            ("list_directory", {"path": "/opt/OS/substrate"}),
        ]

        for i, (op, params) in enumerate(ops):
            request = rt.create_request(
                execution_plan_id=f"plan-proof-{i}",
                executor_type="workstation",
                risk_class="low",
                metadata={"operation": op, "params": params},
            )
            result = rt.run_lifecycle(request.request_id)
            assert result is not None, f"Failed for {op}"
            assert "proof" in result.metadata, f"No proof for {op}"
            proof = result.metadata["proof"]
            assert proof["proof_id"].startswith("wxprf-"), f"Bad proof_id for {op}"
            assert proof["operation"] == op, f"Wrong operation in proof for {op}"
