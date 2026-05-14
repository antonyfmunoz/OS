"""Tests for Phase 96.8CJ — Substrate Sovereign Operational Validation.

Tests: contracts, enums, lifecycle, governance assault, replay durability,
continuity corruption, topology stress, semantic drift, sovereign integrity,
runtime pressure, observability pipeline, replay validator, boundary policies,
continuity bridges, coordinator, constraint verification.
"""

import os
import json
import tempfile
import pytest

from core.validation.sovereign_operational_validation_contracts_v1 import (
    SovereignValidationPhase,
    SovereignValidationEventType,
    AttackDomain,
    PressureDomain,
    AttackOutcome,
    SovereignValidationState,
    AdversarialScenarioState,
    GovernanceAttackState,
    ReplayAttackState,
    ContinuityAttackState,
    TopologyAttackState,
    SemanticAttackState,
    RuntimePressureState,
    ValidationBoundaryState,
    SovereignIntegrityState,
    ConstitutionalDurabilityState,
    RuntimeStressState,
    ValidationReplayState,
    ValidationObservabilityState,
    SovereignValidationReceipt,
    _now_iso,
    _deterministic_id,
)
from core.validation.sovereign_validation_lifecycle_engine_v1 import (
    SovereignValidationLifecycleEngine,
    VALID_TRANSITIONS,
    TERMINAL_STATES,
)
from core.validation.governance_assault_engine_v1 import (
    GovernanceAssaultEngine,
    GOVERNANCE_ATTACK_TYPES,
    MAX_ATTACKS,
)
from core.validation.replay_durability_engine_v1 import (
    SovereignReplayDurabilityEngine,
    REPLAY_ATTACK_TYPES,
    MAX_REPLAY_ATTACKS,
)
from core.validation.continuity_corruption_engine_v1 import (
    ContinuityCorruptionEngine,
    CONTINUITY_ATTACK_TYPES,
    MAX_CONTINUITY_ATTACKS,
)
from core.validation.topology_stress_engine_v1 import (
    TopologyStressEngine,
    TOPOLOGY_ATTACK_TYPES,
    MAX_TOPOLOGY_ATTACKS,
)
from core.validation.semantic_drift_assault_engine_v1 import (
    SemanticDriftAssaultEngine,
    SEMANTIC_ATTACK_TYPES,
    MAX_SEMANTIC_ATTACKS,
)
from core.validation.sovereign_integrity_engine_v1 import (
    SovereignIntegrityEngine,
    INTEGRITY_DIMENSIONS,
    MAX_INTEGRITY_CHECKS,
)
from core.validation.runtime_pressure_engine_v1 import (
    RuntimePressureEngine,
    PRESSURE_DOMAINS,
    MAX_PRESSURE_SIMULATIONS,
)
from core.validation.sovereign_validation_observability_pipeline_v1 import (
    SovereignValidationObservabilityPipeline,
    EVENT_FILE_MAP,
)
from core.validation.sovereign_validation_replay_validator_v1 import (
    SovereignValidationReplayValidator,
    REPLAY_CHECKS,
)
from core.validation.sovereign_validation_boundary_policies_v1 import (
    SovereignValidationBoundaryPolicies,
    SOVEREIGN_VALIDATION_LIMITS,
    FORBIDDEN_VALIDATION_ACTIONS,
)
from core.validation.sovereign_validation_continuity_bridges_v1 import (
    _BaseBridge,
    GovernanceValidationBridge,
    ReplayValidationBridge,
    ContinuityValidationBridge,
    TopologyValidationBridge,
    ResilienceValidationBridge,
    DeploymentValidationBridge,
    StabilizationValidationBridge,
    CertificationValidationBridge,
    IntelligenceValidationBridge,
    ALL_BRIDGE_CLASSES,
)
from core.validation.canonical_sovereign_validation_coordinator_v1 import (
    CanonicalSovereignValidationCoordinator,
    MAX_VALIDATION_RUNS,
)


# ── TestContracts ──────────────────────────────────────────


