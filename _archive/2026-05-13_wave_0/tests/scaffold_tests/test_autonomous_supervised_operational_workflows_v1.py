"""Tests for Phase 96.8BS — Autonomous Supervised Operational Workflows.

Validates:
  - Workflow contracts (9 contracts, enums, serialization, hashing)
  - Workflow governance bridge (recursion, escalation, step governance)
  - Workflow boundary policies (depth, duration, transitions, sequences)
  - Workflow engine (spine-only execution, all 6 workflows)
  - Workflow registry (7 registered, 6 implemented)
  - Workflow continuity bridge (checkpoints, resume, open loops)
  - Workflow observability pipeline (9 event types)
  - Workflow replay validator (6 checks per trace, session replay)
  - Workflow lifecycle engine (9 states, transitions, terminal states)
  - Integration (full workflow execution through spine)
  - No direct execution (all steps go through spine)
"""

from __future__ import annotations

import tempfile
import pytest
from typing import Any

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.workflows.operational_workflow_contracts_v1 import (
    MODE_PERMISSIONS,
    OperationalWorkflow,
    SupervisedOperationalMode,
    WorkflowBoundary,
    WorkflowCheckpoint,
    WorkflowContext,
    WorkflowContinuation,
    WorkflowContinuationType,
    WorkflowDecision,
    WorkflowDecisionType,
    WorkflowOutcome,
    WorkflowPhase,
    WorkflowReceipt,
    WorkflowStep,
    WorkflowStepType,
    WorkflowType,
    _content_hash,
    _new_id,
)
from core.workflows.workflow_governance_bridge_v1 import (
    FORBIDDEN_ESCALATION_PATHS,
    FORBIDDEN_RECURSIVE_CHAINS,
    MODE_HIERARCHY,
    WorkflowGovernanceBridge,
)
from core.workflows.workflow_boundary_policies_v1 import (
    DEFAULT_BOUNDARIES,
    WorkflowBoundaryEnforcer,
)
from core.workflows.canonical_operational_workflow_engine_v1 import (
    CanonicalOperationalWorkflowEngine,
)
from core.workflows.operational_workflow_registry_v1 import (
    OperationalWorkflowRegistry,
)
from core.workflows.workflow_continuity_bridge_v1 import (
    WorkflowContinuityBridge,
)
from core.workflows.workflow_observability_pipeline_v1 import (
    WorkflowObservabilityPipeline,
)
from core.workflows.workflow_replay_validator_v1 import (
    WorkflowReplayValidator,
)
from core.workflows.workflow_lifecycle_engine_v1 import (
    VALID_TRANSITIONS,
    WorkflowLifecycleEngine,
    WorkflowSession,
)
from core.runtime.live_substrate_runtime_spine_v1 import LiveSubstrateRuntimeSpine


# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture
def spine():
    s = LiveSubstrateRuntimeSpine()
    s.initialize("test-session")
    return s


@pytest.fixture
def engine(spine):
    return CanonicalOperationalWorkflowEngine(spine=spine)


@pytest.fixture
def registry():
    return OperationalWorkflowRegistry()


@pytest.fixture
def governance():
    return WorkflowGovernanceBridge()


@pytest.fixture
def enforcer():
    return WorkflowBoundaryEnforcer()


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


# =====================================================================
# Test Workflow Contracts
# =====================================================================


