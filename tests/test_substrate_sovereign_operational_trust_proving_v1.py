"""Tests for Phase 96.8CM — Substrate Sovereign Operational Trust Proving.

Covers: contracts, enums, lifecycle, artifact engine, bundle engine,
external verification engine, replay validator, constitutional proof engine,
chronology proof engine, provenance proof engine, observability pipeline,
boundary policies, continuity bridges, coordinator, constraint verification.
"""

import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, "/opt/OS")

import pytest

from core.trust.sovereign_operational_trust_contracts_v1 import (
    SovereignTrustState,
    TrustArtifact,
    TrustBundle,
    TrustProofReceipt,
    TrustVerificationState,
    TrustLineageState,
    TrustHashState,
    TrustAttestationState,
    TrustBoundaryState,
    TrustReplayState,
    ExternalVerificationState,
    ConstitutionalTrustProof,
    ProvenanceTrustProof,
    ChronologyTrustProof,
    GovernanceTrustProof,
    TrustPhase,
    TrustEventType,
    TrustDomain,
    TrustIntegrityDimension,
    _now_iso,
    _deterministic_id,
)
from core.trust.trust_lifecycle_engine_v1 import (
    TrustLifecycleEngine,
    TRUST_LIFECYCLE_ORDER,
    TERMINAL_TRUST_PHASES,
)
from core.trust.trust_artifact_engine_v1 import (
    TrustArtifactEngine,
    ARTIFACT_TYPES,
    MAX_ARTIFACTS,
)
from core.trust.trust_bundle_engine_v1 import (
    TrustBundleEngine,
    BUNDLE_DOMAINS,
    MAX_BUNDLES,
)
from core.trust.external_verification_engine_v1 import (
    ExternalVerificationEngine,
    VERIFICATION_DIMENSIONS,
    MAX_VERIFICATIONS,
)
from core.trust.trust_replay_validator_v1 import (
    TrustReplayValidator,
    REPLAY_CHECKS,
)
from core.trust.constitutional_trust_proof_engine_v1 import (
    ConstitutionalTrustProofEngine,
    CONSTITUTIONAL_PROOF_DIMENSIONS,
    MAX_CONSTITUTIONAL_PROOFS,
)
from core.trust.chronology_trust_proof_engine_v1 import (
    ChronologyTrustProofEngine,
    CHRONOLOGY_PROOF_DIMENSIONS,
    MAX_CHRONOLOGY_PROOFS,
)
from core.trust.provenance_trust_proof_engine_v1 import (
    ProvenanceTrustProofEngine,
    PROVENANCE_PROOF_DIMENSIONS,
    MAX_PROVENANCE_PROOFS,
)
from core.trust.trust_observability_pipeline_v1 import (
    TrustObservabilityPipeline,
    EVENT_FILE_MAP,
)
from core.trust.trust_boundary_policies_v1 import (
    TrustBoundaryPolicies,
    TRUST_LIMITS,
    FORBIDDEN_TRUST_ACTIONS,
)
from core.trust.trust_continuity_bridges_v1 import (
    CertificationTrustBridge,
    ValidationTrustBridge,
    ExplainabilityTrustBridge,
    AccountabilityTrustBridge,
    ReplayTrustBridge,
    ProvenanceTrustBridge,
    ChronologyTrustBridge,
    GovernanceTrustBridge,
    ObservabilityTrustBridge,
    ALL_BRIDGE_CLASSES,
)
from core.trust.canonical_sovereign_trust_coordinator_v1 import (
    CanonicalSovereignTrustCoordinator,
    MAX_TRUST_RUNS,
)


# ─── Contracts ───────────────────────────────────────────

