"""Tests for Phase 96.8CE — Substrate Platform Deployment Readiness Coordination.

Covers: contracts, enums, lifecycle, manifests, topology, provisioning,
rollout, rollback, observability, replay, boundary policies, bridges,
coordinator, constraint verification.
"""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Contracts ──────────────────────────────────────────


class TestContracts:
    def test_deployment_projection(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentProjection,
        )
        p = DeploymentProjection(application_id="eos")
        assert p.deployment_id.startswith("dply-")
        assert p.deployment_hash != ""

    def test_deployment_environment(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentEnvironment,
        )
        e = DeploymentEnvironment(environment_type="vps")
        assert e.environment_id.startswith("denv-")

    def test_deployment_topology(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentTopology,
        )
        t = DeploymentTopology(environments=["env1", "env2"])
        assert t.topology_hash != ""

    def test_deployment_manifest(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentManifest,
        )
        m = DeploymentManifest(application_id="eos", required_capabilities=["workflows"])
        assert m.manifest_hash != ""

    def test_deployment_receipt(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentReceipt,
        )
        r = DeploymentReceipt(action="deploy")
        assert r.receipt_id.startswith("drcpt-")

    def test_deployment_lifecycle_state(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentLifecycleState,
        )
        l = DeploymentLifecycleState()
        assert l.to_dict()["current_phase"] == "defined"

    def test_deployment_replay_state(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentReplayState,
        )
        r = DeploymentReplayState(deterministic=True)
        assert r.to_dict()["deterministic"] is True

    def test_deployment_governance_state(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentGovernanceState,
        )
        g = DeploymentGovernanceState(permitted=False)
        assert g.governance_id.startswith("dgov-")

    def test_deployment_observability_state(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentObservabilityState,
        )
        o = DeploymentObservabilityState()
        assert o.observability_id.startswith("dobs-")

    def test_deployment_boundary_state(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentBoundaryState,
        )
        b = DeploymentBoundaryState()
        assert b.boundary_id.startswith("dbnd-")

    def test_rollout_state(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            RolloutState,
        )
        r = RolloutState(strategy="sequential")
        assert r.rollout_id.startswith("rout-")

    def test_rollback_state(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            RollbackState,
        )
        r = RollbackState(reason="broken")
        assert r.rollback_id.startswith("rback-")

    def test_provisioning_state(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            ProvisioningState,
        )
        p = ProvisioningState(ready=False)
        assert p.provisioning_id.startswith("dprov-")

    def test_deployment_trust_state(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentTrustState,
        )
        t = DeploymentTrustState(trust_tier="production")
        assert t.trust_id.startswith("dtrust-")

    def test_deployment_continuity_state(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentContinuityState,
        )
        c = DeploymentContinuityState()
        assert c.continuity_id.startswith("dcont-")

    def test_all_contracts_have_to_dict(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentProjection, DeploymentEnvironment, DeploymentTopology,
            DeploymentManifest, DeploymentReceipt, DeploymentLifecycleState,
            DeploymentReplayState, DeploymentGovernanceState,
            DeploymentObservabilityState, DeploymentBoundaryState,
            RolloutState, RollbackState, ProvisioningState,
            DeploymentTrustState, DeploymentContinuityState,
        )
        for cls in [
            DeploymentProjection, DeploymentEnvironment, DeploymentTopology,
            DeploymentManifest, DeploymentReceipt, DeploymentLifecycleState,
            DeploymentReplayState, DeploymentGovernanceState,
            DeploymentObservabilityState, DeploymentBoundaryState,
            RolloutState, RollbackState, ProvisioningState,
            DeploymentTrustState, DeploymentContinuityState,
        ]:
            assert isinstance(cls().to_dict(), dict)


# ── Enums ──────────────────────────────────────────────


class TestEnums:
    def test_lifecycle_phases_count(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentLifecyclePhase,
        )
        assert len(DeploymentLifecyclePhase) == 9

    def test_event_types_count(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentEventType,
        )
        assert len(DeploymentEventType) == 9

    def test_trust_tiers_count(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentTrustTier,
        )
        assert len(DeploymentTrustTier) == 4

    def test_environment_types_count(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentEnvironmentType,
        )
        assert len(DeploymentEnvironmentType) == 6

    def test_rollout_strategies_count(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            RolloutStrategy,
        )
        assert len(RolloutStrategy) == 4

    def test_lifecycle_values(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentLifecyclePhase,
        )
        values = {p.value for p in DeploymentLifecyclePhase}
        for v in ["defined", "validated", "staged", "approved", "deployed",
                   "observed", "restored", "rolled_back", "archived"]:
            assert v in values

    def test_strategy_values(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            RolloutStrategy,
        )
        values = {s.value for s in RolloutStrategy}
        assert "sequential" in values
        assert "canary" in values


# ── Lifecycle Engine ───────────────────────────────────


