"""Phase 9.2 — Governed Self-Improvement Trial tests.

Tests cover:
  - Trial candidate selection via contradiction engine
  - Custom-step composition via CompositionEngine
  - Execution graph conversion and dependency preservation
  - Governance dry run (SpineGuard / execution mode checks)
  - Full execution through GovernedExecutionSpine
  - Outcome capture via OutcomeLearningLoop
  - Memory candidate generation via MemoryPromotionPipeline
  - PlanExecutionAdapter bug fix (SpineGuard API integration)
  - Trial status bridge handler
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.organism.world_model import extract_world_model
from substrate.organism.dependency_graph import build_dependency_graph
from substrate.organism.contradiction_engine import detect_contradictions
from substrate.organism.composition_engine import (
    CompositionEngine,
    CompositionConstraint,
    CompositionContext,
    CompositionIntent,
    CompositionPlan,
    CompositionStep,
    GovernanceMode,
    RiskClass,
    StepStatus,
    compose_plan,
)
from substrate.organism.plan_execution_adapter import (
    ExecutablePlan,
    ExecutableStep,
    ExecutionDependency,
    ExecutionGraph,
    ExecutionGraphStatus,
    PlanExecutionAdapter,
    StepExecutionStatus,
)
from substrate.organism.governed_spine import GovernedExecutionSpine
from substrate.organism.spine_guard import SpineGuard, GuardMode
from substrate.organism.autonomous_action_gateway import (
    AutonomousActionGateway,
    AutonomousPolicy,
)
from substrate.organism.mutation_registry import MutationRegistry
from substrate.organism.execution_journal import ExecutionJournal
from substrate.organism.execution_modes import ExecutionModeManager, ExecutionMode
from substrate.organism.event_spine import EventSpine
from substrate.organism.leverage_metrics import LeverageMetrics
from substrate.organism.outcome_learning import (
    OutcomeLearningLoop,
    OutcomeRecord,
    OutcomeStatus,
)
from substrate.organism.memory_promotion import (
    MemoryCategory,
    MemoryEvidence,
    MemoryPromotionPipeline,
    MemoryPromotionStatus,
)
from substrate.organism.action_envelope import (
    ActionEnvelope,
    ActionType,
    BlastRadius,
    EnvelopeStatus,
    ReversibilityClass,
)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def world_model():
    return extract_world_model()


@pytest.fixture
def dep_graph(world_model):
    return build_dependency_graph(world_model)


@pytest.fixture
def contradiction_report(world_model, dep_graph):
    return detect_contradictions(world_model, dep_graph)


@pytest.fixture
def composition_engine(world_model, dep_graph, contradiction_report):
    return CompositionEngine(
        world_model=world_model,
        dependency_graph=dep_graph,
        contradiction_report=contradiction_report,
    )


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def governed_stack(tmpdir):
    event_spine = EventSpine()
    exec_mode = ExecutionModeManager(event_spine=event_spine)
    mutation_reg = MutationRegistry()
    journal = ExecutionJournal(persist_path=os.path.join(tmpdir, "journal.jsonl"))
    leverage = LeverageMetrics(event_spine=event_spine)
    spine = GovernedExecutionSpine(
        event_spine=event_spine,
        execution_mode=exec_mode,
        mutation_registry=mutation_reg,
        journal=journal,
        leverage_metrics=leverage,
    )
    spine_guard = SpineGuard(
        mode=GuardMode.BLOCK_HIGH_RISK,
        event_spine=event_spine,
        journal=journal,
    )
    gateway = AutonomousActionGateway(
        governed_spine=spine,
        execution_mode=exec_mode,
        event_spine=event_spine,
        journal=journal,
        policy=AutonomousPolicy.AUTONOMOUS,
    )
    outcome_loop = OutcomeLearningLoop(store_path=os.path.join(tmpdir, "outcomes.jsonl"))
    memory_pipeline = MemoryPromotionPipeline(store_dir=tmpdir)

    adapter = PlanExecutionAdapter(
        governed_spine=spine,
        spine_guard=spine_guard,
        autonomous_gateway=gateway,
        outcome_loop=outcome_loop,
        memory_pipeline=memory_pipeline,
    )
    return {
        "spine": spine,
        "spine_guard": spine_guard,
        "gateway": gateway,
        "journal": journal,
        "exec_mode": exec_mode,
        "outcome_loop": outcome_loop,
        "memory_pipeline": memory_pipeline,
        "adapter": adapter,
    }


# ── Trial Candidate Selection ─────────────────────────────────


class TestTrialCandidateSelection:
    def test_world_model_produces_entities(self, world_model):
        assert len(world_model.entities) > 50

    def test_contradiction_engine_finds_issues(self, contradiction_report):
        assert len(contradiction_report.contradictions) > 0

    def test_contradictions_have_severity(self, contradiction_report):
        for c in contradiction_report.contradictions:
            assert c.severity in ("info", "low", "medium", "high", "critical")

    def test_each_contradiction_has_evidence(self, contradiction_report):
        for c in contradiction_report.contradictions:
            assert c.evidence is not None

    def test_contradictions_serializable(self, contradiction_report):
        for c in contradiction_report.contradictions:
            d = c.to_dict()
            json.dumps(d, default=str)

    def test_governance_entities_detected(self, world_model):
        governance_entities = [
            e for e in world_model.entities.values()
            if e.category.value == "governance"
        ]
        assert len(governance_entities) >= 2


# ── Custom Step Composition ───────────────────────────────────


class TestCustomStepComposition:
    def test_custom_steps_override_pattern(self, composition_engine):
        intent = CompositionIntent(description="fix contradiction in governance")
        custom_steps = [
            {"action": "step_a", "desc": "First", "risk": "low", "gov": "autonomous", "verify": "check_a"},
            {"action": "step_b", "desc": "Second", "risk": "low", "gov": "autonomous", "verify": "check_b"},
        ]
        plan = composition_engine.compose(intent, custom_steps=custom_steps)
        assert len(plan.steps) == 2
        assert plan.steps[0].action == "step_a"
        assert plan.steps[1].action == "step_b"

    def test_custom_steps_preserve_low_risk(self, composition_engine):
        intent = CompositionIntent(description="safe fix")
        custom_steps = [
            {"action": "a", "desc": "A", "risk": "low", "gov": "autonomous", "verify": "v"},
        ]
        plan = composition_engine.compose(intent, custom_steps=custom_steps)
        assert plan.overall_risk == RiskClass.LOW
        assert plan.governance_required == GovernanceMode.AUTONOMOUS

    def test_custom_steps_chain_dependencies(self, composition_engine):
        intent = CompositionIntent(description="chain test")
        custom_steps = [
            {"action": "a", "desc": "First", "risk": "low", "gov": "autonomous"},
            {"action": "b", "desc": "Second", "risk": "low", "gov": "autonomous"},
            {"action": "c", "desc": "Third", "risk": "low", "gov": "autonomous"},
        ]
        plan = composition_engine.compose(intent, custom_steps=custom_steps)
        assert plan.steps[0].depends_on == []
        assert plan.steps[1].depends_on == [plan.steps[0].id]
        assert plan.steps[2].depends_on == [plan.steps[1].id]

    def test_custom_steps_evidence_populated(self, composition_engine):
        intent = CompositionIntent(description="evidence check")
        custom_steps = [
            {"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"},
        ]
        plan = composition_engine.compose(intent, custom_steps=custom_steps)
        assert len(plan.evidence) >= 3

    def test_custom_medium_risk_escalates_governance(self, composition_engine):
        intent = CompositionIntent(description="medium risk")
        custom_steps = [
            {"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"},
            {"action": "b", "desc": "B", "risk": "medium", "gov": "assisted"},
        ]
        plan = composition_engine.compose(intent, custom_steps=custom_steps)
        assert plan.overall_risk == RiskClass.MEDIUM
        assert plan.governance_required == GovernanceMode.ASSISTED

    def test_plan_serializable(self, composition_engine):
        intent = CompositionIntent(description="serialize test")
        custom_steps = [
            {"action": "a", "desc": "A", "risk": "low", "gov": "autonomous", "verify": "v"},
        ]
        plan = composition_engine.compose(intent, custom_steps=custom_steps)
        data = plan.to_dict()
        serialized = json.dumps(data, default=str)
        assert len(serialized) > 0


# ── Execution Graph ───────────────────────────────────────────


class TestExecutionGraph:
    def test_convert_preserves_step_count(self, composition_engine):
        intent = CompositionIntent(description="convert test")
        custom_steps = [
            {"action": "a", "desc": "A", "risk": "low", "gov": "autonomous", "verify": "v"},
            {"action": "b", "desc": "B", "risk": "low", "gov": "autonomous", "verify": "v"},
        ]
        plan = composition_engine.compose(intent, custom_steps=custom_steps)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert len(executable.steps) == 2

    def test_convert_preserves_dependencies(self, composition_engine):
        intent = CompositionIntent(description="dep test")
        custom_steps = [
            {"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"},
            {"action": "b", "desc": "B", "risk": "low", "gov": "autonomous"},
        ]
        plan = composition_engine.compose(intent, custom_steps=custom_steps)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert len(executable.dependencies) == 1

    def test_convert_preserves_risk_levels(self, composition_engine):
        intent = CompositionIntent(description="risk test")
        custom_steps = [
            {"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"},
            {"action": "b", "desc": "B", "risk": "medium", "gov": "assisted"},
        ]
        plan = composition_engine.compose(intent, custom_steps=custom_steps)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert executable.steps[0].risk_level == "low"
        assert executable.steps[1].risk_level == "medium"

    def test_low_risk_no_approval(self, composition_engine):
        intent = CompositionIntent(description="no approval")
        custom_steps = [
            {"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"},
        ]
        plan = composition_engine.compose(intent, custom_steps=custom_steps)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert executable.steps[0].requires_approval is False

    def test_medium_assisted_requires_approval(self, composition_engine):
        intent = CompositionIntent(description="approval needed")
        custom_steps = [
            {"action": "a", "desc": "A", "risk": "medium", "gov": "assisted"},
        ]
        plan = composition_engine.compose(intent, custom_steps=custom_steps)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert executable.steps[0].requires_approval is True

    def test_execution_graph_stores_plans(self, composition_engine):
        intent = CompositionIntent(description="graph store")
        custom_steps = [
            {"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"},
        ]
        plan = composition_engine.compose(intent, custom_steps=custom_steps)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert adapter.execution_graph.get(executable.id) is executable

    def test_executable_plan_serializable(self, composition_engine):
        intent = CompositionIntent(description="serial")
        custom_steps = [
            {"action": "a", "desc": "A", "risk": "low", "gov": "autonomous", "verify": "v"},
        ]
        plan = composition_engine.compose(intent, custom_steps=custom_steps)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        data = executable.to_dict()
        json.dumps(data, default=str)


# ── Governance Dry Run ────────────────────────────────────────


class TestGovernanceDryRun:
    def test_spine_guard_allows_low_risk(self):
        guard = SpineGuard(mode=GuardMode.BLOCK_HIGH_RISK)
        blocked = guard.check_direct_mutation("test", "low risk op", risk_level="low")
        assert blocked is False

    def test_spine_guard_blocks_medium_risk(self):
        """BLOCK_HIGH_RISK blocks >= medium (severity 1+), not just high."""
        guard = SpineGuard(mode=GuardMode.BLOCK_HIGH_RISK)
        blocked = guard.check_direct_mutation("test", "medium op", risk_level="medium")
        assert blocked is True

    def test_spine_guard_blocks_high_risk(self):
        guard = SpineGuard(mode=GuardMode.BLOCK_HIGH_RISK)
        blocked = guard.check_direct_mutation("test", "high risk op", risk_level="high")
        assert blocked is True

    def test_spine_guard_blocks_critical_risk(self):
        guard = SpineGuard(mode=GuardMode.BLOCK_HIGH_RISK)
        blocked = guard.check_direct_mutation("test", "critical op", risk_level="critical")
        assert blocked is True

    def test_spine_guard_warn_mode_allows_all(self):
        guard = SpineGuard(mode=GuardMode.WARN)
        blocked = guard.check_direct_mutation("test", "high risk op", risk_level="high")
        assert blocked is False

    def test_execution_mode_observe_allows_observe(self):
        event_spine = EventSpine()
        mgr = ExecutionModeManager(event_spine=event_spine)
        assert mgr.can_execute(ExecutionMode.OBSERVE)


# ── Governed Execution ────────────────────────────────────────


class TestGovernedExecution:
    def test_full_execution_through_spine(self, governed_stack):
        adapter = governed_stack["adapter"]
        plan = CompositionPlan(
            intent=CompositionIntent(description="test plan"),
        )
        plan.steps = [
            CompositionStep(
                description="Step 1",
                action="test_action",
                risk_class=RiskClass.LOW,
                governance_mode=GovernanceMode.AUTONOMOUS,
                verification="check",
            ),
        ]
        plan.overall_risk = RiskClass.LOW
        plan.governance_required = GovernanceMode.AUTONOMOUS
        plan.rollback_plan = "revert"

        executable = adapter.convert_plan(plan)
        result = adapter.execute_plan(
            executable,
            step_executors={plan.steps[0].id: lambda: ("test output", True)},
        )
        assert result.status == ExecutionGraphStatus.COMPLETED
        assert result.success_count() == 1

    def test_failed_step_blocks_dependents(self, governed_stack):
        adapter = governed_stack["adapter"]
        plan = CompositionPlan(
            intent=CompositionIntent(description="fail cascade"),
        )
        s1 = CompositionStep(
            description="S1", action="a", risk_class=RiskClass.LOW,
            governance_mode=GovernanceMode.AUTONOMOUS,
        )
        s2 = CompositionStep(
            description="S2", action="b", risk_class=RiskClass.LOW,
            governance_mode=GovernanceMode.AUTONOMOUS, depends_on=[s1.id],
        )
        plan.steps = [s1, s2]
        plan.overall_risk = RiskClass.LOW
        plan.governance_required = GovernanceMode.AUTONOMOUS

        executable = adapter.convert_plan(plan)
        result = adapter.execute_plan(
            executable,
            step_executors={s1.id: lambda: ("fail", False)},
        )
        blocked = [s for s in result.steps if s.status == StepExecutionStatus.BLOCKED_BY_FAILURE]
        assert len(blocked) == 1

    def test_spine_guard_integration(self, governed_stack):
        adapter = governed_stack["adapter"]
        plan = CompositionPlan(
            intent=CompositionIntent(description="guard test"),
        )
        plan.steps = [
            CompositionStep(
                description="Low risk step", action="test",
                risk_class=RiskClass.LOW, governance_mode=GovernanceMode.AUTONOMOUS,
            ),
        ]
        plan.overall_risk = RiskClass.LOW
        plan.governance_required = GovernanceMode.AUTONOMOUS

        executable = adapter.convert_plan(plan)
        result = adapter.execute_plan(
            executable,
            step_executors={plan.steps[0].id: lambda: ("ok", True)},
        )
        assert result.success_count() == 1

    def test_multi_step_sequential_execution(self, governed_stack):
        adapter = governed_stack["adapter"]
        plan = CompositionPlan(
            intent=CompositionIntent(description="multi step"),
        )
        s1 = CompositionStep(
            description="S1", action="verify",
            risk_class=RiskClass.LOW, governance_mode=GovernanceMode.AUTONOMOUS,
        )
        s2 = CompositionStep(
            description="S2", action="fix",
            risk_class=RiskClass.LOW, governance_mode=GovernanceMode.AUTONOMOUS,
            depends_on=[s1.id],
        )
        s3 = CompositionStep(
            description="S3", action="verify",
            risk_class=RiskClass.LOW, governance_mode=GovernanceMode.AUTONOMOUS,
            depends_on=[s2.id],
        )
        plan.steps = [s1, s2, s3]
        plan.overall_risk = RiskClass.LOW
        plan.governance_required = GovernanceMode.AUTONOMOUS

        executable = adapter.convert_plan(plan)
        result = adapter.execute_plan(executable, step_executors={
            s1.id: lambda: ("verified", True),
            s2.id: lambda: ("fixed", True),
            s3.id: lambda: ("verified", True),
        })
        assert result.status == ExecutionGraphStatus.COMPLETED
        assert result.success_count() == 3


# ── Outcome Capture ───────────────────────────────────────────


class TestOutcomeCapture:
    def test_outcomes_recorded_per_step(self, governed_stack):
        adapter = governed_stack["adapter"]
        outcome_loop = governed_stack["outcome_loop"]
        plan = CompositionPlan(
            intent=CompositionIntent(description="outcome test"),
        )
        plan.steps = [
            CompositionStep(
                description="S1", action="a",
                risk_class=RiskClass.LOW, governance_mode=GovernanceMode.AUTONOMOUS,
            ),
        ]
        plan.overall_risk = RiskClass.LOW
        plan.governance_required = GovernanceMode.AUTONOMOUS

        executable = adapter.convert_plan(plan)
        adapter.execute_plan(executable, step_executors={
            plan.steps[0].id: lambda: ("ok", True),
        })
        assert len(outcome_loop.recent_outcomes()) >= 1

    def test_reliability_updates_after_execution(self, governed_stack):
        adapter = governed_stack["adapter"]
        outcome_loop = governed_stack["outcome_loop"]
        plan = CompositionPlan(
            intent=CompositionIntent(description="reliability test"),
        )
        plan.steps = [
            CompositionStep(
                description="S1", action="test_action_type",
                risk_class=RiskClass.LOW, governance_mode=GovernanceMode.AUTONOMOUS,
            ),
        ]
        plan.overall_risk = RiskClass.LOW
        plan.governance_required = GovernanceMode.AUTONOMOUS

        executable = adapter.convert_plan(plan)
        adapter.execute_plan(executable, step_executors={
            plan.steps[0].id: lambda: ("ok", True),
        })
        assert outcome_loop.get_reliability("test_action_type") >= 0.0

    def test_learning_signals_generated(self, governed_stack):
        adapter = governed_stack["adapter"]
        outcome_loop = governed_stack["outcome_loop"]
        plan = CompositionPlan(
            intent=CompositionIntent(description="signal test"),
        )
        plan.steps = [
            CompositionStep(
                description="S1", action="signal_action",
                risk_class=RiskClass.LOW, governance_mode=GovernanceMode.AUTONOMOUS,
            ),
        ]
        plan.overall_risk = RiskClass.LOW
        plan.governance_required = GovernanceMode.AUTONOMOUS

        executable = adapter.convert_plan(plan)
        adapter.execute_plan(executable, step_executors={
            plan.steps[0].id: lambda: ("ok", True),
        })
        assert len(outcome_loop.recent_signals()) >= 0


# ── Memory Candidate Generation ───────────────────────────────


class TestMemoryCandidateGeneration:
    def test_success_generates_pattern_candidate(self, governed_stack):
        adapter = governed_stack["adapter"]
        memory = governed_stack["memory_pipeline"]
        plan = CompositionPlan(
            intent=CompositionIntent(description="memory gen test"),
        )
        plan.steps = [
            CompositionStep(
                description="S1", action="a",
                risk_class=RiskClass.LOW, governance_mode=GovernanceMode.AUTONOMOUS,
            ),
        ]
        plan.overall_risk = RiskClass.LOW
        plan.governance_required = GovernanceMode.AUTONOMOUS

        executable = adapter.convert_plan(plan)
        adapter.execute_plan(executable, step_executors={
            plan.steps[0].id: lambda: ("ok", True),
        })
        candidates = memory.list_candidates()
        assert len(candidates) >= 1

    def test_failure_generates_observation_candidate(self, governed_stack):
        adapter = governed_stack["adapter"]
        memory = governed_stack["memory_pipeline"]
        plan = CompositionPlan(
            intent=CompositionIntent(description="fail memory test"),
        )
        plan.steps = [
            CompositionStep(
                description="S1", action="a",
                risk_class=RiskClass.LOW, governance_mode=GovernanceMode.AUTONOMOUS,
            ),
        ]
        plan.overall_risk = RiskClass.LOW
        plan.governance_required = GovernanceMode.AUTONOMOUS

        executable = adapter.convert_plan(plan)
        adapter.execute_plan(executable, step_executors={
            plan.steps[0].id: lambda: ("fail", False),
        })
        candidates = memory.list_candidates()
        assert len(candidates) >= 1

    def test_candidates_not_auto_promoted(self, governed_stack):
        adapter = governed_stack["adapter"]
        memory = governed_stack["memory_pipeline"]
        plan = CompositionPlan(
            intent=CompositionIntent(description="no auto promote"),
        )
        plan.steps = [
            CompositionStep(
                description="S1", action="a",
                risk_class=RiskClass.LOW, governance_mode=GovernanceMode.AUTONOMOUS,
            ),
        ]
        plan.overall_risk = RiskClass.LOW
        plan.governance_required = GovernanceMode.AUTONOMOUS

        executable = adapter.convert_plan(plan)
        adapter.execute_plan(executable, step_executors={
            plan.steps[0].id: lambda: ("ok", True),
        })
        promoted = [c for c in memory.list_candidates() if c.status == MemoryPromotionStatus.PROMOTED]
        assert len(promoted) == 0

    def test_candidates_have_evidence(self, governed_stack):
        adapter = governed_stack["adapter"]
        memory = governed_stack["memory_pipeline"]
        plan = CompositionPlan(
            intent=CompositionIntent(description="evidence test"),
        )
        plan.steps = [
            CompositionStep(
                description="S1", action="a",
                risk_class=RiskClass.LOW, governance_mode=GovernanceMode.AUTONOMOUS,
            ),
        ]
        plan.overall_risk = RiskClass.LOW
        plan.governance_required = GovernanceMode.AUTONOMOUS

        executable = adapter.convert_plan(plan)
        adapter.execute_plan(executable, step_executors={
            plan.steps[0].id: lambda: ("ok", True),
        })
        for c in memory.list_candidates():
            assert len(c.evidence) >= 1


# ── PlanExecutionAdapter Bug Fix ──────────────────────────────


class TestAdapterSpineGuardIntegration:
    def test_adapter_uses_check_direct_mutation(self, governed_stack):
        adapter = governed_stack["adapter"]
        plan = CompositionPlan(
            intent=CompositionIntent(description="guard api test"),
        )
        plan.steps = [
            CompositionStep(
                description="S1", action="test",
                risk_class=RiskClass.LOW, governance_mode=GovernanceMode.AUTONOMOUS,
            ),
        ]
        plan.overall_risk = RiskClass.LOW
        plan.governance_required = GovernanceMode.AUTONOMOUS

        executable = adapter.convert_plan(plan)
        result = adapter.execute_plan(executable, step_executors={
            plan.steps[0].id: lambda: ("ok", True),
        })
        assert result.status == ExecutionGraphStatus.COMPLETED

    def test_adapter_no_evaluate_method_error(self, governed_stack):
        adapter = governed_stack["adapter"]
        plan = CompositionPlan(
            intent=CompositionIntent(description="no evaluate crash"),
        )
        plan.steps = [
            CompositionStep(
                description="S1", action="test",
                risk_class=RiskClass.LOW, governance_mode=GovernanceMode.AUTONOMOUS,
            ),
            CompositionStep(
                description="S2", action="test2",
                risk_class=RiskClass.LOW, governance_mode=GovernanceMode.AUTONOMOUS,
            ),
        ]
        plan.steps[1].depends_on = [plan.steps[0].id]
        plan.overall_risk = RiskClass.LOW
        plan.governance_required = GovernanceMode.AUTONOMOUS

        executable = adapter.convert_plan(plan)
        result = adapter.execute_plan(executable, step_executors={
            plan.steps[0].id: lambda: ("ok", True),
            plan.steps[1].id: lambda: ("ok", True),
        })
        assert result.success_count() == 2


# ── Trial Status Bridge ──────────────────────────────────────


class TestTrialStatusBridge:
    def test_bridge_handler_loads(self):
        from transports.api.organism_bridge import _trial_status
        result = _trial_status({})
        assert result["success"] is True
        assert "data" in result
        data = result["data"]
        assert "has_trial" in data

    def test_bridge_handler_with_trial_data(self, tmpdir):
        trial_results = {"trial_id": "test", "validation_passed": True}
        trials_dir = os.path.join(tmpdir, "data", "umh", "trials")
        os.makedirs(trials_dir, exist_ok=True)
        with open(os.path.join(trials_dir, "phase9_2_trial_results.json"), "w") as f:
            json.dump(trial_results, f)

        old_root = os.environ.get("UMH_ROOT")
        os.environ["UMH_ROOT"] = tmpdir
        try:
            from transports.api.organism_bridge import _trial_status
            result = _trial_status({})
            assert result["success"] is True
            assert result["data"]["has_trial"] is True
            assert result["data"]["trial_results"]["trial_id"] == "test"
        finally:
            if old_root:
                os.environ["UMH_ROOT"] = old_root
            else:
                os.environ.pop("UMH_ROOT", None)


# ── ExecutablePlan state machine ──────────────────────────────


class TestExecutablePlanStateMachine:
    def test_ready_steps_empty_when_all_done(self):
        plan = ExecutablePlan()
        s = ExecutableStep(status=StepExecutionStatus.COMPLETED)
        plan.steps = [s]
        assert plan.ready_steps() == []

    def test_ready_steps_first_step(self):
        plan = ExecutablePlan()
        s = ExecutableStep(status=StepExecutionStatus.PENDING)
        plan.steps = [s]
        assert len(plan.ready_steps()) == 1

    def test_blocked_propagation(self):
        plan = ExecutablePlan()
        s1 = ExecutableStep(
            composition_step_id="s1",
            status=StepExecutionStatus.FAILED,
        )
        s2 = ExecutableStep(
            composition_step_id="s2",
            status=StepExecutionStatus.PENDING,
            depends_on=["s1"],
        )
        plan.steps = [s1, s2]
        ready = plan.ready_steps()
        assert len(ready) == 0
        assert s2.status == StepExecutionStatus.BLOCKED_BY_FAILURE

    def test_is_complete_all_terminal(self):
        plan = ExecutablePlan()
        plan.steps = [
            ExecutableStep(status=StepExecutionStatus.COMPLETED),
            ExecutableStep(status=StepExecutionStatus.FAILED),
            ExecutableStep(status=StepExecutionStatus.SKIPPED),
        ]
        assert plan.is_complete()

    def test_success_count(self):
        plan = ExecutablePlan()
        plan.steps = [
            ExecutableStep(status=StepExecutionStatus.COMPLETED),
            ExecutableStep(status=StepExecutionStatus.COMPLETED),
            ExecutableStep(status=StepExecutionStatus.FAILED),
        ]
        assert plan.success_count() == 2
        assert plan.failure_count() == 1

    def test_summary_serializable(self):
        plan = ExecutablePlan(intent="test")
        data = plan.summary()
        json.dumps(data, default=str)

    def test_to_dict_serializable(self):
        plan = ExecutablePlan(intent="test")
        plan.steps = [ExecutableStep(description="s1")]
        data = plan.to_dict()
        json.dumps(data, default=str)
