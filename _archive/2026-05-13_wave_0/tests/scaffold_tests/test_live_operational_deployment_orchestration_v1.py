"""Tests for Phase 96.8CF — Live Operational Deployment Orchestration.

Verifies: contracts, enums, lifecycle, execution graph, routing,
checkpoints, recovery, synchronization, observability, replay,
boundary policies, continuity bridges, coordinator, constraints.
"""

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.orchestration.live_operational_deployment_contracts_v1 import (
    LiveDeploymentOperation,
    RuntimeDeploymentState,
    DeploymentExecutionGraph,
    OperationalDeploymentReceipt,
    DeploymentCheckpointState,
    DeploymentRoutingState,
    DeploymentReplayState,
    DeploymentGovernanceState,
    DeploymentObservabilityState,
    DeploymentRecoveryState,
    DeploymentBoundaryState,
    DeploymentContinuationState,
    DeploymentSynchronizationState,
    DeploymentTrustState,
    DeploymentOperatorIntentState,
    OrchestrationLifecyclePhase,
    OrchestrationEventType,
    OrchestrationTrustTier,
    RecoveryAction,
    SynchronizationTarget,
)
from core.orchestration.deployment_orchestration_lifecycle_engine_v1 import (
    DeploymentOrchestrationLifecycleEngine,
    VALID_TRANSITIONS,
    TERMINAL_STATES,
)
from core.orchestration.deployment_execution_graph_engine_v1 import (
    DeploymentExecutionGraphEngine,
    MAX_NODES,
    MAX_EDGES,
    MAX_FANOUT,
)
from core.orchestration.live_deployment_routing_engine_v1 import (
    LiveDeploymentRoutingEngine,
    KNOWN_ENVIRONMENTS,
    TRUST_HIERARCHY,
    MAX_ROUTING_DEPTH,
)
from core.orchestration.deployment_checkpoint_engine_v1 import (
    DeploymentCheckpointEngine,
    MAX_CHECKPOINTS,
    MAX_CHECKPOINTS_PER_OPERATION,
)
from core.orchestration.deployment_recovery_coordination_engine_v1 import (
    DeploymentRecoveryCoordinationEngine,
    MAX_PENDING_RECOMMENDATIONS,
    KNOWN_ACTIONS,
)
from core.orchestration.deployment_synchronization_engine_v1 import (
    DeploymentSynchronizationEngine,
    KNOWN_TARGETS,
    MAX_EPOCH_GAP,
)
from core.orchestration.deployment_orchestration_observability_pipeline_v1 import (
    DeploymentOrchestrationObservabilityPipeline,
    EVENT_FILE_MAP,
)
from core.orchestration.deployment_orchestration_replay_validator_v1 import (
    DeploymentOrchestrationReplayValidator,
    REPLAY_CHECKS,
)
from core.orchestration.deployment_orchestration_boundary_policies_v1 import (
    ORCHESTRATION_LIMITS,
    FORBIDDEN_ORCHESTRATION_ACTIONS,
    enforce_limit,
    is_forbidden,
    get_all_limits,
    get_all_forbidden,
    validate_boundaries,
)
from core.orchestration.deployment_orchestration_continuity_bridges_v1 import (
    ALL_BRIDGES,
    ContinuityOrchestrationBridge,
    ResilienceOrchestrationBridge,
    ScalingOrchestrationBridge,
    WorkflowsOrchestrationBridge,
    ApplicationsOrchestrationBridge,
    EnvironmentsOrchestrationBridge,
    CognitionOrchestrationBridge,
    ReplayOrchestrationBridge,
    ObservabilityOrchestrationBridge,
)
from core.orchestration.canonical_live_operational_deployment_coordinator_v1 import (
    CanonicalLiveOperationalDeploymentCoordinator,
)


# ── Contracts ──────────────────────────────────────────────