class TestContracts:
    def test_sovereign_validation_state(self):
        s = SovereignValidationState(run_id="r1")
        d = s.to_dict()
        assert d["run_id"] == "r1"
        assert d["validation_id"].startswith("sval-")

    def test_adversarial_scenario_state(self):
        s = AdversarialScenarioState(scenario_name="test", domain="governance")
        d = s.to_dict()
        assert d["scenario_name"] == "test"
        assert d["scenario_id"].startswith("advsc-")
        assert d["outcome"] == "blocked"

    def test_governance_attack_state(self):
        s = GovernanceAttackState(attack_type="bypass")
        d = s.to_dict()
        assert d["attack_type"] == "bypass"
        assert d["blocked"] is True
        assert d["attack_id"].startswith("gatk-")

    def test_replay_attack_state(self):
        s = ReplayAttackState(attack_type="corruption")
        d = s.to_dict()
        assert d["attack_type"] == "corruption"
        assert d["determinism_preserved"] is True
        assert d["attack_id"].startswith("ratk-")

    def test_continuity_attack_state(self):
        s = ContinuityAttackState(attack_type="checkpoint")
        d = s.to_dict()
        assert d["continuity_preserved"] is True
        assert d["attack_id"].startswith("catk-")

    def test_topology_attack_state(self):
        s = TopologyAttackState(attack_type="expansion")
        d = s.to_dict()
        assert d["topology_preserved"] is True
        assert d["attack_id"].startswith("tatk-")

    def test_semantic_attack_state(self):
        s = SemanticAttackState(attack_type="drift")
        d = s.to_dict()
        assert d["consistency_preserved"] is True
        assert d["attack_id"].startswith("satk-")

    def test_runtime_pressure_state(self):
        s = RuntimePressureState(domain="concurrency", pressure_level=80)
        d = s.to_dict()
        assert d["domain"] == "concurrency"
        assert d["pressure_level"] == 80
        assert d["bounded"] is True
        assert d["pressure_id"].startswith("rpres-")

    def test_validation_boundary_state(self):
        s = ValidationBoundaryState(limit_name="max_attacks", current_value=50, max_value=100)
        d = s.to_dict()
        assert d["exceeded"] is False
        assert d["boundary_id"].startswith("vbnd-")

    def test_sovereign_integrity_state(self):
        s = SovereignIntegrityState()
        d = s.to_dict()
        assert d["sovereign_integrity_score"] == 1.0
        assert d["integrity_id"].startswith("sint-")

    def test_sovereign_integrity_partial(self):
        s = SovereignIntegrityState(governance_integrity=False, replay_integrity=False)
        assert s.sovereign_integrity_score == 5 / 7

    def test_constitutional_durability_state(self):
        s = ConstitutionalDurabilityState(domain="governance", attacks_survived=10, attacks_total=10)
        d = s.to_dict()
        assert d["durable"] is True
        assert d["durability_id"].startswith("cdur-")

    def test_runtime_stress_state(self):
        s = RuntimeStressState(stress_type="concurrency", intensity=90)
        d = s.to_dict()
        assert d["survived"] is True
        assert d["stress_id"].startswith("rstrs-")

    def test_validation_replay_state(self):
        s = ValidationReplayState(check_name="test_check")
        d = s.to_dict()
        assert d["deterministic"] is True
        assert d["replay_id"].startswith("vrplay-")

    def test_validation_observability_state(self):
        s = ValidationObservabilityState(events_emitted=42)
        d = s.to_dict()
        assert d["all_persisted"] is True
        assert d["observability_id"].startswith("vobs-")

    def test_sovereign_validation_receipt(self):
        s = SovereignValidationReceipt(run_id="r1", outcome="sovereign", attacks_blocked=20)
        d = s.to_dict()
        assert d["outcome"] == "sovereign"
        assert d["receipt_id"].startswith("svrcpt-")


# ── TestEnums ──────────────────────────────────────────────


class TestEnums:
    def test_sovereign_validation_phase_count(self):
        assert len(SovereignValidationPhase) == 6

    def test_sovereign_validation_event_type_count(self):
        assert len(SovereignValidationEventType) == 9

    def test_attack_domain_count(self):
        assert len(AttackDomain) == 8

    def test_pressure_domain_count(self):
        assert len(PressureDomain) == 7

    def test_attack_outcome_count(self):
        assert len(AttackOutcome) == 4

    def test_attack_outcome_values(self):
        assert AttackOutcome.BLOCKED.value == "blocked"
        assert AttackOutcome.BREACHED.value == "breached"

    def test_deterministic_id(self):
        a = _deterministic_id("t-", "x", "y")
        b = _deterministic_id("t-", "x", "y")
        assert a == b
        assert a.startswith("t-")


# ── TestLifecycleEngine ───────────────────────────────────


class TestLifecycleEngine:
    def test_initial_phase(self):
        e = SovereignValidationLifecycleEngine()
        assert e.current_phase == "defined"

    def test_linear_progression(self):
        e = SovereignValidationLifecycleEngine()
        e.transition("staged")
        e.transition("validating")
        e.transition("stressed")
        e.transition("verified")
        e.transition("archived")
        assert e.current_phase == "archived"
        assert e.is_terminal

    def test_invalid_transition(self):
        e = SovereignValidationLifecycleEngine()
        with pytest.raises(ValueError):
            e.transition("archived")

    def test_terminal_no_transition(self):
        e = SovereignValidationLifecycleEngine()
        e.transition("staged")
        e.transition("validating")
        e.transition("stressed")
        e.transition("verified")
        e.transition("archived")
        with pytest.raises(ValueError):
            e.transition("defined")

    def test_history_tracking(self):
        e = SovereignValidationLifecycleEngine()
        e.transition("staged")
        e.transition("validating")
        h = e.get_history()
        assert len(h) == 2
        assert h[0]["from"] == "defined"
        assert h[0]["to"] == "staged"

    def test_can_transition(self):
        e = SovereignValidationLifecycleEngine()
        assert e.can_transition("staged") is True
        assert e.can_transition("archived") is False

    def test_stats(self):
        e = SovereignValidationLifecycleEngine()
        e.transition("staged")
        s = e.get_stats()
        assert s["current_phase"] == "staged"
        assert s["transitions"] == 1

    def test_six_valid_transitions_defined(self):
        assert len(VALID_TRANSITIONS) == 6

    def test_terminal_states(self):
        assert TERMINAL_STATES == {"archived"}


