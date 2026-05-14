"""Tests for Phase 96.8BZ — Adaptive Substrate Resilience Coordination.

Tests: contracts, lifecycle, instability detection, cascading failure
interruption, checkpoint integrity, degraded survivability, recovery
recommendation, observability, replay, boundary policies, continuity
bridges, canonical coordinator, constraint verification.
"""

from __future__ import annotations

import sys
import tempfile
import shutil

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import pytest

from core.resilience.adaptive_resilience_contracts_v1 import (
    ResilienceState,
    FaultContainmentState,
    InstabilitySignal,
    CascadingFailureState,
    RecoveryCoordinationReceipt,
    SubsystemHealthState,
    RecoveryBoundaryState,
    ContinuityPreservationState,
    CheckpointIntegrityState,
    RecoveryReplayState,
    SurvivabilityScore,
    IsolationDecision,
    RecoveryRecommendation,
    DegradedSurvivabilityState,
    ResilienceLifecycleState,
    ResilienceEventType,
    InstabilityClass,
    IsolationScope,
    RecoveryAction,
    _now_iso,
    _new_id,
)


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ── Contract Tests ──────────────────────────────────────────────


class TestResilienceState:
    def test_defaults(self):
        s = ResilienceState()
        assert s.state_id.startswith("rstate-")
        assert s.lifecycle == "stable"
        assert s.instability_score == 0.0

    def test_to_dict(self):
        s = ResilienceState()
        d = s.to_dict()
        assert "state_id" in d
        assert d["lifecycle"] == "stable"


class TestFaultContainmentState:
    def test_defaults(self):
        f = FaultContainmentState()
        assert f.containment_id.startswith("fcon-")
        assert f.contained is False

    def test_to_dict(self):
        f = FaultContainmentState(fault_source="sub_a", contained=True)
        d = f.to_dict()
        assert d["fault_source"] == "sub_a"
        assert d["contained"] is True


class TestInstabilitySignal:
    def test_defaults(self):
        s = InstabilitySignal()
        assert s.signal_id.startswith("isig-")
        assert s.instability_class == "transient"

    def test_to_dict(self):
        s = InstabilitySignal(source="sub_b", severity=0.5)
        d = s.to_dict()
        assert d["source"] == "sub_b"
        assert d["severity"] == 0.5


class TestCascadingFailureState:
    def test_defaults(self):
        c = CascadingFailureState()
        assert c.cascade_id.startswith("casc-")
        assert c.interrupted is False

    def test_to_dict(self):
        c = CascadingFailureState(origin_subsystem="sub_a")
        d = c.to_dict()
        assert d["origin_subsystem"] == "sub_a"


class TestRecoveryCoordinationReceipt:
    def test_defaults(self):
        r = RecoveryCoordinationReceipt()
        assert r.receipt_id.startswith("rrcpt-")

    def test_to_dict(self):
        r = RecoveryCoordinationReceipt(operation="test")
        d = r.to_dict()
        assert d["operation"] == "test"


class TestSubsystemHealthState:
    def test_defaults(self):
        h = SubsystemHealthState()
        assert h.health_id.startswith("sheal-")
        assert h.healthy is True

    def test_to_dict(self):
        h = SubsystemHealthState(subsystem_id="spine")
        d = h.to_dict()
        assert d["subsystem_id"] == "spine"


class TestRecoveryBoundaryState:
    def test_defaults(self):
        b = RecoveryBoundaryState()
        assert b.boundary_id.startswith("rbnd-")
        assert b.within_bounds is True

    def test_to_dict(self):
        b = RecoveryBoundaryState(max_recovery_attempts=5)
        assert b.to_dict()["max_recovery_attempts"] == 5


class TestContinuityPreservationState:
    def test_defaults(self):
        c = ContinuityPreservationState()
        assert c.preservation_id.startswith("cpres-")
        assert c.continuity_intact is True

    def test_to_dict(self):
        c = ContinuityPreservationState(checkpoint_count=3)
        assert c.to_dict()["checkpoint_count"] == 3


class TestCheckpointIntegrityState:
    def test_defaults(self):
        c = CheckpointIntegrityState()
        assert c.integrity_id.startswith("cint-")
        assert c.valid is True

    def test_to_dict(self):
        c = CheckpointIntegrityState(checkpoint_id="ckpt-test")
        assert c.to_dict()["checkpoint_id"] == "ckpt-test"


class TestRecoveryReplayState:
    def test_defaults(self):
        r = RecoveryReplayState()
        assert r.replay_id.startswith("rrply-")
        assert r.deterministic is True

    def test_to_dict(self):
        r = RecoveryReplayState(check_name="test_check")
        assert r.to_dict()["check_name"] == "test_check"


class TestSurvivabilityScore:
    def test_defaults(self):
        s = SurvivabilityScore()
        assert s.score_id.startswith("sscore-")
        assert s.overall_score == 1.0

    def test_to_dict(self):
        s = SurvivabilityScore(fault_tolerance=0.8)
        assert s.to_dict()["fault_tolerance"] == 0.8


class TestIsolationDecision:
    def test_defaults(self):
        i = IsolationDecision()
        assert i.decision_id.startswith("isodec-")
        assert i.isolated is False

    def test_to_dict(self):
        i = IsolationDecision(target="sub_a", isolated=True)
        d = i.to_dict()
        assert d["target"] == "sub_a"
        assert d["isolated"] is True


class TestRecoveryRecommendation:
    def test_defaults(self):
        r = RecoveryRecommendation()
        assert r.recommendation_id.startswith("rrec-")
        assert r.approved is False

    def test_to_dict(self):
        r = RecoveryRecommendation(action="restart_subsystem")
        assert r.to_dict()["action"] == "restart_subsystem"


class TestDegradedSurvivabilityState:
    def test_defaults(self):
        d = DegradedSurvivabilityState()
        assert d.survivability_id.startswith("dsurv-")
        assert d.can_continue is True

    def test_to_dict(self):
        d = DegradedSurvivabilityState(survivability_score=0.7)
        assert d.to_dict()["survivability_score"] == 0.7


