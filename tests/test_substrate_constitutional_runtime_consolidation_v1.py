"""Tests for Phase 96.8CG — Substrate Constitutional Runtime Consolidation.

Verifies: contracts, enums, lifecycle, invariants, unified replay,
unified lifecycle, unified topology, unified continuity, unified
observability, constitutional observability, replay validator,
boundary policies, continuity bridges, coordinator, constraints.
"""

import hashlib
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, "/opt/OS")

from core.constitutional.constitutional_runtime_contracts_v1 import (
    ConstitutionalInvariant,
    RuntimeConstitutionState,
    UnifiedGovernanceState,
    UnifiedReplayState,
    UnifiedContinuityState,
    UnifiedTopologyState,
    UnifiedLifecycleState,
    UnifiedObservabilityState,
    UnifiedBoundaryState,
    UnifiedTrustState,
    ConstitutionalReceipt,
    ConstitutionalReplayState,
    ConstitutionalViolationState,
    ConstitutionalProofState,
    RuntimeCoherenceState,
    ConstitutionalPhase,
    ConstitutionalEventType,
    InvariantDomain,
    SemanticDriftType,
    ViolationSeverity,
)
from core.constitutional.constitutional_lifecycle_engine_v1 import (
    ConstitutionalLifecycleEngine,
    VALID_TRANSITIONS,
    TERMINAL_STATES,
)
from core.constitutional.invariant_consolidation_engine_v1 import (
    InvariantConsolidationEngine,
    CONSOLIDATED_INVARIANTS,
    MAX_INVARIANTS,
)
from core.constitutional.unified_replay_semantics_engine_v1 import (
    UnifiedReplaySemanticsEngine,
    KNOWN_REPLAY_LAYERS,
    REPLAY_CHECKS as REPLAY_SEMANTIC_CHECKS,
)
from core.constitutional.unified_lifecycle_semantics_engine_v1 import (
    UnifiedLifecycleSemanticsEngine,
    KNOWN_LIFECYCLE_LAYERS,
    LIFECYCLE_SEMANTICS,
)
from core.constitutional.unified_topology_semantics_engine_v1 import (
    UnifiedTopologySemanticsEngine,
    KNOWN_TOPOLOGY_DOMAINS,
)
from core.constitutional.unified_continuity_semantics_engine_v1 import (
    UnifiedContinuitySemanticsEngine,
    KNOWN_CONTINUITY_LAYERS,
)
from core.constitutional.unified_observability_semantics_engine_v1 import (
    UnifiedObservabilitySemanticsEngine,
    KNOWN_OBSERVABILITY_LAYERS,
    OBSERVABILITY_SEMANTICS,
)
from core.constitutional.constitutional_observability_pipeline_v1 import (
    ConstitutionalObservabilityPipeline,
    EVENT_FILE_MAP,
)
from core.constitutional.constitutional_replay_validator_v1 import (
    ConstitutionalReplayValidator,
    REPLAY_CHECKS,
)
from core.constitutional.constitutional_boundary_policies_v1 import (
    CONSTITUTIONAL_LIMITS,
    FORBIDDEN_CONSTITUTIONAL_ACTIONS,
    enforce_limit,
    is_forbidden,
    get_all_limits,
    get_all_forbidden,
    validate_boundaries,
)
from core.constitutional.constitutional_continuity_bridges_v1 import (
    ALL_BRIDGES,
    GovernanceConstitutionalBridge,
    ReplayConstitutionalBridge,
    ContinuityConstitutionalBridge,
    TopologyConstitutionalBridge,
    ObservabilityConstitutionalBridge,
    DeploymentConstitutionalBridge,
    ApplicationsConstitutionalBridge,
    CognitionConstitutionalBridge,
    OrchestrationConstitutionalBridge,
)
from core.constitutional.canonical_constitutional_runtime_coordinator_v1 import (
    CanonicalConstitutionalRuntimeCoordinator,
)


# ── Contracts ──────────────────────────────────────────────