class TestContracts:
    def test_live_deployment_operation(self):
        op = LiveDeploymentOperation(
            application_id="eos", environment_id="vps",
        )
        d = op.to_dict()
        assert d["operation_id"].startswith("ldop-")
        assert d["application_id"] == "eos"

    def test_runtime_deployment_state(self):
        s = RuntimeDeploymentState(operation_id="op-1")
        d = s.to_dict()
        assert d["state_id"].startswith("rdst-")
        assert d["phase"] == "planned"

    def test_deployment_execution_graph(self):
        g = DeploymentExecutionGraph(nodes=["a", "b"])
        d = g.to_dict()
        assert d["graph_id"].startswith("dgraph-")
        assert len(d["nodes"]) == 2

    def test_operational_deployment_receipt(self):
        r = OperationalDeploymentReceipt(operation_id="op-1")
        d = r.to_dict()
        assert d["receipt_id"].startswith("drcpt-")

    def test_deployment_checkpoint_state(self):
        c = DeploymentCheckpointState(operation_id="op-1", content_hash="abc")
        d = c.to_dict()
        assert d["checkpoint_id"].startswith("dckpt-")

    def test_deployment_routing_state(self):
        r = DeploymentRoutingState(operation_id="op-1", source_environment="vps")
        d = r.to_dict()
        assert d["routing_id"].startswith("droute-")

    def test_deployment_replay_state(self):
        s = DeploymentReplayState(check_name="test")
        d = s.to_dict()
        assert d["replay_id"].startswith("dreplay-")

    def test_deployment_governance_state(self):
        g = DeploymentGovernanceState(operation_id="op-1")
        d = g.to_dict()
        assert d["governance_id"].startswith("dgov-")

    def test_deployment_observability_state(self):
        o = DeploymentObservabilityState(operation_id="op-1")
        d = o.to_dict()
        assert d["observability_id"].startswith("dobs-")

    def test_deployment_recovery_state(self):
        r = DeploymentRecoveryState(operation_id="op-1", action="recommend_rollback")
        d = r.to_dict()
        assert d["recovery_id"].startswith("drecov-")

    def test_deployment_boundary_state(self):
        b = DeploymentBoundaryState(limit_name="max_ops", current_value=5, max_value=50)
        d = b.to_dict()
        assert d["boundary_id"].startswith("dbnd-")

    def test_deployment_continuation_state(self):
        c = DeploymentContinuationState(operation_id="op-1")
        d = c.to_dict()
        assert d["continuation_id"].startswith("dcont-")

    def test_deployment_synchronization_state(self):
        s = DeploymentSynchronizationState(target="application_runtime")
        d = s.to_dict()
        assert d["sync_id"].startswith("dsync-")

    def test_deployment_trust_state(self):
        t = DeploymentTrustState(operation_id="op-1")
        d = t.to_dict()
        assert d["trust_id"].startswith("dtrust-")

    def test_deployment_operator_intent_state(self):
        i = DeploymentOperatorIntentState(intent="deploy", set_by="operator")
        d = i.to_dict()
        assert d["intent_id"].startswith("dintent-")
        assert d["set_by"] == "operator"

    def test_all_contracts_have_to_dict(self):
        classes = [
            LiveDeploymentOperation, RuntimeDeploymentState,
            DeploymentExecutionGraph, OperationalDeploymentReceipt,
            DeploymentCheckpointState, DeploymentRoutingState,
            DeploymentReplayState, DeploymentGovernanceState,
            DeploymentObservabilityState, DeploymentRecoveryState,
            DeploymentBoundaryState, DeploymentContinuationState,
            DeploymentSynchronizationState, DeploymentTrustState,
            DeploymentOperatorIntentState,
        ]
        assert len(classes) == 15
        for cls in classes:
            assert hasattr(cls, "to_dict")


# ── Enums ──────────────────────────────────────────────────


class TestEnums:
    def test_lifecycle_phases_count(self):
        assert len(OrchestrationLifecyclePhase) == 10

    def test_event_types_count(self):
        assert len(OrchestrationEventType) == 8

    def test_trust_tiers_count(self):
        assert len(OrchestrationTrustTier) == 4

    def test_recovery_actions_count(self):
        assert len(RecoveryAction) == 5

    def test_sync_targets_count(self):
        assert len(SynchronizationTarget) == 5

    def test_lifecycle_values(self):
        values = {p.value for p in OrchestrationLifecyclePhase}
        assert "planned" in values
        assert "archived" in values
        assert "coordinated" in values

    def test_event_type_values(self):
        values = {e.value for e in OrchestrationEventType}
        assert "deployment_operation_started" in values
        assert "deployment_replay_validated" in values


# ── Lifecycle Engine ───────────────────────────────────────