# ── Enum Tests ──────────────────────────────────────────────────


class TestEnums:
    def test_resilience_lifecycle_state_count(self):
        assert len(ResilienceLifecycleState) == 10

    def test_resilience_event_type_count(self):
        assert len(ResilienceEventType) == 10

    def test_instability_class_count(self):
        assert len(InstabilityClass) == 5

    def test_isolation_scope_count(self):
        assert len(IsolationScope) == 5

    def test_recovery_action_count(self):
        assert len(RecoveryAction) == 5


# ── Lifecycle Tests ─────────────────────────────────────────────


class TestResilienceLifecycleEngine:
    def test_initial_state(self, tmp_dir):
        from core.resilience.resilience_lifecycle_engine_v1 import (
            ResilienceLifecycleEngine,
        )
        e = ResilienceLifecycleEngine(state_dir=tmp_dir)
        assert e.current_state == "stable"

    def test_valid_transition(self, tmp_dir):
        from core.resilience.resilience_lifecycle_engine_v1 import (
            ResilienceLifecycleEngine,
        )
        e = ResilienceLifecycleEngine(state_dir=tmp_dir)
        assert e.transition(ResilienceLifecycleState.MONITORED) is True
        assert e.current_state == "monitored"

    def test_invalid_transition(self, tmp_dir):
        from core.resilience.resilience_lifecycle_engine_v1 import (
            ResilienceLifecycleEngine,
        )
        e = ResilienceLifecycleEngine(state_dir=tmp_dir)
        assert e.transition(ResilienceLifecycleState.DEGRADED) is False
        assert e.current_state == "stable"

    def test_full_lifecycle(self, tmp_dir):
        from core.resilience.resilience_lifecycle_engine_v1 import (
            ResilienceLifecycleEngine,
        )
        e = ResilienceLifecycleEngine(state_dir=tmp_dir)
        assert e.transition(ResilienceLifecycleState.MONITORED)
        assert e.transition(ResilienceLifecycleState.UNSTABLE)
        assert e.transition(ResilienceLifecycleState.DEGRADED)
        assert e.transition(ResilienceLifecycleState.ISOLATED)
        assert e.transition(ResilienceLifecycleState.RECOVERING)
        assert e.transition(ResilienceLifecycleState.VALIDATED)
        assert e.transition(ResilienceLifecycleState.STABILIZED)
        assert e.transition(ResilienceLifecycleState.STABLE)
        assert e.current_state == "stable"

    def test_terminal_state(self, tmp_dir):
        from core.resilience.resilience_lifecycle_engine_v1 import (
            ResilienceLifecycleEngine,
        )
        e = ResilienceLifecycleEngine(state_dir=tmp_dir)
        e.transition(ResilienceLifecycleState.SUSPENDED)
        e.transition(ResilienceLifecycleState.ARCHIVED)
        assert e.current_state == "archived"
        assert e.transition(ResilienceLifecycleState.STABLE) is False

    def test_can_transition(self, tmp_dir):
        from core.resilience.resilience_lifecycle_engine_v1 import (
            ResilienceLifecycleEngine,
        )
        e = ResilienceLifecycleEngine(state_dir=tmp_dir)
        assert e.can_transition(ResilienceLifecycleState.MONITORED) is True
        assert e.can_transition(ResilienceLifecycleState.DEGRADED) is False

    def test_get_valid_transitions(self, tmp_dir):
        from core.resilience.resilience_lifecycle_engine_v1 import (
            ResilienceLifecycleEngine,
        )
        e = ResilienceLifecycleEngine(state_dir=tmp_dir)
        valid = e.get_valid_transitions()
        assert "monitored" in valid
        assert "suspended" in valid

    def test_stats(self, tmp_dir):
        from core.resilience.resilience_lifecycle_engine_v1 import (
            ResilienceLifecycleEngine,
        )
        e = ResilienceLifecycleEngine(state_dir=tmp_dir)
        e.transition(ResilienceLifecycleState.MONITORED)
        stats = e.get_stats()
        assert stats["total_transitions"] == 1


# ── Instability Detection Tests ─────────────────────────────────