class TestWorkflowContracts:
    def test_workflow_type_enum(self):
        assert len(WorkflowType) == 8
        assert WorkflowType.OPERATIONAL_BRIEFING.value == "operational_briefing"

    def test_workflow_step_type_enum(self):
        assert len(WorkflowStepType) == 7
        assert WorkflowStepType.SPINE_TRAVERSAL.value == "spine_traversal"

    def test_workflow_phase_enum(self):
        assert len(WorkflowPhase) == 9

    def test_supervised_operational_mode_enum(self):
        assert len(SupervisedOperationalMode) == 4
        assert SupervisedOperationalMode.INSPECT_ONLY.value == "inspect_only"

    def test_workflow_decision_type_enum(self):
        assert len(WorkflowDecisionType) == 9

    def test_workflow_continuation_type_enum(self):
        assert len(WorkflowContinuationType) == 5

    def test_mode_permissions_complete(self):
        assert len(MODE_PERMISSIONS) == 4
        for mode in SupervisedOperationalMode:
            assert mode.value in MODE_PERMISSIONS

    def test_workflow_boundary_instantiation(self):
        b = WorkflowBoundary()
        assert b.boundary_id.startswith("wbnd-")
        assert b.max_traversal_depth == 10
        assert b.operational_mode == SupervisedOperationalMode.INSPECT_ONLY

    def test_workflow_boundary_checks(self):
        b = WorkflowBoundary(
            max_traversal_depth=5,
            operational_mode=SupervisedOperationalMode.SUPERVISED_EXECUTION,
        )
        assert b.check_depth(4)
        assert not b.check_depth(5)

    def test_workflow_boundary_step_allowed(self):
        b = WorkflowBoundary(operational_mode=SupervisedOperationalMode.INSPECT_ONLY)
        assert b.check_step_allowed(WorkflowStepType.SPINE_TRAVERSAL)
        assert not b.check_step_allowed(WorkflowStepType.CHECKPOINT)

    def test_workflow_step_instantiation(self):
        s = WorkflowStep(command="runtime-status", step_type=WorkflowStepType.SPINE_TRAVERSAL)
        assert s.step_id.startswith("wstep-")
        assert not s.completed

    def test_workflow_step_serialization(self):
        s = WorkflowStep(command="test")
        d = s.to_dict()
        assert "step_id" in d
        assert "content_hash" in d

    def test_operational_workflow_instantiation(self):
        wf = OperationalWorkflow(
            workflow_type=WorkflowType.OPERATIONAL_BRIEFING,
            name="Test",
        )
        assert wf.workflow_id.startswith("wflow-")
        assert wf.correlation_id.startswith("wcorr-")

    def test_operational_workflow_finalize(self):
        wf = OperationalWorkflow(
            steps=[
                WorkflowStep(command="a"),
                WorkflowStep(command="b"),
            ]
        )
        wf.finalize()
        assert wf.total_steps == 2
        assert wf.steps[0].step_index == 0
        assert wf.steps[1].step_index == 1

    def test_workflow_context_tracking(self):
        ctx = WorkflowContext()
        ctx.record_spine_traversal("workstation")
        assert ctx.spine_traversals == 1
        assert ctx.last_embodiment == "workstation"
        ctx.record_spine_traversal("browser")
        assert ctx.embodiment_transitions == 1
        assert ctx.spine_traversals == 2

    def test_workflow_decision_instantiation(self):
        d = WorkflowDecision(decision_type=WorkflowDecisionType.GOVERNANCE)
        assert d.decision_id.startswith("wdec-")
        assert d.approved

    def test_workflow_checkpoint_instantiation(self):
        c = WorkflowCheckpoint(workflow_id="wf-1", step_index=3)
        assert c.checkpoint_id.startswith("wchk-")
        assert c.resumable

    def test_workflow_receipt_instantiation(self):
        r = WorkflowReceipt(workflow_id="wf-1")
        assert r.receipt_id.startswith("wrcpt-")

    def test_workflow_outcome_properties(self):
        o = WorkflowOutcome(status=WorkflowPhase.COMPLETED)
        assert o.succeeded
        assert not o.denied
        o2 = WorkflowOutcome(status=WorkflowPhase.DENIED)
        assert o2.denied
        assert not o2.succeeded

    def test_workflow_continuation_instantiation(self):
        c = WorkflowContinuation(workflow_id="wf-1")
        assert c.continuation_id.startswith("wcont-")

    def test_all_contracts_serialize(self):
        objs = [
            WorkflowBoundary(),
            WorkflowStep(command="test"),
            OperationalWorkflow(name="test"),
            WorkflowContext(),
            WorkflowDecision(),
            WorkflowCheckpoint(),
            WorkflowReceipt(),
            WorkflowOutcome(),
            WorkflowContinuation(),
        ]
        for obj in objs:
            d = obj.to_dict()
            assert isinstance(d, dict)
            h = obj.content_hash()
            assert isinstance(h, str) and len(h) == 24

    def test_content_hash_deterministic(self):
        s1 = WorkflowStep(command="runtime-status", step_type=WorkflowStepType.SPINE_TRAVERSAL)
        s2 = WorkflowStep(command="runtime-status", step_type=WorkflowStepType.SPINE_TRAVERSAL)
        assert s1.content_hash() == s2.content_hash()


# =====================================================================
# Test Workflow Governance Bridge
# =====================================================================


