"""North Star Integrated Operating Test Harness.

Builds integrated two-track operating plans (Business + Self-Build),
captures results, runs reviews, identifies gaps, and recommends
improvements. Operator-assisted only.

No execution. No external calls. No scraping. No DMs. No posting.
"""

from __future__ import annotations

from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.workflows.business_workflow import (
    build_personal_brand_to_initiate_arena_workflow,
    generate_business_test_tasks,
)
from umh.workflows.contracts import (
    DailyWorkflowPlan,
    IntegratedOperatingPlan,
    NorthStarTestReport,
    WorkflowResult,
    WorkflowReview,
    WorkflowTrack,
    _wf_id,
)
from umh.workflows.kpis import (
    build_default_kpis_for_first_workflow,
    build_default_self_build_kpis,
)
from umh.workflows.self_build_workflow import (
    build_umh_self_build_workflow,
    generate_self_build_test_tasks,
)


def build_north_star_test_plan(
    date: str | None = None,
    context: dict[str, Any] | None = None,
) -> IntegratedOperatingPlan:
    return build_integrated_operating_plan(date=date, context=context)


def build_integrated_operating_plan(
    date: str | None = None,
    context: dict[str, Any] | None = None,
) -> IntegratedOperatingPlan:
    if date is None:
        date = _iso_now()[:10]

    business_wf = build_personal_brand_to_initiate_arena_workflow()
    business_tasks = generate_business_test_tasks(context)
    business_kpis = build_default_kpis_for_first_workflow()
    business_kpi_names = [k.kpi_name.value for k in business_kpis]

    business_plan = DailyWorkflowPlan(
        plan_id=_wf_id("bplan"),
        date=date,
        workflow=business_wf,
        tasks=business_tasks,
        kpis_to_track=business_kpi_names,
        highest_leverage_actions=[
            "DM 5-20 prospects — direct revenue path",
            "Publish one piece of content — feeds top of funnel",
            "Follow up with existing leads — highest close probability",
            "Capture and document objections — improves sales process",
        ],
        non_actions=[
            "Do NOT redesign the website today",
            "Do NOT build new features in EOS today (use self-build track)",
            "Do NOT research new tools or platforms",
            "Do NOT optimize content strategy without publishing first",
        ],
        risks=[
            "Perfectionism delays publishing",
            "Outreach avoidance disguised as preparation",
            "Tool research instead of outreach",
            "Building instead of selling",
        ],
        metadata={"track": "business_revenue", "version": "v1"},
    )

    sb_wf = build_umh_self_build_workflow()
    sb_tasks = generate_self_build_test_tasks(context)
    sb_kpis = build_default_self_build_kpis()
    sb_kpi_names = [k.kpi_name.value for k in sb_kpis]

    sb_plan = DailyWorkflowPlan(
        plan_id=_wf_id("sbplan"),
        date=date,
        workflow=sb_wf,
        tasks=sb_tasks,
        kpis_to_track=sb_kpi_names,
        highest_leverage_actions=[
            "Complete one scoped phase — compounds system capability",
            "Write tests for new code — prevents regression",
            "Run safety scan — maintains governance",
            "Write phase report — captures learning",
        ],
        non_actions=[
            "Do NOT start a new architecture expansion",
            "Do NOT build autonomous agents",
            "Do NOT expand doctrine without first testing existing phases",
            "Do NOT skip safety validation",
        ],
        risks=[
            "Scope creep during implementation",
            "Building instead of selling (wrong time allocation)",
            "Skipping tests to move faster",
            "Architecture drift from unplanned changes",
        ],
        metadata={"track": "self_build", "version": "v1"},
    )

    plan = IntegratedOperatingPlan(
        plan_id=_wf_id("nsplan"),
        date=date,
        tracks=[WorkflowTrack.BUSINESS_REVENUE.value, WorkflowTrack.SELF_BUILD.value],
        business_plan=business_plan,
        self_build_plan=sb_plan,
        highest_leverage_actions=[
            "BUSINESS: DM 5-20 prospects — direct revenue path",
            "BUSINESS: Publish one piece of content — feeds top of funnel",
            "SELF-BUILD: Complete one scoped phase — compounds system capability",
            "BUSINESS: Capture objections — improves sales process",
        ],
        non_actions=[
            "Do NOT build instead of selling",
            "Do NOT expand architecture without testing existing phases first",
            "Do NOT skip daily review",
            "Do NOT start new initiatives without finishing current sprint",
        ],
        risks=[
            "Time allocation imbalance between tracks",
            "Self-build track consuming time meant for revenue",
            "Revenue track avoidance through building",
            "Neither track producing measurable output",
        ],
        required_manual_inputs=[
            "Content angle for today",
            "Prospect list or platform to engage",
            "Build phase selection from roadmap",
            "End-of-day KPI entries for both tracks",
            "Objections and bottlenecks captured",
        ],
        metadata={"version": "v1", "context": context or {}},
    )
    return apply_leverage_to_integrated_plan(plan, context)


def apply_leverage_to_integrated_plan(
    plan: IntegratedOperatingPlan,
    context: dict[str, Any] | None = None,
) -> IntegratedOperatingPlan:
    leverage_priority = {
        "human": 1,
        "distribution": 2,
        "content_media": 3,
        "knowledge": 4,
        "data": 5,
        "code_software": 6,
        "systems_process": 7,
    }
    for sub_plan in [plan.business_plan, plan.self_build_plan]:
        if sub_plan is None:
            continue
        for task in sub_plan.tasks:
            lev = task.leverage_type
            task.metadata["leverage_priority"] = leverage_priority.get(lev, 99)
        sub_plan.tasks.sort(key=lambda t: t.metadata.get("leverage_priority", 99))
    return plan