class TestInstabilityDetectionEngine:
    def test_record_success(self, tmp_dir):
        from core.resilience.instability_detection_engine_v1 import (
            InstabilityDetectionEngine,
        )
        e = InstabilityDetectionEngine(state_dir=tmp_dir)
        h = e.record_success("sub_a")
        assert h.healthy is True
        assert h.consecutive_failures == 0

    def test_record_failure_below_threshold(self, tmp_dir):
        from core.resilience.instability_detection_engine_v1 import (
            InstabilityDetectionEngine,
        )
        e = InstabilityDetectionEngine(state_dir=tmp_dir)
        sig = e.record_failure("sub_a")
        assert sig is None

    def test_record_failure_triggers_signal(self, tmp_dir):
        from core.resilience.instability_detection_engine_v1 import (
            InstabilityDetectionEngine,
        )
        e = InstabilityDetectionEngine(state_dir=tmp_dir)
        for _ in range(2):
            e.record_failure("sub_a")
        sig = e.record_failure("sub_a")
        assert sig is not None
        assert sig.source == "sub_a"

    def test_compute_instability_score_zero(self, tmp_dir):
        from core.resilience.instability_detection_engine_v1 import (
            InstabilityDetectionEngine,
        )
        e = InstabilityDetectionEngine(state_dir=tmp_dir)
        assert e.compute_instability_score() == 0.0

    def test_compute_instability_score_nonzero(self, tmp_dir):
        from core.resilience.instability_detection_engine_v1 import (
            InstabilityDetectionEngine,
        )
        e = InstabilityDetectionEngine(state_dir=tmp_dir)
        e.record_success("sub_a")
        for _ in range(3):
            e.record_failure("sub_b")
        score = e.compute_instability_score()
        assert score > 0.0

    def test_classify_instability(self, tmp_dir):
        from core.resilience.instability_detection_engine_v1 import (
            InstabilityDetectionEngine,
        )
        e = InstabilityDetectionEngine(state_dir=tmp_dir)
        assert e.classify_instability(0.0) == "stable"
        assert e.classify_instability(0.2) == "transient"
        assert e.classify_instability(0.5) == "intermittent"
        assert e.classify_instability(0.7) == "persistent"
        assert e.classify_instability(0.85) == "cascading"
        assert e.classify_instability(0.95) == "systemic"

    def test_get_unhealthy_subsystems(self, tmp_dir):
        from core.resilience.instability_detection_engine_v1 import (
            InstabilityDetectionEngine,
        )
        e = InstabilityDetectionEngine(state_dir=tmp_dir)
        for _ in range(3):
            e.record_failure("sub_a")
        assert "sub_a" in e.get_unhealthy_subsystems()

    def test_get_degraded_subsystems(self, tmp_dir):
        from core.resilience.instability_detection_engine_v1 import (
            InstabilityDetectionEngine,
        )
        e = InstabilityDetectionEngine(state_dir=tmp_dir)
        for _ in range(3):
            e.record_failure("sub_a")
        assert "sub_a" in e.get_degraded_subsystems()

    def test_success_resets_failure(self, tmp_dir):
        from core.resilience.instability_detection_engine_v1 import (
            InstabilityDetectionEngine,
        )
        e = InstabilityDetectionEngine(state_dir=tmp_dir)
        e.record_failure("sub_a")
        e.record_failure("sub_a")
        e.record_success("sub_a")
        h = e.get_health("sub_a")
        assert h.consecutive_failures == 0
        assert h.healthy is True

    def test_max_subsystem_limit(self, tmp_dir):
        from core.resilience.instability_detection_engine_v1 import (
            InstabilityDetectionEngine,
            MAX_TRACKED_SUBSYSTEMS,
        )
        e = InstabilityDetectionEngine(state_dir=tmp_dir)
        for i in range(MAX_TRACKED_SUBSYSTEMS):
            e.record_success(f"sub_{i}")
        with pytest.raises(ValueError):
            e.record_success(f"sub_{MAX_TRACKED_SUBSYSTEMS}")

    def test_stats(self, tmp_dir):
        from core.resilience.instability_detection_engine_v1 import (
            InstabilityDetectionEngine,
        )
        e = InstabilityDetectionEngine(state_dir=tmp_dir)
        stats = e.get_stats()
        assert stats["total_subsystems"] == 0


# ── Cascading Failure Tests ──────────────────────────────────────


class TestCascadingFailureInterruptionEngine:
    def test_report_new_failure(self, tmp_dir):
        from core.resilience.cascading_failure_interruption_engine_v1 import (
            CascadingFailureInterruptionEngine,
        )
        e = CascadingFailureInterruptionEngine(state_dir=tmp_dir)
        c = e.report_failure("sub_a")
        assert c.origin_subsystem == "sub_a"
        assert not c.interrupted

    def test_report_cascading_failure(self, tmp_dir):
        from core.resilience.cascading_failure_interruption_engine_v1 import (
            CascadingFailureInterruptionEngine,
        )
        e = CascadingFailureInterruptionEngine(state_dir=tmp_dir)
        e.report_failure("sub_a")
        c = e.report_failure("sub_b", upstream_subsystem="sub_a")
        assert "sub_b" in c.affected_subsystems
        assert c.propagation_depth == 1

    def test_auto_interrupt_at_max_depth(self, tmp_dir):
        from core.resilience.cascading_failure_interruption_engine_v1 import (
            CascadingFailureInterruptionEngine,
            MAX_PROPAGATION_DEPTH,
        )
        e = CascadingFailureInterruptionEngine(state_dir=tmp_dir)
        e.report_failure("origin")
        for i in range(MAX_PROPAGATION_DEPTH):
            e.report_failure(f"sub_{i}", upstream_subsystem="origin")
        cascade = e.get_cascade("origin")
        assert cascade.interrupted is True

    def test_contain_fault(self, tmp_dir):
        from core.resilience.cascading_failure_interruption_engine_v1 import (
            CascadingFailureInterruptionEngine,
        )
        e = CascadingFailureInterruptionEngine(state_dir=tmp_dir)
        e.report_failure("sub_a")
        con = e.contain_fault("sub_a", "network", ["sub_b"])
        assert con.contained is True
        assert con.propagation_blocked is True

    def test_get_active_cascades(self, tmp_dir):
        from core.resilience.cascading_failure_interruption_engine_v1 import (
            CascadingFailureInterruptionEngine,
        )
        e = CascadingFailureInterruptionEngine(state_dir=tmp_dir)
        e.report_failure("sub_a")
        assert len(e.get_active_cascades()) == 1

    def test_clear_cascade(self, tmp_dir):
        from core.resilience.cascading_failure_interruption_engine_v1 import (
            CascadingFailureInterruptionEngine,
        )
        e = CascadingFailureInterruptionEngine(state_dir=tmp_dir)
        e.report_failure("sub_a")
        assert e.clear_cascade("sub_a") is True
        assert e.clear_cascade("nonexistent") is False

    def test_max_active_cascades(self, tmp_dir):
        from core.resilience.cascading_failure_interruption_engine_v1 import (
            CascadingFailureInterruptionEngine,
            MAX_ACTIVE_CASCADES,
        )
        e = CascadingFailureInterruptionEngine(state_dir=tmp_dir)
        for i in range(MAX_ACTIVE_CASCADES + 1):
            e.report_failure(f"origin_{i}")
        stats = e.get_stats()
        assert stats["total_cascades"] <= MAX_ACTIVE_CASCADES + 1

    def test_stats(self, tmp_dir):
        from core.resilience.cascading_failure_interruption_engine_v1 import (
            CascadingFailureInterruptionEngine,
        )
        e = CascadingFailureInterruptionEngine(state_dir=tmp_dir)
        stats = e.get_stats()
        assert stats["active_cascades"] == 0


