"""End-to-end test for UMH subsystems and ExecutionPipeline.

Tests individual subsystem lifecycles (TraceStore, ProofStore,
OutcomeClassifier, MemoryCandidateGenerator, WorkstationState) and the
full pipeline write+query path via ExecutionPipeline.submit_signal()
with Orchestrator's read-only query facade.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from services.umh.control_plane.pipeline import ExecutionPipeline
from services.umh.execution.executor import WorkPacketExecutor, build_default_executor
from services.umh.governance.policy_engine import PolicyEngine
from services.umh.governance.risk_classes import RiskClass
from services.umh.memory.candidate_generator import (
    MemoryCandidate,
    MemoryCandidateGenerator,
    PromotionStatus,
)
from services.umh.memory.promoter import MemoryPromoter
from services.umh.observability.outcome_classifier import (
    ClassificationResult,
    OutcomeCategory,
    OutcomeClassifier,
)
from services.umh.observability.proof_store import ProofArtifact, ProofStore
from services.umh.observability.trace_store import Trace, TraceStatus, TraceStore
from services.umh.orchestrator import Orchestrator
from services.umh.workstation.state import (
    ResumeState,
    WorkstationProfile,
    WorkstationSessionState,
    WorkstationSnapshot,
    WorkstationStateManager,
)


def test_trace_store() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = TraceStore(td)

        trace = store.create_trace(
            "test signal: user requested dashboard build",
            interpretation_ref="interp-001",
            governance_decision="approved",
            work_packet={"task": "build dashboard", "priority": "high"},
            adapter_used="discord",
            environment="vps",
            metadata={"session": "test-session-001"},
        )
        assert trace.trace_id.startswith("trace-")
        assert trace.status == TraceStatus.PENDING
        assert "dashboard" in trace.input_signal

        store.update_trace(
            trace.trace_id,
            status=TraceStatus.RUNNING,
            started_at="2026-05-18T10:00:00+00:00",
        )

        store.update_trace(
            trace.trace_id,
            status=TraceStatus.COMPLETED,
            execution_result={"success": True, "output": "dashboard built"},
            outcome="success",
            outcome_detail="completed successfully",
            completed_at="2026-05-18T10:01:00+00:00",
        )

        retrieved = store.get_trace(trace.trace_id)
        assert retrieved is not None
        assert retrieved.status == TraceStatus.COMPLETED
        assert retrieved.outcome == "success"

        results = store.query_traces(status=TraceStatus.COMPLETED)
        assert len(results) == 1
        assert results[0]["trace_id"] == trace.trace_id

        assert len(store.recent_traces(5)) == 1
        assert store.count() == 1


def test_proof_store() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = ProofStore(td)

        proof = store.store_proof(
            trace_id="trace-abc123",
            proof_type="test_result",
            content={
                "test_name": "test_dashboard_build",
                "passed": True,
                "assertions": 5,
                "duration_ms": 120,
            },
            summary="All 5 assertions passed in 120ms",
        )
        assert proof.proof_id.startswith("proof-")
        assert proof.proof_type == "test_result"

        retrieved = store.get_proof(proof.proof_id)
        assert retrieved is not None
        assert retrieved.content["passed"] is True

        assert len(store.proofs_for_trace("trace-abc123")) == 1
        assert len(store.recent_proofs(5)) == 1


def test_outcome_classifier() -> None:
    classifier = OutcomeClassifier()

    assert classifier.classify({"success": True, "output": "done"}).category == OutcomeCategory.SUCCESS
    assert classifier.classify({"error": "connection refused"}).category == OutcomeCategory.ERROR
    assert classifier.classify({"exit_code": 1}).category == OutcomeCategory.FAILURE
    assert classifier.classify({"timeout": True, "timeout_detail": "30s exceeded"}).category == OutcomeCategory.TIMEOUT
    assert classifier.classify({"skipped": True, "skip_reason": "not applicable"}).category == OutcomeCategory.SKIPPED
    assert classifier.classify({"partial": True, "partial_detail": "3 of 5 tasks done"}).category == OutcomeCategory.PARTIAL
    assert classifier.classify({}).category == OutcomeCategory.UNKNOWN
    assert classifier.classify({"output": "some data"}).category == OutcomeCategory.SUCCESS


def test_memory_candidate_generator() -> None:
    with tempfile.TemporaryDirectory() as td:
        gen = MemoryCandidateGenerator(td)

        candidate = gen.generate_candidate(
            source_trace_id="trace-abc123",
            content="Dashboard build pattern works with adapter=discord",
            reason="successful execution pattern worth remembering",
            confidence=0.8,
            scope="project",
            tags=["dashboard", "discord", "pattern"],
        )
        assert candidate.candidate_id.startswith("memcand-")
        assert candidate.promotion_status == PromotionStatus.STAGED
        assert "Dashboard" in candidate.content

        auto = gen.generate_from_trace(
            trace_id="trace-def456",
            input_signal="user requested KPI report generation",
            outcome="success",
            outcome_detail="report generated with 12 metrics",
            execution_result={"output": "report.pdf", "adapter": "operator_api"},
        )
        assert auto is not None
        assert "auto-generated" in auto.tags

        skipped = gen.generate_from_trace(
            trace_id="trace-ghi789",
            input_signal="failed task",
            outcome="failure",
            outcome_detail="connection refused",
        )
        assert skipped is None

        assert len(gen.get_candidates()) == 2
        assert len(gen.get_candidates(trace_id="trace-abc123")) == 1
        assert gen.count() == 2


def test_workstation_state() -> None:
    with tempfile.TemporaryDirectory() as td:
        manager = WorkstationStateManager(td)

        profile = WorkstationProfile.detect(user_id="antony", session_id="session-d")
        assert profile.hostname != ""
        assert profile.active_environment in ("vps", "local")

        session = WorkstationSessionState()
        session.record_activity("trace-001", "success")
        session.record_activity("trace-002", "failure")
        session.record_error()
        session.candidate_count = 1
        assert session.trace_count == 2
        assert session.error_count == 1

        recent_traces = [
            {
                "trace_id": "trace-002",
                "status": "failed",
                "outcome": "failure",
                "input_signal_preview": "failed task",
            },
            {
                "trace_id": "trace-001",
                "status": "completed",
                "outcome": "success",
                "input_signal_preview": "successful task",
            },
        ]

        snapshot = manager.build_snapshot(profile, session, recent_traces)
        assert snapshot.snapshot_at != ""
        assert "2 traces" in snapshot.resume.resume_summary
        assert "1 error" in snapshot.resume.resume_summary
        assert len(snapshot.resume.next_suggested_actions) > 0
        assert any("error" in a.lower() for a in snapshot.resume.next_suggested_actions)

        loaded = manager.load_snapshot()
        assert loaded is not None
        assert loaded.profile.user_id == "antony"


def test_pipeline_e2e() -> None:
    """Full pipeline write path + Orchestrator query facade.

    Replaces the former test_orchestrator_e2e which used the deprecated
    execute_trace() wrapper. Now exercises ExecutionPipeline.submit_signal()
    for writes and Orchestrator's read-only methods for queries.
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        trace_store = TraceStore(root / "traces")
        candidate_gen = MemoryCandidateGenerator(root / "memory_candidates")
        promoter = MemoryPromoter(path=root / "memories.json")

        executor = build_default_executor()

        pipeline = ExecutionPipeline(
            policy_engine=PolicyEngine(safe_roots=["/opt/OS"]),
            executor=executor,
            trace_store=trace_store,
            candidate_generator=candidate_gen,
            memory_promoter=promoter,
        )

        # --- Signal 1: successful shell command ---
        r1 = pipeline.submit_signal(
            "echo dashboard built",
            risk_class=RiskClass.READ_ONLY,
            adapter_name="shell",
            operation="execute",
            params={"command": "echo dashboard built"},
            metadata={"source": "e2e_test"},
        )
        assert r1.governance_approved is True
        assert r1.executed is True
        assert r1.success is True
        assert r1.proof_id is not None
        assert r1.outcome_type == "success"
        assert r1.memory_candidate_id is not None

        # --- Signal 2: governance-blocked (high risk, no pre-approval) ---
        r2 = pipeline.submit_signal(
            "send outreach emails to 50 leads",
            risk_class=RiskClass.IRREVERSIBLE_WRITE,
        )
        assert r2.governance_approved is False
        assert r2.executed is False
        assert r2.success is None
        assert r2.proof_id is None

        # --- Query via Orchestrator sharing the same stores ---
        orch = Orchestrator.__new__(Orchestrator)
        orch.trace_store = trace_store
        orch.proof_store = ProofStore(root / "proofs")
        orch.candidate_gen = candidate_gen
        orch.classifier = OutcomeClassifier()
        orch.state_manager = WorkstationStateManager(root / "workstation_state")
        orch._session = WorkstationSessionState()
        orch._session.record_activity("t1", "success")
        orch._session.record_activity("t2", "failure")
        orch._session.record_error()
        orch._profile = WorkstationProfile.detect()

        traces_resp = orch.get_traces()
        assert traces_resp["total"] == 2
        assert len(traces_resp["traces"]) == 2

        resume = orch.get_resume()
        assert "profile" in resume
        assert "session" in resume
        assert "resume" in resume
        assert resume["session"]["trace_count"] == 2
        assert resume["session"]["error_count"] == 1

        stats = orch.get_stats()
        assert stats["traces"] == 2


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  PASS  {name}")
            except AssertionError as e:
                print(f"  FAIL  {name}: {e}")
            except Exception as e:
                print(f"  ERROR {name}: {e}")
