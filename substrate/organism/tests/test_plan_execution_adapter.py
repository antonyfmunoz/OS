"""Tests for plan_execution_adapter — Phase 9.1 Composition→Execution bridge.

Covers:
  - Plan conversion from CompositionPlan to ExecutablePlan
  - Dependency preservation and graph structure
  - Governance preservation (risk, approval, mode)
  - Approval routing through spine
  - Execution graph traversal (sequential, parallel, blocked)
  - Rollback generation
  - Outcome recording into OutcomeLearningLoop
  - Memory candidate generation into MemoryPromotionPipeline
  - Edge cases and failure modes
"""

from __future__ import annotations

import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from substrate.organism.plan_execution_adapter import (
    ExecutablePlan,
    ExecutableStep,
    ExecutionDependency,
    ExecutionGraph,
    ExecutionGraphStatus,
    PlanExecutionAdapter,
    StepExecutionStatus,
    _infer_action_type,
)
from substrate.organism.composition_engine import (
    CompositionIntent,
    CompositionPlan,
    CompositionStep,
    GovernanceMode,
    RiskClass,
    StepStatus,
)
from substrate.organism.action_envelope import (
    ActionEnvelope,
    ActionType,
    EnvelopeStatus,
)
from substrate.organism.outcome_learning import (
    OutcomeLearningLoop,
    OutcomeStatus,
)
from substrate.organism.memory_promotion import (
    MemoryCategory,
    MemoryPromotionPipeline,
    MemoryPromotionStatus,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_plan(
    num_steps: int = 3,
    risk: RiskClass = RiskClass.LOW,
    governance: GovernanceMode = GovernanceMode.AUTONOMOUS,
    chain: bool = False,
) -> CompositionPlan:
    """Build a test CompositionPlan with configurable steps."""
    steps = []
    for i in range(num_steps):
        deps = [steps[i - 1].id] if chain and i > 0 else []
        steps.append(CompositionStep(
            id=f"step-{i}",
            description=f"Test step {i}",
            action=f"test action {i}",
            depends_on=deps,
            risk_class=risk,
            governance_mode=governance,
            verification=f"verify step {i}",
        ))
    return CompositionPlan(
        id="plan-001",
        intent=CompositionIntent(description="Test plan"),
        steps=steps,
        overall_risk=risk,
        governance_required=governance,
        rollback_plan="undo everything",
        evidence=["evidence-1", "evidence-2"],
    )


class FakeSpine:
    """Mock GovernedExecutionSpine that records submissions."""

    def __init__(
        self,
        auto_approve: bool = True,
        fail_steps: set[str] | None = None,
        reject_steps: set[str] | None = None,
    ):
        self.submitted: list[ActionEnvelope] = []
        self.approved: list[str] = []
        self._auto_approve = auto_approve
        self._fail_steps = fail_steps or set()
        self._reject_steps = reject_steps or set()
        self._pending: dict[str, ActionEnvelope] = {}

    def submit(self, envelope: ActionEnvelope) -> ActionEnvelope:
        self.submitted.append(envelope)
        step_id = envelope.metadata.get("step_id", "")

        if step_id in self._reject_steps:
            envelope.status = EnvelopeStatus.REJECTED
            envelope.rejected_reason = "governance_rejected"
            return envelope

        if envelope.constraints.require_approval and self._auto_approve:
            envelope.status = EnvelopeStatus.PROPOSED
            self._pending[envelope.envelope_id] = envelope
            return envelope

        if envelope.constraints.require_approval:
            envelope.status = EnvelopeStatus.PROPOSED
            self._pending[envelope.envelope_id] = envelope
            return envelope

        if step_id in self._fail_steps:
            envelope.status = EnvelopeStatus.FAILED
            envelope.result_output = "step execution failed"
            envelope.result_success = False
            return envelope

        envelope.status = EnvelopeStatus.COMPLETED
        envelope.result_output = f"executed: {envelope.intent}"
        envelope.result_success = True
        return envelope

    def approve(self, envelope_id: str, approved_by: str = "operator") -> ActionEnvelope | None:
        envelope = self._pending.pop(envelope_id, None)
        if envelope is None:
            return None
        self.approved.append(envelope_id)
        step_id = envelope.metadata.get("step_id", "")
        if step_id in self._fail_steps:
            envelope.status = EnvelopeStatus.FAILED
            envelope.result_success = False
            return envelope
        envelope.status = EnvelopeStatus.COMPLETED
        envelope.result_output = f"approved and executed: {envelope.intent}"
        envelope.result_success = True
        envelope.approved_by = approved_by
        return envelope


# ── Plan conversion tests ─────────────────────────────────────────────────────


class TestPlanConversion:
    def test_basic_conversion(self):
        plan = _make_plan(3)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert isinstance(executable, ExecutablePlan)
        assert len(executable.steps) == 3
        assert executable.source_plan_id == "plan-001"
        assert executable.intent == "Test plan"

    def test_step_fields_preserved(self):
        plan = _make_plan(1, risk=RiskClass.HIGH, governance=GovernanceMode.OPERATOR_REQUIRED)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        step = executable.steps[0]
        assert step.risk_level == "high"
        assert step.governance_mode == "operator_required"
        assert step.requires_approval is True
        assert step.description == "Test step 0"
        assert step.action == "test action 0"
        assert step.verification == "verify step 0"

    def test_autonomous_no_approval(self):
        plan = _make_plan(1, governance=GovernanceMode.AUTONOMOUS)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert executable.steps[0].requires_approval is False

    def test_assisted_requires_approval(self):
        plan = _make_plan(1, governance=GovernanceMode.ASSISTED)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert executable.steps[0].requires_approval is True

    def test_operator_required_approval(self):
        plan = _make_plan(1, governance=GovernanceMode.OPERATOR_REQUIRED)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert executable.steps[0].requires_approval is True

    def test_risk_level_mapping(self):
        for risk in RiskClass:
            plan = _make_plan(1, risk=risk)
            adapter = PlanExecutionAdapter()
            executable = adapter.convert_plan(plan)
            assert executable.steps[0].risk_level == risk.value
            assert executable.overall_risk == risk.value

    def test_evidence_chain_preserved(self):
        plan = _make_plan(1)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert executable.evidence == ["evidence-1", "evidence-2"]
        assert executable.steps[0].evidence_chain == ["evidence-1", "evidence-2"]

    def test_rollback_plan_preserved(self):
        plan = _make_plan(1)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert executable.rollback_plan == "undo everything"

    def test_plan_added_to_graph(self):
        adapter = PlanExecutionAdapter()
        plan = _make_plan(1)
        executable = adapter.convert_plan(plan)
        assert adapter.execution_graph.get(executable.id) is executable

    def test_empty_plan_conversion(self):
        plan = CompositionPlan(
            id="empty",
            intent=CompositionIntent(description="Empty"),
            steps=[],
        )
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert len(executable.steps) == 0
        assert executable.intent == "Empty"


# ── Dependency preservation tests ─────────────────────────────────────────────


class TestDependencyPreservation:
    def test_chain_dependencies(self):
        plan = _make_plan(3, chain=True)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert len(executable.dependencies) == 2
        assert executable.dependencies[0].source_step_id == "step-0"
        assert executable.dependencies[0].target_step_id == "step-1"
        assert executable.dependencies[1].source_step_id == "step-1"
        assert executable.dependencies[1].target_step_id == "step-2"

    def test_no_dependencies(self):
        plan = _make_plan(3, chain=False)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert len(executable.dependencies) == 0

    def test_step_depends_on_preserved(self):
        plan = _make_plan(3, chain=True)
        adapter = PlanExecutionAdapter()
        executable = adapter.convert_plan(plan)
        assert executable.steps[0].depends_on == []
        assert executable.steps[1].depends_on == ["step-0"]
        assert executable.steps[2].depends_on == ["step-1"]

    def test_dependency_to_dict(self):
        dep = ExecutionDependency("a", "b", "sequential")
        d = dep.to_dict()
        assert d["source"] == "a"
        assert d["target"] == "b"
        assert d["type"] == "sequential"


# ── Governance preservation tests ─────────────────────────────────────────────


class TestGovernancePreservation:
    def test_governance_mode_in_metadata(self):
        plan = _make_plan(1, governance=GovernanceMode.OPERATOR_REQUIRED)
        adapter = PlanExecutionAdapter(governed_spine=FakeSpine(auto_approve=False))
        executable = adapter.convert_plan(plan)
        envelope = adapter._build_envelope(executable.steps[0], executable)
        assert envelope.metadata["governance_mode"] == "operator_required"
        assert envelope.constraints.require_approval is True

    def test_risk_level_in_envelope(self):
        plan = _make_plan(1, risk=RiskClass.CRITICAL)
        adapter = PlanExecutionAdapter(governed_spine=FakeSpine())
        executable = adapter.convert_plan(plan)
        envelope = adapter._build_envelope(executable.steps[0], executable)
        assert envelope.risk_level == "critical"

    def test_plan_id_in_metadata(self):
        plan = _make_plan(1)
        adapter = PlanExecutionAdapter(governed_spine=FakeSpine())
        executable = adapter.convert_plan(plan)
        envelope = adapter._build_envelope(executable.steps[0], executable)
        assert envelope.metadata["plan_id"] == executable.id
        assert envelope.metadata["step_id"] == "step-0"

    def test_verification_strategy_set(self):
        plan = _make_plan(1)
        adapter = PlanExecutionAdapter(governed_spine=FakeSpine())
        executable = adapter.convert_plan(plan)
        envelope = adapter._build_envelope(executable.steps[0], executable)
        assert envelope.verification is not None
        assert "verify step 0" in envelope.verification.description

    def test_rollback_strategy_set(self):
        plan = _make_plan(1)
        adapter = PlanExecutionAdapter(governed_spine=FakeSpine())
        executable = adapter.convert_plan(plan)
        envelope = adapter._build_envelope(executable.steps[0], executable)
        assert envelope.rollback is not None
        assert "undo everything" in envelope.rollback.description

    def test_high_risk_retries_zero(self):
        plan = _make_plan(1, risk=RiskClass.HIGH)
        adapter = PlanExecutionAdapter(governed_spine=FakeSpine())
        executable = adapter.convert_plan(plan)
        envelope = adapter._build_envelope(executable.steps[0], executable)
        assert envelope.constraints.max_retries == 0

    def test_low_risk_retries_one(self):
        plan = _make_plan(1, risk=RiskClass.LOW)
        adapter = PlanExecutionAdapter(governed_spine=FakeSpine())
        executable = adapter.convert_plan(plan)
        envelope = adapter._build_envelope(executable.steps[0], executable)
        assert envelope.constraints.max_retries == 1


# ── Approval routing tests ────────────────────────────────────────────────────


class TestApprovalRouting:
    def test_operator_required_goes_to_pending(self):
        spine = FakeSpine(auto_approve=False)
        adapter = PlanExecutionAdapter(governed_spine=spine)
        plan = _make_plan(1, governance=GovernanceMode.OPERATOR_REQUIRED)
        executable = adapter.convert_plan(plan)
        result = adapter.execute_plan(executable)
        assert result.steps[0].status == StepExecutionStatus.AWAITING_APPROVAL

    def test_approve_step_executes(self):
        spine = FakeSpine(auto_approve=False)
        adapter = PlanExecutionAdapter(governed_spine=spine)
        plan = _make_plan(1, governance=GovernanceMode.OPERATOR_REQUIRED)
        executable = adapter.convert_plan(plan)
        adapter.execute_plan(executable)
        pending = adapter.check_pending_approvals(executable)
        assert len(pending) == 1
        step = adapter.approve_step(executable, "step-0", approved_by="test")
        assert step is not None
        assert step.status == StepExecutionStatus.COMPLETED

    def test_approve_nonexistent_step_returns_none(self):
        spine = FakeSpine()
        adapter = PlanExecutionAdapter(governed_spine=spine)
        plan = _make_plan(1)
        executable = adapter.convert_plan(plan)
        result = adapter.approve_step(executable, "nonexistent")
        assert result is None

    def test_approve_without_spine_returns_none(self):
        adapter = PlanExecutionAdapter()
        plan = _make_plan(1)
        executable = adapter.convert_plan(plan)
        result = adapter.approve_step(executable, "step-0")
        assert result is None


# ── Execution graph traversal tests ───────────────────────────────────────────


class TestExecutionGraphTraversal:
    def test_parallel_execution_all_succeed(self):
        spine = FakeSpine()
        adapter = PlanExecutionAdapter(governed_spine=spine)
        plan = _make_plan(3, chain=False)
        executable = adapter.convert_plan(plan)
        result = adapter.execute_plan(executable)
        assert result.status == ExecutionGraphStatus.COMPLETED
        assert all(s.status == StepExecutionStatus.COMPLETED for s in result.steps)
        assert len(spine.submitted) == 3

    def test_sequential_execution_chain(self):
        spine = FakeSpine()
        adapter = PlanExecutionAdapter(governed_spine=spine)
        plan = _make_plan(3, chain=True)
        executable = adapter.convert_plan(plan)
        result = adapter.execute_plan(executable)
        assert result.status == ExecutionGraphStatus.COMPLETED
        assert all(s.status == StepExecutionStatus.COMPLETED for s in result.steps)

    def test_failed_step_blocks_dependents(self):
        spine = FakeSpine(fail_steps={"step-0"})
        adapter = PlanExecutionAdapter(governed_spine=spine)
        plan = _make_plan(3, chain=True)
        executable = adapter.convert_plan(plan)
        result = adapter.execute_plan(executable)
        assert result.steps[0].status == StepExecutionStatus.FAILED
        assert result.steps[1].status == StepExecutionStatus.BLOCKED_BY_FAILURE
        assert result.steps[2].status == StepExecutionStatus.BLOCKED_BY_FAILURE
        assert result.status == ExecutionGraphStatus.FAILED

    def test_partial_failure_status(self):
        spine = FakeSpine(fail_steps={"step-2"})
        adapter = PlanExecutionAdapter(governed_spine=spine)
        plan = _make_plan(3, chain=False)
        executable = adapter.convert_plan(plan)
        result = adapter.execute_plan(executable)
        assert result.status == ExecutionGraphStatus.PARTIALLY_COMPLETED
        assert result.success_count() == 2
        assert result.failure_count() == 1

    def test_rejected_step_fails(self):
        spine = FakeSpine(reject_steps={"step-1"})
        adapter = PlanExecutionAdapter(governed_spine=spine)
        plan = _make_plan(3, chain=False)
        executable = adapter.convert_plan(plan)
        result = adapter.execute_plan(executable)
        assert result.steps[1].status == StepExecutionStatus.FAILED
        assert "governance_rejected" in result.steps[1].error
        assert result.status == ExecutionGraphStatus.PARTIALLY_COMPLETED

    def test_no_spine_fails_immediately(self):
        adapter = PlanExecutionAdapter()
        plan = _make_plan(2)
        executable = adapter.convert_plan(plan)
        result = adapter.execute_plan(executable)
        assert result.status == ExecutionGraphStatus.FAILED

    def test_ready_steps_respects_completed(self):
        plan = ExecutablePlan(steps=[
            ExecutableStep(composition_step_id="a", depends_on=[], status=StepExecutionStatus.COMPLETED),
            ExecutableStep(composition_step_id="b", depends_on=["a"], status=StepExecutionStatus.PENDING),
        ])
        ready = plan.ready_steps()
        assert len(ready) == 1
        assert ready[0].composition_step_id == "b"

    def test_ready_steps_blocks_on_failure(self):
        plan = ExecutablePlan(steps=[
            ExecutableStep(composition_step_id="a", depends_on=[], status=StepExecutionStatus.FAILED),
            ExecutableStep(composition_step_id="b", depends_on=["a"], status=StepExecutionStatus.PENDING),
        ])
        ready = plan.ready_steps()
        assert len(ready) == 0
        assert plan.steps[1].status == StepExecutionStatus.BLOCKED_BY_FAILURE

    def test_is_complete_all_terminal(self):
        plan = ExecutablePlan(steps=[
            ExecutableStep(status=StepExecutionStatus.COMPLETED),
            ExecutableStep(status=StepExecutionStatus.FAILED),
            ExecutableStep(status=StepExecutionStatus.SKIPPED),
        ])
        assert plan.is_complete() is True

    def test_is_complete_with_pending(self):
        plan = ExecutablePlan(steps=[
            ExecutableStep(status=StepExecutionStatus.COMPLETED),
            ExecutableStep(status=StepExecutionStatus.PENDING),
        ])
        assert plan.is_complete() is False


# ── Rollback generation tests ─────────────────────────────────────────────────


class TestRollbackGeneration:
    def test_rollback_strategy_from_plan(self):
        plan = _make_plan(1)
        adapter = PlanExecutionAdapter(governed_spine=FakeSpine())
        executable = adapter.convert_plan(plan)
        envelope = adapter._build_envelope(executable.steps[0], executable)
        assert envelope.rollback is not None
        assert envelope.rollback.description == "undo everything"

    def test_no_rollback_when_plan_empty(self):
        plan = CompositionPlan(
            id="no-rb",
            intent=CompositionIntent(description="No rollback"),
            steps=[CompositionStep(id="s1", description="step")],
            rollback_plan="",
        )
        adapter = PlanExecutionAdapter(governed_spine=FakeSpine())
        executable = adapter.convert_plan(plan)
        envelope = adapter._build_envelope(executable.steps[0], executable)
        assert envelope.rollback is None


# ── Outcome generation tests ──────────────────────────────────────────────────


class TestOutcomeGeneration:
    def test_outcomes_recorded_on_success(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            loop = OutcomeLearningLoop(store_path=path)
            spine = FakeSpine()
            adapter = PlanExecutionAdapter(governed_spine=spine, outcome_loop=loop)
            plan = _make_plan(3, chain=False)
            executable = adapter.convert_plan(plan)
            adapter.execute_plan(executable)
            assert len(loop.recent_outcomes(50)) == 3
            for outcome in loop.recent_outcomes(50):
                assert outcome.status == OutcomeStatus.SUCCESS
                assert outcome.plan_id == "plan-001"
        finally:
            os.unlink(path)

    def test_outcomes_recorded_on_failure(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            loop = OutcomeLearningLoop(store_path=path)
            spine = FakeSpine(fail_steps={"step-0"})
            adapter = PlanExecutionAdapter(governed_spine=spine, outcome_loop=loop)
            plan = _make_plan(1)
            executable = adapter.convert_plan(plan)
            adapter.execute_plan(executable)
            outcomes = loop.recent_outcomes(50)
            assert len(outcomes) == 1
            assert outcomes[0].status == OutcomeStatus.FAILURE
        finally:
            os.unlink(path)

    def test_outcomes_include_step_id(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            loop = OutcomeLearningLoop(store_path=path)
            spine = FakeSpine()
            adapter = PlanExecutionAdapter(governed_spine=spine, outcome_loop=loop)
            plan = _make_plan(1)
            executable = adapter.convert_plan(plan)
            adapter.execute_plan(executable)
            outcome = loop.recent_outcomes(1)[0]
            assert outcome.step_id == "step-0"
        finally:
            os.unlink(path)

    def test_no_outcome_without_loop(self):
        spine = FakeSpine()
        adapter = PlanExecutionAdapter(governed_spine=spine, outcome_loop=None)
        plan = _make_plan(1)
        executable = adapter.convert_plan(plan)
        adapter.execute_plan(executable)


# ── Memory candidate generation tests ─────────────────────────────────────────


class TestMemoryCandidateGeneration:
    def test_success_generates_pattern_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MemoryPromotionPipeline(store_dir=tmpdir)
            spine = FakeSpine()
            adapter = PlanExecutionAdapter(
                governed_spine=spine, memory_pipeline=pipeline,
            )
            plan = _make_plan(2)
            executable = adapter.convert_plan(plan)
            adapter.execute_plan(executable)
            candidates = pipeline.list_candidates()
            assert len(candidates) >= 1
            assert any(c.category == MemoryCategory.PATTERN for c in candidates)

    def test_failure_generates_observation_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MemoryPromotionPipeline(store_dir=tmpdir)
            spine = FakeSpine(fail_steps={"step-0"})
            adapter = PlanExecutionAdapter(
                governed_spine=spine, memory_pipeline=pipeline,
            )
            plan = _make_plan(1)
            executable = adapter.convert_plan(plan)
            adapter.execute_plan(executable)
            candidates = pipeline.list_candidates()
            assert len(candidates) >= 1
            assert any(c.category == MemoryCategory.OBSERVATION for c in candidates)

    def test_partial_generates_observation_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MemoryPromotionPipeline(store_dir=tmpdir)
            spine = FakeSpine(fail_steps={"step-1"})
            adapter = PlanExecutionAdapter(
                governed_spine=spine, memory_pipeline=pipeline,
            )
            plan = _make_plan(2)
            executable = adapter.convert_plan(plan)
            adapter.execute_plan(executable)
            candidates = pipeline.list_candidates()
            assert len(candidates) >= 1

    def test_no_auto_promotion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MemoryPromotionPipeline(store_dir=tmpdir)
            spine = FakeSpine()
            adapter = PlanExecutionAdapter(
                governed_spine=spine, memory_pipeline=pipeline,
            )
            plan = _make_plan(2)
            executable = adapter.convert_plan(plan)
            adapter.execute_plan(executable)
            canonical = pipeline.list_canonical()
            assert len(canonical) == 0

    def test_no_memory_without_pipeline(self):
        spine = FakeSpine()
        adapter = PlanExecutionAdapter(governed_spine=spine, memory_pipeline=None)
        plan = _make_plan(1)
        executable = adapter.convert_plan(plan)
        adapter.execute_plan(executable)


# ── Action type inference tests ───────────────────────────────────────────────


class TestActionTypeInference:
    def test_filesystem_inferred(self):
        assert _infer_action_type("create file config.yaml") == ActionType.FILESYSTEM

    def test_container_inferred(self):
        assert _infer_action_type("restart docker container") == ActionType.CONTAINER

    def test_deployment_inferred(self):
        assert _infer_action_type("deploy to production") == ActionType.DEPLOYMENT

    def test_test_inferred(self):
        assert _infer_action_type("verify health check") == ActionType.TEST

    def test_process_inferred(self):
        assert _infer_action_type("restart service") == ActionType.PROCESS

    def test_default_is_state(self):
        assert _infer_action_type("something unknown") == ActionType.STATE

    def test_explicit_type_keyword(self):
        assert _infer_action_type("network configuration") == ActionType.NETWORK
        assert _infer_action_type("cleanup old files") == ActionType.CLEANUP
        assert _infer_action_type("ingestion pipeline") == ActionType.INGESTION


# ── Serialization tests ──────────────────────────────────────────────────────


class TestSerialization:
    def test_executable_step_to_dict(self):
        step = ExecutableStep(
            id="s1", plan_id="p1", composition_step_id="cs1",
            description="test", action="do thing", risk_level="low",
        )
        d = step.to_dict()
        assert d["id"] == "s1"
        assert d["plan_id"] == "p1"
        assert d["status"] == "pending"

    def test_executable_plan_to_dict(self):
        plan = ExecutablePlan(
            id="p1", source_plan_id="sp1", intent="test",
            steps=[ExecutableStep(id="s1", status=StepExecutionStatus.COMPLETED)],
        )
        d = plan.to_dict()
        assert d["summary"]["id"] == "p1"
        assert d["summary"]["total_steps"] == 1
        assert d["summary"]["step_status"]["completed"] == 1

    def test_execution_graph_to_dict(self):
        graph = ExecutionGraph()
        plan = ExecutablePlan(id="p1", intent="test")
        graph.add(plan)
        d = graph.to_dict()
        assert d["total_plans"] == 1
        assert "p1" in d["plans"]

    def test_adapter_to_dict(self):
        adapter = PlanExecutionAdapter()
        d = adapter.to_dict()
        assert "execution_graph" in d
        assert "pending_envelopes" in d

    def test_plan_summary(self):
        plan = ExecutablePlan(
            id="p1", source_plan_id="sp1", intent="test",
            overall_risk="high", governance_required="operator_required",
        )
        s = plan.summary()
        assert s["overall_risk"] == "high"
        assert s["governance_required"] == "operator_required"


# ── ExecutionGraph tests ─────────────────────────────────────────────────────


class TestExecutionGraph:
    def test_add_and_get(self):
        graph = ExecutionGraph()
        plan = ExecutablePlan(id="p1")
        graph.add(plan)
        assert graph.get("p1") is plan
        assert graph.get("nonexistent") is None

    def test_active_plans(self):
        graph = ExecutionGraph()
        graph.add(ExecutablePlan(id="a", status=ExecutionGraphStatus.EXECUTING))
        graph.add(ExecutablePlan(id="b", status=ExecutionGraphStatus.COMPLETED))
        graph.add(ExecutablePlan(id="c", status=ExecutionGraphStatus.PENDING))
        active = graph.active_plans()
        assert len(active) == 2

    def test_completed_plans(self):
        graph = ExecutionGraph()
        graph.add(ExecutablePlan(id="a", status=ExecutionGraphStatus.COMPLETED, completed_at=2.0))
        graph.add(ExecutablePlan(id="b", status=ExecutionGraphStatus.FAILED, completed_at=1.0))
        graph.add(ExecutablePlan(id="c", status=ExecutionGraphStatus.EXECUTING))
        completed = graph.completed_plans()
        assert len(completed) == 2
        assert completed[0].id == "a"


# ── Integration-style end-to-end test ────────────────────────────────────────


class TestEndToEnd:
    def test_full_observe_understand_act_learn_loop(self):
        """Full pipeline: plan → convert → execute → outcomes → memory."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            outcome_path = f.name
        with tempfile.TemporaryDirectory() as memory_dir:
            try:
                outcome_loop = OutcomeLearningLoop(store_path=outcome_path)
                memory_pipeline = MemoryPromotionPipeline(store_dir=memory_dir)
                spine = FakeSpine()

                adapter = PlanExecutionAdapter(
                    governed_spine=spine,
                    outcome_loop=outcome_loop,
                    memory_pipeline=memory_pipeline,
                )

                plan = _make_plan(4, chain=True)
                executable = adapter.convert_plan(plan)

                assert executable.status == ExecutionGraphStatus.PENDING
                assert len(executable.steps) == 4

                result = adapter.execute_plan(executable)

                assert result.status == ExecutionGraphStatus.COMPLETED
                assert result.success_count() == 4

                outcomes = outcome_loop.recent_outcomes(50)
                assert len(outcomes) == 4

                candidates = memory_pipeline.list_candidates()
                assert len(candidates) >= 1

                canonical = memory_pipeline.list_canonical()
                assert len(canonical) == 0

                graph_data = adapter.to_dict()
                assert graph_data["execution_graph"]["total_plans"] == 1

            finally:
                os.unlink(outcome_path)
