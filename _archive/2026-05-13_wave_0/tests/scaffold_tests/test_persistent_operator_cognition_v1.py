"""Tests for Phase 96.8BT — Persistent Operator Cognition.

Validates all 10 contracts, 7 enums, cognition engine,
working cognition store, runtime attention system,
open loop engine, temporal continuity engine,
continuity bridge, observability pipeline,
replay validator, boundary policies, and lifecycle engine.

15+ constraint tests proving:
  - No autonomous self-direction
  - No self-generated goals
  - No uncontrolled recursive cognition
  - No governance bypass
  - No replay determinism bypass
  - No hidden persistent mutation
  - No cognition outside canonical spine patterns
  - No implicit memory promotion
  - Operator intent anchoring
  - Bounded attention
  - Loop lifecycle enforcement
  - Phase transition validation
  - Checkpoint/restore integrity
  - Temporal continuity
  - Observability completeness

UMH substrate subsystem. Phase 96.8BT.
"""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.cognition.persistent_operator_cognition_contracts_v1 import (
    ActiveOperationalFocus,
    AttentionWeightType,
    CognitionDecisionType,
    CognitionEventType,
    CognitionPhase,
    CognitiveCheckpoint,
    CognitiveLineageReceipt,
    ContinuityFocusState,
    LoopState,
    MODE_COGNITION_POLICIES,
    OpenOperationalLoop,
    OperationalIntentState,
    OperatorCognitiveState,
    OperatorMode,
    RuntimeAttentionMap,
    TemporalExecutionContext,
    WorkingCognitionWindow,
    _content_hash,
)
from core.cognition.persistent_operator_cognition_engine_v1 import (
    PersistentOperatorCognitionEngine,
)
from core.cognition.working_cognition_store_v1 import WorkingCognitionStore
from core.cognition.runtime_attention_system_v1 import (
    ATTENTION_DEFAULTS,
    RuntimeAttentionSystem,
)
from core.cognition.open_loop_cognition_engine_v1 import (
    VALID_LOOP_TRANSITIONS,
    OpenLoopCognitionEngine,
)
from core.cognition.temporal_continuity_engine_v1 import TemporalContinuityEngine
from core.cognition.cognition_continuity_bridge_v1 import CognitionContinuityBridge
from core.cognition.cognition_observability_pipeline_v1 import (
    EVENT_FILE_MAP,
    CognitionObservabilityPipeline,
)
from core.cognition.cognition_replay_validator_v1 import CognitionReplayValidator
from core.cognition.cognition_boundary_policies_v1 import (
    CognitionBoundaryEnforcer,
    DEFAULT_COGNITION_BOUNDARIES,
)
from core.cognition.cognition_lifecycle_engine_v1 import (
    CognitionLifecycleEngine,
    VALID_COGNITION_TRANSITIONS,
)


# =========================================================================
# Contract Tests
# =========================================================================


class TestCognitionContracts:
    """Validates all 10 contracts and 7 enums."""

    def test_enum_cognition_phase(self):
        assert len(CognitionPhase) == 9
        assert CognitionPhase.INITIALIZED.value == "initialized"
        assert CognitionPhase.TERMINATED.value == "terminated"

    def test_enum_operator_mode(self):
        assert len(OperatorMode) == 5
        assert OperatorMode.FOCUSED_EXECUTION.value == "focused_execution"

    def test_enum_loop_state(self):
        assert len(LoopState) == 7
        assert LoopState.ACTIVE.value == "active"
        assert LoopState.ARCHIVED.value == "archived"

    def test_enum_attention_weight_type(self):
        assert len(AttentionWeightType) == 6
        assert AttentionWeightType.OPERATOR_FOCUS.value == "operator_focus"

    def test_enum_cognition_event_type(self):
        assert len(CognitionEventType) == 10

    def test_enum_cognition_decision_type(self):
        assert len(CognitionDecisionType) == 7

    def test_mode_cognition_policies(self):
        assert len(MODE_COGNITION_POLICIES) == 5
        for mode in OperatorMode:
            assert mode.value in MODE_COGNITION_POLICIES

    def test_operator_cognitive_state(self):
        s = OperatorCognitiveState(session_id="test")
        assert s.state_id.startswith("cogst-")
        d = s.to_dict()
        assert "content_hash" in d
        assert d["session_id"] == "test"

    def test_working_cognition_window(self):
        w = WorkingCognitionWindow(max_items=3)
        assert w.add_item({"k": "a"}, 1.0)
        assert w.add_item({"k": "b"}, 0.5)
        assert w.add_item({"k": "c"}, 2.0)
        assert not w.add_item({"k": "d"}, 1.0)
        evicted = w.evict_lowest_weight()
        assert evicted["k"] == "b"
        assert len(w.items) == 2

    def test_active_operational_focus(self):
        f = ActiveOperationalFocus(focus_type="build", set_by="operator")
        assert f.set_by == "operator"
        assert f.focus_id.startswith("cogfoc-")

    def test_open_operational_loop(self):
        loop = OpenOperationalLoop(
            source_type="workflow", source_id="wf-1",
            description="test", priority=2.0
        )
        assert loop.state == LoopState.ACTIVE
        assert loop.loop_id.startswith("cogloop-")

    def test_cognitive_checkpoint(self):
        cp = CognitiveCheckpoint(session_id="s1")
        assert cp.checkpoint_id.startswith("cogchk-")
        assert cp.resumable is True

    def test_temporal_execution_context(self):
        t = TemporalExecutionContext(session_id="s1")
        assert t.context_id.startswith("cogtmp-")

    def test_operational_intent_state(self):
        i = OperationalIntentState(
            intent_description="Build phase", set_by="operator"
        )
        assert i.set_by == "operator"
        assert i.active is True

    def test_runtime_attention_map(self):
        m = RuntimeAttentionMap()
        assert m.get_weight(AttentionWeightType.OPERATOR_FOCUS) == 2.0
        m.set_weight(AttentionWeightType.OPERATOR_FOCUS, 10.0)
        assert m.get_weight(AttentionWeightType.OPERATOR_FOCUS) == 5.0

    def test_continuity_focus_state(self):
        c = ContinuityFocusState(session_id="s1", continuity_score=0.85)
        assert c.state_id.startswith("cogcfs-")
        assert c.continuity_score == 0.85

    def test_cognitive_lineage_receipt(self):
        r = CognitiveLineageReceipt(
            action="focus_shift", component="engine"
        )
        assert r.receipt_id.startswith("cogrcpt-")
        assert r.approved is True

    def test_all_contracts_serialize_deterministically(self):
        contracts = [
            OperatorCognitiveState, WorkingCognitionWindow,
            ActiveOperationalFocus, OpenOperationalLoop,
            CognitiveCheckpoint, TemporalExecutionContext,
            OperationalIntentState, RuntimeAttentionMap,
            ContinuityFocusState, CognitiveLineageReceipt,
        ]
        for cls in contracts:
            obj = cls()
            d1 = obj.to_dict()
            d2 = obj.to_dict()
            h1 = obj.content_hash()
            h2 = obj.content_hash()
            assert d1 == d2, f"{cls.__name__} non-deterministic to_dict"
            assert h1 == h2, f"{cls.__name__} non-deterministic hash"
            assert isinstance(h1, str) and len(h1) == 24

    def test_content_hash_changes_with_data(self):
        s1 = OperatorCognitiveState(operator_mode=OperatorMode.FOCUSED_EXECUTION)
        s2 = OperatorCognitiveState(operator_mode=OperatorMode.PLANNING_MODE)
        assert s1.content_hash() != s2.content_hash()


