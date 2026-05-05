"""Phase 86 — EOS Tomorrow Operating Loop tests.

Tests all Phase 86 modules: contracts, orchestrator, first workflow template,
views, and safety. Includes full pipeline test and Phase 75B–86 regression.
"""

import ast
import pathlib
import unittest
from unittest.mock import patch

import sys

sys.path.insert(0, "/opt/OS")

from umh.tomorrow.contracts import (
    DailyObjective,
    DailyReview,
    KPIDefinition,
    KPIType,
    LoopCadence,
    LoopPhase,
    ReviewOutcome,
    TomorrowHandoff,
    TomorrowLoopState,
    WorkflowStage,
    WorkflowStageStatus,
    WorkflowTemplate,
    normalize_kpi_type,
    normalize_loop_phase,
    normalize_review_outcome,
    normalize_stage_status,
    _loop_id,
)
from umh.tomorrow.orchestrator import (
    _VALID_TRANSITIONS,
    add_objective,
    complete_loop,
    initialize_loop,
    record_objective_completion,
    run_brief,
    run_close,
    run_full_cycle,
    run_handoff,
    run_prepare,
    run_review,
    start_execute,
)
from umh.tomorrow.first_workflow import build_first_workflow_template
from umh.tomorrow.views import (
    DailyBriefView,
    TomorrowLoopView,
    WorkflowTemplateView,
    brief_from_state,
    loop_state_to_view,
    template_to_view,
)
from umh.tomorrow.safety import (
    TomorrowSafetyResult,
    validate_tomorrow_module_boundaries,
)


# ─── Helper ─────────────────────────────────────────────────────────


def _make_template(stage_count: int = 3) -> WorkflowTemplate:
    stages = []
    for i in range(1, stage_count + 1):
        stages.append(
            WorkflowStage(
                stage_id=f"stg_{i}",
                stage_number=i,
                name=f"Stage {i}",
                objective=f"Do stage {i}",
                owner="test_owner",
                status=WorkflowStageStatus.ACTIVE if i <= 2 else WorkflowStageStatus.NOT_STARTED,
            )
        )
    kpis = [
        KPIDefinition(kpi_id="kpi_1", name="Test KPI", kpi_type=KPIType.COUNT, target="10+"),
    ]
    return WorkflowTemplate(
        template_id="tmpl_test",
        name="Test Template",
        description="Test workflow",
        stages=stages,
        kpis=kpis,
        cadence=LoopCadence.DAILY,
        owner="test_owner",
        entity="test_entity",
    )


# ═══════════════════════════════════════════════════════════════════
#  1. CONTRACT TESTS
# ═══════════════════════════════════════════════════════════════════


class TestContractEnums(unittest.TestCase):
    def test_loop_phase_values(self):
        expected = {
            "not_started",
            "prepare",
            "brief",
            "execute",
            "review",
            "close",
            "handoff",
            "completed",
            "failed",
            "unknown",
        }
        self.assertEqual({m.value for m in LoopPhase}, expected)

    def test_workflow_stage_status_values(self):
        expected = {"not_started", "active", "blocked", "completed", "skipped", "unknown"}
        self.assertEqual({m.value for m in WorkflowStageStatus}, expected)

    def test_kpi_type_values(self):
        expected = {"count", "rate", "currency", "duration", "percentage", "boolean", "unknown"}
        self.assertEqual({m.value for m in KPIType}, expected)

    def test_review_outcome_values(self):
        expected = {"on_track", "needs_adjustment", "blocked", "critical", "unknown"}
        self.assertEqual({m.value for m in ReviewOutcome}, expected)

    def test_loop_cadence_values(self):
        expected = {"daily", "weekly", "unknown"}
        self.assertEqual({m.value for m in LoopCadence}, expected)

    def test_all_enums_have_unknown(self):
        for enum_cls in [LoopPhase, WorkflowStageStatus, KPIType, ReviewOutcome, LoopCadence]:
            self.assertIn(
                "unknown", {m.value for m in enum_cls}, f"{enum_cls.__name__} missing UNKNOWN"
            )


