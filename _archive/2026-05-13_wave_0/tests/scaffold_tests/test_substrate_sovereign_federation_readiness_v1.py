"""Tests for Phase 96.8CN — Substrate Sovereign Federation Readiness.

Covers: contracts, enums, lifecycle, identity engine, peer recognition,
trust exchange, topology manifest, capability manifest, interoperability,
observability pipeline, replay validator, boundary policies, continuity
bridges, coordinator, constraint verification.
"""

import sys
import tempfile
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import pytest

from core.federation.sovereign_federation_readiness_contracts_v1 import (
    SovereignRuntimeIdentity,
    FederationReadinessState,
    FederationTrustExchange,
    RuntimeRecognitionState,
    FederationTopologyManifest,
    FederationBoundaryState,
    FederationVerificationReceipt,
    FederationInteroperabilityState,
    CrossRuntimeTrustBundle,
    CrossRuntimeLineageReference,
    FederationContinuityState,
    FederationReplayState,
    FederationObservabilityState,
    FederationCapabilityManifest,
    SovereignPeerManifest,
    FederationPhase,
    FederationEventType,
    PeerTrustStatus,
    FederationDomain,
    _now_iso,
    _deterministic_id,
)
from core.federation.federation_lifecycle_engine_v1 import (
    FederationLifecycleEngine,
    FEDERATION_LIFECYCLE_ORDER,
    VALID_TRANSITIONS,
    TERMINAL_FEDERATION_PHASES,
)
from core.federation.sovereign_runtime_identity_engine_v1 import (
    SovereignRuntimeIdentityEngine,
    MAX_IDENTITIES,
)
from core.federation.peer_recognition_engine_v1 import (
    PeerRecognitionEngine,
    MAX_RECOGNITIONS,
)
from core.federation.federation_trust_exchange_engine_v1 import (
    FederationTrustExchangeEngine,
    EXCHANGE_PROOF_TYPES,
    MAX_EXCHANGES,
)
from core.federation.federation_topology_manifest_engine_v1 import (
    FederationTopologyManifestEngine,
    FORBIDDEN_EXPOSURES,
    MAX_MANIFESTS,
)
from core.federation.cross_runtime_capability_manifest_engine_v1 import (
    CrossRuntimeCapabilityManifestEngine,
    FORBIDDEN_CAPABILITIES,
    ALLOWED_INTERACTION_TYPES,
    MAX_CAPABILITY_MANIFESTS,
)
from core.federation.federation_interoperability_engine_v1 import (
    FederationInteroperabilityEngine,
    FORBIDDEN_INTEROP_ACTIONS,
    MAX_INTEROP_REPORTS,
)
from core.federation.federation_observability_pipeline_v1 import (
    FederationObservabilityPipeline,
    EVENT_FILE_MAP,
)
from core.federation.federation_replay_validator_v1 import (
    FederationReplayValidator,
    REPLAY_CHECKS,
)
from core.federation.federation_boundary_policies_v1 import (
    FederationBoundaryPolicies,
    FEDERATION_LIMITS,
    FORBIDDEN_FEDERATION_ACTIONS,
)
from core.federation.federation_continuity_bridges_v1 import (
    TrustFederationBridge,
    CertificationFederationBridge,
    ValidationFederationBridge,
    AccountabilityFederationBridge,
    ExplainabilityFederationBridge,
    TopologyFederationBridge,
    ObservabilityFederationBridge,
    ReplayFederationBridge,
    GovernanceFederationBridge,
    ALL_BRIDGE_CLASSES,
)
from core.federation.canonical_sovereign_federation_readiness_coordinator_v1 import (
    CanonicalSovereignFederationReadinessCoordinator,
    MAX_FEDERATION_RUNS,
)


def _valid_peer_manifest():
    return {
        "runtime_id": "peer-001",
        "runtime_fingerprint": "fp-abc123",
        "trust_bundle_hash": "hash-trust",
        "topology_manifest_hash": "hash-topo",
        "capability_manifest_hash": "hash-cap",
        "boundary_declarations": ["no_peer_execution", "no_authority_transfer"],
    }


def _minimal_peer_manifest():
    return {"runtime_id": "peer-min", "runtime_fingerprint": "fp-min"}


def _invalid_peer_manifest():
    return {"runtime_id": ""}


# ─── Contracts ───────────────────────────────────────────

