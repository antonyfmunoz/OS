"""Phase 88 daily review — build reviews, extract lessons, recommend improvements.

Supports both single-track DailyWorkflowReview and North Star dual-track
WorkflowReview contracts.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from typing import Any

from umh.workflows.contracts import (
    DailyWorkflowPlan,
    DailyWorkflowResult,
    DailyWorkflowReview,
    WorkflowResult,
    WorkflowReview,
    WorkflowTrack,
    _wf_id,
)


def build_daily_workflow_review(
    plan: DailyWorkflowPlan,
    result: DailyWorkflowResult,
) -> DailyWorkflowReview:
    total_tasks = len(plan.tasks)
    completed = len(result.completed_tasks)
    skipped = len(result.skipped_tasks)
    completion_rate = completed / total_tasks if total_tasks > 0 else 0.0

    bottlenecks = identify_bottlenecks(result)
    lessons = extract_lessons_from_result(result)
    template_candidates = identify_template_candidates(result)
    next_actions = recommend_next_day_actions_from_result(result, completion_rate)

    what_worked = list(result.wins) if result.wins else []
    what_failed = list(result.losses) if result.losses else []

    summary_parts = [f"{completed}/{total_tasks} tasks completed"]
    if skipped:
        summary_parts.append(f"{skipped} skipped")
    if result.objections:
        summary_parts.append(f"{len(result.objections)} objections captured")
    if result.bottlenecks:
        summary_parts.append(f"{len(result.bottlenecks)} bottlenecks found")

    recommended_changes: list[str] = []
    if template_candidates:
        recommended_changes.append(f"Template candidates: {', '.join(template_candidates[:3])}")
    if completion_rate < 0.5:
        recommended_changes.append("Reduce task count — plan was too ambitious")
    if not result.objections:
        recommended_changes.append(
            "Capture at least one objection — they improve the sales process"
        )

    return DailyWorkflowReview(
        review_id=_wf_id("review"),
        date=result.date,
        summary=". ".join(summary_parts),
        what_worked=what_worked,
        what_failed=what_failed,
        bottlenecks=bottlenecks,
        lessons=lessons,
        next_actions=next_actions,
        recommended_changes=recommended_changes,
        confidence=completion_rate,
        metadata={
            "plan_id": plan.plan_id,
            "result_id": result.result_id,
            "completion_rate": completion_rate,
            "template_candidates": template_candidates,
        },
    )


def extract_lessons_from_result(result: DailyWorkflowResult) -> list[str]:
    lessons: list[str] = []
    if result.objections:
        lessons.append(
            f"Captured {len(result.objections)} objections — review for content/offer improvement"
        )
    if result.bottlenecks:
        lessons.append(
            f"Found {len(result.bottlenecks)} bottlenecks — address the biggest one first"
        )
    if result.wins:
        lessons.append(f"Wins: {', '.join(result.wins[:3])}")
    if result.losses:
        lessons.append(f"Losses: {', '.join(result.losses[:3])}")
    if not result.completed_tasks:
        lessons.append("No tasks completed — investigate why and simplify tomorrow's plan")
    if result.notes:
        lessons.append(f"{len(result.notes)} notes captured — review for insights")
    return lessons


def recommend_next_day_actions(review: DailyWorkflowReview) -> list[str]:
    actions: list[str] = list(review.next_actions)
    if review.bottlenecks and not any("bottleneck" in a.lower() for a in actions):
        actions.insert(0, f"Address bottleneck: {review.bottlenecks[0]}")
    if review.confidence < 0.5 and not any("simplif" in a.lower() for a in actions):
        actions.append("Simplify tomorrow's plan — fewer tasks, higher leverage")
    return actions


def recommend_next_day_actions_from_result(
    result: DailyWorkflowResult,
    completion_rate: float,
) -> list[str]:
    actions: list[str] = []
    if result.bottlenecks:
        actions.append(f"Fix bottleneck: {result.bottlenecks[0]}")
    if result.losses:
        actions.append(f"Address loss: {result.losses[0]}")
    if completion_rate < 0.5:
        actions.append("Reduce task count or increase time allocation")
    if not result.objections:
        actions.append("Make it a priority to capture objections tomorrow")
    if result.wins:
        actions.append(f"Repeat what worked: {result.wins[0]}")
    if not actions:
        actions.append("Continue the plan — consistency compounds")
    return actions


def identify_bottlenecks(result: DailyWorkflowResult) -> list[str]:
    bottlenecks = list(result.bottlenecks)
    skip_reasons = [s.get("reason", "") for s in result.skipped_tasks if s.get("reason")]
    for reason in skip_reasons:
        entry = f"Skipped task reason: {reason}"
        if entry not in bottlenecks:
            bottlenecks.append(entry)
    if not result.completed_tasks and not result.skipped_tasks:
        bottlenecks.append("No tasks completed or skipped — possible planning or motivation issue")
    return bottlenecks


def identify_template_candidates(result: DailyWorkflowResult) -> list[str]:
    candidates: list[str] = []
    if len(result.completed_tasks) >= 3:
        candidates.append("Daily task checklist — enough tasks completed to templatize")
    if result.objections:
        candidates.append("Objection capture template — standardize collection")
    if result.bottlenecks:
        candidates.append("Bottleneck tracker template — track patterns over time")
    if result.kpi_records:
        candidates.append("KPI recording template — standardize daily metrics capture")
    return candidates


# ─── North Star WorkflowResult-based review ─────────────────────────


def build_workflow_review(
    result: WorkflowResult,
    track: WorkflowTrack = WorkflowTrack.UNKNOWN,
) -> WorkflowReview:
    completed = len(result.completed_tasks)
    skipped = len(result.skipped_tasks)
    total = completed + skipped
    completion_rate = completed / total if total > 0 else 0.0

    bottlenecks = _identify_workflow_bottlenecks(result)
    lessons = extract_lessons_from_workflow_result(result)
    next_actions = _recommend_workflow_next_actions(result, completion_rate)

    summary_parts = [f"{completed} tasks completed"]
    if skipped:
        summary_parts.append(f"{skipped} skipped")
    if result.objections:
        summary_parts.append(f"{len(result.objections)} objections captured")
    if result.bottlenecks:
        summary_parts.append(f"{len(result.bottlenecks)} bottlenecks found")

    recommended_changes: list[str] = []
    if completion_rate < 0.5 and total > 0:
        recommended_changes.append("Reduce task count — plan was too ambitious")
    if track == WorkflowTrack.BUSINESS_REVENUE and not result.objections:
        recommended_changes.append("Capture at least one objection tomorrow")
    if track == WorkflowTrack.SELF_BUILD and not result.artifacts:
        recommended_changes.append("Ensure build produces at least one artifact (report, test, code)")

    return WorkflowReview(
        review_id=_wf_id("wfreview"),
        date=result.date,
        track=track,
        summary=". ".join(summary_parts),
        what_worked=list(result.wins),
        what_failed=list(result.losses),
        bottlenecks=bottlenecks,
        lessons=lessons,
        next_actions=next_actions,
        recommended_changes=recommended_changes,
        template_candidates=[],
        confidence=completion_rate,
        metadata={
            "result_id": result.result_id,
            "completion_rate": completion_rate,
        },
    )


def build_business_workflow_review(
    plan: DailyWorkflowPlan,
    result: WorkflowResult,
) -> WorkflowReview:
    return build_workflow_review(result, WorkflowTrack.BUSINESS_REVENUE)


def build_self_build_workflow_review(
    plan: DailyWorkflowPlan,
    result: WorkflowResult,
) -> WorkflowReview:
    return build_workflow_review(result, WorkflowTrack.SELF_BUILD)


def extract_lessons_from_workflow_result(result: WorkflowResult) -> list[str]:
    lessons: list[str] = []
    if result.objections:
        lessons.append(
            f"Captured {len(result.objections)} objections — review for improvement"
        )
    if result.bottlenecks:
        lessons.append(
            f"Found {len(result.bottlenecks)} bottlenecks — address the biggest one first"
        )
    if result.wins:
        lessons.append(f"Wins: {', '.join(result.wins[:3])}")
    if result.losses:
        lessons.append(f"Losses: {', '.join(result.losses[:3])}")
    if not result.completed_tasks:
        lessons.append("No tasks completed — investigate and simplify plan")
    if result.notes:
        lessons.append(f"{len(result.notes)} notes captured — review for insights")
    return lessons


def identify_workflow_bottlenecks(result: WorkflowResult) -> list[str]:
    return _identify_workflow_bottlenecks(result)


def identify_workflow_system_gaps(result: WorkflowResult) -> list[str]:
    gaps: list[str] = []
    if not result.completed_tasks:
        gaps.append("No tasks completed — system may not support this workflow")
    if not result.kpi_records:
        gaps.append("No KPIs recorded — tracking integration missing")
    if result.bottlenecks:
        for b in result.bottlenecks[:3]:
            gaps.append(f"Bottleneck gap: {b}")
    return gaps


def identify_workflow_template_candidates(result: WorkflowResult) -> list[str]:
    candidates: list[str] = []
    if len(result.completed_tasks) >= 3:
        candidates.append("Task checklist template")
    if result.objections:
        candidates.append("Objection response template")
    if result.bottlenecks:
        candidates.append("Bottleneck tracker template")
    if result.kpi_records:
        candidates.append("KPI recording template")
    return candidates


def _identify_workflow_bottlenecks(result: WorkflowResult) -> list[str]:
    bottlenecks = list(result.bottlenecks)
    skip_reasons = [s.get("reason", "") for s in result.skipped_tasks if s.get("reason")]
    for reason in skip_reasons:
        entry = f"Skipped: {reason}"
        if entry not in bottlenecks:
            bottlenecks.append(entry)
    if not result.completed_tasks and not result.skipped_tasks:
        bottlenecks.append("No tasks completed or skipped")
    return bottlenecks


def _recommend_workflow_next_actions(
    result: WorkflowResult,
    completion_rate: float,
) -> list[str]:
    actions: list[str] = []
    if result.bottlenecks:
        actions.append(f"Fix bottleneck: {result.bottlenecks[0]}")
    if result.losses:
        actions.append(f"Address loss: {result.losses[0]}")
    if completion_rate < 0.5:
        actions.append("Reduce task count or increase time allocation")
    if result.wins:
        actions.append(f"Repeat what worked: {result.wins[0]}")
    if not actions:
        actions.append("Continue the plan — consistency compounds")
    return actions
