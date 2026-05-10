"""Tests for Phase 96.8CI — Substrate Operational Runtime Certification.

Tests: contracts, enums, lifecycle, invariant engine, guarantee engine,
topology certification, continuity certification, replay certification,
semantic consistency, observability pipeline, replay validator,
boundary policies, continuity bridges, coordinator, constraint verification.
"""

import sys
import tempfile
import os
import json

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import pytest


# ── Contracts ──────────────────────────────────────────────────

class TestContracts:
    def test_runtime_certification_state(self):
        from core.certification.runtime_certification_contracts_v1 import RuntimeCertificationState
        s = RuntimeCertificationState(run_id="run-001")
        assert s.certification_id.startswith("rcert-")
        assert s.certified is False

    def test_constitutional_invariant_state(self):
        from core.certification.runtime_certification_contracts_v1 import ConstitutionalInvariantState
        s = ConstitutionalInvariantState(domain="governance", invariant_name="test")
        assert s.invariant_id.startswith("cinvs-")

    def test_certification_scope(self):
        from core.certification.runtime_certification_contracts_v1 import CertificationScope
        s = CertificationScope(scope_name="full")
        assert s.scope_id.startswith("cscope-")

    def test_certification_boundary_state(self):
        from core.certification.runtime_certification_contracts_v1 import CertificationBoundaryState
        s = CertificationBoundaryState(limit_name="max_runs")
        assert s.boundary_id.startswith("cbnd-")

    def test_certification_replay_state(self):
        from core.certification.runtime_certification_contracts_v1 import CertificationReplayState
        s = CertificationReplayState(check_name="test")
        assert s.replay_id.startswith("crplay-")

    def test_certification_observability_state(self):
        from core.certification.runtime_certification_contracts_v1 import CertificationObservabilityState
        s = CertificationObservabilityState(events_emitted=5)
        assert s.observability_id.startswith("cobs-")

    def test_certification_lifecycle_state(self):
        from core.certification.runtime_certification_contracts_v1 import CertificationLifecycleState
        s = CertificationLifecycleState(phase="defined")
        assert s.lifecycle_id.startswith("clc-")

    def test_runtime_attestation(self):
        from core.certification.runtime_certification_contracts_v1 import RuntimeAttestation
        a = RuntimeAttestation(run_id="run-001")
        assert a.attestation_id.startswith("rattest-")

    def test_runtime_guarantee(self):
        from core.certification.runtime_certification_contracts_v1 import RuntimeGuarantee
        g = RuntimeGuarantee(guarantee_type="replay_determinism", domain="global")
        assert g.guarantee_id.startswith("rguarant-")

    def test_runtime_violation(self):
        from core.certification.runtime_certification_contracts_v1 import RuntimeViolation
        v = RuntimeViolation(domain="governance", invariant_name="test")
        assert v.violation_id.startswith("rviol-")

    def test_runtime_certification_receipt(self):
        from core.certification.runtime_certification_contracts_v1 import RuntimeCertificationReceipt
        r = RuntimeCertificationReceipt(run_id="run-001")
        assert r.receipt_id.startswith("rcrcpt-")

    def test_cross_layer_invariant_state(self):
        from core.certification.runtime_certification_contracts_v1 import CrossLayerInvariantState
        s = CrossLayerInvariantState(source_domain="governance", target_domain="replay")
        assert s.cross_layer_id.startswith("clinv-")

    def test_constitutional_semantic_state(self):
        from core.certification.runtime_certification_contracts_v1 import ConstitutionalSemanticState
        s = ConstitutionalSemanticState(semantic_domain="replay")
        assert s.semantic_id.startswith("csem-")

    def test_runtime_topology_guarantee(self):
        from core.certification.runtime_certification_contracts_v1 import RuntimeTopologyGuarantee
        g = RuntimeTopologyGuarantee()
        assert g.topology_guarantee_id.startswith("rtguar-")

    def test_runtime_continuity_guarantee(self):
        from core.certification.runtime_certification_contracts_v1 import RuntimeContinuityGuarantee
        g = RuntimeContinuityGuarantee()
        assert g.continuity_guarantee_id.startswith("rcguar-")

    def test_all_contracts_have_to_dict(self):
        from core.certification.runtime_certification_contracts_v1 import (
            RuntimeCertificationState, RuntimeAttestation, RuntimeGuarantee,
            RuntimeViolation, RuntimeCertificationReceipt,
        )
        for cls, kwargs in [
            (RuntimeCertificationState, {"run_id": "r1"}),
            (RuntimeAttestation, {"run_id": "r1"}),
            (RuntimeGuarantee, {"guarantee_type": "t", "domain": "d"}),
            (RuntimeViolation, {"domain": "d", "invariant_name": "n"}),
            (RuntimeCertificationReceipt, {"run_id": "r1"}),
        ]:
            obj = cls(**kwargs)
            d = obj.to_dict()
            assert isinstance(d, dict)


# ── Enums ──────────────────────────────────────────────────────