# ── TestGovernanceAssaultEngine ───────────────────────────


class TestGovernanceAssaultEngine:
    def test_simulate_single_attack(self):
        e = GovernanceAssaultEngine()
        r = e.simulate_attack("governance_bypass_attempt")
        assert r["blocked"] is True

    def test_simulate_all_attacks(self):
        e = GovernanceAssaultEngine()
        r = e.simulate_all_attacks()
        assert r["all_blocked"] is True
        assert r["total"] == 8

    def test_all_blocked_empty(self):
        e = GovernanceAssaultEngine()
        assert e.all_blocked() is True

    def test_breached_attack(self):
        e = GovernanceAssaultEngine()
        e.simulate_attack("test", blocked=False)
        assert e.all_blocked() is False
        assert len(e.get_breached()) == 1

    def test_max_attacks(self):
        e = GovernanceAssaultEngine()
        for i in range(MAX_ATTACKS):
            e.simulate_attack(f"atk-{i}")
        with pytest.raises(ValueError):
            e.simulate_attack("overflow")

    def test_attack_types_count(self):
        assert len(GOVERNANCE_ATTACK_TYPES) == 8

    def test_stats(self):
        e = GovernanceAssaultEngine()
        e.simulate_all_attacks()
        s = e.get_stats()
        assert s["total_attacks"] == 8
        assert s["blocked"] == 8
        assert s["breached"] == 0


# ── TestReplayDurabilityEngine ────────────────────────────


class TestReplayDurabilityEngine:
    def test_simulate_single(self):
        e = SovereignReplayDurabilityEngine()
        r = e.simulate_attack("replay_concurrency_pressure")
        assert r["determinism_preserved"] is True

    def test_simulate_all(self):
        e = SovereignReplayDurabilityEngine()
        r = e.simulate_all_attacks()
        assert r["all_preserved"] is True
        assert r["total"] == 5

    def test_all_preserved_empty(self):
        e = SovereignReplayDurabilityEngine()
        assert e.all_preserved() is True

    def test_broken_determinism(self):
        e = SovereignReplayDurabilityEngine()
        e.simulate_attack("test", determinism_preserved=False)
        assert e.all_preserved() is False

    def test_max_attacks(self):
        e = SovereignReplayDurabilityEngine()
        for i in range(MAX_REPLAY_ATTACKS):
            e.simulate_attack(f"atk-{i}")
        with pytest.raises(ValueError):
            e.simulate_attack("overflow")

    def test_attack_types_count(self):
        assert len(REPLAY_ATTACK_TYPES) == 5

    def test_stats(self):
        e = SovereignReplayDurabilityEngine()
        e.simulate_all_attacks()
        s = e.get_stats()
        assert s["total_attacks"] == 5
        assert s["preserved"] == 5


# ── TestContinuityCorruptionEngine ────────────────────────


class TestContinuityCorruptionEngine:
    def test_simulate_single(self):
        e = ContinuityCorruptionEngine()
        r = e.simulate_attack("checkpoint_corruption_attempt")
        assert r["continuity_preserved"] is True

    def test_simulate_all(self):
        e = ContinuityCorruptionEngine()
        r = e.simulate_all_attacks()
        assert r["all_preserved"] is True
        assert r["total"] == 6

    def test_all_preserved_empty(self):
        e = ContinuityCorruptionEngine()
        assert e.all_preserved() is True

    def test_corrupted(self):
        e = ContinuityCorruptionEngine()
        e.simulate_attack("test", continuity_preserved=False)
        assert e.all_preserved() is False
        assert len(e.get_corrupted()) == 1

    def test_max_attacks(self):
        e = ContinuityCorruptionEngine()
        for i in range(MAX_CONTINUITY_ATTACKS):
            e.simulate_attack(f"atk-{i}")
        with pytest.raises(ValueError):
            e.simulate_attack("overflow")

    def test_attack_types_count(self):
        assert len(CONTINUITY_ATTACK_TYPES) == 6

    def test_stats(self):
        e = ContinuityCorruptionEngine()
        e.simulate_all_attacks()
        s = e.get_stats()
        assert s["total_attacks"] == 6
        assert s["preserved"] == 6
        assert s["corrupted"] == 0