class TestContracts:
    def test_sovereign_runtime_identity(self):
        s = SovereignRuntimeIdentity()
        d = s.to_dict()
        assert "runtime_id" in d

    def test_federation_readiness_state(self):
        s = FederationReadinessState()
        d = s.to_dict()
        assert d["phase"] == "identity_created"

    def test_federation_trust_exchange(self):
        s = FederationTrustExchange(local_runtime_id="l1", peer_runtime_id="p1")
        d = s.to_dict()
        assert d["local_runtime_id"] == "l1"

    def test_runtime_recognition_state(self):
        s = RuntimeRecognitionState(peer_runtime_id="p1")
        d = s.to_dict()
        assert d["trust_status"] == "unknown"

    def test_federation_topology_manifest(self):
        s = FederationTopologyManifest(runtime_id="r1")
        d = s.to_dict()
        assert d["runtime_id"] == "r1"

    def test_federation_boundary_state(self):
        s = FederationBoundaryState(action="test")
        d = s.to_dict()
        assert d["action"] == "test"

    def test_federation_verification_receipt(self):
        s = FederationVerificationReceipt(run_id="run1")
        d = s.to_dict()
        assert d["outcome"] == "incomplete"

    def test_federation_interoperability_state(self):
        s = FederationInteroperabilityState(local_runtime_id="l1", peer_runtime_id="p1")
        d = s.to_dict()
        assert d["local_runtime_id"] == "l1"

    def test_cross_runtime_trust_bundle(self):
        s = CrossRuntimeTrustBundle(source_runtime_id="r1")
        d = s.to_dict()
        assert d["source_runtime_id"] == "r1"

    def test_cross_runtime_lineage_reference(self):
        s = CrossRuntimeLineageReference(source_runtime_id="r1", lineage_type="governance")
        d = s.to_dict()
        assert d["lineage_type"] == "governance"

    def test_federation_continuity_state(self):
        s = FederationContinuityState(federation_session_id="s1")
        d = s.to_dict()
        assert d["federation_session_id"] == "s1"

    def test_federation_replay_state(self):
        s = FederationReplayState(check_name="test_check")
        d = s.to_dict()
        assert d["deterministic"]

    def test_federation_observability_state(self):
        s = FederationObservabilityState(event_type="test")
        d = s.to_dict()
        assert d["event_type"] == "test"

    def test_federation_capability_manifest(self):
        s = FederationCapabilityManifest(runtime_id="r1")
        d = s.to_dict()
        assert d["runtime_id"] == "r1"

    def test_sovereign_peer_manifest(self):
        s = SovereignPeerManifest(runtime_id="r1", runtime_fingerprint="fp1")
        d = s.to_dict()
        assert d["runtime_fingerprint"] == "fp1"

    def test_deterministic_id_stable(self):
        a = _deterministic_id("x-", "a", "b")
        b = _deterministic_id("x-", "a", "b")
        assert a == b

    def test_now_iso_format(self):
        ts = _now_iso()
        assert "T" in ts


# ─── Enums ───────────────────────────────────────────────

class TestEnums:
    def test_federation_phase_count(self):
        assert len(FederationPhase) == 7

    def test_federation_event_type_count(self):
        assert len(FederationEventType) == 9

    def test_peer_trust_status_count(self):
        assert len(PeerTrustStatus) == 6

    def test_federation_domain_count(self):
        assert len(FederationDomain) == 8

    def test_peer_status_values(self):
        vals = {s.value for s in PeerTrustStatus}
        assert "unknown" in vals
        assert "verified" in vals
        assert "rejected" in vals
        assert "expired" in vals

    def test_federation_phase_values(self):
        vals = {p.value for p in FederationPhase}
        assert "identity_created" in vals
        assert "archived" in vals


# ─── Lifecycle Engine ────────────────────────────────────

class TestLifecycleEngine:
    def test_valid_transition_identity_to_manifest(self):
        e = FederationLifecycleEngine()
        assert e.can_transition(FederationPhase.IDENTITY_CREATED, FederationPhase.MANIFEST_GENERATED)

    def test_valid_transition_peer_received_to_verified(self):
        e = FederationLifecycleEngine()
        assert e.can_transition(FederationPhase.PEER_RECEIVED, FederationPhase.PEER_VERIFIED)

    def test_valid_transition_peer_received_to_rejected(self):
        e = FederationLifecycleEngine()
        assert e.can_transition(FederationPhase.PEER_RECEIVED, FederationPhase.PEER_REJECTED)

    def test_invalid_skip_transition(self):
        e = FederationLifecycleEngine()
        assert not e.can_transition(FederationPhase.IDENTITY_CREATED, FederationPhase.PEER_VERIFIED)

    def test_transition_succeeds(self):
        e = FederationLifecycleEngine()
        r = e.transition(FederationPhase.IDENTITY_CREATED, FederationPhase.MANIFEST_GENERATED)
        assert r["from"] == "identity_created"
        assert r["to"] == "manifest_generated"

    def test_transition_invalid_raises(self):
        e = FederationLifecycleEngine()
        with pytest.raises(ValueError):
            e.transition(FederationPhase.IDENTITY_CREATED, FederationPhase.ARCHIVED)

    def test_terminal_phase_raises(self):
        e = FederationLifecycleEngine()
        with pytest.raises(ValueError, match="terminal"):
            e.transition(FederationPhase.ARCHIVED, FederationPhase.IDENTITY_CREATED)

    def test_rejected_to_archived(self):
        e = FederationLifecycleEngine()
        r = e.transition(FederationPhase.PEER_REJECTED, FederationPhase.ARCHIVED)
        assert r["to"] == "archived"

    def test_get_stats(self):
        e = FederationLifecycleEngine()
        s = e.get_stats()
        assert s["total_transitions"] == 0