class TestWorkflowGovernanceBridge:
    def test_workflow_start_approved(self, governance):
        wf = OperationalWorkflow(
            workflow_type=WorkflowType.OPERATIONAL_BRIEFING,
            operational_mode=SupervisedOperationalMode.INSPECT_ONLY,
        )
        ctx = WorkflowContext()
        dec = governance.evaluate_workflow_start(wf, ctx)
        assert dec.approved

    def test_recursive_chain_denied(self, governance):
        wf1 = OperationalWorkflow(workflow_type=WorkflowType.OPERATIONAL_BRIEFING)
        ctx = WorkflowContext()
        governance.evaluate_workflow_start(wf1, ctx)
        wf2 = OperationalWorkflow(workflow_type=WorkflowType.OPERATIONAL_BRIEFING)
        dec = governance.evaluate_workflow_start(wf2, ctx)
        assert not dec.approved
        assert "Recursive" in dec.denial_reason

    def test_complete_clears_chain(self, governance):
        wf = OperationalWorkflow(workflow_type=WorkflowType.RUNTIME_INSPECTION)
        ctx = WorkflowContext()
        governance.evaluate_workflow_start(wf, ctx)
        governance.complete_workflow("runtime_inspection")
        wf2 = OperationalWorkflow(workflow_type=WorkflowType.RUNTIME_INSPECTION)
        dec = governance.evaluate_workflow_start(wf2, ctx)
        assert dec.approved

    def test_escalation_denied(self, governance):
        dec = governance.evaluate_escalation_request(
            SupervisedOperationalMode.SUPERVISED_EXECUTION,
            SupervisedOperationalMode.INSPECT_ONLY,
            "wf-1",
            "corr-1",
        )
        assert not dec.approved

    def test_escalation_one_level_allowed(self, governance):
        dec = governance.evaluate_escalation_request(
            SupervisedOperationalMode.GOVERNED_ANALYSIS,
            SupervisedOperationalMode.INSPECT_ONLY,
            "wf-1",
            "corr-1",
        )
        assert dec.approved

    def test_step_governance_approved(self, governance):
        wf = OperationalWorkflow(
            workflow_type=WorkflowType.OPERATIONAL_BRIEFING,
            operational_mode=SupervisedOperationalMode.INSPECT_ONLY,
        )
        ctx = WorkflowContext()
        step = WorkflowStep(step_type=WorkflowStepType.SPINE_TRAVERSAL)
        dec = governance.evaluate_step(step, wf, ctx)
        assert dec.approved

    def test_step_governance_denied_by_mode(self, governance):
        wf = OperationalWorkflow(
            workflow_type=WorkflowType.OPERATIONAL_BRIEFING,
            operational_mode=SupervisedOperationalMode.INSPECT_ONLY,
        )
        ctx = WorkflowContext()
        step = WorkflowStep(step_type=WorkflowStepType.CHECKPOINT)
        dec = governance.evaluate_step(step, wf, ctx)
        assert not dec.approved

    def test_step_governance_depth_exceeded(self, governance):
        wf = OperationalWorkflow(
            workflow_type=WorkflowType.OPERATIONAL_BRIEFING,
            operational_mode=SupervisedOperationalMode.INSPECT_ONLY,
        )
        ctx = WorkflowContext()
        ctx.traversal_depth = 10
        step = WorkflowStep(step_type=WorkflowStepType.SPINE_TRAVERSAL)
        dec = governance.evaluate_step(step, wf, ctx)
        assert not dec.approved

    def test_governance_stats(self, governance):
        wf = OperationalWorkflow(workflow_type=WorkflowType.OPERATIONAL_BRIEFING)
        ctx = WorkflowContext()
        governance.evaluate_workflow_start(wf, ctx)
        stats = governance.get_stats()
        assert stats["approvals"] == 1
        assert stats["active_chain_depth"] == 1

    def test_forbidden_workflow_transitions(self, governance):
        wf1 = OperationalWorkflow(workflow_type=WorkflowType.WORKSTATION_INSPECTION)
        ctx = WorkflowContext()
        governance.evaluate_workflow_start(wf1, ctx)
        wf2 = OperationalWorkflow(workflow_type=WorkflowType.BROWSER_INSPECTION)
        dec = governance.evaluate_workflow_start(wf2, ctx)
        assert not dec.approved


# =====================================================================
# Test Workflow Boundary Policies
# =====================================================================


