"""Phase 88 — First Real Operating Workflow Test Harness v1.

Tests for contracts, first workflow, test harness, KPIs, daily results,
review, views, safety, strategy docs, and regression.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from umh.workflows.contracts import (
    DailyWorkflowPlan,
    DailyWorkflowResult,
    DailyWorkflowReview,
    KPIName,
    WorkflowDefinition,
    WorkflowKPIRecord,
    WorkflowStage,
    WorkflowStageDefinition,
    WorkflowStatus,
    WorkflowTask,
    normalize_kpi_name,
    normalize_workflow_stage,
    normalize_workflow_status,
)


class TestContractNormalizers(unittest.TestCase):
    def test_normalize_workflow_stage(self):
        self.assertEqual(
            normalize_workflow_stage("content_strategy"), WorkflowStage.CONTENT_STRATEGY
        )
        self.assertEqual(
            normalize_workflow_stage("CONTENT_STRATEGY"), WorkflowStage.CONTENT_STRATEGY
        )

    def test_normalize_workflow_status(self):
        self.assertEqual(normalize_workflow_status("planned"), WorkflowStatus.PLANNED)
        self.assertEqual(normalize_workflow_status("active"), WorkflowStatus.ACTIVE)

    def test_normalize_kpi_name(self):
        self.assertEqual(normalize_kpi_name("posts_published"), KPIName.POSTS_PUBLISHED)
        self.assertEqual(normalize_kpi_name("dms_opened"), KPIName.DMS_OPENED)

    def test_unknowns_degrade_safely(self):
        self.assertEqual(normalize_workflow_stage("nonsense"), WorkflowStage.UNKNOWN)
        self.assertEqual(normalize_workflow_status("nonsense"), WorkflowStatus.UNKNOWN)
        self.assertEqual(normalize_kpi_name("nonsense"), KPIName.UNKNOWN)


class TestContractSerialization(unittest.TestCase):
    def test_task_roundtrip(self):
        t = WorkflowTask(task_id="t1", stage=WorkflowStage.PUBLISHING, title="Publish")
        d = t.to_dict()
        t2 = WorkflowTask.from_dict(d)
        self.assertEqual(t2.stage, WorkflowStage.PUBLISHING)
        self.assertEqual(d["stage"], "publishing")

    def test_plan_roundtrip(self):
        p = DailyWorkflowPlan(plan_id="p1", date="2026-05-04")
        d = p.to_dict()
        p2 = DailyWorkflowPlan.from_dict(d)
        self.assertEqual(p2.date, "2026-05-04")

    def test_kpi_record_roundtrip(self):
        k = WorkflowKPIRecord(kpi_name=KPIName.DMS_OPENED, value=10.0, unit="count")
        d = k.to_dict()
        k2 = WorkflowKPIRecord.from_dict(d)
        self.assertEqual(k2.kpi_name, KPIName.DMS_OPENED)
        self.assertEqual(k2.value, 10.0)

    def test_result_roundtrip(self):
        r = DailyWorkflowResult(result_id="r1", date="2026-05-04")
        d = r.to_dict()
        r2 = DailyWorkflowResult.from_dict(d)
        self.assertEqual(r2.result_id, "r1")

    def test_review_roundtrip(self):
        rv = DailyWorkflowReview(review_id="rv1", date="2026-05-04", confidence=0.8)
        d = rv.to_dict()
        rv2 = DailyWorkflowReview.from_dict(d)
        self.assertEqual(rv2.confidence, 0.8)

    def test_workflow_definition_roundtrip(self):
        wf = WorkflowDefinition(workflow_id="wf1", name="Test", product="test_prod")
        d = wf.to_dict()
        wf2 = WorkflowDefinition.from_dict(d)
        self.assertEqual(wf2.product, "test_prod")

    def test_stage_definition_roundtrip(self):
        s = WorkflowStageDefinition(
            stage=WorkflowStage.CONTENT_STRATEGY,
            name="Content Strategy",
            objective="Choose angle",
        )
        d = s.to_dict()
        s2 = WorkflowStageDefinition.from_dict(d)
        self.assertEqual(s2.stage, WorkflowStage.CONTENT_STRATEGY)


class TestFirstWorkflow(unittest.TestCase):
    def setUp(self):
        from umh.workflows.first_workflow import build_personal_brand_to_initiate_arena_workflow

        self.wf = build_personal_brand_to_initiate_arena_workflow()

    def test_workflow_builds(self):
        self.assertIsInstance(self.wf, WorkflowDefinition)
        self.assertTrue(self.wf.workflow_id)

    def test_workflow_has_16_stages(self):
        self.assertEqual(len(self.wf.stages), 16)

    def test_includes_content_strategy(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.CONTENT_STRATEGY, stages)

    def test_includes_publishing(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.PUBLISHING, stages)

    def test_includes_dm_conversation(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.DM_CONVERSATION, stages)

    def test_includes_lead_capture(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.LEAD_CAPTURE, stages)

    def test_includes_qualification(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.QUALIFICATION, stages)

    def test_includes_sales_conversation(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.SALES_CONVERSATION, stages)

    def test_includes_onboarding(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.ONBOARDING, stages)

    def test_includes_fulfillment(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.FULFILLMENT, stages)

    def test_includes_testimonial_capture(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.TESTIMONIAL_CAPTURE, stages)

    def test_includes_end_of_day_review(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.END_OF_DAY_REVIEW, stages)

    def test_includes_weekly_improvement(self):
        stages = {s.stage for s in self.wf.stages}
        self.assertIn(WorkflowStage.WEEKLY_IMPROVEMENT, stages)

    def test_workflow_has_kpis(self):
        self.assertTrue(len(self.wf.kpis) > 0)

    def test_workflow_name(self):
        self.assertIn("Initiate Arena", self.wf.name)

    def test_workflow_product(self):
        self.assertEqual(self.wf.product, "initiate_arena")

    def test_stages_have_objectives(self):
        for s in self.wf.stages:
            self.assertTrue(s.objective, f"Stage {s.name} missing objective")

    def test_stages_have_expected_output(self):
        for s in self.wf.stages:
            self.assertTrue(s.expected_output, f"Stage {s.name} missing expected_output")


class TestTestHarness(unittest.TestCase):
    def setUp(self):
        from umh.workflows.test_harness import build_first_workflow_test_plan

        self.plan = build_first_workflow_test_plan(date="2026-05-04")

    def test_daily_plan_builds(self):
        self.assertIsInstance(self.plan, DailyWorkflowPlan)
        self.assertTrue(self.plan.plan_id)

    def test_daily_plan_includes_tasks(self):
        self.assertTrue(len(self.plan.tasks) > 0)

    def test_daily_plan_includes_highest_leverage_actions(self):
        self.assertTrue(len(self.plan.highest_leverage_actions) > 0)

    def test_daily_plan_includes_non_actions(self):
        self.assertTrue(len(self.plan.non_actions) > 0)

    def test_daily_plan_includes_kpis_to_track(self):
        self.assertTrue(len(self.plan.kpis_to_track) > 0)

    def test_daily_plan_includes_risks(self):
        self.assertTrue(len(self.plan.risks) > 0)

    def test_tasks_are_sorted_by_leverage(self):
        priorities = [t.metadata.get("leverage_priority", 99) for t in self.plan.tasks]
        self.assertEqual(priorities, sorted(priorities))

    def test_manual_result_template_builds(self):
        from umh.workflows.test_harness import build_manual_result_capture_template

        template = build_manual_result_capture_template(self.plan)
        self.assertIn("tasks", template)
        self.assertIn("kpis", template)
        self.assertEqual(len(template["tasks"]), len(self.plan.tasks))

    def test_validate_daily_result_empty(self):
        from umh.workflows.test_harness import validate_daily_result

        result = DailyWorkflowResult(result_id="r1", date="2026-05-04")
        v = validate_daily_result(result)
        self.assertFalse(v["valid"])
        self.assertTrue(len(v["warnings"]) > 0)

    def test_validate_daily_result_populated(self):
        from umh.workflows.test_harness import validate_daily_result

        result = DailyWorkflowResult(
            result_id="r1",
            date="2026-05-04",
            completed_tasks=["t1"],
            kpi_records=[WorkflowKPIRecord(kpi_name=KPIName.POSTS_PUBLISHED, value=1.0)],
        )
        v = validate_daily_result(result)
        self.assertTrue(v["valid"])


class TestKPIs(unittest.TestCase):
    def setUp(self):
        from umh.workflows.kpis import build_default_kpis_for_first_workflow

        self.kpis = build_default_kpis_for_first_workflow()

    def test_default_kpis_include_posts_published(self):
        names = {k.kpi_name for k in self.kpis}
        self.assertIn(KPIName.POSTS_PUBLISHED, names)

    def test_default_kpis_include_dms_opened(self):
        names = {k.kpi_name for k in self.kpis}
        self.assertIn(KPIName.DMS_OPENED, names)

    def test_default_kpis_include_leads_captured(self):
        names = {k.kpi_name for k in self.kpis}
        self.assertIn(KPIName.LEADS_CAPTURED, names)

    def test_default_kpis_include_calls_booked(self):
        names = {k.kpi_name for k in self.kpis}
        self.assertIn(KPIName.CALLS_BOOKED, names)

    def test_default_kpis_include_objections_captured(self):
        names = {k.kpi_name for k in self.kpis}
        self.assertIn(KPIName.OBJECTIONS_CAPTURED, names)

    def test_default_kpis_include_revenue(self):
        names = {k.kpi_name for k in self.kpis}
        self.assertIn(KPIName.REVENUE_COLLECTED, names)

    def test_default_kpis_include_bottlenecks(self):
        names = {k.kpi_name for k in self.kpis}
        self.assertIn(KPIName.BOTTLENECKS_FOUND, names)

    def test_create_kpi_record(self):
        from umh.workflows.kpis import create_kpi_record

        r = create_kpi_record(KPIName.DMS_OPENED, 15.0, "count", WorkflowStage.DM_CONVERSATION)
        self.assertEqual(r.kpi_name, KPIName.DMS_OPENED)
        self.assertEqual(r.value, 15.0)

    def test_validate_kpi_record_valid(self):
        from umh.workflows.kpis import validate_kpi_record

        r = WorkflowKPIRecord(kpi_name=KPIName.POSTS_PUBLISHED, value=1.0)
        v = validate_kpi_record(r)
        self.assertTrue(v["valid"])

    def test_validate_kpi_record_unknown(self):
        from umh.workflows.kpis import validate_kpi_record

        r = WorkflowKPIRecord(kpi_name=KPIName.UNKNOWN, value=1.0)
        v = validate_kpi_record(r)
        self.assertFalse(v["valid"])

    def test_summarize_kpis(self):
        from umh.workflows.kpis import summarize_kpis

        records = [
            WorkflowKPIRecord(kpi_name=KPIName.DMS_OPENED, value=10.0),
            WorkflowKPIRecord(kpi_name=KPIName.DMS_OPENED, value=5.0),
            WorkflowKPIRecord(kpi_name=KPIName.POSTS_PUBLISHED, value=1.0),
        ]
        s = summarize_kpis(records)
        self.assertEqual(s["totals"]["dms_opened"], 15.0)
        self.assertEqual(s["totals"]["posts_published"], 1.0)

    def test_compare_kpis_to_targets(self):
        from umh.workflows.kpis import compare_kpis_to_targets

        records = [
            WorkflowKPIRecord(kpi_name=KPIName.DMS_OPENED, value=15.0),
            WorkflowKPIRecord(kpi_name=KPIName.POSTS_PUBLISHED, value=1.0),
        ]
        c = compare_kpis_to_targets(records)
        self.assertIn("met", c)
        self.assertIn("missed", c)
        self.assertTrue(c["total_kpis"] > 0)


class TestDailyResults(unittest.TestCase):
    def setUp(self):
        from umh.workflows.daily_results import create_empty_daily_result
        from umh.workflows.test_harness import build_first_workflow_test_plan

        self.plan = build_first_workflow_test_plan(date="2026-05-04")
        self.result = create_empty_daily_result(self.plan)

    def test_empty_daily_result_creates(self):
        self.assertIsInstance(self.result, DailyWorkflowResult)
        self.assertEqual(self.result.date, "2026-05-04")

    def test_completed_task_can_be_added(self):
        from umh.workflows.daily_results import add_completed_task

        add_completed_task(self.result, "task_1")
        self.assertIn("task_1", self.result.completed_tasks)

    def test_skipped_task_can_be_added(self):
        from umh.workflows.daily_results import add_skipped_task

        add_skipped_task(self.result, "task_2", "no time")
        self.assertEqual(len(self.result.skipped_tasks), 1)
        self.assertEqual(self.result.skipped_tasks[0]["reason"], "no time")

    def test_objection_can_be_added(self):
        from umh.workflows.daily_results import add_objection

        add_objection(self.result, "Too expensive")
        self.assertIn("Too expensive", self.result.objections)

    def test_bottleneck_can_be_added(self):
        from umh.workflows.daily_results import add_bottleneck

        add_bottleneck(self.result, "No CRM system")
        self.assertIn("No CRM system", self.result.bottlenecks)

    def test_note_can_be_added(self):
        from umh.workflows.daily_results import add_note

        add_note(self.result, "Prospect mentioned competitor X")
        self.assertIn("Prospect mentioned competitor X", self.result.notes)

    def test_win_can_be_added(self):
        from umh.workflows.daily_results import add_win

        add_win(self.result, "Booked first call")
        self.assertIn("Booked first call", self.result.wins)

    def test_kpi_record_can_be_added(self):
        from umh.workflows.daily_results import add_kpi_record

        r = WorkflowKPIRecord(kpi_name=KPIName.DMS_OPENED, value=10.0)
        add_kpi_record(self.result, r)
        self.assertEqual(len(self.result.kpi_records), 1)


class TestReview(unittest.TestCase):
    def _build_populated_result(self):
        from umh.workflows.daily_results import (
            add_bottleneck,
            add_completed_task,
            add_objection,
            add_skipped_task,
            add_win,
            add_loss,
            add_kpi_record,
            create_empty_daily_result,
        )
        from umh.workflows.test_harness import build_first_workflow_test_plan

        plan = build_first_workflow_test_plan(date="2026-05-04")
        result = create_empty_daily_result(plan)
        for t in plan.tasks[:5]:
            add_completed_task(result, t.task_id)
        add_skipped_task(result, plan.tasks[5].task_id, "ran out of time")
        add_objection(result, "Too expensive")
        add_objection(result, "Not ready yet")
        add_bottleneck(result, "No CRM system")
        add_win(result, "Booked first call")
        add_loss(result, "Post got no engagement")
        add_kpi_record(result, WorkflowKPIRecord(kpi_name=KPIName.DMS_OPENED, value=8.0))
        add_kpi_record(result, WorkflowKPIRecord(kpi_name=KPIName.POSTS_PUBLISHED, value=1.0))
        return plan, result

    def test_review_builds(self):
        from umh.workflows.review import build_daily_workflow_review

        plan, result = self._build_populated_result()
        review = build_daily_workflow_review(plan, result)
        self.assertIsInstance(review, DailyWorkflowReview)
        self.assertTrue(review.review_id)

    def test_review_identifies_bottlenecks(self):
        from umh.workflows.review import build_daily_workflow_review

        plan, result = self._build_populated_result()
        review = build_daily_workflow_review(plan, result)
        self.assertTrue(len(review.bottlenecks) > 0)

    def test_review_recommends_next_actions(self):
        from umh.workflows.review import build_daily_workflow_review

        plan, result = self._build_populated_result()
        review = build_daily_workflow_review(plan, result)
        self.assertTrue(len(review.next_actions) > 0)

    def test_review_identifies_template_candidates(self):
        from umh.workflows.review import build_daily_workflow_review

        plan, result = self._build_populated_result()
        review = build_daily_workflow_review(plan, result)
        self.assertTrue(len(review.metadata.get("template_candidates", [])) > 0)

    def test_review_has_what_worked(self):
        from umh.workflows.review import build_daily_workflow_review

        plan, result = self._build_populated_result()
        review = build_daily_workflow_review(plan, result)
        self.assertTrue(len(review.what_worked) > 0)

    def test_review_has_lessons(self):
        from umh.workflows.review import build_daily_workflow_review

        plan, result = self._build_populated_result()
        review = build_daily_workflow_review(plan, result)
        self.assertTrue(len(review.lessons) > 0)

    def test_review_summary_not_empty(self):
        from umh.workflows.review import build_daily_workflow_review

        plan, result = self._build_populated_result()
        review = build_daily_workflow_review(plan, result)
        self.assertTrue(review.summary)

    def test_next_day_recommendations(self):
        from umh.workflows.test_harness import build_next_day_recommendations
        from umh.workflows.review import build_daily_workflow_review

        plan, result = self._build_populated_result()
        review = build_daily_workflow_review(plan, result)
        recs = build_next_day_recommendations(review)
        self.assertTrue(len(recs) > 0)

    def test_recommend_next_day_actions_fn(self):
        from umh.workflows.review import recommend_next_day_actions, build_daily_workflow_review

        plan, result = self._build_populated_result()
        review = build_daily_workflow_review(plan, result)
        actions = recommend_next_day_actions(review)
        self.assertTrue(len(actions) > 0)

    def test_identify_bottlenecks_fn(self):
        from umh.workflows.review import identify_bottlenecks

        result = DailyWorkflowResult(
            result_id="r1",
            date="2026-05-04",
            bottlenecks=["No CRM"],
            skipped_tasks=[{"task_id": "t1", "reason": "too slow"}],
        )
        bn = identify_bottlenecks(result)
        self.assertTrue(len(bn) >= 2)

    def test_identify_template_candidates_fn(self):
        from umh.workflows.review import identify_template_candidates

        result = DailyWorkflowResult(
            result_id="r1",
            date="2026-05-04",
            completed_tasks=["t1", "t2", "t3"],
            objections=["Too expensive"],
            bottlenecks=["No CRM"],
            kpi_records=[WorkflowKPIRecord(kpi_name=KPIName.DMS_OPENED, value=5.0)],
        )
        candidates = identify_template_candidates(result)
        self.assertTrue(len(candidates) >= 3)

    def test_extract_lessons(self):
        from umh.workflows.review import extract_lessons_from_result

        result = DailyWorkflowResult(
            result_id="r1",
            date="2026-05-04",
            objections=["Too expensive"],
            bottlenecks=["No CRM"],
            wins=["Booked call"],
        )
        lessons = extract_lessons_from_result(result)
        self.assertTrue(len(lessons) >= 2)


class TestViews(unittest.TestCase):
    def test_workflow_to_view(self):
        from umh.workflows.first_workflow import build_personal_brand_to_initiate_arena_workflow
        from umh.workflows.views import workflow_to_view

        wf = build_personal_brand_to_initiate_arena_workflow()
        v = workflow_to_view(wf)
        self.assertEqual(v.stage_count, 16)
        d = v.to_dict()
        self.assertNotIn("password", str(d).lower())
        self.assertNotIn("secret", str(d).lower())

    def test_task_to_view(self):
        from umh.workflows.views import task_to_view

        t = WorkflowTask(task_id="t1", stage=WorkflowStage.PUBLISHING, title="Publish")
        v = task_to_view(t)
        self.assertEqual(v.stage, "publishing")

    def test_plan_to_view(self):
        from umh.workflows.test_harness import build_first_workflow_test_plan
        from umh.workflows.views import plan_to_view

        plan = build_first_workflow_test_plan(date="2026-05-04")
        v = plan_to_view(plan)
        self.assertTrue(v.task_count > 0)
        self.assertTrue(v.kpi_count > 0)

    def test_result_to_view(self):
        from umh.workflows.views import result_to_view

        r = DailyWorkflowResult(
            result_id="r1",
            date="2026-05-04",
            completed_tasks=["t1", "t2"],
            objections=["obj1"],
        )
        v = result_to_view(r)
        self.assertEqual(v.completed_count, 2)
        self.assertEqual(v.objection_count, 1)

    def test_review_to_view(self):
        from umh.workflows.views import review_to_view

        rv = DailyWorkflowReview(
            review_id="rv1",
            date="2026-05-04",
            bottlenecks=["b1"],
            lessons=["l1", "l2"],
            next_actions=["a1"],
            confidence=0.7,
        )
        v = review_to_view(rv)
        self.assertEqual(v.bottleneck_count, 1)
        self.assertEqual(v.lesson_count, 2)
        self.assertEqual(v.confidence, 0.7)

    def test_dashboard_view_serializes(self):
        from umh.workflows.test_harness import build_first_workflow_test_plan
        from umh.workflows.views import build_first_workflow_dashboard_view

        plan = build_first_workflow_test_plan(date="2026-05-04")
        dv = build_first_workflow_dashboard_view(plan=plan)
        d = dv.to_dict()
        self.assertIn("workflow_name", d)
        self.assertTrue(d["stage_count"] > 0)
        self.assertTrue(d["task_count"] > 0)

    def test_views_omit_secrets(self):
        from umh.workflows.test_harness import build_first_workflow_test_plan
        from umh.workflows.views import build_first_workflow_dashboard_view

        plan = build_first_workflow_test_plan(date="2026-05-04")
        dv = build_first_workflow_dashboard_view(plan=plan)
        d_str = str(dv.to_dict()).lower()
        self.assertNotIn("password", d_str)
        self.assertNotIn("api_key", d_str)
        self.assertNotIn("secret", d_str)
        self.assertNotIn("credential", d_str)


class TestSafety(unittest.TestCase):
    def test_safety_scan_passes(self):
        from umh.workflows.safety import validate_workflow_modules_are_manual_only

        r = validate_workflow_modules_are_manual_only()
        self.assertTrue(r["all_safe"], f"Safety violations: {r}")
        self.assertTrue(r["modules_checked"] > 0)

    def test_safety_detects_requests(self):
        from umh.workflows.safety import check_module_safety

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("import requests\n")
            f.flush()
            r = check_module_safety(f.name)
        os.unlink(f.name)
        self.assertFalse(r["safe"])
        self.assertIn("requests", r["forbidden_imports"])

    def test_safety_detects_httpx(self):
        from umh.workflows.safety import check_module_safety

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("import httpx\n")
            f.flush()
            r = check_module_safety(f.name)
        os.unlink(f.name)
        self.assertFalse(r["safe"])

    def test_safety_detects_subprocess(self):
        from umh.workflows.safety import check_module_safety

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("import subprocess\n")
            f.flush()
            r = check_module_safety(f.name)
        os.unlink(f.name)
        self.assertFalse(r["safe"])
        self.assertIn("subprocess", r["forbidden_imports"])

    def test_safety_detects_send_pattern(self):
        from umh.workflows.safety import check_module_safety

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("def send_dm():\n    pass\n")
            f.flush()
            r = check_module_safety(f.name)
        os.unlink(f.name)
        self.assertFalse(r["safe"])
        self.assertIn("send_dm", r["execution_patterns"])

    def test_safety_detects_adapter_import(self):
        from umh.workflows.safety import check_module_safety

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("from umh.adapters.instagram import InstaClient\n")
            f.flush()
            r = check_module_safety(f.name)
        os.unlink(f.name)
        self.assertFalse(r["safe"])
        self.assertTrue(len(r["forbidden_module_prefixes"]) > 0)

    def test_plan_has_no_external_execution(self):
        from umh.workflows.safety import validate_plan_has_no_external_execution
        from umh.workflows.test_harness import build_first_workflow_test_plan

        plan = build_first_workflow_test_plan(date="2026-05-04")
        r = validate_plan_has_no_external_execution(plan)
        self.assertTrue(r["safe"])

    def test_tasks_are_manual_or_advisory(self):
        from umh.workflows.safety import validate_task_is_manual_or_advisory
        from umh.workflows.test_harness import build_first_workflow_test_plan

        plan = build_first_workflow_test_plan(date="2026-05-04")
        for task in plan.tasks:
            r = validate_task_is_manual_or_advisory(task)
            self.assertTrue(r["safe"], f"Task '{task.title}' not manual: {r}")

    def test_scan_forbidden_imports_clean(self):
        from umh.workflows.safety import scan_workflow_for_forbidden_imports

        violations = scan_workflow_for_forbidden_imports()
        self.assertEqual(violations, [])

    def test_scan_execution_patterns_clean(self):
        from umh.workflows.safety import scan_workflow_for_execution_patterns

        patterns = scan_workflow_for_execution_patterns()
        self.assertEqual(patterns, [])

    def test_nonexistent_dir_returns_warning(self):
        from umh.workflows.safety import validate_workflow_modules_are_manual_only

        r = validate_workflow_modules_are_manual_only("/tmp/nonexistent_88_dir")
        self.assertFalse(r["all_safe"])
        self.assertTrue(len(r["warnings"]) > 0)

    def test_empty_dir_returns_warning(self):
        from umh.workflows.safety import validate_workflow_modules_are_manual_only

        with tempfile.TemporaryDirectory() as td:
            r = validate_workflow_modules_are_manual_only(td)
        self.assertFalse(r["all_safe"])
        self.assertTrue(len(r["warnings"]) > 0)


class TestDocUpdates(unittest.TestCase):
    def test_operations_template_exists(self):
        self.assertTrue(
            os.path.isfile("/opt/OS/docs/operations/first_workflow_test_run_template.md")
        )

    def test_operations_template_has_kpi_section(self):
        with open("/opt/OS/docs/operations/first_workflow_test_run_template.md") as f:
            content = f.read()
        self.assertIn("KPI Targets", content)

    def test_operations_template_has_objections_section(self):
        with open("/opt/OS/docs/operations/first_workflow_test_run_template.md") as f:
            content = f.read()
        self.assertIn("Objections", content)

    def test_operations_template_has_bottlenecks_section(self):
        with open("/opt/OS/docs/operations/first_workflow_test_run_template.md") as f:
            content = f.read()
        self.assertIn("Bottlenecks", content)

    def test_operations_template_has_template_candidates(self):
        with open("/opt/OS/docs/operations/first_workflow_test_run_template.md") as f:
            content = f.read()
        self.assertIn("Template", content)

    def test_operations_template_has_improvements(self):
        with open("/opt/OS/docs/operations/first_workflow_test_run_template.md") as f:
            content = f.read()
        self.assertIn("Improvements", content)


class TestRegression(unittest.TestCase):
    def test_phase87b_importable(self):
        from umh.ingestion.contracts import SourceClass

        self.assertTrue(hasattr(SourceClass, "EMAIL"))

    def test_phase87a_importable(self):
        from umh.distributed.contracts import RuntimeNodeType

        self.assertTrue(hasattr(RuntimeNodeType, "VPS"))

    def test_phase87_importable(self):
        from umh.leverage.contracts import LeverageType

        self.assertTrue(hasattr(LeverageType, "CODE_SOFTWARE"))

    def test_phase86_importable(self):
        from umh.tomorrow.contracts import DailyObjective

        self.assertTrue(hasattr(DailyObjective, "objective_id"))


if __name__ == "__main__":
    unittest.main()
