"""Tests for Phase 96.8CL — Substrate Sovereign Operational Accountability Proving.

Tests: contracts, enums, lifecycle, chronology, governance history,
replay history, continuity accountability, provenance history,
constitutional audit, historical integrity, observability pipeline,
replay validator, boundary policies, continuity bridges, coordinator,
constraint verification.
"""

import os
import json
import tempfile
import pytest

from core.accountability.sovereign_operational_accountability_contracts_v1 import (
    AccountabilityPhase,
    AccountabilityEventType,
    AccountabilityDomain,
    HistoricalIntegrityDimension,
    TemporalAccountabilityState,
    ConstitutionalChronologyState,
    GovernanceHistoryState,
    ReplayHistoryState,
    ContinuityHistoryState,
    DeploymentHistoryState,
    OperationalTimelineState,
    AccountabilityLineageState,
    AccountabilityReplayState,
    AccountabilityProvenanceState,
    AccountabilityBoundaryState,
    ConstitutionalAuditState,
    HistoricalIntegrityState,
    AccountabilityObservabilityState,
    SovereignAccountabilityReceipt,
    _now_iso,
    _deterministic_id,
)
from core.accountability.accountability_lifecycle_engine_v1 import (
    AccountabilityLifecycleEngine,
    VALID_TRANSITIONS,
    TERMINAL_STATES,
)
from core.accountability.constitutional_chronology_engine_v1 import (
    ConstitutionalChronologyEngine,
    CHRONOLOGY_DOMAINS,
    MAX_CHRONOLOGY_ENTRIES,
)
from core.accountability.governance_history_engine_v1 import (
    GovernanceHistoryEngine,
    GOVERNANCE_HISTORY_TYPES,
    MAX_GOVERNANCE_HISTORY,
)
from core.accountability.replay_history_engine_v1 import (
    ReplayHistoryEngine,
    REPLAY_HISTORY_TYPES,
    MAX_REPLAY_HISTORY,
)
from core.accountability.continuity_accountability_engine_v1 import (
    ContinuityAccountabilityEngine,
    CONTINUITY_HISTORY_TYPES,
    MAX_CONTINUITY_HISTORY,
)
from core.accountability.operational_provenance_history_engine_v1 import (
    OperationalProvenanceHistoryEngine,
    PROVENANCE_HISTORY_DOMAINS,
    MAX_PROVENANCE_HISTORY,
)
from core.accountability.constitutional_audit_engine_v1 import (
    ConstitutionalAuditEngine,
    AUDIT_DOMAINS,
    MAX_AUDITS,
)
from core.accountability.historical_integrity_engine_v1 import (
    HistoricalIntegrityEngine,
    INTEGRITY_DIMENSIONS,
    MAX_INTEGRITY_CHECKS,
)
from core.accountability.accountability_observability_pipeline_v1 import (
    AccountabilityObservabilityPipeline,
    EVENT_FILE_MAP,
)
from core.accountability.sovereign_accountability_replay_validator_v1 import (
    SovereignAccountabilityReplayValidator,
    REPLAY_CHECKS,
)
from core.accountability.accountability_boundary_policies_v1 import (
    AccountabilityBoundaryPolicies,
    ACCOUNTABILITY_LIMITS,
    FORBIDDEN_ACCOUNTABILITY_ACTIONS,
)
from core.accountability.accountability_continuity_bridges_v1 import (
    ReplayAccountabilityBridge,
    GovernanceAccountabilityBridge,
    ContinuityAccountabilityBridge,
    TopologyAccountabilityBridge,
    DeploymentAccountabilityBridge,
    ValidationAccountabilityBridge,
    CertificationAccountabilityBridge,
    ExplainabilityAccountabilityBridge,
    OrchestrationAccountabilityBridge,
    ALL_BRIDGE_CLASSES,
)
from core.accountability.canonical_sovereign_accountability_coordinator_v1 import (
    CanonicalSovereignAccountabilityCoordinator,
    MAX_ACCOUNTABILITY_RUNS,
)


# ── TestContracts ──────────────────────────────────────────


