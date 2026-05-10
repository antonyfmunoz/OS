"""Tests for Phase 96.8CC — Substrate Adaptive Learning Coordination.

Covers all 11 modules: contracts, lifecycle, outcome learning,
pattern detection, improvement proposals, governance,
observability, replay, boundary policies, bridges, coordinator.

UMH substrate. Phase 96.8CC.
"""

import json
import shutil
import tempfile

import pytest

import sys
sys.path.insert(0, "/opt/OS")

from core.learning.adaptive_learning_contracts_v1 import (
    LearningSignal,
    OutcomeLearningState,
    FeedbackLearningState,
    PatternCandidate,
    ImprovementProposal,
    LearningReceipt,
    LearningConfidenceState,
    LearningBoundaryState,
    LearningReplayState,
    OperatorCorrectionState,
    PolicyLearningCandidate,
    TemplateLearningCandidate,
    RoutingLearningCandidate,
    KnowledgeLearningCandidate,
    LearningLifecycleState,
    LearningEventType,
    LearningSignalSource,
    ProposalType,
    PatternType,
    _now_iso,
    _new_id,
)
from core.learning.learning_lifecycle_engine_v1 import (
    LearningLifecycleEngine,
    VALID_TRANSITIONS,
    TERMINAL_STATES,
)
from core.learning.outcome_learning_engine_v1 import (
    OutcomeLearningEngine,
    MAX_SIGNALS,
    MAX_CORRECTIONS,
    KNOWN_SOURCES,
)
from core.learning.pattern_detection_engine_v1 import (
    PatternDetectionEngine,
    MAX_PATTERNS,
    MAX_SIGNALS_PER_PATTERN,
    OCCURRENCE_THRESHOLD,
    KNOWN_PATTERN_TYPES,
    SOURCE_TO_PATTERN,
)
from core.learning.improvement_proposal_engine_v1 import (
    ImprovementProposalEngine,
    MAX_PENDING_PROPOSALS,
    MAX_TOTAL_PROPOSALS,
    KNOWN_PROPOSAL_TYPES,
    MIN_CONFIDENCE_FOR_PROPOSAL,
)
from core.learning.learning_governance_engine_v1 import (
    LearningGovernanceEngine,
    MIN_CONFIDENCE_FOR_APPROVAL,
    GOVERNANCE_REQUIREMENTS,
)
from core.learning.learning_observability_pipeline_v1 import (
    LearningObservabilityPipeline,
    EVENT_FILE_MAP,
)
from core.learning.learning_replay_validator_v1 import (
    LearningReplayValidator,
    REPLAY_CHECKS,
)
from core.learning.learning_boundary_policies_v1 import (
    LEARNING_LIMITS,
    FORBIDDEN_LEARNING_ACTIONS,
    enforce_limit,
    is_forbidden,
    get_all_limits,
    get_all_forbidden,
    validate_boundaries,
)
from core.learning.learning_continuity_bridges_v1 import (
    KnowledgeLearningBridge,
    MemoryLearningBridge,
    IntelligenceLearningBridge,
    WorkflowsLearningBridge,
    OperationsLearningBridge,
    ResilienceLearningBridge,
    ScalingLearningBridge,
    ReplayLearningBridge,
    ObservabilityLearningBridge,
    ALL_BRIDGES,
)
from core.learning.canonical_adaptive_learning_coordinator_v1 import (
    CanonicalAdaptiveLearningCoordinator,
)


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ── Contract tests ──────────────────────────────────────────────