class TestContractNormalization(unittest.TestCase):
    def test_normalize_loop_phase(self):
        self.assertEqual(normalize_loop_phase("prepare"), LoopPhase.PREPARE)
        self.assertEqual(normalize_loop_phase("EXECUTE"), LoopPhase.EXECUTE)
        self.assertEqual(normalize_loop_phase(" brief "), LoopPhase.BRIEF)
        self.assertEqual(normalize_loop_phase("garbage"), LoopPhase.UNKNOWN)

    def test_normalize_stage_status(self):
        self.assertEqual(normalize_stage_status("active"), WorkflowStageStatus.ACTIVE)
        self.assertEqual(normalize_stage_status("not_started"), WorkflowStageStatus.NOT_STARTED)
        self.assertEqual(normalize_stage_status("nope"), WorkflowStageStatus.UNKNOWN)

    def test_normalize_kpi_type(self):
        self.assertEqual(normalize_kpi_type("count"), KPIType.COUNT)
        self.assertEqual(normalize_kpi_type("PERCENTAGE"), KPIType.PERCENTAGE)
        self.assertEqual(normalize_kpi_type("bad"), KPIType.UNKNOWN)

    def test_normalize_review_outcome(self):
        self.assertEqual(normalize_review_outcome("on_track"), ReviewOutcome.ON_TRACK)
        self.assertEqual(normalize_review_outcome("blocked"), ReviewOutcome.BLOCKED)
        self.assertEqual(normalize_review_outcome("fake"), ReviewOutcome.UNKNOWN)

    def test_loop_id_format(self):
        lid = _loop_id("test")
        self.assertTrue(lid.startswith("test_"))
        self.assertTrue(len(lid) > 5)


class TestContractDataclasses(unittest.TestCase):
    def test_kpi_definition_to_dict(self):
        k = KPIDefinition(kpi_id="k1", name="Revenue", kpi_type=KPIType.CURRENCY, target="$10K")
        d = k.to_dict()
        self.assertEqual(d["kpi_id"], "k1")
        self.assertEqual(d["kpi_type"], "currency")

    def test_workflow_stage_to_dict(self):
        s = WorkflowStage(stage_id="s1", stage_number=1, name="Test", objective="Do thing")
        d = s.to_dict()
        self.assertEqual(d["stage_id"], "s1")
        self.assertEqual(d["status"], "not_started")

    def test_workflow_template_properties(self):
        t = _make_template(5)
        self.assertEqual(t.stage_count, 5)
        self.assertEqual(t.kpi_count, 1)

    def test_daily_objective_to_dict(self):
        o = DailyObjective(objective_id="o1", description="Test", priority="high")
        d = o.to_dict()
        self.assertEqual(d["priority"], "high")
        self.assertFalse(d["completed"])

    def test_daily_review_completion_rate(self):
        r = DailyReview(objectives_completed=3, objectives_total=10)
        self.assertAlmostEqual(r.completion_rate, 0.3)

    def test_daily_review_completion_rate_zero_total(self):
        r = DailyReview(objectives_completed=0, objectives_total=0)
        self.assertAlmostEqual(r.completion_rate, 0.0)

    def test_tomorrow_handoff_to_dict(self):
        h = TomorrowHandoff(
            handoff_id="h1",
            date="2026-05-03",
            continuity_notes=["keep going"],
            unresolved=["fix bug"],
        )
        d = h.to_dict()
        self.assertEqual(d["date"], "2026-05-03")
        self.assertEqual(len(d["continuity_notes"]), 1)

    def test_loop_state_properties(self):
        s = TomorrowLoopState(
            loop_id="l1",
            date="2026-05-03",
            phase=LoopPhase.EXECUTE,
            objectives=[
                DailyObjective(objective_id="o1", completed=True),
                DailyObjective(objective_id="o2", completed=False),
            ],
        )
        self.assertEqual(s.objective_count, 2)
        self.assertEqual(s.completed_count, 1)
        self.assertFalse(s.is_terminal)

    def test_loop_state_terminal(self):
        s = TomorrowLoopState(phase=LoopPhase.COMPLETED)
        self.assertTrue(s.is_terminal)
        s2 = TomorrowLoopState(phase=LoopPhase.FAILED)
        self.assertTrue(s2.is_terminal)

    def test_loop_state_to_dict(self):
        s = TomorrowLoopState(loop_id="l1", date="2026-05-03", phase=LoopPhase.BRIEF)
        d = s.to_dict()
        self.assertEqual(d["phase"], "brief")
        self.assertIsNone(d["review"])
        self.assertIsNone(d["handoff"])