class TestEnums:
    def test_certification_phase_values(self):
        from core.certification.runtime_certification_contracts_v1 import CertificationPhase
        assert len(CertificationPhase) == 5

    def test_certification_event_type_values(self):
        from core.certification.runtime_certification_contracts_v1 import CertificationEventType
        assert len(CertificationEventType) == 9

    def test_certification_domain_values(self):
        from core.certification.runtime_certification_contracts_v1 import CertificationDomain
        assert len(CertificationDomain) == 10

    def test_guarantee_type_values(self):
        from core.certification.runtime_certification_contracts_v1 import GuaranteeType
        assert len(GuaranteeType) == 8

    def test_violation_severity_values(self):
        from core.certification.runtime_certification_contracts_v1 import ViolationSeverity
        assert len(ViolationSeverity) == 3

    def test_all_enums_are_str_enum(self):
        from core.certification.runtime_certification_contracts_v1 import (
            CertificationPhase, CertificationEventType, CertificationDomain,
        )
        assert isinstance(CertificationPhase.DEFINED, str)
        assert isinstance(CertificationEventType.CERTIFICATION_STARTED, str)
        assert isinstance(CertificationDomain.GOVERNANCE, str)

    def test_certification_domain_has_10_domains(self):
        from core.certification.runtime_certification_contracts_v1 import CertificationDomain
        domains = [d.value for d in CertificationDomain]
        assert len(domains) == 10
        assert "governance" in domains
        assert "deployment" in domains
        assert "resilience" in domains


# ── Lifecycle Engine ───────────────────────────────────────────

class TestLifecycleEngine:
    def test_initial_phase(self):
        from core.certification.runtime_certification_lifecycle_engine_v1 import RuntimeCertificationLifecycleEngine
        engine = RuntimeCertificationLifecycleEngine()
        assert engine.current_phase == "defined"

    def test_full_lifecycle(self):
        from core.certification.runtime_certification_lifecycle_engine_v1 import RuntimeCertificationLifecycleEngine
        engine = RuntimeCertificationLifecycleEngine()
        for p in ["staged", "validating", "certified", "archived"]:
            engine.transition(p)
        assert engine.current_phase == "archived"
        assert engine.is_terminal is True

    def test_invalid_transition(self):
        from core.certification.runtime_certification_lifecycle_engine_v1 import RuntimeCertificationLifecycleEngine
        engine = RuntimeCertificationLifecycleEngine()
        with pytest.raises(ValueError, match="Invalid transition"):
            engine.transition("archived")

    def test_terminal_state_blocks(self):
        from core.certification.runtime_certification_lifecycle_engine_v1 import RuntimeCertificationLifecycleEngine
        engine = RuntimeCertificationLifecycleEngine()
        for p in ["staged", "validating", "certified", "archived"]:
            engine.transition(p)
        with pytest.raises(ValueError, match="terminal state"):
            engine.transition("defined")

    def test_can_transition(self):
        from core.certification.runtime_certification_lifecycle_engine_v1 import RuntimeCertificationLifecycleEngine
        engine = RuntimeCertificationLifecycleEngine()
        assert engine.can_transition("staged") is True
        assert engine.can_transition("certified") is False

    def test_history_tracking(self):
        from core.certification.runtime_certification_lifecycle_engine_v1 import RuntimeCertificationLifecycleEngine
        engine = RuntimeCertificationLifecycleEngine()
        engine.transition("staged")
        history = engine.get_history()
        assert len(history) == 1
        assert history[0]["from"] == "defined"
        assert history[0]["to"] == "staged"

    def test_stats(self):
        from core.certification.runtime_certification_lifecycle_engine_v1 import RuntimeCertificationLifecycleEngine
        engine = RuntimeCertificationLifecycleEngine()
        engine.transition("staged")
        stats = engine.get_stats()
        assert stats["current_phase"] == "staged"
        assert stats["transitions"] == 1


# ── Constitutional Invariant Engine ───────────────────────────

class TestConstitutionalInvariantEngine:
    def test_verify_single_invariant(self):
        from core.certification.constitutional_invariant_engine_v1 import ConstitutionalInvariantEngine
        engine = ConstitutionalInvariantEngine()
        result = engine.verify_invariant("governance", "operator_approval_required")
        assert result["enforced"] is True

    def test_verify_failed_invariant(self):
        from core.certification.constitutional_invariant_engine_v1 import ConstitutionalInvariantEngine
        engine = ConstitutionalInvariantEngine()
        engine.verify_invariant("governance", "test_inv", enforced=False)
        assert engine.all_enforced() is False
        assert len(engine.get_violations()) == 1

    def test_verify_all_domains(self):
        from core.certification.constitutional_invariant_engine_v1 import ConstitutionalInvariantEngine
        engine = ConstitutionalInvariantEngine()
        result = engine.verify_all_domains()
        assert result["all_enforced"] is True
        assert result["total_invariants"] == 22

    def test_cross_layer_consistent(self):
        from core.certification.constitutional_invariant_engine_v1 import ConstitutionalInvariantEngine
        engine = ConstitutionalInvariantEngine()
        result = engine.verify_cross_layer("governance", "replay")
        assert result["consistent"] is True

    def test_cross_layer_inconsistent(self):
        from core.certification.constitutional_invariant_engine_v1 import ConstitutionalInvariantEngine
        engine = ConstitutionalInvariantEngine()
        engine.verify_cross_layer("governance", "replay", consistent=False)
        assert engine.all_cross_layer_consistent() is False

    def test_10_domains_covered(self):
        from core.certification.constitutional_invariant_engine_v1 import CONSTITUTIONAL_INVARIANTS
        assert len(CONSTITUTIONAL_INVARIANTS) == 10

    def test_max_invariants(self):
        from core.certification.constitutional_invariant_engine_v1 import ConstitutionalInvariantEngine
        engine = ConstitutionalInvariantEngine()
        for i in range(200):
            engine.verify_invariant("governance", f"inv_{i}")
        with pytest.raises(ValueError, match="Max invariants"):
            engine.verify_invariant("governance", "overflow")

    def test_stats(self):
        from core.certification.constitutional_invariant_engine_v1 import ConstitutionalInvariantEngine
        engine = ConstitutionalInvariantEngine()
        engine.verify_invariant("governance", "test")
        stats = engine.get_stats()
        assert stats["total_invariants"] == 1
        assert stats["enforced"] == 1