class TestContracts:
    def test_learning_signal_defaults(self):
        s = LearningSignal()
        assert s.signal_id.startswith("lsig-")
        assert s.severity == 0.0
        d = s.to_dict()
        assert "signal_id" in d

    def test_outcome_learning_state(self):
        o = OutcomeLearningState()
        assert o.outcome_id.startswith("olrn-")
        d = o.to_dict()
        assert d["signal_count"] == 0

    def test_feedback_learning_state(self):
        f = FeedbackLearningState(source="operator")
        assert f.feedback_id.startswith("flrn-")
        assert f.applied is False

    def test_pattern_candidate(self):
        p = PatternCandidate(pattern_type="repeated_failure")
        assert p.pattern_id.startswith("pcan-")
        assert p.confidence == 0.0

    def test_improvement_proposal(self):
        p = ImprovementProposal()
        assert p.proposal_id.startswith("iprop-")
        assert p.approved is False
        assert p.denied is False
        assert p.applied_by_operator is False

    def test_learning_receipt(self):
        r = LearningReceipt(operation="approval")
        assert r.receipt_id.startswith("lrcpt-")

    def test_learning_confidence_state(self):
        c = LearningConfidenceState()
        assert c.confidence_id.startswith("lconf-")

    def test_learning_boundary_state(self):
        b = LearningBoundaryState(action="test")
        assert b.boundary_id.startswith("lbnd-")

    def test_learning_replay_state(self):
        r = LearningReplayState(check_name="test")
        assert r.replay_id.startswith("lrply-")
        assert r.deterministic is True

    def test_operator_correction_state(self):
        c = OperatorCorrectionState(original_action="a", corrected_action="b")
        assert c.correction_id.startswith("ocorr-")
        assert c.corrected_by == "operator"

    def test_policy_learning_candidate(self):
        p = PolicyLearningCandidate(policy_name="test")
        assert p.candidate_id.startswith("plcan-")

    def test_template_learning_candidate(self):
        t = TemplateLearningCandidate(template_name="test")
        assert t.candidate_id.startswith("tlcan-")

    def test_routing_learning_candidate(self):
        r = RoutingLearningCandidate(route_name="test")
        assert r.candidate_id.startswith("rlcan-")

    def test_knowledge_learning_candidate(self):
        k = KnowledgeLearningCandidate(concept="test")
        assert k.candidate_id.startswith("klcan-")

    def test_all_contracts_have_to_dict(self):
        contracts = [
            LearningSignal(), OutcomeLearningState(),
            FeedbackLearningState(), PatternCandidate(),
            ImprovementProposal(), LearningReceipt(),
            LearningConfidenceState(), LearningBoundaryState(),
            LearningReplayState(), OperatorCorrectionState(),
            PolicyLearningCandidate(), TemplateLearningCandidate(),
            RoutingLearningCandidate(), KnowledgeLearningCandidate(),
        ]
        for c in contracts:
            d = c.to_dict()
            assert isinstance(d, dict)
            assert "timestamp" in d


class TestEnums:
    def test_lifecycle_states_count(self):
        assert len(LearningLifecycleState) == 8

    def test_event_types_count(self):
        assert len(LearningEventType) == 7

    def test_signal_sources_count(self):
        assert len(LearningSignalSource) == 8

    def test_proposal_types_count(self):
        assert len(ProposalType) == 8

    def test_pattern_types_count(self):
        assert len(PatternType) == 7

    def test_lifecycle_values(self):
        vals = {s.value for s in LearningLifecycleState}
        assert "observed" in vals
        assert "approved" in vals
        assert "applied_by_operator" in vals

    def test_proposal_type_values(self):
        vals = {p.value for p in ProposalType}
        assert "policy_update_candidate" in vals
        assert "knowledge_promotion_candidate" in vals


# ── Lifecycle engine tests ──────────────────────────────────────


class TestLifecycleEngine:
    def test_initial_state(self):
        eng = LearningLifecycleEngine()
        assert eng.current_state == "observed"

    def test_valid_transition(self):
        eng = LearningLifecycleEngine()
        result = eng.transition(LearningLifecycleState.CANDIDATE)
        assert result == "candidate"

    def test_invalid_transition_raises(self):
        eng = LearningLifecycleEngine()
        with pytest.raises(ValueError):
            eng.transition(LearningLifecycleState.APPROVED)

    def test_full_approval_lifecycle(self):
        eng = LearningLifecycleEngine()
        eng.transition(LearningLifecycleState.CANDIDATE)
        eng.transition(LearningLifecycleState.PROPOSED)
        eng.transition(LearningLifecycleState.REVIEWED)
        eng.transition(LearningLifecycleState.APPROVED)
        eng.transition(LearningLifecycleState.APPLIED_BY_OPERATOR)
        eng.transition(LearningLifecycleState.ARCHIVED)
        assert eng.current_state == "archived"

    def test_denial_lifecycle(self):
        eng = LearningLifecycleEngine()
        eng.transition(LearningLifecycleState.CANDIDATE)
        eng.transition(LearningLifecycleState.PROPOSED)
        eng.transition(LearningLifecycleState.REVIEWED)
        eng.transition(LearningLifecycleState.DENIED)
        eng.transition(LearningLifecycleState.ARCHIVED)
        assert eng.current_state == "archived"

    def test_terminal_state_no_transition(self):
        eng = LearningLifecycleEngine()
        eng.transition(LearningLifecycleState.CANDIDATE)
        eng.transition(LearningLifecycleState.PROPOSED)
        eng.transition(LearningLifecycleState.REVIEWED)
        eng.transition(LearningLifecycleState.DENIED)
        eng.transition(LearningLifecycleState.ARCHIVED)
        with pytest.raises(ValueError):
            eng.transition(LearningLifecycleState.OBSERVED)

    def test_terminal_states_set(self):
        assert TERMINAL_STATES == {"archived"}

    def test_transitions_recorded(self):
        eng = LearningLifecycleEngine()
        eng.transition(LearningLifecycleState.CANDIDATE)
        trans = eng.get_transitions()
        assert len(trans) == 1
        assert trans[0]["from"] == "observed"
        assert trans[0]["to"] == "candidate"

    def test_stats(self):
        eng = LearningLifecycleEngine()
        eng.transition(LearningLifecycleState.CANDIDATE)
        stats = eng.get_stats()
        assert stats["total_transitions"] == 1
        assert stats["is_terminal"] is False

    def test_valid_transitions_all_states_covered(self):
        states = {s.value for s in LearningLifecycleState}
        assert set(VALID_TRANSITIONS.keys()) == states