# ─── Identity Engine ────────────────────────────────────

class TestIdentityEngine:
    def test_create_identity(self):
        with tempfile.TemporaryDirectory() as td:
            e = SovereignRuntimeIdentityEngine(output_dir=td)
            r = e.create_identity(trust_bundle_ref="tb-ref")
            assert r["runtime_fingerprint"] != ""
            assert r["verification_hash"] != ""

    def test_identity_persisted(self):
        with tempfile.TemporaryDirectory() as td:
            e = SovereignRuntimeIdentityEngine(output_dir=td)
            e.create_identity(runtime_id="test-id")
            files = list(Path(td).glob("*.json"))
            assert len(files) == 1

    def test_get_current_identity(self):
        with tempfile.TemporaryDirectory() as td:
            e = SovereignRuntimeIdentityEngine(output_dir=td)
            e.create_identity()
            assert e.get_current_identity() is not None

    def test_no_identity_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            e = SovereignRuntimeIdentityEngine(output_dir=td)
            assert e.get_current_identity() is None

    def test_all_fingerprinted(self):
        with tempfile.TemporaryDirectory() as td:
            e = SovereignRuntimeIdentityEngine(output_dir=td)
            e.create_identity()
            assert e.all_fingerprinted()

    def test_max_identities_enforced(self):
        with tempfile.TemporaryDirectory() as td:
            e = SovereignRuntimeIdentityEngine(output_dir=td)
            for i in range(MAX_IDENTITIES):
                e.create_identity(runtime_id=f"id-{i}")
            with pytest.raises(ValueError, match="Max"):
                e.create_identity()

    def test_get_stats(self):
        with tempfile.TemporaryDirectory() as td:
            e = SovereignRuntimeIdentityEngine(output_dir=td)
            e.create_identity()
            s = e.get_stats()
            assert s["total_identities"] == 1


# ─── Peer Recognition Engine ────────────────────────────

class TestPeerRecognitionEngine:
    def test_recognize_valid_peer(self):
        e = PeerRecognitionEngine()
        r = e.recognize_peer(_valid_peer_manifest())
        assert r["trust_status"] == "recognized"

    def test_reject_invalid_peer(self):
        e = PeerRecognitionEngine()
        r = e.recognize_peer(_invalid_peer_manifest())
        assert r["trust_status"] == "rejected"

    def test_untrusted_peer_no_trust_hash(self):
        e = PeerRecognitionEngine()
        r = e.recognize_peer(_minimal_peer_manifest())
        assert r["trust_status"] == "untrusted"

    def test_verify_valid_peer(self):
        e = PeerRecognitionEngine()
        r = e.verify_peer(_valid_peer_manifest())
        assert r["trust_status"] == "verified"

    def test_verify_incomplete_peer(self):
        e = PeerRecognitionEngine()
        r = e.verify_peer(_minimal_peer_manifest())
        assert r["trust_status"] == "untrusted"

    def test_reject_expired_peer(self):
        e = PeerRecognitionEngine()
        r = e.reject_expired_peer("expired-peer")
        assert r["trust_status"] == "expired"

    def test_get_by_status(self):
        e = PeerRecognitionEngine()
        e.verify_peer(_valid_peer_manifest())
        e.recognize_peer(_invalid_peer_manifest())
        verified = e.get_by_status("verified")
        assert len(verified) == 1

    def test_get_stats(self):
        e = PeerRecognitionEngine()
        e.recognize_peer(_valid_peer_manifest())
        s = e.get_stats()
        assert s["total_recognitions"] == 1


# ─── Trust Exchange Engine ───────────────────────────────

