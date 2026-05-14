"""Tests for Phase 96.8BV — Persistent Operational Substrate Sessions.

Tests:
  - contracts (10 contracts, 4 enums)
  - canonical session manager
  - session lifecycle engine
  - session chronology engine
  - session checkpoint engine
  - session continuity engine
  - session observability pipeline
  - session replay validator
  - session boundary policies
  - session continuity bridges
  - constraint enforcement (15 constraint classes)
"""

import sys
import tempfile

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.sessions.persistent_substrate_session_contracts_v1 import (
    CheckpointType,
    ChronologyEventKind,
    SessionCheckpoint,
    SessionChronology,
    SessionCognitionState,
    SessionContinuityState,
    SessionEmbodimentState,
    SessionEventType,
    SessionIngressState,
    SessionLifecycleState,
    SessionLineageReceipt,
    SessionState,
    SessionWorkflowState,
    SubstrateSession,
    _content_hash,
)
from core.sessions.canonical_substrate_session_manager_v1 import (
    CanonicalSubstrateSessionManager,
)
from core.sessions.session_lifecycle_engine_v1 import (
    SessionLifecycleEngine,
    VALID_SESSION_TRANSITIONS,
    TERMINAL_STATES,
)
from core.sessions.session_chronology_engine_v1 import SessionChronologyEngine
from core.sessions.session_checkpoint_engine_v1 import SessionCheckpointEngine
from core.sessions.session_continuity_engine_v1 import SessionContinuityEngine
from core.sessions.session_observability_pipeline_v1 import (
    SessionObservabilityPipeline,
    EVENT_FILE_MAP,
)
from core.sessions.session_replay_validator_v1 import (
    SessionReplayValidator,
    DETERMINISM_CHECKS,
)
from core.sessions.session_boundary_policies_v1 import (
    SessionBoundaryEnforcer,
    DEFAULT_SESSION_BOUNDARIES,
    FORBIDDEN_SESSION_OPERATIONS,
)
from core.sessions.session_continuity_bridges_v1 import (
    SessionIngressBridge,
    SessionCognitionBridge,
    SessionWorkflowBridge,
    SessionEmbodimentBridge,
    SessionObservabilityBridge,
    SessionReplayBridge,
)


# =========================================================================
# Contract Tests
# =========================================================================


class TestSessionContracts:

    def test_enum_session_state(self):
        assert len(SessionState) == 8
        assert SessionState.INITIALIZED.value == "initialized"
        assert SessionState.TERMINATED.value == "terminated"

    def test_enum_session_event_type(self):
        assert len(SessionEventType) == 9
        assert SessionEventType.SESSION_CREATED.value == "session_created"
        assert SessionEventType.CHRONOLOGY_UPDATED.value == "chronology_updated"

    def test_enum_chronology_event_kind(self):
        assert len(ChronologyEventKind) == 8
        assert ChronologyEventKind.SESSION_CREATION.value == "session_creation"
        assert ChronologyEventKind.OPERATOR_RESUMPTION.value == "operator_resumption"

    def test_enum_checkpoint_type(self):
        assert len(CheckpointType) == 3
        assert CheckpointType.RESUMABLE.value == "resumable"
        assert CheckpointType.LINEAGE_COMPLETE.value == "lineage_complete"

    def test_substrate_session(self):
        s = SubstrateSession(operator_id="op-1")
        assert s.session_id.startswith("sssess-")
        assert s.operator_id == "op-1"
        d = s.to_dict()
        assert "session_id" in d
        assert "operator_id" in d

    def test_session_chronology(self):
        ch = SessionChronology(session_id="s-1", kind="session_creation")
        assert ch.event_id.startswith("sschron-")
        d = ch.to_dict()
        assert d["kind"] == "session_creation"

    def test_session_checkpoint(self):
        cp = SessionCheckpoint(session_id="s-1")
        assert cp.checkpoint_id.startswith("sschkp-")
        assert cp.content_hash
        d = cp.to_dict()
        assert "content_hash" in d

    def test_session_continuity_state(self):
        cs = SessionContinuityState(session_id="s-1")
        assert cs.continuity_id.startswith("sscont-")
        assert cs.content_hash

    def test_session_cognition_state(self):
        c = SessionCognitionState(session_id="s-1", operator_mode="focused")
        d = c.to_dict()
        assert d["operator_mode"] == "focused"

    def test_session_workflow_state(self):
        w = SessionWorkflowState(session_id="s-1", active_workflows=2)
        d = w.to_dict()
        assert d["active_workflows"] == 2

    def test_session_embodiment_state(self):
        e = SessionEmbodimentState(session_id="s-1", workstation_mode="developer")
        d = e.to_dict()
        assert d["workstation_mode"] == "developer"

    def test_session_ingress_state(self):
        i = SessionIngressState(session_id="s-1", total_signals=5)
        d = i.to_dict()
        assert d["total_signals"] == 5

    def test_session_lifecycle_state(self):
        ls = SessionLifecycleState(session_id="s-1", state="active")
        d = ls.to_dict()
        assert d["state"] == "active"

    def test_session_lineage_receipt(self):
        lr = SessionLineageReceipt(session_id="s-1", operation="create")
        assert lr.receipt_id.startswith("ssrcpt-")
        assert lr.content_hash

    def test_all_contracts_serialize_deterministically(self):
        s1 = SubstrateSession(session_id="fixed", operator_id="op-1")
        s2 = SubstrateSession(session_id="fixed", operator_id="op-1")
        d1 = {k: v for k, v in s1.to_dict().items() if k not in ("created_at", "last_activity")}
        d2 = {k: v for k, v in s2.to_dict().items() if k not in ("created_at", "last_activity")}
        assert d1 == d2

    def test_content_hash_changes_with_data(self):
        h1 = _content_hash({"a": 1})
        h2 = _content_hash({"a": 2})
        assert h1 != h2