class TestWorkflowBoundaryPolicies:
    def test_default_boundaries_all_modes(self, enforcer):
        for mode in SupervisedOperationalMode:
            boundary = enforcer.create_boundary(mode)
            assert boundary.operational_mode == mode

    def test_inspect_only_boundaries(self, enforcer):
        b = enforcer.create_boundary(SupervisedOperationalMode.INSPECT_ONLY)
        assert b.max_traversal_depth == DEFAULT_BOUNDARIES["inspect_only"]["max_traversal_depth"]

    def test_override_capped_at_default(self, enforcer):
        b = enforcer.create_boundary(
            SupervisedOperationalMode.INSPECT_ONLY,
            overrides={"max_traversal_depth": 100},
        )
        assert b.max_traversal_depth == DEFAULT_BOUNDARIES["inspect_only"]["max_traversal_depth"]

    def test_override_below_default(self, enforcer):
        b = enforcer.create_boundary(
            SupervisedOperationalMode.SUPERVISED_EXECUTION,
            overrides={"max_traversal_depth": 3},
        )
        assert b.max_traversal_depth == 3

    def test_boundary_check_pass(self, enforcer):
        b = enforcer.create_boundary(SupervisedOperationalMode.INSPECT_ONLY)
        ctx = WorkflowContext()
        dec = enforcer.check_all_boundaries(b, ctx)
        assert dec.approved

    def test_boundary_check_depth_exceeded(self, enforcer):
        b = enforcer.create_boundary(SupervisedOperationalMode.INSPECT_ONLY)
        ctx = WorkflowContext()
        ctx.traversal_depth = 100
        dec = enforcer.check_all_boundaries(b, ctx)
        assert not dec.approved
        assert "DEPTH_EXCEEDED" in dec.denial_reason

    def test_boundary_check_duration_exceeded(self, enforcer):
        b = enforcer.create_boundary(SupervisedOperationalMode.INSPECT_ONLY)
        ctx = WorkflowContext()
        dec = enforcer.check_all_boundaries(b, ctx, elapsed_seconds=999)
        assert not dec.approved
        assert "DURATION_EXCEEDED" in dec.denial_reason

    def test_boundary_check_traversals_exceeded(self, enforcer):
        b = enforcer.create_boundary(SupervisedOperationalMode.INSPECT_ONLY)
        ctx = WorkflowContext()
        ctx.spine_traversals = 100
        dec = enforcer.check_all_boundaries(b, ctx)
        assert not dec.approved

    def test_boundary_check_forbidden_sequence(self, enforcer):
        b = enforcer.create_boundary(SupervisedOperationalMode.INSPECT_ONLY)
        ctx = WorkflowContext()
        recent = ["spine_traversal"] * 4
        dec = enforcer.check_all_boundaries(b, ctx, recent_step_types=recent)
        assert not dec.approved
        assert "FORBIDDEN_SEQUENCE" in dec.denial_reason

    def test_enforcer_stats(self, enforcer):
        b = enforcer.create_boundary(SupervisedOperationalMode.INSPECT_ONLY)
        ctx = WorkflowContext()
        enforcer.check_all_boundaries(b, ctx)
        stats = enforcer.get_stats()
        assert stats["checks_performed"] == 1


# =====================================================================
# Test Workflow Engine
# =====================================================================


class TestWorkflowEngine:
    def test_execute_operational_briefing(self, engine, registry):
        wf = registry.create_workflow("operational_briefing", session_id="test")
        outcome = engine.execute_workflow(wf)
        assert outcome.succeeded
        assert outcome.steps_completed == outcome.steps_total
        assert outcome.spine_traversals >= 2

    def test_execute_operational_resume(self, engine, registry):
        wf = registry.create_workflow("operational_resume", session_id="test")
        outcome = engine.execute_workflow(wf)
        assert outcome.succeeded

    def test_execute_runtime_inspection(self, engine, registry):
        wf = registry.create_workflow("runtime_inspection", session_id="test")
        outcome = engine.execute_workflow(wf)
        assert outcome.succeeded
        assert outcome.spine_traversals >= 3

    def test_execute_governed_planning(self, engine, registry):
        wf = registry.create_workflow("governed_planning", session_id="test")
        outcome = engine.execute_workflow(wf)
        assert outcome.succeeded

    def test_execute_browser_inspection(self, engine, registry):
        wf = registry.create_workflow("browser_inspection", session_id="test")
        outcome = engine.execute_workflow(wf)
        assert outcome.succeeded

    def test_execute_workstation_inspection(self, engine, registry):
        wf = registry.create_workflow("workstation_inspection", session_id="test")
        outcome = engine.execute_workflow(wf)
        assert outcome.succeeded

    def test_recursive_workflow_denied(self, spine):
        gov = WorkflowGovernanceBridge()
        engine = CanonicalOperationalWorkflowEngine(spine=spine, governance=gov)
        registry = OperationalWorkflowRegistry()

        wf1 = registry.create_workflow("operational_briefing", session_id="test")
        gov.evaluate_workflow_start(wf1, WorkflowContext())

        wf2 = registry.create_workflow("operational_briefing", session_id="test")
        outcome = engine.execute_workflow(wf2)
        assert outcome.denied

    def test_engine_stats(self, engine, registry):
        wf = registry.create_workflow("operational_briefing", session_id="test")
        engine.execute_workflow(wf)
        stats = engine.get_stats()
        assert stats["workflows_executed"] == 1
        assert stats["workflows_completed"] == 1

    def test_checkpoints_created(self, engine, registry):
        wf = registry.create_workflow("operational_briefing", session_id="test")
        outcome = engine.execute_workflow(wf)
        assert outcome.checkpoints_created >= 1

    def test_lineage_receipts_emitted(self, engine, registry):
        wf = registry.create_workflow("operational_briefing", session_id="test")
        outcome = engine.execute_workflow(wf)
        assert len(outcome.lineage_receipts) > 0

    def test_governance_decisions_recorded(self, engine, registry):
        wf = registry.create_workflow("operational_briefing", session_id="test")
        outcome = engine.execute_workflow(wf)
        assert outcome.governance_decisions > 0