class TestContracts:
    def test_temporal_accountability_state(self):
        s = TemporalAccountabilityState(run_id="r1")
        d = s.to_dict()
        assert d["run_id"] == "r1"
        assert d["accountability_id"].startswith("tacct-")

    def test_constitutional_chronology_state(self):
        s = ConstitutionalChronologyState(domain="governance", entries=10)
        d = s.to_dict()
        assert d["monotonic"] is True
        assert d["chronology_id"].startswith("cchron-")

    def test_governance_history_state(self):
        s = GovernanceHistoryState(decision_count=5, approvals=4, denials=1)
        d = s.to_dict()
        assert d["timeline_deterministic"] is True
        assert d["history_id"].startswith("ghist-")

    def test_replay_history_state(self):
        s = ReplayHistoryState(generations=3, restorations=1)
        d = s.to_dict()
        assert d["consistency_preserved"] is True
        assert d["history_id"].startswith("rhist-")

    def test_continuity_history_state(self):
        s = ContinuityHistoryState(checkpoints=5, restorations=2)
        d = s.to_dict()
        assert d["integrity_preserved"] is True
        assert d["history_id"].startswith("chist-")

    def test_deployment_history_state(self):
        s = DeploymentHistoryState(deployments=3, rollbacks=0)
        d = s.to_dict()
        assert d["all_governed"] is True
        assert d["history_id"].startswith("dhist-")

    def test_operational_timeline_state(self):
        s = OperationalTimelineState(domain="governance", events=10)
        d = s.to_dict()
        assert d["monotonic"] is True
        assert d["timeline_id"].startswith("otl-")

    def test_accountability_lineage_state(self):
        s = AccountabilityLineageState(source_id="s1", target_id="t1")
        d = s.to_dict()
        assert d["lineage_type"] == "temporal"
        assert d["lineage_id"].startswith("alin-")

    def test_accountability_replay_state(self):
        s = AccountabilityReplayState(check_name="test")
        d = s.to_dict()
        assert d["deterministic"] is True
        assert d["replay_id"].startswith("arplay-")

    def test_accountability_provenance_state(self):
        s = AccountabilityProvenanceState(graph_name="test", nodes=5, edges=4)
        d = s.to_dict()
        assert d["deterministic"] is True
        assert d["provenance_id"].startswith("aprov-")

    def test_accountability_boundary_state(self):
        s = AccountabilityBoundaryState(limit_name="max_audits", current_value=50, max_value=200)
        d = s.to_dict()
        assert d["exceeded"] is False
        assert d["boundary_id"].startswith("abnd-")

    def test_constitutional_audit_state(self):
        s = ConstitutionalAuditState(audit_domain="governance", findings=0)
        d = s.to_dict()
        assert d["all_compliant"] is True
        assert d["audit_id"].startswith("caudit-")

    def test_historical_integrity_state(self):
        s = HistoricalIntegrityState()
        d = s.to_dict()
        assert d["historical_integrity_score"] == 1.0
        assert d["integrity_id"].startswith("hint-")

    def test_historical_integrity_partial(self):
        s = HistoricalIntegrityState(chronology_intact=False, governance_intact=False)
        assert s.historical_integrity_score == 4 / 6

    def test_accountability_observability_state(self):
        s = AccountabilityObservabilityState(events_emitted=20)
        d = s.to_dict()
        assert d["all_persisted"] is True
        assert d["observability_id"].startswith("aobs-")

    def test_sovereign_accountability_receipt(self):
        s = SovereignAccountabilityReceipt(run_id="r1", audits_generated=6)
        d = s.to_dict()
        assert d["outcome"] == "accountable"
        assert d["receipt_id"].startswith("sarcpt-")


# ── TestEnums ──────────────────────────────────────────────


class TestEnums:
    def test_accountability_phase_count(self):
        assert len(AccountabilityPhase) == 5

    def test_accountability_event_type_count(self):
        assert len(AccountabilityEventType) == 8

    def test_accountability_domain_count(self):
        assert len(AccountabilityDomain) == 7

    def test_historical_integrity_dimension_count(self):
        assert len(HistoricalIntegrityDimension) == 6

    def test_deterministic_id(self):
        a = _deterministic_id("t-", "x", "y")
        b = _deterministic_id("t-", "x", "y")
        assert a == b

    def test_phase_values(self):
        assert AccountabilityPhase.DEFINED.value == "defined"
        assert AccountabilityPhase.AUDITING.value == "auditing"


# ── TestLifecycleEngine ───────────────────────────────────