# =========================================================================
# Lifecycle Engine Tests
# =========================================================================


class TestSessionLifecycleEngine:

    def test_register_session(self, tmp_path):
        lce = SessionLifecycleEngine(state_dir=tmp_path)
        state = lce.register("s-1")
        assert state == "initialized"
        assert lce.get_state("s-1") == "initialized"

    def test_valid_transitions(self, tmp_path):
        lce = SessionLifecycleEngine(state_dir=tmp_path)
        lce.register("s-1")
        assert lce.transition("s-1", SessionState.ACTIVE)
        assert lce.get_state("s-1") == "active"
        assert lce.transition("s-1", SessionState.CHECKPOINTED)
        assert lce.transition("s-1", SessionState.SUSPENDED)
        assert lce.transition("s-1", SessionState.RESUMED)
        assert lce.transition("s-1", SessionState.ACTIVE)

    def test_invalid_transition(self, tmp_path):
        lce = SessionLifecycleEngine(state_dir=tmp_path)
        lce.register("s-1")
        assert not lce.transition("s-1", SessionState.RESUMED)

    def test_terminal_state(self, tmp_path):
        lce = SessionLifecycleEngine(state_dir=tmp_path)
        lce.register("s-1")
        lce.transition("s-1", SessionState.ACTIVE)
        lce.transition("s-1", SessionState.TERMINATED)
        assert lce.is_terminal("s-1")
        assert not lce.transition("s-1", SessionState.ACTIVE)

    def test_full_lifecycle(self, tmp_path):
        lce = SessionLifecycleEngine(state_dir=tmp_path)
        lce.register("s-1")
        lce.transition("s-1", SessionState.ACTIVE)
        lce.transition("s-1", SessionState.CHECKPOINTED)
        lce.transition("s-1", SessionState.ARCHIVED)
        lce.transition("s-1", SessionState.TERMINATED)
        assert lce.is_terminal("s-1")

    def test_lineage_persisted(self, tmp_path):
        lce = SessionLifecycleEngine(state_dir=tmp_path)
        lce.register("s-1")
        lce.transition("s-1", SessionState.ACTIVE)
        path = tmp_path / "session_lifecycle_lineage.jsonl"
        assert path.exists()

    def test_active_sessions(self, tmp_path):
        lce = SessionLifecycleEngine(state_dir=tmp_path)
        lce.register("s-1")
        lce.register("s-2")
        lce.transition("s-1", SessionState.ACTIVE)
        lce.transition("s-2", SessionState.ACTIVE)
        lce.transition("s-2", SessionState.TERMINATED)
        active = lce.get_active_sessions()
        assert "s-1" in active
        assert "s-2" not in active

    def test_nonexistent_session(self, tmp_path):
        lce = SessionLifecycleEngine(state_dir=tmp_path)
        assert lce.get_state("nope") is None
        assert not lce.transition("nope", SessionState.ACTIVE)


# =========================================================================
# Chronology Engine Tests
# =========================================================================