# =====================================================================
# Test Workflow Registry
# =====================================================================


class TestWorkflowRegistry:
    def test_list_all_workflows(self, registry):
        workflows = registry.list_workflows()
        assert len(workflows) == 7

    def test_list_implemented(self, registry):
        implemented = registry.list_implemented()
        assert len(implemented) == 6

    def test_create_known_workflow(self, registry):
        wf = registry.create_workflow("operational_briefing")
        assert wf is not None
        assert wf.workflow_type == WorkflowType.OPERATIONAL_BRIEFING

    def test_create_unknown_workflow(self, registry):
        wf = registry.create_workflow("nonexistent")
        assert wf is None

    def test_workflow_info(self, registry):
        info = registry.get_workflow_info("operational_briefing")
        assert info is not None
        assert info["implemented"]

    def test_workflow_has_steps(self, registry):
        for wf_type in [
            "operational_briefing",
            "operational_resume",
            "runtime_inspection",
            "governed_planning",
            "browser_inspection",
            "workstation_inspection",
        ]:
            wf = registry.create_workflow(wf_type)
            assert len(wf.steps) > 0, f"{wf_type} has no steps"

    def test_mode_override(self, registry):
        wf = registry.create_workflow(
            "operational_briefing",
            mode_override=SupervisedOperationalMode.GOVERNED_ANALYSIS,
        )
        assert wf.operational_mode == SupervisedOperationalMode.GOVERNED_ANALYSIS

    def test_registry_stats(self, registry):
        stats = registry.get_stats()
        assert stats["total_registered"] == 7
        assert stats["implemented"] == 6


# =====================================================================
# Test Workflow Continuity Bridge
# =====================================================================


class TestWorkflowContinuityBridge:
    def test_persist_successful_outcome(self, tmp_dir):
        bridge = WorkflowContinuityBridge(state_dir=tmp_dir)
        bridge.start_session("test")
        outcome = WorkflowOutcome(
            workflow_id="wf-1",
            status=WorkflowPhase.COMPLETED,
        )
        cont = bridge.persist_outcome(outcome)
        assert cont.continuation_type == WorkflowContinuationType.COMPLETE

    def test_persist_denied_outcome(self, tmp_dir):
        bridge = WorkflowContinuityBridge(state_dir=tmp_dir)
        outcome = WorkflowOutcome(
            workflow_id="wf-1",
            status=WorkflowPhase.DENIED,
        )
        cont = bridge.persist_outcome(outcome)
        assert cont.continuation_type == WorkflowContinuationType.DENIED

    def test_persist_failed_outcome_creates_loop(self, tmp_dir):
        bridge = WorkflowContinuityBridge(state_dir=tmp_dir)
        outcome = WorkflowOutcome(
            workflow_id="wf-1",
            status=WorkflowPhase.FAILED,
            error_message="test error",
        )
        cont = bridge.persist_outcome(outcome)
        assert cont.continuation_type == WorkflowContinuationType.FAILED
        assert len(cont.open_loop_ids) == 1
        assert len(bridge.get_open_loops()) == 1

    def test_resolve_open_loop(self, tmp_dir):
        bridge = WorkflowContinuityBridge(state_dir=tmp_dir)
        outcome = WorkflowOutcome(
            workflow_id="wf-1",
            status=WorkflowPhase.FAILED,
        )
        bridge.persist_outcome(outcome)
        loop_id = bridge.get_open_loops()[0]["loop_id"]
        assert bridge.resolve_open_loop(loop_id)
        assert len(bridge.get_open_loops()) == 0

    def test_checkpoint_persistence(self, tmp_dir):
        bridge = WorkflowContinuityBridge(state_dir=tmp_dir)
        chk = WorkflowCheckpoint(workflow_id="wf-1", step_index=2)
        bridge.persist_checkpoint(chk)
        latest = bridge.get_latest_checkpoint("wf-1")
        assert latest is not None
        assert latest.step_index == 2

    def test_resume_packet(self, tmp_dir):
        bridge = WorkflowContinuityBridge(state_dir=tmp_dir)
        bridge.start_session("test")
        bridge.persist_checkpoint(WorkflowCheckpoint(workflow_id="wf-1"))
        packet = bridge.create_resume_packet()
        assert "open_loops" in packet
        assert "available_checkpoints" in packet

    def test_continuity_stats(self, tmp_dir):
        bridge = WorkflowContinuityBridge(state_dir=tmp_dir)
        outcome = WorkflowOutcome(status=WorkflowPhase.COMPLETED)
        bridge.persist_outcome(outcome)
        stats = bridge.get_stats()
        assert stats["events_persisted"] == 1