# ── Checkpoint Integrity Tests ───────────────────────────────────


class TestCheckpointIntegrityEngine:
    def test_create_checkpoint(self, tmp_dir):
        from core.resilience.checkpoint_integrity_engine_v1 import (
            CheckpointIntegrityEngine,
        )
        e = CheckpointIntegrityEngine(state_dir=tmp_dir)
        ck = e.create_checkpoint("sub_a", {"version": 1})
        assert ck.checkpoint_id.startswith("ckpt-")
        assert ck.valid is True

    def test_validate_matching(self, tmp_dir):
        from core.resilience.checkpoint_integrity_engine_v1 import (
            CheckpointIntegrityEngine,
        )
        e = CheckpointIntegrityEngine(state_dir=tmp_dir)
        e.create_checkpoint("sub_a", {"version": 1, "data": "test"})
        result = e.validate_checkpoint("sub_a", {"version": 1, "data": "test"})
        assert result.valid is True

    def test_validate_mismatching(self, tmp_dir):
        from core.resilience.checkpoint_integrity_engine_v1 import (
            CheckpointIntegrityEngine,
        )
        e = CheckpointIntegrityEngine(state_dir=tmp_dir)
        e.create_checkpoint("sub_a", {"version": 1})
        result = e.validate_checkpoint("sub_a", {"version": 2})
        assert result.valid is False

    def test_validate_no_checkpoint(self, tmp_dir):
        from core.resilience.checkpoint_integrity_engine_v1 import (
            CheckpointIntegrityEngine,
        )
        e = CheckpointIntegrityEngine(state_dir=tmp_dir)
        result = e.validate_checkpoint("nonexistent", {"data": "x"})
        assert result is None

    def test_get_latest_checkpoint(self, tmp_dir):
        from core.resilience.checkpoint_integrity_engine_v1 import (
            CheckpointIntegrityEngine,
        )
        e = CheckpointIntegrityEngine(state_dir=tmp_dir)
        e.create_checkpoint("sub_a", {"v": 1})
        e.create_checkpoint("sub_a", {"v": 2})
        latest = e.get_latest_checkpoint("sub_a")
        assert latest is not None

    def test_checkpoint_count(self, tmp_dir):
        from core.resilience.checkpoint_integrity_engine_v1 import (
            CheckpointIntegrityEngine,
        )
        e = CheckpointIntegrityEngine(state_dir=tmp_dir)
        e.create_checkpoint("sub_a", {"v": 1})
        e.create_checkpoint("sub_a", {"v": 2})
        assert e.get_checkpoint_count("sub_a") == 2

    def test_preservation_state(self, tmp_dir):
        from core.resilience.checkpoint_integrity_engine_v1 import (
            CheckpointIntegrityEngine,
        )
        e = CheckpointIntegrityEngine(state_dir=tmp_dir)
        e.create_checkpoint("sub_a", {"v": 1})
        state = e.get_preservation_state()
        assert "sub_a" in state.preserved_subsystems

    def test_max_checkpoints_per_subsystem(self, tmp_dir):
        from core.resilience.checkpoint_integrity_engine_v1 import (
            CheckpointIntegrityEngine,
            MAX_CHECKPOINTS_PER_SUBSYSTEM,
        )
        e = CheckpointIntegrityEngine(state_dir=tmp_dir)
        for i in range(MAX_CHECKPOINTS_PER_SUBSYSTEM + 5):
            e.create_checkpoint("sub_a", {"v": i})
        assert e.get_checkpoint_count("sub_a") == MAX_CHECKPOINTS_PER_SUBSYSTEM

    def test_stats(self, tmp_dir):
        from core.resilience.checkpoint_integrity_engine_v1 import (
            CheckpointIntegrityEngine,
        )
        e = CheckpointIntegrityEngine(state_dir=tmp_dir)
        stats = e.get_stats()
        assert stats["total_checkpoints"] == 0


# ── Degraded Survivability Tests ─────────────────────────────────