class TestLifecycleEngine:
    def test_initial_phase(self):
        e = AccountabilityLifecycleEngine()
        assert e.current_phase == "defined"

    def test_linear_progression(self):
        e = AccountabilityLifecycleEngine()
        for p in ["reconstructing", "auditing", "validated", "archived"]:
            e.transition(p)
        assert e.current_phase == "archived"
        assert e.is_terminal

    def test_invalid_transition(self):
        e = AccountabilityLifecycleEngine()
        with pytest.raises(ValueError):
            e.transition("archived")

    def test_terminal_no_transition(self):
        e = AccountabilityLifecycleEngine()
        for p in ["reconstructing", "auditing", "validated", "archived"]:
            e.transition(p)
        with pytest.raises(ValueError):
            e.transition("defined")

    def test_history_tracking(self):
        e = AccountabilityLifecycleEngine()
        e.transition("reconstructing")
        h = e.get_history()
        assert len(h) == 1
        assert h[0]["from"] == "defined"

    def test_can_transition(self):
        e = AccountabilityLifecycleEngine()
        assert e.can_transition("reconstructing") is True
        assert e.can_transition("archived") is False

    def test_stats(self):
        e = AccountabilityLifecycleEngine()
        e.transition("reconstructing")
        s = e.get_stats()
        assert s["current_phase"] == "reconstructing"

    def test_five_valid_transitions(self):
        assert len(VALID_TRANSITIONS) == 5

    def test_terminal_states(self):
        assert TERMINAL_STATES == {"archived"}


# ── TestConstitutionalChronologyEngine ────────────────────


class TestConstitutionalChronologyEngine:
    def test_record_single(self):
        e = ConstitutionalChronologyEngine()
        r = e.record_chronology("governance")
        assert r["monotonic"] is True

    def test_record_all_domains(self):
        e = ConstitutionalChronologyEngine()
        r = e.record_all_domains()
        assert r["all_monotonic"] is True
        assert r["total"] == 7

    def test_all_monotonic_empty(self):
        e = ConstitutionalChronologyEngine()
        assert e.all_monotonic() is True

    def test_non_monotonic(self):
        e = ConstitutionalChronologyEngine()
        e.record_chronology("test", monotonic=False)
        assert e.all_monotonic() is False

    def test_orphans(self):
        e = ConstitutionalChronologyEngine()
        e.record_chronology("test", no_orphans=False)
        assert e.all_no_orphans() is False

    def test_max_entries(self):
        e = ConstitutionalChronologyEngine()
        for i in range(MAX_CHRONOLOGY_ENTRIES):
            e.record_chronology(f"d-{i}")
        with pytest.raises(ValueError):
            e.record_chronology("overflow")

    def test_domains_count(self):
        assert len(CHRONOLOGY_DOMAINS) == 7

    def test_stats(self):
        e = ConstitutionalChronologyEngine()
        e.record_all_domains()
        s = e.get_stats()
        assert s["total_entries"] == 7


# ── TestGovernanceHistoryEngine ───────────────────────────


class TestGovernanceHistoryEngine:
    def test_record_single(self):
        e = GovernanceHistoryEngine()
        r = e.record_history(decision_count=5, approvals=4, denials=1)
        assert r["timeline_deterministic"] is True

    def test_record_all_types(self):
        e = GovernanceHistoryEngine()
        r = e.record_all_types()
        assert r["all_deterministic"] is True
        assert r["total"] == 5

    def test_all_deterministic_empty(self):
        e = GovernanceHistoryEngine()
        assert e.all_deterministic() is True

    def test_max_history(self):
        e = GovernanceHistoryEngine()
        for i in range(MAX_GOVERNANCE_HISTORY):
            e.record_history()
        with pytest.raises(ValueError):
            e.record_history()

    def test_types_count(self):
        assert len(GOVERNANCE_HISTORY_TYPES) == 5

    def test_stats(self):
        e = GovernanceHistoryEngine()
        e.record_all_types()
        s = e.get_stats()
        assert s["total_entries"] == 5


# ── TestReplayHistoryEngine ──────────────────────────────