# =====================================================================
# Test Workflow Observability Pipeline
# =====================================================================


class TestWorkflowObservabilityPipeline:
    def test_record_workflow_trace(self, tmp_dir):
        obs = WorkflowObservabilityPipeline(obs_dir=tmp_dir)
        wf = OperationalWorkflow(name="test")
        outcome = WorkflowOutcome(status=WorkflowPhase.COMPLETED)
        obs.record_workflow_trace(wf, outcome)
        assert len(obs.get_recent_traces()) == 1

    def test_record_step_event(self, tmp_dir):
        obs = WorkflowObservabilityPipeline(obs_dir=tmp_dir)
        obs.record_step_event("wf-1", "step-1", "spine_traversal", "runtime-status", True)
        assert len(obs.get_recent_step_events()) == 1

    def test_record_governance_event(self, tmp_dir):
        obs = WorkflowObservabilityPipeline(obs_dir=tmp_dir)
        obs.record_governance_event("wf-1", "start", True, ["RULE_1"])
        assert len(obs.get_recent_governance_events()) == 1

    def test_record_boundary_event(self, tmp_dir):
        obs = WorkflowObservabilityPipeline(obs_dir=tmp_dir)
        obs.record_boundary_event("wf-1", ["DEPTH_EXCEEDED"], {})
        stats = obs.get_stats()
        assert stats["boundary_events"] == 1

    def test_record_checkpoint_event(self, tmp_dir):
        obs = WorkflowObservabilityPipeline(obs_dir=tmp_dir)
        obs.record_checkpoint_event("wf-1", "chk-1", 3)
        stats = obs.get_stats()
        assert stats["checkpoint_events"] == 1

    def test_record_continuation_event(self, tmp_dir):
        obs = WorkflowObservabilityPipeline(obs_dir=tmp_dir)
        obs.record_continuation_event("wf-1", "complete")
        stats = obs.get_stats()
        assert stats["continuation_events"] == 1

    def test_record_completion_event(self, tmp_dir):
        obs = WorkflowObservabilityPipeline(obs_dir=tmp_dir)
        obs.record_completion_event("wf-1", "operational_briefing", 5, 5, 100)
        stats = obs.get_stats()
        assert stats["completion_events"] == 1

    def test_record_denial_event(self, tmp_dir):
        obs = WorkflowObservabilityPipeline(obs_dir=tmp_dir)
        obs.record_denial_event("wf-1", "runtime_inspection", "recursive")
        stats = obs.get_stats()
        assert stats["denial_events"] == 1

    def test_record_failure_event(self, tmp_dir):
        obs = WorkflowObservabilityPipeline(obs_dir=tmp_dir)
        obs.record_failure_event("wf-1", "governed_planning", "timeout", 2, 5)
        stats = obs.get_stats()
        assert stats["failure_events"] == 1

    def test_all_nine_event_types(self, tmp_dir):
        obs = WorkflowObservabilityPipeline(obs_dir=tmp_dir)
        wf = OperationalWorkflow(name="test")
        outcome = WorkflowOutcome(status=WorkflowPhase.COMPLETED)
        obs.record_workflow_trace(wf, outcome)
        obs.record_step_event("wf-1", "s1", "spine", "cmd", True)
        obs.record_governance_event("wf-1", "start", True, [])
        obs.record_boundary_event("wf-1", [], {})
        obs.record_checkpoint_event("wf-1", "chk-1", 1)
        obs.record_continuation_event("wf-1", "complete")
        obs.record_completion_event("wf-1", "briefing", 5, 5, 100)
        obs.record_denial_event("wf-1", "insp", "denied")
        obs.record_failure_event("wf-1", "plan", "err", 1, 5)
        stats = obs.get_stats()
        assert all(v >= 1 for v in stats.values())


# =====================================================================
# Test Workflow Replay Validator
# =====================================================================


