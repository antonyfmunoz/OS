"""Tests for eos_ai.platforms.eos.execution_bridge."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from eos_ai.platforms.eos.execution_bridge import (
    ExecutionBridgeResult,
    execute_created_work_immediately,
)
from eos_ai.substrate.task_system import (
    Task,
    TaskExecutionPolicy,
    TaskStatus,
    TaskStore,
    create_task,
)
from eos_ai.substrate.task_pipeline import PipelineStore
from eos_ai.substrate.station_presence import StationPresenceStore
from eos_ai.substrate.operator_session import OperatorSessionStore


class TestExecutionBridge:
    """ExecutionBridge — immediate execution from EAResponse."""

    def setup_method(self):
        """Reset all singleton stores before each test."""
        TaskStore.reset_default_for_tests()
        PipelineStore.reset_default_for_tests()
        StationPresenceStore.reset_default_for_tests()
        OperatorSessionStore.reset_default_for_tests()

    def teardown_method(self):
        """Clean up singleton stores after each test."""
        TaskStore.reset_default_for_tests()
        PipelineStore.reset_default_for_tests()
        StationPresenceStore.reset_default_for_tests()
        OperatorSessionStore.reset_default_for_tests()

    # ── Result dataclass ───────────────────────────────────────────────────

    def test_result_dataclass(self):
        """ExecutionBridgeResult.to_dict() serializes all fields."""
        r = ExecutionBridgeResult(
            executed_task_ids=["t1"],
            executed_pipeline_ids=["p1"],
            blocked_task_ids=["t2"],
            execution_summaries={"t1": "done"},
            errors={"t3": "not found"},
        )
        d = r.to_dict()
        assert d["executed_task_ids"] == ["t1"]
        assert d["executed_pipeline_ids"] == ["p1"]
        assert d["blocked_task_ids"] == ["t2"]
        assert d["execution_summaries"] == {"t1": "done"}
        assert d["errors"] == {"t3": "not found"}

    # ── Empty input ────────────────────────────────────────────────────────

    def test_empty_input_returns_empty_result(self):
        """No task_ids and no pipeline_ids returns empty result immediately."""
        result = execute_created_work_immediately([], [])
        assert result.executed_task_ids == []
        assert result.executed_pipeline_ids == []
        assert result.blocked_task_ids == []
        assert result.execution_summaries == {}
        assert result.errors == {}

    # ── Autonomous task executes ───────────────────────────────────────────

    def test_autonomous_task_executes(self):
        """An autonomous READY task executes in dry_run mode."""
        task = create_task("build the landing page")
        assert task.execution_policy == TaskExecutionPolicy.AUTONOMOUS
        assert task.status == TaskStatus.READY

        result = execute_created_work_immediately([task.task_id], [], dry_run=True)
        assert task.task_id in result.executed_task_ids
        assert task.task_id not in result.errors
        assert task.task_id in result.execution_summaries

    # ── Non-autonomous task blocked ────────────────────────────────────────

    def test_non_autonomous_task_blocked(self):
        """A needs_operator task is blocked, not executed."""
        # "decide which database migration to deploy" triggers needs_operator
        task = create_task("decide which database migration to deploy")
        assert task.execution_policy == TaskExecutionPolicy.NEEDS_OPERATOR
        assert task.status == TaskStatus.WAITING_ON_OPERATOR

        result = execute_created_work_immediately([task.task_id], [], dry_run=True)
        assert task.task_id in result.blocked_task_ids
        assert task.task_id not in result.executed_task_ids
        assert task.task_id in result.execution_summaries

    # ── Missing task reported as error ─────────────────────────────────────

    def test_missing_task_reported_as_error(self):
        """A nonexistent task ID lands in errors."""
        fake_id = "task_does_not_exist"
        result = execute_created_work_immediately([fake_id], [], dry_run=True)
        assert fake_id in result.errors
        assert result.errors[fake_id] == "task not found"
        assert fake_id not in result.executed_task_ids

    # ── Local-first preference ─────────────────────────────────────────────

    def test_local_first_preference(self):
        """prefer_local=True still executes; local_available comes from station_presence."""
        task = create_task("write unit tests")
        assert task.execution_policy == TaskExecutionPolicy.AUTONOMOUS

        result = execute_created_work_immediately(
            [task.task_id], [], prefer_local=True, dry_run=True
        )
        assert task.task_id in result.executed_task_ids
        assert task.task_id not in result.errors

    # ── to_dict roundtrip ──────────────────────────────────────────────────

    def test_to_dict_roundtrip(self):
        """All fields survive to_dict() serialization."""
        r = ExecutionBridgeResult(
            executed_task_ids=["a", "b"],
            executed_pipeline_ids=["p1"],
            blocked_task_ids=["c"],
            execution_summaries={"a": "ok", "b": "ok", "p1": "ok"},
            errors={"d": "fail"},
        )
        d = r.to_dict()
        assert isinstance(d, dict)
        assert set(d.keys()) == {
            "executed_task_ids",
            "executed_pipeline_ids",
            "blocked_task_ids",
            "execution_summaries",
            "errors",
        }
        assert len(d["executed_task_ids"]) == 2
        assert len(d["executed_pipeline_ids"]) == 1
        assert len(d["blocked_task_ids"]) == 1
        assert len(d["execution_summaries"]) == 3
        assert len(d["errors"]) == 1
