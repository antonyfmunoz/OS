"""Tests for Phase 96.8BW — Governed Long-Horizon Operational Execution.

Tests:
  - contracts (12 contracts, 4 enums)
  - canonical coordinator
  - operational lifecycle engine
  - operational dependency engine
  - deferred execution engine
  - operational continuation engine
  - operational chronology engine
  - operational observability pipeline
  - operational replay validator
  - operational boundary policies
  - operational execution graph engine
  - operational continuation bridges
  - constraint enforcement (16 constraint classes)
"""

import sys
import tempfile

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.operations.long_horizon_operational_contracts_v1 import (
    ChronologyEventKind,
    DeferredExecutionState,
    DependencyType,
    ExecutionDependency,
    ExecutionStage,
    OperationalApprovalState,
    OperationalCampaign,
    OperationalCheckpoint,
    OperationalConstraint,
    OperationalContinuationState,
    OperationalEventType,
    OperationalExecutionReceipt,
    OperationalLifecycleState,
    OperationalObjective,
    OperationalProgressState,
    OperationalWaitingState,
    _content_hash,
)
from core.operations.canonical_long_horizon_execution_coordinator_v1 import (
    CanonicalLongHorizonExecutionCoordinator,
)
from core.operations.operational_lifecycle_engine_v1 import (
    OperationalLifecycleEngine,
    VALID_OPERATIONAL_TRANSITIONS,
    TERMINAL_STATES,
    FINAL_STATES,
)
from core.operations.operational_dependency_engine_v1 import (
    OperationalDependencyEngine,
)
from core.operations.deferred_execution_engine_v1 import DeferredExecutionEngine
from core.operations.operational_continuation_engine_v1 import (
    OperationalContinuationEngine,
)
from core.operations.operational_chronology_engine_v1 import (
    OperationalChronologyEngine,
)
from core.operations.operational_observability_pipeline_v1 import (
    OperationalObservabilityPipeline,
    EVENT_FILE_MAP,
)
from core.operations.operational_replay_validator_v1 import (
    OperationalReplayValidator,
    DETERMINISM_CHECKS,
)
from core.operations.operational_boundary_policies_v1 import (
    OperationalBoundaryEnforcer,
    FORBIDDEN_OPERATIONAL_ACTIONS,
)
from core.operations.operational_execution_graph_engine_v1 import (
    OperationalExecutionGraphEngine,
)
from core.operations.operational_continuation_bridges_v1 import (
    SessionOperationsBridge,
    WorkflowOperationsBridge,
    CognitionOperationsBridge,
    EmbodimentOperationsBridge,
    ObservabilityOperationsBridge,
    ReplayOperationsBridge,
    IngressOperationsBridge,
)


# =========================================================================
# Contract Tests
# =========================================================================


class TestOperationalContracts:

    def test_enum_lifecycle_state(self):
        assert len(OperationalLifecycleState) == 12

    def test_enum_event_type(self):
        assert len(OperationalEventType) == 12

    def test_enum_dependency_type(self):
        assert len(DependencyType) == 6

    def test_enum_chronology_event_kind(self):
        assert len(ChronologyEventKind) == 10

    def test_operational_objective(self):
        obj = OperationalObjective(operator_id="op-1", description="test")
        assert obj.objective_id.startswith("opobj-")
        assert obj.set_by == "operator"

    def test_execution_stage(self):
        s = ExecutionStage(name="s1", sequence=0)
        assert s.stage_id.startswith("opstg-")
        d = s.to_dict()
        assert d["name"] == "s1"

    def test_operational_campaign(self):
        c = OperationalCampaign(objective_id="obj-1", operator_id="op-1")
        assert c.campaign_id.startswith("opcmp-")

    def test_execution_dependency(self):
        d = ExecutionDependency(source_stage_id="s1", target_stage_id="s2")
        assert d.dependency_id.startswith("opdep-")

    def test_deferred_execution_state(self):
        d = DeferredExecutionState(campaign_id="c1", stage_id="s1")
        assert d.deferred_id.startswith("opdef-")

    def test_operational_checkpoint(self):
        c = OperationalCheckpoint(campaign_id="c1")
        assert c.checkpoint_id.startswith("opchkp-")
        assert c.content_hash

    def test_operational_constraint(self):
        c = OperationalConstraint(constraint_type="depth", limit=10, current=5)
        assert c.constraint_id.startswith("opcon-")

    def test_operational_approval(self):
        a = OperationalApprovalState(campaign_id="c1", stage_id="s1")
        assert a.approval_id.startswith("opapv-")

    def test_operational_receipt(self):
        r = OperationalExecutionReceipt(campaign_id="c1", operation="start")
        assert r.receipt_id.startswith("oprcpt-")
        assert r.content_hash

    def test_operational_progress(self):
        p = OperationalProgressState(campaign_id="c1", total_stages=5, completed_stages=2)
        assert p.progress_pct == 40.0

    def test_operational_waiting(self):
        w = OperationalWaitingState(campaign_id="c1", stage_id="s1")
        assert w.waiting_id.startswith("opwait-")

    def test_operational_continuation(self):
        c = OperationalContinuationState(campaign_id="c1", checkpoint_id="cp1")
        assert c.continuation_id.startswith("opcont-")
        assert c.content_hash

    def test_serialization_deterministic(self):
        o1 = OperationalObjective(objective_id="fixed", operator_id="op-1", description="t")
        o2 = OperationalObjective(objective_id="fixed", operator_id="op-1", description="t")
        d1 = {k: v for k, v in o1.to_dict().items() if k != "created_at"}
        d2 = {k: v for k, v in o2.to_dict().items() if k != "created_at"}
        assert d1 == d2