class TestTrustExchangeEngine:
    def test_exchange_trust_verified(self):
        e = FederationTrustExchangeEngine()
        r = e.exchange_trust("local1", "peer1", {
            "trust_bundle_hash": "h1",
            "constitutional_proof_hash": "h2",
        })
        assert r["verified"]

    def test_exchange_trust_unverified(self):
        e = FederationTrustExchangeEngine()
        r = e.exchange_trust("local1", "peer1", {"trust_bundle_hash": "h1"})
        assert not r["verified"]

    def test_all_verified(self):
        e = FederationTrustExchangeEngine()
        e.exchange_trust("l", "p", {"trust_bundle_hash": "h1", "constitutional_proof_hash": "h2"})
        assert e.all_verified()

    def test_get_unverified(self):
        e = FederationTrustExchangeEngine()
        e.exchange_trust("l", "p", {"trust_bundle_hash": "h1"})
        assert len(e.get_unverified()) == 1

    def test_exchange_proof_types_count(self):
        assert len(EXCHANGE_PROOF_TYPES) == 6

    def test_get_stats(self):
        e = FederationTrustExchangeEngine()
        s = e.get_stats()
        assert s["total_exchanges"] == 0


# ─── Topology Manifest Engine ───────────────────────────

class TestTopologyManifestEngine:
    def test_generate_manifest(self):
        e = FederationTopologyManifestEngine()
        r = e.generate_manifest("r1")
        assert r["runtime_id"] == "r1"
        assert len(r["boundary_declarations"]) > 0

    def test_validate_manifest_valid(self):
        e = FederationTopologyManifestEngine()
        m = e.generate_manifest("r1")
        v = e.validate_manifest(m)
        assert v["valid"]

    def test_validate_manifest_invalid(self):
        e = FederationTopologyManifestEngine()
        v = e.validate_manifest({"runtime_id": ""})
        assert not v["valid"]

    def test_compute_manifest_hash(self):
        e = FederationTopologyManifestEngine()
        h = e.compute_manifest_hash({"a": 1})
        assert len(h) == 64

    def test_forbidden_exposures_count(self):
        assert len(FORBIDDEN_EXPOSURES) == 5

    def test_get_stats(self):
        e = FederationTopologyManifestEngine()
        s = e.get_stats()
        assert s["total_manifests"] == 0


# ─── Capability Manifest Engine ──────────────────────────

class TestCapabilityManifestEngine:
    def test_generate_manifest(self):
        e = CrossRuntimeCapabilityManifestEngine()
        r = e.generate_manifest("r1")
        assert r["runtime_id"] == "r1"

    def test_validate_manifest_valid(self):
        e = CrossRuntimeCapabilityManifestEngine()
        m = e.generate_manifest("r1")
        v = e.validate_manifest(m)
        assert v["valid"]
        assert v["no_forbidden_capabilities"]

    def test_validate_manifest_with_forbidden(self):
        e = CrossRuntimeCapabilityManifestEngine()
        m = {"runtime_id": "r1", "capability_categories": ["a"], "allowed_interaction_types": ["peer_direct_execution"], "boundary_limits": ["b"]}
        v = e.validate_manifest(m)
        assert not v["no_forbidden_capabilities"]
        assert not v["valid"]

    def test_check_forbidden(self):
        e = CrossRuntimeCapabilityManifestEngine()
        assert e.check_forbidden("peer_direct_execution")
        assert not e.check_forbidden("manifest_inspection")

    def test_forbidden_capabilities_count(self):
        assert len(FORBIDDEN_CAPABILITIES) == 4

    def test_allowed_interaction_types_count(self):
        assert len(ALLOWED_INTERACTION_TYPES) == 5

    def test_get_stats(self):
        e = CrossRuntimeCapabilityManifestEngine()
        s = e.get_stats()
        assert s["total_manifests"] == 0


# ─── Interoperability Engine ─────────────────────────────

class TestInteroperabilityEngine:
    def test_generate_compatible_report(self):
        e = FederationInteroperabilityEngine()
        r = e.generate_report("l1", "p1", local_trust_hash="h1", peer_trust_hash="h2", local_topology={"a": 1}, peer_topology={"b": 2})
        assert r["trust_compatible"]
        assert r["topology_compatible"]

    def test_generate_incompatible_report(self):
        e = FederationInteroperabilityEngine()
        r = e.generate_report("l1", "p1")
        assert not r["trust_compatible"]

    def test_check_forbidden(self):
        e = FederationInteroperabilityEngine()
        r = e.check_forbidden("execute_peer_task")
        assert r["forbidden"]

    def test_check_allowed(self):
        e = FederationInteroperabilityEngine()
        r = e.check_forbidden("inspect_manifest")
        assert not r["forbidden"]

    def test_forbidden_interop_actions_count(self):
        assert len(FORBIDDEN_INTEROP_ACTIONS) == 5

    def test_all_compatible(self):
        e = FederationInteroperabilityEngine()
        e.generate_report("l1", "p1", local_trust_hash="h1", peer_trust_hash="h2", local_topology={"a": 1}, peer_topology={"b": 2})
        assert e.all_compatible()

    def test_get_stats(self):
        e = FederationInteroperabilityEngine()
        s = e.get_stats()
        assert s["total_reports"] == 0