class TestDegradedSurvivabilityEngine:
    def test_empty_assessment(self, tmp_dir):
        from core.resilience.degraded_survivability_engine_v1 import (
            DegradedSurvivabilityEngine,
        )
        e = DegradedSurvivabilityEngine(state_dir=tmp_dir)
        state = e.assess_survivability()
        assert state.survivability_score == 1.0
        assert state.can_continue is True

    def test_all_healthy(self, tmp_dir):
        from core.resilience.degraded_survivability_engine_v1 import (
            DegradedSurvivabilityEngine,
        )
        e = DegradedSurvivabilityEngine(state_dir=tmp_dir)
        e.register_subsystem("sub_a")
        e.register_subsystem("sub_b")
        state = e.assess_survivability()
        assert state.survivability_score == 1.0

    def test_partial_degradation(self, tmp_dir):
        from core.resilience.degraded_survivability_engine_v1 import (
            DegradedSurvivabilityEngine,
        )
        e = DegradedSurvivabilityEngine(state_dir=tmp_dir)
        e.register_subsystem("sub_a")
        e.register_subsystem("sub_b")
        e.mark_degraded("sub_a")
        state = e.assess_survivability()
        assert state.survivability_score < 1.0
        assert "sub_a" in state.degraded_subsystems

    def test_critical_subsystem_degradation(self, tmp_dir):
        from core.resilience.degraded_survivability_engine_v1 import (
            DegradedSurvivabilityEngine,
        )
        e = DegradedSurvivabilityEngine(state_dir=tmp_dir)
        e.register_subsystem("spine")
        e.register_subsystem("sub_a")
        e.mark_degraded("spine")
        state = e.assess_survivability()
        assert state.survivability_score < 0.5

    def test_below_minimum(self, tmp_dir):
        from core.resilience.degraded_survivability_engine_v1 import (
            DegradedSurvivabilityEngine,
        )
        e = DegradedSurvivabilityEngine(state_dir=tmp_dir)
        e.register_subsystem("spine")
        e.register_subsystem("governance")
        e.register_subsystem("continuity")
        e.mark_degraded("spine")
        e.mark_degraded("governance")
        e.mark_degraded("continuity")
        state = e.assess_survivability()
        assert state.can_continue is False

    def test_mark_functional_restores(self, tmp_dir):
        from core.resilience.degraded_survivability_engine_v1 import (
            DegradedSurvivabilityEngine,
        )
        e = DegradedSurvivabilityEngine(state_dir=tmp_dir)
        e.register_subsystem("sub_a")
        e.mark_degraded("sub_a")
        e.mark_functional("sub_a")
        state = e.assess_survivability()
        assert state.survivability_score == 1.0

    def test_compute_survivability_score(self, tmp_dir):
        from core.resilience.degraded_survivability_engine_v1 import (
            DegradedSurvivabilityEngine,
        )
        e = DegradedSurvivabilityEngine(state_dir=tmp_dir)
        e.register_subsystem("sub_a")
        score = e.compute_survivability_score()
        assert score.overall_score > 0.0
        assert "sub_a" in score.subsystem_scores

    def test_stats(self, tmp_dir):
        from core.resilience.degraded_survivability_engine_v1 import (
            DegradedSurvivabilityEngine,
        )
        e = DegradedSurvivabilityEngine(state_dir=tmp_dir)
        e.register_subsystem("sub_a")
        stats = e.get_stats()
        assert stats["total_subsystems"] == 1


# ── Recovery Recommendation Tests ────────────────────────────────


class TestRecoveryRecommendationEngine:
    def test_recommend(self, tmp_dir):
        from core.resilience.recovery_recommendation_engine_v1 import (
            RecoveryRecommendationEngine,
        )
        e = RecoveryRecommendationEngine(state_dir=tmp_dir)
        rec = e.recommend("sub_a", "persistent")
        assert rec.action == "isolate_environment"
        assert rec.priority == "high"
        assert rec.approved is False

    def test_recommend_cascading(self, tmp_dir):
        from core.resilience.recovery_recommendation_engine_v1 import (
            RecoveryRecommendationEngine,
        )
        e = RecoveryRecommendationEngine(state_dir=tmp_dir)
        rec = e.recommend("sub_a", "cascading")
        assert rec.priority == "critical"

    def test_approve(self, tmp_dir):
        from core.resilience.recovery_recommendation_engine_v1 import (
            RecoveryRecommendationEngine,
        )
        e = RecoveryRecommendationEngine(state_dir=tmp_dir)
        rec = e.recommend("sub_a")
        ok = e.approve(rec.recommendation_id, "operator")
        assert ok is True
        assert len(e.get_pending()) == 0

    def test_reject(self, tmp_dir):
        from core.resilience.recovery_recommendation_engine_v1 import (
            RecoveryRecommendationEngine,
        )
        e = RecoveryRecommendationEngine(state_dir=tmp_dir)
        rec = e.recommend("sub_a")
        ok = e.reject(rec.recommendation_id)
        assert ok is True
        assert len(e.get_pending()) == 0

    def test_approve_nonexistent(self, tmp_dir):
        from core.resilience.recovery_recommendation_engine_v1 import (
            RecoveryRecommendationEngine,
        )
        e = RecoveryRecommendationEngine(state_dir=tmp_dir)
        assert e.approve("fake-id") is False

    def test_get_pending_by_priority(self, tmp_dir):
        from core.resilience.recovery_recommendation_engine_v1 import (
            RecoveryRecommendationEngine,
        )
        e = RecoveryRecommendationEngine(state_dir=tmp_dir)
        e.recommend("sub_a", "cascading")
        e.recommend("sub_b", "transient")
        critical = e.get_pending_by_priority("critical")
        assert len(critical) == 1

    def test_history(self, tmp_dir):
        from core.resilience.recovery_recommendation_engine_v1 import (
            RecoveryRecommendationEngine,
        )
        e = RecoveryRecommendationEngine(state_dir=tmp_dir)
        rec = e.recommend("sub_a")
        e.approve(rec.recommendation_id)
        history = e.get_history()
        assert len(history) == 1

    def test_stats(self, tmp_dir):
        from core.resilience.recovery_recommendation_engine_v1 import (
            RecoveryRecommendationEngine,
        )
        e = RecoveryRecommendationEngine(state_dir=tmp_dir)
        rec = e.recommend("sub_a")
        e.approve(rec.recommendation_id)
        stats = e.get_stats()
        assert stats["total_generated"] == 1
        assert stats["total_approved"] == 1


# ── Observability Tests ──────────────────────────────────────────


class TestResilienceObservabilityPipeline:
    def test_emit_all_event_types(self, tmp_dir):
        from core.resilience.resilience_observability_pipeline_v1 import (
            ResilienceObservabilityPipeline,
        )
        p = ResilienceObservabilityPipeline(state_dir=tmp_dir)
        p.emit_instability_detected(source="sub_a")
        p.emit_fault_contained(source="sub_a")
        p.emit_cascade_interrupted(origin="sub_a")
        p.emit_checkpoint_created(subsystem="sub_a")
        p.emit_checkpoint_validated(subsystem="sub_a")
        p.emit_isolation_applied(target="sub_a")
        p.emit_recovery_recommended(target="sub_a")
        p.emit_recovery_validated(target="sub_a")
        p.emit_survivability_assessed(score=0.8)
        p.emit_resilience_restored(from_state="degraded")
        stats = p.get_stats()
        assert stats["total_events"] == 10

    def test_event_file_map_dynamic(self):
        from core.resilience.resilience_observability_pipeline_v1 import (
            EVENT_FILE_MAP,
            ResilienceEventType,
        )
        assert len(EVENT_FILE_MAP) == len(ResilienceEventType)

    def test_stats_counts(self, tmp_dir):
        from core.resilience.resilience_observability_pipeline_v1 import (
            ResilienceObservabilityPipeline,
        )
        p = ResilienceObservabilityPipeline(state_dir=tmp_dir)
        p.emit_instability_detected()
        p.emit_instability_detected()
        stats = p.get_stats()
        assert stats["event_counts"]["instability_detected"] == 2