class TestLifecycleEngine:
    def test_initial_phase(self):
        le = DeploymentOrchestrationLifecycleEngine()
        assert le.current_phase == "planned"

    def test_valid_transition(self):
        le = DeploymentOrchestrationLifecycleEngine()
        result = le.transition("validated")
        assert result["from"] == "planned"
        assert result["to"] == "validated"

    def test_invalid_transition_raises(self):
        le = DeploymentOrchestrationLifecycleEngine()
        with pytest.raises(ValueError):
            le.transition("archived")

    def test_unknown_phase_raises(self):
        le = DeploymentOrchestrationLifecycleEngine()
        with pytest.raises(ValueError):
            le.transition("nonexistent")

    def test_full_lifecycle_coordinate(self):
        le = DeploymentOrchestrationLifecycleEngine()
        for phase in ["validated", "staged", "approved", "coordinated", "observed"]:
            le.transition(phase)
        assert le.current_phase == "observed"

    def test_checkpoint_path(self):
        le = DeploymentOrchestrationLifecycleEngine()
        for phase in ["validated", "staged", "approved", "coordinated",
                       "observed", "checkpointed"]:
            le.transition(phase)
        assert le.current_phase == "checkpointed"

    def test_restore_path(self):
        le = DeploymentOrchestrationLifecycleEngine()
        for phase in ["validated", "staged", "approved", "coordinated",
                       "observed", "checkpointed", "restored", "observed"]:
            le.transition(phase)
        assert le.current_phase == "observed"

    def test_rollback_path(self):
        le = DeploymentOrchestrationLifecycleEngine()
        for phase in ["validated", "staged", "approved", "coordinated",
                       "observed", "rolled_back"]:
            le.transition(phase)
        assert le.current_phase == "rolled_back"

    def test_terminal_state(self):
        le = DeploymentOrchestrationLifecycleEngine()
        for phase in ["validated", "staged", "approved", "coordinated",
                       "observed", "rolled_back", "archived"]:
            le.transition(phase)
        assert le.is_terminal()
        with pytest.raises(ValueError):
            le.transition("planned")

    def test_terminal_states_set(self):
        assert TERMINAL_STATES == {"archived"}

    def test_all_phases_covered(self):
        all_phases = {p.value for p in OrchestrationLifecyclePhase}
        transition_phases = set(VALID_TRANSITIONS.keys())
        assert all_phases == transition_phases

    def test_stats(self):
        le = DeploymentOrchestrationLifecycleEngine()
        le.transition("validated")
        stats = le.get_stats()
        assert stats["current_phase"] == "validated"
        assert stats["total_transitions"] == 1


# ── Execution Graph Engine ─────────────────────────────────


class TestExecutionGraphEngine:
    def test_add_node(self):
        ge = DeploymentExecutionGraphEngine(state_dir=tempfile.mkdtemp())
        assert ge.add_node("n1") is True

    def test_duplicate_node(self):
        ge = DeploymentExecutionGraphEngine(state_dir=tempfile.mkdtemp())
        ge.add_node("n1")
        assert ge.add_node("n1") is True

    def test_add_edge(self):
        ge = DeploymentExecutionGraphEngine(state_dir=tempfile.mkdtemp())
        ge.add_node("n1")
        ge.add_node("n2")
        assert ge.add_edge("n1", "n2") is True

    def test_self_edge_denied(self):
        ge = DeploymentExecutionGraphEngine(state_dir=tempfile.mkdtemp())
        ge.add_node("n1")
        assert ge.add_edge("n1", "n1") is False

    def test_cycle_prevention(self):
        ge = DeploymentExecutionGraphEngine(state_dir=tempfile.mkdtemp())
        ge.add_node("a")
        ge.add_node("b")
        ge.add_node("c")
        ge.add_edge("a", "b")
        ge.add_edge("b", "c")
        assert ge.add_edge("c", "a") is False

    def test_fanout_limit(self):
        ge = DeploymentExecutionGraphEngine(state_dir=tempfile.mkdtemp())
        ge.add_node("src")
        for i in range(MAX_FANOUT + 1):
            ge.add_node(f"tgt-{i}")
        for i in range(MAX_FANOUT):
            assert ge.add_edge("src", f"tgt-{i}") is True
        assert ge.add_edge("src", f"tgt-{MAX_FANOUT}") is False

    def test_unknown_node_edge_denied(self):
        ge = DeploymentExecutionGraphEngine(state_dir=tempfile.mkdtemp())
        ge.add_node("n1")
        assert ge.add_edge("n1", "unknown") is False

    def test_graph_hash_deterministic(self):
        ge1 = DeploymentExecutionGraphEngine(state_dir=tempfile.mkdtemp())
        ge2 = DeploymentExecutionGraphEngine(state_dir=tempfile.mkdtemp())
        for ge in [ge1, ge2]:
            ge.add_node("a")
            ge.add_node("b")
            ge.add_edge("a", "b")
        assert ge1.get_graph_hash() == ge2.get_graph_hash()

    def test_orphan_detection(self):
        ge = DeploymentExecutionGraphEngine(state_dir=tempfile.mkdtemp())
        ge.add_node("a")
        ge.add_node("b")
        ge.add_node("orphan")
        ge.add_edge("a", "b")
        orphans = ge.get_orphans()
        assert "orphan" in orphans
        assert "a" not in orphans

    def test_dependencies_and_dependents(self):
        ge = DeploymentExecutionGraphEngine(state_dir=tempfile.mkdtemp())
        ge.add_node("a")
        ge.add_node("b")
        ge.add_edge("a", "b")
        assert ge.get_dependents("a") == ["b"]
        assert ge.get_dependencies("b") == ["a"]

    def test_stats(self):
        ge = DeploymentExecutionGraphEngine(state_dir=tempfile.mkdtemp())
        ge.add_node("a")
        stats = ge.get_stats()
        assert stats["total_nodes"] == 1


# ── Routing Engine ─────────────────────────────────────────


