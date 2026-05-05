"""Tests for UMH CLI — phase 6c.

Exercises the CLI as a real subprocess to verify exit codes,
output formatting, and JSON mode.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

_CLI = [sys.executable, "-m", "umh.control.cli"]
_CWD = "/opt/OS"


def _run(*args: str, **kwargs) -> subprocess.CompletedProcess:
    """Run the CLI with given args and return the result."""
    return subprocess.run(
        [*_CLI, *args],
        capture_output=True,
        text=True,
        cwd=_CWD,
        timeout=30,
        env={
            **__import__("os").environ,
            "UMH_APPROVAL_BACKEND": "memory",
            "PYTEST_CURRENT_TEST": "1",
        },
        **kwargs,
    )


class TestPlanCommand:
    """Tests for the 'plan' subcommand."""

    def test_plan_valid_input_exits_zero(self):
        result = _run("plan", "check system health")
        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
        assert "Plan:" in result.stdout
        assert "Status:" in result.stdout

    def test_plan_json_returns_valid_json(self):
        result = _run("plan", "check system health", "--json")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert "plan_id" in data
        assert "status" in data
        assert "steps" in data

    def test_plan_vague_input_exits_one(self):
        result = _run("plan", "do something")
        assert result.returncode == 1, (
            f"Expected exit 1 for vague input, got {result.returncode}\nstdout: {result.stdout}"
        )


class TestExecuteCommand:
    """Tests for the 'execute' subcommand."""

    def test_execute_valid_template_exits_zero(self):
        result = _run("execute", "check system health")
        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
        assert "Executing..." in result.stdout or '"task"' in result.stdout

    def test_execute_json_returns_task_id(self):
        result = _run("execute", "check system health", "--json")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert "task" in data
        if data["task"] is not None:
            assert "id" in data["task"]


class TestTaskCommands:
    """Tests for task and tasks subcommands."""

    def test_tasks_exits_zero(self):
        result = _run("tasks")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_task_missing_id_exits_nonzero(self):
        result = _run("task", "nonexistent_task_id_12345")
        assert result.returncode != 0


class TestApprovalsCommand:
    """Tests for the 'approvals' subcommand."""

    def test_approvals_exits_zero(self):
        result = _run("approvals")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        # Either "No pending approvals." or a list
        assert result.stdout.strip()


class TestEdgeCases:
    """Tests for error handling and edge cases."""

    def test_invalid_subcommand_exits_nonzero(self):
        result = _run("bogus_command")
        assert result.returncode != 0

    def test_no_subcommand_exits_nonzero(self):
        result = _run()
        assert result.returncode != 0

    def test_no_direct_execution_bypass(self):
        """Verify cli.py does not call execution engine directly."""
        cli_path = "/opt/OS/umh/control/cli.py"
        with open(cli_path) as f:
            source = f.read()

        forbidden = [
            "from umh.execution.engine import execute",
            "from umh.execution.engine import lightweight_execute",
            "engine.execute(",
            "lightweight_execute(",
        ]
        for pattern in forbidden:
            assert pattern not in source, (
                f"CLI must not bypass the planning layer. Found: {pattern}"
            )
