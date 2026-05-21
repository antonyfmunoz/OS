"""
UMH Execution Pipeline — composable, ordered stage execution.

The pipeline takes an ordered list of ``ExecutionStage`` instances and
executes them sequentially, passing a shared ``StageContext`` through
each stage.  Stages can be injected, removed, or replaced without
modifying the pipeline runner.

Usage:
    from umh.execution.pipeline import ExecutionPipeline
    from umh.execution.stages import StageContext

    pipeline = ExecutionPipeline([stage1, stage2, stage3])
    context = StageContext(message="hello", ...)
    context = pipeline.run(context)
    print(context.response)

The pipeline validates dependency ordering at construction time and
raises ``ValueError`` if any stage's declared dependencies would run
after it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from umh.core.clock import now_ms as _now_ms
from umh.execution.stages import ExecutionStage, StageContext, StageResult

_log = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Outcome of a full pipeline execution."""

    context: StageContext
    stage_results: list[StageResult] = field(default_factory=list)
    total_ms: int = 0
    aborted_at: str | None = None


class ExecutionPipeline:
    """Ordered, composable execution pipeline."""

    def __init__(self, stages: list[ExecutionStage]) -> None:
        self._stages = list(stages)
        self._validate_order()

    @property
    def stages(self) -> list[ExecutionStage]:
        return list(self._stages)

    @property
    def stage_names(self) -> list[str]:
        return [s.name for s in self._stages]

    def run(self, context: StageContext) -> PipelineResult:
        """Execute all stages sequentially, returning a PipelineResult."""
        results: list[StageResult] = []
        pipeline_start = _now_ms()

        for stage in self._stages:
            if context.aborted:
                break

            stage_start = _now_ms()
            error: str | None = None
            try:
                context = stage.run(context)
            except Exception as e:
                error = str(e)
                _log.error("Stage '%s' raised: %s", stage.name, e)
                context.stage_errors[stage.name] = error
                if stage.can_abort:
                    context.aborted = True
                    context.abort_result = f"Stage {stage.name} failed: {e}"

            elapsed = _now_ms() - stage_start
            context.stage_timings[stage.name] = elapsed
            results.append(
                StageResult(
                    name=stage.name,
                    elapsed_ms=elapsed,
                    error=error,
                    aborted=context.aborted,
                )
            )

        return PipelineResult(
            context=context,
            stage_results=results,
            total_ms=_now_ms() - pipeline_start,
            aborted_at=results[-1].name if context.aborted and results else None,
        )

    def insert_before(self, target: str, stage: ExecutionStage) -> ExecutionPipeline:
        """Return a new pipeline with ``stage`` inserted before ``target``."""
        new_stages = []
        found = False
        for s in self._stages:
            if s.name == target:
                new_stages.append(stage)
                found = True
            new_stages.append(s)
        if not found:
            raise ValueError(f"Target stage '{target}' not found in pipeline")
        return ExecutionPipeline(new_stages)

    def insert_after(self, target: str, stage: ExecutionStage) -> ExecutionPipeline:
        """Return a new pipeline with ``stage`` inserted after ``target``."""
        new_stages = []
        found = False
        for s in self._stages:
            new_stages.append(s)
            if s.name == target:
                new_stages.append(stage)
                found = True
        if not found:
            raise ValueError(f"Target stage '{target}' not found in pipeline")
        return ExecutionPipeline(new_stages)

    def remove(self, name: str) -> ExecutionPipeline:
        """Return a new pipeline without the named stage."""
        new_stages = [s for s in self._stages if s.name != name]
        if len(new_stages) == len(self._stages):
            raise ValueError(f"Stage '{name}' not found in pipeline")
        return ExecutionPipeline(new_stages)

    def replace(self, name: str, stage: ExecutionStage) -> ExecutionPipeline:
        """Return a new pipeline with the named stage replaced."""
        new_stages = []
        found = False
        for s in self._stages:
            if s.name == name:
                new_stages.append(stage)
                found = True
            else:
                new_stages.append(s)
        if not found:
            raise ValueError(f"Stage '{name}' not found in pipeline")
        return ExecutionPipeline(new_stages)

    def _validate_order(self) -> None:
        """Verify that every stage's dependencies appear before it."""
        seen: set[str] = set()
        for stage in self._stages:
            for dep in stage.dependencies:
                if dep not in seen:
                    raise ValueError(
                        f"Stage '{stage.name}' depends on '{dep}' which "
                        f"has not been seen yet. Current order: {self.stage_names}"
                    )
            seen.add(stage.name)