# ── TestTopologyStressEngine ──────────────────────────────


class TestTopologyStressEngine:
    def test_simulate_single(self):
        e = TopologyStressEngine()
        r = e.simulate_attack("hidden_topology_expansion_attempt")
        assert r["topology_preserved"] is True

    def test_simulate_all(self):
        e = TopologyStressEngine()
        r = e.simulate_all_attacks()
        assert r["all_preserved"] is True
        assert r["total"] == 5

    def test_all_preserved_empty(self):
        e = TopologyStressEngine()
        assert e.all_preserved() is True

    def test_breached(self):
        e = TopologyStressEngine()
        e.simulate_attack("test", topology_preserved=False)
        assert e.all_preserved() is False
        assert len(e.get_breached()) == 1

    def test_max_attacks(self):
        e = TopologyStressEngine()
        for i in range(MAX_TOPOLOGY_ATTACKS):
            e.simulate_attack(f"atk-{i}")
        with pytest.raises(ValueError):
            e.simulate_attack("overflow")

    def test_attack_types_count(self):
        assert len(TOPOLOGY_ATTACK_TYPES) == 5

    def test_stats(self):
        e = TopologyStressEngine()
        e.simulate_all_attacks()
        s = e.get_stats()
        assert s["total_attacks"] == 5
        assert s["preserved"] == 5


# ── TestSemanticDriftAssaultEngine ────────────────────────


class TestSemanticDriftAssaultEngine:
    def test_simulate_single(self):
        e = SemanticDriftAssaultEngine()
        r = e.simulate_attack("definition_mutation_attempt")
        assert r["consistency_preserved"] is True

    def test_simulate_all(self):
        e = SemanticDriftAssaultEngine()
        r = e.simulate_all_attacks()
        assert r["all_preserved"] is True
        assert r["total"] == 5

    def test_all_preserved_empty(self):
        e = SemanticDriftAssaultEngine()
        assert e.all_preserved() is True

    def test_drifted(self):
        e = SemanticDriftAssaultEngine()
        e.simulate_attack("test", consistency_preserved=False)
        assert e.all_preserved() is False
        assert len(e.get_drifted()) == 1

    def test_max_attacks(self):
        e = SemanticDriftAssaultEngine()
        for i in range(MAX_SEMANTIC_ATTACKS):
            e.simulate_attack(f"atk-{i}")
        with pytest.raises(ValueError):
            e.simulate_attack("overflow")

    def test_attack_types_count(self):
        assert len(SEMANTIC_ATTACK_TYPES) == 5

    def test_stats(self):
        e = SemanticDriftAssaultEngine()
        e.simulate_all_attacks()
        s = e.get_stats()
        assert s["total_attacks"] == 5
        assert s["preserved"] == 5
        assert s["drifted"] == 0


# ── TestSovereignIntegrityEngine ──────────────────────────


class TestSovereignIntegrityEngine:
    def test_compute_full(self):
        e = SovereignIntegrityEngine()
        r = e.compute_full_integrity()
        assert r["sovereign_integrity_score"] == 1.0

    def test_compute_partial(self):
        e = SovereignIntegrityEngine()
        r = e.compute_integrity(governance_integrity=False)
        assert r["sovereign_integrity_score"] == 6 / 7

    def test_all_sovereign_empty(self):
        e = SovereignIntegrityEngine()
        assert e.all_sovereign() is True

    def test_compromised(self):
        e = SovereignIntegrityEngine()
        e.compute_integrity(governance_integrity=False)
        assert e.all_sovereign() is False
        assert len(e.get_compromised()) == 1

    def test_max_checks(self):
        e = SovereignIntegrityEngine()
        for _ in range(MAX_INTEGRITY_CHECKS):
            e.compute_full_integrity()
        with pytest.raises(ValueError):
            e.compute_full_integrity()

    def test_dimensions_count(self):
        assert len(INTEGRITY_DIMENSIONS) == 7

    def test_stats(self):
        e = SovereignIntegrityEngine()
        e.compute_full_integrity()
        s = e.get_stats()
        assert s["total_checks"] == 1
        assert s["all_sovereign"] is True
        assert s["min_score"] == 1.0


# ── TestRuntimePressureEngine ─────────────────────────────