class TestContracts:
    def test_constitutional_invariant(self):
        inv = ConstitutionalInvariant(domain="governance", name="operator_required")
        d = inv.to_dict()
        assert d["invariant_id"].startswith("cinv-")
        assert d["enforced"] is True

    def test_runtime_constitution_state(self):
        s = RuntimeConstitutionState()
        d = s.to_dict()
        assert d["state_id"].startswith("rcst-")

    def test_unified_governance_state(self):
        g = UnifiedGovernanceState(layers_validated=5)
        d = g.to_dict()
        assert d["governance_id"].startswith("ugov-")

    def test_unified_replay_state(self):
        r = UnifiedReplayState(checks_passed=10)
        d = r.to_dict()
        assert d["replay_id"].startswith("ureplay-")

    def test_unified_continuity_state(self):
        c = UnifiedContinuityState(layers_synchronized=3)
        d = c.to_dict()
        assert d["continuity_id"].startswith("ucont-")

    def test_unified_topology_state(self):
        t = UnifiedTopologyState(topologies_validated=4)
        d = t.to_dict()
        assert d["topology_id"].startswith("utopo-")

    def test_unified_lifecycle_state(self):
        l = UnifiedLifecycleState(layers_validated=6)
        d = l.to_dict()
        assert d["lifecycle_id"].startswith("ulife-")

    def test_unified_observability_state(self):
        o = UnifiedObservabilityState(pipelines_validated=5)
        d = o.to_dict()
        assert d["observability_id"].startswith("uobs-")

    def test_unified_boundary_state(self):
        b = UnifiedBoundaryState(policies_validated=3)
        d = b.to_dict()
        assert d["boundary_id"].startswith("ubnd-")

    def test_unified_trust_state(self):
        t = UnifiedTrustState(trust_tiers_validated=4)
        d = t.to_dict()
        assert d["trust_id"].startswith("utrust-")

    def test_constitutional_receipt(self):
        r = ConstitutionalReceipt(action="validate_invariants")
        d = r.to_dict()
        assert d["receipt_id"].startswith("crcpt-")

    def test_constitutional_replay_state(self):
        s = ConstitutionalReplayState(check_name="test")
        d = s.to_dict()
        assert d["replay_id"].startswith("crplay-")

    def test_constitutional_violation_state(self):
        v = ConstitutionalViolationState(
            invariant_id="cinv-abc", domain="governance",
        )
        d = v.to_dict()
        assert d["violation_id"].startswith("cviol-")

    def test_constitutional_proof_state(self):
        p = ConstitutionalProofState(domain="governance")
        d = p.to_dict()
        assert d["proof_id"].startswith("cproof-")

    def test_runtime_coherence_state(self):
        c = RuntimeCoherenceState(layers_checked=5, coherent=True)
        d = c.to_dict()
        assert d["coherence_id"].startswith("rcoher-")

    def test_all_contracts_have_to_dict(self):
        classes = [
            ConstitutionalInvariant, RuntimeConstitutionState,
            UnifiedGovernanceState, UnifiedReplayState,
            UnifiedContinuityState, UnifiedTopologyState,
            UnifiedLifecycleState, UnifiedObservabilityState,
            UnifiedBoundaryState, UnifiedTrustState,
            ConstitutionalReceipt, ConstitutionalReplayState,
            ConstitutionalViolationState, ConstitutionalProofState,
            RuntimeCoherenceState,
        ]
        assert len(classes) == 15
        for cls in classes:
            assert hasattr(cls, "to_dict")


# ── Enums ──────────────────────────────────────────────────


class TestEnums:
    def test_constitutional_phases_count(self):
        assert len(ConstitutionalPhase) == 7

    def test_event_types_count(self):
        assert len(ConstitutionalEventType) == 7

    def test_invariant_domains_count(self):
        assert len(InvariantDomain) == 8

    def test_drift_types_count(self):
        assert len(SemanticDriftType) == 6

    def test_violation_severity_count(self):
        assert len(ViolationSeverity) == 3

    def test_phase_values(self):
        values = {p.value for p in ConstitutionalPhase}
        assert "defined" in values
        assert "archived" in values
        assert "consolidated" in values
        assert "hardened" in values

    def test_domain_values(self):
        values = {d.value for d in InvariantDomain}
        assert "governance" in values
        assert "replay" in values
        assert "resilience" in values


# ── Lifecycle Engine ───────────────────────────────────────