class TestRoutingEngine:
    def test_route_operation(self):
        re = LiveDeploymentRoutingEngine()
        route = re.route("op-1", "vps", "vps")
        assert route is not None
        assert route.route_hash != ""

    def test_operator_only(self):
        re = LiveDeploymentRoutingEngine()
        with pytest.raises(ValueError):
            re.route("op-1", "vps", "vps", approved_by="bot")

    def test_unknown_environment_rejected(self):
        re = LiveDeploymentRoutingEngine()
        route = re.route("op-1", "vps", "nonexistent")
        assert route is None

    def test_routing_depth_limit(self):
        re = LiveDeploymentRoutingEngine()
        for i in range(MAX_ROUTING_DEPTH):
            result = re.route(f"op-{i}", "vps", "vps")
            assert result is not None
        result = re.route("op-extra", "vps", "vps")
        assert result is None

    def test_clear_chain(self):
        re = LiveDeploymentRoutingEngine()
        for i in range(MAX_ROUTING_DEPTH):
            re.route(f"op-{i}", "vps", "vps")
        re.clear_chain()
        result = re.route("op-new", "vps", "vps")
        assert result is not None

    def test_trust_validation_pass(self):
        re = LiveDeploymentRoutingEngine()
        assert re.validate_trust("development", "production") is True

    def test_trust_validation_fail(self):
        re = LiveDeploymentRoutingEngine()
        assert re.validate_trust("production", "development") is False

    def test_known_environments(self):
        assert len(KNOWN_ENVIRONMENTS) == 6
        assert "vps" in KNOWN_ENVIRONMENTS
        assert "cloud" in KNOWN_ENVIRONMENTS

    def test_trust_hierarchy(self):
        assert TRUST_HIERARCHY["production"] > TRUST_HIERARCHY["sandbox"]

    def test_stats(self):
        re = LiveDeploymentRoutingEngine()
        re.route("op-1", "vps", "vps")
        stats = re.get_stats()
        assert stats["total_routes"] == 1


# ── Checkpoint Engine ──────────────────────────────────────


class TestCheckpointEngine:
    def test_create_checkpoint(self):
        ce = DeploymentCheckpointEngine(state_dir=tempfile.mkdtemp())
        ckpt = ce.create_checkpoint("op-1", "state_data")
        assert ckpt is not None
        assert ckpt.content_hash != ""

    def test_restore_checkpoint(self):
        ce = DeploymentCheckpointEngine(state_dir=tempfile.mkdtemp())
        ckpt = ce.create_checkpoint("op-1", "state_data")
        restored = ce.restore_checkpoint(ckpt.checkpoint_id)
        assert restored is not None
        assert restored.content_hash == ckpt.content_hash

    def test_restore_nonexistent(self):
        ce = DeploymentCheckpointEngine(state_dir=tempfile.mkdtemp())
        assert ce.restore_checkpoint("nonexistent") is None

    def test_verify_determinism(self):
        ce = DeploymentCheckpointEngine(state_dir=tempfile.mkdtemp())
        ckpt = ce.create_checkpoint("op-1", "state_data")
        assert ce.verify_determinism(ckpt.checkpoint_id, "state_data") is True
        assert ce.verify_determinism(ckpt.checkpoint_id, "different") is False

    def test_per_operation_limit(self):
        ce = DeploymentCheckpointEngine(state_dir=tempfile.mkdtemp())
        for i in range(MAX_CHECKPOINTS_PER_OPERATION):
            assert ce.create_checkpoint("op-1", f"data-{i}") is not None
        assert ce.create_checkpoint("op-1", "extra") is None

    def test_latest_checkpoint(self):
        ce = DeploymentCheckpointEngine(state_dir=tempfile.mkdtemp())
        ce.create_checkpoint("op-1", "first")
        ce.create_checkpoint("op-1", "second")
        latest = ce.get_latest_checkpoint("op-1")
        assert latest is not None
        expected_hash = hashlib.sha256(b"second").hexdigest()[:16]
        assert latest.content_hash == expected_hash

    def test_stats(self):
        ce = DeploymentCheckpointEngine(state_dir=tempfile.mkdtemp())
        ce.create_checkpoint("op-1", "data")
        stats = ce.get_stats()
        assert stats["total_checkpoints"] == 1


# ── Recovery Engine ────────────────────────────────────────