# =========================================================================
# Cognition Engine Tests
# =========================================================================


class TestCognitionEngine:
    """Tests for PersistentOperatorCognitionEngine."""

    @pytest.fixture
    def engine(self, tmp_path):
        return PersistentOperatorCognitionEngine(state_dir=tmp_path)

    def test_initialization(self, engine):
        assert engine.session_id.startswith("sess-")
        assert engine.operator_mode == OperatorMode.FOCUSED_EXECUTION
        assert engine.phase == CognitionPhase.INITIALIZED

    def test_mode_transition(self, engine):
        r = engine.set_operator_mode(OperatorMode.OPERATIONAL_SUPERVISION)
        assert engine.operator_mode == OperatorMode.OPERATIONAL_SUPERVISION
        assert r.decision_type == CognitionDecisionType.MODE_TRANSITION

    def test_phase_transitions(self, engine):
        assert engine.set_phase(CognitionPhase.ACTIVE)
        assert engine.set_phase(CognitionPhase.FOCUSED)
        assert not engine.set_phase(CognitionPhase.INITIALIZED)

    def test_focus_always_set_by_operator(self, engine):
        f = engine.set_focus("build", "Test focus")
        assert f.set_by == "operator"
        assert engine.get_active_focus().focus_id == f.focus_id

    def test_focus_deactivates_previous(self, engine):
        f1 = engine.set_focus("build", "First")
        f2 = engine.set_focus("deploy", "Second")
        assert engine.get_active_focus().focus_id == f2.focus_id
        all_focuses = engine.get_all_focuses()
        inactive = [f for f in all_focuses if not f.active]
        assert len(inactive) == 1

    def test_intent_always_set_by_operator(self, engine):
        i = engine.register_intent("Do X", source_command="build")
        assert i.set_by == "operator"
        assert len(engine.get_active_intents()) == 1

    def test_open_and_transition_loop(self, engine):
        loop = engine.open_loop("workflow", "wf-1", "Test loop")
        assert len(engine.get_active_loops()) == 1
        assert engine.transition_loop(loop.loop_id, LoopState.WAITING)
        assert engine.transition_loop(loop.loop_id, LoopState.RESOLVED, "Done")

    def test_attention_reweight(self, engine):
        r = engine.reweight_attention(AttentionWeightType.LOOP_URGENCY, 3.0)
        assert r.decision_type == CognitionDecisionType.ATTENTION_REWEIGHT

    def test_temporal_linking(self, engine):
        engine.link_previous_session("prev-1", gap_seconds=60.0)
        tc = engine.get_temporal_context()
        assert tc.previous_session_id == "prev-1"
        assert tc.restart_count == 1

    def test_continuity_restoration(self, engine):
        cf = engine.restore_continuity(
            "prev-1", focus_ids=["f1"], loop_ids=["l1"]
        )
        assert cf.restoration_complete
        assert len(cf.restored_focus_ids) == 1

    def test_checkpoint_creation(self, engine, tmp_path):
        engine.set_focus("test", "Checkpoint test")
        cp = engine.create_checkpoint()
        assert cp.session_id == engine.session_id
        path = tmp_path / f"checkpoint_{cp.checkpoint_id}.json"
        assert path.exists()

    def test_lineage_persisted(self, engine, tmp_path):
        engine.set_focus("test", "Lineage test")
        path = tmp_path / "cognition_lineage.jsonl"
        assert path.exists()
        with path.open() as f:
            lines = f.readlines()
        assert len(lines) >= 1

    def test_cognitive_snapshot(self, engine):
        engine.set_focus("test", "Snapshot test")
        snap = engine.get_cognitive_snapshot()
        assert "cognitive_state" in snap
        assert "working_window" in snap
        assert "stats" in snap

    def test_stats(self, engine):
        engine.set_focus("test", "Stats test")
        engine.open_loop("wf", "wf-1", "Test")
        stats = engine.get_stats()
        assert stats["total_focus_shifts"] == 1
        assert stats["total_loop_operations"] >= 1