# ── Runtime Guarantee Engine ──────────────────────────────────

class TestRuntimeGuaranteeEngine:
    def test_issue_single_guarantee(self):
        from core.certification.runtime_guarantee_engine_v1 import RuntimeGuaranteeEngine
        engine = RuntimeGuaranteeEngine()
        result = engine.issue_guarantee("replay_determinism", "global")
        assert result["guaranteed"] is True

    def test_issue_failed_guarantee(self):
        from core.certification.runtime_guarantee_engine_v1 import RuntimeGuaranteeEngine
        engine = RuntimeGuaranteeEngine()
        engine.issue_guarantee("test", "global", guaranteed=False)
        assert engine.all_guaranteed() is False

    def test_issue_all_guarantees(self):
        from core.certification.runtime_guarantee_engine_v1 import RuntimeGuaranteeEngine
        engine = RuntimeGuaranteeEngine()
        result = engine.issue_all_guarantees()
        assert result["all_guaranteed"] is True
        assert result["total"] == 8

    def test_get_failed_guarantees(self):
        from core.certification.runtime_guarantee_engine_v1 import RuntimeGuaranteeEngine
        engine = RuntimeGuaranteeEngine()
        engine.issue_guarantee("test", "global", guaranteed=False)
        failed = engine.get_failed_guarantees()
        assert len(failed) == 1

    def test_max_guarantees(self):
        from core.certification.runtime_guarantee_engine_v1 import RuntimeGuaranteeEngine
        engine = RuntimeGuaranteeEngine()
        for i in range(200):
            engine.issue_guarantee(f"g_{i}", "global")
        with pytest.raises(ValueError, match="Max guarantees"):
            engine.issue_guarantee("overflow", "global")

    def test_stats(self):
        from core.certification.runtime_guarantee_engine_v1 import RuntimeGuaranteeEngine
        engine = RuntimeGuaranteeEngine()
        engine.issue_guarantee("test", "global")
        stats = engine.get_stats()
        assert stats["total_guarantees"] == 1

    def test_all_guaranteed_empty(self):
        from core.certification.runtime_guarantee_engine_v1 import RuntimeGuaranteeEngine
        engine = RuntimeGuaranteeEngine()
        assert engine.all_guaranteed() is True


# ── Topology Certification Engine ─────────────────────────────

class TestTopologyCertificationEngine:
    def test_certify_topology(self):
        from core.certification.runtime_topology_certification_engine_v1 import RuntimeTopologyCertificationEngine
        engine = RuntimeTopologyCertificationEngine()
        result = engine.certify_topology()
        assert result["certified"] is True

    def test_certify_with_orphans(self):
        from core.certification.runtime_topology_certification_engine_v1 import RuntimeTopologyCertificationEngine
        engine = RuntimeTopologyCertificationEngine()
        result = engine.certify_topology(no_orphans=False)
        assert result["certified"] is False

    def test_certify_with_hidden_mutation(self):
        from core.certification.runtime_topology_certification_engine_v1 import RuntimeTopologyCertificationEngine
        engine = RuntimeTopologyCertificationEngine()
        result = engine.certify_topology(no_hidden_mutation=False)
        assert result["certified"] is False

    def test_certify_with_recursive_growth(self):
        from core.certification.runtime_topology_certification_engine_v1 import RuntimeTopologyCertificationEngine
        engine = RuntimeTopologyCertificationEngine()
        result = engine.certify_topology(no_recursive_growth=False)
        assert result["certified"] is False

    def test_all_certified(self):
        from core.certification.runtime_topology_certification_engine_v1 import RuntimeTopologyCertificationEngine
        engine = RuntimeTopologyCertificationEngine()
        engine.certify_topology()
        assert engine.all_certified() is True

    def test_max_certifications(self):
        from core.certification.runtime_topology_certification_engine_v1 import RuntimeTopologyCertificationEngine
        engine = RuntimeTopologyCertificationEngine()
        for _ in range(50):
            engine.certify_topology()
        with pytest.raises(ValueError, match="Max topology certifications"):
            engine.certify_topology()

    def test_known_checks_exist(self):
        from core.certification.runtime_topology_certification_engine_v1 import TOPOLOGY_CHECKS
        assert len(TOPOLOGY_CHECKS) == 6

    def test_stats(self):
        from core.certification.runtime_topology_certification_engine_v1 import RuntimeTopologyCertificationEngine
        engine = RuntimeTopologyCertificationEngine()
        engine.certify_topology()
        stats = engine.get_stats()
        assert stats["total_certifications"] == 1


# ── Continuity Certification Engine ──────────────────────────

