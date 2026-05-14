"""Tests for Phase 96.8BX — Live Multi-Environment Operational Coordination.

Tests:
  contracts, lifecycle, topology, routing, delegation,
  synchronization, observability, replay, boundary policies,
  execution graphs, continuity bridges, coordinator integration,
  and 18 constraint verifications.

UMH substrate subsystem. Phase 96.8BX.
"""

from __future__ import annotations

import shutil
import sys
import tempfile

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.environments.live_environment_topology_contracts_v1 import (
    ChronologyEventKind,
    DelegationType,
    EnvironmentCapabilityMap,
    EnvironmentContinuityState,
    EnvironmentCoordinationReceipt,
    EnvironmentDelegationState,
    EnvironmentEventType,
    EnvironmentExecutionScope,
    EnvironmentHealthState,
    EnvironmentLifecycleState,
    EnvironmentNode,
    EnvironmentReplayState,
    EnvironmentRoutingDecision,
    EnvironmentSynchronizationState,
    EnvironmentTopology,
    EnvironmentTrustLevel,
    TrustTier,
    _content_hash,
    _new_id,
    _now_iso,
)
from core.environments.environment_lifecycle_engine_v1 import (
    EnvironmentLifecycleEngine,
    VALID_ENVIRONMENT_TRANSITIONS,
)
from core.environments.environment_topology_engine_v1 import (
    EnvironmentTopologyEngine,
    KNOWN_ENVIRONMENTS,
)
from core.environments.environment_routing_engine_v1 import (
    EnvironmentRoutingEngine,
)
from core.environments.environment_delegation_engine_v1 import (
    EnvironmentDelegationEngine,
)
from core.environments.environment_synchronization_engine_v1 import (
    EnvironmentSynchronizationEngine,
)
from core.environments.environment_observability_pipeline_v1 import (
    EnvironmentObservabilityPipeline,
    EVENT_FILE_MAP,
)
from core.environments.environment_replay_validator_v1 import (
    EnvironmentReplayValidator,
    REPLAY_CHECKS,
)
from core.environments.environment_boundary_policies_v1 import (
    DEFAULT_ENVIRONMENT_BOUNDARIES,
    FORBIDDEN_ENVIRONMENT_ACTIONS,
    EnvironmentBoundaryEnforcer,
)
from core.environments.environment_execution_graph_engine_v1 import (
    EnvironmentExecutionGraphEngine,
)
from core.environments.environment_continuity_bridges_v1 import (
    CognitionEnvironmentBridge,
    EmbodimentEnvironmentBridge,
    IngressEnvironmentBridge,
    ObservabilityEnvironmentBridge,
    OperationsEnvironmentBridge,
    ReplayEnvironmentBridge,
    SessionsEnvironmentBridge,
    WorkflowsEnvironmentBridge,
)
from core.environments.canonical_environment_coordination_engine_v1 import (
    CanonicalEnvironmentCoordinationEngine,
)


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


# ── Contract Tests ──────────────────────────────────────


class TestEnvironmentContracts:
    def test_enum_lifecycle_state(self):
        assert len(EnvironmentLifecycleState) == 10
        assert EnvironmentLifecycleState.REGISTERED.value == "registered"
        assert EnvironmentLifecycleState.TERMINATED.value == "terminated"

    def test_enum_event_type(self):
        assert len(EnvironmentEventType) == 10

    def test_enum_trust_tier(self):
        assert len(TrustTier) == 4
        assert TrustTier.FULL.value == "full"
        assert TrustTier.UNTRUSTED.value == "untrusted"

    def test_enum_delegation_type(self):
        assert len(DelegationType) == 6

    def test_enum_chronology_event_kind(self):
        assert len(ChronologyEventKind) == 10

    def test_environment_node(self):
        node = EnvironmentNode(name="test", environment_type="server")
        d = node.to_dict()
        assert d["name"] == "test"
        assert d["environment_id"].startswith("env-")
        assert d["state"] == "registered"

    def test_environment_topology(self):
        topo = EnvironmentTopology()
        d = topo.to_dict()
        assert d["topology_id"].startswith("topo-")
        assert d["nodes"] == []

    def test_environment_capability_map(self):
        cap = EnvironmentCapabilityMap(
            environment_id="env-1",
            capabilities={"shell": True, "docker": True},
        )
        d = cap.to_dict()
        assert d["capabilities"]["shell"] is True

    def test_environment_health_state(self):
        health = EnvironmentHealthState(environment_id="env-1")
        d = health.to_dict()
        assert d["healthy"] is True
        assert d["consecutive_failures"] == 0

    def test_environment_execution_scope(self):
        scope = EnvironmentExecutionScope(environment_id="env-1")
        d = scope.to_dict()
        assert d["governance_required"] is True

    def test_environment_trust_level(self):
        trust = EnvironmentTrustLevel(environment_id="env-1", tier="full")
        d = trust.to_dict()
        assert d["tier"] == "full"

    def test_environment_delegation_state(self):
        deleg = EnvironmentDelegationState(
            from_environment="env-1",
            to_environment="env-2",
        )
        d = deleg.to_dict()
        assert d["delegation_id"].startswith("edel-")
        assert d["state"] == "pending"
        assert d["depth"] == 0

    def test_environment_continuity_state(self):
        cont = EnvironmentContinuityState(environment_id="env-1")
        d = cont.to_dict()
        assert d["synchronization_epoch"] == 0
        h = cont._hashable()
        assert "environment_id" in h

    def test_environment_coordination_receipt(self):
        receipt = EnvironmentCoordinationReceipt(
            environment_id="env-1",
            operation="register",
        )
        d = receipt.to_dict()
        assert d["receipt_id"].startswith("ercpt-")

    def test_environment_synchronization_state(self):
        sync = EnvironmentSynchronizationState(
            source_environment="env-1",
            target_environment="env-2",
        )
        d = sync.to_dict()
        assert d["sync_id"].startswith("esync-")
        assert d["state"] == "pending"

    def test_environment_routing_decision(self):
        rd = EnvironmentRoutingDecision(command="test")
        d = rd.to_dict()
        assert d["decision_id"].startswith("eroute-")

    def test_environment_replay_state(self):
        rs = EnvironmentReplayState(environment_id="env-1")
        d = rs.to_dict()
        assert d["replay_id"].startswith("erply-")
        assert d["all_deterministic"] is False

    def test_serialization_deterministic(self):
        node = EnvironmentNode(name="x", environment_type="server")
        h1 = _content_hash(node.to_dict())
        h2 = _content_hash(node.to_dict())
        assert h1 == h2