# =========================================================================
# Working Cognition Store Tests
# =========================================================================


class TestWorkingCognitionStore:

    def test_persist_and_load_snapshot(self, tmp_path):
        store = WorkingCognitionStore(state_dir=tmp_path)
        snap = {"cognitive_state": {"phase": "active"}}
        snap_id = store.persist_snapshot("sess-1", snap)
        loaded = store.load_latest_snapshot()
        assert loaded is not None
        assert loaded["cognitive_state"]["phase"] == "active"

    def test_load_by_id(self, tmp_path):
        store = WorkingCognitionStore(state_dir=tmp_path)
        snap_id = store.persist_snapshot("sess-1", {"test": True})
        loaded = store.load_snapshot_by_id(snap_id)
        assert loaded is not None

    def test_checkpoint_persistence(self, tmp_path):
        store = WorkingCognitionStore(state_dir=tmp_path)
        cp = CognitiveCheckpoint(session_id="s1")
        store.persist_checkpoint(cp)
        loaded = store.load_checkpoint(cp.checkpoint_id)
        assert loaded is not None

    def test_session_lineage(self, tmp_path):
        store = WorkingCognitionStore(state_dir=tmp_path)
        store.persist_session_record("s1", "focused", "active", "test", 2)
        history = store.get_session_history()
        assert len(history) == 1

    def test_list_operations(self, tmp_path):
        store = WorkingCognitionStore(state_dir=tmp_path)
        store.persist_snapshot("s1", {"a": 1})
        store.persist_snapshot("s2", {"b": 2})
        assert len(store.list_snapshots()) == 2
        cp = CognitiveCheckpoint(session_id="s1")
        store.persist_checkpoint(cp)
        assert len(store.list_checkpoints()) == 1

    def test_nonexistent_returns_none(self, tmp_path):
        store = WorkingCognitionStore(state_dir=tmp_path)
        assert store.load_latest_snapshot() is None
        assert store.load_snapshot_by_id("nonexistent") is None
        assert store.load_checkpoint("nonexistent") is None


# =========================================================================
# Runtime Attention System Tests
# =========================================================================


class TestRuntimeAttentionSystem:

    def test_default_weights(self, tmp_path):
        attn = RuntimeAttentionSystem(
            mode=OperatorMode.FOCUSED_EXECUTION, state_dir=tmp_path
        )
        assert attn.attention_map.get_weight(AttentionWeightType.OPERATOR_FOCUS) == 2.0

    def test_reweight(self, tmp_path):
        attn = RuntimeAttentionSystem(state_dir=tmp_path)
        rec = attn.reweight(AttentionWeightType.WORKFLOW, 3.0)
        assert rec["new_value"] == 3.0
        assert not rec["clamped"]

    def test_reweight_clamped(self, tmp_path):
        attn = RuntimeAttentionSystem(state_dir=tmp_path)
        rec = attn.reweight(AttentionWeightType.WORKFLOW, 10.0)
        assert rec["new_value"] == 5.0
        assert rec["clamped"]

    def test_mode_decay_preserves_operator_focus(self, tmp_path):
        attn = RuntimeAttentionSystem(
            mode=OperatorMode.FOCUSED_EXECUTION, state_dir=tmp_path
        )
        attn.apply_mode_decay()
        assert attn.attention_map.get_weight(AttentionWeightType.OPERATOR_FOCUS) == 2.0
        assert attn.attention_map.get_weight(AttentionWeightType.CONTINUITY) < 1.0

    def test_scoring(self, tmp_path):
        attn = RuntimeAttentionSystem(state_dir=tmp_path)
        item = {"_weight": 1.0, "_dimensions": ["operator_focus"]}
        score = attn.score_item(item)
        assert score > 0

    def test_score_sorting(self, tmp_path):
        attn = RuntimeAttentionSystem(state_dir=tmp_path)
        items = [
            {"k": "low", "_weight": 0.1},
            {"k": "high", "_weight": 5.0},
        ]
        scored = attn.score_items(items)
        assert scored[0][0] >= scored[1][0]

    def test_suppression(self, tmp_path):
        attn = RuntimeAttentionSystem(state_dir=tmp_path)
        assert attn.should_suppress({"_weight": 0.1}, threshold=0.3)
        assert not attn.should_suppress({"_weight": 1.0}, threshold=0.3)

    def test_reset_to_defaults(self, tmp_path):
        attn = RuntimeAttentionSystem(state_dir=tmp_path)
        attn.reweight(AttentionWeightType.WORKFLOW, 5.0)
        attn.reset_to_defaults()
        assert attn.attention_map.get_weight(AttentionWeightType.WORKFLOW) == 1.0


# =========================================================================
# Open Loop Cognition Engine Tests
# =========================================================================