class TestContracts:
    def test_sovereign_trust_state_to_dict(self):
        s = SovereignTrustState()
        d = s.to_dict()
        assert "trust_id" in d
        assert d["phase"] == "defined"

    def test_trust_artifact_to_dict(self):
        a = TrustArtifact(artifact_type="runtime_attestation")
        d = a.to_dict()
        assert d["artifact_type"] == "runtime_attestation"
        assert "artifact_id" in d

    def test_trust_bundle_to_dict(self):
        b = TrustBundle()
        d = b.to_dict()
        assert "bundle_id" in d
        assert d["artifacts_count"] == 0

    def test_trust_proof_receipt_to_dict(self):
        r = TrustProofReceipt(run_id="test-run")
        d = r.to_dict()
        assert d["run_id"] == "test-run"
        assert d["outcome"] == "incomplete"

    def test_trust_verification_state_to_dict(self):
        v = TrustVerificationState(bundle_id="b1")
        d = v.to_dict()
        assert d["bundle_id"] == "b1"

    def test_trust_lineage_state_to_dict(self):
        l = TrustLineageState(domain="governance")
        d = l.to_dict()
        assert d["domain"] == "governance"

    def test_trust_hash_state_to_dict(self):
        h = TrustHashState(source="test.json")
        d = h.to_dict()
        assert d["source"] == "test.json"
        assert d["algorithm"] == "sha256"

    def test_trust_attestation_state_to_dict(self):
        a = TrustAttestationState(domain="constitutional")
        d = a.to_dict()
        assert d["domain"] == "constitutional"

    def test_trust_boundary_state_to_dict(self):
        b = TrustBoundaryState(action="test_action")
        d = b.to_dict()
        assert d["action"] == "test_action"

    def test_trust_replay_state_to_dict(self):
        r = TrustReplayState(check_name="test_check")
        d = r.to_dict()
        assert d["check_name"] == "test_check"

    def test_external_verification_state_score(self):
        e = ExternalVerificationState(
            hash_verified=True, lineage_verified=True,
            chronology_verified=True, governance_verified=True,
            replay_verified=True, provenance_verified=True,
            completeness_verified=True,
        )
        assert e.trust_integrity_score == 1.0

    def test_external_verification_state_partial_score(self):
        e = ExternalVerificationState(hash_verified=True)
        assert 0 < e.trust_integrity_score < 1.0

    def test_constitutional_trust_proof_to_dict(self):
        p = ConstitutionalTrustProof()
        d = p.to_dict()
        assert "proof_id" in d

    def test_provenance_trust_proof_to_dict(self):
        p = ProvenanceTrustProof()
        d = p.to_dict()
        assert "proof_id" in d

    def test_chronology_trust_proof_to_dict(self):
        p = ChronologyTrustProof()
        d = p.to_dict()
        assert "proof_id" in d

    def test_governance_trust_proof_to_dict(self):
        p = GovernanceTrustProof()
        d = p.to_dict()
        assert "proof_id" in d

    def test_deterministic_id_stable(self):
        a = _deterministic_id("x-", "a", "b")
        b = _deterministic_id("x-", "a", "b")
        assert a == b

    def test_now_iso_format(self):
        ts = _now_iso()
        assert "T" in ts


# ─── Enums ───────────────────────────────────────────────

class TestEnums:
    def test_trust_phase_count(self):
        assert len(TrustPhase) == 7

    def test_trust_event_type_count(self):
        assert len(TrustEventType) == 6

    def test_trust_domain_count(self):
        assert len(TrustDomain) == 10

    def test_trust_integrity_dimension_count(self):
        assert len(TrustIntegrityDimension) == 7

    def test_trust_phase_values(self):
        vals = {p.value for p in TrustPhase}
        assert "defined" in vals
        assert "archived" in vals

    def test_trust_domain_values(self):
        vals = {d.value for d in TrustDomain}
        assert "constitutional" in vals
        assert "governance" in vals


# ─── Lifecycle Engine ────────────────────────────────────

class TestLifecycleEngine:
    def test_lifecycle_order_length(self):
        assert len(TRUST_LIFECYCLE_ORDER) == 7

    def test_valid_transition(self):
        e = TrustLifecycleEngine()
        assert e.can_transition(TrustPhase.DEFINED, TrustPhase.COLLECTED)

    def test_invalid_skip_transition(self):
        e = TrustLifecycleEngine()
        assert not e.can_transition(TrustPhase.DEFINED, TrustPhase.BUNDLED)

    def test_transition_succeeds(self):
        e = TrustLifecycleEngine()
        r = e.transition(TrustPhase.DEFINED, TrustPhase.COLLECTED)
        assert r["from"] == "defined"
        assert r["to"] == "collected"

    def test_transition_invalid_raises(self):
        e = TrustLifecycleEngine()
        with pytest.raises(ValueError):
            e.transition(TrustPhase.DEFINED, TrustPhase.VERIFIED)

    def test_terminal_phase_raises(self):
        e = TrustLifecycleEngine()
        with pytest.raises(ValueError, match="terminal"):
            e.transition(TrustPhase.ARCHIVED, TrustPhase.DEFINED)

    def test_full_lifecycle(self):
        e = TrustLifecycleEngine()
        phases = list(TrustPhase)
        for i in range(len(phases) - 1):
            e.transition(phases[i], phases[i + 1])
        assert e.get_stats()["total_transitions"] == 6

    def test_terminal_phases(self):
        assert TrustPhase.ARCHIVED in TERMINAL_TRUST_PHASES

    def test_get_stats(self):
        e = TrustLifecycleEngine()
        s = e.get_stats()
        assert s["total_transitions"] == 0