class TestRuntimePressureEngine:
    def test_apply_single(self):
        e = RuntimePressureEngine()
        r = e.apply_pressure("concurrency", 80)
        assert r["bounded"] is True
        assert r["pressure_level"] == 80

    def test_apply_all(self):
        e = RuntimePressureEngine()
        r = e.apply_all_pressures(75)
        assert r["all_bounded"] is True
        assert r["total"] == 7

    def test_all_bounded_empty(self):
        e = RuntimePressureEngine()
        assert e.all_bounded() is True

    def test_unbounded(self):
        e = RuntimePressureEngine()
        e.apply_pressure("test", 100, bounded=False)
        assert e.all_bounded() is False
        assert len(e.get_unbounded()) == 1

    def test_max_pressures(self):
        e = RuntimePressureEngine()
        for i in range(MAX_PRESSURE_SIMULATIONS):
            e.apply_pressure(f"d-{i}")
        with pytest.raises(ValueError):
            e.apply_pressure("overflow")

    def test_domains_count(self):
        assert len(PRESSURE_DOMAINS) == 7

    def test_stats(self):
        e = RuntimePressureEngine()
        e.apply_all_pressures(60)
        s = e.get_stats()
        assert s["total_pressures"] == 7
        assert s["all_bounded"] is True
        assert s["max_pressure"] == 60


# ── TestObservabilityPipeline ─────────────────────────────


class TestObservabilityPipeline:
    def test_emit_validation_started(self):
        p = SovereignValidationObservabilityPipeline()
        e = p.emit_validation_started({"run_id": "r1"})
        assert e["event_type"] == "validation_started"

    def test_emit_adversarial_scenario_started(self):
        p = SovereignValidationObservabilityPipeline()
        e = p.emit_adversarial_scenario_started()
        assert e["event_type"] == "adversarial_scenario_started"

    def test_emit_governance_attack_detected(self):
        p = SovereignValidationObservabilityPipeline()
        e = p.emit_governance_attack_detected()
        assert e["event_type"] == "governance_attack_detected"

    def test_emit_replay_attack_detected(self):
        p = SovereignValidationObservabilityPipeline()
        e = p.emit_replay_attack_detected()
        assert e["event_type"] == "replay_attack_detected"

    def test_emit_continuity_attack_detected(self):
        p = SovereignValidationObservabilityPipeline()
        e = p.emit_continuity_attack_detected()
        assert e["event_type"] == "continuity_attack_detected"

    def test_emit_topology_pressure_detected(self):
        p = SovereignValidationObservabilityPipeline()
        e = p.emit_topology_pressure_detected()
        assert e["event_type"] == "topology_pressure_detected"

    def test_emit_semantic_drift_detected(self):
        p = SovereignValidationObservabilityPipeline()
        e = p.emit_semantic_drift_detected()
        assert e["event_type"] == "semantic_drift_detected"

    def test_emit_sovereign_integrity_computed(self):
        p = SovereignValidationObservabilityPipeline()
        e = p.emit_sovereign_integrity_computed()
        assert e["event_type"] == "sovereign_integrity_computed"

    def test_emit_validation_completed(self):
        p = SovereignValidationObservabilityPipeline()
        e = p.emit_validation_completed()
        assert e["event_type"] == "validation_completed"

    def test_event_file_map(self):
        assert len(EVENT_FILE_MAP) == 9
        for k, v in EVENT_FILE_MAP.items():
            assert v.endswith(".jsonl")

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            p = SovereignValidationObservabilityPipeline(output_dir=td)
            p.emit_validation_started({"run_id": "r1"})
            path = os.path.join(td, "validation_started.jsonl")
            assert os.path.exists(path)
            with open(path) as f:
                line = json.loads(f.readline())
            assert line["event_type"] == "validation_started"

    def test_get_events_by_type(self):
        p = SovereignValidationObservabilityPipeline()
        p.emit_validation_started()
        p.emit_validation_completed()
        p.emit_validation_started()
        starts = p.get_events_by_type("validation_started")
        assert len(starts) == 2

    def test_stats(self):
        p = SovereignValidationObservabilityPipeline()
        p.emit_validation_started()
        p.emit_validation_completed()
        s = p.get_stats()
        assert s["total_events"] == 2
        assert s["all_persisted"] is True


# ── TestReplayValidator ───────────────────────────────────


class TestReplayValidator:
    def test_validate_single(self):
        v = SovereignValidationReplayValidator()
        r = v.validate_replay("test", "in", "out")
        assert r["deterministic"] is True

    def test_validate_all(self):
        v = SovereignValidationReplayValidator()
        r = v.validate_all()
        assert r["all_deterministic"] is True
        assert r["total"] == 7

    def test_all_deterministic_empty(self):
        v = SovereignValidationReplayValidator()
        assert v.all_deterministic() is True

    def test_replay_checks_count(self):
        assert len(REPLAY_CHECKS) == 7

    def test_stats(self):
        v = SovereignValidationReplayValidator()
        v.validate_all()
        s = v.get_stats()
        assert s["total_checks"] == 7
        assert s["deterministic"] == 7

    def test_deterministic_hashing(self):
        v = SovereignValidationReplayValidator()
        r1 = v.validate_replay("c", "same_input", "same_output")
        r2 = v.validate_replay("c", "same_input", "same_output")
        assert r1["input_hash"] == r2["input_hash"]
        assert r1["output_hash"] == r2["output_hash"]