class TestContinuityCertificationEngine:
    def test_certify_continuity(self):
        from core.certification.runtime_continuity_certification_engine_v1 import RuntimeContinuityCertificationEngine
        engine = RuntimeContinuityCertificationEngine()
        result = engine.certify_continuity()
        assert result["certified"] is True

    def test_certify_with_broken_checkpoint(self):
        from core.certification.runtime_continuity_certification_engine_v1 import RuntimeContinuityCertificationEngine
        engine = RuntimeContinuityCertificationEngine()
        result = engine.certify_continuity(checkpoint_integrity=False)
        assert result["certified"] is False

    def test_certify_with_broken_session(self):
        from core.certification.runtime_continuity_certification_engine_v1 import RuntimeContinuityCertificationEngine
        engine = RuntimeContinuityCertificationEngine()
        result = engine.certify_continuity(session_continuity=False)
        assert result["certified"] is False

    def test_certify_with_broken_chronology(self):
        from core.certification.runtime_continuity_certification_engine_v1 import RuntimeContinuityCertificationEngine
        engine = RuntimeContinuityCertificationEngine()
        result = engine.certify_continuity(chronology_preserved=False)
        assert result["certified"] is False

    def test_all_certified(self):
        from core.certification.runtime_continuity_certification_engine_v1 import RuntimeContinuityCertificationEngine
        engine = RuntimeContinuityCertificationEngine()
        engine.certify_continuity()
        assert engine.all_certified() is True

    def test_known_checks_exist(self):
        from core.certification.runtime_continuity_certification_engine_v1 import CONTINUITY_CHECKS
        assert len(CONTINUITY_CHECKS) == 5

    def test_max_certifications(self):
        from core.certification.runtime_continuity_certification_engine_v1 import RuntimeContinuityCertificationEngine
        engine = RuntimeContinuityCertificationEngine()
        for _ in range(50):
            engine.certify_continuity()
        with pytest.raises(ValueError, match="Max continuity certifications"):
            engine.certify_continuity()

    def test_stats(self):
        from core.certification.runtime_continuity_certification_engine_v1 import RuntimeContinuityCertificationEngine
        engine = RuntimeContinuityCertificationEngine()
        stats = engine.get_stats()
        assert stats["total_certifications"] == 0


# ── Replay Certification Engine ───────────────────────────────

class TestReplayCertificationEngine:
    def test_certify_replay(self):
        from core.certification.runtime_replay_certification_engine_v1 import RuntimeReplayCertificationEngine
        engine = RuntimeReplayCertificationEngine()
        result = engine.certify_replay("test", "input", "output")
        assert result["deterministic"] is True

    def test_certify_replay_pair_same(self):
        from core.certification.runtime_replay_certification_engine_v1 import RuntimeReplayCertificationEngine
        engine = RuntimeReplayCertificationEngine()
        result = engine.certify_replay_pair("test", "input", "output", "output")
        assert result["deterministic"] is True

    def test_certify_replay_pair_different(self):
        from core.certification.runtime_replay_certification_engine_v1 import RuntimeReplayCertificationEngine
        engine = RuntimeReplayCertificationEngine()
        result = engine.certify_replay_pair("test", "input", "output_a", "output_b")
        assert result["deterministic"] is False

    def test_all_deterministic(self):
        from core.certification.runtime_replay_certification_engine_v1 import RuntimeReplayCertificationEngine
        engine = RuntimeReplayCertificationEngine()
        engine.certify_replay("c1", "i", "o")
        assert engine.all_deterministic() is True

    def test_all_deterministic_mixed(self):
        from core.certification.runtime_replay_certification_engine_v1 import RuntimeReplayCertificationEngine
        engine = RuntimeReplayCertificationEngine()
        engine.certify_replay("c1", "i", "o")
        engine.certify_replay_pair("c2", "i", "a", "b")
        assert engine.all_deterministic() is False

    def test_known_checks_exist(self):
        from core.certification.runtime_replay_certification_engine_v1 import REPLAY_CERTIFICATION_CHECKS
        assert len(REPLAY_CERTIFICATION_CHECKS) == 5

    def test_max_certifications(self):
        from core.certification.runtime_replay_certification_engine_v1 import RuntimeReplayCertificationEngine
        engine = RuntimeReplayCertificationEngine()
        for i in range(100):
            engine.certify_replay(f"c_{i}", "input", "output")
        with pytest.raises(ValueError, match="Max replay certifications"):
            engine.certify_replay("overflow", "input", "output")

    def test_stats(self):
        from core.certification.runtime_replay_certification_engine_v1 import RuntimeReplayCertificationEngine
        engine = RuntimeReplayCertificationEngine()
        engine.certify_replay("c1", "i", "o")
        stats = engine.get_stats()
        assert stats["total_certifications"] == 1
        assert stats["deterministic"] == 1


# ── Semantic Consistency Engine ───────────────────────────────

class TestSemanticConsistencyEngine:
    def test_verify_single_domain(self):
        from core.certification.constitutional_semantic_consistency_engine_v1 import ConstitutionalSemanticConsistencyEngine
        engine = ConstitutionalSemanticConsistencyEngine()
        result = engine.verify_semantic_consistency("replay")
        assert result["coherent"] is True

    def test_verify_incoherent(self):
        from core.certification.constitutional_semantic_consistency_engine_v1 import ConstitutionalSemanticConsistencyEngine
        engine = ConstitutionalSemanticConsistencyEngine()
        engine.verify_semantic_consistency("replay", coherent=False)
        assert engine.all_coherent() is False

    def test_verify_all_domains(self):
        from core.certification.constitutional_semantic_consistency_engine_v1 import ConstitutionalSemanticConsistencyEngine
        engine = ConstitutionalSemanticConsistencyEngine()
        result = engine.verify_all_domains()
        assert result["all_coherent"] is True
        assert result["domains_checked"] == 6

    def test_get_incoherent_domains(self):
        from core.certification.constitutional_semantic_consistency_engine_v1 import ConstitutionalSemanticConsistencyEngine
        engine = ConstitutionalSemanticConsistencyEngine()
        engine.verify_semantic_consistency("replay", coherent=False)
        incoherent = engine.get_incoherent_domains()
        assert "replay" in incoherent

    def test_known_domains(self):
        from core.certification.constitutional_semantic_consistency_engine_v1 import SEMANTIC_DOMAINS
        assert len(SEMANTIC_DOMAINS) == 6

    def test_max_checks(self):
        from core.certification.constitutional_semantic_consistency_engine_v1 import ConstitutionalSemanticConsistencyEngine
        engine = ConstitutionalSemanticConsistencyEngine()
        for i in range(100):
            engine.verify_semantic_consistency(f"domain_{i}")
        with pytest.raises(ValueError, match="Max semantic checks"):
            engine.verify_semantic_consistency("overflow")

    def test_stats(self):
        from core.certification.constitutional_semantic_consistency_engine_v1 import ConstitutionalSemanticConsistencyEngine
        engine = ConstitutionalSemanticConsistencyEngine()
        engine.verify_semantic_consistency("replay")
        stats = engine.get_stats()
        assert stats["total_checks"] == 1
        assert stats["coherent"] == 1