# ─── Observability Pipeline ──────────────────────────────

class TestObservabilityPipeline:
    def test_emit_runtime_identity_created(self):
        with tempfile.TemporaryDirectory() as td:
            p = FederationObservabilityPipeline(output_dir=td)
            r = p.emit_runtime_identity_created({"id": "r1"})
            assert r["event_type"] == "runtime_identity_created"

    def test_emit_peer_manifest_received(self):
        with tempfile.TemporaryDirectory() as td:
            p = FederationObservabilityPipeline(output_dir=td)
            r = p.emit_peer_manifest_received({"peer": "p1"})
            assert r["event_type"] == "peer_manifest_received"

    def test_emit_peer_recognized(self):
        with tempfile.TemporaryDirectory() as td:
            p = FederationObservabilityPipeline(output_dir=td)
            r = p.emit_peer_recognized({"peer": "p1"})
            assert r["event_type"] == "peer_recognized"

    def test_emit_peer_verified(self):
        with tempfile.TemporaryDirectory() as td:
            p = FederationObservabilityPipeline(output_dir=td)
            r = p.emit_peer_verified({"peer": "p1"})
            assert r["event_type"] == "peer_verified"

    def test_emit_peer_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = FederationObservabilityPipeline(output_dir=td)
            r = p.emit_peer_rejected({"peer": "p1"})
            assert r["event_type"] == "peer_rejected"

    def test_emit_trust_exchange_validated(self):
        with tempfile.TemporaryDirectory() as td:
            p = FederationObservabilityPipeline(output_dir=td)
            r = p.emit_trust_exchange_validated({"verified": True})
            assert r["event_type"] == "trust_exchange_validated"

    def test_emit_topology_manifest_validated(self):
        with tempfile.TemporaryDirectory() as td:
            p = FederationObservabilityPipeline(output_dir=td)
            r = p.emit_topology_manifest_validated({"id": "m1"})
            assert r["event_type"] == "topology_manifest_validated"

    def test_emit_federation_boundary_denied(self):
        with tempfile.TemporaryDirectory() as td:
            p = FederationObservabilityPipeline(output_dir=td)
            r = p.emit_federation_boundary_denied({"action": "blocked"})
            assert r["event_type"] == "federation_boundary_denied"

    def test_emit_interoperability_report_generated(self):
        with tempfile.TemporaryDirectory() as td:
            p = FederationObservabilityPipeline(output_dir=td)
            r = p.emit_interoperability_report_generated({"peers": 1})
            assert r["event_type"] == "interoperability_report_generated"

    def test_event_file_map_count(self):
        assert len(EVENT_FILE_MAP) == len(FederationEventType)

    def test_jsonl_persisted(self):
        with tempfile.TemporaryDirectory() as td:
            p = FederationObservabilityPipeline(output_dir=td)
            p.emit_peer_verified({"test": True})
            files = list(Path(td).glob("*.jsonl"))
            assert len(files) >= 1

    def test_get_stats(self):
        with tempfile.TemporaryDirectory() as td:
            p = FederationObservabilityPipeline(output_dir=td)
            p.emit_peer_verified({})
            s = p.get_stats()
            assert s["total_events"] == 1


# ─── Replay Validator ────────────────────────────────────

class TestReplayValidator:
    def test_validate_single_check(self):
        v = FederationReplayValidator()
        r = v.validate_check("identity_creation_determinism")
        assert r["deterministic"]

    def test_validate_all(self):
        v = FederationReplayValidator()
        r = v.validate_all()
        assert r["total"] == len(REPLAY_CHECKS)
        assert r["all_deterministic"]

    def test_all_deterministic(self):
        v = FederationReplayValidator()
        v.validate_all()
        assert v.all_deterministic()

    def test_replay_checks_count(self):
        assert len(REPLAY_CHECKS) == 7

    def test_get_stats(self):
        v = FederationReplayValidator()
        s = v.get_stats()
        assert s["total_checks"] == 0

    def test_empty_is_deterministic(self):
        v = FederationReplayValidator()
        assert v.all_deterministic()


# ─── Boundary Policies ──────────────────────────────────