def build_required_manual_inputs(
    plan: IntegratedOperatingPlan,
) -> list[str]:
    return list(plan.required_manual_inputs)


def build_manual_result_capture_templates(
    plan: IntegratedOperatingPlan,
) -> dict[str, Any]:
    templates: dict[str, Any] = {}
    for label, sub_plan in [("business", plan.business_plan), ("self_build", plan.self_build_plan)]:
        if sub_plan is None:
            continue
        task_entries = []
        for t in sub_plan.tasks:
            task_entries.append({
                "task_id": t.task_id,
                "title": t.title,
                "status": "planned",
                "result": "",
            })
        templates[label] = {
            "plan_id": sub_plan.plan_id,
            "date": sub_plan.date,
            "tasks": task_entries,
            "kpis": {k: 0 for k in sub_plan.kpis_to_track},
            "objections": [],
            "notes": [],
            "bottlenecks": [],
            "wins": [],
            "losses": [],
        }
    return templates


def run_north_star_review(
    business_result: WorkflowResult,
    self_build_result: WorkflowResult,
) -> NorthStarTestReport:
    from umh.workflows.review import (
        build_workflow_review,
        extract_lessons_from_workflow_result,
    )
    from umh.workflows.template_candidates import (
        identify_template_candidates_from_business_result,
        identify_template_candidates_from_self_build_result,
    )

    biz_review = build_workflow_review(business_result, WorkflowTrack.BUSINESS_REVENUE)
    sb_review = build_workflow_review(self_build_result, WorkflowTrack.SELF_BUILD)

    biz_lessons = extract_lessons_from_workflow_result(business_result)
    sb_lessons = extract_lessons_from_workflow_result(self_build_result)
    integrated_lessons = biz_lessons + sb_lessons

    biz_templates = identify_template_candidates_from_business_result(business_result)
    sb_templates = identify_template_candidates_from_self_build_result(self_build_result)
    biz_review.template_candidates = [c["type"] for c in biz_templates]
    sb_review.template_candidates = [c["type"] for c in sb_templates]

    report = NorthStarTestReport(
        report_id=_wf_id("nsreport"),
        date=business_result.date or self_build_result.date or _iso_now()[:10],
        business_result=business_result,
        self_build_result=self_build_result,
        business_review=biz_review,
        self_build_review=sb_review,
        integrated_lessons=integrated_lessons,
        system_gaps=identify_system_gaps_from_test(
            business_result, self_build_result
        ),
        next_day_plan=recommend_next_day_plan_from_results(biz_review, sb_review),
        next_build_recommendations=recommend_next_build_steps_from_results(sb_review),
        metadata={"version": "v1"},
    )
    return report


def identify_system_gaps_from_test(
    business_result: WorkflowResult | None = None,
    self_build_result: WorkflowResult | None = None,
) -> list[str]:
    gaps: list[str] = []
    if business_result:
        if not business_result.completed_tasks:
            gaps.append("No business tasks completed — workflow may be too ambitious or unclear")
        if not business_result.kpi_records:
            gaps.append("No business KPIs captured — tracking system not used")
        if business_result.bottlenecks:
            gaps.append(f"Business bottleneck: {business_result.bottlenecks[0]}")
    if self_build_result:
        if not self_build_result.completed_tasks:
            gaps.append("No self-build tasks completed — build cycle not started")
        if not self_build_result.kpi_records:
            gaps.append("No self-build KPIs captured — metrics not recorded")
        if self_build_result.bottlenecks:
            gaps.append(f"Self-build bottleneck: {self_build_result.bottlenecks[0]}")
    if not gaps:
        gaps.append("No system gaps detected — both tracks produced output")
    return gaps


def recommend_next_day_plan(report: NorthStarTestReport) -> list[str]:
    recs: list[str] = []
    if report.business_review:
        for action in report.business_review.next_actions[:2]:
            recs.append(f"BUSINESS: {action}")
    if report.self_build_review:
        for action in report.self_build_review.next_actions[:2]:
            recs.append(f"SELF-BUILD: {action}")
    if report.system_gaps:
        recs.append(f"ADDRESS GAP: {report.system_gaps[0]}")
    if not recs:
        recs.append("Continue both tracks — consistency compounds")
    return recs


def recommend_next_build_steps(report: NorthStarTestReport) -> list[str]:
    recs: list[str] = []
    if report.self_build_review:
        for action in report.self_build_review.next_actions:
            recs.append(action)
    if report.system_gaps:
        for gap in report.system_gaps[:2]:
            recs.append(f"Fix gap: {gap}")
    if not recs:
        recs.append("Select next phase from roadmap")
    return recs


def recommend_next_day_plan_from_results(
    biz_review: WorkflowReview,
    sb_review: WorkflowReview,
) -> list[str]:
    recs: list[str] = []
    for action in biz_review.next_actions[:2]:
        recs.append(f"BUSINESS: {action}")
    for action in sb_review.next_actions[:2]:
        recs.append(f"SELF-BUILD: {action}")
    if not recs:
        recs.append("Continue both tracks — consistency compounds")
    return recs


def recommend_next_build_steps_from_results(
    sb_review: WorkflowReview,
) -> list[str]:
    recs: list[str] = []
    for action in sb_review.next_actions:
        recs.append(action)
    if not recs:
        recs.append("Select next phase from roadmap")
    return recs