class TestLifecycleEngine:
    def test_initial_phase(self):
        le = ConstitutionalLifecycleEngine()
        assert le.current_phase == "defined"

    def test_valid_transition(self):
        le = ConstitutionalLifecycleEngine()
        result = le.transition("validated")
        assert result["from"] == "defined"
        assert result["to"] == "validated"

    def test_invalid_transition_raises(self):
        le = ConstitutionalLifecycleEngine()
        with pytest.raises(ValueError):
            le.transition("archived")

    def test_unknown_phase_raises(self):
        le = ConstitutionalLifecycleEngine()
        with pytest.raises(ValueError):
            le.transition("nonexistent")

    def test_full_lifecycle(self):
        le = ConstitutionalLifecycleEngine()
        for phase in ["validated", "consolidated", "hardened",
                       "verified", "operational", "archived"]:
            le.transition(phase)
        assert le.current_phase == "archived"
        assert le.is_terminal()

    def test_terminal_states_set(self):
        assert TERMINAL_STATES == {"archived"}

    def test_all_phases_covered(self):
        all_phases = {p.value for p in ConstitutionalPhase}
        transition_phases = set(VALID_TRANSITIONS.keys())
        assert all_phases == transition_phases

    def test_stats(self):
        le = ConstitutionalLifecycleEngine()
        le.transition("validated")
        stats = le.get_stats()
        assert stats["current_phase"] == "validated"
        assert stats["total_transitions"] == 1


# ── Invariant Consolidation Engine ─────────────────────────


class TestInvariantConsolidationEngine:
    def test_consolidated_invariants_loaded(self):
        ie = InvariantConsolidationEngine()
        assert len(ie.get_all_invariants()) == 18

    def test_consolidated_invariants_count(self):
        assert len(CONSOLIDATED_INVARIANTS) == 18

    def test_all_domains_covered(self):
        ie = InvariantConsolidationEngine()
        domains = {i["domain"] for i in ie.get_all_invariants()}
        assert "governance" in domains
        assert "replay" in domains
        assert "continuity" in domains
        assert "lifecycle" in domains
        assert "topology" in domains
        assert "observability" in domains
        assert "scaling" in domains
        assert "resilience" in domains

    def test_validate_domain(self):
        ie = InvariantConsolidationEngine()
        result = ie.validate_domain("governance")
        assert result["invariant_count"] == 3
        assert result["all_enforced"] is True

    def test_validate_all(self):
        ie = InvariantConsolidationEngine()
        result = ie.validate_all()
        assert result["total_invariants"] == 18
        assert result["all_enforced"] is True

    def test_register_new_invariant(self):
        ie = InvariantConsolidationEngine()
        inv = ie.register_invariant("governance", "new_rule", "test")
        assert inv is not None
        assert len(ie.get_all_invariants()) == 19

    def test_register_duplicate_returns_existing(self):
        ie = InvariantConsolidationEngine()
        inv = ie.register_invariant("governance", "operator_approval_required")
        assert inv is not None
        assert len(ie.get_all_invariants()) == 18

    def test_unknown_domain_rejected(self):
        ie = InvariantConsolidationEngine()
        assert ie.register_invariant("nonexistent", "test") is None

    def test_stats(self):
        ie = InvariantConsolidationEngine()
        stats = ie.get_stats()
        assert stats["total_invariants"] == 18
        assert stats["domains_covered"] == 8
        assert stats["all_enforced"] is True


# ── Unified Replay Semantics Engine ────────────────────────


class TestUnifiedReplaySemanticsEngine:
    def test_known_layers_count(self):
        assert len(KNOWN_REPLAY_LAYERS) == 18

    def test_validate_layer_replay(self):
        re = UnifiedReplaySemanticsEngine()
        result = re.validate_layer_replay("spine", "in", "out")
        assert result["deterministic"] is True

    def test_unknown_layer_raises(self):
        re = UnifiedReplaySemanticsEngine()
        with pytest.raises(ValueError):
            re.validate_layer_replay("nonexistent", "in", "out")

    def test_cross_layer_coherence_same(self):
        re = UnifiedReplaySemanticsEngine()
        result = re.validate_cross_layer_coherence(
            "spine", "workstation", "input", "same", "same",
        )
        assert result["deterministic"] is True

    def test_cross_layer_coherence_different(self):
        re = UnifiedReplaySemanticsEngine()
        result = re.validate_cross_layer_coherence(
            "spine", "workstation", "input", "out_a", "out_b",
        )
        assert result["deterministic"] is False

    def test_validate_determinism(self):
        re = UnifiedReplaySemanticsEngine()
        result = re.validate_determinism("cross_layer_coherence", "in", "out")
        assert result["deterministic"] is True

    def test_unknown_check_raises(self):
        re = UnifiedReplaySemanticsEngine()
        with pytest.raises(ValueError):
            re.validate_determinism("nonexistent", "in", "out")

    def test_unified_state(self):
        re = UnifiedReplaySemanticsEngine()
        re.validate_layer_replay("spine", "in", "out")
        state = re.get_unified_state()
        assert state.deterministic is True
        assert state.checks_passed == 1

    def test_stats(self):
        re = UnifiedReplaySemanticsEngine()
        re.validate_layer_replay("spine", "in", "out")
        stats = re.get_stats()
        assert stats["layers_validated"] == 1
        assert stats["total_checks"] == 1