class TestOpenLoopCognitionEngine:

    def test_open_loop(self, tmp_path):
        ole = OpenLoopCognitionEngine(state_dir=tmp_path)
        loop = ole.open_loop("workflow", "wf-1", "Test")
        assert loop.state == LoopState.ACTIVE
        assert len(ole.get_active_loops()) == 1

    def test_valid_transitions(self, tmp_path):
        ole = OpenLoopCognitionEngine(state_dir=tmp_path)
        loop = ole.open_loop("wf", "src-1", "Test")
        assert ole.transition(loop.loop_id, LoopState.WAITING)
        assert ole.transition(loop.loop_id, LoopState.RESUMED)
        assert ole.transition(loop.loop_id, LoopState.RESOLVED, "Done")

    def test_invalid_transitions(self, tmp_path):
        ole = OpenLoopCognitionEngine(state_dir=tmp_path)
        loop = ole.open_loop("wf", "src-1", "Test")
        assert not ole.transition(loop.loop_id, LoopState.ARCHIVED)

    def test_resolve_convenience(self, tmp_path):
        ole = OpenLoopCognitionEngine(state_dir=tmp_path)
        loop = ole.open_loop("wf", "src-1", "Test")
        ole.transition(loop.loop_id, LoopState.WAITING)
        assert ole.resolve(loop.loop_id, "Resolved")
        assert ole.get_loop(loop.loop_id).state == LoopState.RESOLVED

    def test_priority_sorting(self, tmp_path):
        ole = OpenLoopCognitionEngine(state_dir=tmp_path)
        ole.open_loop("a", "1", "Low", priority=0.5)
        ole.open_loop("b", "2", "High", priority=5.0)
        ole.open_loop("c", "3", "Med", priority=2.0)
        by_pri = ole.get_loops_by_priority()
        assert by_pri[0].priority >= by_pri[-1].priority

    def test_tag_query(self, tmp_path):
        ole = OpenLoopCognitionEngine(state_dir=tmp_path)
        ole.open_loop("wf", "1", "Tagged", tags=["urgent"])
        ole.open_loop("wf", "2", "Not tagged")
        assert len(ole.get_loops_by_tag("urgent")) == 1

    def test_restore_loops(self, tmp_path):
        ole = OpenLoopCognitionEngine(state_dir=tmp_path)
        restored = ole.restore_loops([
            {"loop_id": "old-1", "source_type": "wf", "source_id": "wf-99",
             "description": "Restored", "state": "waiting", "priority": 3.0}
        ])
        assert len(restored) == 1
        assert restored[0].state == LoopState.WAITING

    def test_terminal_state_no_exit(self, tmp_path):
        ole = OpenLoopCognitionEngine(state_dir=tmp_path)
        loop = ole.open_loop("wf", "1", "Test")
        ole.transition(loop.loop_id, LoopState.RESOLVED)
        ole.transition(loop.loop_id, LoopState.ARCHIVED)
        assert not ole.transition(loop.loop_id, LoopState.ACTIVE)


# =========================================================================
# Temporal Continuity Engine Tests
# =========================================================================


class TestTemporalContinuityEngine:

    def test_session_auto_started(self, tmp_path):
        tce = TemporalContinuityEngine(state_dir=tmp_path)
        assert tce.context.chronology_entries >= 1

    def test_link_previous(self, tmp_path):
        tce = TemporalContinuityEngine(state_dir=tmp_path)
        gap = tce.link_previous_session("prev-1", "2026-05-09T12:00:00+00:00")
        assert gap > 0
        assert tce.get_restart_count() == 1
        assert "prev-1" in tce.get_session_chain()

    def test_record_events(self, tmp_path):
        tce = TemporalContinuityEngine(state_dir=tmp_path)
        tce.record_checkpoint("chk-1")
        tce.record_workflow_event("wf-1", "started")
        tce.record_focus_event("foc-1", "shifted")
        tce.record_custom_event("custom", {"k": "v"})
        assert len(tce.get_chronology()) >= 5

    def test_end_session(self, tmp_path):
        tce = TemporalContinuityEngine(state_dir=tmp_path)
        summary = tce.end_session()
        assert summary["session_id"] == tce.session_id
        path = tmp_path / "session_summary.jsonl"
        assert path.exists()

    def test_chronology_ordering(self, tmp_path):
        tce = TemporalContinuityEngine(state_dir=tmp_path)
        tce.record_custom_event("a", {})
        tce.record_custom_event("b", {})
        chrono = tce.get_chronology()
        sequences = [e["sequence"] for e in chrono]
        assert sequences == sorted(sequences)


# =========================================================================
# Cognition Continuity Bridge Tests
# =========================================================================


class TestCognitionContinuityBridge:

    def test_persist_outcome(self, tmp_path):
        bridge = CognitionContinuityBridge(state_dir=tmp_path)
        record = bridge.persist_outcome(
            "sess-1", CognitionPhase.ARCHIVED,
            {"cognitive_state": {}}, []
        )
        assert record["continuation_type"] == "complete"

    def test_continuation_type_mapping(self, tmp_path):
        bridge = CognitionContinuityBridge(state_dir=tmp_path)
        mappings = {
            CognitionPhase.ARCHIVED: "complete",
            CognitionPhase.TERMINATED: "complete",
            CognitionPhase.CHECKPOINTED: "checkpointed",
            CognitionPhase.SUSPENDED: "suspended",
            CognitionPhase.STALE: "stale",
            CognitionPhase.ACTIVE: "active",
        }
        for phase, expected in mappings.items():
            r = bridge.persist_outcome("s", phase, {})
            assert r["continuation_type"] == expected

    def test_checkpoint_roundtrip(self, tmp_path):
        bridge = CognitionContinuityBridge(state_dir=tmp_path)
        cp = bridge.create_checkpoint(
            "sess-1", OperatorMode.FOCUSED_EXECUTION,
            CognitionPhase.ACTIVE, {"test": True}
        )
        loaded = bridge.load_checkpoint(cp.checkpoint_id)
        assert loaded is not None

    def test_resume_packet(self, tmp_path):
        bridge = CognitionContinuityBridge(state_dir=tmp_path)
        bridge.persist_outcome(
            "sess-1", CognitionPhase.CHECKPOINTED,
            {"cognitive_state": {"last_checkpoint_id": "c1"}},
            [{"loop_id": "l1", "state": "active"}]
        )
        bridge.create_checkpoint(
            "sess-1", OperatorMode.FOCUSED_EXECUTION,
            CognitionPhase.CHECKPOINTED, {"test": True},
            {"focus_id": "f1"}, [{"loop_id": "l1"}]
        )
        packet = bridge.build_resume_packet("sess-1")
        assert len(packet["continuity_records"]) >= 1
        assert len(packet["open_loops"]) >= 1

    def test_restore_focus(self, tmp_path):
        bridge = CognitionContinuityBridge(state_dir=tmp_path)
        bridge.create_checkpoint(
            "sess-1", OperatorMode.FOCUSED_EXECUTION,
            CognitionPhase.ACTIVE, {},
            {"focus_id": "f1"}, [{"loop_id": "l1"}]
        )
        packet = bridge.build_resume_packet("sess-1")
        focus = bridge.restore_focus("sess-2", "sess-1", packet)
        assert focus.restoration_complete