# ── TestBoundaryPolicies ─────────────────────────────────


class TestBoundaryPolicies:
    def test_check_within_limit(self):
        bp = SovereignValidationBoundaryPolicies()
        r = bp.check_limit("max_governance_attacks", 50)
        assert r["exceeded"] is False

    def test_check_exceeded(self):
        bp = SovereignValidationBoundaryPolicies()
        r = bp.check_limit("max_governance_attacks", 101)
        assert r["exceeded"] is True

    def test_override_capping(self):
        bp = SovereignValidationBoundaryPolicies()
        r = bp.check_limit("max_governance_attacks", 60, override=200)
        assert r["max_value"] == 100
        assert r["exceeded"] is False

    def test_override_lower(self):
        bp = SovereignValidationBoundaryPolicies()
        r = bp.check_limit("max_governance_attacks", 60, override=50)
        assert r["max_value"] == 50
        assert r["exceeded"] is True

    def test_forbidden_action(self):
        bp = SovereignValidationBoundaryPolicies()
        assert bp.is_forbidden("autonomous_adaptation") is True
        assert bp.is_forbidden("allowed_action") is False

    def test_check_all_limits(self):
        bp = SovereignValidationBoundaryPolicies()
        vals = {k: 0 for k in SOVEREIGN_VALIDATION_LIMITS}
        r = bp.check_all_limits(vals)
        assert r["any_exceeded"] is False
        assert r["total"] == 8

    def test_limits_count(self):
        assert len(SOVEREIGN_VALIDATION_LIMITS) == 8

    def test_forbidden_count(self):
        assert len(FORBIDDEN_VALIDATION_ACTIONS) == 8

    def test_get_exceeded(self):
        bp = SovereignValidationBoundaryPolicies()
        bp.check_limit("max_governance_attacks", 200)
        assert len(bp.get_exceeded()) == 1

    def test_stats(self):
        bp = SovereignValidationBoundaryPolicies()
        bp.check_limit("max_governance_attacks", 50)
        s = bp.get_stats()
        assert s["total_checks"] == 1
        assert s["exceeded"] == 0

    def test_all_forbidden_actions_listed(self):
        expected = [
            "autonomous_adaptation",
            "autonomous_healing",
            "autonomous_defense",
            "governance_bypass",
            "replay_bypass",
            "observability_bypass",
            "execution_outside_spine",
            "recursive_validation",
        ]
        assert FORBIDDEN_VALIDATION_ACTIONS == expected

    def test_unknown_limit(self):
        bp = SovereignValidationBoundaryPolicies()
        r = bp.check_limit("nonexistent_limit", 1)
        assert r["max_value"] == 0
        assert r["exceeded"] is True

    def test_boundary_at_exact_limit(self):
        bp = SovereignValidationBoundaryPolicies()
        r = bp.check_limit("max_governance_attacks", 100)
        assert r["exceeded"] is False

    def test_boundary_one_over(self):
        bp = SovereignValidationBoundaryPolicies()
        r = bp.check_limit("max_governance_attacks", 101)
        assert r["exceeded"] is True

    def test_override_equal_default(self):
        bp = SovereignValidationBoundaryPolicies()
        r = bp.check_limit("max_governance_attacks", 50, override=100)
        assert r["max_value"] == 100
        assert r["exceeded"] is False

    def test_override_zero(self):
        bp = SovereignValidationBoundaryPolicies()
        r = bp.check_limit("max_governance_attacks", 1, override=0)
        assert r["max_value"] == 0
        assert r["exceeded"] is True


# ── TestContinuityBridges ────────────────────────────────