# ═══════════════════════════════════════════════════════════════════
#  2. ORCHESTRATOR TESTS
# ═══════════════════════════════════════════════════════════════════


class TestOrchestratorTransitions(unittest.TestCase):
    def test_valid_transitions_complete(self):
        for phase in LoopPhase:
            if phase == LoopPhase.UNKNOWN:
                continue
            self.assertIn(phase, _VALID_TRANSITIONS)

    def test_terminal_phases_have_no_transitions(self):
        self.assertEqual(len(_VALID_TRANSITIONS[LoopPhase.COMPLETED]), 0)
        self.assertEqual(len(_VALID_TRANSITIONS[LoopPhase.FAILED]), 0)

    def test_every_non_terminal_can_fail(self):
        for phase in LoopPhase:
            if phase not in (LoopPhase.COMPLETED, LoopPhase.FAILED, LoopPhase.UNKNOWN):
                self.assertIn(LoopPhase.FAILED, _VALID_TRANSITIONS[phase])

    def test_happy_path_transitions(self):
        happy = [
            LoopPhase.NOT_STARTED,
            LoopPhase.PREPARE,
            LoopPhase.BRIEF,
            LoopPhase.EXECUTE,
            LoopPhase.REVIEW,
            LoopPhase.CLOSE,
            LoopPhase.HANDOFF,
            LoopPhase.COMPLETED,
        ]
        for i in range(len(happy) - 1):
            self.assertIn(happy[i + 1], _VALID_TRANSITIONS[happy[i]])


class TestOrchestratorInitialize(unittest.TestCase):
    def test_basic_initialization(self):
        t = _make_template()
        state = initialize_loop(t, date="2026-05-03")
        self.assertEqual(state.date, "2026-05-03")
        self.assertEqual(state.phase, LoopPhase.NOT_STARTED)
        self.assertEqual(state.template_id, "tmpl_test")

    def test_initialization_with_handoff(self):
        t = _make_template()
        handoff = TomorrowHandoff(
            handoff_id="h1",
            tomorrow_objectives=[
                DailyObjective(objective_id="prev_o1", description="Carry forward"),
            ],
            blockers_carried=["unresolved bug"],
        )
        state = initialize_loop(t, previous_handoff=handoff)
        self.assertEqual(len(state.objectives), 1)
        self.assertEqual(state.objectives[0].description, "Carry forward")
        self.assertTrue(any("unresolved bug" in w for w in state.warnings))

    def test_initialization_auto_date(self):
        t = _make_template()
        state = initialize_loop(t)
        self.assertTrue(len(state.date) == 10)  # YYYY-MM-DD