# ── Replay Validator Tests ───────────────────────────────────────


class TestResilienceReplayValidator:
    def test_validate_all_checks(self, tmp_dir):
        from core.resilience.resilience_replay_validator_v1 import (
            ResilienceReplayValidator,
            REPLAY_CHECKS,
        )
        v = ResilienceReplayValidator(state_dir=tmp_dir)
        inputs = {c: {"test": True} for c in REPLAY_CHECKS}
        outputs = {c: {"result": True} for c in REPLAY_CHECKS}
        results = v.run_all_checks(inputs, outputs)
        assert len(results) == 5
        assert all(r.deterministic for r in results)

    def test_individual_check(self, tmp_dir):
        from core.resilience.resilience_replay_validator_v1 import (
            ResilienceReplayValidator,
        )
        v = ResilienceReplayValidator(state_dir=tmp_dir)
        r = v.validate_instability_detection({"a": 1}, {"b": 2})
        assert r.deterministic is True
        assert r.check_name == "instability_detection"

    def test_hash_stability(self, tmp_dir):
        from core.resilience.resilience_replay_validator_v1 import (
            ResilienceReplayValidator,
        )
        v = ResilienceReplayValidator(state_dir=tmp_dir)
        r1 = v.validate_fault_containment({"x": 1}, {"y": 2})
        r2 = v.validate_fault_containment({"x": 1}, {"y": 2})
        assert r1.input_hash == r2.input_hash
        assert r1.output_hash == r2.output_hash

    def test_stats(self, tmp_dir):
        from core.resilience.resilience_replay_validator_v1 import (
            ResilienceReplayValidator,
        )
        v = ResilienceReplayValidator(state_dir=tmp_dir)
        v.validate_checkpoint_integrity({}, {})
        stats = v.get_stats()
        assert stats["total_validations"] == 1
        assert stats["total_passes"] == 1


# ── Boundary Policy Tests ────────────────────────────────────────


class TestResilienceBoundaryPolicies:
    def test_limits_count(self):
        from core.resilience.resilience_boundary_policies_v1 import (
            RESILIENCE_LIMITS,
        )
        assert len(RESILIENCE_LIMITS) == 10

    def test_forbidden_count(self):
        from core.resilience.resilience_boundary_policies_v1 import (
            FORBIDDEN_RESILIENCE_ACTIONS,
        )
        assert len(FORBIDDEN_RESILIENCE_ACTIONS) == 10

    def test_enforce_recovery_bound(self):
        from core.resilience.resilience_boundary_policies_v1 import (
            enforce_recovery_bound,
        )
        assert enforce_recovery_bound(0) is True
        assert enforce_recovery_bound(2) is True
        assert enforce_recovery_bound(3) is False

    def test_enforce_isolation_depth(self):
        from core.resilience.resilience_boundary_policies_v1 import (
            enforce_isolation_depth,
        )
        assert enforce_isolation_depth(1) is True
        assert enforce_isolation_depth(3) is True
        assert enforce_isolation_depth(4) is False

    def test_enforce_cascade_depth(self):
        from core.resilience.resilience_boundary_policies_v1 import (
            enforce_cascade_depth,
        )
        assert enforce_cascade_depth(0) is True
        assert enforce_cascade_depth(2) is True
        assert enforce_cascade_depth(3) is False

    def test_enforce_survivability_floor(self):
        from core.resilience.resilience_boundary_policies_v1 import (
            enforce_survivability_floor,
        )
        assert enforce_survivability_floor(0.5) is True
        assert enforce_survivability_floor(0.3) is True
        assert enforce_survivability_floor(0.1) is False

    def test_cap_override(self):
        from core.resilience.resilience_boundary_policies_v1 import (
            cap_override,
        )
        assert cap_override(10, 5) == 5
        assert cap_override(3, 5) == 3

    def test_is_forbidden(self):
        from core.resilience.resilience_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("autonomous_repair") is True
        assert is_forbidden("legitimate_action") is False

    def test_get_all(self):
        from core.resilience.resilience_boundary_policies_v1 import (
            get_all_limits,
            get_all_forbidden,
        )
        assert len(get_all_limits()) == 10
        assert len(get_all_forbidden()) == 10


# ── Continuity Bridge Tests ──────────────────────────────────────


