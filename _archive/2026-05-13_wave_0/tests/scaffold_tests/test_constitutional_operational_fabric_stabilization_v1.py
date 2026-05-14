"""Tests for Phase 96.8CH — Constitutional Operational Fabric Stabilization.

Tests: contracts, enums, lifecycle, concurrency durability, replay durability,
continuity durability, topology durability, resilience interaction,
observability pipeline, replay validator, boundary policies,
continuity bridges, coordinator, constraint verification.
"""

import sys
import tempfile
import os
import json

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import pytest


# ── Contracts ──────────────────────────────────────────────────

class TestContracts:
    def test_stabilization_scenario_creation(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import StabilizationScenario
        s = StabilizationScenario(name="test", domain="concurrency")
        assert s.scenario_id.startswith("stab-")
        assert s.name == "test"

    def test_stabilization_scenario_to_dict(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import StabilizationScenario
        s = StabilizationScenario(name="test", domain="replay")
        d = s.to_dict()
        assert d["name"] == "test"
        assert d["domain"] == "replay"
        assert "scenario_id" in d

    def test_runtime_stress_state(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import RuntimeStressState
        s = RuntimeStressState(scenario_id="stab-abc123")
        assert s.stress_id.startswith("rstress-")
        assert s.outcome == "stable"

    def test_operational_durability_state(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import OperationalDurabilityState
        s = OperationalDurabilityState(domain="concurrency")
        assert s.durability_id.startswith("odur-")
        assert s.durable is True

    def test_concurrency_validation_state(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import ConcurrencyValidationState
        s = ConcurrencyValidationState(concurrent_operations=5)
        assert s.concurrency_id.startswith("cval-")

    def test_replay_durability_state(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import ReplayDurabilityState
        s = ReplayDurabilityState(layers_validated=3)
        assert s.replay_id.startswith("rdur-")

    def test_continuity_durability_state(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import ContinuityDurabilityState
        s = ContinuityDurabilityState(layers_validated=2)
        assert s.continuity_id.startswith("cdur-")

    def test_recovery_durability_state(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import RecoveryDurabilityState
        s = RecoveryDurabilityState(recovery_scenarios=4)
        assert s.recovery_id.startswith("recdur-")

    def test_topology_durability_state(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import TopologyDurabilityState
        s = TopologyDurabilityState(topologies_validated=3)
        assert s.topology_id.startswith("tdur-")

    def test_synchronization_durability_state(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import SynchronizationDurabilityState
        s = SynchronizationDurabilityState(targets_validated=2)
        assert s.sync_id.startswith("sdur-")

    def test_fabric_stability_receipt(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import FabricStabilityReceipt
        r = FabricStabilityReceipt(run_id="run-001")
        assert r.receipt_id.startswith("frcpt-")
        assert r.outcome == "stable"

    def test_stability_boundary_state(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import StabilityBoundaryState
        s = StabilityBoundaryState(limit_name="max_ops")
        assert s.boundary_id.startswith("sbnd-")

    def test_stability_replay_state(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import StabilityReplayState
        s = StabilityReplayState(check_name="test_check")
        assert s.replay_id.startswith("srplay-")

    def test_stability_observability_state(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import StabilityObservabilityState
        s = StabilityObservabilityState(events_emitted=10)
        assert s.observability_id.startswith("sobs-")

    def test_stability_lifecycle_state(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import StabilityLifecycleState
        s = StabilityLifecycleState(phase="defined")
        assert s.lifecycle_id.startswith("slc-")

    def test_stability_governance_state(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import StabilityGovernanceState
        s = StabilityGovernanceState()
        assert s.governance_id.startswith("sgov-")
        assert s.governance_preserved is True


# ── Enums ──────────────────────────────────────────────────────

class TestEnums:
    def test_stabilization_phase_values(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import StabilizationPhase
        assert len(StabilizationPhase) == 6
        assert StabilizationPhase.DEFINED == "defined"
        assert StabilizationPhase.ARCHIVED == "archived"

    def test_stabilization_event_type_values(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import StabilizationEventType
        assert len(StabilizationEventType) == 7

    def test_durability_domain_values(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import DurabilityDomain
        assert len(DurabilityDomain) == 8

    def test_stress_intensity_values(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import StressIntensity
        assert len(StressIntensity) == 4

    def test_stabilization_outcome_values(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import StabilizationOutcome
        assert len(StabilizationOutcome) == 4

    def test_all_enums_are_str_enum(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import (
            StabilizationPhase, StabilizationEventType, DurabilityDomain,
            StressIntensity, StabilizationOutcome,
        )
        assert isinstance(StabilizationPhase.DEFINED, str)
        assert isinstance(StabilizationEventType.CONCURRENCY_VALIDATED, str)
        assert isinstance(DurabilityDomain.CONCURRENCY, str)

    def test_durability_domain_has_8_domains(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import DurabilityDomain
        domains = [d.value for d in DurabilityDomain]
        assert "concurrency" in domains
        assert "replay" in domains
        assert "continuity" in domains
        assert "topology" in domains
        assert "resilience" in domains
        assert "scaling" in domains
        assert "deployment" in domains
        assert "orchestration" in domains


# ── Lifecycle Engine ───────────────────────────────────────────

class TestLifecycleEngine:
    def test_initial_phase(self):
        from core.stabilization.stabilization_lifecycle_engine_v1 import StabilizationLifecycleEngine
        engine = StabilizationLifecycleEngine()
        assert engine.current_phase == "defined"

    def test_full_lifecycle(self):
        from core.stabilization.stabilization_lifecycle_engine_v1 import StabilizationLifecycleEngine
        engine = StabilizationLifecycleEngine()
        phases = ["staged", "stressed", "validated", "hardened", "archived"]
        for p in phases:
            engine.transition(p)
        assert engine.current_phase == "archived"
        assert engine.is_terminal is True

    def test_invalid_transition(self):
        from core.stabilization.stabilization_lifecycle_engine_v1 import StabilizationLifecycleEngine
        engine = StabilizationLifecycleEngine()
        with pytest.raises(ValueError, match="Invalid transition"):
            engine.transition("archived")

    def test_terminal_state_blocks(self):
        from core.stabilization.stabilization_lifecycle_engine_v1 import StabilizationLifecycleEngine
        engine = StabilizationLifecycleEngine()
        for p in ["staged", "stressed", "validated", "hardened", "archived"]:
            engine.transition(p)
        with pytest.raises(ValueError, match="terminal state"):
            engine.transition("defined")

    def test_can_transition(self):
        from core.stabilization.stabilization_lifecycle_engine_v1 import StabilizationLifecycleEngine
        engine = StabilizationLifecycleEngine()
        assert engine.can_transition("staged") is True
        assert engine.can_transition("archived") is False

    def test_history_tracking(self):
        from core.stabilization.stabilization_lifecycle_engine_v1 import StabilizationLifecycleEngine
        engine = StabilizationLifecycleEngine()
        engine.transition("staged")
        engine.transition("stressed")
        history = engine.get_history()
        assert len(history) == 2
        assert history[0]["from"] == "defined"
        assert history[0]["to"] == "staged"

    def test_stats(self):
        from core.stabilization.stabilization_lifecycle_engine_v1 import StabilizationLifecycleEngine
        engine = StabilizationLifecycleEngine()
        engine.transition("staged")
        stats = engine.get_stats()
        assert stats["current_phase"] == "staged"
        assert stats["transitions"] == 1

    def test_linear_progression_only(self):
        from core.stabilization.stabilization_lifecycle_engine_v1 import StabilizationLifecycleEngine
        engine = StabilizationLifecycleEngine()
        engine.transition("staged")
        with pytest.raises(ValueError):
            engine.transition("defined")


# ── Concurrency Durability Engine ──────────────────────────────

class TestConcurrencyDurabilityEngine:
    def test_validate_durable(self):
        from core.stabilization.concurrency_durability_engine_v1 import ConcurrencyDurabilityEngine
        engine = ConcurrencyDurabilityEngine()
        result = engine.validate_concurrency(10)
        assert result["durable"] is True

    def test_validate_non_durable(self):
        from core.stabilization.concurrency_durability_engine_v1 import ConcurrencyDurabilityEngine
        engine = ConcurrencyDurabilityEngine()
        result = engine.validate_concurrency(10, all_deterministic=False)
        assert result["durable"] is False

    def test_fanout_not_bounded(self):
        from core.stabilization.concurrency_durability_engine_v1 import ConcurrencyDurabilityEngine
        engine = ConcurrencyDurabilityEngine()
        result = engine.validate_concurrency(10, fanout_bounded=False)
        assert result["durable"] is False

    def test_all_durable_empty(self):
        from core.stabilization.concurrency_durability_engine_v1 import ConcurrencyDurabilityEngine
        engine = ConcurrencyDurabilityEngine()
        assert engine.all_durable() is True

    def test_counts(self):
        from core.stabilization.concurrency_durability_engine_v1 import ConcurrencyDurabilityEngine
        engine = ConcurrencyDurabilityEngine()
        engine.validate_concurrency(10)
        engine.validate_concurrency(5, all_deterministic=False)
        assert engine.get_durable_count() == 1
        assert engine.get_failed_count() == 1

    def test_max_validations(self):
        from core.stabilization.concurrency_durability_engine_v1 import ConcurrencyDurabilityEngine
        engine = ConcurrencyDurabilityEngine()
        for i in range(50):
            engine.validate_concurrency(i)
        with pytest.raises(ValueError, match="Max concurrent validations"):
            engine.validate_concurrency(999)

    def test_stats(self):
        from core.stabilization.concurrency_durability_engine_v1 import ConcurrencyDurabilityEngine
        engine = ConcurrencyDurabilityEngine()
        engine.validate_concurrency(10)
        stats = engine.get_stats()
        assert stats["total_validations"] == 1
        assert stats["all_durable"] is True


# ── Replay Durability Engine ──────────────────────────────────

class TestReplayDurabilityEngine:
    def test_validate_durable(self):
        from core.stabilization.replay_durability_engine_v1 import ReplayDurabilityEngine
        engine = ReplayDurabilityEngine()
        result = engine.validate_replay_durability(5)
        assert result["durable"] is True

    def test_validate_non_deterministic(self):
        from core.stabilization.replay_durability_engine_v1 import ReplayDurabilityEngine
        engine = ReplayDurabilityEngine()
        result = engine.validate_replay_durability(5, all_deterministic=False)
        assert result["durable"] is False

    def test_lineage_broken(self):
        from core.stabilization.replay_durability_engine_v1 import ReplayDurabilityEngine
        engine = ReplayDurabilityEngine()
        result = engine.validate_replay_durability(5, lineage_intact=False)
        assert result["durable"] is False

    def test_all_durable(self):
        from core.stabilization.replay_durability_engine_v1 import ReplayDurabilityEngine
        engine = ReplayDurabilityEngine()
        engine.validate_replay_durability(3)
        engine.validate_replay_durability(5)
        assert engine.all_durable() is True

    def test_counts(self):
        from core.stabilization.replay_durability_engine_v1 import ReplayDurabilityEngine
        engine = ReplayDurabilityEngine()
        engine.validate_replay_durability(3)
        engine.validate_replay_durability(5, all_deterministic=False)
        assert engine.get_durable_count() == 1
        assert engine.get_failed_count() == 1

    def test_max_validations(self):
        from core.stabilization.replay_durability_engine_v1 import ReplayDurabilityEngine
        engine = ReplayDurabilityEngine()
        for i in range(50):
            engine.validate_replay_durability(i)
        with pytest.raises(ValueError, match="Max replay validations"):
            engine.validate_replay_durability(999)

    def test_stats(self):
        from core.stabilization.replay_durability_engine_v1 import ReplayDurabilityEngine
        engine = ReplayDurabilityEngine()
        engine.validate_replay_durability(3)
        stats = engine.get_stats()
        assert stats["total_validations"] == 1


# ── Continuity Durability Engine ──────────────────────────────

class TestContinuityDurabilityEngine:
    def test_validate_durable(self):
        from core.stabilization.continuity_durability_engine_v1 import ContinuityDurabilityEngine
        engine = ContinuityDurabilityEngine()
        result = engine.validate_continuity_durability(3, checkpoints_restored=2)
        assert result["durable"] is True

    def test_validate_not_restored(self):
        from core.stabilization.continuity_durability_engine_v1 import ContinuityDurabilityEngine
        engine = ContinuityDurabilityEngine()
        result = engine.validate_continuity_durability(3, all_restored=False)
        assert result["durable"] is False

    def test_all_durable(self):
        from core.stabilization.continuity_durability_engine_v1 import ContinuityDurabilityEngine
        engine = ContinuityDurabilityEngine()
        engine.validate_continuity_durability(3)
        assert engine.all_durable() is True

    def test_counts(self):
        from core.stabilization.continuity_durability_engine_v1 import ContinuityDurabilityEngine
        engine = ContinuityDurabilityEngine()
        engine.validate_continuity_durability(3)
        engine.validate_continuity_durability(2, all_restored=False)
        assert engine.get_durable_count() == 1
        assert engine.get_failed_count() == 1

    def test_max_validations(self):
        from core.stabilization.continuity_durability_engine_v1 import ContinuityDurabilityEngine
        engine = ContinuityDurabilityEngine()
        for i in range(50):
            engine.validate_continuity_durability(i)
        with pytest.raises(ValueError, match="Max continuity validations"):
            engine.validate_continuity_durability(999)

    def test_stats(self):
        from core.stabilization.continuity_durability_engine_v1 import ContinuityDurabilityEngine
        engine = ContinuityDurabilityEngine()
        stats = engine.get_stats()
        assert stats["total_validations"] == 0
        assert stats["all_durable"] is True


# ── Topology Durability Engine ────────────────────────────────

class TestTopologyDurabilityEngine:
    def test_validate_durable(self):
        from core.stabilization.topology_durability_engine_v1 import TopologyDurabilityEngine
        engine = TopologyDurabilityEngine()
        result = engine.validate_topology_durability(4)
        assert result["durable"] is True

    def test_not_intact(self):
        from core.stabilization.topology_durability_engine_v1 import TopologyDurabilityEngine
        engine = TopologyDurabilityEngine()
        result = engine.validate_topology_durability(4, all_intact=False)
        assert result["durable"] is False

    def test_orphans_detected(self):
        from core.stabilization.topology_durability_engine_v1 import TopologyDurabilityEngine
        engine = TopologyDurabilityEngine()
        result = engine.validate_topology_durability(4, no_orphans=False)
        assert result["durable"] is False

    def test_hidden_mutation(self):
        from core.stabilization.topology_durability_engine_v1 import TopologyDurabilityEngine
        engine = TopologyDurabilityEngine()
        result = engine.validate_topology_durability(4, no_hidden_mutation=False)
        assert result["durable"] is False

    def test_all_durable(self):
        from core.stabilization.topology_durability_engine_v1 import TopologyDurabilityEngine
        engine = TopologyDurabilityEngine()
        engine.validate_topology_durability(3)
        engine.validate_topology_durability(5)
        assert engine.all_durable() is True

    def test_counts(self):
        from core.stabilization.topology_durability_engine_v1 import TopologyDurabilityEngine
        engine = TopologyDurabilityEngine()
        engine.validate_topology_durability(3)
        engine.validate_topology_durability(2, all_intact=False)
        assert engine.get_durable_count() == 1
        assert engine.get_failed_count() == 1

    def test_max_validations(self):
        from core.stabilization.topology_durability_engine_v1 import TopologyDurabilityEngine
        engine = TopologyDurabilityEngine()
        for i in range(50):
            engine.validate_topology_durability(i)
        with pytest.raises(ValueError, match="Max topology validations"):
            engine.validate_topology_durability(999)

    def test_stats(self):
        from core.stabilization.topology_durability_engine_v1 import TopologyDurabilityEngine
        engine = TopologyDurabilityEngine()
        engine.validate_topology_durability(3)
        stats = engine.get_stats()
        assert stats["total_validations"] == 1


# ── Resilience Interaction Engine ─────────────────────────────

class TestResilienceInteractionEngine:
    def test_validate_durable(self):
        from core.stabilization.resilience_interaction_engine_v1 import ResilienceInteractionEngine
        engine = ResilienceInteractionEngine()
        result = engine.validate_resilience(5)
        assert result["durable"] is True

    def test_not_stable(self):
        from core.stabilization.resilience_interaction_engine_v1 import ResilienceInteractionEngine
        engine = ResilienceInteractionEngine()
        result = engine.validate_resilience(5, all_stable=False)
        assert result["durable"] is False

    def test_recursive_loops(self):
        from core.stabilization.resilience_interaction_engine_v1 import ResilienceInteractionEngine
        engine = ResilienceInteractionEngine()
        result = engine.validate_resilience(5, no_recursive_loops=False)
        assert result["durable"] is False

    def test_all_durable(self):
        from core.stabilization.resilience_interaction_engine_v1 import ResilienceInteractionEngine
        engine = ResilienceInteractionEngine()
        engine.validate_resilience(3)
        assert engine.all_durable() is True

    def test_counts(self):
        from core.stabilization.resilience_interaction_engine_v1 import ResilienceInteractionEngine
        engine = ResilienceInteractionEngine()
        engine.validate_resilience(3)
        engine.validate_resilience(2, all_stable=False)
        assert engine.get_durable_count() == 1
        assert engine.get_failed_count() == 1

    def test_max_validations(self):
        from core.stabilization.resilience_interaction_engine_v1 import ResilienceInteractionEngine
        engine = ResilienceInteractionEngine()
        for i in range(50):
            engine.validate_resilience(i)
        with pytest.raises(ValueError, match="Max recovery validations"):
            engine.validate_resilience(999)

    def test_stats(self):
        from core.stabilization.resilience_interaction_engine_v1 import ResilienceInteractionEngine
        engine = ResilienceInteractionEngine()
        stats = engine.get_stats()
        assert stats["total_validations"] == 0


# ── Observability Pipeline ────────────────────────────────────

class TestObservabilityPipeline:
    def test_emit_run_started(self):
        from core.stabilization.stabilization_observability_pipeline_v1 import StabilizationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = StabilizationObservabilityPipeline(state_dir=td)
            event = pipe.emit_stabilization_run_started(run_id="run-001")
            assert event["event_type"] == "stabilization_run_started"

    def test_emit_run_completed(self):
        from core.stabilization.stabilization_observability_pipeline_v1 import StabilizationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = StabilizationObservabilityPipeline(state_dir=td)
            event = pipe.emit_stabilization_run_completed(run_id="run-001", outcome="stable")
            assert event["outcome"] == "stable"

    def test_emit_concurrency_validated(self):
        from core.stabilization.stabilization_observability_pipeline_v1 import StabilizationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = StabilizationObservabilityPipeline(state_dir=td)
            event = pipe.emit_concurrency_validated(concurrent_operations=10)
            assert event["concurrent_operations"] == 10

    def test_emit_replay_durability_validated(self):
        from core.stabilization.stabilization_observability_pipeline_v1 import StabilizationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = StabilizationObservabilityPipeline(state_dir=td)
            event = pipe.emit_replay_durability_validated(layers_validated=5)
            assert event["layers_validated"] == 5

    def test_emit_continuity_durability_validated(self):
        from core.stabilization.stabilization_observability_pipeline_v1 import StabilizationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = StabilizationObservabilityPipeline(state_dir=td)
            event = pipe.emit_continuity_durability_validated(layers_validated=3)
            assert event["layers_validated"] == 3

    def test_emit_topology_durability_validated(self):
        from core.stabilization.stabilization_observability_pipeline_v1 import StabilizationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = StabilizationObservabilityPipeline(state_dir=td)
            event = pipe.emit_topology_durability_validated(domains_validated=4)
            assert event["domains_validated"] == 4

    def test_emit_boundary_denied(self):
        from core.stabilization.stabilization_observability_pipeline_v1 import StabilizationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = StabilizationObservabilityPipeline(state_dir=td)
            event = pipe.emit_stabilization_boundary_denied(
                limit_name="max_ops", current_value=100, max_value=50,
            )
            assert event["limit_name"] == "max_ops"

    def test_event_file_map_has_7_entries(self):
        from core.stabilization.stabilization_observability_pipeline_v1 import EVENT_FILE_MAP
        assert len(EVENT_FILE_MAP) == 7

    def test_jsonl_persistence(self):
        from core.stabilization.stabilization_observability_pipeline_v1 import StabilizationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = StabilizationObservabilityPipeline(state_dir=td)
            pipe.emit_stabilization_run_started(run_id="run-001")
            filepath = os.path.join(td, "stabilization_run_started.jsonl")
            assert os.path.exists(filepath)
            with open(filepath) as f:
                line = f.readline()
                data = json.loads(line)
                assert data["run_id"] == "run-001"

    def test_get_events(self):
        from core.stabilization.stabilization_observability_pipeline_v1 import StabilizationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = StabilizationObservabilityPipeline(state_dir=td)
            pipe.emit_stabilization_run_started(run_id="r1")
            pipe.emit_stabilization_run_completed(run_id="r1")
            assert len(pipe.get_events()) == 2

    def test_stats(self):
        from core.stabilization.stabilization_observability_pipeline_v1 import StabilizationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = StabilizationObservabilityPipeline(state_dir=td)
            pipe.emit_stabilization_run_started(run_id="r1")
            stats = pipe.get_stats()
            assert stats["total_events"] == 1
            assert stats["event_types"] == 7


# ── Replay Validator ──────────────────────────────────────────

class TestReplayValidator:
    def test_validate_determinism(self):
        from core.stabilization.stabilization_replay_validator_v1 import StabilizationReplayValidator
        v = StabilizationReplayValidator()
        result = v.validate_determinism("check_1", "input", "output")
        assert result["deterministic"] is True
        assert result["replay_id"].startswith("srplay-")

    def test_validate_pair_same(self):
        from core.stabilization.stabilization_replay_validator_v1 import StabilizationReplayValidator
        v = StabilizationReplayValidator()
        result = v.validate_replay_pair("check_1", "input", "output", "output")
        assert result["deterministic"] is True

    def test_validate_pair_different(self):
        from core.stabilization.stabilization_replay_validator_v1 import StabilizationReplayValidator
        v = StabilizationReplayValidator()
        result = v.validate_replay_pair("check_1", "input", "output_a", "output_b")
        assert result["deterministic"] is False

    def test_all_deterministic_empty(self):
        from core.stabilization.stabilization_replay_validator_v1 import StabilizationReplayValidator
        v = StabilizationReplayValidator()
        assert v.all_deterministic() is True

    def test_all_deterministic_mixed(self):
        from core.stabilization.stabilization_replay_validator_v1 import StabilizationReplayValidator
        v = StabilizationReplayValidator()
        v.validate_determinism("c1", "i", "o")
        v.validate_replay_pair("c2", "i", "a", "b")
        assert v.all_deterministic() is False

    def test_known_checks_exist(self):
        from core.stabilization.stabilization_replay_validator_v1 import REPLAY_CHECKS
        assert len(REPLAY_CHECKS) == 6
        assert "concurrency_durability" in REPLAY_CHECKS
        assert "governance_validation" in REPLAY_CHECKS

    def test_stats(self):
        from core.stabilization.stabilization_replay_validator_v1 import StabilizationReplayValidator
        v = StabilizationReplayValidator()
        v.validate_determinism("c1", "i", "o")
        stats = v.get_stats()
        assert stats["total_checks"] == 1
        assert stats["deterministic"] == 1


# ── Boundary Policies ────────────────────────────────────────

class TestBoundaryPolicies:
    def test_default_limits(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies, STABILIZATION_LIMITS
        bp = StabilizationBoundaryPolicies()
        limits = bp.get_limits()
        assert limits == STABILIZATION_LIMITS

    def test_check_not_exceeded(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies()
        result = bp.check_limit("max_concurrent_validations", 10)
        assert result["exceeded"] is False

    def test_check_exceeded(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies()
        result = bp.check_limit("max_concurrent_validations", 50)
        assert result["exceeded"] is True

    def test_override_capping(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies(overrides={"max_concurrent_validations": 999})
        limits = bp.get_limits()
        assert limits["max_concurrent_validations"] == 50

    def test_override_lower(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies(overrides={"max_concurrent_validations": 10})
        limits = bp.get_limits()
        assert limits["max_concurrent_validations"] == 10

    def test_is_forbidden(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies()
        assert bp.is_forbidden("autonomous_execution") is True
        assert bp.is_forbidden("valid_action") is False

    def test_forbidden_actions_count(self):
        from core.stabilization.stabilization_boundary_policies_v1 import FORBIDDEN_STABILIZATION_ACTIONS
        assert len(FORBIDDEN_STABILIZATION_ACTIONS) == 8

    def test_limits_count(self):
        from core.stabilization.stabilization_boundary_policies_v1 import STABILIZATION_LIMITS
        assert len(STABILIZATION_LIMITS) == 8

    def test_exceeded_checks(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies()
        bp.check_limit("max_concurrent_validations", 10)
        bp.check_limit("max_concurrent_validations", 999)
        exceeded = bp.get_exceeded_checks()
        assert len(exceeded) == 1

    def test_all_checks(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies()
        bp.check_limit("max_concurrent_validations", 10)
        assert len(bp.get_all_checks()) == 1

    def test_stats(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies()
        stats = bp.get_stats()
        assert stats["total_limits"] == 8
        assert stats["total_forbidden"] == 8

    def test_unknown_limit_returns_zero_max(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies()
        result = bp.check_limit("nonexistent_limit", 1)
        assert result["max_value"] == 0
        assert result["exceeded"] is True

    def test_override_ignored_for_unknown_key(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies(overrides={"fake_key": 999})
        limits = bp.get_limits()
        assert "fake_key" not in limits

    def test_all_forbidden_actions_are_strings(self):
        from core.stabilization.stabilization_boundary_policies_v1 import FORBIDDEN_STABILIZATION_ACTIONS
        for action in FORBIDDEN_STABILIZATION_ACTIONS:
            assert isinstance(action, str)

    def test_governance_bypass_forbidden(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies()
        assert bp.is_forbidden("governance_bypass") is True

    def test_execution_outside_spine_forbidden(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies()
        assert bp.is_forbidden("execution_outside_spine") is True

    def test_recursive_stabilization_forbidden(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies()
        assert bp.is_forbidden("recursive_stabilization") is True


# ── Continuity Bridges ────────────────────────────────────────

class TestContinuityBridges:
    def test_all_bridges_count(self):
        from core.stabilization.stabilization_continuity_bridges_v1 import ALL_BRIDGE_CLASSES
        assert len(ALL_BRIDGE_CLASSES) == 9

    def test_concurrency_bridge(self):
        from core.stabilization.stabilization_continuity_bridges_v1 import ConcurrencyStabilizationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = ConcurrencyStabilizationBridge(state_dir=td)
            record = bridge.record("validate", {"ops": 10})
            assert record["bridge"] == "concurrency_stabilization"

    def test_replay_bridge(self):
        from core.stabilization.stabilization_continuity_bridges_v1 import ReplayStabilizationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = ReplayStabilizationBridge(state_dir=td)
            record = bridge.record("validate")
            assert record["bridge"] == "replay_stabilization"

    def test_continuity_bridge(self):
        from core.stabilization.stabilization_continuity_bridges_v1 import ContinuityStabilizationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = ContinuityStabilizationBridge(state_dir=td)
            record = bridge.record("validate")
            assert record["bridge"] == "continuity_stabilization"

    def test_topology_bridge(self):
        from core.stabilization.stabilization_continuity_bridges_v1 import TopologyStabilizationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = TopologyStabilizationBridge(state_dir=td)
            record = bridge.record("validate")
            assert record["bridge"] == "topology_stabilization"

    def test_resilience_bridge(self):
        from core.stabilization.stabilization_continuity_bridges_v1 import ResilienceStabilizationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = ResilienceStabilizationBridge(state_dir=td)
            record = bridge.record("validate")
            assert record["bridge"] == "resilience_stabilization"

    def test_governance_bridge(self):
        from core.stabilization.stabilization_continuity_bridges_v1 import GovernanceStabilizationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = GovernanceStabilizationBridge(state_dir=td)
            record = bridge.record("validate")
            assert record["bridge"] == "governance_stabilization"

    def test_jsonl_persistence(self):
        from core.stabilization.stabilization_continuity_bridges_v1 import ConcurrencyStabilizationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = ConcurrencyStabilizationBridge(state_dir=td)
            bridge.record("test_action")
            filepath = os.path.join(td, "concurrency_stabilization.jsonl")
            assert os.path.exists(filepath)

    def test_get_records(self):
        from core.stabilization.stabilization_continuity_bridges_v1 import ConcurrencyStabilizationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = ConcurrencyStabilizationBridge(state_dir=td)
            bridge.record("a1")
            bridge.record("a2")
            assert len(bridge.get_records()) == 2

    def test_bridge_stats(self):
        from core.stabilization.stabilization_continuity_bridges_v1 import ConcurrencyStabilizationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = ConcurrencyStabilizationBridge(state_dir=td)
            bridge.record("a1")
            stats = bridge.get_stats()
            assert stats["bridge_name"] == "concurrency_stabilization"
            assert stats["total_records"] == 1

    def test_deployment_orchestration_observability_bridges(self):
        from core.stabilization.stabilization_continuity_bridges_v1 import (
            DeploymentStabilizationBridge,
            OrchestrationStabilizationBridge,
            ObservabilityStabilizationBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            for cls, name in [
                (DeploymentStabilizationBridge, "deployment_stabilization"),
                (OrchestrationStabilizationBridge, "orchestration_stabilization"),
                (ObservabilityStabilizationBridge, "observability_stabilization"),
            ]:
                bridge = cls(state_dir=td)
                record = bridge.record("validate")
                assert record["bridge"] == name


# ── Coordinator ───────────────────────────────────────────────

class TestCoordinator:
    def _make_coordinator(self, td):
        from core.stabilization.canonical_operational_fabric_stabilization_coordinator_v1 import (
            CanonicalOperationalFabricStabilizationCoordinator,
        )
        return CanonicalOperationalFabricStabilizationCoordinator(state_dir=td)

    def test_create_scenario(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            sc = coord.create_scenario("test", "concurrency")
            assert sc["name"] == "test"
            assert sc["scenario_id"].startswith("stab-")

    def test_start_and_complete_run(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            run = coord.start_run("run-001")
            assert run["status"] == "started"
            receipt = coord.complete_run("run-001", outcome="stable", domains_validated=5)
            assert receipt["outcome"] == "stable"
            assert receipt["receipt_id"].startswith("frcpt-")

    def test_validate_concurrency(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.validate_concurrency(10)
            assert result["durable"] is True

    def test_validate_replay_durability(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.validate_replay_durability(5)
            assert result["durable"] is True

    def test_validate_continuity_durability(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.validate_continuity_durability(3, checkpoints_restored=2)
            assert result["durable"] is True

    def test_validate_topology_durability(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.validate_topology_durability(4)
            assert result["durable"] is True

    def test_validate_resilience(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.validate_resilience(5)
            assert result["durable"] is True

    def test_validate_replay_determinism(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.validate_replay_determinism("check_1", "input", "output")
            assert result["deterministic"] is True

    def test_check_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.check_boundary("max_concurrent_validations", 10)
            assert result["exceeded"] is False

    def test_durability_report_all_durable(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.validate_concurrency(10)
            coord.validate_replay_durability(5)
            coord.validate_continuity_durability(3)
            coord.validate_topology_durability(4)
            coord.validate_resilience(3)
            report = coord.get_durability_report()
            assert report["all_durable"] is True

    def test_durability_report_not_all_durable(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.validate_concurrency(10, all_deterministic=False)
            report = coord.get_durability_report()
            assert report["all_durable"] is False

    def test_max_scenarios(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            for i in range(100):
                coord.create_scenario(f"sc_{i}", "concurrency")
            with pytest.raises(ValueError, match="Max scenarios"):
                coord.create_scenario("overflow", "concurrency")

    def test_max_runs(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            for i in range(50):
                coord.start_run(f"run-{i}")
                coord.complete_run(f"run-{i}")
            with pytest.raises(ValueError, match="Max stabilization runs"):
                coord.start_run("overflow")

    def test_stats(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.create_scenario("test", "concurrency")
            coord.start_run("run-001")
            coord.complete_run("run-001")
            stats = coord.get_stats()
            assert "lifecycle" in stats
            assert "concurrency" in stats
            assert "replay" in stats
            assert "continuity" in stats
            assert "topology" in stats
            assert "resilience" in stats
            assert stats["scenarios"] == 1
            assert stats["receipts"] == 1


# ── Constraint Verification ──────────────────────────────────

class TestConstraintVerification:
    def test_concurrency_durability_proven(self):
        from core.stabilization.concurrency_durability_engine_v1 import ConcurrencyDurabilityEngine
        engine = ConcurrencyDurabilityEngine()
        engine.validate_concurrency(10)
        engine.validate_concurrency(20)
        assert engine.all_durable() is True

    def test_concurrency_failure_detected(self):
        from core.stabilization.concurrency_durability_engine_v1 import ConcurrencyDurabilityEngine
        engine = ConcurrencyDurabilityEngine()
        engine.validate_concurrency(10, all_deterministic=False)
        assert engine.all_durable() is False

    def test_replay_durability_proven(self):
        from core.stabilization.replay_durability_engine_v1 import ReplayDurabilityEngine
        engine = ReplayDurabilityEngine()
        engine.validate_replay_durability(5)
        assert engine.all_durable() is True

    def test_continuity_durability_proven(self):
        from core.stabilization.continuity_durability_engine_v1 import ContinuityDurabilityEngine
        engine = ContinuityDurabilityEngine()
        engine.validate_continuity_durability(3, checkpoints_restored=2)
        assert engine.all_durable() is True

    def test_topology_durability_proven(self):
        from core.stabilization.topology_durability_engine_v1 import TopologyDurabilityEngine
        engine = TopologyDurabilityEngine()
        engine.validate_topology_durability(4)
        assert engine.all_durable() is True

    def test_resilience_durability_proven(self):
        from core.stabilization.resilience_interaction_engine_v1 import ResilienceInteractionEngine
        engine = ResilienceInteractionEngine()
        engine.validate_resilience(5)
        assert engine.all_durable() is True

    def test_no_governance_bypass(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies()
        assert bp.is_forbidden("governance_bypass") is True

    def test_no_execution_outside_spine(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies()
        assert bp.is_forbidden("execution_outside_spine") is True

    def test_no_recursive_stabilization(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies()
        assert bp.is_forbidden("recursive_stabilization") is True

    def test_no_autonomous_topology_mutation(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies
        bp = StabilizationBoundaryPolicies()
        assert bp.is_forbidden("autonomous_topology_mutation") is True

    def test_override_capping_enforced(self):
        from core.stabilization.stabilization_boundary_policies_v1 import StabilizationBoundaryPolicies, STABILIZATION_LIMITS
        bp = StabilizationBoundaryPolicies(overrides={k: 9999 for k in STABILIZATION_LIMITS})
        for key, default in STABILIZATION_LIMITS.items():
            assert bp.get_limits()[key] == default

    def test_lifecycle_linear_progression(self):
        from core.stabilization.stabilization_lifecycle_engine_v1 import StabilizationLifecycleEngine, VALID_TRANSITIONS
        for source, targets in VALID_TRANSITIONS.items():
            assert len(targets) <= 1

    def test_lifecycle_terminal_absorbing(self):
        from core.stabilization.stabilization_lifecycle_engine_v1 import StabilizationLifecycleEngine
        engine = StabilizationLifecycleEngine()
        for p in ["staged", "stressed", "validated", "hardened", "archived"]:
            engine.transition(p)
        assert engine.is_terminal is True
        with pytest.raises(ValueError):
            engine.transition("defined")

    def test_replay_determinism_stable(self):
        from core.stabilization.stabilization_replay_validator_v1 import StabilizationReplayValidator
        v = StabilizationReplayValidator()
        v.validate_replay_pair("test", "input", "output", "output")
        assert v.all_deterministic() is True

    def test_full_durability_report(self):
        with tempfile.TemporaryDirectory() as td:
            from core.stabilization.canonical_operational_fabric_stabilization_coordinator_v1 import (
                CanonicalOperationalFabricStabilizationCoordinator,
            )
            coord = CanonicalOperationalFabricStabilizationCoordinator(state_dir=td)
            coord.validate_concurrency(10)
            coord.validate_replay_durability(5)
            coord.validate_continuity_durability(3)
            coord.validate_topology_durability(4)
            coord.validate_resilience(3)
            report = coord.get_durability_report()
            assert report["all_durable"] is True
            assert report["concurrency"]["all_durable"] is True
            assert report["replay"]["all_durable"] is True
            assert report["continuity"]["all_durable"] is True
            assert report["topology"]["all_durable"] is True
            assert report["resilience"]["all_durable"] is True

    def test_8_durability_domains(self):
        from core.stabilization.constitutional_operational_fabric_contracts_v1 import DurabilityDomain
        assert len(DurabilityDomain) == 8

    def test_coordinator_cannot_mutate_silently(self):
        with tempfile.TemporaryDirectory() as td:
            from core.stabilization.canonical_operational_fabric_stabilization_coordinator_v1 import (
                CanonicalOperationalFabricStabilizationCoordinator,
            )
            coord = CanonicalOperationalFabricStabilizationCoordinator(state_dir=td)
            assert not hasattr(coord, "mutate_topology")
            assert not hasattr(coord, "execute")
            assert not hasattr(coord, "deploy")
            assert not hasattr(coord, "scale")