class TestWorkflowReplayValidator:
    def test_replay_single_trace(self, tmp_dir):
        validator = WorkflowReplayValidator(proof_dir=tmp_dir)
        trace = {
            "workflow_id": "wf-1",
            "workflow_type": "operational_briefing",
            "operational_mode": "inspect_only",
            "name": "Test",
        }
        result = validator.replay_workflow_trace(trace)
        assert result.all_passed
        assert len(result.checks) == 6

    def test_replay_governed_analysis(self, tmp_dir):
        validator = WorkflowReplayValidator(proof_dir=tmp_dir)
        trace = {
            "workflow_id": "wf-2",
            "workflow_type": "governed_planning",
            "operational_mode": "governed_analysis",
            "name": "Planning",
        }
        result = validator.replay_workflow_trace(trace)
        assert result.all_passed

    def test_replay_session(self, tmp_dir):
        validator = WorkflowReplayValidator(proof_dir=tmp_dir)
        traces = [
            {
                "workflow_id": "wf-1",
                "workflow_type": "operational_briefing",
                "operational_mode": "inspect_only",
                "name": "B",
            },
            {
                "workflow_id": "wf-2",
                "workflow_type": "runtime_inspection",
                "operational_mode": "inspect_only",
                "name": "R",
            },
        ]
        session = validator.replay_session(traces, session_id="test-sess")
        assert session.all_passed
        assert len(session.results) == 2

    def test_replay_determinism(self, tmp_dir):
        validator = WorkflowReplayValidator(proof_dir=tmp_dir)
        trace = {
            "workflow_id": "wf-1",
            "workflow_type": "operational_briefing",
            "operational_mode": "inspect_only",
            "name": "Test",
        }
        r1 = validator.replay_workflow_trace(trace)
        r2 = validator.replay_workflow_trace(trace)
        for c1, c2 in zip(r1.checks, r2.checks):
            assert c1.passed == c2.passed
            assert c1.actual == c2.actual

    def test_replay_stats(self, tmp_dir):
        validator = WorkflowReplayValidator(proof_dir=tmp_dir)
        trace = {
            "workflow_id": "wf-1",
            "workflow_type": "operational_briefing",
            "operational_mode": "inspect_only",
            "name": "T",
        }
        validator.replay_workflow_trace(trace)
        stats = validator.get_stats()
        assert stats["replays"] == 1
        assert stats["checks_passed"] == 6


# =====================================================================
# Test Workflow Lifecycle Engine
# =====================================================================


class TestWorkflowLifecycleEngine:
    def test_register_workflow(self, tmp_dir):
        lce = WorkflowLifecycleEngine(state_dir=tmp_dir)
        sess = lce.register_workflow("wf-1", "briefing")
        assert sess.state == WorkflowPhase.INITIALIZED

    def test_valid_transitions(self, tmp_dir):
        lce = WorkflowLifecycleEngine(state_dir=tmp_dir)
        lce.register_workflow("wf-1")
        assert lce.transition("wf-1", WorkflowPhase.ACTIVE)
        assert lce.get_state("wf-1") == WorkflowPhase.ACTIVE

    def test_checkpoint_and_resume(self, tmp_dir):
        lce = WorkflowLifecycleEngine(state_dir=tmp_dir)
        lce.register_workflow("wf-1")
        lce.transition("wf-1", WorkflowPhase.ACTIVE)
        assert lce.transition("wf-1", WorkflowPhase.CHECKPOINTED)
        assert lce.transition("wf-1", WorkflowPhase.ACTIVE)

    def test_waiting_and_resume(self, tmp_dir):
        lce = WorkflowLifecycleEngine(state_dir=tmp_dir)
        lce.register_workflow("wf-1")
        lce.transition("wf-1", WorkflowPhase.ACTIVE)
        assert lce.transition("wf-1", WorkflowPhase.WAITING)
        assert lce.transition("wf-1", WorkflowPhase.RESUMED)
        assert lce.transition("wf-1", WorkflowPhase.ACTIVE)

    def test_terminal_states(self, tmp_dir):
        lce = WorkflowLifecycleEngine(state_dir=tmp_dir)
        lce.register_workflow("wf-1")
        lce.transition("wf-1", WorkflowPhase.ACTIVE)
        lce.transition("wf-1", WorkflowPhase.COMPLETED)
        assert not lce.transition("wf-1", WorkflowPhase.ACTIVE)

    def test_denied_is_terminal(self, tmp_dir):
        lce = WorkflowLifecycleEngine(state_dir=tmp_dir)
        lce.register_workflow("wf-1")
        lce.transition("wf-1", WorkflowPhase.DENIED)
        assert not lce.transition("wf-1", WorkflowPhase.ACTIVE)

    def test_invalid_transition(self, tmp_dir):
        lce = WorkflowLifecycleEngine(state_dir=tmp_dir)
        lce.register_workflow("wf-1")
        assert not lce.transition("wf-1", WorkflowPhase.COMPLETED)

    def test_failed_retry(self, tmp_dir):
        lce = WorkflowLifecycleEngine(state_dir=tmp_dir)
        lce.register_workflow("wf-1")
        lce.transition("wf-1", WorkflowPhase.ACTIVE)
        lce.transition("wf-1", WorkflowPhase.FAILED)
        assert lce.transition("wf-1", WorkflowPhase.ACTIVE)

    def test_active_workflows(self, tmp_dir):
        lce = WorkflowLifecycleEngine(state_dir=tmp_dir)
        lce.register_workflow("wf-1")
        lce.register_workflow("wf-2")
        lce.transition("wf-1", WorkflowPhase.ACTIVE)
        lce.transition("wf-2", WorkflowPhase.ACTIVE)
        lce.transition("wf-2", WorkflowPhase.COMPLETED)
        active = lce.get_active_workflows()
        assert len(active) == 1

    def test_lifecycle_stats(self, tmp_dir):
        lce = WorkflowLifecycleEngine(state_dir=tmp_dir)
        lce.register_workflow("wf-1")
        lce.transition("wf-1", WorkflowPhase.ACTIVE)
        stats = lce.get_stats()
        assert stats["total_sessions"] == 1
        assert stats["total_transitions"] == 1

    def test_valid_transitions_map_complete(self):
        for phase in WorkflowPhase:
            assert phase.value in VALID_TRANSITIONS

    def test_unknown_workflow_transition(self, tmp_dir):
        lce = WorkflowLifecycleEngine(state_dir=tmp_dir)
        assert not lce.transition("nonexistent", WorkflowPhase.ACTIVE)