class TestOrchestratorPhases(unittest.TestCase):
    def test_prepare_generates_objectives(self):
        t = _make_template(4)
        state = initialize_loop(t, date="2026-05-03")
        state = run_prepare(state, t)
        self.assertEqual(state.phase, LoopPhase.PREPARE)
        self.assertTrue(len(state.objectives) > 0)

    def test_prepare_skips_if_objectives_exist(self):
        t = _make_template()
        handoff = TomorrowHandoff(
            tomorrow_objectives=[DailyObjective(description="From yesterday")],
        )
        state = initialize_loop(t, previous_handoff=handoff)
        obj_count_before = len(state.objectives)
        state = run_prepare(state, t)
        self.assertEqual(len(state.objectives), obj_count_before)

    def test_brief_produces_metadata(self):
        t = _make_template()
        state = initialize_loop(t)
        state = run_prepare(state, t)
        state = run_brief(state, t)
        self.assertEqual(state.phase, LoopPhase.BRIEF)
        self.assertIn("brief", state.metadata)
        self.assertIn("active_stages", state.metadata["brief"])

    def test_execute_phase(self):
        t = _make_template()
        state = initialize_loop(t)
        state = run_prepare(state, t)
        state = run_brief(state, t)
        state = start_execute(state)
        self.assertEqual(state.phase, LoopPhase.EXECUTE)

    def test_objective_completion(self):
        t = _make_template()
        state = initialize_loop(t)
        state = run_prepare(state, t)
        state = run_brief(state, t)
        state = start_execute(state)
        obj_id = state.objectives[0].objective_id
        result = record_objective_completion(state, obj_id, "Done!")
        self.assertTrue(result)
        self.assertTrue(state.objectives[0].completed)
        self.assertEqual(state.objectives[0].result, "Done!")

    def test_objective_completion_not_found(self):
        t = _make_template()
        state = initialize_loop(t)
        state = run_prepare(state, t)
        result = record_objective_completion(state, "nonexistent")
        self.assertFalse(result)

    def test_add_objective(self):
        t = _make_template()
        state = initialize_loop(t)
        state = run_prepare(state, t)
        before = len(state.objectives)
        obj = add_objective(state, "New objective", priority="high")
        self.assertEqual(len(state.objectives), before + 1)
        self.assertEqual(obj.priority, "high")

    def test_review_on_track(self):
        t = _make_template()
        state = initialize_loop(t)
        state = run_prepare(state, t)
        state = run_brief(state, t)
        state = start_execute(state)
        for obj in state.objectives:
            obj.completed = True
        state = run_review(state, what_worked=["everything"])
        self.assertEqual(state.phase, LoopPhase.REVIEW)
        self.assertIsNotNone(state.review)
        self.assertEqual(state.review.outcome, ReviewOutcome.ON_TRACK)

    def test_review_blocked(self):
        t = _make_template()
        state = initialize_loop(t)
        state = run_prepare(state, t)
        state = run_brief(state, t)
        state = start_execute(state)
        state = run_review(state, blockers=["waiting on vendor"])
        self.assertEqual(state.review.outcome, ReviewOutcome.BLOCKED)

    def test_review_critical(self):
        t = _make_template(5)
        state = initialize_loop(t)
        state = run_prepare(state, t)
        state = run_brief(state, t)
        state = start_execute(state)
        state = run_review(state)
        self.assertEqual(state.review.outcome, ReviewOutcome.CRITICAL)

    def test_close_sets_priorities(self):
        t = _make_template()
        state = initialize_loop(t)
        state = run_prepare(state, t)
        state = run_brief(state, t)
        state = start_execute(state)
        state = run_review(state)
        state = run_close(state, tomorrow_priorities=["Do X", "Do Y"])
        self.assertEqual(state.phase, LoopPhase.CLOSE)
        self.assertEqual(state.review.tomorrow_priorities, ["Do X", "Do Y"])

    def test_handoff_produces_data(self):
        t = _make_template()
        state = initialize_loop(t)
        state = run_prepare(state, t)
        state = run_brief(state, t)
        state = start_execute(state)
        state = run_review(state, blockers=["bug"])
        state = run_close(state, tomorrow_priorities=["Fix bug"])
        state = run_handoff(state, t)
        self.assertEqual(state.phase, LoopPhase.HANDOFF)
        self.assertIsNotNone(state.handoff)
        self.assertTrue(len(state.handoff.tomorrow_objectives) > 0)
        self.assertEqual(state.handoff.blockers_carried, ["bug"])

    def test_complete(self):
        t = _make_template()
        state = initialize_loop(t)
        state = run_prepare(state, t)
        state = run_brief(state, t)
        state = start_execute(state)
        state = run_review(state)
        state = run_close(state)
        state = run_handoff(state, t)
        state = complete_loop(state)
        self.assertEqual(state.phase, LoopPhase.COMPLETED)
        self.assertTrue(state.is_terminal)

    def test_invalid_transition_adds_warning(self):
        t = _make_template()
        state = initialize_loop(t)
        state = run_review(state)  # can't review from NOT_STARTED
        self.assertEqual(state.phase, LoopPhase.NOT_STARTED)
        self.assertTrue(any("Cannot review" in w for w in state.warnings))


