"""tests for worker cell — bounded task execution."""

import pytest
from substrate.organism.protocols import WorkerSpec
from substrate.organism.worker_cell import WorkerCell
from substrate.execution.pipeline import PipelineResult


def test_worker_executes_without_spine():
    spec = WorkerSpec(
        parent_agent_id="researcher-001",
        task="list python files",
        environment_id="vps-prod",
        tools=["shell"],
        model_tier="sonnet",
        risk_class="READ_ONLY",
        timeout_s=30.0,
    )
    cell = WorkerCell()
    result = cell.execute(spec, adapter_name="shell", operation="query")
    assert isinstance(result, PipelineResult)
    assert result.success is True
    assert result.trace_id is not None


def test_worker_result_has_trace_id():
    spec = WorkerSpec(
        parent_agent_id="test-agent",
        task="simple test",
        environment_id="vps-prod",
        tools=["shell"],
        risk_class="READ_ONLY",
    )
    cell = WorkerCell()
    result = cell.execute(spec, adapter_name="shell", operation="query")
    assert result.trace_id is not None
    assert isinstance(str(result.trace_id), str)
