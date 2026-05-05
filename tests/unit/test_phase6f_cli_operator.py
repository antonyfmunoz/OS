"""Tests for Phase 6F Agent 3: CLI Operator UX Upgrade.

Covers:
1. TestPlanCommand — upgraded plan output with quality/explanation
2. TestRunCommand — combined plan+execute flow
3. TestWatchCommand — watch on terminal-state tasks (in-process)
4. TestTaskCommand — task uses summary format (or fallback)
5. TestNoBypass — run command does not bypass execution engine
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase6f")
os.environ["UMH_TASK_BACKEND"] = "memory"
os.environ["UMH_APPROVAL_BACKEND"] = "memory"

import pytest

from umh.control.cli import main as cli_main
from umh.events.stream import reset_event_stream
from umh.orchestrator.task import (
    Task,
    TaskStatus,
    TaskStep,
    _save_task,
    execute_task,
    get_task,
    reset_tasks,
)
from umh.orchestrator.task_store import InMemoryTaskBackend, reset_task_store

_CLI = [sys.executable, "-m", "umh.control.cli"]
_CWD = "/opt/OS"


def _subprocess_run(*args: str, **kwargs) -> subprocess.CompletedProcess:
    """Run the CLI as subprocess."""
    return subprocess.run(
        [*_CLI, *args],
        capture_output=True,
        text=True,
        cwd=_CWD,
        timeout=30,
        env={
            **os.environ,
            "UMH_APPROVAL_BACKEND": "memory",
            "UMH_TASK_BACKEND": "memory",
            "UMH_API_KEY": "test-key-phase6f",
            "PYTEST_CURRENT_TEST": "1",
        },
        **kwargs,
    )


def _cli_capture(*argv: str) -> tuple[int, str]:
    """Run CLI main() in-process and capture stdout. Returns (exit_code, stdout)."""
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        rc = cli_main(list(argv))
    except SystemExit as e:
        rc = e.code if e.code is not None else 0
    finally:
        sys.stdout = old_stdout
    return rc, buf.getvalue()


def _reset():
    reset_event_stream()
    reset_tasks()
    reset_task_store(backend=InMemoryTaskBackend())


# ── 1. TestPlanCommand ───────────────────────────────────────────


class TestPlanCommand:
    """Plan command shows quality, explanation, and validation info."""

    def test_plan_shows_quality_and_explanation(self):
        result = _subprocess_run("plan", "check system health")
        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
        assert "Plan:" in result.stdout
        assert "Quality:" in result.stdout
        assert "Objective:" in result.stdout
        assert "Executable:" in result.stdout

    def test_plan_shows_validation_status(self):
        result = _subprocess_run("plan", "check system health")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Validation:" in result.stdout

    def test_plan_shows_steps(self):
        result = _subprocess_run("plan", "check system health")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Steps:" in result.stdout

    def test_plan_json_is_valid_json(self):
        result = _subprocess_run("plan", "check system health", "--json")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert "plan_id" in data
        assert "status" in data
        assert "steps" in data

    def test_plan_json_has_quality(self):
        result = _subprocess_run("plan", "check system health", "--json")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert "quality" in data
        assert "verdict" in data["quality"]
        assert "score" in data["quality"]

    def test_plan_json_has_explanation(self):
        result = _subprocess_run("plan", "check system health", "--json")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert "explanation" in data
        assert "assumptions" in data["explanation"]
        assert "risks" in data["explanation"]

    def test_plan_rejected_shows_reason(self):
        result = _subprocess_run("plan", "do something")
        assert result.returncode == 1
        assert "Executable: no" in result.stdout

    def test_plan_rejected_json(self):
        result = _subprocess_run("plan", "do something", "--json")
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["status"] == "rejected"


# ── 2. TestRunCommand ────────────────────────────────────────────


class TestRunCommand:
    """Run command combines plan + execute."""

    def test_run_valid_creates_task(self):
        result = _subprocess_run("run", "check system health")
        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
        assert "Task:" in result.stdout
        assert "Inspect:" in result.stdout

    def test_run_json_returns_task(self):
        result = _subprocess_run("run", "check system health", "--json")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert "task" in data
        if data["task"] is not None:
            assert "id" in data["task"]

    def test_run_invalid_exits_nonzero(self):
        result = _subprocess_run("run", "do something")
        assert result.returncode != 0, f"Expected nonzero exit\nstdout: {result.stdout}"

    def test_run_invalid_json_has_error(self):
        result = _subprocess_run("run", "do something", "--json")
        assert result.returncode != 0
        data = json.loads(result.stdout)
        assert "error" in data

    def test_run_shows_plan_brief(self):
        """Run shows abbreviated plan info before executing."""
        result = _subprocess_run("run", "check system health")
        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
        assert "Plan:" in result.stdout
        assert "Quality:" in result.stdout


# ── 3. TestWatchCommand (in-process) ─────────────────────────────


class TestWatchCommand:
    """Watch command polls and exits on terminal states.

    Uses in-process CLI calls so the task store is shared.
    """

    def setup_method(self):
        _reset()

    def test_watch_completed_task_exits_zero(self):
        """Execute a task in-process, then watch it."""
        task = Task(
            steps=[TaskStep(operation="noop", inputs_template={"x": "1"})],
            issued_by="test-cli",
        )
        execute_task(task)
        assert task.status == TaskStatus.COMPLETED

        rc, stdout = _cli_capture("watch", task.id, "--timeout", "5")
        assert rc == 0, f"stdout: {stdout}"

    def test_watch_completed_json(self):
        """Watch --json on completed task returns valid JSON with status."""
        task = Task(
            steps=[TaskStep(operation="noop", inputs_template={"x": "1"})],
            issued_by="test-cli",
        )
        execute_task(task)

        rc, stdout = _cli_capture("watch", task.id, "--timeout", "5", "--json")
        assert rc == 0
        data = json.loads(stdout)
        assert data["status"] == "completed"

    def test_watch_cancelled_task_exits_zero(self):
        """Watch on a cancelled task exits 0."""
        from umh.orchestrator.task import cancel_task, enqueue_task

        task = Task(
            steps=[TaskStep(operation="noop")],
            issued_by="test-cli",
        )
        enqueue_task(task)
        cancel_task(task.id)

        rc, stdout = _cli_capture("watch", task.id, "--timeout", "5")
        assert rc == 0

    def test_watch_nonexistent_task_exits_one(self):
        rc, stdout = _cli_capture("watch", "task_nonexistent_xyz", "--timeout", "5")
        assert rc == 1
        assert "not found" in stdout.lower()

    def test_watch_nonexistent_json(self):
        rc, stdout = _cli_capture("watch", "task_nonexistent_xyz", "--timeout", "5", "--json")
        assert rc == 1
        data = json.loads(stdout)
        assert "error" in data


# ── 4. TestTaskCommand (in-process) ──────────────────────────────


class TestTaskCommand:
    """Task command uses summary format."""

    def setup_method(self):
        _reset()

    def test_task_format_has_status(self):
        """Execute a task, then query it via CLI."""
        task = Task(
            steps=[TaskStep(operation="noop", inputs_template={"x": "1"})],
            issued_by="test-cli",
        )
        execute_task(task)

        rc, stdout = _cli_capture("task", task.id)
        assert rc == 0, f"stdout: {stdout}"
        assert "Task:" in stdout
        assert "Status:" in stdout

    def test_task_json_valid(self):
        """Task --json returns valid JSON."""
        task = Task(
            steps=[TaskStep(operation="noop", inputs_template={"x": "1"})],
            issued_by="test-cli",
        )
        execute_task(task)

        rc, stdout = _cli_capture("task", task.id, "--json")
        assert rc == 0
        data = json.loads(stdout)
        # May have {"task": ..., "summary": ...} or just the task dict
        assert "id" in data or "task" in data

    def test_task_missing_exits_one(self):
        rc, stdout = _cli_capture("task", "task_missing_abc")
        assert rc == 1


# ── 5. TestNoBypass ──────────────────────────────────────────────


class TestNoBypass:
    """CLI must not bypass execution engine."""

    def test_run_command_no_direct_execution(self):
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

    def test_run_uses_execute_plan(self):
        """Verify that cmd_run imports execute_plan from planner."""
        cli_path = "/opt/OS/umh/control/cli.py"
        with open(cli_path) as f:
            source = f.read()

        assert "execute_plan" in source, "cmd_run must use execute_plan()"
        assert "create_plan_from_raw" in source, "cmd_run must use create_plan_from_raw()"


# ── 6. TestAllCommandsHaveJson ───────────────────────────────────


class TestAllCommandsHaveJson:
    """Every subcommand supports --json."""

    def test_plan_json_flag(self):
        result = _subprocess_run("plan", "check system health", "--json")
        data = json.loads(result.stdout)
        assert isinstance(data, dict)

    def test_run_json_flag(self):
        result = _subprocess_run("run", "check system health", "--json")
        data = json.loads(result.stdout)
        assert isinstance(data, dict)

    def test_execute_json_flag(self):
        result = _subprocess_run("execute", "check system health", "--json")
        data = json.loads(result.stdout)
        assert isinstance(data, dict)

    def test_tasks_json_flag(self):
        result = _subprocess_run("tasks", "--json")
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_approvals_json_flag(self):
        result = _subprocess_run("approvals", "--json")
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_timeline_json_flag(self):
        # Timeline with nonexistent task returns JSON error
        result = _subprocess_run("timeline", "task_xyz", "--json")
        data = json.loads(result.stdout)
        assert isinstance(data, (dict, list))