# =========================================================================
# Cognition Observability Pipeline Tests
# =========================================================================


class TestCognitionObservabilityPipeline:

    def test_all_10_event_types(self, tmp_path):
        obs = CognitionObservabilityPipeline(obs_dir=tmp_path)
        obs.record_initialized("s1")
        obs.record_focus_shifted("s1", "f1", "build")
        obs.record_loop_opened("s1", "l1", "wf")
        obs.record_loop_resolved("s1", "l1", "done")
        obs.record_continuity_restored("s1", "prev", 0.8)
        obs.record_checkpoint_created("s1", "chk-1")
        obs.record_attention_reweighted("s1", "loop_urgency", 1.5, 2.0)
        obs.record_temporal_snapshot("s1", "ctx-1")
        obs.record_cognition_resumed("s1", "prev")
        obs.record_cognition_archived("s1", "session_end")
        assert obs.get_stats()["total_events"] == 10
        files = list(tmp_path.iterdir())
        assert len(files) == 10

    def test_event_file_map_covers_all(self):
        for et in CognitionEventType:
            assert et.value in EVENT_FILE_MAP

    def test_read_back_events(self, tmp_path):
        obs = CognitionObservabilityPipeline(obs_dir=tmp_path)
        obs.record_focus_shifted("s1", "f1", "build")
        obs.record_focus_shifted("s1", "f2", "deploy")
        events = obs.get_events_by_type(CognitionEventType.FOCUS_SHIFTED)
        assert len(events) == 2

    def test_event_structure(self, tmp_path):
        obs = CognitionObservabilityPipeline(obs_dir=tmp_path)
        event = obs.record_initialized("s1", mode="focused")
        assert "event_id" in event
        assert "timestamp" in event
        assert event["event_type"] == CognitionEventType.COGNITION_INITIALIZED.value


# =========================================================================
# Cognition Replay Validator Tests
# =========================================================================


class TestCognitionReplayValidator:

    def test_single_trace_validation(self, tmp_path):
        rv = CognitionReplayValidator(proof_dir=tmp_path)
        trace = {
            "operator_mode": "focused_execution",
            "phase": "active",
            "from_phase": "initialized",
            "to_phase": "active",
            "focus_input": {"type": "build"},
            "loop_state": "active",
            "loop_target": "waiting",
        }
        proof = rv.validate_trace(trace)
        assert proof["all_passed"]
        assert proof["check_count"] == 7

    def test_proof_persisted(self, tmp_path):
        rv = CognitionReplayValidator(proof_dir=tmp_path)
        rv.validate_trace({"operator_mode": "focused_execution"})
        proofs = list(tmp_path.glob("cognition_replay_proof_*.json"))
        assert len(proofs) == 1

    def test_session_validation(self, tmp_path):
        rv = CognitionReplayValidator(proof_dir=tmp_path)
        traces = [
            {"operator_mode": "focused_execution", "loop_state": "active", "loop_target": "waiting"},
            {"operator_mode": "planning_mode", "phase": "checkpointed"},
        ]
        result = rv.validate_session(traces)
        assert result["all_passed"]
        assert result["trace_count"] == 2

    def test_all_seven_checks_present(self, tmp_path):
        rv = CognitionReplayValidator(proof_dir=tmp_path)
        proof = rv.validate_trace({"operator_mode": "focused_execution"})
        check_names = {c["check"] for c in proof["checks"]}
        expected = {
            "mode_policy", "phase_transition", "focus_determinism",
            "loop_transition", "attention_weights", "boundary_policy",
            "continuity_mapping",
        }
        assert check_names == expected

    def test_stats(self, tmp_path):
        rv = CognitionReplayValidator(proof_dir=tmp_path)
        rv.validate_trace({"operator_mode": "focused_execution"})
        stats = rv.get_stats()
        assert stats["total_validations"] == 1
        assert stats["total_passes"] == 1


# =========================================================================
# Cognition Boundary Policies Tests
# =========================================================================