class TestSessionChronologyEngine:

    def test_record_event(self, tmp_path):
        ce = SessionChronologyEngine(state_dir=tmp_path)
        ev = ce.record_session_creation("s-1", operator_id="op-1")
        assert ev.session_id == "s-1"
        assert ev.sequence_number == 0

    def test_sequence_numbers(self, tmp_path):
        ce = SessionChronologyEngine(state_dir=tmp_path)
        e1 = ce.record_session_creation("s-1")
        e2 = ce.record_runtime_traversal("s-1", command="status")
        e3 = ce.record_cognition_transition("s-1", "active", "focused")
        assert e1.sequence_number == 0
        assert e2.sequence_number == 1
        assert e3.sequence_number == 2

    def test_all_event_kinds(self, tmp_path):
        ce = SessionChronologyEngine(state_dir=tmp_path)
        ce.record_session_creation("s-1")
        ce.record_runtime_traversal("s-1")
        ce.record_cognition_transition("s-1")
        ce.record_workflow_transition("s-1")
        ce.record_embodiment_transition("s-1")
        ce.record_ingress_transition("s-1")
        ce.record_continuity_restoration("s-1")
        ce.record_operator_resumption("s-1")
        assert ce.get_sequence_number("s-1") == 8

    def test_chronology_snapshot(self, tmp_path):
        ce = SessionChronologyEngine(state_dir=tmp_path)
        ce.record_session_creation("s-1")
        ce.record_runtime_traversal("s-1")
        snap = ce.get_chronology_snapshot("s-1")
        assert len(snap) == 2

    def test_persistence(self, tmp_path):
        ce = SessionChronologyEngine(state_dir=tmp_path)
        ce.record_session_creation("s-1")
        path = tmp_path / "session_chronology.jsonl"
        assert path.exists()

    def test_per_session_isolation(self, tmp_path):
        ce = SessionChronologyEngine(state_dir=tmp_path)
        ce.record_session_creation("s-1")
        ce.record_session_creation("s-2")
        ce.record_runtime_traversal("s-1")
        assert ce.get_sequence_number("s-1") == 2
        assert ce.get_sequence_number("s-2") == 1


# =========================================================================
# Checkpoint Engine Tests
# =========================================================================


class TestSessionCheckpointEngine:

    def test_create_checkpoint(self, tmp_path):
        cpe = SessionCheckpointEngine(state_dir=tmp_path)
        cont = SessionContinuityState(session_id="s-1")
        cp = cpe.create_checkpoint("s-1", cont)
        assert cp.checkpoint_id.startswith("sschkp-")
        assert cp.content_hash

    def test_latest_checkpoint(self, tmp_path):
        cpe = SessionCheckpointEngine(state_dir=tmp_path)
        cont = SessionContinuityState(session_id="s-1")
        cp1 = cpe.create_checkpoint("s-1", cont)
        cp2 = cpe.create_checkpoint("s-1", cont)
        latest = cpe.get_latest_checkpoint("s-1")
        assert latest.checkpoint_id == cp2.checkpoint_id

    def test_checkpoint_by_id(self, tmp_path):
        cpe = SessionCheckpointEngine(state_dir=tmp_path)
        cont = SessionContinuityState(session_id="s-1")
        cp = cpe.create_checkpoint("s-1", cont)
        found = cpe.get_checkpoint_by_id(cp.checkpoint_id)
        assert found is not None
        assert found.checkpoint_id == cp.checkpoint_id

    def test_checkpoint_types(self, tmp_path):
        cpe = SessionCheckpointEngine(state_dir=tmp_path)
        cont = SessionContinuityState(session_id="s-1")
        cp1 = cpe.create_checkpoint("s-1", cont, checkpoint_type=CheckpointType.RESUMABLE)
        cp2 = cpe.create_checkpoint("s-1", cont, checkpoint_type=CheckpointType.REPLAYABLE)
        cp3 = cpe.create_checkpoint("s-1", cont, checkpoint_type=CheckpointType.LINEAGE_COMPLETE)
        assert cp1.checkpoint_type == "resumable"
        assert cp2.checkpoint_type == "replayable"
        assert cp3.checkpoint_type == "lineage_complete"

    def test_verify_hash(self, tmp_path):
        cpe = SessionCheckpointEngine(state_dir=tmp_path)
        cont = SessionContinuityState(session_id="s-1")
        cp = cpe.create_checkpoint("s-1", cont)
        assert cpe.verify_checkpoint_hash(cp)

    def test_persistence(self, tmp_path):
        cpe = SessionCheckpointEngine(state_dir=tmp_path)
        cont = SessionContinuityState(session_id="s-1")
        cp = cpe.create_checkpoint("s-1", cont)
        path = tmp_path / f"session_checkpoint_{cp.checkpoint_id}.json"
        assert path.exists()
        ledger = tmp_path / "session_checkpoints.jsonl"
        assert ledger.exists()

    def test_sequence_numbers(self, tmp_path):
        cpe = SessionCheckpointEngine(state_dir=tmp_path)
        cont = SessionContinuityState(session_id="s-1")
        cp1 = cpe.create_checkpoint("s-1", cont)
        cp2 = cpe.create_checkpoint("s-1", cont)
        assert cp1.sequence_number == 0
        assert cp2.sequence_number == 1


# =========================================================================
# Continuity Engine Tests
# =========================================================================


