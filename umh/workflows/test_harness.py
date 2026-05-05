"""Phase 88 test harness — build plans, capture results, run reviews.

Operator-assisted execution. The system tells the user what to do,
tracks what happened, and learns from the result.

No execution. No external calls. No scraping. No DMs. No posting.
"""

from __future__ import annotations

from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.workflows.contracts import (
    DailyWorkflowPlan,
    DailyWorkflowResult,
    DailyWorkflowReview,
    KPIName,
    WorkflowStage,
    WorkflowStatus,
    WorkflowTask,
    _wf_id,
)
from umh.workflows.first_workflow import build_personal_brand_to_initiate_arena_workflow
from umh.workflows.kpis import build_default_kpis_for_first_workflow
from umh.workflows.review import build_daily_workflow_review


def build_first_workflow_test_plan(
    date: str | None = None,
    context: dict[str, Any] | None = None,
) -> DailyWorkflowPlan:
    if date is None:
        date = _iso_now()[:10]
    workflow = build_personal_brand_to_initiate_arena_workflow()
    tasks = generate_daily_tasks_for_first_workflow(context)
    tasks = apply_leverage_to_workflow_tasks(tasks, context)
    kpis = build_default_kpis_for_first_workflow()
    kpi_names = [k.kpi_name.value for k in kpis]

    return DailyWorkflowPlan(
        plan_id=_wf_id("plan"),
        date=date,
        workflow=workflow,
        tasks=tasks,
        kpis_to_track=kpi_names,
        highest_leverage_actions=[
            "DM 5-20 prospects — direct revenue path",
            "Publish one piece of content — feeds the top of funnel",
            "Follow up with existing leads — highest close probability",
            "Capture and document objections — improves sales process",
        ],
        non_actions=[
            "Do NOT redesign the website today",
            "Do NOT build new features in EOS today",
            "Do NOT research new tools or platforms",
            "Do NOT optimize content strategy without publishing first",
            "Do NOT work on Game of Lyfe",
        ],
        risks=[
            "Perfectionism delays publishing",
            "Outreach avoidance disguised as preparation",
            "Tool research instead of outreach",
            "Building instead of selling",
        ],
        metadata={"version": "v1", "context": context or {}},
    )


def generate_daily_tasks_for_first_workflow(
    context: dict[str, Any] | None = None,
) -> list[WorkflowTask]:
    return [
        WorkflowTask(
            task_id=_wf_id("task"),
            stage=WorkflowStage.CONTENT_STRATEGY,
            title="Choose one content angle for Initiate Arena",
            description="Pick a topic that speaks to your ideal client's pain or aspiration. Tie it to the Initiate Arena offer.",
            priority="high",
            estimated_minutes=15,
            leverage_type="content_media",
            owner="antony",
            expected_output="One content angle written down",
        ),
        WorkflowTask(
            task_id=_wf_id("task"),
            stage=WorkflowStage.CONTENT_PRODUCTION,
            title="Draft one short-form post or script",
            description="Write the post, reel script, or caption. Don't overthink. Ship speed > polish.",
            priority="high",
            estimated_minutes=30,
            leverage_type="content_media",
            owner="antony",
            expected_output="One draft ready to publish",
        ),
        WorkflowTask(
            task_id=_wf_id("task"),
            stage=WorkflowStage.PUBLISHING,
            title="Publish or prepare the post manually",
            description="Post to Instagram, TikTok, X, or wherever your audience is. Manual is fine.",
            priority="high",
            estimated_minutes=10,
            leverage_type="distribution",
            owner="antony",
            expected_output="One post published or scheduled",
        ),
        WorkflowTask(
            task_id=_wf_id("task"),
            stage=WorkflowStage.DM_CONVERSATION,
            title="Identify and DM 5-20 prospects",
            description="Find people who engaged with your content or fit your avatar. Open genuine conversations. No pitching in first message.",
            priority="high",
            estimated_minutes=60,
            leverage_type="human",
            owner="antony",
            expected_output="5-20 conversations opened",
        ),
        WorkflowTask(
            task_id=_wf_id("task"),
            stage=WorkflowStage.DM_CONVERSATION,
            title="Record number of conversations opened",
            description="Track how many new conversations you opened and how many existing ones you advanced.",
            priority="medium",
            estimated_minutes=5,
            leverage_type="data",
            owner="antony",
            expected_output="Conversation count recorded",
        ),
        WorkflowTask(
            task_id=_wf_id("task"),
            stage=WorkflowStage.ENGAGEMENT_CAPTURE,
            title="Capture objections heard today",
            description="Write down every objection, hesitation, or concern you heard. These are gold for improving the offer and content.",
            priority="high",
            estimated_minutes=10,
            leverage_type="knowledge",
            owner="antony",
            expected_output="List of objections captured",
        ),
        WorkflowTask(
            task_id=_wf_id("task"),
            stage=WorkflowStage.LEAD_CAPTURE,
            title="Record leads qualified today",
            description="How many prospects moved from conversation to lead status? Add to CRM or spreadsheet.",
            priority="medium",
            estimated_minutes=10,
            leverage_type="data",
            owner="antony",
            expected_output="Qualified lead count recorded",
        ),
        WorkflowTask(
            task_id=_wf_id("task"),
            stage=WorkflowStage.SALES_CONVERSATION,
            title="Attempt to book call or advance to next step",
            description="For qualified leads, try to book a call or move the conversation toward a decision. Don't force — just ask.",
            priority="high",
            estimated_minutes=20,
            leverage_type="human",
            owner="antony",
            expected_output="Calls booked or next steps set",
        ),
        WorkflowTask(
            task_id=_wf_id("task"),
            stage=WorkflowStage.END_OF_DAY_REVIEW,
            title="Review today's results",
            description="Fill in the daily result template. Be honest. What worked, what didn't, what should change.",
            priority="high",
            estimated_minutes=15,
            leverage_type="knowledge",
            owner="antony",
            expected_output="Completed daily review",
        ),
        WorkflowTask(
            task_id=_wf_id("task"),
            stage=WorkflowStage.END_OF_DAY_REVIEW,
            title="Create next-day improvement recommendation",
            description="Based on today's review, write one specific thing to do differently tomorrow.",
            priority="medium",
            estimated_minutes=5,
            leverage_type="systems_process",
            owner="antony",
            expected_output="One improvement recommendation",
        ),
    ]


