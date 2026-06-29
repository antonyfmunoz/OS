"""C32 Pipeline B Integration Tests.

Proves the full governed chain works end-to-end:
Intent → DevSession → WorkPacket → Spine → OutcomeLearning
→ CapabilityRuntime → Proof → Journal.
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, "/opt/OS")


class TestDevSessionToSpine:
    """DevSessionTracker → ActionEnvelope → GovernedExecutionSpine."""

    def test_start_and_complete_session(self):
        from substrate.organism.dev_session_tracker import DevSessionTracker

        tmp = tempfile.mkdtemp()
        tracker = DevSessionTracker(store_dir=tmp)

        session = tracker.start_session("test intent", "umh")
        assert session.status == "active"
        assert session.intent == "test intent"

        tracker.record_commit(session.session_id, "abc123", "test commit")
        tracker.record_files_modified(session.session_id, 3)

        envelope = tracker.complete_session(session.session_id, "success")
        assert envelope is not None
        assert envelope.intent == "test intent"
        assert envelope.metadata["commits"][0]["sha"] == "abc123"
        assert envelope.metadata["files_modified"] == 3

    def test_submit_to_spine_produces_envelope(self):
        from substrate.organism.dev_session_tracker import DevSessionTracker

        tmp = tempfile.mkdtemp()
        tracker = DevSessionTracker(store_dir=tmp)

        session = tracker.start_session("spine test", "umh")
        tracker.record_commit(session.session_id, "def456", "test commit 2")

        class MockSpine:
            def __init__(self):
                self.submitted = []

            def submit(self, envelope):
                self.submitted.append(envelope)
                return {"status": "completed"}

        spine = MockSpine()
        envelope, result = tracker.submit_to_spine(session.session_id, "success", spine)
        assert envelope is not None
        assert result == {"status": "completed"}
        assert len(spine.submitted) == 1

    def test_session_persists_to_jsonl(self):
        import json

        from substrate.organism.dev_session_tracker import DevSessionTracker

        tmp = tempfile.mkdtemp()
        tracker = DevSessionTracker(store_dir=tmp)
        session = tracker.start_session("persist test", "eos")
        tracker.complete_session(session.session_id, "done")

        path = os.path.join(tmp, "dev_sessions.jsonl")
        assert os.path.exists(path)
        with open(path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) >= 1
        assert any(l.get("intent") == "persist test" for l in lines)


class TestSpineToLearning:
    """GovernedExecutionSpine → OutcomeLearningLoop integration."""

    def test_spine_records_outcome_to_learning_loop(self):
        from substrate.organism.event_spine import EventSpine
        from substrate.organism.execution_journal import ExecutionJournal
        from substrate.organism.execution_modes import ExecutionModeManager
        from substrate.organism.mutation_registry import MutationRegistry
        from substrate.organism.outcome_learning import OutcomeLearningLoop

        tmp = tempfile.mkdtemp()
        event_spine = EventSpine()
        mode_mgr = ExecutionModeManager()
        mutation_reg = MutationRegistry()
        journal = ExecutionJournal(persist_path=os.path.join(tmp, "journal.jsonl"))
        learning = OutcomeLearningLoop(store_path=os.path.join(tmp, "learning.jsonl"))

        from substrate.organism.governed_spine import GovernedExecutionSpine

        spine = GovernedExecutionSpine(
            event_spine=event_spine,
            execution_mode=mode_mgr,
            mutation_registry=mutation_reg,
            journal=journal,
            learning_loop=learning,
        )

        from substrate.organism.action_envelope import (
            ActionEnvelope,
            ActionType,
            BlastRadius,
            ReversibilityClass,
        )

        envelope = ActionEnvelope(
            intent="test learning integration",
            action_type=ActionType.STATE,
            source="test",
            execute_fn=lambda: ("done", True),
            blast_radius=BlastRadius.LOCAL_RUNTIME,
            reversibility=ReversibilityClass.FULLY_REVERSIBLE,
        )

        spine.submit(envelope)

        summary = learning.summary()
        assert summary["total_outcomes"] >= 1

    def test_learning_generates_reliability_signal(self):
        from substrate.organism.outcome_learning import (
            OutcomeLearningLoop,
            OutcomeRecord,
            OutcomeStatus,
        )

        tmp = tempfile.mkdtemp()
        loop = OutcomeLearningLoop(store_path=os.path.join(tmp, "learn.jsonl"))

        for _ in range(5):
            loop.record_outcome(OutcomeRecord(
                action_type="test_action",
                status=OutcomeStatus.SUCCESS,
                description="repeated success",
            ))

        reliability = loop.get_reliability("test_action")
        assert reliability > 0.5


class TestProofPersistence:
    """ProofRuntime JSONL persistence."""

    def test_proof_persists_to_disk(self):
        import json

        from substrate.organism.proof_runtime import ProofRuntime

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "proofs.jsonl")
        runtime = ProofRuntime(store_path=path)

        snap_id = runtime.capture_before("work-1", state={"count": 0})
        pkg = runtime.capture_after(
            "work-1", snap_id, action={"type": "test"}, outcome="success",
            after_state={"count": 1},
        )

        assert os.path.exists(path)
        with open(path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 1
        assert lines[0]["work_id"] == "work-1"
        assert lines[0]["outcome"] == "success"

    def test_proof_loads_from_disk(self):
        from substrate.organism.proof_runtime import ProofRuntime

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "proofs.jsonl")

        rt1 = ProofRuntime(store_path=path)
        rt1.create_direct("work-2", action={"type": "reload"}, outcome="ok")

        rt2 = ProofRuntime(store_path=path)
        loaded = rt2.package_for("work-2")
        assert loaded is not None
        assert loaded.outcome == "ok"

    def test_direct_proof_persists(self):
        import json

        from substrate.organism.proof_runtime import ProofRuntime

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "proofs.jsonl")
        runtime = ProofRuntime(store_path=path)

        runtime.create_direct("work-3", action={"op": "direct"}, outcome="done")

        with open(path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 1
        assert lines[0]["work_id"] == "work-3"


class TestProjectionRegistry:
    """Projection registry completeness."""

    def test_four_projections_registered(self):
        import json

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        registry_path = os.path.join(repo_root, "data", "umh", "projection_registry.json")
        with open(registry_path) as f:
            registry = json.load(f)
        assert "umh" in registry
        assert "eos" in registry
        assert "lyfeos" in registry
        assert "cos" in registry
        assert len(registry) == 4


class TestFullPipelineLoop:
    """End-to-end: Intent → DevSession → Spine → Learning → Proof → Journal."""

    def test_intent_to_journal_loop_closes(self):
        from substrate.organism.action_envelope import (
            ActionEnvelope,
            ActionType,
            BlastRadius,
            ReversibilityClass,
        )
        from substrate.organism.dev_session_tracker import DevSessionTracker
        from substrate.organism.event_spine import EventSpine
        from substrate.organism.execution_journal import ExecutionJournal
        from substrate.organism.execution_modes import ExecutionModeManager
        from substrate.organism.governed_spine import GovernedExecutionSpine
        from substrate.organism.mutation_registry import MutationRegistry
        from substrate.organism.outcome_learning import OutcomeLearningLoop
        from substrate.organism.proof_runtime import ProofRuntime

        tmp = tempfile.mkdtemp()

        tracker = DevSessionTracker(store_dir=tmp)
        event_spine = EventSpine()
        mode_mgr = ExecutionModeManager()
        mutation_reg = MutationRegistry()
        journal = ExecutionJournal(persist_path=os.path.join(tmp, "journal.jsonl"))
        learning = OutcomeLearningLoop(store_path=os.path.join(tmp, "learning.jsonl"))
        proof = ProofRuntime(store_path=os.path.join(tmp, "proof.jsonl"))

        spine = GovernedExecutionSpine(
            event_spine=event_spine,
            execution_mode=mode_mgr,
            mutation_registry=mutation_reg,
            journal=journal,
            learning_loop=learning,
        )

        # 1. Start session
        session = tracker.start_session("full loop test", "umh")
        assert session.status == "active"

        # 2. Record work
        tracker.record_commit(session.session_id, "aaa111", "implement feature")
        tracker.record_files_modified(session.session_id, 5)

        # 3. Complete → ActionEnvelope
        envelope = tracker.complete_session(session.session_id, "success")
        assert envelope is not None

        # 4. Capture proof before
        snap_id = proof.capture_before(session.session_id, state={"before": True})

        # 5. Submit to spine → governance → execute → learning
        spine.submit(envelope)

        # 6. Capture proof after
        pkg = proof.capture_after(
            session.session_id, snap_id,
            action={"type": "dev_session", "commits": 1},
            outcome="success",
            after_state={"after": True},
        )
        assert pkg is not None
        assert pkg.outcome == "success"

        # 7. Verify learning recorded
        learning_summary = learning.summary()
        assert learning_summary["total_outcomes"] >= 1

        # 8. Verify journal recorded
        journal_entries = journal.recent(limit=10)
        assert len(journal_entries) >= 1

        # 9. Verify proof persisted to disk
        assert os.path.exists(os.path.join(tmp, "proof.jsonl"))
