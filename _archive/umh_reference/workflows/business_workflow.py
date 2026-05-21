"""North Star business workflow — Personal Brand to Initiate Arena Revenue Loop.

Re-exports the existing first_workflow and adds track-aware task generation
for the integrated North Star test harness.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from typing import Any

from umh.workflows.contracts import (
    WorkflowDefinition,
    WorkflowStage,
    WorkflowTask,
    WorkflowTrack,
    _wf_id,
)
from umh.workflows.first_workflow import (
    build_personal_brand_to_initiate_arena_workflow as _build_base,
)


def build_personal_brand_to_initiate_arena_workflow() -> WorkflowDefinition:
    wf = _build_base()
    wf.track = WorkflowTrack.BUSINESS_REVENUE
    return wf


def generate_business_test_tasks(
    context: dict[str, Any] | None = None,
) -> list[WorkflowTask]:
    return [
        WorkflowTask(
            task_id=_wf_id("btask"),
            track=WorkflowTrack.BUSINESS_REVENUE,
            stage=WorkflowStage.CONTENT_STRATEGY,
            title="Pick one Initiate Arena content angle",
            description="Choose a topic aligned to Initiate Arena avatar pain or aspiration.",
            priority="high",
            estimated_minutes=15,
            leverage_type="content_media",
            owner="antony",
            manual_only=True,
            expected_output="One content angle written down",
        ),
        WorkflowTask(
            task_id=_wf_id("btask"),
            track=WorkflowTrack.BUSINESS_REVENUE,
            stage=WorkflowStage.CONTENT_PRODUCTION,
            title="Draft one short-form post or script",
            description="Write the post, reel script, or caption. Ship speed > polish.",
            priority="high",
            estimated_minutes=30,
            leverage_type="content_media",
            owner="antony",
            manual_only=True,
            expected_output="One draft ready to publish",
        ),
        WorkflowTask(
            task_id=_wf_id("btask"),
            track=WorkflowTrack.BUSINESS_REVENUE,
            stage=WorkflowStage.PUBLISHING,
            title="Manually publish or prepare post",
            description="Post to primary platform(s). Manual publish is fine.",
            priority="high",
            estimated_minutes=10,
            leverage_type="distribution",
            owner="antony",
            manual_only=True,
            expected_output="One post published or scheduled",
        ),
        WorkflowTask(
            task_id=_wf_id("btask"),
            track=WorkflowTrack.BUSINESS_REVENUE,
            stage=WorkflowStage.DM_CONVERSATION,
            title="Manually engage/comment/DM 5-20 prospects",
            description="Open genuine conversations. No pitching in first message.",
            priority="high",
            estimated_minutes=60,
            leverage_type="human",
            owner="antony",
            manual_only=True,
            expected_output="5-20 conversations opened",
        ),
        WorkflowTask(
            task_id=_wf_id("btask"),
            track=WorkflowTrack.BUSINESS_REVENUE,
            stage=WorkflowStage.DM_CONVERSATION,
            title="Record conversations opened",
            description="Track new and advanced conversations count.",
            priority="medium",
            estimated_minutes=5,
            leverage_type="data",
            owner="antony",
            manual_only=True,
            expected_output="Conversation count recorded",
        ),
        WorkflowTask(
            task_id=_wf_id("btask"),
            track=WorkflowTrack.BUSINESS_REVENUE,
            stage=WorkflowStage.ENGAGEMENT_CAPTURE,
            title="Capture objections heard today",
            description="Write down every objection, hesitation, or concern.",
            priority="high",
            estimated_minutes=10,
            leverage_type="knowledge",
            owner="antony",
            manual_only=True,
            expected_output="List of objections captured",
        ),
        WorkflowTask(
            task_id=_wf_id("btask"),
            track=WorkflowTrack.BUSINESS_REVENUE,
            stage=WorkflowStage.LEAD_CAPTURE,
            title="Record leads qualified today",
            description="How many prospects moved to lead status?",
            priority="medium",
            estimated_minutes=10,
            leverage_type="data",
            owner="antony",
            manual_only=True,
            expected_output="Qualified lead count recorded",
        ),
        WorkflowTask(
            task_id=_wf_id("btask"),
            track=WorkflowTrack.BUSINESS_REVENUE,
            stage=WorkflowStage.SALES_CONVERSATION,
            title="Attempt to book call or advance to next step",
            description="For qualified leads, try to book a call or move toward decision.",
            priority="high",
            estimated_minutes=20,
            leverage_type="human",
            owner="antony",
            manual_only=True,
            expected_output="Calls booked or next steps set",
        ),
        WorkflowTask(
            task_id=_wf_id("btask"),
            track=WorkflowTrack.BUSINESS_REVENUE,
            stage=WorkflowStage.END_OF_DAY_REVIEW,
            title="Record bottlenecks encountered",
            description="Capture what blocked or slowed progress today.",
            priority="high",
            estimated_minutes=5,
            leverage_type="knowledge",
            owner="antony",
            manual_only=True,
            expected_output="Bottleneck list recorded",
        ),
        WorkflowTask(
            task_id=_wf_id("btask"),
            track=WorkflowTrack.BUSINESS_REVENUE,
            stage=WorkflowStage.END_OF_DAY_REVIEW,
            title="Run end-of-day review",
            description="Fill in the daily result template. Be honest.",
            priority="high",
            estimated_minutes=15,
            leverage_type="knowledge",
            owner="antony",
            manual_only=True,
            expected_output="Completed daily review",
        ),
    ]