# =========================================================================
# Lifecycle Engine Tests
# =========================================================================


class TestOperationalLifecycleEngine:

    def test_register(self, tmp_path):
        le = OperationalLifecycleEngine(state_dir=tmp_path)
        assert le.register("e1") == "initialized"

    def test_valid_transitions(self, tmp_path):
        le = OperationalLifecycleEngine(state_dir=tmp_path)
        le.register("e1")
        assert le.transition("e1", OperationalLifecycleState.STAGED)
        assert le.transition("e1", OperationalLifecycleState.APPROVED)
        assert le.transition("e1", OperationalLifecycleState.EXECUTING)
        assert le.transition("e1", OperationalLifecycleState.COMPLETED)

    def test_invalid_transition(self, tmp_path):
        le = OperationalLifecycleEngine(state_dir=tmp_path)
        le.register("e1")
        assert not le.transition("e1", OperationalLifecycleState.COMPLETED)

    def test_terminal(self, tmp_path):
        le = OperationalLifecycleEngine(state_dir=tmp_path)
        le.register("e1")
        le.transition("e1", OperationalLifecycleState.TERMINATED)
        assert le.is_terminal("e1")

    def test_deferred_resume_path(self, tmp_path):
        le = OperationalLifecycleEngine(state_dir=tmp_path)
        le.register("e1")
        le.transition("e1", OperationalLifecycleState.STAGED)
        le.transition("e1", OperationalLifecycleState.EXECUTING)
        le.transition("e1", OperationalLifecycleState.DEFERRED)
        le.transition("e1", OperationalLifecycleState.RESUMED)
        le.transition("e1", OperationalLifecycleState.EXECUTING)
        assert le.get_state("e1") == "executing"

    def test_lineage_persisted(self, tmp_path):
        le = OperationalLifecycleEngine(state_dir=tmp_path)
        le.register("e1")
        le.transition("e1", OperationalLifecycleState.STAGED)
        path = tmp_path / "operational_lifecycle_lineage.jsonl"
        assert path.exists()

    def test_twelve_states_exist(self):
        assert len(VALID_OPERATIONAL_TRANSITIONS) == 12


# =========================================================================
# Dependency Engine Tests
# =========================================================================


class TestOperationalDependencyEngine:

    def test_add_dependency(self, tmp_path):
        de = OperationalDependencyEngine(state_dir=tmp_path)
        dep = de.add_dependency("s1", "s2")
        assert dep is not None
        assert dep.source_stage_id == "s1"

    def test_cycle_prevention(self, tmp_path):
        de = OperationalDependencyEngine(state_dir=tmp_path)
        de.add_dependency("s1", "s2")
        result = de.add_dependency("s2", "s1")
        assert result is None

    def test_self_dependency_prevented(self, tmp_path):
        de = OperationalDependencyEngine(state_dir=tmp_path)
        result = de.add_dependency("s1", "s1")
        assert result is None

    def test_dependency_satisfaction(self, tmp_path):
        de = OperationalDependencyEngine(state_dir=tmp_path)
        de.add_dependency("s1", "s2")
        assert not de.are_dependencies_met("s2")
        de.satisfy("s1")
        assert de.are_dependencies_met("s2")

    def test_execution_order(self, tmp_path):
        de = OperationalDependencyEngine(state_dir=tmp_path)
        de.add_dependency("s1", "s2")
        de.add_dependency("s2", "s3")
        order = de.get_execution_order(["s1", "s2", "s3"])
        assert order.index("s1") < order.index("s2")

    def test_persistence(self, tmp_path):
        de = OperationalDependencyEngine(state_dir=tmp_path)
        de.add_dependency("s1", "s2")
        path = tmp_path / "operational_dependencies.jsonl"
        assert path.exists()