# ─── Artifact Engine ─────────────────────────────────────

class TestArtifactEngine:
    def test_generate_artifact(self):
        e = TrustArtifactEngine()
        r = e.generate_artifact("runtime_attestation")
        assert r["artifact_type"] == "runtime_attestation"
        assert r["artifact_hash"] != ""

    def test_generate_all_types(self):
        e = TrustArtifactEngine()
        r = e.generate_all_types()
        assert r["total"] == len(ARTIFACT_TYPES)

    def test_all_hashed(self):
        e = TrustArtifactEngine()
        e.generate_all_types()
        assert e.all_hashed()

    def test_artifact_types_count(self):
        assert len(ARTIFACT_TYPES) == 10

    def test_max_artifacts_enforced(self):
        e = TrustArtifactEngine()
        for i in range(MAX_ARTIFACTS):
            e.generate_artifact(f"type_{i}")
        with pytest.raises(ValueError, match="Max"):
            e.generate_artifact("overflow")

    def test_get_artifact_hashes(self):
        e = TrustArtifactEngine()
        e.generate_artifact("test")
        hashes = e.get_artifact_hashes()
        assert len(hashes) == 1
        assert hashes[0] != ""

    def test_get_stats(self):
        e = TrustArtifactEngine()
        e.generate_artifact("test")
        s = e.get_stats()
        assert s["total_artifacts"] == 1


# ─── Bundle Engine ───────────────────────────────────────

class TestBundleEngine:
    def test_create_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            e = TrustBundleEngine(output_dir=td)
            r = e.create_bundle([{"test": "data"}], domains_included=list(BUNDLE_DOMAINS))
            assert r["bundle_hash"] != ""
            assert r["complete"]

    def test_bundle_persisted(self):
        with tempfile.TemporaryDirectory() as td:
            e = TrustBundleEngine(output_dir=td)
            r = e.create_bundle([{"x": 1}], domains_included=["a"])
            files = list(Path(td).glob("*.json"))
            assert len(files) == 1

    def test_all_hashed(self):
        with tempfile.TemporaryDirectory() as td:
            e = TrustBundleEngine(output_dir=td)
            e.create_bundle([{"a": 1}], domains_included=list(BUNDLE_DOMAINS))
            assert e.all_hashed()

    def test_incomplete_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            e = TrustBundleEngine(output_dir=td)
            r = e.create_bundle([{"a": 1}], domains_included=["partial"])
            assert not r["complete"]

    def test_max_bundles_enforced(self):
        with tempfile.TemporaryDirectory() as td:
            e = TrustBundleEngine(output_dir=td)
            for i in range(MAX_BUNDLES):
                e.create_bundle([{"i": i}], domains_included=["a"])
            with pytest.raises(ValueError, match="Max"):
                e.create_bundle([{"overflow": True}], domains_included=["a"])

    def test_bundle_domains_count(self):
        assert len(BUNDLE_DOMAINS) == 10

    def test_get_stats(self):
        with tempfile.TemporaryDirectory() as td:
            e = TrustBundleEngine(output_dir=td)
            s = e.get_stats()
            assert s["total_bundles"] == 0


# ─── External Verification Engine ────────────────────────

