"""WorkflowRunner — executes multi-step workflows through governed mutation.

Every step in a workflow is submitted as a governed mutation. The runner
tracks outcomes, dispatches a completion report, and emits learning signals.

This is an EOS projection module. It imports from transports/api/ (governed
mutation wrapper) and substrate/ (report dispatcher, outcome learning).
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from projections.eos.workflows.types import (
    StepResult,
    WorkflowResult,
    WorkflowStep,
)
from substrate.organism.report_dispatcher import (
    DispatchResult,
    Report,
    ReportDispatcher,
)
from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


def _runtime_state_file(subsystem: str, filename: str) -> str:
    from substrate.state.runtime_paths import runtime_state_path

    return str(runtime_state_path(subsystem, filename, create_parent=False))


_JOURNAL_PATH = _runtime_state_file("organism", "execution_journal.jsonl")


def _journal_append(entry: dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(_JOURNAL_PATH), exist_ok=True)
        with open(_JOURNAL_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as exc:
        logger.debug("journal write failed: %s", exc)


class WorkflowRunner:
    """Executes multi-step workflows through governed mutation."""

    def __init__(
        self,
        org_id: str = "",
        venture_id: str = "",
        dispatcher: ReportDispatcher | None = None,
    ) -> None:
        self._org_id = org_id
        self._venture_id = venture_id
        self._dispatcher = dispatcher

    def run(
        self,
        workflow_name: str,
        steps: list[WorkflowStep],
        source: str = "discord",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """Execute a workflow — each step goes through governed_mutation."""
        start = time.monotonic()
        meta = metadata or {}
        step_results: list[StepResult] = []
        failed = False

        _journal_append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": "workflow_start",
                "workflow": workflow_name,
                "steps": len(steps),
                "source": source,
                "org_id": self._org_id,
            }
        )

        for step in steps:
            if failed and not step.skip_on_failure:
                step_results.append(
                    StepResult(
                        step_name=step.name,
                        success=False,
                        skipped=True,
                        output="skipped — prior step failed",
                    )
                )
                continue

            result = self._execute_step(step, workflow_name, source)
            step_results.append(result)

            if not result.success and not result.skipped:
                failed = True

        elapsed = time.monotonic() - start
        completed = sum(1 for r in step_results if r.success)

        wf_result = WorkflowResult(
            workflow_name=workflow_name,
            steps_completed=completed,
            steps_total=len(steps),
            success=not failed,
            step_results=step_results,
            duration_seconds=round(elapsed, 2),
            source=source,
            metadata=meta,
        )

        _journal_append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": "workflow_complete",
                "workflow": workflow_name,
                "success": wf_result.success,
                "steps_completed": completed,
                "steps_total": len(steps),
                "duration_seconds": wf_result.duration_seconds,
            }
        )

        self._dispatch_report(wf_result)

        return wf_result

    def _execute_step(
        self,
        step: WorkflowStep,
        workflow_name: str,
        source: str,
    ) -> StepResult:
        step_meta = {
            "workflow": workflow_name,
            "step": step.name,
            **step.metadata,
        }

        try:
            response = governed_mutation(
                mutation_name=step.mutation_name,
                intent=step.intent,
                execute_fn=step.execute_fn,
                source=source,
                metadata=step_meta,
            )
            return StepResult(
                step_name=step.name,
                success=response.success,
                output=response.output,
                envelope_id=response.envelope_id,
            )
        except Exception as exc:
            logger.error(
                "workflow %s step %s failed: %s",
                workflow_name,
                step.name,
                exc,
            )
            return StepResult(
                step_name=step.name,
                success=False,
                error=str(exc),
            )

    def _dispatch_report(self, result: WorkflowResult) -> DispatchResult | None:
        if self._dispatcher is None:
            return None

        status = "COMPLETE" if result.success else "FAILED"
        step_lines = []
        for sr in result.step_results:
            icon = "+" if sr.success else ("-" if sr.skipped else "x")
            line = f"  {icon} {sr.step_name}"
            if sr.output:
                line += f": {sr.output[:120]}"
            elif sr.error:
                line += f": ERROR — {sr.error[:120]}"
            elif sr.skipped:
                line += " (skipped)"
            step_lines.append(line)

        body = (
            f"# Workflow: {result.workflow_name}\n\n"
            f"**Status**: {status}\n"
            f"**Steps**: {result.steps_completed}/{result.steps_total}\n"
            f"**Duration**: {result.duration_seconds:.1f}s\n"
            f"**Source**: {result.source}\n\n"
            f"## Step Results\n\n" + "\n".join(step_lines)
        )

        report = Report(
            title=f"Workflow {status}: {result.workflow_name}",
            summary=result.summary(),
            body=body,
            metadata={"workflow_result": result.to_dict()},
        )

        try:
            return self._dispatcher.dispatch_report(report)
        except Exception as exc:
            logger.error("report dispatch failed: %s", exc)
            return None