class TestRecoveryEngine:
    def test_recommend(self):
        re = DeploymentRecoveryCoordinationEngine()
        rec = re.recommend("op-1", "recommend_rollback", "test reason")
        assert rec is not None
        assert rec.action == "recommend_rollback"

    def test_unknown_action_rejected(self):
        re = DeploymentRecoveryCoordinationEngine()
        assert re.recommend("op-1", "auto_heal") is None

    def test_approve_requires_operator(self):
        re = DeploymentRecoveryCoordinationEngine()
        rec = re.recommend("op-1", "recommend_rollback")
        with pytest.raises(ValueError):
            re.approve(rec.recovery_id, approved_by="bot")

    def test_approve_moves_to_history(self):
        re = DeploymentRecoveryCoordinationEngine()
        rec = re.recommend("op-1", "recommend_rollback")
        approved = re.approve(rec.recovery_id)
        assert approved is not None
        assert len(re.get_pending()) == 0
        assert len(re.get_history()) == 1

    def test_deny_requires_operator(self):
        re = DeploymentRecoveryCoordinationEngine()
        rec = re.recommend("op-1", "recommend_rollback")
        with pytest.raises(ValueError):
            re.deny(rec.recovery_id, denied_by="bot")

    def test_deny_moves_to_history(self):
        re = DeploymentRecoveryCoordinationEngine()
        rec = re.recommend("op-1", "recommend_rollback")
        denied = re.deny(rec.recovery_id)
        assert denied is not None
        assert len(re.get_pending()) == 0

    def test_known_actions(self):
        assert len(KNOWN_ACTIONS) == 5

    def test_stats(self):
        re = DeploymentRecoveryCoordinationEngine()
        re.recommend("op-1", "recommend_rollback")
        stats = re.get_stats()
        assert stats["pending_count"] == 1


# ── Synchronization Engine ─────────────────────────────────


class TestSynchronizationEngine:
    def test_synchronize(self):
        se = DeploymentSynchronizationEngine()
        state = se.synchronize("application_runtime")
        assert state is not None
        assert state.synchronized is True

    def test_unknown_target_rejected(self):
        se = DeploymentSynchronizationEngine()
        assert se.synchronize("nonexistent") is None

    def test_epoch_increments(self):
        se = DeploymentSynchronizationEngine()
        se.synchronize("application_runtime")
        se.synchronize("environment_runtime")
        assert se.current_epoch == 2

    def test_epoch_gap(self):
        se = DeploymentSynchronizationEngine()
        se.synchronize("application_runtime")
        se.synchronize("environment_runtime")
        gap = se.check_epoch_gap("application_runtime", "environment_runtime")
        assert gap == 1

    def test_is_synchronized(self):
        se = DeploymentSynchronizationEngine()
        assert se.is_synchronized("application_runtime") is False
        se.synchronize("application_runtime")
        assert se.is_synchronized("application_runtime") is True

    def test_known_targets(self):
        assert len(KNOWN_TARGETS) == 5

    def test_stats(self):
        se = DeploymentSynchronizationEngine()
        se.synchronize("application_runtime")
        stats = se.get_stats()
        assert stats["total_syncs"] == 1
        assert stats["synchronized_count"] == 1


# ── Observability Pipeline ─────────────────────────────────


class TestObservabilityPipeline:
    def test_event_file_map_count(self):
        assert len(EVENT_FILE_MAP) == 8

    def test_event_file_map_matches_enum(self):
        enum_values = {e.value for e in OrchestrationEventType}
        map_keys = set(EVENT_FILE_MAP.keys())
        assert enum_values == map_keys

    def test_emit_operation_started(self):
        obs = DeploymentOrchestrationObservabilityPipeline(
            state_dir=tempfile.mkdtemp(),
        )
        event = obs.emit_operation_started(operation_id="op-1")
        assert event["event_type"] == "deployment_operation_started"

    def test_emit_operation_completed(self):
        obs = DeploymentOrchestrationObservabilityPipeline(
            state_dir=tempfile.mkdtemp(),
        )
        event = obs.emit_operation_completed(operation_id="op-1")
        assert event["event_type"] == "deployment_operation_completed"

    def test_emit_checkpoint_created(self):
        obs = DeploymentOrchestrationObservabilityPipeline(
            state_dir=tempfile.mkdtemp(),
        )
        event = obs.emit_checkpoint_created(operation_id="op-1", checkpoint_id="ckpt-1")
        assert event["event_type"] == "deployment_checkpoint_created"

    def test_emit_restore_events(self):
        obs = DeploymentOrchestrationObservabilityPipeline(
            state_dir=tempfile.mkdtemp(),
        )
        e1 = obs.emit_restore_started(operation_id="op-1")
        e2 = obs.emit_restore_completed(operation_id="op-1")
        assert e1["event_type"] == "deployment_restore_started"
        assert e2["event_type"] == "deployment_restore_completed"

    def test_emit_recovery_recommended(self):
        obs = DeploymentOrchestrationObservabilityPipeline(
            state_dir=tempfile.mkdtemp(),
        )
        event = obs.emit_recovery_recommended(
            operation_id="op-1", action="recommend_rollback",
        )
        assert event["event_type"] == "deployment_recovery_recommended"

    def test_emit_boundary_denied(self):
        obs = DeploymentOrchestrationObservabilityPipeline(
            state_dir=tempfile.mkdtemp(),
        )
        event = obs.emit_boundary_denied(operation_id="op-1", reason="test")
        assert event["event_type"] == "deployment_boundary_denied"

    def test_emit_replay_validated(self):
        obs = DeploymentOrchestrationObservabilityPipeline(
            state_dir=tempfile.mkdtemp(),
        )
        event = obs.emit_replay_validated(operation_id="op-1")
        assert event["event_type"] == "deployment_replay_validated"

    def test_events_written_to_file(self):
        d = tempfile.mkdtemp()
        obs = DeploymentOrchestrationObservabilityPipeline(state_dir=d)
        obs.emit_operation_started(operation_id="op-1")
        path = Path(d) / "deployment_operation_started.jsonl"
        assert path.exists()
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 1

    def test_stats(self):
        obs = DeploymentOrchestrationObservabilityPipeline(
            state_dir=tempfile.mkdtemp(),
        )
        obs.emit_operation_started(operation_id="op-1")
        stats = obs.get_stats()
        assert stats["total_events"] == 1