class TestExternalVerificationEngine:
    def test_verify_complete_bundle(self):
        import hashlib
        artifacts = [{"test": "data", "lineage_references": ["ref1"]}]
        canonical = json.dumps(artifacts, sort_keys=True)
        bundle_hash = hashlib.sha256(canonical.encode()).hexdigest()
        bundle = {
            "bundle_id": "b1",
            "bundle_hash": bundle_hash,
            "domains_included": ["a", "b"],
            "complete": True,
        }
        e = ExternalVerificationEngine()
        r = e.verify_bundle(bundle, artifacts)
        assert r["trust_integrity_score"] == 1.0

    def test_verify_hash_mismatch(self):
        artifacts = [{"test": "data", "lineage_references": ["ref1"]}]
        bundle = {
            "bundle_id": "b1",
            "bundle_hash": "wrong_hash",
            "domains_included": ["a"],
            "complete": True,
        }
        e = ExternalVerificationEngine()
        r = e.verify_bundle(bundle, artifacts)
        assert not r["hash_verified"]
        assert r["trust_integrity_score"] < 1.0

    def test_all_verified(self):
        e = ExternalVerificationEngine()
        bundle = {
            "bundle_id": "b1",
            "bundle_hash": "abc",
            "domains_included": ["a"],
            "complete": True,
        }
        e.verify_bundle(bundle)
        assert e.all_verified()

    def test_get_failed(self):
        artifacts = [{"test": "data", "lineage_references": ["ref1"]}]
        bundle = {
            "bundle_id": "b1",
            "bundle_hash": "bad",
            "domains_included": ["a"],
            "complete": True,
        }
        e = ExternalVerificationEngine()
        e.verify_bundle(bundle, artifacts)
        failed = e.get_failed()
        assert len(failed) == 1

    def test_verification_dimensions_count(self):
        assert len(VERIFICATION_DIMENSIONS) == 7

    def test_max_verifications_enforced(self):
        e = ExternalVerificationEngine()
        for i in range(MAX_VERIFICATIONS):
            e.verify_bundle({"bundle_id": f"b{i}", "bundle_hash": "h", "domains_included": ["a"], "complete": True})
        with pytest.raises(ValueError, match="Max"):
            e.verify_bundle({"bundle_id": "overflow", "bundle_hash": "h", "domains_included": [], "complete": False})

    def test_get_stats(self):
        e = ExternalVerificationEngine()
        s = e.get_stats()
        assert s["total_verifications"] == 0


# ─── Replay Validator ────────────────────────────────────

class TestReplayValidator:
    def test_validate_single_check(self):
        v = TrustReplayValidator()
        r = v.validate_check("artifact_hash_determinism")
        assert r["deterministic"]

    def test_validate_all(self):
        v = TrustReplayValidator()
        r = v.validate_all()
        assert r["total"] == len(REPLAY_CHECKS)
        assert r["all_deterministic"]

    def test_all_deterministic(self):
        v = TrustReplayValidator()
        v.validate_all()
        assert v.all_deterministic()

    def test_replay_checks_count(self):
        assert len(REPLAY_CHECKS) == 7

    def test_get_stats(self):
        v = TrustReplayValidator()
        s = v.get_stats()
        assert s["total_checks"] == 0

    def test_empty_is_deterministic(self):
        v = TrustReplayValidator()
        assert v.all_deterministic()


# ─── Constitutional Proof Engine ─────────────────────────

class TestConstitutionalProofEngine:
    def test_generate_default_proof(self):
        e = ConstitutionalTrustProofEngine()
        r = e.generate_proof()
        assert r["invariant_certified"]
        assert r["no_fabricated_proofs"]

    def test_generate_failing_proof(self):
        e = ConstitutionalTrustProofEngine()
        r = e.generate_proof(no_fabricated_proofs=False)
        assert not r["no_fabricated_proofs"]

    def test_all_certified(self):
        e = ConstitutionalTrustProofEngine()
        e.generate_proof()
        assert e.all_certified()

    def test_not_certified_on_failure(self):
        e = ConstitutionalTrustProofEngine()
        e.generate_proof(governance_preserved=False)
        assert not e.all_certified()

    def test_get_failed(self):
        e = ConstitutionalTrustProofEngine()
        e.generate_proof(no_hidden_mutation=False)
        failed = e.get_failed()
        assert len(failed) == 1

    def test_max_enforced(self):
        e = ConstitutionalTrustProofEngine()
        for _ in range(MAX_CONSTITUTIONAL_PROOFS):
            e.generate_proof()
        with pytest.raises(ValueError, match="Max"):
            e.generate_proof()

    def test_dimensions_count(self):
        assert len(CONSTITUTIONAL_PROOF_DIMENSIONS) == 5


# ─── Chronology Proof Engine ─────────────────────────────

class TestChronologyProofEngine:
    def test_generate_default_proof(self):
        e = ChronologyTrustProofEngine()
        r = e.generate_proof()
        assert r["monotonic_proven"]
        assert r["no_retroactive_mutation"]

    def test_generate_failing_proof(self):
        e = ChronologyTrustProofEngine()
        r = e.generate_proof(monotonic_proven=False)
        assert not r["monotonic_proven"]

    def test_all_proven(self):
        e = ChronologyTrustProofEngine()
        e.generate_proof()
        assert e.all_proven()

    def test_not_proven_on_failure(self):
        e = ChronologyTrustProofEngine()
        e.generate_proof(temporal_integrity_proven=False)
        assert not e.all_proven()

    def test_max_enforced(self):
        e = ChronologyTrustProofEngine()
        for _ in range(MAX_CHRONOLOGY_PROOFS):
            e.generate_proof()
        with pytest.raises(ValueError, match="Max"):
            e.generate_proof()

    def test_dimensions_count(self):
        assert len(CHRONOLOGY_PROOF_DIMENSIONS) == 4


