"""tests for worker cell — bounded task execution via the pipeline."""

import pytest
from substrate.organism.protocols import WorkerSpec
from substrate.organism.worker_cell import WorkerCell


def test_worker_executes_shell_read():
    spec = WorkerSpec(
        parent_agent_id="researcher-001",
        task="list python files in services/umh/organism/",
        environment_id="vps-prod",
        tools=["shell"],
        model_tier="sonnet",
        risk_class="READ_ONLY",
        timeout_s=30.0,
    )
    cell = WorkerCell()
    result = cell.execute(
        spec,
        adapter_name="shell",
        operation="query",
        params={
            "command": "ls /opt/OS/services/umh/organism/*.py 2>/dev/null | head -5",
        },
    )
    assert result.executed is True
    assert result.trace_id is not None


def test_worker_returns_failure_on_bad_adapter():
    spec = WorkerSpec(
        parent_agent_id="researcher-001",
        task="test bad adapter",
        environment_id="vps-prod",
        tools=[],
        risk_class="READ_ONLY",
    )
    cell = WorkerCell()
    result = cell.execute(spec, adapter_name="nonexistent_adapter", operation="query", params={})
    assert result.executed is False or result.success is False


def test_worker_result_has_trace_id():
    spec = WorkerSpec(
        parent_agent_id="test-agent",
        task="simple test",
        environment_id="vps-prod",
        tools=["shell"],
        risk_class="READ_ONLY",
    )
    cell = WorkerCell()
    result = cell.execute(
        spec,
        adapter_name="shell",
        operation="query",
        params={
            "command": "echo hello",
        },
    )
    assert result.trace_id is not None
    assert isinstance(str(result.trace_id), str)