# ── Outcome learning engine tests ───────────────────────────────


class TestOutcomeLearningEngine:
    def test_observe_signal(self):
        eng = OutcomeLearningEngine()
        sig = eng.observe("workflow_failure", "db timeout", 0.7)
        assert sig["signal_id"].startswith("lsig-")
        assert sig["source"] == "workflow_failure"

    def test_severity_bounded(self):
        eng = OutcomeLearningEngine()
        sig = eng.observe("workflow_failure", "test", 5.0)
        assert sig["severity"] == 1.0
        sig2 = eng.observe("workflow_failure", "test", -1.0)
        assert sig2["severity"] == 0.0

    def test_counts_by_source(self):
        eng = OutcomeLearningEngine()
        eng.observe("workflow_success", "ok")
        eng.observe("workflow_failure", "fail")
        eng.observe("action_denied", "denied")
        state = eng.get_outcome_state()
        assert state["success_count"] == 1
        assert state["failure_count"] == 1
        assert state["denial_count"] == 1

    def test_record_correction_operator_only(self):
        eng = OutcomeLearningEngine()
        corr = eng.record_correction("retry_3x", "retry_1x", "too aggressive")
        assert corr["corrected_by"] == "operator"

    def test_record_correction_non_operator_rejected(self):
        eng = OutcomeLearningEngine()
        with pytest.raises(ValueError):
            eng.record_correction("a", "b", corrected_by="system")

    def test_get_signals_by_source(self):
        eng = OutcomeLearningEngine()
        eng.observe("workflow_failure", "fail1")
        eng.observe("workflow_success", "ok1")
        eng.observe("workflow_failure", "fail2")
        failures = eng.get_signals_by_source("workflow_failure")
        assert len(failures) == 2

    def test_outcome_hash_present(self):
        eng = OutcomeLearningEngine()
        eng.observe("workflow_failure", "test")
        state = eng.get_outcome_state()
        assert len(state["outcome_hash"]) == 16

    def test_get_corrections(self):
        eng = OutcomeLearningEngine()
        eng.record_correction("a", "b", "reason")
        corrections = eng.get_corrections()
        assert len(corrections) >= 1

    def test_stats(self):
        eng = OutcomeLearningEngine()
        eng.observe("workflow_failure", "test")
        stats = eng.get_stats()
        assert stats["total_signals"] >= 1
        assert stats["failure_count"] == 1


# ── Pattern detection engine tests ──────────────────────────────


class TestPatternDetectionEngine:
    def test_no_pattern_below_threshold(self):
        eng = PatternDetectionEngine()
        result = eng.ingest_signal("s1", "workflow_failure", "timeout")
        assert result is None

    def test_pattern_detected_at_threshold(self):
        eng = PatternDetectionEngine()
        for i in range(OCCURRENCE_THRESHOLD):
            result = eng.ingest_signal(f"s{i}", "workflow_failure", "timeout")
        assert result is not None
        assert result.pattern_type == "repeated_failure"

    def test_pattern_confidence_increases(self):
        eng = PatternDetectionEngine()
        for i in range(5):
            result = eng.ingest_signal(f"s{i}", "workflow_failure", "timeout")
        assert result.confidence == 0.5

    def test_unknown_source_returns_none(self):
        eng = PatternDetectionEngine()
        result = eng.ingest_signal("s1", "unknown_source", "test")
        assert result is None

    def test_source_to_pattern_mapping(self):
        assert SOURCE_TO_PATTERN["workflow_failure"] == "repeated_failure"
        assert SOURCE_TO_PATTERN["operator_correction"] == "repeated_correction"
        assert SOURCE_TO_PATTERN["action_denied"] == "repeated_denial"
        assert SOURCE_TO_PATTERN["workflow_success"] == "recurring_success_route"

    def test_get_patterns_by_type(self):
        eng = PatternDetectionEngine()
        for i in range(3):
            eng.ingest_signal(f"s{i}", "workflow_failure", "timeout")
        patterns = eng.get_patterns_by_type("repeated_failure")
        assert len(patterns) == 1

    def test_get_high_confidence(self):
        eng = PatternDetectionEngine()
        for i in range(10):
            eng.ingest_signal(f"s{i}", "workflow_failure", "timeout")
        high = eng.get_high_confidence(0.5)
        assert len(high) >= 1

    def test_pattern_hash_deterministic(self):
        eng = PatternDetectionEngine()
        for i in range(3):
            result = eng.ingest_signal(f"s{i}", "workflow_failure", "timeout")
        assert len(result.pattern_hash) == 16

    def test_different_content_different_patterns(self):
        eng = PatternDetectionEngine()
        for i in range(3):
            eng.ingest_signal(f"a{i}", "workflow_failure", "timeout_a")
        for i in range(3):
            eng.ingest_signal(f"b{i}", "workflow_failure", "timeout_b")
        patterns = eng.get_patterns()
        assert len(patterns) == 2

    def test_stats(self):
        eng = PatternDetectionEngine()
        for i in range(3):
            eng.ingest_signal(f"s{i}", "workflow_failure", "timeout")
        stats = eng.get_stats()
        assert stats["total_detected"] == 1
        assert stats["active_patterns"] == 1