# =========================================================================
# Deferred Execution Engine Tests
# =========================================================================


class TestDeferredExecutionEngine:

    def test_defer_stage(self, tmp_path):
        de = DeferredExecutionEngine(state_dir=tmp_path)
        state = de.defer_stage("c1", "s1", reason="waiting")
        assert state.deferred_id.startswith("opdef-")
        assert not state.resumed

    def test_resume_deferred(self, tmp_path):
        de = DeferredExecutionEngine(state_dir=tmp_path)
        state = de.defer_stage("c1", "s1")
        assert de.resume_deferred(state.deferred_id)
        assert not de.resume_deferred(state.deferred_id)  # already resumed

    def test_enter_waiting(self, tmp_path):
        de = DeferredExecutionEngine(state_dir=tmp_path)
        w = de.enter_waiting("c1", "s1", waiting_for="approval")
        assert w.waiting_id.startswith("opwait-")

    def test_active_deferred(self, tmp_path):
        de = DeferredExecutionEngine(state_dir=tmp_path)
        de.defer_stage("c1", "s1")
        de.defer_stage("c1", "s2")
        state = de.defer_stage("c1", "s3")
        de.resume_deferred(state.deferred_id)
        assert len(de.get_active_deferred()) == 2

    def test_persistence(self, tmp_path):
        de = DeferredExecutionEngine(state_dir=tmp_path)
        de.defer_stage("c1", "s1")
        path = tmp_path / "deferred_executions.jsonl"
        assert path.exists()


# =========================================================================
# Continuation Engine Tests
# =========================================================================


class TestOperationalContinuationEngine:

    def test_create_checkpoint(self, tmp_path):
        ce = OperationalContinuationEngine(state_dir=tmp_path)
        cp = ce.create_checkpoint("c1", 0, "staged")
        assert cp.checkpoint_id.startswith("opchkp-")
        assert cp.content_hash

    def test_restore_from_checkpoint(self, tmp_path):
        ce = OperationalContinuationEngine(state_dir=tmp_path)
        cp = ce.create_checkpoint("c1", 2, "executing", [{"s": "done"}])
        restored = ce.restore_from_checkpoint(cp.checkpoint_id)
        assert restored is not None
        assert restored.stage_index == 2

    def test_create_continuation(self, tmp_path):
        ce = OperationalContinuationEngine(state_dir=tmp_path)
        cp = ce.create_checkpoint("c1", 0, "staged")
        cont = ce.create_continuation("c1", cp.checkpoint_id, "sess-1")
        assert cont.continuation_id.startswith("opcont-")

    def test_verify_hash(self, tmp_path):
        ce = OperationalContinuationEngine(state_dir=tmp_path)
        cp = ce.create_checkpoint("c1", 0, "staged")
        assert ce.verify_checkpoint_hash(cp)

    def test_persistence(self, tmp_path):
        ce = OperationalContinuationEngine(state_dir=tmp_path)
        ce.create_checkpoint("c1", 0, "staged")
        ledger = tmp_path / "operational_checkpoints.jsonl"
        assert ledger.exists()


# =========================================================================
# Chronology Engine Tests
# =========================================================================