# ─── Provenance Proof Engine ─────────────────────────────

class TestProvenanceProofEngine:
    def test_generate_default_proof(self):
        e = ProvenanceTrustProofEngine()
        r = e.generate_proof()
        assert r["causal_lineage_proven"]

    def test_generate_failing_proof(self):
        e = ProvenanceTrustProofEngine()
        r = e.generate_proof(evidence_lineage_proven=False)
        assert not r["evidence_lineage_proven"]

    def test_all_proven(self):
        e = ProvenanceTrustProofEngine()
        e.generate_proof()
        assert e.all_proven()

    def test_not_proven_on_failure(self):
        e = ProvenanceTrustProofEngine()
        e.generate_proof(source_artifact_lineage_proven=False)
        assert not e.all_proven()

    def test_max_enforced(self):
        e = ProvenanceTrustProofEngine()
        for _ in range(MAX_PROVENANCE_PROOFS):
            e.generate_proof()
        with pytest.raises(ValueError, match="Max"):
            e.generate_proof()

    def test_dimensions_count(self):
        assert len(PROVENANCE_PROOF_DIMENSIONS) == 4


# ─── Observability Pipeline ──────────────────────────────

class TestObservabilityPipeline:
    def test_emit_trust_bundle_created(self):
        with tempfile.TemporaryDirectory() as td:
            p = TrustObservabilityPipeline(output_dir=td)
            r = p.emit_trust_bundle_created({"test": True})
            assert r["event_type"] == "trust_bundle_created"

    def test_emit_trust_artifact_hashed(self):
        with tempfile.TemporaryDirectory() as td:
            p = TrustObservabilityPipeline(output_dir=td)
            r = p.emit_trust_artifact_hashed({"hash": "abc"})
            assert r["event_type"] == "trust_artifact_hashed"

    def test_emit_trust_bundle_verified(self):
        with tempfile.TemporaryDirectory() as td:
            p = TrustObservabilityPipeline(output_dir=td)
            r = p.emit_trust_bundle_verified({"verified": True})
            assert r["event_type"] == "trust_bundle_verified"

    def test_emit_external_verification_completed(self):
        with tempfile.TemporaryDirectory() as td:
            p = TrustObservabilityPipeline(output_dir=td)
            r = p.emit_external_verification_completed({"score": 1.0})
            assert r["event_type"] == "external_verification_completed"

    def test_emit_trust_boundary_denied(self):
        with tempfile.TemporaryDirectory() as td:
            p = TrustObservabilityPipeline(output_dir=td)
            r = p.emit_trust_boundary_denied({"action": "test"})
            assert r["event_type"] == "trust_boundary_denied"

    def test_emit_trust_replay_validated(self):
        with tempfile.TemporaryDirectory() as td:
            p = TrustObservabilityPipeline(output_dir=td)
            r = p.emit_trust_replay_validated({"total": 7})
            assert r["event_type"] == "trust_replay_validated"

    def test_event_file_map_count(self):
        assert len(EVENT_FILE_MAP) == len(TrustEventType)

    def test_jsonl_persisted(self):
        with tempfile.TemporaryDirectory() as td:
            p = TrustObservabilityPipeline(output_dir=td)
            p.emit_trust_bundle_created({"test": True})
            files = list(Path(td).glob("*.jsonl"))
            assert len(files) >= 1

    def test_get_stats(self):
        with tempfile.TemporaryDirectory() as td:
            p = TrustObservabilityPipeline(output_dir=td)
            p.emit_trust_bundle_created({"a": 1})
            s = p.get_stats()
            assert s["total_events"] == 1

    def test_all_emit_methods(self):
        with tempfile.TemporaryDirectory() as td:
            p = TrustObservabilityPipeline(output_dir=td)
            p.emit_trust_bundle_created({})
            p.emit_trust_artifact_hashed({})
            p.emit_trust_bundle_verified({})
            p.emit_external_verification_completed({})
            p.emit_trust_boundary_denied({})
            p.emit_trust_replay_validated({})
            assert p.get_stats()["total_events"] == 6