# ── Unified Lifecycle Semantics Engine ─────────────────────


class TestUnifiedLifecycleSemanticsEngine:
    def test_known_layers_count(self):
        assert len(KNOWN_LIFECYCLE_LAYERS) == 19

    def test_validate_layer_coherent(self):
        le = UnifiedLifecycleSemanticsEngine()
        result = le.validate_layer_lifecycle("spine")
        assert result["coherent"] is True

    def test_validate_layer_incoherent(self):
        le = UnifiedLifecycleSemanticsEngine()
        result = le.validate_layer_lifecycle(
            "spine", terminal_absorbing=False,
        )
        assert result["coherent"] is False

    def test_unknown_layer_raises(self):
        le = UnifiedLifecycleSemanticsEngine()
        with pytest.raises(ValueError):
            le.validate_layer_lifecycle("nonexistent")

    def test_unified_state_coherent(self):
        le = UnifiedLifecycleSemanticsEngine()
        le.validate_layer_lifecycle("spine")
        state = le.get_unified_state()
        assert state.lifecycle_coherent is True

    def test_incoherent_layers_detected(self):
        le = UnifiedLifecycleSemanticsEngine()
        le.validate_layer_lifecycle("spine")
        le.validate_layer_lifecycle("workstation", terminal_absorbing=False)
        incoherent = le.get_incoherent_layers()
        assert "workstation" in incoherent
        assert "spine" not in incoherent

    def test_lifecycle_semantics_defined(self):
        assert len(LIFECYCLE_SEMANTICS) == 5

    def test_stats(self):
        le = UnifiedLifecycleSemanticsEngine()
        le.validate_layer_lifecycle("spine")
        stats = le.get_stats()
        assert stats["layers_validated"] == 1


# ── Unified Topology Semantics Engine ──────────────────────


class TestUnifiedTopologySemanticsEngine:
    def test_known_domains_count(self):
        assert len(KNOWN_TOPOLOGY_DOMAINS) == 5

    def test_register_topology(self):
        te = UnifiedTopologySemanticsEngine()
        result = te.register_topology("environment", "hash123")
        assert result["baseline_match"] is True

    def test_unknown_domain_raises(self):
        te = UnifiedTopologySemanticsEngine()
        with pytest.raises(ValueError):
            te.register_topology("nonexistent", "hash")

    def test_drift_detection(self):
        te = UnifiedTopologySemanticsEngine()
        te.register_topology("environment", "hash1")
        te.register_topology("environment", "hash2")
        assert te.detect_drift("environment") is True

    def test_no_drift_at_baseline(self):
        te = UnifiedTopologySemanticsEngine()
        te.register_topology("environment", "hash1")
        assert te.detect_drift("environment") is False

    def test_unified_hash_deterministic(self):
        te1 = UnifiedTopologySemanticsEngine()
        te2 = UnifiedTopologySemanticsEngine()
        for te in [te1, te2]:
            te.register_topology("environment", "h1")
            te.register_topology("application", "h2")
        assert te1.get_unified_hash() == te2.get_unified_hash()

    def test_update_baseline(self):
        te = UnifiedTopologySemanticsEngine()
        te.register_topology("environment", "hash1")
        te.register_topology("environment", "hash2")
        assert te.detect_drift("environment") is True
        te.update_baseline("environment")
        assert te.detect_drift("environment") is False

    def test_unified_state(self):
        te = UnifiedTopologySemanticsEngine()
        te.register_topology("environment", "hash1")
        state = te.get_unified_state()
        assert state.topology_coherent is True

    def test_stats(self):
        te = UnifiedTopologySemanticsEngine()
        te.register_topology("environment", "hash1")
        stats = te.get_stats()
        assert stats["domains_registered"] == 1


# ── Unified Continuity Semantics Engine ────────────────────


