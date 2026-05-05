"""Phase 86 First Workflow Template — Personal Brand → Initiate Arena Revenue Loop.

Maps the 16-stage revenue loop from docs/strategy/first_operating_workflow.md
into typed WorkflowTemplate/WorkflowStage/KPIDefinition contracts consumable
by the Tomorrow Operating Loop orchestrator.

This is the binding constraint workflow until $10K/month net is stable.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from umh.tomorrow.contracts import (
    KPIDefinition,
    KPIType,
    LoopCadence,
    WorkflowStage,
    WorkflowStageStatus,
    WorkflowTemplate,
    _loop_id,
)


def build_first_workflow_template() -> WorkflowTemplate:
    """Build the Personal Brand → Initiate Arena Revenue Loop template.

    16 stages + 17 KPIs as defined in the first operating workflow doc.
    All stages start as NOT_STARTED. Owner defaults to Antony.
    """
    stages = _build_stages()
    kpis = _build_kpis()

    return WorkflowTemplate(
        template_id=_loop_id("tmpl"),
        name="Personal Brand → Initiate Arena Revenue Loop",
        description=(
            "The first operating workflow: content → engagement → leads → sales → "
            "fulfillment → testimonials → upsell. Touches Personal Brand, Lyfe Institute, "
            "Empyrean Studio, and OST/UMH/EOS."
        ),
        stages=stages,
        kpis=kpis,
        cadence=LoopCadence.DAILY,
        owner="antony",
        entity="lyfe_institute",
        metadata={
            "version": "v1",
            "source": "docs/strategy/first_operating_workflow.md",
            "binding_constraint": "$10K/month net",
            "entities_touched": [
                "personal_brand",
                "lyfe_institute",
                "empyrean_studio",
                "ost",
            ],
        },
    )


def _build_stages() -> list[WorkflowStage]:
    """Build the 16 workflow stages."""

    _s = _loop_id  # shorthand

    return [
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=1,
            name="Content Strategy",
            objective="Define what to post, for whom, and why — aligned to Initiate Arena avatar",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=[
                "target avatar profile",
                "Initiate Arena offer",
                "brand voice",
                "platform trends",
            ],
            outputs=["content calendar", "pillar topics", "hook library", "CTA templates"],
            kpi_ids=["kpi_posts_per_week"],
            failure_modes=[
                "no clear avatar",
                "posting without strategy",
                "copying instead of leading",
            ],
            data_to_capture=["planned vs actual posts", "topic performance over time"],
        ),
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=2,
            name="Content Production",
            objective="Create content pieces — short-form video, carousels, text posts",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=["content calendar", "hooks", "scripts", "brand assets"],
            outputs=["finished content ready to publish"],
            kpi_ids=["kpi_posts_per_week"],
            failure_modes=[
                "perfectionism",
                "over-production",
                "inconsistent quality",
                "no batch process",
            ],
            data_to_capture=["time per piece", "format type", "production method"],
        ),
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=3,
            name="Publishing",
            objective="Post content to platforms at optimal times",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=["finished content", "posting schedule"],
            outputs=["published posts across platforms"],
            kpi_ids=["kpi_posts_per_week"],
            failure_modes=["inconsistent posting", "wrong timing", "missing platforms"],
            data_to_capture=["post URLs", "timestamps", "platforms", "format type"],
        ),
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=4,
            name="Engagement Capture",
            objective="Monitor comments, likes, saves, shares — identify engaged prospects",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=["published posts", "notifications", "analytics"],
            outputs=["list of engaged users", "comment patterns", "engagement signals"],
            kpi_ids=["kpi_comments_per_post"],
            failure_modes=["ignoring engagement", "not responding", "missing high-intent signals"],
            data_to_capture=["engagement metrics per post", "engager profiles", "signal types"],
        ),
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=5,
            name="DM/Comment Conversation",
            objective="Start conversations with engaged prospects, build relationship, identify interest",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=["engaged user list", "DM trigger criteria"],
            outputs=["active conversations", "interest signals", "rapport"],
            kpi_ids=["kpi_dms_opened"],
            failure_modes=["spammy approach", "no follow-up", "generic messages", "slow response"],
            data_to_capture=["DM count", "response rate", "conversation progression"],
        ),
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=6,
            name="Lead Capture",
            objective="Move interested prospects from social to a trackable lead record",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=["interested DM contacts"],
            outputs=["lead records with contact info, source, interest level"],
            kpi_ids=["kpi_leads_captured"],
            failure_modes=["losing contacts", "no tracking system", "no lead source attribution"],
            data_to_capture=[
                "name",
                "contact method",
                "source platform",
                "interest level",
                "timestamp",
            ],
        ),
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=7,
            name="Qualification",
            objective="Determine if lead is a fit for Initiate Arena",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=["lead records", "qualification criteria"],
            outputs=["qualified leads", "disqualified leads with reason"],
            kpi_ids=["kpi_qualified_leads"],
            failure_modes=["selling to wrong people", "skipping qualification", "loose criteria"],
            data_to_capture=[
                "qualification criteria met",
                "disqualification reasons",
                "lead score",
            ],
        ),
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=8,
            name="Sales Conversation / Call Booking",
            objective="Present Initiate Arena offer, handle objections, close or book call",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=["qualified leads", "sales script", "offer details"],
            outputs=["booked calls", "direct closes", "lost reasons"],
            kpi_ids=["kpi_calls_booked", "kpi_show_up_rate", "kpi_objections_captured"],
            failure_modes=["no urgency", "weak pitch", "no follow-up", "no call structure"],
            data_to_capture=[
                "call date",
                "duration",
                "outcome",
                "objections raised",
                "follow-up needed",
            ],
        ),
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=9,
            name="Close / Payment",
            objective="Collect payment and confirm enrollment",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=["agreed sale", "payment link"],
            outputs=["payment received", "enrollment confirmed"],
            kpi_ids=["kpi_close_rate", "kpi_revenue"],
            failure_modes=["payment friction", "no confirmation", "delayed close"],
            data_to_capture=["amount", "date", "payment method", "invoice ID"],
        ),
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=10,
            name="Onboarding",
            objective="Welcome new student, set expectations, grant access, start journey",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=["confirmed enrollment"],
            outputs=["student onboarded", "access granted", "first steps clear"],
            kpi_ids=["kpi_onboarding_completion"],
            failure_modes=["no onboarding", "unclear next steps", "student drops before starting"],
            data_to_capture=["onboarding date", "steps completed", "first action date"],
        ),
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=11,
            name="Initiate Arena Fulfillment",
            objective="Deliver the transformation — training, accountability, community",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=["onboarded student"],
            outputs=["student progress", "completed modules", "transformation evidence"],
            kpi_ids=["kpi_fulfillment_completion", "kpi_manual_hours"],
            failure_modes=[
                "student drops off",
                "no accountability",
                "unclear curriculum",
                "no community",
            ],
            data_to_capture=["modules completed", "check-in attendance", "engagement signals"],
        ),
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=12,
            name="Progress Tracking",
            objective="Measure and display student progress toward transformation",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=["student activity", "milestones"],
            outputs=["progress dashboard", "milestone celebrations"],
            kpi_ids=["kpi_progress_signals"],
            failure_modes=["no tracking", "student doesn't report", "invisible progress"],
            data_to_capture=["milestone dates", "self-assessments", "behavioral metrics"],
        ),
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=13,
            name="Testimonial / Case Study",
            objective="Capture proof of transformation for marketing and social proof",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=["student progress", "completed program", "transformation evidence"],
            outputs=["testimonial text/video", "case study", "before/after"],
            kpi_ids=["kpi_testimonials"],
            failure_modes=["not asking", "asking too late", "no template", "student says no"],
            data_to_capture=["testimonial text", "format", "date", "permission", "usage status"],
        ),
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=14,
            name="Upsell Path to Game of Lyfe",
            objective="Present next-level offer to successful Initiate Arena graduates",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=["completed students", "progress data", "relationship"],
            outputs=["upsell conversations", "Game of Lyfe enrollments"],
            kpi_ids=["kpi_upsell_conversion"],
            failure_modes=["no upsell path defined", "asking too early", "no next product ready"],
            data_to_capture=["upsell attempt date", "outcome", "reason if declined"],
        ),
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=15,
            name="End-of-Day Review",
            objective="Review daily execution against plan, capture learnings",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=["day's activity across all stages"],
            outputs=["daily review notes", "tomorrow's priorities"],
            kpi_ids=[],
            failure_modes=["skipping review", "no template", "no action from insights"],
            data_to_capture=["what worked", "what didn't", "blockers", "tomorrow's top 3"],
        ),
        WorkflowStage(
            stage_id=_s("stg"),
            stage_number=16,
            name="Weekly Improvement Loop",
            objective="Analyze weekly performance, adjust strategy, improve system",
            owner="antony",
            status=WorkflowStageStatus.NOT_STARTED,
            inputs=["week's data across all stages"],
            outputs=["weekly report", "strategy adjustments", "SOP updates"],
            kpi_ids=["kpi_repeated_bottlenecks"],
            failure_modes=["no weekly review", "data not tracked", "no adjustments made"],
            data_to_capture=[
                "weekly metrics",
                "trend direction",
                "adjustments made",
                "next experiments",
            ],
        ),
    ]


def _build_kpis() -> list[KPIDefinition]:
    """Build the 17 KPIs from the first operating workflow."""
    return [
        KPIDefinition(
            kpi_id="kpi_posts_per_week",
            name="Posts published per week",
            kpi_type=KPIType.COUNT,
            target="7+",
            stage_ids=["stage_1", "stage_2", "stage_3"],
        ),
        KPIDefinition(
            kpi_id="kpi_comments_per_post",
            name="Comments generated per post",
            kpi_type=KPIType.COUNT,
            target="increasing trend",
            stage_ids=["stage_4"],
        ),
        KPIDefinition(
            kpi_id="kpi_dms_opened",
            name="DMs opened per week",
            kpi_type=KPIType.COUNT,
            target="20+",
            stage_ids=["stage_5"],
        ),
        KPIDefinition(
            kpi_id="kpi_leads_captured",
            name="Leads captured per week",
            kpi_type=KPIType.COUNT,
            target="10+",
            stage_ids=["stage_6"],
        ),
        KPIDefinition(
            kpi_id="kpi_qualified_leads",
            name="Qualified leads per week",
            kpi_type=KPIType.COUNT,
            target="5+",
            stage_ids=["stage_7"],
        ),
        KPIDefinition(
            kpi_id="kpi_calls_booked",
            name="Calls booked per week",
            kpi_type=KPIType.COUNT,
            target="3+",
            stage_ids=["stage_8"],
        ),
        KPIDefinition(
            kpi_id="kpi_show_up_rate",
            name="Show-up rate",
            kpi_type=KPIType.PERCENTAGE,
            target="80%+",
            stage_ids=["stage_8"],
        ),
        KPIDefinition(
            kpi_id="kpi_close_rate",
            name="Close rate",
            kpi_type=KPIType.PERCENTAGE,
            target="20%+",
            stage_ids=["stage_9"],
        ),
        KPIDefinition(
            kpi_id="kpi_revenue",
            name="Revenue collected per month",
            kpi_type=KPIType.CURRENCY,
            target="$10K+ net",
            stage_ids=["stage_9"],
        ),
        KPIDefinition(
            kpi_id="kpi_onboarding_completion",
            name="Onboarding completion rate",
            kpi_type=KPIType.PERCENTAGE,
            target="95%+",
            stage_ids=["stage_10"],
        ),
        KPIDefinition(
            kpi_id="kpi_fulfillment_completion",
            name="Fulfillment completion rate",
            kpi_type=KPIType.PERCENTAGE,
            target="80%+",
            stage_ids=["stage_11"],
        ),
        KPIDefinition(
            kpi_id="kpi_progress_signals",
            name="Progress signals per student per week",
            kpi_type=KPIType.COUNT,
            target="3+",
            stage_ids=["stage_12"],
        ),
        KPIDefinition(
            kpi_id="kpi_testimonials",
            name="Testimonials captured per cohort",
            kpi_type=KPIType.PERCENTAGE,
            target="50%+ of completers",
            stage_ids=["stage_13"],
        ),
        KPIDefinition(
            kpi_id="kpi_objections_captured",
            name="Objections captured",
            kpi_type=KPIType.COUNT,
            target="all documented",
            stage_ids=["stage_8"],
        ),
        KPIDefinition(
            kpi_id="kpi_upsell_conversion",
            name="Upsell conversion rate",
            kpi_type=KPIType.PERCENTAGE,
            target="track from first graduate",
            stage_ids=["stage_14"],
        ),
        KPIDefinition(
            kpi_id="kpi_manual_hours",
            name="Manual hours per student per week",
            kpi_type=KPIType.DURATION,
            target="decreasing trend",
            stage_ids=["stage_11"],
        ),
        KPIDefinition(
            kpi_id="kpi_repeated_bottlenecks",
            name="Repeated bottlenecks",
            kpi_type=KPIType.COUNT,
            target="decreasing trend",
            stage_ids=["stage_16"],
        ),
    ]
