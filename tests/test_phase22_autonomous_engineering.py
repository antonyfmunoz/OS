"""Phase 22 — Autonomous Engineering Loop tests.

Tests engineering intent classification, plan decomposition, work packet
generation, roadmap gap analysis, governance enforcement, and API routes.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.meta_ide.engineering_intent import (
    EngineeringIntent,
    EngineeringIntentType,
    EngineeringPlan,
    EngineeringPlanReceipt,
    EngineeringTask,
    classify_engineering_intent,
    extract_goal,
)
from substrate.meta_ide.engineering_planner import EngineeringPlanner
from substrate.meta_ide.engineering_work_generator import EngineeringWorkGenerator
from substrate.meta_ide.roadmap_gap_engine import (
    GapAnalysis,
    GapRecommendation,
    RoadmapGap,
    RoadmapGapEngine,
)


# ── Workcell A: Engineering Intent Contract ────────────────────────────


class TestEngineeringIntentClassification:
    """Test deterministic regex-based intent classification."""

    def test_feature_verbs(self) -> None:
        assert classify_engineering_intent("Build onboarding flow") == EngineeringIntentType.FEATURE
        assert classify_engineering_intent("create a new module") == EngineeringIntentType.FEATURE
        assert classify_engineering_intent("Add a health endpoint") == EngineeringIntentType.FEATURE
        assert (
            classify_engineering_intent("implement auth middleware")
            == EngineeringIntentType.FEATURE
        )

    def test_bugfix_verbs(self) -> None:
        assert classify_engineering_intent("Fix the login timeout") == EngineeringIntentType.BUGFIX
        assert (
            classify_engineering_intent("resolve the race condition")
            == EngineeringIntentType.BUGFIX
        )
        assert classify_engineering_intent("debug the auth error") == EngineeringIntentType.BUGFIX

    def test_refactor_verbs(self) -> None:
        assert (
            classify_engineering_intent("Refactor auth middleware")
            == EngineeringIntentType.REFACTOR
        )
        assert (
            classify_engineering_intent("simplify the query builder")
            == EngineeringIntentType.REFACTOR
        )
        assert (
            classify_engineering_intent("extract helper functions")
            == EngineeringIntentType.REFACTOR
        )

    def test_infrastructure_verbs(self) -> None:
        assert (
            classify_engineering_intent("Deploy to staging") == EngineeringIntentType.INFRASTRUCTURE
        )
        assert (
            classify_engineering_intent("configure the CI pipeline")
            == EngineeringIntentType.INFRASTRUCTURE
        )
        assert (
            classify_engineering_intent("migrate the database")
            == EngineeringIntentType.INFRASTRUCTURE
        )

    def test_research_verbs(self) -> None:
        assert (
            classify_engineering_intent("Research slow queries") == EngineeringIntentType.RESEARCH
        )
        assert (
            classify_engineering_intent("investigate memory leak") == EngineeringIntentType.RESEARCH
        )
        assert (
            classify_engineering_intent("analyze performance data")
            == EngineeringIntentType.RESEARCH
        )

    def test_default_to_feature(self) -> None:
        assert classify_engineering_intent("something unknown") == EngineeringIntentType.FEATURE
        assert classify_engineering_intent("") == EngineeringIntentType.FEATURE


class TestEngineeringIntentTypes:
    """Test dataclass shapes and defaults."""

    def test_intent_defaults(self) -> None:
        intent = EngineeringIntent()
        assert intent.intent_id.startswith("ei-")
        assert intent.raw_input == ""
        assert intent.intent_type == EngineeringIntentType.FEATURE
        assert intent.scope == []
        assert intent.estimated_risk == "low"

    def test_task_defaults(self) -> None:
        task = EngineeringTask()
        assert task.task_id.startswith("et-")
        assert task.dependencies == []
        assert task.risk_class == "low"

    def test_plan_defaults(self) -> None:
        plan = EngineeringPlan()
        assert plan.plan_id.startswith("ep-")
        assert plan.status == "draft"
        assert plan.tasks == []

    def test_receipt_defaults(self) -> None:
        receipt = EngineeringPlanReceipt()
        assert receipt.receipt_id.startswith("epr-")
        assert receipt.status == "planned"
        assert receipt.work_packet_ids == []

    def test_to_dict_roundtrip(self) -> None:
        intent = EngineeringIntent(raw_input="test", goal="test goal")
        d = intent.to_dict()
        assert d["raw_input"] == "test"
        assert d["goal"] == "test goal"
        assert d["intent_type"] == "feature"

    def test_plan_to_dict(self) -> None:
        task = EngineeringTask(title="t1", task_type="research")
        plan = EngineeringPlan(
            intent=EngineeringIntent(raw_input="test"),
            tasks=[task],
        )
        d = plan.to_dict()
        assert len(d["tasks"]) == 1
        assert d["status"] == "draft"
        assert d["intent"]["raw_input"] == "test"


class TestGoalExtraction:
    """Test imperative verb stripping."""

    def test_strip_build(self) -> None:
        assert extract_goal("Build onboarding flow") == "onboarding flow"

    def test_strip_fix(self) -> None:
        assert extract_goal("Fix the login timeout") == "the login timeout"

    def test_no_verb(self) -> None:
        assert extract_goal("something else") == "something else"

    def test_empty_input(self) -> None:
        assert extract_goal("") == ""


# ── Workcell B: Engineering Planner ────────────────────────────────────


class TestEngineeringPlanner:
    """Test deterministic plan creation."""

    def test_create_plan_feature(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Build a health endpoint")
        assert plan.status == "draft"
        assert plan.intent.intent_type == EngineeringIntentType.FEATURE
        assert plan.intent.goal == "a health endpoint"
        assert len(plan.tasks) == 5

    def test_create_plan_bugfix(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Fix the login timeout")
        assert plan.intent.intent_type == EngineeringIntentType.BUGFIX
        assert len(plan.tasks) == 3

    def test_create_plan_refactor(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Refactor auth middleware")
        assert plan.intent.intent_type == EngineeringIntentType.REFACTOR
        assert len(plan.tasks) == 4

    def test_create_plan_infrastructure(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Deploy to staging")
        assert plan.intent.intent_type == EngineeringIntentType.INFRASTRUCTURE
        assert len(plan.tasks) == 3

    def test_create_plan_research(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Research slow queries")
        assert plan.intent.intent_type == EngineeringIntentType.RESEARCH
        assert len(plan.tasks) == 3

    def test_dependency_graph_sequential(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Build a health endpoint")
        graph = plan.dependency_graph
        first_task_id = plan.tasks[0].task_id
        assert graph[first_task_id] == []
        for i in range(1, len(plan.tasks)):
            task = plan.tasks[i]
            assert graph[task.task_id] == [plan.tasks[i - 1].task_id]

    def test_risk_assessment_low_for_research_tasks(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Research slow queries")
        for task in plan.tasks:
            assert task.risk_class == "low"

    def test_risk_elevated_for_implementation(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Build a feature")
        impl_tasks = [t for t in plan.tasks if t.task_type == "implementation"]
        assert len(impl_tasks) == 1
        assert impl_tasks[0].risk_class == "medium"

    def test_high_risk_signals(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Build a database migration tool")
        assert plan.intent.estimated_risk == "high"

    def test_context_enrichment_none_engines(self) -> None:
        planner = EngineeringPlanner(
            workspace_engine=None,
            roadmap_intelligence=None,
            reality_engine=None,
        )
        plan = planner.create_plan("Add a test suite")
        assert plan.roadmap_context == {}
        assert plan.workspace_health == {}
        assert plan.engineering_risks == []

    def test_plan_stored_and_retrievable(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Build X")
        retrieved = planner.get_plan(plan.plan_id)
        assert retrieved is plan

    def test_list_plans(self) -> None:
        planner = EngineeringPlanner()
        planner.create_plan("Build A")
        planner.create_plan("Fix B")
        plans = planner.list_plans()
        assert len(plans) == 2

    def test_update_plan_status(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Build X")
        assert planner.update_plan_status(plan.plan_id, "approved")
        assert plan.status == "approved"

    def test_update_plan_status_not_found(self) -> None:
        planner = EngineeringPlanner()
        assert not planner.update_plan_status("nonexistent", "approved")

    def test_scope_detection(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Add a new API endpoint for cockpit")
        assert "transports" in plan.intent.scope
        assert "cockpit" in plan.intent.scope

    def test_domain_detection(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Build auth middleware for the API")
        domains = plan.intent.affected_domains
        assert "security" in domains
        assert "backend" in domains

    def test_success_criteria_per_type(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Fix login bug")
        criteria = plan.intent.success_criteria
        assert any("regression test" in c for c in criteria)

    def test_constraints_passed_through(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan(
            "Build X",
            constraints=["no breaking changes", "Python 3.11 only"],
        )
        assert "no breaking changes" in plan.intent.constraints
        assert "Python 3.11 only" in plan.intent.constraints

    def test_desired_end_state_in_criteria(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan(
            "Build X",
            desired_end_state="Feature fully deployed",
        )
        assert plan.intent.success_criteria[0] == "Feature fully deployed"


# ── Workcell C: Engineering Work Generator ─────────────────────────────


class TestWorkGeneratorComposition:
    """Test plan → WorkPacket bridge via existing engine."""

    def _make_plan(self) -> EngineeringPlan:
        planner = EngineeringPlanner()
        return planner.create_plan("Build a health endpoint")

    def test_generate_packets_calls_engine(self) -> None:
        plan = self._make_plan()
        plan.status = "approved"

        mock_engine = MagicMock()
        mock_packet = MagicMock()
        mock_packet.packet_id = "wp-test-001"
        mock_engine.create_packet_from_intent.return_value = mock_packet

        mock_queue = MagicMock()

        gen = EngineeringWorkGenerator(
            work_packet_engine=mock_engine,
            work_queue=mock_queue,
        )
        receipt = gen.generate_packets(plan)

        assert receipt.status == "packets_generated"
        assert len(receipt.work_packet_ids) == len(plan.tasks)
        assert mock_engine.create_packet_from_intent.call_count == len(plan.tasks)

    def test_source_type_engineering_plan(self) -> None:
        plan = self._make_plan()
        plan.status = "approved"

        mock_engine = MagicMock()
        mock_packet = MagicMock()
        mock_packet.packet_id = "wp-test-002"
        mock_engine.create_packet_from_intent.return_value = mock_packet

        mock_queue = MagicMock()

        gen = EngineeringWorkGenerator(
            work_packet_engine=mock_engine,
            work_queue=mock_queue,
        )
        gen.generate_packets(plan)

        calls = mock_engine.create_packet_from_intent.call_args_list
        for call in calls:
            assert call.kwargs.get("source_type") == "engineering_plan"
            assert call.kwargs.get("source_id") == plan.plan_id

    def test_packets_enqueued(self) -> None:
        plan = self._make_plan()
        plan.status = "approved"

        mock_engine = MagicMock()
        mock_packet = MagicMock()
        mock_packet.packet_id = "wp-test-003"
        mock_engine.create_packet_from_intent.return_value = mock_packet

        mock_queue = MagicMock()

        gen = EngineeringWorkGenerator(
            work_packet_engine=mock_engine,
            work_queue=mock_queue,
        )
        gen.generate_packets(plan)

        assert mock_queue.ingest_work_packet.call_count == len(plan.tasks)

    def test_parent_packet_set(self) -> None:
        plan = self._make_plan()
        plan.status = "approved"

        packet_count = [0]
        mock_engine = MagicMock()

        def make_packet(**kwargs: Any) -> MagicMock:
            pkt = MagicMock()
            pkt.packet_id = f"wp-{packet_count[0]:03d}"
            packet_count[0] += 1
            return pkt

        mock_engine.create_packet_from_intent.side_effect = make_packet
        mock_queue = MagicMock()

        gen = EngineeringWorkGenerator(
            work_packet_engine=mock_engine,
            work_queue=mock_queue,
        )
        receipt = gen.generate_packets(plan)

        assert receipt.work_packet_ids[0] == "wp-000"

    def test_failed_on_invalid_status(self) -> None:
        plan = self._make_plan()
        plan.status = "completed"

        gen = EngineeringWorkGenerator()
        receipt = gen.generate_packets(plan)
        assert receipt.status == "failed"


# ── Governance Enforcement ─────────────────────────────────────────────


class TestGovernanceEnforcement:
    """Verify no bypass of governance."""

    def test_no_execute_method(self) -> None:
        planner = EngineeringPlanner()
        assert not hasattr(planner, "execute")
        assert not hasattr(planner, "run")
        assert not hasattr(planner, "dispatch")

    def test_no_git_mutation(self) -> None:
        import inspect
        from substrate.meta_ide import engineering_planner

        source = inspect.getsource(engineering_planner)
        assert "git push" not in source
        assert "git merge" not in source
        assert "subprocess" not in source

    def test_plan_is_read_only_artifact(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Build something")
        assert plan.status == "draft"
        assert plan.tasks
        for task in plan.tasks:
            assert task.task_id.startswith("et-")


# ── No New Authority ──────────────────────────────────────────────────


class TestNoNewAuthority:
    """Verify Phase 22 creates no new execution authority."""

    def test_planner_has_no_execution(self) -> None:
        planner = EngineeringPlanner()
        public_methods = [m for m in dir(planner) if not m.startswith("_")]
        execution_words = {"execute", "run", "dispatch", "deploy", "push", "merge"}
        for method in public_methods:
            assert method not in execution_words, f"Planner has execution method: {method}"

    def test_generator_only_creates_packets(self) -> None:
        gen = EngineeringWorkGenerator()
        public_methods = [m for m in dir(gen) if not m.startswith("_")]
        assert "generate_packets" in public_methods
        execution_words = {"execute", "run", "dispatch", "deploy", "push"}
        for method in public_methods:
            assert method not in execution_words

    def test_gap_engine_read_only(self) -> None:
        engine = RoadmapGapEngine()
        public_methods = [m for m in dir(engine) if not m.startswith("_")]
        assert "analyze_gaps" in public_methods
        assert "recommend_work" in public_methods
        execution_words = {"execute", "run", "dispatch", "deploy", "push", "create", "write"}
        for method in public_methods:
            assert method not in execution_words


# ── Workcell F: Roadmap Gap Engine ─────────────────────────────────────


class TestRoadmapGapEngine:
    """Test gap detection and recommendation generation."""

    def test_analyze_gaps_no_roadmap(self) -> None:
        engine = RoadmapGapEngine()
        analysis = engine.analyze_gaps()
        assert analysis.total_phases == 0
        assert analysis.completion_percentage == 0.0
        assert analysis.gaps == []

    def test_analyze_gaps_with_mock_roadmap(self) -> None:
        mock_roadmap = MagicMock()

        @dataclass
        class MockPhase:
            phase_number: str = ""
            title: str = ""
            state: str = "PLANNED"

        mock_roadmap.completed_phases.return_value = [
            MockPhase("1", "Setup", "COMPLETED"),
            MockPhase("2", "Core", "COMPLETED"),
        ]
        mock_roadmap.what_remains.return_value = [
            MockPhase("3", "Deploy", "PLANNED"),
        ]
        mock_roadmap.what_is_blocked.return_value = []

        engine = RoadmapGapEngine(roadmap_intelligence=mock_roadmap)
        analysis = engine.analyze_gaps()

        assert analysis.total_phases == 3
        assert analysis.completed_phases == 2
        assert analysis.completion_percentage == pytest.approx(66.7, abs=0.1)
        assert len(analysis.gaps) == 1
        assert analysis.gaps[0].gap_type == "not_started"

    def test_analyze_gaps_blocked(self) -> None:
        mock_roadmap = MagicMock()

        @dataclass
        class MockPhase:
            phase_number: str = ""
            title: str = ""
            state: str = "PLANNED"

        mock_roadmap.completed_phases.return_value = []
        mock_roadmap.what_remains.return_value = [
            MockPhase("1", "Blocked Phase", "PLANNED"),
        ]
        mock_roadmap.what_is_blocked.return_value = [
            MockPhase("1", "Blocked Phase"),
        ]

        engine = RoadmapGapEngine(roadmap_intelligence=mock_roadmap)
        analysis = engine.analyze_gaps()

        assert analysis.blocked_phases == 1
        blocked_gaps = [g for g in analysis.gaps if g.gap_type == "blocked"]
        assert len(blocked_gaps) == 1
        assert blocked_gaps[0].priority_score == 0.9

    def test_recommend_work(self) -> None:
        mock_roadmap = MagicMock()

        @dataclass
        class MockPhase:
            phase_number: str = ""
            title: str = ""
            state: str = "PLANNED"

        mock_roadmap.completed_phases.return_value = []
        mock_roadmap.what_remains.return_value = [
            MockPhase("1", "Auth System", "PLANNED"),
        ]
        mock_roadmap.what_is_blocked.return_value = []

        engine = RoadmapGapEngine(roadmap_intelligence=mock_roadmap)
        recs = engine.recommend_work(max_items=5)

        assert len(recs) == 1
        assert "Auth System" in recs[0].intent_text
        assert recs[0].priority_score == 0.3

    def test_gap_priority_ordering(self) -> None:
        mock_roadmap = MagicMock()

        @dataclass
        class MockPhase:
            phase_number: str = ""
            title: str = ""
            state: str = "PLANNED"

        mock_roadmap.completed_phases.return_value = []
        mock_roadmap.what_remains.return_value = [
            MockPhase("1", "Low Priority", "PLANNED"),
            MockPhase("2", "In Progress", "IN_PROGRESS"),
            MockPhase("3", "Blocked Item", "PLANNED"),
        ]
        mock_roadmap.what_is_blocked.return_value = [
            MockPhase("3", "Blocked Item"),
        ]

        engine = RoadmapGapEngine(roadmap_intelligence=mock_roadmap)
        analysis = engine.analyze_gaps()

        assert analysis.gaps[0].gap_type == "blocked"
        assert analysis.gaps[0].priority_score > analysis.gaps[-1].priority_score

    def test_gap_to_dict(self) -> None:
        gap = RoadmapGap(
            phase_number="5",
            phase_title="Test Phase",
            gap_type="blocked",
            priority_score=0.9,
        )
        d = gap.to_dict()
        assert d["phase_number"] == "5"
        assert d["gap_type"] == "blocked"

    def test_analysis_to_dict(self) -> None:
        analysis = GapAnalysis(
            total_phases=10,
            completed_phases=5,
            completion_percentage=50.0,
        )
        d = analysis.to_dict()
        assert d["total_phases"] == 10
        assert d["completion_percentage"] == 50.0

    def test_recommendation_to_dict(self) -> None:
        rec = GapRecommendation(
            title="Fix it",
            intent_text="Resolve blocking issue for X",
            priority_score=0.8,
        )
        d = rec.to_dict()
        assert d["title"] == "Fix it"
        assert d["intent_text"] == "Resolve blocking issue for X"


# ── Deterministic First ───────────────────────────────────────────────


class TestDeterministicFirst:
    """Verify no LLM calls in the planning pipeline."""

    def test_no_llm_import_in_planner(self) -> None:
        import inspect
        from substrate.meta_ide import engineering_planner

        source = inspect.getsource(engineering_planner)
        assert "call_with_fallback" not in source
        assert "model_router" not in source
        assert "llm_adapter" not in source

    def test_no_llm_import_in_intent(self) -> None:
        import inspect
        from substrate.meta_ide import engineering_intent

        source = inspect.getsource(engineering_intent)
        assert "call_with_fallback" not in source
        assert "model_router" not in source

    def test_no_llm_import_in_gap_engine(self) -> None:
        import inspect
        from substrate.meta_ide import roadmap_gap_engine

        source = inspect.getsource(roadmap_gap_engine)
        assert "call_with_fallback" not in source
        assert "model_router" not in source

    def test_planner_works_with_no_engines(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Build X")
        assert plan.plan_id.startswith("ep-")
        assert len(plan.tasks) > 0


# ── Graceful Degradation ──────────────────────────────────────────────


class TestGracefulDegradation:
    """Test behavior when optional engines are None."""

    def test_planner_none_workspace(self) -> None:
        planner = EngineeringPlanner(workspace_engine=None)
        plan = planner.create_plan("Build X")
        assert plan.workspace_health == {}

    def test_planner_none_roadmap(self) -> None:
        planner = EngineeringPlanner(roadmap_intelligence=None)
        plan = planner.create_plan("Build X")
        assert plan.roadmap_context == {}

    def test_gap_engine_none_roadmap(self) -> None:
        engine = RoadmapGapEngine(roadmap_intelligence=None)
        analysis = engine.analyze_gaps()
        assert analysis.total_phases == 0
        recs = engine.recommend_work()
        assert recs == []


# ── Type Registry ─────────────────────────────────────────────────────


class TestTypeRegistry:
    """Verify all types registered in canonical_types.py."""

    def test_all_types_registered(self) -> None:
        from substrate.canonical_types import lookup

        types_to_check = [
            "EngineeringIntentType",
            "EngineeringIntent",
            "EngineeringTask",
            "EngineeringPlan",
            "EngineeringPlanReceipt",
            "EngineeringPlanner",
            "EngineeringWorkGenerator",
            "RoadmapGapEngine",
            "GapAnalysis",
            "RoadmapGap",
            "GapRecommendation",
        ]
        for type_name in types_to_check:
            result = lookup(type_name)
            assert result is not None, f"{type_name} not registered in canonical_types"

    def test_no_duplicate_registrations(self) -> None:
        from substrate.canonical_types import lookup

        types_to_check = [
            "EngineeringIntentType",
            "EngineeringPlanner",
            "RoadmapGapEngine",
        ]
        for type_name in types_to_check:
            result = lookup(type_name)
            assert result is not None
            assert isinstance(result, list), f"{type_name} lookup should return a list"
            assert len(result) == 1, f"{type_name} should have exactly one canonical location"


# ── Integration E2E ───────────────────────────────────────────────────


class TestIntegrationE2E:
    """End-to-end: intent → plan → approve → packets."""

    def test_feature_intent_to_plan(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Add a health endpoint to the API")

        assert plan.status == "draft"
        assert plan.intent.intent_type == EngineeringIntentType.FEATURE
        assert "a health endpoint to the API" in plan.intent.goal
        assert len(plan.tasks) == 5
        assert plan.dependency_graph
        assert plan.estimated_total_risk in ("low", "medium", "high", "critical")

    def test_plan_approve_generates_packets(self) -> None:
        planner = EngineeringPlanner()
        plan = planner.create_plan("Add a health endpoint to the API")

        mock_engine = MagicMock()
        counter = [0]

        def make_pkt(**kw: Any) -> MagicMock:
            p = MagicMock()
            p.packet_id = f"wp-e2e-{counter[0]:03d}"
            counter[0] += 1
            return p

        mock_engine.create_packet_from_intent.side_effect = make_pkt
        mock_queue = MagicMock()

        gen = EngineeringWorkGenerator(
            work_packet_engine=mock_engine,
            work_queue=mock_queue,
        )
        receipt = gen.generate_packets(plan)

        assert receipt.status == "packets_generated"
        assert len(receipt.work_packet_ids) == 5
        assert mock_queue.ingest_work_packet.call_count == 5

    def test_mutation_source_exists(self) -> None:
        from substrate.reality_model.reality_mutation import MutationSource

        assert hasattr(MutationSource, "ENGINEERING")
        assert MutationSource.ENGINEERING.value == "engineering"

    def test_substrate_api_methods_exist(self) -> None:
        from substrate import Substrate

        assert hasattr(Substrate, "create_engineering_plan")
        assert hasattr(Substrate, "approve_engineering_plan")