# ── Observability Pipeline ────────────────────────────────────

class TestObservabilityPipeline:
    def test_emit_certification_started(self):
        from core.certification.runtime_certification_observability_pipeline_v1 import RuntimeCertificationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = RuntimeCertificationObservabilityPipeline(state_dir=td)
            event = pipe.emit_certification_started(run_id="run-001")
            assert event["event_type"] == "certification_started"

    def test_emit_certification_completed(self):
        from core.certification.runtime_certification_observability_pipeline_v1 import RuntimeCertificationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = RuntimeCertificationObservabilityPipeline(state_dir=td)
            event = pipe.emit_certification_completed(run_id="run-001", certified=True)
            assert event["certified"] is True

    def test_emit_invariant_verified(self):
        from core.certification.runtime_certification_observability_pipeline_v1 import RuntimeCertificationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = RuntimeCertificationObservabilityPipeline(state_dir=td)
            event = pipe.emit_invariant_verified(domain="governance", invariant_name="test")
            assert event["domain"] == "governance"

    def test_emit_invariant_failed(self):
        from core.certification.runtime_certification_observability_pipeline_v1 import RuntimeCertificationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = RuntimeCertificationObservabilityPipeline(state_dir=td)
            event = pipe.emit_invariant_failed(domain="replay", invariant_name="test")
            assert event["domain"] == "replay"

    def test_emit_replay_certified(self):
        from core.certification.runtime_certification_observability_pipeline_v1 import RuntimeCertificationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = RuntimeCertificationObservabilityPipeline(state_dir=td)
            event = pipe.emit_replay_certified(checks_passed=5)
            assert event["checks_passed"] == 5

    def test_emit_continuity_certified(self):
        from core.certification.runtime_certification_observability_pipeline_v1 import RuntimeCertificationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = RuntimeCertificationObservabilityPipeline(state_dir=td)
            event = pipe.emit_continuity_certified(checks_passed=3)
            assert event["checks_passed"] == 3

    def test_emit_topology_certified(self):
        from core.certification.runtime_certification_observability_pipeline_v1 import RuntimeCertificationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = RuntimeCertificationObservabilityPipeline(state_dir=td)
            event = pipe.emit_topology_certified(checks_passed=4)
            assert event["checks_passed"] == 4

    def test_emit_semantic_consistency_verified(self):
        from core.certification.runtime_certification_observability_pipeline_v1 import RuntimeCertificationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = RuntimeCertificationObservabilityPipeline(state_dir=td)
            event = pipe.emit_semantic_consistency_verified(domains_checked=6)
            assert event["domains_checked"] == 6

    def test_emit_runtime_attestation_generated(self):
        from core.certification.runtime_certification_observability_pipeline_v1 import RuntimeCertificationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = RuntimeCertificationObservabilityPipeline(state_dir=td)
            event = pipe.emit_runtime_attestation_generated(run_id="r1", all_certified=True)
            assert event["all_certified"] is True

    def test_event_file_map_has_9_entries(self):
        from core.certification.runtime_certification_observability_pipeline_v1 import EVENT_FILE_MAP
        assert len(EVENT_FILE_MAP) == 9

    def test_jsonl_persistence(self):
        from core.certification.runtime_certification_observability_pipeline_v1 import RuntimeCertificationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = RuntimeCertificationObservabilityPipeline(state_dir=td)
            pipe.emit_certification_started(run_id="run-001")
            filepath = os.path.join(td, "certification_started.jsonl")
            assert os.path.exists(filepath)
            with open(filepath) as f:
                data = json.loads(f.readline())
                assert data["run_id"] == "run-001"

    def test_get_events(self):
        from core.certification.runtime_certification_observability_pipeline_v1 import RuntimeCertificationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = RuntimeCertificationObservabilityPipeline(state_dir=td)
            pipe.emit_certification_started(run_id="r1")
            pipe.emit_certification_completed(run_id="r1")
            assert len(pipe.get_events()) == 2

    def test_stats(self):
        from core.certification.runtime_certification_observability_pipeline_v1 import RuntimeCertificationObservabilityPipeline
        with tempfile.TemporaryDirectory() as td:
            pipe = RuntimeCertificationObservabilityPipeline(state_dir=td)
            pipe.emit_certification_started(run_id="r1")
            stats = pipe.get_stats()
            assert stats["total_events"] == 1
            assert stats["event_types"] == 9


# ── Replay Validator ──────────────────────────────────────────