class TestUnifiedContinuitySemanticsEngine:
    def test_known_layers_count(self):
        assert len(KNOWN_CONTINUITY_LAYERS) == 6

    def test_validate_coherent(self):
        ce = UnifiedContinuitySemanticsEngine()
        result = ce.validate_layer_continuity("session")
        assert result["coherent"] is True

    def test_validate_incoherent(self):
        ce = UnifiedContinuitySemanticsEngine()
        result = ce.validate_layer_continuity(
            "session", lineage_preserved=False,
        )
        assert result["coherent"] is False

    def test_unknown_layer_raises(self):
        ce = UnifiedContinuitySemanticsEngine()
        with pytest.raises(ValueError):
            ce.validate_layer_continuity("nonexistent")

    def test_unified_state(self):
        ce = UnifiedContinuitySemanticsEngine()
        ce.validate_layer_continuity("session")
        state = ce.get_unified_state()
        assert state.continuity_coherent is True

    def test_incoherent_detected(self):
        ce = UnifiedContinuitySemanticsEngine()
        ce.validate_layer_continuity("session")
        ce.validate_layer_continuity("workflow", restoration_verified=False)
        incoherent = ce.get_incoherent_layers()
        assert "workflow" in incoherent

    def test_stats(self):
        ce = UnifiedContinuitySemanticsEngine()
        ce.validate_layer_continuity("session")
        stats = ce.get_stats()
        assert stats["layers_validated"] == 1


# ── Unified Observability Semantics Engine ─────────────────


class TestUnifiedObservabilitySemanticsEngine:
    def test_known_layers_count(self):
        assert len(KNOWN_OBSERVABILITY_LAYERS) == 18

    def test_validate_coherent(self):
        oe = UnifiedObservabilitySemanticsEngine()
        result = oe.validate_layer_observability("spine")
        assert result["coherent"] is True

    def test_validate_incoherent(self):
        oe = UnifiedObservabilitySemanticsEngine()
        result = oe.validate_layer_observability(
            "spine", events_persisted=False,
        )
        assert result["coherent"] is False

    def test_unknown_layer_raises(self):
        oe = UnifiedObservabilitySemanticsEngine()
        with pytest.raises(ValueError):
            oe.validate_layer_observability("nonexistent")

    def test_unified_state(self):
        oe = UnifiedObservabilitySemanticsEngine()
        oe.validate_layer_observability("spine")
        state = oe.get_unified_state()
        assert state.observability_coherent is True

    def test_observability_semantics_defined(self):
        assert len(OBSERVABILITY_SEMANTICS) == 5

    def test_stats(self):
        oe = UnifiedObservabilitySemanticsEngine()
        oe.validate_layer_observability("spine")
        stats = oe.get_stats()
        assert stats["layers_validated"] == 1


# ── Constitutional Observability Pipeline ──────────────────


class TestConstitutionalObservabilityPipeline:
    def test_event_file_map_count(self):
        assert len(EVENT_FILE_MAP) == 7

    def test_event_file_map_matches_enum(self):
        enum_values = {e.value for e in ConstitutionalEventType}
        assert enum_values == set(EVENT_FILE_MAP.keys())

    def test_emit_invariant_validated(self):
        obs = ConstitutionalObservabilityPipeline(state_dir=tempfile.mkdtemp())
        event = obs.emit_invariant_validated(invariant_id="cinv-1", domain="governance")
        assert event["event_type"] == "invariant_validated"

    def test_emit_invariant_violated(self):
        obs = ConstitutionalObservabilityPipeline(state_dir=tempfile.mkdtemp())
        event = obs.emit_invariant_violated(
            invariant_id="cinv-1", domain="governance",
        )
        assert event["event_type"] == "invariant_violated"

    def test_emit_replay_semantics(self):
        obs = ConstitutionalObservabilityPipeline(state_dir=tempfile.mkdtemp())
        event = obs.emit_replay_semantics_validated(layers_checked=5)
        assert event["event_type"] == "replay_semantics_validated"

    def test_emit_lifecycle_semantics(self):
        obs = ConstitutionalObservabilityPipeline(state_dir=tempfile.mkdtemp())
        event = obs.emit_lifecycle_semantics_validated(layers_checked=3)
        assert event["event_type"] == "lifecycle_semantics_validated"

    def test_emit_topology_semantics(self):
        obs = ConstitutionalObservabilityPipeline(state_dir=tempfile.mkdtemp())
        event = obs.emit_topology_semantics_validated(domains_checked=4)
        assert event["event_type"] == "topology_semantics_validated"

    def test_emit_continuity_semantics(self):
        obs = ConstitutionalObservabilityPipeline(state_dir=tempfile.mkdtemp())
        event = obs.emit_continuity_semantics_validated(layers_checked=6)
        assert event["event_type"] == "continuity_semantics_validated"

    def test_emit_constitutional_replay(self):
        obs = ConstitutionalObservabilityPipeline(state_dir=tempfile.mkdtemp())
        event = obs.emit_constitutional_replay_validated(checks_passed=6)
        assert event["event_type"] == "constitutional_replay_validated"

    def test_events_written_to_file(self):
        d = tempfile.mkdtemp()
        obs = ConstitutionalObservabilityPipeline(state_dir=d)
        obs.emit_invariant_validated(invariant_id="cinv-1", domain="governance")
        path = Path(d) / "invariant_validated.jsonl"
        assert path.exists()

    def test_stats(self):
        obs = ConstitutionalObservabilityPipeline(state_dir=tempfile.mkdtemp())
        obs.emit_invariant_validated(invariant_id="cinv-1", domain="governance")
        assert obs.get_stats()["total_events"] == 1