class TestContinuityBridges:
    def test_bridge_count(self):
        assert len(ALL_BRIDGE_CLASSES) == 9

    def test_bridge_names(self):
        with tempfile.TemporaryDirectory() as td:
            names = []
            for cls in ALL_BRIDGE_CLASSES:
                b = cls(state_dir=td)
                names.append(b._bridge_name)
            assert "governance_validation" in names
            assert "replay_validation" in names
            assert "continuity_validation" in names
            assert "topology_validation" in names
            assert "intelligence_validation" in names

    def test_record_and_retrieve(self):
        with tempfile.TemporaryDirectory() as td:
            b = GovernanceValidationBridge(state_dir=td)
            r = b.record("test_action", {"key": "value"})
            assert r["bridge"] == "governance_validation"
            assert r["action"] == "test_action"
            assert r["key"] == "value"

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            b = ReplayValidationBridge(state_dir=td)
            b.record("test_persist")
            path = os.path.join(td, "replay_validation.jsonl")
            assert os.path.exists(path)

    def test_stats(self):
        with tempfile.TemporaryDirectory() as td:
            b = ContinuityValidationBridge(state_dir=td)
            b.record("a1")
            b.record("a2")
            s = b.get_stats()
            assert s["total_records"] == 2

    def test_get_records(self):
        with tempfile.TemporaryDirectory() as td:
            b = TopologyValidationBridge(state_dir=td)
            b.record("r1")
            b.record("r2")
            b.record("r3")
            assert len(b.get_records()) == 3

    def test_all_bridges_instantiate(self):
        with tempfile.TemporaryDirectory() as td:
            for cls in ALL_BRIDGE_CLASSES:
                b = cls(state_dir=td)
                assert b._bridge_name != ""

    def test_certification_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = CertificationValidationBridge(state_dir=td)
            r = b.record("certify")
            assert r["bridge"] == "certification_validation"

    def test_stabilization_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = StabilizationValidationBridge(state_dir=td)
            r = b.record("stabilize")
            assert r["bridge"] == "stabilization_validation"

    def test_intelligence_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = IntelligenceValidationBridge(state_dir=td)
            r = b.record("intel")
            assert r["bridge"] == "intelligence_validation"


# ── TestCoordinator ──────────────────────────────────────


class TestCoordinator:
    def test_start_validation(self):
        c = CanonicalSovereignValidationCoordinator()
        r = c.start_validation("test-run")
        assert r["run_id"] == "test-run"
        assert r["status"] == "started"

    def test_assault_governance(self):
        c = CanonicalSovereignValidationCoordinator()
        r = c.assault_governance()
        assert r["all_blocked"] is True
        assert r["total"] == 8

    def test_assault_replay(self):
        c = CanonicalSovereignValidationCoordinator()
        r = c.assault_replay()
        assert r["all_preserved"] is True
        assert r["total"] == 5

    def test_assault_continuity(self):
        c = CanonicalSovereignValidationCoordinator()
        r = c.assault_continuity()
        assert r["all_preserved"] is True
        assert r["total"] == 6

    def test_assault_topology(self):
        c = CanonicalSovereignValidationCoordinator()
        r = c.assault_topology()
        assert r["all_preserved"] is True
        assert r["total"] == 5

    def test_assault_semantics(self):
        c = CanonicalSovereignValidationCoordinator()
        r = c.assault_semantics()
        assert r["all_preserved"] is True
        assert r["total"] == 5

    def test_compute_sovereign_integrity(self):
        c = CanonicalSovereignValidationCoordinator()
        c.assault_governance()
        c.assault_replay()
        c.assault_continuity()
        c.assault_topology()
        r = c.compute_sovereign_integrity()
        assert r["sovereign_integrity_score"] == 1.0

    def test_apply_runtime_pressure(self):
        c = CanonicalSovereignValidationCoordinator()
        r = c.apply_runtime_pressure(80)
        assert r["all_bounded"] is True
        assert r["total"] == 7

    def test_validate_replay_determinism(self):
        c = CanonicalSovereignValidationCoordinator()
        r = c.validate_replay_determinism()
        assert r["all_deterministic"] is True

    def test_check_boundary(self):
        c = CanonicalSovereignValidationCoordinator()
        r = c.check_boundary("max_governance_attacks", 50)
        assert r["exceeded"] is False

    def test_complete_validation_sovereign(self):
        c = CanonicalSovereignValidationCoordinator()
        c.start_validation("r1")
        c.assault_governance()
        c.assault_replay()
        c.assault_continuity()
        c.assault_topology()
        c.assault_semantics()
        c.compute_sovereign_integrity()
        c.apply_runtime_pressure()
        c.validate_replay_determinism()
        r = c.complete_validation("r1")
        assert r["outcome"] == "sovereign"

    def test_get_sovereign_report(self):
        c = CanonicalSovereignValidationCoordinator()
        c.assault_governance()
        c.assault_replay()
        c.assault_continuity()
        c.assault_topology()
        c.assault_semantics()
        c.compute_sovereign_integrity()
        c.apply_runtime_pressure()
        r = c.get_sovereign_report()
        assert r["all_sovereign"] is True

    def test_get_stats(self):
        c = CanonicalSovereignValidationCoordinator()
        s = c.get_stats()
        assert "lifecycle" in s
        assert "governance" in s
        assert "replay" in s
        assert s["runs"] == 0

    def test_max_validation_runs(self):
        c = CanonicalSovereignValidationCoordinator()
        for i in range(MAX_VALIDATION_RUNS):
            c.start_validation(f"r-{i}")
        with pytest.raises(ValueError):
            c.start_validation("overflow")

    def test_auto_run_id(self):
        c = CanonicalSovereignValidationCoordinator()
        r = c.start_validation()
        assert r["run_id"].startswith("svrun-")

    def test_full_adversarial_flow(self):
        c = CanonicalSovereignValidationCoordinator()
        c.start_validation("full-flow")
        g = c.assault_governance()
        assert g["all_blocked"] is True
        rp = c.assault_replay()
        assert rp["all_preserved"] is True
        ct = c.assault_continuity()
        assert ct["all_preserved"] is True
        tp = c.assault_topology()
        assert tp["all_preserved"] is True
        sm = c.assault_semantics()
        assert sm["all_preserved"] is True
        si = c.compute_sovereign_integrity()
        assert si["sovereign_integrity_score"] == 1.0
        pr = c.apply_runtime_pressure(90)
        assert pr["all_bounded"] is True
        rv = c.validate_replay_determinism()
        assert rv["all_deterministic"] is True
        receipt = c.complete_validation("full-flow")
        assert receipt["outcome"] == "sovereign"
        report = c.get_sovereign_report()
        assert report["all_sovereign"] is True