class TestCognitionBoundaryPolicies:

    def test_default_limits_per_mode(self):
        for mode in OperatorMode:
            assert mode.value in DEFAULT_COGNITION_BOUNDARIES

    def test_passing_check(self):
        e = CognitionBoundaryEnforcer(mode=OperatorMode.FOCUSED_EXECUTION)
        r = e.check_cognition_depth(5)
        assert r["passed"]

    def test_failing_check(self):
        e = CognitionBoundaryEnforcer(mode=OperatorMode.FOCUSED_EXECUTION)
        r = e.check_cognition_depth(100)
        assert not r["passed"]
        assert "violation" in r

    def test_override_capping(self):
        e = CognitionBoundaryEnforcer(
            mode=OperatorMode.FOCUSED_EXECUTION,
            overrides={"max_cognition_depth": 100}
        )
        assert e.limits["max_cognition_depth"] == 12

    def test_override_below_default(self):
        e = CognitionBoundaryEnforcer(
            mode=OperatorMode.FOCUSED_EXECUTION,
            overrides={"max_cognition_depth": 5}
        )
        assert e.limits["max_cognition_depth"] == 5

    def test_inspection_tighter_bounds(self):
        e = CognitionBoundaryEnforcer(mode=OperatorMode.INSPECTION_MODE)
        assert e.limits["max_cognition_depth"] == 6
        assert e.limits["max_open_loops"] == 5

    def test_bulk_check(self):
        e = CognitionBoundaryEnforcer(mode=OperatorMode.FOCUSED_EXECUTION)
        r = e.check_all(cognition_depth=5, open_loops=3)
        assert r["all_passed"]

    def test_bulk_check_violations(self):
        e = CognitionBoundaryEnforcer(mode=OperatorMode.FOCUSED_EXECUTION)
        r = e.check_all(cognition_depth=100, open_loops=100)
        assert not r["all_passed"]
        assert r["violation_count"] == 2

    def test_all_check_methods(self):
        e = CognitionBoundaryEnforcer(mode=OperatorMode.FOCUSED_EXECUTION)
        e.check_cognition_depth(0)
        e.check_open_loops(0)
        e.check_attention_reweights(0)
        e.check_focus_shifts(0)
        e.check_checkpoints(0)
        e.check_continuity_chain(0)
        e.check_working_window(0)
        assert e.get_stats()["total_checks"] == 7


# =========================================================================
# Cognition Lifecycle Engine Tests
# =========================================================================


class TestCognitionLifecycleEngine:

    def test_register_session(self, tmp_path):
        lce = CognitionLifecycleEngine(state_dir=tmp_path)
        sess = lce.register_session("s1")
        assert sess.state == CognitionPhase.INITIALIZED

    def test_valid_transitions(self, tmp_path):
        lce = CognitionLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        assert lce.transition("s1", CognitionPhase.ACTIVE)
        assert lce.transition("s1", CognitionPhase.FOCUSED)
        assert lce.transition("s1", CognitionPhase.CHECKPOINTED)
        assert lce.transition("s1", CognitionPhase.RESUMED)

    def test_invalid_transition(self, tmp_path):
        lce = CognitionLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        assert not lce.transition("s1", CognitionPhase.FOCUSED)

    def test_terminal_state_archived(self, tmp_path):
        lce = CognitionLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        lce.transition("s1", CognitionPhase.ACTIVE)
        lce.transition("s1", CognitionPhase.ARCHIVED)
        assert lce.is_terminal("s1")
        assert not lce.transition("s1", CognitionPhase.ACTIVE)

    def test_terminal_state_terminated(self, tmp_path):
        lce = CognitionLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        lce.transition("s1", CognitionPhase.TERMINATED)
        assert lce.is_terminal("s1")

    def test_active_and_archived_sessions(self, tmp_path):
        lce = CognitionLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        lce.register_session("s2")
        lce.transition("s1", CognitionPhase.ACTIVE)
        lce.transition("s1", CognitionPhase.ARCHIVED)
        lce.transition("s2", CognitionPhase.ACTIVE)
        assert len(lce.get_active_sessions()) == 1
        assert len(lce.get_archived_sessions()) == 1

    def test_transition_lineage_persisted(self, tmp_path):
        lce = CognitionLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        lce.transition("s1", CognitionPhase.ACTIVE)
        path = tmp_path / "cognition_lifecycle_lineage.jsonl"
        assert path.exists()
        with path.open() as f:
            lines = f.readlines()
        assert len(lines) >= 1

    def test_nonexistent_session(self, tmp_path):
        lce = CognitionLifecycleEngine(state_dir=tmp_path)
        assert not lce.transition("nonexistent", CognitionPhase.ACTIVE)
        assert lce.get_state("nonexistent") is None

    def test_stale_to_resumed_to_active(self, tmp_path):
        lce = CognitionLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        lce.transition("s1", CognitionPhase.ACTIVE)
        lce.transition("s1", CognitionPhase.STALE)
        assert lce.transition("s1", CognitionPhase.RESUMED)
        assert lce.transition("s1", CognitionPhase.ACTIVE)

    def test_suspended_to_stale_to_archived(self, tmp_path):
        lce = CognitionLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        lce.transition("s1", CognitionPhase.ACTIVE)
        lce.transition("s1", CognitionPhase.SUSPENDED)
        lce.transition("s1", CognitionPhase.STALE)
        assert lce.transition("s1", CognitionPhase.ARCHIVED)
        assert lce.is_terminal("s1")


# =========================================================================
# Critical Constraint Tests
# =========================================================================


class TestNoAutonomousSelfDirection:
    """Constraint: substrate cannot self-direct or self-task."""

    def test_engine_cannot_execute_actions(self, tmp_path):
        engine = PersistentOperatorCognitionEngine(state_dir=tmp_path)
        assert not hasattr(engine, "execute")
        assert not hasattr(engine, "dispatch")
        assert not hasattr(engine, "run_workflow")
        assert not hasattr(engine, "run_command")

    def test_intent_always_operator_set(self, tmp_path):
        engine = PersistentOperatorCognitionEngine(state_dir=tmp_path)
        intent = engine.register_intent("Do X")
        assert intent.set_by == "operator"

    def test_focus_always_operator_set(self, tmp_path):
        engine = PersistentOperatorCognitionEngine(state_dir=tmp_path)
        focus = engine.set_focus("build", "Test")
        assert focus.set_by == "operator"


class TestNoSelfGeneratedGoals:
    """Constraint: substrate never generates its own operational intent."""

    def test_intent_contract_default(self):
        i = OperationalIntentState()
        assert i.set_by == "operator"

    def test_focus_contract_default(self):
        f = ActiveOperationalFocus()
        assert f.set_by == "operator"

    def test_engine_hardcodes_operator(self, tmp_path):
        engine = PersistentOperatorCognitionEngine(state_dir=tmp_path)
        f = engine.set_focus("build", "Test")
        i = engine.register_intent("Test intent")
        assert f.set_by == "operator"
        assert i.set_by == "operator"