class TestResilienceContinuityBridges:
    def test_scaling_resilience_bridge(self, tmp_dir):
        from core.resilience.resilience_continuity_bridges_v1 import (
            ScalingResilienceBridge,
        )
        b = ScalingResilienceBridge(state_dir=tmp_dir)
        r = b.capture(pressure_score=0.5, instability_score=0.3)
        assert r["bridge_type"] == "scaling_resilience"
        assert b._total_captures == 1

    def test_environments_resilience_bridge(self, tmp_dir):
        from core.resilience.resilience_continuity_bridges_v1 import (
            EnvironmentsResilienceBridge,
        )
        b = EnvironmentsResilienceBridge(state_dir=tmp_dir)
        r = b.capture(environment_id="vps")
        assert r["bridge_type"] == "environments_resilience"

    def test_operations_resilience_bridge(self, tmp_dir):
        from core.resilience.resilience_continuity_bridges_v1 import (
            OperationsResilienceBridge,
        )
        b = OperationsResilienceBridge(state_dir=tmp_dir)
        r = b.capture(campaign_id="c1")
        assert r["bridge_type"] == "operations_resilience"

    def test_workflows_resilience_bridge(self, tmp_dir):
        from core.resilience.resilience_continuity_bridges_v1 import (
            WorkflowsResilienceBridge,
        )
        b = WorkflowsResilienceBridge(state_dir=tmp_dir)
        r = b.capture(workflow_id="wf1")
        assert r["bridge_type"] == "workflows_resilience"

    def test_sessions_resilience_bridge(self, tmp_dir):
        from core.resilience.resilience_continuity_bridges_v1 import (
            SessionsResilienceBridge,
        )
        b = SessionsResilienceBridge(state_dir=tmp_dir)
        r = b.capture(session_id="s1")
        assert r["bridge_type"] == "sessions_resilience"

    def test_replay_resilience_bridge(self, tmp_dir):
        from core.resilience.resilience_continuity_bridges_v1 import (
            ReplayResilienceBridge,
        )
        b = ReplayResilienceBridge(state_dir=tmp_dir)
        r = b.capture(total_validations=5)
        assert r["bridge_type"] == "replay_resilience"

    def test_continuity_resilience_bridge(self, tmp_dir):
        from core.resilience.resilience_continuity_bridges_v1 import (
            ContinuityResilienceBridge,
        )
        b = ContinuityResilienceBridge(state_dir=tmp_dir)
        r = b.capture(checkpoint_count=3)
        assert r["bridge_type"] == "continuity_resilience"

    def test_observability_resilience_bridge(self, tmp_dir):
        from core.resilience.resilience_continuity_bridges_v1 import (
            ObservabilityResilienceBridge,
        )
        b = ObservabilityResilienceBridge(state_dir=tmp_dir)
        r = b.capture(total_events=10)
        assert r["bridge_type"] == "observability_resilience"


# ── Coordinator Tests ────────────────────────────────────────────


class TestCanonicalResilienceCoordinationEngine:
    def test_record_success(self, tmp_dir):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine(state_dir=tmp_dir)
        r = c.record_success("sub_a")
        assert r["healthy"] is True

    def test_record_failure_instability(self, tmp_dir):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine(state_dir=tmp_dir)
        for _ in range(3):
            c.record_failure("sub_a")
        sig = c.record_failure("sub_a")
        assert "signal_id" in sig or sig.get("signal") is None

    def test_contain_fault(self, tmp_dir):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine(state_dir=tmp_dir)
        con = c.contain_fault("sub_a", "boundary_a")
        assert con["contained"] is True

    def test_isolate_subsystem(self, tmp_dir):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine(state_dir=tmp_dir)
        iso = c.isolate_subsystem("sub_a", "subsystem", "test")
        assert iso["isolated"] is True

    def test_checkpoint_create_validate(self, tmp_dir):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine(state_dir=tmp_dir)
        ck = c.create_checkpoint("sub_a", {"v": 1})
        assert "checkpoint_id" in ck
        val = c.validate_checkpoint("sub_a", {"v": 1})
        assert val["valid"] is True

    def test_checkpoint_validate_mismatch(self, tmp_dir):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine(state_dir=tmp_dir)
        c.create_checkpoint("sub_a", {"v": 1})
        val = c.validate_checkpoint("sub_a", {"v": 2})
        assert val["valid"] is False

    def test_assess_survivability(self, tmp_dir):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine(state_dir=tmp_dir)
        surv = c.assess_survivability()
        assert "survivability_score" in surv

    def test_recovery_flow(self, tmp_dir):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine(state_dir=tmp_dir)
        c.record_success("sub_a")
        for _ in range(4):
            c.record_failure("sub_b")
        health = c.get_health()
        assert health["lifecycle_state"] in (
            "monitored", "unstable", "degraded",
        )

    def test_pending_recommendations(self, tmp_dir):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine(state_dir=tmp_dir)
        for _ in range(3):
            c.record_failure("sub_a")
        pending = c.get_pending_recommendations()
        assert len(pending) >= 1

    def test_approve_recommendation(self, tmp_dir):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine(state_dir=tmp_dir)
        for _ in range(3):
            c.record_failure("sub_a")
        pending = c.get_pending_recommendations()
        if pending:
            ok = c.approve_recommendation(pending[0]["recommendation_id"])
            assert ok is True

    def test_reject_recommendation(self, tmp_dir):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine(state_dir=tmp_dir)
        for _ in range(3):
            c.record_failure("sub_a")
        pending = c.get_pending_recommendations()
        if pending:
            ok = c.reject_recommendation(pending[0]["recommendation_id"])
            assert ok is True

    def test_get_stats(self, tmp_dir):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine(state_dir=tmp_dir)
        stats = c.get_stats()
        assert "lifecycle" in stats
        assert "instability" in stats
        assert "cascade" in stats
        assert "checkpoint" in stats
        assert "survivability" in stats
        assert "recommendation" in stats
        assert "observability" in stats

    def test_get_health(self, tmp_dir):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine(state_dir=tmp_dir)
        h = c.get_health()
        assert h["lifecycle_state"] == "stable"
        assert h["instability_score"] == 0.0

    def test_receipts(self, tmp_dir):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine(state_dir=tmp_dir)
        for _ in range(3):
            c.record_failure("sub_a")
        receipts = c.get_recent_receipts()
        assert len(receipts) >= 1


# ── Constraint Verification Tests ────────────────────────────────