class TestOperationalChronologyEngine:

    def test_record_event(self, tmp_path):
        ce = OperationalChronologyEngine(state_dir=tmp_path)
        ev = ce.record_campaign_creation("c1", operator_id="op-1")
        assert ev["sequence_number"] == 0

    def test_all_event_kinds(self, tmp_path):
        ce = OperationalChronologyEngine(state_dir=tmp_path)
        ce.record_objective_creation("c1")
        ce.record_campaign_creation("c1")
        ce.record_stage_transition("c1")
        ce.record_deferred_execution("c1")
        ce.record_continuation_restoration("c1")
        ce.record_approval("c1")
        ce.record_governance_escalation("c1")
        ce.record_stage_completion("c1")
        ce.record_execution_suspension("c1")
        ce.record_execution_termination("c1")
        snap = ce.get_chronology_snapshot("c1")
        assert len(snap) == 10

    def test_sequence_monotonic(self, tmp_path):
        ce = OperationalChronologyEngine(state_dir=tmp_path)
        for i in range(5):
            ev = ce.record_stage_transition("c1")
            assert ev["sequence_number"] == i

    def test_persistence(self, tmp_path):
        ce = OperationalChronologyEngine(state_dir=tmp_path)
        ce.record_campaign_creation("c1")
        path = tmp_path / "operational_chronology.jsonl"
        assert path.exists()


# =========================================================================
# Observability Pipeline Tests
# =========================================================================


class TestOperationalObservabilityPipeline:

    def test_all_12_event_types(self, tmp_path):
        obs = OperationalObservabilityPipeline(obs_dir=tmp_path)
        for et in OperationalEventType:
            obs.record_event(et, "c1")
        assert obs.get_stats()["total_events"] == 12

    def test_event_file_map_complete(self):
        assert len(EVENT_FILE_MAP) == 12

    def test_convenience_methods(self, tmp_path):
        obs = OperationalObservabilityPipeline(obs_dir=tmp_path)
        obs.record_objective_created("c1")
        obs.record_campaign_started("c1")
        obs.record_stage_started("c1")
        obs.record_stage_completed("c1")
        obs.record_stage_failed("c1")
        obs.record_stage_deferred("c1")
        obs.record_continuation_restored("c1")
        obs.record_approval_requested("c1")
        obs.record_approval_received("c1")
        obs.record_execution_suspended("c1")
        obs.record_execution_resumed("c1")
        obs.record_execution_terminated("c1")
        assert obs.get_stats()["total_events"] == 12

    def test_read_back(self, tmp_path):
        obs = OperationalObservabilityPipeline(obs_dir=tmp_path)
        obs.record_objective_created("c1")
        events = obs.get_events_by_type(OperationalEventType.OBJECTIVE_CREATED)
        assert len(events) == 1


# =========================================================================
# Replay Validator Tests
# =========================================================================


class TestOperationalReplayValidator:

    def test_single_trace(self, tmp_path):
        rv = OperationalReplayValidator(proof_dir=tmp_path)
        trace = {
            "chronology": [{"seq": 0}],
            "dependencies": [{"s": "s1"}],
            "deferred": {"stage": "s1"},
            "continuation": {"cp": "cp1"},
            "stages": [{"s": "completed"}],
            "approvals": [{"a": "granted"}],
        }
        proof = rv.validate_trace(trace)
        assert proof["all_passed"]
        assert proof["check_count"] == 6

    def test_all_six_checks(self):
        assert len(DETERMINISM_CHECKS) == 6

    def test_proof_persisted(self, tmp_path):
        rv = OperationalReplayValidator(proof_dir=tmp_path)
        proof = rv.validate_trace({})
        path = tmp_path / f"op_replay_proof_{proof['proof_id']}.json"
        assert path.exists()

    def test_campaign_validation(self, tmp_path):
        rv = OperationalReplayValidator(proof_dir=tmp_path)
        result = rv.validate_campaign([{}, {"chronology": [1]}])
        assert result["all_passed"]
        assert result["trace_count"] == 2


# =========================================================================
# Boundary Policies Tests
# =========================================================================