class TestReplayHistoryEngine:
    def test_record_single(self):
        e = ReplayHistoryEngine()
        r = e.record_history(generations=2, restorations=1)
        assert r["consistency_preserved"] is True

    def test_record_all_types(self):
        e = ReplayHistoryEngine()
        r = e.record_all_types()
        assert r["all_consistent"] is True
        assert r["total"] == 5

    def test_all_consistent_empty(self):
        e = ReplayHistoryEngine()
        assert e.all_consistent() is True

    def test_max_history(self):
        e = ReplayHistoryEngine()
        for i in range(MAX_REPLAY_HISTORY):
            e.record_history()
        with pytest.raises(ValueError):
            e.record_history()

    def test_types_count(self):
        assert len(REPLAY_HISTORY_TYPES) == 5

    def test_stats(self):
        e = ReplayHistoryEngine()
        e.record_all_types()
        s = e.get_stats()
        assert s["total_entries"] == 5


# ── TestContinuityAccountabilityEngine ────────────────────


class TestContinuityAccountabilityEngine:
    def test_record_single(self):
        e = ContinuityAccountabilityEngine()
        r = e.record_history(checkpoints=3, restorations=1)
        assert r["integrity_preserved"] is True

    def test_record_all_types(self):
        e = ContinuityAccountabilityEngine()
        r = e.record_all_types()
        assert r["all_preserved"] is True
        assert r["total"] == 5

    def test_all_preserved_empty(self):
        e = ContinuityAccountabilityEngine()
        assert e.all_preserved() is True

    def test_max_history(self):
        e = ContinuityAccountabilityEngine()
        for i in range(MAX_CONTINUITY_HISTORY):
            e.record_history()
        with pytest.raises(ValueError):
            e.record_history()

    def test_types_count(self):
        assert len(CONTINUITY_HISTORY_TYPES) == 5

    def test_stats(self):
        e = ContinuityAccountabilityEngine()
        e.record_all_types()
        s = e.get_stats()
        assert s["total_entries"] == 5


# ── TestOperationalProvenanceHistoryEngine ────────────────


class TestOperationalProvenanceHistoryEngine:
    def test_generate_single(self):
        e = OperationalProvenanceHistoryEngine()
        r = e.generate_graph("test", nodes=3, edges=2)
        assert r["deterministic"] is True

    def test_generate_all_domains(self):
        e = OperationalProvenanceHistoryEngine()
        r = e.generate_all_domains()
        assert r["all_deterministic"] is True
        assert r["total"] == 5

    def test_all_deterministic_empty(self):
        e = OperationalProvenanceHistoryEngine()
        assert e.all_deterministic() is True

    def test_max_graphs(self):
        e = OperationalProvenanceHistoryEngine()
        for i in range(MAX_PROVENANCE_HISTORY):
            e.generate_graph(f"g-{i}")
        with pytest.raises(ValueError):
            e.generate_graph("overflow")

    def test_domains_count(self):
        assert len(PROVENANCE_HISTORY_DOMAINS) == 5

    def test_stats(self):
        e = OperationalProvenanceHistoryEngine()
        e.generate_all_domains()
        s = e.get_stats()
        assert s["total_graphs"] == 5
        assert s["total_nodes"] == 15


# ── TestConstitutionalAuditEngine ─────────────────────────


class TestConstitutionalAuditEngine:
    def test_generate_single(self):
        e = ConstitutionalAuditEngine()
        r = e.generate_audit("governance")
        assert r["all_compliant"] is True

    def test_generate_all_audits(self):
        e = ConstitutionalAuditEngine()
        r = e.generate_all_audits()
        assert r["all_compliant"] is True
        assert r["all_deterministic"] is True
        assert r["total"] == 6

    def test_all_compliant_empty(self):
        e = ConstitutionalAuditEngine()
        assert e.all_compliant() is True

    def test_max_audits(self):
        e = ConstitutionalAuditEngine()
        for i in range(MAX_AUDITS):
            e.generate_audit(f"d-{i}")
        with pytest.raises(ValueError):
            e.generate_audit("overflow")

    def test_domains_count(self):
        assert len(AUDIT_DOMAINS) == 6

    def test_stats(self):
        e = ConstitutionalAuditEngine()
        e.generate_all_audits()
        s = e.get_stats()
        assert s["total_audits"] == 6
        assert s["all_compliant"] is True


# ── TestHistoricalIntegrityEngine ─────────────────────────