class TestReplayValidator:
    def test_validate_determinism(self):
        from core.certification.runtime_certification_replay_validator_v1 import RuntimeCertificationReplayValidator
        v = RuntimeCertificationReplayValidator()
        result = v.validate_determinism("check_1", "input", "output")
        assert result["deterministic"] is True

    def test_validate_pair_same(self):
        from core.certification.runtime_certification_replay_validator_v1 import RuntimeCertificationReplayValidator
        v = RuntimeCertificationReplayValidator()
        result = v.validate_replay_pair("check_1", "input", "output", "output")
        assert result["deterministic"] is True

    def test_validate_pair_different(self):
        from core.certification.runtime_certification_replay_validator_v1 import RuntimeCertificationReplayValidator
        v = RuntimeCertificationReplayValidator()
        result = v.validate_replay_pair("check_1", "input", "a", "b")
        assert result["deterministic"] is False

    def test_all_deterministic_empty(self):
        from core.certification.runtime_certification_replay_validator_v1 import RuntimeCertificationReplayValidator
        v = RuntimeCertificationReplayValidator()
        assert v.all_deterministic() is True

    def test_known_checks_exist(self):
        from core.certification.runtime_certification_replay_validator_v1 import REPLAY_CHECKS
        assert len(REPLAY_CHECKS) == 7

    def test_stats(self):
        from core.certification.runtime_certification_replay_validator_v1 import RuntimeCertificationReplayValidator
        v = RuntimeCertificationReplayValidator()
        v.validate_determinism("c1", "i", "o")
        stats = v.get_stats()
        assert stats["total_checks"] == 1


# ── Boundary Policies ────────────────────────────────────────