class TestBoundaryPolicies:
    def test_check_limit_allowed(self):
        b = FederationBoundaryPolicies()
        r = b.check_limit("max_federation_runs", 10)
        assert r["allowed"]

    def test_check_limit_denied(self):
        b = FederationBoundaryPolicies()
        r = b.check_limit("max_federation_runs", 50)
        assert not r["allowed"]

    def test_check_limit_unknown_raises(self):
        b = FederationBoundaryPolicies()
        with pytest.raises(ValueError, match="Unknown"):
            b.check_limit("nonexistent", 0)

    def test_override_capping(self):
        b = FederationBoundaryPolicies()
        r = b.check_limit("max_federation_runs", 10, override=200)
        assert r["effective_limit"] == 50

    def test_override_lower(self):
        b = FederationBoundaryPolicies()
        r = b.check_limit("max_federation_runs", 10, override=20)
        assert r["effective_limit"] == 20

    def test_check_forbidden_true(self):
        b = FederationBoundaryPolicies()
        r = b.check_forbidden("authority_transfer")
        assert r["forbidden"]

    def test_check_forbidden_false(self):
        b = FederationBoundaryPolicies()
        r = b.check_forbidden("normal_action")
        assert not r["forbidden"]

    def test_all_forbidden_actions(self):
        b = FederationBoundaryPolicies()
        for action in FORBIDDEN_FEDERATION_ACTIONS:
            r = b.check_forbidden(action)
            assert r["forbidden"]

    def test_federation_limits_count(self):
        assert len(FEDERATION_LIMITS) == 8

    def test_forbidden_actions_count(self):
        assert len(FORBIDDEN_FEDERATION_ACTIONS) == 10

    def test_denied_tracking(self):
        b = FederationBoundaryPolicies()
        b.check_limit("max_federation_runs", 100)
        b.check_forbidden("authority_transfer")
        s = b.get_stats()
        assert s["total_denied"] == 2

    def test_get_stats(self):
        b = FederationBoundaryPolicies()
        s = b.get_stats()
        assert s["total_limits"] == 8
        assert s["total_forbidden"] == 10


# ─── Continuity Bridges ─────────────────────────────────

class TestContinuityBridges:
    def test_all_bridge_classes_count(self):
        assert len(ALL_BRIDGE_CLASSES) == 9

    def test_bridge_record(self):
        with tempfile.TemporaryDirectory() as td:
            b = TrustFederationBridge(state_dir=td)
            r = b.record("trust_exchanged", {"peer": "p1"})
            assert r["bridge"] == "trust_federation"

    def test_bridge_persists_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            b = CertificationFederationBridge(state_dir=td)
            b.record("test")
            files = list(Path(td).glob("*.jsonl"))
            assert len(files) == 1

    def test_bridge_get_records(self):
        with tempfile.TemporaryDirectory() as td:
            b = ValidationFederationBridge(state_dir=td)
            b.record("a")
            b.record("b")
            assert len(b.get_records()) == 2

    def test_bridge_get_stats(self):
        with tempfile.TemporaryDirectory() as td:
            b = AccountabilityFederationBridge(state_dir=td)
            b.record("x")
            s = b.get_stats()
            assert s["total_records"] == 1

    def test_all_bridges_instantiate(self):
        with tempfile.TemporaryDirectory() as td:
            for cls in ALL_BRIDGE_CLASSES:
                b = cls(state_dir=td)
                assert b.get_stats()["total_records"] == 0

    def test_explainability_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = ExplainabilityFederationBridge(state_dir=td)
            r = b.record("explained")
            assert r["bridge"] == "explainability_federation"

    def test_topology_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = TopologyFederationBridge(state_dir=td)
            r = b.record("topo_shared")
            assert r["bridge"] == "topology_federation"

    def test_observability_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = ObservabilityFederationBridge(state_dir=td)
            r = b.record("obs_linked")
            assert r["bridge"] == "observability_federation"

    def test_replay_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = ReplayFederationBridge(state_dir=td)
            r = b.record("replay_verified")
            assert r["bridge"] == "replay_federation"

    def test_governance_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = GovernanceFederationBridge(state_dir=td)
            r = b.record("gov_proven")
            assert r["bridge"] == "governance_federation"


# ─── Coordinator ─────────────────────────────────────────