class TestHistoricalIntegrityEngine:
    def test_verify_full(self):
        e = HistoricalIntegrityEngine()
        r = e.verify_full_integrity()
        assert r["historical_integrity_score"] == 1.0

    def test_verify_partial(self):
        e = HistoricalIntegrityEngine()
        r = e.verify_integrity(chronology_intact=False)
        assert r["historical_integrity_score"] == 5 / 6

    def test_all_intact_empty(self):
        e = HistoricalIntegrityEngine()
        assert e.all_intact() is True

    def test_compromised(self):
        e = HistoricalIntegrityEngine()
        e.verify_integrity(chronology_intact=False)
        assert e.all_intact() is False
        assert len(e.get_compromised()) == 1

    def test_max_checks(self):
        e = HistoricalIntegrityEngine()
        for _ in range(MAX_INTEGRITY_CHECKS):
            e.verify_full_integrity()
        with pytest.raises(ValueError):
            e.verify_full_integrity()

    def test_dimensions_count(self):
        assert len(INTEGRITY_DIMENSIONS) == 6

    def test_stats(self):
        e = HistoricalIntegrityEngine()
        e.verify_full_integrity()
        s = e.get_stats()
        assert s["total_checks"] == 1
        assert s["all_intact"] is True


# ── TestObservabilityPipeline ─────────────────────────────


class TestObservabilityPipeline:
    def test_emit_accountability_started(self):
        p = AccountabilityObservabilityPipeline()
        e = p.emit_accountability_started({"run_id": "r1"})
        assert e["event_type"] == "accountability_started"

    def test_emit_chronology_reconstructed(self):
        p = AccountabilityObservabilityPipeline()
        e = p.emit_chronology_reconstructed()
        assert e["event_type"] == "chronology_reconstructed"

    def test_emit_governance_history_reconstructed(self):
        p = AccountabilityObservabilityPipeline()
        e = p.emit_governance_history_reconstructed()
        assert e["event_type"] == "governance_history_reconstructed"

    def test_emit_replay_history_reconstructed(self):
        p = AccountabilityObservabilityPipeline()
        e = p.emit_replay_history_reconstructed()
        assert e["event_type"] == "replay_history_reconstructed"

    def test_emit_continuity_history_reconstructed(self):
        p = AccountabilityObservabilityPipeline()
        e = p.emit_continuity_history_reconstructed()
        assert e["event_type"] == "continuity_history_reconstructed"

    def test_emit_provenance_history_generated(self):
        p = AccountabilityObservabilityPipeline()
        e = p.emit_provenance_history_generated()
        assert e["event_type"] == "provenance_history_generated"

    def test_emit_constitutional_audit_generated(self):
        p = AccountabilityObservabilityPipeline()
        e = p.emit_constitutional_audit_generated()
        assert e["event_type"] == "constitutional_audit_generated"

    def test_emit_accountability_completed(self):
        p = AccountabilityObservabilityPipeline()
        e = p.emit_accountability_completed()
        assert e["event_type"] == "accountability_completed"

    def test_event_file_map(self):
        assert len(EVENT_FILE_MAP) == 8
        for v in EVENT_FILE_MAP.values():
            assert v.endswith(".jsonl")

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            p = AccountabilityObservabilityPipeline(output_dir=td)
            p.emit_accountability_started({"run_id": "r1"})
            path = os.path.join(td, "accountability_started.jsonl")
            assert os.path.exists(path)
            with open(path) as f:
                line = json.loads(f.readline())
            assert line["event_type"] == "accountability_started"

    def test_get_events_by_type(self):
        p = AccountabilityObservabilityPipeline()
        p.emit_accountability_started()
        p.emit_accountability_completed()
        p.emit_accountability_started()
        starts = p.get_events_by_type("accountability_started")
        assert len(starts) == 2

    def test_stats(self):
        p = AccountabilityObservabilityPipeline()
        p.emit_accountability_started()
        p.emit_accountability_completed()
        s = p.get_stats()
        assert s["total_events"] == 2


# ── TestReplayValidator ───────────────────────────────────