# ── Constitutional Replay Validator ────────────────────────


class TestReplayValidator:
    def test_replay_checks_count(self):
        assert len(REPLAY_CHECKS) == 6

    def test_validate_determinism(self):
        rv = ConstitutionalReplayValidator()
        result = rv.validate_determinism("invariant_validation", "in", "out")
        assert result["deterministic"] is True

    def test_unknown_check_rejected(self):
        rv = ConstitutionalReplayValidator()
        with pytest.raises(ValueError):
            rv.validate_determinism("nonexistent", "in", "out")

    def test_replay_pair_same(self):
        rv = ConstitutionalReplayValidator()
        result = rv.validate_replay_pair(
            "governance_coherence", "in", "same", "same",
        )
        assert result["deterministic"] is True

    def test_replay_pair_different(self):
        rv = ConstitutionalReplayValidator()
        result = rv.validate_replay_pair(
            "governance_coherence", "in", "out_a", "out_b",
        )
        assert result["deterministic"] is False

    def test_all_checks_valid(self):
        rv = ConstitutionalReplayValidator()
        for check in REPLAY_CHECKS:
            result = rv.validate_determinism(check, "input", "output")
            assert result["deterministic"] is True

    def test_stats(self):
        rv = ConstitutionalReplayValidator()
        rv.validate_determinism("invariant_validation", "in", "out")
        stats = rv.get_stats()
        assert stats["total_checks"] == 1
        assert stats["deterministic_count"] == 1


# ── Boundary Policies ─────────────────────────────────────


class TestBoundaryPolicies:
    def test_limits_count(self):
        assert len(CONSTITUTIONAL_LIMITS) == 8

    def test_forbidden_count(self):
        assert len(FORBIDDEN_CONSTITUTIONAL_ACTIONS) == 8

    def test_enforce_limit_default(self):
        assert enforce_limit("max_invariants") == 100

    def test_enforce_limit_override_lower(self):
        assert enforce_limit("max_invariants", 50) == 50

    def test_enforce_limit_override_higher_capped(self):
        assert enforce_limit("max_invariants", 200) == 100

    def test_enforce_limit_unknown_raises(self):
        with pytest.raises(ValueError):
            enforce_limit("nonexistent")

    def test_subsystem_semantic_drift_forbidden(self):
        assert is_forbidden("subsystem_semantic_drift")

    def test_replay_semantic_drift_forbidden(self):
        assert is_forbidden("replay_semantic_drift")

    def test_lifecycle_semantic_drift_forbidden(self):
        assert is_forbidden("lifecycle_semantic_drift")

    def test_topology_semantic_drift_forbidden(self):
        assert is_forbidden("topology_semantic_drift")

    def test_continuity_semantic_drift_forbidden(self):
        assert is_forbidden("continuity_semantic_drift")

    def test_observability_semantic_drift_forbidden(self):
        assert is_forbidden("observability_semantic_drift")

    def test_governance_bypass_forbidden(self):
        assert is_forbidden("governance_bypass")

    def test_execution_outside_spine_forbidden(self):
        assert is_forbidden("execution_outside_spine")

    def test_safe_action_not_forbidden(self):
        assert is_forbidden("validate_invariants") is False

    def test_override_capping(self):
        for name, default in CONSTITUTIONAL_LIMITS.items():
            assert enforce_limit(name, default + 10) == default
            assert enforce_limit(name, max(1, default - 1)) == max(1, default - 1)

    def test_validate_boundaries(self):
        result = validate_boundaries()
        assert result["limits_count"] == 8
        assert result["forbidden_count"] == 8