class TestConstraintVerification:
    def test_no_autonomous_repair(self):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine.__new__(
            CanonicalResilienceCoordinationEngine,
        )
        for attr in ["repair", "auto_repair", "self_repair", "fix", "auto_fix"]:
            assert not hasattr(c, attr)

    def test_no_automatic_rollback(self):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine.__new__(
            CanonicalResilienceCoordinationEngine,
        )
        for attr in ["rollback", "auto_rollback", "revert"]:
            assert not hasattr(c, attr)

    def test_no_self_directed_healing(self):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine.__new__(
            CanonicalResilienceCoordinationEngine,
        )
        for attr in ["heal", "self_heal", "auto_heal"]:
            assert not hasattr(c, attr)

    def test_no_uncontrolled_restart(self):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine.__new__(
            CanonicalResilienceCoordinationEngine,
        )
        for attr in ["restart", "restart_subsystem", "reboot"]:
            assert not hasattr(c, attr)

    def test_no_execute_recovery(self):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine.__new__(
            CanonicalResilienceCoordinationEngine,
        )
        for attr in ["execute_recovery", "run_recovery", "perform_recovery"]:
            assert not hasattr(c, attr)

    def test_no_hidden_state_mutation(self):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine.__new__(
            CanonicalResilienceCoordinationEngine,
        )
        for attr in ["mutate_state", "force_state", "override_state"]:
            assert not hasattr(c, attr)

    def test_recommendations_require_approval(self, tmp_dir):
        from core.resilience.recovery_recommendation_engine_v1 import (
            RecoveryRecommendationEngine,
        )
        e = RecoveryRecommendationEngine(state_dir=tmp_dir)
        rec = e.recommend("sub_a", "cascading")
        assert rec.approved is False
        assert rec.approved_by == ""

    def test_bounded_cascade_propagation(self, tmp_dir):
        from core.resilience.cascading_failure_interruption_engine_v1 import (
            CascadingFailureInterruptionEngine,
            MAX_PROPAGATION_DEPTH,
        )
        e = CascadingFailureInterruptionEngine(state_dir=tmp_dir)
        e.report_failure("origin")
        for i in range(MAX_PROPAGATION_DEPTH + 2):
            e.report_failure(f"sub_{i}", upstream_subsystem="origin")
        cascade = e.get_cascade("origin")
        assert cascade.interrupted is True

    def test_bounded_recovery_attempts(self):
        from core.resilience.resilience_boundary_policies_v1 import (
            enforce_recovery_bound,
            RESILIENCE_LIMITS,
        )
        max_attempts = RESILIENCE_LIMITS["max_recovery_attempts"]
        assert enforce_recovery_bound(max_attempts) is False
        assert enforce_recovery_bound(max_attempts - 1) is True

    def test_bounded_isolation_depth(self):
        from core.resilience.resilience_boundary_policies_v1 import (
            enforce_isolation_depth,
            RESILIENCE_LIMITS,
        )
        max_depth = RESILIENCE_LIMITS["max_isolation_depth"]
        assert enforce_isolation_depth(max_depth) is True
        assert enforce_isolation_depth(max_depth + 1) is False

    def test_deterministic_instability_replay(self, tmp_dir):
        from core.resilience.resilience_replay_validator_v1 import (
            ResilienceReplayValidator,
        )
        v = ResilienceReplayValidator(state_dir=tmp_dir)
        inp = {"subsystem": "sub_a", "failures": 3}
        out = {"score": 0.6, "class": "persistent"}
        r1 = v.validate_instability_detection(inp, out)
        r2 = v.validate_instability_detection(inp, out)
        assert r1.input_hash == r2.input_hash
        assert r1.output_hash == r2.output_hash

    def test_deterministic_containment_replay(self, tmp_dir):
        from core.resilience.resilience_replay_validator_v1 import (
            ResilienceReplayValidator,
        )
        v = ResilienceReplayValidator(state_dir=tmp_dir)
        inp = {"source": "sub_a", "boundary": "net"}
        out = {"contained": True}
        r1 = v.validate_fault_containment(inp, out)
        r2 = v.validate_fault_containment(inp, out)
        assert r1.input_hash == r2.input_hash

    def test_deterministic_cascade_replay(self, tmp_dir):
        from core.resilience.resilience_replay_validator_v1 import (
            ResilienceReplayValidator,
        )
        v = ResilienceReplayValidator(state_dir=tmp_dir)
        inp = {"origin": "sub_a", "depth": 2}
        out = {"interrupted": True}
        r1 = v.validate_cascade_interruption(inp, out)
        r2 = v.validate_cascade_interruption(inp, out)
        assert r1.input_hash == r2.input_hash

    def test_deterministic_checkpoint_replay(self, tmp_dir):
        from core.resilience.resilience_replay_validator_v1 import (
            ResilienceReplayValidator,
        )
        v = ResilienceReplayValidator(state_dir=tmp_dir)
        inp = {"subsystem": "sub_a", "hash": "abc123"}
        out = {"valid": True}
        r1 = v.validate_checkpoint_integrity(inp, out)
        r2 = v.validate_checkpoint_integrity(inp, out)
        assert r1.input_hash == r2.input_hash

    def test_deterministic_recommendation_replay(self, tmp_dir):
        from core.resilience.resilience_replay_validator_v1 import (
            ResilienceReplayValidator,
        )
        v = ResilienceReplayValidator(state_dir=tmp_dir)
        inp = {"target": "sub_a", "class": "persistent"}
        out = {"action": "isolate_environment"}
        r1 = v.validate_recovery_recommendation(inp, out)
        r2 = v.validate_recovery_recommendation(inp, out)
        assert r1.input_hash == r2.input_hash

    def test_all_forbidden_actions_enforced(self):
        from core.resilience.resilience_boundary_policies_v1 import (
            FORBIDDEN_RESILIENCE_ACTIONS,
            is_forbidden,
        )
        for action in FORBIDDEN_RESILIENCE_ACTIONS:
            assert is_forbidden(action) is True

    def test_no_execution_methods(self):
        from core.resilience.canonical_resilience_coordination_engine_v1 import (
            CanonicalResilienceCoordinationEngine,
        )
        c = CanonicalResilienceCoordinationEngine.__new__(
            CanonicalResilienceCoordinationEngine,
        )
        for attr in ["execute", "run_command", "dispatch", "invoke"]:
            assert not hasattr(c, attr)