class TestOrchestratorFullCycle(unittest.TestCase):
    def test_full_cycle_completes(self):
        t = _make_template()
        state = run_full_cycle(
            t,
            date="2026-05-03",
            what_worked=["good day"],
            blockers=["one issue"],
            tomorrow_priorities=["priority 1"],
        )
        self.assertEqual(state.phase, LoopPhase.COMPLETED)
        self.assertTrue(state.is_terminal)
        self.assertIsNotNone(state.review)
        self.assertIsNotNone(state.handoff)
        self.assertTrue(len(state.phase_transitions) >= 7)

    def test_full_cycle_produces_handoff(self):
        t = _make_template()
        state = run_full_cycle(t, tomorrow_priorities=["Next thing"])
        self.assertTrue(len(state.handoff.tomorrow_objectives) > 0)

    def test_two_day_continuity(self):
        t = _make_template()
        day1 = run_full_cycle(t, date="2026-05-03", tomorrow_priorities=["Continue X"])
        day2 = initialize_loop(t, date="2026-05-04", previous_handoff=day1.handoff)
        self.assertTrue(len(day2.objectives) > 0)
        has_continue = any("Continue X" in o.description for o in day2.objectives)
        self.assertTrue(has_continue)


# ═══════════════════════════════════════════════════════════════════
#  3. FIRST WORKFLOW TEMPLATE TESTS
# ═══════════════════════════════════════════════════════════════════


class TestFirstWorkflowTemplate(unittest.TestCase):
    def test_template_has_16_stages(self):
        t = build_first_workflow_template()
        self.assertEqual(t.stage_count, 16)

    def test_template_has_17_kpis(self):
        t = build_first_workflow_template()
        self.assertEqual(t.kpi_count, 17)

    def test_template_name(self):
        t = build_first_workflow_template()
        self.assertIn("Initiate Arena", t.name)
        self.assertIn("Personal Brand", t.name)

    def test_stage_names_match_spec(self):
        t = build_first_workflow_template()
        names = [s.name for s in t.stages]
        self.assertIn("Content Strategy", names)
        self.assertIn("Publishing", names)
        self.assertIn("Lead Capture", names)
        self.assertIn("Close / Payment", names)
        self.assertIn("Onboarding", names)
        self.assertIn("Initiate Arena Fulfillment", names)
        self.assertIn("Testimonial / Case Study", names)
        self.assertIn("Upsell Path to Game of Lyfe", names)
        self.assertIn("End-of-Day Review", names)
        self.assertIn("Weekly Improvement Loop", names)

    def test_stages_are_numbered_sequentially(self):
        t = build_first_workflow_template()
        for i, stage in enumerate(t.stages, 1):
            self.assertEqual(stage.stage_number, i)

    def test_all_stages_start_not_started(self):
        t = build_first_workflow_template()
        for stage in t.stages:
            self.assertEqual(stage.status, WorkflowStageStatus.NOT_STARTED)

    def test_all_stages_have_owner(self):
        t = build_first_workflow_template()
        for stage in t.stages:
            self.assertEqual(stage.owner, "antony")

    def test_stages_have_objectives(self):
        t = build_first_workflow_template()
        for stage in t.stages:
            self.assertTrue(len(stage.objective) > 0)

    def test_stages_have_failure_modes(self):
        t = build_first_workflow_template()
        for stage in t.stages:
            self.assertTrue(len(stage.failure_modes) > 0)

    def test_kpi_types_valid(self):
        t = build_first_workflow_template()
        for kpi in t.kpis:
            self.assertNotEqual(kpi.kpi_type, KPIType.UNKNOWN)

    def test_template_to_dict(self):
        t = build_first_workflow_template()
        d = t.to_dict()
        self.assertEqual(len(d["stages"]), 16)
        self.assertEqual(len(d["kpis"]), 17)
        self.assertEqual(d["cadence"], "daily")

    def test_template_metadata(self):
        t = build_first_workflow_template()
        self.assertIn("binding_constraint", t.metadata)
        self.assertIn("entities_touched", t.metadata)
        self.assertEqual(len(t.metadata["entities_touched"]), 4)