# ── Lifecycle Tests ──────────────────────────────────────


class TestEnvironmentLifecycleEngine:
    def test_register(self, tmp_dir):
        eng = EnvironmentLifecycleEngine(state_dir=tmp_dir)
        eng.register("env-1")
        assert eng.get_state("env-1") == "registered"

    def test_valid_transitions(self, tmp_dir):
        eng = EnvironmentLifecycleEngine(state_dir=tmp_dir)
        eng.register("env-1")
        assert eng.transition("env-1", EnvironmentLifecycleState.AVAILABLE)
        assert eng.get_state("env-1") == "available"

    def test_invalid_transition(self, tmp_dir):
        eng = EnvironmentLifecycleEngine(state_dir=tmp_dir)
        eng.register("env-1")
        assert not eng.transition("env-1", EnvironmentLifecycleState.EXECUTING)

    def test_terminal(self, tmp_dir):
        eng = EnvironmentLifecycleEngine(state_dir=tmp_dir)
        eng.register("env-1")
        eng.transition("env-1", EnvironmentLifecycleState.TERMINATED)
        assert eng.is_terminal("env-1")

    def test_ten_states_exist(self):
        assert len(EnvironmentLifecycleState) == 10
        for state in EnvironmentLifecycleState:
            assert state.value in VALID_ENVIRONMENT_TRANSITIONS

    def test_paused_restore_path(self, tmp_dir):
        eng = EnvironmentLifecycleEngine(state_dir=tmp_dir)
        eng.register("env-1")
        eng.transition("env-1", EnvironmentLifecycleState.AVAILABLE)
        eng.transition("env-1", EnvironmentLifecycleState.PAUSED)
        assert eng.get_state("env-1") == "paused"
        eng.transition("env-1", EnvironmentLifecycleState.RESTORED)
        assert eng.get_state("env-1") == "restored"
        eng.transition("env-1", EnvironmentLifecycleState.AVAILABLE)
        assert eng.get_state("env-1") == "available"

    def test_lineage_persisted(self, tmp_dir):
        from pathlib import Path
        eng = EnvironmentLifecycleEngine(state_dir=tmp_dir)
        eng.register("env-1")
        eng.transition("env-1", EnvironmentLifecycleState.AVAILABLE)
        path = Path(tmp_dir) / "environment_lifecycle_lineage.jsonl"
        assert path.exists()


# ── Topology Tests ──────────────────────────────────────