class TestSessionContinuityEngine:

    def test_capture_state(self, tmp_path):
        ce = SessionContinuityEngine(state_dir=tmp_path)
        cog = SessionCognitionState(session_id="s-1", operator_mode="focused")
        state = ce.capture("s-1", cognition=cog)
        assert state.session_id == "s-1"
        assert state.cognition.operator_mode == "focused"

    def test_update_layers(self, tmp_path):
        ce = SessionContinuityEngine(state_dir=tmp_path)
        ce.capture("s-1")
        cog = SessionCognitionState(session_id="s-1", operator_mode="planning")
        result = ce.update_cognition("s-1", cog)
        assert result is not None
        assert result.cognition.operator_mode == "planning"

        wf = SessionWorkflowState(session_id="s-1", active_workflows=3)
        result = ce.update_workflow("s-1", wf)
        assert result.workflow.active_workflows == 3

    def test_restore(self, tmp_path):
        ce = SessionContinuityEngine(state_dir=tmp_path)
        original = ce.capture("s-1")
        ce2 = SessionContinuityEngine(state_dir=tmp_path)
        restored = ce2.restore("s-1", original)
        assert restored.content_hash == original.content_hash

    def test_resume_packet(self, tmp_path):
        ce = SessionContinuityEngine(state_dir=tmp_path)
        ce.capture("s-1")
        packet = ce.build_resume_packet("s-1")
        assert packet["available"]
        assert "continuity" in packet

    def test_missing_session(self, tmp_path):
        ce = SessionContinuityEngine(state_dir=tmp_path)
        assert ce.get_state("nope") is None
        packet = ce.build_resume_packet("nope")
        assert not packet["available"]

    def test_persistence(self, tmp_path):
        ce = SessionContinuityEngine(state_dir=tmp_path)
        ce.capture("s-1")
        path = tmp_path / "session_continuity.jsonl"
        assert path.exists()


# =========================================================================
# Observability Pipeline Tests
# =========================================================================


class TestSessionObservabilityPipeline:

    def test_all_9_event_types(self, tmp_path):
        obs = SessionObservabilityPipeline(obs_dir=tmp_path)
        for et in SessionEventType:
            obs.record_event(et, "s-1")
        assert obs.get_stats()["total_events"] == 9

    def test_event_file_map_complete(self):
        assert len(EVENT_FILE_MAP) == 9
        for et in SessionEventType:
            assert et.value in EVENT_FILE_MAP

    def test_convenience_methods(self, tmp_path):
        obs = SessionObservabilityPipeline(obs_dir=tmp_path)
        obs.record_created("s-1", operator_id="op-1")
        obs.record_restored("s-1", checkpoint_id="cp-1")
        obs.record_checkpointed("s-1", checkpoint_id="cp-2")
        obs.record_suspended("s-1", reason="pause")
        obs.record_resumed("s-1")
        obs.record_archived("s-1")
        obs.record_terminated("s-1")
        obs.record_expired("s-1")
        obs.record_chronology_updated("s-1")
        assert obs.get_stats()["total_events"] == 9

    def test_event_structure(self, tmp_path):
        obs = SessionObservabilityPipeline(obs_dir=tmp_path)
        ev = obs.record_created("s-1", operator_id="op-1")
        assert ev["event_id"].startswith("ssobs-")
        assert ev["event_type"] == "session_created"
        assert ev["session_id"] == "s-1"

    def test_read_back(self, tmp_path):
        obs = SessionObservabilityPipeline(obs_dir=tmp_path)
        obs.record_created("s-1")
        events = obs.get_events_by_type(SessionEventType.SESSION_CREATED)
        assert len(events) == 1


# =========================================================================
# Replay Validator Tests
# =========================================================================


class TestSessionReplayValidator:

    def test_single_trace(self, tmp_path):
        rv = SessionReplayValidator(proof_dir=tmp_path)
        trace = {
            "checkpoint": {"session_id": "s-1"},
            "chronology": [{"seq": 0}],
            "continuity_state": {"id": "cs-1"},
            "full_state": {"x": 1},
            "cognition": {"mode": "focused"},
            "workflow": {"active": 1},
        }
        proof = rv.validate_trace(trace)
        assert proof["all_passed"]
        assert proof["check_count"] == 6

    def test_all_six_checks(self):
        assert len(DETERMINISM_CHECKS) == 6
        expected = [
            "session_restoration", "chronology_reconstruction",
            "checkpoint_restoration", "continuity_restoration",
            "cognition_restoration", "workflow_restoration",
        ]
        assert DETERMINISM_CHECKS == expected

    def test_proof_persisted(self, tmp_path):
        rv = SessionReplayValidator(proof_dir=tmp_path)
        proof = rv.validate_trace({"checkpoint": {}})
        path = tmp_path / f"session_replay_proof_{proof['proof_id']}.json"
        assert path.exists()

    def test_session_validation(self, tmp_path):
        rv = SessionReplayValidator(proof_dir=tmp_path)
        traces = [
            {"checkpoint": {}, "chronology": [], "continuity_state": {},
             "full_state": {}, "cognition": {}, "workflow": {}},
            {"checkpoint": {"x": 1}, "chronology": [{"a": 1}],
             "continuity_state": {"y": 2}, "full_state": {"z": 3},
             "cognition": {"m": "f"}, "workflow": {"a": 1}},
        ]
        result = rv.validate_session(traces)
        assert result["all_passed"]
        assert result["trace_count"] == 2


# =========================================================================
# Boundary Policies Tests
# =========================================================================