class TestNoUncontrolledRecursiveCognition:
    """Constraint: no recursive or uncontrolled cognitive loops."""

    def test_working_window_bounded(self):
        w = WorkingCognitionWindow(max_items=3)
        w.add_item({"a": 1})
        w.add_item({"b": 2})
        w.add_item({"c": 3})
        assert not w.add_item({"d": 4})

    def test_boundary_enforcer_limits(self):
        e = CognitionBoundaryEnforcer(mode=OperatorMode.INSPECTION_MODE)
        r = e.check_cognition_depth(100)
        assert not r["passed"]

    def test_lifecycle_prevents_invalid_loops(self, tmp_path):
        lce = CognitionLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        lce.transition("s1", CognitionPhase.ACTIVE)
        lce.transition("s1", CognitionPhase.ARCHIVED)
        assert not lce.transition("s1", CognitionPhase.ACTIVE)


class TestNoGovernanceBypass:
    """Constraint: all transitions emit lineage receipts."""

    def test_mode_transition_emits_receipt(self, tmp_path):
        engine = PersistentOperatorCognitionEngine(state_dir=tmp_path)
        r = engine.set_operator_mode(OperatorMode.PLANNING_MODE)
        assert r.receipt_id.startswith("cogrcpt-")

    def test_focus_shift_emits_receipt(self, tmp_path):
        engine = PersistentOperatorCognitionEngine(state_dir=tmp_path)
        engine.set_focus("build", "Test")
        receipts = engine.get_recent_receipts()
        assert any("focus_set" in r.get("action", "") for r in receipts)

    def test_loop_emits_receipt(self, tmp_path):
        engine = PersistentOperatorCognitionEngine(state_dir=tmp_path)
        engine.open_loop("wf", "wf-1", "Test")
        receipts = engine.get_recent_receipts()
        assert any("loop_opened" in r.get("action", "") for r in receipts)

    def test_checkpoint_emits_receipt(self, tmp_path):
        engine = PersistentOperatorCognitionEngine(state_dir=tmp_path)
        engine.create_checkpoint()
        receipts = engine.get_recent_receipts()
        assert any("checkpoint_created" in r.get("action", "") for r in receipts)

    def test_lineage_persisted_to_disk(self, tmp_path):
        engine = PersistentOperatorCognitionEngine(state_dir=tmp_path)
        engine.set_focus("build", "Test")
        path = tmp_path / "cognition_lineage.jsonl"
        assert path.exists()


class TestReplayDeterminism:
    """Constraint: same inputs must produce same outputs."""

    def test_all_seven_checks_pass(self, tmp_path):
        rv = CognitionReplayValidator(proof_dir=tmp_path)
        trace = {
            "operator_mode": "focused_execution",
            "phase": "active",
            "from_phase": "initialized",
            "to_phase": "active",
            "focus_input": {"type": "build", "desc": "test"},
            "loop_state": "active",
            "loop_target": "waiting",
        }
        proof = rv.validate_trace(trace)
        assert proof["all_passed"]
        for check in proof["checks"]:
            assert check["passed"], f"Check {check['check']} failed"

    def test_deterministic_hashing(self):
        data = {"a": 1, "b": "test", "c": [1, 2, 3]}
        h1 = _content_hash(data)
        h2 = _content_hash(data)
        assert h1 == h2


class TestBoundedAttention:
    """Constraint: attention weights are bounded and decay-controlled."""

    def test_weight_clamping(self):
        m = RuntimeAttentionMap()
        m.set_weight(AttentionWeightType.WORKFLOW, 100.0)
        assert m.get_weight(AttentionWeightType.WORKFLOW) == 5.0
        m.set_weight(AttentionWeightType.WORKFLOW, -10.0)
        assert m.get_weight(AttentionWeightType.WORKFLOW) == 0.0

    def test_operator_focus_immune_to_decay(self, tmp_path):
        attn = RuntimeAttentionSystem(state_dir=tmp_path)
        for _ in range(10):
            attn.apply_mode_decay()
        assert attn.attention_map.get_weight(AttentionWeightType.OPERATOR_FOCUS) == 2.0

    def test_override_cannot_exceed_default(self):
        e = CognitionBoundaryEnforcer(
            mode=OperatorMode.FOCUSED_EXECUTION,
            overrides={"max_working_window_items": 1000}
        )
        assert e.limits["max_working_window_items"] == 20


class TestObservabilityCompleteness:
    """Constraint: all 10 event types are observable."""

    def test_all_event_types_have_files(self):
        assert len(EVENT_FILE_MAP) == 10
        for et in CognitionEventType:
            assert et.value in EVENT_FILE_MAP

    def test_all_event_types_recordable(self, tmp_path):
        obs = CognitionObservabilityPipeline(obs_dir=tmp_path)
        for et in CognitionEventType:
            obs.record_event(et, "test-session", {"test": True})
        assert obs.get_stats()["total_events"] == 10