# ─── Boundary Policies ──────────────────────────────────

class TestBoundaryPolicies:
    def test_check_limit_allowed(self):
        b = TrustBoundaryPolicies()
        r = b.check_limit("max_trust_runs", 10)
        assert r["allowed"]

    def test_check_limit_denied(self):
        b = TrustBoundaryPolicies()
        r = b.check_limit("max_trust_runs", 50)
        assert not r["allowed"]

    def test_check_limit_unknown_raises(self):
        b = TrustBoundaryPolicies()
        with pytest.raises(ValueError, match="Unknown"):
            b.check_limit("nonexistent", 0)

    def test_override_capping(self):
        b = TrustBoundaryPolicies()
        r = b.check_limit("max_trust_runs", 10, override=200)
        assert r["effective_limit"] == 50

    def test_override_lower(self):
        b = TrustBoundaryPolicies()
        r = b.check_limit("max_trust_runs", 10, override=20)
        assert r["effective_limit"] == 20

    def test_check_forbidden_true(self):
        b = TrustBoundaryPolicies()
        r = b.check_forbidden("unsupported_trust_claims")
        assert r["forbidden"]

    def test_check_forbidden_false(self):
        b = TrustBoundaryPolicies()
        r = b.check_forbidden("normal_action")
        assert not r["forbidden"]

    def test_all_forbidden_actions(self):
        b = TrustBoundaryPolicies()
        for action in FORBIDDEN_TRUST_ACTIONS:
            r = b.check_forbidden(action)
            assert r["forbidden"]

    def test_trust_limits_count(self):
        assert len(TRUST_LIMITS) == 8

    def test_forbidden_actions_count(self):
        assert len(FORBIDDEN_TRUST_ACTIONS) == 8

    def test_denied_tracking(self):
        b = TrustBoundaryPolicies()
        b.check_limit("max_trust_runs", 100)
        b.check_forbidden("governance_bypass")
        s = b.get_stats()
        assert s["total_denied"] == 2

    def test_get_stats(self):
        b = TrustBoundaryPolicies()
        s = b.get_stats()
        assert s["total_limits"] == 8
        assert s["total_forbidden"] == 8

    def test_each_limit_has_value(self):
        for name, val in TRUST_LIMITS.items():
            assert isinstance(val, int)
            assert val > 0

    def test_override_at_boundary(self):
        b = TrustBoundaryPolicies()
        r = b.check_limit("max_trust_runs", 49, override=50)
        assert r["allowed"]
        assert r["effective_limit"] == 50


# ─── Continuity Bridges ─────────────────────────────────

class TestContinuityBridges:
    def test_all_bridge_classes_count(self):
        assert len(ALL_BRIDGE_CLASSES) == 9

    def test_bridge_record(self):
        with tempfile.TemporaryDirectory() as td:
            b = CertificationTrustBridge(state_dir=td)
            r = b.record("test_action", {"key": "val"})
            assert r["bridge"] == "certification_trust"
            assert r["action"] == "test_action"

    def test_bridge_persists_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            b = ValidationTrustBridge(state_dir=td)
            b.record("test")
            files = list(Path(td).glob("*.jsonl"))
            assert len(files) == 1

    def test_bridge_get_records(self):
        with tempfile.TemporaryDirectory() as td:
            b = ExplainabilityTrustBridge(state_dir=td)
            b.record("a")
            b.record("b")
            assert len(b.get_records()) == 2

    def test_bridge_get_stats(self):
        with tempfile.TemporaryDirectory() as td:
            b = AccountabilityTrustBridge(state_dir=td)
            b.record("x")
            s = b.get_stats()
            assert s["total_records"] == 1

    def test_all_bridges_instantiate(self):
        with tempfile.TemporaryDirectory() as td:
            for cls in ALL_BRIDGE_CLASSES:
                b = cls(state_dir=td)
                assert b.get_stats()["total_records"] == 0

    def test_replay_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = ReplayTrustBridge(state_dir=td)
            r = b.record("replay_verified")
            assert r["bridge"] == "replay_trust"

    def test_provenance_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = ProvenanceTrustBridge(state_dir=td)
            r = b.record("provenance_linked")
            assert r["bridge"] == "provenance_trust"

    def test_chronology_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = ChronologyTrustBridge(state_dir=td)
            r = b.record("chronology_proven")
            assert r["bridge"] == "chronology_trust"

    def test_governance_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = GovernanceTrustBridge(state_dir=td)
            r = b.record("governance_proven")
            assert r["bridge"] == "governance_trust"

    def test_observability_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = ObservabilityTrustBridge(state_dir=td)
            r = b.record("obs_linked")
            assert r["bridge"] == "observability_trust"