class TestSessionBoundaryPolicies:

    def test_default_limits(self):
        be = SessionBoundaryEnforcer()
        assert be.limits["max_active_sessions_per_operator"] == 3
        assert be.limits["max_checkpoints_per_session"] == 50

    def test_passing_check(self):
        be = SessionBoundaryEnforcer()
        r = be.check_active_sessions("op-1", 1)
        assert r["passed"]

    def test_failing_check(self):
        be = SessionBoundaryEnforcer()
        r = be.check_active_sessions("op-1", 5)
        assert not r["passed"]

    def test_override_capping(self):
        be = SessionBoundaryEnforcer(overrides={"max_active_sessions_per_operator": 100})
        assert be.limits["max_active_sessions_per_operator"] == 3

    def test_override_below_default(self):
        be = SessionBoundaryEnforcer(overrides={"max_active_sessions_per_operator": 1})
        assert be.limits["max_active_sessions_per_operator"] == 1

    def test_forbidden_operations(self):
        be = SessionBoundaryEnforcer()
        for op in FORBIDDEN_SESSION_OPERATIONS:
            r = be.check_no_forbidden_operation(op)
            assert not r["passed"]

    def test_safe_operations(self):
        be = SessionBoundaryEnforcer()
        r = be.check_no_forbidden_operation("normal_session_create")
        assert r["passed"]

    def test_no_duplicate_active(self):
        be = SessionBoundaryEnforcer()
        r = be.check_no_duplicate_active("op-1", ["s-1", "s-2"], "s-1")
        assert not r["passed"]
        r = be.check_no_duplicate_active("op-1", ["s-1", "s-2"], "s-3")
        assert r["passed"]

    def test_bulk_check(self):
        be = SessionBoundaryEnforcer()
        result = be.check_all(
            active_sessions=1,
            checkpoints=5,
            chronology_events=10,
            continuity_depth=2,
            restoration_depth=1,
            concurrent_sessions=3,
        )
        assert result["all_passed"]

    def test_bulk_check_failing(self):
        be = SessionBoundaryEnforcer()
        result = be.check_all(
            active_sessions=100,
            checkpoints=100,
        )
        assert not result["all_passed"]
        assert result["violation_count"] >= 2


# =========================================================================
# Continuity Bridges Tests
# =========================================================================


class TestSessionContinuityBridges:

    def test_ingress_bridge(self, tmp_path):
        b = SessionIngressBridge(state_dir=tmp_path)
        s = b.capture_ingress_state("s-1", active_sources=["discord"], total_signals=3)
        assert s.session_id == "s-1"
        assert s.total_signals == 3
        path = tmp_path / "ingress_bridge_lineage.jsonl"
        assert path.exists()

    def test_cognition_bridge(self, tmp_path):
        b = SessionCognitionBridge(state_dir=tmp_path)
        s = b.capture_cognition_state("s-1", operator_mode="focused", open_loops=2)
        assert s.operator_mode == "focused"
        path = tmp_path / "cognition_bridge_lineage.jsonl"
        assert path.exists()

    def test_workflow_bridge(self, tmp_path):
        b = SessionWorkflowBridge(state_dir=tmp_path)
        s = b.capture_workflow_state("s-1", active_workflows=1, workflow_ids=["wf-1"])
        assert s.active_workflows == 1
        path = tmp_path / "workflow_bridge_lineage.jsonl"
        assert path.exists()

    def test_embodiment_bridge(self, tmp_path):
        b = SessionEmbodimentBridge(state_dir=tmp_path)
        s = b.capture_embodiment_state("s-1", workstation_mode="developer")
        assert s.workstation_mode == "developer"
        path = tmp_path / "embodiment_bridge_lineage.jsonl"
        assert path.exists()

    def test_observability_bridge(self, tmp_path):
        b = SessionObservabilityBridge(state_dir=tmp_path)
        s = b.capture_observability_summary("s-1", total_events=10)
        assert s["total_events"] == 10
        path = tmp_path / "observability_bridge_lineage.jsonl"
        assert path.exists()

    def test_replay_bridge(self, tmp_path):
        b = SessionReplayBridge(state_dir=tmp_path)
        s = b.capture_replay_summary("s-1", total_validations=5, total_passes=5)
        assert s["total_passes"] == 5
        path = tmp_path / "replay_bridge_lineage.jsonl"
        assert path.exists()


# =========================================================================
# Canonical Session Manager Tests
# =========================================================================


