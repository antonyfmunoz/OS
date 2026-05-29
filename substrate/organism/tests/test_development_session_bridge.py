"""Tests for DevelopmentSessionBridge — governed coding agent integration.

Validates that any coding harness (Claude Code, Codex, OpenCode, Hermes, etc.)
can register as an organism execution context and emit structured events,
decisions, and coherence observations through the organism protocol.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.organism.development_session_bridge import (
    CoherenceObservation,
    DevelopmentEvent,
    DevelopmentSessionBridge,
)
from substrate.organism.event_spine import EventDomain, EventSpine


@pytest.fixture()
def tmp_umh(tmp_path, monkeypatch):
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))
    import substrate.organism.development_session_bridge as mod
    monkeypatch.setattr(mod, "_SESSIONS_DIR", tmp_path / "data" / "umh" / "sessions")
    monkeypatch.setattr(mod, "_LEARNING_DIR", tmp_path / "data" / "umh" / "organism")
    return tmp_path


class TestSessionLifecycle:
    def test_register_and_close(self, tmp_umh):
        bridge = DevelopmentSessionBridge(session_id="test-lc-001", harness="claude_code")
        bridge.register_session(intent="test lifecycle")

        active = tmp_umh / "data" / "umh" / "sessions" / "active_sessions.jsonl"
        assert active.exists()
        record = json.loads(active.read_text().strip())
        assert record["session_id"] == "test-lc-001"
        assert record["harness"] == "claude_code"
        assert record["status"] == "active"

        result = bridge.close_session(outcome="completed", summary="lifecycle test done")
        assert result["outcome"] == "completed"
        assert result["session_id"] == "test-lc-001"

        session_file = tmp_umh / "data" / "umh" / "sessions" / "test-lc-001.json"
        assert session_file.exists()
        persisted = json.loads(session_file.read_text())
        assert persisted["summary"] == "lifecycle test done"
        assert persisted["duration_seconds"] >= 0

    def test_auto_generates_session_id(self, tmp_umh):
        bridge = DevelopmentSessionBridge(harness="codex")
        assert len(bridge.session_id) == 12

    def test_completed_sessions_log(self, tmp_umh):
        bridge = DevelopmentSessionBridge(session_id="test-log", harness="opencode")
        bridge.register_session()
        bridge.close_session(outcome="failed", summary="test failure")

        completed = tmp_umh / "data" / "umh" / "sessions" / "completed_sessions.jsonl"
        assert completed.exists()
        record = json.loads(completed.read_text().strip())
        assert record["outcome"] == "failed"
        assert record["harness"] == "opencode"


class TestMutationRecording:
    def test_record_mutation(self, tmp_umh):
        bridge = DevelopmentSessionBridge(session_id="test-mut", harness="claude_code")
        evt = bridge.record_mutation(
            description="Move auth middleware",
            files=["transports/api/http/middleware/auth.ts"],
            layer="transports",
            risk_level="medium",
        )

        assert evt.event_type == "mutation"
        assert evt.layer == "transports"
        assert evt.risk_level == "medium"
        assert "transports/api/http/middleware/auth.ts" in bridge._files_touched

    def test_files_touched_accumulates(self, tmp_umh):
        bridge = DevelopmentSessionBridge(session_id="test-acc", harness="hermes")
        bridge.record_mutation("edit a", ["file_a.py"], "substrate")
        bridge.record_mutation("edit b", ["file_b.py", "file_c.py"], "adapters")

        assert bridge._files_touched == {"file_a.py", "file_b.py", "file_c.py"}

    def test_mutation_in_session_record(self, tmp_umh):
        bridge = DevelopmentSessionBridge(session_id="test-rec", harness="claude_code")
        bridge.register_session()
        bridge.record_mutation("create gate", ["scripts/check_x.py"], "scripts", "low")
        result = bridge.close_session()

        assert result["total_events"] == 1
        assert "scripts/check_x.py" in result["files_touched"]


class TestDecisionRecording:
    def test_record_decision(self, tmp_umh):
        bridge = DevelopmentSessionBridge(session_id="test-dec", harness="claude_code")
        dec = bridge.record_decision(
            decision="UMH infra goes in transports/",
            rationale="saas/ is EOS-only",
            alternatives_considered=["Keep in saas/"],
            confidence=0.95,
        )

        assert dec["decision"] == "UMH infra goes in transports/"
        assert dec["confidence"] == 0.95
        assert len(dec["alternatives"]) == 1

    def test_decision_emits_learning_signal(self, tmp_umh):
        bridge = DevelopmentSessionBridge(session_id="test-ls", harness="codex")
        bridge.record_decision("Test decision", "Test rationale", confidence=0.7)

        learning = tmp_umh / "data" / "umh" / "organism" / "learning_signals.jsonl"
        assert learning.exists()
        record = json.loads(learning.read_text().strip())
        assert record["agent_id"] == "developer:codex"
        assert record["pattern_observed"] == "Test decision"
        assert record["confidence"] == 0.7


class TestCoherenceObservations:
    def test_record_observation(self, tmp_umh):
        bridge = DevelopmentSessionBridge(session_id="test-coh", harness="claude_code")
        obs = bridge.record_coherence_observation(
            category="layer_violation",
            description="Infrastructure in projection layer",
            severity="warning",
            affected_files=["saas/middleware/auth.ts"],
            resolution="Moved to transports/",
        )

        assert obs.category == "layer_violation"
        assert obs.severity == "warning"

    def test_observation_in_close(self, tmp_umh):
        bridge = DevelopmentSessionBridge(session_id="test-coh2", harness="claude_code")
        bridge.register_session()
        bridge.record_coherence_observation("type_divergence", "Shadow enum", severity="error")
        bridge.record_coherence_observation("naming", "Projection name in substrate", severity="info")
        result = bridge.close_session()

        assert result["total_coherence_observations"] == 2
        assert len(result["coherence_observations"]) == 2


class TestGateResults:
    def test_record_gate_pass(self, tmp_umh):
        bridge = DevelopmentSessionBridge(session_id="test-gate", harness="claude_code")
        bridge.record_gate_result("dependency_direction", passed=True)

        assert len(bridge._events) == 1
        assert bridge._events[0].event_type == "gate_check"
        assert "passed" in bridge._events[0].description

    def test_record_gate_failure(self, tmp_umh):
        bridge = DevelopmentSessionBridge(session_id="test-gate2", harness="claude_code")
        bridge.record_gate_result("type_coherence", passed=False, violations=3)

        assert "FAILED" in bridge._events[0].description
        assert bridge._events[0].metadata["violations"] == 3


class TestEventSpineIntegration:
    def test_events_emitted_to_spine(self, tmp_umh):
        spine = EventSpine(max_events=100)
        received: list[dict] = []
        spine.subscribe("test", lambda e: received.append(e.to_dict()))

        bridge = DevelopmentSessionBridge(
            session_id="test-spine", harness="claude_code", event_spine=spine,
        )
        bridge.register_session(intent="spine test")
        bridge.record_mutation("edit file", ["a.py"], "substrate")
        bridge.record_decision("chose X", "because Y")
        bridge.record_coherence_observation("leak", "found leak", severity="warning")
        bridge.close_session()

        assert len(received) >= 4
        types = [e["event_type"] for e in received]
        assert "session_started" in types
        assert "development_mutation" in types
        assert "development_decision" in types
        assert "coherence_violation" in types
        assert "session_completed" in types

        for event in received:
            assert event["source"].startswith("dev_session:")
            assert event["correlation_id"] == "test-spine"

    def test_works_without_spine(self, tmp_umh):
        bridge = DevelopmentSessionBridge(session_id="test-nospine", harness="codex")
        bridge.register_session()
        bridge.record_mutation("edit", ["x.py"], "substrate")
        result = bridge.close_session()
        assert result["total_events"] == 1


class TestHarnessAgnostic:
    """The bridge must work identically for any harness."""

    @pytest.mark.parametrize("harness", [
        "claude_code", "codex", "opencode", "hermes", "aider", "cursor",
    ])
    def test_any_harness_can_register(self, tmp_umh, harness):
        bridge = DevelopmentSessionBridge(
            session_id=f"test-{harness}", harness=harness,
        )
        bridge.register_session(intent=f"{harness} test")
        bridge.record_mutation("edit", ["a.py"], "substrate")
        bridge.record_decision("decided X", "because Y")
        result = bridge.close_session()

        assert result["harness"] == harness
        assert result["total_events"] == 1
        assert result["total_decisions"] == 1


class TestToDict:
    def test_bridge_status(self, tmp_umh):
        bridge = DevelopmentSessionBridge(session_id="test-dict", harness="claude_code")
        bridge.record_mutation("edit", ["a.py"], "substrate")
        bridge.record_decision("X", "Y")

        status = bridge.to_dict()
        assert status["session_id"] == "test-dict"
        assert status["harness"] == "claude_code"
        assert status["status"] == "active"
        assert status["total_events"] == 1
        assert status["total_decisions"] == 1
        assert status["files_touched"] == 1