# ═══════════════════════════════════════════════════════════════════
#  4. VIEW TESTS
# ═══════════════════════════════════════════════════════════════════


class TestViews(unittest.TestCase):
    def test_loop_state_to_view(self):
        t = _make_template()
        state = run_full_cycle(t)
        view = loop_state_to_view(state, template_name="Test")
        self.assertIsInstance(view, TomorrowLoopView)
        self.assertEqual(view.phase, "completed")
        self.assertEqual(view.template_name, "Test")
        self.assertTrue(view.has_handoff)

    def test_loop_view_to_dict(self):
        view = TomorrowLoopView(
            loop_id="l1",
            date="2026-05-03",
            phase="execute",
            objective_count=5,
            completed_count=2,
        )
        d = view.to_dict()
        self.assertEqual(d["phase"], "execute")
        self.assertEqual(d["completion_rate"], 0.0)

    def test_template_to_view(self):
        t = build_first_workflow_template()
        view = template_to_view(t)
        self.assertIsInstance(view, WorkflowTemplateView)
        self.assertEqual(view.stage_count, 16)
        self.assertEqual(view.kpi_count, 17)
        self.assertIn("Content Strategy", view.stage_names)

    def test_template_view_to_dict(self):
        view = WorkflowTemplateView(
            template_id="t1",
            name="Test",
            stage_count=5,
        )
        d = view.to_dict()
        self.assertEqual(d["stage_count"], 5)

    def test_brief_from_state(self):
        t = _make_template()
        state = initialize_loop(t)
        state = run_prepare(state, t)
        state = run_brief(state, t)
        brief = brief_from_state(state)
        self.assertIsInstance(brief, DailyBriefView)
        self.assertTrue(brief.objective_count > 0)

    def test_brief_view_to_dict(self):
        brief = DailyBriefView(
            date="2026-05-03",
            objective_count=3,
            active_stages=["Stage 1"],
        )
        d = brief.to_dict()
        self.assertEqual(d["objective_count"], 3)


# ═══════════════════════════════════════════════════════════════════
#  5. SAFETY TESTS
# ═══════════════════════════════════════════════════════════════════


class TestSafety(unittest.TestCase):
    def test_safety_validation_passes(self):
        result = validate_tomorrow_module_boundaries()
        self.assertTrue(result.safe, f"Violations: {result.violations}")
        self.assertTrue(result.modules_checked >= 4)

    def test_safety_result_to_dict(self):
        result = validate_tomorrow_module_boundaries()
        d = result.to_dict()
        self.assertIn("safe", d)
        self.assertIn("modules_checked", d)

    def test_no_forbidden_imports_manual(self):
        tomorrow_dir = pathlib.Path("/opt/OS/umh/tomorrow")
        forbidden = {
            "subprocess",
            "requests",
            "httpx",
            "aiohttp",
            "selenium",
            "playwright",
            "smtplib",
            "telegram",
            "discord",
        }
        for py_file in sorted(tomorrow_dir.glob("*.py")):
            if py_file.name == "__init__.py":
                continue
            source = py_file.read_text()
            tree = ast.parse(source)
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported.add(node.module.split(".")[0])
            for lib in forbidden:
                self.assertNotIn(
                    lib,
                    imported,
                    f"{py_file.name} imports forbidden library '{lib}'",
                )


# ═══════════════════════════════════════════════════════════════════
#  6. FULL PIPELINE + INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════