class TestOperationalBoundaryPolicies:

    def test_default_limits(self):
        be = OperationalBoundaryEnforcer()
        assert be.limits["max_stages_per_campaign"] == 20
        assert be.limits["max_active_campaigns"] == 5

    def test_passing_check(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_stages(5)
        assert r["passed"]

    def test_failing_check(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_stages(25)
        assert not r["passed"]

    def test_override_capping(self):
        be = OperationalBoundaryEnforcer(overrides={"max_stages_per_campaign": 100})
        assert be.limits["max_stages_per_campaign"] == 20

    def test_forbidden_actions(self):
        be = OperationalBoundaryEnforcer()
        for action in FORBIDDEN_OPERATIONAL_ACTIONS:
            r = be.check_no_forbidden_action(action)
            assert not r["passed"]

    def test_safe_actions(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_no_forbidden_action("normal_operation")
        assert r["passed"]

    def test_operator_anchoring(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_objective_has_operator("operator")
        assert r["passed"]
        r = be.check_objective_has_operator("substrate")
        assert not r["passed"]

    def test_bulk_check(self):
        be = OperationalBoundaryEnforcer()
        result = be.check_all(stages=5, active_campaigns=1, execution_depth=2,
                              continuation_depth=1, deferred_count=0, fanout=1)
        assert result["all_passed"]


# =========================================================================
# Execution Graph Tests
# =========================================================================


class TestOperationalExecutionGraph:

    def test_create_graph(self, tmp_path):
        ge = OperationalExecutionGraphEngine(state_dir=tmp_path)
        g = ge.create_graph("c1", "obj-1")
        assert g["graph_id"].startswith("opgraph-")

    def test_add_nodes_and_edges(self, tmp_path):
        ge = OperationalExecutionGraphEngine(state_dir=tmp_path)
        ge.create_graph("c1")
        ge.add_node("c1", "stage", "s1", label="stage 1")
        ge.add_node("c1", "stage", "s2", label="stage 2")
        ge.add_edge("c1", "s1", "s2", edge_type="depends_on")
        g = ge.get_graph("c1")
        assert len(g["nodes"]) == 2
        assert len(g["edges"]) == 1

    def test_graph_hash(self, tmp_path):
        ge = OperationalExecutionGraphEngine(state_dir=tmp_path)
        ge.create_graph("c1")
        ge.add_node("c1", "stage", "s1")
        h = ge.get_graph_hash("c1")
        assert len(h) == 24

    def test_persist_graph(self, tmp_path):
        ge = OperationalExecutionGraphEngine(state_dir=tmp_path)
        ge.create_graph("c1")
        ge.add_node("c1", "stage", "s1")
        assert ge.persist_graph("c1")
        path = tmp_path / "execution_graph_c1.json"
        assert path.exists()


# =========================================================================
# Continuation Bridges Tests
# =========================================================================


class TestOperationalContinuationBridges:

    def test_session_bridge(self, tmp_path):
        b = SessionOperationsBridge(state_dir=tmp_path)
        r = b.capture("c1", session_id="sess-1")
        assert r["bridge_type"] == "session_operations"
        path = tmp_path / "session_operations_lineage.jsonl"
        assert path.exists()

    def test_workflow_bridge(self, tmp_path):
        b = WorkflowOperationsBridge(state_dir=tmp_path)
        r = b.capture("c1", workflow_id="wf-1")
        assert r["bridge_type"] == "workflow_operations"

    def test_cognition_bridge(self, tmp_path):
        b = CognitionOperationsBridge(state_dir=tmp_path)
        r = b.capture("c1", operator_mode="focused")
        assert r["data"]["operator_mode"] == "focused"

    def test_embodiment_bridge(self, tmp_path):
        b = EmbodimentOperationsBridge(state_dir=tmp_path)
        r = b.capture("c1", workstation_mode="developer")
        assert r["data"]["workstation_mode"] == "developer"

    def test_observability_bridge(self, tmp_path):
        b = ObservabilityOperationsBridge(state_dir=tmp_path)
        r = b.capture("c1", total_events=10)
        assert r["data"]["total_events"] == 10

    def test_replay_bridge(self, tmp_path):
        b = ReplayOperationsBridge(state_dir=tmp_path)
        r = b.capture("c1", total_validations=5, total_passes=5)
        assert r["data"]["total_passes"] == 5

    def test_ingress_bridge(self, tmp_path):
        b = IngressOperationsBridge(state_dir=tmp_path)
        r = b.capture("c1", active_sources=["discord"])
        assert r["data"]["active_sources"] == ["discord"]


# =========================================================================
# Canonical Coordinator Tests
# =========================================================================


class TestCanonicalCoordinator:

    def test_create_objective(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "test")
        assert obj.set_by == "operator"

    def test_create_campaign(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "test")
        cmp = coord.create_campaign(obj.objective_id, "op-1",
                                     stages=[{"name": "s1"}, {"name": "s2"}])
        assert cmp is not None
        assert len(cmp.stages) == 2

    def test_stage_execution(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "test")
        cmp = coord.create_campaign(obj.objective_id, "op-1",
                                     stages=[{"name": "s1"}])
        sid = cmp.stages[0].stage_id
        assert coord.start_stage(cmp.campaign_id, sid)
        assert coord.complete_stage(cmp.campaign_id, sid)

    def test_stage_failure(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "test")
        cmp = coord.create_campaign(obj.objective_id, "op-1",
                                     stages=[{"name": "s1"}])
        sid = cmp.stages[0].stage_id
        coord.start_stage(cmp.campaign_id, sid)
        assert coord.fail_stage(cmp.campaign_id, sid, "error")

    def test_deferred_stage(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "test")
        cmp = coord.create_campaign(obj.objective_id, "op-1",
                                     stages=[{"name": "s1"}])
        sid = cmp.stages[0].stage_id
        coord.start_stage(cmp.campaign_id, sid)
        d = coord.defer_stage(cmp.campaign_id, sid, "wait")
        assert d is not None

    def test_approval_gate(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "test")
        cmp = coord.create_campaign(obj.objective_id, "op-1",
                                     stages=[{"name": "s1", "requires_approval": True}])
        sid = cmp.stages[0].stage_id
        assert not coord.start_stage(cmp.campaign_id, sid)
        appr = coord.request_approval(cmp.campaign_id, sid, "op-1")
        coord.grant_approval(appr.approval_id)
        assert coord.start_stage(cmp.campaign_id, sid)

    def test_suspend_resume(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "test")
        cmp = coord.create_campaign(obj.objective_id, "op-1",
                                     stages=[{"name": "s1"}])
        coord.start_stage(cmp.campaign_id, cmp.stages[0].stage_id)
        # Transition to executing first
        coord._lifecycle.transition(cmp.campaign_id, OperationalLifecycleState.EXECUTING)
        assert coord.suspend_campaign(cmp.campaign_id)
        assert coord.resume_campaign(cmp.campaign_id)

    def test_terminate(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "test")
        cmp = coord.create_campaign(obj.objective_id, "op-1",
                                     stages=[{"name": "s1"}])
        assert coord.terminate_campaign(cmp.campaign_id)

    def test_checkpoint(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "test")
        cmp = coord.create_campaign(obj.objective_id, "op-1",
                                     stages=[{"name": "s1"}])
        cp = coord.checkpoint_campaign(cmp.campaign_id)
        assert cp is not None

    def test_progress(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "test")
        cmp = coord.create_campaign(obj.objective_id, "op-1",
                                     stages=[{"name": "s1"}, {"name": "s2"}])
        sid = cmp.stages[0].stage_id
        coord.start_stage(cmp.campaign_id, sid)
        coord.complete_stage(cmp.campaign_id, sid)
        p = coord.get_progress(cmp.campaign_id)
        assert p.completed_stages == 1
        assert p.progress_pct == 50.0

    def test_receipts_persisted(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "test")
        coord.create_campaign(obj.objective_id, "op-1", stages=[{"name": "s1"}])
        receipts = coord.get_recent_receipts()
        assert len(receipts) >= 1
        path = tmp_path / "operational_receipts.jsonl"
        assert path.exists()

    def test_nonexistent_campaign(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        assert coord.get_campaign("nope") is None
        assert not coord.terminate_campaign("nope")
        assert not coord.suspend_campaign("nope")

    def test_campaign_auto_complete(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "test")
        cmp = coord.create_campaign(obj.objective_id, "op-1",
                                     stages=[{"name": "s1"}])
        sid = cmp.stages[0].stage_id
        coord.start_stage(cmp.campaign_id, sid)
        coord.complete_stage(cmp.campaign_id, sid)
        assert cmp.state == "completed"


# =========================================================================
# Constraint Tests
# =========================================================================


class TestNoAutonomousObjectiveGeneration:

    def test_objective_requires_operator(self):
        obj = OperationalObjective(operator_id="op-1", description="test")
        assert obj.set_by == "operator"

    def test_boundary_rejects_non_operator(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_objective_has_operator("substrate")
        assert not r["passed"]

    def test_coordinator_hardcodes_operator(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "test")
        assert obj.set_by == "operator"


class TestNoRecursiveContinuation:

    def test_boundary_limits_continuation_depth(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_continuation_depth(10)
        assert not r["passed"]
        r = be.check_continuation_depth(1)
        assert r["passed"]


class TestNoUncontrolledDeferredExecution:

    def test_boundary_limits_deferred(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_deferred_count(15)
        assert not r["passed"]


class TestNoHiddenScheduling:

    def test_forbidden_hidden_deferred(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_no_forbidden_action("hidden_deferred_execution")
        assert not r["passed"]

    def test_forbidden_background_execution(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_no_forbidden_action("background_autonomous_execution")
        assert not r["passed"]


class TestNoExecutionOutsideSpine:

    def test_coordinator_no_execute(self):
        assert not hasattr(CanonicalLongHorizonExecutionCoordinator, "execute")
        assert not hasattr(CanonicalLongHorizonExecutionCoordinator, "execute_adapter")
        assert not hasattr(CanonicalLongHorizonExecutionCoordinator, "run_command")


class TestDeterministicDependencyReplay:

    def test_dependency_order_stable(self, tmp_path):
        de = OperationalDependencyEngine(state_dir=tmp_path)
        de.add_dependency("s1", "s2")
        de.add_dependency("s2", "s3")
        order1 = de.get_execution_order(["s1", "s2", "s3"])
        order2 = de.get_execution_order(["s1", "s2", "s3"])
        assert order1 == order2


class TestDeterministicChronologyReplay:

    def test_chronology_hash_stable(self, tmp_path):
        rv = OperationalReplayValidator(proof_dir=tmp_path)
        trace = {"chronology": [{"a": 1}, {"b": 2}]}
        p1 = rv.validate_trace(trace)
        p2 = rv.validate_trace(trace)
        assert p1["trace_hash"] == p2["trace_hash"]


class TestDeterministicContinuationReplay:

    def test_checkpoint_hash_stable(self, tmp_path):
        ce = OperationalContinuationEngine(state_dir=tmp_path)
        cp1 = ce.create_checkpoint("c1", 0, "staged", [{"s": "init"}])
        cp2 = ce.create_checkpoint("c1", 0, "staged", [{"s": "init"}])
        assert cp1.content_hash == cp2.content_hash


class TestBoundedExecutionFanout:

    def test_boundary_limits_fanout(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_fanout(5)
        assert not r["passed"]
        r = be.check_fanout(1)
        assert r["passed"]


class TestBoundedContinuationDepth:

    def test_boundary_limits_depth(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_execution_depth(15)
        assert not r["passed"]


class TestExplicitApprovalEnforcement:

    def test_unapproved_stage_cannot_start(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "test")
        cmp = coord.create_campaign(obj.objective_id, "op-1",
                                     stages=[{"name": "s1", "requires_approval": True}])
        sid = cmp.stages[0].stage_id
        assert not coord.start_stage(cmp.campaign_id, sid)


class TestNoOrphanExecutionGraphs:

    def test_campaign_always_has_graph(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "test")
        cmp = coord.create_campaign(obj.objective_id, "op-1",
                                     stages=[{"name": "s1"}])
        graph = coord.get_execution_graph(cmp.campaign_id)
        assert graph is not None
        assert len(graph["nodes"]) >= 3  # objective + campaign + stage


class TestNoWorkflowOwnedObjectives:

    def test_forbidden_self_generated(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_no_forbidden_action("self_generated_objective")
        assert not r["passed"]

    def test_forbidden_autonomous_creation(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_no_forbidden_action("autonomous_campaign_creation")
        assert not r["passed"]


class TestNoCognitionOwnedExecution:

    def test_coordinator_no_self_direct(self):
        assert not hasattr(CanonicalLongHorizonExecutionCoordinator, "self_direct")
        assert not hasattr(CanonicalLongHorizonExecutionCoordinator, "generate_objective")


class TestNoSessionOwnedIntentionality:

    def test_forbidden_self_directed(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_no_forbidden_action("self_directed_execution")
        assert not r["passed"]

    def test_forbidden_independent_spawning(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_no_forbidden_action("independent_task_spawning")
        assert not r["passed"]


class TestNoAutonomousOperationalEscalation:

    def test_forbidden_infinite_progression(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_no_forbidden_action("infinite_progression")
        assert not r["passed"]

    def test_forbidden_uncontrolled_fanout(self):
        be = OperationalBoundaryEnforcer()
        r = be.check_no_forbidden_action("uncontrolled_fanout")
        assert not r["passed"]


# =========================================================================
# Integration Tests
# =========================================================================


class TestIntegration:

    def test_full_campaign_lifecycle(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "full lifecycle test")
        cmp = coord.create_campaign(
            obj.objective_id, "op-1",
            stages=[
                {"name": "research", "description": "gather info"},
                {"name": "implement", "description": "build it"},
                {"name": "validate", "description": "test it", "requires_approval": True},
            ],
        )

        # Execute stage 1
        s1 = cmp.stages[0].stage_id
        assert coord.start_stage(cmp.campaign_id, s1)
        assert coord.complete_stage(cmp.campaign_id, s1)

        # Execute stage 2
        s2 = cmp.stages[1].stage_id
        coord.start_stage(cmp.campaign_id, s2)
        coord.complete_stage(cmp.campaign_id, s2)

        # Stage 3 needs approval
        s3 = cmp.stages[2].stage_id
        assert not coord.start_stage(cmp.campaign_id, s3)
        appr = coord.request_approval(cmp.campaign_id, s3)
        coord.grant_approval(appr.approval_id)
        assert coord.start_stage(cmp.campaign_id, s3)
        coord.complete_stage(cmp.campaign_id, s3)

        assert cmp.state == "completed"
        p = coord.get_progress(cmp.campaign_id)
        assert p.progress_pct == 100.0

    def test_deferred_resume_lifecycle(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "deferred test")
        cmp = coord.create_campaign(obj.objective_id, "op-1",
                                     stages=[{"name": "s1"}])
        sid = cmp.stages[0].stage_id
        coord.start_stage(cmp.campaign_id, sid)
        deferred = coord.defer_stage(cmp.campaign_id, sid, "waiting for data")
        assert deferred is not None

    def test_dependency_enforcement(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "dep test")
        cmp = coord.create_campaign(obj.objective_id, "op-1",
                                     stages=[
                                         {"name": "s1"},
                                         {"name": "s2", "depends_on": []},
                                     ])
        s1 = cmp.stages[0].stage_id
        s2 = cmp.stages[1].stage_id
        coord.start_stage(cmp.campaign_id, s1)
        coord.complete_stage(cmp.campaign_id, s1)
        assert coord.start_stage(cmp.campaign_id, s2)

    def test_replay_determinism_end_to_end(self, tmp_path):
        rv = OperationalReplayValidator(proof_dir=tmp_path)
        trace = {
            "chronology": [{"kind": "stage_transition", "from": "init", "to": "exec"}],
            "dependencies": [{"s1": "met"}],
            "deferred": {},
            "continuation": {"cp": "cp-1"},
            "stages": [{"state": "completed"}],
            "approvals": [{"approved": True}],
        }
        proof = rv.validate_trace(trace)
        assert proof["all_passed"]
        assert proof["check_count"] == 6

    def test_graph_persistence_integration(self, tmp_path):
        coord = CanonicalLongHorizonExecutionCoordinator(state_dir=tmp_path)
        obj = coord.create_objective("op-1", "graph test")
        cmp = coord.create_campaign(obj.objective_id, "op-1",
                                     stages=[{"name": "s1"}, {"name": "s2"}])
        coord.checkpoint_campaign(cmp.campaign_id)
        import os
        graph_file = tmp_path / f"execution_graph_{cmp.campaign_id}.json"
        assert graph_file.exists()

    def test_boundary_enforcement_integration(self, tmp_path):
        be = OperationalBoundaryEnforcer()
        result = be.check_all(
            stages=3, active_campaigns=1, execution_depth=2,
            continuation_depth=0, deferred_count=0, fanout=1,
        )
        assert result["all_passed"]

        for action in FORBIDDEN_OPERATIONAL_ACTIONS:
            r = be.check_no_forbidden_action(action)
            assert not r["passed"]

    def test_bridges_integration(self, tmp_path):
        bridges = [
            SessionOperationsBridge(state_dir=tmp_path),
            WorkflowOperationsBridge(state_dir=tmp_path),
            CognitionOperationsBridge(state_dir=tmp_path),
            EmbodimentOperationsBridge(state_dir=tmp_path),
            ObservabilityOperationsBridge(state_dir=tmp_path),
            ReplayOperationsBridge(state_dir=tmp_path),
            IngressOperationsBridge(state_dir=tmp_path),
        ]
        for b in bridges:
            b.capture("c1")
        lineage_files = [f for f in os.listdir(tmp_path) if f.endswith("_lineage.jsonl")]
        assert len(lineage_files) == 7
