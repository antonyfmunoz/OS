"""C32 Benchmark Cycle Tests — Cycles 2-5.

Tests for endpoints added during benchmark cycles:
  Cycle 2: /organism/adapter-health
  Cycle 3: /organism/spine-analytics
  Cycle 4: /organism/projection-health
  Cycle 5: Full pipeline integration
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, "/opt/OS")


# ── Cycle 2: Adapter Health Dashboard ──────────────────────────────────────


class TestAdapterHealth:
    def test_all_production_manifests_load(self):
        from adapters.adapter_engine.production_manifests import ALL_PRODUCTION_MANIFESTS

        assert len(ALL_PRODUCTION_MANIFESTS) >= 16

    def test_each_manifest_has_capabilities(self):
        from adapters.adapter_engine.production_manifests import ALL_PRODUCTION_MANIFESTS

        for m in ALL_PRODUCTION_MANIFESTS:
            assert m.adapter_id, f"manifest missing adapter_id"
            assert m.capabilities is not None, f"{m.adapter_id} has None capabilities"
            assert len(m.capabilities) >= 1, f"{m.adapter_id} has 0 capabilities"

    def test_handler_returns_summary(self):
        import asyncio

        async def _run():
            # Must import after patching _get_organism
            from transports.api.cockpit_spine_router import _adapter_health

            result = await _adapter_health()
            assert "total_adapters" in result
            assert result["total_adapters"] >= 16
            assert "total_capabilities" in result
            assert result["total_capabilities"] >= 35
            assert "maturity_distribution" in result
            assert "adapters" in result
            assert len(result["adapters"]) == result["total_adapters"]

        asyncio.run(_run())


# ── Cycle 3: Spine Execution Analytics ──────────────────────────────────────


class TestSpineAnalytics:
    def test_journal_has_entries(self):
        from substrate.organism.execution_journal import ExecutionJournal, JournalPhase

        tmp = tempfile.mkdtemp()
        j = ExecutionJournal(persist_path=os.path.join(tmp, "j.jsonl"))
        j.record("env-1", JournalPhase.EXECUTION_COMPLETED, "test", {"elapsed_ms": 100})
        j.record("env-2", JournalPhase.EXECUTION_FAILED, "test", {"elapsed_ms": 200})

        entries = j.recent(limit=10)
        assert len(entries) >= 2

        completed = [e for e in entries if e.phase == JournalPhase.EXECUTION_COMPLETED]
        failed = [e for e in entries if e.phase == JournalPhase.EXECUTION_FAILED]
        assert len(completed) >= 1
        assert len(failed) >= 1

    def test_analytics_computation(self):
        from substrate.organism.execution_journal import ExecutionJournal, JournalPhase

        tmp = tempfile.mkdtemp()
        j = ExecutionJournal(persist_path=os.path.join(tmp, "j.jsonl"))

        for i in range(8):
            j.record(f"env-{i}", JournalPhase.EXECUTION_COMPLETED, "test",
                    {"elapsed_ms": 100 + i * 10, "type": "heartbeat"})
        for i in range(2):
            j.record(f"env-fail-{i}", JournalPhase.EXECUTION_FAILED, "test",
                    {"elapsed_ms": 500, "type": "mutation"})

        entries = j.recent(limit=100)
        completed = [e for e in entries if e.phase == JournalPhase.EXECUTION_COMPLETED]
        failed = [e for e in entries if e.phase == JournalPhase.EXECUTION_FAILED]
        total = len(completed) + len(failed)
        success_rate = len(completed) / total if total > 0 else 0
        assert abs(success_rate - 0.8) < 0.01


# ── Cycle 4: Projection Health ──────────────────────────────────────────────


class TestProjectionHealth:
    def test_registry_has_four_projections(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(repo_root, "data", "umh", "projection_registry.json")
        with open(path) as f:
            reg = json.load(f)
        assert len(reg) == 4
        assert set(reg.keys()) == {"umh", "eos", "lyfeos", "cos"}

    def test_each_projection_has_required_fields(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(repo_root, "data", "umh", "projection_registry.json")
        with open(path) as f:
            reg = json.load(f)
        for pid, pdata in reg.items():
            assert "app_name" in pdata, f"{pid} missing app_name"
            assert "health_url" in pdata, f"{pid} missing health_url"
            assert "public_url" in pdata, f"{pid} missing public_url"

    def test_handler_returns_projections(self):
        import asyncio

        async def _run():
            from transports.api.cockpit_spine_router import _projection_health

            result = await _projection_health()
            assert "total_projections" in result
            assert result["total_projections"] >= 3
            assert "projections" in result
            assert len(result["projections"]) >= 3

        asyncio.run(_run())


# ── Cycle 5: Full Pipeline Integration ──────────────────────────────────────


class TestFullPipelineCycle5:
    def test_governed_execution_produces_complete_trace(self):
        from substrate.organism.action_envelope import (
            ActionEnvelope,
            ActionType,
            BlastRadius,
            ReversibilityClass,
        )
        from substrate.organism.benchmark_harness import BenchmarkHarness
        from substrate.organism.dev_session_tracker import DevSessionTracker
        from substrate.organism.event_spine import EventSpine
        from substrate.organism.execution_journal import ExecutionJournal
        from substrate.organism.execution_modes import ExecutionModeManager
        from substrate.organism.governed_spine import GovernedExecutionSpine
        from substrate.organism.mutation_registry import MutationRegistry
        from substrate.organism.outcome_learning import OutcomeLearningLoop
        from substrate.organism.proof_runtime import ProofRuntime

        tmp = tempfile.mkdtemp()

        # Initialize all subsystems
        tracker = DevSessionTracker(store_dir=tmp)
        event_spine = EventSpine()
        mode_mgr = ExecutionModeManager()
        mutation_reg = MutationRegistry()
        journal = ExecutionJournal(persist_path=os.path.join(tmp, "journal.jsonl"))
        learning = OutcomeLearningLoop(store_path=os.path.join(tmp, "learning.jsonl"))
        proof = ProofRuntime(store_path=os.path.join(tmp, "proof.jsonl"))
        harness = BenchmarkHarness(store_path=os.path.join(tmp, "bench.jsonl"))

        spine = GovernedExecutionSpine(
            event_spine=event_spine,
            execution_mode=mode_mgr,
            mutation_registry=mutation_reg,
            journal=journal,
            learning_loop=learning,
        )

        # Start benchmark
        harness.start_cycle("cycle-5-test", "governed", "full pipeline test")

        # 1. Intent → DevSession
        session = tracker.start_session("cycle 5 full pipeline validation", "umh")
        tracker.record_commit(session.session_id, "test123", "test commit")
        tracker.record_files_modified(session.session_id, 3)

        # 2. Proof before
        snap_id = proof.capture_before(session.session_id, state={"before": True})

        # 3. Complete → ActionEnvelope → Spine
        envelope, spine_result = tracker.submit_to_spine(
            session.session_id, "success", spine
        )
        assert envelope is not None

        # 4. Proof after
        pkg = proof.capture_after(
            session.session_id, snap_id,
            action={"type": "full_pipeline_test"},
            outcome="success",
            after_state={"after": True},
        )

        # 5. End benchmark
        harness.end_cycle("cycle-5-test", "governed",
            files_changed=3, commits=1, tests_written=1, tests_passed=1,
            spine_submissions=1,
            journal_entries=len(journal.recent(100)),
            learning_signals_generated=len(learning.recent_signals(100)),
            proof_packages_created=1,
        )

        # Verify complete chain
        assert learning.summary()["total_outcomes"] >= 1
        assert len(journal.recent(100)) >= 1
        assert pkg.outcome == "success"
        assert os.path.exists(os.path.join(tmp, "proof.jsonl"))
        assert os.path.exists(os.path.join(tmp, "bench.jsonl"))
        assert len(harness.all_records()) == 1