class TestCanonicalSessionManager:

    def test_create_session(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session(operator_id="op-1")
        assert s.session_id.startswith("sssess-")
        assert s.lifecycle.state == "active"

    def test_checkpoint_session(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session()
        cp = mgr.checkpoint_session(s.session_id)
        assert cp is not None
        assert cp["checkpoint_id"].startswith("sschkp-")

    def test_suspend_and_resume(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session(operator_id="op-1")
        assert mgr.suspend_session(s.session_id)
        assert s.lifecycle.state == "suspended"
        r = mgr.resume_session(s.session_id)
        assert r is not None
        assert r.lifecycle.state == "active"

    def test_terminate(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session()
        assert mgr.terminate_session(s.session_id)
        assert s.lifecycle.state == "terminated"

    def test_archive(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session()
        assert mgr.archive_session(s.session_id)
        assert s.lifecycle.state == "archived"

    def test_restore_from_checkpoint(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session(operator_id="op-1")
        cp = mgr.checkpoint_session(s.session_id)
        mgr.suspend_session(s.session_id)
        restored = mgr.restore_session(s.session_id)
        assert restored is not None
        assert restored.lifecycle.state == "active"

    def test_update_cognition(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session()
        cog = SessionCognitionState(session_id=s.session_id, operator_mode="focused")
        assert mgr.update_cognition(s.session_id, cog)
        assert s.cognition.operator_mode == "focused"

    def test_update_workflow(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session()
        wf = SessionWorkflowState(session_id=s.session_id, active_workflows=2)
        assert mgr.update_workflow(s.session_id, wf)

    def test_update_embodiment(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session()
        emb = SessionEmbodimentState(session_id=s.session_id, workstation_mode="dev")
        assert mgr.update_embodiment(s.session_id, emb)

    def test_update_ingress(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session()
        ing = SessionIngressState(session_id=s.session_id, total_signals=5)
        assert mgr.update_ingress(s.session_id, ing)

    def test_operator_sessions(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        mgr.create_session(operator_id="op-1")
        mgr.create_session(operator_id="op-1")
        mgr.create_session(operator_id="op-2")
        assert len(mgr.get_operator_sessions("op-1")) == 2
        assert len(mgr.get_operator_sessions("op-2")) == 1

    def test_chronology_tracking(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session(operator_id="op-1")
        chron = mgr.get_session_chronology(s.session_id)
        assert len(chron) >= 1

    def test_receipts_persisted(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session()
        receipts = mgr.get_recent_receipts()
        assert len(receipts) >= 1
        path = tmp_path / "session_receipts.jsonl"
        assert path.exists()

    def test_resume_packet(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session()
        packet = mgr.get_resume_packet(s.session_id)
        assert packet["available"]

    def test_stats(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        mgr.create_session(operator_id="op-1")
        stats = mgr.get_stats()
        assert stats["total_sessions"] == 1
        assert stats["active_sessions"] == 1

    def test_nonexistent_session(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        assert mgr.get_session("nope") is None
        assert not mgr.terminate_session("nope")
        assert not mgr.suspend_session("nope")
        assert mgr.resume_session("nope") is None


# =========================================================================
# Constraint Tests
# =========================================================================


class TestCanonicalSessionManagerEnforcement:
    """Session manager cannot execute workflows."""

    def test_no_execute_method(self):
        assert not hasattr(CanonicalSubstrateSessionManager, "execute")
        assert not hasattr(CanonicalSubstrateSessionManager, "execute_workflow")
        assert not hasattr(CanonicalSubstrateSessionManager, "dispatch")
        assert not hasattr(CanonicalSubstrateSessionManager, "run")

    def test_no_process_method(self):
        assert not hasattr(CanonicalSubstrateSessionManager, "process")
        assert not hasattr(CanonicalSubstrateSessionManager, "process_command")


class TestCheckpointRestorationDeterminism:
    """Same checkpoint -> same restored state."""

    def test_same_continuity_same_hash(self):
        cog = SessionCognitionState(session_id="s-1", operator_mode="focused")
        wf = SessionWorkflowState(session_id="s-1", active_workflows=2)
        cs1 = SessionContinuityState(session_id="s-1", cognition=cog, workflow=wf)
        cs2 = SessionContinuityState(session_id="s-1", cognition=cog, workflow=wf)
        assert cs1.content_hash == cs2.content_hash

    def test_checkpoint_hash_deterministic(self, tmp_path):
        cpe = SessionCheckpointEngine(state_dir=tmp_path)
        cont = SessionContinuityState(session_id="s-1")
        cp = cpe.create_checkpoint("s-1", cont)
        assert cpe.verify_checkpoint_hash(cp)


class TestChronologyReconstructionDeterminism:
    """Same events -> same timeline."""

    def test_sequence_monotonic(self, tmp_path):
        ce = SessionChronologyEngine(state_dir=tmp_path)
        events = []
        for i in range(5):
            events.append(ce.record_runtime_traversal("s-1", command=f"cmd-{i}"))
        for i, ev in enumerate(events):
            assert ev.sequence_number == i

    def test_snapshot_order(self, tmp_path):
        ce = SessionChronologyEngine(state_dir=tmp_path)
        ce.record_session_creation("s-1")
        ce.record_runtime_traversal("s-1")
        ce.record_cognition_transition("s-1")
        snap = ce.get_chronology_snapshot("s-1")
        for i, ev in enumerate(snap):
            assert ev["sequence_number"] == i


class TestContinuityRestorationConsistency:
    """Same state -> same continuity hash."""

    def test_hash_stable(self, tmp_path):
        ce = SessionContinuityEngine(state_dir=tmp_path)
        cog = SessionCognitionState(session_id="s-1", operator_mode="focused")
        s1 = ce.capture("s-1", cognition=cog)
        ce2 = SessionContinuityEngine(state_dir=tmp_path)
        s2 = ce2.restore("s-1", s1)
        assert s1.content_hash == s2.content_hash


class TestCognitionRestorationConsistency:

    def test_cognition_round_trip(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session()
        cog = SessionCognitionState(session_id=s.session_id, operator_mode="focused", open_loops=3)
        mgr.update_cognition(s.session_id, cog)
        state = mgr.get_continuity_state(s.session_id)
        assert state.cognition.operator_mode == "focused"
        assert state.cognition.open_loops == 3


class TestWorkflowRestorationConsistency:

    def test_workflow_round_trip(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session()
        wf = SessionWorkflowState(session_id=s.session_id, active_workflows=2, workflow_ids=["wf-1"])
        mgr.update_workflow(s.session_id, wf)
        state = mgr.get_continuity_state(s.session_id)
        assert state.workflow.active_workflows == 2


class TestEmbodimentRestorationConsistency:

    def test_embodiment_round_trip(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session()
        emb = SessionEmbodimentState(session_id=s.session_id, workstation_mode="developer")
        mgr.update_embodiment(s.session_id, emb)
        state = mgr.get_continuity_state(s.session_id)
        assert state.embodiment.workstation_mode == "developer"


class TestIngressRestorationConsistency:

    def test_ingress_round_trip(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session()
        ing = SessionIngressState(session_id=s.session_id, active_sources=["discord"], total_signals=5)
        mgr.update_ingress(s.session_id, ing)
        state = mgr.get_continuity_state(s.session_id)
        assert state.ingress.total_signals == 5


class TestSessionReplayDeterminism:

    def test_all_six_checks_pass(self, tmp_path):
        rv = SessionReplayValidator(proof_dir=tmp_path)
        trace = {
            "checkpoint": {"session_id": "s-1", "state": "active"},
            "chronology": [{"seq": 0, "kind": "creation"}],
            "continuity_state": {"id": "cs-1"},
            "full_state": {"lifecycle": "active", "cognition": "focused"},
            "cognition": {"mode": "focused", "loops": 2},
            "workflow": {"active": 1, "completed": 0},
        }
        proof = rv.validate_trace(trace)
        assert proof["all_passed"]
        assert proof["check_count"] == 6


class TestLineageCompleteness:

    def test_receipts_on_every_operation(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session()
        mgr.checkpoint_session(s.session_id)
        mgr.suspend_session(s.session_id)
        mgr.resume_session(s.session_id)
        mgr.archive_session(s.session_id)
        mgr.terminate_session(s.session_id)
        receipts = mgr.get_recent_receipts(limit=20)
        assert len(receipts) >= 6
        operations = [r["operation"] for r in receipts]
        assert "create" in operations
        assert "checkpoint" in operations
        assert "suspend" in operations
        assert "resume" in operations
        assert "archive" in operations
        assert "terminate" in operations


class TestNoHiddenSessionMutation:

    def test_receipts_persisted(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        mgr.create_session()
        path = tmp_path / "session_receipts.jsonl"
        assert path.exists()

    def test_lifecycle_persisted(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        mgr.create_session()
        path = tmp_path / "session_lifecycle_lineage.jsonl"
        assert path.exists()

    def test_chronology_persisted(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        mgr.create_session()
        path = tmp_path / "session_chronology.jsonl"
        assert path.exists()

    def test_continuity_persisted(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        mgr.create_session()
        path = tmp_path / "session_continuity.jsonl"
        assert path.exists()


class TestNoOrphanedContinuity:

    def test_continuity_exists_for_all_sessions(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s1 = mgr.create_session()
        s2 = mgr.create_session()
        assert mgr.get_continuity_state(s1.session_id) is not None
        assert mgr.get_continuity_state(s2.session_id) is not None

    def test_continuity_chain(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s1 = mgr.create_session()
        s2 = mgr.create_session(previous_session_id=s1.session_id)
        state = mgr.get_continuity_state(s2.session_id)
        assert s1.session_id in state.continuity_chain


class TestNoDuplicateActiveSessions:

    def test_boundary_rejects_duplicate(self):
        be = SessionBoundaryEnforcer()
        r = be.check_no_duplicate_active("op-1", ["s-1", "s-2"], "s-1")
        assert not r["passed"]

    def test_boundary_accepts_new(self):
        be = SessionBoundaryEnforcer()
        r = be.check_no_duplicate_active("op-1", ["s-1"], "s-2")
        assert r["passed"]


class TestNoRecursiveRestoration:

    def test_boundary_limits_restoration_depth(self):
        be = SessionBoundaryEnforcer()
        r = be.check_restoration_depth(10)
        assert not r["passed"]
        r = be.check_restoration_depth(1)
        assert r["passed"]


class TestNoInterfaceOwnedSessionState:

    def test_forbidden_interface_ownership(self):
        be = SessionBoundaryEnforcer()
        r = be.check_no_forbidden_operation("interface_owned_session")
        assert not r["passed"]

    def test_forbidden_cognition_execution(self):
        be = SessionBoundaryEnforcer()
        r = be.check_no_forbidden_operation("cognition_owned_execution")
        assert not r["passed"]

    def test_forbidden_workflow_persistence(self):
        be = SessionBoundaryEnforcer()
        r = be.check_no_forbidden_operation("workflow_owned_persistence")
        assert not r["passed"]

    def test_forbidden_parallel_manager(self):
        be = SessionBoundaryEnforcer()
        r = be.check_no_forbidden_operation("parallel_session_manager")
        assert not r["passed"]


# =========================================================================
# Integration Tests
# =========================================================================


class TestIntegration:

    def test_full_session_lifecycle(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session(operator_id="op-1")

        cog = SessionCognitionState(session_id=s.session_id, operator_mode="focused")
        mgr.update_cognition(s.session_id, cog)

        wf = SessionWorkflowState(session_id=s.session_id, active_workflows=1)
        mgr.update_workflow(s.session_id, wf)

        cp = mgr.checkpoint_session(s.session_id)
        assert cp is not None

        mgr.suspend_session(s.session_id)
        restored = mgr.restore_session(s.session_id)
        assert restored.lifecycle.state == "active"

        mgr.archive_session(s.session_id)
        mgr.terminate_session(s.session_id)

        receipts = mgr.get_recent_receipts(limit=20)
        assert len(receipts) >= 6

    def test_multi_session_operator(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s1 = mgr.create_session(operator_id="op-1")
        s2 = mgr.create_session(operator_id="op-1", previous_session_id=s1.session_id)
        assert len(mgr.get_operator_sessions("op-1")) == 2
        assert len(mgr.get_active_sessions()) == 2

    def test_checkpoint_restore_cycle(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session()

        cog = SessionCognitionState(session_id=s.session_id, operator_mode="planning")
        mgr.update_cognition(s.session_id, cog)

        cp = mgr.checkpoint_session(s.session_id)
        cp_id = cp["checkpoint_id"]

        mgr.suspend_session(s.session_id)
        restored = mgr.restore_session(s.session_id, checkpoint_id=cp_id)
        assert restored is not None
        assert restored.lifecycle.state == "active"

    def test_replay_determinism_end_to_end(self, tmp_path):
        mgr = CanonicalSubstrateSessionManager(state_dir=tmp_path)
        s = mgr.create_session(operator_id="op-1")

        cog = SessionCognitionState(session_id=s.session_id, operator_mode="focused")
        mgr.update_cognition(s.session_id, cog)

        state = mgr.get_continuity_state(s.session_id)
        chron = mgr.get_session_chronology(s.session_id)

        rv = SessionReplayValidator(proof_dir=tmp_path)
        trace = {
            "checkpoint": {"session_id": s.session_id},
            "chronology": chron,
            "continuity_state": state.to_dict(),
            "full_state": s.to_dict(),
            "cognition": cog.to_dict(),
            "workflow": {},
        }
        proof = rv.validate_trace(trace)
        assert proof["all_passed"]
        assert proof["check_count"] == 6

    def test_boundary_enforcement_integration(self, tmp_path):
        be = SessionBoundaryEnforcer()
        result = be.check_all(
            active_sessions=1,
            checkpoints=2,
            chronology_events=5,
            continuity_depth=1,
            restoration_depth=0,
            concurrent_sessions=2,
        )
        assert result["all_passed"]

        for op in FORBIDDEN_SESSION_OPERATIONS:
            r = be.check_no_forbidden_operation(op)
            assert not r["passed"]

    def test_observability_integration(self, tmp_path):
        obs = SessionObservabilityPipeline(obs_dir=tmp_path)
        for et in SessionEventType:
            obs.record_event(et, "s-1")

        stats = obs.get_stats()
        assert stats["total_events"] == 9
        for et in SessionEventType:
            assert stats["event_counts"][et.value] == 1

    def test_bridges_integration(self, tmp_path):
        ib = SessionIngressBridge(state_dir=tmp_path)
        cb = SessionCognitionBridge(state_dir=tmp_path)
        wb = SessionWorkflowBridge(state_dir=tmp_path)
        eb = SessionEmbodimentBridge(state_dir=tmp_path)

        ib.capture_ingress_state("s-1", active_sources=["discord"])
        cb.capture_cognition_state("s-1", operator_mode="focused")
        wb.capture_workflow_state("s-1", active_workflows=1)
        eb.capture_embodiment_state("s-1", workstation_mode="developer")

        lineage_files = [f for f in os.listdir(tmp_path) if f.endswith("_lineage.jsonl")]
        assert len(lineage_files) == 4