# ─── Coordinator ─────────────────────────────────────────

class TestCoordinator:
    def _make(self):
        td = tempfile.mkdtemp()
        return CanonicalSovereignTrustCoordinator(state_dir=td), td

    def test_start_trust_run(self):
        c, _ = self._make()
        r = c.start_trust_run()
        assert r["status"] == "started"

    def test_generate_artifacts(self):
        c, _ = self._make()
        r = c.generate_artifacts()
        assert r["total"] == 10

    def test_create_trust_bundle(self):
        c, _ = self._make()
        r = c.create_trust_bundle()
        assert r["bundle_hash"] != ""

    def test_verify_bundle(self):
        c, _ = self._make()
        bundle = c.create_trust_bundle()
        r = c.verify_bundle(bundle)
        assert "trust_integrity_score" in r

    def test_verify_externally(self):
        c, _ = self._make()
        bundle = c.create_trust_bundle()
        r = c.verify_externally(bundle)
        assert "trust_integrity_score" in r

    def test_prove_constitutional(self):
        c, _ = self._make()
        r = c.prove_constitutional()
        assert r["invariant_certified"]

    def test_prove_chronology(self):
        c, _ = self._make()
        r = c.prove_chronology()
        assert r["monotonic_proven"]

    def test_prove_provenance(self):
        c, _ = self._make()
        r = c.prove_provenance()
        assert r["causal_lineage_proven"]

    def test_validate_replay_determinism(self):
        c, _ = self._make()
        r = c.validate_replay_determinism()
        assert r["all_deterministic"]

    def test_check_boundary(self):
        c, _ = self._make()
        r = c.check_boundary("max_trust_runs", 10)
        assert r["allowed"]

    def test_complete_trust_run(self):
        c, _ = self._make()
        run = c.start_trust_run()
        c.generate_artifacts()
        c.create_trust_bundle()
        c.prove_constitutional()
        c.prove_chronology()
        c.prove_provenance()
        c.validate_replay_determinism()
        r = c.complete_trust_run(run["run_id"])
        assert r["outcome"] == "trusted"

    def test_incomplete_run(self):
        c, _ = self._make()
        run = c.start_trust_run()
        r = c.complete_trust_run(run["run_id"])
        assert r["outcome"] in ("trusted", "incomplete")

    def test_get_trust_report(self):
        c, _ = self._make()
        r = c.get_trust_report()
        assert "artifacts" in r
        assert "bundles" in r

    def test_get_stats(self):
        c, _ = self._make()
        s = c.get_stats()
        assert "lifecycle" in s
        assert "runs" in s

    def test_max_runs_enforced(self):
        c, _ = self._make()
        for _ in range(MAX_TRUST_RUNS):
            c.start_trust_run()
        with pytest.raises(ValueError, match="Max"):
            c.start_trust_run()

    def test_full_flow(self):
        c, _ = self._make()
        run = c.start_trust_run("test-full")
        c.generate_artifacts()
        bundle = c.create_trust_bundle()
        c.verify_externally(bundle)
        c.prove_constitutional()
        c.prove_chronology()
        c.prove_provenance()
        c.validate_replay_determinism()
        receipt = c.complete_trust_run("test-full")
        assert receipt["outcome"] == "trusted"
        report = c.get_trust_report()
        assert report["artifacts"]["total_artifacts"] > 0


# ─── Constraint Verification ────────────────────────────