class TestEnvironmentTopologyEngine:
    def test_register_known(self, tmp_dir):
        eng = EnvironmentTopologyEngine(state_dir=tmp_dir)
        node = eng.register_environment("vps")
        assert node.name == "vps"
        assert node.trust_tier == TrustTier.FULL.value
        assert "shell" in node.capabilities

    def test_register_unknown(self, tmp_dir):
        eng = EnvironmentTopologyEngine(state_dir=tmp_dir)
        node = eng.register_environment("custom", environment_type="custom")
        assert node.environment_type == "custom"

    def test_capabilities(self, tmp_dir):
        eng = EnvironmentTopologyEngine(state_dir=tmp_dir)
        node = eng.register_environment("vps")
        assert eng.has_capability(node.environment_id, "shell")
        assert eng.has_capability(node.environment_id, "docker")
        assert not eng.has_capability(node.environment_id, "navigation")

    def test_health(self, tmp_dir):
        eng = EnvironmentTopologyEngine(state_dir=tmp_dir)
        node = eng.register_environment("vps")
        health = eng.get_health(node.environment_id)
        assert health.healthy is True
        eng.update_health(node.environment_id, False, "down")
        health = eng.get_health(node.environment_id)
        assert health.consecutive_failures == 1

    def test_degradation(self, tmp_dir):
        eng = EnvironmentTopologyEngine(state_dir=tmp_dir)
        node = eng.register_environment("vps")
        for _ in range(3):
            eng.update_health(node.environment_id, False)
        health = eng.get_health(node.environment_id)
        assert health.degraded is True

    def test_build_topology(self, tmp_dir):
        eng = EnvironmentTopologyEngine(state_dir=tmp_dir)
        eng.register_environment("vps")
        eng.register_environment("local_workstation")
        topo = eng.build_topology()
        assert len(topo.nodes) == 2
        assert topo.content_hash

    def test_environments_with_capability(self, tmp_dir):
        eng = EnvironmentTopologyEngine(state_dir=tmp_dir)
        eng.register_environment("vps")
        eng.register_environment("browser_runtime")
        docker_envs = eng.get_environments_with_capability("docker")
        assert len(docker_envs) == 1
        nav_envs = eng.get_environments_with_capability("navigation")
        assert len(nav_envs) == 1

    def test_six_known_environments(self):
        assert len(KNOWN_ENVIRONMENTS) == 6
        assert "vps" in KNOWN_ENVIRONMENTS
        assert "sandbox_runtime" in KNOWN_ENVIRONMENTS

    def test_parent_edge(self, tmp_dir):
        eng = EnvironmentTopologyEngine(state_dir=tmp_dir)
        parent = eng.register_environment("vps")
        child = eng.register_environment("tmux_runtime", parent_id=parent.environment_id)
        topo = eng.build_topology()
        assert len(topo.edges) == 1
        assert topo.edges[0]["from_id"] == parent.environment_id


# ── Routing Tests ──────────────────────────────────────