# =====================================================================
# Test Integration — Full Workflow Through Spine
# =====================================================================


class TestIntegration:
    def test_all_six_workflows_through_spine(self, engine, registry):
        workflow_types = [
            "operational_briefing",
            "operational_resume",
            "runtime_inspection",
            "governed_planning",
            "browser_inspection",
            "workstation_inspection",
        ]
        for wf_type in workflow_types:
            wf = registry.create_workflow(wf_type, session_id="test")
            outcome = engine.execute_workflow(wf)
            assert outcome.succeeded, f"{wf_type} failed: {outcome.error_message}"

    def test_spine_traversals_tracked(self, engine, registry):
        wf = registry.create_workflow("runtime_inspection", session_id="test")
        outcome = engine.execute_workflow(wf)
        assert outcome.spine_traversals >= 3

    def test_governance_decisions_tracked(self, engine, registry):
        wf = registry.create_workflow("operational_briefing", session_id="test")
        outcome = engine.execute_workflow(wf)
        assert outcome.governance_decisions >= 2

    def test_result_data_aggregated(self, engine, registry):
        wf = registry.create_workflow("runtime_inspection", session_id="test")
        outcome = engine.execute_workflow(wf)
        assert len(outcome.result_data) > 0

    def test_replay_after_execution(self, engine, registry, tmp_dir):
        wf = registry.create_workflow("operational_briefing", session_id="test")
        outcome = engine.execute_workflow(wf)

        validator = WorkflowReplayValidator(proof_dir=tmp_dir)
        trace = {
            "workflow_id": wf.workflow_id,
            "workflow_type": wf.workflow_type.value,
            "operational_mode": wf.operational_mode.value,
            "name": wf.name,
        }
        replay = validator.replay_workflow_trace(trace)
        assert replay.all_passed


# =====================================================================
# Test No Direct Execution
# =====================================================================


class TestNoDirectExecution:
    def test_engine_requires_spine(self, spine):
        engine = CanonicalOperationalWorkflowEngine(spine=spine)
        registry = OperationalWorkflowRegistry()
        wf = registry.create_workflow("operational_briefing", session_id="test")
        outcome = engine.execute_workflow(wf)
        spine_stats = spine.get_stats()
        assert spine_stats["total_processed"] > 0

    def test_all_steps_go_through_spine(self, spine):
        engine = CanonicalOperationalWorkflowEngine(spine=spine)
        registry = OperationalWorkflowRegistry()

        before = spine.get_stats()["total_processed"]
        wf = registry.create_workflow("runtime_inspection", session_id="test")
        engine.execute_workflow(wf)
        after = spine.get_stats()["total_processed"]

        assert after > before

    def test_workflow_outcome_has_receipts(self, engine, registry):
        wf = registry.create_workflow("operational_briefing", session_id="test")
        outcome = engine.execute_workflow(wf)
        assert len(outcome.lineage_receipts) >= outcome.steps_total

    def test_mode_constrains_execution(self, spine):
        engine = CanonicalOperationalWorkflowEngine(spine=spine)
        wf = OperationalWorkflow(
            workflow_type=WorkflowType.CUSTOM,
            operational_mode=SupervisedOperationalMode.INSPECT_ONLY,
            steps=[
                WorkflowStep(
                    step_type=WorkflowStepType.CHECKPOINT,
                    command="checkpoint",
                ),
            ],
        )
        wf.boundary = WorkflowBoundary(
            operational_mode=SupervisedOperationalMode.INSPECT_ONLY,
        )
        outcome = engine.execute_workflow(wf)
        assert not outcome.succeeded