class TestReplayValidator:
    def test_validate_single(self):
        v = SovereignAccountabilityReplayValidator()
        r = v.validate_replay("test", "in", "out")
        assert r["deterministic"] is True

    def test_validate_all(self):
        v = SovereignAccountabilityReplayValidator()
        r = v.validate_all()
        assert r["all_deterministic"] is True
        assert r["total"] == 7

    def test_all_deterministic_empty(self):
        v = SovereignAccountabilityReplayValidator()
        assert v.all_deterministic() is True

    def test_replay_checks_count(self):
        assert len(REPLAY_CHECKS) == 7

    def test_stats(self):
        v = SovereignAccountabilityReplayValidator()
        v.validate_all()
        s = v.get_stats()
        assert s["total_checks"] == 7

    def test_deterministic_hashing(self):
        v = SovereignAccountabilityReplayValidator()
        r1 = v.validate_replay("c", "same", "same")
        r2 = v.validate_replay("c", "same", "same")
        assert r1["input_hash"] == r2["input_hash"]


# ── TestBoundaryPolicies ─────────────────────────────────


class TestBoundaryPolicies:
    def test_check_within_limit(self):
        bp = AccountabilityBoundaryPolicies()
        r = bp.check_limit("max_audits", 100)
        assert r["exceeded"] is False

    def test_check_exceeded(self):
        bp = AccountabilityBoundaryPolicies()
        r = bp.check_limit("max_audits", 201)
        assert r["exceeded"] is True

    def test_override_capping(self):
        bp = AccountabilityBoundaryPolicies()
        r = bp.check_limit("max_audits", 150, override=300)
        assert r["max_value"] == 200

    def test_override_lower(self):
        bp = AccountabilityBoundaryPolicies()
        r = bp.check_limit("max_audits", 60, override=50)
        assert r["max_value"] == 50
        assert r["exceeded"] is True

    def test_forbidden_action(self):
        bp = AccountabilityBoundaryPolicies()
        assert bp.is_forbidden("hidden_chronology_mutation") is True
        assert bp.is_forbidden("allowed_action") is False

    def test_check_all_limits(self):
        bp = AccountabilityBoundaryPolicies()
        vals = {k: 0 for k in ACCOUNTABILITY_LIMITS}
        r = bp.check_all_limits(vals)
        assert r["any_exceeded"] is False
        assert r["total"] == 8

    def test_limits_count(self):
        assert len(ACCOUNTABILITY_LIMITS) == 8

    def test_forbidden_count(self):
        assert len(FORBIDDEN_ACCOUNTABILITY_ACTIONS) == 7

    def test_get_exceeded(self):
        bp = AccountabilityBoundaryPolicies()
        bp.check_limit("max_audits", 300)
        assert len(bp.get_exceeded()) == 1

    def test_stats(self):
        bp = AccountabilityBoundaryPolicies()
        bp.check_limit("max_audits", 50)
        s = bp.get_stats()
        assert s["total_checks"] == 1

    def test_all_forbidden_actions(self):
        expected = [
            "hidden_chronology_mutation",
            "retroactive_lineage_rewriting",
            "fabricated_accountability",
            "replay_bypass",
            "governance_bypass",
            "recursive_accountability_reconstruction",
            "execution_outside_spine",
        ]
        assert FORBIDDEN_ACCOUNTABILITY_ACTIONS == expected

    def test_at_exact_limit(self):
        bp = AccountabilityBoundaryPolicies()
        r = bp.check_limit("max_audits", 200)
        assert r["exceeded"] is False

    def test_one_over(self):
        bp = AccountabilityBoundaryPolicies()
        r = bp.check_limit("max_audits", 201)
        assert r["exceeded"] is True

    def test_override_zero(self):
        bp = AccountabilityBoundaryPolicies()
        r = bp.check_limit("max_audits", 1, override=0)
        assert r["exceeded"] is True


# ── TestContinuityBridges ────────────────────────────────