# ── Replay Validator ───────────────────────────────────────


class TestReplayValidator:
    def test_replay_checks_count(self):
        assert len(REPLAY_CHECKS) == 6

    def test_validate_determinism(self):
        rv = DeploymentOrchestrationReplayValidator()
        result = rv.validate_determinism("orchestration_graph", "in", "out")
        assert result["deterministic"] is True

    def test_unknown_check_rejected(self):
        rv = DeploymentOrchestrationReplayValidator()
        with pytest.raises(ValueError):
            rv.validate_determinism("nonexistent", "in", "out")

    def test_replay_pair_same(self):
        rv = DeploymentOrchestrationReplayValidator()
        result = rv.validate_replay_pair(
            "deployment_routing", "in", "same", "same",
        )
        assert result["deterministic"] is True

    def test_replay_pair_different(self):
        rv = DeploymentOrchestrationReplayValidator()
        result = rv.validate_replay_pair(
            "deployment_routing", "in", "out_a", "out_b",
        )
        assert result["deterministic"] is False

    def test_all_checks_valid(self):
        rv = DeploymentOrchestrationReplayValidator()
        for check in REPLAY_CHECKS:
            result = rv.validate_determinism(check, "input", "output")
            assert result["deterministic"] is True

    def test_stats(self):
        rv = DeploymentOrchestrationReplayValidator()
        rv.validate_determinism("orchestration_graph", "in", "out")
        stats = rv.get_stats()
        assert stats["total_checks"] == 1
        assert stats["deterministic_count"] == 1


# ── Boundary Policies ─────────────────────────────────────


class TestBoundaryPolicies:
    def test_limits_count(self):
        assert len(ORCHESTRATION_LIMITS) == 8

    def test_forbidden_count(self):
        assert len(FORBIDDEN_ORCHESTRATION_ACTIONS) == 10

    def test_enforce_limit_default(self):
        assert enforce_limit("max_operations") == 50

    def test_enforce_limit_override_lower(self):
        assert enforce_limit("max_operations", 10) == 10

    def test_enforce_limit_override_higher_capped(self):
        assert enforce_limit("max_operations", 100) == 50

    def test_enforce_limit_unknown_raises(self):
        with pytest.raises(ValueError):
            enforce_limit("nonexistent")

    def test_autonomous_deployment_forbidden(self):
        assert is_forbidden("autonomous_deployment") is True

    def test_autonomous_scaling_forbidden(self):
        assert is_forbidden("autonomous_scaling") is True

    def test_autonomous_rollback_forbidden(self):
        assert is_forbidden("autonomous_rollback") is True

    def test_autonomous_recovery_forbidden(self):
        assert is_forbidden("autonomous_recovery") is True

    def test_recursive_orchestration_forbidden(self):
        assert is_forbidden("recursive_orchestration") is True

    def test_hidden_topology_mutation_forbidden(self):
        assert is_forbidden("hidden_topology_mutation") is True

    def test_hidden_deployment_mutation_forbidden(self):
        assert is_forbidden("hidden_deployment_mutation") is True

    def test_hidden_rollout_expansion_forbidden(self):
        assert is_forbidden("hidden_rollout_expansion") is True

    def test_execution_outside_spine_forbidden(self):
        assert is_forbidden("execution_outside_spine") is True

    def test_governance_bypass_forbidden(self):
        assert is_forbidden("governance_bypass") is True

    def test_safe_action_not_forbidden(self):
        assert is_forbidden("deploy_with_approval") is False

    def test_override_capping(self):
        for name, default in ORCHESTRATION_LIMITS.items():
            assert enforce_limit(name, default + 10) == default
            assert enforce_limit(name, default - 1) == default - 1

    def test_validate_boundaries(self):
        result = validate_boundaries()
        assert result["limits_count"] == 8
        assert result["forbidden_count"] == 10


# ── Continuity Bridges ─────────────────────────────────────