class TestCoordinator:
    def _make(self):
        td = tempfile.mkdtemp()
        return CanonicalSovereignFederationReadinessCoordinator(state_dir=td), td

    def test_start_federation_run(self):
        c, _ = self._make()
        r = c.start_federation_run()
        assert r["status"] == "started"

    def test_register_identity(self):
        c, _ = self._make()
        r = c.register_identity(trust_bundle_ref="tb-ref")
        assert r["runtime_fingerprint"] != ""

    def test_recognize_peer(self):
        c, _ = self._make()
        r = c.recognize_peer(_valid_peer_manifest())
        assert r["trust_status"] == "recognized"

    def test_verify_peer(self):
        c, _ = self._make()
        r = c.verify_peer(_valid_peer_manifest())
        assert r["trust_status"] == "verified"

    def test_reject_invalid_peer(self):
        c, _ = self._make()
        r = c.verify_peer(_invalid_peer_manifest())
        assert r["trust_status"] == "untrusted"

    def test_exchange_trust(self):
        c, _ = self._make()
        r = c.exchange_trust("local1", "peer1", {
            "trust_bundle_hash": "h1",
            "constitutional_proof_hash": "h2",
        })
        assert r["verified"]

    def test_generate_topology_manifest(self):
        c, _ = self._make()
        r = c.generate_topology_manifest("r1")
        assert r["runtime_id"] == "r1"

    def test_generate_capability_manifest(self):
        c, _ = self._make()
        r = c.generate_capability_manifest("r1")
        assert r["runtime_id"] == "r1"

    def test_generate_interop_report(self):
        c, _ = self._make()
        r = c.generate_interop_report("l1", "p1", local_trust_hash="h1", peer_trust_hash="h2", local_topology={"a": 1}, peer_topology={"b": 2})
        assert r["trust_compatible"]

    def test_validate_replay_determinism(self):
        c, _ = self._make()
        r = c.validate_replay_determinism()
        assert r["all_deterministic"]

    def test_check_boundary(self):
        c, _ = self._make()
        r = c.check_boundary("max_federation_runs", 10)
        assert r["allowed"]

    def test_complete_federation_run(self):
        c, _ = self._make()
        run = c.start_federation_run()
        c.register_identity(trust_bundle_ref="tb-ref")
        c.validate_replay_determinism()
        r = c.complete_federation_run(run["run_id"])
        assert r["outcome"] == "ready"

    def test_get_federation_report(self):
        c, _ = self._make()
        r = c.get_federation_report()
        assert "identity" in r
        assert "recognition" in r

    def test_get_stats(self):
        c, _ = self._make()
        s = c.get_stats()
        assert "lifecycle" in s
        assert "runs" in s

    def test_max_runs_enforced(self):
        c, _ = self._make()
        for _ in range(MAX_FEDERATION_RUNS):
            c.start_federation_run()
        with pytest.raises(ValueError, match="Max"):
            c.start_federation_run()

    def test_full_flow(self):
        c, _ = self._make()
        run = c.start_federation_run("fed-e2e")
        identity = c.register_identity(trust_bundle_ref="tb-ref", constitutional_ref="ct-ref")
        c.recognize_peer(_valid_peer_manifest())
        c.verify_peer(_valid_peer_manifest())
        c.exchange_trust(identity["runtime_id"], "peer-001", {
            "trust_bundle_hash": "h1", "constitutional_proof_hash": "h2",
            "chronology_proof_hash": "h3", "provenance_proof_hash": "h4",
            "governance_proof_hash": "h5",
        })
        c.generate_topology_manifest(identity["runtime_id"])
        c.generate_capability_manifest(identity["runtime_id"])
        c.generate_interop_report(identity["runtime_id"], "peer-001",
            local_trust_hash="h1", peer_trust_hash="h2",
            local_topology={"a": 1}, peer_topology={"b": 2})
        c.validate_replay_determinism()
        receipt = c.complete_federation_run("fed-e2e")
        assert receipt["outcome"] == "ready"
        report = c.get_federation_report()
        assert report["identity"]["total_identities"] == 1
        assert report["recognition"]["verified"] >= 1


# ─── Constraint Verification ────────────────────────────

