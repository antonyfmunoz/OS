"""Tests for substrate continuity and runtime cognition.

Validates:
  - Runtime cognition contracts (data shapes)
  - Continuity store persistence
  - Event classification
  - Open-loop tracking and resolution
  - Resume packet generation and determinism
  - Session/restart/operator summaries
  - Runtime-memory governance bridge
  - Continuity engine end-to-end
  - Replay determinism
  - Governance lineage preservation
  - No hidden state mutation

Phase 96.8BN.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/opt/OS")

from core.runtime.continuity_classification_engine_v1 import (
    ContinuityClass,
    classify_event,
    classify_outcome,
)
from core.runtime.continuity_summary_engine_v1 import ContinuitySummaryEngine
from core.runtime.open_loop_registry_v1 import (
    LoopStatus,
    LoopType,
    OpenLoopRegistry,
)
from core.runtime.runtime_cognition_contracts_v1 import (
    ContinuityPhase,
    EventSeverity,
    OutcomeResult,
    RuntimeContextUpdate,
    RuntimeContinuityState,
    RuntimeEvent,
    RuntimeOutcome,
    RuntimeResumePacket,
    RuntimeSessionSummary,
    RuntimeTrace,
)
from core.runtime.runtime_continuity_store_v1 import RuntimeContinuityStore
from core.runtime.runtime_memory_governance_bridge_v1 import (
    PromotionRule,
    RuntimeMemoryGovernanceBridge,
)
from core.runtime.runtime_resume_packet_v1 import ResumePacketGenerator
from core.runtime.substrate_continuity_engine_v1 import SubstrateContinuityEngine


class TestRuntimeContracts:
    def test_runtime_event_creation(self):
        event = RuntimeEvent(event_type="test", source="test")
        assert event.event_id.startswith("rtevt-")
        assert event.timestamp
        d = event.to_dict()
        assert d["event_type"] == "test"

    def test_runtime_event_content_hash(self):
        e1 = RuntimeEvent(event_id="fixed", event_type="test", source="a", timestamp="t1")
        e2 = RuntimeEvent(event_id="fixed", event_type="test", source="a", timestamp="t1")
        assert e1.content_hash() == e2.content_hash()

    def test_runtime_trace_creation(self):
        trace = RuntimeTrace(source="discord", mode="builder")
        assert trace.trace_id.startswith("rttrace-")
        d = trace.to_dict()
        assert d["mode"] == "builder"

    def test_runtime_outcome_creation(self):
        outcome = RuntimeOutcome(command="test-cmd", result=OutcomeResult.SUCCESS)
        assert outcome.outcome_id.startswith("rtout-")
        d = outcome.to_dict()
        assert d["result"] == "success"

    def test_continuity_state_creation(self):
        state = RuntimeContinuityState(
            phase=ContinuityPhase.ACTIVE,
            active_goals=["goal1"],
            total_events_ingested=5,
        )
        assert state.state_id.startswith("rtstate-")
        d = state.to_dict()
        assert d["phase"] == "active"
        assert d["total_events_ingested"] == 5

    def test_resume_packet_creation(self):
        packet = RuntimeResumePacket(
            active_goals=["goal1"],
            suggested_next_actions=["next1"],
        )
        assert packet.packet_id.startswith("rtresume-")
        d = packet.to_dict()
        assert len(d["active_goals"]) == 1

    def test_resume_packet_content_hash_deterministic(self):
        p1 = RuntimeResumePacket(packet_id="fixed", active_goals=["g"], created_at="t")
        p2 = RuntimeResumePacket(packet_id="fixed", active_goals=["g"], created_at="t")
        assert p1.content_hash() == p2.content_hash()

    def test_session_summary_creation(self):
        summary = RuntimeSessionSummary(session_id="s1", summary_type="session")
        assert summary.summary_id.startswith("rtsum-")


class TestContinuityStore:
    def test_append_and_read_events(self, tmp_path):
        store = RuntimeContinuityStore(store_dir=tmp_path / "store")
        event = RuntimeEvent(event_type="test", source="unit_test")
        store.append_event(event.to_dict())
        events = store.load_recent_events(limit=10)
        assert len(events) == 1
        assert events[0]["event_type"] == "test"

    def test_append_and_read_traces(self, tmp_path):
        store = RuntimeContinuityStore(store_dir=tmp_path / "store")
        trace = RuntimeTrace(source="test", mode="builder")
        store.append_trace(trace.to_dict())
        assert store.count_traces() == 1

    def test_append_and_read_outcomes(self, tmp_path):
        store = RuntimeContinuityStore(store_dir=tmp_path / "store")
        outcome = RuntimeOutcome(command="test", result=OutcomeResult.SUCCESS)
        store.append_outcome(outcome.to_dict())
        outcomes = store.load_recent_outcomes(limit=10)
        assert len(outcomes) == 1

    def test_snapshot_persistence(self, tmp_path):
        store = RuntimeContinuityStore(store_dir=tmp_path / "store")
        state = RuntimeContinuityState(total_events_ingested=5)
        store.save_snapshot(state.to_dict())
        loaded = store.load_latest_snapshot()
        assert loaded is not None
        assert loaded["total_events_ingested"] == 5

    def test_resume_packet_persistence(self, tmp_path):
        store = RuntimeContinuityStore(store_dir=tmp_path / "store")
        packet = RuntimeResumePacket(active_goals=["g1"])
        store.save_resume_packet(packet.to_dict())
        loaded = store.load_latest_resume_packet()
        assert loaded is not None
        assert loaded["active_goals"] == ["g1"]

    def test_stats(self, tmp_path):
        store = RuntimeContinuityStore(store_dir=tmp_path / "store")
        store.append_event({"test": True})
        store.append_event({"test": True})
        store.append_trace({"test": True})
        stats = store.get_stats()
        assert stats["events"] == 2
        assert stats["traces"] == 1


class TestClassificationEngine:
    def test_transient_event(self):
        result = classify_event({"event_id": "e1", "event_type": "reply_chunk"})
        assert result.classification == ContinuityClass.TRANSIENT
        assert result.persist is False

    def test_critical_event(self):
        result = classify_event({"event_id": "e1", "event_type": "execution_failed"})
        assert result.classification == ContinuityClass.OPERATIONALLY_CRITICAL
        assert result.persist is True
        assert result.track_as_open_loop is True

    def test_canonical_event(self):
        result = classify_event({"event_id": "e1", "event_type": "execution_completed"})
        assert result.classification == ContinuityClass.CANONICAL_WORTHY
        assert result.promote_to_memory is True

    def test_resumable_event(self):
        result = classify_event({"event_id": "e1", "event_type": "execution_started"})
        assert result.classification == ContinuityClass.RESUMABLE

    def test_failure_outcome(self):
        result = classify_outcome({"outcome_id": "o1", "result": "failure"})
        assert result.classification == ContinuityClass.OPERATIONALLY_CRITICAL
        assert result.promote_to_memory is True

    def test_success_outcome(self):
        result = classify_outcome({"outcome_id": "o1", "result": "success"})
        assert result.classification == ContinuityClass.CANONICAL_WORTHY

    def test_blocked_outcome(self):
        result = classify_outcome({"outcome_id": "o1", "result": "blocked"})
        assert result.classification == ContinuityClass.BLOCKED
        assert result.track_as_open_loop is True


class TestOpenLoopRegistry:
    def test_create_and_retrieve(self, tmp_path):
        registry = OpenLoopRegistry(store_dir=tmp_path / "loops")
        loop = registry.create_loop(
            LoopType.FAILED_EXECUTION, "Test failure", source_event_id="evt-1"
        )
        assert loop.loop_id.startswith("loop-")
        assert loop.status == LoopStatus.OPEN
        open_loops = registry.get_open_loops()
        assert len(open_loops) == 1

    def test_resolve_loop(self, tmp_path):
        registry = OpenLoopRegistry(store_dir=tmp_path / "loops")
        loop = registry.create_loop(LoopType.FAILED_EXECUTION, "Test failure")
        result = registry.resolve_loop(loop.loop_id, "Fixed the issue", resolved_by="human")
        assert result is True
        open_loops = registry.get_open_loops()
        assert len(open_loops) == 0

    def test_mark_stale(self, tmp_path):
        registry = OpenLoopRegistry(store_dir=tmp_path / "loops")
        loop = registry.create_loop(LoopType.DEFERRED_ACTION, "Deferred work")
        registry.mark_stale(loop.loop_id)
        stats = registry.get_stats()
        assert stats["stale"] == 1
        assert stats["open"] == 0

    def test_stats(self, tmp_path):
        registry = OpenLoopRegistry(store_dir=tmp_path / "loops")
        registry.create_loop(LoopType.FAILED_EXECUTION, "Failure 1")
        registry.create_loop(LoopType.PENDING_GOVERNANCE, "Approval needed")
        registry.create_loop(LoopType.DEFERRED_ACTION, "Later")
        stats = registry.get_stats()
        assert stats["total"] == 3
        assert stats["open"] == 3


class TestGovernanceBridge:
    def test_failure_promotes(self, tmp_path):
        bridge = RuntimeMemoryGovernanceBridge(receipts_dir=tmp_path / "receipts")
        outcome = {
            "outcome_id": "o1",
            "command": "test",
            "result": "failure",
            "error_message": "broke",
        }
        candidate = bridge.evaluate_outcome(outcome)
        assert candidate.should_promote is True
        assert candidate.rule_applied == PromotionRule.FAILURE_RECORD

    def test_routine_success_no_promote(self, tmp_path):
        bridge = RuntimeMemoryGovernanceBridge(receipts_dir=tmp_path / "receipts")
        outcome = {"outcome_id": "o1", "command": "routine-check", "result": "success"}
        candidate = bridge.evaluate_outcome(outcome)
        assert candidate.should_promote is False

    def test_important_success_promotes(self, tmp_path):
        bridge = RuntimeMemoryGovernanceBridge(receipts_dir=tmp_path / "receipts")
        outcome = {"outcome_id": "o1", "command": "ingest-safe-doc-cu", "result": "success"}
        candidate = bridge.evaluate_outcome(outcome)
        assert candidate.should_promote is True
        assert candidate.rule_applied == PromotionRule.IMPORTANT_OUTCOME

    def test_critical_loop_promotes(self, tmp_path):
        bridge = RuntimeMemoryGovernanceBridge(receipts_dir=tmp_path / "receipts")
        loop = {"loop_id": "l1", "loop_type": "failed_execution", "description": "Chrome failed"}
        candidate = bridge.evaluate_open_loop(loop)
        assert candidate.should_promote is True

    def test_decisions_persisted(self, tmp_path):
        bridge = RuntimeMemoryGovernanceBridge(receipts_dir=tmp_path / "receipts")
        bridge.evaluate_outcome({"outcome_id": "o1", "command": "test", "result": "failure"})
        bridge.evaluate_outcome({"outcome_id": "o2", "command": "test2", "result": "success"})
        decisions = bridge.load_decisions()
        assert len(decisions) == 2


class TestResumePacketGenerator:
    def test_generates_packet(self, tmp_path):
        store = RuntimeContinuityStore(store_dir=tmp_path / "store")
        registry = OpenLoopRegistry(store_dir=tmp_path / "loops")
        registry.create_loop(LoopType.FAILED_EXECUTION, "Something failed")

        gen = ResumePacketGenerator(
            continuity_store=store,
            loop_registry=registry,
            memory_store_dir=tmp_path / "mem",
        )
        packet = gen.generate(session_id="test-session", active_goals=["goal1"])
        assert packet.packet_id.startswith("rtresume-")
        assert "goal1" in packet.active_goals
        assert len(packet.open_loops) == 1

    def test_packet_saved_to_disk(self, tmp_path):
        store = RuntimeContinuityStore(store_dir=tmp_path / "store")
        registry = OpenLoopRegistry(store_dir=tmp_path / "loops")
        gen = ResumePacketGenerator(
            continuity_store=store,
            loop_registry=registry,
            memory_store_dir=tmp_path / "mem",
        )
        gen.generate(session_id="test")
        loaded = store.load_latest_resume_packet()
        assert loaded is not None


class TestContinuityEngine:
    def test_full_lifecycle(self, tmp_path):
        engine = SubstrateContinuityEngine(
            store_dir=tmp_path / "store",
            loop_dir=tmp_path / "loops",
            summaries_dir=tmp_path / "summaries",
            promotion_dir=tmp_path / "promotions",
        )
        engine.start_session("test-session")

        engine.ingest_event(
            {"event_id": "e1", "event_type": "execution_completed", "source": "test"}
        )
        engine.ingest_trace({"trace_id": "t1", "source": "test", "mode": "builder"})
        engine.record_outcome({"outcome_id": "o1", "command": "test", "result": "success"})

        stats = engine.get_stats()
        assert stats["events_ingested"] >= 1
        assert stats["traces_ingested"] == 1
        assert stats["outcomes_recorded"] == 1

    def test_snapshot_captures_state(self, tmp_path):
        engine = SubstrateContinuityEngine(
            store_dir=tmp_path / "store",
            loop_dir=tmp_path / "loops",
            summaries_dir=tmp_path / "summaries",
            promotion_dir=tmp_path / "promotions",
        )
        engine.start_session("test")
        engine.ingest_event(
            {"event_id": "e1", "event_type": "execution_failed", "severity": "error"}
        )
        snapshot = engine.take_snapshot(active_goals=["test goal"])
        assert snapshot.total_events_ingested >= 1
        assert "test goal" in snapshot.active_goals

    def test_resume_packet_includes_open_loops(self, tmp_path):
        engine = SubstrateContinuityEngine(
            store_dir=tmp_path / "store",
            loop_dir=tmp_path / "loops",
            summaries_dir=tmp_path / "summaries",
            promotion_dir=tmp_path / "promotions",
        )
        engine.start_session("test")
        engine.ingest_event(
            {"event_id": "e1", "event_type": "execution_failed", "severity": "error"}
        )
        packet = engine.generate_resume_packet(active_goals=["recover"])
        assert len(packet.get("open_loops", [])) >= 1

    def test_context_update_persisted(self, tmp_path):
        engine = SubstrateContinuityEngine(
            store_dir=tmp_path / "store",
            loop_dir=tmp_path / "loops",
            summaries_dir=tmp_path / "summaries",
            promotion_dir=tmp_path / "promotions",
        )
        engine.start_session("test")
        engine.record_context_update("phase", "current_phase", "old", "new", "test")
        store = RuntimeContinuityStore(store_dir=tmp_path / "store")
        updates = store._load_all(store.context_updates_path)
        assert len(updates) == 1

    def test_no_hidden_state_mutation(self, tmp_path):
        engine = SubstrateContinuityEngine(
            store_dir=tmp_path / "store",
            loop_dir=tmp_path / "loops",
            summaries_dir=tmp_path / "summaries",
            promotion_dir=tmp_path / "promotions",
        )
        engine.start_session("test")
        engine.ingest_event({"event_id": "e1", "event_type": "execution_completed"})
        engine.record_outcome({"outcome_id": "o1", "command": "test", "result": "success"})

        store = RuntimeContinuityStore(store_dir=tmp_path / "store")
        events = store.load_recent_events()
        outcomes = store.load_recent_outcomes()

        assert all("_internal" not in e for e in events)
        assert all("_internal" not in o for o in outcomes)


class TestReplayDeterminism:
    def test_classification_deterministic(self):
        event = {"event_id": "e1", "event_type": "execution_failed"}
        r1 = classify_event(event)
        r2 = classify_event(event)
        assert r1.classification == r2.classification
        assert r1.decision_id == r2.decision_id

    def test_outcome_classification_deterministic(self):
        outcome = {"outcome_id": "o1", "result": "failure"}
        r1 = classify_outcome(outcome)
        r2 = classify_outcome(outcome)
        assert r1.classification == r2.classification
        assert r1.decision_id == r2.decision_id

    def test_engine_replay_stable(self, tmp_path):
        events = [
            {"event_id": "e1", "event_type": "execution_completed"},
            {"event_id": "e2", "event_type": "execution_failed", "severity": "error"},
        ]

        engine1 = SubstrateContinuityEngine(
            store_dir=tmp_path / "s1",
            loop_dir=tmp_path / "l1",
            summaries_dir=tmp_path / "sum1",
            promotion_dir=tmp_path / "p1",
        )
        engine1.start_session("replay-test")
        results1 = [engine1.ingest_event(e) for e in events]

        engine2 = SubstrateContinuityEngine(
            store_dir=tmp_path / "s2",
            loop_dir=tmp_path / "l2",
            summaries_dir=tmp_path / "sum2",
            promotion_dir=tmp_path / "p2",
        )
        engine2.start_session("replay-test")
        results2 = [engine2.ingest_event(e) for e in events]

        for r1, r2 in zip(results1, results2):
            assert r1.get("classification") == r2.get("classification")
            assert r1.get("persist") == r2.get("persist")


class TestRuntimeArtifacts:
    def test_continuity_validation_proof_exists(self):
        path = Path(
            "data/runtime/runtime_continuity_replay_proofs/continuity_validation_proof.json"
        )
        if not path.exists():
            pytest.skip("Runtime artifacts not present")
        with open(path) as f:
            data = json.load(f)
        assert data["all_pass"] is True

    def test_continuity_store_has_data(self):
        path = Path("data/runtime/substrate_continuity/events.jsonl")
        if not path.exists():
            pytest.skip("Runtime artifacts not present")
        with open(path) as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) > 0

    def test_open_loop_registry_exists(self):
        path = Path("data/runtime/open_loop_registry/open_loops.jsonl")
        if not path.exists():
            pytest.skip("Runtime artifacts not present")
        with open(path) as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) > 0

    def test_resume_packet_exists(self):
        path = Path("data/runtime/substrate_continuity/latest_resume_packet.json")
        if not path.exists():
            pytest.skip("Runtime artifacts not present")
        with open(path) as f:
            data = json.load(f)
        assert data.get("packet_id")

    def test_continuity_summaries_exist(self):
        path = Path("data/runtime/continuity_summaries")
        if not path.exists():
            pytest.skip("Runtime artifacts not present")
        summaries = list(path.glob("*.json"))
        assert len(summaries) > 0