# ── Continuity Bridges ─────────────────────────────────────


class TestContinuityBridges:
    def test_all_bridges_count(self):
        assert len(ALL_BRIDGES) == 9

    def test_governance_bridge(self):
        b = GovernanceConstitutionalBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "governance_constitutional"

    def test_replay_bridge(self):
        b = ReplayConstitutionalBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "replay_constitutional"

    def test_continuity_bridge(self):
        b = ContinuityConstitutionalBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "continuity_constitutional"

    def test_topology_bridge(self):
        b = TopologyConstitutionalBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "topology_constitutional"

    def test_observability_bridge(self):
        b = ObservabilityConstitutionalBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "observability_constitutional"

    def test_deployment_bridge(self):
        b = DeploymentConstitutionalBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "deployment_constitutional"

    def test_applications_bridge(self):
        b = ApplicationsConstitutionalBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "applications_constitutional"

    def test_cognition_bridge(self):
        b = CognitionConstitutionalBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "cognition_constitutional"

    def test_orchestration_bridge(self):
        b = OrchestrationConstitutionalBridge(state_dir=tempfile.mkdtemp())
        event = b.record("test", {"key": "value"})
        assert event["bridge"] == "orchestration_constitutional"

    def test_bridge_events_tracked(self):
        b = GovernanceConstitutionalBridge(state_dir=tempfile.mkdtemp())
        b.record("e1", {})
        b.record("e2", {})
        assert len(b.get_events()) == 2

    def test_bridge_writes_to_file(self):
        d = tempfile.mkdtemp()
        b = GovernanceConstitutionalBridge(state_dir=d)
        b.record("test", {"key": "value"})
        path = Path(d) / "governance_constitutional.jsonl"
        assert path.exists()


# ── Coordinator ────────────────────────────────────────────


class TestCoordinator:
    def _make(self):
        return CanonicalConstitutionalRuntimeCoordinator(
            state_dir=tempfile.mkdtemp(),
        )

    def test_validate_invariants(self):
        c = self._make()
        result = c.validate_invariants()
        assert result["total_invariants"] == 18
        assert result["all_enforced"] is True

    def test_validate_replay_semantics(self):
        c = self._make()
        result = c.validate_replay_semantics("spine", "in", "out")
        assert result["deterministic"] is True

    def test_validate_lifecycle_semantics(self):
        c = self._make()
        result = c.validate_lifecycle_semantics("spine")
        assert result["coherent"] is True

    def test_register_topology(self):
        c = self._make()
        result = c.register_topology("environment", "hash123")
        assert result["baseline_match"] is True

    def test_validate_continuity(self):
        c = self._make()
        result = c.validate_continuity("session")
        assert result["coherent"] is True

    def test_validate_observability(self):
        c = self._make()
        result = c.validate_observability("spine")
        assert result["coherent"] is True

    def test_coherence_report_all_coherent(self):
        c = self._make()
        c.validate_replay_semantics("spine", "in", "out")
        c.validate_lifecycle_semantics("spine")
        c.register_topology("environment", "h1")
        c.validate_continuity("session")
        c.validate_observability("spine")
        report = c.get_coherence_report()
        assert report["all_coherent"] is True

    def test_detect_drift_none(self):
        c = self._make()
        c.register_topology("environment", "h1")
        assert len(c.detect_drift()) == 0

    def test_detect_drift_topology(self):
        c = self._make()
        c.register_topology("environment", "h1")
        c.register_topology("environment", "h2")
        drift = c.detect_drift()
        assert "topology:environment" in drift

    def test_detect_drift_lifecycle(self):
        c = self._make()
        c.validate_lifecycle_semantics("spine", terminal_absorbing=False)
        drift = c.detect_drift()
        assert "lifecycle:spine" in drift

    def test_detect_drift_continuity(self):
        c = self._make()
        c.validate_continuity("session", lineage_preserved=False)
        drift = c.detect_drift()
        assert "continuity:session" in drift

    def test_get_health(self):
        c = self._make()
        health = c.get_health()
        assert "lifecycle_phase" in health
        assert "invariants" in health

    def test_get_stats_eight_keys(self):
        c = self._make()
        stats = c.get_stats()
        expected = {
            "lifecycle", "invariants", "replay", "lifecycle_semantics",
            "topology", "continuity", "observability", "obs_pipeline",
        }
        assert set(stats.keys()) == expected

    def test_no_forbidden_methods(self):
        c = self._make()
        forbidden = [
            "execute", "dispatch", "orchestrate", "deploy",
            "scale", "create_execution_path", "bypass_governance",
            "mutate_subsystem", "create_orchestration_path",
        ]
        for name in forbidden:
            assert not hasattr(c, name), f"Has forbidden method: {name}"