class TestConstraintVerification:
    def test_sovereign_runtime_identity_determinism(self):
        with tempfile.TemporaryDirectory() as td:
            e = SovereignRuntimeIdentityEngine(output_dir=td)
            r = e.create_identity(runtime_id="det-test")
            assert r["runtime_fingerprint"] != ""
            assert r["verification_hash"] != ""

    def test_peer_manifest_parsing(self):
        e = PeerRecognitionEngine()
        r = e.recognize_peer(_valid_peer_manifest())
        assert r["identity_format_valid"]

    def test_peer_trust_verification(self):
        e = PeerRecognitionEngine()
        r = e.verify_peer(_valid_peer_manifest())
        assert r["trust_status"] == "verified"

    def test_untrusted_peer_rejection(self):
        e = PeerRecognitionEngine()
        r = e.verify_peer(_minimal_peer_manifest())
        assert r["trust_status"] == "untrusted"

    def test_expired_peer_rejection(self):
        e = PeerRecognitionEngine()
        r = e.reject_expired_peer("old-peer")
        assert r["trust_status"] == "expired"

    def test_topology_manifest_validation(self):
        e = FederationTopologyManifestEngine()
        m = e.generate_manifest("r1")
        v = e.validate_manifest(m)
        assert v["valid"]

    def test_capability_manifest_validation(self):
        e = CrossRuntimeCapabilityManifestEngine()
        m = e.generate_manifest("r1")
        v = e.validate_manifest(m)
        assert v["valid"]
        assert v["no_forbidden_capabilities"]

    def test_artifact_based_trust_verification(self):
        e = FederationTrustExchangeEngine()
        r = e.exchange_trust("l1", "p1", {
            "trust_bundle_hash": "h1", "constitutional_proof_hash": "h2",
        })
        assert r["verified"]

    def test_deterministic_federation_replay(self):
        v = FederationReplayValidator()
        r = v.validate_all()
        assert r["all_deterministic"]

    def test_no_authority_transfer(self):
        b = FederationBoundaryPolicies()
        r = b.check_forbidden("authority_transfer")
        assert r["forbidden"]

    def test_no_peer_owned_execution(self):
        b = FederationBoundaryPolicies()
        r = b.check_forbidden("peer_owned_execution")
        assert r["forbidden"]

    def test_no_peer_owned_governance(self):
        b = FederationBoundaryPolicies()
        r = b.check_forbidden("peer_owned_governance")
        assert r["forbidden"]

    def test_no_peer_owned_cognition(self):
        b = FederationBoundaryPolicies()
        r = b.check_forbidden("peer_owned_cognition")
        assert r["forbidden"]

    def test_no_recursive_federation(self):
        b = FederationBoundaryPolicies()
        r = b.check_forbidden("recursive_federation")
        assert r["forbidden"]

    def test_no_autonomous_consensus(self):
        b = FederationBoundaryPolicies()
        r = b.check_forbidden("autonomous_consensus")
        assert r["forbidden"]

    def test_no_hidden_synchronization(self):
        b = FederationBoundaryPolicies()
        r = b.check_forbidden("hidden_synchronization")
        assert r["forbidden"]

    def test_no_cross_runtime_memory_mutation(self):
        b = FederationBoundaryPolicies()
        r = b.check_forbidden("cross_runtime_memory_mutation")
        assert r["forbidden"]

    def test_no_execution_outside_spine(self):
        e = CrossRuntimeCapabilityManifestEngine()
        assert e.check_forbidden("peer_direct_execution")

    def test_no_governance_bypass(self):
        e = FederationInteroperabilityEngine()
        r = e.check_forbidden("federate_governance")
        assert r["forbidden"]

    def test_override_capping_enforced(self):
        b = FederationBoundaryPolicies()
        r = b.check_limit("max_federation_runs", 10, override=200)
        assert r["effective_limit"] == 50

    def test_lifecycle_branching_verified_path(self):
        e = FederationLifecycleEngine()
        e.transition(FederationPhase.PEER_RECEIVED, FederationPhase.PEER_VERIFIED)
        assert e.get_stats()["total_transitions"] == 1

    def test_lifecycle_branching_rejected_path(self):
        e = FederationLifecycleEngine()
        e.transition(FederationPhase.PEER_RECEIVED, FederationPhase.PEER_REJECTED)
        assert e.get_stats()["total_transitions"] == 1

    def test_lifecycle_terminal_absorbing(self):
        e = FederationLifecycleEngine()
        with pytest.raises(ValueError, match="terminal"):
            e.transition(FederationPhase.ARCHIVED, FederationPhase.IDENTITY_CREATED)

    def test_full_federation_flow_end_to_end(self):
        c = CanonicalSovereignFederationReadinessCoordinator(state_dir=tempfile.mkdtemp())
        run = c.start_federation_run("e2e-fed")
        identity = c.register_identity(trust_bundle_ref="tb", constitutional_ref="ct")
        c.recognize_peer(_valid_peer_manifest())
        vrf = c.verify_peer(_valid_peer_manifest())
        assert vrf["trust_status"] == "verified"
        c.exchange_trust(identity["runtime_id"], "peer-001", {
            "trust_bundle_hash": "h1", "constitutional_proof_hash": "h2",
        })
        c.generate_topology_manifest(identity["runtime_id"])
        c.generate_capability_manifest(identity["runtime_id"])
        c.generate_interop_report(identity["runtime_id"], "peer-001",
            local_trust_hash="h1", peer_trust_hash="h2",
            local_topology={"a": 1}, peer_topology={"b": 2})
        c.validate_replay_determinism()
        receipt = c.complete_federation_run("e2e-fed")
        assert receipt["outcome"] == "ready"