class TestContinuityBridges:
    def test_all_bridges_count(self):
        assert len(ALL_BRIDGES) == 9

    def test_continuity_bridge(self):
        b = ContinuityOrchestrationBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "continuity_orchestration"

    def test_resilience_bridge(self):
        b = ResilienceOrchestrationBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "resilience_orchestration"

    def test_scaling_bridge(self):
        b = ScalingOrchestrationBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "scaling_orchestration"

    def test_workflows_bridge(self):
        b = WorkflowsOrchestrationBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "workflows_orchestration"

    def test_applications_bridge(self):
        b = ApplicationsOrchestrationBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "applications_orchestration"

    def test_environments_bridge(self):
        b = EnvironmentsOrchestrationBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "environments_orchestration"

    def test_cognition_bridge(self):
        b = CognitionOrchestrationBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "cognition_orchestration"

    def test_replay_bridge(self):
        b = ReplayOrchestrationBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "replay_orchestration"

    def test_observability_bridge(self):
        b = ObservabilityOrchestrationBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "observability_orchestration"

    def test_bridge_events_tracked(self):
        b = ContinuityOrchestrationBridge(state_dir=tempfile.mkdtemp())
        b.record("e1", {})
        b.record("e2", {})
        assert len(b.get_events()) == 2
        stats = b.get_stats()
        assert stats["total_events"] == 2

    def test_bridge_writes_to_file(self):
        d = tempfile.mkdtemp()
        b = ContinuityOrchestrationBridge(state_dir=d)
        b.record("test", {"key": "value"})
        path = Path(d) / "continuity_orchestration.jsonl"
        assert path.exists()


# ── Coordinator ────────────────────────────────────────────


class TestCoordinator:
    def _make(self):
        return CanonicalLiveOperationalDeploymentCoordinator(
            state_dir=tempfile.mkdtemp(),
        )

    def test_create_operation(self):
        c = self._make()
        op = c.create_operation("eos", "vps")
        assert op["operation_id"].startswith("ldop-")
        assert op["approved_by"] == "operator"

    def test_create_operation_requires_operator(self):
        c = self._make()
        with pytest.raises(ValueError):
            c.create_operation("eos", "vps", approved_by="bot")

    def test_complete_operation(self):
        c = self._make()
        op = c.create_operation("eos", "vps")
        receipt = c.complete_operation(op["operation_id"])
        assert receipt is not None
        assert receipt["outcome"] == "completed"

    def test_complete_operation_requires_operator(self):
        c = self._make()
        op = c.create_operation("eos", "vps")
        with pytest.raises(ValueError):
            c.complete_operation(op["operation_id"], approved_by="bot")

    def test_route_operation(self):
        c = self._make()
        op = c.create_operation("eos", "vps")
        route = c.route_operation(op["operation_id"], "vps", "vps")
        assert route is not None

    def test_create_checkpoint(self):
        c = self._make()
        op = c.create_operation("eos", "vps")
        ckpt = c.create_checkpoint(op["operation_id"], "state_data")
        assert ckpt is not None

    def test_restore_checkpoint(self):
        c = self._make()
        op = c.create_operation("eos", "vps")
        ckpt = c.create_checkpoint(op["operation_id"], "state_data")
        restored = c.restore_checkpoint(ckpt["checkpoint_id"])
        assert restored is not None

    def test_recommend_recovery(self):
        c = self._make()
        op = c.create_operation("eos", "vps")
        rec = c.recommend_recovery(op["operation_id"], "recommend_rollback")
        assert rec is not None

    def test_approve_recovery(self):
        c = self._make()
        op = c.create_operation("eos", "vps")
        rec = c.recommend_recovery(op["operation_id"], "recommend_rollback")
        approved = c.approve_recovery(rec["recovery_id"])
        assert approved is not None

    def test_synchronize(self):
        c = self._make()
        sync = c.synchronize("application_runtime")
        assert sync is not None

    def test_set_intent(self):
        c = self._make()
        intent = c.set_intent("deploy eos", "op-1")
        assert intent["set_by"] == "operator"

    def test_set_intent_requires_operator(self):
        c = self._make()
        with pytest.raises(ValueError):
            c.set_intent("deploy", set_by="bot")

    def test_add_dependency(self):
        c = self._make()
        op1 = c.create_operation("eos", "vps")
        op2 = c.create_operation("lyfeos", "vps")
        result = c.add_dependency(op1["operation_id"], op2["operation_id"])
        assert result is True

    def test_get_all_operations(self):
        c = self._make()
        c.create_operation("eos", "vps")
        c.create_operation("lyfeos", "vps")
        ops = c.get_all_operations()
        assert len(ops) == 2

    def test_get_health(self):
        c = self._make()
        health = c.get_health()
        assert "lifecycle_phase" in health
        assert "graph" in health

    def test_get_stats_nine_keys(self):
        c = self._make()
        stats = c.get_stats()
        expected = {"lifecycle", "graph", "routing", "checkpoints",
                    "recovery", "sync", "observability", "operations", "intents"}
        assert set(stats.keys()) == expected

    def test_no_forbidden_methods(self):
        c = self._make()
        forbidden = [
            "execute", "dispatch", "deploy_autonomously",
            "scale_autonomously", "self_heal", "self_expand",
            "self_author", "bypass_spine", "auto_rollback",
            "auto_redeploy",
        ]
        for name in forbidden:
            assert not hasattr(c, name), f"Has forbidden method: {name}"