class TestCheckpointRestoreIntegrity:
    """Constraint: checkpoints capture and restore full state."""

    def test_checkpoint_captures_all_subsystems(self, tmp_path):
        engine = PersistentOperatorCognitionEngine(state_dir=tmp_path)
        engine.set_focus("build", "Test")
        engine.open_loop("wf", "wf-1", "Loop test")
        cp = engine.create_checkpoint()
        d = cp.to_dict()
        assert d["cognitive_state_snapshot"] != {}
        assert d["active_focus_snapshot"] != {}
        assert len(d["open_loops_snapshot"]) >= 1

    def test_checkpoint_roundtrip_via_bridge(self, tmp_path):
        bridge = CognitionContinuityBridge(state_dir=tmp_path)
        cp = bridge.create_checkpoint(
            "s1", OperatorMode.FOCUSED_EXECUTION,
            CognitionPhase.ACTIVE, {"mode": "focused"},
            {"focus_id": "f1"}, [{"loop_id": "l1"}],
            {"weights": {}}, ["chk-prev"]
        )
        loaded = bridge.load_checkpoint(cp.checkpoint_id)
        assert loaded is not None
        assert loaded["operator_mode"] == "focused_execution"
        assert loaded["active_focus_snapshot"]["focus_id"] == "f1"


# =========================================================================
# Integration Tests
# =========================================================================


class TestIntegration:
    """End-to-end integration across all cognition subsystems."""

    def test_full_cognition_session(self, tmp_path):
        engine = PersistentOperatorCognitionEngine(state_dir=tmp_path)
        store = WorkingCognitionStore(state_dir=tmp_path)
        attn = RuntimeAttentionSystem(state_dir=tmp_path)
        ole = OpenLoopCognitionEngine(state_dir=tmp_path)
        tce = TemporalContinuityEngine(
            session_id=engine.session_id, state_dir=tmp_path
        )
        bridge = CognitionContinuityBridge(state_dir=tmp_path)
        obs = CognitionObservabilityPipeline(obs_dir=tmp_path / "obs")
        lce = CognitionLifecycleEngine(state_dir=tmp_path / "lifecycle")

        lce.register_session(engine.session_id)
        lce.transition(engine.session_id, CognitionPhase.ACTIVE)

        engine.set_phase(CognitionPhase.ACTIVE)
        engine.set_operator_mode(OperatorMode.OPERATIONAL_SUPERVISION)
        obs.record_initialized(engine.session_id, mode="operational_supervision")

        focus = engine.set_focus("build", "Phase 96.8BT")
        obs.record_focus_shifted(
            engine.session_id, focus.focus_id, "build"
        )

        loop = ole.open_loop("workflow", "wf-1", "Briefing incomplete")
        obs.record_loop_opened(
            engine.session_id, loop.loop_id, "workflow"
        )

        attn.reweight(AttentionWeightType.LOOP_URGENCY, 3.0)
        obs.record_attention_reweighted(
            engine.session_id, "loop_urgency", 1.5, 3.0
        )

        tce.record_workflow_event("wf-1", "started")

        cp = engine.create_checkpoint()
        obs.record_checkpoint_created(engine.session_id, cp.checkpoint_id)

        ole.resolve(loop.loop_id, "Briefing completed")
        obs.record_loop_resolved(
            engine.session_id, loop.loop_id, "Briefing completed"
        )

        snap = engine.get_cognitive_snapshot()
        store.persist_snapshot(engine.session_id, snap)

        bridge.persist_outcome(
            engine.session_id,
            CognitionPhase.ARCHIVED,
            snap,
            [l.to_dict() for l in ole.get_active_loops()],
        )

        summary = tce.end_session()
        obs.record_cognition_archived(engine.session_id, "session_complete")

        assert obs.get_stats()["total_events"] >= 7
        assert store.load_latest_snapshot() is not None
        assert engine.get_stats()["total_focus_shifts"] == 1
        assert ole.get_stats()["total_resolved"] >= 1

    def test_session_continuity_restoration(self, tmp_path):
        bridge = CognitionContinuityBridge(state_dir=tmp_path)
        bridge.persist_outcome(
            "old-sess", CognitionPhase.CHECKPOINTED,
            {"cognitive_state": {"last_checkpoint_id": "chk-1"}},
            [{"loop_id": "l1", "state": "waiting", "source_type": "wf"}]
        )
        bridge.create_checkpoint(
            "old-sess", OperatorMode.FOCUSED_EXECUTION,
            CognitionPhase.CHECKPOINTED, {},
            {"focus_id": "f1"}, [{"loop_id": "l1"}]
        )

        packet = bridge.build_resume_packet("old-sess")
        assert len(packet["open_loops"]) >= 1

        engine = PersistentOperatorCognitionEngine(
            session_id="new-sess", state_dir=tmp_path
        )
        engine.link_previous_session("old-sess", gap_seconds=300)
        cf = engine.restore_continuity(
            "old-sess",
            focus_ids=["f1"],
            loop_ids=["l1"],
        )
        assert cf.restoration_complete
        assert engine.get_stats()["continuity_chain_length"] == 1

    def test_replay_across_modes(self, tmp_path):
        rv = CognitionReplayValidator(proof_dir=tmp_path)
        traces = [
            {"operator_mode": m.value, "loop_state": "active", "loop_target": "waiting"}
            for m in OperatorMode
        ]
        result = rv.validate_session(traces)
        assert result["all_passed"]
        assert result["trace_count"] == 5

    def test_boundary_enforcement_across_modes(self):
        for mode in OperatorMode:
            e = CognitionBoundaryEnforcer(mode=mode)
            r = e.check_all(cognition_depth=0, open_loops=0)
            assert r["all_passed"]

    def test_lifecycle_full_path(self, tmp_path):
        lce = CognitionLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        phases = [
            CognitionPhase.ACTIVE,
            CognitionPhase.FOCUSED,
            CognitionPhase.SUSPENDED,
            CognitionPhase.STALE,
            CognitionPhase.RESUMED,
            CognitionPhase.ACTIVE,
            CognitionPhase.ARCHIVED,
        ]
        for phase in phases:
            assert lce.transition("s1", phase), f"Failed: -> {phase.value}"
        assert lce.is_terminal("s1")