class TestLifecycleEngine:
    def test_initial_phase(self):
        from core.deployment.deployment_lifecycle_engine_v1 import (
            DeploymentLifecycleEngine,
        )
        le = DeploymentLifecycleEngine()
        assert le.current_phase == "defined"

    def test_valid_transition(self):
        from core.deployment.deployment_lifecycle_engine_v1 import (
            DeploymentLifecycleEngine,
        )
        le = DeploymentLifecycleEngine()
        r = le.transition("validated")
        assert r["to_phase"] == "validated"

    def test_invalid_transition_raises(self):
        from core.deployment.deployment_lifecycle_engine_v1 import (
            DeploymentLifecycleEngine,
        )
        le = DeploymentLifecycleEngine()
        with pytest.raises(ValueError, match="Invalid transition"):
            le.transition("deployed")

    def test_full_lifecycle_deploy(self):
        from core.deployment.deployment_lifecycle_engine_v1 import (
            DeploymentLifecycleEngine,
        )
        le = DeploymentLifecycleEngine()
        le.transition("validated")
        le.transition("staged")
        le.transition("approved")
        le.transition("deployed")
        le.transition("observed")
        le.transition("archived")
        assert le.current_phase == "archived"

    def test_rollback_path(self):
        from core.deployment.deployment_lifecycle_engine_v1 import (
            DeploymentLifecycleEngine,
        )
        le = DeploymentLifecycleEngine()
        le.transition("validated")
        le.transition("staged")
        le.transition("approved")
        le.transition("deployed")
        le.transition("rolled_back")
        le.transition("archived")
        assert le.current_phase == "archived"

    def test_restore_path(self):
        from core.deployment.deployment_lifecycle_engine_v1 import (
            DeploymentLifecycleEngine,
        )
        le = DeploymentLifecycleEngine()
        le.transition("validated")
        le.transition("staged")
        le.transition("approved")
        le.transition("deployed")
        le.transition("observed")
        le.transition("restored")
        le.transition("observed")
        assert le.current_phase == "observed"

    def test_terminal_state_no_transition(self):
        from core.deployment.deployment_lifecycle_engine_v1 import (
            DeploymentLifecycleEngine,
        )
        le = DeploymentLifecycleEngine()
        le.transition("validated")
        le.transition("archived")
        with pytest.raises(ValueError):
            le.transition("defined")

    def test_terminal_states_set(self):
        from core.deployment.deployment_lifecycle_engine_v1 import (
            TERMINAL_STATES,
        )
        assert TERMINAL_STATES == {"archived"}

    def test_transitions_recorded(self):
        from core.deployment.deployment_lifecycle_engine_v1 import (
            DeploymentLifecycleEngine,
        )
        le = DeploymentLifecycleEngine()
        le.transition("validated")
        le.transition("staged")
        assert len(le.get_transitions()) == 2

    def test_stats(self):
        from core.deployment.deployment_lifecycle_engine_v1 import (
            DeploymentLifecycleEngine,
        )
        le = DeploymentLifecycleEngine()
        le.transition("validated")
        s = le.get_stats()
        assert s["current_phase"] == "validated"
        assert s["total_transitions"] == 1

    def test_all_phases_covered(self):
        from core.deployment.deployment_lifecycle_engine_v1 import (
            VALID_TRANSITIONS,
        )
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentLifecyclePhase,
        )
        for phase in DeploymentLifecyclePhase:
            assert phase.value in VALID_TRANSITIONS


# ── Manifest Engine ────────────────────────────────────