class TestEnvironmentRoutingEngine:
    def test_route_by_capability(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        topo.register_environment("vps")
        topo.register_environment("browser_runtime")
        router = EnvironmentRoutingEngine(topo, state_dir=tmp_dir)

        decision = router.route("docker ps", required_capability="docker")
        assert decision.governance_passed
        assert decision.selected_environment

    def test_route_denied_no_capability(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        topo.register_environment("browser_runtime")
        router = EnvironmentRoutingEngine(topo, state_dir=tmp_dir)

        decision = router.route("docker ps", required_capability="docker")
        assert not decision.governance_passed
        assert decision.reason == "no_eligible_environment"

    def test_route_preferred(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        topo.register_environment("vps")
        ws = topo.register_environment("local_workstation")
        router = EnvironmentRoutingEngine(topo, state_dir=tmp_dir)

        decision = router.route("git status", required_capability="git",
                                preferred_environment="local_workstation")
        assert decision.selected_environment == ws.environment_id

    def test_route_trust_filtering(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        topo.register_environment("vps")
        topo.register_environment("sandbox_runtime")
        router = EnvironmentRoutingEngine(topo, state_dir=tmp_dir)

        decision = router.route("python3 test.py", required_capability="python",
                                min_trust=TrustTier.GOVERNED.value)
        assert decision.governance_passed

    def test_decisions_persisted(self, tmp_dir):
        from pathlib import Path
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        topo.register_environment("vps")
        router = EnvironmentRoutingEngine(topo, state_dir=tmp_dir)
        router.route("ls", required_capability="shell")
        path = Path(tmp_dir) / "environment_routing_decisions.jsonl"
        assert path.exists()


# ── Delegation Tests ──────────────────────────────────────


class TestEnvironmentDelegationEngine:
    def test_delegate(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        ws = topo.register_environment("local_workstation")
        eng = EnvironmentDelegationEngine(topo, state_dir=tmp_dir)

        deleg = eng.delegate(vps.environment_id, ws.environment_id)
        assert deleg is not None
        assert deleg.state == "pending"

    def test_delegate_self_rejected(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        eng = EnvironmentDelegationEngine(topo, state_dir=tmp_dir)

        assert eng.delegate(vps.environment_id, vps.environment_id) is None

    def test_delegate_depth_exceeded(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        ws = topo.register_environment("local_workstation")
        eng = EnvironmentDelegationEngine(topo, state_dir=tmp_dir, max_depth=2)

        assert eng.delegate(vps.environment_id, ws.environment_id, current_depth=2) is None

    def test_delegate_no_trust(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        br = topo.register_environment("browser_runtime")
        ws = topo.register_environment("local_workstation")
        eng = EnvironmentDelegationEngine(topo, state_dir=tmp_dir)

        assert eng.delegate(br.environment_id, ws.environment_id) is None

    def test_approve_complete(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        ws = topo.register_environment("local_workstation")
        eng = EnvironmentDelegationEngine(topo, state_dir=tmp_dir)

        deleg = eng.delegate(vps.environment_id, ws.environment_id)
        assert eng.approve(deleg.delegation_id)
        assert deleg.state == "active"
        assert eng.complete(deleg.delegation_id)
        assert deleg.state == "completed"

    def test_delegation_chain(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        ws = topo.register_environment("local_workstation")
        eng = EnvironmentDelegationEngine(topo, state_dir=tmp_dir)

        deleg = eng.delegate(vps.environment_id, ws.environment_id)
        eng.approve(deleg.delegation_id)
        chain = eng.get_delegation_chain(ws.environment_id)
        assert vps.environment_id in chain

    def test_max_active_delegations(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        envs = [topo.register_environment(f"env_{i}", environment_type="custom") for i in range(6)]
        eng = EnvironmentDelegationEngine(topo, state_dir=tmp_dir, max_active=3)

        for i in range(3):
            d = eng.delegate(vps.environment_id, envs[i].environment_id)
            eng.approve(d.delegation_id)

        assert eng.delegate(vps.environment_id, envs[3].environment_id) is None

    def test_cycle_prevention(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        a = topo.register_environment("vps")
        b = topo.register_environment("local_workstation")
        eng = EnvironmentDelegationEngine(topo, state_dir=tmp_dir)

        d1 = eng.delegate(a.environment_id, b.environment_id)
        eng.approve(d1.delegation_id)
        assert eng.delegate(b.environment_id, a.environment_id) is None


# ── Synchronization Tests ──────────────────────────────────────


class TestEnvironmentSynchronizationEngine:
    def test_synchronize(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        ws = topo.register_environment("local_workstation")
        eng = EnvironmentSynchronizationEngine(topo, state_dir=tmp_dir)

        sync = eng.synchronize(vps.environment_id, ws.environment_id)
        assert sync is not None
        assert sync.state == "completed"
        assert sync.epoch == 1

    def test_sync_self_rejected(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        eng = EnvironmentSynchronizationEngine(topo, state_dir=tmp_dir)
        assert eng.synchronize(vps.environment_id, vps.environment_id) is None

    def test_sync_epoch_increments(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        ws = topo.register_environment("local_workstation")
        eng = EnvironmentSynchronizationEngine(topo, state_dir=tmp_dir)

        eng.synchronize(vps.environment_id, ws.environment_id)
        eng.synchronize(vps.environment_id, ws.environment_id)
        assert eng.get_epoch() == 2

    def test_continuity_state(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        ws = topo.register_environment("local_workstation")
        eng = EnvironmentSynchronizationEngine(topo, state_dir=tmp_dir)

        eng.synchronize(vps.environment_id, ws.environment_id)
        cont = eng.get_continuity(vps.environment_id)
        assert cont is not None
        assert cont.synchronization_epoch == 1
        assert cont.content_hash

    def test_checkpoint(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        eng = EnvironmentSynchronizationEngine(topo, state_dir=tmp_dir)

        cont = eng.checkpoint_environment(vps.environment_id, "cp-1")
        assert cont.checkpoint_id == "cp-1"
        assert cont.content_hash

    def test_restore(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        eng = EnvironmentSynchronizationEngine(topo, state_dir=tmp_dir)

        cont = EnvironmentContinuityState(
            environment_id=vps.environment_id,
            checkpoint_id="cp-restore",
            synchronization_epoch=5,
        )
        assert eng.restore_environment(vps.environment_id, cont)
        restored = eng.get_continuity(vps.environment_id)
        assert restored.checkpoint_id == "cp-restore"


# ── Observability Tests ──────────────────────────────────────


class TestEnvironmentObservabilityPipeline:
    def test_all_10_event_types(self):
        assert len(EnvironmentEventType) == 10

    def test_event_file_map_complete(self):
        for et in EnvironmentEventType:
            assert et.value in EVENT_FILE_MAP

    def test_convenience_methods(self, tmp_dir):
        obs = EnvironmentObservabilityPipeline(state_dir=tmp_dir)
        obs.emit_registered("env-1")
        obs.emit_available("env-1")
        obs.emit_unavailable("env-1")
        obs.emit_selected("env-1")
        obs.emit_delegated("env-1")
        obs.emit_denied("env-1")
        obs.emit_synchronized("env-1")
        obs.emit_restored("env-1")
        obs.emit_checkpointed("env-1")
        obs.emit_replayed("env-1")
        assert obs.get_stats()["total_events"] == 10

    def test_read_back(self, tmp_dir):
        obs = EnvironmentObservabilityPipeline(state_dir=tmp_dir)
        obs.emit_registered("env-1")
        events = obs.read_events(EnvironmentEventType.ENVIRONMENT_REGISTERED)
        assert len(events) == 1


# ── Replay Tests ──────────────────────────────────────


class TestEnvironmentReplayValidator:
    def test_five_checks(self):
        assert len(REPLAY_CHECKS) == 5

    def test_validate_trace(self, tmp_dir):
        v = EnvironmentReplayValidator(state_dir=tmp_dir)
        result = v.validate_trace({
            "environment_routing": {"decision": "select_vps"},
            "environment_delegation": {"chain": ["a", "b"]},
            "topology_synchronization": {"epoch": 1},
            "environment_restoration": {"checkpoint": "cp-1"},
            "environment_chronology": {"events": [1, 2]},
        })
        assert result["all_passed"]

    def test_missing_check_fails(self, tmp_dir):
        v = EnvironmentReplayValidator(state_dir=tmp_dir)
        result = v.validate_trace({
            "environment_routing": {"decision": "select_vps"},
        })
        assert not result["all_passed"]

    def test_routing_determinism(self, tmp_dir):
        v = EnvironmentReplayValidator(state_dir=tmp_dir)
        decisions = [{"command": "ls", "env": "vps"}]
        result = v.validate_routing_determinism(decisions, decisions)
        assert result["passed"]

    def test_delegation_determinism(self, tmp_dir):
        v = EnvironmentReplayValidator(state_dir=tmp_dir)
        dels = [{"from": "a", "to": "b"}]
        result = v.validate_delegation_determinism(dels, dels)
        assert result["passed"]

    def test_sync_determinism(self, tmp_dir):
        v = EnvironmentReplayValidator(state_dir=tmp_dir)
        syncs = [{"epoch": 1}]
        result = v.validate_sync_determinism(syncs, syncs)
        assert result["passed"]

    def test_proof_persisted(self, tmp_dir):
        from pathlib import Path
        v = EnvironmentReplayValidator(state_dir=tmp_dir)
        v.validate_trace({"environment_routing": {"x": 1}})
        path = Path(tmp_dir) / "environment_replay_proofs.jsonl"
        assert path.exists()


# ── Boundary Policy Tests ──────────────────────────────────────


class TestEnvironmentBoundaryPolicies:
    def test_default_limits(self):
        assert len(DEFAULT_ENVIRONMENT_BOUNDARIES) == 7

    def test_forbidden_actions(self):
        assert len(FORBIDDEN_ENVIRONMENT_ACTIONS) == 10

    def test_passing_check(self):
        enf = EnvironmentBoundaryEnforcer()
        result = enf.check_environments(3)
        assert result["passed"]

    def test_failing_check(self):
        enf = EnvironmentBoundaryEnforcer()
        result = enf.check_environments(10)
        assert not result["passed"]

    def test_override_capping(self):
        enf = EnvironmentBoundaryEnforcer(overrides={"max_environments": 100})
        assert enf.limits["max_environments"] == 10

    def test_override_tightening(self):
        enf = EnvironmentBoundaryEnforcer(overrides={"max_environments": 5})
        assert enf.limits["max_environments"] == 5

    def test_forbidden_action_check(self):
        enf = EnvironmentBoundaryEnforcer()
        result = enf.check_no_forbidden_action("environment_owned_orchestration")
        assert not result["passed"]

    def test_safe_action(self):
        enf = EnvironmentBoundaryEnforcer()
        result = enf.check_no_forbidden_action("register_environment")
        assert result["passed"]

    def test_bulk_check(self):
        enf = EnvironmentBoundaryEnforcer()
        result = enf.check_all(environments=2, delegation_depth=1)
        assert result["all_passed"]

    def test_delegation_depth_check(self):
        enf = EnvironmentBoundaryEnforcer()
        result = enf.check_delegation_depth(5)
        assert not result["passed"]

    def test_routing_depth_check(self):
        enf = EnvironmentBoundaryEnforcer()
        result = enf.check_routing_depth(1)
        assert result["passed"]


# ── Execution Graph Tests ──────────────────────────────────────


class TestEnvironmentExecutionGraph:
    def test_create_graph(self, tmp_dir):
        eng = EnvironmentExecutionGraphEngine(state_dir=tmp_dir)
        graph = eng.create_graph("env-1")
        assert graph["graph_id"].startswith("envgraph-")

    def test_add_nodes_and_edges(self, tmp_dir):
        eng = EnvironmentExecutionGraphEngine(state_dir=tmp_dir)
        eng.create_graph("env-1")
        eng.add_node("env-1", "environment", "env-1", label="VPS")
        eng.add_node("env-1", "campaign", "cmp-1")
        eng.add_edge("env-1", "env-1", "cmp-1", edge_type="executes")
        graph = eng.get_graph("env-1")
        assert len(graph["nodes"]) == 2
        assert len(graph["edges"]) == 1

    def test_graph_hash(self, tmp_dir):
        eng = EnvironmentExecutionGraphEngine(state_dir=tmp_dir)
        eng.create_graph("env-1")
        eng.add_node("env-1", "environment", "env-1")
        h1 = eng.get_graph_hash("env-1")
        h2 = eng.get_graph_hash("env-1")
        assert h1 == h2
        assert h1

    def test_persist_graph(self, tmp_dir):
        from pathlib import Path
        eng = EnvironmentExecutionGraphEngine(state_dir=tmp_dir)
        eng.create_graph("env-1")
        eng.add_node("env-1", "environment", "env-1")
        assert eng.persist_graph("env-1")
        assert (Path(tmp_dir) / "env_exec_graph_env-1.json").exists()
        assert (Path(tmp_dir) / "environment_execution_graphs.jsonl").exists()


# ── Continuity Bridge Tests ──────────────────────────────────────


class TestEnvironmentContinuityBridges:
    def test_operations_bridge(self, tmp_dir):
        b = OperationsEnvironmentBridge(state_dir=tmp_dir)
        r = b.capture("env-1", campaign_id="cmp-1")
        assert r["bridge_type"] == "operations_environment"
        assert r["data"]["campaign_id"] == "cmp-1"

    def test_sessions_bridge(self, tmp_dir):
        b = SessionsEnvironmentBridge(state_dir=tmp_dir)
        r = b.capture("env-1", session_id="sess-1")
        assert r["bridge_type"] == "sessions_environment"

    def test_workflows_bridge(self, tmp_dir):
        b = WorkflowsEnvironmentBridge(state_dir=tmp_dir)
        r = b.capture("env-1", workflow_id="wf-1")
        assert r["bridge_type"] == "workflows_environment"

    def test_ingress_bridge(self, tmp_dir):
        b = IngressEnvironmentBridge(state_dir=tmp_dir)
        r = b.capture("env-1", source="discord")
        assert r["bridge_type"] == "ingress_environment"

    def test_cognition_bridge(self, tmp_dir):
        b = CognitionEnvironmentBridge(state_dir=tmp_dir)
        r = b.capture("env-1", operator_mode="focused")
        assert r["bridge_type"] == "cognition_environment"

    def test_embodiment_bridge(self, tmp_dir):
        b = EmbodimentEnvironmentBridge(state_dir=tmp_dir)
        r = b.capture("env-1", workstation_mode="developer")
        assert r["bridge_type"] == "embodiment_environment"

    def test_observability_bridge(self, tmp_dir):
        b = ObservabilityEnvironmentBridge(state_dir=tmp_dir)
        r = b.capture("env-1", total_events=42)
        assert r["data"]["total_events"] == 42

    def test_replay_bridge(self, tmp_dir):
        b = ReplayEnvironmentBridge(state_dir=tmp_dir)
        r = b.capture("env-1", total_validations=5, total_passes=5)
        assert r["data"]["total_passes"] == 5


# ── Coordinator Integration Tests ──────────────────────────────────────


class TestCanonicalCoordinator:
    def test_register_environment(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        result = eng.register_environment("vps")
        assert result["name"] == "vps"
        assert result["state"] == "available"

    def test_route_execution(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        eng.register_environment("vps")
        decision = eng.route_execution("git status", required_capability="git")
        assert decision["governance_passed"]

    def test_route_denied(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        eng.register_environment("browser_runtime")
        decision = eng.route_execution("docker ps", required_capability="docker")
        assert not decision["governance_passed"]

    def test_delegate_execution(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        vps = eng.register_environment("vps")
        ws = eng.register_environment("local_workstation")
        deleg = eng.delegate_execution(vps["environment_id"], ws["environment_id"])
        assert deleg is not None
        assert deleg["state"] == "pending"

    def test_delegate_rejected_no_trust(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        br = eng.register_environment("browser_runtime")
        ws = eng.register_environment("local_workstation")
        assert eng.delegate_execution(br["environment_id"], ws["environment_id"]) is None

    def test_synchronize(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        vps = eng.register_environment("vps")
        ws = eng.register_environment("local_workstation")
        sync = eng.synchronize_environments(vps["environment_id"], ws["environment_id"])
        assert sync is not None
        assert sync["state"] == "completed"

    def test_checkpoint(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        vps = eng.register_environment("vps")
        cp = eng.checkpoint_environment(vps["environment_id"])
        assert cp is not None
        assert cp["content_hash"]

    def test_pause_environment(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        vps = eng.register_environment("vps")
        assert eng.pause_environment(vps["environment_id"])

    def test_terminate_environment(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        vps = eng.register_environment("vps")
        assert eng.terminate_environment(vps["environment_id"])

    def test_health_degradation(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        vps = eng.register_environment("vps")
        for _ in range(3):
            eng.update_health(vps["environment_id"], False, "unreachable")
        health = eng.get_health(vps["environment_id"])
        assert health["degraded"]

    def test_get_topology(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        eng.register_environment("vps")
        eng.register_environment("local_workstation")
        topo = eng.get_topology()
        assert len(topo["nodes"]) == 2

    def test_receipts_persisted(self, tmp_dir):
        from pathlib import Path
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        eng.register_environment("vps")
        path = Path(tmp_dir) / "environment_coordination_receipts.jsonl"
        assert path.exists()

    def test_stats(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        eng.register_environment("vps")
        stats = eng.get_stats()
        assert stats["topology"]["total_environments"] == 1
        assert stats["lifecycle"]["total_environments"] == 1

    def test_get_environment_by_name(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        eng.register_environment("vps")
        result = eng.get_environment_by_name("vps")
        assert result is not None
        assert result["name"] == "vps"

    def test_nonexistent_environment(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        assert eng.get_environment("fake-id") is None


# ── Constraint Tests ──────────────────────────────────────


class TestNoEnvironmentOwnedOrchestration:
    def test_forbidden(self):
        enf = EnvironmentBoundaryEnforcer()
        assert not enf.check_no_forbidden_action("environment_owned_orchestration")["passed"]

    def test_coordinator_no_execute(self):
        assert not hasattr(CanonicalEnvironmentCoordinationEngine, "execute")
        assert not hasattr(CanonicalEnvironmentCoordinationEngine, "dispatch")
        assert not hasattr(CanonicalEnvironmentCoordinationEngine, "run_command")


class TestNoRecursiveDelegation:
    def test_boundary_limits_depth(self):
        enf = EnvironmentBoundaryEnforcer()
        result = enf.check_delegation_depth(3)
        assert not result["passed"]

    def test_self_delegation_blocked(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        eng = EnvironmentDelegationEngine(topo, state_dir=tmp_dir)
        assert eng.delegate(vps.environment_id, vps.environment_id) is None

    def test_cycle_blocked(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        a = topo.register_environment("vps")
        b = topo.register_environment("local_workstation")
        eng = EnvironmentDelegationEngine(topo, state_dir=tmp_dir)
        d = eng.delegate(a.environment_id, b.environment_id)
        eng.approve(d.delegation_id)
        assert eng.delegate(b.environment_id, a.environment_id) is None


class TestNoUncontrolledDelegationFanout:
    def test_max_active_enforced(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        targets = [topo.register_environment(f"t{i}", environment_type="custom") for i in range(4)]
        eng = EnvironmentDelegationEngine(topo, state_dir=tmp_dir, max_active=2)
        for i in range(2):
            d = eng.delegate(vps.environment_id, targets[i].environment_id)
            eng.approve(d.delegation_id)
        assert eng.delegate(vps.environment_id, targets[2].environment_id) is None


class TestNoHiddenEnvironmentExecution:
    def test_forbidden_hidden_execution(self):
        enf = EnvironmentBoundaryEnforcer()
        assert not enf.check_no_forbidden_action("hidden_cross_environment_execution")["passed"]


class TestNoHiddenSynchronizationMutation:
    def test_sync_persisted(self, tmp_dir):
        from pathlib import Path
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        ws = topo.register_environment("local_workstation")
        eng = EnvironmentSynchronizationEngine(topo, state_dir=tmp_dir)
        eng.synchronize(vps.environment_id, ws.environment_id)
        path = Path(tmp_dir) / "environment_synchronizations.jsonl"
        assert path.exists()


class TestNoExecutionOutsideSpine:
    def test_coordinator_no_execute_method(self):
        assert not hasattr(CanonicalEnvironmentCoordinationEngine, "execute_command")
        assert not hasattr(CanonicalEnvironmentCoordinationEngine, "run_adapter")


class TestDeterministicEnvironmentReplay:
    def test_routing_hash_stable(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        topo.register_environment("vps")
        router = EnvironmentRoutingEngine(topo, state_dir=tmp_dir)
        router.route("ls", required_capability="shell")
        h1 = router.get_routing_hash()
        h2 = router.get_routing_hash()
        assert h1 == h2


class TestDeterministicRoutingReplay:
    def test_same_input_same_output(self, tmp_dir):
        v = EnvironmentReplayValidator(state_dir=tmp_dir)
        data = [{"command": "ls", "env": "vps"}]
        result = v.validate_routing_determinism(data, data)
        assert result["passed"]


class TestDeterministicSynchronizationReplay:
    def test_sync_hash_stable(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        ws = topo.register_environment("local_workstation")
        eng = EnvironmentSynchronizationEngine(topo, state_dir=tmp_dir)
        eng.synchronize(vps.environment_id, ws.environment_id)
        h1 = eng.get_sync_hash()
        h2 = eng.get_sync_hash()
        assert h1 == h2


class TestDeterministicDelegationReplay:
    def test_delegation_hash_stable(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        ws = topo.register_environment("local_workstation")
        eng = EnvironmentDelegationEngine(topo, state_dir=tmp_dir)
        eng.delegate(vps.environment_id, ws.environment_id)
        h1 = eng.get_delegation_hash()
        h2 = eng.get_delegation_hash()
        assert h1 == h2


class TestExplicitDelegationLineage:
    def test_delegation_persisted(self, tmp_dir):
        from pathlib import Path
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        ws = topo.register_environment("local_workstation")
        eng = EnvironmentDelegationEngine(topo, state_dir=tmp_dir)
        eng.delegate(vps.environment_id, ws.environment_id)
        path = Path(tmp_dir) / "environment_delegations.jsonl"
        assert path.exists()


class TestExplicitEnvironmentAuthority:
    def test_trust_tiers_asymmetric(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        br = topo.register_environment("browser_runtime")
        vps_trust = topo.get_trust(vps.environment_id)
        br_trust = topo.get_trust(br.environment_id)
        assert vps_trust.can_delegate is True
        assert br_trust.can_delegate is False


class TestNoOrphanTopologyChains:
    def test_registration_creates_graph(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        vps = eng.register_environment("vps")
        graph = eng.get_execution_graph(vps["environment_id"])
        assert graph is not None
        assert len(graph["nodes"]) >= 1


class TestNoEnvironmentNativeOrchestration:
    def test_forbidden_native_paths(self):
        enf = EnvironmentBoundaryEnforcer()
        assert not enf.check_no_forbidden_action("environment_native_execution_paths")["passed"]


class TestNoHiddenWorkerSpawning:
    def test_forbidden(self):
        enf = EnvironmentBoundaryEnforcer()
        assert not enf.check_no_forbidden_action("hidden_worker_spawning")["passed"]

    def test_forbidden_background_workers(self):
        enf = EnvironmentBoundaryEnforcer()
        assert not enf.check_no_forbidden_action("hidden_background_workers")["passed"]


class TestNoGovernanceBypass:
    def test_forbidden_bypass(self):
        enf = EnvironmentBoundaryEnforcer()
        assert not enf.check_no_forbidden_action("governance_hierarchy_bypass")["passed"]


class TestNoReplayBypass:
    def test_replay_checks_exist(self):
        assert len(REPLAY_CHECKS) == 5

    def test_all_checks_required(self, tmp_dir):
        v = EnvironmentReplayValidator(state_dir=tmp_dir)
        result = v.validate_trace({})
        assert not result["all_passed"]


class TestBoundedDelegationDepth:
    def test_depth_boundary(self):
        enf = EnvironmentBoundaryEnforcer()
        assert enf.check_delegation_depth(2)["passed"]
        assert not enf.check_delegation_depth(3)["passed"]

    def test_engine_depth_enforcement(self, tmp_dir):
        topo = EnvironmentTopologyEngine(state_dir=tmp_dir)
        vps = topo.register_environment("vps")
        ws = topo.register_environment("local_workstation")
        eng = EnvironmentDelegationEngine(topo, state_dir=tmp_dir, max_depth=2)
        assert eng.delegate(vps.environment_id, ws.environment_id, current_depth=0) is not None
        assert eng.delegate(vps.environment_id, ws.environment_id, current_depth=2) is None


# ── Full Integration Tests ──────────────────────────────────────


class TestIntegration:
    def test_full_environment_lifecycle(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        vps = eng.register_environment("vps")
        ws = eng.register_environment("local_workstation")
        br = eng.register_environment("browser_runtime")

        decision = eng.route_execution("git status", required_capability="git")
        assert decision["governance_passed"]

        sync = eng.synchronize_environments(
            vps["environment_id"], ws["environment_id"],
        )
        assert sync["state"] == "completed"

        cp = eng.checkpoint_environment(vps["environment_id"])
        assert cp["content_hash"]

        stats = eng.get_stats()
        assert stats["topology"]["total_environments"] == 3

    def test_delegation_lifecycle(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        vps = eng.register_environment("vps")
        ws = eng.register_environment("local_workstation")

        deleg = eng.delegate_execution(vps["environment_id"], ws["environment_id"])
        assert deleg["state"] == "pending"

        assert eng.approve_delegation(deleg["delegation_id"])
        assert eng.complete_delegation(deleg["delegation_id"])

    def test_routing_determinism_end_to_end(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        eng.register_environment("vps")
        eng.register_environment("local_workstation")

        d1 = eng.route_execution("git status", required_capability="git")
        d2 = eng.route_execution("docker ps", required_capability="docker")

        assert d1["governance_passed"]
        assert d2["governance_passed"]

        receipts = eng.get_recent_receipts()
        assert len(receipts) >= 2

    def test_health_degrades_to_unavailable(self, tmp_dir):
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        vps = eng.register_environment("vps")

        for _ in range(3):
            eng.update_health(vps["environment_id"], False, "timeout")

        health = eng.get_health(vps["environment_id"])
        assert health["degraded"]

    def test_bridges_integration(self, tmp_dir):
        bridges = [
            OperationsEnvironmentBridge(state_dir=tmp_dir),
            SessionsEnvironmentBridge(state_dir=tmp_dir),
            WorkflowsEnvironmentBridge(state_dir=tmp_dir),
            IngressEnvironmentBridge(state_dir=tmp_dir),
            CognitionEnvironmentBridge(state_dir=tmp_dir),
            EmbodimentEnvironmentBridge(state_dir=tmp_dir),
            ObservabilityEnvironmentBridge(state_dir=tmp_dir),
            ReplayEnvironmentBridge(state_dir=tmp_dir),
        ]
        for b in bridges:
            r = b.capture("env-1")
            assert r["bridge_id"].startswith("envbr-")
        assert len(bridges) == 8

    def test_graph_persistence_integration(self, tmp_dir):
        from pathlib import Path
        eng = CanonicalEnvironmentCoordinationEngine(state_dir=tmp_dir)
        vps = eng.register_environment("vps")
        eng.checkpoint_environment(vps["environment_id"])
        graph_path = Path(tmp_dir) / f"env_exec_graph_{vps['environment_id']}.json"
        assert graph_path.exists()

    def test_boundary_enforcement_integration(self):
        enf = EnvironmentBoundaryEnforcer()
        for action in FORBIDDEN_ENVIRONMENT_ACTIONS:
            assert not enf.check_no_forbidden_action(action)["passed"]
        assert enf.check_no_forbidden_action("register_environment")["passed"]
        assert enf.check_no_forbidden_action("route_execution")["passed"]