def apply_leverage_to_workflow_tasks(
    tasks: list[WorkflowTask],
    context: dict[str, Any] | None = None,
) -> list[WorkflowTask]:
    leverage_priority = {
        "human": 1,
        "distribution": 2,
        "content_media": 3,
        "knowledge": 4,
        "data": 5,
        "systems_process": 6,
    }
    for task in tasks:
        lev = task.leverage_type
        if lev in leverage_priority:
            task.metadata["leverage_priority"] = leverage_priority[lev]
        else:
            task.metadata["leverage_priority"] = 99
    return sorted(tasks, key=lambda t: t.metadata.get("leverage_priority", 99))


def build_manual_result_capture_template(plan: DailyWorkflowPlan) -> dict[str, Any]:
    task_entries = []
    for t in plan.tasks:
        task_entries.append(
            {
                "task_id": t.task_id,
                "title": t.title,
                "status": "planned",
                "result": "",
            }
        )
    return {
        "plan_id": plan.plan_id,
        "date": plan.date,
        "tasks": task_entries,
        "kpis": {k: 0 for k in plan.kpis_to_track},
        "objections": [],
        "notes": [],
        "bottlenecks": [],
        "wins": [],
        "losses": [],
    }


def validate_daily_result(result: DailyWorkflowResult) -> dict[str, Any]:
    warnings: list[str] = []
    if not result.date:
        warnings.append("Result has no date")
    if not result.completed_tasks and not result.skipped_tasks:
        warnings.append("No tasks completed or skipped — result may be empty")
    if not result.kpi_records:
        warnings.append("No KPI records captured")
    return {"valid": len(warnings) == 0, "warnings": warnings}


def run_manual_workflow_review(
    plan: DailyWorkflowPlan,
    result: DailyWorkflowResult,
) -> DailyWorkflowReview:
    return build_daily_workflow_review(plan, result)


def build_next_day_recommendations(review: DailyWorkflowReview) -> list[str]:
    recommendations: list[str] = []
    if review.bottlenecks:
        recommendations.append(f"Address top bottleneck: {review.bottlenecks[0]}")
    if review.what_failed:
        recommendations.append(f"Fix or skip: {review.what_failed[0]}")
    if not review.what_worked:
        recommendations.append(
            "Nothing noted as working — try to identify at least one win tomorrow"
        )
    else:
        recommendations.append(f"Double down on: {review.what_worked[0]}")
    for action in review.next_actions:
        if action not in recommendations:
            recommendations.append(action)
    if not recommendations:
        recommendations.append("Continue executing the same plan — consistency compounds")
    return recommendations