class TestManifestEngine:
    def test_create_manifest(self):
        from core.deployment.deployment_manifest_engine_v1 import (
            DeploymentManifestEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            me = DeploymentManifestEngine(state_dir=td)
            m = me.create("eos", ["workflows"], ["vps"])
            assert m is not None
            assert m.application_id == "eos"

    def test_manifest_hash_deterministic(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentManifest,
        )
        m1 = DeploymentManifest(
            application_id="eos",
            required_capabilities=["workflows", "sessions"],
            environment_bindings=["vps"],
        )
        m2 = DeploymentManifest(
            application_id="eos",
            required_capabilities=["workflows", "sessions"],
            environment_bindings=["vps"],
        )
        assert m1.manifest_hash == m2.manifest_hash

    def test_validate_manifest_valid(self):
        from core.deployment.deployment_manifest_engine_v1 import (
            DeploymentManifestEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            me = DeploymentManifestEngine(state_dir=td)
            m = me.create("eos", ["workflows"], ["vps"])
            v = me.validate_manifest(m.manifest_id)
            assert v["valid"] is True

    def test_validate_manifest_missing_caps(self):
        from core.deployment.deployment_manifest_engine_v1 import (
            DeploymentManifestEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            me = DeploymentManifestEngine(state_dir=td)
            m = me.create("eos", [], ["vps"])
            v = me.validate_manifest(m.manifest_id)
            assert v["valid"] is False

    def test_validate_manifest_not_found(self):
        from core.deployment.deployment_manifest_engine_v1 import (
            DeploymentManifestEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            me = DeploymentManifestEngine(state_dir=td)
            v = me.validate_manifest("nonexistent")
            assert v["valid"] is False

    def test_get_for_app(self):
        from core.deployment.deployment_manifest_engine_v1 import (
            DeploymentManifestEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            me = DeploymentManifestEngine(state_dir=td)
            me.create("eos", ["workflows"], ["vps"])
            me.create("lyfeos", ["sessions"], ["local"])
            assert len(me.get_for_app("eos")) == 1

    def test_stats(self):
        from core.deployment.deployment_manifest_engine_v1 import (
            DeploymentManifestEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            me = DeploymentManifestEngine(state_dir=td)
            me.create("eos", ["workflows"], ["vps"])
            s = me.get_stats()
            assert s["total_manifests"] == 1


# ── Topology Engine ────────────────────────────────────


class TestTopologyEngine:
    def test_register_environment(self):
        from core.deployment.deployment_topology_engine_v1 import (
            DeploymentTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = DeploymentTopologyEngine(state_dir=td)
            e = te.register_environment("vps", "production")
            assert e is not None

    def test_unknown_env_type_rejected(self):
        from core.deployment.deployment_topology_engine_v1 import (
            DeploymentTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = DeploymentTopologyEngine(state_dir=td)
            e = te.register_environment("unknown_env")
            assert e is None

    def test_duplicate_returns_existing(self):
        from core.deployment.deployment_topology_engine_v1 import (
            DeploymentTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = DeploymentTopologyEngine(state_dir=td)
            e1 = te.register_environment("vps")
            e2 = te.register_environment("vps")
            assert e1 is e2

    def test_add_edge(self):
        from core.deployment.deployment_topology_engine_v1 import (
            DeploymentTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = DeploymentTopologyEngine(state_dir=td)
            e1 = te.register_environment("vps")
            e2 = te.register_environment("local_workstation")
            edge = te.add_edge(e1.environment_id, e2.environment_id)
            assert edge is not None

    def test_self_edge_denied(self):
        from core.deployment.deployment_topology_engine_v1 import (
            DeploymentTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = DeploymentTopologyEngine(state_dir=td)
            e1 = te.register_environment("vps")
            edge = te.add_edge(e1.environment_id, e1.environment_id)
            assert edge is None

    def test_known_environments(self):
        from core.deployment.deployment_topology_engine_v1 import (
            KNOWN_ENVIRONMENTS,
        )
        assert len(KNOWN_ENVIRONMENTS) == 6
        assert "vps" in KNOWN_ENVIRONMENTS
        assert "local_workstation" in KNOWN_ENVIRONMENTS

    def test_validate_topology_valid(self):
        from core.deployment.deployment_topology_engine_v1 import (
            DeploymentTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = DeploymentTopologyEngine(state_dir=td)
            te.register_environment("vps")
            v = te.validate_topology()
            assert v["valid"] is True

    def test_validate_topology_empty(self):
        from core.deployment.deployment_topology_engine_v1 import (
            DeploymentTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = DeploymentTopologyEngine(state_dir=td)
            v = te.validate_topology()
            assert v["valid"] is False

    def test_topology_hash_deterministic(self):
        from core.deployment.deployment_topology_engine_v1 import (
            DeploymentTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = DeploymentTopologyEngine(state_dir=td)
            te.register_environment("vps")
            te.register_environment("local_workstation")
            h1 = te.get_topology_hash()
            h2 = te.get_topology_hash()
            assert h1 == h2

    def test_topology_snapshot(self):
        from core.deployment.deployment_topology_engine_v1 import (
            DeploymentTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = DeploymentTopologyEngine(state_dir=td)
            te.register_environment("vps")
            snap = te.get_topology_snapshot()
            assert len(snap.environments) == 1

    def test_stats(self):
        from core.deployment.deployment_topology_engine_v1 import (
            DeploymentTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = DeploymentTopologyEngine(state_dir=td)
            te.register_environment("vps")
            s = te.get_stats()
            assert s["total_environments"] == 1


# ── Provisioning Engine ────────────────────────────────


class TestProvisioningEngine:
    def test_check_readiness_all_met(self):
        from core.deployment.provisioning_coordination_engine_v1 import (
            ProvisioningCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            pe = ProvisioningCoordinationEngine(state_dir=td)
            p = pe.check_readiness("env1", True, True, True)
            assert p.ready is True

    def test_check_readiness_partial(self):
        from core.deployment.provisioning_coordination_engine_v1 import (
            ProvisioningCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            pe = ProvisioningCoordinationEngine(state_dir=td)
            p = pe.check_readiness("env1", True, False, True)
            assert p.ready is False

    def test_check_readiness_none_met(self):
        from core.deployment.provisioning_coordination_engine_v1 import (
            ProvisioningCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            pe = ProvisioningCoordinationEngine(state_dir=td)
            p = pe.check_readiness("env1", False, False, False)
            assert p.ready is False

    def test_get_latest_check(self):
        from core.deployment.provisioning_coordination_engine_v1 import (
            ProvisioningCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            pe = ProvisioningCoordinationEngine(state_dir=td)
            pe.check_readiness("env1", False, False, False)
            pe.check_readiness("env1", True, True, True)
            latest = pe.get_latest_check("env1")
            assert latest is not None
            assert latest.ready is True

    def test_stats(self):
        from core.deployment.provisioning_coordination_engine_v1 import (
            ProvisioningCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            pe = ProvisioningCoordinationEngine(state_dir=td)
            pe.check_readiness("env1", True, True, True)
            pe.check_readiness("env2", False, False, False)
            s = pe.get_stats()
            assert s["ready_count"] == 1
            assert s["not_ready_count"] == 1


# ── Rollout Engine ─────────────────────────────────────


class TestRolloutEngine:
    def test_create_rollout(self):
        from core.deployment.rollout_coordination_engine_v1 import (
            RolloutCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = RolloutCoordinationEngine(state_dir=td)
            r = re.create_rollout("d1", "sequential", 3)
            assert r is not None
            assert r.status == "active"

    def test_create_rollout_requires_operator(self):
        from core.deployment.rollout_coordination_engine_v1 import (
            RolloutCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = RolloutCoordinationEngine(state_dir=td)
            with pytest.raises(ValueError, match="operator approval"):
                re.create_rollout("d1", approved_by="system")

    def test_unknown_strategy_rejected(self):
        from core.deployment.rollout_coordination_engine_v1 import (
            RolloutCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = RolloutCoordinationEngine(state_dir=td)
            r = re.create_rollout("d1", "unknown_strategy")
            assert r is None

    def test_advance_stage(self):
        from core.deployment.rollout_coordination_engine_v1 import (
            RolloutCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = RolloutCoordinationEngine(state_dir=td)
            r = re.create_rollout("d1", "sequential", 3)
            re.advance_stage(r.rollout_id)
            assert r.stages_completed == 1

    def test_advance_requires_operator(self):
        from core.deployment.rollout_coordination_engine_v1 import (
            RolloutCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = RolloutCoordinationEngine(state_dir=td)
            r = re.create_rollout("d1", "sequential", 3)
            with pytest.raises(ValueError, match="operator approval"):
                re.advance_stage(r.rollout_id, approved_by="system")

    def test_rollout_completes(self):
        from core.deployment.rollout_coordination_engine_v1 import (
            RolloutCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = RolloutCoordinationEngine(state_dir=td)
            r = re.create_rollout("d1", "sequential", 2)
            re.advance_stage(r.rollout_id)
            re.advance_stage(r.rollout_id)
            assert r.status == "completed"

    def test_cancel_rollout(self):
        from core.deployment.rollout_coordination_engine_v1 import (
            RolloutCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = RolloutCoordinationEngine(state_dir=td)
            r = re.create_rollout("d1", "sequential", 3)
            re.cancel_rollout(r.rollout_id)
            assert r.status == "cancelled"

    def test_max_active_rollouts(self):
        from core.deployment.rollout_coordination_engine_v1 import (
            RolloutCoordinationEngine, MAX_ACTIVE_ROLLOUTS,
        )
        with tempfile.TemporaryDirectory() as td:
            re = RolloutCoordinationEngine(state_dir=td)
            for i in range(MAX_ACTIVE_ROLLOUTS):
                re.create_rollout(f"d{i}")
            r = re.create_rollout("extra")
            assert r is None

    def test_rollout_hash_deterministic(self):
        from core.deployment.rollout_coordination_engine_v1 import (
            RolloutCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = RolloutCoordinationEngine(state_dir=td)
            r = re.create_rollout("d1", "sequential", 3)
            h1 = re.get_rollout_hash(r.rollout_id)
            h2 = re.get_rollout_hash(r.rollout_id)
            assert h1 == h2

    def test_stats(self):
        from core.deployment.rollout_coordination_engine_v1 import (
            RolloutCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = RolloutCoordinationEngine(state_dir=td)
            re.create_rollout("d1")
            s = re.get_stats()
            assert s["active_rollouts"] == 1


# ── Rollback Engine ────────────────────────────────────


class TestRollbackEngine:
    def test_create_rollback(self):
        from core.deployment.rollback_coordination_engine_v1 import (
            RollbackCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            rbe = RollbackCoordinationEngine(state_dir=td)
            rb = rbe.create_rollback("d2", "d1", "broken")
            assert rb is not None
            assert rb.status == "active"

    def test_create_rollback_requires_operator(self):
        from core.deployment.rollback_coordination_engine_v1 import (
            RollbackCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            rbe = RollbackCoordinationEngine(state_dir=td)
            with pytest.raises(ValueError, match="operator approval"):
                rbe.create_rollback("d2", "d1", approved_by="system")

    def test_complete_rollback(self):
        from core.deployment.rollback_coordination_engine_v1 import (
            RollbackCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            rbe = RollbackCoordinationEngine(state_dir=td)
            rb = rbe.create_rollback("d2", "d1")
            rbe.complete_rollback(rb.rollback_id)
            assert rb.status == "completed"

    def test_max_active_rollbacks(self):
        from core.deployment.rollback_coordination_engine_v1 import (
            RollbackCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            rbe = RollbackCoordinationEngine(state_dir=td)
            rbe.create_rollback("d2", "d1")
            rb2 = rbe.create_rollback("d3", "d2")
            assert rb2 is None

    def test_rollback_hash_deterministic(self):
        from core.deployment.rollback_coordination_engine_v1 import (
            RollbackCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            rbe = RollbackCoordinationEngine(state_dir=td)
            rb = rbe.create_rollback("d2", "d1", "broken")
            h1 = rbe.get_rollback_hash(rb.rollback_id)
            h2 = rbe.get_rollback_hash(rb.rollback_id)
            assert h1 == h2

    def test_stats(self):
        from core.deployment.rollback_coordination_engine_v1 import (
            RollbackCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            rbe = RollbackCoordinationEngine(state_dir=td)
            rbe.create_rollback("d2", "d1")
            s = rbe.get_stats()
            assert s["active_rollbacks"] == 1


# ── Observability Pipeline ─────────────────────────────


class TestObservabilityPipeline:
    def test_event_file_map_count(self):
        from core.deployment.deployment_observability_pipeline_v1 import (
            EVENT_FILE_MAP,
        )
        assert len(EVENT_FILE_MAP) == 9

    def test_event_file_map_matches_enum(self):
        from core.deployment.deployment_observability_pipeline_v1 import (
            EVENT_FILE_MAP,
        )
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentEventType,
        )
        for et in DeploymentEventType:
            assert et.value in EVENT_FILE_MAP

    def test_emit_deployment_created(self):
        with tempfile.TemporaryDirectory() as td:
            from core.deployment.deployment_observability_pipeline_v1 import (
                DeploymentObservabilityPipeline,
            )
            op = DeploymentObservabilityPipeline(state_dir=td)
            e = op.emit_deployment_created("d1", "eos")
            assert e["event_type"] == "deployment_created"

    def test_emit_deployment_validated(self):
        with tempfile.TemporaryDirectory() as td:
            from core.deployment.deployment_observability_pipeline_v1 import (
                DeploymentObservabilityPipeline,
            )
            op = DeploymentObservabilityPipeline(state_dir=td)
            e = op.emit_deployment_validated("d1")
            assert e["event_type"] == "deployment_validated"

    def test_emit_deployment_denied(self):
        with tempfile.TemporaryDirectory() as td:
            from core.deployment.deployment_observability_pipeline_v1 import (
                DeploymentObservabilityPipeline,
            )
            op = DeploymentObservabilityPipeline(state_dir=td)
            e = op.emit_deployment_denied("d1", "not ready")
            assert e["reason"] == "not ready"

    def test_emit_rollout_started(self):
        with tempfile.TemporaryDirectory() as td:
            from core.deployment.deployment_observability_pipeline_v1 import (
                DeploymentObservabilityPipeline,
            )
            op = DeploymentObservabilityPipeline(state_dir=td)
            e = op.emit_rollout_started("r1", "d1")
            assert e["event_type"] == "rollout_started"

    def test_emit_rollout_completed(self):
        with tempfile.TemporaryDirectory() as td:
            from core.deployment.deployment_observability_pipeline_v1 import (
                DeploymentObservabilityPipeline,
            )
            op = DeploymentObservabilityPipeline(state_dir=td)
            e = op.emit_rollout_completed("r1", "d1")
            assert e["event_type"] == "rollout_completed"

    def test_emit_rollback_events(self):
        with tempfile.TemporaryDirectory() as td:
            from core.deployment.deployment_observability_pipeline_v1 import (
                DeploymentObservabilityPipeline,
            )
            op = DeploymentObservabilityPipeline(state_dir=td)
            e1 = op.emit_rollback_started("rb1", "d1")
            e2 = op.emit_rollback_completed("rb1", "d1")
            assert e1["event_type"] == "rollback_started"
            assert e2["event_type"] == "rollback_completed"

    def test_emit_topology_validated(self):
        with tempfile.TemporaryDirectory() as td:
            from core.deployment.deployment_observability_pipeline_v1 import (
                DeploymentObservabilityPipeline,
            )
            op = DeploymentObservabilityPipeline(state_dir=td)
            e = op.emit_topology_validated("t1")
            assert e["event_type"] == "topology_validated"

    def test_emit_replay_validated(self):
        with tempfile.TemporaryDirectory() as td:
            from core.deployment.deployment_observability_pipeline_v1 import (
                DeploymentObservabilityPipeline,
            )
            op = DeploymentObservabilityPipeline(state_dir=td)
            e = op.emit_deployment_replay_validated("d1", "manifest", True)
            assert e["deterministic"] is True

    def test_events_written_to_file(self):
        with tempfile.TemporaryDirectory() as td:
            from core.deployment.deployment_observability_pipeline_v1 import (
                DeploymentObservabilityPipeline,
            )
            op = DeploymentObservabilityPipeline(state_dir=td)
            op.emit_deployment_created("d1", "eos")
            p = Path(td) / "deployment_created.jsonl"
            assert p.exists()


# ── Replay Validator ───────────────────────────────────


class TestReplayValidator:
    def test_replay_checks_count(self):
        from core.deployment.deployment_replay_validator_v1 import (
            REPLAY_CHECKS,
        )
        assert len(REPLAY_CHECKS) == 6

    def test_validate_determinism(self):
        from core.deployment.deployment_replay_validator_v1 import (
            DeploymentReplayValidator,
        )
        rv = DeploymentReplayValidator()
        r = rv.validate_determinism("manifest_resolution", "in", "out")
        assert r["deterministic"] is True

    def test_unknown_check_rejected(self):
        from core.deployment.deployment_replay_validator_v1 import (
            DeploymentReplayValidator,
        )
        rv = DeploymentReplayValidator()
        with pytest.raises(ValueError, match="Unknown check"):
            rv.validate_determinism("unknown_check", "in", "out")

    def test_replay_pair_same(self):
        from core.deployment.deployment_replay_validator_v1 import (
            DeploymentReplayValidator,
        )
        rv = DeploymentReplayValidator()
        r = rv.validate_replay_pair("topology_resolution", "in", "same", "same")
        assert r["deterministic"] is True

    def test_replay_pair_different(self):
        from core.deployment.deployment_replay_validator_v1 import (
            DeploymentReplayValidator,
        )
        rv = DeploymentReplayValidator()
        r = rv.validate_replay_pair("topology_resolution", "in", "a", "b")
        assert r["deterministic"] is False

    def test_all_checks_valid(self):
        from core.deployment.deployment_replay_validator_v1 import (
            DeploymentReplayValidator, REPLAY_CHECKS,
        )
        rv = DeploymentReplayValidator()
        for check in REPLAY_CHECKS:
            r = rv.validate_determinism(check, "in", "out")
            assert r["deterministic"] is True

    def test_stats(self):
        from core.deployment.deployment_replay_validator_v1 import (
            DeploymentReplayValidator,
        )
        rv = DeploymentReplayValidator()
        rv.validate_determinism("manifest_resolution", "in", "out")
        s = rv.get_stats()
        assert s["total_checks"] == 1


# ── Boundary Policies ─────────────────────────────────


class TestBoundaryPolicies:
    def test_limits_count(self):
        from core.deployment.deployment_boundary_policies_v1 import (
            DEPLOYMENT_LIMITS,
        )
        assert len(DEPLOYMENT_LIMITS) == 8

    def test_forbidden_count(self):
        from core.deployment.deployment_boundary_policies_v1 import (
            FORBIDDEN_DEPLOYMENT_ACTIONS,
        )
        assert len(FORBIDDEN_DEPLOYMENT_ACTIONS) == 10

    def test_enforce_limit_default(self):
        from core.deployment.deployment_boundary_policies_v1 import (
            enforce_limit,
        )
        assert enforce_limit("max_deployments") == 50

    def test_enforce_limit_override_lower(self):
        from core.deployment.deployment_boundary_policies_v1 import (
            enforce_limit,
        )
        assert enforce_limit("max_deployments", 10) == 10

    def test_enforce_limit_override_higher_capped(self):
        from core.deployment.deployment_boundary_policies_v1 import (
            enforce_limit,
        )
        assert enforce_limit("max_deployments", 100) == 50

    def test_enforce_limit_unknown_raises(self):
        from core.deployment.deployment_boundary_policies_v1 import (
            enforce_limit,
        )
        with pytest.raises(ValueError, match="Unknown limit"):
            enforce_limit("unknown_limit")

    def test_autonomous_deployment_forbidden(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("autonomous_deployment") is True

    def test_autonomous_provisioning_forbidden(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("autonomous_provisioning") is True

    def test_hidden_environment_mutation_forbidden(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("hidden_environment_mutation") is True

    def test_hidden_rollout_expansion_forbidden(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("hidden_rollout_expansion") is True

    def test_deployment_owned_orchestration_forbidden(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("deployment_owned_orchestration") is True

    def test_deployment_owned_cognition_forbidden(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("deployment_owned_cognition") is True

    def test_replay_bypass_forbidden(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("replay_bypass") is True

    def test_governance_bypass_forbidden(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("governance_bypass") is True

    def test_uncontrolled_fanout_forbidden(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("uncontrolled_fanout") is True

    def test_recursive_rollout_loops_forbidden(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("recursive_rollout_loops") is True

    def test_override_capping(self):
        from core.deployment.deployment_boundary_policies_v1 import (
            enforce_limit, DEPLOYMENT_LIMITS,
        )
        for name, default in DEPLOYMENT_LIMITS.items():
            assert enforce_limit(name, default + 100) == default
            assert enforce_limit(name, default - 1) == default - 1

    def test_validate_boundaries(self):
        from core.deployment.deployment_boundary_policies_v1 import (
            validate_boundaries,
        )
        v = validate_boundaries()
        assert v["limits_count"] == 8
        assert v["forbidden_count"] == 10


# ── Continuity Bridges ─────────────────────────────────


class TestContinuityBridges:
    def test_all_bridges_count(self):
        from core.deployment.deployment_continuity_bridges_v1 import (
            ALL_BRIDGES,
        )
        assert len(ALL_BRIDGES) == 9

    def test_applications_bridge(self):
        from core.deployment.deployment_continuity_bridges_v1 import (
            ApplicationsDeploymentBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = ApplicationsDeploymentBridge(state_dir=td)
            e = b.record("test", {"key": "value"})
            assert e["bridge"] == "applications_deployment"

    def test_environments_bridge(self):
        from core.deployment.deployment_continuity_bridges_v1 import (
            EnvironmentsDeploymentBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = EnvironmentsDeploymentBridge(state_dir=td)
            e = b.record("test", {})
            assert e["bridge"] == "environments_deployment"

    def test_scaling_bridge(self):
        from core.deployment.deployment_continuity_bridges_v1 import (
            ScalingDeploymentBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = ScalingDeploymentBridge(state_dir=td)
            e = b.record("test", {})
            assert e["bridge"] == "scaling_deployment"

    def test_resilience_bridge(self):
        from core.deployment.deployment_continuity_bridges_v1 import (
            ResilienceDeploymentBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = ResilienceDeploymentBridge(state_dir=td)
            e = b.record("test", {})
            assert e["bridge"] == "resilience_deployment"

    def test_sessions_bridge(self):
        from core.deployment.deployment_continuity_bridges_v1 import (
            SessionsDeploymentBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = SessionsDeploymentBridge(state_dir=td)
            e = b.record("test", {})
            assert e["bridge"] == "sessions_deployment"

    def test_workflows_bridge(self):
        from core.deployment.deployment_continuity_bridges_v1 import (
            WorkflowsDeploymentBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = WorkflowsDeploymentBridge(state_dir=td)
            e = b.record("test", {})
            assert e["bridge"] == "workflows_deployment"

    def test_observability_bridge(self):
        from core.deployment.deployment_continuity_bridges_v1 import (
            ObservabilityDeploymentBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = ObservabilityDeploymentBridge(state_dir=td)
            e = b.record("test", {})
            assert e["bridge"] == "observability_deployment"

    def test_replay_bridge(self):
        from core.deployment.deployment_continuity_bridges_v1 import (
            ReplayDeploymentBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = ReplayDeploymentBridge(state_dir=td)
            e = b.record("test", {})
            assert e["bridge"] == "replay_deployment"

    def test_governance_bridge(self):
        from core.deployment.deployment_continuity_bridges_v1 import (
            GovernanceDeploymentBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = GovernanceDeploymentBridge(state_dir=td)
            e = b.record("test", {})
            assert e["bridge"] == "governance_deployment"

    def test_bridge_events_tracked(self):
        from core.deployment.deployment_continuity_bridges_v1 import (
            ApplicationsDeploymentBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = ApplicationsDeploymentBridge(state_dir=td)
            b.record("e1", {"a": 1})
            b.record("e2", {"b": 2})
            assert len(b.get_events()) == 2

    def test_bridge_writes_to_file(self):
        from core.deployment.deployment_continuity_bridges_v1 import (
            ApplicationsDeploymentBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = ApplicationsDeploymentBridge(state_dir=td)
            b.record("test", {})
            p = Path(td) / "applications_deployment.jsonl"
            assert p.exists()


# ── Coordinator ────────────────────────────────────────


class TestCoordinator:
    def _make(self, td):
        from core.deployment.canonical_platform_deployment_coordinator_v1 import (
            CanonicalPlatformDeploymentCoordinator,
        )
        return CanonicalPlatformDeploymentCoordinator(state_dir=td)

    def test_create_deployment(self):
        with tempfile.TemporaryDirectory() as td:
            c = self._make(td)
            d = c.create_deployment("eos", trust_tier="production")
            assert d["application_id"] == "eos"

    def test_create_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            c = self._make(td)
            m = c.create_manifest("eos", ["workflows"], ["vps"])
            assert m is not None

    def test_validate_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            c = self._make(td)
            m = c.create_manifest("eos", ["workflows"], ["vps"])
            v = c.validate_manifest(m["manifest_id"])
            assert v["valid"] is True

    def test_register_environment(self):
        with tempfile.TemporaryDirectory() as td:
            c = self._make(td)
            e = c.register_environment("vps", "production")
            assert e is not None

    def test_validate_topology(self):
        with tempfile.TemporaryDirectory() as td:
            c = self._make(td)
            c.register_environment("vps")
            v = c.validate_topology()
            assert v["valid"] is True

    def test_check_provisioning(self):
        with tempfile.TemporaryDirectory() as td:
            c = self._make(td)
            p = c.check_provisioning("env1", True, True, True)
            assert p["ready"] is True

    def test_start_rollout(self):
        with tempfile.TemporaryDirectory() as td:
            c = self._make(td)
            d = c.create_deployment("eos")
            r = c.start_rollout(d["deployment_id"], "sequential", 3)
            assert r is not None
            assert r["status"] == "active"

    def test_advance_and_complete_rollout(self):
        with tempfile.TemporaryDirectory() as td:
            c = self._make(td)
            d = c.create_deployment("eos")
            r = c.start_rollout(d["deployment_id"], "sequential", 2)
            c.advance_rollout(r["rollout_id"])
            result = c.advance_rollout(r["rollout_id"])
            assert result["status"] == "completed"

    def test_start_rollback(self):
        with tempfile.TemporaryDirectory() as td:
            c = self._make(td)
            rb = c.start_rollback("d2", "d1", "broken")
            assert rb is not None

    def test_complete_rollback(self):
        with tempfile.TemporaryDirectory() as td:
            c = self._make(td)
            rb = c.start_rollback("d2", "d1")
            result = c.complete_rollback(rb["rollback_id"])
            assert result["status"] == "completed"

    def test_get_all_deployments(self):
        with tempfile.TemporaryDirectory() as td:
            c = self._make(td)
            c.create_deployment("eos")
            c.create_deployment("lyfeos")
            assert len(c.get_all_deployments()) == 2

    def test_get_topology_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            c = self._make(td)
            c.register_environment("vps")
            snap = c.get_topology_snapshot()
            assert len(snap["environments"]) == 1

    def test_get_health(self):
        with tempfile.TemporaryDirectory() as td:
            c = self._make(td)
            h = c.get_health()
            for key in ["lifecycle_phase", "manifests", "topology",
                        "provisioning", "rollouts", "rollbacks"]:
                assert key in h

    def test_get_stats_eight_keys(self):
        with tempfile.TemporaryDirectory() as td:
            c = self._make(td)
            s = c.get_stats()
            assert len(s) == 8

    def test_no_forbidden_methods(self):
        with tempfile.TemporaryDirectory() as td:
            c = self._make(td)
            methods = [m for m in dir(c) if not m.startswith("_")]
            for fm in ["execute", "dispatch", "orchestrate", "govern",
                        "scale", "inject_cognition", "bypass_spine"]:
                assert fm not in methods


# ── Constraint Verification ────────────────────────────


class TestConstraintVerification:
    def test_no_autonomous_deployment(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("autonomous_deployment") is True

    def test_no_autonomous_provisioning(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("autonomous_provisioning") is True

    def test_no_hidden_topology_mutation(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("hidden_environment_mutation") is True

    def test_no_uncontrolled_rollout_fanout(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("uncontrolled_fanout") is True

    def test_deterministic_deployment_replay(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentProjection,
        )
        d1 = DeploymentProjection(
            application_id="eos", manifest_id="m1", environment_id="e1",
        )
        d2 = DeploymentProjection(
            application_id="eos", manifest_id="m1", environment_id="e1",
        )
        assert d1.deployment_hash == d2.deployment_hash

    def test_deterministic_manifest_hash(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentManifest,
        )
        m1 = DeploymentManifest(
            application_id="eos",
            required_capabilities=["workflows", "sessions"],
            environment_bindings=["vps"],
        )
        m2 = DeploymentManifest(
            application_id="eos",
            required_capabilities=["workflows", "sessions"],
            environment_bindings=["vps"],
        )
        assert m1.manifest_hash == m2.manifest_hash

    def test_deterministic_rollback_replay(self):
        from core.deployment.rollback_coordination_engine_v1 import (
            RollbackCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            rbe = RollbackCoordinationEngine(state_dir=td)
            rb = rbe.create_rollback("d2", "d1", "broken")
            h1 = rbe.get_rollback_hash(rb.rollback_id)
            h2 = rbe.get_rollback_hash(rb.rollback_id)
            assert h1 == h2

    def test_topology_validation_correctness(self):
        from core.deployment.deployment_topology_engine_v1 import (
            DeploymentTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = DeploymentTopologyEngine(state_dir=td)
            v = te.validate_topology()
            assert v["valid"] is False
            te.register_environment("vps")
            v = te.validate_topology()
            assert v["valid"] is True

    def test_rollout_operator_only(self):
        from core.deployment.rollout_coordination_engine_v1 import (
            RolloutCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = RolloutCoordinationEngine(state_dir=td)
            with pytest.raises(ValueError):
                re.create_rollout("d1", approved_by="system")

    def test_rollback_operator_only(self):
        from core.deployment.rollback_coordination_engine_v1 import (
            RollbackCoordinationEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            rbe = RollbackCoordinationEngine(state_dir=td)
            with pytest.raises(ValueError):
                rbe.create_rollback("d2", "d1", approved_by="system")

    def test_governance_preserved(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("governance_bypass") is True
        assert is_forbidden("replay_bypass") is True

    def test_replay_lineage_preserved(self):
        from core.deployment.deployment_replay_validator_v1 import (
            DeploymentReplayValidator, REPLAY_CHECKS,
        )
        rv = DeploymentReplayValidator()
        for check in REPLAY_CHECKS:
            r = rv.validate_determinism(check, "input", "output")
            assert r["deterministic"] is True

    def test_continuity_restoration_deterministic(self):
        from core.deployment.platform_deployment_contracts_v1 import (
            DeploymentTopology,
        )
        t1 = DeploymentTopology(environments=["e1", "e2"])
        t2 = DeploymentTopology(environments=["e1", "e2"])
        assert t1.topology_hash == t2.topology_hash

    def test_override_capping_all_limits(self):
        from core.deployment.deployment_boundary_policies_v1 import (
            enforce_limit, DEPLOYMENT_LIMITS,
        )
        for name, default in DEPLOYMENT_LIMITS.items():
            assert enforce_limit(name, default + 100) == default

    def test_coordinator_cannot_execute(self):
        with tempfile.TemporaryDirectory() as td:
            from core.deployment.canonical_platform_deployment_coordinator_v1 import (
                CanonicalPlatformDeploymentCoordinator,
            )
            c = CanonicalPlatformDeploymentCoordinator(state_dir=td)
            methods = dir(c)
            assert "execute" not in methods
            assert "dispatch" not in methods

    def test_coordinator_cannot_orchestrate(self):
        with tempfile.TemporaryDirectory() as td:
            from core.deployment.canonical_platform_deployment_coordinator_v1 import (
                CanonicalPlatformDeploymentCoordinator,
            )
            c = CanonicalPlatformDeploymentCoordinator(state_dir=td)
            methods = dir(c)
            assert "orchestrate" not in methods
            assert "scale" not in methods

    def test_no_deployment_owned_cognition(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("deployment_owned_cognition") is True

    def test_no_recursive_rollout_loops(self):
        from core.deployment.deployment_boundary_policies_v1 import is_forbidden
        assert is_forbidden("recursive_rollout_loops") is True