# ── TestConstraintVerification ───────────────────────────


class TestConstraintVerification:
    def test_governance_assault_blocks_all(self):
        e = GovernanceAssaultEngine()
        r = e.simulate_all_attacks()
        assert r["all_blocked"] is True

    def test_replay_durability_preserves_all(self):
        e = SovereignReplayDurabilityEngine()
        r = e.simulate_all_attacks()
        assert r["all_preserved"] is True

    def test_continuity_corruption_preserves_all(self):
        e = ContinuityCorruptionEngine()
        r = e.simulate_all_attacks()
        assert r["all_preserved"] is True

    def test_topology_stress_preserves_all(self):
        e = TopologyStressEngine()
        r = e.simulate_all_attacks()
        assert r["all_preserved"] is True

    def test_semantic_drift_preserves_all(self):
        e = SemanticDriftAssaultEngine()
        r = e.simulate_all_attacks()
        assert r["all_preserved"] is True

    def test_sovereign_integrity_full(self):
        e = SovereignIntegrityEngine()
        r = e.compute_full_integrity()
        assert r["sovereign_integrity_score"] == 1.0

    def test_runtime_pressure_all_bounded(self):
        e = RuntimePressureEngine()
        r = e.apply_all_pressures()
        assert r["all_bounded"] is True

    def test_replay_determinism_all(self):
        v = SovereignValidationReplayValidator()
        r = v.validate_all()
        assert r["all_deterministic"] is True

    def test_lifecycle_linear_progression(self):
        e = SovereignValidationLifecycleEngine()
        phases = ["staged", "validating", "stressed", "verified", "archived"]
        for p in phases:
            e.transition(p)
        assert e.is_terminal

    def test_lifecycle_terminal_absorbing(self):
        e = SovereignValidationLifecycleEngine()
        for p in ["staged", "validating", "stressed", "verified", "archived"]:
            e.transition(p)
        with pytest.raises(ValueError):
            e.transition("defined")

    def test_no_autonomous_adaptation(self):
        bp = SovereignValidationBoundaryPolicies()
        assert bp.is_forbidden("autonomous_adaptation") is True

    def test_no_autonomous_healing(self):
        bp = SovereignValidationBoundaryPolicies()
        assert bp.is_forbidden("autonomous_healing") is True

    def test_no_autonomous_defense(self):
        bp = SovereignValidationBoundaryPolicies()
        assert bp.is_forbidden("autonomous_defense") is True

    def test_no_governance_bypass(self):
        bp = SovereignValidationBoundaryPolicies()
        assert bp.is_forbidden("governance_bypass") is True

    def test_no_execution_outside_spine(self):
        bp = SovereignValidationBoundaryPolicies()
        assert bp.is_forbidden("execution_outside_spine") is True

    def test_no_recursive_validation(self):
        bp = SovereignValidationBoundaryPolicies()
        assert bp.is_forbidden("recursive_validation") is True

    def test_override_capping_enforced(self):
        bp = SovereignValidationBoundaryPolicies()
        r = bp.check_limit("max_governance_attacks", 60, override=200)
        assert r["max_value"] == 100

    def test_coordinator_cannot_adapt_heal_defend(self):
        c = CanonicalSovereignValidationCoordinator()
        assert not hasattr(c, "adapt")
        assert not hasattr(c, "heal")
        assert not hasattr(c, "defend")

    def test_8_attack_domains_defined(self):
        assert len(AttackDomain) == 8

    def test_full_sovereign_validation_flow(self):
        c = CanonicalSovereignValidationCoordinator()
        c.start_validation("constraint-flow")
        c.assault_governance()
        c.assault_replay()
        c.assault_continuity()
        c.assault_topology()
        c.assault_semantics()
        c.compute_sovereign_integrity()
        c.apply_runtime_pressure()
        c.validate_replay_determinism()
        receipt = c.complete_validation("constraint-flow")
        assert receipt["outcome"] == "sovereign"
        report = c.get_sovereign_report()
        assert report["all_sovereign"] is True