class TestContinuityBridges:
    def test_bridge_count(self):
        assert len(ALL_BRIDGE_CLASSES) == 9

    def test_bridge_names(self):
        with tempfile.TemporaryDirectory() as td:
            names = [cls(state_dir=td)._bridge_name for cls in ALL_BRIDGE_CLASSES]
            assert "replay_accountability" in names
            assert "governance_accountability" in names
            assert "orchestration_accountability" in names

    def test_record_and_retrieve(self):
        with tempfile.TemporaryDirectory() as td:
            b = GovernanceAccountabilityBridge(state_dir=td)
            r = b.record("test_action", {"key": "value"})
            assert r["bridge"] == "governance_accountability"

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            b = ReplayAccountabilityBridge(state_dir=td)
            b.record("test")
            path = os.path.join(td, "replay_accountability.jsonl")
            assert os.path.exists(path)

    def test_stats(self):
        with tempfile.TemporaryDirectory() as td:
            b = ContinuityAccountabilityBridge(state_dir=td)
            b.record("a1")
            b.record("a2")
            s = b.get_stats()
            assert s["total_records"] == 2

    def test_get_records(self):
        with tempfile.TemporaryDirectory() as td:
            b = TopologyAccountabilityBridge(state_dir=td)
            b.record("r1")
            b.record("r2")
            assert len(b.get_records()) == 2

    def test_all_bridges_instantiate(self):
        with tempfile.TemporaryDirectory() as td:
            for cls in ALL_BRIDGE_CLASSES:
                b = cls(state_dir=td)
                assert b._bridge_name != ""

    def test_explainability_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = ExplainabilityAccountabilityBridge(state_dir=td)
            r = b.record("explain")
            assert r["bridge"] == "explainability_accountability"

    def test_certification_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = CertificationAccountabilityBridge(state_dir=td)
            r = b.record("certify")
            assert r["bridge"] == "certification_accountability"

    def test_orchestration_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = OrchestrationAccountabilityBridge(state_dir=td)
            r = b.record("orch")
            assert r["bridge"] == "orchestration_accountability"


# ── TestCoordinator ──────────────────────────────────────