class TestFullPipeline(unittest.TestCase):
    def test_full_pipeline_with_first_workflow(self):
        """End-to-end: build template → init loop → full cycle → verify all fields."""
        template = build_first_workflow_template()
        self.assertEqual(template.stage_count, 16)
        self.assertEqual(template.kpi_count, 17)

        state = run_full_cycle(
            template,
            date="2026-05-03",
            what_worked=["content was strong"],
            what_didnt=["DM response rate low"],
            blockers=["no payment link yet"],
            tomorrow_priorities=["Set up Stripe", "Record 3 videos"],
        )

        self.assertEqual(state.phase, LoopPhase.COMPLETED)
        self.assertTrue(state.is_terminal)
        self.assertIsNotNone(state.review)
        self.assertIsNotNone(state.handoff)
        self.assertEqual(state.review.what_worked, ["content was strong"])
        self.assertEqual(state.review.what_didnt, ["DM response rate low"])
        self.assertEqual(state.review.blockers, ["no payment link yet"])
        self.assertEqual(state.handoff.blockers_carried, ["no payment link yet"])

        has_stripe = any("Stripe" in o.description for o in state.handoff.tomorrow_objectives)
        self.assertTrue(has_stripe)

        view = loop_state_to_view(state, template_name=template.name)
        self.assertEqual(view.phase, "completed")
        self.assertTrue(view.has_handoff)
        d = view.to_dict()
        self.assertIn("loop_id", d)

    def test_multi_day_continuity(self):
        """Three-day continuity test: day1 → day2 → day3 with handoff chain."""
        template = build_first_workflow_template()

        day1 = run_full_cycle(template, date="2026-05-03", tomorrow_priorities=["A", "B"])
        day2 = initialize_loop(template, date="2026-05-04", previous_handoff=day1.handoff)
        day2 = run_prepare(day2, template)
        day2 = run_brief(day2, template)
        day2 = start_execute(day2)
        for obj in day2.objectives[:2]:
            record_objective_completion(day2, obj.objective_id, "Done")
        day2 = run_review(day2)
        day2 = run_close(day2, tomorrow_priorities=["C"])
        day2 = run_handoff(day2, template)
        day2 = complete_loop(day2)

        day3 = initialize_loop(template, date="2026-05-05", previous_handoff=day2.handoff)
        self.assertTrue(len(day3.objectives) > 0)
        self.assertEqual(day3.date, "2026-05-05")


# ═══════════════════════════════════════════════════════════════════
#  7. REGRESSION TESTS
# ═══════════════════════════════════════════════════════════════════


class TestPhase86Regression(unittest.TestCase):
    """Verify all Phase 75B–86 modules remain importable."""

    def test_phase75b_importable(self):
        from umh.execution.engine import dispatch_prompt  # noqa: F401

    def test_phase76_importable(self):
        from umh.adapters.registry import AdapterRegistry  # noqa: F401

    def test_phase77_importable(self):
        from umh.workstation.profile import WorkstationProfile  # noqa: F401

    def test_phase78_importable(self):
        from umh.feedback.outcome import OutcomeRecord  # noqa: F401

    def test_phase79_importable(self):
        from umh.observability.system_status import SystemStatus  # noqa: F401

    def test_phase80_importable(self):
        from umh.registry.contracts import RegistryType  # noqa: F401

    def test_phase81_importable(self):
        from umh.ontology.laws import UniversalLaw  # noqa: F401

    def test_phase82_importable(self):
        from umh.storage.backend import StorageBackend  # noqa: F401

    def test_phase84_importable(self):
        from umh.control.api import app  # noqa: F401

    def test_phase84a_importable(self):
        from umh.ontology.polarity_synthesis import PolaritySynthesis  # noqa: F401

    def test_phase85_importable(self):
        from umh.council.deliberation import deliberate  # noqa: F401

    def test_phase85b_importable(self):
        from umh.council.archetypes import get_all_thinker_profiles  # noqa: F401
        from umh.council.adversarial import run_adversarial_assessment  # noqa: F401
        from umh.council.synthesis_protocol import synthesize_enhanced_advisory  # noqa: F401

    def test_phase86_importable(self):
        from umh.tomorrow.contracts import TomorrowLoopState  # noqa: F401
        from umh.tomorrow.orchestrator import run_full_cycle  # noqa: F401
        from umh.tomorrow.first_workflow import build_first_workflow_template  # noqa: F401
        from umh.tomorrow.views import loop_state_to_view  # noqa: F401
        from umh.tomorrow.safety import validate_tomorrow_module_boundaries  # noqa: F401


if __name__ == "__main__":
    unittest.main()