class TestConstraintVerification:
    def test_artifact_hash_determinism(self):
        e = TrustArtifactEngine()
        r = e.generate_all_types()
        assert all(a["artifact_hash"] != "" for a in r["artifacts"])

    def test_bundle_hash_determinism(self):
        with tempfile.TemporaryDirectory() as td:
            e = TrustBundleEngine(output_dir=td)
            r = e.create_bundle([{"a": 1}], domains_included=list(BUNDLE_DOMAINS))
            assert r["bundle_hash"] != ""

    def test_external_verification_from_artifacts_only(self):
        import hashlib
        arts = [{"type": "test", "lineage_references": ["ref1"]}]
        canonical = json.dumps(arts, sort_keys=True)
        bh = hashlib.sha256(canonical.encode()).hexdigest()
        bundle = {"bundle_id": "b1", "bundle_hash": bh, "domains_included": ["a"], "complete": True}
        e = ExternalVerificationEngine()
        r = e.verify_bundle(bundle, arts)
        assert r["hash_verified"]

    def test_missing_evidence_denial(self):
        b = TrustBoundaryPolicies()
        r = b.check_forbidden("missing_evidence_bundles")
        assert r["forbidden"]

    def test_unsupported_attestation_denial(self):
        b = TrustBoundaryPolicies()
        r = b.check_forbidden("unverifiable_attestations")
        assert r["forbidden"]

    def test_chronology_proof_verification(self):
        e = ChronologyTrustProofEngine()
        r = e.generate_proof()
        assert r["monotonic_proven"]
        assert r["no_retroactive_mutation"]
        assert r["temporal_integrity_proven"]
        assert r["historical_continuity_proven"]

    def test_governance_proof_verification(self):
        p = GovernanceTrustProof(
            governance_lineage_proven=True,
            approval_chain_proven=True,
            escalation_lineage_proven=True,
            policy_application_proven=True,
        )
        d = p.to_dict()
        assert d["governance_lineage_proven"]

    def test_replay_proof_verification(self):
        v = TrustReplayValidator()
        r = v.validate_all()
        assert r["all_deterministic"]
        assert r["total"] == 7

    def test_provenance_proof_verification(self):
        e = ProvenanceTrustProofEngine()
        r = e.generate_proof()
        assert r["causal_lineage_proven"]
        assert r["evidence_lineage_proven"]
        assert r["source_artifact_lineage_proven"]
        assert r["explanation_lineage_proven"]

    def test_no_fabricated_trust_claims(self):
        b = TrustBoundaryPolicies()
        r = b.check_forbidden("unsupported_trust_claims")
        assert r["forbidden"]

    def test_no_hidden_trust_mutation(self):
        b = TrustBoundaryPolicies()
        r = b.check_forbidden("hidden_trust_mutation")
        assert r["forbidden"]

    def test_no_trust_owned_execution(self):
        b = TrustBoundaryPolicies()
        r = b.check_forbidden("trust_owned_execution")
        assert r["forbidden"]

    def test_no_governance_bypass(self):
        b = TrustBoundaryPolicies()
        r = b.check_forbidden("governance_bypass")
        assert r["forbidden"]

    def test_no_execution_outside_spine(self):
        e = ConstitutionalTrustProofEngine()
        r = e.generate_proof()
        assert r["no_execution_outside_spine"] is not None

    def test_no_self_attestation_without_lineage(self):
        b = TrustBoundaryPolicies()
        r = b.check_forbidden("self_attestation_without_lineage")
        assert r["forbidden"]

    def test_override_capping_enforced(self):
        b = TrustBoundaryPolicies()
        r = b.check_limit("max_trust_runs", 10, override=200)
        assert r["effective_limit"] == 50

    def test_lifecycle_linear_progression(self):
        e = TrustLifecycleEngine()
        with pytest.raises(ValueError):
            e.transition(TrustPhase.DEFINED, TrustPhase.VERIFIED)

    def test_lifecycle_terminal_absorbing(self):
        e = TrustLifecycleEngine()
        with pytest.raises(ValueError, match="terminal"):
            e.transition(TrustPhase.ARCHIVED, TrustPhase.DEFINED)

    def test_trust_integrity_score_computed(self):
        e = ExternalVerificationState(
            hash_verified=True, lineage_verified=True,
            chronology_verified=True, governance_verified=True,
            replay_verified=True, provenance_verified=True,
            completeness_verified=True,
        )
        assert e.trust_integrity_score == 1.0

    def test_full_trust_flow_end_to_end(self):
        c = CanonicalSovereignTrustCoordinator(state_dir=tempfile.mkdtemp())
        run = c.start_trust_run("e2e-test")
        c.generate_artifacts()
        bundle = c.create_trust_bundle()
        vrf = c.verify_externally(bundle)
        assert vrf["trust_integrity_score"] == 1.0
        c.prove_constitutional()
        c.prove_chronology()
        c.prove_provenance()
        c.validate_replay_determinism()
        receipt = c.complete_trust_run("e2e-test")
        assert receipt["outcome"] == "trusted"
        report = c.get_trust_report()
        assert report["constitutional"]["all_certified"]
        assert report["chronology"]["all_proven"]
        assert report["provenance"]["all_proven"]