# ── Constraint Verification ────────────────────────────────


class TestConstraintVerification:
    def _make(self):
        return CanonicalConstitutionalRuntimeCoordinator(
            state_dir=tempfile.mkdtemp(),
        )

    def test_unified_replay_determinism(self):
        re = UnifiedReplaySemanticsEngine()
        re.validate_layer_replay("spine", "input", "output")
        re.validate_layer_replay("workstation", "input", "output")
        state = re.get_unified_state()
        assert state.deterministic is True

    def test_unified_lifecycle_semantics(self):
        le = UnifiedLifecycleSemanticsEngine()
        for layer in ["spine", "workstation", "browser", "workflows"]:
            le.validate_layer_lifecycle(layer)
        state = le.get_unified_state()
        assert state.lifecycle_coherent is True

    def test_unified_topology_semantics(self):
        te = UnifiedTopologySemanticsEngine()
        for domain in KNOWN_TOPOLOGY_DOMAINS:
            te.register_topology(domain, "consistent_hash")
        state = te.get_unified_state()
        assert state.topology_coherent is True

    def test_unified_continuity_semantics(self):
        ce = UnifiedContinuitySemanticsEngine()
        for layer in KNOWN_CONTINUITY_LAYERS:
            ce.validate_layer_continuity(layer)
        state = ce.get_unified_state()
        assert state.continuity_coherent is True

    def test_unified_observability_semantics(self):
        oe = UnifiedObservabilitySemanticsEngine()
        for layer in ["spine", "workstation", "browser"]:
            oe.validate_layer_observability(layer)
        state = oe.get_unified_state()
        assert state.observability_coherent is True

    def test_no_semantic_drift_at_baseline(self):
        c = self._make()
        for domain in KNOWN_TOPOLOGY_DOMAINS:
            c.register_topology(domain, "base_hash")
        for layer in ["spine", "workstation"]:
            c.validate_lifecycle_semantics(layer)
            c.validate_observability(layer)
        for layer in ["session", "workflow"]:
            c.validate_continuity(layer)
        drift = c.detect_drift()
        assert len(drift) == 0

    def test_semantic_drift_detected(self):
        c = self._make()
        c.register_topology("environment", "h1")
        c.register_topology("environment", "h2")
        c.validate_lifecycle_semantics("spine", terminal_absorbing=False)
        drift = c.detect_drift()
        assert len(drift) >= 2

    def test_no_governance_bypass(self):
        assert is_forbidden("governance_bypass")

    def test_no_execution_outside_spine(self):
        assert is_forbidden("execution_outside_spine")

    def test_deterministic_constitutional_replay(self):
        rv = ConstitutionalReplayValidator()
        for check in REPLAY_CHECKS:
            result = rv.validate_determinism(check, "input", "output")
            assert result["deterministic"] is True
        assert rv.get_stats()["total_checks"] == 6

    def test_constitutional_lineage_preservation(self):
        rv = ConstitutionalReplayValidator()
        result = rv.validate_replay_pair(
            "governance_coherence", "input", "same", "same",
        )
        assert result["deterministic"] is True

    def test_invariant_consolidation_complete(self):
        ie = InvariantConsolidationEngine()
        domains = {i["domain"] for i in ie.get_all_invariants()}
        expected = {d.value for d in InvariantDomain}
        assert domains == expected

    def test_override_capping_all_limits(self):
        for name, default in CONSTITUTIONAL_LIMITS.items():
            assert enforce_limit(name, default + 100) == default

    def test_coordinator_cannot_execute(self):
        c = self._make()
        for attr in ["execute", "dispatch", "deploy", "scale"]:
            assert not hasattr(c, attr)

    def test_coordinator_cannot_mutate_subsystems(self):
        c = self._make()
        for attr in ["mutate_subsystem", "modify_governance",
                      "override_invariant", "bypass_replay"]:
            assert not hasattr(c, attr)

    def test_all_drift_types_defined(self):
        assert len(SemanticDriftType) == 6
        values = {d.value for d in SemanticDriftType}
        assert "replay_drift" in values
        assert "governance_drift" in values
