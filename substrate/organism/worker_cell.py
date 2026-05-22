"""Worker cell — bounded task execution through the existing pipeline."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from services.umh.control_plane.pipeline import ExecutionPipeline, PipelineResult
from services.umh.execution.executor import build_default_executor
from services.umh.governance.risk_classes import RiskClass
from substrate.organism.protocols import WorkerSpec
from services.umh.protocols.signal import SignalSource


class WorkerCell:
    def __init__(self, pipeline: ExecutionPipeline | None = None) -> None:
        self._pipeline = pipeline or ExecutionPipeline(executor=build_default_executor())

    def execute(
        self,
        spec: WorkerSpec,
        *,
        adapter_name: str = "shell",
        operation: str = "query",
        params: dict[str, Any] | None = None,
    ) -> PipelineResult:
        try:
            risk = RiskClass[spec.risk_class]
        except KeyError:
            risk = RiskClass.READ_ONLY

        return self._pipeline.submit_signal(
            spec.task,
            source=SignalSource.INTERNAL_EVENT,
            risk_class=risk,
            adapter_name=adapter_name,
            operation=operation,
            params=params or {},
            metadata={
                "worker_cell_id": str(spec.id),
                "parent_agent_id": spec.parent_agent_id,
                "environment_id": spec.environment_id,
                "model_tier": spec.model_tier,
                "parent_trace_id": str(spec.parent_trace_id) if spec.parent_trace_id else None,
            },
        )