# ── Constraint Verification ────────────────────────────────


class TestConstraintVerification:
    def _make(self):
        return CanonicalLiveOperationalDeploymentCoordinator(
            state_dir=tempfile.mkdtemp(),
        )

    def test_no_autonomous_deployment(self):
        assert is_forbidden("autonomous_deployment")
        c = self._make()
        with pytest.raises(ValueError):
            c.create_operation("eos", "vps", approved_by="autonomous")

    def test_no_autonomous_scaling(self):
        assert is_forbidden("autonomous_scaling")

    def test_no_autonomous_rollback(self):
        assert is_forbidden("autonomous_rollback")

    def test_no_autonomous_recovery(self):
        assert is_forbidden("autonomous_recovery")
        re = DeploymentRecoveryCoordinationEngine()
        rec = re.recommend("op-1", "recommend_rollback")
        with pytest.raises(ValueError):
            re.approve(rec.recovery_id, approved_by="system")

    def test_no_recursive_orchestration(self):
        assert is_forbidden("recursive_orchestration")
        ge = DeploymentExecutionGraphEngine(state_dir=tempfile.mkdtemp())
        ge.add_node("a")
        ge.add_node("b")
        ge.add_node("c")
        ge.add_edge("a", "b")
        ge.add_edge("b", "c")
        assert ge.add_edge("c", "a") is False

    def test_deterministic_deployment_replay(self):
        rv = DeploymentOrchestrationReplayValidator()
        result = rv.validate_replay_pair(
            "orchestration_graph", "input", "same", "same",
        )
        assert result["deterministic"] is True

    def test_deterministic_checkpoint_restore(self):
        ce = DeploymentCheckpointEngine(state_dir=tempfile.mkdtemp())
        ckpt = ce.create_checkpoint("op-1", "state_data")
        assert ce.verify_determinism(ckpt.checkpoint_id, "state_data") is True
        assert ce.verify_determinism(ckpt.checkpoint_id, "different") is False

    def test_deployment_graph_integrity(self):
        ge = DeploymentExecutionGraphEngine(state_dir=tempfile.mkdtemp())
        ge.add_node("a")
        ge.add_node("b")
        ge.add_edge("a", "b")
        assert ge.add_edge("a", "a") is False
        h1 = ge.get_graph_hash()
        ge2 = DeploymentExecutionGraphEngine(state_dir=tempfile.mkdtemp())
        ge2.add_node("a")
        ge2.add_node("b")
        ge2.add_edge("a", "b")
        assert ge2.get_graph_hash() == h1

    def test_topology_validation_correctness(self):
        re = LiveDeploymentRoutingEngine()
        assert re.validate_trust("development", "production") is True
        assert re.validate_trust("production", "development") is False
        assert re.validate_trust("staging", "staging") is True

    def test_governance_preserved(self):
        c = self._make()
        with pytest.raises(ValueError):
            c.create_operation("eos", "vps", approved_by="system")
        with pytest.raises(ValueError):
            c.set_intent("deploy", set_by="system")

    def test_replay_lineage_preserved(self):
        rv = DeploymentOrchestrationReplayValidator()
        for check in REPLAY_CHECKS:
            result = rv.validate_determinism(check, "input", "output")
            assert result["deterministic"] is True
        assert rv.get_stats()["total_checks"] == 6

    def test_continuity_restoration_deterministic(self):
        ce = DeploymentCheckpointEngine(state_dir=tempfile.mkdtemp())
        ckpt = ce.create_checkpoint("op-1", "deterministic_state")
        restored = ce.restore_checkpoint(ckpt.checkpoint_id)
        h = hashlib.sha256(b"deterministic_state").hexdigest()[:16]
        assert restored.content_hash == h

    def test_override_capping_all_limits(self):
        for name, default in ORCHESTRATION_LIMITS.items():
            assert enforce_limit(name, default + 100) == default
            assert enforce_limit(name, max(1, default - 1)) == max(1, default - 1)

    def test_coordinator_cannot_execute(self):
        c = self._make()
        for attr in ["execute", "execute_deployment", "run_deployment"]:
            assert not hasattr(c, attr)

    def test_coordinator_cannot_orchestrate_autonomously(self):
        c = self._make()
        for attr in ["self_orchestrate", "auto_orchestrate", "autonomous_deploy"]:
            assert not hasattr(c, attr)

    def test_no_deployment_owned_cognition(self):
        c = self._make()
        for attr in ["think", "reason", "plan_autonomously", "decide"]:
            assert not hasattr(c, attr)

    def test_no_hidden_topology_mutation(self):
        assert is_forbidden("hidden_topology_mutation")

    def test_no_execution_outside_spine(self):
        assert is_forbidden("execution_outside_spine")

    def test_no_governance_bypass(self):
        assert is_forbidden("governance_bypass")
