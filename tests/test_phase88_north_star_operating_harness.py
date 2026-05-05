"""Phase 88 — North Star Integrated Operating Test Harness v1.

Tests for expanded contracts, business workflow, self-build workflow,
north star harness, KPIs, daily results, review, template candidates,
views, safety, and regression against prior phases.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from umh.workflows.contracts import (
    BusinessStage,
    DailyWorkflowPlan,
    DailyWorkflowResult,
    DailyWorkflowReview,
    IntegratedOperatingPlan,
    KPIName,
    NorthStarTestReport,
    SelfBuildStage,
    WorkflowDefinition,
    WorkflowKPIRecord,
    WorkflowResult,
    WorkflowReview,
    WorkflowStage,
    WorkflowStageDefinition,
    WorkflowStatus,
    WorkflowTask,
    WorkflowTrack,
    normalize_business_stage,
    normalize_kpi_name,
    normalize_self_build_stage,
    normalize_workflow_stage,
    normalize_workflow_status,
    normalize_workflow_track,
)


# ═══════════════════════════════════════════════════════════════════════
# Contracts
# ═══════════════════════════════════════════════════════════════════════


class TestContractNormalizers(unittest.TestCase):
    def test_01_workflow_track_normalizes(self):
        self.assertEqual(normalize_workflow_track("business_revenue"), WorkflowTrack.BUSINESS_REVENUE)
        self.assertEqual(normalize_workflow_track("self_build"), WorkflowTrack.SELF_BUILD)
        self.assertEqual(normalize_workflow_track("nonsense"), WorkflowTrack.UNKNOWN)

    def test_02_workflow_stage_normalizes(self):
        self.assertEqual(normalize_workflow_stage("content_strategy"), WorkflowStage.CONTENT_STRATEGY)
        self.assertEqual(normalize_workflow_stage("context_load"), WorkflowStage.CONTEXT_LOAD)
        self.assertEqual(normalize_workflow_stage("nonsense"), WorkflowStage.UNKNOWN)

    def test_03_business_stage_normalizes(self):
        self.assertEqual(normalize_business_stage("content_strategy"), BusinessStage.CONTENT_STRATEGY)
        self.assertEqual(normalize_business_stage("dm_conversation"), BusinessStage.DM_CONVERSATION)
        self.assertEqual(normalize_business_stage("nonsense"), BusinessStage.UNKNOWN)

    def test_04_self_build_stage_normalizes(self):
        self.assertEqual(normalize_self_build_stage("phase_selection"), SelfBuildStage.PHASE_SELECTION)
        self.assertEqual(normalize_self_build_stage("testing"), SelfBuildStage.TESTING)
        self.assertEqual(normalize_self_build_stage("nonsense"), SelfBuildStage.UNKNOWN)

    def test_05_workflow_status_normalizes(self):
        self.assertEqual(normalize_workflow_status("planned"), WorkflowStatus.PLANNED)
        self.assertEqual(normalize_workflow_status("nonsense"), WorkflowStatus.UNKNOWN)

    def test_06_kpi_normalizes(self):
        self.assertEqual(normalize_kpi_name("posts_published"), KPIName.POSTS_PUBLISHED)
        self.assertEqual(normalize_kpi_name("files_changed"), KPIName.FILES_CHANGED)
        self.assertEqual(normalize_kpi_name("nonsense"), KPIName.UNKNOWN)

    def test_07_workflow_definition_serializes(self):
        wf = WorkflowDefinition(
            workflow_id="wf1", track=WorkflowTrack.BUSINESS_REVENUE, name="Test"
        )
        d = wf.to_dict()
        wf2 = WorkflowDefinition.from_dict(d)
        self.assertEqual(wf2.track, WorkflowTrack.BUSINESS_REVENUE)

    def test_08_workflow_task_serializes(self):
        t = WorkflowTask(
            task_id="t1",
            track=WorkflowTrack.SELF_BUILD,
            stage=WorkflowStage.MANUAL_EXECUTION,
            manual_only=True,
        )
        d = t.to_dict()
        t2 = WorkflowTask.from_dict(d)
        self.assertEqual(t2.track, WorkflowTrack.SELF_BUILD)
        self.assertTrue(t2.manual_only)

    def test_09_kpi_record_serializes(self):
        k = WorkflowKPIRecord(kpi_name=KPIName.FILES_CHANGED, value=5.0, unit="count")
        d = k.to_dict()
        k2 = WorkflowKPIRecord.from_dict(d)
        self.assertEqual(k2.kpi_name, KPIName.FILES_CHANGED)

    def test_10_integrated_plan_serializes(self):
        p = IntegratedOperatingPlan(
            plan_id="ip1",
            date="2026-05-04",
            tracks=["business_revenue", "self_build"],
        )
        d = p.to_dict()
        p2 = IntegratedOperatingPlan.from_dict(d)
        self.assertEqual(p2.plan_id, "ip1")
        self.assertEqual(len(p2.tracks), 2)

    def test_11_workflow_result_serializes(self):
        r = WorkflowResult(
            result_id="wr1",
            track=WorkflowTrack.BUSINESS_REVENUE,
            date="2026-05-04",
            artifacts=["report.md"],
        )
        d = r.to_dict()
        r2 = WorkflowResult.from_dict(d)
        self.assertEqual(r2.track, WorkflowTrack.BUSINESS_REVENUE)
        self.assertIn("report.md", r2.artifacts)

    def test_12_workflow_review_serializes(self):
        rv = WorkflowReview(
            review_id="rv1",
            track=WorkflowTrack.SELF_BUILD,
            template_candidates=["test_checklist"],
            confidence=0.8,
        )
        d = rv.to_dict()
        rv2 = WorkflowReview.from_dict(d)
        self.assertEqual(rv2.track, WorkflowTrack.SELF_BUILD)
        self.assertIn("test_checklist", rv2.template_candidates)

    def test_13_north_star_report_serializes(self):
        report = NorthStarTestReport(
            report_id="nsr1",
            date="2026-05-04",
            integrated_lessons=["lesson1"],
            system_gaps=["gap1"],
        )
        d = report.to_dict()
        r2 = NorthStarTestReport.from_dict(d)
        self.assertEqual(r2.report_id, "nsr1")
        self.assertIn("lesson1", r2.integrated_lessons)


# ═══════════════════════════════════════════════════════════════════════
# Business Workflow
# ═══════════════════════════════════════════════════════════════════════


class TestBusinessWorkflow(unittest.TestCase):
    def setUp(self):
        from umh.workflows.business_workflow import (
            build_personal_brand_to_initiate_arena_workflow,
            generate_business_test_tasks,
        )

        self.wf = build_personal_brand_to_initiate_arena_workflow()
        self.tasks = generate_business_test_tasks()

    def test_14_business_workflow_builds(self):
        self.assertIsInstance(self.wf, WorkflowDefinition)
        self.assertTrue(self.wf.workflow_id)

    def test_15_business_workflow_has_16_stages(self):
        self.assertEqual(len(self.wf.stages), 16)

    def test_16_includes_content_strategy(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.CONTENT_STRATEGY, stages)

    def test_17_includes_publishing(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.PUBLISHING, stages)

    def test_18_includes_dm_conversation(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.DM_CONVERSATION, stages)

    def test_19_includes_lead_capture(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.LEAD_CAPTURE, stages)

    def test_20_includes_qualification(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.QUALIFICATION, stages)

    def test_21_includes_sales_conversation(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.SALES_CONVERSATION, stages)

    def test_22_includes_onboarding(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.ONBOARDING, stages)

    def test_23_includes_fulfillment(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.FULFILLMENT, stages)

    def test_24_includes_testimonial_capture(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.TESTIMONIAL_CAPTURE, stages)

    def test_25_includes_end_of_day_review(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.END_OF_DAY_REVIEW, stages)

    def test_26_business_test_tasks_build(self):
        self.assertTrue(len(self.tasks) >= 10)

    def test_27_business_tasks_are_manual_only(self):
        for t in self.tasks:
            self.assertTrue(t.manual_only, f"Task '{t.title}' not manual_only")

    def test_28_business_tasks_include_content_angle(self):
        titles = [t.title.lower() for t in self.tasks]
        self.assertTrue(any("content angle" in t for t in titles))

    def test_29_business_tasks_include_short_form_draft(self):
        titles = [t.title.lower() for t in self.tasks]
        self.assertTrue(any("draft" in t or "short-form" in t for t in titles))

    def test_30_business_tasks_include_manual_outreach(self):
        titles = [t.title.lower() for t in self.tasks]
        self.assertTrue(any("dm" in t or "engage" in t or "prospect" in t for t in titles))

    def test_31_business_tasks_include_objections_capture(self):
        titles = [t.title.lower() for t in self.tasks]
        self.assertTrue(any("objection" in t for t in titles))

    def test_32_business_tasks_include_review(self):
        titles = [t.title.lower() for t in self.tasks]
        self.assertTrue(any("review" in t for t in titles))

    def test_business_workflow_track(self):
        self.assertEqual(self.wf.track, WorkflowTrack.BUSINESS_REVENUE)

    def test_business_tasks_have_track(self):
        for t in self.tasks:
            self.assertEqual(t.track, WorkflowTrack.BUSINESS_REVENUE)


# ═══════════════════════════════════════════════════════════════════════
# Self-Build Workflow
# ═══════════════════════════════════════════════════════════════════════


class TestSelfBuildWorkflow(unittest.TestCase):
    def setUp(self):
        from umh.workflows.self_build_workflow import (
            build_umh_self_build_workflow,
            generate_self_build_test_tasks,
        )

        self.wf = build_umh_self_build_workflow()
        self.tasks = generate_self_build_test_tasks()

    def test_33_self_build_workflow_builds(self):
        self.assertIsInstance(self.wf, WorkflowDefinition)
        self.assertTrue(self.wf.workflow_id)
        self.assertEqual(self.wf.track, WorkflowTrack.SELF_BUILD)

    def test_34_self_build_includes_phase_selection(self):
        names = [s.name.lower() for s in self.wf.stages]
        self.assertTrue(any("phase selection" in n for n in names))

    def test_35_self_build_includes_doc_context_load(self):
        names = [s.name.lower() for s in self.wf.stages]
        self.assertTrue(any("doc context" in n for n in names))

    def test_36_self_build_includes_architecture_review(self):
        names = [s.name.lower() for s in self.wf.stages]
        self.assertTrue(any("architecture review" in n for n in names))

    def test_37_self_build_includes_implementation_plan(self):
        names = [s.name.lower() for s in self.wf.stages]
        self.assertTrue(any("implementation plan" in n for n in names))

    def test_38_self_build_includes_testing(self):
        names = [s.name.lower() for s in self.wf.stages]
        self.assertTrue(any("testing" in n for n in names))

    def test_39_self_build_includes_safety_validation(self):
        names = [s.name.lower() for s in self.wf.stages]
        self.assertTrue(any("safety" in n for n in names))

    def test_40_self_build_includes_reporting(self):
        names = [s.name.lower() for s in self.wf.stages]
        self.assertTrue(any("reporting" in n for n in names))

    def test_41_self_build_includes_drift_detection(self):
        names = [s.name.lower() for s in self.wf.stages]
        self.assertTrue(any("drift" in n for n in names))

    def test_42_self_build_tasks_build(self):
        self.assertTrue(len(self.tasks) >= 10)

    def test_43_self_build_tasks_are_manual_or_operator_assisted(self):
        for t in self.tasks:
            self.assertTrue(t.manual_only, f"Task '{t.title}' not manual_only")

    def test_self_build_has_11_stages(self):
        self.assertEqual(len(self.wf.stages), 11)

    def test_self_build_tasks_have_track(self):
        for t in self.tasks:
            self.assertEqual(t.track, WorkflowTrack.SELF_BUILD)


# ═══════════════════════════════════════════════════════════════════════
# North Star Harness
# ═══════════════════════════════════════════════════════════════════════


class TestNorthStarHarness(unittest.TestCase):
    def setUp(self):
        from umh.workflows.north_star_harness import build_north_star_test_plan

        self.plan = build_north_star_test_plan(date="2026-05-04")

    def test_44_north_star_plan_builds(self):
        self.assertIsInstance(self.plan, IntegratedOperatingPlan)
        self.assertTrue(self.plan.plan_id)

    def test_45_integrated_plan_includes_business_track(self):
        self.assertIsNotNone(self.plan.business_plan)
        self.assertIn("business_revenue", self.plan.tracks)

    def test_46_integrated_plan_includes_self_build_track(self):
        self.assertIsNotNone(self.plan.self_build_plan)
        self.assertIn("self_build", self.plan.tracks)

    def test_47_integrated_plan_includes_highest_leverage_actions(self):
        self.assertTrue(len(self.plan.highest_leverage_actions) > 0)

    def test_48_integrated_plan_includes_non_actions(self):
        self.assertTrue(len(self.plan.non_actions) > 0)

    def test_49_integrated_plan_includes_risks(self):
        self.assertTrue(len(self.plan.risks) > 0)

    def test_50_integrated_plan_includes_required_manual_inputs(self):
        self.assertTrue(len(self.plan.required_manual_inputs) > 0)

    def test_51_manual_result_templates_build(self):
        from umh.workflows.north_star_harness import build_manual_result_capture_templates

        templates = build_manual_result_capture_templates(self.plan)
        self.assertIn("business", templates)
        self.assertIn("self_build", templates)
        self.assertTrue(len(templates["business"]["tasks"]) > 0)
        self.assertTrue(len(templates["self_build"]["tasks"]) > 0)

    def test_52_north_star_review_builds(self):
        from umh.workflows.north_star_harness import run_north_star_review

        biz = WorkflowResult(
            result_id="br1",
            date="2026-05-04",
            track=WorkflowTrack.BUSINESS_REVENUE,
            completed_tasks=["t1", "t2"],
            objections=["Too expensive"],
            bottlenecks=["No CRM"],
            wins=["Good conversation"],
            losses=["Post flopped"],
        )
        sb = WorkflowResult(
            result_id="sbr1",
            date="2026-05-04",
            track=WorkflowTrack.SELF_BUILD,
            completed_tasks=["st1", "test_st", "report_st"],
            bottlenecks=["Flaky test"],
            wins=["Phase completed"],
        )
        report = run_north_star_review(biz, sb)
        self.assertIsInstance(report, NorthStarTestReport)
        self.assertTrue(report.report_id)

    def test_53_system_gaps_are_identified(self):
        from umh.workflows.north_star_harness import identify_system_gaps_from_test

        biz = WorkflowResult(
            result_id="br1",
            date="2026-05-04",
            track=WorkflowTrack.BUSINESS_REVENUE,
            bottlenecks=["No CRM"],
        )
        gaps = identify_system_gaps_from_test(biz, None)
        self.assertTrue(len(gaps) > 0)

    def test_54_next_day_plan_is_recommended(self):
        from umh.workflows.north_star_harness import run_north_star_review, recommend_next_day_plan

        biz = WorkflowResult(
            result_id="br1", date="2026-05-04", track=WorkflowTrack.BUSINESS_REVENUE,
            completed_tasks=["t1"], wins=["win1"],
        )
        sb = WorkflowResult(
            result_id="sbr1", date="2026-05-04", track=WorkflowTrack.SELF_BUILD,
            completed_tasks=["st1"], wins=["win2"],
        )
        report = run_north_star_review(biz, sb)
        recs = recommend_next_day_plan(report)
        self.assertTrue(len(recs) > 0)

    def test_55_next_build_steps_recommended(self):
        from umh.workflows.north_star_harness import run_north_star_review, recommend_next_build_steps

        biz = WorkflowResult(
            result_id="br1", date="2026-05-04", track=WorkflowTrack.BUSINESS_REVENUE,
            completed_tasks=["t1"],
        )
        sb = WorkflowResult(
            result_id="sbr1", date="2026-05-04", track=WorkflowTrack.SELF_BUILD,
            completed_tasks=["st1"], bottlenecks=["drift found"],
        )
        report = run_north_star_review(biz, sb)
        recs = recommend_next_build_steps(report)
        self.assertTrue(len(recs) > 0)

    def test_integrated_plan_serializes_roundtrip(self):
        d = self.plan.to_dict()
        p2 = IntegratedOperatingPlan.from_dict(d)
        self.assertEqual(p2.plan_id, self.plan.plan_id)
        self.assertEqual(len(p2.tracks), 2)

    def test_leverage_applied_to_business_tasks(self):
        bp = self.plan.business_plan
        self.assertIsNotNone(bp)
        priorities = [t.metadata.get("leverage_priority", 99) for t in bp.tasks]
        self.assertEqual(priorities, sorted(priorities))


# ═══════════════════════════════════════════════════════════════════════
# KPIs
# ═══════════════════════════════════════════════════════════════════════


class TestKPIs(unittest.TestCase):
    def setUp(self):
        from umh.workflows.kpis import (
            build_default_kpis_for_first_workflow,
            build_default_self_build_kpis,
        )

        self.biz_kpis = build_default_kpis_for_first_workflow()
        self.sb_kpis = build_default_self_build_kpis()

    def test_56_business_kpis_include_posts_published(self):
        names = {k.kpi_name for k in self.biz_kpis}
        self.assertIn(KPIName.POSTS_PUBLISHED, names)

    def test_57_business_kpis_include_dms_opened(self):
        names = {k.kpi_name for k in self.biz_kpis}
        self.assertIn(KPIName.DMS_OPENED, names)

    def test_58_business_kpis_include_leads_captured(self):
        names = {k.kpi_name for k in self.biz_kpis}
        self.assertIn(KPIName.LEADS_CAPTURED, names)

    def test_59_business_kpis_include_calls_booked(self):
        names = {k.kpi_name for k in self.biz_kpis}
        self.assertIn(KPIName.CALLS_BOOKED, names)

    def test_60_business_kpis_include_objections_captured(self):
        names = {k.kpi_name for k in self.biz_kpis}
        self.assertIn(KPIName.OBJECTIONS_CAPTURED, names)

    def test_61_self_build_kpis_include_files_changed(self):
        names = {k.kpi_name for k in self.sb_kpis}
        self.assertIn(KPIName.FILES_CHANGED, names)

    def test_62_self_build_kpis_include_tests_passed(self):
        names = {k.kpi_name for k in self.sb_kpis}
        self.assertIn(KPIName.TESTS_PASSED, names)

    def test_63_self_build_kpis_include_regression_status(self):
        names = {k.kpi_name for k in self.sb_kpis}
        self.assertIn(KPIName.REGRESSION_STATUS, names)

    def test_64_self_build_kpis_include_safety_violations(self):
        names = {k.kpi_name for k in self.sb_kpis}
        self.assertIn(KPIName.SAFETY_VIOLATIONS, names)

    def test_65_kpi_summaries_work(self):
        from umh.workflows.kpis import summarize_kpis

        records = [
            WorkflowKPIRecord(kpi_name=KPIName.FILES_CHANGED, value=3.0),
            WorkflowKPIRecord(kpi_name=KPIName.TESTS_PASSED, value=10.0),
        ]
        s = summarize_kpis(records)
        self.assertEqual(s["totals"]["files_changed"], 3.0)
        self.assertEqual(s["totals"]["tests_passed"], 10.0)


# ═══════════════════════════════════════════════════════════════════════
# Results / Review
# ═══════════════════════════════════════════════════════════════════════


class TestDailyResultsNorthStar(unittest.TestCase):
    def test_66_empty_business_result_creates(self):
        from umh.workflows.daily_results import create_empty_workflow_result

        r = create_empty_workflow_result(WorkflowTrack.BUSINESS_REVENUE)
        self.assertEqual(r.track, WorkflowTrack.BUSINESS_REVENUE)

    def test_67_empty_self_build_result_creates(self):
        from umh.workflows.daily_results import create_empty_workflow_result

        r = create_empty_workflow_result(WorkflowTrack.SELF_BUILD)
        self.assertEqual(r.track, WorkflowTrack.SELF_BUILD)

    def test_68_completed_task_can_be_added(self):
        from umh.workflows.daily_results import (
            add_completed_task_to_workflow_result,
            create_empty_workflow_result,
        )

        r = create_empty_workflow_result(WorkflowTrack.BUSINESS_REVENUE)
        add_completed_task_to_workflow_result(r, "task_1")
        self.assertIn("task_1", r.completed_tasks)

    def test_69_skipped_task_can_be_added(self):
        from umh.workflows.daily_results import (
            add_skipped_task_to_workflow_result,
            create_empty_workflow_result,
        )

        r = create_empty_workflow_result(WorkflowTrack.BUSINESS_REVENUE)
        add_skipped_task_to_workflow_result(r, "task_2", "no time")
        self.assertEqual(len(r.skipped_tasks), 1)

    def test_70_kpi_record_can_be_added(self):
        from umh.workflows.daily_results import (
            add_kpi_record_to_workflow_result,
            create_empty_workflow_result,
        )

        r = create_empty_workflow_result(WorkflowTrack.SELF_BUILD)
        rec = WorkflowKPIRecord(kpi_name=KPIName.FILES_CHANGED, value=5.0)
        add_kpi_record_to_workflow_result(r, rec)
        self.assertEqual(len(r.kpi_records), 1)

    def test_71_objection_can_be_added(self):
        from umh.workflows.daily_results import (
            add_objection_to_workflow_result,
            create_empty_workflow_result,
        )

        r = create_empty_workflow_result(WorkflowTrack.BUSINESS_REVENUE)
        add_objection_to_workflow_result(r, "Too expensive")
        self.assertIn("Too expensive", r.objections)

    def test_72_bottleneck_can_be_added(self):
        from umh.workflows.daily_results import (
            add_bottleneck_to_workflow_result,
            create_empty_workflow_result,
        )

        r = create_empty_workflow_result(WorkflowTrack.SELF_BUILD)
        add_bottleneck_to_workflow_result(r, "Flaky tests")
        self.assertIn("Flaky tests", r.bottlenecks)

    def test_73_artifact_can_be_added(self):
        from umh.workflows.daily_results import (
            add_artifact_to_workflow_result,
            create_empty_workflow_result,
        )

        r = create_empty_workflow_result(WorkflowTrack.SELF_BUILD)
        add_artifact_to_workflow_result(r, "phase_report.md")
        self.assertIn("phase_report.md", r.artifacts)


class TestReviewNorthStar(unittest.TestCase):
    def _build_biz_result(self):
        return WorkflowResult(
            result_id="br1",
            date="2026-05-04",
            track=WorkflowTrack.BUSINESS_REVENUE,
            completed_tasks=["t1", "t2", "t3"],
            skipped_tasks=[{"task_id": "t4", "reason": "ran out of time"}],
            objections=["Too expensive"],
            bottlenecks=["No CRM"],
            wins=["First call booked"],
            losses=["Post flopped"],
            kpi_records=[WorkflowKPIRecord(kpi_name=KPIName.DMS_OPENED, value=8.0)],
        )

    def _build_sb_result(self):
        return WorkflowResult(
            result_id="sbr1",
            date="2026-05-04",
            track=WorkflowTrack.SELF_BUILD,
            completed_tasks=["st1", "test_st2", "safety_st3", "report_st4"],
            bottlenecks=["Flaky test"],
            wins=["Phase completed"],
            kpi_records=[WorkflowKPIRecord(kpi_name=KPIName.TESTS_PASSED, value=50.0)],
        )

    def test_74_business_review_identifies_bottlenecks(self):
        from umh.workflows.review import build_workflow_review

        review = build_workflow_review(self._build_biz_result(), WorkflowTrack.BUSINESS_REVENUE)
        self.assertTrue(len(review.bottlenecks) > 0)

    def test_75_self_build_review_identifies_bottlenecks(self):
        from umh.workflows.review import build_workflow_review

        review = build_workflow_review(self._build_sb_result(), WorkflowTrack.SELF_BUILD)
        self.assertTrue(len(review.bottlenecks) > 0)

    def test_76_review_recommends_next_actions(self):
        from umh.workflows.review import build_workflow_review

        review = build_workflow_review(self._build_biz_result(), WorkflowTrack.BUSINESS_REVENUE)
        self.assertTrue(len(review.next_actions) > 0)

    def test_77_review_identifies_system_gaps(self):
        from umh.workflows.review import identify_workflow_system_gaps

        gaps = identify_workflow_system_gaps(self._build_biz_result())
        self.assertIsInstance(gaps, list)

    def test_78_review_identifies_template_candidates(self):
        from umh.workflows.review import identify_workflow_template_candidates

        candidates = identify_workflow_template_candidates(self._build_biz_result())
        self.assertTrue(len(candidates) > 0)

    def test_review_extracts_lessons(self):
        from umh.workflows.review import extract_lessons_from_workflow_result

        lessons = extract_lessons_from_workflow_result(self._build_biz_result())
        self.assertTrue(len(lessons) > 0)


# ═══════════════════════════════════════════════════════════════════════
# Template Candidates
# ═══════════════════════════════════════════════════════════════════════


class TestTemplateCandidates(unittest.TestCase):
    def test_79_business_result_produces_candidates(self):
        from umh.workflows.template_candidates import (
            identify_template_candidates_from_business_result,
        )

        result = WorkflowResult(
            result_id="br1",
            date="2026-05-04",
            track=WorkflowTrack.BUSINESS_REVENUE,
            completed_tasks=["content_t1", "dm_t2", "qualify_t3"],
            objections=["Too expensive"],
        )
        candidates = identify_template_candidates_from_business_result(result)
        types = [c["type"] for c in candidates]
        self.assertTrue(any("content" in t or "dm" in t or "objection" in t for t in types))

    def test_80_self_build_result_produces_candidates(self):
        from umh.workflows.template_candidates import (
            identify_template_candidates_from_self_build_result,
        )

        result = WorkflowResult(
            result_id="sbr1",
            date="2026-05-04",
            track=WorkflowTrack.SELF_BUILD,
            completed_tasks=["phase_st1", "test_st2", "report_st3", "safety_st4"],
        )
        candidates = identify_template_candidates_from_self_build_result(result)
        types = [c["type"] for c in candidates]
        self.assertTrue(
            any("phase" in t or "test" in t or "report" in t or "build" in t for t in types)
        )

    def test_81_candidate_summary_builds(self):
        from umh.workflows.template_candidates import (
            build_template_candidate_summary,
            identify_template_candidates_from_business_result,
            identify_template_candidates_from_self_build_result,
        )

        biz = WorkflowResult(
            result_id="br1", date="2026-05-04", track=WorkflowTrack.BUSINESS_REVENUE,
            completed_tasks=["t1", "t2", "t3"], objections=["obj1"],
        )
        sb = WorkflowResult(
            result_id="sbr1", date="2026-05-04", track=WorkflowTrack.SELF_BUILD,
            completed_tasks=["test_t", "report_t", "phase_t", "safety_t"],
        )
        all_candidates = (
            identify_template_candidates_from_business_result(biz)
            + identify_template_candidates_from_self_build_result(sb)
        )
        summary = build_template_candidate_summary(all_candidates)
        self.assertTrue(summary["total"] > 0)
        self.assertIn("types", summary)


# ════════════════════════════════════════════════════════════════════��══
# Views
# ═══════════════════════════════════════════════════════════════════════


class TestViewsNorthStar(unittest.TestCase):
    def test_82_workflow_view_serializes(self):
        from umh.workflows.business_workflow import (
            build_personal_brand_to_initiate_arena_workflow,
        )
        from umh.workflows.views import workflow_to_view

        wf = build_personal_brand_to_initiate_arena_workflow()
        v = workflow_to_view(wf)
        d = v.to_dict()
        self.assertIn("workflow_id", d)

    def test_83_task_view_serializes(self):
        from umh.workflows.views import task_to_view

        t = WorkflowTask(
            task_id="t1",
            track=WorkflowTrack.BUSINESS_REVENUE,
            stage=WorkflowStage.PUBLISHING,
        )
        v = task_to_view(t)
        d = v.to_dict()
        self.assertIn("task_id", d)

    def test_84_integrated_plan_view_serializes(self):
        from umh.workflows.north_star_harness import build_north_star_test_plan
        from umh.workflows.views import integrated_plan_to_view

        plan = build_north_star_test_plan(date="2026-05-04")
        v = integrated_plan_to_view(plan)
        d = v.to_dict()
        self.assertIn("plan_id", d)
        self.assertTrue(d["business_task_count"] > 0)
        self.assertTrue(d["self_build_task_count"] > 0)

    def test_85_result_view_serializes(self):
        from umh.workflows.views import workflow_result_to_view

        r = WorkflowResult(
            result_id="wr1",
            track=WorkflowTrack.BUSINESS_REVENUE,
            completed_tasks=["t1"],
            artifacts=["report.md"],
        )
        v = workflow_result_to_view(r)
        d = v.to_dict()
        self.assertEqual(d["completed_count"], 1)
        self.assertEqual(d["artifact_count"], 1)

    def test_86_review_view_serializes(self):
        from umh.workflows.views import workflow_review_to_view

        rv = WorkflowReview(
            review_id="rv1",
            track=WorkflowTrack.SELF_BUILD,
            bottlenecks=["b1"],
            lessons=["l1"],
            template_candidates=["tc1"],
            confidence=0.7,
        )
        v = workflow_review_to_view(rv)
        d = v.to_dict()
        self.assertEqual(d["bottleneck_count"], 1)
        self.assertEqual(d["template_candidate_count"], 1)

    def test_87_report_view_serializes(self):
        from umh.workflows.views import report_to_view

        report = NorthStarTestReport(
            report_id="nsr1",
            date="2026-05-04",
            integrated_lessons=["l1", "l2"],
            system_gaps=["g1"],
        )
        v = report_to_view(report)
        d = v.to_dict()
        self.assertEqual(d["integrated_lesson_count"], 2)
        self.assertEqual(d["system_gap_count"], 1)

    def test_88_dashboard_view_serializes(self):
        from umh.workflows.north_star_harness import build_north_star_test_plan
        from umh.workflows.views import build_north_star_dashboard_view

        plan = build_north_star_test_plan(date="2026-05-04")
        dv = build_north_star_dashboard_view(plan=plan)
        d = dv.to_dict()
        self.assertIn("business_track_name", d)
        self.assertIn("self_build_track_name", d)
        self.assertTrue(d["business_task_count"] > 0)
        self.assertTrue(d["self_build_task_count"] > 0)

    def test_89_views_omit_secrets(self):
        from umh.workflows.north_star_harness import build_north_star_test_plan
        from umh.workflows.views import build_north_star_dashboard_view

        plan = build_north_star_test_plan(date="2026-05-04")
        dv = build_north_star_dashboard_view(plan=plan)
        d_str = str(dv.to_dict()).lower()
        self.assertNotIn("password", d_str)
        self.assertNotIn("api_key", d_str)
        self.assertNotIn("secret", d_str)
        self.assertNotIn("credential", d_str)


# ═══════════════════════════════════════════════════════════════════════
# Safety
# ═══════════════════════════════════════════════════════════════════════


class TestSafetyNorthStar(unittest.TestCase):
    def test_90_safety_scan_passes_workflow_modules(self):
        from umh.workflows.safety import validate_workflow_modules_are_manual_only

        r = validate_workflow_modules_are_manual_only()
        self.assertTrue(r["all_safe"], f"Safety violations: {r}")
        self.assertTrue(r["modules_checked"] > 0)

    def test_91_detects_subprocess(self):
        from umh.workflows.safety import check_module_safety

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("import subprocess\n")
            f.flush()
            r = check_module_safety(f.name)
        os.unlink(f.name)
        self.assertFalse(r["safe"])
        self.assertIn("subprocess", r["forbidden_imports"])

    def test_92_detects_requests_httpx_socket(self):
        from umh.workflows.safety import check_module_safety

        for mod in ["requests", "httpx", "socket"]:
            with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
                f.write(f"import {mod}\n")
                f.flush()
                r = check_module_safety(f.name)
            os.unlink(f.name)
            self.assertFalse(r["safe"], f"{mod} not detected")

    def test_93_detects_browser_automation(self):
        from umh.workflows.safety import check_module_safety

        for mod in ["selenium", "playwright"]:
            with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
                f.write(f"import {mod}\n")
                f.flush()
                r = check_module_safety(f.name)
            os.unlink(f.name)
            self.assertFalse(r["safe"], f"{mod} not detected")

    def test_94_detects_adapter_import(self):
        from umh.workflows.safety import check_module_safety

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("from umh.adapters.instagram import InstaClient\n")
            f.flush()
            r = check_module_safety(f.name)
        os.unlink(f.name)
        self.assertFalse(r["safe"])

    def test_95_detects_send_post_dm_pattern(self):
        from umh.workflows.safety import check_module_safety

        for func in ["send_dm", "send_message", "post_content"]:
            with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
                f.write(f"def {func}():\n    pass\n")
                f.flush()
                r = check_module_safety(f.name)
            os.unlink(f.name)
            self.assertFalse(r["safe"], f"{func} not detected")

    def test_96_detects_execution_engine_pattern(self):
        from umh.workflows.safety import check_module_safety

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("def execute():\n    pass\n")
            f.flush()
            r = check_module_safety(f.name)
        os.unlink(f.name)
        self.assertFalse(r["safe"])

    def test_97_detects_memory_promotion_pattern(self):
        from umh.workflows.safety import check_module_safety

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("def promote_memory():\n    pass\n")
            f.flush()
            r = check_module_safety(f.name)
        os.unlink(f.name)
        self.assertFalse(r["safe"])

    def test_98_detects_governance_mutation_pattern(self):
        from umh.workflows.safety import check_module_safety

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("from umh.governance.engine import approve\n")
            f.flush()
            r = check_module_safety(f.name)
        os.unlink(f.name)
        self.assertFalse(r["safe"])

    def test_99_detects_live_model_provider_call(self):
        from umh.workflows.safety import check_module_safety

        for pattern in ["fetch", "scrape", "crawl"]:
            with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
                f.write(f"def {pattern}():\n    pass\n")
                f.flush()
                r = check_module_safety(f.name)
            os.unlink(f.name)
            self.assertFalse(r["safe"], f"{pattern} not detected")

    def test_100_plan_has_no_external_execution(self):
        from umh.workflows.north_star_harness import build_north_star_test_plan
        from umh.workflows.safety import validate_plan_has_no_external_execution

        plan = build_north_star_test_plan(date="2026-05-04")
        for sub in [plan.business_plan, plan.self_build_plan]:
            r = validate_plan_has_no_external_execution(sub)
            self.assertTrue(r["safe"], f"Plan has external execution: {r}")

    def test_101_tasks_are_manual_advisory_only(self):
        from umh.workflows.north_star_harness import build_north_star_test_plan
        from umh.workflows.safety import validate_task_is_manual_or_advisory

        plan = build_north_star_test_plan(date="2026-05-04")
        for sub in [plan.business_plan, plan.self_build_plan]:
            for task in sub.tasks:
                r = validate_task_is_manual_or_advisory(task)
                self.assertTrue(r["safe"], f"Task '{task.title}' not manual: {r}")

    def test_102_report_has_no_execution(self):
        from umh.workflows.north_star_harness import run_north_star_review
        from umh.workflows.safety import validate_report_has_no_execution

        biz = WorkflowResult(
            result_id="br1", date="2026-05-04", track=WorkflowTrack.BUSINESS_REVENUE,
            completed_tasks=["t1"],
        )
        sb = WorkflowResult(
            result_id="sbr1", date="2026-05-04", track=WorkflowTrack.SELF_BUILD,
            completed_tasks=["st1"],
        )
        report = run_north_star_review(biz, sb)
        r = validate_report_has_no_execution(report)
        self.assertTrue(r["safe"], f"Report has execution: {r}")


# ═══════════════════════════════════════════════════════════════════════
# Regression
# ═══════════════════════════════════════════════════════════════════════


class TestRegression(unittest.TestCase):
    def test_103_phase87b_importable(self):
        from umh.ingestion.contracts import SourceClass

        self.assertTrue(hasattr(SourceClass, "EMAIL"))

    def test_104_phase87a_importable(self):
        from umh.distributed.contracts import RuntimeNodeType

        self.assertTrue(hasattr(RuntimeNodeType, "VPS"))

    def test_105_phase87_importable(self):
        from umh.leverage.contracts import LeverageType

        self.assertTrue(hasattr(LeverageType, "CODE_SOFTWARE"))

    def test_106_phase86_importable(self):
        from umh.tomorrow.contracts import DailyObjective

        self.assertTrue(hasattr(DailyObjective, "objective_id"))

    def test_107_phase85b_importable(self):
        from umh.council.archetypes import ThinkerArchetype

        self.assertTrue(hasattr(ThinkerArchetype, "FIRST_PRINCIPLES"))

    def test_existing_phase88_test_plan_still_works(self):
        from umh.workflows.test_harness import build_first_workflow_test_plan

        plan = build_first_workflow_test_plan(date="2026-05-04")
        self.assertIsInstance(plan, DailyWorkflowPlan)
        self.assertTrue(len(plan.tasks) > 0)

    def test_existing_phase88_first_workflow_still_works(self):
        from umh.workflows.first_workflow import build_personal_brand_to_initiate_arena_workflow

        wf = build_personal_brand_to_initiate_arena_workflow()
        self.assertEqual(len(wf.stages), 16)


if __name__ == "__main__":
    unittest.main()
