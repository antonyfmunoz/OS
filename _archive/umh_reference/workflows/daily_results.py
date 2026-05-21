"""Phase 88 daily results — capture and manage workflow execution results.

Supports both DailyWorkflowResult (single-track) and WorkflowResult (North Star).

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.workflows.contracts import (
    DailyWorkflowPlan,
    DailyWorkflowResult,
    WorkflowKPIRecord,
    WorkflowResult,
    WorkflowTrack,
    _wf_id,
)


def create_empty_daily_result(plan: DailyWorkflowPlan) -> DailyWorkflowResult:
    return DailyWorkflowResult(
        result_id=_wf_id("result"),
        date=plan.date,
        metadata={"plan_id": plan.plan_id},
    )


def add_completed_task(result: DailyWorkflowResult, task_id: str) -> DailyWorkflowResult:
    if task_id not in result.completed_tasks:
        result.completed_tasks.append(task_id)
    return result


def add_skipped_task(
    result: DailyWorkflowResult,
    task_id: str,
    reason: str = "",
) -> DailyWorkflowResult:
    result.skipped_tasks.append({"task_id": task_id, "reason": reason})
    return result


def add_objection(result: DailyWorkflowResult, objection: str) -> DailyWorkflowResult:
    result.objections.append(objection)
    return result


def add_note(result: DailyWorkflowResult, note: str) -> DailyWorkflowResult:
    result.notes.append(note)
    return result


def add_bottleneck(result: DailyWorkflowResult, bottleneck: str) -> DailyWorkflowResult:
    result.bottlenecks.append(bottleneck)
    return result


def add_win(result: DailyWorkflowResult, win: str) -> DailyWorkflowResult:
    result.wins.append(win)
    return result


def add_loss(result: DailyWorkflowResult, loss: str) -> DailyWorkflowResult:
    result.losses.append(loss)
    return result


def add_kpi_record(
    result: DailyWorkflowResult,
    record: WorkflowKPIRecord,
) -> DailyWorkflowResult:
    result.kpi_records.append(record)
    return result


def daily_result_to_dict(result: DailyWorkflowResult) -> dict[str, Any]:
    return result.to_dict()


# ─── North Star WorkflowResult helpers ──────────────────────────────


def create_empty_workflow_result(
    track: WorkflowTrack,
    plan: DailyWorkflowPlan | None = None,
) -> WorkflowResult:
    date = plan.date if plan else _iso_now()[:10]
    return WorkflowResult(
        result_id=_wf_id("wfresult"),
        date=date,
        track=track,
        metadata={"plan_id": plan.plan_id if plan else ""},
    )


def add_completed_task_to_workflow_result(
    result: WorkflowResult, task_id: str
) -> WorkflowResult:
    if task_id not in result.completed_tasks:
        result.completed_tasks.append(task_id)
    return result


def add_skipped_task_to_workflow_result(
    result: WorkflowResult, task_id: str, reason: str = ""
) -> WorkflowResult:
    result.skipped_tasks.append({"task_id": task_id, "reason": reason})
    return result


def add_kpi_record_to_workflow_result(
    result: WorkflowResult, record: WorkflowKPIRecord
) -> WorkflowResult:
    result.kpi_records.append(record)
    return result


def add_objection_to_workflow_result(
    result: WorkflowResult, objection: str
) -> WorkflowResult:
    result.objections.append(objection)
    return result


def add_note_to_workflow_result(
    result: WorkflowResult, note: str
) -> WorkflowResult:
    result.notes.append(note)
    return result


def add_bottleneck_to_workflow_result(
    result: WorkflowResult, bottleneck: str
) -> WorkflowResult:
    result.bottlenecks.append(bottleneck)
    return result


def add_artifact_to_workflow_result(
    result: WorkflowResult, artifact: str
) -> WorkflowResult:
    result.artifacts.append(artifact)
    return result


def workflow_result_to_dict(result: WorkflowResult) -> dict[str, Any]:
    return result.to_dict()