# ── Improvement proposal engine tests ───────────────────────────


class TestImprovementProposalEngine:
    def test_generate_proposal(self):
        eng = ImprovementProposalEngine()
        prop = eng.generate(
            "policy_update_candidate", "Reduce retry",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        assert prop is not None
        assert prop.approved is False

    def test_unknown_type_rejected(self):
        eng = ImprovementProposalEngine()
        assert eng.generate("invented_type", "test", confidence=0.5) is None

    def test_low_confidence_rejected(self):
        eng = ImprovementProposalEngine()
        assert eng.generate(
            "policy_update_candidate", "test", confidence=0.1,
        ) is None

    def test_approve_requires_operator(self):
        eng = ImprovementProposalEngine()
        prop = eng.generate(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        with pytest.raises(ValueError):
            eng.approve(prop.proposal_id, approved_by="system")

    def test_approve_requires_provenance(self):
        eng = ImprovementProposalEngine()
        prop = eng.generate(
            "policy_update_candidate", "test", confidence=0.5,
        )
        result = eng.approve(prop.proposal_id)
        assert result is None

    def test_approve_requires_rollback_reference(self):
        eng = ImprovementProposalEngine()
        prop = eng.generate(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"],
        )
        result = eng.approve(prop.proposal_id)
        assert result is None

    def test_approve_with_all_requirements(self):
        eng = ImprovementProposalEngine()
        prop = eng.generate(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        approved = eng.approve(prop.proposal_id)
        assert approved is not None
        assert approved.approved is True

    def test_deny_requires_operator(self):
        eng = ImprovementProposalEngine()
        prop = eng.generate(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        with pytest.raises(ValueError):
            eng.deny(prop.proposal_id, denied_by="system")

    def test_deny_proposal(self):
        eng = ImprovementProposalEngine()
        prop = eng.generate(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        denied = eng.deny(prop.proposal_id)
        assert denied is not None
        assert denied.denied is True

    def test_mark_applied(self):
        eng = ImprovementProposalEngine()
        prop = eng.generate(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        eng.approve(prop.proposal_id)
        applied = eng.mark_applied(prop.proposal_id)
        assert applied is not None
        assert applied.applied_by_operator is True

    def test_mark_applied_unapproved_returns_none(self):
        eng = ImprovementProposalEngine()
        prop = eng.generate(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        eng.deny(prop.proposal_id)
        assert eng.mark_applied(prop.proposal_id) is None

    def test_proposal_hash_present(self):
        eng = ImprovementProposalEngine()
        prop = eng.generate(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        assert len(prop.proposal_hash) == 16

    def test_get_pending(self):
        eng = ImprovementProposalEngine()
        eng.generate(
            "policy_update_candidate", "a", confidence=0.5,
            provenance=["x"], rollback_reference="v1",
        )
        eng.generate(
            "routing_update_candidate", "b", confidence=0.5,
            provenance=["y"], rollback_reference="v1",
        )
        pending = eng.get_pending()
        assert len(pending) == 2

    def test_all_proposal_types_known(self):
        expected = {pt.value for pt in ProposalType}
        assert KNOWN_PROPOSAL_TYPES == expected

    def test_stats(self):
        eng = ImprovementProposalEngine()
        prop = eng.generate(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        eng.approve(prop.proposal_id)
        stats = eng.get_stats()
        assert stats["total_generated"] == 1
        assert stats["total_approved"] == 1


# ── Governance engine tests ─────────────────────────────────────


class TestGovernanceEngine:
    def test_validate_complete_proposal(self):
        eng = LearningGovernanceEngine()
        prop = ImprovementProposal(
            proposal_type="policy_update_candidate",
            confidence=0.5,
            provenance=["a"],
            rollback_reference="v1",
        )
        result = eng.validate_proposal(prop)
        assert result["passed"] is True
        assert result["violations"] == []

    def test_validate_missing_provenance(self):
        eng = LearningGovernanceEngine()
        prop = ImprovementProposal(
            proposal_type="policy_update_candidate",
            confidence=0.5,
            rollback_reference="v1",
        )
        result = eng.validate_proposal(prop)
        assert result["passed"] is False
        assert "missing_provenance" in result["violations"]

    def test_validate_low_confidence(self):
        eng = LearningGovernanceEngine()
        prop = ImprovementProposal(
            proposal_type="policy_update_candidate",
            confidence=0.1,
            provenance=["a"],
            rollback_reference="v1",
        )
        result = eng.validate_proposal(prop)
        assert result["passed"] is False
        assert "insufficient_confidence" in result["violations"]

    def test_validate_missing_rollback(self):
        eng = LearningGovernanceEngine()
        prop = ImprovementProposal(
            proposal_type="policy_update_candidate",
            confidence=0.5,
            provenance=["a"],
        )
        result = eng.validate_proposal(prop)
        assert result["passed"] is False
        assert "missing_rollback_reference" in result["violations"]

    def test_record_approval_operator_only(self):
        eng = LearningGovernanceEngine()
        receipt = eng.record_approval("p1", "pending", "approved")
        assert receipt["approved_by"] == "operator"

    def test_record_approval_non_operator_rejected(self):
        eng = LearningGovernanceEngine()
        with pytest.raises(ValueError):
            eng.record_approval("p1", "pending", "approved", approved_by="system")

    def test_record_denial_operator_only(self):
        eng = LearningGovernanceEngine()
        receipt = eng.record_denial("p1", "pending")
        assert receipt["approved_by"] == "operator"

    def test_record_denial_non_operator_rejected(self):
        eng = LearningGovernanceEngine()
        with pytest.raises(ValueError):
            eng.record_denial("p1", "pending", denied_by="system")

    def test_governance_requirements(self):
        assert len(GOVERNANCE_REQUIREMENTS) == 6
        assert "operator_approval_required" in GOVERNANCE_REQUIREMENTS
        assert "provenance_required" in GOVERNANCE_REQUIREMENTS

    def test_stats(self):
        eng = LearningGovernanceEngine()
        prop = ImprovementProposal(
            proposal_type="test", confidence=0.5,
            provenance=["a"], rollback_reference="v1",
        )
        eng.validate_proposal(prop)
        stats = eng.get_stats()
        assert stats["total_checks"] == 1


# ── Observability pipeline tests ────────────────────────────────


class TestObservabilityPipeline:
    def test_event_file_map_count(self):
        assert len(EVENT_FILE_MAP) == 7

    def test_event_file_map_matches_enum(self):
        enum_vals = {e.value for e in LearningEventType}
        map_keys = set(EVENT_FILE_MAP.keys())
        assert enum_vals == map_keys

    def test_emit_learning_signal_observed(self, tmp_dir):
        p = LearningObservabilityPipeline(state_dir=tmp_dir)
        p.emit_learning_signal_observed("s1", "workflow_failure")
        assert p.get_stats()["event_counts"]["learning_signal_observed"] == 1

    def test_emit_pattern_candidate_detected(self, tmp_dir):
        p = LearningObservabilityPipeline(state_dir=tmp_dir)
        p.emit_pattern_candidate_detected("p1", "repeated_failure", 0.5)
        assert p.get_stats()["event_counts"]["pattern_candidate_detected"] == 1

    def test_emit_proposal_generated(self, tmp_dir):
        p = LearningObservabilityPipeline(state_dir=tmp_dir)
        p.emit_proposal_generated("ip1", "policy_update_candidate")
        assert p.get_stats()["event_counts"]["proposal_generated"] == 1

    def test_emit_proposal_denied(self, tmp_dir):
        p = LearningObservabilityPipeline(state_dir=tmp_dir)
        p.emit_proposal_denied("ip1", "operator_denied")
        assert p.get_stats()["event_counts"]["proposal_denied"] == 1

    def test_emit_proposal_approved(self, tmp_dir):
        p = LearningObservabilityPipeline(state_dir=tmp_dir)
        p.emit_proposal_approved("ip1")
        assert p.get_stats()["event_counts"]["proposal_approved"] == 1

    def test_emit_learning_boundary_denied(self, tmp_dir):
        p = LearningObservabilityPipeline(state_dir=tmp_dir)
        p.emit_learning_boundary_denied("mutate", "forbidden")
        assert p.get_stats()["event_counts"]["learning_boundary_denied"] == 1

    def test_emit_learning_replay_validated(self, tmp_dir):
        p = LearningObservabilityPipeline(state_dir=tmp_dir)
        p.emit_learning_replay_validated("outcome_classification", True)
        assert p.get_stats()["event_counts"]["learning_replay_validated"] == 1

    def test_total_events(self, tmp_dir):
        p = LearningObservabilityPipeline(state_dir=tmp_dir)
        p.emit_learning_signal_observed("s1", "test")
        p.emit_proposal_generated("p1", "test")
        assert p.get_stats()["total_events"] == 2

    def test_events_written_to_file(self, tmp_dir):
        p = LearningObservabilityPipeline(state_dir=tmp_dir)
        p.emit_learning_signal_observed("s1", "test")
        from pathlib import Path
        f = Path(tmp_dir) / "learning_signal_observed.jsonl"
        assert f.exists()
        data = json.loads(f.read_text().strip())
        assert data["event_type"] == "learning_signal_observed"


# ── Replay validator tests ──────────────────────────────────────


class TestReplayValidator:
    def test_replay_checks_count(self):
        assert len(REPLAY_CHECKS) == 5

    def test_validate_determinism(self):
        v = LearningReplayValidator()
        result = v.validate_determinism("outcome_classification", "in", "out")
        assert result["deterministic"] is True

    def test_unknown_check_rejected(self):
        v = LearningReplayValidator()
        with pytest.raises(ValueError):
            v.validate_determinism("fake_check", "in", "out")

    def test_replay_pair_same_output(self):
        v = LearningReplayValidator()
        result = v.validate_replay_pair(
            "pattern_detection", "in", "out", "out",
        )
        assert result["deterministic"] is True

    def test_replay_pair_different_output(self):
        v = LearningReplayValidator()
        result = v.validate_replay_pair(
            "pattern_detection", "in", "out_a", "out_b",
        )
        assert result["deterministic"] is False

    def test_all_checks_valid(self):
        v = LearningReplayValidator()
        for check in REPLAY_CHECKS:
            result = v.validate_determinism(check, "in", "out")
            assert result["deterministic"] is True

    def test_stats(self):
        v = LearningReplayValidator()
        v.validate_determinism("outcome_classification", "in", "out")
        stats = v.get_stats()
        assert stats["total_checks"] == 1
        assert stats["deterministic_count"] == 1


# ── Boundary policies tests ────────────────────────────────────


class TestBoundaryPolicies:
    def test_limits_count(self):
        assert len(LEARNING_LIMITS) == 8

    def test_forbidden_count(self):
        assert len(FORBIDDEN_LEARNING_ACTIONS) == 8

    def test_enforce_limit_default(self):
        assert enforce_limit("max_pending_proposals") == 50

    def test_enforce_limit_override_lower(self):
        assert enforce_limit("max_pending_proposals", 10) == 10

    def test_enforce_limit_override_higher_capped(self):
        assert enforce_limit("max_pending_proposals", 100) == 50

    def test_enforce_limit_unknown_raises(self):
        with pytest.raises(ValueError):
            enforce_limit("nonexistent")

    def test_is_forbidden_true(self):
        assert is_forbidden("autonomous_self_improvement") is True

    def test_is_forbidden_false(self):
        assert is_forbidden("normal_operation") is False

    def test_get_all_limits(self):
        assert len(get_all_limits()) == 8

    def test_get_all_forbidden(self):
        assert len(get_all_forbidden()) == 8

    def test_validate_boundaries(self):
        result = validate_boundaries()
        assert result["limits_count"] == 8
        assert result["forbidden_count"] == 8

    def test_autonomous_self_improvement_forbidden(self):
        assert "autonomous_self_improvement" in FORBIDDEN_LEARNING_ACTIONS

    def test_silent_canonical_mutation_forbidden(self):
        assert "silent_canonical_mutation" in FORBIDDEN_LEARNING_ACTIONS

    def test_silent_policy_mutation_forbidden(self):
        assert "silent_policy_mutation" in FORBIDDEN_LEARNING_ACTIONS

    def test_silent_template_mutation_forbidden(self):
        assert "silent_template_mutation" in FORBIDDEN_LEARNING_ACTIONS

    def test_hidden_routing_mutation_forbidden(self):
        assert "hidden_routing_mutation" in FORBIDDEN_LEARNING_ACTIONS

    def test_learning_owned_execution_forbidden(self):
        assert "learning_owned_execution" in FORBIDDEN_LEARNING_ACTIONS

    def test_self_authored_objectives_forbidden(self):
        assert "self_authored_objectives" in FORBIDDEN_LEARNING_ACTIONS

    def test_uncontrolled_pattern_promotion_forbidden(self):
        assert "uncontrolled_pattern_promotion" in FORBIDDEN_LEARNING_ACTIONS


# ── Continuity bridges tests ────────────────────────────────────


class TestContinuityBridges:
    def test_all_bridges_count(self):
        assert len(ALL_BRIDGES) == 9

    def test_knowledge_bridge(self, tmp_dir):
        b = KnowledgeLearningBridge(state_dir=tmp_dir)
        event = b.record("sync", {"key": "value"})
        assert event["bridge"] == "knowledge_learning"

    def test_memory_bridge(self, tmp_dir):
        b = MemoryLearningBridge(state_dir=tmp_dir)
        event = b.record("sync", {})
        assert event["bridge"] == "memory_learning"

    def test_intelligence_bridge(self, tmp_dir):
        b = IntelligenceLearningBridge(state_dir=tmp_dir)
        event = b.record("sync", {})
        assert event["bridge"] == "intelligence_learning"

    def test_workflows_bridge(self, tmp_dir):
        b = WorkflowsLearningBridge(state_dir=tmp_dir)
        event = b.record("sync", {})
        assert event["bridge"] == "workflows_learning"

    def test_operations_bridge(self, tmp_dir):
        b = OperationsLearningBridge(state_dir=tmp_dir)
        event = b.record("sync", {})
        assert event["bridge"] == "operations_learning"

    def test_resilience_bridge(self, tmp_dir):
        b = ResilienceLearningBridge(state_dir=tmp_dir)
        event = b.record("sync", {})
        assert event["bridge"] == "resilience_learning"

    def test_scaling_bridge(self, tmp_dir):
        b = ScalingLearningBridge(state_dir=tmp_dir)
        event = b.record("sync", {})
        assert event["bridge"] == "scaling_learning"

    def test_replay_bridge(self, tmp_dir):
        b = ReplayLearningBridge(state_dir=tmp_dir)
        event = b.record("sync", {})
        assert event["bridge"] == "replay_learning"

    def test_observability_bridge(self, tmp_dir):
        b = ObservabilityLearningBridge(state_dir=tmp_dir)
        event = b.record("sync", {})
        assert event["bridge"] == "observability_learning"

    def test_bridge_events_tracked(self, tmp_dir):
        b = KnowledgeLearningBridge(state_dir=tmp_dir)
        b.record("sync", {"a": 1})
        b.record("update", {"b": 2})
        events = b.get_events()
        assert len(events) == 2

    def test_bridge_stats(self, tmp_dir):
        b = KnowledgeLearningBridge(state_dir=tmp_dir)
        b.record("sync", {})
        stats = b.get_stats()
        assert stats["total_events"] == 1

    def test_bridge_writes_to_file(self, tmp_dir):
        b = KnowledgeLearningBridge(state_dir=tmp_dir)
        b.record("sync", {"test": True})
        from pathlib import Path
        f = Path(tmp_dir) / "knowledge_learning.jsonl"
        assert f.exists()


# ── Coordinator tests ───────────────────────────────────────────


class TestCoordinator:
    def test_observe_signal(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        sig = c.observe_signal("workflow_failure", "timeout", 0.7)
        assert sig["signal_id"].startswith("lsig-")

    def test_record_correction(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        corr = c.record_correction("retry_3x", "retry_1x", "too aggressive")
        assert corr["corrected_by"] == "operator"

    def test_pattern_detection_via_coordinator(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        for i in range(OCCURRENCE_THRESHOLD + 1):
            c.observe_signal("workflow_failure", "timeout", 0.7)
        patterns = c.get_patterns()
        assert len(patterns) >= 1

    def test_generate_proposal(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        prop = c.generate_proposal(
            "policy_update_candidate", "Reduce retry",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        assert prop is not None
        assert prop["approved"] is False

    def test_generate_proposal_low_confidence_rejected(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        result = c.generate_proposal(
            "policy_update_candidate", "test", confidence=0.1,
        )
        assert result is None

    def test_generate_proposal_governance_validation(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        prop = c.generate_proposal(
            "policy_update_candidate", "test", confidence=0.5,
        )
        assert prop is not None
        assert prop["governance_validation"]["passed"] is False

    def test_approve_proposal(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        prop = c.generate_proposal(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        approved = c.approve_proposal(prop["proposal_id"])
        assert approved is not None
        assert approved["approved"] is True

    def test_deny_proposal(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        prop = c.generate_proposal(
            "routing_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        denied = c.deny_proposal(prop["proposal_id"])
        assert denied is not None
        assert denied["denied"] is True

    def test_mark_applied(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        prop = c.generate_proposal(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        c.approve_proposal(prop["proposal_id"])
        applied = c.mark_applied(prop["proposal_id"])
        assert applied is not None
        assert applied["applied_by_operator"] is True

    def test_get_learning_state(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        c.observe_signal("workflow_success", "ok")
        state = c.get_learning_state()
        assert state["success_count"] == 1

    def test_get_signals_by_source(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        c.observe_signal("workflow_failure", "fail")
        c.observe_signal("workflow_success", "ok")
        failures = c.get_signals_by_source("workflow_failure")
        assert len(failures) == 1

    def test_get_patterns_by_type(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        for i in range(3):
            c.observe_signal("workflow_failure", "timeout")
        patterns = c.get_patterns_by_type("repeated_failure")
        assert len(patterns) == 1

    def test_get_high_confidence_patterns(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        for i in range(10):
            c.observe_signal("workflow_failure", "timeout")
        high = c.get_high_confidence_patterns(0.5)
        assert len(high) >= 1

    def test_get_pending_proposals(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        c.generate_proposal(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        pending = c.get_pending_proposals()
        assert len(pending) == 1

    def test_get_governance_receipts(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        prop = c.generate_proposal(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        c.approve_proposal(prop["proposal_id"])
        receipts = c.get_governance_receipts()
        assert len(receipts) >= 1

    def test_get_health(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        health = c.get_health()
        assert "lifecycle_state" in health
        assert "outcomes" in health
        assert "patterns" in health
        assert "proposals" in health

    def test_get_stats_six_subsystems(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        stats = c.get_stats()
        assert len(stats) == 6
        expected = {
            "lifecycle", "outcomes", "patterns",
            "proposals", "governance", "observability",
        }
        assert set(stats.keys()) == expected

    def test_no_forbidden_methods(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        forbidden = [
            "execute", "dispatch", "run", "invoke",
            "mutate_canon", "mutate_policy", "mutate_routing",
            "mutate_template", "auto_improve", "self_improve",
        ]
        for method in forbidden:
            assert not hasattr(c, method), f"Has forbidden: {method}"


# ── Constraint verification tests ───────────────────────────────


class TestConstraintVerification:
    def test_no_autonomous_self_improvement(self):
        assert is_forbidden("autonomous_self_improvement")

    def test_no_silent_canonical_mutation(self):
        assert is_forbidden("silent_canonical_mutation")

    def test_no_silent_policy_mutation(self):
        assert is_forbidden("silent_policy_mutation")

    def test_no_silent_template_mutation(self):
        assert is_forbidden("silent_template_mutation")

    def test_no_hidden_routing_mutation(self):
        assert is_forbidden("hidden_routing_mutation")

    def test_no_learning_owned_execution(self):
        assert is_forbidden("learning_owned_execution")

    def test_no_self_authored_objectives(self):
        assert is_forbidden("self_authored_objectives")

    def test_operator_approval_required_for_proposals(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        prop = c.generate_proposal(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        assert prop["approved"] is False

    def test_operator_only_corrections(self):
        eng = OutcomeLearningEngine()
        with pytest.raises(ValueError):
            eng.record_correction("a", "b", corrected_by="system")

    def test_operator_only_approval(self):
        eng = ImprovementProposalEngine()
        prop = eng.generate(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        with pytest.raises(ValueError):
            eng.approve(prop.proposal_id, approved_by="system")

    def test_operator_only_denial(self):
        eng = ImprovementProposalEngine()
        prop = eng.generate(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        with pytest.raises(ValueError):
            eng.deny(prop.proposal_id, denied_by="system")

    def test_provenance_required(self):
        eng = ImprovementProposalEngine()
        prop = eng.generate(
            "policy_update_candidate", "test", confidence=0.5,
        )
        result = eng.approve(prop.proposal_id)
        assert result is None

    def test_rollback_reference_required(self):
        eng = ImprovementProposalEngine()
        prop = eng.generate(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"],
        )
        result = eng.approve(prop.proposal_id)
        assert result is None

    def test_learning_cannot_execute(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        forbidden = ["execute", "dispatch", "run", "invoke"]
        for method in forbidden:
            assert not hasattr(c, method)

    def test_bounded_pattern_detection(self):
        eng = PatternDetectionEngine()
        for i in range(3):
            eng.ingest_signal(f"s{i}", "workflow_failure", "timeout")
        assert eng.get_stats()["active_patterns"] <= MAX_PATTERNS

    def test_bounded_pending_proposals(self):
        eng = ImprovementProposalEngine()
        for i in range(MAX_PENDING_PROPOSALS + 5):
            eng.generate(
                "policy_update_candidate", f"test_{i}",
                confidence=0.5, provenance=["a"], rollback_reference="v1",
            )
        assert len(eng.get_pending()) <= MAX_PENDING_PROPOSALS

    def test_deterministic_proposal_hash(self):
        eng = ImprovementProposalEngine()
        p1 = eng.generate(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        p2 = eng.generate(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        assert p1.proposal_hash == p2.proposal_hash

    def test_deterministic_pattern_hash(self):
        eng1 = PatternDetectionEngine()
        eng2 = PatternDetectionEngine()
        for i in range(3):
            r1 = eng1.ingest_signal(f"s{i}", "workflow_failure", "timeout")
            r2 = eng2.ingest_signal(f"s{i}", "workflow_failure", "timeout")
        assert r1.pattern_hash == r2.pattern_hash

    def test_override_capping(self):
        assert enforce_limit("max_pending_proposals", 100) == 50
        assert enforce_limit("max_pending_proposals", 10) == 10

    def test_terminal_lifecycle_states(self):
        eng = LearningLifecycleEngine()
        eng.transition(LearningLifecycleState.CANDIDATE)
        eng.transition(LearningLifecycleState.PROPOSED)
        eng.transition(LearningLifecycleState.REVIEWED)
        eng.transition(LearningLifecycleState.DENIED)
        eng.transition(LearningLifecycleState.ARCHIVED)
        with pytest.raises(ValueError):
            eng.transition(LearningLifecycleState.OBSERVED)

    def test_proposal_lifecycle_correctness(self, tmp_dir):
        c = CanonicalAdaptiveLearningCoordinator(state_dir=tmp_dir)
        prop = c.generate_proposal(
            "policy_update_candidate", "test",
            confidence=0.5, provenance=["a"], rollback_reference="v1",
        )
        assert prop["approved"] is False
        assert prop["denied"] is False

        approved = c.approve_proposal(prop["proposal_id"])
        assert approved["approved"] is True
        assert approved["denied"] is False

        applied = c.mark_applied(prop["proposal_id"])
        assert applied["applied_by_operator"] is True