class TestCoordinator:
    def test_start_accountability(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        r = c.start_accountability("test-run")
        assert r["run_id"] == "test-run"
        assert r["status"] == "started"

    def test_reconstruct_chronology(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        r = c.reconstruct_chronology()
        assert r["all_monotonic"] is True
        assert r["total"] == 7

    def test_reconstruct_governance_history(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        r = c.reconstruct_governance_history()
        assert r["all_deterministic"] is True

    def test_reconstruct_replay_history(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        r = c.reconstruct_replay_history()
        assert r["all_consistent"] is True

    def test_reconstruct_continuity_history(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        r = c.reconstruct_continuity_history()
        assert r["all_preserved"] is True

    def test_generate_provenance_history(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        r = c.generate_provenance_history()
        assert r["all_deterministic"] is True

    def test_generate_constitutional_audit(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        r = c.generate_constitutional_audit()
        assert r["all_compliant"] is True

    def test_verify_historical_integrity(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        r = c.verify_historical_integrity()
        assert r["historical_integrity_score"] == 1.0

    def test_validate_replay_determinism(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        r = c.validate_replay_determinism()
        assert r["all_deterministic"] is True

    def test_check_boundary(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        r = c.check_boundary("max_audits", 50)
        assert r["exceeded"] is False

    def test_complete_accountability(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        c.start_accountability("r1")
        c.reconstruct_chronology()
        c.reconstruct_governance_history()
        c.reconstruct_replay_history()
        c.reconstruct_continuity_history()
        c.generate_provenance_history()
        c.generate_constitutional_audit()
        c.verify_historical_integrity()
        c.validate_replay_determinism()
        r = c.complete_accountability("r1")
        assert r["outcome"] == "accountable"

    def test_get_accountability_report(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        c.reconstruct_chronology()
        c.reconstruct_governance_history()
        c.reconstruct_replay_history()
        c.reconstruct_continuity_history()
        c.generate_provenance_history()
        c.generate_constitutional_audit()
        c.verify_historical_integrity()
        r = c.get_accountability_report()
        assert r["all_accountable"] is True

    def test_get_stats(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        s = c.get_stats()
        assert "lifecycle" in s
        assert s["runs"] == 0

    def test_max_runs(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        for i in range(MAX_ACCOUNTABILITY_RUNS):
            c.start_accountability(f"r-{i}")
        with pytest.raises(ValueError):
            c.start_accountability("overflow")

    def test_auto_run_id(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        r = c.start_accountability()
        assert r["run_id"].startswith("acctrun-")

    def test_full_accountability_flow(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        c.start_accountability("full-flow")
        ch = c.reconstruct_chronology()
        assert ch["all_monotonic"] is True
        gov = c.reconstruct_governance_history()
        assert gov["all_deterministic"] is True
        rep = c.reconstruct_replay_history()
        assert rep["all_consistent"] is True
        cont = c.reconstruct_continuity_history()
        assert cont["all_preserved"] is True
        prov = c.generate_provenance_history()
        assert prov["all_deterministic"] is True
        audit = c.generate_constitutional_audit()
        assert audit["all_compliant"] is True
        integ = c.verify_historical_integrity()
        assert integ["historical_integrity_score"] == 1.0
        rv = c.validate_replay_determinism()
        assert rv["all_deterministic"] is True
        receipt = c.complete_accountability("full-flow")
        assert receipt["outcome"] == "accountable"
        report = c.get_accountability_report()
        assert report["all_accountable"] is True


# ── TestConstraintVerification ───────────────────────────


class TestConstraintVerification:
    def test_deterministic_chronology_reconstruction(self):
        e = ConstitutionalChronologyEngine()
        r = e.record_all_domains()
        assert r["all_monotonic"] is True

    def test_deterministic_governance_history(self):
        e = GovernanceHistoryEngine()
        r = e.record_all_types()
        assert r["all_deterministic"] is True

    def test_deterministic_replay_history(self):
        e = ReplayHistoryEngine()
        r = e.record_all_types()
        assert r["all_consistent"] is True

    def test_deterministic_continuity_history(self):
        e = ContinuityAccountabilityEngine()
        r = e.record_all_types()
        assert r["all_preserved"] is True

    def test_deterministic_audit_generation(self):
        e = ConstitutionalAuditEngine()
        r = e.generate_all_audits()
        assert r["all_deterministic"] is True

    def test_no_fabricated_accountability(self):
        bp = AccountabilityBoundaryPolicies()
        assert bp.is_forbidden("fabricated_accountability") is True

    def test_no_hidden_chronology_mutation(self):
        bp = AccountabilityBoundaryPolicies()
        assert bp.is_forbidden("hidden_chronology_mutation") is True

    def test_no_retroactive_lineage_rewriting(self):
        bp = AccountabilityBoundaryPolicies()
        assert bp.is_forbidden("retroactive_lineage_rewriting") is True

    def test_no_governance_bypass(self):
        bp = AccountabilityBoundaryPolicies()
        assert bp.is_forbidden("governance_bypass") is True

    def test_no_replay_bypass(self):
        bp = AccountabilityBoundaryPolicies()
        assert bp.is_forbidden("replay_bypass") is True

    def test_no_execution_outside_spine(self):
        bp = AccountabilityBoundaryPolicies()
        assert bp.is_forbidden("execution_outside_spine") is True

    def test_accountability_replay_determinism(self):
        v = SovereignAccountabilityReplayValidator()
        r = v.validate_all()
        assert r["all_deterministic"] is True

    def test_historical_integrity_preservation(self):
        e = HistoricalIntegrityEngine()
        r = e.verify_full_integrity()
        assert r["historical_integrity_score"] == 1.0

    def test_provenance_history_determinism(self):
        e = OperationalProvenanceHistoryEngine()
        r = e.generate_all_domains()
        assert r["all_deterministic"] is True

    def test_override_capping_enforced(self):
        bp = AccountabilityBoundaryPolicies()
        r = bp.check_limit("max_audits", 100, override=300)
        assert r["max_value"] == 200

    def test_coordinator_cannot_mutate_rewrite(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        assert not hasattr(c, "mutate")
        assert not hasattr(c, "rewrite")
        assert not hasattr(c, "fabricate")

    def test_lifecycle_linear_progression(self):
        e = AccountabilityLifecycleEngine()
        for p in ["reconstructing", "auditing", "validated", "archived"]:
            e.transition(p)
        assert e.is_terminal

    def test_lifecycle_terminal_absorbing(self):
        e = AccountabilityLifecycleEngine()
        for p in ["reconstructing", "auditing", "validated", "archived"]:
            e.transition(p)
        with pytest.raises(ValueError):
            e.transition("defined")

    def test_7_accountability_domains(self):
        assert len(AccountabilityDomain) == 7

    def test_full_accountability_flow(self):
        c = CanonicalSovereignAccountabilityCoordinator()
        c.start_accountability("constraint-flow")
        c.reconstruct_chronology()
        c.reconstruct_governance_history()
        c.reconstruct_replay_history()
        c.reconstruct_continuity_history()
        c.generate_provenance_history()
        c.generate_constitutional_audit()
        c.verify_historical_integrity()
        c.validate_replay_determinism()
        receipt = c.complete_accountability("constraint-flow")
        assert receipt["outcome"] == "accountable"
