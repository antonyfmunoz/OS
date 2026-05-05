"""Phase 88 first workflow — Personal Brand → Initiate Arena Revenue Loop.

Encodes the 16-stage revenue loop from docs/strategy/first_operating_workflow.md
into typed WorkflowDefinition/WorkflowStageDefinition contracts consumable by
the test harness, daily plan builder, and review system.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from umh.workflows.contracts import (
    KPIName,
    WorkflowDefinition,
    WorkflowStage,
    WorkflowStageDefinition,
    _wf_id,
)


def build_personal_brand_to_initiate_arena_workflow() -> WorkflowDefinition:
    stages = _build_stages()
    kpis = [k.value for k in KPIName if k != KPIName.UNKNOWN]
    return WorkflowDefinition(
        workflow_id=_wf_id("wkfl"),
        name="Personal Brand → Initiate Arena Revenue Loop",
        purpose=(
            "Generate $10K/month net profit through content-led outreach, "
            "lead capture, qualification, sales conversations, and Initiate Arena "
            "fulfillment. This is the binding constraint workflow."
        ),
        stages=stages,
        primary_company="lyfe_institute",
        product="initiate_arena",
        owner="antony",
        success_criteria=[
            "$10K/month net profit from Initiate Arena",
            "Repeatable content → lead → close pipeline",
            "Documented objections and sales process",
            "Fulfillment system that produces testimonials",
            "Weekly improvement loop operational",
        ],
        kpis=kpis,
        metadata={
            "version": "v1",
            "source": "docs/strategy/first_operating_workflow.md",
            "entities_touched": [
                "personal_brand",
                "lyfe_institute",
                "empyrean_studio",
                "ost",
            ],
        },
    )


def _build_stages() -> list[WorkflowStageDefinition]:
    return [
        WorkflowStageDefinition(
            stage=WorkflowStage.CONTENT_STRATEGY,
            name="Content Strategy",
            objective="Choose content angle that attracts Initiate Arena prospects",
            expected_output="One content angle or hook for today's post",
            kpi=KPIName.POSTS_PUBLISHED.value,
            common_bottlenecks=[
                "No clear avatar defined",
                "Perfectionism — overplanning instead of posting",
                "Not tied to offer",
            ],
            notes="Content IS advertising. Every post should attract the right person.",
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.CONTENT_PRODUCTION,
            name="Content Production",
            objective="Draft one short-form post, reel, or script",
            expected_output="One draft ready to publish or record",
            kpi=KPIName.POSTS_PUBLISHED.value,
            common_bottlenecks=[
                "Perfectionism — endless editing",
                "No batch process",
                "Equipment/tool friction",
            ],
            notes="Speed > polish at this stage. Ship daily.",
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.PUBLISHING,
            name="Publishing",
            objective="Publish the post to primary platform(s)",
            expected_output="One published post live on platform",
            kpi=KPIName.POSTS_PUBLISHED.value,
            common_bottlenecks=[
                "Platform friction",
                "Scheduling tool issues",
                "Not publishing consistently",
            ],
            notes="Manual publish is fine. Consistency > automation.",
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.ENGAGEMENT_CAPTURE,
            name="Engagement Capture",
            objective="Identify and engage with prospect comments and interactions",
            expected_output="List of engaged prospects from today's content",
            kpi=KPIName.COMMENTS_GENERATED.value,
            common_bottlenecks=[
                "Not checking engagement",
                "No system for tracking who engaged",
                "Ignoring comments",
            ],
            notes="Every comment is a potential lead signal.",
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.DM_CONVERSATION,
            name="DM / Comment Conversation",
            objective="Open conversations with 5-20 prospects via DM or comment reply",
            expected_output="Conversations opened, objections captured",
            kpi=KPIName.DMS_OPENED.value,
            common_bottlenecks=[
                "Fear of outreach",
                "No conversation framework",
                "Sounding salesy instead of helpful",
            ],
            notes="Manual DMs. No automation. Genuine conversation.",
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.LEAD_CAPTURE,
            name="Lead Capture",
            objective="Move interested prospects into a trackable lead list",
            expected_output="New leads added to CRM or spreadsheet",
            kpi=KPIName.LEADS_CAPTURED.value,
            common_bottlenecks=[
                "No CRM or tracking system",
                "Not following up",
                "Losing track of conversations",
            ],
            notes="Even a spreadsheet works. Track name, platform, status, last contact.",
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.QUALIFICATION,
            name="Qualification",
            objective="Determine which leads are a good fit for Initiate Arena",
            expected_output="Qualified leads list with fit assessment",
            kpi=KPIName.QUALIFIED_LEADS.value,
            common_bottlenecks=[
                "No qualification criteria",
                "Afraid to disqualify",
                "Spending time on bad-fit leads",
            ],
            notes="Qualifying saves time. Not everyone is a fit.",
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.SALES_CONVERSATION,
            name="Sales Conversation / Call Booking",
            objective="Book and conduct sales conversations with qualified leads",
            expected_output="Calls booked or sales conversations had",
            kpi=KPIName.CALLS_BOOKED.value,
            common_bottlenecks=[
                "No booking system",
                "Leads go cold before call",
                "No sales script or framework",
                "Not asking for the close",
            ],
            notes="Calendly or manual scheduling. Have a framework, not a script.",
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.CLOSE_PAYMENT,
            name="Close / Payment",
            objective="Close the sale and collect payment",
            expected_output="Payment collected, new client confirmed",
            kpi=KPIName.REVENUE_COLLECTED.value,
            common_bottlenecks=[
                "No payment system",
                "Pricing objections",
                "No urgency or scarcity",
                "Not following up after call",
            ],
            notes="Stripe or manual invoice. Don't overcomplicate.",
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.ONBOARDING,
            name="Onboarding",
            objective="Welcome new client and deliver first-day experience",
            expected_output="Client onboarded with clear next steps",
            kpi=KPIName.ONBOARDING_COMPLETED.value,
            common_bottlenecks=[
                "No onboarding process",
                "Client confusion about next steps",
                "No welcome materials",
            ],
            notes="First impression matters. Clear, structured, immediate value.",
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.FULFILLMENT,
            name="Initiate Arena Fulfillment",
            objective="Deliver the Initiate Arena program content and coaching",
            expected_output="Client progressing through program milestones",
            kpi=KPIName.FULFILLMENT_COMPLETED.value,
            common_bottlenecks=[
                "Content not ready",
                "No delivery schedule",
                "Client disengagement",
            ],
            notes="Build as you sell initially. Document everything for scale.",
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.PROGRESS_TRACKING,
            name="Progress Tracking",
            objective="Monitor client progress and intervene if stalled",
            expected_output="Progress update per active client",
            kpi=KPIName.FULFILLMENT_COMPLETED.value,
            common_bottlenecks=[
                "No tracking system",
                "Not checking in regularly",
                "Client drops off silently",
            ],
            notes="Weekly check-ins minimum. Track milestones, not just attendance.",
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.TESTIMONIAL_CAPTURE,
            name="Testimonial / Case Study",
            objective="Capture testimonials and results from completed clients",
            expected_output="Written or video testimonial from client",
            kpi=KPIName.TESTIMONIALS_CAPTURED.value,
            common_bottlenecks=[
                "Not asking",
                "Asking too late",
                "No template for testimonial request",
            ],
            notes="Ask at peak satisfaction. Provide a simple format.",
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.UPSELL_PATH,
            name="Upsell Path to Game of Lyfe",
            objective="Identify clients ready for deeper engagement",
            expected_output="Upsell candidates identified",
            kpi=KPIName.QUALIFIED_LEADS.value,
            common_bottlenecks=[
                "Game of Lyfe not built yet",
                "No upsell framework",
                "Premature upsell attempt",
            ],
            notes="Future stage. Track interest signals now. Build Game of Lyfe later.",
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.END_OF_DAY_REVIEW,
            name="End-of-Day Review",
            objective="Review today's results, capture lessons, plan improvements",
            expected_output="Completed daily review with lessons and next actions",
            kpi=KPIName.BOTTLENECKS_FOUND.value,
            common_bottlenecks=[
                "Skipping review",
                "Not being honest about results",
                "No structured review process",
            ],
            notes="This stage is what makes the loop improve. Never skip.",
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.WEEKLY_IMPROVEMENT,
            name="Weekly Improvement Loop",
            objective="Synthesize weekly patterns and make structural improvements",
            expected_output="Weekly improvement plan with specific changes",
            kpi=KPIName.BOTTLENECKS_FOUND.value,
            common_bottlenecks=[
                "Not aggregating daily reviews",
                "Making too many changes at once",
                "Not measuring improvement",
            ],
            notes="One structural change per week. Measure its effect.",
        ),
    ]