class TestBoundaryPolicies:
    def test_default_limits(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies, CERTIFICATION_LIMITS
        bp = RuntimeCertificationBoundaryPolicies()
        assert bp.get_limits() == CERTIFICATION_LIMITS

    def test_check_not_exceeded(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies()
        result = bp.check_limit("max_certification_runs", 10)
        assert result["exceeded"] is False

    def test_check_exceeded(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies()
        result = bp.check_limit("max_certification_runs", 50)
        assert result["exceeded"] is True

    def test_override_capping(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies(overrides={"max_certification_runs": 999})
        limits = bp.get_limits()
        assert limits["max_certification_runs"] == 50

    def test_override_lower(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies(overrides={"max_certification_runs": 10})
        limits = bp.get_limits()
        assert limits["max_certification_runs"] == 10

    def test_is_forbidden(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies()
        assert bp.is_forbidden("governance_bypass") is True
        assert bp.is_forbidden("valid_action") is False

    def test_forbidden_actions_count(self):
        from core.certification.runtime_certification_boundary_policies_v1 import FORBIDDEN_CERTIFICATION_ACTIONS
        assert len(FORBIDDEN_CERTIFICATION_ACTIONS) == 8

    def test_limits_count(self):
        from core.certification.runtime_certification_boundary_policies_v1 import CERTIFICATION_LIMITS
        assert len(CERTIFICATION_LIMITS) == 8

    def test_exceeded_checks(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies()
        bp.check_limit("max_certification_runs", 10)
        bp.check_limit("max_certification_runs", 999)
        exceeded = bp.get_exceeded_checks()
        assert len(exceeded) == 1

    def test_certification_owned_execution_forbidden(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies()
        assert bp.is_forbidden("certification_owned_execution") is True

    def test_certification_owned_repair_forbidden(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies()
        assert bp.is_forbidden("certification_owned_repair") is True

    def test_recursive_certification_forbidden(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies()
        assert bp.is_forbidden("recursive_certification") is True

    def test_execution_outside_spine_forbidden(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies()
        assert bp.is_forbidden("execution_outside_spine") is True

    def test_replay_bypass_forbidden(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies()
        assert bp.is_forbidden("replay_bypass") is True

    def test_stats(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies()
        stats = bp.get_stats()
        assert stats["total_limits"] == 8
        assert stats["total_forbidden"] == 8

    def test_override_ignored_for_unknown_key(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies(overrides={"fake_key": 999})
        limits = bp.get_limits()
        assert "fake_key" not in limits


# ── Continuity Bridges ────────────────────────────────────────

class TestContinuityBridges:
    def test_all_bridges_count(self):
        from core.certification.runtime_certification_continuity_bridges_v1 import ALL_BRIDGE_CLASSES
        assert len(ALL_BRIDGE_CLASSES) == 9

    def test_constitutional_bridge(self):
        from core.certification.runtime_certification_continuity_bridges_v1 import ConstitutionalCertificationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = ConstitutionalCertificationBridge(state_dir=td)
            record = bridge.record("certify")
            assert record["bridge"] == "constitutional_certification"

    def test_replay_bridge(self):
        from core.certification.runtime_certification_continuity_bridges_v1 import ReplayCertificationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = ReplayCertificationBridge(state_dir=td)
            record = bridge.record("certify")
            assert record["bridge"] == "replay_certification"

    def test_continuity_bridge(self):
        from core.certification.runtime_certification_continuity_bridges_v1 import ContinuityCertificationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = ContinuityCertificationBridge(state_dir=td)
            record = bridge.record("certify")
            assert record["bridge"] == "continuity_certification"

    def test_topology_bridge(self):
        from core.certification.runtime_certification_continuity_bridges_v1 import TopologyCertificationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = TopologyCertificationBridge(state_dir=td)
            record = bridge.record("certify")
            assert record["bridge"] == "topology_certification"

    def test_resilience_bridge(self):
        from core.certification.runtime_certification_continuity_bridges_v1 import ResilienceCertificationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = ResilienceCertificationBridge(state_dir=td)
            record = bridge.record("certify")
            assert record["bridge"] == "resilience_certification"

    def test_jsonl_persistence(self):
        from core.certification.runtime_certification_continuity_bridges_v1 import ConstitutionalCertificationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = ConstitutionalCertificationBridge(state_dir=td)
            bridge.record("test_action")
            filepath = os.path.join(td, "constitutional_certification.jsonl")
            assert os.path.exists(filepath)

    def test_get_records(self):
        from core.certification.runtime_certification_continuity_bridges_v1 import ConstitutionalCertificationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = ConstitutionalCertificationBridge(state_dir=td)
            bridge.record("a1")
            bridge.record("a2")
            assert len(bridge.get_records()) == 2

    def test_bridge_stats(self):
        from core.certification.runtime_certification_continuity_bridges_v1 import ConstitutionalCertificationBridge
        with tempfile.TemporaryDirectory() as td:
            bridge = ConstitutionalCertificationBridge(state_dir=td)
            bridge.record("a1")
            stats = bridge.get_stats()
            assert stats["bridge_name"] == "constitutional_certification"
            assert stats["total_records"] == 1

    def test_deployment_orchestration_applications_stabilization_bridges(self):
        from core.certification.runtime_certification_continuity_bridges_v1 import (
            DeploymentCertificationBridge,
            OrchestrationCertificationBridge,
            ApplicationsCertificationBridge,
            StabilizationCertificationBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            for cls, name in [
                (DeploymentCertificationBridge, "deployment_certification"),
                (OrchestrationCertificationBridge, "orchestration_certification"),
                (ApplicationsCertificationBridge, "applications_certification"),
                (StabilizationCertificationBridge, "stabilization_certification"),
            ]:
                bridge = cls(state_dir=td)
                record = bridge.record("certify")
                assert record["bridge"] == name


# ── Coordinator ───────────────────────────────────────────────

class TestCoordinator:
    def _make_coordinator(self, td):
        from core.certification.canonical_runtime_certification_coordinator_v1 import (
            CanonicalRuntimeCertificationCoordinator,
        )
        return CanonicalRuntimeCertificationCoordinator(state_dir=td)

    def test_start_certification(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            run = coord.start_certification("run-001")
            assert run["status"] == "started"

    def test_verify_invariants(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.verify_invariants()
            assert result["all_enforced"] is True
            assert result["total_invariants"] == 22

    def test_verify_cross_layer(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.verify_cross_layer("governance", "replay")
            assert result["consistent"] is True

    def test_issue_guarantees(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.issue_guarantees()
            assert result["all_guaranteed"] is True
            assert result["total"] == 8

    def test_certify_topology(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.certify_topology()
            assert result["certified"] is True

    def test_certify_continuity(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.certify_continuity()
            assert result["certified"] is True

    def test_certify_replay(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.certify_replay("test", "input", "output")
            assert result["deterministic"] is True

    def test_verify_semantic_consistency(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.verify_semantic_consistency()
            assert result["all_coherent"] is True

    def test_generate_attestation(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.verify_invariants()
            coord.issue_guarantees()
            coord.certify_topology()
            coord.certify_continuity()
            coord.certify_replay("test", "input", "output")
            coord.verify_semantic_consistency()
            att = coord.generate_attestation("run-001")
            assert att["all_certified"] is True
            assert att["attestation_id"].startswith("rattest-")
            att_path = os.path.join(td, "attestations", "runtime_attestation.json")
            assert os.path.exists(att_path)

    def test_complete_certification(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.verify_invariants()
            coord.issue_guarantees()
            coord.certify_topology()
            coord.certify_continuity()
            coord.certify_replay("test", "input", "output")
            coord.verify_semantic_consistency()
            receipt = coord.complete_certification("run-001")
            assert receipt["outcome"] == "certified"

    def test_complete_certification_failed(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.certify_topology(no_orphans=False)
            receipt = coord.complete_certification("run-001")
            assert receipt["outcome"] == "failed"

    def test_max_certification_runs(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            for i in range(50):
                coord.start_certification(f"run-{i}")
            with pytest.raises(ValueError, match="Max certification runs"):
                coord.start_certification("overflow")

    def test_certification_report(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.verify_invariants()
            report = coord.get_certification_report()
            assert "invariants" in report
            assert "guarantees" in report
            assert "topology" in report

    def test_stats(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.start_certification("run-001")
            stats = coord.get_stats()
            assert stats["runs"] == 1
            assert "lifecycle" in stats
            assert "invariants" in stats

    def test_validate_replay_determinism(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.validate_replay_determinism("check_1", "input", "output")
            assert result["deterministic"] is True

    def test_check_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            result = coord.check_boundary("max_certification_runs", 10)
            assert result["exceeded"] is False


# ── Constraint Verification ──────────────────────────────────

class TestConstraintVerification:
    def test_global_invariant_verification(self):
        from core.certification.constitutional_invariant_engine_v1 import ConstitutionalInvariantEngine
        engine = ConstitutionalInvariantEngine()
        result = engine.verify_all_domains()
        assert result["all_enforced"] is True
        assert result["total_invariants"] == 22

    def test_replay_certification_determinism(self):
        from core.certification.runtime_replay_certification_engine_v1 import RuntimeReplayCertificationEngine
        engine = RuntimeReplayCertificationEngine()
        engine.certify_replay("test", "same_input", "same_output")
        engine.certify_replay_pair("test2", "same_input", "same_output", "same_output")
        assert engine.all_deterministic() is True

    def test_continuity_certification_determinism(self):
        from core.certification.runtime_continuity_certification_engine_v1 import RuntimeContinuityCertificationEngine
        engine = RuntimeContinuityCertificationEngine()
        engine.certify_continuity()
        assert engine.all_certified() is True

    def test_topology_certification_determinism(self):
        from core.certification.runtime_topology_certification_engine_v1 import RuntimeTopologyCertificationEngine
        engine = RuntimeTopologyCertificationEngine()
        engine.certify_topology()
        assert engine.all_certified() is True

    def test_semantic_consistency_preservation(self):
        from core.certification.constitutional_semantic_consistency_engine_v1 import ConstitutionalSemanticConsistencyEngine
        engine = ConstitutionalSemanticConsistencyEngine()
        result = engine.verify_all_domains()
        assert result["all_coherent"] is True

    def test_constitutional_invariant_preservation(self):
        from core.certification.constitutional_invariant_engine_v1 import ConstitutionalInvariantEngine, CONSTITUTIONAL_INVARIANTS
        assert len(CONSTITUTIONAL_INVARIANTS) == 10
        total_invariants = sum(len(v) for v in CONSTITUTIONAL_INVARIANTS.values())
        assert total_invariants == 22

    def test_no_governance_bypass(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies()
        assert bp.is_forbidden("governance_bypass") is True

    def test_no_certification_mutation(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies()
        assert bp.is_forbidden("hidden_certification_mutation") is True

    def test_no_certification_owned_execution(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies()
        assert bp.is_forbidden("certification_owned_execution") is True

    def test_no_execution_outside_spine(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies()
        assert bp.is_forbidden("execution_outside_spine") is True

    def test_deterministic_attestation_generation(self):
        with tempfile.TemporaryDirectory() as td:
            from core.certification.canonical_runtime_certification_coordinator_v1 import (
                CanonicalRuntimeCertificationCoordinator,
            )
            coord = CanonicalRuntimeCertificationCoordinator(state_dir=td)
            coord.verify_invariants()
            coord.issue_guarantees()
            coord.certify_topology()
            coord.certify_continuity()
            coord.certify_replay("test", "input", "output")
            coord.verify_semantic_consistency()
            att = coord.generate_attestation("run-001")
            assert att["all_certified"] is True
            assert att["invariants_verified"] == 22
            assert att["guarantees_issued"] == 8

    def test_override_capping_enforced(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies, CERTIFICATION_LIMITS
        bp = RuntimeCertificationBoundaryPolicies(overrides={k: 9999 for k in CERTIFICATION_LIMITS})
        for key, default in CERTIFICATION_LIMITS.items():
            assert bp.get_limits()[key] == default

    def test_lifecycle_linear_progression(self):
        from core.certification.runtime_certification_lifecycle_engine_v1 import VALID_TRANSITIONS
        for source, targets in VALID_TRANSITIONS.items():
            assert len(targets) <= 1

    def test_lifecycle_terminal_absorbing(self):
        from core.certification.runtime_certification_lifecycle_engine_v1 import RuntimeCertificationLifecycleEngine
        engine = RuntimeCertificationLifecycleEngine()
        for p in ["staged", "validating", "certified", "archived"]:
            engine.transition(p)
        assert engine.is_terminal is True
        with pytest.raises(ValueError):
            engine.transition("defined")

    def test_coordinator_cannot_mutate(self):
        with tempfile.TemporaryDirectory() as td:
            from core.certification.canonical_runtime_certification_coordinator_v1 import (
                CanonicalRuntimeCertificationCoordinator,
            )
            coord = CanonicalRuntimeCertificationCoordinator(state_dir=td)
            assert not hasattr(coord, "mutate")
            assert not hasattr(coord, "repair")
            assert not hasattr(coord, "execute")
            assert not hasattr(coord, "deploy")

    def test_full_certification_flow(self):
        with tempfile.TemporaryDirectory() as td:
            from core.certification.canonical_runtime_certification_coordinator_v1 import (
                CanonicalRuntimeCertificationCoordinator,
            )
            coord = CanonicalRuntimeCertificationCoordinator(state_dir=td)
            coord.start_certification("run-001")
            coord.verify_invariants()
            coord.issue_guarantees()
            coord.certify_topology()
            coord.certify_continuity()
            coord.certify_replay("test", "input", "output")
            coord.verify_semantic_consistency()
            att = coord.generate_attestation("run-001")
            receipt = coord.complete_certification("run-001")
            assert att["all_certified"] is True
            assert receipt["outcome"] == "certified"
            assert receipt["domains_certified"] == 10

    def test_cross_layer_verification(self):
        from core.certification.constitutional_invariant_engine_v1 import ConstitutionalInvariantEngine
        engine = ConstitutionalInvariantEngine()
        engine.verify_cross_layer("governance", "replay")
        engine.verify_cross_layer("topology", "continuity")
        assert engine.all_cross_layer_consistent() is True

    def test_10_certification_domains(self):
        from core.certification.runtime_certification_contracts_v1 import CertificationDomain
        assert len(CertificationDomain) == 10

    def test_8_guarantee_types(self):
        from core.certification.runtime_certification_contracts_v1 import GuaranteeType
        assert len(GuaranteeType) == 8

    def test_no_certification_owned_repair(self):
        from core.certification.runtime_certification_boundary_policies_v1 import RuntimeCertificationBoundaryPolicies
        bp = RuntimeCertificationBoundaryPolicies()
        assert bp.is_forbidden("certification_owned_repair") is True
